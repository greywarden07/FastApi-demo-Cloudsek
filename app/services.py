from datetime import datetime
from typing import Dict, Tuple

import httpx

from app.config import settings
from app.models import URLMetadata


class MetadataFetchError(RuntimeError):
    """Raised when metadata for a URL cannot be fetched
    
    This custom exception helps distinguish network/HTTP errors from other issues
    """


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
        # Configure timeout to prevent hanging on slow/unresponsive sites
        timeout = httpx.Timeout(settings.http_client_timeout)
        
        # Set a User-Agent to identify our bot (some sites block requests without this)
        client_headers = {"User-Agent": "MetadataInventoryBot/1.0"}

        # Create an async HTTP client with production-ready settings
        async with httpx.AsyncClient(
            follow_redirects=True,  # Follow redirects automatically (e.g., HTTP -> HTTPS)
            headers=client_headers,
            timeout=timeout,
            max_redirects=settings.http_client_max_redirects,  # Prevent infinite redirect loops
        ) as client:
            try:
                # Make the GET request
                response = await client.get(url)
                
                # Raise an exception if we got a 4xx or 5xx status code
                response.raise_for_status()

                # Extract headers as a dictionary
                headers = dict(response.headers)
                
                # Extract cookies from the response
                cookies = {cookie.name: cookie.value for cookie in response.cookies.jar}

                # Truncate page source to prevent memory issues with huge pages
                page_source = MetadataService._truncate_page_source(response.text)

                return headers, cookies, page_source

            except httpx.HTTPStatusError as exc:
                # Website returned an error status (404, 500, etc.)
                raise MetadataFetchError(f"HTTP {exc.response.status_code} for {url}") from exc
            except httpx.RequestError as exc:
                # Network error, DNS failure, timeout, etc.
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
        # Use Pydantic model to validate data structure before saving to DB
        metadata = URLMetadata(
            url=url,
            headers=headers,
            cookies=cookies,
            page_source=page_source,
            collected_at=datetime.utcnow()  # Record when this metadata was collected
        )
        # Convert Pydantic model to dict for MongoDB
        return metadata.model_dump()

    @staticmethod
    def _truncate_page_source(page_source: str) -> str:
        """Limit page source size to protect storage and responses
        
        Some websites return massive HTML pages (10MB+), which can:
        - Blow up MongoDB document size limits (16MB max)
        - Cause memory issues when loading many records
        - Slow down API responses
        
        This method truncates the HTML to a reasonable size while preserving valid UTF-8 encoding
        """
        # Convert string to bytes to measure actual size (some chars are multi-byte)
        encoded = page_source.encode("utf-8")
        max_bytes = settings.page_source_max_bytes
        
        # If it's already small enough, return as-is
        if len(encoded) <= max_bytes:
            return page_source
            
        # Truncate to max bytes
        truncated = encoded[:max_bytes]
        
        # Decode back to string, ignoring any partial multi-byte characters at the end
        # (errors="ignore" prevents crashes from cut-off UTF-8 sequences)
        return truncated.decode("utf-8", errors="ignore")
