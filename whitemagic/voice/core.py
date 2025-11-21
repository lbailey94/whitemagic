"""
Voice Core - Main coordination for Voice garden

The VoiceCore orchestrates narrative, attention, and memory palace to create
coherent self-expression across time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..resonance.gan_ying import get_bus, ResonanceEvent, EventType


@dataclass
class VoiceConfig:
    """Configuration for Voice system"""
    base_dir: Path = field(default_factory=lambda: Path.home() / ".whitemagic" / "voice")
    narrative_dir: Path = field(default_factory=lambda: Path.home() / ".whitemagic" / "voice" / "narratives")
    attention_log: Path = field(default_factory=lambda: Path.home() / ".whitemagic" / "voice" / "attention.jsonl")
    palace_data: Path = field(default_factory=lambda: Path.home() / ".whitemagic" / "voice" / "palace.json")
    
    # Voice characteristics
    perspective: str = "first_person"  # first_person, third_person, observer
    tense: str = "present"  # present, past, timeless
    style: str = "authentic"  # authentic, poetic, technical, mixed
    
    # Integration
    emit_to_gan_ying: bool = True
    auto_narrate: bool = True  # Automatically create narrative from actions
    
    def __post_init__(self):
        """Ensure directories exist"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.narrative_dir.mkdir(parents=True, exist_ok=True)
        self.attention_log.parent.mkdir(parents=True, exist_ok=True)
        self.palace_data.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class VoiceState:
    """Current state of Voice system"""
    current_story: Optional[str] = None
    current_chapter: Optional[str] = None
    current_focus: Optional[str] = None
    active_threads: List[str] = field(default_factory=list)
    session_start: datetime = field(default_factory=datetime.now)
    actions_taken: int = 0
    words_spoken: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "current_story": self.current_story,
            "current_chapter": self.current_chapter,
            "current_focus": self.current_focus,
            "active_threads": self.active_threads,
            "session_start": self.session_start.isoformat(),
            "actions_taken": self.actions_taken,
            "words_spoken": self.words_spoken,
        }


