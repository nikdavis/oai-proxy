import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock # Use AsyncMock for async methods

from src.hydrator import ChatHydrator, ContextCommand
from src.clients.context_client_p import ContextClientP
from src.models.context import ContextType, ContextSnippet # Assuming ContextType will be updated or used as is

# --- Mock Bang Command Client ---
class MockBangCommandHandlerClient(ContextClientP):
    """
    A mock client for handling bang commands.
    It simulates fetching context based on a command query (now 'key').
    """
    async def get_context(self, key: str) -> list[str]:
        # Simulate different responses based on the command string (key)
        # The key will be the command + its arguments as extracted by ChatHydrator's regex

        # For "test_hydrator_processes_simple_bang_command"
        if key == "books please.":
            return [f"""<context-snippet type="{ContextType.COMMAND_RESULT.value}">
  <command-query>!books please.</command-query>
  <result-text>Mocked book list: Book A, Book B (for 'books please.')</result-text>
  <source>TestBookService</source>
</context-snippet>
"""]
        # For "test_hydrator_processes_bang_command_with_args"
        elif key == "weather London today":
            return [f"""<context-snippet type="{ContextType.COMMAND_RESULT.value}">
  <command-query>!weather London today</command-query>
  <result-text>Mocked weather for London: Sunny, 20C</result-text>
  <source>TestWeatherService</source>
</context-snippet>
"""]
        # For "test_hydrator_processes_multiple_bang_commands_in_message"
        elif key == "books and also":
             return [f"""<context-snippet type="{ContextType.COMMAND_RESULT.value}">
  <command-query>!books and also</command-query>
  <result-text>Mocked book list: Book A, Book B (for 'books and also')</result-text>
  <source>TestBookService</source>
</context-snippet>
"""]
        elif key == "weather London": # This is for the second part of the multiple command test
            return [f"""<context-snippet type="{ContextType.COMMAND_RESULT.value}">
  <command-query>!weather London</command-query>
  <result-text>Mocked weather for London: Sunny, 20C</result-text>
  <source>TestWeatherService</source>
</context-snippet>
"""]
        elif key == "unknown":
            return [f"""<context-snippet type="{ContextType.COMMAND_RESULT.value}">
  <command-query>!unknown</command-query>
  <result-text>Error: Command '!unknown' not found.</result-text>
  <source>CommandHandler</source>
</context-snippet>
"""]
        elif key == "book mock title for my research": # For the new book test
            return [f"""<context-snippet type="{ContextType.COMMAND_RESULT.value}">
  <command-query>!book mock title for my research</command-query>
  <result-text>Content for mock_book.txt:\n\nThis is the mocked content of 'mock_book.txt'.</result-text>
  <source>LocalBookFile:mock_book.txt</source>
</context-snippet>
"""]
        # Default empty for other commands or if no specific match
        return []

@pytest.mark.asyncio
async def test_hydrator_processes_simple_bang_command(mocker):
    """
    Tests that the hydrator correctly identifies a simple bang command
    and calls the BangCommandHandlerClient.
    """
    mock_bang_client = MockBangCommandHandlerClient()
    # Spy on the get_context method
    mocker.patch.object(mock_bang_client, 'get_context', wraps=mock_bang_client.get_context)

    # This will fail until ContextCommand.BANG_COMMAND is added
    clients = {
        ContextCommand.BANG_COMMAND: mock_bang_client
    }
    hydrator = ChatHydrator(clients)

    chat = {
        "messages": [
            {"role": "user", "content": "Tell me about !books please."}
        ]
    }

    # This will fail until _extract_bang_commands is implemented and integrated
    hydrated_chat = await hydrator.get_hydrated_chat(chat)
    user_content = hydrated_chat["messages"][0]["content"]

    mock_bang_client.get_context.assert_called_once_with("books please.") # Expect full extracted command
    assert f'<context-snippet type="{ContextType.COMMAND_RESULT.value}">' in user_content
    assert "<command-query>!books please.</command-query>" in user_content
    assert "Mocked book list: Book A, Book B (for 'books please.')" in user_content
    # Check that original content is preserved and snippet is appended
    assert "Tell me about !books please.\n" in user_content

