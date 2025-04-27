import pytest
from unittest.mock import patch, MagicMock
from src.clients.litellm_client import LiteLLMClient
from src.models.message import Message

@pytest.mark.asyncio
async def test_context_callback():
    client = LiteLLMClient()
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is AI?")
    ]

    with patch('src.utils.context_retriever.get_relevant_context') as mock_context:
        mock_context.return_value = "[Test context]"
        result = await client.context_callback(messages)

        assert len(result) == 2
        assert result[1].content.startswith("[Test context]")
        assert "What is AI?" in result[1].content

@pytest.mark.asyncio
async def test_success_callback():
    client = LiteLLMClient()
    mock_response = {
        "choices": [
            {"text": "AI stands for Artificial Intelligence"},
            {"text": "It's a branch of computer science"}
        ]
    }

    result = await client.success_callback(mock_response)

    assert "choices" in result
    assert len(result["choices"]) == 2
    assert "AI stands for" in result["choices"][0]
