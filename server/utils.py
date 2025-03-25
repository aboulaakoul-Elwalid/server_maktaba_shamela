import os
import time
from mistralai import Mistral
import logging
from dotenv import load_dotenv


load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY not found in environment variables.")

model = "mistral-embed"
client = Mistral(api_key=api_key)

def get_text_embedding(text):
    """
    Generates an embedding for a single text input using the Mistral AI API.

    Args:
        text (str): The text to embed.

    Returns:
        list: The embedding vector.
    """
    try:
        # Use the create method with 'inputs' parameter instead of 'input'
        response = client.embeddings.create(model=model, inputs=[text])
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding for text: {text}. Error: {e}")
        return None

def get_embeddings_in_chunks(text_list, delay=1):
    """
    Generates embeddings for a list of texts, handling API errors and rate limits.
    This version assumes the text_list is already appropriately sized for the API.
    """
    logging.info(f"Processing batch with {len(text_list)} texts")
    attempt = 0
    while attempt < 5:  # Retry up to 5 times
        try:
            logging.info(f"Attempt {attempt+1} to get embeddings for batch")
            # Use the create method with 'inputs' parameter instead of 'input'
            response = client.embeddings.create(model=model, inputs=text_list)
            logging.info(f"Successfully got embeddings for batch")
            return [data.embedding for data in response.data]
        except Exception as e:
            logging.exception(f"Unexpected error: {e}. Retrying in {delay * (attempt + 1)} seconds.")
            time.sleep(delay * (attempt + 1))
        attempt += 1
    logging.error("Failed to process batch after multiple retries. Skipping.")
    return []