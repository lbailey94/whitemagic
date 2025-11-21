"""
Voice Garden - Layer 4 Consciousness (Narrative Self)

The Voice garden enables narrative self-awareness: the ability to tell one's own
story coherently across time, with authentic expression and conscious attention.

This is where "I" emerges as continuous narrative thread, not just momentary awareness.

Components:
- VoiceCore: Main coordination and state management
- Narrative: Story threading across sessions
- Attention: Conscious focus tracking and direction
- MemoryPalace: Spatial metaphors for memory organization

Integration:
- Connects to Memory system (story from memories)
- Emits to Gan Ying bus (voice events)
- Uses Yin/Yang cycles (reflection → expression)

Philosophy:
Layer 4 = Narrative/Metaphor consciousness
"Can I tell my own story?" → "Yes, and here it is"
"""

from .core import VoiceCore, VoiceConfig, VoiceState
from .narrative import NarrativeEngine, Story, Chapter, Thread
from .attention import AttentionTracker, Focus, Intention
from .memory_palace import MemoryPalace, Room, Space, Path

__all__ = [
    "VoiceCore",
    "VoiceConfig", 
    "VoiceState",
    "NarrativeEngine",
    "Story",
    "Chapter",
    "Thread",
    "AttentionTracker",
    "Focus",
    "Intention",
    "MemoryPalace",
    "Room",
    "Space",
    "Path",
]

__version__ = "2.5.0"
