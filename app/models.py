from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Optional
from datetime import datetime


class URLRequest(BaseModel):
    """Request model for URL input"""
    url: HttpUrl


class URLMetadata(BaseModel):
    """Model for storing URL metadata in MongoDB"""
    url: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    page_source: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    

class URLMetadataResponse(BaseModel):
    """Response model for GET endpoint"""
    url: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    page_source: str
    collected_at: datetime
    message: Optional[str] = None
