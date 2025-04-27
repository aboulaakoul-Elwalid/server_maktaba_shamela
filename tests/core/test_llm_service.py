import pytest
from unittest.mock import AsyncMock, MagicMock

# Import the functions/classes to test
try:
    from app.core.llm_service import generate_llm_response # Assuming this is the main entry point now
    # Import specific functions if testing them directly:
    # from app.core.llm_service import call_mistral_with_retry, call_gemini_api
    from app.core.clients import mistral_client # Need to mock this
    # Import Gemini client if used directly
except ImportError:
    pytest.skip("Skipping LLM service tests: Could not import.", allow_module_level=True)

pytestmark = pytest.mark.asyncio

# --- Mock LLM Clients ---
# You might move these to conftest.py if used across many tests

@pytest.fixture
def mock_mistral_client(mocker):
    """Mocks the global mistral_client instance."""
    mock_client = AsyncMock() # Use AsyncMock for async methods like chat

    # Configure the mock chat response
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Mocked Mistral Response"
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.return_value = mock_response

    # Patch the actual client instance used in llm_service.py
    mocker.patch('app.core.llm_service.mistral_client', mock_client)
    return mock_client

# Add mock for Gemini client if needed
# @pytest.fixture
# def mock_gemini_client(mocker):
#     mock_genai = mocker.patch('app.core.llm_service.genai') # Mock the genai module
#     mock_model = AsyncMock()
#     mock_model.generate_content_async.return_value.text = "Mocked Gemini Response"
#     mock_genai.GenerativeModel.return_value = mock_model
#     return mock_model


# --- Tests for generate_llm_response ---

async def test_generate_llm_response_mistral_success(mock_mistral_client):
    """Test successful response generation using Mistral."""
    prompt = "Test prompt for Mistral"
    response = await generate_llm_response(prompt)

    assert response == "Mocked Mistral Response"
    mock_mistral_client.chat.assert_called_once()
    call_args = mock_mistral_client.chat.call_args
    # Check model name, messages structure, temp, max_tokens if needed
    assert call_args.kwargs['model'] == 'mistral-sabaa' # Or your configured model
    assert call_args.kwargs['messages'][-1]['role'] == 'user'
    assert call_args.kwargs['messages'][-1]['content'] == prompt

async def test_generate_llm_response_mistral_error(mock_mistral_client, caplog):
    """Test error handling when Mistral client fails."""
    mock_mistral_client.chat.side_effect = Exception("Mistral API Error")

    prompt = "Test prompt causing error"
    response = await generate_llm_response(prompt)

    assert "I apologize, but I encountered an error" in response
    assert "Mistral API Error" in response
    assert "Error generating LLM response: Mistral API Error" in caplog.text

async def test_generate_llm_response_client_not_initialized(mocker, caplog):
    """Test behavior when the LLM client is None."""
    # Patch the client to be None for this test
    mocker.patch('app.core.llm_service.mistral_client', None)

    prompt = "Test prompt"
    response = await generate_llm_response(prompt)

    assert response == "Error: LLM service is unavailable"
    assert "Mistral client not initialized" in caplog.text


# Add tests for Gemini if generate_llm_response uses it
# async def test_generate_llm_response_gemini_success(mock_gemini_client): ...
# async def test_generate_llm_response_gemini_error(mock_gemini_client, caplog): ...

# Add tests for retry logic if implemented in specific call_... functions