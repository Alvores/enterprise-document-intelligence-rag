from typing import Dict, Any
from urllib.parse import urlparse

from llama_index.core import VectorStoreIndex, PromptTemplate
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from backend.app.core.config import settings
from backend.app.core.constants import TOP_K_RETRIEVAL, HYBRID_VECTOR_WEIGHT, RAG_SYSTEM_TEMPLATE, RAG_REFINE_TEMPLATE
from backend.app.services.ollama_client import llm_service
from backend.app.core.logging import logger

class RetrievalService:
    """Orchestrates document retrieval and LLM answer generation."""
    
    def __init__(self):
        # We use the exact same embedding model used in ingestion to ensure vectors match
        self.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu"
        )
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
                port=url.port,
                user=url.username,
                table_name="enterprise_documents",
                embed_dim=settings.EMBEDDING_DIMENSION,
                hybrid_search=True,
                text_search_config="english"
            )
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self.embed_model
            )
        return self._index

    @property
    def query_engine(self) -> RetrieverQueryEngine:
        """Assembles the retrieval, the LLM, and the system prompt."""
        if self._query_engine is None:
            logger.info("Initializing RAG Query Engine...")
            
            # 1. Configure the Retriever (Fetch Top 5 chunks)
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=TOP_K_RETRIEVAL
            )
            
            # 2. Assemble the Engine with our local Ollama model
            self._query_engine = RetrieverQueryEngine.from_args(
                retriever=retriever,
                llm=llm_service.llm,
                vector_store_query_mode="hybrid",
                alpha=HYBRID_VECTOR_WEIGHT
            )
            
            # 3. Inject our strict Enterprise System Prompt
            qa_prompt = PromptTemplate(RAG_SYSTEM_TEMPLATE)
            refine_prompt = PromptTemplate(RAG_REFINE_TEMPLATE)
            self._query_engine.update_prompts({
                "response_synthesizer:text_qa_template": qa_prompt,
                "response_synthesizer:refine_template": refine_prompt
            })
            
        return self._query_engine

    def query(self, user_question: str) -> Dict[str, Any]:
        """Executes a RAG query and extracts citations."""
        logger.info("Executing RAG query", extra={"query": user_question})
        
        try:
            # 1. Run the query through the engine
            response = self.query_engine.query(user_question)
            
            # 2. Extract citations (The exact chunks used by the LLM)
            citations = []
            for node in response.source_nodes:
                citations.append({
                    "document_id": node.metadata.get("document_id", "Unknown"),
                    "filename": node.metadata.get("filename", "Unknown"),
                    "score": float(node.score) if node.score else 0.0,
                    "text": node.get_content().strip()
                })
                
            logger.info("Query successful", extra={"citations_retrieved": len(citations)})
            
            # 3. Return the payload
            return {
                "answer": str(response),
                "sources": citations
            }
            
        except Exception as e:
            logger.error("RAG query failed", extra={"error": str(e)})
            raise ValueError(f"Failed to process query: {str(e)}")

# Singleton instance for the application
retrieval_service = RetrievalService()