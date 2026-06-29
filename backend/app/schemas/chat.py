from pydantic import BaseModel, Field
from typing import List

class QueryRequest(BaseModel):
    """The incoming payload from the user."""
    query: str = Field(..., description="The question to ask the RAG system", min_length=2)

class Citation(BaseModel):
    """Represents a specific chunk of text used to generate the answer."""
    document_id: str = Field(..., description="UUID of the source document")
    filename: str = Field(..., description="Original filename")
    text: str = Field(..., description="The actual text chunk retrieved")
    score: float = Field(..., description="Mathematical similarity score")

class QueryResponse(BaseModel):
    """The outgoing payload containing the answer and verifiable citations."""
    answer: str = Field(..., description="The LLM-generated response")
    sources: List[Citation] = Field(default_factory=list, description="List of documents used for context")
    execution_time_ms: int = Field(..., description="Total time taken to retrieve and generate")