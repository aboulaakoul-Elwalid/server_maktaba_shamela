from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.schemas import MessageCreate, Message, ConversationResponse
from app.core.chat_service import (
    store_message, generate_rag_response, generate_streaming_response,
    create_new_conversation, get_user_conversations
)
from app.api.dependencies import get_user_or_anonymous, check_rate_limit
from app.core.clients import appwrite_db
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from app.core.retrieval import query_vector_store
from app.config.settings import settings
from appwrite.query import Query
import json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

@router.post("/messages", response_model=Dict[str, Any], dependencies=[Depends(check_rate_limit)])
async def send_message(message: MessageCreate, user: dict = Depends(get_user_or_anonymous)):
    """Send a message and get an AI response"""
    # Check if user is anonymous
    is_anonymous = user.get("is_anonymous", False)
    
    # 1. Store user message - Appwrite SDK is synchronous, don't use await
    user_message = store_message(
        user["user_id"], 
        message.content, 
        "user", 
        message.conversation_id,
        is_anonymous=is_anonymous
    )
    
    # 2. Generate AI response using RAG (keep await here, it's your own async function)
    rag_response = await generate_rag_response(query=message.content)
    
    # 3. Store AI response - Appwrite SDK is synchronous, don't use await
    ai_message = store_message(
        "ai", 
        rag_response["response"], 
        "ai", 
        message.conversation_id, 
        sources=rag_response.get("context"),
        is_anonymous=is_anonymous
    )
    
    return {
        "user_message": user_message,
        "ai_message": ai_message
    }

@router.post("/conversations", response_model=Dict[str, str])
async def create_conversation(user: dict = Depends(get_user_or_anonymous)):
    """Create a new conversation"""
    # Appwrite SDK is synchronous, don't use await
    return create_new_conversation(user["user_id"], user.get("is_anonymous", False))

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(user: dict = Depends(get_user_or_anonymous)):
    """List all conversations for a user"""
    # Appwrite SDK is synchronous, don't use await
    return get_user_conversations(user["user_id"])

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str, 
    user: dict = Depends(get_user_or_anonymous)
):
    """Get all messages for a specific conversation"""
    try:
        # First verify the conversation exists
        try:
            # Appwrite SDK is synchronous, don't use await
            conversation = appwrite_db.get_document(
                database_id="arabia_db",
                collection_id="conversations",
                document_id=conversation_id
            )
            logger.info(f"Found conversation: {conversation['$id']} for user: {conversation['user_id']}")
        except Exception as e:
            logger.error(f"Error finding conversation: {str(e)}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Use proper Appwrite Query class for filtering
        # Get messages for this conversation using proper Query syntax
        all_messages = appwrite_db.list_documents(
            database_id="arabia_db",
            collection_id="messages",
            queries=[Query.equal("conversation_id", conversation_id)]
        )
        
        # Format response
        conversation_messages = []
        for doc in all_messages.get('documents', []):
            conversation_messages.append({
                "user_id": doc.get('user_id'),
                "content": doc.get('content'),
                "message_id": doc.get('$id'),
                "message_type": doc.get('message_type'),
                "timestamp": doc.get('timestamp'),
                "conversation_id": doc.get('conversation_id')
            })
                
        return conversation_messages
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/stream")
async def stream_message(message: MessageCreate, user: dict = Depends(get_user_or_anonymous)):
    """Send a message and get a streaming response"""
    return StreamingResponse(
        generate_streaming_response(message.content),
        media_type="text/event-stream"
    )

@router.get("/debug", response_model=Dict[str, Any])
async def debug_rag(query: str = "Arabia", user: dict = Depends(get_user_or_anonymous)):
    """Debug endpoint to test RAG components separately"""
    try:
        # Test retrieval
        documents = query_vector_store(query_text=query, top_k=3)
        
        # Test formatting
        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                "text": doc.text_snippet[:100],
                "book": doc.metadata.book_name,
                "section": doc.metadata.section_title,
                "score": doc.score
            })
        
        # Test Mistral client
        from app.core.clients import mistral_client
        mistral_status = "initialized" if mistral_client else "not initialized"
        
        return {
            "retrieval_status": "success" if documents else "failed",
            "document_count": len(documents) if documents else 0,
            "sample_documents": formatted_docs[:2] if documents else [],
            "mistral_client": mistral_status,
            "api_keys_present": {
                "mistral": bool(settings.MISTRAL_API_KEY),
                "pinecone": bool(settings.PINECONE_API_KEY),
                "appwrite": bool(settings.APPWRITE_API_KEY)
            }
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return {"error": str(e)}

def get_message_sources(message_id: str):
    """Get sources for a specific message"""
    try:
        # Appwrite SDK is synchronous, don't use await
        result = appwrite_db.list_documents(
            database_id="arabia_db",
            collection_id="message_sources",
            queries=[Query.equal("message_id", message_id)]
        )
        
        sources = []
        for doc in result['documents']:
            # Parse metadata JSON
            metadata = json.loads(doc.get('metadata', '{}'))
            sources.append({
                "book_name": metadata.get("book_name", "Unknown"),
                "section_title": metadata.get("section_title", "Unknown"),
                "text_snippet": metadata.get("text_snippet", ""),
                "url": doc.get("url", ""),
                "relevance": metadata.get("relevance", 0),
                "document_id": metadata.get("document_id", "")
            })
        return sources
    except Exception as e:
        logger.error(f"Failed to get message sources: {str(e)}")
        return []

@router.get("/debug/conversation/{conversation_id}")
async def debug_get_conversation(conversation_id: str):
    """Debug endpoint to directly test conversation retrieval"""
    try:
        # Appwrite SDK is synchronous, don't use await
        result = appwrite_db.get_document(
            database_id="arabia_db",
            collection_id="conversations",
            document_id=conversation_id
        )
        return {"status": "success", "conversation": result}
    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__}