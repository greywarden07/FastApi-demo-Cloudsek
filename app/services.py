from datetime import datetime
from typing import Dict, Tuple

import httpx

from app.config import settings
from app.models import URLMetadata


class MetadataFetchError(RuntimeError):
    """Raised when metadata for a URL cannot be fetched"""


class MetadataService:
    """Service to collect metadata from URLs"""
    
    @staticmethod
    async def fetch_url_metadata(url: str) -> Tuple[Dict[str, str], Dict[str, str], str]:
        """
        Fetch headers, cookies, and page source from a URL
        
        Args:
            url: The URL to fetch metadata from
            
        Returns:
            Tuple of (headers, cookies, page_source)
        """
        timeout = httpx.Timeout(settings.http_client_timeout)
        client_headers = {"User-Agent": "MetadataInventoryBot/1.0"}

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers=client_headers,
            timeout=timeout,
            max_redirects=settings.http_client_max_redirects,
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()

                headers = dict(response.headers)
                cookies = {cookie.name: cookie.value for cookie in response.cookies.jar}

                page_source = MetadataService._truncate_page_source(response.text)

                return headers, cookies, page_source

            except httpx.HTTPStatusError as exc:
                raise MetadataFetchError(f"HTTP {exc.response.status_code} for {url}") from exc
            except httpx.RequestError as exc:
                raise MetadataFetchError(f"Error fetching URL {url}: {exc}") from exc
    
    @staticmethod
    def create_metadata_document(url: str, headers: Dict, cookies: Dict, page_source: str) -> dict:
        """
        Create a metadata document for MongoDB storage
        
        Args:
            url: The URL
            headers: Response headers
            cookies: Response cookies
            page_source: HTML page source
            
        Returns:
            Dictionary ready for MongoDB insertion
        """
        metadata = URLMetadata(
            url=url,
            headers=headers,
            cookies=cookies,
            page_source=page_source,
            collected_at=datetime.utcnow()
        )
        return metadata.model_dump()

    @staticmethod
    def _truncate_page_source(page_source: str) -> str:
        """Limit page source size to protect storage and responses"""
        encoded = page_source.encode("utf-8")
        max_bytes = settings.page_source_max_bytes
        if len(encoded) <= max_bytes:
            return page_source
        truncated = encoded[:max_bytes]
        return truncated.decode("utf-8", errors="ignore")
