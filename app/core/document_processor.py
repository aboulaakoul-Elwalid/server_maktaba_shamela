# app/core/document_processor.py (new file)
"""Module for processing documents from the Shamela Library."""

import requests
import re
import hashlib
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional
import logging
# ... other imports ...

logger = logging.getLogger(__name__)

def fetch_document(url: str) -> Optional[str]:
    """
    Fetch document content from URL.
    
    Args:
        url: URL of the document to fetch
        
    Returns:
        Document content as text or None if fetch fails
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch document from {url}: {e}")
        return None

def extract_shamela_metadata(content: str) -> Dict[str, str]:
    """
    Extract metadata specific to Shamela Library documents.
    
    Args:
        content: HTML content of the document
        
    Returns:
        Dictionary of metadata
    """
    soup = BeautifulSoup(content, 'html.parser')
    metadata = {}
    
    # Extract book name
    book_name_elem = soup.select_one('.book-title')
    if book_name_elem:
        metadata["book_name"] = book_name_elem.text.strip()
    
    # Extract author
    author_elem = soup.select_one('.author-name')
    if author_elem:
        metadata["author"] = author_elem.text.strip()
    
    # Extract publication date
    pub_date_elem = soup.select_one('.publication-date')
    if pub_date_elem:
        metadata["publication_date"] = pub_date_elem.text.strip()
    
    # Extract categories/topics
    topics = []
    topic_elems = soup.select('.category-tag')
    for elem in topic_elems:
        topics.append(elem.text.strip())
    if topics:
        metadata["topics"] = ", ".join(topics)
    
    return metadata

def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks of approximately max_chunk_size characters.
    
    Args:
        text: Text to split
        max_chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Clean text - remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # If text is short, return it as is
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Get chunk of max_chunk_size or remainder
        end = min(start + max_chunk_size, len(text))
        
        # Try to find a sentence boundary to end on
        if end < len(text):
            # Look for sentence ending punctuation followed by space
            # within the last 200 characters of the chunk
            search_from = max(end - 200, start + 200)  # Don't search too close to start
            search_text = text[search_from:end]
            
            # Find last occurrence of sentence boundary
            sentence_end = max(
                search_text.rfind('. '),
                search_text.rfind('! '),
                search_text.rfind('? '),
                search_text.rfind('.\n'),
                search_text.rfind('!\n'),
                search_text.rfind('?\n')
            )
            
            if sentence_end != -1:
                end = search_from + sentence_end + 2  # Include the punctuation and space
        
        # Add chunk
        chunks.append(text[start:end].strip())
        
        # Move to next chunk with overlap
        start = end - overlap
    
    return chunks

def generate_stable_document_id(url: str, metadata: Dict[str, str]) -> str:
    """
    Generate a stable document ID based on URL and important metadata.
    
    Args:
        url: Document URL
        metadata: Document metadata
        
    Returns:
        Stable document ID
    """
    # Use URL path as base for ID
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    # Create a string combining important metadata
    id_parts = [
        path_parts[-1] if path_parts else "unknown",
        metadata.get("book_name", ""),
        metadata.get("section_title", "")
    ]
    
    # Create a hash from the combined parts
    id_string = "_".join([part for part in id_parts if part])
    return f"shamela_{hashlib.sha256(id_string.encode()).hexdigest()[:24]}"

def process_document(url: str) -> Tuple[Optional[List[Dict]], Optional[Dict]]:
    """
    Process a document from URL to chunks with embeddings.
    
    Args:
        url: Document URL
        
    Returns:
        Tuple of (document_chunks, metadata) or (None, None) if processing fails
    """
    # Fetch document
    content = fetch_document(url)
    if not content:
        return None, None
    
    # Extract metadata
    metadata = extract_shamela_metadata(content)
    
    # Extract main text
    soup = BeautifulSoup(content, 'html.parser')
    main_content = soup.select_one('.main-content')
    if not main_content:
        logger.error(f"Could not find main content in document: {url}")
        return None, None
    
    text = main_content.get_text(strip=True)
    
    # Chunk text
    chunks = chunk_text(text)
    
    # Prepare result with stable IDs
    base_id = generate_stable_document_id(url, metadata)
    result = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"{base_id}_{i:03d}"
        chunk_metadata = {
            **metadata,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "text": chunk,
            "source_url": url
        }
        result.append({
            "id": chunk_id,
            "text": chunk,
            "metadata": chunk_metadata
        })
    
    return result, metadata