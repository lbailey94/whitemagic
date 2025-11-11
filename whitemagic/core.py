"""
WhiteMagic Core - Memory Management System

This module contains the core MemoryManager class that handles all memory operations.
Refactored from the original memory_manager.py to be importable as a Python package.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
# from .models import ConsolidationEntry
from .fileio import file_lock, atomic_write
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Sequence

from .constants import (
    DEFAULT_MEMORY_DIR,
    DEFAULT_SHORT_TERM_DIR,
    DEFAULT_LONG_TERM_DIR,
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_METADATA_FILE,
    DEFAULT_SHORT_TERM_RETENTION_DAYS,
    DEFAULT_CONSOLIDATION_THRESHOLD,
    DEFAULT_NORMALIZE_TAGS,
    AUTO_PROMOTION_TAGS,
    TIER_CONTEXT_RULES,
    MEMORY_TYPE_SHORT_TERM,
    MEMORY_TYPE_LONG_TERM,
    VALID_MEMORY_TYPES,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    SORT_BY_CREATED,
    SORT_BY_UPDATED,
    SORT_BY_ACCESSED,
    VALID_SORT_OPTIONS,
    MEMORY_FILE_EXTENSION,
)
from .exceptions import (
    MemoryNotFoundError,
    InvalidMemoryTypeError,
    InvalidSortOptionError,
    InvalidTierError,
    MemoryAlreadyArchivedError,
    MemoryNotArchivedError,
    FileOperationError,
)
from .models import (
    Memory,
    MemoryCreate,
    MemoryUpdate,
    MemorySearchQuery,
    ContextRequest,
    ConsolidateRequest,
    RestoreRequest,
    NormalizeTagsRequest,
)
from .utils import (
    now_iso,
    slugify,
    normalize_tags,
    clean_markdown,
    truncate_text,
    summarize_text,
    create_preview,
    split_frontmatter,
    parse_frontmatter,
    create_frontmatter,
    parse_datetime,
)


class MemoryManager:
    """
    Manage AI memory across short-term, long-term, and archived storage.

    Features:
    - Robust metadata catalogue with persistence and audit logging
    - Soft-delete (archive) flow for consolidated short-term memories
    - Automatic promotion heuristics for reusable insights
    - Token-aware context generation
    - Tag normalization and management
    - Full CRUD operations with validation

    Example:
        >>> manager = MemoryManager(base_dir="/path/to/project")
        >>> memory = manager.create_memory(
        ...     MemoryCreate(
        ...         title="Important Insight",
        ...         content="Details here...",
        ...         type="long_term",
        ...         tags=["heuristic", "debugging"]
        ...     )
        ... )
    """

    # Default metadata structure
    DEFAULT_METADATA: Dict[str, Any] = {
        "version": "2.1",
        "short_term_retention_days": DEFAULT_SHORT_TERM_RETENTION_DAYS,
        "consolidation_threshold": DEFAULT_CONSOLIDATION_THRESHOLD,
        "memory_index": [],
        "consolidation_log": [],
    }

    # Auto-promotion tags
    PROMOTION_TAGS = AUTO_PROMOTION_TAGS

    # Tag normalization setting
    NORMALIZE_TAGS = DEFAULT_NORMALIZE_TAGS

    # Tier context rules
    TIER_CONTEXT_RULES = TIER_CONTEXT_RULES

    def __init__(self, base_dir: Path | str = ".") -> None:
        """
        Initialize the Memory Manager.

        Args:
            base_dir: Base directory for the memory system
        """
        self.base_dir = Path(base_dir).resolve()
        self.short_term_dir = self.base_dir / DEFAULT_SHORT_TERM_DIR
        self.long_term_dir = self.base_dir / DEFAULT_LONG_TERM_DIR
        self.archive_dir = self.base_dir / DEFAULT_ARCHIVE_DIR
        self.metadata_file = self.base_dir / DEFAULT_METADATA_FILE

        # Create directories
        self.short_term_dir.mkdir(parents=True, exist_ok=True)
        self.long_term_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata and build index
        self.metadata: Dict[str, Any] = self._load_metadata()
        raw_index = self.metadata.get("memory_index", [])
        self._index: Dict[str, Dict[str, Any]] = {}

        for item in raw_index if isinstance(raw_index, list) else []:
            normalised = self._normalise_index_entry(item)
            if normalised:
                self._index[normalised["filename"]] = normalised

        self._prune_missing_files()

    # ------------------------------------------------------------------ #
    # Metadata Management
    # ------------------------------------------------------------------ #

    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load metadata from metadata.json file.

        Returns:
            Dictionary with metadata and memory index
        """
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as handle:
                try:
                    data = json.load(handle)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Merge with defaults
        metadata = dict(self.DEFAULT_METADATA)
        metadata.update({k: v for k, v in data.items() if k != "memory_index"})
        metadata["memory_index"] = data.get("memory_index", [])
        metadata["consolidation_log"] = data.get("consolidation_log", [])

        return metadata

    def _normalise_index_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and normalize an index entry.

        Args:
            entry: Raw index entry from metadata

        Returns:
            Normalized entry or None if invalid
        """
        filename = entry.get("filename")
        if not filename or not isinstance(filename, str):
            return None

        # Build normalized entry
        normalised: Dict[str, Any] = {
            "filename": filename,
            "title": str(entry.get("title", "Untitled")),
            "type": str(entry.get("type", MEMORY_TYPE_SHORT_TERM)),
            "path": str(entry.get("path", "")),
            "created": str(entry.get("created", "")),
        }

        # Optional fields
        if "updated" in entry:
            normalised["updated"] = str(entry["updated"])
        if "accessed" in entry:
            normalised["accessed"] = str(entry["accessed"])
        if "tags" in entry:
            normalised["tags"] = entry["tags"] if isinstance(entry["tags"], list) else []
        if "status" in entry:
            normalised["status"] = str(entry["status"])
        if "archived_at" in entry:
            normalised["archived_at"] = str(entry["archived_at"])
        if "restored_at" in entry:
            normalised["restored_at"] = str(entry["restored_at"])
        if "promoted_from" in entry:
            normalised["promoted_from"] = str(entry["promoted_from"])

        return normalised

    def _directory_for_type(self, memory_type: str) -> Path:
        """
        Get the directory path for a given memory type.

        Args:
            memory_type: Memory type (short_term, long_term, or archive)

        Returns:
            Path to the directory

        Raises:
            InvalidMemoryTypeError: If memory type is invalid
        """
        if memory_type == MEMORY_TYPE_SHORT_TERM:
            return self.short_term_dir
        if memory_type == MEMORY_TYPE_LONG_TERM:
            return self.long_term_dir
        if memory_type == "archive":
            return self.archive_dir

        raise InvalidMemoryTypeError(memory_type, VALID_MEMORY_TYPES | {"archive"})

    def _save_metadata(self) -> None:
        """
        Save metadata and index to metadata.json file.
        """
        # Serialize index entries
        serialised_entries = []
        for entry in self._index.values():
            ready = dict(entry)

            # Ensure lists are properly formatted
            if "tags" in ready and isinstance(ready["tags"], list):
                ready["tags"] = list(ready["tags"])

            serialised_entries.append(ready)

        # Update metadata
        self.metadata["memory_index"] = serialised_entries

        # Write to file with locking and atomic write
        with file_lock(self.metadata_file):
            content = json.dumps(self.metadata, indent=2)
            atomic_write(self.metadata_file, content)

    def _prune_missing_files(self) -> None:
        """
        Remove index entries for files that no longer exist on disk.
        """
        removed = []
        for filename, entry in list(self._index.items()):
            file_path = self.base_dir / entry["path"]
            if not file_path.exists():
                removed.append(filename)
                del self._index[filename]

        if removed:
            self._save_metadata()

    def _touch_entry(self, filename: str, *, accessed: bool = False, updated: bool = False) -> None:
        """
        Update access or modification timestamps for a memory entry.

        Args:
            filename: Memory filename
            accessed: If True, update accessed timestamp
            updated: If True, update updated timestamp
        """
        entry = self._index.get(filename)
        if not entry:
            return

        timestamp = now_iso()

        if accessed:
            entry["last_accessed"] = timestamp
        if updated:
            entry["last_updated"] = timestamp

    # ------------------------------------------------------------------ #
    # Helper: Tag Normalization
    # ------------------------------------------------------------------ #

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        """
        Normalize tags to lowercase for consistency.

        Args:
            tags: List of tags to normalize

        Returns:
            List of normalized tags (lowercase, stripped, no duplicates)
        """
        return normalize_tags(tags, normalize=self.NORMALIZE_TAGS)

    # ------------------------------------------------------------------ #
    # Internal Helpers
    # ------------------------------------------------------------------ #

    def _read_memory_file(self, entry: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Read a memory file and split into frontmatter and body.

        Args:
            entry: Memory index entry

        Returns:
            Tuple of (frontmatter dict, body text)
        """
        path = self.base_dir / entry["path"]
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        return split_frontmatter(raw)

    def _unique_archive_path(self, filename: str) -> Path:
        """
        Generate a unique path in the archive directory.

        If filename exists, append a counter.

        Args:
            filename: Desired filename

        Returns:
            Unique path in archive directory
        """
        candidate = self.archive_dir / filename
        if not candidate.exists():
            return candidate

        # Add counter if file exists
        base = candidate.stem
        ext = candidate.suffix
        counter = 1
        while True:
            candidate = self.archive_dir / f"{base}_{counter}{ext}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _serialise_for_listing(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize an index entry for API/listing output.

        Args:
            entry: Memory index entry

        Returns:
            Serialized dictionary
        """
        return {
            "filename": entry.get("filename"),
            "title": entry.get("title"),
            "type": entry.get("type"),
            "created": entry.get("created"),
            "tags": entry.get("tags", []),
            "status": entry.get("status", STATUS_ACTIVE),
            "path": entry.get("path"),
        }

    def _entries(
        self,
        memory_type: Optional[str],
        include_archived: bool = False,
        sort_by: str = SORT_BY_CREATED,
    ) -> List[Dict[str, Any]]:
        """
        Get filtered and sorted entries from the index.

        Args:
            memory_type: Filter by type (None = all)
            include_archived: Include archived memories
            sort_by: Sort field (created, updated, or accessed)

        Returns:
            List of matching entries

        Raises:
            InvalidSortOptionError: If sort_by is invalid
        """
        if sort_by not in VALID_SORT_OPTIONS:
            raise InvalidSortOptionError(sort_by, VALID_SORT_OPTIONS)

        filtered = []
        for entry in self._index.values():
            # Filter by type
            if memory_type and entry.get("type") != memory_type:
                continue

            # Filter by status
            status = entry.get("status", STATUS_ACTIVE)
            if status == STATUS_ARCHIVED and not include_archived:
                continue

            filtered.append(entry)

        # Sort by requested field
        if sort_by == SORT_BY_ACCESSED:
            filtered.sort(key=lambda e: e.get("last_accessed", ""), reverse=True)
        elif sort_by == SORT_BY_UPDATED:
            filtered.sort(key=lambda e: e.get("last_updated", ""), reverse=True)
        else:  # default to SORT_BY_CREATED
            filtered.sort(key=lambda e: e.get("created", ""), reverse=True)

        return filtered

    # ------------------------------------------------------------------ #
    # CRUD Operations
    # ------------------------------------------------------------------ #

    def create_memory(
        self,
        title: str,
        content: str,
        memory_type: str = MEMORY_TYPE_SHORT_TERM,
        tags: Optional[Sequence[str]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Create a new memory entry.

        Args:
            title: Memory title
            content: Memory content (markdown)
            memory_type: Type of memory (short_term or long_term)
            tags: List of tags
            extra_fields: Additional frontmatter fields

        Returns:
            Path to the created memory file

        Raises:
            InvalidMemoryTypeError: If memory_type is invalid
        """
        if memory_type not in VALID_MEMORY_TYPES:
            raise InvalidMemoryTypeError(memory_type, VALID_MEMORY_TYPES)

        # Normalize tags
        tags_list = [tag.strip() for tag in (tags or []) if tag and tag.strip()]
        normalized_tags = self._normalize_tags(tags_list)

        # Create filename
        timestamp = datetime.now()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{slugify(title)}{MEMORY_FILE_EXTENSION}"

        # Get directory and filepath
        directory = self._directory_for_type(memory_type)
        filepath = directory / filename

        # Create frontmatter
        frontmatter_str = create_frontmatter(
            title=title,
            timestamp=timestamp,
            tags=normalized_tags,
            extra_fields=extra_fields or {},
        )

        # Write file
        body = content.strip() + "\n"
        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write(frontmatter_str)
            handle.write("\n")
            handle.write(body)

        # Update index
        entry = {
            "filename": filename,
            "title": title,
            "type": memory_type,
            "tags": normalized_tags,
            "created": timestamp.isoformat(),
            "last_updated": timestamp.isoformat(),
            "last_accessed": timestamp.isoformat(),
            "path": str(filepath.relative_to(self.base_dir)),
            "status": STATUS_ACTIVE,
        }
        self._index[filename] = entry
        self._save_metadata()

        return filepath

    def read_recent_memories(
        self,
        memory_type: str = MEMORY_TYPE_SHORT_TERM,
        limit: int = 5,
        include_archived: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Read recent memories of a given type.

        Args:
            memory_type: Type of memory to read
            limit: Maximum number of memories to return
            include_archived: Include archived memories

        Returns:
            List of memory payloads with entry, frontmatter, and body
        """
        entries = self._entries(memory_type, include_archived=include_archived)
        limited = entries[:limit] if limit else entries
        payload = []

        for entry in limited:
            frontmatter_dict, body = self._read_memory_file(entry)
            payload.append(
                {
                    "entry": entry,
                    "frontmatter": frontmatter_dict,
                    "body": body,
                }
            )
            self._touch_entry(entry["filename"], accessed=True)

        if limited:
            self._save_metadata()

        return payload

    def search_memories(
        self,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        *,
        include_archived: bool = False,
        include_content: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query, type, and tags.

        Args:
            query: Search query string
            memory_type: Filter by memory type
            tags: Filter by tags (AND logic)
            include_archived: Include archived memories
            include_content: Search in content (slower but more thorough)

        Returns:
            List of search results with entry, preview, and score
        """
        query_lower = query.lower() if query else None
        tag_set = {tag.lower() for tag in (tags or [])}

        results = []
        for entry in self._entries(memory_type, include_archived):
            entry_tags = {tag.lower() for tag in entry.get("tags", [])}

            # Filter by tags
            if tag_set and not tag_set.issubset(entry_tags):
                continue

            matches_query = query_lower is None
            preview_text = ""
            score = 0

            if query_lower:
                title_match = query_lower in entry.get("title", "").lower()
                tag_match = any(query_lower in tag for tag in entry_tags)

                if include_content:
                    frontmatter_dict, body = self._read_memory_file(entry)
                    content = f"{frontmatter_dict}\n{body}"
                    content_match = query_lower in content.lower()
                    preview_text = create_preview(body)
                else:
                    content_match = False
                    preview_text = ""

                matches_query = title_match or tag_match or content_match
                score = sum(
                    [
                        2 if title_match else 0,
                        1 if tag_match else 0,
                        1 if content_match else 0,
                    ]
                )
            else:
                frontmatter_dict, body = self._read_memory_file(entry)
                preview_text = create_preview(body)

            if matches_query:
                results.append(
                    {
                        "entry": entry,
                        "preview": preview_text,
                        "score": score,
                    }
                )

        # Sort by score (desc) then by created date (desc)
        results.sort(
            key=lambda item: (
                -(item["score"]),
                item["entry"].get("created", ""),
            ),
            reverse=False,
        )
        return results

    # ------------------------------------------------------------------ #
    # Context Generation
    # ------------------------------------------------------------------ #

    def generate_context_summary(self, tier: int) -> str:
        """
        Generate a context summary for a given tier.

        Args:
            tier: Context tier (0, 1, or 2)

        Returns:
            Formatted context string

        Raises:
            InvalidTierError: If tier is invalid
        """
        if tier not in self.TIER_CONTEXT_RULES:
            raise InvalidTierError(tier, set(self.TIER_CONTEXT_RULES.keys()))

        rules = self.TIER_CONTEXT_RULES[tier]
        sections = []
        sections.append(f"## Context Package (Tier {tier})\n")

        for memory_type, heading in [
            (MEMORY_TYPE_SHORT_TERM, "Short-Term Memories"),
            (MEMORY_TYPE_LONG_TERM, "Long-Term Knowledge"),
        ]:
            config = rules.get(memory_type)
            if not config or config.get("limit", 0) <= 0:
                continue

            payload = self.read_recent_memories(memory_type, limit=config["limit"])
            if not payload:
                continue

            sections.append(f"### {heading}\n")
            for item in payload:
                entry = item["entry"]
                body = item["body"]
                tags = ", ".join(entry.get("tags", [])) or "none"
                created = entry.get("created", "")[:19]

                formatted_body = self._format_body_for_context(
                    body,
                    mode=config.get("mode", "summary"),
                    max_chars=config.get("max_chars", 0),
                )

                sections.append(
                    f"- **{entry.get('title', entry['filename'])}** "
                    f"(created: {created}, tags: {tags})\n"
                    f"  {formatted_body}\n"
                )

        summary = "\n".join(sections).strip() + "\n"
        self._save_metadata()
        return summary

    def _format_body_for_context(self, body: str, *, mode: str, max_chars: int) -> str:
        """
        Format memory body for context generation.

        Args:
            body: Memory body text
            mode: Format mode (summary, detailed, full)
            max_chars: Maximum characters

        Returns:
            Formatted body text
        """
        cleaned = clean_markdown(body)
        if not cleaned:
            return "(empty memory)"

        if mode == "summary":
            return summarize_text(cleaned, 80)
        if mode == "detailed":
            return truncate_text(cleaned, max_chars or 1200)
        if mode == "full":
            if max_chars and len(cleaned) > max_chars:
                return truncate_text(cleaned, max_chars)
            return cleaned
        return summarize_text(cleaned, 80)

    # ------------------------------------------------------------------ #
    # Consolidation
    # ------------------------------------------------------------------ #

    def consolidate_short_term(
        self,
        *,
        auto_promote_tags: Optional[Sequence[str]] = None,
        dry_run: bool = False,
        min_age_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Consolidate old short-term memories.

        Archives memories older than retention period and optionally
        auto-promotes memories with special tags to long-term.

        Args:
            auto_promote_tags: Tags that trigger auto-promotion
            dry_run: If True, don't actually consolidate
            min_age_days: Minimum age in days for consolidation (overrides default retention period)

        Returns:
            Dict with consolidation results
        """
        # Use provided min_age_days or fall back to metadata/default
        retention_days = (
            min_age_days
            if min_age_days is not None
            else int(self.metadata.get("short_term_retention_days", DEFAULT_SHORT_TERM_RETENTION_DAYS))
        )
        cutoff = datetime.now() - timedelta(days=retention_days)
        promotion_tags = {tag.lower() for tag in (auto_promote_tags or self.PROMOTION_TAGS)}

        old_entries = []
        for entry in self._entries(MEMORY_TYPE_SHORT_TERM):
            if entry.get("status") != STATUS_ACTIVE:
                continue
            file_path = self.base_dir / entry["path"]
            if not file_path.exists():
                continue
            modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            if modified <= cutoff:
                frontmatter_dict, body = self._read_memory_file(entry)
                tags = {tag.lower() for tag in frontmatter_dict.get("tags", entry.get("tags", []))}
                should_promote = bool(promotion_tags & tags)
                old_entries.append(
                    {
                        "entry": entry,
                        "frontmatter": frontmatter_dict,
                        "body": body,
                        "modified": modified,
                        "promote": should_promote,
                    }
                )

        if not old_entries:
            return {
                "archived": 0,
                "auto_promoted": 0,
                "dry_run": dry_run,
                "promoted_files": [],
                "archived_files": [],
            }

        now = datetime.now()
        consolidated_title = f"Consolidated Insights - {now.strftime('%Y-%m-%d')}"
        consolidated_lines = [
            "# Consolidated Short-Term Memories",
            f"**Consolidation Date**: {now_iso()}",
            f"**Source Memories**: {len(old_entries)}",
            "",
        ]

        auto_promoted_files = []
        archive_targets = []

        for item in old_entries:
            entry = item["entry"]
            frontmatter_dict = item["frontmatter"]
            body = item["body"]

            consolidated_lines.append(
                f"## {entry.get('title', entry['filename'])} " f"({entry['filename']})"
            )
            consolidated_lines.append(f"- Created: {entry.get('created', '')[:19]}")
            tags = ", ".join(frontmatter_dict.get("tags", entry.get("tags", []))) or "none"
            consolidated_lines.append(f"- Tags: {tags}")
            consolidated_lines.append("")
            consolidated_lines.append(body.strip())
            consolidated_lines.append("\n---\n")

            if item["promote"] and not dry_run:
                promotion_content = (
                    body.strip() + "\n\n---\n\n*Auto-promoted from short-term on " f"{now_iso()}.*"
                )
                promoted_path = self.create_memory(
                    title=entry.get("title", entry["filename"]),
                    content=promotion_content,
                    memory_type=MEMORY_TYPE_LONG_TERM,
                    tags=frontmatter_dict.get("tags", entry.get("tags", [])),
                )
                auto_promoted_files.append(str(promoted_path))

            if not dry_run:
                archive_targets.append(entry["filename"])

        consolidated_content = "\n".join(consolidated_lines).strip() + "\n"
        long_term_path = None
        if not dry_run:
            long_term_path = self.create_memory(
                title=consolidated_title,
                content=consolidated_content,
                memory_type=MEMORY_TYPE_LONG_TERM,
                tags=["consolidated", "archive"],
            )

        # Archive memories
        if not dry_run:
            for filename in archive_targets:
                entry = self._index.get(filename)
                if not entry:
                    continue
                current_path = self.base_dir / entry["path"]
                if not current_path.exists():
                    continue
                archive_path = self._unique_archive_path(filename)
                current_path.rename(archive_path)
                entry["status"] = STATUS_ARCHIVED
                entry["archived_at"] = now_iso()
                entry["path"] = str(archive_path.relative_to(self.base_dir))
                self._touch_entry(filename, updated=True)

        # Log consolidation
        log_entry = {
            "run_at": now_iso(),
            "dry_run": dry_run,
            "source_files": [item["entry"]["filename"] for item in old_entries],
            "auto_promoted": auto_promoted_files,
            "consolidated_entry": str(long_term_path) if long_term_path else None,
        }
        consolidation_log = self.metadata.setdefault("consolidation_log", [])
        consolidation_log.append(log_entry)

        if not dry_run:
            self._save_metadata()

        return {
            "archived": len(archive_targets),
            "auto_promoted": len(auto_promoted_files),
            "dry_run": dry_run,
            "promoted_files": auto_promoted_files,
            "archived_files": archive_targets,
        }

    # ------------------------------------------------------------------ #
    # Update Operations
    # ------------------------------------------------------------------ #

    def delete_memory(self, filename: str, *, permanent: bool = False) -> Dict[str, Any]:
        """
        Delete or archive a memory.

        Args:
            filename: Memory filename
            permanent: If True, delete permanently; else archive

        Returns:
            Dict with success status and action taken
        """
        entry = self._index.get(filename)
        if not entry:
            return {"success": False, "error": f"Memory '{filename}' not found in index"}

        file_path = self.base_dir / entry["path"]

        # If file doesn't exist, just remove from index
        if not file_path.exists():
            self._index.pop(filename, None)
            self._save_metadata()
            return {"success": True, "action": "removed_from_index", "filename": filename}

        if permanent:
            # Permanent deletion
            file_path.unlink()
            self._index.pop(filename, None)
            self._save_metadata()
            return {"success": True, "action": "permanently_deleted", "filename": filename}
        else:
            # Archive it
            if entry.get("status") == STATUS_ARCHIVED:
                return {"success": False, "error": f"Memory '{filename}' is already archived"}

            archive_path = self._unique_archive_path(filename)
            file_path.rename(archive_path)
            entry["status"] = STATUS_ARCHIVED
            entry["archived_at"] = now_iso()
            entry["path"] = str(archive_path.relative_to(self.base_dir))
            self._touch_entry(filename, updated=True)
            self._save_metadata()
            return {
                "success": True,
                "action": "archived",
                "filename": filename,
                "path": str(archive_path),
            }

    def update_memory(
        self,
        filename: str,
        *,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        add_tags: Optional[Sequence[str]] = None,
        remove_tags: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update a memory's metadata or content.

        Args:
            filename: The memory filename to update
            title: New title (if provided)
            content: New content (if provided)
            tags: Replace all tags with these (if provided)
            add_tags: Add these tags to existing
            remove_tags: Remove these tags from existing

        Returns:
            Dict with success status and updated path
        """
        entry = self._index.get(filename)
        if not entry:
            return {"success": False, "error": f"Memory '{filename}' not found"}

        file_path = self.base_dir / entry["path"]
        if not file_path.exists():
            return {"success": False, "error": f"Memory file not found at {file_path}"}

        # Read current content
        frontmatter_dict, body = self._read_memory_file(entry)

        # Update title
        if title:
            entry["title"] = title
            frontmatter_dict["title"] = title

        # Update tags with proper normalization
        if tags is not None:
            # Replace all tags (normalized)
            current_tags = self._normalize_tags(list(tags))
        else:
            # Build normalized tag map to handle legacy mixed-case tags
            if self.NORMALIZE_TAGS:
                # Create map: lowercase -> actual tag
                tag_map = {tag.lower(): tag.lower() for tag in entry.get("tags", [])}
            else:
                tag_map = {tag: tag for tag in entry.get("tags", [])}

            # Add new tags
            if add_tags:
                for tag in self._normalize_tags(list(add_tags)):
                    if self.NORMALIZE_TAGS:
                        tag_map[tag] = tag
                    else:
                        tag_map[tag] = tag

            # Remove tags (comparing normalized keys)
            if remove_tags:
                for tag in self._normalize_tags(list(remove_tags)):
                    tag_map.pop(tag if not self.NORMALIZE_TAGS else tag.lower(), None)

            current_tags = list(tag_map.values())

        entry["tags"] = current_tags
        frontmatter_dict["tags"] = current_tags

        # Update content if provided
        if content is not None:
            body = content.strip() + "\n"

        # Write back to file
        created_dt = parse_datetime(entry["created"])
        new_frontmatter = create_frontmatter(
            title=frontmatter_dict.get("title", entry["title"]),
            timestamp=created_dt,
            tags=current_tags,
            extra_fields={
                k: v for k, v in frontmatter_dict.items() if k not in ["title", "created", "tags"]
            },
        )

        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(new_frontmatter)
            handle.write("\n")
            handle.write(body)

        self._touch_entry(filename, updated=True)
        self._save_metadata()

        return {"success": True, "filename": filename, "path": str(file_path)}

    def restore_memory(
        self, filename: str, *, memory_type: str = MEMORY_TYPE_SHORT_TERM
    ) -> Dict[str, Any]:
        """
        Restore an archived memory back to active status.

        Args:
            filename: Memory filename to restore
            memory_type: Target memory type (short_term or long_term)

        Returns:
            Dict with success status and restored path
        """
        entry = self._index.get(filename)
        if not entry:
            return {"success": False, "error": f"Memory '{filename}' not found"}

        if entry.get("status") != STATUS_ARCHIVED:
            return {"success": False, "error": f"Memory '{filename}' is not archived"}

        if memory_type not in VALID_MEMORY_TYPES:
            return {"success": False, "error": f"Invalid memory_type: {memory_type}"}

        # Move file from archive to target directory
        source_path = self.base_dir / entry["path"]
        target_dir = self._directory_for_type(memory_type)
        target_path = target_dir / filename

        if not source_path.exists():
            return {"success": False, "error": f"Archived file not found at {source_path}"}

        if target_path.exists():
            return {"success": False, "error": f"File already exists at {target_path}"}

        source_path.rename(target_path)

        # Update metadata
        entry["status"] = STATUS_ACTIVE
        entry["type"] = memory_type
        entry["path"] = str(target_path.relative_to(self.base_dir))
        entry["restored_at"] = now_iso()
        self._touch_entry(filename, updated=True)
        self._save_metadata()

        return {
            "success": True,
            "filename": filename,
            "memory_type": memory_type,
            "path": str(target_path),
        }

    def normalize_legacy_tags(self, *, dry_run: bool = True) -> Dict[str, Any]:
        """
        Normalize all existing tags to lowercase (migration tool).

        This is useful for cleaning up legacy data that predates the
        tag normalization feature.

        Args:
            dry_run: If True, only report what would be changed

        Returns:
            Dict with affected memories and changes
        """
        changes = []

        for filename, entry in list(self._index.items()):
            original_tags = entry.get("tags", [])
            if not original_tags:
                continue

            normalized_tags = self._normalize_tags(original_tags)

            if original_tags != normalized_tags:
                changes.append(
                    {
                        "filename": filename,
                        "title": entry.get("title", ""),
                        "before": original_tags,
                        "after": normalized_tags,
                    }
                )

                if not dry_run:
                    # Update in memory
                    entry["tags"] = normalized_tags

                    # Update file
                    file_path = self.base_dir / entry["path"]
                    if file_path.exists():
                        frontmatter_dict, body = self._read_memory_file(entry)
                        created_dt = parse_datetime(entry["created"])
                        new_frontmatter = create_frontmatter(
                            title=entry.get("title", ""),
                            timestamp=created_dt,
                            tags=normalized_tags,
                            extra_fields={
                                k: v
                                for k, v in frontmatter_dict.items()
                                if k not in ["title", "created", "tags"]
                            },
                        )
                        with open(file_path, "w", encoding="utf-8") as handle:
                            handle.write(new_frontmatter)
                            handle.write("\n")
                            handle.write(body)

        if not dry_run and changes:
            self._save_metadata()

        return {"dry_run": dry_run, "affected_memories": len(changes), "changes": changes}

    # ------------------------------------------------------------------ #
    # Listing & Stats
    # ------------------------------------------------------------------ #

    def list_all_memories(
        self, *, include_archived: bool = False, sort_by: str = SORT_BY_CREATED
    ) -> Dict[str, Any]:
        """
        List all memories grouped by type.

        Args:
            include_archived: Include archived memories
            sort_by: Sort field (created, updated, or accessed)

        Returns:
            Dict with memories grouped by type and metadata
        """
        data = {
            "short_term": [
                self._serialise_for_listing(entry)
                for entry in self._entries(
                    MEMORY_TYPE_SHORT_TERM, include_archived=False, sort_by=sort_by
                )
            ],
            "long_term": [
                self._serialise_for_listing(entry)
                for entry in self._entries(
                    MEMORY_TYPE_LONG_TERM, include_archived=False, sort_by=sort_by
                )
            ],
        }

        if include_archived:
            archived = [
                self._serialise_for_listing(entry)
                for entry in self._entries(None, include_archived=True, sort_by=sort_by)
                if entry.get("status") == STATUS_ARCHIVED
            ]
            data["archived"] = archived

        data["metadata"] = {
            "short_term_retention_days": self.metadata.get(
                "short_term_retention_days", DEFAULT_SHORT_TERM_RETENTION_DAYS
            ),
            "consolidation_threshold": self.metadata.get(
                "consolidation_threshold", DEFAULT_CONSOLIDATION_THRESHOLD
            ),
            "counts": {
                "short_term": len(data["short_term"]),
                "long_term": len(data["long_term"]),
                "archived": len(data.get("archived", [])),
            },
        }
        return data

    def list_all_tags(self, *, include_archived: bool = False) -> Dict[str, Any]:
        """
        Get a list of all unique tags with usage counts.

        Args:
            include_archived: Include tags from archived memories

        Returns:
            Dict with tag statistics
        """
        tag_counts: Dict[str, int] = {}
        tag_types: Dict[str, set] = {}  # Track which memory types use each tag

        for entry in self._entries(None, include_archived=include_archived):
            memory_type = entry.get("type", "unknown")
            for tag in entry.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if tag not in tag_types:
                    tag_types[tag] = set()
                tag_types[tag].add(memory_type)

        # Sort by count descending
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))

        # Calculate unique memories with tags
        memories_with_tags = len(
            [
                entry
                for entry in self._entries(None, include_archived=include_archived)
                if entry.get("tags")
            ]
        )

        return {
            "tags": [
                {
                    "tag": tag,
                    "count": count,
                    "used_in": sorted(list(tag_types[tag])),
                }
                for tag, count in sorted_tags
            ],
            "total_unique_tags": len(tag_counts),
            "total_tag_usages": sum(tag_counts.values()),
            "total_memories_with_tags": memories_with_tags,
        }
