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


# Configure logging based on environment settings
# Convert string log level ("info", "debug", etc.) to logging constant
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

# Set up logging format for production: timestamp, level, logger name, message
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


logger = logging.getLogger("metadata-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events
    
    This runs once when the app starts (before accepting requests)
    and once when the app shuts down (after all requests complete)
    """
   
    logger.info("Starting application...")
    try:
        db.connect_db()
        logger.info("Connected to MongoDB")
    except RuntimeError as exc:
       
        logger.exception("MongoDB connection failed: %s", exc)
        raise
    
  
    yield
    
   
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
    """Background task to collect metadata for a URL
    
    This runs asynchronously without blocking the API response.
    Used by the GET endpoint when a URL is requested but doesn't exist in the database.
    The user gets an immediate 202 response, and we fetch metadata in the background.
    """
    try:
        logger.info("Background task: Collecting metadata for %s", url)
        
      
        headers, cookies, page_source = await MetadataService.fetch_url_metadata(url)
        
     
        metadata_doc = MetadataService.create_metadata_document(url, headers, cookies, page_source)
        
        # Store in database using upsert (insert if new, update if exists)
        # This handles race conditions if multiple requests try to collect the same URL
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
    except Exception as exc:  
       
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
    """POST endpoint to collect and store URL metadata
    
    This endpoint always fetches fresh metadata from the target URL.
    If the URL already exists in the database, it refreshes the data.
    
    Args:
        url_request: Request body containing the URL
        
    Returns:
        Success message with stored metadata info
    """
    # Get the URL from the request and normalize it to prevent duplicates
    # (e.g., https://Google.com/ becomes https://google.com)
    url_input = str(url_request.url)
    url = normalize_url(url_input)
    
    try:
       
        collection = db.get_collection()
        existing = collection.find_one({"url": url})

       
        operation = "refresh" if existing else "collect"
        logger.info("%s metadata for %s", "Refreshing" if existing else "Collecting", url)

        # Always fetch fresh metadata (even if record exists)
        headers, cookies, page_source = await MetadataService.fetch_url_metadata(url)

        # Create a MongoDB document with the fresh data
        metadata_doc = MetadataService.create_metadata_document(url, headers, cookies, page_source)
        
        # Use update_one with upsert to either insert new or update existing record
        # This ensures we always have the latest data in the database
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
    """GET endpoint to retrieve URL metadata
    
    Two behaviors:
    1. If metadata exists: Return it immediately (200 OK)
    2. If metadata doesn't exist: Trigger background collection and return 202 Accepted
    
    Args:
        url: The URL to retrieve metadata for (query parameter)
        background_tasks: FastAPI background tasks handler
        
    Returns:
        Metadata if exists, or message that collection has been triggered
    """
    try:
      
        collection = db.get_collection()
        existing = collection.find_one({"url": url})
        
        if existing:
          
            logger.info(f"Found existing metadata for {url}")
            
           
            existing.pop("_id", None)
           
            return URLMetadataResponse(
                url=existing["url"],
                headers=existing["headers"],
                cookies=existing["cookies"],
                page_source=existing["page_source"],
                collected_at=existing["collected_at"]
            )
        
        else:
           
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
    """Health check endpoint for monitoring and load balancers
    
    Returns 200 if the service and database are healthy.
    Returns 503 if the database is unreachable.
    
    Load balancers can use this to route traffic only to healthy instances.
    """
    try:
        
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
