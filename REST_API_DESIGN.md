# REST API Design: WhiteMagic as a Service

## Executive Summary

This document details the HTTP/REST API design for WhiteMagic, enabling remote access, cross-language clients, and cloud deployments.

**Prerequisites**: Python API (see PYTHON_API_DESIGN.md)  
**Framework**: FastAPI (async, auto-docs, type validation)  
**Effort**: 3-4 weeks  
**Impact**: Unlocks microservices, cross-language support, cloud deployment

---

## Why REST API?

### Use Cases

1. **Microservices Architecture**
   - Memory service runs independently
   - Multiple apps share one memory store
   - Horizontal scaling with load balancer

2. **Cross-Language Support**
   - JavaScript/TypeScript clients
   - Go services
   - Mobile apps (iOS/Android)
   - Any language with HTTP client

3. **Cloud Deployment**
   - AWS Lambda / Cloud Run (serverless)
   - Kubernetes deployments
   - Railway / Heroku (PaaS)
   - Docker containers

4. **Web Dashboards**
   - Admin UI for memory management
   - Visualization and analytics
   - Team collaboration

5. **Remote Access**
   - AI runs on server A, memory on server B
   - Distributed systems
   - Edge computing scenarios

---

## Architecture

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | FastAPI | Async, auto OpenAPI docs, Pydantic validation |
| **Server** | Uvicorn | ASGI server, production-ready |
| **Validation** | Pydantic v2 | Type-safe request/response models |
| **Docs** | OpenAPI/Swagger | Auto-generated from code |
| **Auth** | JWT/OAuth2 | Optional, industry standard |
| **Deployment** | Docker | Portable, standard |

### System Diagram

```
┌─────────────┐
│   Clients   │
│  (Any Lang) │
└──────┬──────┘
       │ HTTP/JSON
       ▼
┌─────────────────────┐
│   FastAPI Server    │
│  (Uvicorn/Gunicorn) │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  MemoryManager      │
│  (Python API)       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  File System        │
│  (Markdown Files)   │
└─────────────────────┘
```

---

## API Specification

### Base URL

```
Development: http://localhost:8000
Production:  https://api.whitemagic.ai
```

### Authentication (Optional)

```http
Authorization: Bearer <jwt_token>
```

### Content Type

```
Content-Type: application/json
Accept: application/json
```

---

## Endpoints

### 1. Create Memory

**POST** `/memories`

Creates a new memory entry.

**Request:**
```json
{
  "title": "Bug Fix Strategy",
  "content": "Use binary search to isolate performance issues",
  "memory_type": "short_term",
  "tags": ["debugging", "performance"]
}
```

**Response:** `201 Created`
```json
{
  "filename": "20231101_120000_bug_fix_strategy.md",
  "title": "Bug Fix Strategy",
  "path": "memory/short_term/20231101_120000_bug_fix_strategy.md",
  "memory_type": "short_term",
  "tags": ["debugging", "performance"],
  "created": "2023-11-01T12:00:00Z",
  "last_updated": "2023-11-01T12:00:00Z",
  "last_accessed": "2023-11-01T12:00:00Z",
  "status": "active"
}
```

**Errors:**
- `400 Bad Request` - Invalid memory_type or missing fields
- `500 Internal Server Error` - File system error

---

### 2. List Memories

**GET** `/memories`

List all memories with optional filtering.

**Query Parameters:**
- `memory_type` (optional): Filter by type ("short_term" or "long_term")
- `include_archived` (optional, default=false): Include archived memories
- `sort_by` (optional, default="created"): Sort field ("created", "updated", "accessed")
- `limit` (optional): Max results to return
- `offset` (optional): Pagination offset

