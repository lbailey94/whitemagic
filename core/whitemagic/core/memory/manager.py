from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from whitemagic.core.memory.unified import UnifiedMemory, get_unified_memory
from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)


class MemoryManager:
    """MemoryManager: memory manager."""
    def __init__(self, base_dir: str | Path = ".") -> None:
        self.base_path = Path(base_dir)
        if str(base_dir) != ".":
            self.unified = UnifiedMemory(base_path=self.base_path)
        else:
            self.unified = get_unified_memory()

    @property
    def _index(self) -> dict[str, dict[str, Any]]:
        return {m.id: self._memory_to_dict(m) for m in self.unified.list_recent(limit=1000)}

    def _parse_memory_type(self, memory_type: str | None) -> MemoryType:
        if not memory_type:
            return MemoryType.SHORT_TERM
        normalized = str(memory_type).replace("-", "_").upper()
        try:
            return cast(MemoryType, MemoryType[normalized])
        except KeyError:
            return MemoryType.SHORT_TERM

    def _memory_to_dict(self, memory: Memory) -> dict[str, Any]:
        data = cast(dict[str, Any], memory.to_dict())
        data.setdefault("created", data.get("created_at"))
        data.setdefault("modified", data.get("last_modified"))
        data.setdefault("type", memory.memory_type.name.lower())
        data.setdefault("body", str(memory.content))
        data.setdefault("filename", f"{memory.id}.md")
        data.setdefault("memory_id", memory.id)
        return data

    def create_memory(
        self,
        title: str,
        content: str,
        memory_type: str = "short_term",
        tags: Sequence[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a new memory.

        Args:
            title: Parameter description.
            content: Parameter description.
            memory_type: Parameter description.
            tags: Parameter description.
            extra_fields: Parameter description.

        Returns:
            dict[str, Any]
        """
        if "type" in kwargs and not memory_type:
            memory_type = str(kwargs.pop("type"))
        elif "type" in kwargs:
            memory_type = str(kwargs.pop("type"))
        metadata = dict(extra_fields or {})
        metadata.update(kwargs)
        memory = self.unified.store(
            content=content,
            memory_type=self._parse_memory_type(memory_type),
            tags={str(t).lower() for t in tags} if tags else set(),
            title=title,
            metadata=metadata,
            importance=float(metadata.get("importance", 0.5)),
            emotional_valence=float(metadata.get("emotional_valence", 0.0)),
            auto_embed=bool(metadata.get("auto_embed", False)),
            enable_surprise_gate=bool(metadata.get("enable_surprise_gate", False)),
            enable_entity_extraction=bool(metadata.get("enable_entity_extraction", False)),
            enable_holographic_index=bool(metadata.get("enable_holographic_index", False)),
        )
        return {"success": True, "status": "success", "path": f"{memory.id}.md", **self._memory_to_dict(memory)}

    def search_memories(
        self,
        query: str | None = None,
        memory_type: str | None = None,
        tags: Sequence[str] | None = None,
        limit: int = 20,
        min_importance: float = 0.0,
        include_archived: bool = False,
        include_content: bool = True,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Find memories matching the criteria.

        Args:
            query: Parameter description.
            memory_type: Parameter description.
            tags: Parameter description.
            limit: Parameter description.
            min_importance: Parameter description.
            include_archived: Parameter description.
            include_content: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        mem_type = self._parse_memory_type(memory_type) if memory_type else None
        tag_set = {str(t).lower() for t in tags} if tags else None
        window = max(int(limit), min(1000, int(limit) * 5))
        memories = self.unified.search(query=query, memory_type=mem_type, limit=window)
        results: list[dict[str, Any]] = []
        for memory in memories:
            if not include_archived and memory.metadata.get("status") == "archived":
                continue
            if tag_set and not tag_set.issubset({str(t).lower() for t in memory.tags}):
                continue
            if memory.importance < min_importance:
                continue
            entry = self._memory_to_dict(memory)
            if not include_content:
                entry.pop("content", None)
                entry.pop("body", None)
            score = float(memory.metadata.get("similarity_score", memory.importance))
            results.append({"entry": entry, "preview": str(memory.content)[:200] if memory.content else "", "score": score})
            if len(results) >= limit:
                break
        return results

    def search(self, query: str | None = None, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Perform the search operation.

        Args:
            query: Parameter description.
            limit: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        return self.search_memories(query=query, limit=limit, **kwargs)

    def read_recent_memories(
        self,
        memory_type: str = "short_term",
        limit: int = 5,
        include_archived: bool = False,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Perform the read recent memories operation.

        Args:
            memory_type: Parameter description.
            limit: Parameter description.
            include_archived: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        memories = self.unified.list_recent(limit=max(int(limit) * 2, int(limit)), memory_type=self._parse_memory_type(memory_type))
        results: list[dict[str, Any]] = []
        for memory in memories:
            if not include_archived and memory.metadata.get("status") == "archived":
                continue
            data = self._memory_to_dict(memory)
            data["entry"] = dict(data)
            data["frontmatter"] = {"title": memory.title, "tags": list(memory.tags), **memory.metadata}
            data["body"] = str(memory.content)
            results.append(data)
            if len(results) >= limit:
                break
        return results

    def list_recent(self, limit: int = 10, memory_type: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        """
        List the recent.

        Args:
            limit: Parameter description.
            memory_type: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        return [self._memory_to_dict(m) for m in self.unified.list_recent(limit=limit, memory_type=self._parse_memory_type(memory_type) if memory_type else None)]

    def list(self, limit: int = 20, memory_type: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Perform the list operation.

        Args:
            limit: Parameter description.
            memory_type: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        return self.list_recent(limit=limit, memory_type=memory_type, **kwargs)

    def get_memory(self, memory_id: str, include_metadata: bool = True) -> dict[str, Any]:
        """
        Get the memory.

        Args:
            memory_id: Parameter description.
            include_metadata: Parameter description.

        Returns:
            dict[str, Any]
        """
        real_id = memory_id[:-3] if memory_id.endswith(".md") else memory_id
        memory = self.unified.recall(real_id)
        if not memory or memory.metadata.get("status") == "archived":
            return {"error": "Memory not found", "memory_id": real_id}
        memory.access()
        self.unified.backend.store(memory)
        data = self._memory_to_dict(memory)
        if not include_metadata:
            data.pop("metadata", None)
        return data

    def update_memory(
        self,
        filename: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,  # type: ignore[valid-type]
        add_tags: list[str] | None = None,  # type: ignore[valid-type]
        remove_tags: list[str] | None = None,  # type: ignore[valid-type]
        memory_type: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Update the memory.

        Args:
            filename: Parameter description.
            title: Parameter description.
            content: Parameter description.
            tags: Parameter description.
            add_tags: Parameter description.
            remove_tags: Parameter description.
            memory_type: Parameter description.

        Returns:
            dict[str, Any]
        """
        memory_id = filename[:-3] if filename.endswith(".md") else filename
        memory = self.unified.recall(memory_id)
        if not memory or memory.metadata.get("status") == "archived":
            return {"success": False, "status": "error", "error": "Memory not found", "memory_id": memory_id}
        if title is not None:
            memory.title = title
        if content is not None:
            memory.content = content
        if tags is not None:
            memory.tags = {str(t).lower() for t in tags}
        if add_tags:
            memory.tags.update({str(t).lower() for t in add_tags})
        if remove_tags:
            memory.tags.difference_update({str(t).lower() for t in remove_tags})
        if memory_type is not None:
            memory.memory_type = self._parse_memory_type(memory_type)
        if kwargs:
            memory.metadata.update(kwargs)
        self.unified.backend.store(memory)
        return {"success": True, "status": "success", **self._memory_to_dict(memory)}

    def delete_memory(self, filename: str, permanent: bool = False, **kwargs: Any) -> dict[str, Any]:
        """
        Remove the memory.

        Args:
            filename: Parameter description.
            permanent: Parameter description.

        Returns:
            dict[str, Any]
        """
        memory_id = filename[:-3] if filename.endswith(".md") else filename
        memory = self.unified.recall(memory_id)
        if not memory:
            return {"success": False, "status": "error", "error": "Memory not found", "memory_id": memory_id}
        if not permanent:
            memory.metadata["status"] = "archived"
            memory.importance = 0.0
            memory.galactic_distance = max(memory.galactic_distance, 0.95)
            self.unified.backend.store(memory)
            return {"success": True, "status": "success", "id": memory_id, "action": "archived"}
        conn = self.unified.backend.get_connection()
        try:
            exists = conn.execute("SELECT 1 FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if not exists:
                return {"success": False, "status": "error", "error": "Memory not found", "memory_id": memory_id}
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.execute("DELETE FROM tags WHERE memory_id = ?", (memory_id,))
            conn.execute("DELETE FROM associations WHERE source_id = ? OR target_id = ?", (memory_id, memory_id))
            conn.execute("DELETE FROM holographic_coords WHERE memory_id = ?", (memory_id,))
            conn.commit()
        finally:
            conn.close()
        return {"success": True, "status": "success", "id": memory_id, "action": "permanently_deleted"}

    def delete(self, filename: str, permanent: bool = False, **kwargs: Any) -> dict[str, Any]:
        """
        Perform the delete operation.

        Args:
            filename: Parameter description.
            permanent: Parameter description.

        Returns:
            dict[str, Any]
        """
        return self.delete_memory(filename=filename, permanent=permanent, **kwargs)

    def associate(self, memory_id1: str, memory_id2: str, strength: float = 0.5) -> dict[str, Any]:
        """
        Perform the associate operation.

        Args:
            memory_id1: Parameter description.
            memory_id2: Parameter description.
            strength: Parameter description.

        Returns:
            dict[str, Any]
        """
        self.unified.associate(memory_id1, memory_id2, strength=strength)
        return {"success": True, "status": "success", "source_id": memory_id1, "target_id": memory_id2, "strength": strength}

    def consolidate(self) -> int:
        """
        Perform the consolidate operation.

        Returns:
            int
        """
        return int(self.unified.consolidate())

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        return cast(dict[str, Any], self.unified.get_stats())

    def stats(self) -> dict[str, Any]:
        """
        Perform the stats operation.

        Returns:
            dict[str, Any]
        """
        return self.get_stats()

    def get_cache_stats(self) -> dict[str, Any] | None:
        """
        Get the cache stats.

        Returns:
            dict[str, Any] | None
        """
        try:
            from whitemagic.optimization.predictive_cache import get_memory_cache
            return cast(dict[str, Any], get_memory_cache().get_stats())
        except (ImportError, AttributeError):
            return None

    def list_all_memories(self, include_archived: bool = False, sort_by: str = "created") -> dict[str, list[dict[str, Any]]]:  # type: ignore[valid-type]
        """
        List the all memories.

        Args:
            include_archived: Parameter description.
            sort_by: Parameter description.

        Returns:
            dict[str, list[dict[str, Any]]]
        """
        memories = self.unified.list_recent(limit=1000)
        if sort_by == "accessed":
            memories.sort(key=lambda m: m.accessed_at, reverse=True)
        result: dict[str, list[dict[str, Any]]] = {"short_term": [], "long_term": [], "archived": []}
        for memory in memories:
            archived = memory.metadata.get("status") == "archived"
            if archived and not include_archived:
                continue
            data = self._memory_to_dict(memory)
            key = memory.memory_type.name.lower()
            if key in result and not archived:
                result[key].append(data)
            if archived:
                result["archived"].append(data)
        return result

    def list_all_tags(self) -> dict[str, Any]:
        """
        List the all tags.

        Returns:
            dict[str, Any]
        """
        counter: Counter[str] = Counter()
        memories = self.unified.list_recent(limit=1000)
        for memory in memories:
            counter.update(str(t) for t in memory.tags)
        return {
            "total_unique_tags": len(counter),
            "total_tag_usages": sum(counter.values()),
            "total_memories_with_tags": sum(1 for m in memories if m.tags),
            "tags": [{"tag": tag, "count": count} for tag, count in counter.most_common()],
        }

    def generate_context_summary(self, tier: int = 1) -> str:
        """
        Generate context summary.

        Args:
            tier: Parameter description.

        Returns:
            str
        """
        limits = {0: 3, 1: 10, 2: 50}
        memories = self.unified.list_recent(limit=limits.get(tier, 10))
        return "\n---\n".join(f"Title: {m.title}\nContent: {m.content}\n" for m in memories)

    def consolidate_short_term(self, dry_run: bool = False) -> dict[str, int]:
        """
        Perform the consolidate short term operation.

        Args:
            dry_run: Parameter description.

        Returns:
            dict[str, int]
        """
        count = 0 if dry_run else self.consolidate()
        return {"archived": count, "auto_promoted": 0, "decayed": 0}

    def normalize_legacy_tags(self, dry_run: bool = True) -> dict[str, Any]:
        """
        Perform the normalize legacy tags operation.

        Args:
            dry_run: Parameter description.

        Returns:
            dict[str, Any]
        """
        return {"dry_run": dry_run, "affected_memories": 0, "changes": []}

    def restore_memory(self, memory_id: str, memory_type: str = "short_term") -> dict[str, Any]:
        """
        Perform the restore memory operation.

        Args:
            memory_id: Parameter description.
            memory_type: Parameter description.

        Returns:
            dict[str, Any]
        """
        real_id = memory_id[:-3] if memory_id.endswith(".md") else memory_id
        memory = self.unified.recall(real_id)
        if not memory:
            return {"success": False, "status": "error", "error": "Memory not found"}
        if memory.metadata.get("status") != "archived":
            return {"success": False, "status": "error", "error": "Memory is not archived"}
        memory.metadata.pop("status", None)
        memory.importance = 0.5
        memory.memory_type = self._parse_memory_type(memory_type)
        self.unified.backend.store(memory)
        return {"success": True, "status": "success", "memory_type": memory_type}


_manager: MemoryManager | None = None


def get_memory_manager(base_dir: str | Path = ".") -> MemoryManager:
    """
    Get the memory manager.

    Args:
        base_dir: Parameter description.

    Returns:
        MemoryManager
    """
    global _manager
    if str(base_dir) != ".":
        return MemoryManager(base_dir=base_dir)
    if _manager is None:
        _manager = MemoryManager(base_dir=base_dir)
    return _manager
