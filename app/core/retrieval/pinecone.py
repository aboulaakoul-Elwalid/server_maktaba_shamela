import logging
from typing import List, Optional
from app.core.clients import get_pinecone_index
from app.core.embeddings import get_text_embedding
from app.models.schemas import DocumentMatch, DocumentMetadata
from .base import Retriever
from app.config.settings import settings

logger = logging.getLogger(__name__)

class PineconeRetriever(Retriever):
    """Retriever implementation using Pinecone."""

    async def retrieve(self, query: str, top_k: int) -> List[DocumentMatch]:
        """
        Retrieves documents from Pinecone based on the query.
        Always returns a list (possibly empty), never None.
        """
        try:
            index = get_pinecone_index()
            if not index:
                logger.error("Pinecone index not available for retrieval.")
                return []

            # Assuming get_text_embedding is synchronous for now.
            query_embedding = get_text_embedding(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding for retrieval.")
                return []

            logger.debug(f"Querying Pinecone index '{settings.PINECONE_INDEX_NAME}' with top_k={top_k}")
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

                    # Extract fields safely
                    raw_text_content = metadata_dict.get('text', "")  # Default to empty string
                    if not raw_text_content:  # Log if text is actually empty in metadata
                        logger.warning(f"Match ID {match_id}: 'text' field is missing or empty in raw metadata.")

                    author = metadata_dict.get('author_name')
                    book = metadata_dict.get('book_name')
                    category = metadata_dict.get('category_name')
                    section = metadata_dict.get('section_title')

                    # Convert book_id to string if it exists
                    book_id_val = metadata_dict.get('book_id')
                    book_id_str: Optional[str] = None
                    if book_id_val is not None:
                        try:
                            # Convert float to int first (if applicable), then to string
                            book_id_str = str(int(book_id_val))
                        except (ValueError, TypeError):
                            # If conversion fails, log it and keep as None or original string if already str
                            logger.warning(f"Match ID {match_id}: Could not convert book_id '{book_id_val}' to string. Setting to None.")
                            book_id_str = None

                    try:
                        # Create Pydantic model using the converted book_id_str
                        metadata = DocumentMetadata(
                            author_name=author,
                            book_name=book,
                            category_name=category,
                            section_title=section,
                            text=raw_text_content,
                            book_id=book_id_str  # Pass the converted string or None
                        )

                        doc_match = DocumentMatch(
                            id=match_id,
                            score=match.get('score', 0.0),
                            metadata=metadata
                        )
                        matches.append(doc_match)
                    except Exception as pydantic_error:
                        logger.error(f"Pydantic validation failed for metadata of match ID {match_id}: {pydantic_error}")
                        logger.debug(f"Failing metadata dictionary (post book_id conversion attempt): {metadata_dict}")

            else:
                logger.warning(f"No matches found in Pinecone for query: {query[:50]}...")

            # Log how many matches *successfully* passed validation
            logger.info(f"Successfully processed {len(matches)} documents after validation.")
            return matches

        except Exception as e:
            logger.exception(f"CRITICAL Error querying Pinecone vector store: {e}")
            return []