**Response:** `200 OK`
```json
{
  "memories": [
    {
      "filename": "20231101_120000_bug_fix.md",
      "title": "Bug Fix Strategy",
      "memory_type": "short_term",
      "tags": ["debugging"],
      "created": "2023-11-01T12:00:00Z",
      "status": "active"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

---

### 3. Search Memories

**GET** `/memories/search`

Search memories by keywords and tags.

**Query Parameters:**
- `query` (optional): Search keywords
- `tags` (optional, multi-value): Filter by tags
- `memory_type` (optional): Filter by type
- `include_archived` (optional): Include archived
- `titles_only` (optional, default=false): Skip content scan

**Response:** `200 OK`
```json
{
  "results": [
    {
      "memory": {
        "filename": "20231101_120000_bug_fix.md",
        "title": "Bug Fix Strategy",
        "tags": ["debugging", "performance"]
      },
      "score": 0.95,
      "preview": "Use binary search to isolate performance issues...",
      "match_type": "content"
    }
  ],
  "total": 3
}
```

---

### 4. Get Memory

**GET** `/memories/{filename}`

Retrieve a specific memory with full content.

**Response:** `200 OK`
```json
{
  "filename": "20231101_120000_bug_fix.md",
  "title": "Bug Fix Strategy",
  "content": "Use binary search to isolate performance issues...",
  "memory_type": "short_term",
  "tags": ["debugging", "performance"],
  "created": "2023-11-01T12:00:00Z",
  "last_updated": "2023-11-01T12:00:00Z",
  "last_accessed": "2023-11-01T12:00:00Z",
  "status": "active",
  "path": "memory/short_term/20231101_120000_bug_fix.md"
}
```

**Errors:**
- `404 Not Found` - Memory doesn't exist

---

### 5. Update Memory

**PATCH** `/memories/{filename}`

Update memory content or metadata.

**Request:**
```json
{
  "title": "Updated Title",
  "content": "New content",
  "add_tags": ["new-tag"],
  "remove_tags": ["old-tag"]
}
```

**Response:** `200 OK`
```json
{
  "filename": "20231101_120000_bug_fix.md",
  "title": "Updated Title",
  "tags": ["debugging", "performance", "new-tag"],
  "last_updated": "2023-11-01T13:00:00Z"
}
```

---

### 6. Delete Memory

**DELETE** `/memories/{filename}`

Delete or archive a memory.

**Query Parameters:**
- `permanent` (optional, default=false): Permanently delete vs archive

**Response:** `204 No Content`

Or with details:
```json
{
  "action": "archived",
  "filename": "20231101_120000_bug_fix.md",
  "archived_path": "memory/archive/20231101_120000_bug_fix.md"
}
```

---

### 7. List Tags

**GET** `/tags`

Get all tags with usage statistics.

**Query Parameters:**
- `include_archived` (optional): Include archived memories

**Response:** `200 OK`
```json
{
  "tags": [
    {
      "name": "debugging",
      "count": 15,
      "used_in": ["short_term", "long_term"]
    },
    {
      "name": "performance",
      "count": 12,
      "used_in": ["short_term"]
    }
  ],
  "total_unique_tags": 23,
  "total_tagged_memories": 87
}
```

---

### 8. Generate Context

**GET** `/context/{tier}`

Generate context summary for AI prompt.

**Path Parameters:**
- `tier`: Context tier (0, 1, or 2)

**Response:** `200 OK` (text/plain)
```
=== SHORT-TERM CONTEXT ===
- Bug Fix Strategy (tags: debugging, performance)
  Use binary search to isolate performance issues

- Caching Pattern (tags: performance, proven)
  Redis cache reduced DB load by 70%

=== LONG-TERM PATTERNS ===
...
```

---

### 9. Consolidate

**POST** `/consolidate`

Run consolidation on short-term memories.

**Request:**
```json
{
  "dry_run": false,
  "auto_promote_tags": ["heuristic", "proven"]
}
```

**Response:** `200 OK`
```json
{
  "archived": 5,
  "auto_promoted": 2,
  "created_long_term": "20231101_consolidated.md",
  "dry_run": false,
  "timestamp": "2023-11-01T14:00:00Z"
}
```

---

### 10. Health Check

**GET** `/health`

Service health status.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "uptime_seconds": 3600,
  "memory_count": {
    "short_term": 15,
    "long_term": 42,
    "archived": 128
  }
}
```

---

## Implementation

### FastAPI Server

