# test_rag.py
import os
import sys
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Import after environment variables are loaded
from app.core.retrieval_old import query_vector_store
from app.core.clients import init_mistral_client

def test_retrieval():
    """Test document retrieval from vector database"""
    try:
        documents = query_vector_store(query_text="Arabia", top_k=3)
        print(f"Retrieved {len(documents)} documents")
        for i, doc in enumerate(documents):
            print(f"Document {i+1}: {doc.metadata.book_name}")
            print(f"Score: {doc.score}")
            print(f"Text: {doc.text_snippet[:100]}...")
            print("---")
        return True
    except Exception as e:
        print(f"Retrieval test failed: {e}")
        return False

def test_mistral_client():
    """Test Mistral client initialization and API call"""
    try:
        client = init_mistral_client()
        if not client:
            print("Failed to initialize Mistral client")
            return False
            
        print("Testing a simple API call...")
        response = client.chat(
            model="mistral-medium",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, this is a test'"}
            ]
        )
        
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"Mistral API test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing RAG components:")
    print("\n1. Testing retrieval...")
    retrieval_success = test_retrieval()
    
    print("\n2. Testing Mistral client...")
    mistral_success = test_mistral_client()
    
    print("\nResults:")
    print(f"Retrieval: {'✅' if retrieval_success else '❌'}")
    print(f"Mistral API: {'✅' if mistral_success else '❌'}")
    
    if not retrieval_success or not mistral_success:
        print("\nSome tests failed. Check your environment variables and connections.")
        print("Required environment variables:")
        print(f"MISTRAL_API_KEY: {'Set' if os.environ.get('MISTRAL_API_KEY') else 'Missing'}")
        print(f"PINECONE_API_KEY: {'Set' if os.environ.get('PINECONE_API_KEY') else 'Missing'}")
        print(f"PINECONE_INDEX_NAME: {'Set' if os.environ.get('PINECONE_INDEX_NAME') else 'Missing'}")