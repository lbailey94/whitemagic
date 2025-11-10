"""
WhiteMagic API - FastAPI Application

REST API for WhiteMagic memory management system.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from functools import lru_cache

from datetime import datetime
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Setup logging first
from .structured_logging import setup_logging, get_logger

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"
setup_logging(level=log_level, json_logs=json_logs)

logger = get_logger(__name__)

from .database import Database, User
from .dependencies import set_database, CurrentUser, DBSession
from .memory_service import get_memory_manager
from .version import get_version, get_version_dict
from .rate_limit import (
    RateLimiter,
    set_rate_limiter,
    get_rate_limiter,
    refresh_quota_usage,
)
from .middleware import RequestLoggingMiddleware, RateLimitMiddleware, CORSHeadersMiddleware
from .models import (
    CreateMemoryRequest,
    UpdateMemoryRequest,
    MemoryResponse,
    MemoryListResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    ContextRequest,
    ContextResponse,
    ConsolidateRequest,
    ConsolidateResponse,
    StatsResponse,
    TagsResponse,
    UserResponse,
    UserInfo,
    UsageStats,
    ErrorResponse,
    ErrorDetail,
    SuccessResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("whitemagic_startup", extra={"version": get_version()})
    
    database_url = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./whitemagic.db"  # Default for development
    )

    db = Database(database_url, echo=False)
    await db.create_tables()
    set_database(db)
    logger.info("database_initialized", extra={"url": database_url.split("@")[-1]})  # Hide credentials

    # Initialize rate limiter
    redis_url = os.getenv("REDIS_URL")
    rate_limiter = RateLimiter(redis_url)
    set_rate_limiter(rate_limiter)
    logger.info("rate_limiter_initialized", extra={"redis_enabled": bool(redis_url)})

    yield

    # Shutdown
    logger.info("whitemagic_shutdown")
    await rate_limiter.close()
    await db.close()


# Create FastAPI app
app = FastAPI(
    title="WhiteMagic API",
    description="Memory scaffolding for AI agents with tiered context generation",
    version=get_version(),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "https://yourdomain.com").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(CORSHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Optional Sentry integration
@lru_cache(maxsize=1)
def _maybe_init_sentry() -> None:
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
            environment=os.getenv("ENVIRONMENT", "production"),
            release=os.getenv("SENTRY_RELEASE", "whitemagic-2.1.0"),
        )
        logger.info("sentry_initialized")
    except ImportError:
        logger.warning("sentry_sdk_not_installed", extra={"dsn_set": True})


_maybe_init_sentry()


# ============================================================================
# Health & System Endpoints
# ============================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint (liveness probe).
    
    Returns 200 if the service is running.
    Does not check external dependencies.
    """
    return {
        "status": "healthy",
        "version": get_version(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/ready", tags=["System"])
async def readiness_check(db: DBSession):
    """
    Readiness check endpoint (readiness probe).
    
    Returns 200 if the service can handle requests.
    Checks database connectivity.
    """
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "version": get_version(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """
    Get frozen OpenAPI v1 schema.
    
    This endpoint returns the complete API schema.
    Clients can use this for code generation.
    """
    return app.openapi()


@app.get("/version", tags=["System"])
async def get_version_info():
    """Get version information"""
    return get_version_dict()


# Exception handlers


def _read_memory_body(manager, entry: dict) -> str:
    """Return the body for a memory entry."""
    path_str = entry.get("path")
    if not path_str:
        return ""

    file_path = manager.base_dir / path_str
    if not file_path.exists():
        return ""

    try:
        _, body = manager._read_memory_file(entry)
        return body
    except Exception:
        return ""


def _memory_response(manager, entry: dict) -> MemoryResponse:
    """Serialize a memory entry (including content) for API responses."""
    return MemoryResponse(
        filename=entry["filename"],
        title=entry["title"],
        type=entry["type"],
        tags=entry.get("tags", []),
        created=entry["created"],
        path=entry["path"],
        content=_read_memory_body(manager, entry),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=exc.detail,
            )
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "unexpected_error",
        exc_info=True,
        extra={
            "method": request.method,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            )
        ).model_dump(),
    )


# Dashboard endpoint (serve HTML)
@app.get("/", tags=["Dashboard"])
async def dashboard_home():
    """Serve dashboard HTML."""
    dashboard_path = Path(__file__).parent.parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "WhiteMagic API", "version": "2.1.0", "docs": "/docs"}


# Mount static files for dashboard
dashboard_dir = Path(__file__).parent.parent.parent / "dashboard"
if dashboard_dir.exists():
    app.mount("/static", StaticFiles(directory=str(dashboard_dir)), name="static")


# Include Whop routes
from .routes import whop, dashboard

