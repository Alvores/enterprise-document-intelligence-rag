import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    """Provides a reusable FastAPI TestClient without triggering live DB lifespan hooks."""
    return TestClient(app)
