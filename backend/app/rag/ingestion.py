import hashlib
import uuid
from typing import Any
from urllib.parse import urlparse

import fitz  # PyMuPDF
from llama_index.core import Document as LlamaDocument
from llama_index.core import Settings as LlamaIndexSettings
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from transformers import AutoTokenizer

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.connection import db_manager
from backend.app.services.storage_queue import storage_queue


class IngestionService:
    def __init__(self):
        # Initialize embedding model (Forced to CPU per ADR-005)
        self.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu",
            query_instruction="Represent this sentence for searching relevant articles: ",
        )

        # Load embedding tokenizer identifier
        logger.info("Downloading native embedding tokenizer for ingestion telemetry...")
        self.embed_tokenizer = AutoTokenizer.from_pretrained(settings.EMBEDDING_TOKENIZER_ID)

        # Configure chunking strategy
        self.pipeline = IngestionPipeline(
            transformations=[
                SentenceWindowNodeParser.from_defaults(
                    window_size=settings.SENTENCE_WINDOW_SIZE,
                    window_metadata_key="window",
                    original_text_metadata_key="original_text",
                ),
                self.embed_model,
            ]
        )
        self._vector_store = None

    @property
    def vector_store(self):
        """Lazy-loads the PGVectorStore connection."""
        if self._vector_store is None:
            url = urlparse(settings.DATABASE_URL)
            self._vector_store = PGVectorStore.from_params(
                database=url.path[1:],
                host=url.hostname,
                password=url.password,
                port=url.port or 5432,
                user=url.username,
                table_name="enterprise_documents",
                embed_dim=settings.EMBEDDING_DIMENSION,
                hybrid_search=True,
                text_search_config="english",
            )
            self.pipeline.vector_store = self._vector_store
        return self._vector_store

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extracts text from PDF bytes using PyMuPDF."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.page_count == 0:
                raise ValueError("PDF has no pages.")

            text_parts = [page.get_text() for page in doc]
            full_text = "\n".join(text_parts).strip()

            if not full_text:
                raise ValueError("No extractable text found (scanned image without OCR?)")

            return full_text
        except Exception as e:
            logger.error("PDF text extraction failed", extra={"error": str(e)})
            raise ValueError(f"Failed to extract text: {str(e)}")

    def stage_document(self, pdf_bytes: bytes, filename: str) -> dict[str, Any]:
        """Producer: validates deduplication, stages PDF bytes, and publishes ingestion event."""
        # 1. Generate SHA-256 hash of the file content
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        logger.info(
            "Staging document for ingestion", extra={"file_name": filename, "file_hash": file_hash}
        )

        # 2. Deduplication Check: Does this exact file already exist?
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, chunk_count, status FROM documents WHERE file_hash = %s;",
                    (file_hash,),
                )
                existing_doc = cur.fetchone()

                if existing_doc:
                    if existing_doc[2] in ("READY", "PENDING"):
                        logger.info(
                            "Duplicate document detected; skipping ingestion.",
                            extra={"file_name": filename, "status": existing_doc[2]},
                        )
                        return {
                            "document_id": str(existing_doc[0]),
                            "filename": filename,
                            "chunk_count": existing_doc[1],
                            "status": "skipped_duplicate",
                        }
                    # Previous attempt failed; clear row so the user can re-upload
                    cur.execute("DELETE FROM documents WHERE file_hash = %s;", (file_hash,))
            conn.commit()

        # 3. Stage raw PDF binary to GCS (or local staging dir)
        document_id = str(uuid.uuid4())
        gcs_uri = storage_queue.upload_bytes(document_id, filename, pdf_bytes)

        # 4. Insert initial PENDING record (chunk_count starts at 0 until worker finishes)
        insert_sql = """
            INSERT INTO documents (id, filename, file_hash, chunk_count, status, gcs_uri)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        insert_sql, (document_id, filename, file_hash, 0, "PENDING", gcs_uri)
                    )
                conn.commit()
        except Exception as e:
            logger.error("Failed to store initial document metadata", extra={"error": str(e)})
            raise ValueError("Database error while saving document metadata.")

        # 5. Publish ingestion event to Cloud Pub/Sub (or dispatch inline in local mode)
        storage_queue.publish_event(
            {
                "document_id": document_id,
                "filename": filename,
                "file_hash": file_hash,
                "gcs_uri": gcs_uri,
            }
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "chunk_count": 0,
            "status": "PENDING",
        }

    def process_document_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Consumer: downloads staged PDF, generates sentence-window embeddings, updates status."""
        filename = payload["filename"]
        document_id = payload["document_id"]
        file_hash = payload["file_hash"]
        gcs_uri = payload["gcs_uri"]

        logger.info(
            "Processing ingestion event",
            extra={"document_id": document_id, "file_name": filename, "gcs_uri": gcs_uri},
        )

        try:
            # 1. Setup Token Telemetry
            embed_counter = TokenCountingHandler(tokenizer=self.embed_tokenizer.encode)
            LlamaIndexSettings.callback_manager = CallbackManager([embed_counter])

            # 2. Download staged PDF bytes and extract raw text
            pdf_bytes = storage_queue.download_bytes(gcs_uri)
            raw_text = self.extract_text(pdf_bytes)

            doc = LlamaDocument(
                text=raw_text,
                metadata={
                    "filename": filename,
                    "document_id": document_id,
                    "file_hash": file_hash,
                },
            )

            # 3. Parse into sentence windows, embed, and upsert into pgvector
            _ = self.vector_store
            nodes = self.pipeline.run(documents=[doc])

            if not nodes:
                raise ValueError("Ingestion pipeline produced zero chunks.")

            # 4. Transition document state to READY
            self._mark_document_ready(document_id=document_id, chunk_count=len(nodes))

            # 5. Log Exact Embedding Telemetry
            logger.info(
                "Exact Embedding Telemetry Captured",
                extra={
                    "document_id": document_id,
                    "file_name": filename,
                    "chunks_generated": len(nodes),
                    "total_embedding_tokens": embed_counter.total_embedding_token_count,
                },
            )
            logger.info(
                "Ingestion complete", extra={"document_id": document_id, "chunks": len(nodes)}
            )

            return {
                "document_id": document_id,
                "filename": filename,
                "chunk_count": len(nodes),
                "status": "READY",
            }

        except Exception as e:
            logger.error(
                "Async document processing failed",
                extra={"document_id": document_id, "error": str(e)},
            )
            self._mark_document_failed(document_id=document_id, error_message=str(e))
            raise

    def _mark_document_ready(self, document_id: str, chunk_count: int) -> None:
        """Marks the document as READY with its final chunk count."""
        update_sql = """
            UPDATE documents
            SET status = 'READY', chunk_count = %s, error_message = NULL
            WHERE id = %s
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(update_sql, (chunk_count, document_id))
                conn.commit()
        except Exception as e:
            logger.error("Failed to mark document READY", extra={"error": str(e)})
            raise ValueError("Database error while updating document status.")

    def _mark_document_failed(self, document_id: str, error_message: str) -> None:
        """Records the failure reason on the document row without masking the original error."""
        update_sql = """
            UPDATE documents
            SET status = 'FAILED', error_message = %s
            WHERE id = %s
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(update_sql, (error_message[:1000], document_id))
                conn.commit()
        except Exception as db_err:
            logger.error(
                "Failed to persist FAILED status to database",
                extra={"document_id": document_id, "error": str(db_err)},
            )


# Singleton instance for the application
ingestion_service = IngestionService()
