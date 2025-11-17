"""
Session Management System

Provides state management for work sessions with checkpoint/resume capabilities.
Enables seamless continuation of work across interruptions.

Features:
- Session creation and lifecycle management
- Automatic checkpointing (every 30 min default)
- Resume with full context restoration
- Session metrics and progress tracking
- Multi-session support

Usage:
    from whitemagic.sessions import SessionManager
    
    # Create session
    manager = SessionManager()
    session = await manager.create_session(
        name="v2.2.7-implementation",
        goals=["Parallel infra", "MCP tools"],
        auto_checkpoint=True
    )
    
    # Work...
    
    # Checkpoint
    await manager.checkpoint_session(session.id)
    
    # Resume later
    session = await manager.resume_session(session.id)
"""

from whitemagic.sessions.manager import SessionManager, Session, SessionStatus
from whitemagic.sessions.checkpoint import CheckpointManager, Checkpoint

__all__ = [
    "SessionManager",
    "Session",
    "SessionStatus",
    "CheckpointManager",
    "Checkpoint",
]
