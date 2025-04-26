import pytest
from fastapi.testclient import TestClient
import time

# --- Test Class for Chat Flow ---
class TestChatFlow:

    # Store conversation ID to share between tests in the class
    conversation_id: str = None
    auth_headers: dict = {}

    @pytest.fixture(autouse=True)
    def setup_auth_header(self, authenticated_user_token: str):
        """Fixture to automatically set the auth header for all tests in this class."""
        TestChatFlow.auth_headers = {"Authorization": f"Bearer {authenticated_user_token}"}
        print(f"\n--- Setup Auth Header for TestChatFlow ---")

    def test_create_conversation(self, client: TestClient):
        """Tests creating a new conversation."""
        print("\n--- Testing Create Conversation ---")
        response = client.post("/chat/conversations", headers=TestChatFlow.auth_headers)

        print(f"Create Conversation Headers: {TestChatFlow.auth_headers}")
        print(f"Create Conversation Status: {response.status_code}")
        print(f"Create Conversation Body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()
        assert "conversation_id" in response_data
        assert isinstance(response_data["conversation_id"], str)
        TestChatFlow.conversation_id = response_data["conversation_id"] # Store for next tests

    def test_send_first_message(self, client: TestClient):
        """Tests sending the first message to the created conversation."""
        print("\n--- Testing Send First Message ---")
        assert TestChatFlow.conversation_id is not None, "Create conversation must run first"

        message_payload = {"content": "Tell me about the pillars of Islam."}
        # Note: Your actual endpoint might be /chat/messages and takes conversation_id in payload
        # Adjusting based on the prompt's desired structure: POST /chat/conversations/{id}/message
        # If your actual endpoint is different (like POST /chat/messages), change the URL below.
        # Based on your chat.py, the endpoint is POST /messages, taking conversation_id in payload
        message_payload_with_id = {
            "content": "Tell me about the pillars of Islam.",
            "conversation_id": TestChatFlow.conversation_id
        }
        response = client.post(
            "/chat/messages", # Corrected based on chat.py
            headers=TestChatFlow.auth_headers,
            json=message_payload_with_id
        )

        print(f"Send Message Headers: {TestChatFlow.auth_headers}")
        print(f"Send Message Payload: {message_payload_with_id}")
        print(f"Send Message Status: {response.status_code}")
        print(f"Send Message Body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()
        # Assert based on the actual response structure of your /chat/messages endpoint
        assert "ai_response" in response_data
        assert "sources" in response_data
        assert response_data.get("conversation_id") == TestChatFlow.conversation_id

    def test_send_follow_up_message(self, client: TestClient):
        """Tests sending a follow-up message."""
        print("\n--- Testing Send Follow-up Message ---")
        assert TestChatFlow.conversation_id is not None, "Create conversation must run first"
        time.sleep(1) # Small delay sometimes helps avoid race conditions or rate limits

        message_payload_with_id = {
            "content": "What is Zakat?",
            "conversation_id": TestChatFlow.conversation_id
        }
        response = client.post(
            "/chat/messages", # Corrected based on chat.py
            headers=TestChatFlow.auth_headers,
            json=message_payload_with_id
        )

        print(f"Send Follow-up Headers: {TestChatFlow.auth_headers}")
        print(f"Send Follow-up Payload: {message_payload_with_id}")
        print(f"Send Follow-up Status: {response.status_code}")
        print(f"Send Follow-up Body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()
        assert "ai_response" in response_data
        # Add more specific assertions if needed

    def test_get_conversation_history(self, client: TestClient):
        """Tests retrieving the full message history for the conversation."""
        print("\n--- Testing Get Conversation History ---")
        assert TestChatFlow.conversation_id is not None, "Create conversation must run first"

        # Based on your chat.py, the endpoint is GET /chat/conversations/{id}/messages
        response = client.get(
            f"/chat/conversations/{TestChatFlow.conversation_id}/messages",
            headers=TestChatFlow.auth_headers
        )

        print(f"Get History Headers: {TestChatFlow.auth_headers}")
        print(f"Get History URL: /chat/conversations/{TestChatFlow.conversation_id}/messages")
        print(f"Get History Status: {response.status_code}")
        print(f"Get History Body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, list)
        # Expecting user message, AI response, user message, AI response = 4 messages
        assert len(response_data) >= 4 # Check if at least 4 messages exist
        # Check order and content (optional but good)
        assert response_data[0].get("message_type") == "user"
        assert response_data[0].get("content") == "Tell me about the pillars of Islam."
        assert response_data[1].get("message_type") == "ai"
        assert response_data[2].get("message_type") == "user"
        assert response_data[2].get("content") == "What is Zakat?"
        assert response_data[3].get("message_type") == "ai"
        # Check if conversation_id matches in messages
        for msg in response_data:
            assert msg.get("conversation_id") == TestChatFlow.conversation_id
