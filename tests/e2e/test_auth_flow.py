import pytest
from fastapi.testclient import TestClient
import random
import string

# --- Helper to generate random email ---
def random_email():
    domain = "test.pytest.dev"
    username_length = 10
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
    return f"{username}@{domain}"

# --- Test Class for Auth Flow ---
# Using a class allows sharing state (like user_data, token) between tests if needed,
# though keeping tests independent is often preferred.
class TestAuthFlow:

    # Store created user details and token for sequential tests within the class
    user_data = {}
    auth_token = None

    def test_register_user(self, client: TestClient):
        """Tests user registration via the /auth/register endpoint."""
        print("\n--- Testing User Registration ---")
        email = random_email()
        password = "TestPassword123!"
        name = "Pytest User"
        TestAuthFlow.user_data = {"email": email, "password": password, "name": name} # Store for login test

        response = client.post(
            "/auth/register",
            json=TestAuthFlow.user_data
        )

        print(f"Register Request Body: {TestAuthFlow.user_data}")
        print(f"Register Response Status: {response.status_code}")
        print(f"Register Response Body: {response.text}") # Use .text for raw response

        assert response.status_code == 200 # Or 201 if you use Created status
        response_data = response.json()
        assert "user_id" in response_data
        assert isinstance(response_data["user_id"], str)
        assert response_data.get("message") == "User registered successfully"

    def test_login_user(self, client: TestClient):
        """Tests user login via the /auth/login endpoint using registered credentials."""
        print("\n--- Testing User Login ---")
        # Ensure registration test ran first and user_data is populated
        assert "email" in TestAuthFlow.user_data, "Registration must run before login test"

        login_payload = {
            "email": TestAuthFlow.user_data["email"],
            "password": TestAuthFlow.user_data["password"]
        }
        response = client.post(
            "/auth/login",
            json=login_payload
        )

        print(f"Login Request Body: {login_payload}")
        print(f"Login Response Status: {response.status_code}")
        print(f"Login Response Body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()
        assert "access_token" in response_data
        assert response_data.get("token_type") == "bearer"
        assert "expires_in" in response_data
        assert "issued_at" in response_data
        TestAuthFlow.auth_token = response_data["access_token"] # Store token for /me test

    def test_get_me(self, client: TestClient):
        """Tests fetching user profile via the /auth/me endpoint using the obtained token."""
        print("\n--- Testing Get Me ---")
        # Ensure login test ran first and token is available
        assert TestAuthFlow.auth_token is not None, "Login must run before get_me test"
        assert "email" in TestAuthFlow.user_data, "Registration/Login must run before get_me test"

        headers = {"Authorization": f"Bearer {TestAuthFlow.auth_token}"}
        response = client.get("/auth/me", headers=headers)

        print(f"Get Me Headers: {headers}")
        print(f"Get Me Response Status: {response.status_code}")
        print(f"Get Me Response Body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()
        assert "user_id" in response_data
        assert response_data.get("email") == TestAuthFlow.user_data["email"]
        assert response_data.get("name") == TestAuthFlow.user_data["name"]
        assert response_data.get("is_anonymous") is False