app.include_router(whop.router)
app.include_router(dashboard.router)


# Memory endpoints


@app.post("/api/v1/memories", response_model=MemoryResponse, tags=["Memories"])
async def create_memory(
    request: CreateMemoryRequest,
    user: CurrentUser,
    session: DBSession,
):
    """
    Create a new memory.

    Requires authentication via API key.
    """
    try:
        manager = get_memory_manager(user)

        # Run blocking I/O in thread pool
        path = await asyncio.to_thread(
            manager.create_memory,
            title=request.title,
            content=request.content,
            memory_type=request.type,
            tags=request.tags,
        )

        # Get the created memory details
        all_memories = await asyncio.to_thread(manager.list_all_memories)
        memories = all_memories.get(request.type, [])
        created_memory = next((m for m in memories if m["filename"] == path.name), None)

        if not created_memory:
            raise HTTPException(500, "Memory created but not found")

        await refresh_quota_usage(session, user, manager)

        return _memory_response(manager, created_memory)

    except Exception as e:
        raise HTTPException(500, f"Failed to create memory: {str(e)}")


@app.get("/api/v1/memories", response_model=MemoryListResponse, tags=["Memories"])
async def list_memories(
    user: CurrentUser,
    type: Optional[str] = None,
):
    """
    List all memories for the current user.

    Optionally filter by type (short_term or long_term).
    """
    try:
        manager = get_memory_manager(user)
        all_memories = await asyncio.to_thread(manager.list_all_memories)

        # Filter by type if specified
        if type:
            memories = all_memories.get(type, [])
        else:
            # Combine all types
            memories = all_memories.get("short_term", []) + all_memories.get("long_term", [])

        memory_responses = [_memory_response(manager, m) for m in memories]

        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses),
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to list memories: {str(e)}")


@app.get("/api/v1/memories/{filename}", response_model=MemoryResponse, tags=["Memories"])
async def get_memory(
    filename: str,
    user: CurrentUser,
):
    """Get a specific memory by filename."""
    try:
        manager = get_memory_manager(user)

        # Find the memory
        all_memories = await asyncio.to_thread(manager.list_all_memories)
        # Search in all types
        all_items = all_memories.get("short_term", []) + all_memories.get("long_term", [])
        memory = next((m for m in all_items if m["filename"] == filename), None)

        if not memory:
            raise HTTPException(404, f"Memory not found: {filename}")

        return _memory_response(manager, memory)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get memory: {str(e)}")


