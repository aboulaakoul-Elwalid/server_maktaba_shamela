# app/core/context_formatter.py
import logging
from typing import List, Dict, Tuple, Optional
# Assuming DocumentMatch and DocumentMetadata are defined in schemas
from app.models.schemas import DocumentMatch, Message
from app.config.settings import settings

logger = logging.getLogger(__name__)

# --- Configuration ---
CONTEXT_SNIPPET_MAX_LENGTH = 300 # Max characters per document snippet in context
HISTORY_MAX_MESSAGES = 6 # Max number of recent messages to include

# --- New History Formatter ---
def format_history(messages: List[Message]) -> str:
    """Formats recent conversation messages into a string for the LLM prompt."""
    if not messages:
        return "No previous conversation history."

    history_lines = []
    # Take the most recent messages up to the limit
    recent_messages = messages[-HISTORY_MAX_MESSAGES:]
    for msg in recent_messages:
        role = "User" if msg.message_type == "user" else "Assistant"
        history_lines.append(f"{role}: {msg.content}")

    return "\n".join(history_lines)

# --- Updated Context Formatter ---
def format_context_and_extract_sources(
    documents: List[DocumentMatch]
) -> Tuple[str, List[Dict[str, any]]]:
    """
    Formats retrieved documents into context text for LLM and extracts source info.
    Limits text snippet length and generates source URLs.
    """
    context_parts = []
    sources = []

    if not documents:
        logger.warning("No documents provided for context formatting.")
        return "No relevant context found.", []

    logger.debug(f"Formatting context from {len(documents)} documents.")
    try:
        for i, doc in enumerate(documents):
            metadata = doc.metadata
            doc_id = doc.id # This is the section_id like "6315_0_6_0_116"

            # Extract book_id (assuming format "bookid_...")
            book_id = doc_id.split('_')[0] if '_' in doc_id else None
            source_url = f"https://shamela.ws/book/{book_id}" if book_id else None

            # Limit the text snippet length
            text_snippet = metadata.text[:CONTEXT_SNIPPET_MAX_LENGTH]
            if len(metadata.text) > CONTEXT_SNIPPET_MAX_LENGTH:
                text_snippet += "..."

            # Format for the prompt context
            context_parts.append(
                f"Source Document [ID: {doc_id}]\n"
                f"Book: {metadata.book_name}\n"
                f"Section: {metadata.section_title}\n"
                f"Content: {text_snippet}\n---\n"
            )

            # Store structured source info
            sources.append({
                "document_id": doc_id,
                "book_id": book_id,
                "book_name": metadata.book_name,
                "section_title": metadata.section_title,
                "score": doc.score,
                "url": source_url
                # Add 'text': text_snippet here if needed in the final API response sources
            })

        context_text = "\n".join(context_parts)
        logger.debug("Successfully formatted context and extracted sources.")
        return context_text, sources

    except AttributeError as e:
        logger.exception(f"AttributeError during context formatting: {e}. Check DocumentMetadata schema and retrieval results.")
        error_context = "Error: Could not format context due to missing metadata attribute."
        return error_context, [] # Return empty sources on error
    except Exception as e:
        logger.exception(f"Unexpected error formatting context: {str(e)}")
        error_context = f"Error: An unexpected error occurred while formatting context: {e}"
        return error_context, []

# --- Updated Prompt Constructor ---
def construct_llm_prompt(history_text: str, context_text: str, query: str) -> str:
    """
    Constructs the final prompt string including history, context, and query.
    """
    # Use the template from settings, now including history
    prompt = settings.PROMPT_TEMPLATE.format(
        history=history_text,
        context_text=context_text,
        query=query
    )
    logger.debug(f"Constructed LLM Prompt (start): {prompt[:300]}...") # Log more chars
    return prompt
