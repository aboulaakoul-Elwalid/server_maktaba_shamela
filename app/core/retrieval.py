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
    Query the vector store using semantic search.
    
    This function:
    1. Converts the query text to an embedding vector
    2. Searches the Pinecone index for similar vectors
    3. Formats and returns the matching documents
    
    Args:
        query_text: The text to search for
        top_k: Number of results to return (default: 5)
        
    Returns:
        List of matched documents with scores and metadata,
        or None if the query fails
    """
    try:
        # Step 1: Generate embedding for the query
        query_embedding = get_text_embedding(query_text)
        if query_embedding is None:
            logger.error(f"Failed to generate embedding for query: '{query_text}'")
            return None
        
        logger.info(f"Generated embedding for query: '{query_text[:50]}...'")
        
        # Step 2: Query Pinecone index
        index = get_pinecone_index()
        response = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # Step 3: Process and return results
        if not response or 'matches' not in response:
            logger.warning("No matches found or invalid response from Pinecone")
            return []
            
        logger.info(f"Found {len(response['matches'])} matches in vector store")
        
        # Convert Pinecone response to our schema model
        matches = []
        for match in response['matches']:
            try:
                # Extract document metadata
                metadata = match.get('metadata', {})
                
                # Create DocumentMatch object (will be validated by Pydantic)
                document_match = DocumentMatch(
                    score=match['score'],
                    id=match['id'],
                    metadata=DocumentMetadata(
                        book_name=metadata.get('book_name', 'Unknown'),
                        section_title=metadata.get('section_title', 'Unknown'),
                        text=metadata.get('text', 'No text available')
                    )
                )
                matches.append(document_match)
                
            except KeyError as e:
                logger.error(f"Missing expected field in match: {e}")
                continue
                
        return matches
        
    except Exception as e:
        logger.error(f"Error querying vector store: {str(e)}")
        return None