from fastapi import APIRouter, HTTPException
from backend.app.core.logging import logger
from backend.app.db.connection import db_manager

router = APIRouter(tags=["Health & Operations"])

@router.get("/health")
def health_check():
    logger.info("Basic liveness check invoked")
    return {"status": "ok", "service": "Enterprise RAG Platform"}

@router.get("/health/db")
def database_health_check():
    logger.info("Database readiness check invoked")
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Check for the vector extension specifically
                cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
                result = cur.fetchone()
                
                return {
                    "status": "healthy",
                    "database": "connected",
                    "pgvector": "installed" if result else "missing"
                }
    except Exception as e:
        logger.error("Database health check failed", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Database is unavailable")