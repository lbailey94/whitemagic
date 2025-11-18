"""
Scratchpad System - Working Memory

Temporary working memory for active tasks. Perfect for tracking decisions,
questions, and next steps during a work session.

Usage:
    from whitemagic.scratchpad import ScratchpadManager

    manager = ScratchpadManager()
    scratchpad = await manager.create("debugging-session")

    await manager.update(scratchpad.id, "decisions", "Use approach A")
    await manager.finalize(scratchpad.id)  # Convert to memory
"""

from whitemagic.scratchpad.manager import Scratchpad, ScratchpadManager

__all__ = ["ScratchpadManager", "Scratchpad"]
