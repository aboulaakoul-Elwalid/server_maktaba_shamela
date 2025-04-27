from fastapi.testclient import TestClient
import pytest
# The client fixture is automatically available from conftest.py

def test_read_root(client: TestClient):
    """Test the root endpoint '/'."""
    response = client.get("/")
    assert response.status_code == 200
    # Adjust the expected JSON based on your actual root endpoint response in app/main.py
    # This assumes your root endpoint returns {"message": "Hello World"}
    try:
        # Update this line to match the actual response
        expected_json = {"message": "Hello World"}
        assert response.json() == expected_json
    except KeyError:
        # Handle cases where the root endpoint might return something different
        # or if the response is not JSON
        pytest.fail(f"Root endpoint did not return expected JSON. Response: {response.text}")

# Add more basic tests here if your main.py has other simple endpoints
# like a health check '/health'
# def test_health_check(client: TestClient):
#     response = client.get("/health") # Assuming you have a /health endpoint
#     assert response.status_code == 200
#     assert response.json() == {"status": "ok"}