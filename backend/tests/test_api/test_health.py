from unittest.mock import MagicMock, patch


def test_health_check(client):
    """Test the basic liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Enterprise RAG Platform"}


@patch("backend.app.api.health.db_manager.get_connection")
def test_database_health_check(mock_get_conn, client):
    """Test the database readiness probe with a mocked database connection."""
    # 1. Setup mock cursor to return valid pgvector query response
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)  # Simulates "SELECT 1" and pgvector check success

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    # 2. Call health endpoint
    response = client.get("/health/db")

    # 3. Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["pgvector"] == "installed"