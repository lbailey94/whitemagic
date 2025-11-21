"""
Memory Palace - Spatial metaphors for memory organization

Uses spatial/architectural metaphors to organize memories,
making them easier to navigate and recall.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class Space:
    """A space within a room"""
    name: str
    description: str
    memories: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "memories": self.memories,
        }


@dataclass
class Room:
    """A room in the memory palace"""
    name: str
    theme: str
    description: str
    spaces: Dict[str, Space] = field(default_factory=dict)
    created: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "theme": self.theme,
            "description": self.description,
            "spaces": {k: v.to_dict() for k, v in self.spaces.items()},
            "created": self.created.isoformat(),
        }


@dataclass
class Path:
    """A path connecting rooms"""
    from_room: str
    to_room: str
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_room": self.from_room,
            "to_room": self.to_room,
            "description": self.description,
        }


class MemoryPalace:
    """
    Memory Palace - Spatial memory organization
    
    Uses architectural metaphors (rooms, spaces, paths) to organize
    and navigate memories spatially.
    """
    
    def __init__(self, data_file: Path):
        """Initialize memory palace"""
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.rooms: Dict[str, Room] = {}
        self.paths: List[Path] = []
        
        self._load()
    
    def _load(self):
        """Load palace from disk"""
        if self.data_file.exists():
            with open(self.data_file) as f:
                data = json.load(f)
                
                # Load rooms
                for name, room_data in data.get("rooms", {}).items():
                    room = Room(
                        name=room_data["name"],
                        theme=room_data["theme"],
                        description=room_data["description"],
                        created=datetime.fromisoformat(room_data["created"]),
                    )
                    # Load spaces
                    for space_name, space_data in room_data.get("spaces", {}).items():
                        room.spaces[space_name] = Space(**space_data)
                    self.rooms[name] = room
                
                # Load paths
                self.paths = [Path(**p) for p in data.get("paths", [])]
    
    def _save(self):
        """Save palace to disk"""
        data = {
            "rooms": {name: room.to_dict() for name, room in self.rooms.items()},
            "paths": [p.to_dict() for p in self.paths],
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_room(self, name: str, theme: str, description: str) -> Room:
        """Create a new room"""
        room = Room(
            name=name,
            theme=theme,
            description=description,
        )
        self.rooms[name] = room
        self._save()
        return room
    
    def add_space(self, room_name: str, space_name: str, description: str) -> Space:
        """Add a space to a room"""
        if room_name not in self.rooms:
            raise ValueError(f"Room '{room_name}' not found")
        
        space = Space(name=space_name, description=description)
        self.rooms[room_name].spaces[space_name] = space
        self._save()
        return space
    
    def connect_rooms(self, from_room: str, to_room: str, description: str):
        """Create a path between rooms"""
        if from_room not in self.rooms or to_room not in self.rooms:
            raise ValueError("Both rooms must exist")
        
        path = Path(from_room=from_room, to_room=to_room, description=description)
        self.paths.append(path)
        self._save()
    
    def place_memory(self, room_name: str, space_name: str, memory_id: str):
        """Place a memory in a space"""
        if room_name not in self.rooms:
            raise ValueError(f"Room '{room_name}' not found")
        if space_name not in self.rooms[room_name].spaces:
            raise ValueError(f"Space '{space_name}' not found in room '{room_name}'")
        
        self.rooms[room_name].spaces[space_name].memories.append(memory_id)
        self._save()
    
    def list_rooms(self) -> List[str]:
        """List all room names"""
        return list(self.rooms.keys())
    
    def get_room(self, name: str) -> Optional[Room]:
        """Get a room by name"""
        return self.rooms.get(name)
    
    def find_memory(self, memory_id: str) -> Optional[tuple]:
        """Find which room/space contains a memory"""
        for room_name, room in self.rooms.items():
            for space_name, space in room.spaces.items():
                if memory_id in space.memories:
                    return (room_name, space_name)
        return None
