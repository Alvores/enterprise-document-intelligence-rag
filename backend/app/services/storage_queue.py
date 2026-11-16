"""Storage and queue abstraction for asynchronous document ingestion.

Two backends are supported:
- ``gcp``: uploads PDFs to Google Cloud Storage and publishes events to Cloud Pub/Sub.
- ``local``: stages PDFs under a local directory and dispatches events inline so
  Docker Compose and evaluation tests work without GCP credentials.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.app.core.logging import logger

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_URI_PREFIX = "local://"


class StorageQueue:
    """Handles upload/download of PDF bytes and publishing of ingestion events."""

    def __init__(self) -> None:
        configured_backend = settings.STORAGE_BACKEND.strip().lower()
        if configured_backend:
            if configured_backend not in {"local", "gcp"}:
                raise ValueError(
                    f"Unsupported STORAGE_BACKEND={configured_backend!r}; expected \
                        'local' or 'gcp'."
                )
            self.backend = configured_backend
        else:
            # Auto-select GCP mode when cloud bucket & topic are configured
            self.backend = (
                "gcp" if (settings.GCS_BUCKET_NAME and settings.PUBSUB_TOPIC_ID) else "local"
            )

        self._staging_dir = (
            Path(settings.LOCAL_STAGING_DIR).expanduser()
            if settings.LOCAL_STAGING_DIR
            else _REPO_ROOT / "data" / "staging"
        )

        self._storage_client = None
        self._publisher_client = None

    @property
    def is_cloud(self) -> bool:
        """Whether the GCS + Pub/Sub backend is active."""
        return self.backend == "gcp"

    @property
    def storage_client(self):
        """Lazily creates the GCS client so local mode never touches GCP auth."""
        if self._storage_client is None:
            from google.cloud import storage

            self._storage_client = storage.Client(project=settings.GCP_PROJECT_ID or None)
        return self._storage_client

    @property
    def publisher_client(self):
        """Lazily creates the Pub/Sub publisher so local mode never touches GCP auth."""
        if self._publisher_client is None:
            from google.cloud import pubsub_v1

            self._publisher_client = pubsub_v1.PublisherClient()
        return self._publisher_client

    def upload_bytes(self, document_id: str, filename: str, pdf_bytes: bytes) -> str:
        """Stores a PDF and returns its canonical URI (``gs://`` or ``local://``)."""
        safe_filename = Path(filename).name or "document.pdf"

        if self.is_cloud:
            bucket_name = self._require_bucket()
            blob_name = f"{document_id}/{safe_filename}"
            blob = self.storage_client.bucket(bucket_name).blob(blob_name)
            blob.upload_from_string(pdf_bytes, content_type="application/pdf")
            uri = f"gs://{bucket_name}/{blob_name}"
            logger.info(
                "Uploaded PDF to GCS",
                extra={"document_id": document_id, "gcs_uri": uri},
            )
            return uri

        destination = self._staging_dir / document_id / safe_filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(pdf_bytes)
        uri = f"{_LOCAL_URI_PREFIX}{document_id}/{safe_filename}"
        logger.info(
            "Staged PDF locally",
            extra={"document_id": document_id, "path": str(destination)},
        )
        return uri

    def download_bytes(self, uri: str) -> bytes:
        """Reads PDF bytes back from a ``gs://`` or ``local://`` URI."""
        if uri.startswith(_LOCAL_URI_PREFIX):
            if self.is_cloud:
                raise ValueError(f"Local URI is not valid for the gcp backend: {uri}")
            relative = uri.removeprefix(_LOCAL_URI_PREFIX)
            path = (self._staging_dir / relative).resolve()
            staging_root = self._staging_dir.resolve()
            if staging_root not in path.parents:
                raise ValueError(f"Refusing to read outside the staging directory: {uri}")
            return path.read_bytes()

        if not self.is_cloud:
            raise ValueError(f"Only local:// URIs are supported in local mode, got: {uri}")

        if not uri.startswith("gs://"):
            raise ValueError(f"Unsupported storage URI: {uri}")

        bucket_name, _, blob_name = uri.removeprefix("gs://").partition("/")
        if not bucket_name or not blob_name:
            raise ValueError(f"Malformed GCS URI: {uri}")

        return self.storage_client.bucket(bucket_name).blob(blob_name).download_as_bytes()

    def publish_event(
        self,
        payload: dict[str, Any],
        *,
        consumer: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        """Publishes an ingestion event to Pub/Sub, or dispatches it inline in local mode."""
        if not self.is_cloud:
            handler = consumer or self._dispatch_local_event
            handler(payload)
            return

        topic_id = self._require_topic()
        if not settings.GCP_PROJECT_ID:
            raise RuntimeError("GCP_PROJECT_ID must be set when STORAGE_BACKEND=gcp.")

        topic_path = self.publisher_client.topic_path(settings.GCP_PROJECT_ID, topic_id)
        data = json.dumps(payload).encode("utf-8")

        future = self.publisher_client.publish(topic_path, data=data)
        message_id = future.result(timeout=30)
        logger.info(
            "Published ingestion event",
            extra={"message_id": message_id, "topic": topic_id},
        )

    def verify_worker_token(self, authorization_header: str | None) -> None:
        """Validates the Pub/Sub push OIDC Bearer token. No-op in local mode."""
        if not self.is_cloud:
            return

        if not settings.WORKER_OIDC_AUDIENCE:
            raise PermissionError("WORKER_OIDC_AUDIENCE is required to verify Pub/Sub push tokens.")
        if not authorization_header:
            raise PermissionError("Missing Authorization header on Pub/Sub push request.")

        token = authorization_header.removeprefix("Bearer ").removeprefix("bearer ").strip()
        if not token:
            raise PermissionError("Empty Pub/Sub OIDC bearer token.")

        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        try:
            id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=settings.WORKER_OIDC_AUDIENCE,
            )
        except Exception as e:
            logger.warning("Rejected worker OIDC token", extra={"error": str(e)})
            raise PermissionError("Invalid Pub/Sub OIDC token.") from e

    @staticmethod
    def _dispatch_local_event(payload: dict[str, Any]) -> None:
        """Invokes the consumer inline so local uploads complete before returning."""
        from backend.app.rag.ingestion import ingestion_service

        handler = getattr(ingestion_service, "process_document_event", None)
        if handler is None:
            raise RuntimeError(
                "Local dispatch requires IngestionService.process_document_event(payload)."
            )
        handler(payload)

    def _require_bucket(self) -> str:
        if not settings.GCS_BUCKET_NAME:
            raise RuntimeError("GCS_BUCKET_NAME must be set when STORAGE_BACKEND=gcp.")
        return settings.GCS_BUCKET_NAME

    def _require_topic(self) -> str:
        if not settings.PUBSUB_TOPIC_ID:
            raise RuntimeError("PUBSUB_TOPIC_ID must be set when STORAGE_BACKEND=gcp.")
        return settings.PUBSUB_TOPIC_ID


storage_queue = StorageQueue()
