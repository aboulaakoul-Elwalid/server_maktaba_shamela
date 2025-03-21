# app/api/endpoints/ingestion.py
"""
API endpoints for document ingestion.

This module defines the /ingestion endpoint which:
1. Receives document URLs or text content
2. Processes the documents (fetching if needed)
3. Generates embeddings and stores in Pinecone
4. Returns a confirmation response

This is a placeholder implementation since the ingestion logic would
depend on specific document formats and sources for the Shamela library.
"""

from fastapi import APIRouter, HTTPException, Depends, status
import logging
import hashlib
import time
from typing import Dict, Any, List
import uuid

from app.models.schemas import IngestionRequest, IngestionResponse
from app.core.embeddings import get_text_embedding, get_embeddings_in_chunks
from app.api.dependencies import get_pinecone_client, verify_api_key
from app.core.document_processor import process_document
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

# Add this new endpoint to batch process documents
@router.post(
    "/batch",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
    summary="Ingest multiple documents in the background",
    response_description="Ingestion job status"
)
async def ingest_documents_batch(
    request: List[IngestionRequest],
    background_tasks: BackgroundTasks,
    pinecone_index=Depends(get_pinecone_client)
):
    """
    Ingest multiple documents into the vector database as a background task.
    
    This endpoint accepts a list of document URLs and processes them asynchronously.
    """
    # Generate a batch job ID
    batch_id = str(uuid.uuid4())
    
    # Add the task to background processing
    background_tasks.add_task(
        process_document_batch, 
        request, 
        batch_id, 
        pinecone_index
    )
    
    return IngestionResponse(
        success=True,
        document_id=batch_id,
        message=f"Batch ingestion started with ID: {batch_id}"
    )

# Update the main ingestion endpoint
@router.post(
    "/",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    summary="Ingest a document",
    response_description="Ingestion status"
)
async def ingest_document(
    request: IngestionRequest,
    pinecone_index=Depends(get_pinecone_client)
):
    """
    Ingest a document into the vector database.
    
    This endpoint:
    1. Takes a document URL or text via JSON request
    2. Processes the document (in a real app, would fetch from URL)
    3. Generates embeddings for the document
    4. Stores the document and its metadata in Pinecone
    
    Note: This is a simplified placeholder implementation.
    A complete implementation would handle:
    - Document fetching from URLs
    - Text extraction from various formats
    - Chunking long documents
    - More sophisticated metadata extraction
    
    Returns:
        JSON object with ingestion status
    """
    logger.info(f"Processing document from: {request.document_url}")
    
    try:
        # Process the document
        chunks, metadata = process_document(str(request.document_url))
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not process document - invalid content or format"
            )
        
        # Combine user-provided metadata with extracted metadata
        if request.metadata:
            for chunk in chunks:
                chunk["metadata"].update(request.metadata)
        
        # Generate embeddings for all chunks
        texts = [chunk["text"] for chunk in chunks]
        embeddings = get_embeddings_in_chunks(texts)
        
        if not embeddings or None in embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embeddings for one or more chunks"
            )
        
        # Prepare vectors for Pinecone
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is None:
                logger.warning(f"Skipping chunk {i} due to missing embedding")
                continue
                
            vectors.append({
                "id": chunk["id"],
                "values": embedding,
                "metadata": chunk["metadata"]
            })
        
        # Batch upsert to Pinecone (in chunks of 100 for performance)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            pinecone_index.upsert(vectors=batch)
        
        logger.info(f"Successfully ingested document with {len(vectors)} chunks")
        
        return IngestionResponse(
            success=True,
            document_id=chunks[0]["id"].split("_")[0],  # Base document ID
            message=f"Document successfully ingested with {len(vectors)} chunks"
        )
        
    except Exception as e:
        logger.error(f"Failed to ingest document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )