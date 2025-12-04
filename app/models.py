from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Optional
from datetime import datetime


class URLRequest(BaseModel):
    """Request model for URL input
    
    Used for POST /metadata endpoint to validate incoming URLs.
    HttpUrl type ensures the URL is properly formatted before we try to fetch it.
    """
    url: HttpUrl


class URLMetadata(BaseModel):
    """Model for storing URL metadata in MongoDB
    
    This represents the structure of documents saved in the database.
    Pydantic validates the data types before we insert into MongoDB.
    """
    url: str  # Normalized URL (lowercase domain, no trailing slash)
    headers: Dict[str, str]  # HTTP response headers
    cookies: Dict[str, str]  # Cookies from the response
    page_source: str  # HTML content (truncated to max size)
    collected_at: datetime = Field(default_factory=datetime.utcnow)  # Timestamp when metadata was collected
    

class URLMetadataResponse(BaseModel):
    """Response model for GET endpoint
    
    This structure is returned to API consumers when they request metadata.
    Matches URLMetadata but adds an optional message field for additional info.
    """
    url: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    page_source: str
    collected_at: datetime
    message: Optional[str] = None  # Optional field for status messages
