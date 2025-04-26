# app/core/streaming.py
import logging
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List
from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.exception import AppwriteException

# Import necessary functions from refactored modules
from app.core.storage import store_message, update_conversation_timestamp
from app.core.retrieval import query_vector_store
from app.core.context_formatter import format_context_and_extract_sources, construct_llm_prompt, format_history
from app.core.llm_service import call_mistral_streaming, call_gemini_streaming
from app.config.settings import settings
from app.models.schemas import Message

logger = logging.getLogger(__name__)

# --- Configuration ---
HISTORY_FETCH_LIMIT = 10  # How many messages to fetch (format_history will take the last N)

async def generate_streaming_response(
    db: Databases,
    query: str,
    user_id: str,
    conversation_id: str,
    is_anonymous: bool
) -> AsyncGenerator[str, None]:
    """
    Generates a Server-Sent Events (SSE) stream including conversation history.

    Handles retrieval, context formatting, LLM call, and message storage,
    yielding events for different stages and content chunks.

    Args:
        db: Appwrite Databases service instance.
        query: The user's query.
        user_id: The user's ID (can be anonymous).
        conversation_id: The conversation ID (can be anonymous).
        is_anonymous: Flag indicating if the user is anonymous.

    Yields:
        str: SSE formatted strings (e.g., "event: <type>\ndata: <json>\n\n").
    """
    full_response_content = ""
    final_sources = []
    model_used = "none"
    fallback_used = False
    error_detail = None
    message_id = None  # To store the ID of the AI's response message
    history_text = "No history fetched."  # Default

    try:
        # 0. Fetch Conversation History (if not anonymous and conversation_id exists)
        conversation_messages: List[Message] = []
        if not is_anonymous and conversation_id:
            try:
                logger.debug(f"Streaming: Fetching ALL history for conversation {conversation_id}")  # <<< Log change
                history_result = db.list_documents(
                    database_id=settings.APPWRITE_DATABASE_ID,
                    collection_id=settings.APPWRITE_MESSAGES_COLLECTION_ID,
                    queries=[
                        Query.equal("conversation_id", conversation_id),
                        Query.order_desc("timestamp"),
                        # Query.limit(HISTORY_FETCH_LIMIT)  # <<< REMOVED LIMIT
                    ]
                )
                raw_docs = history_result.get('documents', [])[::-1]
                for doc in raw_docs:
                    try:
                        conversation_messages.append(Message(
                            message_id=doc.get('$id'), conversation_id=doc.get('conversation_id'),
                            user_id=doc.get('user_id'), content=doc.get('content'),
                            message_type=doc.get('message_type'), timestamp=doc.get('timestamp'),
                            sources=doc.get('sources', [])
                        ))
                    except Exception as pydantic_error:
                        logger.warning(f"Streaming: Pydantic validation failed for history doc ID {doc.get('$id')}: {pydantic_error}")

                history_text = format_history(conversation_messages)
                logger.debug(f"Streaming: Formatted History (first 200 chars): {history_text[:200]}...")

            except AppwriteException as e:
                logger.error(f"Streaming: Appwrite error fetching history for conversation {conversation_id}: {e.message}")
                error_detail = "Failed to fetch conversation history."
                yield f"event: error\ndata: {json.dumps({'detail': error_detail})}\n\n"
            except Exception as e:
                logger.exception(f"Streaming: Unexpected error fetching history for conversation {conversation_id}: {e}")
                error_detail = "Unexpected error fetching history."
                yield f"event: error\ndata: {json.dumps({'detail': error_detail})}\n\n"

        # 1. Initial thinking event & Store User Message
        yield "event: thinking\ndata: {}\n\n"
        try:
            user_message = store_message(db, user_id, query, "user", conversation_id, is_anonymous=is_anonymous)
            logger.info(f"Streaming: Stored user message (ID: {user_message.get('message_id', 'N/A')}) for conversation {conversation_id}")
            if not is_anonymous and conversation_id:
                update_conversation_timestamp(db, conversation_id)
        except Exception as store_err:
            logger.error(f"Streaming: Failed to store user message for conversation {conversation_id}: {store_err}")
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to save your message.'})}\n\n"

        # 2. Retrieval Stage
        yield "event: retrieving\ndata: {}\n\n"
        documents = None
        try:
            documents = query_vector_store(query_text=query, top_k=settings.RETRIEVAL_TOP_K)
            if not documents:
                logger.warning(f"Streaming: No documents retrieved for query in conversation {conversation_id}")
                documents = []
            else:
                logger.info(f"Streaming: Retrieved {len(documents)} documents for conversation {conversation_id}")
        except Exception as retrieval_err:
            logger.error(f"Streaming: Error during vector store query for conversation {conversation_id}: {retrieval_err}")
            error_detail = f"Retrieval error: {retrieval_err}"
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to retrieve information.'})}\n\n"
            error_response = "I'm having trouble finding relevant information right now."
            try:
                store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception:
                pass
            yield f"event: content\ndata: {json.dumps({'text': error_response})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        # 3. Context Formatting Stage
        yield "event: formatting\ndata: {}\n\n"
        context_text, final_sources = "", []  # Initialize
        try:
            context_text, final_sources = format_context_and_extract_sources(documents)
            logger.debug(f"Streaming: Formatted Context (first 300 chars): {context_text[:300]}")
            if not context_text:
                logger.warning(f"Streaming: Context formatting returned empty text for conversation {conversation_id}")
                context_text = "No relevant context could be formatted."
        except Exception as format_err:
            logger.exception(f"Streaming: Error formatting context for conversation {conversation_id}: {format_err}")
            error_detail = f"Context formatting error: {format_err}"
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to process retrieved information.'})}\n\n"
            error_response = "I encountered an issue processing the information."
            try:
                store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception:
                pass
            yield f"event: content\ndata: {json.dumps({'text': error_response})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        # 4. LLM Generation Stage (Now includes history)
        yield "event: generating\ndata: {}\n\n"
        prompt = construct_llm_prompt(history_text, context_text, query)

        # --- Streaming LLM Call Logic ---
        llm_stream = None
        try:
            logger.info(f"Streaming: Attempting Mistral stream for conversation {conversation_id}")
            llm_stream = call_mistral_streaming(prompt)
            model_used = settings.MISTRAL_MODEL
            logger.info(f"Streaming: Mistral stream initiated for conversation {conversation_id}")

        except Exception as mistral_err:
            logger.error(f"Streaming: Mistral stream initiation failed for conversation {conversation_id}: {mistral_err}")
            llm_stream = None

        # Fallback to Gemini stream if Mistral failed
        if llm_stream is None:
            logger.warning(f"Streaming: Mistral stream failed. Attempting fallback to Gemini stream for conversation {conversation_id}")
            fallback_used = True
            try:
                llm_stream = call_gemini_streaming(prompt)
                model_used = settings.GEMINI_MODEL
                logger.info(f"Streaming: Gemini stream fallback initiated for conversation {conversation_id}")
            except Exception as gemini_err:
                logger.error(f"Streaming: Gemini stream fallback also failed for conversation {conversation_id}: {gemini_err}")
                error_detail = f"Primary LLM stream failed. Fallback LLM stream error: {gemini_err}"
                yield f"event: error\ndata: {json.dumps({'detail': 'LLM is unavailable.'})}\n\n"
                error_response = "I'm currently unable to generate a response. Please try again later."
                try:
                    store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
                except Exception:
                    pass
                yield f"event: content\ndata: {json.dumps({'text': error_response})}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

        # 5. Stream Content Chunks
        if llm_stream:
            try:
                async for chunk in llm_stream:
                    if chunk:
                        full_response_content += chunk
                        yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                logger.info(f"Streaming: Finished consuming LLM stream for conversation {conversation_id}")
            except Exception as stream_err:
                logger.error(f"Streaming: Error consuming LLM stream for conversation {conversation_id}: {stream_err}")
                error_detail = f"LLM stream consumption error: {stream_err}"
                yield f"event: error\ndata: {json.dumps({'detail': 'Error during response generation.'})}\n\n"
        else:
            logger.error(f"Streaming: No LLM stream available after primary and fallback attempts for conversation {conversation_id}")
            error_detail = "LLM stream unavailable."
            yield f"event: error\ndata: {json.dumps({'detail': error_detail})}\n\n"
            error_response = "Failed to connect to the language model."
            try:
                store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception:
                pass
            yield f"event: content\ndata: {json.dumps({'text': error_response})}\n\n"

        # 6. Store AI Message (after streaming content)
        if full_response_content:
            try:
                ai_message = store_message(
                    db=db, user_id="ai", content=full_response_content, message_type="ai",
                    conversation_id=conversation_id, is_anonymous=is_anonymous,
                    sources=final_sources
                )
                message_id = ai_message.get('message_id')
                logger.info(f"Streaming: Stored AI message (ID: {message_id}) for conversation {conversation_id}")
                if not is_anonymous and conversation_id:
                    update_conversation_timestamp(db, conversation_id)
            except Exception as store_err:
                logger.error(f"Streaming: Failed to store AI message for conversation {conversation_id}: {store_err}")
                yield f"event: error\ndata: {json.dumps({'detail': 'Failed to save the full AI response.'})}\n\n"
                if error_detail:
                    error_detail += "; Failed to store AI response."
                else:
                    error_detail = "Failed to store AI response."
        else:
            logger.error(f"Streaming: AI response generation resulted in empty content for conversation {conversation_id}. Final error detail: {error_detail}")

        # 7. Yield Sources
        yield f"event: sources\ndata: {json.dumps(final_sources)}\n\n"
        logger.debug(f"Streaming: Yielded {len(final_sources)} sources for conversation {conversation_id}")

        # 8. Yield Final Metadata (Optional)
        final_data = {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "model_used": model_used,
            "fallback_used": fallback_used,
            "error": error_detail
        }
        yield f"event: final_data\ndata: {json.dumps(final_data)}\n\n"

        # 9. Done Event
        yield "event: done\ndata: {}\n\n"
        logger.info(f"Streaming finished for conversation {conversation_id}")

    except Exception as e:
        logger.exception(f"Critical error in streaming response pipeline for conversation {conversation_id}: {str(e)}")
        try:
            yield f"event: error\ndata: {json.dumps({'detail': f'Critical stream error: {str(e)}'})}\n\n"
            error_response = "A critical error occurred during streaming."
            store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
        except Exception:
            pass
        yield "event: done\ndata: {}\n\n"
