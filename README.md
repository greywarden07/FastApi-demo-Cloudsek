# HTTP Metadata Inventory API

FastAPI service that captures HTTP metadata (headers, cookies, HTML snapshot) for any URL and persists it in MongoDB. The project ships with async acquisition, background collection, and a production-friendly Docker setup.

## Features
- REST API to trigger metadata collection or retrieve cached metadata
- Background refresh when metadata is missing
- Centralized configuration via environment variables only (no secrets in code)
- Hardened MongoDB lifecycle with health checks and unique indexing
- HTTP client safeguards (timeouts, redirects, payload truncation)
- Comprehensive pytest suite covering services and API surface

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
- `GET /` – Service metadata
- `POST /metadata` – Fetch + persist metadata immediately
- `GET /metadata?url=...` – Retrieve metadata (triggers background fetch when missing)
- `GET /health` – MongoDB connectivity probe

## Project Layout
```
app/
  config.py        # Pydantic settings loader
  database.py      # MongoDB lifecycle + indexing
  main.py          # FastAPI application and routes
  models.py        # Request/response schemas
  services.py      # HTTP metadata acquisition
```