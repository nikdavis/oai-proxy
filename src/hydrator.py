import asyncio
import re
from enum import StrEnum, auto
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Union

import loguru

from src.clients.bang_command_handler_client import (
    BangCommandHandlerClient,  # Added import
)
from src.clients.multi_client import MultiClient
from src.clients.website_client import WebsiteContextClient

logger = loguru.logger


class ContextCommand(StrEnum):
    WEBSITE = auto()
    BANG_COMMAND = auto()


# cache of context snippets
context_cache: Dict[str, List[str]] = {}


class ContextClient(Protocol):
    async def get_context(self, key: str) -> List[str]:
        return []  # Default empty implementation


class ChatHydrator:
    def __init__(self, clients: Mapping[ContextCommand, ContextClient]):
        self.clients: Mapping[ContextCommand, ContextClient] = clients
        self.url_pattern = re.compile(
            r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?"
        )
        # Pattern for bang commands: !command <arguments up to newline/end of string>
        # Captures the command and its arguments (e.g., "books" or "weather London today")
        # The command name is group 1: alphanumeric + _.-
        # Arguments are group 2: zero or more sequences of (space + alphanumeric/_.- word)
        self.bang_command_pattern = re.compile(
            r"!([a-zA-Z0-9_.-]+)((?:\s+[a-zA-Z0-9_.-]+)*)"
        )

    def _extract_urls(self, text: str) -> List[str]:
        if not text:
            return []

        return self.url_pattern.findall(text)

    def _extract_bang_commands(self, text: str) -> List[str]:
        if not text:
            return []

        extracted_commands = []
        for match in self.bang_command_pattern.finditer(text):
            command_name = match.group(1)
            args_part = match.group(2) if match.group(2) else ""
            full_command = (command_name + args_part).strip()
            if full_command:  # Ensure we don't add empty strings if somehow matched
                extracted_commands.append(full_command)
        return extracted_commands

    async def get_hydrated_chat(self, chat: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Hydrating chat: {chat}")
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

                    context_snippets = []  # Combined snippets from all sources

                    # Process URLs
                    if urls and ContextCommand.WEBSITE in self.clients:
                        url_snippets_to_add = []
                        for url in urls:
                            if url in context_cache:
                                url_snippets_to_add.extend(context_cache[url])
                            else:
                                new_snippets = await self.clients[
                                    ContextCommand.WEBSITE
                                ].get_context(url)
                                context_cache[url] = new_snippets  # Cache for URLs
                                url_snippets_to_add.extend(new_snippets)
                        if url_snippets_to_add:
                            context_snippets.extend(url_snippets_to_add)
                            logger.info(
                                f"Collected {len(url_snippets_to_add)} context snippets for URLs"
                            )

                    # Extract Bang Commands
                    bang_commands = self._extract_bang_commands(original_content)
                    if bang_commands:
                        logger.info(
                            f"Found {len(bang_commands)} bang commands: {bang_commands}"
                        )
                    else:
                        logger.info("No bang commands found")

                    # Process Bang Commands
                    if bang_commands and ContextCommand.BANG_COMMAND in self.clients:
                        bang_snippets_to_add = []
                        for command_str in bang_commands:
                            cache_key = f"!{command_str}"  # Cache key for bang commands
                            if cache_key in context_cache:
                                bang_snippets_to_add.extend(context_cache[cache_key])
                            else:
                                # The command_str (e.g., "books" or "weather London") is the key for the client
                                new_snippets = await self.clients[
                                    ContextCommand.BANG_COMMAND
                                ].get_context(command_str)
                                context_cache[cache_key] = new_snippets
                                bang_snippets_to_add.extend(new_snippets)
                        if bang_snippets_to_add:
                            context_snippets.extend(bang_snippets_to_add)
                            logger.info(
                                f"Collected {len(bang_snippets_to_add)} context snippets for bang commands"
                            )

                    # Append all collected snippets to the message content
                    if context_snippets:
                        # Ensure original content ends with a newline if it doesn't already, before appending snippets
                        current_content = hydrated_message.get(
                            "content", ""
                        )  # Get potentially already modified content
                        if current_content and not current_content.endswith("\n"):
                            hydrated_message["content"] = current_content + "\n"
                        # else: # content already has newline or is empty
                        # hydrated_message["content"] = current_content

                        hydrated_message["content"] += "\n" + "\n\n".join(
                            context_snippets
                        )
                        logger.info(
                            f"Appended a total of {len(context_snippets)} context snippets to the message"
                        )

            hydrated_chat["messages"].append(hydrated_message)

        return hydrated_chat


# Initialize context clients
# website_client = WebsiteContextClient()
multi_client = MultiClient()
bang_command_client = BangCommandHandlerClient()  # Instantiate the new client

clients: Mapping[
    ContextCommand, ContextClient
] = {  # Ensure type hint for the dictionary
    ContextCommand.WEBSITE: multi_client,
    ContextCommand.BANG_COMMAND: bang_command_client,  # Add the new client to the registry
}
