import pytest
from unittest.mock import AsyncMock, MagicMock, patch

try:
    from app.core.chat_service import generate_rag_response
    from app.models.schemas import DocumentMatch, DocumentMetadata, Message
    from app.config.settings import settings
    from datetime import datetime
except ImportError:
    pytest.skip("Skipping chat service tests: Could not import.", allow_module_level=True)

pytestmark = pytest.mark.asyncio

# --- Fixtures for Mocks (Consider moving common ones to conftest.py) ---

@pytest.fixture
def mock_db_chat_service(mocker):
    """Mock Appwrite DB specifically for chat_service tests."""
    mock = mocker.MagicMock() # Use MagicMock for synchronous parts if any
    # Mock list_documents for history fetching
    mock.list_documents.return_value = {
        'total': 1,
        'documents': [
            {'$id': 'hist1', 'user_id': 'user1', 'content': 'Previous question', 'message_type': 'user', '$createdAt': datetime.now().isoformat()}
        ]
    }
    # Mock create_document for storing messages
    mock.create_document.return_value = {'$id': 'new_msg_id'}
    return mock

@pytest.fixture
def mock_retriever_chat_service(mocker):
    """Mock Retriever specifically for chat_service tests."""
    mock = mocker.AsyncMock()
    # Sample retrieval result
    mock_meta = DocumentMetadata(text="Retrieved context text.", book_id="1", book_name="Book")
    mock_match = DocumentMatch(id="retrieved_doc1", score=0.8, metadata=mock_meta)
    mock.retrieve.return_value = [mock_match]
    return mock

@pytest.fixture
def mock_get_retriever(mocker, mock_retriever_chat_service):
    """Patch the get_retriever factory function."""
    return mocker.patch('app.core.chat_service.get_retriever', return_value=mock_retriever_chat_service)

@pytest.fixture
def mock_format_context(mocker):
    """Mock format_context_and_extract_sources."""
    # Return sample context text and sources list
    return mocker.patch(
        'app.core.chat_service.format_context_and_extract_sources',
        return_value=(
            "Formatted context: Retrieved context text.", # context_text
            [{"document_id": "retrieved_doc1", "content": "Retrieved context text.", "book_id": "1"}] # final_sources
        )
    )

@pytest.fixture
def mock_construct_prompt(mocker):
    """Mock construct_llm_prompt."""
    return mocker.patch('app.core.chat_service.construct_llm_prompt', return_value="Final LLM Prompt")

@pytest.fixture
def mock_generate_llm_response(mocker):
    """Mock generate_llm_response."""
    return mocker.patch('app.core.chat_service.generate_llm_response', return_value="Mocked LLM Answer")

@pytest.fixture
def mock_store_message(mocker):
    """Mock store_message function."""
    # Return the structure expected by generate_rag_response
    return mocker.patch('app.core.chat_service.store_message', side_effect=lambda **kwargs: {'$id': f"{kwargs['message_type']}_msg_id"})


# --- Test generate_rag_response ---

async def test_generate_rag_response_success_flow(
    mock_db_chat_service,
    mock_get_retriever,
    mock_retriever_chat_service,
    mock_format_context,
    mock_construct_prompt,
    mock_generate_llm_response,
    mock_store_message
):
    """Test the successful end-to-end flow of generate_rag_response."""
    query = "What is the context?"
    user_id = "user1"
    conversation_id = "conv1"

    result = await generate_rag_response(
        db=mock_db_chat_service,
        query=query,
        user_id=user_id,
        conversation_id=conversation_id,
        is_anonymous=False
    )

    # Assertions
    mock_db_chat_service.list_documents.assert_called_once() # History fetched
    mock_store_message.assert_any_call( # User message stored
        db=mock_db_chat_service,
        user_id=user_id,
        content=query,
        message_type='user',
        conversation_id=conversation_id,
        is_anonymous=False,
        sources=None
    )
    mock_get_retriever.assert_called_once()
    mock_retriever_chat_service.retrieve.assert_called_once_with(query, top_k=settings.DEFAULT_TOP_K)
    mock_format_context.assert_called_once() # With retrieved docs
    mock_construct_prompt.assert_called_once() # With history, context, query
    mock_generate_llm_response.assert_called_once_with("Final LLM Prompt")
    mock_store_message.assert_any_call( # AI message stored
        db=mock_db_chat_service,
        user_id=settings.AI_USER_ID, # Check AI user ID
        content="Mocked LLM Answer",
        message_type='ai',
        conversation_id=conversation_id,
        is_anonymous=False,
        sources=[{"document_id": "retrieved_doc1", "content": "Retrieved context text.", "book_id": "1"}] # Check sources passed
    )

    # Check final result structure
    assert result["ai_response"] == "Mocked LLM Answer"
    assert result["conversation_id"] == conversation_id
    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_id"] == "retrieved_doc1"
    assert result["message_id"] == "ai_msg_id" # From mock_store_message

async def test_generate_rag_response_no_docs_retrieved(
    mock_db_chat_service,
    mock_get_retriever,
    mock_retriever_chat_service,
    mock_format_context,
    mock_generate_llm_response,
    mock_store_message,
    caplog
):
    """Test flow when retriever returns no documents."""
    mock_retriever_chat_service.retrieve.return_value = [] # Override mock
    mock_format_context.return_value = ("No relevant context found.", []) # Simulate formatter output

    query = "Obscure query"
    user_id = "user2"
    conversation_id = "conv2"

    result = await generate_rag_response(
        db=mock_db_chat_service,
        query=query,
        user_id=user_id,
        conversation_id=conversation_id,
        is_anonymous=False
    )

    mock_retriever_chat_service.retrieve.assert_called_once()
    mock_format_context.assert_called_once_with([]) # Called with empty list
    assert "No documents retrieved for query" in caplog.text # Check warning log
    mock_generate_llm_response.assert_called_once() # LLM still called, but with no context prompt
    mock_store_message.assert_any_call(message_type='ai', sources=[]) # AI message stored with empty sources

    assert "No relevant context found" in result["ai_response"] # Check response reflects lack of context
    assert result["sources"] == []

# Add tests for:
# - Retrieval error
# - LLM generation error
# - History fetching error
# - Anonymous user flow