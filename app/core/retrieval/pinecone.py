import logging
from typing import List, Optional
from app.core.clients import get_pinecone_index
from app.core.embeddings import get_text_embedding
from app.models.schemas import DocumentMatch, DocumentMetadata
from .base import Retriever # Import the protocol

logger = logging.getLogger(__name__)

class PineconeRetriever(Retriever):
    """Retriever implementation using Pinecone."""

    async def retrieve(self, query: str, top_k: int) -> Optional[List[DocumentMatch]]:
        """
        Retrieves documents from Pinecone based on the query.
        """
        try:
            index = get_pinecone_index()
            if not index:
                logger.error("Pinecone index not available for retrieval.")
                return None

            # Assuming get_text_embedding is synchronous for now.
            # If it becomes async, add 'await' here.
            query_embedding = get_text_embedding(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding for retrieval.")
                return None

            logger.debug(f"Querying Pinecone index '{index.name}' with top_k={top_k}")
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )

            matches = []
            if results and results.get('matches'):
                logger.debug(f"Received {len(results['matches'])} matches from Pinecone.")
                for match in results['matches']:
                    match_id = match.get('id', 'UNKNOWN_ID')
                    metadata_dict = match.get('metadata', {})
                    logger.debug(f"Raw metadata for match ID {match_id}: {metadata_dict}")

                    # Extract text safely
                    raw_text_content = metadata_dict.get('text')
                    if raw_text_content is None:
                        logger.error(f"Match ID {match_id}: CRITICAL - 'text' field missing in Pinecone metadata! Keys: {list(metadata_dict.keys())}")
                        raw_text_content = "" # Default to empty string

                    # Extract other relevant fields
                    author = metadata_dict.get('author_name')
                    book = metadata_dict.get('book_name')
                    category = metadata_dict.get('category_name')
                    section = metadata_dict.get('section_title')
                    book_id_meta = metadata_dict.get('book_id') # Get book_id if stored separately

                    try:
                        metadata = DocumentMetadata(
                            author_name=author,
                            book_name=book,
                            category_name=category,
                            section_title=section,
                            text=raw_text_content,
                            book_id=book_id_meta # Pass book_id if available
                        )

                        doc_match = DocumentMatch(
                            id=match_id,
                            score=match.get('score', 0.0),
                            metadata=metadata
                        )
                        matches.append(doc_match)
                    except Exception as pydantic_error:
                        logger.error(f"Pydantic validation failed for metadata of match ID {match_id}: {pydantic_error}")
                        logger.debug(f"Failing metadata dictionary: {metadata_dict}")

            else:
                logger.warning(f"No matches found in Pinecone for query: {query[:50]}...")

            return matches

        except Exception as e:
            logger.exception(f"Error querying Pinecone vector store: {e}")
            return None
