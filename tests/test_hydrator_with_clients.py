import pytest
from typing import List
import xml.etree.ElementTree as ET
from src.hydrator import ChatHydrator, ContextClient, ContextCommand
from src.clients.website_client import WebsiteContextClient


class MockWebsiteClient(ContextClient):
    """Mock website client for testing."""

    async def get_context(self, url: str) -> List[str]:
        """Mock implementation of get_context."""
        return [f"""
<context-snippet type="website">
  <url>{url}</url>
  <text-content>Mocked content for testing: {url}</text-content>
  <title>Mock Title</title>
</context-snippet>
"""]


@pytest.mark.asyncio
async def test_hydrator_with_mock_clients():
    """Test hydrator with mock clients."""
    # Create hydrator with mock clients
    clients = {
        ContextCommand.WEBSITE: MockWebsiteClient()
    }
    hydrator = ChatHydrator(clients)

    # Create test chat with URLs
    chat = {
        "messages": [
            {
                "role": "user",
                "content": "Check out https://example.com and https://test.org"
            },
            {
                "role": "assistant",
                "content": "I'll check those out!"
            }
        ]
    }

    # Hydrate the chat
    hydrated_chat = await hydrator.get_hydrated_chat(chat)

    # Verify structure
    assert len(hydrated_chat["messages"]) == 2

    # Context is now appended to content field
    user_content = hydrated_chat["messages"][0]["content"]
    assert "https://example.com" in user_content
    assert "https://test.org" in user_content
    assert "<context-snippet" in user_content
    assert "Mocked content for testing" in user_content

    # Make sure we can parse the XML from the content
    content_parts = user_content.split("\n\n")
    assert len(content_parts) >= 3  # Original content + 2 snippets

    # Parse one of the XML snippets
    for part in content_parts[1:]:  # Skip the original content
        if "<context-snippet" in part:
            root = ET.fromstring(part)
            assert root.tag == "context-snippet"
            assert root.attrib["type"] == "website"
            url_found = False
            for url_elem in root.findall(".//url"):
                if url_elem.text in ["https://example.com", "https://test.org"]:
                    url_found = True
            assert url_found, "Expected URL not found in XML"


@pytest.mark.asyncio
async def test_hydrator_with_real_clients():
    """Test hydrator with real clients."""
    # Create hydrator with real clients
    clients = {
        ContextCommand.WEBSITE: WebsiteContextClient()
    }
    hydrator = ChatHydrator(clients)

    # Create test chat with URLs
    chat = {
        "messages": [
            {
                "role": "user",
                "content": "Check out https://example.com"
            }
        ]
    }

    # Hydrate the chat
    hydrated_chat = await hydrator.get_hydrated_chat(chat)

    # Verify structure
    assert len(hydrated_chat["messages"]) == 1

    # Context is now appended to content field
    user_content = hydrated_chat["messages"][0]["content"]
    assert "https://example.com" in user_content
    assert "<context-snippet" in user_content

    # Check for expected content in any part of the message
    assert "bunny" in user_content.lower() or "mocked content" in user_content.lower()
