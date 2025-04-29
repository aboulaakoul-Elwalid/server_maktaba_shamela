from dotenv import load_dotenv
import logging
import os
import json
import asyncio
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check required environment variables
print("=== Environment Variables ===")
print(f"MISTRAL_API_KEY: {'Set' if os.environ.get('MISTRAL_API_KEY') else 'Missing'}")
print(f"PINECONE_API_KEY: {'Set' if os.environ.get('PINECONE_API_KEY') else 'Missing'}")
print(f"PINECONE_INDEX_NAME: {'Set' if os.environ.get('PINECONE_INDEX_NAME') else 'Missing'}")
print()

# Test the direct API approach with requests
def test_direct_api_call():
    print("=== Testing Direct API Call ===")
    import requests
    
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not found")
        return False
    
    try:
        print("Sending API request to Mistral...")
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "mistral-tiny",  # Use tiny for testing
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello in Arabic."}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            }
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return False
        
        data = response.json()
        print("\nResponse content:")
        print(data["choices"][0]["message"]["content"])
        return True
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        return False

# Test the Mistral Python SDK
def test_python_sdk():
    print("\n=== Testing Python SDK ===")
    try:
        from mistralai.client import MistralClient
        from mistralai.models.chat_completion import ChatMessage
        
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            print("ERROR: MISTRAL_API_KEY not found")
            return False
        
        print("Initializing MistralClient from official SDK...")
        client = MistralClient(api_key=api_key)
        
        # Check client properties and methods
        print("\nMethods and attributes available:")
        for item in dir(client):
            if not item.startswith('_'):
                print(f"- {item}")
        
        # Try using the SDK properly
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="Say hello in Arabic.")
        ]
        
        print("\nSending request via SDK...")
        chat_response = client.chat(
            model="mistral-tiny",
            messages=messages
        )
        
        print("\nResponse content:")
        print(chat_response.choices[0].message.content)
        return True
        
    except ImportError:
        print("ERROR: mistralai SDK not installed. Install with: pip install mistralai")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        return False

# Run tests
print("Starting tests...\n")
http_test = test_direct_api_call()
sdk_test = test_python_sdk()

print("\n=== Results ===")
print(f"Direct API call: {'SUCCESS ✅' if http_test else 'FAILED ❌'}")
print(f"Python SDK: {'SUCCESS ✅' if sdk_test else 'FAILED ❌'}")

if not sdk_test:
    print("\n=== Recommendation ===")
    print("Try installing the official Mistral SDK: pip install mistralai")