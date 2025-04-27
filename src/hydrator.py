import re
from enum import StrEnum, auto
from typing import Dict, List, Any, Optional, Callable, Protocol, Mapping, Union
import asyncio
from src.clients.website_client import WebsiteContextClient
from src.clients.multi_client import MultiClient
import loguru
logger = loguru.logger

class ContextCommand(StrEnum):
    WEBSITE = auto()

# cache of context snippets
context_cache: Dict[str, List[str]] = {}

class ContextClient(Protocol):
    async def get_context(self, key: str) -> List[str]:
        return []  # Default empty implementation


class ChatHydrator:
    def __init__(self, clients: dict[ContextCommand, ContextClient]):
        self.clients = clients
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?'
        )
        # Add more patterns for other entity types (commands, etc.)

    def _extract_urls(self, text: str) -> List[str]:
        if not text:
            return []

        return self.url_pattern.findall(text)

    async def get_hydrated_chat(self, chat: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Hydrating chat: {chat}")
        print(f"Chat: {chat}")
        if not chat or "messages" not in chat:
            logger.warning("No valid chat object provided to hydrate")
            return chat

        # Log system prompt if present
        for message in chat.get("messages", []):
            if message.get("role") == "system":
                print(f"System prompt: {message.get('content')}")
                break

        # Create a new chat object with the same structure
        hydrated_chat = dict(chat)
        hydrated_chat["messages"] = []

        for message in chat.get("messages", []):
            # Create a copy of the message
            hydrated_message = dict(message)
            logger.info(f"Inspecting message: {hydrated_message['content'][:100]}")

            # Process user messages
            if message.get("role") == "user":
                # Check for URLs in content
                original_content = message.get("content", "")
                if isinstance(original_content, str):
                    # Extract URLs
                    urls = self._extract_urls(original_content)

                    if urls:
                        logger.info(f"Found {len(urls)} URLs: {urls}")
                    else:
                        logger.info("No URLs found")

                    context_snippets = []

                    if urls and ContextCommand.WEBSITE in self.clients:
                        for url in urls:
                            # check cache for context snippets
                            if url in context_cache:
                                context_snippets.extend(context_cache[url])
                            else:
                                new_snippets = await self.clients[ContextCommand.WEBSITE].get_context(url)
                                context_cache[url] = new_snippets
                                context_snippets.extend(new_snippets)

                        if context_snippets:
                            hydrated_message["content"] += "\n\n" + "\n\n".join(context_snippets)
                            logger.info(f"Added {len(context_snippets)} context snippets for URLs")

                # Add more entity extraction and context retrieval here (commands, etc.)


            hydrated_chat["messages"].append(hydrated_message)

        return hydrated_chat


# Initialize context clients
# website_client = WebsiteContextClient()
multi_client = MultiClient()

clients = {
    ContextCommand.WEBSITE: multi_client
}