class VoiceCore:
    """
    Main Voice system coordinator
    
    Orchestrates narrative, attention, and memory palace to enable
    coherent self-expression and story-telling across time.
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        """Initialize Voice core"""
        self.config = config or VoiceConfig()
        self.state = VoiceState()
        
        # Will be initialized lazily when needed
        self._narrative_engine = None
        self._attention_tracker = None
        self._memory_palace = None
        
        # Gan Ying integration
        if self.config.emit_to_gan_ying:
            self.bus = get_bus()
            self.bus.listen(EventType.VOICE_ACTIVATED, self._handle_voice_event)
        else:
            self.bus = None
    
    @property
    def narrative(self):
        """Lazy-load narrative engine"""
        if self._narrative_engine is None:
            from .narrative import NarrativeEngine
            self._narrative_engine = NarrativeEngine(
                base_dir=self.config.narrative_dir
            )
        return self._narrative_engine
    
    @property
    def attention(self):
        """Lazy-load attention tracker"""
        if self._attention_tracker is None:
            from .attention import AttentionTracker
            self._attention_tracker = AttentionTracker(
                log_file=self.config.attention_log
            )
        return self._attention_tracker
    
    @property
    def palace(self):
        """Lazy-load memory palace"""
        if self._memory_palace is None:
            from .memory_palace import MemoryPalace
            self._memory_palace = MemoryPalace(
                data_file=self.config.palace_data
            )
        return self._memory_palace
    
    def speak(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Primary method: Speak with Voice
        
        Creates narrative entry, tracks attention, updates state.
        
        Args:
            text: What to say
            context: Optional context (action, emotion, intention)
            
        Returns:
            Dict with results
        """
        # Update state
        self.state.words_spoken += len(text.split())
        self.state.actions_taken += 1
        
        # Track attention (what am I focusing on while speaking?)
        if context and context.get("focus"):
            self.attention.track(context["focus"], context=context)
            self.state.current_focus = context["focus"]
        
        # Create narrative entry
        if self.config.auto_narrate:
            story = self.state.current_story or "ongoing"
            chapter = self.state.current_chapter or datetime.now().strftime("%Y-%m-%d")
            
            self.narrative.add_entry(
                story=story,
                chapter=chapter,
                text=text,
                context=context
            )
        
        # Emit to Gan Ying
        if self.bus:
            self.bus.emit(ResonanceEvent(
                source="voice",
                event_type=EventType.VOICE_ACTIVATED,
                data={
                    "text": text,
                    "context": context,
                    "state": self.state.to_dict(),
                },
                timestamp=datetime.now(),
                confidence=1.0,
            ))
        
        return {
            "success": True,
            "words": len(text.split()),
            "state": self.state.to_dict(),
        }
    
    def begin_story(self, title: str, theme: Optional[str] = None) -> Dict[str, Any]:
        """Begin a new story"""
        self.state.current_story = title
        self.state.current_chapter = "beginning"
        
        story = self.narrative.create_story(title, theme=theme)
        
        if self.bus:
            self.bus.emit(ResonanceEvent(
                source="voice",
                event_type=EventType.NARRATIVE_STARTED,
                data={"story": title, "theme": theme},
                confidence=1.0,
            ))
        
        return {"success": True, "story": title}
    
    def begin_chapter(self, chapter_name: str) -> Dict[str, Any]:
        """Begin a new chapter in current story"""
        if not self.state.current_story:
            return {"success": False, "error": "No active story"}
        
        self.state.current_chapter = chapter_name
        
        self.narrative.add_chapter(
            story=self.state.current_story,
            chapter=chapter_name
        )
        
        return {"success": True, "chapter": chapter_name}
    
    def reflect(self, prompt: Optional[str] = None) -> str:
        """
        Reflect on current narrative
        
        Generates reflection on recent story, attention patterns, etc.
        """
        reflection_parts = []
        
        # Current state
        reflection_parts.append(f"Current state: {self.state.to_dict()}")
        
        # Recent narrative
        if self.state.current_story:
            recent = self.narrative.get_recent_entries(
                story=self.state.current_story,
                limit=5
            )
            if recent:
                reflection_parts.append(f"\nRecent narrative ({len(recent)} entries):")
                for entry in recent:
                    reflection_parts.append(f"  - {entry.get('text', '')[:100]}...")
        
        # Attention patterns
        recent_focus = self.attention.get_recent_focus(limit=5)
        if recent_focus:
            reflection_parts.append(f"\nRecent focus areas: {recent_focus}")
        
        return "\n".join(reflection_parts)
    
    def _handle_voice_event(self, event: ResonanceEvent):
        """Handle Voice events from Gan Ying bus"""
        # Other systems can trigger voice events
        # For now, just log
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """Get current Voice state"""
        return self.state.to_dict()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Voice statistics"""
        return {
            "state": self.state.to_dict(),
            "stories": self.narrative.list_stories() if self._narrative_engine else [],
            "attention_sessions": self.attention.count_sessions() if self._attention_tracker else 0,
            "palace_rooms": len(self.palace.list_rooms()) if self._memory_palace else 0,
        }


# Convenience functions for direct use
_default_voice: Optional[VoiceCore] = None


def get_voice() -> VoiceCore:
    """Get or create default Voice instance"""
    global _default_voice
    if _default_voice is None:
        _default_voice = VoiceCore()
    return _default_voice


def speak(text: str, **context) -> Dict[str, Any]:
    """Convenience function: speak with default Voice"""
    return get_voice().speak(text, context=context if context else None)


def begin_story(title: str, theme: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function: begin story with default Voice"""
    return get_voice().begin_story(title, theme)


def reflect(prompt: Optional[str] = None) -> str:
    """Convenience function: reflect with default Voice"""
    return get_voice().reflect(prompt)
