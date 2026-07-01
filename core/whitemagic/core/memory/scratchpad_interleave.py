"""Scratchpad Interleaving - Controlled Cross-Pollination of Ideas.

Manages multiple parallel scratchpads with intelligent interleaving
at phase boundaries for creative synthesis.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads
from whitemagic.utils.fileio import atomic_write, file_lock


class Scratchpad:
    """A single working memory scratchpad with chain-of-thought state tracking.

    Supports sequential-thinking-style chain state (thought_number, total_thoughts),
    branching (branch_id, branch_from), and revision (is_revision, revises_entry).
    """

    def __init__(self, name: str, focus: str | None = None):
        self.name = name
        self.focus = focus
        self.entries: list[dict[str, Any]] = []
        self.created = datetime.now()
        self.last_active = datetime.now()
        self._main_chain_length = 0
        self._branch_counter = 0

    def write(
        self,
        content: str,
        tag: str | None = None,
        thought_number: int | None = None,
        total_thoughts: int | None = None,
        branch_id: str | None = None,
        branch_from: int | None = None,
        is_revision: bool = False,
        revises_entry: int | None = None,
    ) -> dict[str, Any]:
        """Write to scratchpad with optional chain state metadata.

        Args:
            content: The thought content.
            tag: Section tag (current_focus, decisions, questions, next_steps, ideas).
            thought_number: Position in the chain (auto-incremented if None).
            total_thoughts: Estimated total thoughts in this chain.
            branch_id: Branch identifier for forked chains.
            branch_from: Thought number to branch from.
            is_revision: Whether this entry revises an earlier one.
            revises_entry: Entry index being revised.

        Returns:
            The entry dict that was appended.
        """
        if thought_number is None:
            if branch_id:
                branch_entries = [e for e in self.entries if e.get("branch_id") == branch_id]
                thought_number = len(branch_entries) + 1
            else:
                self._main_chain_length += 1
                thought_number = self._main_chain_length

        if total_thoughts is None:
            total_thoughts = thought_number

        if branch_id and branch_id not in {e.get("branch_id") for e in self.entries if e.get("branch_id")}:
            self._branch_counter += 1

        entry = {
            "content": content,
            "tag": tag,
            "timestamp": datetime.now().isoformat(),
            "thought_number": thought_number,
            "total_thoughts": total_thoughts,
            "branch_id": branch_id,
            "branch_from": branch_from,
            "is_revision": is_revision,
            "revises_entry": revises_entry,
            "entry_index": len(self.entries),
        }
        self.entries.append(entry)
        self.last_active = datetime.now()
        return entry

    def read_recent(self, count: int = 5) -> list[str]:
        """Read recent entries."""
        return [e["content"] for e in self.entries[-count:]]

    def clear(self) -> None:
        """Clear scratchpad."""
        self.entries = []

    def get_chain_status(self) -> dict[str, Any]:
        """Return chain-of-thought state for sequential-thinking compatibility."""
        main_entries = [e for e in self.entries if not e.get("branch_id")]
        branches: dict[str, list[dict[str, Any]]] = {}
        for e in self.entries:
            bid = e.get("branch_id")
            if bid:
                branches.setdefault(bid, []).append(e)
        last_entry = self.entries[-1] if self.entries else None
        return {
            "thought_number": last_entry.get("thought_number", 0) if last_entry else 0,
            "total_thoughts": last_entry.get("total_thoughts", 0) if last_entry else 0,
            "thought_history_length": len(self.entries),
            "branches": list(branches.keys()),
            "branch_count": len(branches),
            "main_chain_length": len(main_entries),
            "is_revision": last_entry.get("is_revision", False) if last_entry else False,
        }

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "name": self.name,
            "focus": self.focus,
            "entries": self.entries,
            "created": self.created.isoformat(),
            "last_active": self.last_active.isoformat(),
            "main_chain_length": self._main_chain_length,
            "branch_count": self._branch_counter,
        }


class ScratchpadManager:
    """Manages multiple scratchpads with interleaving."""

    MAX_SCRATCHPADS = 7  # Working memory limit (Miller's Law)

    def __init__(self, scratch_dir: Path | None = None):
        self.scratch_dir = scratch_dir or (WM_ROOT / "scratchpads")
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        self.scratchpads: dict[str, Scratchpad] = {}
        self.interleave_history: list[dict[str, Any]] = []
        self._load_scratchpads()

    def _load_scratchpads(self) -> None:
        """Load existing scratchpads."""
        for pad_file in self.scratch_dir.glob("*.json"):
            try:
                with file_lock(pad_file):
                    data: dict[str, Any] = _json_loads(pad_file.read_text())
                pad = Scratchpad(data["name"], data.get("focus"))
                pad.entries = data.get("entries", [])
                pad._main_chain_length = data.get("main_chain_length", len([
                    e for e in pad.entries if not e.get("branch_id")
                ]))
                pad._branch_counter = data.get("branch_count", len({
                    e.get("branch_id") for e in pad.entries if e.get("branch_id")
                }))
                self.scratchpads[data["name"]] = pad
            except (ValueError, OSError):
                pass

    def _save_scratchpad(self, name: str) -> None:
        """Save a scratchpad."""
        if name in self.scratchpads:
            pad_file = self.scratch_dir / f"{name}.json"
            with file_lock(pad_file):
                atomic_write(pad_file, _json_dumps(self.scratchpads[name].to_dict(), indent=2))

    def create(self, name: str, focus: str | None = None) -> Scratchpad:
        """Create a new scratchpad."""
        if len(self.scratchpads) >= self.MAX_SCRATCHPADS:
            oldest = min(self.scratchpads.values(), key=lambda p: p.last_active)
            del self.scratchpads[oldest.name]

        pad = Scratchpad(name, focus)
        self.scratchpads[name] = pad
        self._save_scratchpad(name)
        return pad

    def write_to(
        self,
        name: str,
        content: str,
        tag: str | None = None,
        thought_number: int | None = None,
        total_thoughts: int | None = None,
        branch_id: str | None = None,
        branch_from: int | None = None,
        is_revision: bool = False,
        revises_entry: int | None = None,
    ) -> dict[str, Any]:
        """Write to a specific scratchpad with chain state support.

        Returns the entry dict with chain state metadata.
        """
        if name not in self.scratchpads:
            self.create(name)
        entry = self.scratchpads[name].write(
            content, tag,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            branch_id=branch_id,
            branch_from=branch_from,
            is_revision=is_revision,
            revises_entry=revises_entry,
        )
        self._save_scratchpad(name)
        return entry

    def interleave(self, pad_names: list[str] | None = None) -> dict[str, Any]:
        """Interleave scratchpads - merge insights at phase boundary.

        This is the "dream synthesis" moment where separate
        working memories cross-pollinate.
        """
        pads = pad_names or list(self.scratchpads.keys())

        # Gather all recent entries
        all_entries = []
        for name in pads:
            if name in self.scratchpads:
                for entry in self.scratchpads[name].entries[-3:
                    ]:
                    all_entries.append({
                        "source": name,
                        "content": entry["content"],
                        "tag": entry.get("tag"),
                    })

        # Create synthesis
        synthesis = {
            "timestamp": datetime.now().isoformat(),
            "sources": pads,
            "entries_merged": len(all_entries),
            "entries": all_entries,
        }

        self.interleave_history.append(synthesis)
        return synthesis

    def get_chain_status(self, name: str) -> dict[str, Any]:
        """Get chain-of-thought status for a scratchpad.

        Returns thought_number, total_thoughts, thought_history_length,
        branches, and revision state — compatible with sequential-thinking.
        """
        if name not in self.scratchpads:
            return {"error": f"Scratchpad not found: {name}"}
        return self.scratchpads[name].get_chain_status()

    def get_active_pads(self) -> list[str]:
        """Get names of active scratchpads."""
        return list(self.scratchpads.keys())

    def summarize_all(self) -> dict[str, list[str]]:
        """Get summary of all scratchpads."""
        return {
            name: pad.read_recent(3)
            for name, pad in self.scratchpads.items()
        }


# Singleton
_manager: ScratchpadManager | None = None

def get_scratchpad_manager() -> ScratchpadManager:
    """
    Get the scratchpad manager.

    Returns:
        ScratchpadManager
    """
    global _manager
    if _manager is None:
        _manager = ScratchpadManager()
    return _manager
