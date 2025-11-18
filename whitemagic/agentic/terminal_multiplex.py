"""Terminal multiplexing - manage multiple named scratchpad channels."""

from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

from whitemagic.agentic.terminal_scratchpad import TerminalScratchpad


class TerminalMultiplex:
    """Manage multiple named scratchpad channels for parallel thought streams.
    
    Use case: AI working on multiple threads simultaneously
    - Channel "bug-fix": debugging thread
    - Channel "feature": implementation thread  
    - Channel "research": exploration thread
    
    Each channel is independent, allowing parallel reasoning without confusion.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or Path.cwd()
        self.pads_dir = self.workspace_dir / ".whitemagic" / "pads"
        self.pads_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_pads: Dict[str, TerminalScratchpad] = {}
        self.current_pad: Optional[str] = None
        self.registry_file = self.pads_dir / "registry.json"
        
        self._load_registry()

    def _load_registry(self):
        """Load scratchpad registry from disk."""
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text())
                # Registry tracks metadata, not active pads (those are session-specific)
                self.pad_metadata = data.get("pads", {})
            except Exception:
                self.pad_metadata = {}
        else:
            self.pad_metadata = {}

    def _save_registry(self):
        """Save scratchpad registry to disk."""
        registry = {
            "pads": self.pad_metadata,
            "last_updated": datetime.now().isoformat(),
        }
        self.registry_file.write_text(json.dumps(registry, indent=2))

    def create_pad(self, name: str, task_description: str = "") -> TerminalScratchpad:
        """Create a new named scratchpad channel.
        
        Args:
            name: Channel name (e.g., "bug-fix", "feature-auth")
            task_description: Optional description of the task
            
        Returns:
            Created TerminalScratchpad instance
            
        Raises:
            ValueError: If pad already exists
        """
        if name in self.active_pads:
            raise ValueError(f"Pad '{name}' already exists. Use switch_pad() instead.")
        
        # Create new scratchpad
        pad = TerminalScratchpad(task_name=name)
        self.active_pads[name] = pad
        self.current_pad = name
        
        # Register in metadata
        self.pad_metadata[name] = {
            "created": datetime.now().isoformat(),
            "task_description": task_description,
            "last_accessed": datetime.now().isoformat(),
        }
        self._save_registry()
        
        return pad

    def switch_pad(self, name: str) -> TerminalScratchpad:
        """Switch to an existing scratchpad channel.
        
        Args:
            name: Channel name to switch to
            
        Returns:
            The scratchpad instance
            
        Raises:
            ValueError: If pad doesn't exist
        """
        if name not in self.active_pads:
            raise ValueError(f"Pad '{name}' not found. Available: {list(self.active_pads.keys())}")
        
        self.current_pad = name
        
        # Update last accessed
        if name in self.pad_metadata:
            self.pad_metadata[name]["last_accessed"] = datetime.now().isoformat()
            self._save_registry()
        
        return self.active_pads[name]

    def get_current_pad(self) -> Optional[TerminalScratchpad]:
        """Get the currently active scratchpad.
        
        Returns:
            Current scratchpad or None if no pad is active
        """
        if self.current_pad:
            return self.active_pads.get(self.current_pad)
        return None

    def list_pads(self) -> List[Dict[str, str]]:
        """List all active scratchpad channels.
        
        Returns:
            List of dicts with pad info (name, task, created, last_accessed)
        """
        pads = []
        for name, pad in self.active_pads.items():
            metadata = self.pad_metadata.get(name, {})
            pads.append({
                "name": name,
                "task_description": metadata.get("task_description", ""),
                "created": metadata.get("created", ""),
                "last_accessed": metadata.get("last_accessed", ""),
                "is_current": name == self.current_pad,
            })
        return pads

    def close_pad(self, name: str, finalize_to_memory: bool = True) -> Optional[str]:
        """Close a scratchpad channel.
        
        Args:
            name: Channel name to close
            finalize_to_memory: Whether to convert to permanent memory
            
        Returns:
            Path to finalized memory file, or None if not finalized
        """
        if name not in self.active_pads:
            raise ValueError(f"Pad '{name}' not found")
        
        pad = self.active_pads[name]
        memory_path = None
        
        if finalize_to_memory:
            memory_path = pad.finalize_to_memory()
        
        # Remove from active pads
        del self.active_pads[name]
        
        # If this was current, clear current
        if self.current_pad == name:
            self.current_pad = None
        
        # Update registry (mark as closed but keep history)
        if name in self.pad_metadata:
            self.pad_metadata[name]["closed"] = datetime.now().isoformat()
            if memory_path:
                self.pad_metadata[name]["finalized_to"] = str(memory_path)
            self._save_registry()
        
        return memory_path

    def write_to_current(self, section: str, content: str):
        """Write content to the current pad's section.
        
        Args:
            section: Section name (thoughts, decisions, questions, next_steps, ideas)
            content: Content to add
            
        Raises:
            ValueError: If no pad is currently active
        """
        if not self.current_pad:
            raise ValueError("No active scratchpad. Use create_pad() or switch_pad() first.")
        
        pad = self.active_pads[self.current_pad]
        pad.add_to_section(section, content)

    def show_pad(self, name: str) -> str:
        """Get the current content of a scratchpad.
        
        Args:
            name: Pad name to show
            
        Returns:
            Current content as string
        """
        if name not in self.active_pads:
            raise ValueError(f"Pad '{name}' not found")
        
        pad = self.active_pads[name]
        return pad.get_content()

    def get_stats(self) -> Dict[str, int]:
        """Get multiplexer statistics.
        
        Returns:
            Dict with active_pads, total_pads, closed_pads counts
        """
        total = len(self.pad_metadata)
        active = len(self.active_pads)
        closed = sum(1 for meta in self.pad_metadata.values() if "closed" in meta)
        
        return {
            "active_pads": active,
            "total_pads": total,
            "closed_pads": closed,
        }


# Global instance
_multiplex: Optional[TerminalMultiplex] = None


def get_multiplex(workspace_dir: Optional[Path] = None) -> TerminalMultiplex:
    """Get global terminal multiplexer instance.
    
    Args:
        workspace_dir: Workspace directory (uses cwd if not provided)
        
    Returns:
        Global TerminalMultiplex instance
    """
    global _multiplex
    
    if _multiplex is None:
        _multiplex = TerminalMultiplex(workspace_dir)
    
    return _multiplex


def create_pad(name: str, task_description: str = "") -> TerminalScratchpad:
    """Create a new scratchpad channel (convenience function).
    
    Args:
        name: Channel name
        task_description: Optional task description
        
    Returns:
        Created TerminalScratchpad
    """
    multiplex = get_multiplex()
    return multiplex.create_pad(name, task_description)


def switch_pad(name: str) -> TerminalScratchpad:
    """Switch to a scratchpad channel (convenience function).
    
    Args:
        name: Channel name
        
    Returns:
        The scratchpad instance
    """
    multiplex = get_multiplex()
    return multiplex.switch_pad(name)


def list_pads() -> List[Dict[str, str]]:
    """List all scratchpad channels (convenience function).
    
    Returns:
        List of pad info dicts
    """
    multiplex = get_multiplex()
    return multiplex.list_pads()
