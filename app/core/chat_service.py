# app/core/chat_service.py
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
import logging
from fastapi import HTTPException
from app.core.clients import appwrite_db
from app.core.rag import generate_rag_response as core_generate_rag_response
from appwrite.permission import Permission
from appwrite.role import Role

logger = logging.getLogger(__name__)

async def store_message(user_id: str, content: str, message_type: str, 
                       conversation_id: Optional[str] = None, 
                       sources: Optional[List[Dict]] = None) -> Dict:
    """Store a message in the Appwrite database"""
    try:
        message_data = {
            "user_id": user_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat(),
        }
        
        if conversation_id:
            message_data["conversation_id"] = conversation_id
            
        if sources:
            message_data["sources"] = sources
            
        # Add permissions
        permissions = [
            Permission.read(Role.user(user_id))
        ]
        
        # If it's a conversation message, add read permission for conversation owner
        if conversation_id:
            try:
                conversation = await appwrite_db.get_document(
                    database_id="arabia_db",
                    collection_id="conversations",
                    document_id=conversation_id
                )
                conversation_owner = conversation["user_id"]
                if conversation_owner != user_id:
                    permissions.append(Permission.read(Role.user(conversation_owner)))
            except:
                pass
            
        result = await appwrite_db.create_document(
            database_id="arabia_db",
            collection_id="messages",
            document_id="unique()",
            data=message_data,
            permissions=permissions
        )
        
        return {
            "user_id": result["user_id"],
            "content": result["content"],
            "message_id": result["$id"],
            "message_type": result["message_type"],
            "timestamp": result["timestamp"],
            "conversation_id": result.get("conversation_id"),
            "sources": result.get("sources")
        }
    except Exception as e:
        logger.error(f"Failed to store message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store message: {str(e)}")

async def generate_rag_response(query: str) -> Dict:
    """Generate an AI response using the RAG system"""
    try:
        return await core_generate_rag_response(query=query)
    except Exception as e:
        logger.error(f"Failed to generate RAG response: {str(e)}")
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "context": []
        }

async def generate_streaming_response(query: str) -> AsyncGenerator[str, None]:
    """Generate a streaming response for the client"""
    try:
        yield "data: Thinking...\n\n"
        response = await generate_rag_response(query)
        content = response["response"]
        chunk_size = 10
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"

async def create_new_conversation(user_id: str) -> Dict[str, str]:
    """Create a new conversation"""
    try:
        result = await appwrite_db.create_document(
            database_id="arabia_db",
            collection_id="conversations",
            document_id="unique()",
            data={
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "title": "New Conversation"
            }
        )
        
        return {"conversation_id": result["$id"]}
    except Exception as e:
        logger.error(f"Failed to create conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_user_conversations(user_id: str) -> List[Dict]:
    """Get all conversations for a user"""
    try:
        result = await appwrite_db.list_documents(
            database_id="arabia_db",
            collection_id="conversations",
            queries=[f'user_id="{user_id}"']
        )
        
        conversations = []
        for doc in result['documents']:
            conversations.append({
                "conversation_id": doc["$id"],
                "title": doc.get("title", "Untitled"),
                "created_at": doc["created_at"]
            })
        
        return conversations
    except Exception as e:
        logger.error(f"Failed to list conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))