@app.put("/api/v1/memories/{filename}", response_model=MemoryResponse, tags=["Memories"])
async def update_memory(
    filename: str,
    request: UpdateMemoryRequest,
    user: CurrentUser,
    session: DBSession,
):
    """Update an existing memory."""
    try:
        manager = get_memory_manager(user)

        # Build update kwargs
        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.content is not None:
            updates["content"] = request.content
        if request.tags is not None:
            updates["tags"] = request.tags

        if not updates:
            raise HTTPException(400, "No updates provided")

        await asyncio.to_thread(manager.update_memory, filename, **updates)
        await refresh_quota_usage(session, user, manager)

        return await get_memory(filename, user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update memory: {str(e)}")


@app.delete("/api/v1/memories/{filename}", response_model=SuccessResponse, tags=["Memories"])
async def delete_memory(
    filename: str,
    user: CurrentUser,
    session: DBSession,
):
    """Delete a memory."""
    try:
        manager = get_memory_manager(user)
        await asyncio.to_thread(manager.delete_memory, filename)
        await refresh_quota_usage(session, user, manager)

        return SuccessResponse(message=f"Memory deleted: {filename}")

    except Exception as e:
        raise HTTPException(500, f"Failed to delete memory: {str(e)}")


# Search endpoint


@app.post("/api/v1/search", response_model=SearchResponse, tags=["Search"])
async def search_memories(
    request: SearchRequest,
    user: CurrentUser,
):
    """
    Search memories by query and/or tags.

    Returns ranked results with preview snippets.
    """
    try:
        manager = get_memory_manager(user)

        results = await asyncio.to_thread(
            manager.search_memories,
            query=request.query,
            tags=request.tags,
            memory_type=request.type,
        )
        
        # Apply limit after search
        if request.limit:
            results = results[:request.limit]

        search_results = [
            SearchResultItem(
                filename=r["entry"]["filename"],
                title=r["entry"]["title"],
                type=r["entry"]["type"],
                tags=r["entry"].get("tags", []),
                created=r["entry"]["created"],
                preview=r.get("preview", "")[:200],  # First 200 chars
                score=r.get("score", 0),
            )
            for r in results
        ]

        return SearchResponse(
            results=search_results,
            total=len(search_results),
            query=request.query,
        )

    except Exception as e:
        raise HTTPException(500, f"Search failed: {str(e)}")


# Context generation endpoint


@app.post("/api/v1/context", response_model=ContextResponse, tags=["Context"])
async def generate_context(
    request: ContextRequest,
    user: CurrentUser,
):
    """
    Generate context summary at specified tier.

    - Tier 0: Minimal (titles only)
    - Tier 1: Balanced (titles + previews)
    - Tier 2: Full (complete content)
    """
    try:
        manager = get_memory_manager(user)
        context = await asyncio.to_thread(manager.generate_context_summary, tier=request.tier)

        # Count memories included (rough estimate)
        all_memories = await asyncio.to_thread(manager.list_all_memories)
        memories_count = len(all_memories.get("short_term", [])) + len(
            all_memories.get("long_term", [])
        )

        return ContextResponse(
            context=context,
            tier=request.tier,
            memories_included=memories_count,
        )

    except Exception as e:
        raise HTTPException(500, f"Context generation failed: {str(e)}")


# Consolidation endpoint


@app.post("/api/v1/consolidate", response_model=ConsolidateResponse, tags=["Consolidation"])
async def consolidate_memories(
    request: ConsolidateRequest,
    user: CurrentUser,
    session: DBSession,
):
    """
    Consolidate old short-term memories to archive.

    Memories with 'proven' tag are promoted to long-term.
    """
    try:
        manager = get_memory_manager(user)

        result = await asyncio.to_thread(
            manager.consolidate_short_term,
            dry_run=request.dry_run,
            min_age_days=request.min_age_days,
        )

        message = f"{'[DRY RUN] ' if request.dry_run else ''}Archived {result['archived']} memories"
        if result.get("auto_promoted", 0) > 0:
            message += f", promoted {result['auto_promoted']} to long-term"

        if not request.dry_run:
            await refresh_quota_usage(session, user, manager)

        return ConsolidateResponse(
            archived_count=result.get("archived", 0),
            promoted_count=result.get("auto_promoted", 0),
            dry_run=request.dry_run,
            message=message,
        )

    except Exception as e:
        raise HTTPException(500, f"Consolidation failed: {str(e)}")


# Statistics and tags endpoints


@app.get("/api/v1/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_statistics(user: CurrentUser):
    """Get memory statistics."""
    try:
        manager = get_memory_manager(user)

        # Get memory counts
        all_memories = await asyncio.to_thread(manager.list_all_memories)
        short_term_count = len(all_memories.get("short_term", []))
        long_term_count = len(all_memories.get("long_term", []))

        # Get tag stats
        tag_data = await asyncio.to_thread(manager.list_all_tags)
        total_tags = tag_data.get("total_unique_tags", 0)

        # Extract top tags with counts
        most_used_tags = [(tag["tag"], tag["count"]) for tag in tag_data.get("tags", [])[:10]]

        return StatsResponse(
            short_term_count=short_term_count,
            long_term_count=long_term_count,
            total_count=short_term_count + long_term_count,
            total_tags=total_tags,
            most_used_tags=most_used_tags,
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to get statistics: {str(e)}")


@app.get("/api/v1/tags", response_model=TagsResponse, tags=["Tags"])
async def list_tags(user: CurrentUser):
    """List all unique tags."""
    try:
        manager = get_memory_manager(user)
        tag_data = await asyncio.to_thread(manager.list_all_tags)

        # Extract just the tag names from the dict structure
        tags = [tag["tag"] for tag in tag_data.get("tags", [])]

        return TagsResponse(
            tags=sorted(tags),
            total=len(tags),
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to list tags: {str(e)}")


# User information endpoint


@app.get("/api/v1/user/me", response_model=UserResponse, tags=["User"])
async def get_current_user_info(
    user: CurrentUser,
    session: DBSession,
):
    """Get current user information and usage stats."""
    try:
        # Get quota from database
        from .database import Quota
        from sqlalchemy import select

        result = await session.execute(select(Quota).where(Quota.user_id == user.id))
        quota = result.scalar_one_or_none()

        if not quota:
            # Create default quota
            quota = Quota(user_id=user.id)
            session.add(quota)
            await session.commit()
            await session.refresh(quota)

        manager = get_memory_manager(user)
        await refresh_quota_usage(session, user, manager)

        return UserResponse(
            user=UserInfo(
                id=user.id,
                email=user.email,
                plan_tier=user.plan_tier,
                created_at=user.created_at,
                last_seen_at=user.last_seen_at,
            ),
            usage=UsageStats(
                requests_today=quota.requests_today,
                requests_this_month=quota.requests_this_month,
                memories_count=quota.memories_count,
                storage_bytes=quota.storage_bytes,
            ),
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to get user info: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
