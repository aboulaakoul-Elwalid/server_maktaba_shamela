import pytest
from fastapi.testclient import TestClient
import os
import sys
import random
import string # Import random and string

# Add the project root to the Python path to allow importing 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import your FastAPI app instance
try:
    from app.main import app
except ImportError as e:
    print(f"Error importing FastAPI app: {e}")
    print("Please ensure 'app.main:app' points to your FastAPI application instance.")
    from fastapi import FastAPI
    app = FastAPI()


@pytest.fixture(scope="module")
def client():
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        print("\n--- Initializing TestClient ---")
        yield test_client
        print("\n--- Tearing down TestClient ---")

# --- Helper to generate random email ---
# (Moved here to be reusable by fixtures)
def random_email():
    domain = "fixture.pytest.dev"
    username_length = 10
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
    return f"{username}@{domain}"

@pytest.fixture(scope="module")
def authenticated_user_token(client: TestClient):
    """
    Registers and logs in a user, returning the auth token.
    Scope is 'module' to reuse the same user/token for all tests in a module.
    """
    print("\n--- Fixture: Creating authenticated user ---")
    email = random_email()
    password = "FixturePassword123!"
    name = "Fixture User"
    user_data = {"email": email, "password": password, "name": name}

    # Register
    reg_response = client.post("/auth/register", json=user_data)
    if reg_response.status_code != 200:
         # Handle potential 409 conflict if email somehow already exists
         if reg_response.status_code == 409:
             print(f"Fixture Warning: User {email} might already exist. Attempting login.")
         else:
             pytest.fail(f"Fixture failed: Registration failed with status {reg_response.status_code}, body: {reg_response.text}")
    else:
        print(f"Fixture: User {email} registered.")

    # Login
    login_payload = {"email": email, "password": password}
    login_response = client.post("/auth/login", json=login_payload)
    assert login_response.status_code == 200, f"Fixture failed: Login failed with status {login_response.status_code}, body: {login_response.text}"
    token_data = login_response.json()
    token = token_data.get("access_token")
    assert token is not None, "Fixture failed: Access token not found in login response."
    print(f"Fixture: User {email} logged in, token obtained.")

    yield token # Provide the token to the tests

    print(f"\n--- Fixture: Teardown for authenticated user {email} ---")
    # Optional: Add cleanup logic here if needed (e.g., delete user via API key)