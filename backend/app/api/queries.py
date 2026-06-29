import time
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.chat import QueryRequest, QueryResponse, Citation
from backend.app.rag.retrieval import retrieval_service
from backend.app.core.logging import logger

router = APIRouter(tags=["Query & Retrieval"])

@router.post(
    "/query", 
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK
)
async def execute_query(request: QueryRequest):
    start_time = time.time()
    
    try:
        # Handoff to the RAG Engine
        result = retrieval_service.query(request.query)
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Map raw dictionary sources to strict Pydantic Citation models
        citations = [
            Citation(
                document_id=source["document_id"],
                filename=source["filename"],
                text=source["text"],
                score=source["score"]
            )
            for source in result.get("sources", [])
        ]
        
        return QueryResponse(
            answer=result["answer"],
            sources=citations,
            execution_time_ms=execution_time_ms
        )
        
    except ValueError as e:
        logger.warning("RAG query rejected", extra={"error": str(e), "query": request.query})
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Unexpected RAG failure", extra={"error": str(e), "query": request.query})
        raise HTTPException(status_code=500, detail="Failed to process query against the document database.")