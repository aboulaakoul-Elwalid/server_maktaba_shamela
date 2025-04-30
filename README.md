# Arabia RAG API

**Project Goal:** To provide a robust backend API for a Retrieval-Augmented Generation (RAG) system focused on the Qatar Shamela Library, enabling users to interact with the library's content through a conversational interface.

**Core Functionality:** The API handles user authentication, manages chat conversations, retrieves relevant text chunks from a vector database (Pinecone) based on user queries, uses a Large Language Model (Mistral AI) to generate context-aware responses, and stores conversation history (using Appwrite).

## Features

- **RAG Pipeline:** Implements a full RAG pipeline:
  - User query processing.
  - Semantic search via vector embeddings in Pinecone.
  - Context retrieval and formatting.
  - Response generation using Mistral AI.
- **Text Embedding:** Utilizes Mistral AI models for generating high-quality text embeddings.
- **Vector Database:** Leverages Pinecone for efficient storage and retrieval of text embeddings.
- **Document Processing:** Includes capabilities for processing and chunking source documents (initially designed for JSON/TXT, adaptable for PDF).
- **Arabic Language Support:** Incorporates Arabic text normalization and processing techniques.
- **User Authentication & Management:** Secure user registration and login using JWT via Appwrite.
- **Conversation Management:** Stores and retrieves chat history per user in Appwrite. Supports anonymous sessions (without storage).
- **API Endpoints:** Provides FastAPI endpoints for:
  - Authentication (Register, Login, Get User).
  - Chat (Send message, Stream message, Create/List conversations, Get messages).
- **Streaming Support:** Offers Server-Sent Events (SSE) for real-time streaming of AI responses.
- **Configuration:** Centralized configuration management using Pydantic and `.env` files.

## Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

- **Python:** Version 3.12 or higher.
- **API Keys:**
  - Mistral AI API Key
  - Pinecone API Key & Environment
- **Appwrite Instance:**
  - A running Appwrite instance (Cloud or self-hosted).
  - Appwrite Project ID
  - Appwrite API Key (with necessary permissions for Databases).
  - Appwrite Endpoint URL.
- **Git:** For cloning the repository.
- **Environment Variables:** A `.env` file is required to store sensitive keys and configuration. See `.env.example`.

### Installation & Setup

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/aboulaakoul-Elwalid/server_maktaba_shamela # Replace with your repo URL
    cd arabia-rag-api
    ```

2.  **Create Virtual Environment:**

    ```bash
    python -m venv venv
    ```

3.  **Activate Virtual Environment:**

    - **Windows:**
      ```bash
      .\venv\Scripts\activate
      ```
    - **macOS/Linux:**
      ```bash
      source venv/bin/activate
      ```

4.  **Install Dependencies:**

    ```bash
    uv add -r requirements.txt
    ```

5.  **Configure Environment Variables:**

    - Copy the example file: `copy .env.example .env` (Windows) or `cp .env.example .env` (macOS/Linux).
    - **Edit the `.env` file** and fill in your actual API keys, Appwrite details (Project ID, API Key, Endpoint), Pinecone details, and any other required settings. Refer to [`app/config/settings.py`](app/config/settings.py) for all possible variables.

6.  **Set up Appwrite Database & Collections:**
    - The application requires specific Appwrite database collections (e.g., for users, conversations, messages).
    - **Option A (Recommended if script exists):** Run the setup script (if provided):
      ```bash
      python -m app.models.setup_appwrite_collections
      ```

### Running the Application

1.  **Start the FastAPI Server:**

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    - `--reload`: Enables auto-reloading during development. Remove for production.

2.  **Access the API:**
    - **Base URL:** `http://localhost:8000`
    - **Interactive Docs (Swagger UI):** `http://localhost:8000/docs`
    - **Alternative Docs (ReDoc):** `http://localhost:8000/redoc`

## Project Structure

```
.
├── app/                  # Core FastAPI application source code
│   ├── api/              # API layer: Routers, dependencies, auth utils
│   │   ├── endpoints/    # Route handlers (auth.py, chat.py, etc.)
│   │   ├── dependencies.py # FastAPI dependency injection functions
│   │   └── auth_utils.py # Authentication helper functions
│   ├── config/           # Configuration loading
│   │   └── settings.py   # Pydantic settings model (loads .env)
│   ├── core/             # Business logic: RAG, LLM, DB interactions
│   │   ├── ingestion/    # Data ingestion/processing scripts (not complete ,still working on it)
│   │   ├── chat_service.py # Non-streaming RAG orchestration
│   │   ├── streaming.py  # Streaming RAG orchestration (SSE)
│   │   ├── retrieval.py  # Pinecone vector retrieval logic
│   │   ├── llm_service.py # LLM interaction logic (Mistral)
│   │   ├── embeddings.py # Text embedding generation logic
│   │   ├── storage.py    # Appwrite database interaction logic
│   │   └── context_formatter.py # Prompt formatting logic
│   ├── models/           # Data models and DB setup
│   │   ├── schemas.py    # Pydantic schemas for API I/O and data validation
│   │   └── setup_appwrite_collections.py # (Optional) Appwrite setup script
│   ├── utils/            # Shared utility functions
│   ├── main.py           # FastAPI app factory: creates app, mounts routers
│   └── __init__.py
├── docs/                 # Documentation files (like this README, API specs)
├── logs/                 # Application log files (if configured)
├── tests/                # Automated tests (unit, integration)
├── .env                  # Local environment variables (Git ignored)
├── .env.example          # Example environment variables template
├── main.py               # Root entry point for ASGI servers (imports app.main:app)
├── requirements.txt      # Python package dependencies
├── pyproject.toml        # Project metadata, build system config (Poetry/Flit)
└── README.md             # This file
```

