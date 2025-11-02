"""
WhiteMagic API - FastAPI Application

REST API for WhiteMagic memory management system.
"""

import os
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from whitemagic import MemoryManager

from .database import Database, User
from .dependencies import set_database, CurrentUser, DBSession
from .rate_limit import RateLimiter, set_rate_limiter, get_rate_limiter
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


# Global memory manager instances (keyed by user ID)
_memory_managers: dict[str, MemoryManager] = {}


def get_memory_manager(user: User) -> MemoryManager:
    """
    Get or create a MemoryManager for a user.
    
    Each user gets their own isolated memory directory.
    """
    user_id_str = str(user.id)
    
    if user_id_str not in _memory_managers:
        # User-specific base directory
        base_dir = Path(os.getenv("WM_BASE_PATH", ".")) / "users" / user_id_str
        base_dir.mkdir(parents=True, exist_ok=True)
        
        _memory_managers[user_id_str] = MemoryManager(base_dir=str(base_dir))
    
    return _memory_managers[user_id_str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./whitemagic.db"  # Default for development
    )
    
    db = Database(database_url, echo=False)
    await db.create_tables()
    set_database(db)
    
    # Initialize rate limiter
    redis_url = os.getenv("REDIS_URL")
    rate_limiter = RateLimiter(redis_url)
    set_rate_limiter(rate_limiter)
    
    yield
    
    # Shutdown
    await rate_limiter.close()
    await db.close()


# Create FastAPI app
app = FastAPI(
    title="WhiteMagic API",
    description="Tiered memory management system for AI agents",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(CORSHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
# Note: RateLimitMiddleware requires rate_limiter to be initialized
# It's added in a startup event handler below


# Exception handlers

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
    # TODO: Log to Sentry
    print(f"Unexpected error: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            )
        ).model_dump(),
    )


# Health check endpoint

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.2.0"}


# Dashboard endpoint (serve HTML)
@app.get("/", tags=["Dashboard"])
async def dashboard_home():
    """Serve dashboard HTML."""
    dashboard_path = Path(__file__).parent.parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "WhiteMagic API", "version": "0.2.0", "docs": "/docs"}


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
):
    """
    Create a new memory.
    
    Requires authentication via API key.
    """
    try:
        manager = get_memory_manager(user)
        
        path = manager.create_memory(
            title=request.title,
            content=request.content,
            memory_type=request.type,
            tags=request.tags,
        )
        
        # Get the created memory details
        memories = manager.list_memories(memory_type=request.type)
        created_memory = next(
            (m for m in memories if m["filename"] == path.name),
            None
        )
        
        if not created_memory:
            raise HTTPException(500, "Memory created but not found")
        
        return MemoryResponse(
            filename=created_memory["filename"],
            title=created_memory["title"],
            type=created_memory["type"],
            tags=created_memory.get("tags", []),
            created=created_memory["created"],
            path=str(path),
        )
        
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
        memories = manager.list_memories(memory_type=type)
        
        memory_responses = [
            MemoryResponse(
                filename=m["filename"],
                title=m["title"],
                type=m["type"],
                tags=m.get("tags", []),
                created=m["created"],
                path=m["path"],
            )
            for m in memories
        ]
        
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
        memories = manager.list_memories()
        memory = next((m for m in memories if m["filename"] == filename), None)
        
        if not memory:
            raise HTTPException(404, f"Memory not found: {filename}")
        
        return MemoryResponse(
            filename=memory["filename"],
            title=memory["title"],
            type=memory["type"],
            tags=memory.get("tags", []),
            created=memory["created"],
            path=memory["path"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get memory: {str(e)}")


@app.put("/api/v1/memories/{filename}", response_model=MemoryResponse, tags=["Memories"])
async def update_memory(
    filename: str,
    request: UpdateMemoryRequest,
    user: CurrentUser,
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
        
        manager.update_memory(filename, **updates)
        
        # Return updated memory
        return await get_memory(filename, user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update memory: {str(e)}")


@app.delete("/api/v1/memories/{filename}", response_model=SuccessResponse, tags=["Memories"])
async def delete_memory(
    filename: str,
    user: CurrentUser,
):
    """Delete a memory."""
    try:
        manager = get_memory_manager(user)
        manager.delete_memory(filename)
        
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
        
        results = manager.search_memories(
            query=request.query,
            tags=request.tags,
            memory_type=request.type,
        )
        
        # Limit results
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
        context = manager.generate_context_summary(tier=request.tier)
        
        # Count memories included (rough estimate)
        memories_count = len(manager.list_memories())
        
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
):
    """
    Consolidate old short-term memories to archive.
    
    Memories with 'proven' tag are promoted to long-term.
    """
    try:
        manager = get_memory_manager(user)
        
        result = manager.consolidate_memories(
            dry_run=request.dry_run,
            min_age_days=request.min_age_days,
        )
        
        message = f"{'[DRY RUN] ' if request.dry_run else ''}Archived {result['archived']} memories"
        if result.get('promoted', 0) > 0:
            message += f", promoted {result['promoted']} to long-term"
        
        return ConsolidateResponse(
            archived_count=result.get("archived", 0),
            promoted_count=result.get("promoted", 0),
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
        stats = manager.get_stats()
        
        return StatsResponse(
            short_term_count=stats.get("short_term_count", 0),
            long_term_count=stats.get("long_term_count", 0),
            total_count=stats.get("total_memories", 0),
            total_tags=stats.get("total_tags", 0),
            most_used_tags=stats.get("most_used_tags", [])[:10],  # Top 10
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get statistics: {str(e)}")


@app.get("/api/v1/tags", response_model=TagsResponse, tags=["Tags"])
async def list_tags(user: CurrentUser):
    """List all unique tags."""
    try:
        manager = get_memory_manager(user)
        tags = manager.list_tags()
        
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
        
        result = await session.execute(
            select(Quota).where(Quota.user_id == user.id)
        )
        quota = result.scalar_one_or_none()
        
        if not quota:
            # Create default quota
            quota = Quota(user_id=user.id)
            session.add(quota)
            await session.commit()
            await session.refresh(quota)
        
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
