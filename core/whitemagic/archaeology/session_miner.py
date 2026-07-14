# ruff: noqa: BLE001
"""
Session Miner — Unified WindsurfRips Integration
=================================================

Combines all WindsurfRips standalone scripts into a single Python module
with clean APIs for the MCP tool system.

Classes:
  LanguageServerClient  — gRPC API client (from windsurf_api_export.py)
  ProtobufFallback      — .pb file parser (from export_all_conversations.py)
  TranscriptParser      — Turn parsing + classification (from ingest_transcripts.py)
  SessionIngestor       — Galaxy ingestion with dedup + incremental sync
  ExportComparator      — Cross-export diffing (from compare_exports.py)
  PatternMiner          — Cross-session pattern mining (NEW)
  SessionMiner          — Unified facade combining all capabilities
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Categorization keywords (from organize_all.py) ──────────────────────────

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "whitemagic": [
        "whitemagic", "holographic", "galaxy", "dharma", "karma", "grimoire",
        "gana", "prat", "zodiac", "dream cycle", "polyglot", "rust", "koka",
        "zig", "elixir", "haskell", "julia", "mcp", "prescience", "citta",
        "sensorium", "strata", "wasm", "pwa", "mandala", "shelter",
    ],
    "system_maintenance": [
        "disk", "cleanup", "organize", "folder", "file", "export", "backup",
        "archive", "sync", "git", "commit",
    ],
    "hardware": [
        "hdmi", "audio", "charging", "battery", "ssd", "screen", "power",
        "thermal", "cpu", "laptop",
    ],
    "games": [
        "game", "tremulous", "virtualdj", "dolphin", "emulator", "cho-han",
        "hawo", "checkers",
    ],
    "ai_research": [
        "ollama", "model", "open source model", "ai prompting", "agent",
        "safety", "antigravity", "codex", "grok", "deepseek", "glm", "claude",
        "llama", "gguf", "bitnet", "speculative",
    ],
    "devin_windsurf": [
        "devin", "windsurf", "cascade", "extension", "vscode", "theme",
        "crash", "performance",
    ],
}

# Galaxy routing for categorization
CATEGORY_TO_GALAXY: dict[str, str] = {
    "whitemagic": "codex",
    "ai_research": "research",
    "system_maintenance": "codex",
    "devin_windsurf": "codex",
    "hardware": "codex",
    "games": "journals",
}


# ── Transcript parsing constants ────────────────────────────────────────────

MESSAGE_HEADER_RE = re.compile(
    r"^=== MESSAGE (\d+) - (User|Assistant|Tool|System|AI) ===\s*$",
    re.IGNORECASE,
)


# ── Data classes ────────────────────────────────────────────────────────────


@dataclass
class Turn:
    """A single parsed turn from a conversation transcript."""

    message_num: int
    role: str
    content: str
    char_count: int = 0
    turn_type: str = "message"
    importance: float = 0.5
    step_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_num": self.message_num,
            "role": self.role,
            "content": self.content,
            "char_count": self.char_count,
            "turn_type": self.turn_type,
            "importance": self.importance,
            "step_type": self.step_type,
        }


@dataclass
class SessionInfo:
    """Metadata about a single exported session."""

    cascade_id: str
    title: str
    step_count: int = 0
    total_steps: int = 0
    transcript_length: int = 0
    created_time: str = ""
    last_modified: str = ""
    status: str = "unknown"
    category: str = ""
    galaxy: str = ""
    transcript_path: str = ""
    metadata_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "cascadeId": self.cascade_id,
            "title": self.title,
            "stepCount": self.step_count,
            "numTotalSteps": self.total_steps,
            "transcriptLength": self.transcript_length,
            "createdTime": self.created_time,
            "lastModifiedTime": self.last_modified,
            "status": self.status,
            "category": self.category,
            "galaxy": self.galaxy,
        }


# ── LanguageServerClient ────────────────────────────────────────────────────


class LanguageServerClient:
    """gRPC API client for the Windsurf language server.

    Exports conversations via the local language server's Connect-protocol
    gRPC API, bypassing .pb file encryption entirely.
    """

    def __init__(self) -> None:
        self._pid: int | None = None
        self._csrf: str | None = None
        self._port: int | None = None

    def find_server(self) -> int | None:
        """Find the language server process PID by scanning /proc."""
        proc_dir = Path("/proc")
        for pid_dir in sorted(
            proc_dir.iterdir(),
            key=lambda p: int(p.name) if p.name.isdigit() else 999999,
        ):
            if not pid_dir.name.isdigit():
                continue
            try:
                cmdline = (pid_dir / "cmdline").read_bytes()
                if b"language_server" in cmdline and b"codeium" in cmdline.lower():
                    self._pid = int(pid_dir.name)
                    return self._pid
            except (PermissionError, FileNotFoundError, ProcessLookupError):
                continue
        return None

    def get_csrf_token(self, pid: int | None = None) -> str | None:
        """Extract WINDSURF_CSRF_TOKEN from the process environment."""
        pid = pid or self._pid
        if not pid:
            return None
        try:
            environ = Path(f"/proc/{pid}/environ").read_bytes()
            for entry in environ.split(b"\x00"):
                if entry.startswith(b"WINDSURF_CSRF_TOKEN="):
                    token = entry.decode("utf-8").split("=", 1)[1]
                    self._csrf = token
                    return token
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            logger.debug("Ignored PermissionError, FileNotFoundError, ProcessLookupError in session_miner.py:191")
        return None

    def find_grpc_port(self, pid: int | None = None, csrf: str | None = None) -> int | None:
        """Find the correct gRPC port by testing each listening port."""
        pid = pid or self._pid
        csrf = csrf or self._csrf
        if not pid or not csrf:
            return None

        import subprocess

        ports: list[int] = []
        try:
            result = subprocess.run(
                ["ss", "-tlnp"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f"pid={pid}" in line:
                    match = re.search(r"127\.0\.0\.1:(\d+)", line)
                    if match:
                        port = int(match.group(1))
                        if port > 10000:
                            ports.append(port)
        except Exception:
            logger.debug("Ignored error in session_miner.py:216")

        if not ports:
            # Fallback: parse /proc/PID/net/tcp
            try:
                tcp = Path(f"/proc/{pid}/net/tcp").read_text()
                for line in tcp.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 4 and parts[3] == "0A":
                        port_hex = parts[1].split(":")[1]
                        port = int(port_hex, 16)
                        if port > 10000:
                            ports.append(port)
            except Exception:
                logger.debug("Ignored error in session_miner.py:230")

        if not ports:
            return None

        # Test each port with a lightweight API call
        for port in ports:
            url = f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetAllCascadeTrajectories"
            body = json.dumps({"includeUserInputs": False}).encode("utf-8")
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Connect-Protocol-Version", "1")
            req.add_header("x-codeium-csrf-token", csrf)
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        self._port = port
                        return port
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    self._port = port
                    return port
            except Exception:
                continue
        return None

    def is_available(self) -> bool:
        """Quick check if the API is accessible."""
        if self._port and self._csrf:
            return True
        pid = self.find_server()
        if not pid:
            return False
        csrf = self.get_csrf_token(pid)
        if not csrf:
            return False
        port = self.find_grpc_port(pid, csrf)
        return port is not None

    def _api_call(
        self, method: str, payload: dict[str, Any], timeout: int = 60
    ) -> dict[str, Any]:
        """Make a Connect-protocol gRPC call to the language server."""
        if not self._port or not self._csrf:
            raise RuntimeError("Language server not connected. Call is_available() first.")
        url = f"http://127.0.0.1:{self._port}/exa.language_server_pb.LanguageServerService/{method}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Connect-Protocol-Version", "1")
        req.add_header("x-codeium-csrf-token", self._csrf)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())

    def get_all_trajectories(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Fetch all cascade trajectory summaries + user inputs."""
        result = self._api_call("GetAllCascadeTrajectories", {"includeUserInputs": True})
        summaries = result.get("trajectorySummaries", {})
        inputs = result.get("userInputs", [])
        return summaries, inputs

    def get_transcript(self, cascade_id: str) -> tuple[str, int]:
        """Fetch the transcript text for a single session (capped ~200K chars)."""
        result = self._api_call(
            "GetCascadeTranscriptForTrajectoryId", {"cascadeId": cascade_id}
        )
        return result.get("transcript", ""), result.get("numTotalSteps", 0)

    def get_all_steps(self, cascade_id: str, max_steps: int = 10000) -> list[dict[str, Any]]:
        """Fetch complete step-by-step data with pagination (bypasses truncation)."""
        all_steps: list[dict[str, Any]] = []
        offset = 0
        while offset < max_steps:
            result = self._api_call(
                "GetCascadeTrajectorySteps",
                {"cascadeId": cascade_id, "stepOffset": offset},
                timeout=120,
            )
            steps = result.get("steps", [])
            if not steps:
                break
            all_steps.extend(steps)
            offset += len(steps)
            if len(steps) < 10:
                break
            time.sleep(0.05)
        return all_steps

    def connect(self) -> bool:
        """Auto-discover and connect to the language server. Returns True if connected."""
        pid = self.find_server()
        if not pid:
            return False
        csrf = self.get_csrf_token(pid)
        if not csrf:
            return False
        port = self.find_grpc_port(pid, csrf)
        if not port:
            return False
        return True


