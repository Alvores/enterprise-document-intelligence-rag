from datetime import datetime

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response returned when a document is accepted for ingestion."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    chunk_count: int = Field(..., description="Number of chunks created")
    status: str = Field(..., description="Status of the ingestion")
    uploaded_at: datetime = Field(default_factory=datetime.now)


class PubSubMessage(BaseModel):
    """Inner message object within a Google Cloud Pub/Sub push request."""

    data: str = Field(..., description="Base64-encoded JSON event payload")
    messageId: str | None = None
    publishTime: str | None = None
    attributes: dict[str, str] | None = None


class PubSubPushEnvelope(BaseModel):
    """Incoming webhook envelope from a Google Cloud Pub/Sub push subscription."""

    message: PubSubMessage = Field(..., description="Pub/Sub push message wrapper")
    subscription: str | None = None


class DocumentStatusResponse(BaseModel):
    """Response returned when polling a document's ingestion status."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    chunk_count: int = Field(..., description="Number of chunks created")
    status: str = Field(..., description="Current ingestion status (PENDING, READY, FAILED)")
    error_message: str | None = None
    created_at: datetime
