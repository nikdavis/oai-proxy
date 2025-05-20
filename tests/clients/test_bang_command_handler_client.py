import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.clients.bang_command_handler_client import BangCommandHandlerClient
from src.models.context import CommandContextSnippet

# Test data
TEST_BOOKS_DIR = "./test_books_temp/"
BOOK1_CONTENT = "This is The Great Gatsby."
BOOK2_CONTENT = "This is Moby Dick."


@pytest.fixture
def client_with_mocks(autouse=True):
    """Fixture to create a client with common mocks for os."""
    with (
        patch("os.getenv", return_value=TEST_BOOKS_DIR) as mock_getenv,
        patch("os.path.isdir") as mock_isdir,
        patch("os.listdir") as mock_listdir,
        patch("os.path.isfile") as mock_isfile,
    ):
        # Ensure the test directory exists for setup/teardown if needed by tests
        # but individual tests will mock os.path.isdir etc.
        if not os.path.exists(TEST_BOOKS_DIR):
            os.makedirs(TEST_BOOKS_DIR, exist_ok=True)

        client = BangCommandHandlerClient()

        yield client, mock_isdir, mock_listdir, mock_isfile

        # Clean up the test directory
        if os.path.exists(os.path.join(TEST_BOOKS_DIR, "gatsby.txt")):
            os.remove(os.path.join(TEST_BOOKS_DIR, "gatsby.txt"))
        if os.path.exists(os.path.join(TEST_BOOKS_DIR, "moby.txt")):
            os.remove(os.path.join(TEST_BOOKS_DIR, "moby.txt"))
        try:
            if os.path.exists(TEST_BOOKS_DIR) and (
                not os.listdir(TEST_BOOKS_DIR)
                if callable(os.listdir)
                and not isinstance(os.listdir, MagicMock)
                or hasattr(os.listdir, "_mock_wraps")
                and os.listdir._mock_wraps is None
                else True
            ):  # Check if listdir is not a broken mock
                os.rmdir(TEST_BOOKS_DIR)
            elif os.path.exists(
                TEST_BOOKS_DIR
            ):  # If not empty, log a warning or handle as per test needs
                print(
                    f"Warning: Test directory {TEST_BOOKS_DIR} was not empty after tests."
                )
        except OSError as e:
            print(
                f"Warning: OSError during teardown attempting to list or remove {TEST_BOOKS_DIR}: {e}"
            )


class TestBangCommandHandlerClientScanDirectory:
    def test_scan_book_directory_not_found(self, client_with_mocks):
        client, mock_isdir, _, _ = client_with_mocks
        mock_isdir.reset_mock()  # Reset before setting new behavior and re-calling
        mock_isdir.return_value = False

        client._scan_book_directory()

        assert client.available_book_files == []
        mock_isdir.assert_called_once_with(TEST_BOOKS_DIR)

    def test_scan_book_directory_empty(self, client_with_mocks):
        client, mock_isdir, mock_listdir, _ = client_with_mocks
        mock_isdir.reset_mock()
        mock_listdir.reset_mock()
        mock_isdir.return_value = True
        mock_listdir.return_value = []

        client._scan_book_directory()

        assert client.available_book_files == []
        mock_listdir.assert_called_once_with(TEST_BOOKS_DIR)

    def test_scan_book_directory_with_txt_files(self, client_with_mocks):
        client, mock_isdir, mock_listdir, mock_isfile = client_with_mocks
        mock_isdir.reset_mock()
        mock_listdir.reset_mock()
        mock_isfile.reset_mock()

        mock_isdir.return_value = True
        mock_listdir.return_value = ["gatsby.txt", "moby.txt", "notes.md"]

        def side_effect_isfile(path):
            if path == os.path.join(TEST_BOOKS_DIR, "gatsby.txt"):
                return True
            if path == os.path.join(TEST_BOOKS_DIR, "moby.txt"):
                return True
            # notes.md is a file, but not a .txt file, so isfile won't be called for it by the filtered logic
            return False  # Default for other paths like notes.md if os.path.isfile was called directly

        mock_isfile.side_effect = side_effect_isfile

        client._scan_book_directory()

        assert sorted(client.available_book_files) == sorted(["gatsby.txt", "moby.txt"])
        # isfile is only called for .txt files due to "if filename.endswith('.txt')"
        assert mock_isfile.call_count == 2

    def test_scan_book_directory_os_error(self, client_with_mocks):
        client, mock_isdir, mock_listdir, _ = client_with_mocks
        mock_isdir.reset_mock()
        mock_listdir.reset_mock()

        mock_isdir.return_value = True
        mock_listdir.side_effect = OSError("Test OS error")

        client._scan_book_directory()

        assert client.available_book_files == []
        # We can also assert that listdir was called
        mock_listdir.assert_called_once_with(TEST_BOOKS_DIR)


