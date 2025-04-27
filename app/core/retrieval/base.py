import logging
from typing import List, Protocol, Optional
from app.models.schemas import DocumentMatch

logger = logging.getLogger(__name__)

class Retriever(Protocol):
    """Protocol defining the interface for all retriever implementations."""

    async def retrieve(self, query: str, top_k: int) -> Optional[List[DocumentMatch]]:
        """
        Retrieves relevant documents for a given query.

        Args:
            query: The user's query text.
            top_k: The maximum number of documents to return.

        Returns:
            A list of DocumentMatch objects, or None if an error occurs.
        """
        ...
