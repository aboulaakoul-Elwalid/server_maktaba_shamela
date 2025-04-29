# Arabia RAG API Documentation

## 1. Introduction

This document provides documentation for the Arabia RAG FastAPI backend API. The API provides endpoints for user authentication, managing chat conversations, performing Retrieval-Augmented Generation (RAG) queries (both streaming and non-streaming), and potentially document ingestion/retrieval management.

**Base URL:** (Assuming local development) `http://localhost:8000`

## 2. Authentication

Authentication is handled via JWT (JSON Web Tokens). Users register and log in to obtain a token, which must be included in the `Authorization` header for protected endpoints.

**Header Format:** `Authorization: Bearer <your_jwt_token>`

### 2.1 Authentication Dependencies

These FastAPI dependencies handle user identification:

- **`get_current_user`**:
  - Requires a valid JWT token in the `Authorization: Bearer <token>` header.
  - Verifies the token and retrieves the corresponding user data from the database (via mocked Appwrite `Account.get` in tests).
  - If the token is invalid, expired, or missing, it raises an `HTTPException` (typically 401 Unauthorized).
  - Returns a `UserResponse` object for the authenticated user.
- **`get_user_or_anonymous`**:
  - Attempts to get a user via `get_current_user`.
  - If successful, returns the authenticated `UserResponse`.
  - If `get_current_user` fails (no token, invalid token), it creates and returns a temporary `UserResponse` object representing an anonymous user (e.g., `user_id="anonymous_..."`, `is_anonymous=True`).
  - **Crucially, this allows endpoints to proceed even without authentication, but provides a flag (`is_anonymous`) to modify behavior (like skipping database storage).**

### 2.2 Authentication Endpoints

_(Located in `app/api/endpoints/auth.py`)_

- **`POST /auth/register`**
  - **Summary:** Creates a new user account.
  - **Authentication:** None required.
  - **Request Body:** `UserCreate` schema (e.g., `{"email": "user@example.com", "password": "password123", "name": "Test User"}`)
  - **Response Body (Success - 201 Created):** `UserResponse` schema (contains user details like ID, email, name, but **not** the password).
  - **Errors:** 400 (Email already registered), 503 (Database error).
- **`POST /auth/login`**
  - **Summary:** Authenticates a user and returns a JWT token.
  - **Authentication:** None required.
  - **Request Body:** `OAuth2PasswordRequestForm` (standard FastAPI form data: `username` (which is the email) and `password`).
  - **Response Body (Success - 200 OK):** `Token` schema (`{"access_token": "...", "token_type": "bearer"}`).
  - **Errors:** 401 (Invalid credentials), 503 (Database error).
- **`GET /auth/users/me`**
  - **Summary:** Retrieves the profile of the currently authenticated user.
  - **Authentication:** Required (`get_current_user`).
  - **Request Body:** None.
  - **Response Body (Success - 200 OK):** `UserResponse` schema.
  - **Errors:** 401 (Not authenticated).

## 3. Chat API

Handles creating conversations, sending messages, and retrieving history. Supports both standard request/response and Server-Sent Events (SSE) streaming. Allows anonymous users for temporary chats (no data stored).

_(Located in `app/api/endpoints/chat.py`)_

### 3.1 Chat Schemas

- **`MessageCreate`**: Used for sending messages.
  - `content`: (string, required) The text of the user's message.
  - `conversation_id`: (string, optional) The ID of the conversation to continue. If omitted when sending the _first_ message, a new conversation might be created implicitly _only if the user is authenticated_. Anonymous users sending a message without a `conversation_id` will not have a conversation created or stored.
- **`ChatResponse`**: Response for the non-streaming chat endpoint.
  - `ai_response`: (string) The generated text response from the LLM.
  - `sources`: (List[`Source`]) A list of source documents used to generate the response.
  - `conversation_id`: (string | null) The ID of the conversation. `null` if the user was anonymous.
  - `user_message_id`: (string | null) The ID of the stored user message. `null` if the user was anonymous.
  - `ai_message_id`: (string | null) The ID of the stored AI message. `null` if the user was anonymous.