```python
# whitemagic/api/server.py
from fastapi import FastAPI, HTTPException, Query, Path as PathParam
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from whitemagic import MemoryManager
from whitemagic.exceptions import MemoryNotFoundError, InvalidTierError

# Initialize FastAPI
app = FastAPI(
    title="WhiteMagic API",
    description="Memory scaffolding for AI models",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global memory manager (or use dependency injection)
manager = MemoryManager()

# Request/Response Models
class CreateMemoryRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    memory_type: str = Field("short_term", pattern="^(short_term|long_term)$")
    tags: List[str] = Field(default_factory=list)

class UpdateMemoryRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = None
    add_tags: List[str] = Field(default_factory=list)
    remove_tags: List[str] = Field(default_factory=list)
    replace_tags: Optional[List[str]] = None

class MemoryResponse(BaseModel):
    filename: str
    title: str
    path: str
    memory_type: str
    tags: List[str]
    created: datetime
    last_updated: datetime
    last_accessed: datetime
    status: str
    content: Optional[str] = None

class SearchResultResponse(BaseModel):
    memory: MemoryResponse
    score: float
    preview: str
    match_type: str

# Endpoints
@app.post("/memories", response_model=MemoryResponse, status_code=201)
def create_memory(request: CreateMemoryRequest):
    """Create a new memory."""
    try:
        memory = manager.create_memory(
            title=request.title,
            content=request.content,
            memory_type=request.memory_type,
            tags=request.tags
        )
        return MemoryResponse(**memory.to_dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/memories", response_model=List[MemoryResponse])
def list_memories(
    memory_type: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    sort_by: str = Query("created"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all memories."""
    try:
        result = manager.list_all_memories(
            include_archived=include_archived,
            sort_by=sort_by
        )
        
        # Flatten and filter
        memories = []
        if memory_type:
            memories = result.get(memory_type, [])
        else:
            memories = result["short_term"] + result["long_term"]
            if include_archived:
                memories += result.get("archived", [])
        
        # Apply pagination
        return [
            MemoryResponse(**m.to_dict()) 
            for m in memories[offset:offset+limit]
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories/search", response_model=List[SearchResultResponse])
def search_memories(
    query: Optional[str] = Query(None),
    tags: List[str] = Query([]),
    memory_type: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    titles_only: bool = Query(False)
):
    """Search memories."""
    try:
        results = manager.search_memories(
            query=query,
            tags=tags,
            memory_type=memory_type,
            include_archived=include_archived,
            include_content=not titles_only
        )
        return [
            SearchResultResponse(**r.to_dict())
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories/{filename}", response_model=MemoryResponse)
def get_memory(filename: str = PathParam(...)):
    """Get a specific memory."""
    try:
        # Implementation: read from index
        entry = manager._index.get(filename)
        if not entry:
            raise MemoryNotFoundError(filename)
        
        frontmatter, content = manager._read_memory_file(entry)
        memory = Memory.from_entry(entry, content=content)
        return MemoryResponse(**memory.to_dict())
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/memories/{filename}", response_model=MemoryResponse)
def update_memory(
    filename: str = PathParam(...),
    request: UpdateMemoryRequest = None
):
    """Update a memory."""
    try:
        memory = manager.update_memory(
            filename=filename,
            title=request.title,
            content=request.content,
            tags=request.replace_tags,
            add_tags=request.add_tags,
            remove_tags=request.remove_tags
        )
        return MemoryResponse(**memory.to_dict())
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/memories/{filename}", status_code=204)
def delete_memory(
    filename: str = PathParam(...),
    permanent: bool = Query(False)
):
    """Delete or archive a memory."""
    try:
        manager.delete_memory(filename, permanent=permanent)
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tags")
def list_tags(include_archived: bool = Query(False)):
    """List all tags."""
    try:
        result = manager.list_all_tags(include_archived=include_archived)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/{tier}", response_class=PlainTextResponse)
def get_context(tier: int = PathParam(..., ge=0, le=2)):
    """Generate context for a tier."""
    try:
        return manager.generate_context_summary(tier)
    except InvalidTierError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/consolidate")
def consolidate(
    dry_run: bool = Query(True),
    auto_promote_tags: List[str] = Query([])
):
    """Consolidate short-term memories."""
    try:
        result = manager.consolidate_short_term(
            dry_run=dry_run,
            auto_promote_tags=auto_promote_tags or None
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    """Health check."""
    try:
        summary = manager.list_all_memories()
        return {
            "status": "healthy",
            "version": "2.1.0",
            "memory_count": summary.counts
        }
    except Exception:
        return {
            "status": "unhealthy",
            "version": "2.1.0"
        }

# Startup/shutdown
@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    print("WhiteMagic API starting...")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    print("WhiteMagic API shutting down...")
```

---

## Running the Server

### Development

```bash
# Install dependencies
pip install whitemagic[api]

# Run with auto-reload
uvicorn whitemagic.api.server:app --reload --port 8000

# Server starts at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Production

```bash
# Multi-worker setup
uvicorn whitemagic.api.server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info

# Or with Gunicorn
gunicorn whitemagic.api.server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY whitemagic/ ./whitemagic/
COPY memory/ ./memory/

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "whitemagic.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  whitemagic-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./memory:/app/memory
    environment:
      - LOG_LEVEL=info
    restart: unless-stopped

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - whitemagic-api
```

### Build and Run

```bash
# Build
docker build -t whitemagic-api:2.1.0 .

# Run
docker run -p 8000:8000 -v $(pwd)/memory:/app/memory whitemagic-api:2.1.0

