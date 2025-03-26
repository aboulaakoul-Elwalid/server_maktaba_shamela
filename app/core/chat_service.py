# app/core/chat_service.py
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import logging
from fastapi import HTTPException
from app.core.clients import appwrite_db
from app.core.rag import generate_rag_response as core_generate_rag_response
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.query import Query
import json
from app.core.retrieval import query_vector_store
from app.core.clients import mistral_client
import requests
import asyncio
import uuid
import random
import time

logger = logging.getLogger(__name__)

# Helper function to extract book_id from document_id
def extract_book_id(document_id: str) -> str:
    """Extract the book ID from the document ID format (usually book_id_section_id)"""
    if not document_id:
        return ""
    
    # Parse the document_id which is usually in format like "6315_0_2_0_264"
    # The first part is typically the book_id
    parts = document_id.split('_')
    if parts and parts[0].isdigit():
        return parts[0]
    return ""

def store_message(user_id: str, content: str, message_type: str, 
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
        
        # For anonymous users, handle without database storage
        if is_anonymous:
            # Add URLs to sources for anonymous users
            if sources:
                for source in sources:
                    book_id = extract_book_id(source.get("document_id", ""))
                    source["url"] = f"https://shamela.ws/book/{book_id}" if book_id else ""
            
            return {
                "user_id": user_id,
                "content": content,
                "message_id": f"anon_{uuid.uuid4().hex}",
                "message_type": message_type,
                "timestamp": message_data["timestamp"],
                "conversation_id": conversation_id,
                "sources": sources
            }
        
        # For authenticated users, handle with database storage
        if conversation_id:
            message_data["conversation_id"] = conversation_id
        
        # Store the message - Appwrite SDK is synchronous, don't use await
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
        
        # Process sources
        if sources and not is_anonymous:
            try:
                for source in sources:
                    # Add URL to source
                    book_id = extract_book_id(source.get("document_id", ""))
                    url = f"https://shamela.ws/book/{book_id}" if book_id else ""
                    source["url"] = url
                    
                    # Store in message_sources collection
                    appwrite_db.create_document(
                        database_id="arabia_db",
                        collection_id="message_sources",
                        document_id="unique()",
                        data={
                            "message_id": message_result["$id"],
                            "title": f"{source.get('book_name', 'Unknown')} - {source.get('section_title', 'Unknown')}",
                            "content": source.get("text_snippet", ""),
                            "url": url,
                            "metadata": json.dumps({
                                "book_name": source.get("book_name", "Unknown"),
                                "section_title": source.get("section_title", "Unknown"),
                                "text_snippet": source.get("text_snippet", ""),
                                "relevance": source.get("relevance", 0),
                                "document_id": source.get("document_id", "")
                            })
                        },
                        permissions=[
                            Permission.read(Role.user(user_id)),
                            Permission.update(Role.user(user_id)),
                            Permission.delete(Role.user(user_id))
                        ]
                    )
            except Exception as source_error:
                logger.warning(f"Could not store sources: {str(source_error)}")
        
        # Return the message with sources
        return {
            "user_id": message_result["user_id"],
            "content": message_result["content"],
            "message_id": message_result["$id"],
            "message_type": message_result["message_type"],
            "timestamp": message_result["timestamp"],
            "conversation_id": message_result.get("conversation_id"),
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Failed to store message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store message: {str(e)}")

def call_mistral_with_retry(prompt, max_retries=3, base_delay=1.0):
    """Call Mistral API with exponential backoff retry logic for rate limits"""
    from app.config.settings import settings
    import requests
    
    logger.info(f"Calling Mistral API with retry (max attempts: {max_retries})")
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Mistral API attempt {attempt+1}/{max_retries}")
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}"
                },
                json={
                    "model": "mistral-saba-2502",
                    "messages": [
                        {"role": "system", "content": "You are a knowledgeable assistant specializing in Arabic and Islamic texts."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            # Success - return the response
            if response.status_code == 200:
                logger.info("Mistral API call successful")
                return response
                
            # Handle rate limits with exponential backoff
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) * base_delay + random.random()
                    logger.warning(f"Rate limit (429) hit. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                else:
                    logger.error("Maximum retry attempts reached for rate limit")
            
            # Other error statuses - log and return
            logger.error(f"Mistral API error: {response.status_code} - {response.text}")
            return response
            
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) * base_delay + random.random()
                logger.warning(f"API call failed: {str(e)}. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error(f"All retry attempts failed: {str(e)}")
                raise
    
    # If we get here, all retries failed with rate limits
    raise Exception("Failed to call Mistral API after multiple retries")

def call_gemini_api(prompt):
    """Call Google Gemini as fallback when Mistral fails or gets rate limited"""
    import google.generativeai as genai
    from app.config.settings import settings
    
    logger.info("Falling back to Google Gemini API")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=settings.API_KEY_GOOGLE)
        
        # Create model instance
        model = genai.GenerativeModel("gemini-pro")
        
        # Generate response
        response = model.generate_content(prompt)
        
        if response and hasattr(response, 'text'):
            logger.info("Successfully received response from Gemini API")
            return {
                "success": True,
                "content": response.text
            }
        else:
            logger.error("Gemini API returned invalid response")
            return {
                "success": False, 
                "error": "Invalid response from Gemini"
            }
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return {"success": False, "error": str(e)}

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
                "response": "I'm having trouble finding relevant information right now. Please try again in a moment.",
                "context": []
            }
            
        if not documents or len(documents) == 0:
            logger.warning("No relevant documents found for query")
            return {
                "response": "I couldn't find specific information about that topic in my knowledge base. Could you try rephrasing your question?",
                "context": []
            }
        
        # 2. Format documents into context for the LLM
        try:
            logger.debug("Formatting documents into context")
            context_text = ""
            sources = []
            
            for i, doc in enumerate(documents):
                # Get document properties
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
        except Exception as e:
            logger.error(f"Error formatting context: {str(e)}")
            return {
                "response": "I'm having trouble processing the information for your question. Please try again later.",
                "context": []
            }
        
        # 3. Create prompt for the LLM
        prompt = f"""You are a helpful assistant that specializes in providing information about the history, culture, and society of the Arab world. You are also an expert in Islamic texts and traditions. Use the following context to answer the user's question.

    Context:
    {context_text}

    Question: {query}

    Answer:
    """
        
        # 4. Try Mistral API first, fall back to Gemini if needed
        try:
            # Use the retry function for Mistral
            mistral_response = None
            gemini_response = None
            answer = None
            model_used = "mistral"
            fallback_used = False
            
            try:
                mistral_response = call_mistral_with_retry(prompt)
                
                # If Mistral succeeds, use its response
                if mistral_response.status_code == 200:
                    data = mistral_response.json()
                    answer = data["choices"][0]["message"]["content"]
                    logger.info("Using Mistral response")
                else:
                    # Mistral failed, try Gemini
                    logger.warning(f"Mistral API failed with status {mistral_response.status_code}, trying Gemini...")
                    gemini_response = call_gemini_api(prompt)
                    
                    if gemini_response["success"]:
                        answer = gemini_response["content"]
                        model_used = "gemini"
                        fallback_used = True
                        logger.info("Using Gemini response (fallback)")
                    else:
                        # Both APIs failed
                        logger.error("Both Mistral and Gemini failed")
                        return {
                            "response": "I apologize, but all available AI services are currently experiencing issues. Please try again later.",
                            "context": sources
                        }
            except Exception as mistral_error:
                # Mistral exception, try Gemini
                logger.error(f"Mistral API exception: {str(mistral_error)}, trying Gemini...")
                gemini_response = call_gemini_api(prompt)
                
                if gemini_response["success"]:
                    answer = gemini_response["content"]
                    model_used = "gemini"
                    fallback_used = True
                    logger.info("Using Gemini response (fallback after exception)")
                else:
                    # Both APIs failed
                    logger.error("Both Mistral and Gemini failed")
                    return {
                        "response": "I apologize, but all available AI services are currently experiencing issues. Please try again later.",
                        "context": sources
                    }
            
            # Return the answer with model info
            return {
                "response": answer,
                "context": sources,
                "model_used": model_used,
                "fallback_used": fallback_used
            }
        except Exception as e:
            logger.error(f"Error in LLM response generation: {str(e)}")
            return {
                "response": "I apologize, but I'm having trouble processing your question right now. Please try again later.",
                "context": sources
            }
    except Exception as e:
        logger.error(f"Error in RAG pipeline: {str(e)}")
        return {
            "response": "I'm experiencing technical difficulties at the moment. Please try again later.",
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
        
        # Add URLs to sources before streaming
        for source in sources:
            # Extract book_id from document_id
            book_id = extract_book_id(source.get("document_id", ""))
            source["url"] = f"https://shamela.ws/book/{book_id}" if book_id else ""
        
        # Stream the response in chunks
        chunk_size = 100
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0.1)
            
        # Send sources information with URLs
        if sources:
            yield "\n\ndata: Sources:\n\n"
            for i, source in enumerate(sources):
                source_text = f"[{i+1}] {source['book_name']} - {source['section_title']}"
                # Add URL if available
                if source.get("url"):
                    source_text += f" ({source['url']})"
                yield f"data: {source_text}\n\n"
                await asyncio.sleep(0.05)
        
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in streaming response: {str(e)}")
        yield f"data: Error: {str(e)}\n\n"
        yield "data: [DONE]\n\n"

def create_new_conversation(user_id: str, is_anonymous: bool = False) -> Dict[str, str]:
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
        
        # Create the conversation - Appwrite SDK is synchronous, don't use await
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
    
def get_user_conversations(user_id: str) -> List[Dict]:
    """Get all conversations for a user"""
    try:
        # Log the request for debugging
        logger.info(f"Getting conversations for user: {user_id}")
        
        # Get all documents - Appwrite SDK is synchronous, don't use await
        result = appwrite_db.list_documents(
            database_id="arabia_db",
            collection_id="conversations",
            queries=[Query.equal("user_id", user_id)]
        )
        
        # Log what we got back
        logger.info(f"Got {len(result.get('documents', []))} conversations for user: {user_id}")
        
        # Format conversations
        conversations = []
        for doc in result.get('documents', []):
            conversations.append({
                "conversation_id": doc["$id"],
                "title": doc.get("title", "New Conversation"),
                "created_at": doc.get("created_at", "")
            })
        
        return conversations
    except Exception as e:
        logger.error(f"Failed to list conversations: {str(e)}")
        # Return empty list instead of error
        return []