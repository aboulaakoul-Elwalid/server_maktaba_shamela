# app/core/storage.py
import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import HTTPException, status # Added status import
from appwrite.services.databases import Databases
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.query import Query
from appwrite.exception import AppwriteException # Added AppwriteException import
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Helper function moved from chat_service
def extract_book_id(document_id: str) -> str:
    """Extract the book ID from the document ID format (usually book_id_section_id)"""
    if not document_id:
        return ""
    parts = document_id.split('_')
    if parts and parts[0].isdigit():
        return parts[0]
    return ""

def store_message(
    db: Databases,
    user_id: str,
    content: str,
    message_type: str,
    conversation_id: Optional[str] = None,
    sources: Optional[List[Dict]] = None,
    is_anonymous: bool = False
) -> Dict:
    """Store a message in the Appwrite database using the provided db client."""
    try:
        message_data = {
            "user_id": user_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat(),
        }

        if is_anonymous:
            # For anonymous users, we don't persist to DB, just return a structure
            # consistent with persisted messages for the RAG response flow.
            logger.debug(f"Handling anonymous message storage for user {user_id}")
            return {
                "user_id": user_id,
                "content": content,
                "message_id": f"anon_{uuid.uuid4().hex}",
                "message_type": message_type,
                "timestamp": message_data["timestamp"],
                "conversation_id": conversation_id,
                "sources": sources or [] # Ensure sources is a list
            }

        if conversation_id:
            message_data["conversation_id"] = conversation_id
        else:
            logger.warning(f"Attempting to store message for user {user_id} without conversation_id")
            # Decide if this should be an error or if a conversation should be created implicitly
            # For now, let's raise an error if not anonymous and no conversation_id
            raise ValueError("conversation_id is required for non-anonymous users")


        logger.debug(f"Storing message for user {user_id} in conversation {conversation_id}")
        message_result = db.create_document(
            database_id=settings.APPWRITE_DATABASE_ID,
            collection_id=settings.APPWRITE_MESSAGES_COLLECTION_ID,
            document_id="unique()",
            data=message_data,
            permissions=[
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id))
            ]
        )
        logger.info(f"Stored message {message_result['$id']} for user {user_id}")

        # Store sources if they exist and user is not anonymous
        stored_source_ids = []
        if sources:
            logger.debug(f"Storing {len(sources)} sources for message {message_result['$id']}")
            try:
                for source in sources:
                    book_id = extract_book_id(source.get("document_id", ""))
                    url = f"https://shamela.ws/book/{book_id}" if book_id else ""
                    source["url"] = url # Add URL to the source dict for the return value

                    source_data = {
                        "message_id": message_result["$id"],
                        "title": f"{source.get('book_name', 'Unknown')} - {source.get('section_title', 'Unknown')}",
                        "content": source.get("content", ""), # Use "content" key from the formatted source
                        "url": url,
                        "metadata": json.dumps({ # Store detailed metadata as JSON string
                            "book_name": source.get("book_name", "Unknown"),
                            "section_title": source.get("section_title", "Unknown"),
                            "relevance": source.get("relevance", 0), # Assuming relevance is score
                            "document_id": source.get("document_id", "")
                        }, ensure_ascii=False) # <-- ADD ensure_ascii=False HERE
                    }

                    source_doc = db.create_document(
                        database_id=settings.APPWRITE_DATABASE_ID,
                        collection_id=settings.APPWRITE_MESSAGE_SOURCES_COLLECTION_ID,
                        document_id="unique()",
                        data=source_data,
                        permissions=[
                            Permission.read(Role.user(user_id)),
                            # Sources are usually read-only once created with the message
                        ]
                    )
                    stored_source_ids.append(source_doc['$id'])
                logger.info(f"Stored {len(stored_source_ids)} sources for message {message_result['$id']}")
            except Exception as source_error:
                # Log warning but don't fail the entire message storage
                logger.warning(f"Could not store sources for message {message_result['$id']}: {str(source_error)}")

        # Return a dictionary matching the structure expected by the caller
        return {
            "user_id": message_result["user_id"],
            "content": message_result["content"],
            "message_id": message_result["$id"],
            "message_type": message_result["message_type"],
            "timestamp": message_result["timestamp"],
            "conversation_id": message_result.get("conversation_id"),
            "sources": sources # Return the original sources list with added URLs
        }
    except Exception as e:
        logger.exception(f"Failed to store message for user {user_id}: {str(e)}")
        # Re-raise as HTTPException for the API layer
        raise HTTPException(status_code=500, detail=f"Failed to store message.")


