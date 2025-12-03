import os

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("COLLECTION_NAME", "metadata")

from app.main import app
from app.database import db


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database collection"""
    with patch('app.main.db') as mock:
        mock_collection = MagicMock()
        mock.get_collection.return_value = mock_collection
        yield mock_collection


@pytest.fixture
def mock_metadata_service():
    """Mock MetadataService for testing"""
    with patch('app.main.MetadataService') as mock:
        mock.fetch_url_metadata = AsyncMock()
        mock.create_metadata_document = MagicMock()
        yield mock
