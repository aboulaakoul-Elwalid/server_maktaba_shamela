import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import MagicMock
from appwrite.services.account import Account
from appwrite.services.users import Users
from app.main import app  # Import app for dependency overrides
from app.core.clients import get_admin_account_service, get_admin_users_service

# Add the project root to the Python path to allow imports from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import the FastAPI app instance
try:
    from app.main import app
    from app.models.schemas import DocumentMatch, DocumentMetadata
except ImportError as e:
    print(f"Error importing FastAPI app or other modules from app: {e}")
    print("Ensure your FastAPI instance is named 'app' in app/main.py")
    raise

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Provides a FastAPI TestClient instance for API testing.
    Scope is 'session' to create the client only once per test session.
    """
    # Use a context manager to ensure startup/shutdown events are handled
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def sample_document_match():
    """ Provides a sample DocumentMatch object for testing. """
    return DocumentMatch(
        id="test_doc_1",
        score=0.9,
        metadata=DocumentMetadata(
            text="This is sample text content for testing purposes.",
            book_name="Sample Book",
            section_title="Sample Section",
            book_id="123",
            author_name="Test Author",
            category_name="Test Category"
        )
    )

@pytest.fixture(scope="session")  # Scope session: log in only once per test run
def authenticated_user_token(client: TestClient) -> str:
    """
    Logs in a test user and returns the access token.
    Uses mocks for Appwrite services.
    """
    print("\n--- Fixture: Logging in test user ---")
    # Create mocks for Appwrite services needed for login
    mock_account = MagicMock(spec=Account)
    mock_users = MagicMock(spec=Users)

    # Configure mocks for successful login
    mock_account.create_email_password_session.return_value = {'userId': 'e2e_test_user_id'}
    mock_users.create_jwt.return_value = {'jwt': 'mocked_e2e_jwt_token'}

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    # Override dependencies specifically for this fixture's login call
    app.dependency_overrides[get_admin_account_service] = lambda: mock_account
    app.dependency_overrides[get_admin_users_service] = lambda: mock_users

    # Perform the login request
    login_data = {"email": "e2e_test@example.com", "password": "e2e_password"}
    response = client.post("/auth/login", json=login_data)

    # Restore original overrides immediately after use
    app.dependency_overrides = original_overrides

    # Check response and return token
    if response.status_code != 200:
        pytest.fail(f"Failed to authenticate test user for E2E tests. Status: {response.status_code}, Body: {response.text}")

    token = response.json().get("access_token")
    if not token:
         pytest.fail("Failed to get access_token from login response in fixture.")

    print(f"--- Fixture: Obtained token: {token[:5]}... ---")
    return token

# Add other common fixtures below as needed