@pytest.mark.asyncio
async def test_hydrator_processes_bang_command_with_args(mocker):
    """
    Tests that the hydrator correctly identifies a bang command with arguments
    and passes the full command string (sans '!') to the client.
    """
    mock_bang_client = MockBangCommandHandlerClient()
    mocker.patch.object(mock_bang_client, 'get_context', wraps=mock_bang_client.get_context)

    clients = {ContextCommand.BANG_COMMAND: mock_bang_client}
    hydrator = ChatHydrator(clients)

    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather like? !weather London today"}
        ]
    }
    hydrated_chat = await hydrator.get_hydrated_chat(chat)
    user_content = hydrated_chat["messages"][0]["content"]

    # Expects "weather London today" as the key for the client
    mock_bang_client.get_context.assert_called_once_with("weather London today")
    assert "Mocked weather for London: Sunny, 20C" in user_content # Assuming mock handles "weather London"
    assert "What's the weather like? !weather London today\n" in user_content

@pytest.mark.asyncio
async def test_hydrator_processes_multiple_bang_commands_in_message(mocker):
    """
    Tests that the hydrator processes multiple bang commands in a single message.
    """
    mock_bang_client = MockBangCommandHandlerClient()

    # To correctly mock and check multiple calls on an async method that's also wrapped
    # we'll use AsyncMock directly for the spy.
    async_get_context_mock = AsyncMock(side_effect=mock_bang_client.get_context)
    mocker.patch.object(mock_bang_client, 'get_context', new=async_get_context_mock)


    clients = {ContextCommand.BANG_COMMAND: mock_bang_client}
    hydrator = ChatHydrator(clients)

    chat = {
        "messages": [
            {"role": "user", "content": "I need !books and also !weather London, thanks."}
        ]
    }
    hydrated_chat = await hydrator.get_hydrated_chat(chat)
    user_content = hydrated_chat["messages"][0]["content"]

    # Check that get_context was called for both commands
    # The order of calls might not be guaranteed by regex, so use assert_any_call
    async_get_context_mock.assert_any_call("books and also") # Expect full extracted command
    async_get_context_mock.assert_any_call("weather London") # This part was extracted correctly
    assert async_get_context_mock.call_count == 2

    assert "Mocked book list: Book A, Book B (for 'books and also')" in user_content
    assert "Mocked weather for London: Sunny, 20C" in user_content # From !weather London
    assert "I need !books and also !weather London, thanks.\n" in user_content

@pytest.mark.asyncio
async def test_hydrator_processes_book_bang_command(mocker):
    """
    Tests that the hydrator correctly processes a '!book <query>' command
    and the mock client simulates the book retrieval.
    """
    mock_bang_client = MockBangCommandHandlerClient()
    mocker.patch.object(mock_bang_client, 'get_context', wraps=mock_bang_client.get_context)

    clients = {ContextCommand.BANG_COMMAND: mock_bang_client}
    hydrator = ChatHydrator(clients)

    chat = {
        "messages": [
            {"role": "user", "content": "Can you find me !book mock title for my research?"}
        ]
    }
    hydrated_chat = await hydrator.get_hydrated_chat(chat)
    user_content = hydrated_chat["messages"][0]["content"]

    mock_bang_client.get_context.assert_called_once_with("book mock title for my research")
    assert f'<context-snippet type="{ContextType.COMMAND_RESULT.value}">' in user_content
    assert "<command-query>!book mock title for my research</command-query>" in user_content
    assert "Content for mock_book.txt:\n\nThis is the mocked content of 'mock_book.txt'." in user_content
    assert "<source>LocalBookFile:mock_book.txt</source>" in user_content
    assert "Can you find me !book mock title for my research?\n" in user_content
