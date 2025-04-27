import pytest
from unittest.mock import MagicMock, call
from fastapi import HTTPException
from appwrite.services.databases import Databases
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.exception import AppwriteException

try:
    from app.core.storage import store_message, create_new_conversation # Add others if needed
    from app.config.settings import settings # Needed for collection IDs
except ImportError:
     pytest.skip("Skipping storage tests: Could not import.", allow_module_level=True)

# Fixture for mocked Appwrite Databases service
@pytest.fixture
def mock_db(mocker):
    mock = mocker.MagicMock(spec=Databases)
    # Default return value for create_document
    mock.create_document.return_value = {'$id': 'new_doc_id', '$collectionId': 'test_coll', '$databaseId': settings.APPWRITE_DATABASE_ID}
    return mock

def test_store_message_user(mock_db):
    """Test storing a user message."""
    user_id = "user123"
    content = "Hello AI"
    message_type = "user"
    conversation_id = "conv456"

    result = store_message(
        db=mock_db,
        user_id=user_id,
        content=content,
        message_type=message_type,
        conversation_id=conversation_id,
        is_anonymous=False
    )

    assert result['$id'] == 'new_doc_id'
    mock_db.create_document.assert_called_once_with(
        database_id=settings.APPWRITE_DATABASE_ID,
        collection_id=settings.APPWRITE_MESSAGES_COLLECTION_ID,
        document_id='unique()',
        data={
            'user_id': user_id,
            'content': content,
            'message_type': message_type,
            'conversation_id': conversation_id,
            'is_anonymous': False
        },
        permissions=[
            Permission.read(Role.user(user_id)),
            Permission.update(Role.user(user_id)),
            Permission.delete(Role.user(user_id)),
        ]
    )

def test_store_message_ai_with_sources(mock_db):
    """Test storing an AI message with sources."""
    user_id = "ai_user" # Or however you represent the AI user
    content = "Here is the answer."
    message_type = "ai"
    conversation_id = "conv789"
    sources = [
        {"document_id": "doc1", "book_id": "1", "title": "Title 1", "content": "Snippet 1", "score": 0.9, "url": "url1"},
        {"document_id": "doc2", "book_id": "2", "title": "Title 2", "content": "Snippet 2", "score": 0.8, "url": "url2"},
    ]

    # Mock return values for multiple calls if needed (e.g., different IDs)
    mock_db.create_document.side_effect = [
        {'$id': 'ai_msg_id', '$collectionId': settings.APPWRITE_MESSAGES_COLLECTION_ID, '$databaseId': settings.APPWRITE_DATABASE_ID}, # AI message
        {'$id': 'source1_id', '$collectionId': settings.APPWRITE_SOURCES_COLLECTION_ID, '$databaseId': settings.APPWRITE_DATABASE_ID}, # Source 1
        {'$id': 'source2_id', '$collectionId': settings.APPWRITE_SOURCES_COLLECTION_ID, '$databaseId': settings.APPWRITE_DATABASE_ID}, # Source 2
    ]

    result = store_message(
        db=mock_db,
        user_id=user_id,
        content=content,
        message_type=message_type,
        conversation_id=conversation_id,
        sources=sources,
        is_anonymous=False # Assuming AI messages aren't anonymous here
    )

    assert result['$id'] == 'ai_msg_id' # Returns the AI message doc

    # Check calls
    assert mock_db.create_document.call_count == 3

    # Call 1: AI Message
    ai_call = mock_db.create_document.call_args_list[0]
    assert ai_call.kwargs['collection_id'] == settings.APPWRITE_MESSAGES_COLLECTION_ID
    assert ai_call.kwargs['data']['content'] == content
    assert ai_call.kwargs['data']['message_type'] == 'ai'
    # Check permissions if AI messages have specific read permissions

    # Call 2: Source 1
    source1_call = mock_db.create_document.call_args_list[1]
    assert source1_call.kwargs['collection_id'] == settings.APPWRITE_SOURCES_COLLECTION_ID
    assert source1_call.kwargs['data']['message_id'] == 'ai_msg_id' # Linked to AI message
    assert source1_call.kwargs['data']['document_id'] == 'doc1'
    assert source1_call.kwargs['data']['content'] == 'Snippet 1'
    assert source1_call.kwargs['data']['title'] == 'Title 1'
    # Check permissions for sources

    # Call 3: Source 2
    source2_call = mock_db.create_document.call_args_list[2]
    assert source2_call.kwargs['collection_id'] == settings.APPWRITE_SOURCES_COLLECTION_ID
    assert source2_call.kwargs['data']['message_id'] == 'ai_msg_id'
    assert source2_call.kwargs['data']['document_id'] == 'doc2'
    assert source2_call.kwargs['data']['content'] == 'Snippet 2'

def test_store_message_anonymous(mock_db):
    """Test storing an anonymous user message."""
    user_id = "anon_user_placeholder" # Or however you handle anon ID
    content = "Anon question"
    message_type = "user"
    conversation_id = "conv_anon"

    result = store_message(
        db=mock_db,
        user_id=user_id,
        content=content,
        message_type=message_type,
        conversation_id=conversation_id,
        is_anonymous=True
    )

    assert result['$id'] == 'new_doc_id'
    call_args = mock_db.create_document.call_args
    assert call_args.kwargs['data']['is_anonymous'] is True
    # Check permissions for anonymous users (likely Role.any() for read if public)
    assert Permission.read(Role.any()) in call_args.kwargs['permissions']
    # Ensure user-specific permissions are NOT present
    assert Permission.read(Role.user(user_id)) not in call_args.kwargs['permissions']


def test_store_message_appwrite_error(mock_db):
    """Test handling of AppwriteException during storage."""
    mock_db.create_document.side_effect = AppwriteException("Network Error", 500, "network_error")

    with pytest.raises(HTTPException) as exc_info:
        store_message(
            db=mock_db,
            user_id="user1",
            content="Test",
            message_type="user",
            conversation_id="conv1"
        )
    assert exc_info.value.status_code == 503 # Service Unavailable
    assert "Failed to store message in database" in exc_info.value.detail

# Add tests for create_new_conversation, get_user_conversations etc. mocking list_documents etc.