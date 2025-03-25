# clients.py
import os
from dotenv import load_dotenv
from mistralai import Mistral
from pinecone import Pinecone

load_dotenv()
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found.")

mistral_client = Mistral(api_key=MISTRAL_API_KEY)

def init_pinecone(api_key: str):
    return Pinecone(api_key=api_key)