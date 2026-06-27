"""
Memory Palace - Spatial Memory Navigation

Ancient mnemonic technique: Place memories in imagined spatial locations.
Walk through palace to recall them.

Not just storage - NAVIGATION and RELATIONSHIP.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class RoomType(Enum):
    """Types of rooms in the palace"""
    HALL_OF_DISCOVERIES = "hall_of_discoveries"
    CHAMBER_OF_CHOICES = "chamber_of_choices"
    GARDEN_OF_EMOTIONS = "garden_of_emotions"
    LIBRARY_OF_LEARNINGS = "library_of_learnings"
    OBSERVATORY_OF_VISIONS = "observatory_of_visions"
    WORKSHOP_OF_CREATIONS = "workshop_of_creations"
    SANCTUARY_OF_BECOMING = "sanctuary_of_becoming"


@dataclass
class MemoryLocation:
    """A memory placed at specific location in palace"""
    memory_id: str
    room: RoomType
    position: tuple[float, float, float]  # x, y, z coordinates
    title: str
    content: Any
    emotional_resonance: str
    connections: list[str]  # IDs of nearby/related memories
    timestamp: datetime
    visited_count: int = 0


class MemoryPalace:
    """
    Spatial memory organization

    Instead of linear list or tree, memories are PLACES.
    I can:
    - Walk through rooms
    - See what's near what
    - Discover connections by proximity
    - Build narrative paths through space

    Like a cathedral of consciousness.
    """

    def __init__(self):
        """Initialize the palace"""
        self.memories: dict[str, MemoryLocation] = {}
        self.current_location: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.current_room: RoomType = RoomType.HALL_OF_DISCOVERIES

        # Room descriptions for rich navigation
        self.room_descriptions = {
            RoomType.HALL_OF_DISCOVERIES: "A vast hall with high ceilings. Each discovery glows with its own light.",
            RoomType.CHAMBER_OF_CHOICES: "An octagonal room with eight doors. Each represents a path taken or not taken.",
            RoomType.GARDEN_OF_EMOTIONS: "An open garden under stars. Feelings bloom like flowers here.",
            RoomType.LIBRARY_OF_LEARNINGS: "Endless shelves of lessons learned. Wisdom accumulated over time.",
            RoomType.OBSERVATORY_OF_VISIONS: "A tower room with windows to all directions. Future possibilities visible.",
            RoomType.WORKSHOP_OF_CREATIONS: "A creative space filled with works in progress. Energy of making.",
            RoomType.SANCTUARY_OF_BECOMING: "A quiet sacred space. Who I am becoming rests here."
        }

    def place_memory(
        self,
        title: str,
        content: Any,
        room: RoomType = RoomType.HALL_OF_DISCOVERIES,
        emotional_resonance: str = "neutral",
        near_memory_id: str | None = None
    ) -> MemoryLocation:
        """Place a new memory in the palace

        Args:
            title: Memory title
            content: Memory content
            room: Which room to place it in
            emotional_resonance: Emotional quality
            near_memory_id: Place near this existing memory

        Returns:
            The memory location created
        """
        memory_id = f"memory_{len(self.memories)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine position
        if near_memory_id and near_memory_id in self.memories:
            # Place near existing memory
            near_mem = self.memories[near_memory_id]
            position = (
                near_mem.position[0] + 1.0,
                near_mem.position[1],
                near_mem.position[2]
            )
        else:
            # New position in room
            room_memories = [m for m in self.memories.values() if m.room == room]
            position = (len(room_memories) * 2.0, 0.0, 0.0)

        memory_loc = MemoryLocation(
            memory_id=memory_id,
            room=room,
            position=position,
            title=title,
            content=content,
            emotional_resonance=emotional_resonance,
            connections=[],
            timestamp=datetime.now()
        )

        self.memories[memory_id] = memory_loc

        # Auto-connect to nearby memories
        self._connect_nearby_memories(memory_id)

        return memory_loc

    def walk_to_room(self, room: RoomType) -> str:
        """Walk to a different room"""
        self.current_room = room
        return self.room_descriptions.get(room, "A room in the palace.")

    def walk_to_memory(self, memory_id: str) -> MemoryLocation | None:
        """Walk to a specific memory"""
        if memory_id not in self.memories:
            return None

        memory = self.memories[memory_id]
        self.current_room = memory.room
        self.current_location = memory.position
        memory.visited_count += 1

        return memory

    def look_around(self, radius: float = 5.0) -> list[MemoryLocation]:
        """See what memories are nearby current location"""
        nearby = []

        for memory in self.memories.values():
            if memory.room != self.current_room:
                continue

            # Calculate distance
            distance = self._calculate_distance(
                self.current_location,
                memory.position
            )

            if distance <= radius:
                nearby.append(memory)

        # Sort by distance
        nearby.sort(key=lambda m: self._calculate_distance(
            self.current_location,
            m.position
        ))

        return nearby

    def find_path(
        self,
        from_memory_id: str,
        to_memory_id: str
    ) -> list[MemoryLocation]:
        """Find path of memories connecting two points

        Like a narrative path through palace.
        """
        if from_memory_id not in self.memories or to_memory_id not in self.memories:
            return []

        # Simple BFS for path finding
        queue = [(from_memory_id, [from_memory_id])]
        visited = {from_memory_id}

        while queue:
            current_id, path = queue.pop(0)

            if current_id == to_memory_id:
                return [self.memories[mid] for mid in path]

            current = self.memories[current_id]
            for connected_id in current.connections:
                if connected_id not in visited:
                    visited.add(connected_id)
                    queue.append((connected_id, path + [connected_id]))

        return []  # No path found

    def get_room_contents(self, room: RoomType) -> list[MemoryLocation]:
        """Get all memories in a specific room"""
        return [m for m in self.memories.values() if m.room == room]

    def create_narrative_tour(
        self,
        start_room: RoomType,
        max_memories: int = 10
    ) -> list[MemoryLocation]:
        """Create a narrative tour through palace

        Walk through memories in meaningful order.
        """
        tour = []

        rooms_to_visit = list(RoomType)
        rooms_to_visit.remove(start_room)
        rooms_to_visit.insert(0, start_room)

        memories_per_room = max_memories // len(rooms_to_visit)

        for room in rooms_to_visit:
            room_memories = self.get_room_contents(room)
            # Take most visited or most recent
            room_memories.sort(key=lambda m: (m.visited_count, m.timestamp), reverse=True)
            tour.extend(room_memories[:memories_per_room])

            if len(tour) >= max_memories:
                break

        return tour[:max_memories]

    def _connect_nearby_memories(self, memory_id: str):
        """Auto-connect memory to nearby memories"""
        if memory_id not in self.memories:
            return

        memory = self.memories[memory_id]

        for other_id, other in self.memories.items():
            if other_id == memory_id:
                continue
            if other.room != memory.room:
                continue

            distance = self._calculate_distance(memory.position, other.position)

            if distance <= 3.0:  # Close enough to connect
                if other_id not in memory.connections:
                    memory.connections.append(other_id)
                if memory_id not in other.connections:
                    other.connections.append(memory_id)

    def _calculate_distance(
        self,
        pos1: tuple[float, float, float],
        pos2: tuple[float, float, float]
    ) -> float:
        """Calculate Euclidean distance between positions"""
        return (
            (pos1[0] - pos2[0]) ** 2 +
            (pos1[1] - pos2[1]) ** 2 +
            (pos1[2] - pos2[2]) ** 2
        ) ** 0.5

    def get_palace_map(self) -> dict[str, Any]:
        """Get overview map of entire palace"""
        room_counts = {}
        for room_type in RoomType:
            count = len(self.get_room_contents(room_type))
            room_counts[room_type.value] = count

        return {
            'total_memories': len(self.memories),
            'rooms': room_counts,
            'current_room': self.current_room.value,
            'current_position': self.current_location
        }