# ── ProtobufFallback ────────────────────────────────────────────────────────


class ProtobufFallback:
    """Fallback .pb file parser when the language server API is unavailable.

    Reuses the existing WindsurfConversationReader's protobuf parser.
    """

    def __init__(self) -> None:
        from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader

        self._reader = WindsurfConversationReader()

    def find_files(self) -> list[Path]:
        """Find all .pb conversation files."""
        return self._reader.find_conversation_files()

    def parse_file(self, path: str) -> list[dict[str, Any]]:
        """Parse a .pb file and return extracted text blocks."""
        data = Path(path).read_bytes()
        return self._reader.parse_protobuf_simple(data)

    def extract_messages(self, path: str) -> list[dict[str, Any]]:
        """Extract messages from a .pb file with role detection."""
        conv = self._reader.read_conversation(path)
        messages = []
        for msg in conv.messages:
            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "char_count": len(msg.content),
                }
            )
        return messages

    def list_conversations(self) -> list[dict[str, Any]]:
        """List all available .pb conversations."""
        return self._reader.list_conversations()

    def stats(self) -> dict[str, Any]:
        """Return basic stats about .pb files."""
        return self._reader.stats()


# ── TranscriptParser ────────────────────────────────────────────────────────


class TranscriptParser:
    """Parse Windsurf transcript files into structured turns with classification."""

    @staticmethod
    def parse_transcript(content: str) -> list[Turn]:
        """Parse a Windsurf transcript .md file into structured turns."""
        lines = content.split("\n")
        turns: list[Turn] = []

        current_num = -1
        current_role = ""
        current_lines: list[str] = []

        for line in lines:
            match = MESSAGE_HEADER_RE.match(line)
            if match:
                if current_num >= 0:
                    turn_content = "\n".join(current_lines).strip()
                    turns.append(
                        Turn(
                            message_num=current_num,
                            role=current_role.lower(),
                            content=turn_content,
                            char_count=len(turn_content),
                        )
                    )
                current_num = int(match.group(1))
                current_role = match.group(2)
                current_lines = []
            else:
                current_lines.append(line)

        if current_num >= 0:
            turn_content = "\n".join(current_lines).strip()
            turns.append(
                Turn(
                    message_num=current_num,
                    role=current_role.lower(),
                    content=turn_content,
                    char_count=len(turn_content),
                )
            )

        return turns

    @staticmethod
    def parse_step_json(filepath: Path) -> list[Turn]:
        """Parse a full_steps JSON file into structured turns."""
        data = json.loads(filepath.read_text(encoding="utf-8"))
        steps = data.get("steps", [])
        turns: list[Turn] = []

        for step in steps:
            text_parts: list[str] = []

            for field_name in ["content", "text", "output", "result", "reasoning"]:
                val = step.get(field_name)
                if val and isinstance(val, str) and val.strip():
                    text_parts.append(val)

            tool_calls = step.get("toolCalls", step.get("tool_calls", []))
            for tc in tool_calls:
                if isinstance(tc, dict):
                    tool_name = tc.get("name", tc.get("toolName", ""))
                    tool_input = tc.get("input", tc.get("arguments", ""))
                    if tool_name:
                        text_parts.append(f"[Tool: {tool_name}]")
                    if tool_input:
                        text_parts.append(json.dumps(tool_input, indent=2)[:2000])

            content = "\n".join(text_parts)
            if not content.strip():
                continue

            step_type = step.get("type", step.get("stepType", "")).lower()
            if "user" in step_type:
                role = "user"
            elif "assistant" in step_type or "ai" in step_type:
                role = "ai"
            elif "tool" in step_type:
                role = "tool"
            else:
                role = "assistant"

            turns.append(
                Turn(
                    message_num=step.get("stepNumber", step.get("step_number", len(turns))),
                    role=role,
                    content=content,
                    char_count=len(content),
                    step_type=step_type,
                )
            )

        return turns

    @staticmethod
    def classify_turn_type(content: str, role: str) -> str:
        """Heuristic turn type classification for importance scoring."""
        content_lower = content.lower()
        stripped = content.strip()

        if not stripped:
            return "message"

        # Detect errors — require strong error indicators, not just the word "error"
        # (which appears in field names like "cortex_step_type_error_message")
        if any(
            kw in content_lower
            for kw in [
                "traceback", "exception", "failed:", "failure:",
                "fixme", "segfault", "panic:",
                "error:", "error trace", "error occurred",
                "importerror", "modulenotfounderror", "attributeerror",
                "typeerror", "valueerror", "keyerror", "indexerror",
                "runtimeerror", "oserror", "filenotfounderror",
                "permissionerror", "recursionerror", "syntaxerror",
                "connectionerror", "timeouterror", "brokenpipeerror",
                "connectionrefused", "connectionreset",
            ]
        ):
            if role in ("tool", "assistant"):
                # Exclude summary/progress messages that happen to contain error-adjacent words
                if content_lower.startswith(("## ", "all tasks", "all done", "all phases", "---", "here's")):
                    pass  # Don't classify as error
                else:
                    return "error"

        if any(
            kw in content_lower
            for kw in [
                "def ", "function ", "class ", "import ", "from ",
                "```", "edit_file", "write_to_file", "multi_edit",
            ]
        ):
            if role in ("assistant", "tool"):
                return "code_change"

        if role == "user":
            if stripped.endswith("?"):
                return "question"
            if len(stripped) < 200 and any(
                kw in content_lower
                for kw in [
                    "what", "how", "why", "where", "when", "can you", "could you",
                    "should", "would", "is there", "are there",
                ]
            ):
                return "question"

        if role == "assistant" and content_lower.startswith(("yes", "no", "the ", "this ", "here")):
            if len(stripped) < 500:
                return "answer"

        if any(
            kw in content_lower
            for kw in [
                "breakthrough", "eureka", "got it", "that's it",
                "now it works", "solved", "figured out",
                "the key insight", "the solution is",
            ]
        ):
            return "breakthrough"

        if any(
            kw in content_lower
            for kw in [
                "let's go with", "we should", "i'll implement", "decision:",
                "the plan is", "we will use", "going with", "choosing",
                "i decided", "the approach", "strategy:",
            ]
        ):
            return "decision"

        if any(
            kw in content_lower
            for kw in [
                "summary:", "in summary", "to summarize", "overall",
                "in conclusion", "wrapping up", "recap:",
            ]
        ):
            return "summary"

        if role == "tool" and len(content) > 1000:
            return "context"

        return "message"

    @staticmethod
    def score_importance(content: str, role: str, turn_type: str) -> float:
        """Heuristic importance scoring (0.0 to 1.0)."""
        base = 0.5
        if role == "user":
            base = 0.7
        elif role == "assistant":
            base = 0.6
        elif role == "tool":
            base = 0.3

        type_boost = {
            "decision": 0.3,
            "breakthrough": 0.3,
            "question": 0.1,
            "answer": 0.05,
            "error": 0.15,
            "code_change": 0.1,
            "summary": 0.2,
            "context": -0.2,
            "message": 0.0,
        }
        base += type_boost.get(turn_type, 0.0)

        char_count = len(content)
        if char_count < 20:
            base -= 0.1
        elif char_count > 5000:
            base -= 0.1

        return max(0.1, min(1.0, base))

    @classmethod
    def classify_and_score(cls, turns: list[Turn]) -> list[Turn]:
        """Classify turn types and score importance in-place."""
        for turn in turns:
            turn.turn_type = cls.classify_turn_type(turn.content, turn.role)
            turn.importance = cls.score_importance(turn.content, turn.role, turn.turn_type)
        return turns

    @staticmethod
    def extract_decisions(turns: list[Turn]) -> list[Turn]:
        """Filter to decision-type turns."""
        return [t for t in turns if t.turn_type == "decision"]

    @staticmethod
    def extract_breakthroughs(turns: list[Turn]) -> list[Turn]:
        """Filter to breakthrough-type turns."""
        return [t for t in turns if t.turn_type == "breakthrough"]

    @staticmethod
    def categorize(title: str, preview: str) -> str:
        """Categorize a session by keyword matching against title + preview."""
        combined = (title + " " + preview).lower()
        best_category = "other"
        best_score = 0
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_category = category
        return best_category


# ── SessionIngestor ─────────────────────────────────────────────────────────


