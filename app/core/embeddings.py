# app/core/embeddings.py
"""
Embedding generation module.

This module handles the conversion of text into vector embeddings using
the Mistral embedding model. These embeddings are mathematical representations
of text that capture semantic meaning, allowing for:
1. Semantic similarity comparison
2. Storage in vector databases like Pinecone
3. Retrieval based on meaning rather than keyword matching

The module is separated from API endpoints to:
- Allow reuse across different parts of the application
- Simplify testing
- Provide a clean abstraction over the embedding API
"""

import logging
import time
from typing import List, Optional
from app.config.settings import settings
from mistralai import Mistral  # Import Mistral client directly

logger = logging.getLogger(__name__)

# Initialize Mistral client (moved here from clients.py)
try:
    mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY)
    logger.info("Mistral client initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize Mistral client: {e}")
    mistral_client = None

# Add this function to handle reconnection attempts
def ensure_mistral_client():
    global mistral_client
    
    if mistral_client:
        return mistral_client
        
    try:
        mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY)
        logger.info("Mistral client initialized successfully")
        return mistral_client
    except Exception as e:
        logger.error(f"Failed to initialize Mistral client: {e}")
        return None

# Then modify get_text_embedding to use this function
def get_text_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding for a single text input using the Mistral embedding model.

    Args:
        text: The text to convert to an embedding vector

    Returns:
        List of float values representing the embedding, or None if generation fails

    Note:
        This function handles a single text. For batch processing,
        use get_embeddings_in_chunks
    """
    client = ensure_mistral_client()
    if not client:
        logger.error("Mistral client not available")
        return None

    try:
        # The Mistral client expects inputs as a list, even for single items
        logger.debug(f"Generating embedding for text: {text[:50]}...")

        response = client.embeddings.create(
            model="mistral-embed",
            inputs=[text]
        )

        # Extract the embedding from the response
        embedding = response.data[0].embedding
        logger.debug("Successfully generated embedding")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None

def get_embeddings_in_chunks(text_list: List[str],
                            max_retries: int = 5,
                            base_delay: float = 1.0) -> List[Optional[List[float]]]:
    """
    Generate embeddings for a list of texts with retry logic.

    Handles batch processing with built-in error handling and exponential backoff
    for retries, which is essential when working with external APIs that might
    have rate limits or occasional failures.

    Args:
        text_list: List of texts to generate embeddings for
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff in seconds

    Returns:
        List of embeddings (or None for failed items)
    """
    if not mistral_client:
        logger.error("Mistral client not initialized")
        return [None] * len(text_list)

    logger.info(f"Processing batch with {len(text_list)} texts")

    attempt = 0
    while attempt < max_retries:
        try:
            logger.info(f"Attempt {attempt+1} to get embeddings for batch")

            response = mistral_client.embeddings.create(
                model="mistral-embed",
                inputs=text_list
            )

            logger.info("Successfully got embeddings for batch")
            return [data.embedding for data in response.data]

        except Exception as e:
            delay = base_delay * (2 ** attempt)  # Exponential backoff
            logger.exception(f"Error: {e}. Retrying in {delay} seconds.")
            time.sleep(delay)
            attempt += 1

    logger.error("Failed to process batch after multiple retries")
    return [None] * len(text_list)  # Return a list of None values matching input length