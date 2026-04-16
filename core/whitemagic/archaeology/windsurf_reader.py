"""
Windsurf Conversation Reader
============================

Reads protobuf conversation files from Windsurf/Cascade.
Location: ~/.codeium/windsurf/cascade/*.pb

These are binary protobuf files containing conversation history.
This module provides tools to:
- List available conversations
- Read conversation content
- Extract and index conversation data
- Import conversations into WhiteMagic memory
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A full conversation from Windsurf."""
    id: str
    path: str
    messages: list[ConversationMessage] = field(default_factory=list)
    created: str | None = None
    modified: str | None = None
    title: str | None = None
    size_bytes: int = 0

    def message_count(self) -> int:
        return len(self.messages)

    def to_markdown(self) -> str:
        """Export conversation as markdown."""
        lines = [
            f"# Conversation: {self.title or self.id}",
            f"**Created**: {self.created}",
            f"**Messages**: {self.message_count()}",
            "",
            "---",
            ""
        ]

        for i, msg in enumerate(self.messages, 1):
            role_emoji = "👤" if msg.role == "user" else "🤖" if msg.role == "assistant" else "⚙️"
            lines.append(f"## {role_emoji} {msg.role.title()} ({i})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "title": self.title,
            "created": self.created,
            "modified": self.modified,
            "message_count": self.message_count(),
            "size_bytes": self.size_bytes,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.messages
            ]
        }


class WindsurfConversationReader:
    """
    Read Windsurf/Cascade conversation files.
    
    The conversations are stored as protobuf binary files at:
    ~/.codeium/windsurf/cascade/
    
    This reader provides:
    - List available conversations
    - Read and parse conversation content
    - Export to various formats
    - Index conversations for search
    """

    DEFAULT_PATHS = [
        # Path expansion justified: External app data (Codeium/Windsurf)
        # See /media/lucas/SD_CARD/WHITEMAGIC/core/docs/SECOND_TEAM_PATH_CLEANUP.md
        Path.home() / ".codeium" / "windsurf" / "cascade",
        Path.home() / ".codeium" / "cascade",
    ]

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path
        if not self.base_path:
            for path in self.DEFAULT_PATHS:
                if path.exists():
                    self.base_path = path
                    break

        self._conversations: dict[str, Conversation] = {}
        self._index_path = WM_ROOT / "archaeology" / "windsurf_index.json"
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    def find_conversation_files(self) -> list[Path]:
        """Find all .pb conversation files."""
        if not self.base_path or not self.base_path.exists():
            return []

        pb_files: list[Path] = []
        for pattern in ["*.pb", "**/*.pb"]:
            pb_files.extend(self.base_path.glob(pattern))

        return sorted(set(pb_files), key=lambda p: p.stat().st_mtime, reverse=True)

    def list_conversations(self) -> list[dict[str, Any]]:
        """List all available conversations with metadata."""
        conversations = []

        for pb_file in self.find_conversation_files():
            try:
                stat = pb_file.stat()
                conv_id = pb_file.stem

                conversations.append({
                    "id": conv_id,
                    "path": str(pb_file),
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                })
            except Exception:
                continue

        return conversations

    def read_conversation_raw(self, path: str) -> bytes:
        """Read raw protobuf bytes from a conversation file."""
        return Path(path).read_bytes()

    def parse_protobuf_simple(self, data: bytes) -> list[dict[str, Any]]:
        """
        Simple protobuf parser for extracting text content.
        
        This is a best-effort parser that extracts string fields
        without requiring the full protobuf schema.
        """
        messages = []
        pos = 0

        while pos < len(data):
            try:
                # Read varint for field tag
                tag, pos = self._read_varint(data, pos)
                if tag == 0:
                    break

                field_num = tag >> 3
                wire_type = tag & 0x7

                if wire_type == 0:  # Varint
                    _, pos = self._read_varint(data, pos)
                elif wire_type == 1:  # 64-bit
                    pos += 8
                elif wire_type == 2:  # Length-delimited (string/bytes/embedded)
                    length, pos = self._read_varint(data, pos)
                    content = data[pos:pos + length]
                    pos += length

                    # Try to decode as UTF-8 string
                    try:
                        text = content.decode('utf-8')
                        if len(text) > 10 and text.isprintable():
                            messages.append({
                                "field": field_num,
                                "content": text,
                                "length": len(text)
                            })
                    except UnicodeDecodeError:
                        pass
                elif wire_type == 5:  # 32-bit
                    pos += 4
                else:
                    break

            except (IndexError, ValueError):
                break

        return messages

    def _read_varint(self, data: bytes, pos: int) -> tuple:
        """Read a varint from bytes."""
        result = 0
        shift = 0
        while pos < len(data):
            byte = data[pos]
            pos += 1
            result |= (byte & 0x7f) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return result, pos

    def read_conversation(self, path: str) -> Conversation:
        """
        Read and parse a conversation file.
        
        Args:
            path: Path to the .pb file
            
        Returns:
            Conversation object with parsed messages
        """
        pb_path = Path(path)
        if not pb_path.exists():
            raise FileNotFoundError(f"Conversation file not found: {path}")

        data = pb_path.read_bytes()
        stat = pb_path.stat()

        # Parse protobuf content
        parsed = self.parse_protobuf_simple(data)

        # Extract messages (heuristic: longer strings are likely message content)
        messages = []
        current_role = "unknown"

        for item in parsed:
            content = item["content"].strip()

            # Skip very short or metadata-like content
            if len(content) < 20:
                # Check for role indicators
                if "user" in content.lower():
                    current_role = "user"
                elif "assistant" in content.lower() or "claude" in content.lower():
                    current_role = "assistant"
                continue

            # This looks like actual message content
            messages.append(ConversationMessage(
                role=current_role,
                content=content,
            ))

            # Alternate role assumption
            current_role = "assistant" if current_role == "user" else "user"

        conv = Conversation(
            id=pb_path.stem,
            path=str(pb_path),
            messages=messages,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            size_bytes=stat.st_size,
        )
        return conv

    def stats(self) -> dict[str, Any]:
        """Return statistics about Windsurf conversations."""
        files = self.find_conversation_files()
        total_size = sum(f.stat().st_size for f in files)
        return {
            "total_conversations": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_path": str(self.base_path) if self.base_path else None,
        }

    def export_conversation(self, path: str, format: str = "markdown") -> str:
        """Export a conversation to a given format."""
        conv = self.read_conversation(path)
        if format == "json":
            return json.dumps(conv.to_dict(), indent=2)
        elif format == "markdown":
            return conv.to_markdown()
        else:
            return "\n\n".join([f"[{m.role}] {m.content}" for m in conv.messages])

    def search_conversations(self, query: str) -> list[dict[str, Any]]:
        """Search across all conversations for a query."""
        results = []
        query_lower = query.lower()

        for pb_file in self.find_conversation_files():
            try:
                conv = self.read_conversation(str(pb_file))
                matches = []
                for i, msg in enumerate(conv.messages):
                    if query_lower in msg.content.lower():
                        matches.append({
                            "message_index": i,
                            "role": msg.role,
                            "preview": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                        })

                if matches:
                    results.append({
                        "id": conv.id,
                        "path": conv.path,
                        "title": conv.title,
                        "match_count": len(matches),
                        "matches": matches
                    })
            except Exception:
                continue

        return results
