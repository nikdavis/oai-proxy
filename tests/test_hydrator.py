import pytest

from src.clients.website_client import WebsiteContextClient
from src.hydrator import ChatHydrator, ContextCommand


@pytest.mark.asyncio
async def test_chat_hydrator_with_urls():
    """Test the hydrator with chat containing URLs."""
    # Create a test chat with URLs
    test_chat = {
        "messages": [
            {
                "role": "user",
                "content": "Check out this website: https://example.com and also https://test.org",
            },
            {"role": "assistant", "content": "Here's another: https://python.org"},
        ]
    }

    # Initialize the hydrator with the website client
    clients = {ContextCommand.WEBSITE: WebsiteContextClient()}
    hydrator = ChatHydrator(clients)

    # Get the hydrated chat
    hydrated_chat = await hydrator.get_hydrated_chat(test_chat)

    # Verify structure is preserved
    assert len(hydrated_chat["messages"]) == 2
    assert hydrated_chat["messages"][0]["role"] == "user"
    assert hydrated_chat["messages"][1]["role"] == "assistant"

    # Verify URL handling and context enrichment
    user_content = hydrated_chat["messages"][0]["content"]
    assert "https://example.com" in user_content
    assert "https://test.org" in user_content
    assert "<context-snippet" in user_content

    # Assistant messages shouldn't be modified yet (only user messages)
    assert (
        hydrated_chat["messages"][1]["content"] == "Here's another: https://python.org"
    )


@pytest.mark.asyncio
async def test_chat_hydrator_without_urls():
    """Test the hydrator with chat containing no URLs."""
    # Create a test chat without URLs
    test_chat = {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]
    }

    # Initialize the hydrator
    clients = {ContextCommand.WEBSITE: WebsiteContextClient()}
    hydrator = ChatHydrator(clients)

    # Get the hydrated chat
    hydrated_chat = await hydrator.get_hydrated_chat(test_chat)

    # Verify structure is preserved
    assert len(hydrated_chat["messages"]) == 2

    # Verify content is unchanged (no hydration needed)
    assert hydrated_chat["messages"][0]["content"] == "Hello, how are you?"
    assert hydrated_chat["messages"][1]["content"] == "I'm doing well, thank you!"


@pytest.mark.asyncio
async def test_chat_hydrator_empty_chat():
    """Test the hydrator with an empty chat."""
    # Initialize the hydrator
    clients = {ContextCommand.WEBSITE: WebsiteContextClient()}
    hydrator = ChatHydrator(clients)

    # Test with empty chat
    empty_chat = {}
    hydrated_chat = await hydrator.get_hydrated_chat(empty_chat)

    # Verify empty chat is returned as is
    assert hydrated_chat == {}
