import uuid
import fitz  # PyMuPDF
from urllib.parse import urlparse
from typing import Dict, Any
import hashlib

from llama_index.core import Document as LlamaDocument
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.connection import db_manager

class IngestionService:
    def __init__(self):
        # Initialize embedding model (Forced to CPU per ADR-005)
        self.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu"
        )
        
        # Configure chunking strategy
        self.pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=settings.CHUNK_SIZE, 
                    chunk_overlap=settings.CHUNK_OVERLAP
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
                port=url.port,
                user=url.username,
                table_name="enterprise_documents",
                embed_dim=settings.EMBEDDING_DIMENSION,
                hybrid_search=True,
                text_search_config="english"
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

    def ingest_document(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Runs the complete ingestion pipeline with SHA-256 deduplication."""
        
        # 1. Generate SHA-256 hash of the file content
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        logger.info("Starting ingestion", extra={"file_name": filename, "file_hash": file_hash})
        
        # 2. Deduplication Check: Does this exact file already exist?
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, chunk_count FROM documents WHERE file_hash = %s;", 
                    (file_hash,)
                )
                existing_doc = cur.fetchone()
                
                if existing_doc:
                    logger.info("Duplicate document detected; skipping ingestion.", extra={"file_name": filename})
                    return {
                        "document_id": str(existing_doc[0]),
                        "filename": filename,
                        "chunk_count": existing_doc[1],
                        "status": "skipped_duplicate"
                    }

        # 3. Proceed with Ingestion (if new file)
        raw_text = self.extract_text(pdf_bytes)
        document_id = str(uuid.uuid4())
        
        doc = LlamaDocument(
            text=raw_text,
            metadata={"filename": filename, "document_id": document_id, "file_hash": file_hash}
        )
        
        _ = self.vector_store
        nodes = self.pipeline.run(documents=[doc])
        
        if not nodes:
            raise ValueError("Ingestion pipeline produced zero chunks.")
            
        # 4. Save to Document Tracking Table
        self._store_document_metadata(
            document_id=document_id,
            filename=filename,
            file_hash=file_hash,
            chunk_count=len(nodes)
        )
            
        logger.info("Ingestion complete", extra={
            "document_id": document_id, 
            "chunks": len(nodes)
        })
        
        return {
            "document_id": document_id,
            "filename": filename,
            "chunk_count": len(nodes),
            "status": "success"
        }

    def _store_document_metadata(self, document_id: str, filename: str, file_hash: str, chunk_count: int):
        """Persists the master document record to PostgreSQL."""
        insert_sql = """
            INSERT INTO documents (id, filename, file_hash, chunk_count)
            VALUES (%s, %s, %s, %s)
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(insert_sql, (document_id, filename, file_hash, chunk_count))
                conn.commit()
        except Exception as e:
            logger.error("Failed to store document metadata", extra={"error": str(e)})
            raise ValueError("Database error while saving document metadata.")
        
# Singleton instance for the application
ingestion_service = IngestionService()