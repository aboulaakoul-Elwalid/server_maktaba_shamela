import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import MagicMock, patch
from appwrite.services.account import Account
from appwrite.services.users import Users
from app.main import app
from app.core.clients import get_admin_account_service, get_admin_users_service

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
    patches the actual Appwrite account validation method for the session.
    """
    print("\n--- Fixture: Logging in test user AND Patching Validation ---")
    mock_user_id = "mock_conftest_user_id"
    mock_email = "conftest_test@example.com"
    mock_name = "Mock Conftest User"
    mock_token = "mocked_conftest_jwt_token" # This is the token we return

    # --- Mock Login Services (for /auth/login endpoint) ---
    mock_login_account = MagicMock(spec=Account)
    mock_login_users = MagicMock(spec=Users)
    # Simulate successful session creation for login
    mock_login_account.create_email_password_session.return_value = {'userId': mock_user_id}
    # Simulate successful JWT creation for login
    mock_login_users.create_jwt.return_value = {'jwt': mock_token}

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_admin_account_service] = lambda: mock_login_account
    app.dependency_overrides[get_admin_users_service] = lambda: mock_login_users

    login_data = {"email": mock_email, "password": "conftest_password"}
    response = client.post("/auth/login", json=login_data)
    app.dependency_overrides = original_overrides # Restore overrides after login call

    if response.status_code != 200:
        pytest.fail(f"Failed to authenticate test user via /auth/login. Status: {response.status_code}, Body: {response.text}")
    token = response.json().get("access_token")
    if not token or token != mock_token:
         pytest.fail(f"Failed to get expected mock token '{mock_token}' from login response. Got: {token}")

    # --- Patch Actual Validation Method (Account.get) ---
    # The target is the 'get' method within the 'Account' class from the appwrite SDK
    validation_patch_target = 'appwrite.services.account.Account.get' # <-- CORRECTED TARGET

    # Define the mock user data that Account.get should return when patched
    mock_appwrite_user_data = {
        '$id': mock_user_id,
        'email': mock_email,
        'name': mock_name,
        '$registration': '2025-01-01T10:00:00.000+00:00', # Example timestamp
        'prefs': {}
        # Add any other fields your get_current_user expects from user_data
    }

    patcher = None
    try:
        # Create the patcher for Account.get
        patcher = patch(validation_patch_target, return_value=mock_appwrite_user_data)
        # Start the patch
        mocked_validation_method = patcher.start()
        print(f"--- Fixture: Validation patched ('{validation_patch_target}' -> user {mock_user_id}). Started. ---")

        # Register finalizer to stop the patch
        request.addfinalizer(patcher.stop)
        print(f"--- Fixture: Registered finalizer to stop patch. Yielding token: {token[:5]}... ---")

    except Exception as e: # Catch broader exceptions during patching setup
        if patcher: patcher.stop()
        pytest.fail(f"Failed to patch validation method '{validation_patch_target}'. Error: {e}")

    # Yield the mock token - any call to Account.get() during tests using this fixture
    # will now return mock_appwrite_user_data
    yield token

    # Finalizer registered via addfinalizer will call patcher.stop() automatically
    print(f"--- Fixture: Session ending, validation patch stopped for '{validation_patch_target}' ---")

# Add other common fixtures below as needed
