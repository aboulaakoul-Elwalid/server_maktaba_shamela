# app/core/streaming.py
import logging
import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from appwrite.services.databases import Databases

# Import necessary functions from refactored modules
from app.core.storage import store_message, update_conversation_timestamp
from app.core.retrieval import query_vector_store
from app.core.context_formatter import format_context_and_extract_sources, construct_llm_prompt
from app.core.llm_service import call_mistral_with_retry, call_gemini_api

logger = logging.getLogger(__name__)

async def generate_streaming_response(
    db: Databases,
    query: str,
    user_id: str,
    conversation_id: str,
    is_anonymous: bool
) -> AsyncGenerator[str, None]:
    """
    Generates a Server-Sent Events (SSE) stream for a RAG response.

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
    message_id = None # To store the ID of the AI's response message

    try:
        # 1. Initial thinking event & Store User Message
        yield "event: thinking\ndata: {}\n\n"
        try:
            # Store user message (important for history, even if RAG fails later)
            # For anonymous, this returns a dict but doesn't hit DB
            user_message = store_message(db, user_id, query, "user", conversation_id, is_anonymous=is_anonymous)
            logger.info(f"Stored user message (ID: {user_message.get('message_id', 'N/A')}) for conversation {conversation_id}")
            # Update conversation timestamp after user message
            if not is_anonymous:
                 update_conversation_timestamp(db, conversation_id)
        except Exception as store_err:
            logger.error(f"Failed to store user message for conversation {conversation_id}: {store_err}")
            # Decide if we should stop or continue; continuing might be better UX
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to save your message.'})}\n\n"
            # We might still try to generate a response

        # 2. Retrieval Stage
        yield "event: retrieving\ndata: {}\n\n"
        documents = None
        try:
            documents = query_vector_store(query_text=query, top_k=5) # Make top_k configurable?
            logger.info(f"Retrieved {len(documents) if documents else 0} documents for conversation {conversation_id}")
        except Exception as retrieval_err:
            logger.error(f"Error during vector store query for conversation {conversation_id}: {retrieval_err}")
            error_detail = f"Retrieval error: {retrieval_err}"
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to retrieve information.'})}\n\n"
            # Attempt to store an error message and end
            error_response = "I'm having trouble finding relevant information right now."
            try:
                store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception: pass # Ignore storage error here
            yield f"event: content\ndata: {json.dumps({'text': error_response})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return # Stop processing

        if not documents:
            logger.warning(f"No relevant documents found for query in conversation {conversation_id}")
            no_docs_response = "I couldn't find specific information about that topic in my knowledge base."
            try:
                store_message(db, "ai", no_docs_response, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception: pass
            yield f"event: content\ndata: {json.dumps({'text': no_docs_response})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return # Stop processing

        # 3. Context Formatting Stage
        yield "event: formatting\ndata: {}\n\n" # Added formatting event
        try:
            context_text, sources_for_llm = format_context_and_extract_sources(documents)
            final_sources = sources_for_llm # Store for later yielding and saving
            if not context_text: # Handle case where formatting failed internally
                 raise ValueError("Context formatting returned empty text.")
            logger.debug(f"Context formatted for conversation {conversation_id}")
        except Exception as format_err:
            logger.error(f"Error formatting context for conversation {conversation_id}: {format_err}")
            error_detail = f"Context formatting error: {format_err}"
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to process retrieved information.'})}\n\n"
            error_response = "I'm having trouble processing the information for your question."
            try:
                store_message(db, "ai", error_response, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception: pass
            yield f"event: content\ndata: {json.dumps({'text': error_response})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return # Stop processing

        # 4. LLM Generation Stage
        yield "event: generating\ndata: {}\n\n"
        prompt = construct_llm_prompt(context_text, query)

        try:
            # Attempt Mistral first
            mistral_response = call_mistral_with_retry(prompt)
            if mistral_response.status_code == 200:
                try:
                    data = mistral_response.json()
                    full_response_content = data["choices"][0]["message"]["content"]
                    model_used = "mistral"
                    logger.info(f"Mistral response received for conversation {conversation_id}")
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.error(f"Error parsing successful Mistral response for {conversation_id}: {e}")
                    error_detail = "Mistral response parsing error"
                    # Fall through to Gemini
            else:
                # Log Mistral failure reason and try Gemini
                fail_reason = mistral_response.reason or f"Status {mistral_response.status_code}"
                fail_body = mistral_response.text[:100] + ('...' if len(mistral_response.text) > 100 else '')
                error_detail = f"Mistral failed ({fail_reason}): {fail_body}"
                logger.warning(f"{error_detail}. Trying Gemini for conversation {conversation_id}...")

            # If Mistral failed or parsing failed, try Gemini
            if model_used != "mistral":
                gemini_result = call_gemini_api(prompt)
                if gemini_result["success"]:
                    full_response_content = gemini_result["content"]
                    model_used = "gemini"
                    fallback_used = True
                    error_detail = None # Clear previous Mistral error if Gemini succeeded
                    logger.info(f"Gemini fallback successful for conversation {conversation_id}")
                else:
                    # Both failed
                    gemini_fail_reason = gemini_result.get('error', 'Unknown Gemini error')
                    logger.error(f"Both Mistral and Gemini failed for {conversation_id}. Gemini error: {gemini_fail_reason}")
                    # Keep the latest error detail (from Gemini)
                    error_detail = f"Gemini fallback failed: {gemini_fail_reason}"
                    full_response_content = f"I apologize, but AI services are experiencing issues. ({error_detail})"

        except Exception as llm_exception:
            logger.exception(f"Exception during LLM call sequence for {conversation_id}: {llm_exception}")
            error_detail = f"LLM call exception: {llm_exception}"
            full_response_content = f"I apologize, but AI services encountered an error. ({error_detail})"

        # 5. Stream Content Chunks
        if full_response_content:
            logger.info(f"Streaming LLM response ({model_used}, fallback: {fallback_used}) for conversation {conversation_id}")
            chunk_size = 50 # Make configurable?
            for i in range(0, len(full_response_content), chunk_size):
                chunk = full_response_content[i:i+chunk_size]
                yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                await asyncio.sleep(0.02) # Small delay for smoother streaming
        else:
            # Should have been handled above, but as a fallback
            logger.error(f"LLM generation resulted in empty content for conversation {conversation_id}")
            full_response_content = "Error: No response content generated."
            yield f"event: content\ndata: {json.dumps({'text': full_response_content})}\n\n"


        # 6. Store AI Message (after streaming content)
        try:
            # Pass the final_sources extracted during formatting
            ai_message = store_message(
                db, "ai", full_response_content, "ai", conversation_id,
                sources=final_sources, is_anonymous=is_anonymous
            )
            message_id = ai_message.get('message_id')
            logger.info(f"Stored AI message (ID: {message_id or 'N/A'}) for conversation {conversation_id}")
            # Update conversation timestamp after AI message
            if not is_anonymous:
                 update_conversation_timestamp(db, conversation_id)
        except Exception as store_err:
            logger.error(f"Failed to store AI message for conversation {conversation_id}: {store_err}")
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to save AI response.'})}\n\n"
            # Continue to yield sources and done event

        # 7. Yield Sources
        yield f"event: sources\ndata: {json.dumps(final_sources)}\n\n"
        logger.debug(f"Yielded {len(final_sources)} sources for conversation {conversation_id}")

        # 8. Yield Final Metadata (Optional)
        final_data = {
            "conversation_id": conversation_id,
            "message_id": message_id, # ID of the stored AI message
            "model_used": model_used,
            "fallback_used": fallback_used,
            "error": error_detail
        }
        yield f"event: final_data\ndata: {json.dumps(final_data)}\n\n"

        # 9. Done Event
        yield "event: done\ndata: {}\n\n"
        logger.info(f"Streaming finished for conversation {conversation_id}")

    except Exception as e:
        # Catch-all for unexpected errors in the stream generation itself
        logger.exception(f"Critical error in streaming response pipeline for conversation {conversation_id}: {str(e)}")
        try:
            # Attempt to yield a final error event
            yield f"event: error\ndata: {json.dumps({'detail': f'An internal streaming error occurred: {e}'})}\n\n"
        except Exception: pass # Ignore if yielding fails
        # Ensure done event is sent even after critical error
        yield "event: done\ndata: {}\n\n"
