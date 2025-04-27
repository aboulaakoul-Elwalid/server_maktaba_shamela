# app/core/chat_service.py
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.exception import AppwriteException

# Import necessary functions from refactored modules
from app.core.storage import store_message, update_conversation_timestamp
from app.core.retrieval import get_retriever, Retriever  # Use the new retrieval package
from app.core.context_formatter import format_context_and_extract_sources, construct_llm_prompt, format_history
from app.core.llm_service import call_mistral_with_retry, call_gemini_api
from app.config.settings import settings
from app.models.schemas import Message, DocumentMatch

logger = logging.getLogger(__name__)

# --- Configuration ---
HISTORY_FETCH_LIMIT = 10  # How many messages to fetch (format_history will take the last N)

async def generate_rag_response(
    db: Databases,
    query: str,
    user_id: str,
    conversation_id: str,
    is_anonymous: bool
) -> Dict[str, Any]:
    """
    Orchestrates the RAG pipeline including conversation history.

    1. Fetches conversation history.
    2. Stores the user message.
    3. Retrieves relevant documents.
    4. Formats context and extracts sources.
    5. Calls LLM (Mistral with Gemini fallback).
    6. Stores the AI response.
    7. Returns the response and sources.

    Args:
        db: Appwrite Databases service instance.
        query: The user's query.
        user_id: The user's ID (can be anonymous).
        conversation_id: The conversation ID (can be anonymous).
        is_anonymous: Flag indicating if the user is anonymous.

    Returns:
        Dict containing the AI response, sources, and metadata.
    """
    ai_response_content = "Error: Could not generate response."
    final_sources = []
    model_used = "none"
    fallback_used = False
    error_detail = None
    ai_message_id = None
    history_text = "No history fetched."  # Default

    try:
        # 0. Fetch Conversation History (if not anonymous and conversation_id exists)
        conversation_messages: List[Message] = []
        if not is_anonymous and conversation_id:
            try:
                logger.debug(f"Fetching ALL history for conversation {conversation_id}")  # Log change
                history_result = db.list_documents(
                    database_id=settings.APPWRITE_DATABASE_ID,
                    collection_id=settings.APPWRITE_MESSAGES_COLLECTION_ID,
                    queries=[
                        Query.equal("conversation_id", conversation_id),
                        Query.order_desc("timestamp"),  # Fetch newest first
                        # Query.limit(HISTORY_FETCH_LIMIT)  # REMOVED LIMIT
                    ]
                )
                # Map Appwrite docs to Pydantic models (reverse order for correct chronology)
                raw_docs = history_result.get('documents', [])[::-1]  # Reverse to get oldest first
                for doc in raw_docs:
                    try:
                        # Basic mapping, assuming schema matches Message fields
                        conversation_messages.append(Message(
                            message_id=doc.get('$id'),
                            conversation_id=doc.get('conversation_id'),
                            user_id=doc.get('user_id'),
                            content=doc.get('content'),
                            message_type=doc.get('message_type'),
                            timestamp=doc.get('timestamp'),
                            sources=doc.get('sources', [])  # Handle potential missing sources
                        ))
                    except Exception as pydantic_error:
                        logger.warning(f"Pydantic validation failed for history doc ID {doc.get('$id')}: {pydantic_error}")
                        # Optionally skip invalid messages

                history_text = format_history(conversation_messages)
                logger.debug(f"Formatted History (first 200 chars): {history_text[:200]}...")

            except AppwriteException as e:
                logger.error(f"Appwrite error fetching history for conversation {conversation_id}: {e.message}")
                # Continue without history, maybe set error detail?
                error_detail = "Failed to fetch conversation history."
            except Exception as e:
                logger.exception(f"Unexpected error fetching history for conversation {conversation_id}: {e}")
                error_detail = "Unexpected error fetching history."

        # 1. Store User Message
        try:
            user_message = store_message(
                db=db, user_id=user_id, content=query, message_type="user",
                conversation_id=conversation_id, is_anonymous=is_anonymous
            )
            logger.info(f"Stored user message (ID: {user_message.get('message_id', 'N/A')}) for conversation {conversation_id}")
            # Update conversation timestamp after user message
            if not is_anonymous and conversation_id:
                update_conversation_timestamp(db, conversation_id)
        except Exception as store_err:
            logger.error(f"Failed to store user message for conversation {conversation_id}: {store_err}")
            # Decide if we should stop or continue; continuing might be better UX

        # 2. Retrieve Documents using the new retriever
        logger.debug(f"Retrieving documents for query: {query[:50]}...")
        documents: Optional[List[DocumentMatch]] = None
        try:
            retriever: Retriever = get_retriever()  # Get the configured retriever instance
            documents = await retriever.retrieve(query=query, top_k=settings.RETRIEVAL_TOP_K)
            if not documents:
                logger.warning(f"No documents retrieved for query in conversation {conversation_id}")
                documents = []  # Ensure it's an empty list for formatting
            else:
                logger.info(f"Retrieved {len(documents)} documents for conversation {conversation_id}")
        except Exception as e:
            logger.exception(f"Error during vector store retrieval for conversation {conversation_id}: {str(e)}")
            error_detail = f"Retrieval error: {e}"
            ai_response_content = "I'm having trouble finding relevant information right now."
            try:
                store_message(db, "ai", ai_response_content, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception:
                pass
            return {"response": ai_response_content, "sources": [], "error_detail": error_detail}

        # 3. Format Context & Extract Sources
        logger.debug(f"Formatting context for conversation {conversation_id}")
        context_text, final_sources = format_context_and_extract_sources(documents)
        logger.debug(f"Formatted Context Text (first 300 chars):\n{context_text[:300]}")

        # 4. Construct Prompt (Now includes history) and Call LLM
        prompt = construct_llm_prompt(history_text, context_text, query)
        logger.info(f"Attempting LLM call (Mistral first) for conversation {conversation_id}...")
        try:
            # Attempt Mistral
            mistral_response = call_mistral_with_retry(prompt)
            if mistral_response.status_code == 200:
                try:
                    data = mistral_response.json()
                    if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
                        ai_response_content = data["choices"][0]["message"]["content"]
                        model_used = settings.MISTRAL_MODEL
                        logger.info(f"Mistral response successful for conversation {conversation_id}")
                    else:
                        logger.error(f"Invalid Mistral response structure for conversation {conversation_id}: {data}")
                        error_detail = "Invalid response structure from primary LLM."
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to decode Mistral JSON response for conversation {conversation_id}: {json_err}")
                    error_detail = "Failed to parse primary LLM response."

            # If Mistral failed (non-200 status or parsing error), try Gemini
            if model_used == "none":
                logger.warning(f"Mistral call failed (Status: {mistral_response.status_code if mistral_response else 'N/A'}). Attempting fallback to Gemini for conversation {conversation_id}")
                fallback_used = True
                gemini_result = call_gemini_api(prompt)
                if gemini_result.get("success"):
                    ai_response_content = gemini_result["content"]
                    model_used = settings.GEMINI_MODEL
                    logger.info(f"Gemini fallback successful for conversation {conversation_id}")
                else:
                    logger.error(f"Gemini fallback also failed for conversation {conversation_id}. Error: {gemini_result.get('error', 'Unknown Gemini error')}")
                    error_detail = f"Primary LLM failed. Fallback LLM error: {gemini_result.get('error', 'Unknown')}"

        except Exception as llm_exception:
            logger.exception(f"Unhandled exception during LLM calls for conversation {conversation_id}: {llm_exception}")
            error_detail = f"LLM processing error: {llm_exception}"

        # 5. Store AI Message
        if ai_response_content and not ai_response_content.startswith("Error:"):
            try:
                ai_message = store_message(
                    db=db, user_id="ai", content=ai_response_content, message_type="ai",
                    conversation_id=conversation_id, is_anonymous=is_anonymous,
                    sources=final_sources
                )
                ai_message_id = ai_message.get('message_id')
                logger.info(f"Stored AI message (ID: {ai_message_id}) for conversation {conversation_id}")
                if not is_anonymous and conversation_id:
                    update_conversation_timestamp(db, conversation_id)
            except Exception as store_err:
                logger.error(f"Failed to store AI message for conversation {conversation_id}: {store_err}")
                if error_detail:
                    error_detail += "; Failed to store AI response."
                else:
                    error_detail = "Failed to store AI response."
        else:
            logger.error(f"AI response generation failed for conversation {conversation_id}. Final error detail: {error_detail}")

        # 6. Return result
        return {
            "response": ai_response_content,
            "sources": final_sources,
            "conversation_id": conversation_id,
            "ai_message_id": ai_message_id,
            "model_used": model_used,
            "fallback_used": fallback_used,
            "error_detail": error_detail
        }

    except Exception as e:
        logger.exception(f"Critical error in RAG pipeline for conversation {conversation_id}: {str(e)}")
        return {
            "response": "An unexpected critical error occurred.",
            "sources": [],
            "conversation_id": conversation_id,
            "ai_message_id": None,
            "model_used": "none",
            "fallback_used": False,
            "error_detail": f"Critical pipeline error: {str(e)}"
        }

async def generate_streaming_response(
    db: Databases,
    query: str,
    user_id: str,
    conversation_id: str,
    is_anonymous: bool
):
    """
    Orchestrates the RAG pipeline for a streaming response.

    Args:
        db: Appwrite Databases service instance.
        query: The user's query.
        user_id: The user's ID (can be anonymous).
        conversation_id: The conversation ID (can be anonymous).
        is_anonymous: Flag indicating if the user is anonymous.

    Yields:
        Streaming chunks of the AI response.
    """
    try:
        documents = query_vector_store(query_text=query, top_k=settings.RETRIEVAL_TOP_K)
        full_response_content = "Generated response content based on documents."
        if full_response_content:
            logger.info(f"Streaming response for conversation {conversation_id}.")
            chunk_size = settings.STREAM_CHUNK_SIZE
            for i in range(0, len(full_response_content), chunk_size):
                chunk = full_response_content[i:i+chunk_size]
                yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                await asyncio.sleep(settings.STREAM_CHUNK_DELAY)
    except Exception as e:
        logger.exception(f"Error in streaming response for conversation {conversation_id}: {str(e)}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"