@pytest.mark.asyncio
class TestBangCommandHandlerClientListBooks:
    async def test_handle_list_books_no_books(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = []  # Ensure no books for this test

        snippet = await client._handle_list_books_command([])

        assert isinstance(snippet, CommandContextSnippet)
        assert snippet.content["command_query"] == "!books"
        assert "No books available" in snippet.content["result_text"]
        assert snippet.content["source"] == "LocalBookDirectory"

    async def test_handle_list_books_with_books(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["gatsby.txt", "moby.txt"]

        snippet = await client._handle_list_books_command([])

        assert isinstance(snippet, CommandContextSnippet)
        assert snippet.content["command_query"] == "!books"
        assert "Available books:" in snippet.content["result_text"]
        assert "- gatsby.txt" in snippet.content["result_text"]
        assert "- moby.txt" in snippet.content["result_text"]
        assert snippet.content["source"] == "LocalBookDirectory"


# Placeholder for _handle_get_book_detail_command tests
@pytest.mark.asyncio
class TestBangCommandHandlerClientGetBookDetail:
    async def test_get_book_detail_no_query(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = [
            "exists.txt"
        ]  # Needs some books to pass initial check

        snippet = await client._handle_get_book_detail_command([])

        assert "Usage: !book <query>" in snippet.content["result_text"]
        assert snippet.content["command_query"] == "!book"
        assert snippet.content["source"] == "BangCommandHandlerClient"

    async def test_get_book_detail_no_available_books(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = []

        snippet = await client._handle_get_book_detail_command(["some query"])

        assert "No books available to search" in snippet.content["result_text"]
        assert snippet.content["command_query"] == "!book some query"
        assert snippet.content["source"] == "LocalBookDirectory"

    async def test_get_book_detail_exact_match_success(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["The Great Gatsby.txt", "Moby Dick.txt"]

        mock_file_content = "This is the full content of The Great Gatsby."
        with patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ) as mocked_open_file:
            # Test exact match (case-insensitive for query part, original filename for retrieval)
            snippet = await client._handle_get_book_detail_command(["the great gatsby"])

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "The Great Gatsby.txt"),
                "r",
                encoding="utf-8",
            )
            assert isinstance(snippet, CommandContextSnippet)
            assert snippet.content["command_query"] == "!book the great gatsby"
            assert (
                f"Content for The Great Gatsby.txt:\n\n{mock_file_content}"
                == snippet.content["result_text"]
            )
            assert snippet.content["source"] == "LocalBookFile:The Great Gatsby.txt"

    async def test_get_book_detail_match_with_txt_in_query(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["Moby Dick.txt"]

        mock_file_content = "Call me Ishmael."
        with patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ) as mocked_open_file:
            snippet = await client._handle_get_book_detail_command(["moby dick.txt"])

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "Moby Dick.txt"), "r", encoding="utf-8"
            )
            assert (
                f"Content for Moby Dick.txt:\n\n{mock_file_content}"
                == snippet.content["result_text"]
            )

    async def test_get_book_detail_match_without_txt_in_query(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["Another Book.txt"]

        mock_file_content = "Details about another book."
        with patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ) as mocked_open_file:
            snippet = await client._handle_get_book_detail_command(["another book"])

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "Another Book.txt"), "r", encoding="utf-8"
            )
            assert (
                f"Content for Another Book.txt:\n\n{mock_file_content}"
                == snippet.content["result_text"]
            )

    async def test_get_book_detail_case_insensitive_match(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["UPPERCASE BOOK.txt"]

        mock_file_content = "Content of uppercase book."
        with patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ) as mocked_open_file:
            snippet = await client._handle_get_book_detail_command(
                ["uppercase book"]
            )  # Query is lowercase

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "UPPERCASE BOOK.txt"),
                "r",
                encoding="utf-8",
            )
            assert (
                f"Content for UPPERCASE BOOK.txt:\n\n{mock_file_content}"
                == snippet.content["result_text"]
            )

    async def test_get_book_detail_no_match(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["Some Book.txt"]

        snippet = await client._handle_get_book_detail_command(["nonexistent book"])

        assert (
            "Book matching query 'nonexistent book' not found"
            in snippet.content["result_text"]
        )
        assert snippet.content["command_query"] == "!book nonexistent book"
        assert snippet.content["source"] == "LocalBookDirectory"

    async def test_get_book_detail_match_file_read_error(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["error_book.txt"]

        with patch("builtins.open", mock_open()) as mocked_open_file:
            mocked_open_file.side_effect = IOError("Cannot read file")
            snippet = await client._handle_get_book_detail_command(
                ["error_book"]
            )  # Exact match for filename part

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "error_book.txt"), "r", encoding="utf-8"
            )
            assert (
                "Error reading content for book 'error_book.txt'"
                in snippet.content["result_text"]
            )
            assert "Cannot read file" in snippet.content["result_text"]
            assert snippet.content["source"] == "LocalBookFile:error_book.txt"

    async def test_get_book_detail_match_file_not_found_on_disk_unexpected(
        self, client_with_mocks
    ):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["ghost_book.txt"]

        with patch("builtins.open", mock_open()) as mocked_open_file:
            mocked_open_file.side_effect = FileNotFoundError("File vanished")
            snippet = await client._handle_get_book_detail_command(["ghost_book"])

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "ghost_book.txt"), "r", encoding="utf-8"
            )
            assert (
                "Error: Book file 'ghost_book.txt' was matched but could not be found on disk."
                in snippet.content["result_text"]
            )
            assert snippet.content["source"] == "LocalBookFile"

    async def test_get_book_detail_match_content_truncation(self, client_with_mocks):
        client, _, _, _ = client_with_mocks
        client.available_book_files = ["long_story.txt"]

        long_content = "a" * 4000
        expected_truncated_content = ("a" * 3000) + "\n... (truncated)"

        with patch(
            "builtins.open", mock_open(read_data=long_content)
        ) as mocked_open_file:
            snippet = await client._handle_get_book_detail_command(["long_story"])

            mocked_open_file.assert_called_once_with(
                os.path.join(TEST_BOOKS_DIR, "long_story.txt"), "r", encoding="utf-8"
            )
            assert (
                f"Content for long_story.txt:\n\n{expected_truncated_content}"
                == snippet.content["result_text"]
            )
