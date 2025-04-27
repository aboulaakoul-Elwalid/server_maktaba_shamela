import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

# Use the client fixture from conftest.py

# --- Fixtures for Mocking Service Layer ---

@pytest.fixture
def mock_generate_rag_response_api(mocker):
    """Mocks the generate_rag_response service function."""
    mock_func = AsyncMock(return_value={
        "ai_response": "Mocked RAG answer",
        "sources": [{"document_id": "doc1", "content": "Snippet"}],
        "conversation_id": "conv123",
        "message_id": "ai_msg_456",
        "success": True
    })
    # Patch the function where it's imported in the endpoint file
    mocker.patch('app.api.endpoints.chat.generate_rag_response', mock_func)
    return mock_func

@pytest.fixture
def mock_generate_streaming_response_api(mocker):
    """Mocks the generate_streaming_response service function."""
    async def mock_streamer(*args, **kwargs):
        yield "event: chunk\ndata: {\"token\": \"Streamed \"}\n\n"
        yield "event: chunk\ndata: {\"token\": \"response\"}\n\n"
        yield "event: sources\ndata: []\n\n" # Empty sources for simplicity
        yield "event: message_id\ndata: {\"message_id\": \"stream_ai_id\"}\n\n"

    mock_func = MagicMock(return_value=mock_streamer()) # Return the generator
    mocker.patch('app.api.endpoints.chat.generate_streaming_response', mock_func)
    return mock_func


@pytest.fixture
def mock_get_user_conversations_api(mocker):
    """Mocks the get_user_conversations service function."""
    mock_func = AsyncMock(return_value=[
        {"conversation_id": "conv1", "last_message_snippet": "Hi", "timestamp": "2025-04-27T10:00:00Z"},
        {"conversation_id": "conv2", "last_message_snippet": "Hello", "timestamp": "2025-04-27T09:00:00Z"},
    ])
    mocker.patch('app.api.endpoints.chat.get_user_conversations', mock_func)
    return mock_func

@pytest.fixture
def mock_db_dependency(mocker):
    """Mocks the database dependency for endpoints."""
    mock = MagicMock()
    # Patch the specific dependency function used in the endpoint signature
    # Adjust path if your dependency function is named differently or located elsewhere
    mocker.patch('app.api.dependencies.get_admin_db_service', return_value=mock)
    return mock

# --- Test /chat/messages Endpoint ---

def test_send_message_success(client: TestClient, mock_db_dependency, mock_generate_rag_response_api):
    """Test successful message sending (non-streaming)."""
    payload = {"content": "Test query", "conversation_id": "conv123"}
    # Assuming API key verification is handled by other tests or fixtures
    headers = {"X-API-Key": "test-key"} # Add a dummy key if needed by endpoint

    response = client.post("/chat/messages", json=payload, headers=headers)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["ai_response"] == "Mocked RAG answer"
    assert json_response["conversation_id"] == "conv123"
    assert len(json_response["sources"]) == 1
    assert json_response["message_id"] == "ai_msg_456"

    # Check if the service function was called correctly
    mock_generate_rag_response_api.assert_called_once()
    call_args = mock_generate_rag_response_api.call_args
    assert call_args.kwargs['query'] == "Test query"
    assert call_args.kwargs['conversation_id'] == "conv123"
    # Assert db dependency was passed if type-hinted in service func

def test_send_message_validation_error(client: TestClient, headers={"X-API-Key": "test-key"}):
    """Test sending message with invalid payload (missing content)."""
    payload = {"conversation_id": "conv123"} # Missing 'content'
    response = client.post("/chat/messages", json=payload, headers=headers)
    assert response.status_code == 422 # Unprocessable Entity

# --- Test /chat/stream Endpoint ---

def test_stream_message_success(client: TestClient, mock_db_dependency, mock_generate_streaming_response_api):
    """Test successful message streaming."""
    payload = {"content": "Stream query", "conversation_id": "conv_stream"}
    headers = {"X-API-Key": "test-key"}

    response = client.post("/chat/stream", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Check the streamed content (collect it)
    streamed_data = response.text.split('\n\n') # Split by SSE message separator
    # Filter out empty strings resulting from trailing separators
    streamed_data = [item for item in streamed_data if item]

    assert len(streamed_data) == 4 # Based on mock_generate_streaming_response_api
    assert streamed_data[0].startswith("event: chunk\ndata:")
    assert streamed_data[1].startswith("event: chunk\ndata:")
    assert streamed_data[2].startswith("event: sources\ndata:")
    assert streamed_data[3].startswith("event: message_id\ndata:")

    # Check if the service function was called
    mock_generate_streaming_response_api.assert_called_once()
    call_args = mock_generate_streaming_response_api.call_args
    assert call_args.kwargs['query'] == "Stream query"
    assert call_args.kwargs['conversation_id'] == "conv_stream"

# --- Test /chat/conversations Endpoint ---

def test_get_conversations_success(client: TestClient, mock_db_dependency, mock_get_user_conversations_api):
    """Test fetching user conversations."""
    headers = {"X-API-Key": "test-key"}
    # Assuming user ID is derived from API key or JWT (mock that dependency if needed)
    user_id = "user_from_key" # Placeholder

    # Mock the dependency that provides user_id if it's separate
    # mocker.patch('app.api.endpoints.chat.get_current_user_id', return_value=user_id)

    response = client.get("/chat/conversations", headers=headers)

    assert response.status_code == 200
    json_response = response.json()
    assert isinstance(json_response, list)
    assert len(json_response) == 2 # Based on mock
    assert json_response[0]["conversation_id"] == "conv1"
    assert json_response[1]["conversation_id"] == "conv2"

    # Check if service was called (assuming user_id is passed)
    # mock_get_user_conversations_api.assert_called_once_with(db=mock_db_dependency, user_id=user_id)


# Add tests for:
# - Missing API Key / Auth errors for all endpoints
# - Rate limiting errors (if rate limiter dependency is applied)
# - Errors raised by the service layer (e.g., generate_rag_response raises HTTPException)