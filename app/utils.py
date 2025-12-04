"""Utility helpers for the metadata service."""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """Return a canonical representation of the provided URL.
    
    This prevents duplicates caused by minor URL variations:
    - https://Google.com/ and https://google.com become the same
    - Trailing slashes are removed for consistency
    - Query parameters are preserved
    """
    # Remove any leading/trailing whitespace
    stripped = url.strip()
    # Break the URL into components
    parts = urlsplit(stripped)

    # Lowercase the scheme (http/https) and domain for consistency
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    # Remove trailing slashes from the path, but keep the path empty if it's just "/"
    path = parts.path.rstrip('/')
    if not path:
        path = ''

    # Keep query parameters as-is (they might be case-sensitive)
    query = parts.query

    # Reassemble the URL in canonical form (no fragment)
    return urlunsplit((scheme, netloc, path, query, ''))
