"""🧠 NeuralMemory - The Core Dataclass.

A memory unit with neural properties that strengthen and weaken
like biological neurons. Implements Hebbian learning principles.

Created: December 2, 2025 (Hanuman Tuesday)
"""

from whitemagic.core.memory.unified_types import (
    LinkType as LinkType,
)
from whitemagic.core.memory.unified_types import (
    Memory as Memory,
)
from whitemagic.core.memory.unified_types import (
    MemoryState as MemoryState,
)

# NeuralMemory is the canonical alias — Memory already has all neural fields
NeuralMemory = Memory
