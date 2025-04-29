import pytest
from fastapi.testclient import TestClient
from typing import Dict # Import Dict

# --- Test Class for Anonymous Chat Access ---
class TestAnonymousChat:

    # We need a valid conversation ID created by an authenticated user
    # We can potentially reuse the authenticated flow or create one specifically
    @pytest.fixture(scope="class")
    def authenticated_conversation(self, client: TestClient, authenticated_user_token: str) -> Dict[str, str]:
        """Creates a conversation using an authenticated user."""
        print("\n--- Fixture: Creating conversation for anonymous tests ---")
        auth_headers = {"Authorization": f"Bearer {authenticated_user_token}"}
        response = client.post("/chat/conversations", headers=auth_headers)
        assert response.status_code == 201, "Failed to create conversation in fixture (expecting 201)" # <-- CHANGE BACK TO 201
        data = response.json()
        assert "id" in data
        print(f"--- Fixture: Created conversation ID: {data['id']} ---")
        # Return user ID and conversation ID
        # We need the user ID associated with the token from the fixture
        # For now, let's assume the conftest fixture patch uses 'mock_conftest_user_id'
        # A better way would be to decode the mock token or have the fixture return the user ID
        return {"conversation_id": data["id"], "user_id": "mock_conftest_user_id"}


    def test_get_conversation_history_anonymously(self, client: TestClient, authenticated_conversation: Dict[str, str]):
        """Tests that an anonymous user CANNOT get history for someone else's conversation."""
        print("\n--- Testing GET /messages anonymously ---")
        conversation_id = authenticated_conversation["conversation_id"]
        url = f"/chat/conversations/{conversation_id}/messages"
        print(f"Request URL: {url}")

        # Make request WITHOUT Authorization header
        response = client.get(url)

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        # --- ASSERTION ---
        # We expect access denied (401, 403) or potentially 404 if the endpoint hides existence
        # Let's check against the 404 you observed, but also consider 401/403
        assert response.status_code in [401, 403, 404], f"Expected 401/403/404 but got {response.status_code}"

        # Specifically check if it's the 404 you saw
        if response.status_code == 404:
             print("WARN: Received 404 Not Found. Should this be 401 Unauthorized or 403 Forbidden instead?")
             # Check if the detail matches the one you saw from the frontend
             assert response.json().get("detail") == "Not Found", "404 detail message mismatch"
        elif response.status_code == 403:
             # Check the specific detail message from our get_conversation_messages endpoint
             assert response.json().get("detail") == "Anonymous users cannot retrieve conversation history."
        elif response.status_code == 401:
             # Default FastAPI 401 message
             assert response.json().get("detail") == "Not authenticated"


    def test_send_message_anonymously_to_existing_convo(self, client: TestClient, authenticated_conversation: Dict[str, str]):
        """Tests that an anonymous user CANNOT send messages to someone else's conversation."""
        print("\n--- Testing POST /messages anonymously to existing convo ---")
        conversation_id = authenticated_conversation["conversation_id"]
        url = "/chat/messages"
        payload = {"content": "Anonymous message attempt", "conversation_id": conversation_id}
        print(f"Request URL: {url}")
        print(f"Request Payload: {payload}")

        # Make request WITHOUT Authorization header
        response = client.post(url, json=payload)

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        # --- ASSERTION ---
        # Expecting 401/403 (or maybe 404 if conversation check happens before auth)
        assert response.status_code in [401, 403, 404], f"Expected 401/403/404 but got {response.status_code}"

        # Add specific checks based on expected behavior (likely 401 or 403)
        if response.status_code == 401:
            assert response.json().get("detail") == "Not authenticated"
        # Add checks for 403/404 if applicable based on your endpoint logic


    # Potential test: Sending a message without a conversation ID anonymously
    # def test_send_first_message_anonymously(self, client: TestClient):
    #     """Tests sending the first message anonymously (behavior depends on design)."""
    #     print("\n--- Testing POST /messages anonymously (first message) ---")
    #     url = "/chat/messages"
    #     payload = {"content": "First anonymous message"}
    #     print(f"Request URL: {url}")
    #     print(f"Request Payload: {payload}")
    #
    #     response = client.post(url, json=payload)
    #
    #     print(f"Response Status: {response.status_code}")
    #     print(f"Response Body: {response.text}")
    #
    #     # --- ASSERTION ---
    #     # This depends entirely on whether you WANT to allow anonymous chat.
    #     # If YES: Expect 200 OK, response should contain message details and maybe a conversation_id
    #     # If NO: Expect 401 Unauthorized or 403 Forbidden
    #     assert response.status_code in [200, 401, 403] # Adjust based on desired behavior
    #     if response.status_code == 200:
    #         # Add assertions for successful anonymous message
    #         pass
    #     elif response.status_code == 401:
    #         assert response.json().get("detail") == "Not authenticated"
    #     elif response.status_code == 403:
    #         # Add assertion for specific 403 detail if applicable
    #         pass
