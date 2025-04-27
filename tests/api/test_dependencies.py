import pytest
from fastapi import HTTPException, Header
from unittest.mock import MagicMock
import time

try:
    from app.api.dependencies import verify_api_key, rate_limiter, get_pinecone_client
    from app.config.settings import settings
    # Assuming API_KEYS and rate limit settings are in 'settings'
except ImportError:
     pytest.skip("Skipping dependency tests: Could not import.", allow_module_level=True)

# --- Test verify_api_key ---

def test_verify_api_key_valid(mocker):
    """Test valid API key verification."""
    # Mock settings if API_KEYS is loaded from there
    mock_settings = MagicMock()
    mock_settings.API_KEYS = {"valid-key": {"user": "testuser", "rate_limit": 100}}
    mocker.patch('app.api.dependencies.settings', mock_settings)

    # Simulate the dependency injection
    result = verify_api_key(api_key="valid-key")
    assert result is True

def test_verify_api_key_missing():
    """Test missing API key header."""
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(api_key=None)
    assert exc_info.value.status_code == 401
    assert "API Key required" in exc_info.value.detail

def test_verify_api_key_invalid(mocker):
    """Test invalid API key."""
    mock_settings = MagicMock()
    mock_settings.API_KEYS = {"valid-key": {"user": "testuser"}}
    mocker.patch('app.api.dependencies.settings', mock_settings)

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(api_key="invalid-key")
    assert exc_info.value.status_code == 403
    assert "Invalid API Key" in exc_info.value.detail

# --- Test rate_limiter ---

@pytest.fixture(autouse=True) # Apply to all tests in this module
def clear_rate_limit_store():
    """Clear the in-memory store before/after each test."""
    # Assuming the store is a global dict in dependencies.py
    try:
        from app.api.dependencies import api_key_usage
        api_key_usage.clear()
        yield
        api_key_usage.clear()
    except ImportError:
        yield # Do nothing if store not found

def test_rate_limiter_within_limit(mocker):
    """Test rate limiter when calls are within the limit."""
    mock_settings = MagicMock()
    mock_settings.API_KEYS = {"test-key": {"user": "test", "rate_limit": 5}} # 5 calls per minute
    mocker.patch('app.api.dependencies.settings', mock_settings)

    # Simulate 5 calls within the same minute
    current_time = time.time()
    mocker.patch('time.time', return_value=current_time)
    for _ in range(5):
        assert rate_limiter(api_key="test-key") is True

def test_rate_limiter_exceed_limit(mocker):
    """Test rate limiter when calls exceed the limit."""
    mock_settings = MagicMock()
    mock_settings.API_KEYS = {"test-key": {"user": "test", "rate_limit": 3}} # 3 calls per minute
    mocker.patch('app.api.dependencies.settings', mock_settings)

    current_time = time.time()
    mocker.patch('time.time', return_value=current_time)

    # First 3 calls should pass
    for _ in range(3):
        assert rate_limiter(api_key="test-key") is True

    # 4th call should fail
    with pytest.raises(HTTPException) as exc_info:
        rate_limiter(api_key="test-key")
    assert exc_info.value.status_code == 429 # Too Many Requests
    assert "Rate limit exceeded" in exc_info.value.detail

def test_rate_limiter_new_minute(mocker):
    """Test rate limiter resets in a new minute."""
    mock_settings = MagicMock()
    mock_settings.API_KEYS = {"test-key": {"user": "test", "rate_limit": 2}}
    mocker.patch('app.api.dependencies.settings', mock_settings)

    # Call 1 and 2 in minute 1
    time1 = time.time()
    mocker.patch('time.time', return_value=time1)
    assert rate_limiter(api_key="test-key") is True
    assert rate_limiter(api_key="test-key") is True

    # Call 3 should fail in minute 1
    with pytest.raises(HTTPException):
        rate_limiter(api_key="test-key")

    # Call 4 in minute 2 should pass
    time2 = time1 + 61 # Advance time by more than 60 seconds
    mocker.patch('time.time', return_value=time2)
    assert rate_limiter(api_key="test-key") is True

# --- Test get_pinecone_client ---

def test_get_pinecone_client_success(mocker):
    """Test successful retrieval of pinecone index via dependency."""
    mock_index = MagicMock(name="MockPineconeIndex")
    mocker.patch('app.api.dependencies.get_pinecone_index', return_value=mock_index)

    result = get_pinecone_client()
    assert result is mock_index

def test_get_pinecone_client_failure(mocker):
    """Test failure when getting pinecone index via dependency."""
    mocker.patch('app.api.dependencies.get_pinecone_index', side_effect=Exception("Connection failed"))

    with pytest.raises(HTTPException) as exc_info:
        get_pinecone_client()
    assert exc_info.value.status_code == 503
    assert "Cannot connect to vector database: Connection failed" in exc_info.value.detail