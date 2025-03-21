# app/api/endpoints/retrieval.py
"""
API endpoints for vector database retrieval.

This module defines the /retrieval endpoint which:
1. Receives a query text in a request
2. Retrieves semantically similar documents from Pinecone
3. Returns the matching documents with their metadata
"""

from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import RetrievalRequest, RetrievalResponse
from app.core.retrieval import query_vector_store
from app.api.dependencies import verify_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["retrieval"])

@router.post(
    "/",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
    summary="Retrieve relevant documents",
    response_description="Documents matching the query"
)
async def retrieve_documents(request: RetrievalRequest):
    """
    Retrieve documents similar to the query text.
    
    This endpoint:
    1. Takes a query text via JSON request
    2. Converts it to an embedding vector
    3. Searches Pinecone for similar document vectors
    4. Returns the matching documents with metadata
    
    The top_k parameter controls how many results to return.
    
    Returns:
        JSON object containing matched documents with their metadata
    """
    logger.info(f"Received retrieval request for query: {request.query[:50]}...")
    
    matches = query_vector_store(request.query, top_k=request.top_k)
    
    if matches is None:
        logger.error("Retrieval operation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )
    
    logger.info(f"Retrieved {len(matches)} documents")
    return RetrievalResponse(matches=matches)