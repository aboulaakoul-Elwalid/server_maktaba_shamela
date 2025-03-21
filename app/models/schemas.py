# app/models/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional

class EmbedRequest(BaseModel):
    """
    Request model for the /embed endpoint.
    
    This Pydantic model:
    1. Validates incoming JSON has the expected structure
    2. Provides clear documentation in OpenAPI/Swagger UI
    3. Handles type conversion automatically
    
    Field attributes provide additional validation and documentation.
    """
    text: str = Field(..., 
                     description="Text to generate embeddings for",
                     min_length=1)

class EmbedResponse(BaseModel):
    """Response model for the /embed endpoint."""
    embedding: List[float] = Field(..., 
                                 description="Vector representation of the input text")

class RetrievalRequest(BaseModel):
    """Request model for the /retrieval endpoint."""
    query: str = Field(..., 
                      description="Query text to search for", 
                      min_length=1)
    top_k: int = Field(default=5, 
                     description="Number of results to return",
                     ge=1, le=100)

class DocumentMetadata(BaseModel):
    """Metadata model for retrieved documents."""
    book_name: str
    section_title: str
    text: str

class DocumentMatch(BaseModel):
    """Model for a single document match."""
    score: float = Field(..., description="Similarity score")
    id: str = Field(..., description="Document ID")
    metadata: DocumentMetadata = Field(..., description="Document metadata")

class RetrievalResponse(BaseModel):
    """Response model for the /retrieval endpoint."""
    matches: List[DocumentMatch] = Field(..., 
                                       description="List of matched documents")

class IngestionRequest(BaseModel):
    """Request model for the /ingestion endpoint."""
    document_url: HttpUrl = Field(..., 
                                description="URL of the document to ingest")
    # Alternative for direct text ingestion
    # text: Optional[str] = Field(None, description="Text content to ingest")
    metadata: Optional[Dict[str, Any]] = Field(default={}, 
                                             description="Additional metadata")

class IngestionResponse(BaseModel):
    """Response model for the /ingestion endpoint."""
    success: bool = Field(..., description="Whether ingestion was successful")
    document_id: Optional[str] = Field(None, description="ID of the ingested document")
    message: str = Field(..., description="Status message")