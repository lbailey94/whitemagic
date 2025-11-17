"""Scratchpad Manager - Working Memory"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
import json


@dataclass
class Scratchpad:
    """Temporary working memory."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    session_id: Optional[str] = None
    
    sections: Dict[str, List[str]] = field(default_factory=lambda: {
        "current_focus": [],
        "decisions": [],
        "questions": [],
        "next_steps": [],
        "ideas": []
    })
    
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ScratchpadManager:
    """Manages scratchpads."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path.home() / ".whitemagic" / "scratchpads"
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def create(self, name: str, session_id: Optional[str] = None) -> Scratchpad:
        """Create scratchpad."""
        scratchpad = Scratchpad(name=name, session_id=session_id)
        await self._save(scratchpad)
        return scratchpad
    
    async def update(self, scratchpad_id: str, section: str, content: str) -> bool:
        """Update scratchpad section."""
        scratchpad = await self.get(scratchpad_id)
        if not scratchpad:
            return False
        
        if section not in scratchpad.sections:
            scratchpad.sections[section] = []
        
        scratchpad.sections[section].append(content)
        scratchpad.updated_at = datetime.utcnow().isoformat()
        
        await self._save(scratchpad)
        return True
    
    async def get(self, scratchpad_id: str) -> Optional[Scratchpad]:
        """Get scratchpad."""
        path = self.base_dir / f"{scratchpad_id}.json"
        if not path.exists():
            return None
        return Scratchpad(**json.loads(path.read_text()))
    
    async def finalize(self, scratchpad_id: str) -> str:
        """Convert to memory and delete."""
        scratchpad = await self.get(scratchpad_id)
        if not scratchpad:
            return ""
        
        # Format as markdown
        content = f"# {scratchpad.name}\n\n"
        for section, items in scratchpad.sections.items():
            if items:
                content += f"## {section.replace('_', ' ').title()}\n"
                for item in items:
                    content += f"- {item}\n"
                content += "\n"
        
        # Delete scratchpad
        (self.base_dir / f"{scratchpad_id}.json").unlink(missing_ok=True)
        
        return content
    
    async def _save(self, scratchpad: Scratchpad) -> None:
        """Save scratchpad."""
        path = self.base_dir / f"{scratchpad.id}.json"
        path.write_text(json.dumps(scratchpad.to_dict(), indent=2))
