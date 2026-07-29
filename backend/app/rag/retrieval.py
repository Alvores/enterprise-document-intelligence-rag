from typing import Any
from urllib.parse import urlparse

from llama_index.core import PromptTemplate, VectorStoreIndex
from llama_index.core import Settings as LlamaIndexSettings
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from transformers import AutoTokenizer

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag.constants import (
    HYBRID_VECTOR_WEIGHT,
    RAG_REFINE_TEMPLATE,
    RAG_SYSTEM_TEMPLATE,
    TOP_K_RETRIEVAL,
)
from backend.app.services.llm_factory import llm_service


class RetrievalService:
    """Orchestrates document retrieval and LLM answer generation."""

    def __init__(self):
        # We use the exact same embedding model used in ingestion to ensure vectors match
        self.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu",
            query_instruction="Represent this sentence for searching relevant articles: ",
        )

        # Initialize native tokenizers for exact LLMOps telemetry
        logger.info("Downloading native tokenizers for telemetry...")
        self.embed_tokenizer = AutoTokenizer.from_pretrained(settings.EMBEDDING_TOKENIZER_ID)
        self.llm_tokenizer = AutoTokenizer.from_pretrained(settings.LLM_TOKENIZER_ID)

        self._index = None
        self._query_engine = None

    @property
    def index(self) -> VectorStoreIndex:
        """Lazy-loads the connection to pgvector."""
        if self._index is None:
            url = urlparse(settings.DATABASE_URL)
            vector_store = PGVectorStore.from_params(
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
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, embed_model=self.embed_model
            )
        return self._index

    @property
    def query_engine(self) -> RetrieverQueryEngine:
        """Assembles the retrieval, the LLM, and the system prompt."""
        if self._query_engine is None:
            logger.info("Initializing RAG Query Engine...")

            # 1. Configure the Retriever (Fetch Top 5 chunks)
            retriever = VectorIndexRetriever(index=self.index, similarity_top_k=TOP_K_RETRIEVAL)

            # 2. Assemble the Engine with our local Ollama model
            self._query_engine = RetrieverQueryEngine.from_args(
                retriever=retriever,
                llm=llm_service.llm,
                vector_store_query_mode="hybrid",
                alpha=HYBRID_VECTOR_WEIGHT,
            )

            # 3. Inject our strict Enterprise System Prompt
            qa_prompt = PromptTemplate(RAG_SYSTEM_TEMPLATE)
            refine_prompt = PromptTemplate(RAG_REFINE_TEMPLATE)
            self._query_engine.update_prompts(
                {
                    "response_synthesizer:text_qa_template": qa_prompt,
                    "response_synthesizer:refine_template": refine_prompt,
                }
            )

        return self._query_engine

    def query(self, user_question: str) -> dict[str, Any]:
        """Executes a RAG query and extracts citations."""
        logger.info("Executing RAG query", extra={"query": user_question})

        # Set up exact token counters for this specific request
        embed_counter = TokenCountingHandler(tokenizer=self.embed_tokenizer.encode)
        llm_counter = TokenCountingHandler(tokenizer=self.llm_tokenizer.encode)
        LlamaIndexSettings.callback_manager = CallbackManager([embed_counter, llm_counter])

        try:
            # 1. Run the query through the engine
            response = self.query_engine.query(user_question)

            # 2. Extract citations (The exact chunks used by the LLM)
            citations = []
            for node in response.source_nodes:
                citations.append(
                    {
                        "document_id": node.metadata.get("document_id", "Unknown"),
                        "filename": node.metadata.get("filename", "Unknown"),
                        "score": float(node.score) if node.score else 0.0,
                        "text": node.get_content().strip(),
                    }
                )

            # 3. Log Exact Telemetry
            logger.info(
                "Exact LLM Telemetry Captured",
                extra={
                    "prompt_tokens": llm_counter.prompt_llm_token_count,
                    "completion_tokens": llm_counter.completion_llm_token_count,
                    "total_llm_tokens": llm_counter.total_llm_token_count,
                    "embedding_tokens": embed_counter.total_embedding_token_count,
                },
            )
            logger.info("Query successful", extra={"citations_retrieved": len(citations)})

            # 4. Return the payload
            return {"answer": str(response), "sources": citations}

        except Exception as e:
            logger.error("RAG query failed", extra={"error": str(e)})
            raise ValueError(f"Failed to process query: {str(e)}")


# Singleton instance for the application
retrieval_service = RetrievalService()
