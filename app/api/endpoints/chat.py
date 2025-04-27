from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.schemas import MessageCreate, Message, ConversationResponse, DocumentMatch
from app.core.storage import create_new_conversation, get_user_conversations
from app.core.chat_service import generate_rag_response
from app.core.streaming import generate_streaming_response
from app.api.dependencies import get_user_or_anonymous, check_rate_limit
from app.core.clients import get_admin_db_service
from appwrite.services.databases import Databases
from typing import List, Dict, Any, Optional
from app.core.retrieval import get_retriever, Retriever  # Use the new retrieval package
from app.core.context_formatter import format_context_and_extract_sources, construct_llm_prompt
from app.config.settings import settings
from appwrite.query import Query
from appwrite.exception import AppwriteException
from app.api.auth_utils import UserResponse
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

@router.post("/messages", response_model=Dict[str, Any], dependencies=[Depends(check_rate_limit)])
async def send_message(
    message: MessageCreate,
    user: UserResponse = Depends(get_user_or_anonymous),
    db: Databases = Depends(get_admin_db_service)
):
    """Send a message and get an AI response (non-streaming)."""
    is_anonymous = user.is_anonymous
    conversation_id = message.conversation_id
    user_id = user.user_id

    if not conversation_id and not is_anonymous:
        try:
            new_convo = create_new_conversation(db=db, user_id=user_id, is_anonymous=is_anonymous)
            conversation_id = new_convo["conversation_id"]
            logger.info(f"Created new conversation {conversation_id} for message.")
        except HTTPException as e:
            logger.error(f"Failed to create conversation implicitly for user {user_id}: {e.detail}")
            raise HTTPException(status_code=e.status_code, detail=f"Could not start conversation: {e.detail}")
    elif not conversation_id and is_anonymous:
        conversation_id = f"anon_conv_{uuid.uuid4().hex}"
        logger.info(f"Using temporary anonymous conversation ID: {conversation_id}")

    try:
        rag_response_data = await generate_rag_response(
            db=db,
            query=message.content,
            user_id=user_id,
            conversation_id=conversation_id,
            is_anonymous=is_anonymous
        )

        return {
            "ai_response": rag_response_data.get("response"),
            "sources": rag_response_data.get("sources", []),
            "conversation_id": rag_response_data.get("conversation_id"),
            "message_id": rag_response_data.get("message_id"),
            "model_used": rag_response_data.get("model_used"),
            "error": rag_response_data.get("error_detail")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing message in conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message.")

@router.post("/conversations", response_model=Dict[str, str])
async def create_conversation_endpoint(
    user: UserResponse = Depends(get_user_or_anonymous),
    db: Databases = Depends(get_admin_db_service)
):
    """Create a new conversation explicitly."""
    return create_new_conversation(db=db, user_id=user.user_id, is_anonymous=user.is_anonymous)

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations_endpoint(
    user: UserResponse = Depends(get_user_or_anonymous),
    db: Databases = Depends(get_admin_db_service)
):
    """List all conversations for the authenticated user."""
    if user.is_anonymous:
        return []

    conversations_data = get_user_conversations(db=db, user_id=user.user_id)
    response = [
        ConversationResponse(
            id=conv.get('$id'),
            title=conv.get('title'),
            created_at=conv.get('created_at'),
            last_updated=conv.get('last_updated')
        ) for conv in conversations_data
    ]
    return response

@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(
    conversation_id: str,
    user: UserResponse = Depends(get_user_or_anonymous),
    db: Databases = Depends(get_admin_db_service)
):
    """Get all messages for a specific conversation."""
    if user.is_anonymous:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anonymous users cannot retrieve conversation history.")

    try:
        try:
            convo_doc = db.get_document(
                database_id=settings.APPWRITE_DATABASE_ID,
                collection_id=settings.APPWRITE_CONVERSATIONS_COLLECTION_ID,
                document_id=conversation_id
            )
            if convo_doc.get('user_id') != user.user_id:
                logger.warning(f"User {user.user_id} attempted to access conversation {conversation_id} owned by {convo_doc.get('user_id')}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or access denied.")
        except AppwriteException as ae:
            if ae.code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
            else:
                raise

        all_messages_result = db.list_documents(
            database_id=settings.APPWRITE_DATABASE_ID,
            collection_id=settings.APPWRITE_MESSAGES_COLLECTION_ID,
            queries=[
                Query.equal("conversation_id", conversation_id),
                Query.order_asc("timestamp")
            ]
        )

        conversation_messages = []
        for doc in all_messages_result.get('documents', []):
            # Map Appwrite doc to your Message Pydantic model
            # TODO: Implement source fetching if required by Message model and performance allows.
            # This currently requires N+1 queries (1 query per message to get its sources).
            # Consider embedding sources in the message document or fetching only on demand.
            try:
                message_model = Message(
                    message_id=doc.get('$id'),  # <<< FIX: Changed 'id' to 'message_id'
                    conversation_id=doc.get('conversation_id'),
                    user_id=doc.get('user_id'),
                    content=doc.get('content'),
                    message_type=doc.get('message_type'),
                    timestamp=doc.get('timestamp'),
                    sources=[]  # Placeholder - see TODO above
                )
                conversation_messages.append(message_model)
            except Exception as pydantic_error:
                # Log the specific document that failed validation
                logger.error(f"Pydantic validation failed for Appwrite doc ID {doc.get('$id')}: {pydantic_error}")
                logger.debug(f"Failing document data: {doc}")
                # Optionally skip this message or raise the error depending on desired behavior
                # continue # Skip this message and log

        return conversation_messages

    except AppwriteException as e:
        logger.error(f"Appwrite error retrieving messages for conversation {conversation_id}: {e.message}")
        status_code = status.HTTP_404_NOT_FOUND if e.code == 404 else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=status_code, detail=f"Failed to retrieve messages: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error retrieving messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while retrieving messages.")

