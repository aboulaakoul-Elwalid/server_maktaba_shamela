import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import MagicMock, patch
from appwrite.services.account import Account
from appwrite.services.users import Users
from app.main import app
from app.core.clients import get_admin_account_service, get_admin_users_service
from app.api import auth_utils

# Add the project root to the Python path to allow imports from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import schemas
try:
    from app.models.schemas import DocumentMatch, DocumentMetadata
except ImportError as e:
    print(f"Error importing FastAPI app or other modules from app: {e}")
    raise

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Provides a FastAPI TestClient instance for API testing.
    Scope is 'session' to create the client only once per test session.
    """
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

@pytest.fixture(scope="session")
def authenticated_user_token(client: TestClient, request) -> str:
    """
    Logs in a test user (using mocks), returns the access token, AND
    patches the token validation utility for the session using start/stop.
    """
    print("\n--- Fixture: Logging in test user AND Patching Validation ---")
    mock_user_id = "mock_conftest_user_id"
    mock_token = "mocked_conftest_jwt_token"

    # --- Mock Login Services ---
    mock_account = MagicMock(spec=Account)
    mock_users = MagicMock(spec=Users)
    mock_account.create_email_password_session.return_value = {'userId': mock_user_id}
    mock_users.create_jwt.return_value = {'jwt': mock_token}

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_admin_account_service] = lambda: mock_account
    app.dependency_overrides[get_admin_users_service] = lambda: mock_users

    login_data = {"email": "conftest_test@example.com", "password": "conftest_password"}
    response = client.post("/auth/login", json=login_data)
    app.dependency_overrides = original_overrides # Restore overrides for login part

    if response.status_code != 200:
        pytest.fail(f"Failed to authenticate test user. Status: {response.status_code}, Body: {response.text}")
    token = response.json().get("access_token")
    if not token or token != mock_token:
         pytest.fail(f"Failed to get expected mock token '{mock_token}'. Got: {token}")

    # --- Patch Validation Utility using start/stop ---
    validation_util_path = 'app.api.auth_utils.validate_appwrite_token'
    patcher = None # Initialize patcher
    try:
        # Create the patcher
        patcher = patch(validation_util_path, return_value={'userId': mock_user_id})
        # Start the patch
        mocked_validation = patcher.start()
        print(f"--- Fixture: Validation patched ('{validation_util_path}' -> {mock_user_id}). Started. ---")

        # Register a finalizer to stop the patch when the session ends
        request.addfinalizer(patcher.stop)
        print(f"--- Fixture: Registered finalizer to stop patch. Yielding token: {token[:5]}... ---")

    except AttributeError:
        if patcher: patcher.stop() # Attempt cleanup if start failed partially
        pytest.fail(f"Failed to patch validation util. Check if '{validation_util_path}' is correct.")
    except Exception as e:
        if patcher: patcher.stop() # Attempt cleanup
        pytest.fail(f"Error during patching setup in conftest: {e}")

    # Yield the token - the patch is now active and will be stopped by the finalizer
    yield token

# Add other common fixtures below as needed
