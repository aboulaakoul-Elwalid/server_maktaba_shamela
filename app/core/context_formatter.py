# app/core/context_formatter.py
import logging
from typing import List, Dict, Tuple, Optional
# Assuming DocumentMatch and DocumentMetadata are defined in schemas
from app.models.schemas import DocumentMatch
from app.config.settings import settings # Ensure this import exists

logger = logging.getLogger(__name__)

def format_context_and_extract_sources(
    documents: List[DocumentMatch]
) -> Tuple[str, List[Dict[str, any]]]:
    """
    Formats retrieved documents into context text for LLM and extracts source info.

    Args:
        documents: A list of DocumentMatch objects from the vector store query.

    Returns:
        A tuple containing:
        - context_text (str): Formatted string with document content and source info.
        - sources (List[Dict]): A list of dictionaries, each representing a source document.
    """
    context_text = ""
    sources = []

    if not documents:
        logger.warning("No documents provided for context formatting.")
        return "", []

    logger.debug(f"Formatting context from {len(documents)} documents.")
    try:
        for i, doc in enumerate(documents):
            # --- Metadata Access Fix ---
            # Access attributes directly from the Pydantic model `doc.metadata`
            # Use getattr for safe access with defaults if fields might be missing
            # (though Pydantic validation should ensure they exist if not Optional)
            metadata = doc.metadata # This is a DocumentMetadata object

            # Safely get attributes, providing defaults
            book_name = getattr(metadata, 'book_name', "Unknown book")
            section_title = getattr(metadata, 'section_title', "Unknown section")
            # Use doc.id as fallback if document_id isn't explicitly in metadata
            doc_id = getattr(metadata, 'document_id', doc.id)
            # Get the actual text content
            doc_text = getattr(metadata, 'text', "No text available")

            # --- Build Context String ---
            context_text += f"\n--- Document {i+1} (ID: {doc_id}) ---\n"
            context_text += f"Source: {book_name} - {section_title}\n"
            context_text += f"Content:\n{doc_text}\n"
            # context_text += f"Relevance Score: {doc.score:.4f}\n" # Optional: include score

            # --- Extract Source Information ---
            sources.append({
                "book_name": book_name,
                "section_title": section_title,
                "text_snippet": doc_text[:150] + "..." if len(doc_text) > 150 else doc_text, # Create snippet
                "relevance": doc.score,
                "document_id": doc_id # Use the potentially overridden doc_id
            })

        logger.debug("Successfully formatted context and extracted sources.")
        return context_text.strip(), sources

    except AttributeError as e:
        logger.exception(f"AttributeError during context formatting: {e}. Check DocumentMetadata schema and retrieval results.")
        # Depending on desired behavior, could return partial results or raise error
        error_context = "Error: Could not format context due to missing metadata attribute."
        return error_context, [] # Return empty sources on error
    except Exception as e:
        logger.exception(f"Unexpected error formatting context: {str(e)}")
        # Return error message in context and empty sources
        error_context = f"Error: An unexpected error occurred while formatting context: {e}"
        return error_context, []

def construct_llm_prompt(context_text: str, query: str) -> str:
    """
    Constructs the final prompt string to be sent to the LLM.

    Args:
        context_text: The formatted context string from retrieved documents.
        query: The user's original query.

    Returns:
        The complete prompt string.
    """
    # Use the template from settings
    prompt = settings.PROMPT_TEMPLATE.format(context_text=context_text, query=query)
    logger.debug(f"Constructed LLM Prompt (start): {prompt[:200]}...")
    return prompt
