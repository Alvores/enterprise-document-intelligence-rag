import os

from llama_index.llms.gemini import Gemini
from llama_index.llms.ollama import Ollama

from backend.app.core.config import settings
from backend.app.core.logging import logger


class LLMService:
    """Manages generative LLM instances across Local (Ollama) and Cloud (Gemini) environments."""

    def __init__(self):
        self.model_name = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            gemini_key = os.getenv("GEMINI_API_KEY")

            if gemini_key:
                logger.info("Initializing Gemini Generative Model for Cloud Runtime...")
                self._llm = Gemini(
                    model="models/gemini-3.6-flash",
                    api_key=gemini_key,
                    temperature=self.temperature,
                )
            else:
                logger.info(
                    "Initializing Ollama Generative Model for Local Runtime...",
                    extra={"model": self.model_name, "host": settings.OLLAMA_HOST},
                )
                self._llm = Ollama(
                    model=self.model_name,
                    base_url=settings.OLLAMA_HOST,
                    temperature=self.temperature,
                    request_timeout=120.0,
                )
        return self._llm


llm_service = LLMService()
