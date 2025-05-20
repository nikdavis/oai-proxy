import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_chat_completions():
    response = client.post(
        "/chat/completions",
        json=[{"role": "user", "content": "What is AI?"}]
    )
    assert response.status_code == 200
    assert "choices" in response.json()
