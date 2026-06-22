from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response after a document is uploaded and processed."""
    
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    chunk_count: int = Field(..., description="Number of chunks created")
    status: str = Field(..., description="Status of the ingestion")
    uploaded_at: datetime = Field(default_factory=datetime.now)