def create_new_conversation(db: Databases, user_id: str, is_anonymous: bool) -> Dict[str, str]:
    """Creates a new conversation document in Appwrite."""
    conversation_id = uuid.uuid4().hex
    # Generate ISO format string *without* microseconds to fit size=30 limit
    now_iso_truncated = datetime.now(timezone.utc).isoformat(timespec='seconds')
    # Example: '2025-04-26T21:00:00+00:00' (25 chars)

    title = f"Chat {now_iso_truncated.split('T')[0]}" # Use truncated time for title too

    try:
        logger.info(f"Attempting to create conversation {conversation_id} for user {user_id}")
        document_data = {
            "user_id": user_id,
            "title": title,
            # Use the truncated timestamp string
            "created_at": now_iso_truncated,
            "is_anonymous": is_anonymous
        }

        result = db.create_document(
            database_id=settings.APPWRITE_DATABASE_ID,
            collection_id=settings.APPWRITE_CONVERSATIONS_COLLECTION_ID,
            document_id=conversation_id,
            data=document_data,
            permissions=[
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id)),
            ] if not is_anonymous else []
        )
        logger.info(f"Successfully created conversation {result['$id']}")
        return {"conversation_id": result['$id'], "message": "Conversation created successfully"}

    except AppwriteException as e:
        logger.error(f"Failed to create conversation for user {user_id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to create conversation: {e.message}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error creating conversation for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the conversation."
        )


def get_user_conversations(
    db: Databases,
    user_id: str
) -> List[Dict]:
    """Get all conversations for a user using the provided db client."""
    # Note: This function does not apply to anonymous users as they don't have stored conversations.
    # The API endpoint should handle the case where an anonymous user tries to list conversations.
    if not user_id or user_id.startswith("anon_"):
         logger.warning("Attempted to get conversations for an anonymous or invalid user ID.")
         return []

    try:
        logger.info(f"Fetching conversations for user: {user_id}")

        # Query Appwrite for conversations belonging to the user
        result = db.list_documents(
            database_id=settings.APPWRITE_DATABASE_ID,
            collection_id=settings.APPWRITE_CONVERSATIONS_COLLECTION_ID,
            queries=[
                Query.equal("user_id", user_id),
                Query.order_desc("last_updated") # Order by most recently updated
            ]
        )

        total_found = result.get('total', 0)
        logger.info(f"Found {total_found} conversations for user: {user_id}")

        # Format the response
        conversations = [
            {
                '$id': doc.get('$id'),
                'title': doc.get('title', 'Untitled Conversation'),
                'created_at': doc.get('created_at'),
                'last_updated': doc.get('last_updated') # Include last updated time
            } for doc in result.get('documents', [])
        ]
        return conversations

    except Exception as e:
        logger.exception(f"Failed to list conversations for user {user_id}: {str(e)}")
        # Return empty list on error, or consider raising HTTPException
        return []

def update_conversation_timestamp(db: Databases, conversation_id: str):
    """Updates the last_updated timestamp of a conversation."""
    if conversation_id.startswith("anon_conv_"):
        logger.debug(f"Skipping timestamp update for anonymous conversation {conversation_id}")
        return # No need to update for anonymous

    try:
        logger.debug(f"Updating timestamp for conversation {conversation_id}")
        db.update_document(
            database_id=settings.APPWRITE_DATABASE_ID,
            collection_id=settings.APPWRITE_CONVERSATIONS_COLLECTION_ID,
            document_id=conversation_id,
            data={"last_updated": datetime.now().isoformat()}
        )
        logger.info(f"Timestamp updated for conversation {conversation_id}")
    except Exception as e:
        # Log error but don't let it block the chat flow
        logger.error(f"Failed to update timestamp for conversation {conversation_id}: {e}")
