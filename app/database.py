from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings


class Database:
    """MongoDB database connection handler"""

    # Store the client as a class variable so we can reuse the same connection
    client: MongoClient | None = None

    @classmethod
    def connect_db(cls) -> MongoClient:
        """Establish connection to MongoDB if not connected"""
        # If we already have a connection, just return it (connection pooling)
        if cls.client is not None:
            return cls.client

        try:
            # Create a new MongoDB client with production-ready settings
            cls.client = MongoClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=5_000,  # Fail fast if can't find a server
                connectTimeoutMS=5_000,  # Don't wait forever to establish connection
                maxPoolSize=50,  # Allow up to 50 concurrent connections
                retryWrites=True,  # Automatically retry failed writes
            )
            # Verify the connection actually works before proceeding
            cls.client.admin.command("ping")
            # Create any indexes we need (like unique constraint on URLs)
            cls._ensure_indexes()
            return cls.client
        except PyMongoError as exc:
            # Clean up and raise a more helpful error message
            cls.client = None
            raise RuntimeError(f"Unable to connect to MongoDB: {exc}")

    @classmethod
    def close_db(cls) -> None:
        """Close MongoDB connection"""
        if cls.client is not None:
            cls.client.close()
            cls.client = None

    @classmethod
    def get_collection(cls):
        """Get the metadata collection, connecting if necessary"""
        # Make sure we have a connection first
        client = cls.connect_db()
        # Navigate to our specific database and collection
        database = client[settings.database_name]
        return database[settings.collection_name]

    @classmethod
    def _ensure_indexes(cls) -> None:
        """Create indexes required for production workloads"""
        collection = cls.client[settings.database_name][settings.collection_name]
        # Create a unique index on URL to prevent duplicates and speed up lookups
        collection.create_index("url", unique=True)


# Global database instance that we'll import everywhere
db = Database()