## `app` Directory Deep Dive

- **`app/api`**: Handles incoming HTTP requests.
  - `endpoints`: Defines specific routes (e.g., `/chat/messages`). Each file typically uses a FastAPI `APIRouter`.
  - `dependencies.py`: Contains reusable functions injected into route handlers (e.g., `get_current_user` to verify JWT tokens).
  - `auth_utils.py`: Helpers for password hashing, token creation, etc.
- **`app/config`**: Manages application settings.
  - `settings.py`: Defines a Pydantic `BaseSettings` class that automatically loads variables from the `.env` file, providing type validation.
- **`app/core`**: The heart of the application logic.
  - `chat_service.py` / `streaming.py`: Orchestrate the flow of a user request – retrieving context, calling the LLM, and formatting the response.
  - `retrieval.py`: Queries Pinecone to find relevant document chunks.
  - `llm_service.py`: Communicates with the Mistral AI API.
  - `embeddings.py`: Generates vector embeddings for text.
  - `storage.py`: Interacts with Appwrite (CRUD operations for conversations/messages). Handles logic for anonymous users (skipping DB writes).
  - `context_formatter.py`: Prepares the final prompt for the LLM, including retrieved context and chat history.
  - `ingestion/`: Contains standalone scripts related to processing source data (e.g., PDFs) and uploading embeddings/metadata to Pinecone. **Note:** The code in this directory is currently complex, potentially messy, and reflects an extensive data processing effort. It is not fully integrated or representative of the final intended state and will be cleaned and updated in the future. This part is separate from the main API runtime logic.
- **`app/models`**: Defines data structures.
  - `schemas.py`: Pydantic models ensure data consistency in API requests/responses and internal function calls.
  - `setup_appwrite_collections.py`: (If present) Automates the creation of necessary Appwrite resources.
- **`app/utils`**: General helper functions (e.g., text cleaning, logging setup) used across different modules.
- **`app/main.py`**: Creates the main `FastAPI` application instance, includes routers from `app/api/endpoints`, and configures middleware (like CORS).

## API Endpoints Overview

(Based on [`docs/doc_backend_struct.md`](docs/doc_backend_struct.md))

- **Authentication (`/auth`)**
  - `POST /register`: Create a new user.
  - `POST /login`: Authenticate and get JWT token.
  - `GET /users/me`: Get current authenticated user's profile.
- **Chat (`/chat`)**
  - `POST /messages`: Send a message, get a standard RAG response. (Supports anonymous users).
  - `POST /messages/stream`: Send a message, get a streaming SSE response. (Supports anonymous users).
  - `POST /conversations`: Create a new empty conversation (Authenticated users only).
  - `GET /conversations`: List conversations for the authenticated user.
  - `GET /conversations/{conversation_id}/messages`: Get message history for a specific conversation (Authenticated users only).

_Refer to `/docs` on the running server for detailed request/response schemas and testing._

## Configuration Details

The application relies on environment variables for configuration. These are loaded via Pydantic's `BaseSettings` from a `.env` file located in the project root. Copy `.env.example` to `.env` and fill in the required values.

Refer to [`app/config/settings.py`](app/config/settings.py) for the complete list and default values.

**Required Environment Variables:**

- `MISTRAL_API_KEY`: Your API key for Mistral AI services (embedding, generation).
- `PINECONE_API_KEY`: Your API key for Pinecone.
- `APPWRITE_ENDPOINT`: The URL of your Appwrite instance (e.g., `https://cloud.appwrite.io/v1`).
- `APPWRITE_PROJECT_ID`: Your Appwrite project identifier.
- `APPWRITE_API_KEY`: Your Appwrite API key (secret, with database permissions).
- `APPWRITE_CONVERSATIONS_COLLECTION_ID`: ID of the Appwrite collection storing conversation metadata.
- `APPWRITE_MESSAGES_COLLECTION_ID`: ID of the Appwrite collection storing chat messages.
- `APPWRITE_MESSAGE_SOURCES_COLLECTION_ID`: ID of the Appwrite collection storing message sources/references.
- `SECRET_KEY`: A secret string used for signing JWT tokens (ensure this is strong and kept private).

**Optional API Keys:**

- `API_KEY_GOOGLE`: API key if using Google Gemini models (optional).

**Key Configurable Variables (with defaults):**

- `PINECONE_ENVIRONMENT`: The Pinecone environment (default: `us-west1-gcp`).
- `PINECONE_INDEX_NAME`: The name of the Pinecone index to use.
- `EMBEDDING_MODEL_NAME`: Name of the Mistral embedding model to use (mistral-embed).
- `LLM_MODEL_NAME`: Name of the Mistral chat model to use (mistral-sabaa).

## Testing

```bash
pytest tests/
```

## Deployment

-i used render, it was a good experience.
