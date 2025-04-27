# app/core/rag.py
"""
Retrieval-Augmented Generation (RAG) pipeline module.

This module combines retrieval from the vector database with text generation
to create a complete RAG system. It:
1. Takes a user query
2. Retrieves relevant context from Pinecone
3. Reformats the context for use in a prompt
4. Generates a response using the query + context

Why a separate RAG module?
- Encapsulates the complete RAG flow in one place
- Can be used by multiple endpoints or services
- Separates concerns between retrieval and generation
Enhanced Retrieval-Augmented Generation (RAG) pipeline module.

"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from app.core.retrieval_old import query_vector_store
from app.config.settings import settings
from app.core.embeddings import mistral_client  # Import the already initialized client

logger = logging.getLogger(__name__)

def format_context_for_prompt(matches: List[Dict[str, Any]], query: str) -> str:
    """
    Format retrieved documents into a context string for the LLM prompt.
    
    Args:
        matches: List of document matches from the vector store
        query: Original user query
        
    Returns:
        Formatted context string
    """
    # Organize documents by book for better context
    book_contexts = {}
    
    # Group documents by book
    for i, match in enumerate(matches):
        metadata = match.metadata
        book_name = metadata.book_name
        
        if book_name not in book_contexts:
            book_contexts[book_name] = []
        
        # Format the passage with section title and text
        passage = {
            "section": metadata.section_title,
            "text": metadata.text,
            "score": match.score,
            "document_id": match.id
        }
        book_contexts[book_name].append(passage)
    
    # Format the full context with citation information
    context_parts = []
    citation_idx = 1
    citations = {}
    
    # For Arabic-specific content, we might need to handle right-to-left text
    for book_name, passages in book_contexts.items():
        # Book header
        context_parts.append(f"## {book_name}")
        
        # Sort passages by relevance score
        passages.sort(key=lambda x: x["score"], reverse=True)
        
        # Add each passage with citation markers
        for passage in passages:
            citation_id = f"[{citation_idx}]"
            citation_details = {
                "id": citation_idx,
                "book": book_name,
                "section": passage["section"],
                "document_id": passage["document_id"]
            }
            citations[citation_id] = citation_details
            
            context_parts.append(f"### {passage['section']} {citation_id}")
            context_parts.append(passage["text"])
            context_parts.append("---")
            citation_idx += 1
    
    # Add citation information at the end
    context_parts.append("## Citations")
    for citation_id, details in citations.items():
        context_parts.append(f"{citation_id}: {details['book']}, {details['section']}")
    
    # Format the question to guide the LLM
    prompt_intro = f"""
Please answer this question based only on the provided context:
QUESTION: {query}

CONTEXT:
"""
    
    return prompt_intro + "\n\n".join(context_parts)

async def generate_llm_response(prompt: str) -> str:
    """
    Generate a response using the Mistral LLM API.
    
    Args:
        prompt: The formatted prompt with context
        
    Returns:
        Generated text response
    """
    try:
        if not mistral_client:
            logger.error("Mistral client not initialized")
            return "Error: LLM service is unavailable"
            
        # Call Mistral's chat completion API
        response = mistral_client.chat(
            model="mistral-sabaa",  # or mistral-small/mistral-large based on your needs
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant specializing in Islamic and Arabic texts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower for more factual responses
            max_tokens=1000
        )
        
        # Extract the response text
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}")
        return f"I apologize, but I encountered an error generating a response. Error: {str(e)}"

async def generate_rag_response(
    query: str, 
    top_k: int = 5,
    reranking: bool = True
) -> Dict[str, Any]:
    """
    Generate a response using the enhanced RAG pipeline.
    
    This async function:
    1. Retrieves relevant documents for the query
    2. Reranks results if enabled (placeholder for implementation)
    3. Formats them as context for a prompt
    4. Generates a response using an LLM
    
    Args:
        query: User's question or query
        top_k: Number of documents to retrieve
        reranking: Whether to rerank results (requires implementation)
        
    Returns:
        Dictionary containing the response and context
    """
    logger.info(f"Processing RAG query: {query[:50]}...")
    
    # Step 1: Retrieve relevant documents
    matches = query_vector_store(query, top_k=top_k)
    
    if not matches:
        logger.warning("No relevant documents found for query")
        return {
            "response": "I couldn't find any relevant information to answer your question.",
            "context": [],
            "success": False
        }
    
    # Step 2: Rerank results (placeholder - implement if needed)
    if reranking:
        logger.info("Reranking results (placeholder)")
        # This would reorder matches based on a more sophisticated relevance model
        # For example, using a cross-encoder rather than bi-encoder model
        pass
    
    # Step 3: Format documents as context prompt
    context_prompt = format_context_for_prompt(matches, query)
    
    # Step 4: Generate response with LLM
    try:
        response = await generate_llm_response(context_prompt)
        logger.info("RAG response generated successfully")
        
        return {
            "response": response,
            "context": [
                {
                    "book_name": match.metadata.book_name,
                    "section_title": match.metadata.section_title,
                    "text_snippet": match.metadata.text[:200] + "...",
                    "relevance": match.score,
                    "document_id": match.id
                }
                for match in matches
            ],
            "success": True
        }
    except Exception as e:
        logger.error(f"Error generating RAG response: {e}")
        return {
            "response": "There was an error generating a response to your question.",
            "context": [],
            "success": False,
            "error": str(e)
        }