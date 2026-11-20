import base64
import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import patch

from backend.app.core.config import settings

DOCUMENT_ID = "11111111-1111-1111-1111-111111111111"
AUTHORIZATION = "Bearer test-token"
VALID_EVENT = {
    "document_id": DOCUMENT_ID,
    "filename": "test_paper.pdf",
    "file_hash": "6cd3556deb0da54bca060b4c39479839",
    "gcs_uri": "gs://my-bucket/test_paper.pdf",
}


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, query, params=None):
        pass

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self, row):
        self._cursor = _FakeCursor(row)

    def cursor(self):
        return self._cursor

    def commit(self):
        pass


@contextmanager
def _fake_db_connection(row):
    yield _FakeConnection(row)


def _encode_push_envelope(event: dict) -> dict:
    data = base64.b64encode(json.dumps(event).encode("utf-8")).decode("utf-8")
    return {
        "message": {
            "data": data,
            "messageId": "msg-123",
            "publishTime": "2026-11-18T00:00:00Z",
        },
        "subscription": "projects/enterprise-rag-2026/subscriptions/worker-push",
    }


def test_upload_unauthorized(client):
    """Ensure the API rejects calls missing a valid API key completely."""
    file_data = {"file": ("test.pdf", b"dummy data", "application/pdf")}
    response = client.post("/documents/upload", files=file_data)  # No headers
    assert response.status_code == 401


def test_upload_invalid_file_type(client):
    """Ensure the API rejects non-PDF files before triggering AI logic."""
    file_data = {"file": ("malicious.exe", b"dummy bytes", "application/x-msdownload")}
    response = client.post(
        "/documents/upload", files=file_data, headers={"X-API-Key": settings.API_KEY}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are accepted."


@patch("backend.app.api.documents.ingestion_service.stage_document")
def test_stage_valid_pdf(mock_ingest, client):
    """Ensure valid PDFs are staged and the API returns 202 Accepted."""

    mock_ingest.return_value = {
        "document_id": "test-uuid-1234",
        "filename": "test_paper.pdf",
        "chunk_count": 0,
        "status": "PENDING",
    }

    file_data = {"file": ("test_paper.pdf", b"%PDF-1.4 dummy data", "application/pdf")}
    response = client.post(
        "/documents/upload", files=file_data, headers={"X-API-Key": settings.API_KEY}
    )

    assert response.status_code == 202

    data = response.json()
    assert data["document_id"] == "test-uuid-1234"
    assert data["filename"] == "test_paper.pdf"
    assert data["chunk_count"] == 0
    assert data["status"] == "PENDING"
    assert "uploaded_at" in data

    mock_ingest.assert_called_once()


@patch("backend.app.api.documents.ingestion_service.process_document_event")
@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_valid_pubsub(mock_verify, mock_process, client):
    """Ensure a valid Pub/Sub envelope is decoded, dispatched, and ACKed with 200."""

    mock_process.return_value = {
        "document_id": DOCUMENT_ID,
        "filename": "test_paper.pdf",
        "chunk_count": 15,
        "status": "READY",
    }

    response = client.post(
        "/documents/worker",
        json=_encode_push_envelope(VALID_EVENT),
        headers={"Authorization": AUTHORIZATION},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["document_id"] == DOCUMENT_ID
    assert data["filename"] == "test_paper.pdf"
    assert data["chunk_count"] == 15
    assert data["status"] == "READY"

    mock_verify.assert_called_once_with(AUTHORIZATION)
    mock_process.assert_called_once_with(VALID_EVENT)


@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_worker_invalid_oidc(mock_verify, client):
    """Ensure an invalid OIDC token is rejected with 401 (not ACKed)."""
    mock_verify.side_effect = PermissionError("Invalid Pub/Sub OIDC token.")

    response = client.post(
        "/documents/worker",
        json=_encode_push_envelope(VALID_EVENT),
        headers={"Authorization": "Bearer tampered-token"},
    )

    assert response.status_code == 401
    assert "OIDC" in response.json()["detail"]


@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_worker_corrupt_base64(mock_verify, client):
    """Ensure a corrupt Base64 payload returns 400."""
    response = client.post("/documents/worker", json={"message": {"data": "@@@@"}})

    assert response.status_code == 400


@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_worker_corrupt_json(mock_verify, client):
    """Ensure Base64 that does not decode to JSON returns 400."""
    encoded = base64.b64encode(b"definitely-not-json").decode("utf-8")

    response = client.post("/documents/worker", json={"message": {"data": encoded}})

    assert response.status_code == 400


@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_worker_missing_event_keys(mock_verify, client):
    """Ensure a decoded event missing required keys returns 400."""
    encoded = base64.b64encode(json.dumps({"document_id": DOCUMENT_ID}).encode("utf-8"))

    response = client.post("/documents/worker", json={"message": {"data": encoded.decode("utf-8")}})

    assert response.status_code == 400


@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_worker_empty_data(mock_verify, client):
    """Ensure an empty message.data field returns 400."""
    response = client.post("/documents/worker", json={"message": {"data": ""}})

    assert response.status_code == 400


@patch("backend.app.api.documents.ingestion_service.process_document_event")
@patch("backend.app.api.documents.storage_queue.verify_worker_token")
def test_process_worker_returns_500_on_failure(mock_verify, mock_process, client):
    """Ensure a transient ingestion failure returns 500 so Pub/Sub retries."""
    mock_process.side_effect = RuntimeError("database connection dropped")

    response = client.post(
        "/documents/worker",
        json=_encode_push_envelope(VALID_EVENT),
        headers={"Authorization": AUTHORIZATION},
    )

    assert response.status_code == 500


@patch("backend.app.api.documents.db_manager.get_connection")
def test_get_document_status_ready(mock_get_connection, client):
    """Ensure polling a READY document returns its status payload."""
    mock_get_connection.return_value = _fake_db_connection(
        (
            uuid.UUID(DOCUMENT_ID),
            "test_paper.pdf",
            15,
            "READY",
            None,
            datetime.now(UTC),
        )
    )

    response = client.get(f"/documents/{DOCUMENT_ID}", headers={"X-API-Key": settings.API_KEY})

    assert response.status_code == 200

    data = response.json()
    assert data["document_id"] == DOCUMENT_ID
    assert data["filename"] == "test_paper.pdf"
    assert data["chunk_count"] == 15
    assert data["status"] == "READY"
    assert data["error_message"] is None


@patch("backend.app.api.documents.db_manager.get_connection")
def test_get_document_status_not_found(mock_get_connection, client):
    """Ensure polling an unknown document returns 404."""
    mock_get_connection.return_value = _fake_db_connection(None)

    response = client.get(f"/documents/{DOCUMENT_ID}", headers={"X-API-Key": settings.API_KEY})

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_get_document_status_invalid_uuid(client):
    """Ensure a non-UUID identifier returns 404 without hitting the database."""
    response = client.get("/documents/not-a-uuid", headers={"X-API-Key": settings.API_KEY})

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."
