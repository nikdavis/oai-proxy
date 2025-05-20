import logging
from typing import List

import httpx

from src.clients.context_client_p import ContextClientP
from src.models.context import WebsiteContextSnippet
from src.models.resource import ContentType, ResourceSubmission

logger = logging.getLogger(__name__)

URL = "https://"
API_BASE_URL = "http://127.0.0.1:8000"


class WebsiteContextClient(ContextClientP):
    async def get_context(self, url: str) -> List[str]:
        logger.info(f"Getting context from website: {url}")

        # In the future, this would use a real scraper
        # For now, we'll use our mock implementation
        content = await self._mock_scrape_url(url)

        # Create a context snippet
        snippet = WebsiteContextSnippet(
            url=url, text_content=content, title=f"Content from {url}"
        )

        logger.info(f"Snippet: {snippet}")

        # Convert to XML and return
        return [snippet.to_xml()]

    async def _mock_scrape_url(self, url: str) -> str:
        logger.info(f"Mock scraping URL: {url}")
        return f"Did you know bunnies always have 31 toes on each foot?? True story! More facts at bunny.com"