- **`Source`**: Detailed information about a source document.
  - `document_id`: (string) Original ID from the vector store.
  - `book_id`: (string) Extracted book ID.
  - `book_name`: (string | null) Name of the source book.
  - `title`: (string | null) Section title within the book.
  - `score`: (float | null) Relevance score.
  - `url`: (string | null) URL to the source (e.g., Shamela).
  - `content`: (string | null) The relevant text snippet used as context.
- **`Message`**: Represents a stored message in a conversation (used for history).
  - `message_id`: (string) Unique ID of the message.
  - `conversation_id`: (string) ID of the conversation it belongs to.
  - `user_id`: (string) ID of the sender ('ai' or user ID).
  - `content`: (string) Text content.
  - `message_type`: (string) "user" or "ai".
  - `timestamp`: (string) ISO 8601 timestamp.
  - `sources`: (List[`Source`] | null) List of sources for AI messages.
- **`ConversationResponse`**: Represents a conversation entry (used for listing conversations).
  - `id`: (string) Conversation ID.
  - `user_id`: (string) ID of the user who owns it.
  - `title`: (string) Title of the conversation.
  - `created_at`: (string) ISO 8601 timestamp.
  - `last_updated`: (string | null) ISO 8601 timestamp.

### 3.2 Chat Endpoints

- **`POST /chat/messages`**
  - **Summary:** Send a message, get a standard RAG response.
  - **Authentication:** Optional (`get_user_or_anonymous`).
  - **Request Body:** `MessageCreate` schema.
  - **Response Body (Success - 200 OK):** `ChatResponse` schema.
    - If **authenticated**: Stores user message, generates response, stores AI message, returns response/sources/IDs. Creates conversation if `conversation_id` is omitted and it's the first message.
    - If **anonymous**: Skips history fetch, skips storing user/AI messages, generates response, returns response/sources with `null` IDs. Does **not** create a conversation.
  - **Core Logic:** Calls `generate_rag_response` in `chat_service.py`.
  - **Errors:** 422 (Invalid request body), 500 (LLM/RAG error), 503 (Database error during storage _if authenticated_).
- **`POST /chat/messages/stream`**
  - **Summary:** Send a message, get a streaming RAG response via Server-Sent Events (SSE).
  - **Authentication:** Optional (`get_user_or_anonymous`).
  - **Request Body:** `MessageCreate` schema.
  - **Response Body (Success - 200 OK):** `text/event-stream`. Sequence of SSE events.
    - **Common Events (Authenticated & Anonymous):**
      - `event: chunk\ndata: {"token": "..."}\n\n`: Streamed tokens from the LLM response.
      - `event: sources\ndata: [{"document_id": ..., "content": ...}, ...]\n\n`: Final list of source documents used.
      - `event: error\ndata: {"detail": "..."}\n\n`: Indicates an error occurred during generation.
      - `event: end\ndata: [DONE]\n\n`: Signals the end of the stream.
    - **Authenticated Only Events:**
      - `event: conversation_id\ndata: {"conversation_id": "..."}\n\n`: Sent _once_ if a new conversation was created for the authenticated user.
      - `event: message_id\ndata: {"message_id": "..."}\n\n`: Sent _once_ after the full AI response is generated and stored, providing the ID of the stored AI message.
  - **Core Logic:** Calls `generate_streaming_response` in `streaming.py`. Handles conditional storage and event yielding based on `is_anonymous`.
  - **Errors:** 422 (Invalid request body), potentially SSE `error` events for LLM/RAG/storage failures.
- **`POST /chat/conversations`**
  - **Summary:** Explicitly creates a new, empty conversation for the authenticated user.
  - **Authentication:** Required (`get_current_user`).
  - **Request Body:** None.
  - **Response Body (Success - 201 Created):** `{"conversation_id": "...", "message": "Conversation created successfully"}`.
  - **Errors:** 401 (Not authenticated), 503 (Database error).
