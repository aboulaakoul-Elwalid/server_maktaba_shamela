import requests
import json
import random
import string
import time
import os

# --- Configuration ---
# Use environment variable or hardcode (use env var for flexibility)
API_BASE_URL = os.getenv("PROD_API_URL", "https://server-maktaba-shamela.onrender.com")
REGISTER_ENDPOINT = f"{API_BASE_URL}/auth/register"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
CONVERSATIONS_ENDPOINT = f"{API_BASE_URL}/chat/conversations"
STREAM_ENDPOINT = f"{API_BASE_URL}/chat/messages/stream"

# --- Helper Functions ---

def random_string(length=10):
    """Generates a random string for unique emails/names."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def register_user(session: requests.Session) -> dict:
    """Registers a new random user."""
    email = f"test_{random_string()}@pytest.prod.dev"
    password = f"TestPass_{random_string()}!"
    name = f"Pytest Prod User {random_string(5)}"
    payload = {"email": email, "password": password, "name": name}
    print(f"\n[REGISTER] Attempting registration for: {email}")
    try:
        response = session.post(REGISTER_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status() # Raise exception for 4xx/5xx errors
        print(f"[REGISTER] Success: {response.status_code}")
        print(f"[REGISTER] Response: {response.json()}")
        # Return credentials needed for login
        return {"email": email, "password": password, "data": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"[REGISTER] FAILED: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[REGISTER] Response Body: {e.response.text}")
        raise

def login_user(session: requests.Session, credentials: dict) -> str:
    """Logs in the user and returns the auth token."""
    payload = {"email": credentials["email"], "password": credentials["password"]}
    print(f"\n[LOGIN] Attempting login for: {credentials['email']}")
    try:
        response = session.post(LOGIN_ENDPOINT, json=payload, timeout=20)
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("Access token not found in login response")
        print(f"[LOGIN] Success: {response.status_code}")
        print(f"[LOGIN] Token Received: {token[:15]}...")
        return token
    except requests.exceptions.RequestException as e:
        print(f"[LOGIN] FAILED: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[LOGIN] Response Body: {e.response.text}")
        raise
    except ValueError as e:
        print(f"[LOGIN] FAILED: {e}")
        print(f"[LOGIN] Response Body: {response.text}")
        raise


def create_conversation(session: requests.Session, token: str) -> str:
    """Creates a new conversation and returns its ID."""
    headers = {"Authorization": f"Bearer {token}"}
    print("\n[CREATE CONVO] Attempting to create conversation...")
    try:
        response = session.post(CONVERSATIONS_ENDPOINT, headers=headers, timeout=20)
        response.raise_for_status()
        convo_id = response.json().get("conversation_id")
        if not convo_id:
            raise ValueError("Conversation ID not found in creation response")
        print(f"[CREATE CONVO] Success: {response.status_code}")
        print(f"[CREATE CONVO] Conversation ID: {convo_id}")
        return convo_id
    except requests.exceptions.RequestException as e:
        print(f"[CREATE CONVO] FAILED: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[CREATE CONVO] Response Body: {e.response.text}")
        raise
    except ValueError as e:
        print(f"[CREATE CONVO] FAILED: {e}")
        print(f"[CREATE CONVO] Response Body: {response.text}")
        raise

def test_streaming_message():
    """Performs the full E2E streaming test."""
    session = requests.Session() # Use a session to persist cookies if needed (though JWT is header-based)
    auth_token = None
    conversation_id = None

    try:
        # 1. Register
        user_credentials = register_user(session)

        # 2. Login
        auth_token = login_user(session, user_credentials)

        # 3. Create Conversation
        conversation_id = create_conversation(session, auth_token)

        # 4. Send Streaming Message
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" # Important for SSE
        }
        payload = {
            "content": "Tell me about the concept of Tawhid in Islam.",
            "conversation_id": conversation_id
            # No history needed for the first message of authenticated user
        }
        print(f"\n[STREAM REQ] Sending message to {STREAM_ENDPOINT}")
        print(f"[STREAM REQ] Payload: {json.dumps(payload)}")

        received_chunk = False
        received_sources = False
        received_message_id = False
        received_end = False
        full_response_text = ""

        try:
            # Use stream=True and iter_lines() for SSE
            with session.post(STREAM_ENDPOINT, headers=headers, json=payload, stream=True, timeout=60) as response:
                response.raise_for_status() # Check for initial HTTP errors
                print("[STREAM RESP] Connected. Waiting for events...")

                current_event = {}
                for line_bytes in response.iter_lines():
                    if not line_bytes: # End of an event
                        if current_event.get("event") == "chunk":
                            try:
                                data = json.loads(current_event.get("data", "{}"))
                                token = data.get("token", "")
                                print(f"  chunk: '{token}'") # Print token directly
                                full_response_text += token
                                received_chunk = True
                            except json.JSONDecodeError:
                                print(f"  [WARN] Failed to parse chunk data: {current_event.get('data')}")
                        elif current_event.get("event") == "sources":
                            print(f"  sources: {current_event.get('data')}")
                            received_sources = True
                        elif current_event.get("event") == "message_id":
                            print(f"  message_id: {current_event.get('data')}")
                            received_message_id = True
                        elif current_event.get("event") == "end":
                            print(f"  end: {current_event.get('data')}")
                            received_end = True
                        elif current_event.get("event") == "error":
                            print(f"  [ERROR EVENT]: {current_event.get('data')}")
                            # Decide if this is a fatal error for the test
                        elif current_event.get("event"): # Other events?
                             print(f"  {current_event.get('event')}: {current_event.get('data')}")

                        current_event = {} # Reset for next event
                        continue

                    line = line_bytes.decode('utf-8')
                    if line.startswith("event:"):
                        current_event["event"] = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        current_event["data"] = line.split(":", 1)[1].strip()
                    # Ignore other lines like 'id:' or comments ':'

                print("\n[STREAM RESP] Stream finished.")
                print(f"[STREAM RESP] Full AI Response Text:\n{full_response_text}")

        except requests.exceptions.RequestException as e:
            print(f"[STREAM REQ] FAILED: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[STREAM REQ] Response Body: {e.response.text}")
            raise

        # --- Assertions ---
        print("\n[ASSERTIONS]")
        assert received_chunk, "Did not receive any 'chunk' events"
        assert received_sources, "Did not receive 'sources' event"
        # message_id is only sent if stored (i.e., not anonymous)
        assert received_message_id, "Did not receive 'message_id' event (check if AI message was stored)"
        assert received_end, "Did not receive 'end' event"
        assert len(full_response_text) > 0, "Full response text is empty"
        print("[ASSERTIONS] All checks passed!")

    finally:
        # Optional: Clean up user/conversation if needed (requires delete endpoints)
        print("\n[CLEANUP] Test finished.")
        session.close()

# --- Run the test ---
if __name__ == "__main__":
    test_streaming_message()