from unittest.mock import patch

def test_upload_invalid_file_type(client):
    """Ensure the API rejects non-PDF files before triggering AI logic."""
    file_data = {"file": ("malicious.exe", b"dummy bytes", "application/x-msdownload")}
    response = client.post("/documents/upload", files=file_data)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are accepted."

@patch("backend.app.api.documents.ingestion_service.ingest_document")
def test_upload_valid_pdf(mock_ingest, client):
    """Ensure valid PDFs are routed correctly and responses match the schema."""
    
    # 1. Instruct the mock to return a fake successful pipeline result
    mock_ingest.return_value = {
        "document_id": "test-uuid-1234",
        "filename": "test_paper.pdf",
        "chunk_count": 15,
        "status": "success"
    }

    # 2. Send a fake PDF payload
    file_data = {"file": ("test_paper.pdf", b"%PDF-1.4 dummy data", "application/pdf")}
    response = client.post("/documents/upload", files=file_data)

    # 3. Assertions
    assert response.status_code == 201
    
    data = response.json()
    assert data["document_id"] == "test-uuid-1234"
    assert data["filename"] == "test_paper.pdf"
    assert data["chunk_count"] == 15
    assert data["status"] == "success"
    assert "uploaded_at" in data
    
    # Verify the AI service was actually called with our bytes
    mock_ingest.assert_called_once()