# app/core/retrieval.py
"""
Vector database retrieval module.

This module handles querying the Pinecone vector database to find
documents similar to a given query. It:
1. Converts query text to embeddings
2. Searches the vector database for similar vectors
3. Returns matches with their metadata and similarity scores

Separation of retrieval logic from API endpoints allows:
- Reuse in different contexts (API, command-line tools, scheduled jobs)
- Unit testing without API dependencies
- Clear separation of concerns
"""

import logging
from typing import List, Dict, Any, Optional
from app.core.clients import get_pinecone_index
from app.core.embeddings import get_text_embedding
from app.models.schemas import DocumentMatch, DocumentMetadata

logger = logging.getLogger(__name__)

def query_vector_store(
    query_text: str,
    top_k: int = 5
) -> Optional[List[DocumentMatch]]:
    """
    Queries the vector store for documents similar to the query text.

    Args:
        query_text: The text to search for.
        top_k: The number of results to return.

    Returns:
        A list of DocumentMatch objects or None if an error occurs.
    """
    try:
        index = get_pinecone_index()
        if not index:
            logger.error("Pinecone index not available.")
            return None

        query_embedding = get_text_embedding(query_text)
        if not query_embedding:
            logger.error("Failed to generate query embedding.")
            return None

        logger.debug(f"Querying Pinecone index with top_k={top_k}")
        # Ensure include_metadata=True is used
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )

        matches = []
        if results and results.get('matches'):
            logger.debug(f"Received {len(results['matches'])} matches from Pinecone.")
            for match in results['matches']:
                match_id = match.get('id', 'UNKNOWN_ID') # Get ID for logging
                metadata_dict = match.get('metadata', {})
                # Log the raw metadata received for debugging
                logger.debug(f"Raw metadata for match ID {match_id}: {metadata_dict}")

                # Explicitly check and log the 'text' field from the raw dict
                raw_text_content = metadata_dict.get('text') # Use .get() which returns None if key is missing
                if raw_text_content is not None: # Check if the key existed and had a value (even if empty string)
                    logger.info(f"Match ID {match_id}: Found 'text' field in raw metadata (first 100 chars): '{str(raw_text_content)[:100]}'")
                    if not raw_text_content:
                         logger.warning(f"Match ID {match_id}: 'text' field exists in raw metadata but is empty.")
                else:
                    # Log if the 'text' key was completely missing from the metadata dictionary
                    logger.error(f"Match ID {match_id}: CRITICAL - Did NOT find 'text' field in raw metadata! Keys present: {list(metadata_dict.keys())}")
                    # Assign empty string if text is missing to avoid downstream errors, but log the error.
                    raw_text_content = ''

                # Extract fields, ensuring 'text' is present in the Pydantic model
                try:
                    # Create the Pydantic model using the extracted (or defaulted) text
                    metadata = DocumentMetadata(
                        book_name=metadata_dict.get('book_name', 'Unknown Book'),
                        section_title=metadata_dict.get('section_title', 'Unknown Section'),
                        text=raw_text_content # Assign the potentially empty string if key was missing
                    )
                    # This warning confirms if the Pydantic model's field ended up empty
                    if not metadata.text and raw_text_content is not None: # Log only if it wasn't missing entirely
                         logger.warning(f"Match ID {match_id}: Pydantic model 'metadata.text' is empty after assignment (was empty in source).")

                    doc_match = DocumentMatch(
                        id=match_id,
                        score=match.get('score', 0.0),
                        metadata=metadata
                    )
                    matches.append(doc_match)
                except Exception as pydantic_error:
                     # This catches errors during Pydantic model creation itself
                     logger.error(f"Pydantic validation failed for metadata of match ID {match_id}: {pydantic_error}")
                     logger.debug(f"Failing metadata dictionary: {metadata_dict}")
                     # Optionally skip this match or handle differently

        else:
             logger.warning("No matches found in Pinecone results.")

        return matches

    except Exception as e:
        logger.exception(f"Error querying vector store: {e}")
        return None