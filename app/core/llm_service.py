# app/core/llm_service.py
import logging
import requests
import json
import random
import time
import asyncio # <<< Add asyncio import
from typing import Dict, List, Any, Optional, Tuple, Union, AsyncGenerator # <<< Add AsyncGenerator

from app.config.settings import settings
# ... other imports ...
logger = logging.getLogger(__name__)

def call_mistral_with_retry(prompt: str, max_retries: int = 3, base_delay: float = 1.0) -> requests.Response:
    """
    Call Mistral API with exponential backoff retry logic.

    Args:
        prompt: The prompt to send to the Mistral API.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay for exponential backoff in seconds.

    Returns:
        requests.Response: The response object from the requests library.
                           Status code indicates success or failure type.
    """
    if not settings.MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY is not configured in settings.")
        # Simulate a requests.Response object for consistent error handling upstream
        error_response = requests.Response()
        error_response.status_code = 500 # Internal Server Error
        error_response._content = b'{"message": "Mistral API key not configured."}'
        error_response.reason = "Configuration Error"
        return error_response

    logger.info(f"Calling Mistral API (max attempts: {max_retries})")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}"
    }
    payload = {
        "model": settings.MISTRAL_MODEL, # Use setting
        "messages": [
            {"role": "system", "content": "You are a knowledgeable assistant specializing in Arabic and Islamic texts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": settings.MISTRAL_TEMPERATURE, # Use setting
        "max_tokens": settings.MISTRAL_MAX_TOKENS   # Use setting
    }
    logger.debug(f"Mistral Request Payload (first 200 chars): {json.dumps(payload)[:200]}...")

    for attempt in range(max_retries):
        try:
            logger.debug(f"Mistral API attempt {attempt+1}/{max_retries}")
            response = requests.post(
                settings.MISTRAL_API_ENDPOINT, # Use setting
                headers=headers,
                json=payload,
                timeout=settings.LLM_TIMEOUT # Use setting
            )
            logger.debug(f"Mistral Response Status: {response.status_code}")

            # Log non-200 responses for debugging
            if response.status_code != 200:
                try:
                    # Limit logging potentially large/sensitive response bodies
                    response_text = response.text[:500] + ('...' if len(response.text) > 500 else '')
                    logger.warning(f"Mistral Response Body (non-200, status {response.status_code}): {response_text}")
                except Exception as log_err:
                    logger.warning(f"Could not log Mistral response body: {log_err}")

            # Success case
            if response.status_code == 200:
                logger.info("Mistral API call successful")
                return response

            # Rate limit handling (429)
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    # Try reading Retry-After header, fall back to exponential backoff
                    retry_after = response.headers.get("Retry-After")
                    try:
                        sleep_time = int(retry_after) + random.uniform(0, 1) # Add jitter
                        logger.warning(f"Rate limit (429) hit. Retrying after {sleep_time:.2f} seconds (from header)...")
                    except (TypeError, ValueError):
                        sleep_time = (2 ** attempt) * base_delay + random.uniform(0, 1) # Exponential backoff + jitter
                        logger.warning(f"Rate limit (429) hit. Retrying in {sleep_time:.2f} seconds (calculated)...")
                    time.sleep(sleep_time)
                    continue # Go to the next attempt
                else:
                    logger.error("Maximum retry attempts reached for rate limit (429)")
                    return response # Return the 429 response after max retries

            # Handle other non-retryable client/server errors (4xx, 5xx excluding 429)
            # These are returned directly without retry
            logger.error(f"Mistral API returned non-retryable error: {response.status_code}")
            return response

        except requests.exceptions.Timeout:
            logger.warning(f"Mistral API call timed out (attempt {attempt+1}/{max_retries}).")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) * base_delay + random.uniform(0, 1)
                logger.warning(f"Retrying after timeout in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Maximum retry attempts reached after timeouts.")
                # Simulate a 408 Timeout response
                timeout_response = requests.Response()
                timeout_response.status_code = 408 # Request Timeout
                timeout_response._content = b'{"message": "Request timed out after multiple retries."}'
                timeout_response.reason = "Request Timeout"
                return timeout_response

        except requests.exceptions.RequestException as e:
            # Catch other connection errors, DNS errors, etc.
            logger.error(f"Mistral API request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) * base_delay + random.uniform(0, 1)
                logger.warning(f"Retrying after request exception in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Maximum retry attempts reached after request exceptions.")
                # Simulate a 503 Service Unavailable response
                conn_err_response = requests.Response()
                conn_err_response.status_code = 503 # Service Unavailable
                conn_err_response._content = f'{{"message": "Could not connect to Mistral API: {str(e)}"}}'.encode()
                conn_err_response.reason = "Service Unavailable"
                return conn_err_response

    # This part should ideally not be reached if the loop handles all cases
    logger.error("Exited Mistral retry loop unexpectedly.")
    final_error_response = requests.Response()
    final_error_response.status_code = 500 # Internal Server Error
    final_error_response._content = b'{"message": "Failed to call Mistral API after multiple retries."}'
    final_error_response.reason = "Internal Server Error"
    return final_error_response


def call_gemini_api(prompt: str) -> Dict[str, any]:
    """
    Call Google Gemini API as a fallback.

    Args:
        prompt: The prompt to send to the Gemini API.

    Returns:
        Dict containing:
            - success (bool): True if the call was successful and response parsed.
            - content (str, optional): The generated text if successful.
            - error (str, optional): Error message if the call failed or response was blocked.
    """
    if not settings.API_KEY_GOOGLE:
        logger.error("API_KEY_GOOGLE is not configured in settings.")
        return {"success": False, "error": "Gemini API key not configured."}

    logger.info("Falling back to Google Gemini API")
    try:
        # Dynamically import google.generativeai to avoid making it a hard dependency
        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google.generativeai package not installed. Install with: pip install google-generativeai")
            return {"success": False, "error": "Gemini library not installed."}

        genai.configure(api_key=settings.API_KEY_GOOGLE)
        model = genai.GenerativeModel(settings.GEMINI_MODEL) # Use setting

        logger.debug(f"Gemini Prompt (first 200 chars): {prompt[:200]}...")

        # Add safety settings if needed
        # safety_settings = [...]
        # response = model.generate_content(prompt, safety_settings=safety_settings)
        response = model.generate_content(prompt)

        logger.debug(f"Gemini Raw Response Object: {response}")

        generated_text = None
        # Handle potential blocking or errors in the response
        try:
            # Accessing response.text can raise ValueError if blocked
            generated_text = response.text
            logger.debug(f"Gemini Generated Text (via .text): {generated_text[:200]}...")
        except ValueError as e:
            # Check if the response was blocked due to safety settings or other reasons
            logger.warning(f"Gemini response.text raised ValueError: {e}. Checking prompt_feedback.")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason
                logger.warning(f"Gemini prompt blocked. Reason: {reason}")
                return {"success": False, "error": f"Gemini prompt blocked: {reason}"}
            else:
                # If .text failed for other reasons
                logger.error(f"Gemini response error (ValueError without block reason): {e}")
                return {"success": False, "error": f"Gemini response error: {e}"}
        except AttributeError:
            # Fallback if .text attribute doesn't exist (older versions or different structure)
            logger.warning("Gemini response object does not have a '.text' attribute. Checking parts.")
            if response and hasattr(response, 'parts') and response.parts:
                # Concatenate text from all parts
                generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                logger.debug(f"Gemini Generated Text (via .parts): {generated_text[:200]}...")
            else:
                # If no .text and no .parts, the response is unusable
                logger.error(f"Gemini API returned an unexpected response structure: {response}")
                return {"success": False, "error": "Invalid response structure from Gemini."}

        # Final check if text was successfully extracted
        if generated_text is not None:
            logger.info("Successfully received and parsed response from Gemini API")
            return {"success": True, "content": generated_text}
        else:
            # Should not happen if logic above is correct, but as a safeguard
            logger.error(f"Gemini response processing failed to extract text. Raw response: {response}")
            return {"success": False, "error": "Failed to extract text from Gemini response."}

    except Exception as e:
        # Catch any other exceptions during API call or processing
        logger.exception(f"Gemini API error occurred: {str(e)}")
        return {"success": False, "error": f"Gemini API call failed: {str(e)}"}

# --- Placeholder Streaming Functions ---

async def call_mistral_streaming(prompt: str) -> AsyncGenerator[str, None]:
    """
    Placeholder for Mistral streaming API call.
    Replace with actual implementation using Mistral's streaming capabilities.
    """
    logger.warning("Using placeholder implementation for call_mistral_streaming")
    # Simulate network delay
    await asyncio.sleep(0.1)
    # Simulate receiving chunks
    yield "Placeholder: Streaming Mistral response chunk 1. "
    await asyncio.sleep(0.1)
    yield "Placeholder: Streaming Mistral response chunk 2."
    # Simulate potential error for testing fallback
    # raise ConnectionError("Simulated Mistral stream error")

async def call_gemini_streaming(prompt: str) -> AsyncGenerator[str, None]:
    """
    Placeholder for Gemini streaming API call.
    Replace with actual implementation using Gemini's streaming capabilities.
    """
    logger.warning("Using placeholder implementation for call_gemini_streaming")
    # Simulate network delay
    await asyncio.sleep(0.1)
    # Simulate receiving chunks
    yield "Placeholder: Streaming Gemini fallback chunk 1. "
    await asyncio.sleep(0.1)
    yield "Placeholder: Streaming Gemini fallback chunk 2."
