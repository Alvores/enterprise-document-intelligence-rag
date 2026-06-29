from unittest.mock import patch

def test_query_validation_error(client):
    """Ensure the API rejects empty or overly short queries before hitting the LLM."""
    payload = {"query": "a"} # Shorter than min_length=2
    response = client.post("/query", json=payload)
    
    assert response.status_code == 422

@patch("backend.app.api.queries.retrieval_service.query")
def test_successful_rag_query(mock_query, client):
    """Ensure a valid query returns the expected Pydantic schema and citations."""
    
    # 1. Instruct the mock to return a fake dictionary mimicking the engine's output
    mock_query.return_value = {
        "answer": "This is a mocked LLM answer about attention.",
        "sources": [
            {
                "document_id": "test-doc-uuid",
                "filename": "fake_paper.pdf",
                "text": "This chunk mentions attention.",
                "score": 0.85
            }
        ]
    }
    
    # 2. Send the HTTP request
    payload = {"query": "What is attention?"}
    response = client.post("/query", json=payload)
    
    # 3. Assertions
    assert response.status_code == 200
    
    data = response.json()
    assert data["answer"] == "This is a mocked LLM answer about attention."
    assert len(data["sources"]) == 1
    
    # Check the citation mapping
    citation = data["sources"][0]
    assert citation["filename"] == "fake_paper.pdf"
    assert citation["score"] == 0.85
    
    # Check that execution time was calculated and included
    assert "execution_time_ms" in data
    assert type(data["execution_time_ms"]) is int
    
    # Verify the internal service was called exactly once with our string
    mock_query.assert_called_once_with("What is attention?")