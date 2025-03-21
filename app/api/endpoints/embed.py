# app/api/endpoints/embed.py
"""
API endpoints for text embedding generation.

This module defines the /embed endpoint which:
1. Receives text in a request
2. Generates vector embeddings using Mistral
3. Returns the embeddings in the response

The endpoint is defined using FastAPI's Router, allowing:
- Modular API organization
- Separate versioning
- Independent testing
"""

from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import EmbedRequest, EmbedResponse
from app.core.embeddings import get_text_embedding
from app.api.dependencies import verify_api_key
import logging

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a router instance
# tags parameter groups related endpoints in the OpenAPI documentation
router = APIRouter(tags=["embeddings"])

@router.post(
    "/",
    response_model=EmbedResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],  # Optional API key verification
    summary="Generate text embeddings",
    response_description="Vector embedding for the input text"
)
async def embed_text(request: EmbedRequest):
    """
    Generate a vector embedding for the provided text.
    
    This endpoint:
    1. Takes a text input via JSON request
    2. Sends it to Mistral's embedding API
    3. Returns the resulting embedding vector
    
    The embedding can be used for:
    - Storing documents in vector databases
    - Computing semantic similarity between texts
    - Input to machine learning models
    
    Returns:
        JSON object containing the embedding vector
    """
    logger.info(f"Received embedding request for text: {request.text[:50]}...")
    
    embedding = get_text_embedding(request.text)
    
    if embedding is None:
        logger.error("Embedding generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding"
        )
        
    logger.info("Embedding generated successfully")
    return EmbedResponse(embedding=embedding)