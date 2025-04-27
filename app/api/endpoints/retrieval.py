# app/api/endpoints/retrieval.py
"""
API endpoints for vector database retrieval.

This module defines the /retrieval endpoint which:
1. Receives a query text in a request
2. Retrieves semantically similar documents from Pinecone
3. Returns the matching documents with their metadata
"""

from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import RetrievalRequest, RetrievalResponse, DocumentMatch
from app.core.retrieval import get_retriever, Retriever
from app.config.settings import settings
from app.api.dependencies import verify_api_key
import logging
from typing import List, Optional, Dict, Any

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
    Retrieve documents similar to the query text using the configured retriever.
    
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

    try:
        retriever: Retriever = get_retriever()
        matches: Optional[List[DocumentMatch]] = await retriever.retrieve(request.query, top_k=request.top_k)

        if matches is None:
            logger.error("Retrieval operation failed (retriever returned None)")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents due to an internal error."
            )

        logger.info(f"Retrieved {len(matches)} documents")
        return RetrievalResponse(matches=matches, query=request.query)

    except Exception as e:
        logger.exception(f"Unexpected error during retrieval endpoint processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )

@router.get("/debug", response_model=Dict[str, Any])
async def debug_rag(query: str = "Test query"):
    """Debug endpoint to test the RAG pipeline components."""
    try:
        retriever: Retriever = get_retriever()
        documents: Optional[List[DocumentMatch]] = await retriever.retrieve(query=query, top_k=settings.RETRIEVAL_TOP_K)

        if not documents:
            logger.warning("No relevant documents found for debug query")
            return {
                "query": query,
                "documents": [],
                "success": False
            }

        return {
            "query": query,
            "documents": documents,
            "success": True
        }

    except Exception as e:
        logger.exception(f"Error during debug endpoint processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during debug processing: {e}"
        )