import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that root endpoint responds with basic state details."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Prime Backend is active" in data["message"]


def test_system_health():
    """Verify system health endpoint."""
    response = client.get("/api/system/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_system_config():
    """Verify config retrieval endpoints hide sensitive API keys."""
    response = client.get("/api/system/config")
    assert response.status_code == 200
    data = response.json()
    assert "has_gemini_key" in data
    assert "secret_key" not in data  # Sensitive keys should be hidden


def test_agent_conversation():
    """Test standard conversational agent routing."""
    response = client.post("/api/agents/command", json={"prompt": "hello jarvis"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "speech_response" in data