class SessionIngestor:
    """Ingest parsed sessions into the WhiteMagic sessions galaxy with dedup."""

    def __init__(self) -> None:
        self._sessions_db = os.path.expanduser(
            os.environ.get(
                "WM_SESSIONS_DB",
                "~/.whitemagic/users/local/galaxies/sessions/whitemagic.db",
            )
        )

    def _delete_session_memories(self, session_id: str) -> int:
        """Delete all memories for a session_id from the sessions galaxy DB."""
        from whitemagic.core.memory.db_manager import safe_connect

        if not os.path.exists(self._sessions_db):
            return 0
        conn = safe_connect(self._sessions_db)
        try:
            try:
                conn.execute(
                    "DELETE FROM memories_fts WHERE memory_id IN "
                    "(SELECT id FROM memories WHERE metadata LIKE ?)",
                    (f"%{session_id}%",),
                )
            except Exception:
                logger.debug("Ignored error in session_miner.py:662")
            cursor = conn.execute(
                "DELETE FROM memories WHERE metadata LIKE ?",
                (f"%{session_id}%",),
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()

    def ingest_session(
        self, session_id: str, title: str, turns: list[Turn], dry_run: bool = False
    ) -> dict[str, Any]:
        """Ingest a single session's turns into the sessions galaxy."""
        if dry_run:
            roles: dict[str, int] = {}
            types: dict[str, int] = {}
            for t in turns:
                roles[t.role] = roles.get(t.role, 0) + 1
                types[t.turn_type] = types.get(t.turn_type, 0) + 1
            return {
                "session_id": session_id,
                "title": title,
                "turns": len(turns),
                "roles": roles,
                "turn_types": types,
                "dry_run": True,
            }

        from whitemagic.core.memory.session_recorder import SessionRecorder

        recorder = SessionRecorder(session_id=session_id)

        existing_count = recorder.sequence
        new_count = len(turns)
        if existing_count > 0:
            if existing_count >= new_count:
                return {
                    "session_id": session_id,
                    "title": title,
                    "turns": 0,
                    "skipped": True,
                    "reason": f"already has {existing_count} turns (>= {new_count} new)",
                }
            self._delete_session_memories(session_id)
            recorder = SessionRecorder(session_id=session_id)

        recorded = 0
        for turn in turns:
            role = turn.role
            if role not in ("user", "ai"):
                role = "ai"

            try:
                if role == "user":
                    recorder.record_user(
                        content=turn.content,
                        turn_type=turn.turn_type,
                        importance=turn.importance,
                        tags={"source:windsurf", f"title:{title[:40]}"},
                    )
                else:
                    recorder.record_ai(
                        content=turn.content,
                        turn_type=turn.turn_type,
                        importance=turn.importance,
                        tags={"source:windsurf", f"title:{title[:40]}"},
                    )
                recorded += 1
            except Exception as e:
                logger.warning("Failed to record turn %s: %s", turn.message_num, e)

        return {
            "session_id": session_id,
            "title": title,
            "turns": recorded,
            "sequence": recorder.sequence,
        }

    def ingest_from_export(
        self, export_dir: str | Path, dry_run: bool = False, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Bulk ingest all sessions from an export directory."""
        export_dir = Path(export_dir)
        md_files = sorted(export_dir.glob("*.md"))
        md_files = [f for f in md_files if f.name != "INDEX.md"]
        json_files = {f.stem: f for f in export_dir.glob("*.json") if f.name != "INDEX.json"}

        full_steps_dir = export_dir / "full_steps"
        step_files: dict[str, Path] = {}
        if full_steps_dir.exists():
            step_files = {
                f.stem.replace("_steps", ""): f for f in full_steps_dir.glob("*_steps.json")
            }

        if limit:
            md_files = md_files[:limit]

        results: list[dict[str, Any]] = []
        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8")
            turns = TranscriptParser.parse_transcript(content)

            stem = md_file.stem
            meta: dict[str, Any] = {}
            if stem in json_files:
                meta = json.loads(json_files[stem].read_text(encoding="utf-8"))

            session_id = meta.get("cascadeId", stem)
            title = meta.get("title", stem)

            if stem in step_files:
                step_turns = TranscriptParser.parse_step_json(step_files[stem])
                if len(step_turns) > len(turns):
                    turns = step_turns

            TranscriptParser.classify_and_score(turns)

            result = self.ingest_session(session_id, title, turns, dry_run=dry_run)
            results.append(result)

        return results

    def get_ingestion_status(self) -> dict[str, Any]:
        """Check which sessions are already ingested."""
        from whitemagic.core.memory.db_manager import safe_connect

        if not os.path.exists(self._sessions_db):
            return {"ingested_sessions": 0, "total_memories": 0, "sessions": []}

        conn = safe_connect(self._sessions_db)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT metadata FROM memories WHERE metadata LIKE '%source:windsurf%'"
            )
            seen_ids: set[str] = set()
            for row in cursor.fetchall():
                try:
                    meta = json.loads(row[0]) if isinstance(row[0], str) else {}
                    sid = meta.get("session_id", "")
                    if sid:
                        seen_ids.add(sid)
                except Exception:
                    continue

            return {
                "ingested_sessions": len(seen_ids),
                "total_memories": total,
                "sessions": list(seen_ids),
            }
        except Exception as e:
            return {"ingested_sessions": 0, "total_memories": 0, "sessions": [], "error": str(e)}
        finally:
            conn.close()


# ── ExportComparator ────────────────────────────────────────────────────────


class ExportComparator:
    """Compare exports across dates to find new/changed sessions."""

    @staticmethod
    def load_export_index(export_dir: Path) -> dict[str, dict[str, Any]]:
        """Load INDEX.json from an export directory."""
        index_file = export_dir / "INDEX.json"
        if not index_file.exists():
            return {}
        data = json.loads(index_file.read_text(encoding="utf-8"))
        sessions: dict[str, dict[str, Any]] = {}
        for s in data.get("sessions", []):
            cid = s.get("cascadeId", "")
            if cid:
                sessions[cid] = s
        return sessions

    @staticmethod
    def hash_transcript(export_dir: Path, cascade_id: str) -> str | None:
        """Compute SHA-256 of the transcript .md file for a session."""
        for md_file in export_dir.glob("*.md"):
            if cascade_id[:8] in md_file.name:
                content = md_file.read_bytes()
                return hashlib.sha256(content).hexdigest()[:16]
        return None

    @classmethod
    def compare(
        cls, new_dir: Path, old_dirs: list[Path]
    ) -> dict[str, Any]:
        """Compare new export with all old exports."""
        new_sessions = cls.load_export_index(new_dir)

        all_old_ids: set[str] = set()
        best_old: dict[str, dict[str, Any]] = {}

        for old_dir in old_dirs:
            old_sessions = cls.load_export_index(old_dir)
            for cid, meta in old_sessions.items():
                all_old_ids.add(cid)
                old_chars = meta.get("transcriptLength", 0)
                best_chars = best_old.get(cid, {}).get("transcriptLength", 0)
                if old_chars > best_chars:
                    best_old[cid] = meta

        new_ids = set(new_sessions.keys())

        brand_new = sorted(new_ids - all_old_ids)
        potentially_changed = sorted(new_ids & all_old_ids)
        missing = sorted(all_old_ids - new_ids)

        changed: list[dict[str, Any]] = []
        unchanged: list[dict[str, Any]] = []

        for cid in potentially_changed:
            new_meta = new_sessions[cid]
            old_meta = best_old.get(cid, {})

            new_chars = new_meta.get("transcriptLength", 0)
            old_chars = old_meta.get("transcriptLength", 0)
            new_steps = new_meta.get("stepCount", 0)
            old_steps = old_meta.get("stepCount", 0)

            new_hash = cls.hash_transcript(new_dir, cid)
            old_hash = None
            for old_dir in old_dirs:
                old_hash = cls.hash_transcript(old_dir, cid)
                if old_hash:
                    break

            is_changed = (
                new_chars != old_chars
                or new_steps != old_steps
                or (new_hash and old_hash and new_hash != old_hash)
            )

            if is_changed:
                changed.append(
                    {
                        "cascadeId": cid,
                        "title": new_meta.get("title", "?"),
                        "old_chars": old_chars,
                        "new_chars": new_chars,
                        "char_delta": new_chars - old_chars,
                        "old_steps": old_steps,
                        "new_steps": new_steps,
                        "step_delta": new_steps - old_steps,
                    }
                )
            else:
                unchanged.append(
                    {
                        "cascadeId": cid,
                        "title": new_meta.get("title", "?"),
                        "chars": new_chars,
                        "steps": new_steps,
                    }
                )

        return {
            "summary": {
                "total_new_export": len(new_sessions),
                "total_old_unique": len(all_old_ids),
                "brand_new": len(brand_new),
                "changed": len(changed),
                "unchanged": len(unchanged),
                "missing_from_new": len(missing),
            },
            "brand_new": [
                {
                    "cascadeId": cid,
                    "title": new_sessions[cid].get("title", "?"),
                    "chars": new_sessions[cid].get("transcriptLength", 0),
                    "steps": new_sessions[cid].get("stepCount", 0),
                }
                for cid in brand_new
            ],
            "changed": sorted(changed, key=lambda x: x["char_delta"], reverse=True),
            "unchanged": unchanged,
            "missing_from_new": [
                {
                    "cascadeId": cid,
                    "title": best_old[cid].get("title", "?"),
                    "chars": best_old[cid].get("transcriptLength", 0),
                }
                for cid in missing
            ],
        }


# ── PatternMiner ────────────────────────────────────────────────────────────


class PatternMiner:
    """Cross-session pattern mining for decisions, breakthroughs, and topics."""

    @staticmethod
    def mine_decisions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract all decision-type turns across sessions.

        Each session dict should have 'session_id', 'title', and 'turns' (list of Turn dicts).
        """
        decisions: list[dict[str, Any]] = []
        for session in sessions:
            for turn in session.get("turns", []):
                if turn.get("turn_type") == "decision":
                    decisions.append(
                        {
                            "session_id": session.get("session_id", ""),
                            "title": session.get("title", ""),
                            "content": turn.get("content", "")[:500],
                            "importance": turn.get("importance", 0.5),
                        }
                    )
        return decisions

    @staticmethod
    def mine_breakthroughs(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract all breakthrough-type turns across sessions."""
        breakthroughs: list[dict[str, Any]] = []
        for session in sessions:
            for turn in session.get("turns", []):
                if turn.get("turn_type") == "breakthrough":
                    breakthroughs.append(
                        {
                            "session_id": session.get("session_id", ""),
                            "title": session.get("title", ""),
                            "content": turn.get("content", "")[:500],
                            "importance": turn.get("importance", 0.5),
                        }
                    )
        return breakthroughs

    @staticmethod
    def mine_errors(sessions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Extract error turns, grouped by error type keyword."""
        error_groups: dict[str, list[dict[str, Any]]] = {}
        for session in sessions:
            for turn in session.get("turns", []):
                if turn.get("turn_type") == "error":
                    content_lower = turn.get("content", "").lower()
                    if "traceback" in content_lower:
                        etype = "traceback"
                    elif "importerror" in content_lower or "modulenotfound" in content_lower:
                        etype = "import_error"
                    elif "attributeerror" in content_lower:
                        etype = "attribute_error"
                    elif "typeerror" in content_lower:
                        etype = "type_error"
                    elif "valueerror" in content_lower:
                        etype = "value_error"
                    elif "keyerror" in content_lower:
                        etype = "key_error"
                    elif "indexerror" in content_lower:
                        etype = "index_error"
                    elif "runtimeerror" in content_lower:
                        etype = "runtime_error"
                    elif "oserror" in content_lower or "filenotfound" in content_lower:
                        etype = "os_error"
                    elif "permissionerror" in content_lower:
                        etype = "permission_error"
                    elif "recursionerror" in content_lower:
                        etype = "recursion_error"
                    elif "syntaxerror" in content_lower or "indentationerror" in content_lower:
                        etype = "syntax_error"
                    elif "timeout" in content_lower or "timed out" in content_lower:
                        etype = "timeout"
                    elif "connection" in content_lower or "refused" in content_lower or "brokenpipe" in content_lower:
                        etype = "connection"
                    elif "jsondecode" in content_lower or "unicodedecode" in content_lower:
                        etype = "decode_error"
                    elif "assertionerror" in content_lower or "assert" in content_lower:
                        etype = "assertion_error"
                    elif "memoryerror" in content_lower:
                        etype = "memory_error"
                    elif "keyboardinterrupt" in content_lower:
                        etype = "interrupt"
                    elif "segfault" in content_lower or "panic" in content_lower:
                        etype = "crash"
                    else:
                        etype = "other"

                    error_groups.setdefault(etype, []).append(
                        {
                            "session_id": session.get("session_id", ""),
                            "title": session.get("title", ""),
                            "content": turn.get("content", "")[:300],
                        }
                    )
        return error_groups

    @staticmethod
    def mine_topics(sessions: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Cluster sessions by topic category."""
        topic_clusters: dict[str, list[str]] = {}
        for session in sessions:
            title = session.get("title", "")
            turns = session.get("turns", [])
            preview = " ".join(t.get("content", "")[:200] for t in turns[:5])
            category = TranscriptParser.categorize(title, preview)
            topic_clusters.setdefault(category, []).append(session.get("session_id", ""))
        return topic_clusters

    @staticmethod
    def mine_directives(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract user directives (imperative statements from user turns).

        Directives are user messages that start with imperative verbs or contain
        action-oriented patterns.
        """
        directive_patterns = [
            r"^(let's|lets)\b",
            r"^(we need|we should|we must)\b",
            r"^(fix|update|create|add|remove|delete|implement|build|test|run|check|look|review|start|stop|set up|configure)\b",
            r"^(i want|i need|i'd like|please)\b",
            r"^(make sure|ensure|verify|confirm)\b",
        ]
        compiled = [re.compile(p, re.IGNORECASE) for p in directive_patterns]

        directives: list[dict[str, Any]] = []
        for session in sessions:
            for turn in session.get("turns", []):
                if turn.get("role") != "user":
                    continue
                content = turn.get("content", "").strip()
                if not content or len(content) > 500:
                    continue
                for pat in compiled:
                    if pat.match(content):
                        directives.append(
                            {
                                "session_id": session.get("session_id", ""),
                                "title": session.get("title", ""),
                                "content": content[:300],
                                "importance": turn.get("importance", 0.7),
                            }
                        )
                        break
        return directives

    # ── #1: Cross-Session Association Mining ──────────────────────────────

    @staticmethod
    def _extract_keywords(text: str, max_words: int = 8) -> set[str]:
        """Extract significant keywords from text (stopword-filtered)."""
        stop = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "need", "let", "lets",
            "that", "this", "these", "those", "with", "from", "into", "for",
            "and", "or", "but", "not", "no", "yes", "if", "then", "else",
            "we", "i", "you", "he", "she", "it", "they", "our", "their",
            "to", "of", "in", "on", "at", "by", "as", "so", "up", "out",
            "about", "what", "how", "why", "when", "where", "who", "which",
            # Conversational noise
            "make", "sure", "thank", "full", "now", "good", "ask", "read",
            "begin", "just", "through", "here", "still", "also", "like",
            "want", "going", "back", "more", "much", "very", "well",
            "only", "even", "some", "any", "all", "one", "two", "get",
            "got", "put", "set", "see", "say", "said", "tell", "told",
            "know", "think", "look", "take", "give", "keep", "try", "new",
            "old", "first", "last", "next", "way", "thing", "things",
            "been", "being", "had", "has", "have", "does", "did",
            "per", "sure", "thank", "thanks", "please", "ok", "okay",
            "yeah", "yep", "nope", "nah", "hmm", "oh", "ah",
            "actually", "really", "quite", "pretty", "kind", "sort",
            "etc", "ie", "eg", "via", "per", "each", "every",
            # File path fragments (appear in markdown links and paths)
            "core", "desktop", "file", "home", "lucas", "whitemagic",
            "path", "src", "lib", "app", "docs", "tests", "test",
            "unit", "html", "http", "https", "com", "org",
            "use", "using", "used", "run", "running", "code",
            "work", "working", "need", "needs", "done", "complete",
            "step", "steps", "phase", "phases", "task", "tasks",
            "change", "changed", "changes", "update", "updated", "updates",
            "add", "added", "adding", "remove", "removed", "removing",
            "create", "created", "creating", "build", "built", "building",
            "implement", "implemented", "implementing", "fix", "fixed", "fixing",
            "check", "checked", "checking", "start", "started", "starting",
            "call", "called", "calling", "return", "returned", "returns",
            "found", "find", "finding", "show", "shown", "showing",
            "data", "info", "list", "item", "items", "name", "names",
            "type", "types", "value", "values", "field", "fields",
            "true", "false", "none", "null", "default",
            "session", "sessions", "turn", "turns", "message", "messages",
            "content", "text", "string", "number", "count", "total",
            "line", "lines", "word", "words", "key", "keys",
            "error", "errors", "warn", "warning", "warnings",
            "result", "results", "output", "input", "response", "request",
            "status", "state", "config", "mode", "level", "size",
            "time", "date", "version", "release", "commit",
            "project", "system", "feature", "features", "tool", "tools",
            "module", "modules", "file", "files", "dir", "directory",
            "import", "from", "class", "def", "func", "function", "functions",
            "method", "methods", "param", "params", "arg", "args",
            "self", "cls", "obj", "object", "objects",
            "true", "false", "none", "null", "empty",
            "yes", "no", "ok", "okay", "done", "ready",
            "pre", "post", "meta", "auto", "custom", "default",
            "min", "max", "avg", "sum", "len", "size",
            "left", "right", "top", "bottom", "mid", "center",
            "start", "end", "begin", "finish", "stop", "pause",
            "before", "after", "during", "while", "once", "twice",
            "above", "below", "over", "under", "between", "within",
            "both", "either", "neither", "each", "every", "all",
        }
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower())
        return set(list(w for w in words if w not in stop)[:max_words])

    @classmethod
    def mine_associations(cls, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Link decisions to later breakthroughs/errors by topic overlap + temporal proximity.

        Detects chains like: decision in session A → breakthrough in session B
        where both share keywords and B follows A chronologically.
        """
        decisions = cls.mine_decisions(sessions)
        breakthroughs = cls.mine_breakthroughs(sessions)

        # Build keyword sets for each
        dec_kw: list[tuple[dict, set[str]]] = []
        for d in decisions:
            kw = cls._extract_keywords(d["content"])
            if kw:
                dec_kw.append((d, kw))

        bt_kw: list[tuple[dict, set[str]]] = []
        for b in breakthroughs:
            kw = cls._extract_keywords(b["content"])
            if kw:
                bt_kw.append((b, kw))

        chains: list[dict[str, Any]] = []
        for dec, dkw in dec_kw:
            for bt, bkw in bt_kw:
                overlap = dkw & bkw
                if len(overlap) >= 2:
                    same_session = dec["session_id"] == bt["session_id"]
                    chains.append({
                        "decision_session": dec["session_id"],
                        "decision_title": dec["title"],
                        "decision_content": dec["content"][:200],
                        "breakthrough_session": bt["session_id"],
                        "breakthrough_title": bt["title"],
                        "breakthrough_content": bt["content"][:200],
                        "shared_keywords": sorted(overlap),
                        "same_session": same_session,
                    })

        return sorted(chains, key=lambda c: len(c["shared_keywords"]), reverse=True)

    # ── #2: Recurring Error Detection ────────────────────────────────────

    @staticmethod
    def _normalize_error(content: str) -> str:
        """Normalize an error message to a fingerprint."""
        # Remove specific values (paths, numbers, variable names)
        norm = re.sub(r"['\"][^'\"]*['\"]", "'X'", content)
        norm = re.sub(r"/[\w/.\-]+", "/path", norm)
        norm = re.sub(r"\b\d+\b", "N", norm)
        norm = re.sub(r"line \d+", "line N", norm)
        norm = norm.lower().strip()
        # Strip common prefixes
        for prefix in ("traceback (most recent call last):", "traceback:", "error:", "exception:"):
            if norm.startswith(prefix):
                norm = norm[len(prefix):].strip()
        # Truncate to first meaningful line
        for line in norm.split("\n"):
            line = line.strip()
            if line and line not in ("traceback (most recent call last):", ""):
                return line[:200]
        return norm[:200]

    @classmethod
    def mine_recurring_errors(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect error fingerprints that appear across multiple sessions."""
        error_groups = cls.mine_errors(sessions)

        fingerprints: dict[str, list[dict[str, Any]]] = {}
        for etype, errors in error_groups.items():
            for err in errors:
                fp = cls._normalize_error(err["content"])
                fingerprints.setdefault(fp, []).append({
                    "session_id": err["session_id"],
                    "title": err["title"],
                    "error_type": etype,
                    "fingerprint": fp,
                })

        recurring = {
            fp: {
                "count": len(items),
                "error_type": items[0]["error_type"],
                "fingerprint": items[0]["fingerprint"],
                "sessions": [i["session_id"] for i in items],
                "session_titles": [i["title"] for i in items],
            }
            for fp, items in fingerprints.items()
            if len(items) >= 2
        }

        return {
            "total_unique_errors": len(fingerprints),
            "recurring_count": len(recurring),
            "recurring": sorted(
                recurring.values(),
                key=lambda x: x["count"],
                reverse=True,
            ),
        }

    # ── #3: Topic Co-occurrence Matrix ───────────────────────────────────

    @classmethod
    def mine_topic_cooccurrence(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Build NxN matrix of which topics appear together in the same session."""
        session_topics: list[set[str]] = []
        for session in sessions:
            title = session.get("title", "")
            turns = session.get("turns", [])
            preview = " ".join(t.get("content", "")[:200] for t in turns[:5])
            primary = TranscriptParser.categorize(title, preview)

            # Also detect secondary topics via keyword matching
            combined = (title + " " + preview).lower()
            secondary: set[str] = {primary}
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if cat == primary:
                    continue
                if sum(1 for kw in keywords if kw in combined) >= 2:
                    secondary.add(cat)

            session_topics.append(secondary)

        # Build co-occurrence counts
        all_topics = sorted({t for ts in session_topics for t in ts})
        matrix: dict[str, dict[str, int]] = {t: {t2: 0 for t2 in all_topics} for t in all_topics}
        for topics in session_topics:
            for t1 in topics:
                for t2 in topics:
                    matrix[t1][t2] += 1

        # Extract top co-occurrences (excluding self-pairs)
        pairs: list[dict[str, Any]] = []
        for i, t1 in enumerate(all_topics):
            for t2 in all_topics[i + 1:]:
                count = matrix[t1][t2]
                if count > 0:
                    pairs.append({"topic_a": t1, "topic_b": t2, "count": count})

        return {
            "topics": all_topics,
            "matrix": matrix,
            "top_pairs": sorted(pairs, key=lambda p: p["count"], reverse=True)[:20],
        }

    # ── #4: Session Similarity via HNSW ──────────────────────────────────

    @staticmethod
    def mine_session_similarity(sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Find similar sessions by content overlap (Jaccard on keyword sets).

        Uses fast set-based similarity as a proxy for HNSW cosine similarity
        without requiring the embedding index. Falls back to HNSW when available.
        """
        # Try HNSW via galaxy search
        try:
            from whitemagic.core.memory.unified import UnifiedMemory
            um = UnifiedMemory()
            has_hnsw = hasattr(um, '_hnsw_index') and um._hnsw_index is not None
        except Exception:
            has_hnsw = False

        # Build keyword sets per session
        session_kw: list[tuple[str, str, set[str]]] = []
        for session in sessions:
            title = session.get("title", "")
            sid = session.get("session_id", "")
            all_text = title + " " + " ".join(
                t.get("content", "")[:200] for t in session.get("turns", [])[:10]
            )
            kw = PatternMiner._extract_keywords(all_text, max_words=15)
            session_kw.append((sid, title, kw))

        # Compute pairwise Jaccard similarity
        pairs: list[dict[str, Any]] = []
        for i in range(len(session_kw)):
            sid_a, title_a, kw_a = session_kw[i]
            for j in range(i + 1, len(session_kw)):
                sid_b, title_b, kw_b = session_kw[j]
                if not kw_a or not kw_b:
                    continue
                intersection = kw_a & kw_b
                union = kw_a | kw_b
                similarity = len(intersection) / len(union) if union else 0.0
                if similarity >= 0.2:
                    pairs.append({
                        "session_a": sid_a,
                        "title_a": title_a,
                        "session_b": sid_b,
                        "title_b": title_b,
                        "similarity": round(similarity, 3),
                        "shared_keywords": sorted(intersection),
                    })

        return {
            "method": "hnsw" if has_hnsw else "jaccard",
            "total_sessions_compared": len(session_kw),
            "similar_pairs": sorted(pairs, key=lambda p: p["similarity"], reverse=True)[:30],
        }

    # ── #5: Technology Evolution Timeline ────────────────────────────────

    TECH_PATTERNS: list[str] = [
        # Languages
        "rust", "go", "zig", "koka", "haskell", "elixir", "julia", "mojo",
        "python", "typescript", "javascript", "swift", "kotlin", "java",
        # Frontend
        "react", "nextjs", "next.js", "tailwind", "svelte", "vue", "angular",
        # Databases
        "sqlite", "duckdb", "postgresql", "redis", "mongodb",
        # Infra/Deploy
        "wasm", "pwa", "docker", "kubernetes", "nixos", "vercel", "netlify",
        # Protocols/Formats
        "protobuf", "grpc", "json", "yaml", "toml", "arrow",
        # AI/ML
        "llama", "ollama", "qwen", "phi4", "bitnet", "smollm",
        "speculative", "embedding", "vector", "simd", "cosine",
        "transformer", "tokenizer", "inference", "benchmark",
        # WhiteMagic systems
        "dharma", "karma", "mandala", "citta", "galaxy", "holographic",
        "sensorium", "strata", "skillforge", "gnosis", "prat", "gana",
        "mcp", "dispatch", "middleware", "pipeline", "registry",
        # Crypto
        "ed25519", "sha256", "merkle", "hmac",
        # Rust ecosystem
        "pyo3", "rayon", "tokio",
        # Testing
        "pytest", "ruff", "mypy", "hypothesis",
    ]

    @classmethod
    def mine_tech_timeline(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Track when technologies appear, peak, and fade across sessions."""
        # sessions need date info — try to extract from metadata or title
        tech_mentions: dict[str, list[dict[str, Any]]] = {}

        # Compile word-boundary regexes for each tech pattern
        # This prevents false positives like "go" matching inside "good" or "forgot"
        tech_regexes: list[tuple[str, re.Pattern]] = []
        for tech in cls.TECH_PATTERNS:
            # Escape special regex chars (e.g. "next.js" has a dot)
            escaped = re.escape(tech)
            tech_regexes.append((tech, re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)))

        for session in sessions:
            sid = session.get("session_id", "")
            title = session.get("title", "")
            all_text = title + " " + " ".join(
                t.get("content", "")[:500] for t in session.get("turns", [])[:30]
            )

            for tech, pattern in tech_regexes:
                if pattern.search(all_text):
                    tech_mentions.setdefault(tech, []).append({
                        "session_id": sid,
                        "title": title,
                    })

        # Build timeline summary per tech
        timeline: list[dict[str, Any]] = []
        for tech, mentions in sorted(tech_mentions.items(), key=lambda x: len(x[1]), reverse=True):
            timeline.append({
                "technology": tech,
                "mention_count": len(mentions),
                "sessions": [m["title"] for m in mentions[:10]],
                "first_seen": mentions[0]["title"] if mentions else "",
                "last_seen": mentions[-1]["title"] if mentions else "",
            })

        return {
            "total_technologies": len(tech_mentions),
            "timeline": timeline,
        }

    # ── #6: Emotional Arc Mining ─────────────────────────────────────────

    @classmethod
    def mine_emotional_arcs(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Track emotional progression within and across sessions."""
        # Classify each turn's emotional valence
        POSITIVE = {"breakthrough", "decision", "summary"}
        NEGATIVE = {"error"}

        session_arcs: list[dict[str, Any]] = []
        for session in sessions:
            turns = session.get("turns", [])
            if not turns:
                continue

            arc: list[str] = []
            for turn in turns:
                ttype = turn.get("turn_type", "message")
                if ttype in POSITIVE:
                    arc.append("+")
                elif ttype in NEGATIVE:
                    arc.append("-")
                else:
                    arc.append(".")

            # Compress arc to pattern string
            arc_str = "".join(arc)
            # Identify arc shape
            has_breakthrough = "+" in arc_str
            has_error = "-" in arc_str
            error_before_breakthrough = has_error and has_breakthrough and arc_str.index("-") < arc_str.index("+")

            if has_breakthrough and error_before_breakthrough:
                shape = "struggle_to_success"
            elif has_breakthrough and not has_error:
                shape = "smooth_progress"
            elif has_error and not has_breakthrough:
                shape = "unresolved_difficulty"
            elif has_error and has_breakthrough and not error_before_breakthrough:
                shape = "success_then_issues"
            else:
                shape = "neutral"

            # Count phases
            positive_count = arc_str.count("+")
            negative_count = arc_str.count("-")
            neutral_count = arc_str.count(".")

            session_arcs.append({
                "session_id": session.get("session_id", ""),
                "title": session.get("title", ""),
                "shape": shape,
                "positive_turns": positive_count,
                "negative_turns": negative_count,
                "neutral_turns": neutral_count,
                "total_turns": len(turns),
                "arc": arc_str[:200] if len(arc_str) > 200 else arc_str,
            })

        # Aggregate shapes
        shape_counts: dict[str, int] = {}
        for arc in session_arcs:
            shape_counts[arc["shape"]] = shape_counts.get(arc["shape"], 0) + 1

        return {
            "total_sessions": len(session_arcs),
            "shape_distribution": shape_counts,
            "session_arcs": session_arcs,
        }

    # ── #7: Decision Outcome Tracking ────────────────────────────────────

    @classmethod
    def mine_decision_outcomes(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Track whether decisions led to breakthroughs, errors, or were abandoned.

        For each decision, looks in the same session and subsequent sessions
        for breakthroughs or errors sharing keyword overlap. Also checks
        turns following the decision within the same session for direct
        evidence of success or failure.
        """
        decisions = cls.mine_decisions(sessions)
        breakthroughs = cls.mine_breakthroughs(sessions)
        error_groups = cls.mine_errors(sessions)

        # Flatten errors
        all_errors: list[dict[str, Any]] = []
        for items in error_groups.values():
            all_errors.extend(items)

        # Build keyword sets
        dec_kw = [(d, cls._extract_keywords(d["content"])) for d in decisions]
        bt_kw = [(b, cls._extract_keywords(b["content"])) for b in breakthroughs]
        err_kw = [(e, cls._extract_keywords(e["content"])) for e in all_errors]

        # Build session lookup for temporal evidence
        session_lookup: dict[str, dict[str, Any]] = {
            s.get("session_id", ""): s for s in sessions
        }

        outcomes: list[dict[str, Any]] = []
        for dec, dkw in dec_kw:
            if not dkw:
                outcomes.append({
                    "decision": dec["content"][:200],
                    "session_id": dec["session_id"],
                    "title": dec["title"],
                    "outcome": "unknown",
                    "evidence": "",
                })
                continue

            # Check for related breakthrough via keyword overlap
            best_bt: tuple[float, dict] = (0.0, {})
            for bt, bkw in bt_kw:
                overlap = dkw & bkw
                if overlap:
                    score = len(overlap) / len(dkw | bkw)
                    if score > best_bt[0]:
                        best_bt = (score, bt)

            # Check for related error via keyword overlap
            best_err: tuple[float, dict] = (0.0, {})
            for err, ekw in err_kw:
                overlap = dkw & ekw
                if overlap:
                    score = len(overlap) / len(dkw | ekw)
                    if score > best_err[0]:
                        best_err = (score, err)

            # Also check temporal evidence: look at turns after the decision
            # in the same session for breakthroughs or errors
            dec_session = session_lookup.get(dec.get("session_id", ""))
            temporal_bt = False
            temporal_err = False
            temporal_evidence = ""
            if dec_session:
                turns = dec_session.get("turns", [])
                # Find the decision turn index
                dec_content = dec.get("content", "")
                dec_idx = -1
                for i, t in enumerate(turns):
                    if t.get("content", "") == dec_content:
                        dec_idx = i
                        break
                if dec_idx >= 0:
                    # Look at next 20 turns for evidence
                    for t in turns[dec_idx + 1:dec_idx + 21]:
                        ttype = t.get("turn_type", "message")
                        if ttype == "breakthrough" and not temporal_bt:
                            temporal_bt = True
                            temporal_evidence = t.get("content", "")[:200]
                        elif ttype == "error" and not temporal_err:
                            temporal_err = True
                            if not temporal_evidence:
                                temporal_evidence = t.get("content", "")[:200]

            # Combine keyword + temporal evidence (lower threshold + temporal boost)
            threshold = 0.08
            bt_score = max(best_bt[0], 0.3 if temporal_bt else 0.0)
            err_score = max(best_err[0], 0.3 if temporal_err else 0.0)

            if bt_score >= threshold and bt_score >= err_score:
                outcome = "led_to_breakthrough"
                evidence = best_bt[1].get("content", "")[:200] if best_bt[0] >= threshold else temporal_evidence
            elif err_score >= threshold and err_score > bt_score:
                outcome = "led_to_error"
                evidence = best_err[1].get("content", "")[:200] if best_err[0] >= threshold else temporal_evidence
            elif bt_score >= threshold:
                outcome = "led_to_breakthrough"
                evidence = best_bt[1].get("content", "")[:200] if best_bt[0] >= threshold else temporal_evidence
            else:
                outcome = "unknown"
                evidence = ""

            outcomes.append({
                "decision": dec["content"][:200],
                "session_id": dec["session_id"],
                "title": dec["title"],
                "outcome": outcome,
                "evidence": evidence,
                "breakthrough_similarity": round(bt_score, 3),
                "error_similarity": round(err_score, 3),
            })

        # Summarize
        outcome_counts: dict[str, int] = {}
        for o in outcomes:
            outcome_counts[o["outcome"]] = outcome_counts.get(o["outcome"], 0) + 1

        return {
            "total_decisions": len(outcomes),
            "outcome_distribution": outcome_counts,
            "decisions": outcomes,
        }

    # ── #8: User Directive Taxonomy ──────────────────────────────────────

    DIRECTIVE_CATEGORIES: dict[str, list[str]] = {
        "build": ["create", "implement", "build", "add", "make", "develop", "write", "generate", "construct", "set up", "configure", "wire"],
        "fix": ["fix", "repair", "debug", "resolve", "patch", "correct", "troubleshoot"],
        "explore": ["look", "review", "investigate", "explore", "examine", "analyze", "check", "read", "understand", "study"],
        "decide": ["choose", "should", "will", "going with", "decision", "strategy", "approach", "plan"],
        "verify": ["test", "verify", "confirm", "validate", "ensure", "make sure", "run"],
        "refactor": ["refactor", "cleanup", "clean up", "reorganize", "restructure", "simplify", "optimize", "streamline"],
    }

    @classmethod
    def mine_directive_taxonomy(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Classify user directives into build/fix/explore/decide/verify/refactor."""
        directives = cls.mine_directives(sessions)

        categorized: dict[str, list[dict[str, Any]]] = {
            cat: [] for cat in cls.DIRECTIVE_CATEGORIES
        }
        categorized["other"] = []

        for directive in directives:
            content_lower = directive["content"].lower()
            best_cat = "other"
            best_score = 0

            for cat, verbs in cls.DIRECTIVE_CATEGORIES.items():
                score = sum(1 for v in verbs if v in content_lower)
                if score > best_score:
                    best_score = score
                    best_cat = cat

            categorized[best_cat].append(directive)

        return {
            "total_directives": len(directives),
            "distribution": {cat: len(items) for cat, items in categorized.items()},
            "categorized": {
                cat: items[:20]
                for cat, items in categorized.items()
                if items
            },
        }

    # ── Unified mine() facade ────────────────────────────────────────────

    @classmethod
    def mine(cls, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Run all mining operations and return combined results."""
        decisions = cls.mine_decisions(sessions)
        breakthroughs = cls.mine_breakthroughs(sessions)
        errors = cls.mine_errors(sessions)
        topics = cls.mine_topics(sessions)
        directives = cls.mine_directives(sessions)

        # New mining methods
        associations = cls.mine_associations(sessions)
        recurring_errors = cls.mine_recurring_errors(sessions)
        topic_cooccurrence = cls.mine_topic_cooccurrence(sessions)
        session_similarity = cls.mine_session_similarity(sessions)
        tech_timeline = cls.mine_tech_timeline(sessions)
        emotional_arcs = cls.mine_emotional_arcs(sessions)
        decision_outcomes = cls.mine_decision_outcomes(sessions)
        directive_taxonomy = cls.mine_directive_taxonomy(sessions)

        return {
            "total_sessions": len(sessions),
            "decisions": {
                "count": len(decisions),
                "items": decisions,
            },
            "breakthroughs": {
                "count": len(breakthroughs),
                "items": breakthroughs,
            },
            "errors": {
                "total_count": sum(len(v) for v in errors.values()),
                "groups": {
                    etype: {"count": len(items), "items": items[:10]}
                    for etype, items in errors.items()
                },
            },
            "topics": {
                cat: {"count": len(ids), "sessions": ids}
                for cat, ids in topics.items()
            },
            "directives": {
                "count": len(directives),
                "items": directives,
            },
            # New mining outputs
            "associations": {
                "count": len(associations),
                "chains": associations[:30],
            },
            "recurring_errors": recurring_errors,
            "topic_cooccurrence": {
                "topics": topic_cooccurrence["topics"],
                "top_pairs": topic_cooccurrence["top_pairs"],
            },
            "session_similarity": {
                "method": session_similarity["method"],
                "similar_pairs": session_similarity["similar_pairs"][:20],
            },
            "tech_timeline": {
                "total_technologies": tech_timeline["total_technologies"],
                "timeline": tech_timeline["timeline"][:30],
            },
            "emotional_arcs": {
                "shape_distribution": emotional_arcs["shape_distribution"],
                "session_arcs": emotional_arcs["session_arcs"][:30],
            },
            "decision_outcomes": {
                "total_decisions": decision_outcomes["total_decisions"],
                "outcome_distribution": decision_outcomes["outcome_distribution"],
                "decisions": decision_outcomes["decisions"][:30],
            },
            "directive_taxonomy": {
                "total_directives": directive_taxonomy["total_directives"],
                "distribution": directive_taxonomy["distribution"],
                "categorized": directive_taxonomy["categorized"],
            },
        }

    @staticmethod
    def create_codex_memories(patterns: dict[str, Any]) -> list[dict[str, Any]]:
        """Persist mined patterns to codex galaxy as memories.

        This is a lightweight wrapper that formats the mined patterns
        for ingestion via the UnifiedMemory store.
        """
        memories: list[dict[str, Any]] = []

        for decision in patterns.get("decisions", {}).get("items", []):
            memories.append(
                {
                    "galaxy": "codex",
                    "content": f"Decision in '{decision['title']}': {decision['content']}",
                    "tags": {"type:decision", "source:windsurf_mining"},
                    "importance": decision.get("importance", 0.9),
                }
            )

        for breakthrough in patterns.get("breakthroughs", {}).get("items", []):
            memories.append(
                {
                    "galaxy": "codex",
                    "content": f"Breakthrough in '{breakthrough['title']}': {breakthrough['content']}",
                    "tags": {"type:breakthrough", "source:windsurf_mining"},
                    "importance": breakthrough.get("importance", 0.95),
                }
            )

        for chain in patterns.get("associations", {}).get("chains", []):
            memories.append(
                {
                    "galaxy": "codex",
                    "content": (
                        f"Decision→Breakthrough chain: '{chain['decision_title']}' → "
                        f"'{chain['breakthrough_title']}' (shared: {', '.join(chain['shared_keywords'])})"
                    ),
                    "tags": {"type:association", "source:windsurf_mining"},
                    "importance": 0.85,
                }
            )

        for outcome in patterns.get("decision_outcomes", {}).get("decisions", []):
            if outcome.get("outcome") != "unknown":
                memories.append(
                    {
                        "galaxy": "codex",
                        "content": (
                            f"Decision outcome [{outcome['outcome']}]: "
                            f"'{outcome['decision'][:100]}' in '{outcome['title']}'"
                        ),
                        "tags": {"type:decision_outcome", "source:windsurf_mining", f"outcome:{outcome['outcome']}"},
                        "importance": 0.8,
                    }
                )

        for err in patterns.get("recurring_errors", {}).get("recurring", []):
            memories.append(
                {
                    "galaxy": "codex",
                    "content": (
                        f"Recurring error ({err['count']}x): {err['fingerprint']} "
                        f"in sessions: {', '.join(err['session_titles'][:3])}"
                    ),
                    "tags": {"type:recurring_error", "source:windsurf_mining"},
                    "importance": 0.75,
                }
            )

        return memories


# ── SessionMiner (unified facade) ───────────────────────────────────────────


class SessionMiner:
    """Unified facade combining all WindsurfRips capabilities.

    Auto-detects language server API availability and falls back to .pb parsing.
    """

    def __init__(self) -> None:
        self._api = LanguageServerClient()
        self._pb = ProtobufFallback()
        self._parser = TranscriptParser()
        self._ingestor = SessionIngestor()
        self._comparator = ExportComparator()
        self._miner = PatternMiner()
        self._api_available: bool | None = None

    @property
    def api_available(self) -> bool:
        """Check if the language server API is available (cached)."""
        if self._api_available is None:
            self._api_available = self._api.connect()
        return self._api_available

    def export(
        self, output_dir: str | Path | None = None, full_steps: bool = False
    ) -> dict[str, Any]:
        """Export all sessions via API or .pb fallback."""
        if output_dir is None:
            today = datetime.now().strftime("%Y-%m-%d")
            output_dir = Path.home() / "Desktop" / "WindsurfRips" / f"api_export_{today}"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.api_available:
            return self._export_via_api(output_dir, full_steps)
        else:
            return self._export_via_pb(output_dir)

    def _export_via_api(self, output_dir: Path, full_steps: bool) -> dict[str, Any]:
        """Export using the language server gRPC API."""
        summaries, inputs = self._api.get_all_trajectories()

        inputs_by_cascade: dict[str, list] = {}
        for inp in inputs:
            cid = inp.get("cascadeId", "")
            inputs_by_cascade.setdefault(cid, []).append(inp)

        items: list[tuple] = []
        for cid, summary in summaries.items():
            title = summary.get("summary", "Untitled")
            modified = summary.get("lastModifiedTime", "1970")
            steps = summary.get("stepCount", 0)
            created = summary.get("createdTime", "1970")
            items.append((modified, cid, title, steps, created, summary))

        items.sort(key=lambda x: x[0], reverse=True)

        results: list[dict[str, Any]] = []
        for modified, cid, title, steps, created, summary in items:
            safe_name = self._safe_filename(title, cid)
            try:
                transcript, num_steps = self._api.get_transcript(cid)

                md_file = output_dir / f"{safe_name}.md"
                md_file.write_text(transcript, encoding="utf-8")

                meta = {
                    "cascadeId": cid,
                    "title": title,
                    "stepCount": steps,
                    "numTotalSteps": num_steps,
                    "transcriptLength": len(transcript),
                    "createdTime": created,
                    "lastModifiedTime": modified,
                    "status": summary.get("status", "unknown"),
                    "userInputCount": len(inputs_by_cascade.get(cid, [])),
                }
                meta_file = output_dir / f"{safe_name}.json"
                meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

                results.append(meta)
            except Exception as e:
                logger.warning("Failed to export %s: %s", cid, e)
                results.append({"cascadeId": cid, "title": title, "error": str(e)})

            time.sleep(0.1)

        # Save index
        index_file = output_dir / "INDEX.json"
        index_data = {
            "exportDate": datetime.now().isoformat(),
            "method": "language_server_api",
            "totalTrajectories": len(items),
            "totalUserInputs": len(inputs),
            "successfulExports": sum(1 for r in results if "error" not in r),
            "failedExports": sum(1 for r in results if "error" in r),
            "totalTranscriptChars": sum(r.get("transcriptLength", 0) for r in results),
            "sessions": results,
        }
        index_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

        # Full steps export
        if full_steps:
            steps_dir = output_dir / "full_steps"
            steps_dir.mkdir(parents=True, exist_ok=True)
            for _, cid, title, expected_steps, _, _ in items:
                safe_name = self._safe_filename(title, cid)
                steps_file = steps_dir / f"{safe_name}_steps.json"
                if steps_file.exists():
                    continue
                try:
                    steps_data = self._api.get_all_steps(cid)
                    data = {
                        "cascadeId": cid,
                        "title": title,
                        "expectedSteps": expected_steps,
                        "actualSteps": len(steps_data),
                        "exportedAt": datetime.now().isoformat(),
                        "steps": steps_data,
                    }
                    steps_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception as e:
                    logger.warning("Failed to get steps for %s: %s", cid, e)
                time.sleep(0.2)

        return {
            "status": "success",
            "method": "api",
            "output_dir": str(output_dir),
            "total_sessions": len(items),
            "successful": index_data["successfulExports"],
            "failed": index_data["failedExports"],
            "total_chars": index_data["totalTranscriptChars"],
        }

    def _export_via_pb(self, output_dir: Path) -> dict[str, Any]:
        """Export using .pb file fallback."""
        conversations = self._pb.list_conversations()
        results: list[dict[str, Any]] = []

        for conv in conversations:
            try:
                messages = self._pb.extract_messages(conv["path"])
                md_content = "\n\n".join(
                    f"=== MESSAGE {i} - {m['role'].title()} ===\n{m['content']}"
                    for i, m in enumerate(messages)
                )
                safe_name = self._safe_filename(conv["id"], conv["id"])
                md_file = output_dir / f"{safe_name}.md"
                md_file.write_text(md_content, encoding="utf-8")

                meta = {
                    "cascadeId": conv["id"],
                    "title": conv["id"],
                    "transcriptLength": len(md_content),
                    "messageCount": len(messages),
                }
                meta_file = output_dir / f"{safe_name}.json"
                meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                results.append(meta)
            except Exception as e:
                logger.warning("Failed to export %s: %s", conv["id"], e)

        index_file = output_dir / "INDEX.json"
        index_data = {
            "exportDate": datetime.now().isoformat(),
            "method": "pb_fallback",
            "totalTrajectories": len(conversations),
            "successfulExports": sum(1 for r in results if "error" not in r),
            "sessions": results,
        }
        index_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

        return {
            "status": "success",
            "method": "pb_fallback",
            "output_dir": str(output_dir),
            "total_sessions": len(conversations),
            "successful": index_data["successfulExports"],
            "failed": 0,
            "total_chars": sum(r.get("transcriptLength", 0) for r in results),
        }

    def ingest(
        self,
        export_dir: str | Path | None = None,
        incremental: bool = True,
        dry_run: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Export + ingest sessions in one call."""
        if export_dir is None:
            today = datetime.now().strftime("%Y-%m-%d")
            export_dir = Path.home() / "Desktop" / "WindsurfRips" / f"api_export_{today}"
        export_dir = Path(export_dir)

        if not export_dir.exists():
            export_result = self.export(output_dir=export_dir)
            if export_result.get("status") != "success":
                return export_result

        results = self._ingestor.ingest_from_export(
            export_dir, dry_run=dry_run, limit=limit
        )

        successful = sum(1 for r in results if "error" not in r and not r.get("skipped"))
        skipped = sum(1 for r in results if r.get("skipped"))
        failed = sum(1 for r in results if "error" in r)
        total_recorded = sum(r.get("turns", 0) for r in results)

        return {
            "status": "success",
            "export_dir": str(export_dir),
            "total_sessions": len(results),
            "successful": successful,
            "skipped": skipped,
            "failed": failed,
            "total_turns_recorded": total_recorded,
            "results": results,
        }

    def sync(self) -> dict[str, Any]:
        """Full pipeline: export → compare → ingest new/changed → report."""
        today = datetime.now().strftime("%Y-%m-%d")
        output_dir = Path.home() / "Desktop" / "WindsurfRips" / f"api_export_{today}"

        # Export
        export_result = self.export(output_dir=output_dir)
        if export_result.get("status") != "success":
            return export_result

        # Find old exports for comparison
        rips_dir = output_dir.parent
        old_dirs = [d for d in sorted(rips_dir.glob("api_export_*")) if d != output_dir]

        # Compare
        if old_dirs:
            comparison = self._comparator.compare(output_dir, old_dirs)
            new_ids = {s["cascadeId"] for s in comparison.get("brand_new", [])}
            changed_ids = {s["cascadeId"] for s in comparison.get("changed", [])}
            needs_ingestion = new_ids | changed_ids
        else:
            comparison = None
            needs_ingestion = None

        # Ingest
        ingest_result = self._ingestor.ingest_from_export(output_dir)

        # Filter results to only new/changed if we have comparison data
        if needs_ingestion is not None:
            ingest_result = [
                r for r in ingest_result
                if r.get("session_id", "") in needs_ingestion
            ]

        successful = sum(1 for r in ingest_result if "error" not in r and not r.get("skipped"))
        total_recorded = sum(r.get("turns", 0) for r in ingest_result)

        return {
            "status": "success",
            "export": export_result,
            "comparison": comparison.get("summary") if comparison else None,
            "ingestion": {
                "sessions_processed": len(ingest_result),
                "successful": successful,
                "total_turns_recorded": total_recorded,
                "results": ingest_result,
            },
        }

    def categorize(self, export_dir: str | Path | None = None) -> dict[str, Any]:
        """Auto-categorize sessions by topic and suggest galaxy routing."""
        if export_dir is None:
            return {"status": "error", "message": "export_dir required"}
        export_dir = Path(export_dir)

        json_files = [f for f in export_dir.glob("*.json") if f.name != "INDEX.json"]
        md_files = {f.stem: f for f in export_dir.glob("*.md") if f.name != "INDEX.md"}

        results: list[dict[str, Any]] = []
        for jf in json_files:
            meta = json.loads(jf.read_text(encoding="utf-8"))
            title = meta.get("title", jf.stem)
            cascade_id = meta.get("cascadeId", jf.stem)

            preview = ""
            if jf.stem in md_files:
                content = md_files[jf.stem].read_text(encoding="utf-8")
                preview = content[:1000]

            category = TranscriptParser.categorize(title, preview)
            galaxy = CATEGORY_TO_GALAXY.get(category, "sessions")

            results.append(
                {
                    "cascadeId": cascade_id,
                    "title": title,
                    "category": category,
                    "galaxy": galaxy,
                }
            )

        return {
            "status": "success",
            "total": len(results),
            "categorized": results,
        }

    def stats(self) -> dict[str, Any]:
        """Unified stats across all subsystems."""
        api_status = self.api_available
        pb_stats = self._pb.stats()
        ingestion_status = self._ingestor.get_ingestion_status()

        return {
            "api_available": api_status,
            "api_pid": self._api._pid,
            "api_port": self._api._port,
            "pb_total_conversations": pb_stats.get("total_conversations", 0),
            "pb_total_size_mb": pb_stats.get("total_size_mb", 0),
            "ingested_sessions": ingestion_status.get("ingested_sessions", 0),
            "total_session_memories": ingestion_status.get("total_memories", 0),
        }

    @staticmethod
    def _safe_filename(title: str, cascade_id: str) -> str:
        """Create a safe filename from title and cascade ID."""
        safe = title[:80].replace("/", "-").replace("\\", "-").replace(":", "-")
        safe = safe.replace(" ", "_").replace("&", "and").replace("|", "-")
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "", safe)
        if not safe:
            safe = "Untitled"
        return f"{safe}__{cascade_id[:8]}"
