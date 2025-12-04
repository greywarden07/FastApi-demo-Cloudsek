# HTTP Metadata Inventory API

FastAPI service that captures HTTP metadata (headers, cookies, HTML snapshot) for any URL and persists it in MongoDB. The project ships with async acquisition, background collection, and a production-friendly Docker setup.

## Features
- **Automatic Data Refresh**: POST the same URL multiple times to fetch fresh metadata (headers, cookies, content update automatically)
- **URL Normalization**: Prevents duplicates by treating `https://Google.com/`, `https://google.com`, and `HTTPS://GOOGLE.COM/` as the same URL
- **Background Collection**: GET requests trigger async metadata collection when records don't exist (202 response)
- **Production-Ready Configuration**: All settings from environment variables only (no hardcoded secrets)
- **Database Reliability**: Connection validation on startup, unique indexes, connection pooling, and timeouts
- **Comprehensive Error Handling**: Graceful handling of network failures, timeouts, HTTP errors, and database issues
- **HTTP Client Safeguards**: Configurable timeouts, redirect limits, and page source truncation to prevent memory issues
- **Full Test Coverage**: 12 passing tests covering API endpoints, services, normalization, and refresh behavior

## Getting Started
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Create environment file**
   ```bash
   cp .env.example .env
   # Update MongoDB credentials + optional overrides
   ```
3. **Run the API**
   ```bash
   uvicorn app.main:app --reload
   ```

## Docker Compose
```bash
docker compose up --build
```
This brings up both the API (`http://localhost:8000`) and MongoDB (`mongodb://localhost:27017`).

## Running Tests
```bash
pytest --cov=app tests/
```

## Configuration
All settings are sourced from environment variables. Key entries:
- `MONGODB_URL` – Mongo connection string (required)
- `DATABASE_NAME` – Database name (required)
- `COLLECTION_NAME` – Collection for metadata (required)
- `LOG_LEVEL` – Standard logging level (default `INFO`)
- `HTTP_CLIENT_TIMEOUT` – Seconds before HTTP requests time out (default `20`)
- `HTTP_CLIENT_MAX_REDIRECTS` – Redirect limit (default `5`)
- `PAGE_SOURCE_MAX_BYTES` – Max stored HTML bytes (default `500000`)

## API Surface
- `GET /` – Service information and available endpoints
- `POST /metadata` – Fetch and store/update metadata for a URL
  - First POST: Creates new record (201 Created)
  - Subsequent POSTs: Refreshes existing data (200 OK)
  - Automatic URL normalization prevents duplicates
- `GET /metadata?url=...` – Retrieve stored metadata
  - Returns data immediately if exists (200 OK)
  - Triggers background collection if missing (202 Accepted)
- `GET /health` – Database connectivity check for monitoring/load balancers

## Project Layout
```
app/
  config.py        # Pydantic settings loader with environment variable validation
  database.py      # MongoDB connection lifecycle, indexing, and pooling
  main.py          # FastAPI application with API endpoints and lifespan management
  models.py        # Pydantic request/response schemas for validation
  services.py      # HTTP metadata acquisition with error handling and truncation
  utils.py         # URL normalization to prevent duplicate records
tests/
  conftest.py      # Pytest fixtures for mocking
  test_api.py      # API endpoint tests (POST, GET, health checks)
  test_services.py # Service layer tests (HTTP fetching, error handling)
```

## Key Improvements

### 1. URL Normalization
All URLs are normalized before storage to prevent duplicates:
- Lowercase scheme and domain: `HTTPS://GOOGLE.COM` → `https://google.com`
- Remove trailing slashes: `https://google.com/` → `https://google.com`
- This ensures `https://Google.com/`, `https://google.com`, and `HTTPS://google.com//` are treated as the same resource

### 2. Automatic Refresh
Unlike traditional APIs that reject duplicate POSTs, this API refreshes existing data:
- First POST to `example.com`: Fetches and stores metadata
- Second POST to `example.com`: Fetches fresh metadata and updates the record
- Useful for tracking website changes over time (updated headers, new cookies, content changes)

### 3. Comprehensive Error Handling
Every failure scenario returns a proper HTTP response:
- Network timeouts → 502 Bad Gateway
- HTTP 404/500 errors → 502 with status details
- Database unavailable → 503 Service Unavailable
- Invalid URLs → 422 Unprocessable Entity
- All errors are logged with context for debugging

### 4. Production-Ready Configuration
Zero hardcoded values - everything comes from environment variables:
- Required: `MONGODB_URL`, `DATABASE_NAME`, `COLLECTION_NAME`
- Optional with defaults: `LOG_LEVEL`, `HTTP_CLIENT_TIMEOUT`, `PAGE_SOURCE_MAX_BYTES`
- App fails fast at startup if required variables are missing

## Documentation
See `CHANGES.md` for detailed explanations of all improvements and their rationale.