- **`GET /chat/conversations`**
  - **Summary:** Retrieves a list of all conversations belonging to the authenticated user.
  - **Authentication:** Required (`get_current_user`).
  - **Request Body:** None.
  - **Response Body (Success - 200 OK):** `List[ConversationResponse]` schema.
  - **Errors:** 401 (Not authenticated), 503 (Database error).
- **`GET /chat/conversations/{conversation_id}/messages`**
  - **Summary:** Retrieves the message history for a specific conversation owned by the authenticated user.
  - **Authentication:** Required (`get_current_user`).
  - **Request Body:** None.
  - **Path Parameter:** `conversation_id` (string, required).
  - **Response Body (Success - 200 OK):** `List[Message]` schema.
  - **Errors:** 401 (Not authenticated), 403 (Authenticated user does not own this conversation), 404 (Conversation not found), 503 (Database error).

## 4. Core Logic Overview

_(Brief descriptions of key functions called by endpoints)_

- **`generate_rag_response` (`chat_service.py`):**
  - Handles the non-streaming RAG process.
  - Conditionally fetches history (if auth).
  - Conditionally stores user message (if auth).
  - Performs document retrieval.
  - Formats context.
  - Calls LLM (non-streaming).
  - Conditionally stores AI message (if auth).
  - Returns structured response.
- **`generate_streaming_response` (`streaming.py`):**
  - Handles the streaming RAG process using SSE.
  - Conditionally fetches history (if auth).
  - Conditionally stores user message (if auth).
  - Performs document retrieval.
  - Formats context.
  - Calls LLM (streaming).
  - Yields `chunk` and `sources` events.
  - Conditionally stores AI message (if auth).
  - Conditionally yields `conversation_id` and `message_id` events (if auth).
  - Yields `error` or `end` events.
- **`store_message` (`storage.py`):**
  - Handles writing user/AI messages and their sources to the database.
  - Contains logic to **skip database writes** if `is_anonymous` is `True`, returning a temporary structure instead.
- **`update_conversation_timestamp` (`storage.py`):**
  - Updates the `last_updated` field on a conversation document.
  - Skips updates if the `conversation_id` indicates it's an anonymous one (e.g., starts with `anon_conv_`).
- **`format_context_and_extract_sources` (`context_formatter.py`):**
  - Takes retrieved `DocumentMatch` objects.
  - Creates the formatted text string (`context_text`) to be included in the LLM prompt.
  - Extracts structured source information (including text snippets) suitable for storage and API responses.
- **`construct_llm_prompt` (`context_formatter.py`):**
  - Assembles the final prompt string using history, context, and the user query.

## 5. Other APIs (Ingestion, Retrieval - Placeholder)

_(Add details here later if needed, similar to the Chat API section)_

- **Ingestion API (`app/api/endpoints/ingestion.py`):** Likely handles adding documents to the vector store (e.g., `/ingest`, `/ingest/batch`). Requires API key authentication.
- **Retrieval API (`app/api/endpoints/retrieval.py`):** May provide direct access to the document retriever (e.g., `/retrieve`). Authentication TBD.

## 6. Configuration

_(Located in `app/config/settings.py`)_

Key settings are managed via Pydantic's `BaseSettings`, likely loaded from environment variables or a `.env` file. Important settings include:

- Appwrite credentials (`APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, `APPWRITE_DATABASE_ID`, collection IDs)
- LLM API keys and model names (`MISTRAL_API_KEY`, `GEMINI_API_KEY`, etc.)
- Vector store details (e.g., Pinecone API key, environment, index name)
- JWT Secret Key (`SECRET_KEY`) and algorithm (`ALGORITHM`)
- Token expiration time (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- Retrieval parameters (`RETRIEVAL_TOP_K`)

---
