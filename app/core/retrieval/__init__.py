import logging
from functools import lru_cache
from app.config.settings import settings
from .base import Retriever
from .pinecone import PineconeRetriever
# Import other retriever implementations here if added later
# from .faiss import FaissRetriever

logger = logging.getLogger(__name__)

@lru_cache()
def get_retriever() -> Retriever:
    """
    Factory function to get the configured retriever instance.
    Uses LRU cache to return a singleton instance.
    """
    provider = settings.RETRIEVER_PROVIDER.lower()
    logger.info(f"Initializing retriever with provider: {provider}")

    if provider == "pinecone":
        return PineconeRetriever()
    # Add other providers here
    # elif provider == "faiss":
    #     return FaissRetriever()
    else:
        logger.error(f"Unsupported retriever provider configured: {provider}")
        raise ValueError(f"Unsupported retriever provider: {provider}")

# Expose the factory function
__all__ = ["get_retriever", "Retriever"]
