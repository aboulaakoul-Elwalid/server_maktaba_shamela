import pytest

try:
    from app.core.retrieval import get_retriever
    from app.core.retrieval.pinecone import PineconeRetriever
    # Import other retriever types if you add them later
    # from app.core.retrieval.other_retriever import OtherRetriever
    from app.config.settings import Settings
except ImportError:
     pytest.skip("Skipping retriever factory tests: Could not import.", allow_module_level=True)

def test_get_retriever_pinecone(mocker):
    """Test getting PineconeRetriever when provider is 'pinecone'."""
    mock_settings = Settings(RETRIEVER_PROVIDER='pinecone') # Create dummy settings
    mocker.patch('app.core.retrieval.settings', mock_settings) # Mock the settings used by get_retriever

    retriever = get_retriever()
    assert isinstance(retriever, PineconeRetriever)

def test_get_retriever_unknown(mocker):
    """Test getting an unknown retriever provider."""
    mock_settings = Settings(RETRIEVER_PROVIDER='unknown_provider')
    mocker.patch('app.core.retrieval.settings', mock_settings)

    with pytest.raises(ValueError, match="Unknown retriever provider: unknown_provider"):
        get_retriever()

# Add tests for other providers if you implement them
# def test_get_retriever_other(mocker):
#     mock_settings = Settings(RETRIEVER_PROVIDER='other')
#     mocker.patch('app.core.retrieval.settings', mock_settings)
#     retriever = get_retriever()
#     assert isinstance(retriever, OtherRetriever)