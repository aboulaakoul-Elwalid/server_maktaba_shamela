import pytest
from pydantic import ValidationError

# Import the schemas you want to test
try:
    from app.models.schemas import (
        MessageCreate,
        Message,
        DocumentMetadata,
        DocumentMatch,
        ConversationResponse,
        RetrievalRequest,
        # Add other schemas as needed
    )
    from datetime import datetime
except ImportError:
    pytest.skip("Skipping schema tests: Could not import schemas.", allow_module_level=True)

# --- Message Schemas ---

def test_message_create_valid():
    data = {"content": "Hello", "conversation_id": "conv123"}
    msg = MessageCreate(**data)
    assert msg.content == "Hello"
    assert msg.conversation_id == "conv123"

def test_message_create_missing_content():
    data = {"conversation_id": "conv123"}
    with pytest.raises(ValidationError):
        MessageCreate(**data)

def test_message_valid():
    # Assuming timestamp is handled correctly on creation or default
    now = datetime.now()
    data = {
        "message_id": "msg1",
        "conversation_id": "conv1",
        "user_id": "user1",
        "content": "Test",
        "message_type": "user",
        "timestamp": now,
        "sources": []
    }
    msg = Message(**data)
    assert msg.message_id == "msg1"
    assert msg.message_type == "user"
    assert msg.timestamp == now

# --- Document Schemas ---

def test_document_metadata_valid():
    data = {
        "text": "Sample text",
        "book_name": "Book",
        "section_title": "Section",
        "book_id": "123",
        "author_name": "Author",
        "category_name": "Category"
    }
    meta = DocumentMetadata(**data)
    assert meta.text == "Sample text"
    assert meta.book_id == "123"

def test_document_metadata_missing_text():
    # Text is required
    data = {"book_name": "Book", "book_id": "123"}
    with pytest.raises(ValidationError):
        DocumentMetadata(**data)

def test_document_metadata_optional_fields():
    # Test with only required fields
    data = {"text": "Minimal text"}
    meta = DocumentMetadata(**data)
    assert meta.text == "Minimal text"
    assert meta.book_name is None
    assert meta.book_id is None

def test_document_match_valid(sample_document_match): # Assuming fixture exists
    """Tests if a valid DocumentMatch can be created (using fixture)."""
    assert sample_document_match.id == "test_doc_1"
    assert sample_document_match.score == 0.9
    assert sample_document_match.metadata.text == "This is sample text content for testing purposes."

# --- Other Schemas ---

def test_retrieval_request_valid():
    req = RetrievalRequest(query="test query", top_k=10)
    assert req.query == "test query"
    assert req.top_k == 10

# Add more tests for other schemas (ConversationResponse, etc.)