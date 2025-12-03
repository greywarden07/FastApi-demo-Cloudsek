import pytest
from datetime import datetime
from unittest import mock

from app.database import db


def test_root_endpoint(client):
    """Test the root endpoint returns API information"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "endpoints" in data
    assert "POST /metadata" in data["endpoints"]
    assert "GET /metadata" in data["endpoints"]


def test_post_metadata_success(client, mock_db, mock_metadata_service):
    """Test POST /metadata endpoint with successful metadata collection"""
    
    # Mock database - no existing record
    mock_db.find_one.return_value = None
    
    # Mock metadata service
    mock_metadata_service.fetch_url_metadata.return_value = (
        {"content-type": "text/html"},
        {"session": "abc123"},
        "<html>Test Page</html>"
    )
    mock_metadata_service.create_metadata_document.return_value = {
        "url": "https://example.com",
        "headers": {"content-type": "text/html"},
        "cookies": {"session": "abc123"},
        "page_source": "<html>Test Page</html>",
        "collected_at": datetime.utcnow()
    }
    
    # Make request
    response = client.post(
        "/metadata",
        json={"url": "https://example.com"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Metadata collected and stored successfully"
    assert data["url"].rstrip('/') == "https://example.com"
    assert "collected_at" in data
    assert "stats" in data


def test_post_metadata_already_exists(client, mock_db):
    """Test POST /metadata when URL already exists in database"""
    
    # Mock database - existing record
    mock_db.find_one.return_value = {
        "url": "https://example.com",
        "headers": {},
        "cookies": {},
        "page_source": "",
        "collected_at": datetime.utcnow()
    }
    
    response = client.post(
        "/metadata",
        json={"url": "https://example.com"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "URL metadata already exists"


def test_post_metadata_invalid_url(client):
    """Test POST /metadata with invalid URL"""
    response = client.post(
        "/metadata",
        json={"url": "not-a-valid-url"}
    )
    
    assert response.status_code == 422  # Validation error


def test_get_metadata_exists(client, mock_db):
    """Test GET /metadata when record exists in database"""
    
    # Mock database - existing record
    mock_db.find_one.return_value = {
        "url": "https://example.com",
        "headers": {"content-type": "text/html"},
        "cookies": {"session": "abc123"},
        "page_source": "<html>Test</html>",
        "collected_at": datetime.utcnow()
    }
    
    response = client.get("/metadata?url=https://example.com")
    
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com"
    assert "headers" in data
    assert "cookies" in data
    assert "page_source" in data
    assert "collected_at" in data


def test_get_metadata_not_exists(client, mock_db):
    """Test GET /metadata when record doesn't exist - triggers background task"""
    
    # Mock database - no existing record
    mock_db.find_one.return_value = None
    
    response = client.get("/metadata?url=https://example.com")
    
    assert response.status_code == 202
    data = response.json()
    assert "Record doesn't exist" in data["message"]
    assert data["url"] == "https://example.com"
    assert data["status"] == "pending_collection"


def test_get_metadata_missing_url_parameter(client):
    """Test GET /metadata without URL parameter"""
    response = client.get("/metadata")
    
    assert response.status_code == 422  # Missing required parameter


def test_health_check_success(client):
    """Test health check endpoint when database is connected"""
    with mock.patch.object(db, 'connect_db') as mock_connect:
        mock_client = mock.MagicMock()
        mock_client.admin.command.return_value = {'ok': 1}
        mock_connect.return_value = mock_client

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


def test_health_check_failure(client):
    """Test health check endpoint when database is disconnected"""
    with mock.patch.object(db, 'connect_db') as mock_connect:
        mock_client = mock.MagicMock()
        mock_client.admin.command.side_effect = Exception("Connection failed")
        mock_connect.return_value = mock_client

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
