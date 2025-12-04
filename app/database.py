from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings


class Database:
    """MongoDB database connection handler"""

    client: MongoClient | None = None

    @classmethod
    def connect_db(cls) -> MongoClient:
        """Establish connection to MongoDB if not connected"""
        if cls.client is not None:
            return cls.client

        try:
            cls.client = MongoClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=5_000,
                connectTimeoutMS=5_000,
                maxPoolSize=50,
                retryWrites=True,
            )
            cls.client.admin.command("ping")
            cls._ensure_indexes()
            return cls.client
        except PyMongoError as exc:
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
        client = cls.connect_db()
        database = client[settings.database_name]
        return database[settings.collection_name]

    @classmethod
    def _ensure_indexes(cls) -> None:
        """Create indexes required for production workloads"""
        collection = cls.client[settings.database_name][settings.collection_name]
        collection.create_index("url", unique=True)


# Global database instance
db = Database()
