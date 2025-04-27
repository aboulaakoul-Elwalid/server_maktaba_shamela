# app/models/schemas.py
from pydantic import BaseModel, Field, HttpUrl, model_validator  # Import model_validator
from typing import List, Dict, Any, Optional
import datetime  # Added for timestamp

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


# --- Retrieval Schemas ---

class DocumentMetadata(BaseModel):
    """Metadata associated with a retrieved document chunk."""
    author_name: Optional[str] = Field(None, description="Author of the source book")
    book_name: Optional[str] = Field(None, description="Name of the source book")
    category_name: Optional[str] = Field(None, description="Category of the source book")
    section_title: Optional[str] = Field(None, description="Title of the section within the book")
    text: str = Field(..., description="The actual text content of the document chunk")
    book_id: Optional[str] = Field(None, description="Unique identifier for the book (e.g., for URL generation)")

class DocumentMatch(BaseModel):
    """Represents a single document match from the retriever."""
    id: str = Field(..., description="Unique identifier for the document chunk (e.g., section_id)")
    score: float = Field(..., description="Relevance score from the retrieval system")
    metadata: DocumentMetadata = Field(..., description="Structured metadata for the document")

class RetrievalRequest(BaseModel):
    """Request model for the /retrieval endpoint."""
    query: str = Field(...,
                      description="Query text to search for",
                      min_length=1)
    top_k: int = Field(5, description="Number of documents to retrieve", ge=1, le=50)

class RetrievalResponse(BaseModel):
    """Response model for the /retrieval endpoint."""
    matches: List[DocumentMatch] = Field(..., description="List of retrieved document matches")
    query: str = Field(..., description="The original query text")


# --- Ingestion Schemas ---

class IngestionRequest(BaseModel):
    """Request model for the /ingest endpoint."""
    source_url: Optional[HttpUrl] = Field(None, description="URL of the source document (optional)")
    text_content: Optional[str] = Field(None, description="Raw text content to ingest (optional)")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata to associate with the document")

    @model_validator(mode='before')  # This decorator will now be recognized
    def check_source_or_content(cls, values):
        if not values.get('source_url') and not values.get('text_content'):
            raise ValueError('Either source_url or text_content must be provided')
        return values

class IngestionResponse(BaseModel):
    """Response model for the /ingest endpoint."""
    status: str = Field(..., description="Ingestion status (e.g., 'success', 'failed')")
    message: str = Field(..., description="Details about the ingestion process")
    processed_chunks: Optional[int] = Field(None, description="Number of chunks processed")


# --- Chat Schemas ---

class MessageCreate(BaseModel):
    """Request model for sending a message."""
    content: str = Field(..., min_length=1, description="The content of the user's message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID (optional)")

class Message(BaseModel):
    """Represents a single message in a conversation."""
    message_id: str = Field(..., description="Unique ID of the message")
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")
    user_id: str = Field(..., description="ID of the user who sent the message (or 'ai')")
    content: str = Field(..., description="The text content of the message")
    message_type: str = Field(..., description="Type of message ('user' or 'ai')")
    timestamp: datetime.datetime = Field(..., description="Timestamp when the message was created")
    sources: List[Dict[str, Any]] = Field([], description="List of source documents cited by an AI message")

class ConversationResponse(BaseModel):
    """Response model for listing conversations."""
    id: str = Field(..., description="Unique ID of the conversation")
    title: Optional[str] = Field(None, description="Title of the conversation (optional)")
    created_at: datetime.datetime = Field(..., description="Timestamp when the conversation was created")
    last_updated: datetime.datetime = Field(..., description="Timestamp when the conversation was last updated")