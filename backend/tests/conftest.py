import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    """Provides a reusable FastAPI TestClient with lifespan startup/shutdown."""
    with TestClient(app) as c:
        yield c
