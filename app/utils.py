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
   
    stripped = url.strip()
   
    parts = urlsplit(stripped)

    
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    
    path = parts.path.rstrip('/')
    if not path:
        path = ''

    
    query = parts.query

    
    return urlunsplit((scheme, netloc, path, query, ''))