# Or with docker-compose
docker-compose up -d
```

---

## Client Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Create memory
response = requests.post(f"{BASE_URL}/memories", json={
    "title": "API Test",
    "content": "Testing the API",
    "tags": ["test", "api"]
})
memory = response.json()
print(f"Created: {memory['filename']}")

# Search
response = requests.get(f"{BASE_URL}/memories/search", params={
    "query": "performance",
    "tags": ["debugging"]
})
results = response.json()
for result in results:
    print(f"Found: {result['memory']['title']}")

# Get context
response = requests.get(f"{BASE_URL}/context/1")
context = response.text
print(context)

# Update
response = requests.patch(
    f"{BASE_URL}/memories/{memory['filename']}",
    json={"add_tags": ["verified"]}
)

# Delete
requests.delete(f"{BASE_URL}/memories/{memory['filename']}")
```

### JavaScript/TypeScript

```typescript
const BASE_URL = 'http://localhost:8000';

// Create memory
const response = await fetch(`${BASE_URL}/memories`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        title: 'Bug Fix',
        content: 'Resolved caching issue',
        tags: ['bugfix', 'cache']
    })
});
const memory = await response.json();

// Search
const results = await fetch(
    `${BASE_URL}/memories/search?query=cache`
).then(r => r.json());

// Get context
const context = await fetch(`${BASE_URL}/context/1`).then(r => r.text());

// Update
await fetch(`${BASE_URL}/memories/${memory.filename}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({add_tags: ['resolved']})
});

// Delete
await fetch(`${BASE_URL}/memories/${memory.filename}`, {
    method: 'DELETE'
});
```

### cURL

```bash
# Create
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Testing","tags":["test"]}'

# Search
curl "http://localhost:8000/memories/search?query=cache&tags=performance"

# Get context
curl http://localhost:8000/context/1

# Update
curl -X PATCH http://localhost:8000/memories/20231101_test.md \
  -H "Content-Type: application/json" \
  -d '{"add_tags":["verified"]}'

# Delete
curl -X DELETE http://localhost:8000/memories/20231101_test.md

# Health check
curl http://localhost:8000/health
```

---

## Advanced Features

### Authentication (JWT)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()
SECRET_KEY = "your-secret-key"

def verify_token(credentials: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        return payload["sub"]  # user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/memories")
def create_memory(
    request: CreateMemoryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user_id = verify_token(credentials)
    # ... create memory for user
```

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.post("/memories")
@limiter.limit("10/minute")
def create_memory(request: Request, ...):
    pass
```

### CORS (Cross-Origin)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Logging & Monitoring

```python
import logging
from prometheus_client import Counter, Histogram

# Prometheus metrics
request_count = Counter(
    'whitemagic_requests_total',
    'Total requests'
)
request_duration = Histogram(
    'whitemagic_request_duration_seconds',
    'Request duration'
)

# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logging.info(f"{request.method} {request.url} - {duration:.3f}s")
    request_count.inc()
    request_duration.observe(duration)
    
    return response
```

---

## Cloud Deployment

### AWS Lambda (Serverless)

```python
# lambda_handler.py
from mangum import Mangum
from whitemagic.api.server import app

handler = Mangum(app)
```

### Google Cloud Run

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/whitemagic-api', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/whitemagic-api']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - gcloud
      - run
      - deploy
      - whitemagic-api
      - --image=gcr.io/$PROJECT_ID/whitemagic-api
      - --platform=managed
      - --region=us-central1
```

### Railway / Heroku

```
# Procfile
web: uvicorn whitemagic.api.server:app --host 0.0.0.0 --port $PORT
```

---

## Testing

### API Tests

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from whitemagic.api.server import app

client = TestClient(app)

def test_create_memory():
    response = client.post("/memories", json={
        "title": "Test",
        "content": "Test content",
        "tags": ["test"]
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test"

def test_search_memories():
    response = client.get("/memories/search?query=test")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)

def test_get_context():
    response = client.get("/context/1")
    assert response.status_code == 200
    assert len(response.text) > 0

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

---

## Benefits Summary

| Benefit | Impact |
|---------|--------|
| **Cross-Language** | Any language can use WhiteMagic |
| **Remote Access** | Distributed systems, microservices |
| **Scalability** | Horizontal scaling, load balancing |
| **Cloud Native** | Deploy anywhere (AWS, GCP, Azure) |
| **Standard Monitoring** | Prometheus, Datadog, etc. |
| **Auto Documentation** | OpenAPI/Swagger UI |
| **Authentication** | Standard OAuth/JWT flows |

---

## Next Steps

1. **Implement Core Endpoints** (Week 1)
2. **Add Auth & Rate Limiting** (Week 2)
3. **Docker & Deployment Guides** (Week 3)
4. **Load Testing & Optimization** (Week 4)

See TOOL_WRAPPERS_GUIDE.md for AI framework integrations.
