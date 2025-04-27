# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_embed_endpoint():
    """Test the embedding endpoint."""
    test_text = "بسم الله الرحمن الرحيم"
    response = client.post(
        "/embed",
        json={"text": test_text},
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "embedding" in data
    assert isinstance(data["embedding"], list)
    assert len(data["embedding"]) > 0

def test_retrieval_endpoint():
    """Test the retrieval endpoint."""
    test_query = "زكاة المال"
    response = client.post(
        "/retrieval",
        json={"query": test_query, "top_k": 3},
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data