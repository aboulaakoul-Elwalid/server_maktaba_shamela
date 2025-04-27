import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Assuming your auth logic uses settings for users/passwords/secrets
try:
    from app.config.settings import settings
except ImportError:
     pytest.skip("Skipping auth endpoint tests: Could not import settings.", allow_module_level=True)

# Use the client fixture from conftest.py

def test_login_for_access_token_success(client: TestClient, mocker):
    """Test successful login and token generation."""
    # Mock settings if user credentials are stored there
    mock_settings = MagicMock()
    mock_settings.ADMIN_USERNAME = "testadmin"
    mock_settings.ADMIN_PASSWORD = "testpassword"
    mock_settings.SECRET_KEY = "test-secret"
    mock_settings.ALGORITHM = "HS256"
    mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    # Patch the settings object used within the auth endpoint logic
    mocker.patch('app.api.endpoints.auth.settings', mock_settings)
    # Mock the create_access_token function if it's complex, or test its output
    mocker.patch('app.api.endpoints.auth.create_access_token', return_value="mocked_jwt_token")

    login_data = {"username": "testadmin", "password": "testpassword"}
    response = client.post("/auth/token", data=login_data) # Assuming form data

    assert response.status_code == 200
    assert response.json() == {"access_token": "mocked_jwt_token", "token_type": "bearer"}

def test_login_for_access_token_invalid_credentials(client: TestClient, mocker):
    """Test login with invalid credentials."""
    mock_settings = MagicMock()
    mock_settings.ADMIN_USERNAME = "testadmin"
    mock_settings.ADMIN_PASSWORD = "correctpassword"
    mocker.patch('app.api.endpoints.auth.settings', mock_settings)

    login_data = {"username": "testadmin", "password": "wrongpassword"}
    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 401 # Unauthorized
    assert "Incorrect username or password" in response.json().get("detail", "")

def test_login_for_access_token_incorrect_username(client: TestClient, mocker):
    """Test login with incorrect username."""
    mock_settings = MagicMock()
    mock_settings.ADMIN_USERNAME = "correctadmin"
    mock_settings.ADMIN_PASSWORD = "password"
    mocker.patch('app.api.endpoints.auth.settings', mock_settings)

    login_data = {"username": "wrongadmin", "password": "password"}
    response = client.post("/auth/token", data=login_data)

    assert response.status_code == 401
    assert "Incorrect username or password" in response.json().get("detail", "")

# Add tests for token validation endpoint if you have one (e.g., /users/me)