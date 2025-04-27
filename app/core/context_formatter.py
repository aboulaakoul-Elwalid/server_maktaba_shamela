# app/core/context_formatter.py
import logging
from typing import List, Dict, Tuple, Any
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
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Formats retrieved documents into context text for LLM and extracts source info,
    including the text snippet for storage and API response.
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
            doc_id = doc.id

            # Ensure metadata and text exist
            if not metadata or not hasattr(metadata, 'text') or not metadata.text:
                logger.warning(f"Skipping document {doc_id} due to missing metadata or text.")
                continue # Skip this document

            logger.debug(f"Processing doc ID: {doc_id}, Metadata Text (first 100 chars): '{metadata.text[:100]}'")

            # Extract book_id and generate URL
            book_id = metadata.book_id or (doc_id.split('_')[0] if '_' in doc_id else None)
            source_url = f"https://shamela.ws/book/{book_id}" if book_id else None

            # Limit the text snippet length
            raw_text = metadata.text
            text_snippet = raw_text[:CONTEXT_SNIPPET_MAX_LENGTH]
            if len(raw_text) > CONTEXT_SNIPPET_MAX_LENGTH:
                text_snippet += "..."

            # Format for the prompt context (context_parts)
            context_parts.append(
                f"Source Document [ID: {doc_id}]\n"
                f"Book: {metadata.book_name or 'Unknown'}\n"
                f"Section: {metadata.section_title or 'Unknown'}\n"
                f"Content: {text_snippet}\n---\n"
            )

            # Store structured source info for storage/API (sources list)
            sources.append({
                "document_id": doc_id,
                "book_id": book_id,
                "book_name": metadata.book_name,
                "title": metadata.section_title,
                "score": doc.score,
                "url": source_url,
                "content": text_snippet
            })

        context_text = "\n".join(context_parts)
        logger.debug("Successfully formatted context and extracted sources.")
        if sources:
            logger.debug(f"Sample source item structure: {sources[0]}")
        return context_text, sources

    except AttributeError as e:
        logger.exception(f"AttributeError during context formatting: {e}. Check DocumentMatch structure.")
        return "Error formatting context due to missing attribute.", []
    except Exception as e:
        logger.exception(f"Unexpected error during context formatting: {e}")
        return "Error formatting context.", []

# --- Updated Prompt Constructor ---
def construct_llm_prompt(history_text: str, context_text: str, query: str) -> str:
    """
    Constructs the final prompt string including history, context, and query.
    """
    prompt = settings.PROMPT_TEMPLATE.format(
        history=history_text,
        context_text=context_text,
        query=query
    )
    logger.debug(f"Constructed LLM Prompt (start): {prompt[:300]}...")
    return prompt
