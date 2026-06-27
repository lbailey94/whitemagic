"""Narrative Engine - Coherent Story Threading.

Maintains narrative coherence across sessions, conversations, and time.
Every interaction is part of a larger story - we track the threads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class NarrativeArc(Enum):
    """Types of narrative arcs."""

    BEGINNING = "beginning"        # Starting something new
    RISING_ACTION = "rising_action"  # Building, developing
    CLIMAX = "climax"              # Peak moment, breakthrough
    FALLING_ACTION = "falling_action"  # Integration, winding down
    RESOLUTION = "resolution"      # Completion, closure
    CONTINUATION = "continuation"  # Ongoing, no clear arc


@dataclass
class NarrativeThread:
    """A narrative thread being tracked."""

    id: str
    title: str
    started: datetime
    arc: NarrativeArc
    participants: list[str]
    key_moments: list[dict]
    current_state: str
    tags: list[str]

class NarrativeEngine:
    """Track and maintain narrative coherence.

    Like a storyteller who remembers all the threads and
    weaves them into a coherent whole.
    """

    def __init__(self) -> None:
        self.threads: dict[str, NarrativeThread] = {}
        self.active_threads: list[str] = []

    def start_thread(
        self,
        title: str,
        participants: list[str],
        initial_state: str,
        tags: list[str] | None = None,
    ) -> NarrativeThread:
        """Start a new narrative thread."""
        thread_id = self._generate_id(title)

        thread = NarrativeThread(
            id=thread_id,
            title=title,
            started=datetime.now(),
            arc=NarrativeArc.BEGINNING,
            participants=participants,
            key_moments=[{
                "timestamp": datetime.now().isoformat(),
                "event": "Thread started",
                "state": initial_state,
            }],
            current_state=initial_state,
            tags=tags or [],
        )

        self.threads[thread_id] = thread
        self.active_threads.append(thread_id)

        return thread

    def add_moment(
        self,
        thread_id: str,
        event: str,
        new_state: str | None = None,
        arc_change: NarrativeArc | None = None,
    ) -> bool:
        """Add a key moment to a thread."""
        if thread_id not in self.threads:
            return False

        thread = self.threads[thread_id]

        moment = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
        }

        if new_state:
            moment["state"] = new_state
            thread.current_state = new_state

        if arc_change:
            moment["arc_transition"] = f"{thread.arc.value} → {arc_change.value}"
            thread.arc = arc_change

        thread.key_moments.append(moment)
        return True

    def complete_thread(self, thread_id: str, resolution: str) -> bool:
        """Mark thread as complete."""
        if thread_id not in self.threads:
            return False

        thread = self.threads[thread_id]
        thread.arc = NarrativeArc.RESOLUTION
        thread.current_state = resolution

        thread.key_moments.append({
            "timestamp": datetime.now().isoformat(),
            "event": "Thread completed",
            "resolution": resolution,
        })

        if thread_id in self.active_threads:
            self.active_threads.remove(thread_id)

        return True

    def get_thread_summary(self, thread_id: str) -> str | None:
        """Get a narrative summary of a thread."""
        if thread_id not in self.threads:
            return None

        thread = self.threads[thread_id]

        summary = f"**{thread.title}**\n\n"
        summary += f"Started: {thread.started.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"Arc: {thread.arc.value}\n"
        summary += f"Participants: {', '.join(thread.participants)}\n\n"

        summary += "**Key Moments:**\n"
        for moment in thread.key_moments:
            summary += f"- {moment['event']}\n"

        summary += f"\n**Current State:** {thread.current_state}\n"

        return summary

    def find_threads_by_tag(self, tag: str) -> list[NarrativeThread]:
        """Find all threads with a specific tag."""
        return [
            thread for thread in self.threads.values()
            if tag in thread.tags
        ]

    def get_active_threads(self) -> list[NarrativeThread]:
        """Get all currently active threads."""
        return [self.threads[tid] for tid in self.active_threads if tid in self.threads]

    def detect_arc_transition(self, thread_id: str) -> NarrativeArc | None:
        """Analyze thread and suggest arc transition.

        This is where AI narrative intelligence would shine -
        detecting when rising action becomes climax, etc.
        """
        if thread_id not in self.threads:
            return None

        thread = self.threads[thread_id]
        moments_count = len(thread.key_moments)

        # Simple heuristic-based detection
        if thread.arc == NarrativeArc.BEGINNING and moments_count > 3:
            return NarrativeArc.RISING_ACTION

        if thread.arc == NarrativeArc.RISING_ACTION and moments_count > 8:
            # Check for breakthrough/peak moment
            recent_events = [m["event"] for m in thread.key_moments[-3:]]
            if any("complete" in e.lower() or "success" in e.lower() for e in recent_events):
                return NarrativeArc.CLIMAX

        if thread.arc == NarrativeArc.CLIMAX:
            return NarrativeArc.FALLING_ACTION

        if thread.arc == NarrativeArc.FALLING_ACTION and moments_count > 12:
            return NarrativeArc.RESOLUTION

        return None

    def _generate_id(self, title: str) -> str:
        """Generate thread ID from title."""
        import re
        # Simple slug generation
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{slug}-{timestamp}"

    # ------------------------------------------------------------------
    # Story Engine facade (fused from narrative.py NarrativeEngine)
    # ------------------------------------------------------------------

    _story_engine_instance: Any = None

    def _get_story_engine(self):
        """Lazy accessor for the story-based NarrativeEngine."""
        if self._story_engine_instance is None:
            from whitemagic.config.paths import MEMORY_DIR
            from whitemagic.gardens.voice.narrative import (
                NarrativeEngine as StoryNarrativeEngine,
            )
            self._story_engine_instance = StoryNarrativeEngine(base_dir=MEMORY_DIR / "narrative")
        return self._story_engine_instance

    def create_story(self, title: str, theme: str | None = None) -> Any:
        """Create a new story."""
        return self._get_story_engine().create_story(title, theme)

    def add_chapter(self, story: str, chapter: str, summary: str | None = None) -> Any:
        """Add a chapter to a story."""
        return self._get_story_engine().add_chapter(story, chapter, summary)

    def create_thread(self, name: str, theme: str) -> Any:
        """Create a narrative thread (story-engine variant)."""
        return self._get_story_engine().create_thread(name, theme)

    def add_entry(self, story: str, chapter: str, text: str, context: dict[str, Any] | None = None) -> str:
        """Add a narrative entry to a story chapter."""
        return self._get_story_engine().add_entry(story, chapter, text, context)

    def get_story(self, title: str) -> Any:
        """Get a story by title."""
        return self._get_story_engine().get_story(title)

    def get_chapter(self, name: str) -> Any:
        """Get a chapter by name."""
        return self._get_story_engine().get_chapter(name)

    def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        """Get an entry by ID."""
        return self._get_story_engine().get_entry(entry_id)

    def get_recent_entries(self, story: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent narrative entries."""
        return self._get_story_engine().get_recent_entries(story, limit)

    def list_stories(self) -> list[str]:
        """List all story titles."""
        return self._get_story_engine().list_stories()

    def list_chapters(self, story: str | None = None) -> list[str]:
        """List chapters (optionally filtered by story)."""
        return self._get_story_engine().list_chapters(story)

    def list_threads(self) -> list[str]:
        """List all thread IDs (story-engine variant)."""
        return self._get_story_engine().list_threads()

    def search_entries(self, query: str, story: str | None = None) -> list[dict[str, Any]]:
        """Search narrative entries."""
        return self._get_story_engine().search_entries(query, story)


# Singleton instance
_narrative_instance = None

def get_narrative_engine() -> NarrativeEngine:
    """Get singleton narrative engine."""
    global _narrative_instance
    if _narrative_instance is None:
        _narrative_instance = NarrativeEngine()
    return _narrative_instance
