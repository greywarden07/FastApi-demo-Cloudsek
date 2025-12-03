import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services import MetadataFetchError, MetadataService


@pytest.mark.asyncio
async def test_fetch_url_metadata_success():
    """Test successful metadata fetching"""
    
    # Mock httpx response
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/html", "server": "nginx"}
    mock_response.cookies = MagicMock()
    mock_response.cookies.jar = [
        SimpleNamespace(name="session", value="abc123"),
        SimpleNamespace(name="user_id", value="12345")
    ]
    mock_response.text = "<html><body>Test Page</body></html>"
    mock_response.raise_for_status.return_value = None
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        headers, cookies, page_source = await MetadataService.fetch_url_metadata("https://example.com")
        
        assert isinstance(headers, dict)
        assert "content-type" in headers
        assert isinstance(cookies, dict)
        assert "session" in cookies
        assert isinstance(page_source, str)
        assert "<html>" in page_source


@pytest.mark.asyncio
async def test_fetch_url_metadata_request_error():
    """Test metadata fetching with request error"""
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError("Connection failed")
        
        with pytest.raises(MetadataFetchError) as exc_info:
            await MetadataService.fetch_url_metadata("https://example.com")
        
        assert "Error fetching URL" in str(exc_info.value)


def test_create_metadata_document():
    """Test metadata document creation"""
    
    url = "https://example.com"
    headers = {"content-type": "text/html"}
    cookies = {"session": "abc123"}
    page_source = "<html>Test</html>"
    
    document = MetadataService.create_metadata_document(url, headers, cookies, page_source)
    
    assert isinstance(document, dict)
    assert document["url"] == url
    assert document["headers"] == headers
    assert document["cookies"] == cookies
    assert document["page_source"] == page_source
    assert "collected_at" in document
