import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.database import db
from app.models import URLMetadataResponse, URLRequest
from app.services import MetadataFetchError, MetadataService
from app.utils import normalize_url


log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("metadata-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events"""
    # Startup
    logger.info("Starting application...")
    try:
        db.connect_db()
        logger.info("Connected to MongoDB")
    except RuntimeError as exc:
        logger.exception("MongoDB connection failed: %s", exc)
        raise
    yield
    # Shutdown
    logger.info("Shutting down application...")
    db.close_db()
    logger.info("Closed MongoDB connection")


app = FastAPI(
    title="HTTP Metadata Inventory API",
    description="API to collect and store HTTP metadata (headers, cookies, page source) from URLs",
    version="1.0.0",
    lifespan=lifespan
)


async def collect_metadata_background(url: str):
    """
    Background task to collect metadata for a URL
    This runs asynchronously without blocking the response
    """
    try:
        logger.info("Background task: Collecting metadata for %s", url)
        
        # Fetch metadata
        headers, cookies, page_source = await MetadataService.fetch_url_metadata(url)
        
        # Create document
        metadata_doc = MetadataService.create_metadata_document(url, headers, cookies, page_source)
        
        # Store in database
        collection = db.get_collection()
        collection.update_one(
            {"url": url},
            {"$set": metadata_doc},
            upsert=True,
        )
        
        logger.info("Background task: Successfully collected metadata for %s", url)
        
    except MetadataFetchError as exc:
        logger.error("Background metadata fetch failed for %s: %s", url, exc)
    except RuntimeError as exc:
        logger.error("Background metadata DB error for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected background error for %s: %s", url, exc)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "HTTP Metadata Inventory API",
        "endpoints": {
            "POST /metadata": "Collect and store metadata for a URL",
            "GET /metadata": "Retrieve metadata for a URL (triggers background collection if not exists)"
        }
    }


@app.post("/metadata", status_code=201)
async def create_metadata(url_request: URLRequest):
    """
    POST endpoint to collect and store URL metadata
    
    Args:
        url_request: Request body containing the URL
        
    Returns:
        Success message with stored metadata info
    """
    url_input = str(url_request.url)
    url = normalize_url(url_input)
    
    try:
        collection = db.get_collection()
        existing = collection.find_one({"url": url})

        operation = "refresh" if existing else "collect"
        logger.info("%s metadata for %s", "Refreshing" if existing else "Collecting", url)

        headers, cookies, page_source = await MetadataService.fetch_url_metadata(url)

        metadata_doc = MetadataService.create_metadata_document(url, headers, cookies, page_source)
        collection.update_one(
            {"url": url},
            {"$set": metadata_doc},
            upsert=True,
        )

        logger.info("Successfully %s metadata for %s", "refreshed" if existing else "stored", url)

        response_payload = {
            "message": "Metadata refreshed successfully" if existing else "Metadata collected and stored successfully",
            "url": url,
            "collected_at": metadata_doc["collected_at"].isoformat(),
            "stats": {
                "headers_count": len(headers),
                "cookies_count": len(cookies),
                "page_source_length": len(page_source)
            }
        }

        if existing:
            return JSONResponse(status_code=200, content=response_payload)

        return response_payload
        
    except MetadataFetchError as exc:
        logger.warning("Metadata fetch failed for %s: %s", url, exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except DuplicateKeyError:
        logger.info("Duplicate metadata detected for %s", url)
        raise HTTPException(status_code=409, detail="Metadata already exists")
    except RuntimeError as exc:
        logger.error("Database error for %s: %s", url, exc)
        raise HTTPException(status_code=503, detail="Database unavailable")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error processing POST for %s: %s", url, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metadata")
async def get_metadata(url: str, background_tasks: BackgroundTasks):
    """
    GET endpoint to retrieve URL metadata
    If record doesn't exist, triggers background collection
    
    Args:
        url: The URL to retrieve metadata for (query parameter)
        background_tasks: FastAPI background tasks handler
        
    Returns:
        Metadata if exists, or message that collection has been triggered
    """
    try:
        # Check if URL exists in database
        collection = db.get_collection()
        existing = collection.find_one({"url": url})
        
        if existing:
            # Record exists - return it
            logger.info(f"Found existing metadata for {url}")
            
            # Remove MongoDB _id field for response
            existing.pop("_id", None)
            
            return URLMetadataResponse(
                url=existing["url"],
                headers=existing["headers"],
                cookies=existing["cookies"],
                page_source=existing["page_source"],
                collected_at=existing["collected_at"]
            )
        
        else:
            # Record doesn't exist - trigger background collection
            logger.info(f"Record not found for {url}, triggering background collection")
            
            background_tasks.add_task(collect_metadata_background, url)
            
            return JSONResponse(
                status_code=202,
                content={
                    "message": "Record doesn't exist & request has been logged to collect the metadata, please check later",
                    "url": url,
                    "status": "pending_collection"
                }
            )
    
    except RuntimeError as exc:
        logger.error("Database error during GET for %s: %s", url, exc)
        raise HTTPException(status_code=503, detail="Database unavailable")
    except Exception as exc:  # noqa: BLE001
        logger.error("Error processing GET request for %s: %s", url, exc)
        raise HTTPException(status_code=500, detail="Error retrieving metadata")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        client = db.connect_db()
        client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except RuntimeError as exc:
        logger.error("Database health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(exc)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
