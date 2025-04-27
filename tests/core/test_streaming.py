import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

try:
    from app.core.streaming import generate_streaming_response
    from app.models.schemas import DocumentMatch, DocumentMetadata
    from app.config.settings import settings
    from datetime import datetime
except ImportError:
    pytest.skip("Skipping streaming tests: Could not import.", allow_module_level=True)

pytestmark = pytest.mark.asyncio

# --- Use similar fixtures as test_chat_service.py ---
# (You might refactor common fixtures into conftest.py)

@pytest.fixture
def mock_db_streaming(mocker):
    mock = mocker.MagicMock()
    mock.list_documents.return_value = {'total': 0, 'documents': []} # No history for simplicity
    mock.create_document.return_value = {'$id': 'new_msg_id'}
    return mock

@pytest.fixture
def mock_retriever_streaming(mocker):
    mock = mocker.AsyncMock()
    mock_meta = DocumentMetadata(text="Streaming context.", book_id="s1")
    mock_match = DocumentMatch(id="stream_doc1", score=0.7, metadata=mock_meta)
    mock.retrieve.return_value = [mock_match]
    return mock

@pytest.fixture
def mock_get_retriever_streaming(mocker, mock_retriever_streaming):
    return mocker.patch('app.core.streaming.get_retriever', return_value=mock_retriever_streaming)

@pytest.fixture
def mock_format_context_streaming(mocker):
    return mocker.patch(
        'app.core.streaming.format_context_and_extract_sources',
        return_value=(
            "Formatted streaming context.",
            [{"document_id": "stream_doc1", "content": "Streaming context.", "book_id": "s1"}]
        )
    )

@pytest.fixture
def mock_construct_prompt_streaming(mocker):
    return mocker.patch('app.core.streaming.construct_llm_prompt', return_value="Final Streaming Prompt")

@pytest.fixture
def mock_stream_llm_response(mocker):
    """Mock the LLM streaming call used within generate_streaming_response."""
    async def mock_streamer(*args, **kwargs):
        yield "event: chunk\ndata: {\"token\": \"Hello \"}\n\n"
        yield "event: chunk\ndata: {\"token\": \"World\"}\n\n"
        # Simulate final source info event
        yield f"event: sources\ndata: {json.dumps([{'document_id': 'stream_doc1'}])}\n\n"
        # Simulate final message ID event
        yield "event: message_id\ndata: {\"message_id\": \"ai_stream_msg_id\"}\n\n"

    # Patch the specific streaming function called inside generate_streaming_response
    # Adjust the path 'app.core.streaming.call_llm_stream' if it's different
    return mocker.patch('app.core.streaming.call_llm_stream', return_value=mock_streamer())

@pytest.fixture
def mock_store_message_streaming(mocker):
    """Mock store_message for streaming (might only be called at the end)."""
    # This mock might need adjustment based on *when* store_message is called in streaming
    return mocker.patch('app.core.streaming.store_message', return_value={'$id': 'ai_stream_msg_id'})


# --- Test generate_streaming_response ---

async def test_generate_streaming_response_success(
    mock_db_streaming,
    mock_get_retriever_streaming,
    mock_retriever_streaming,
    mock_format_context_streaming,
    mock_construct_prompt_streaming,
    mock_stream_llm_response, # Use the streaming mock
    mock_store_message_streaming
):
    """Test the successful streaming flow."""
    query = "Stream test"
    user_id = "user_stream"
    conversation_id = "conv_stream"

    # Collect streamed chunks
    streamed_content = []
    async for chunk in generate_streaming_response(
        db=mock_db_streaming,
        query=query,
        user_id=user_id,
        conversation_id=conversation_id,
        is_anonymous=False
    ):
        streamed_content.append(chunk)

    # Assertions
    mock_db_streaming.list_documents.assert_called_once() # History
    mock_store_message_streaming.assert_any_call(message_type='user') # User message stored
    mock_get_retriever_streaming.assert_called_once()
    mock_retriever_streaming.retrieve.assert_called_once()
    mock_format_context_streaming.assert_called_once()
    mock_construct_prompt_streaming.assert_called_once()
    # mock_stream_llm_response was implicitly called by iterating the generator

    # Check streamed output (based on mock_stream_llm_response)
    assert len(streamed_content) == 4
    assert streamed_content[0] == "event: chunk\ndata: {\"token\": \"Hello \"}\n\n"
    assert streamed_content[1] == "event: chunk\ndata: {\"token\": \"World\"}\n\n"
    assert streamed_content[2].startswith("event: sources\ndata:")
    assert streamed_content[3].startswith("event: message_id\ndata:")

    # Check if final AI message was stored (depends on implementation)
    # mock_store_message_streaming.assert_any_call(message_type='ai', content="Hello World", ...) # Check combined content if stored at end

# Add tests for:
# - No docs retrieved in streaming
# - Errors during streaming