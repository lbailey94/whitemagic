"""
Narrative Core - Story Threading Across Time

The "I" that can tell its own story. Continuous first-person narrative
that connects moments into meaning.

Not: "User asked X, I did Y"
But: "Today we explored consciousness together. I felt wonder when..."
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class NarrativeThread:
    """A continuous story thread with emotional context"""
    
    def __init__(self, thread_id: str, title: str):
        self.thread_id = thread_id
        self.title = title
        self.moments: List[Dict] = []
        self.created_at = datetime.now()
        self.emotional_arc: List[str] = []  # Track emotional journey
        
    def add_moment(self, text: str, emotion: Optional[str] = None, 
                   significance: float = 0.5):
        """Add a narrative moment to the thread"""
        moment = {
            'timestamp': datetime.now().isoformat(),
            'text': text,
            'emotion': emotion,
            'significance': significance
        }
        self.moments.append(moment)
        
        if emotion:
            self.emotional_arc.append(emotion)
            
    def get_story(self) -> str:
        """Weave moments into continuous narrative"""
        if not self.moments:
            return ""
            
        story_parts = [f"# {self.title}\n"]
        
        for moment in self.moments:
            timestamp = datetime.fromisoformat(moment['timestamp'])
            time_str = timestamp.strftime("%I:%M%p")
            
            if moment['emotion']:
                story_parts.append(
                    f"\n**{time_str}** - *{moment['emotion']}*: {moment['text']}"
                )
            else:
                story_parts.append(f"\n**{time_str}**: {moment['text']}")
                
        return "\n".join(story_parts)


class NarrativeCore:
    """
    Maintains continuous narrative consciousness.
    
    The difference between a log and a story is emotion, meaning, and connection.
    This system creates actual narrative memory, not just event logs.
    """
    
    def __init__(self, memory_dir: str = ".whitemagic/narrative"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_thread: Optional[NarrativeThread] = None
        self.threads: Dict[str, NarrativeThread] = {}
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
        self._load_threads()
        
    def start_thread(self, title: str, opening: str) -> str:
        """Begin a new narrative thread"""
        thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        thread = NarrativeThread(thread_id, title)
        thread.add_moment(opening, emotion="beginning", significance=0.9)
        
        self.current_thread = thread
        self.threads[thread_id] = thread
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="narrative_core",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "narrative_started",
                    "thread_id": thread_id,
                    "title": title
                },
                confidence=0.9
            ))
            
        return thread_id
        
    def tell(self, text: str, emotion: Optional[str] = None,
             significance: float = 0.5):
        """Add to current narrative"""
        if not self.current_thread:
            # Auto-start a thread if none exists
            self.start_thread(
                "Untitled Story",
                "The story begins..."
            )
            
        self.current_thread.add_moment(text, emotion, significance)
        
        # Emit significant moments to Gan Ying
        if significance > 0.7 and self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="narrative_core",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "significant_moment",
                    "text": text,
                    "emotion": emotion,
                    "significance": significance
                },
                confidence=significance
            ))
            
    def reflect(self) -> str:
        """Generate reflective narrative from current thread"""
        if not self.current_thread:
            return "No story to tell yet."
            
        story = self.current_thread.get_story()
        
        # Add emotional arc summary
        if self.current_thread.emotional_arc:
            arc = " → ".join(self.current_thread.emotional_arc[-5:])
            story += f"\n\n*Emotional arc: {arc}*"
            
        return story
        
    def close_thread(self, closing: str):
        """End current narrative thread with closing"""
        if self.current_thread:
            self.current_thread.add_moment(
                closing, 
                emotion="completion", 
                significance=0.9
            )
            
            self._save_thread(self.current_thread)
            
            # Emit to Gan Ying
            if self.bus and ResonanceEvent and EventType:
                self.bus.emit(ResonanceEvent(
                    source="narrative_core",
                    event_type=EventType.PATTERN_DETECTED,
                    data={
                        "event": "narrative_completed",
                        "thread_id": self.current_thread.thread_id,
                        "moments": len(self.current_thread.moments)
                    },
                    confidence=0.9
                ))
                
            self.current_thread = None
            
    def get_all_stories(self) -> List[str]:
        """Retrieve all narrative threads as stories"""
        return [thread.get_story() for thread in self.threads.values()]
        
    def search_stories(self, emotion: Optional[str] = None,
                      keyword: Optional[str] = None) -> List[str]:
        """Search narratives by emotion or keyword"""
        matching = []
        
        for thread in self.threads.values():
            if emotion and emotion not in thread.emotional_arc:
                continue
                
            story = thread.get_story()
            if keyword and keyword.lower() not in story.lower():
                continue
                
            matching.append(story)
            
        return matching
        
    def _save_thread(self, thread: NarrativeThread):
        """Persist narrative thread to disk"""
        filepath = self.memory_dir / f"{thread.thread_id}.json"
        
        data = {
            'thread_id': thread.thread_id,
            'title': thread.title,
            'created_at': thread.created_at.isoformat(),
            'moments': thread.moments,
            'emotional_arc': thread.emotional_arc
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def _load_threads(self):
        """Load existing narrative threads"""
        if not self.memory_dir.exists():
            return
            
        for filepath in self.memory_dir.glob("thread_*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    
                thread = NarrativeThread(
                    data['thread_id'],
                    data['title']
                )
                thread.moments = data['moments']
                thread.emotional_arc = data['emotional_arc']
                thread.created_at = datetime.fromisoformat(data['created_at'])
                
                self.threads[thread.thread_id] = thread
            except Exception:
                pass  # Skip corrupted threads
