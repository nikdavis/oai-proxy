import asyncio
import os
import shlex  # For robust command string parsing
from typing import (  # Keep Any for now if truly needed, otherwise try to be more specific
    Any,
    Awaitable,
    Callable,
    List,
)

import loguru

# import litellm # Removed for deterministic matching
from src.clients.context_client_p import ContextClientP
from src.models.context import (  # ContextType not used, can be removed later if still unused
    CommandContextSnippet,
    ContextType,
)

logger = loguru.logger

# Type for a handler function
CommandHandler = Callable[[list[str]], Awaitable[CommandContextSnippet]]


class BangCommandHandlerClient(ContextClientP):
    def __init__(self):
        self.command_handlers: dict[str, CommandHandler] = {}
        self.books_dir_path: str = os.getenv("BOOKS_DIR_PATH", "./context/books/")
        self.available_book_files: List[str] = []
        self._scan_book_directory()
        self._register_handlers()

    def _scan_book_directory(self):
        """Scans the configured directory for .txt book files."""
        logger.info(f"Scanning for book files in: {self.books_dir_path}")
        if not os.path.isdir(self.books_dir_path):
            logger.warning(
                f"Books directory '{self.books_dir_path}' not found. No books will be available."
            )
            self.available_book_files = []
            return

        try:
            for filename in os.listdir(self.books_dir_path):
                if filename.endswith(".txt") and os.path.isfile(
                    os.path.join(self.books_dir_path, filename)
                ):
                    self.available_book_files.append(filename)
            if self.available_book_files:
                logger.info(
                    f"Found {len(self.available_book_files)} book(s): {self.available_book_files}"
                )
            else:
                logger.warning(f"No .txt files found in '{self.books_dir_path}'.")
        except Exception as e:
            logger.error(f"Error scanning book directory '{self.books_dir_path}': {e}")
            self.available_book_files = []

    def _register_handlers(self):
        self.register_command("testcmd", self._handle_test_command)
        self.register_command("books", self._handle_list_books_command)
        self.register_command("book", self._handle_get_book_detail_command)
        self.register_command(
            "b", self._handle_get_book_detail_command
        )  # Alias for !book

    def register_command(self, command_name: str, handler: CommandHandler):
        if command_name in self.command_handlers:
            logger.warning(
                f"Command '{command_name}' is already registered. Overwriting."
            )
        self.command_handlers[command_name] = handler
        logger.info(f"Registered bang command: !{command_name}")

    async def _parse_command_string(
        self, command_query: str
    ) -> tuple[str | None, list[str]]:
        """
        Parses the command query into a command and its arguments.
        Example: "weather London" -> ("weather", ["London"])
                 "books" -> ("books", [])
        """
        try:
            parts = shlex.split(command_query)
            if not parts:
                return None, []
            command = parts[0]
            args = parts[1:]
            return command, args
        except ValueError as e:
            logger.error(f"Error parsing command string '{command_query}': {e}")
            return None, []

    async def get_context(
        self, key: str
    ) -> list[str]:  # Changed 'command_query' to 'key'
        """
        Receives a command query string (passed as 'key'),
        parses it, dispatches to the appropriate handler, and returns
        the XML representation of the CommandContextSnippet.
        """
        logger.info(f"BangCommandHandlerClient received command query (key): '{key}'")

        command_name, args = await self._parse_command_string(key)  # Use 'key' here

        if not command_name:
            error_snippet = CommandContextSnippet(
                command_query=f"!{key}",  # Re-add '!' for the snippet, use 'key'
                result_text="Error: Could not parse command.",
                source="BangCommandHandlerClient",
            )
            return [error_snippet.to_xml()]

        handler = self.command_handlers.get(command_name)

        if handler:
            try:
                snippet = await handler(args)
                return [snippet.to_xml()]
            except Exception as e:
                logger.error(
                    f"Error executing handler for command '{command_name}' with args '{args}': {e}"
                )
                error_snippet = CommandContextSnippet(
                    command_query=f"!{command_name} {' '.join(args) if args else ''}",
                    result_text=f"Error executing command '{command_name}': {str(e)}",
                    source="BangCommandHandlerClient",
                )
                return [error_snippet.to_xml()]
        else:
            logger.warning(f"No handler found for command: {command_name}")
            not_found_snippet = CommandContextSnippet(
                command_query=f"!{command_name} {' '.join(args) if args else ''}",
                result_text=f"Error: Command '!{command_name}' not found.",
                source="BangCommandHandlerClient",
            )
            return [not_found_snippet.to_xml()]

    # --- Example/Placeholder Handler ---
    async def _handle_test_command(self, args: list[str]) -> CommandContextSnippet:
        logger.info(f"Executing _handle_test_command with args: {args}")
        return CommandContextSnippet(
            command_query=f"!testcmd {' '.join(args) if args else ''}",
            result_text=f"Test command executed successfully with args: {args}",
            source="TestCommandHandler",
        )

    # --- Book Command Handlers ---

    async def _handle_list_books_command(
        self, args: list[str]
    ) -> CommandContextSnippet:
        logger.info(f"Executing _handle_list_books_command with args: {args}")

        if args:
            potential_book_file_arg = args[0]
            # Normalize the first argument (potential book file) for matching
            normalized_query_arg = potential_book_file_arg.lower()
            if normalized_query_arg.endswith(".txt"):
                normalized_query_arg = normalized_query_arg[:-4]

            matched_filename_for_delegation = None
            for book_file_in_list in self.available_book_files:
                normalized_book_file_in_list = book_file_in_list.lower()
                if normalized_book_file_in_list.endswith(".txt"):
                    normalized_book_file_in_list = normalized_book_file_in_list[:-4]

                if normalized_query_arg == normalized_book_file_in_list:
                    matched_filename_for_delegation = book_file_in_list  # Use original filename
                    break

            if matched_filename_for_delegation:
                logger.info(
                    f"Command '!books {potential_book_file_arg}...' matches book '{matched_filename_for_delegation}'. "
                    f"Delegating to _handle_get_book_detail_command for this book."
                )
                # Delegate to the handler that gets book details.
                # The rest of `args` (e.g., "what is this about") are not used for book retrieval itself
                # but will be part of the overall prompt to the LLM.
                return await self._handle_get_book_detail_command([matched_filename_for_delegation])

        # Original behavior: list all books if no specific book identified in args[0] or no args
        if not self.available_book_files:
            return CommandContextSnippet(
                command_query="!books",
                result_text="No books available. Please check the configuration for BOOKS_DIR_PATH.",
                source="LocalBookDirectory",
            )

        book_list_str = "\n".join(
            [f"- {book_file}" for book_file in self.available_book_files]
        )
        return CommandContextSnippet(
            command_query="!books",
            result_text=f"Available books:\n{book_list_str}",
            source="LocalBookDirectory",
        )

    async def _handle_get_book_detail_command(
        self, args: list[str]
    ) -> CommandContextSnippet:
        user_query = " ".join(args).strip()
        command_query_str = f"!book {user_query}" if user_query else "!book"
        logger.info(
            f"Executing _handle_get_book_detail_command with query: '{user_query}'"
        )

        if not user_query:
            return CommandContextSnippet(
                command_query=command_query_str,
                result_text="Usage: !book <query> or !b <query>. Please provide a search query for the book title.",
                source="BangCommandHandlerClient",
            )

        if not self.available_book_files:
            return CommandContextSnippet(
                command_query=command_query_str,
                result_text="No books available to search. Please check the BOOKS_DIR_PATH configuration.",
                source="LocalBookDirectory",
            )

        # Deterministic filename matching
        normalized_user_query = user_query.lower()
        if normalized_user_query.endswith(".txt"):
            normalized_user_query = normalized_user_query[:-4]

        matched_filename = None
        for book_file in self.available_book_files:
            normalized_book_file = book_file.lower()
            if normalized_book_file.endswith(".txt"):
                normalized_book_file = normalized_book_file[:-4]

            if normalized_user_query == normalized_book_file:
                matched_filename = (
                    book_file  # Use the original filename with case and extension
                )
                break

        logger.info(
            f"Normalized query: '{normalized_user_query}', Matched filename: {matched_filename}"
        )

        if matched_filename:
            try:
                book_file_path = os.path.join(self.books_dir_path, matched_filename)
                with open(book_file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                return CommandContextSnippet(
                    command_query=command_query_str,
                    result_text=f"Content for {matched_filename}:\n\n{content}",
                    source=f"LocalBookFile:{matched_filename}",
                )
            except (
                FileNotFoundError
            ):  # Should be rare if available_book_files is accurate
                logger.error(
                    f"Book file '{matched_filename}' (matched deterministically) not found at path: {book_file_path}"
                )
                return CommandContextSnippet(
                    command_query=command_query_str,
                    result_text=f"Error: Book file '{matched_filename}' was matched but could not be found on disk.",
                    source="LocalBookFile",
                )
            except Exception as e:
                logger.error(f"Error reading book file '{matched_filename}': {e}")
                return CommandContextSnippet(
                    command_query=command_query_str,
                    result_text=f"Error reading content for book '{matched_filename}': {str(e)}",
                    source=f"LocalBookFile:{matched_filename}",
                )
        else:
            logger.info(f"No matching book found for query '{user_query}'.")
            return CommandContextSnippet(
                command_query=command_query_str,
                result_text=f"Book matching query '{user_query}' not found. Try '!books' to see available titles.",
                source="LocalBookDirectory",
            )


# Example of how it might be instantiated and used (for testing purposes)
async def main():
    # Create a dummy context/books directory and some files for testing
    test_books_dir = "./context/books_test_temp"
    os.makedirs(test_books_dir, exist_ok=True)
    with open(
        os.path.join(test_books_dir, "Sample Book One.txt"), "w"
    ) as f:  # Note the casing
        f.write("This is the content of sample book one.")
    with open(os.path.join(test_books_dir, "another_title.txt"), "w") as f:
        f.write("Content for another title here.")
    with open(os.path.join(test_books_dir, "ExactMatch.txt"), "w") as f:
        f.write("Content for ExactMatch.")

    # Temporarily set the environment variable for the test
    original_books_dir_path = os.getenv("BOOKS_DIR_PATH")
    os.environ["BOOKS_DIR_PATH"] = test_books_dir

    client = BangCommandHandlerClient()  # Now uses BOOKS_DIR_PATH from env

    # Test 1: List books
    print("--- Test: !books ---")
    result_list = await client.get_context("books")
    print(result_list[0] if result_list else "No result")

    # Test 2: Get book detail (exact match, case-insensitive query)
    print("\n--- Test: !book sample book one ---")
    result_detail = await client.get_context("book sample book one")
    print(result_detail[0] if result_detail else "No result")

    # Test 3: Get book detail (exact match with .txt in query)
    print("\n--- Test: !b another_title.txt ---")
    result_detail_b = await client.get_context("b another_title.txt")
    print(result_detail_b[0] if result_detail_b else "No result")

    # Test 4: Get book detail (exact match, case-sensitive query matching case-sensitive filename)
    print("\n--- Test: !book ExactMatch ---")
    result_detail_c = await client.get_context("book ExactMatch")
    print(result_detail_c[0] if result_detail_c else "No result")

    # Test 5: Get book detail (non-existent)
    print("\n--- Test: !book non_existent_book ---")
    result_detail_d = await client.get_context("book non_existent_book")
    print(result_detail_d[0] if result_detail_d else "No result")

    # Test 6: Unknown command
    print("\n--- Test: !unknowncmd ---")
    result3 = await client.get_context("unknowncmd arg1")
    print(result3[0] if result3 else "No result")

    # Test 7: Command with arguments (testcmd)
    print("\n--- Test: !testcmd with args ---")
    result4 = await client.get_context('testcmd arg1 "argument with spaces"')
    print(result4[0] if result4 else "No result")

    # Test 8: !book with no query
    print("\n--- Test: !book (no query) ---")
    result5 = await client.get_context("book")
    print(result5[0] if result5 else "No result")

    # Clean up test directory and files
    if original_books_dir_path is None:
        del os.environ["BOOKS_DIR_PATH"]
    else:
        os.environ["BOOKS_DIR_PATH"] = original_books_dir_path

    try:
        os.remove(os.path.join(test_books_dir, "Sample Book One.txt"))
        os.remove(os.path.join(test_books_dir, "another_title.txt"))
        os.remove(os.path.join(test_books_dir, "ExactMatch.txt"))
        os.rmdir(test_books_dir)
        logger.info(f"Cleaned up test directory: {test_books_dir}")
    except OSError as e:
        logger.error(f"Error cleaning up test directory {test_books_dir}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
