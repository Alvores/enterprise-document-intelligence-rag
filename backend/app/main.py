from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.app.core.config import settings
from backend.app.db.connection import db_manager
from backend.app.core.logging import logger
from backend.app.api import health, documents, queries

# Define the lifespan context manager BEFORE creating the app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up microservice...")
    db_manager.initialize_pool()
    yield
    # Shutdown logic
    logger.info("Shutting down microservice...")
    if db_manager.pool:
        db_manager.pool.closeall()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise Document Intelligence API powered by FastAPI and LlamaIndex",
        lifespan=lifespan
    )
    
    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"], # React local development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routers
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(queries.router)
    
    return app

app = create_app()