import pytest
from typing import List

# Assuming your formatter function is in app.core.context_formatter
# Adjust the import path if necessary
try:
    from app.core.context_formatter import format_context_and_extract_sources, CONTEXT_SNIPPET_MAX_LENGTH
    from app.models.schemas import DocumentMatch, DocumentMetadata
except ImportError as e:
    print(f"Error importing from app.core.context_formatter or app.models.schemas: {e}")
    # Define dummy classes/functions if import fails, so pytest can collect tests
    class DocumentMatch: pass
    class DocumentMetadata: pass
    def format_context_and_extract_sources(docs): return "Error", []
    CONTEXT_SNIPPET_MAX_LENGTH = 300 # Define a default if import fails


# Mark tests in this module as asyncio tests if they use async functions
# pytestmark = pytest.mark.asyncio

# --- Test Cases ---

def test_format_context_and_extract_sources_empty_docs():
    """
    Test format_context_and_extract_sources with an empty list of documents.
    It should return the specific "no context" string and an empty list.
    """
    input_documents: List[DocumentMatch] = []
    expected_context = "No relevant context found."
    expected_sources = []

    actual_context, actual_sources = format_context_and_extract_sources(input_documents)

    assert actual_context == expected_context
    assert actual_sources == expected_sources

def test_format_context_and_extract_sources_valid_doc_short_text():
    """
    Test format_context_and_extract_sources with a single valid document
    where the text is shorter than the max snippet length.
    """
    sample_text = "This is short content."
    sample_doc = DocumentMatch(
        id="book1_chap1_sec1",
        score=0.85,
        metadata=DocumentMetadata(
            text=sample_text,
            book_name="Book Of Samples",
            section_title="Chapter One",
            book_id="1",
            author_name="Author Name",
            category_name="Category"
        )
    )
    input_documents: List[DocumentMatch] = [sample_doc]

    actual_context, actual_sources = format_context_and_extract_sources(input_documents)

    # Check context string format
    assert "Source Document [ID: book1_chap1_sec1]" in actual_context
    assert "Book: Book Of Samples" in actual_context
    assert "Section: Chapter One" in actual_context
    assert f"Content: {sample_text}" in actual_context # Exact match, no truncation
    assert "..." not in actual_context # Ensure no ellipsis added

    # Check sources list structure
    assert len(actual_sources) == 1
    source_item = actual_sources[0]
    assert source_item["document_id"] == "book1_chap1_sec1"
    assert source_item["book_id"] == "1"
    assert source_item["book_name"] == "Book Of Samples"
    assert source_item["title"] == "Chapter One"
    assert source_item["score"] == 0.85
    assert "content" in source_item
    assert source_item["content"] == sample_text # Exact match
    assert source_item["url"] == "https://shamela.ws/book/1"

def test_format_context_and_extract_sources_valid_doc_long_text():
    """
    Test format_context_and_extract_sources with a single valid document
    where the text is longer than the max snippet length and should be truncated.
    """
    long_text = "This is very long content that definitely exceeds the maximum snippet length defined by CONTEXT_SNIPPET_MAX_LENGTH. " * 10
    expected_snippet = long_text[:CONTEXT_SNIPPET_MAX_LENGTH] + "..."

    sample_doc = DocumentMatch(
        id="book2_chap2_sec2",
        score=0.90,
        metadata=DocumentMetadata(
            text=long_text,
            book_name="Another Book",
            section_title="Chapter Two",
            book_id="2",
            # Optional fields can be None
            author_name=None,
            category_name=None
        )
    )
    input_documents: List[DocumentMatch] = [sample_doc]

    actual_context, actual_sources = format_context_and_extract_sources(input_documents)

    # Check context string format
    assert "Source Document [ID: book2_chap2_sec2]" in actual_context
    assert "Book: Another Book" in actual_context
    assert "Section: Chapter Two" in actual_context
    assert f"Content: {expected_snippet}" in actual_context # Check for truncated snippet

    # Check sources list structure
    assert len(actual_sources) == 1
    source_item = actual_sources[0]
    assert source_item["document_id"] == "book2_chap2_sec2"
    assert source_item["book_id"] == "2"
    assert source_item["book_name"] == "Another Book"
    assert source_item["title"] == "Chapter Two"
    assert source_item["score"] == 0.90
    assert "content" in source_item
    assert source_item["content"] == expected_snippet # Check truncated snippet
    assert source_item["url"] == "https://shamela.ws/book/2"

def test_format_context_and_extract_sources_missing_text():
    """
    Test that a document with missing or empty metadata.text is skipped.
    """
    valid_doc = DocumentMatch(
        id="valid_doc", score=0.8, metadata=DocumentMetadata(text="Valid text", book_id="3")
    )
    invalid_doc_empty = DocumentMatch(
        id="invalid_doc_empty", score=0.6, metadata=DocumentMetadata(text="", book_id="5") # text="" is valid Pydantic but should be skipped by formatter
    )

    input_documents: List[DocumentMatch] = [valid_doc, invalid_doc_empty]

    actual_context, actual_sources = format_context_and_extract_sources(input_documents)

    # Check that only the valid document was processed
    assert "Source Document [ID: valid_doc]" in actual_context
    assert "Source Document [ID: invalid_doc_empty]" not in actual_context # This check remains important

    assert len(actual_sources) == 1
    assert actual_sources[0]["document_id"] == "valid_doc"

def test_format_context_and_extract_sources_multiple_docs():
    """
    Test with multiple valid documents.
    """
    doc1 = DocumentMatch(id="doc1", score=0.9, metadata=DocumentMetadata(text="Content 1", book_id="10"))
    doc2 = DocumentMatch(id="doc2", score=0.8, metadata=DocumentMetadata(text="Content 2", book_id="11"))

    input_documents: List[DocumentMatch] = [doc1, doc2]
    actual_context, actual_sources = format_context_and_extract_sources(input_documents)

    assert "Source Document [ID: doc1]" in actual_context
    assert "Content: Content 1" in actual_context
    assert "Source Document [ID: doc2]" in actual_context
    assert "Content: Content 2" in actual_context

    assert len(actual_sources) == 2
    assert actual_sources[0]["document_id"] == "doc1"
    assert actual_sources[1]["document_id"] == "doc2"
    assert actual_sources[0]["content"] == "Content 1"
    assert actual_sources[1]["content"] == "Content 2"

# Add tests for format_history and construct_llm_prompt if they exist
# in context_formatter.py and have non-trivial logic.