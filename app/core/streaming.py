# app/core/streaming.py
import logging
import json
import asyncio
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.exception import AppwriteException

# Import necessary functions from refactored modules
from app.core.storage import store_message, update_conversation_timestamp, create_new_conversation
from app.core.retrieval import get_retriever, Retriever
from app.core.context_formatter import format_context_and_extract_sources, construct_llm_prompt, format_history
from app.core.llm_service import call_mistral_streaming, call_gemini_streaming
from app.config.settings import settings
from app.models.schemas import Message, DocumentMatch, HistoryMessage, MessageCreate
from app.api.auth_utils import UserResponse
from app.core.chat_service import format_frontend_history

logger = logging.getLogger(__name__)

# --- Configuration ---
HISTORY_FETCH_LIMIT = 10  # How many messages to fetch (format_history will take the last N)

async def generate_streaming_response(
    db: Databases,
    message: MessageCreate,
    user_id: str,
    conversation_id: str,
    is_anonymous: bool
) -> AsyncGenerator[str, None]:
    """
    Generates a Server-Sent Events (SSE) stream for the RAG response,
    including conversation history and using the refactored retriever.

    Args:
        db: Appwrite Databases service instance.
        message: The user's message object.
        user_id: The user ID.
        conversation_id: The conversation ID (can be a temporary ID for anonymous users).
        is_anonymous: Boolean indicating if the user is anonymous.

    Yields:
        Server-Sent Events formatted strings.
    """
    query = message.content
    full_ai_response = ""
    final_sources = []
    stored_user_message_id = None
    stored_ai_message_id = None
    history_text = "No history available."

    try:
        # --- Conditional: Fetch/Use History ---
        conversation_messages: List[Message] = []
        if not is_anonymous and conversation_id:
            try:
                logger.debug(f"Fetching history for authenticated stream {conversation_id}")
                # Fetch conversation history logic here
                history_text = format_history(conversation_messages)
                logger.debug(f"Stream History Formatted (first 200 chars): {history_text[:200]}...")
            except Exception as history_err:
                logger.error(f"Error fetching history for stream {conversation_id}: {history_err}")

        elif is_anonymous and message.history:
            try:
                history_text = format_frontend_history(message.history)
                logger.debug(f"Stream: Using frontend-provided history for anonymous user.")
            except Exception as format_err:
                logger.error(f"Stream: Error formatting frontend history: {format_err}")
        elif is_anonymous:
            logger.debug("Stream: Anonymous user with no history provided by frontend.")

        # --- Conditional: Store User Message ---
        if not is_anonymous:
            try:
                user_msg_result = store_message(
                    db=db,
                    user_id=user_id,
                    content=query,
                    message_type="user",
                    conversation_id=conversation_id,
                    is_anonymous=False
                )
                stored_user_message_id = user_msg_result.get("message_id")
                logger.info(f"Stored user message {stored_user_message_id} for stream.")
                update_conversation_timestamp(db, conversation_id)
            except Exception as store_err:
                logger.error(f"Failed to store user message for stream user {user_id}: {store_err}")
        else:
            logger.debug(f"Skipping user message storage for anonymous stream.")

        # --- Core RAG Logic (Retrieval, Formatting, LLM Stream) ---
        retriever: Retriever = get_retriever()
        retrieved_docs = await retriever.retrieve(query=query, top_k=settings.RETRIEVAL_TOP_K)

        context_string, sources_for_llm = format_context_and_extract_sources(retrieved_docs)
        final_sources = sources_for_llm

        prompt = construct_llm_prompt(history_text, context_string, query)
        logger.info(f"Attempting LLM stream...")

        llm_stream: Optional[AsyncGenerator[str, None]] = None
        try:
            llm_stream = call_mistral_streaming(prompt)
        except Exception as mistral_err:
            logger.error(f"Mistral stream initiation failed: {mistral_err}")
            llm_stream = None

        if llm_stream is None:
            try:
                llm_stream = call_gemini_streaming(prompt)
            except Exception as gemini_err:
                logger.error(f"Gemini stream fallback also failed: {gemini_err}")
                yield f"event: error\ndata: {json.dumps({'detail': 'LLM is unavailable.'})}\n\n"
                yield "event: end\ndata: [DONE]\n\n"
                return

        async for chunk in llm_stream:
            if chunk:
                full_ai_response += chunk
                yield f"event: chunk\ndata: {json.dumps({'token': chunk})}\n\n"

        yield f"event: sources\ndata: {json.dumps(final_sources)}\n\n"

        # --- Conditional: Store AI Message & Yield AI Message ID ---
        if full_ai_response and not full_ai_response.startswith("Error:"):
            if not is_anonymous:
                try:
                    ai_msg_result = store_message(
                        db=db,
                        user_id="ai",
                        content=full_ai_response,
                        message_type="ai",
                        conversation_id=conversation_id,
                        sources=final_sources,
                        is_anonymous=False
                    )
                    stored_ai_message_id = ai_msg_result.get("message_id")
                    logger.info(f"Stored AI message {stored_ai_message_id} for stream.")
                    yield f"event: message_id\ndata: {json.dumps({'message_id': stored_ai_message_id})}\n\n"
                    update_conversation_timestamp(db, conversation_id)
                except Exception as store_err:
                    logger.error(f"Failed to store AI message for stream: {store_err}")
            else:
                logger.debug(f"Skipping AI message storage for anonymous stream.")

    except Exception as e:
        logger.exception(f"Error during streaming response generation: {e}")
        yield f"event: error\ndata: {json.dumps({'detail': 'An error occurred during streaming.'})}\n\n"
    finally:
        yield "event: end\ndata: [DONE]\n\n"
