import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically locate the .env file at the project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

class Settings:
    APP_NAME: str = "Enterprise Document Intelligence RAG"
    APP_VERSION: str = "0.1.0"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Ollama Configuration
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

settings = Settings()