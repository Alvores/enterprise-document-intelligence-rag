from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from backend.app.core.config import settings
from backend.app.core.logging import logger

# Define the exact header name we expect clients to use
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Validates the incoming API key against the environment secret."""
    if not api_key:
        logger.warning("Rejected request: Missing API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    if api_key != settings.API_KEY:
        logger.warning("Rejected request: Invalid API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    return api_key
