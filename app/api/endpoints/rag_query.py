# app/api/endpoints/rag_query.py (new file)
"""
API endpoints for RAG queries combining retrieval and generation.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models.schemas import RetrievalRequest
from app.core.rag import generate_rag_response
from app.api.dependencies import verify_api_key

logger = logging.getLogger(__name__)

# Create router for RAG endpoints
router = APIRouter(tags=["rag"])

class RagQueryRequest(BaseModel):
    """Request model for the /rag/query endpoint."""
    query: str = Field(..., description="User's question", min_length=1)
    top_k: int = Field(default=5, description="Number of documents to retrieve", ge=1, le=20)
    reranking: bool = Field(default=True, description="Whether to rerank results")

class RagResponse(BaseModel):
    """Response model for RAG queries."""
    response: str = Field(..., description="Generated answer")
    success: bool = Field(..., description="Whether the query was successful")
    context: List[Dict[str, Any]] = Field(..., description="Retrieved document contexts")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

@router.post(
    "/query",
    response_model=RagResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
    summary="Answer a question using RAG",
    response_description="Generated answer with context"
)
async def rag_query(request: RagQueryRequest):
    """
    Answer a question using Retrieval-Augmented Generation.
    
    This endpoint:
    1. Takes a query text via JSON request
    2. Retrieves relevant documents from the Shamela library
    3. Generates an answer based on the retrieved documents
    4. Returns both the answer and the supporting context
    """
    logger.info(f"Received RAG query: {request.query[:50]}...")
    
    try:
        # Use the RAG pipeline to generate a response
        result = await generate_rag_response(
            query=request.query,
            top_k=request.top_k,
            reranking=request.reranking
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing RAG query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}"
        )