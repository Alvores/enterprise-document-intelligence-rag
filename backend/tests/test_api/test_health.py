def test_health_check(client):
    """Test the basic liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Enterprise RAG Platform"}

def test_database_health_check(client):
    """Test the database readiness probe."""
    response = client.get("/health/db")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["pgvector"] == "installed"