import logging
from typing import List
import httpx
from src.models.context import WebsiteContextSnippet
from src.models.resource import ResourceSubmission, ContentType
from src.clients.context_client_p import ContextClientP

API_BASE_URL = "http://127.0.0.1:8000"

logger = logging.getLogger(__name__)
class MultiClient(ContextClientP):
    """Client that uses the Context Killer API to create and retrieve resources."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url

    async def get_context(self, url: str) -> List[str]:
        """
        Post a URL to the API and retrieve the processed content.
        Implements the ContextClient protocol.
        """
        logger.info(f"Getting context via API for URL: {url}")

        # Create a resource via the API
        async with httpx.AsyncClient() as client:
            # Create the resource submission
            submission = ResourceSubmission(
                url=url,
                type=ContentType.WEBPAGE,
                title=f"Content from {url}"
            )

            # Post to create resource
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/resources",
                    json=submission.model_dump(),
                    timeout=30.0
                )
                response.raise_for_status()
                resource = response.json()

                print(f"Resource: {resource}")

                # Create a context snippet from the resource
                snippet = WebsiteContextSnippet(
                    url=resource["url"],
                    text_content=resource["content"],
                    title=resource["title"]
                )

                # Convert to XML and return
                return [snippet.to_xml()]

            except httpx.HTTPError as e:
                logger.error(f"Error creating resource: {e}")
                # Fall back to mock implementation if API fails
                return await self._mock_fallback(url)

    async def _mock_fallback(self, url: str) -> List[str]:
        """Fallback method if the API request fails."""
        logger.info(f"Using fallback mock for URL: {url}")
        content = f"API request failed. This is fallback content for {url}"

        snippet = WebsiteContextSnippet(
            url=url,
            text_content=content,
            title=f"Fallback content for {url}"
        )

        return [snippet.to_xml()]
