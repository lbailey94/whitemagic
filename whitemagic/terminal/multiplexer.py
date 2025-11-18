"""
Terminal Multiplexer - Multiple Named Scratchpads

Inspired by tmux/screen but for thought streams:
- Multiple parallel scratchpads
- Switch between different problem contexts
- Isolation prevents cognitive clutter
- Aligns with parallel reasoning philosophy
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TerminalSession:
    """A multiplexed terminal session with multiple pads."""
    
    id: str
    name: str
    active_pad: Optional[str] = None
    pads: Dict[str, str] = field(default_factory=dict)  # pad_name -> pad_id
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)


class TerminalMultiplexer:
    """
    Manages multiple parallel thought streams.
    
    Like tmux for your thinking:
    - Create multiple named pads
    - Switch between them instantly
    - Each pad isolated from others
    - Perfect for parallel problem-solving
    """
    
    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path.home() / ".whitemagic" / "terminal_sessions"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[TerminalSession] = None
    
    def create_session(self, name: str) -> TerminalSession:
        """Create a new multiplexed session."""
        session_id = f"tmux_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        session = TerminalSession(
            id=session_id,
            name=name
        )
        
        self._save_session(session)
        self.current_session = session
        
        return session
    
    def add_pad(self, pad_name: str, pad_id: str) -> bool:
        """Add a pad to current session."""
        if not self.current_session:
            return False
        
        self.current_session.pads[pad_name] = pad_id
        self.current_session.last_accessed = datetime.utcnow().isoformat()
        
        # Set as active if it's the first pad
        if len(self.current_session.pads) == 1:
            self.current_session.active_pad = pad_name
        
        self._save_session(self.current_session)
        return True
    
    def switch_pad(self, pad_name: str) -> Optional[str]:
        """Switch to a different pad in current session."""
        if not self.current_session:
            return None
        
        if pad_name not in self.current_session.pads:
            return None
        
        self.current_session.active_pad = pad_name
        self.current_session.last_accessed = datetime.utcnow().isoformat()
        
        self._save_session(self.current_session)
        
        return self.current_session.pads[pad_name]
    
    def list_pads(self) -> List[Dict]:
        """List all pads in current session."""
        if not self.current_session:
            return []
        
        return [
            {
                "name": name,
                "pad_id": pad_id,
                "active": name == self.current_session.active_pad
            }
            for name, pad_id in self.current_session.pads.items()
        ]
    
    def get_active_pad(self) -> Optional[tuple[str, str]]:
        """Get current active pad (name, id)."""
        if not self.current_session or not self.current_session.active_pad:
            return None
        
        pad_name = self.current_session.active_pad
        pad_id = self.current_session.pads.get(pad_name)
        
        return (pad_name, pad_id) if pad_id else None
    
    def close_session(self) -> bool:
        """Close current session and archive."""
        if not self.current_session:
            return False
        
        # Move to archive
        archive_path = self.storage_dir / "archive" / f"{self.current_session.id}.json"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        archive_path.write_text(json.dumps(asdict(self.current_session), indent=2))
        
        # Remove from active
        active_path = self.storage_dir / f"{self.current_session.id}.json"
        active_path.unlink(missing_ok=True)
        
        self.current_session = None
        return True
    
    def load_session(self, session_id: str) -> Optional[TerminalSession]:
        """Load an existing session."""
        session_path = self.storage_dir / f"{session_id}.json"
        
        if not session_path.exists():
            return None
        
        data = json.loads(session_path.read_text())
        session = TerminalSession(**data)
        
        self.current_session = session
        return session
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions."""
        sessions = []
        
        for session_file in self.storage_dir.glob("tmux_*.json"):
            try:
                data = json.loads(session_file.read_text())
                sessions.append({
                    "id": data["id"],
                    "name": data["name"],
                    "pads": len(data["pads"]),
                    "created": data["created"],
                    "last_accessed": data["last_accessed"]
                })
            except Exception:
                continue
        
        return sorted(sessions, key=lambda x: x["last_accessed"], reverse=True)
    
    def _save_session(self, session: TerminalSession):
        """Save session to disk."""
        session_path = self.storage_dir / f"{session.id}.json"
        session_path.write_text(json.dumps(asdict(session), indent=2))
    
    def get_session_layout(self) -> Dict:
        """Get visual layout of current session."""
        if not self.current_session:
            return {"error": "No active session"}
        
        layout = {
            "session": self.current_session.name,
            "pads": len(self.current_session.pads),
            "active": self.current_session.active_pad,
            "layout": []
        }
        
        for pad_name, pad_id in self.current_session.pads.items():
            layout["layout"].append({
                "name": pad_name,
                "id": pad_id,
                "active": pad_name == self.current_session.active_pad,
                "symbol": "▶" if pad_name == self.current_session.active_pad else "▷"
            })
        
        return layout
