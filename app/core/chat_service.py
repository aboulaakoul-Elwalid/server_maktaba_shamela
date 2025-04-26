# app/core/chat_service.py
import logging
import json
import asyncio
from typing import Dict, Any
from fastapi import HTTPException
from appwrite.services.databases import Databases

# Import necessary functions from refactored modules
from app.core.storage import store_message, update_conversation_timestamp
from app.core.retrieval import query_vector_store
from app.core.context_formatter import format_context_and_extract_sources, construct_llm_prompt
from app.core.llm_service import call_mistral_with_retry, call_gemini_api
from app.config.settings import settings # Ensure this import exists

logger = logging.getLogger(__name__)

async def generate_rag_response(
    db: Databases,
    query: str,
    user_id: str,
    conversation_id: str,
    is_anonymous: bool
) -> Dict[str, Any]:
    """
    Orchestrates the RAG pipeline for a non-streaming response.

    1. Stores the user message.
    2. Retrieves relevant documents.
    3. Formats context and extracts sources.
    4. Calls LLM (Mistral with Gemini fallback).
    5. Stores the AI response.
    6. Returns the response and sources.

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

    try:
        # 1. Store User Message
        try:
            user_message = store_message(
                db=db, user_id=user_id, content=query, message_type="user",
                conversation_id=conversation_id, is_anonymous=is_anonymous
            )
            logger.info(f"Stored user message (ID: {user_message.get('message_id', 'N/A')}) for conversation {conversation_id}")
            # Update conversation timestamp after user message
            if not is_anonymous:
                 update_conversation_timestamp(db, conversation_id)
        except Exception as store_err:
            logger.error(f"Failed to store user message for conversation {conversation_id}: {store_err}")
            # Allow proceeding to generate response, but log the error
            error_detail = f"Failed to store user message: {store_err}"
            # Consider if this should be a hard failure depending on requirements

        # 2. Retrieve Documents
        logger.debug(f"Retrieving documents for query: {query[:50]}...")
        documents = None
        try:
            documents = query_vector_store(query_text=query, top_k=settings.RETRIEVAL_TOP_K) # Use setting
            logger.info(f"Retrieved {len(documents) if documents else 0} documents for conversation {conversation_id}")
        except Exception as e:
            logger.exception(f"Error retrieving documents for conversation {conversation_id}: {str(e)}")
            error_detail = f"Retrieval error: {e}"
            ai_response_content = "I'm having trouble finding relevant information right now. Please try again in a moment."
            # Attempt to store error message before returning
            try:
                store_message(db, "ai", ai_response_content, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception: pass
            return {"response": ai_response_content, "sources": [], "error_detail": error_detail}

        if not documents:
            logger.warning(f"No relevant documents found for query in conversation {conversation_id}")
            ai_response_content = "I couldn't find specific information about that topic in my knowledge base. Could you try rephrasing?"
            try:
                store_message(db, "ai", ai_response_content, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception: pass
            return {"response": ai_response_content, "sources": [], "error_detail": "No documents found"}

        # 3. Format Context and Extract Sources
        logger.debug(f"Formatting context for conversation {conversation_id}")
        try:
            context_text, sources_for_llm = format_context_and_extract_sources(documents)
            final_sources = sources_for_llm # Keep sources for the final response and storage
            if not context_text: # Handle case where formatting failed internally
                 raise ValueError("Context formatting returned empty text.")
        except Exception as e:
            logger.exception(f"Error formatting context for conversation {conversation_id}: {str(e)}")
            error_detail = f"Context formatting error: {e}"
            ai_response_content = "I'm having trouble processing the information for your question. Please try again later."
            try:
                store_message(db, "ai", ai_response_content, "ai", conversation_id, is_anonymous=is_anonymous)
            except Exception: pass
            return {"response": ai_response_content, "sources": [], "error_detail": error_detail}

        # 4. Construct Prompt and Call LLM
        prompt = construct_llm_prompt(context_text, query)
        logger.info(f"Attempting LLM call (Mistral first) for conversation {conversation_id}...")
        try:
            # Attempt Mistral
            mistral_response = call_mistral_with_retry(prompt)
            if mistral_response.status_code == 200:
                try:
                    data = mistral_response.json()
                    # Basic validation of response structure
                    if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
                        ai_response_content = data["choices"][0]["message"]["content"]
                        model_used = "mistral"
                        logger.info(f"Successfully used Mistral response for conversation {conversation_id}.")
                    else:
                        logger.error(f"Unexpected successful Mistral response structure for {conversation_id}: {data}")
                        error_detail = "Mistral JSON structure error"
                        # Fall through to Gemini
                except (json.JSONDecodeError, KeyError, IndexError) as json_err:
                    logger.error(f"Error decoding successful Mistral response for {conversation_id}: {json_err}")
                    error_detail = f"Mistral JSON decode error: {json_err}"
                    # Fall through to Gemini
            else:
                # Log Mistral failure and set error detail before trying Gemini
                mistral_fail_reason = mistral_response.reason or f"Status {mistral_response.status_code}"
                mistral_fail_body = mistral_response.text[:100] + ('...' if len(mistral_response.text) > 100 else '')
                error_detail = f"Mistral failed ({mistral_fail_reason}): {mistral_fail_body}"
                logger.warning(f"{error_detail}. Trying Gemini for conversation {conversation_id}...")

            # If Mistral didn't succeed, try Gemini
            if model_used != "mistral":
                gemini_response = call_gemini_api(prompt)
                if gemini_response["success"]:
                    ai_response_content = gemini_response["content"]
                    model_used = "gemini"
                    fallback_used = True
                    error_detail = None # Clear previous Mistral error if Gemini succeeded
                    logger.info(f"Successfully used Gemini response (fallback) for conversation {conversation_id}.")
                else:
                    # Both failed, keep the latest error (Gemini's)
                    gemini_fail_reason = gemini_response.get('error', 'Unknown Gemini error')
                    logger.error(f"Both Mistral and Gemini failed for {conversation_id}. Gemini error: {gemini_fail_reason}")
                    error_detail = f"Gemini fallback failed: {gemini_fail_reason}"
                    # Use a generic error message if both failed
                    ai_response_content = f"I apologize, but AI services are experiencing issues. Please try again later."

        except Exception as llm_call_exception:
            logger.exception(f"Exception during LLM call sequence for {conversation_id}: {llm_call_exception}")
            error_detail = f"LLM call exception: {llm_call_exception}"
            ai_response_content = f"I apologize, but AI services encountered an error. Please try again later."

        logger.info(f"LLM call finished for {conversation_id}. Model: {model_used}, Fallback: {fallback_used}. Answer length: {len(ai_response_content)}")
        logger.debug(f"Generated Answer (start): {ai_response_content[:200]}...")

        # 5. Store AI Response
        try:
            # Pass the final_sources extracted during formatting
            ai_message_stored = store_message(
                db=db, user_id="ai", content=ai_response_content, message_type="ai",
                conversation_id=conversation_id, sources=final_sources, # Pass sources here
                is_anonymous=is_anonymous
            )
            ai_message_id = ai_message_stored.get('message_id')
            # The sources returned by store_message might have added URLs, use these.
            final_sources = ai_message_stored.get("sources", [])
            logger.info(f"Stored AI message (ID: {ai_message_id or 'N/A'}) for conversation {conversation_id}")
            # Update conversation timestamp after AI message
            if not is_anonymous:
                 update_conversation_timestamp(db, conversation_id)
        except Exception as store_err:
            logger.error(f"Failed to store AI message for conversation {conversation_id}: {store_err}")
            # Log error but return the generated response anyway
            if not error_detail: # Avoid overwriting a more specific LLM error
                 error_detail = f"Failed to store AI response: {store_err}"

        # 6. Return Result
        return {
            "response": ai_response_content,
            "sources": final_sources, # Return sources possibly enriched with URLs
            "conversation_id": conversation_id, # Include conversation ID in response
            "message_id": ai_message_id, # Include AI message ID
            "model_used": model_used,
            "fallback_used": fallback_used,
            "error_detail": error_detail # Include error detail if any occurred
        }

    except Exception as e:
        # Catch-all for unexpected errors in the main orchestration flow
        logger.exception(f"Critical error in RAG pipeline for conversation {conversation_id}: {str(e)}")
        # Attempt to store a generic error message
        try:
            store_message(db, "ai", "I encountered a critical error and couldn't process your request.", "ai", conversation_id, is_anonymous=is_anonymous)
        except Exception as store_err:
            logger.error(f"Failed to store critical error message for {conversation_id}: {store_err}")
        # Return a user-friendly error response
        return {
            "response": "I'm experiencing technical difficulties at the moment. Please try again later.",
            "sources": [],
            "conversation_id": conversation_id,
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
        documents = query_vector_store(query_text=query, top_k=settings.RETRIEVAL_TOP_K) # Use setting
        # Process documents and generate response (simplified for brevity)
        full_response_content = "Generated response content based on documents."
        if full_response_content:
            logger.info(f"Streaming response for conversation {conversation_id}.")
            chunk_size = settings.STREAM_CHUNK_SIZE # Use setting
            for i in range(0, len(full_response_content), chunk_size):
                chunk = full_response_content[i:i+chunk_size]
                yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                await asyncio.sleep(settings.STREAM_CHUNK_DELAY) # Use setting
    except Exception as e:
        logger.exception(f"Error in streaming response for conversation {conversation_id}: {str(e)}")
        yield f