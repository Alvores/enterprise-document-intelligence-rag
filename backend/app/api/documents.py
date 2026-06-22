from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.app.schemas.document import DocumentUploadResponse
from backend.app.rag.ingestion import ingestion_service
from backend.app.core.config import settings
from backend.app.core.logging import logger

router = APIRouter(tags=["Document Management"])

@router.post(
    "/documents/upload", 
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")
            
        # Handoff to the AI Service
        result = ingestion_service.ingest_document(pdf_bytes=file_bytes, filename=file.filename)
        
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            chunk_count=result["chunk_count"],
            status=result["status"]
        )
        
    except ValueError as e:
        logger.warning("Document ingestion validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Unexpected ingestion failure", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to process document.")