from llama_index.llms.ollama import Ollama
from backend.app.core.config import settings
from backend.app.core.logging import logger

class LLMService:
    """Manages the connection to the local generative LLM."""
    
    def __init__(self):
        self.model_name = settings.LLM_MODEL
        self.host = settings.OLLAMA_HOST
        self.temperature = settings.LLM_TEMPERATURE
        self._llm = None

    @property
    def llm(self) -> Ollama:
        """Lazy-loads the Ollama connection."""
        if self._llm is None:
            logger.info("Initializing Ollama Generative Model...", extra={
                "model": self.model_name,
                "host": self.host
            })
            self._llm = Ollama(
                model=self.model_name,
                base_url=self.host,
                temperature=self.temperature,
                request_timeout=120.0 # Generation can take longer than embeddings
            )
        return self._llm

# Singleton instance
llm_service = LLMService()