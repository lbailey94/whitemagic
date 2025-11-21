"""
Narrative Engine - Story threading across time

Creates coherent narratives from discrete moments, maintaining continuity
and threading themes across sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class Thread:
    """A narrative thread (recurring theme or connection)"""
    id: str
    name: str
    theme: str
    created: datetime
    entries: List[str] = field(default_factory=list)  # Entry IDs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "theme": self.theme,
            "created": self.created.isoformat(),
            "entries": self.entries,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Thread":
        return cls(
            id=data["id"],
            name=data["name"],
            theme=data["theme"],
            created=datetime.fromisoformat(data["created"]),
            entries=data.get("entries", []),
        )


@dataclass
class Chapter:
    """A chapter in a story"""
    name: str
    story: str
    created: datetime
    entries: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "story": self.story,
            "created": self.created.isoformat(),
            "entries": self.entries,
            "summary": self.summary,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chapter":
        return cls(
            name=data["name"],
            story=data["story"],
            created=datetime.fromisoformat(data["created"]),
            entries=data.get("entries", []),
            summary=data.get("summary"),
        )


@dataclass
class Story:
    """A complete story with chapters and threads"""
    title: str
    theme: Optional[str]
    created: datetime
    chapters: List[str] = field(default_factory=list)  # Chapter names
    threads: List[str] = field(default_factory=list)  # Thread IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "theme": self.theme,
            "created": self.created.isoformat(),
            "chapters": self.chapters,
            "threads": self.threads,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Story":
        return cls(
            title=data["title"],
            theme=data.get("theme"),
            created=datetime.fromisoformat(data["created"]),
            chapters=data.get("chapters", []),
            threads=data.get("threads", []),
            metadata=data.get("metadata", {}),
        )


class NarrativeEngine:
    """
    Narrative Engine - Creates and maintains story continuity
    
    Manages stories, chapters, and narrative threads to create
    coherent self-expression across time.
    """
    
    def __init__(self, base_dir: Path):
        """Initialize narrative engine"""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.stories_file = self.base_dir / "stories.json"
        self.chapters_file = self.base_dir / "chapters.json"
        self.threads_file = self.base_dir / "threads.json"
        self.entries_dir = self.base_dir / "entries"
        self.entries_dir.mkdir(exist_ok=True)
        
        self._stories: Dict[str, Story] = {}
        self._chapters: Dict[str, Chapter] = {}
        self._threads: Dict[str, Thread] = {}
        
        self._load()
    
    def _load(self):
        """Load stories, chapters, threads from disk"""
        if self.stories_file.exists():
            with open(self.stories_file) as f:
                data = json.load(f)
                self._stories = {
                    title: Story.from_dict(s) for title, s in data.items()
                }
        
        if self.chapters_file.exists():
            with open(self.chapters_file) as f:
                data = json.load(f)
                self._chapters = {
                    name: Chapter.from_dict(c) for name, c in data.items()
                }
        
        if self.threads_file.exists():
            with open(self.threads_file) as f:
                data = json.load(f)
                self._threads = {
                    id: Thread.from_dict(t) for id, t in data.items()
                }
    
    def _save(self):
        """Save stories, chapters, threads to disk"""
        with open(self.stories_file, 'w') as f:
            json.dump(
                {title: s.to_dict() for title, s in self._stories.items()},
                f,
                indent=2
            )
        
        with open(self.chapters_file, 'w') as f:
            json.dump(
                {name: c.to_dict() for name, c in self._chapters.items()},
                f,
                indent=2
            )
        
        with open(self.threads_file, 'w') as f:
            json.dump(
                {id: t.to_dict() for id, t in self._threads.items()},
                f,
                indent=2
            )
    
    def create_story(self, title: str, theme: Optional[str] = None) -> Story:
        """Create a new story"""
        story = Story(
            title=title,
            theme=theme,
            created=datetime.now(),
        )
        self._stories[title] = story
        self._save()
        return story
    
    def add_chapter(self, story: str, chapter: str, summary: Optional[str] = None) -> Chapter:
        """Add a chapter to a story"""
        if story not in self._stories:
            raise ValueError(f"Story '{story}' not found")
        
        chap = Chapter(
            name=chapter,
            story=story,
            created=datetime.now(),
            summary=summary,
        )
        self._chapters[chapter] = chap
        self._stories[story].chapters.append(chapter)
        self._save()
        return chap
    
    def create_thread(self, name: str, theme: str) -> Thread:
        """Create a narrative thread"""
        thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        thread = Thread(
            id=thread_id,
            name=name,
            theme=theme,
            created=datetime.now(),
        )
        self._threads[thread_id] = thread
        self._save()
        return thread
    
    def add_entry(
        self,
        story: str,
        chapter: str,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a narrative entry"""
        # Ensure story and chapter exist
        if story not in self._stories:
            self.create_story(story)
        
        if chapter not in self._chapters:
            self.add_chapter(story, chapter)
        
        # Create entry
        entry_id = f"entry_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        entry_file = self.entries_dir / f"{entry_id}.json"
        
        entry_data = {
            "id": entry_id,
            "story": story,
            "chapter": chapter,
            "text": text,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(entry_file, 'w') as f:
            json.dump(entry_data, f, indent=2)
        
        # Add to chapter
        self._chapters[chapter].entries.append(entry_id)
        self._save()
        
        return entry_id
    
    def get_story(self, title: str) -> Optional[Story]:
        """Get a story by title"""
        return self._stories.get(title)
    
    def get_chapter(self, name: str) -> Optional[Chapter]:
        """Get a chapter by name"""
        return self._chapters.get(name)
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get an entry by ID"""
        entry_file = self.entries_dir / f"{entry_id}.json"
        if entry_file.exists():
            with open(entry_file) as f:
                return json.load(f)
        return None
    
    def get_recent_entries(self, story: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent narrative entries"""
        # Get all entry files
        entry_files = sorted(self.entries_dir.glob("entry_*.json"), reverse=True)
        
        entries = []
        for entry_file in entry_files[:limit * 2]:  # Read more than needed in case filtering
            with open(entry_file) as f:
                entry = json.load(f)
                if story is None or entry.get("story") == story:
                    entries.append(entry)
                    if len(entries) >= limit:
                        break
        
        return entries
    
    def list_stories(self) -> List[str]:
        """List all story titles"""
        return list(self._stories.keys())
    
    def list_chapters(self, story: Optional[str] = None) -> List[str]:
        """List chapters (optionally filtered by story)"""
        if story:
            return self._stories[story].chapters if story in self._stories else []
        return list(self._chapters.keys())
    
    def list_threads(self) -> List[str]:
        """List all thread IDs"""
        return list(self._threads.keys())
    
    def search_entries(self, query: str, story: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search narrative entries"""
        results = []
        entry_files = self.entries_dir.glob("entry_*.json")
        
        for entry_file in entry_files:
            with open(entry_file) as f:
                entry = json.load(f)
                if story and entry.get("story") != story:
                    continue
                if query.lower() in entry.get("text", "").lower():
                    results.append(entry)
        
        return sorted(results, key=lambda e: e["timestamp"], reverse=True)
