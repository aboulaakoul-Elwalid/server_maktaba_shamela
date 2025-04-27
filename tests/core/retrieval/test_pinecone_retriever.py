import pytest
from unittest.mock import MagicMock, AsyncMock

# Assuming your retriever is here
try:
    from app.core.retrieval.pinecone import PineconeRetriever
    from app.models.schemas import DocumentMatch, DocumentMetadata
except ImportError:
    pytest.skip("Skipping pinecone retriever tests: Could not import.", allow_module_level=True)

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_pinecone_index(mocker):
    """Mocks the Pinecone index object."""
    mock_index = MagicMock()
    # Configure the mock query method
    mock_index.query.return_value = {
        'matches': [
            {
                'id': 'doc1',
                'score': 0.9,
                'metadata': {'text': 'Content 1', 'book_id': '10', 'book_name': 'Book 1'}
            },
            {
                'id': 'doc2_float_id',
                'score': 0.8,
                'metadata': {'text': 'Content 2', 'book_id': 20.0, 'book_name': 'Book 2'} # Test float conversion
            }
        ]
    }
    return mock_index

@pytest.fixture
def mock_get_pinecone_index(mocker, mock_pinecone_index):
    """Mocks the get_pinecone_index function."""
    return mocker.patch('app.core.retrieval.pinecone.get_pinecone_index', return_value=mock_pinecone_index)

@pytest.fixture
def mock_get_text_embedding(mocker):
    """Mocks the get_text_embedding function."""
    # Return a dummy embedding vector
    return mocker.patch('app.core.retrieval.pinecone.get_text_embedding', return_value=[0.1, 0.2, 0.3])

async def test_retrieve_success(mock_get_pinecone_index, mock_get_text_embedding, mock_pinecone_index):
    """Test successful retrieval."""
    retriever = PineconeRetriever()
    query = "test query"
    top_k = 2

    matches = await retriever.retrieve(query, top_k)

    assert len(matches) == 2
    assert isinstance(matches[0], DocumentMatch)
    assert matches[0].id == 'doc1'
    assert matches[0].score == 0.9
    assert matches[0].metadata.text == 'Content 1'
    assert matches[0].metadata.book_id == '10' # Should be string
    assert matches[1].id == 'doc2_float_id'
    assert matches[1].metadata.book_id == '20' # Should be converted to string '20'

    # Check if dependencies were called
    mock_get_text_embedding.assert_called_once_with(query)
    mock_pinecone_index.query.assert_called_once()
    # You can add more specific assertions on the query arguments if needed

async def test_retrieve_no_matches(mock_get_pinecone_index, mock_get_text_embedding, mock_pinecone_index):
    """Test retrieval when Pinecone returns no matches."""
    mock_pinecone_index.query.return_value = {'matches': []} # Override fixture
    retriever = PineconeRetriever()
    matches = await retriever.retrieve("query", 5)
    assert matches == []

async def test_retrieve_embedding_failure(mock_get_pinecone_index, mock_get_text_embedding, mock_pinecone_index):
    """Test retrieval when text embedding fails."""
    mock_get_text_embedding.return_value = None # Simulate failure
    retriever = PineconeRetriever()
    matches = await retriever.retrieve("query", 5)
    assert matches == []
    mock_pinecone_index.query.assert_not_called() # Pinecone shouldn't be queried

async def test_retrieve_pinecone_index_failure(mock_get_pinecone_index, mock_get_text_embedding):
    """Test retrieval when getting the Pinecone index fails."""
    mock_get_pinecone_index.return_value = None # Simulate failure
    retriever = PineconeRetriever()
    matches = await retriever.retrieve("query", 5)
    assert matches == []
    mock_get_text_embedding.assert_not_called() # Embedding shouldn't be generated

async def test_retrieve_pinecone_query_error(mock_get_pinecone_index, mock_get_text_embedding, mock_pinecone_index, caplog):
    """Test retrieval when the index.query call raises an exception."""
    mock_pinecone_index.query.side_effect = Exception("Pinecone connection error")
    retriever = PineconeRetriever()
    matches = await retriever.retrieve("query", 5)
    assert matches == []
    assert "CRITICAL Error querying Pinecone vector store: Pinecone connection error" in caplog.text

async def test_retrieve_pydantic_error_skips_match(mock_get_pinecone_index, mock_get_text_embedding, mock_pinecone_index, caplog):
    """Test that a document causing a Pydantic error (other than book_id) is skipped."""
    mock_pinecone_index.query.return_value = {
        'matches': [
            {
                'id': 'valid_doc', 'score': 0.9, 'metadata': {'text': 'Valid', 'book_id': '1'}
            },
            {
                 # Simulate metadata missing required 'text' field after retrieval
                'id': 'invalid_doc', 'score': 0.8, 'metadata': {'book_id': '2'}
            }
        ]
    }
    retriever = PineconeRetriever()
    matches = await retriever.retrieve("query", 5)

    assert len(matches) == 1 # Only the valid doc should be returned
    assert matches[0].id == 'valid_doc'
    assert "Pydantic validation failed for metadata of match ID invalid_doc" in caplog.text