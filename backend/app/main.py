from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import health
from backend.app.core.config import settings
from backend.app.db.connection import db_manager
from backend.app.core.logging import logger
from backend.app.api import health, documents, queries

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise Document Intelligence API powered by FastAPI and LlamaIndex"
    )
    
    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"], # React local development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Application startup lifecycle
    @app.on_event("startup")
    def startup_event():
        logger.info("Starting up microservice...")
        db_manager.initialize_pool()
        
    @app.on_event("shutdown")
    def shutdown_event():
        logger.info("Shutting down microservice...")
        if db_manager.pool:
            db_manager.pool.closeall()

    # Include Routers
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(queries.router)
    
    return app

app = create_app()