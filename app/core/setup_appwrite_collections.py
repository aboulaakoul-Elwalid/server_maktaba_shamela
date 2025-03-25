# setup_appwrite_collections.py
import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.id import ID
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Appwrite client
def get_appwrite_client():
    client = Client()
    client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1'))
    client.set_project(os.environ.get('APPWRITE_PROJECT_ID'))
    client.set_key(os.environ.get('APPWRITE_API_KEY'))
    return client

async def setup_appwrite_collections():
    client = get_appwrite_client()
    databases = Databases(client)
    
    # 1. Create database if it doesn't exist
    try:
        database = databases.create(
            database_id='arabia_db',
            name='Arabia Database'
        )
        print("✅ Created database: arabia_db")
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("ℹ️ Database arabia_db already exists")
        else:
            print(f"❌ Database creation error: {str(e)}")
            return
    
    # 2. Create conversations collection
    try:
        conversations = databases.create_collection(
            database_id='arabia_db',
            collection_id='conversations',
            name='Conversations',
            permissions=[
                Permission.read(Role.users()),  # Only authenticated users can read
                Permission.create(Role.users()),  # Only authenticated users can create
                Permission.update(Role.users()),  # Only authenticated users can update
                Permission.delete(Role.users()),  # Only authenticated users can delete
            ],
            document_security=True  # Enable document-level security
        )
        print("✅ Created collection: conversations")
        
        # Add attributes to conversations collection
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='conversations',
            key='user_id',
            size=36,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='conversations',
            key='title',
            size=100,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='conversations',
            key='created_at',
            size=30,
            required=True
        )
        print("✅ Added attributes to conversations collection")
        
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("ℹ️ Collection conversations already exists")
        else:
            print(f"❌ Collection creation error: {str(e)}")
    
    # 3. Create messages collection
    try:
        messages = databases.create_collection(
            database_id='arabia_db',
            collection_id='messages',
            name='Messages',
            permissions=[
                Permission.read(Role.users()),  # Only authenticated users can read
                Permission.create(Role.users()),  # Only authenticated users can create
            ],
            document_security=True  # Enable document-level security
        )
        print("✅ Created collection: messages")
        
        # Add attributes to messages collection
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='messages',
            key='user_id',
            size=36,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='messages',
            key='content',
            size=16000,  # Long text size
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='messages',
            key='message_type',
            size=10,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='messages',
            key='timestamp',
            size=30,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='messages',
            key='conversation_id',
            size=36,
            required=False
        )
        # Create a JSON attribute for sources
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='messages',
            key='sources',
            size=16000,  # Large size for JSON
            required=False,
            array=True
        )
        print("✅ Added attributes to messages collection")
        
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("ℹ️ Collection messages already exists")
        else:
            print(f"❌ Collection creation error: {str(e)}")

    # 3.5 Create sources collection
    try:
        sources = databases.create_collection(
            database_id='arabia_db',
            collection_id='sources',
            name='Message Sources',
            permissions=[
                Permission.read(Role.users()),  # Only authenticated users can read
                Permission.create(Role.users()),  # Only authenticated users can create
            ],
            document_security=True  # Enable document-level security
        )
        print("✅ Created collection: sources")
        
        # Add attributes to sources collection
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='sources',
            key='message_id',  # Reference to the parent message
            size=36,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='sources',
            key='title',
            size=200,
            required=False
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='sources',
            key='content',  # The excerpt from the source
            size=6000,
            required=True
        )
        databases.create_string_attribute(
            database_id='arabia_db',
            collection_id='sources',
            key='metadata',  # For storing JSON metadata
            size=2000,
            required=False
        )
        
        # Create an index for faster lookups by message_id
        databases.create_index(
            database_id='arabia_db',
            collection_id='sources',
            key='message_sources_lookup',
            type='key',
            attributes=['message_id']
        )
        print("✅ Added attributes and index to sources collection")
        
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("ℹ️ Collection sources already exists")
        else:
            print(f"❌ Source collection creation error: {str(e)}")

    # 4. Create indexes for faster queries
    try:
        # Index for conversation_id in messages collection
        databases.create_index(
            database_id='arabia_db',
            collection_id='messages',
            key='conversation_lookup',
            type='key',
            attributes=['conversation_id']
        )
        print("✅ Created index: conversation_lookup")
        
        # Index for user_id in conversations collection
        databases.create_index(
            database_id='arabia_db',
            collection_id='conversations',
            key='user_lookup',
            type='key',
            attributes=['user_id']
        )
        print("✅ Created index: user_lookup")
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("ℹ️ Indexes already exist")
        else:
            print(f"❌ Index creation error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(setup_appwrite_collections())