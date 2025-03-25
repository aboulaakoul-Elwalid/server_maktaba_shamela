from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.schemas import MessageCreate, Message, ConversationResponse
from app.core.chat_service import (
    store_message, generate_rag_response, generate_streaming_response,
    create_new_conversation, get_user_conversations
)
from app.api.dependencies import get_current_user
from app.core.clients import appwrite_db
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

@router.post("/messages", response_model=Dict[str, Any])
async def send_message(message: MessageCreate, user: dict = Depends(get_current_user)):
    """Send a message and get an AI response"""
    # 1. Store user message
    user_message = await store_message(
        user["user_id"], 
        message.content, 
        "user", 
        message.conversation_id
    )
    
    # 2. Generate AI response using RAG
    rag_response = await generate_rag_response(query=message.content)
    
    # 3. Store AI response
    ai_message = await store_message(
        "ai", 
        rag_response["response"], 
        "ai", 
        message.conversation_id, 
        sources=rag_response.get("context")
    )
    
    return {
        "user_message": user_message,
        "ai_message": ai_message
    }

@router.get("/messages", response_model=List[Message])
async def get_messages(
    conversation_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get messages, optionally filtered by conversation"""
    try:
        # Build query
        queries = []
        if conversation_id:
            queries.append(f'conversation_id="{conversation_id}"')
        
        # Get messages from Appwrite
        result = await appwrite_db.list_documents(
            database_id="arabia_db",
            collection_id="messages",
            queries=queries if queries else None
        )
        
        messages = []
        for doc in result['documents']:
            messages.append(Message(
                user_id=doc['user_id'],
                content=doc['content'],
                message_id=doc['$id'],
                message_type=doc['message_type'],
                timestamp=datetime.fromisoformat(doc['timestamp']),
                conversation_id=doc.get('conversation_id'),
                sources=doc.get('sources')
            ))
        
        return messages
    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations", response_model=Dict[str, str])
async def create_conversation(user: dict = Depends(get_current_user)):
    """Create a new conversation"""
    return await create_new_conversation(user["user_id"])

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(user: dict = Depends(get_current_user)):
    """List all conversations for a user"""
    return await get_user_conversations(user["user_id"])

@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(
    conversation_id: str, 
    user: dict = Depends(get_current_user)
):
    """Get all messages for a specific conversation"""
    try:
        # First check if the conversation exists and belongs to the user
        try:
            conversation = await appwrite_db.get_document(
                database_id="arabia_db",
                collection_id="conversations",
                document_id=conversation_id
            )
            
            if conversation["user_id"] != user["user_id"]:
                raise HTTPException(status_code=403, detail="You don't have access to this conversation")
                
        except Exception as e:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages for this conversation
        result = await appwrite_db.list_documents(
            database_id="arabia_db",
            collection_id="messages",
            queries=[f'conversation_id="{conversation_id}"'],
            orderAttributes=["timestamp"],
            orderTypes=["ASC"]
        )
        
        messages = []
        for doc in result['documents']:
            messages.append(Message(
                user_id=doc['user_id'],
                content=doc['content'],
                message_id=doc['$id'],
                message_type=doc['message_type'],
                timestamp=datetime.fromisoformat(doc['timestamp']),
                conversation_id=doc.get('conversation_id'),
                sources=doc.get('sources')
            ))
        
        return messages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/stream")
async def send_message_stream(
    message: MessageCreate, 
    user: dict = Depends(get_current_user)
):
    """Stream an AI response"""
    # Store the user message first
    await store_message(
        user["user_id"],
        message.content,
        "user",
        message.conversation_id
    )
    
    # Return a streaming response
    return StreamingResponse(
        generate_streaming_response(message.content),
        media_type="text/event-stream"
    )

@router.get("/debug", response_model=Dict[str, Any])
async def debug_rag(query: str = "Arabia", user: dict = Depends(get_current_user)):
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