# app/core/chat_service.py
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import logging
from fastapi import HTTPException
from app.core.clients import appwrite_db
from app.core.rag import generate_rag_response as core_generate_rag_response
from appwrite.permission import Permission
from appwrite.role import Role
import json
from app.core.retrieval import query_vector_store
from app.core.clients import mistral_client  # Make sure this is correctly imported
import requests
import asyncio

logger = logging.getLogger(__name__)

# Fix store_message function
import uuid

async def store_message(user_id: str, content: str, message_type: str, 
                       conversation_id: Optional[str] = None, 
                       sources: Optional[List[Dict]] = None,
                       is_anonymous: bool = False) -> Dict:
    """Store a message in the Appwrite database"""
    try:
        # Create message data
        message_data = {
            "user_id": user_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat(),
        }
        
        # For anonymous users, don't store in database
        if is_anonymous:
            logger.info(f"Anonymous user message, not storing in database")
            return {
                "user_id": user_id,
                "content": content,
                "message_id": f"anon_{uuid.uuid4().hex}",
                "message_type": message_type,
                "timestamp": message_data["timestamp"],
                "conversation_id": conversation_id,
                "sources": sources
            }
        
        # For authenticated users, continue with database storage
        if conversation_id:
            message_data["conversation_id"] = conversation_id
            
        if sources:
            message_data["sources"] = sources
        
        # Store in Appwrite
        message_result = appwrite_db.create_document(
            database_id="arabia_db",
            collection_id="messages",
            document_id="unique()",
            data=message_data,
            permissions=[
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id))
            ]
        )
        
        return {
            "user_id": message_result["user_id"],
            "content": message_result["content"],
            "message_id": message_result["$id"],
            "message_type": message_result["message_type"],
            "timestamp": message_result["timestamp"],
            "conversation_id": message_result.get("conversation_id"),
            "sources": message_result.get("sources")
        }
    except Exception as e:
        logger.error(f"Failed to store message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store message: {str(e)}")

async def generate_rag_response(query: str) -> Dict[str, Any]:
    """Generate an AI response using RAG with direct Mistral API call"""
    try:
        # 1. Retrieve relevant documents
        logger.debug(f"Retrieving documents for query: {query[:50]}...")
        try:
            documents = query_vector_store(query_text=query, top_k=5)
            logger.debug(f"Retrieved {len(documents) if documents else 0} documents")
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return {
                "response": "I encountered an error retrieving relevant information. Please try again later.",
                "context": []
            }
            
        if not documents or len(documents) == 0:
            logger.warning("No relevant documents found for query")
            return {
                "response": "I couldn't find any relevant information to answer your question about Arabia. Could you please rephrase or ask a different question?",
                "context": []
            }
        
        # 2. Format documents into context for the LLM
        try:
            logger.debug("Formatting documents into context")
            context_text = ""
            sources = []
            
            for i, doc in enumerate(documents):
                # Get document properties - adapt these field names based on your schema
                doc_text = getattr(doc, 'text', None)
                if doc_text is None:
                    doc_text = getattr(doc, 'content', "No text available")
                
                book_name = doc.metadata.book_name if hasattr(doc.metadata, 'book_name') else "Unknown book"
                section_title = doc.metadata.section_title if hasattr(doc.metadata, 'section_title') else "Unknown section"
                
                # Add document text to context
                context_text += f"\nDocument {i+1}:\n{doc_text}\n"
                context_text += f"Source: {book_name}, {section_title}\n\n"
                
                # Save source information for the response
                sources.append({
                    "book_name": book_name,
                    "section_title": section_title,
                    "text_snippet": doc_text[:100] + "...." if doc_text else "No text available",
                    "relevance": doc.score,
                    "document_id": getattr(doc, 'id', f"doc_{i}")
                })
            logger.debug("Context formatting complete")
        except Exception as e:
            logger.error(f"Error formatting context: {str(e)}")
            return {
                "response": "I encountered an error processing the documents. Please try again later.",
                "context": []
            }
        
        # 3. Create prompt for the LLM
        prompt = f"""You are a helpful assistant that specializes in providing information about the history, culture, and society of the Arab world. You are also an expert in Islamic texts and traditions. Use the following context to answer the user's question.

    Context:
    {context_text}

    Question: {query}

    Answer:
    """
        
        # 4. Call Mistral API to generate a response
        try:
            logger.debug("Calling Mistral API directly via HTTP")
            
            from app.config.settings import settings
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}"
                },
                json={
                    "model": "mistral-saba-2502",  # Adjust as needed
                    "messages": [
                        {"role": "system", "content": "You are a knowledgeable assistant specializing in Arabic and Islamic texts."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.99,
                    "max_tokens": 1000
                },
                timeout=30  # Add timeout to prevent hanging
            )
            
            if response.status_code != 200:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return {
                    "response": f"I encountered an error generating a response. Status code: {response.status_code}",
                    "context": sources
                }
            
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            
            logger.debug("Successfully received response from Mistral API")
            return {
                "response": answer,
                "context": sources
            }
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error generating a response: {str(e)}",
                "context": sources
            }
    except Exception as e:
        logger.error(f"Error in RAG pipeline: {str(e)}")
        return {
            "response": "I apologize, but I encountered an error processing your question. Please try again later.",
            "context": []
        }

async def generate_streaming_response(query: str) -> AsyncGenerator[str, None]:
    """Generate a streaming response for the client"""
    try:
        yield "data: Thinking...\n\n"
        
        # Get RAG response
        response = await generate_rag_response(query)
        content = response["response"]
        sources = response.get("context", [])
        
        # Stream the response in small chunks to simulate typing
        chunk_size = 10  # Characters per chunk
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0.05)  # Small delay to make it more natural
            
        # Send sources information if available
        if sources:
            yield "\n\ndata: Sources:\n\n"
            for i, source in enumerate(sources):
                yield f"data: [{i+1}] {source['book_name']} - {source['section_title']}\n\n"
                await asyncio.sleep(0.05)
        
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in streaming response: {str(e)}")
        yield f"data: Error: {str(e)}\n\n"
        yield "data: [DONE]\n\n"

async def create_new_conversation(user_id: str, is_anonymous: bool = False) -> Dict[str, str]:
    """Create a new conversation"""
    try:
        # For anonymous users, don't store in database
        if is_anonymous:
            conversation_id = f"anon_conv_{uuid.uuid4().hex}"
            return {
                "conversation_id": conversation_id,
                "message": "Anonymous conversation created"
            }
            
        # For authenticated users, store in Appwrite
        conversation_data = {
            "user_id": user_id,
            "title": "New Conversation",
            "created_at": datetime.now().isoformat()
        }
        
        # Create the conversation
        result = appwrite_db.create_document(
            database_id="arabia_db",
            collection_id="conversations",
            document_id="unique()",
            data=conversation_data,
            permissions=[
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id))
            ]
        )
        
        return {
            "conversation_id": result["$id"],
            "message": "Conversation created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_user_conversations(user_id: str, is_anonymous: bool = False) -> List[Dict]:
    """Get all conversations for a user"""
    try:
        # For anonymous users, return empty list (no stored conversations)
        if is_anonymous:
            return []
            
        # For authenticated users, query Appwrite
        result = appwrite_db.list_documents(
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