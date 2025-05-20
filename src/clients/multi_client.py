import logging
from typing import List
import httpx
from loguru import logger
from src.models.context import WebsiteContextSnippet
from src.models.resource import ResourceSubmission, ContentType
from src.clients.context_client_p import ContextClientP


API_BASE_URL = "http://127.0.0.1:8000"

class MultiClient(ContextClientP):
    """Client that uses the Context Killer API to create and retrieve resources."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url

    async def get_context(self, key: str) -> List[str]: # Changed 'url' to 'key'
        """
        Post a URL (passed as 'key') to the API and retrieve the processed content.
        Implements the ContextClient protocol.
        """
        logger.info(f"Getting context via API for URL (key): {key}")

        # Create a resource via the API
        async with httpx.AsyncClient() as client:
            # Create the resource submission
            submission = ResourceSubmission(
                url=key, # Use 'key' here
                title=f"Content from {key}" # Use 'key' here
            )

            # Post to create resource
            try:
                logger.info(f"POST {self.base_url}/api/v1/resources {submission.model_dump()}")

                response = await client.post(
                    f"{self.base_url}/api/v1/resources",
                    json=submission.model_dump(),
                    timeout=180.0
                )

                resource = response.json()

                logger.debug(f"Resource: {resource}")
                logger.debug(f"Resource response metadata: {response.headers}")
                logger.debug(f"Resource response status code: {response.status_code}")

                # Create a context snippet from the resource
                snippet = WebsiteContextSnippet(
                    url=resource["url"],
                    text_content=resource["content"],
                    title=resource["title"]
                )

                logger.info(f"Snippet: {snippet}")

                # Convert to XML and return
                return [snippet.to_xml()]

            except httpx.HTTPError as e:
                logger.error(f"Error creating resource: {e}")
                # Fall back to mock implementation if API fails
                return await self._mock_fallback(key) # Pass 'key'

    async def _mock_fallback(self, key: str) -> List[str]: # Changed 'url' to 'key'
        """Fallback method if the API request fails."""
        logger.info(f"Using fallback mock for URL (key): {key}")
        content = f"API request failed. This is fallback content for {key}" # Use 'key'

        snippet = WebsiteContextSnippet(
            url=key, # Use 'key'
            text_content=content,
            title=f"Fallback content for {key}" # Use 'key'
        )

        return [snippet.to_xml()]