@router.post("/messages/stream", dependencies=[Depends(check_rate_limit)])
async def stream_message(
    message: MessageCreate,
    user: UserResponse = Depends(get_user_or_anonymous),
    db: Databases = Depends(get_admin_db_service)
):
    """Send a message and get a streaming response using SSE."""
    is_anonymous = user.is_anonymous
    conversation_id = message.conversation_id
    user_id = user.user_id

    if not conversation_id and not is_anonymous:
        try:
            new_convo = create_new_conversation(db=db, user_id=user_id, is_anonymous=is_anonymous)
            conversation_id = new_convo["conversation_id"]
            logger.info(f"Created new conversation {conversation_id} for streaming message.")
        except HTTPException as e:
            logger.error(f"Failed to create conversation implicitly for user {user_id} (stream): {e.detail}")
            pass
    elif not conversation_id and is_anonymous:
        conversation_id = f"anon_conv_{uuid.uuid4().hex}"
        logger.info(f"Using temporary anonymous conversation ID for stream: {conversation_id}")

    return StreamingResponse(
        generate_streaming_response(
            db=db,
            query=message.content,
            user_id=user_id,
            conversation_id=conversation_id,
            is_anonymous=is_anonymous
        ),
        media_type="text/event-stream"
    )

@router.get("/debug", response_model=Dict[str, Any])
async def debug_rag(query: str = "Test query", user: UserResponse = Depends(get_user_or_anonymous)):
    """Debug endpoint to test the RAG pipeline components."""
    try:
        retriever: Retriever = get_retriever()
        documents: Optional[List[DocumentMatch]] = await retriever.retrieve(query=query, top_k=settings.RETRIEVAL_TOP_K)

        formatted_docs = []
        if documents:
            _, sources = format_context_and_extract_sources(documents)
            formatted_docs = sources

        return {
            "query": query,
            "retriever_provider": settings.RETRIEVER_PROVIDER,
            "retrieval_status": "success" if documents is not None else "failed",
            "document_count": len(documents) if documents else 0,
            "sample_formatted_sources": formatted_docs[:2],
            "llm_keys_present": {
                "mistral": bool(settings.MISTRAL_API_KEY),
                "gemini": bool(settings.API_KEY_GOOGLE),
                "pinecone": bool(settings.PINECONE_API_KEY),
                "appwrite": bool(settings.APPWRITE_API_KEY)
            }
        }
    except Exception as e:
        logger.exception(f"Debug endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/conversation/{conversation_id}")
async def debug_get_conversation(
    conversation_id: str,
    db: Databases = Depends(get_admin_db_service)
):
    """Debug endpoint to directly test conversation retrieval from Appwrite."""
    try:
        result = db.get_document(
            database_id=settings.APPWRITE_DATABASE_ID,
            collection_id=settings.APPWRITE_CONVERSATIONS_COLLECTION_ID,
            document_id=conversation_id
        )
        return {"status": "success", "conversation": result}
    except AppwriteException as e:
        logger.error(f"Debug conversation retrieval error: {e.message} (Code: {e.code})")
        status_code = 404 if e.code == 404 else 503
        return {"status": "error", "message": e.message, "code": e.code, "http_status": status_code}
    except Exception as e:
        logger.exception(f"Unexpected debug conversation retrieval error: {e}")
        return {"status": "error", "message": str(e), "http_status": 500}
