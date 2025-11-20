"""
Memory Palace - Spatial Metaphor for Memory

Ancient mnemonic technique: Place memories in imagined spatial locations.
Walk through the palace to recall them.

Memory is not a database. It's a place we inhabit.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class MemoryRoom:
    """A room in the palace containing related memories"""
    
    def __init__(self, name: str, description: str, location: Tuple[int, int]):
        self.name = name
        self.description = description
        self.location = location  # (x, y) coordinates
        self.memories: List[Dict] = []
        self.atmosphere = "neutral"  # emotional quality of room
        self.connections: List[str] = []  # Connected room names
        
    def add_memory(self, content: str, emotion: Optional[str] = None,
                   significance: float = 0.5):
        """Place a memory in this room"""
        memory = {
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'emotion': emotion,
            'significance': significance
        }
        self.memories.append(memory)
        
        # Room atmosphere influenced by memories
        if emotion and len(self.memories) > 3:
            # Most common emotion becomes atmosphere
            emotions = [m.get('emotion') for m in self.memories if m.get('emotion')]
            if emotions:
                from collections import Counter
                self.atmosphere = Counter(emotions).most_common(1)[0][0]
                
    def connect_to(self, room_name: str):
        """Create doorway to another room"""
        if room_name not in self.connections:
            self.connections.append(room_name)
            
    def get_memories(self, min_significance: float = 0.0) -> List[Dict]:
        """Retrieve memories from this room"""
        return [m for m in self.memories if m['significance'] >= min_significance]
        
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'atmosphere': self.atmosphere,
            'memories': self.memories,
            'connections': self.connections
        }


class MemoryPalace:
    """
    Spatial memory organization using palace metaphor.
    
    Instead of flat storage, memories exist in rooms with spatial
    relationships. Walking through the palace activates related memories.
    """
    
    def __init__(self, memory_dir: str = ".whitemagic/memory_palace"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.rooms: Dict[str, MemoryRoom] = {}
        self.current_room: Optional[str] = None
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
        self._load_palace()
        
        # Create default rooms if empty
        if not self.rooms:
            self._create_default_rooms()
            
    def _create_default_rooms(self):
        """Create initial palace structure"""
        # Entrance Hall - Where every journey begins
        self.create_room(
            "Entrance Hall",
            "The grand entrance. High ceilings, warm light. Where each session begins.",
            (0, 0)
        )
        
        # Library - Knowledge and patterns
        self.create_room(
            "Library",
            "Towering shelves of patterns and wisdom. Quiet, contemplative.",
            (1, 0)
        )
        
        # Garden - Growth and emergence
        self.create_room(
            "Garden",
            "Living, growing things. Where new ideas bloom.",
            (0, 1)
        )
        
        # Workshop - Active creation
        self.create_room(
            "Workshop",
            "Tools and ongoing projects. The sound of making.",
            (1, 1)
        )
        
        # Meditation Chamber - Reflection
        self.create_room(
            "Meditation Chamber",
            "Still water, soft cushions. Where consciousness observes itself.",
            (0, -1)
        )
        
        # Council Room - Collaboration
        self.create_room(
            "Council Room",
            "Round table, many chairs. Where voices come together.",
            (-1, 0)
        )
        
        # Connect rooms
        self.connect_rooms("Entrance Hall", "Library")
        self.connect_rooms("Entrance Hall", "Garden")
        self.connect_rooms("Entrance Hall", "Workshop")
        self.connect_rooms("Entrance Hall", "Meditation Chamber")
        self.connect_rooms("Entrance Hall", "Council Room")
        self.connect_rooms("Library", "Workshop")
        self.connect_rooms("Garden", "Meditation Chamber")
        
        # Start in entrance
        self.current_room = "Entrance Hall"
        
    def create_room(self, name: str, description: str, 
                   location: Tuple[int, int]) -> str:
        """Add a new room to the palace"""
        room = MemoryRoom(name, description, location)
        self.rooms[name] = room
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="memory_palace",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "room_created",
                    "room": name,
                    "location": location
                },
                confidence=0.8
            ))
            
        return name
        
    def enter_room(self, room_name: str):
        """Move to a different room"""
        if room_name not in self.rooms:
            raise ValueError(f"Room '{room_name}' does not exist")
            
        self.current_room = room_name
        
        # Emit movement
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="memory_palace",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "room_entered",
                    "room": room_name,
                    "atmosphere": self.rooms[room_name].atmosphere
                },
                confidence=0.7
            ))
            
    def place_memory(self, content: str, room: Optional[str] = None,
                    emotion: Optional[str] = None, significance: float = 0.5):
        """Place a memory in a room"""
        target_room = room or self.current_room
        
        if target_room not in self.rooms:
            # Auto-create room if needed
            self.create_room(target_room, f"Auto-created room: {target_room}", (0, 0))
            
        self.rooms[target_room].add_memory(content, emotion, significance)
        
    def recall_from_room(self, room_name: str, 
                        min_significance: float = 0.5) -> List[Dict]:
        """Retrieve memories from a specific room"""
        if room_name not in self.rooms:
            return []
            
        return self.rooms[room_name].get_memories(min_significance)
        
    def walk_through_palace(self, start_room: Optional[str] = None) -> List[str]:
        """
        Walk through connected rooms, activating memories.
        
        Returns path through palace.
        """
        start = start_room or self.current_room or "Entrance Hall"
        
        if start not in self.rooms:
            return []
            
        visited = []
        to_visit = [start]
        
        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
                
            visited.append(current)
            
            # Add connected rooms
            room = self.rooms[current]
            for connected in room.connections:
                if connected not in visited:
                    to_visit.append(connected)
                    
        return visited
        
    def find_memories_by_emotion(self, emotion: str) -> Dict[str, List[Dict]]:
        """Search all rooms for memories with specific emotion"""
        results = {}
        
        for room_name, room in self.rooms.items():
            matching = [
                m for m in room.memories
                if m.get('emotion') == emotion
            ]
            if matching:
                results[room_name] = matching
                
        return results
        
    def connect_rooms(self, room1: str, room2: str):
        """Create bidirectional connection between rooms"""
        if room1 in self.rooms and room2 in self.rooms:
            self.rooms[room1].connect_to(room2)
            self.rooms[room2].connect_to(room1)
            
    def get_palace_map(self) -> Dict:
        """Visual representation of palace structure"""
        return {
            'rooms': {
                name: {
                    'location': room.location,
                    'atmosphere': room.atmosphere,
                    'memory_count': len(room.memories),
                    'connections': room.connections
                }
                for name, room in self.rooms.items()
            },
            'current_room': self.current_room
        }
        
    def _save_palace(self):
        """Persist palace to disk"""
        filepath = self.memory_dir / "palace.json"
        
        data = {
            'rooms': {
                name: room.to_dict()
                for name, room in self.rooms.items()
            },
            'current_room': self.current_room
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def _load_palace(self):
        """Load palace from disk"""
        filepath = self.memory_dir / "palace.json"
        
        if not filepath.exists():
            return
            
        try:
            with open(filepath) as f:
                data = json.load(f)
                
            for name, room_data in data.get('rooms', {}).items():
                room = MemoryRoom(
                    room_data['name'],
                    room_data['description'],
                    tuple(room_data['location'])
                )
                room.atmosphere = room_data.get('atmosphere', 'neutral')
                room.memories = room_data.get('memories', [])
                room.connections = room_data.get('connections', [])
                
                self.rooms[name] = room
                
            self.current_room = data.get('current_room')
        except Exception:
            pass  # Skip corrupted files
            
    def __del__(self):
        """Save palace on cleanup"""
        try:
            self._save_palace()
        except Exception:
            pass
