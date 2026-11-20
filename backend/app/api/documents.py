import base64
import binascii
import json
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import verify_api_key
from backend.app.db.connection import db_manager
from backend.app.rag.ingestion import ingestion_service
from backend.app.schemas.document import (
    DocumentStatusResponse,
    DocumentUploadResponse,
    PubSubPushEnvelope,
)
from backend.app.services.storage_queue import storage_queue

router = APIRouter(tags=["Document Management"])


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)

        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")

        result = ingestion_service.stage_document(pdf_bytes=file_bytes, filename=file.filename)

        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            chunk_count=result["chunk_count"],
            status=result["status"],
        )

    except ValueError as e:
        logger.warning("Document ingestion validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Unexpected ingestion failure", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to process document.")


_REQUIRED_EVENT_KEYS = {"document_id", "filename", "file_hash", "gcs_uri"}


@router.post(
    "/documents/worker",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def process_document_worker(
    envelope: PubSubPushEnvelope,
    authorization: str | None = Header(default=None),
):
    try:
        storage_queue.verify_worker_token(authorization)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not envelope.message.data:
        raise HTTPException(status_code=400, detail="Empty Pub/Sub message data.")

    try:
        raw_json = base64.b64decode(envelope.message.data).decode("utf-8")
        event_payload = json.loads(raw_json)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.error("Invalid Pub/Sub envelope payload", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail="Malformed Pub/Sub message payload.")

    if not isinstance(event_payload, dict) or not _REQUIRED_EVENT_KEYS.issubset(event_payload):
        logger.error(
            "Pub/Sub payload missing required keys",
            extra={
                "received_keys": list(event_payload) if isinstance(event_payload, dict) else None
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Pub/Sub payload must include document_id, filename, file_hash, and gcs_uri.",
        )

    try:
        result = ingestion_service.process_document_event(event_payload)
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            chunk_count=result["chunk_count"],
            status=result["status"],
        )
    except Exception as e:
        logger.error("Worker document processing failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to process document event: {e}")


@router.get(
    "/documents/{document_id}",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def get_document_status(document_id: str):
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, chunk_count, status, error_message, created_at
                    FROM documents
                    WHERE id = %s;
                    """,
                    (document_id,),
                )
                doc = cur.fetchone()
                if not doc:
                    raise HTTPException(status_code=404, detail="Document not found.")

                return DocumentStatusResponse(
                    document_id=str(doc[0]),
                    filename=doc[1],
                    chunk_count=doc[2],
                    status=doc[3],
                    error_message=doc[4],
                    created_at=doc[5],
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document status retrieval failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve document status.")
