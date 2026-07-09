# ruff: noqa: BLE001
"""Tool Usage Tracker — SQLite-persisted statistics for every MCP tool call.

Tracks per-tool, per-gana, and per-session usage with:
  - Timestamp and duration
  - Success/error status and error codes
  - Input/output token estimates
  - Gana classification (which of the 28 Ganas handled the call)
  - Session ID for cross-session analysis

Persists to SQLite so stats survive restarts. Provides query methods for:
  - Individual tool profiles (call count, last used, avg duration, error rate)
  - All tools profile (including never-used tools)
  - Per-Gana aggregation
  - Recent activity feed
  - Usage heatmap data

Usage:
    from whitemagic.core.monitoring.tool_usage_tracker import get_tool_usage_tracker

    tracker = get_tool_usage_tracker()
    tracker.record("search_memories", gana="gana_winnowing_basket",
                   duration_ms=12.5, success=True, input_tokens=50, output_tokens=200)
    stats = tracker.get_tool_stats("search_memories")
    never_used = tracker.get_never_used_tools(all_tool_names=[...])
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)


class ToolUsageTracker:
    """SQLite-persisted tool usage statistics."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            from whitemagic.config.paths import WM_ROOT

            db_path = WM_ROOT / "tool_usage.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with schema."""
        conn = safe_connect(str(self.db_path))
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                timestamp_iso TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                gana TEXT,
                session_id TEXT,
                duration_ms REAL,
                success INTEGER NOT NULL DEFAULT 1,
                error_code TEXT,
                error_message TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                locality TEXT DEFAULT 'edge'
            )
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_calls(tool_name)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON tool_calls(timestamp)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_gana ON tool_calls(gana)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON tool_calls(session_id)
        """)

        conn.commit()
        conn.close()

    def record(
        self,
        tool_name: str,
        gana: str | None = None,
        session_id: str | None = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error_code: str | None = None,
        error_message: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        locality: str = "edge",
    ) -> None:
        """Record a single tool call.

        Args:
            tool_name: Name of the tool that was called.
            gana: Which Gana meta-tool handled the call (e.g. "gana_ghost").
            session_id: Session identifier for cross-session analysis.
            duration_ms: Call duration in milliseconds.
            success: Whether the call succeeded.
            error_code: Error code if failed.
            error_message: Error message if failed.
            input_tokens: Estimated input token count.
            output_tokens: Estimated output token count.
            locality: Where computation happened (edge/local/cloud).
        """
        now = time.time()
        now_iso = datetime.now().isoformat()

        try:
            conn = safe_connect(str(self.db_path), timeout=5)
            conn.execute(
                """INSERT INTO tool_calls
                   (timestamp, timestamp_iso, tool_name, gana, session_id,
                    duration_ms, success, error_code, error_message,
                    input_tokens, output_tokens, locality)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now,
                    now_iso,
                    tool_name,
                    gana,
                    session_id,
                    round(duration_ms, 2),
                    1 if success else 0,
                    error_code,
                    error_message,
                    input_tokens,
                    output_tokens,
                    locality,
                ),
            )
            conn.commit()
            conn.close()
        except (OSError, Exception) as e:
            logger.debug("ToolUsageTracker record failed: %s", e)

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        """Get detailed statistics for a specific tool.

        Returns:
            Dict with call_count, last_used, first_used, avg_duration_ms,
            p50_ms, p90_ms, error_rate, total_tokens, etc.
        """
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        c.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp), "
            "AVG(duration_ms), SUM(success), "
            "SUM(input_tokens), SUM(output_tokens) "
            "FROM tool_calls WHERE tool_name = ?",
            (tool_name,),
        )
        row = c.fetchone()
        conn.close()

        if not row or row[0] == 0:
            return {
                "tool": tool_name,
                "call_count": 0,
                "last_used": None,
                "first_used": None,
                "avg_duration_ms": 0.0,
                "success_rate": 0.0,
                "error_count": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "status": "never_used",
            }

        call_count, first_ts, last_ts, avg_dur, success_sum, in_tok, out_tok = row
        success_count = success_sum or 0
        error_count = call_count - success_count

        last_used_iso = datetime.fromtimestamp(last_ts).isoformat() if last_ts else None
        first_used_iso = (
            datetime.fromtimestamp(first_ts).isoformat() if first_ts else None
        )

        return {
            "tool": tool_name,
            "call_count": call_count,
            "last_used": last_used_iso,
            "first_used": first_used_iso,
            "avg_duration_ms": round(avg_dur or 0, 2),
            "success_rate": round(success_count / max(1, call_count), 4),
            "error_count": error_count,
            "total_input_tokens": in_tok or 0,
            "total_output_tokens": out_tok or 0,
            "status": "active" if last_ts and (time.time() - last_ts) < 3600 else "idle",
        }

    def get_all_tool_stats(self) -> dict[str, Any]:
        """Get statistics for all tools that have been called at least once."""
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        c.execute(
            "SELECT tool_name, COUNT(*), MAX(timestamp), AVG(duration_ms), "
            "SUM(success), SUM(input_tokens), SUM(output_tokens) "
            "FROM tool_calls GROUP BY tool_name ORDER BY COUNT(*) DESC"
        )
        rows = c.fetchall()
        conn.close()

        tools = {}
        for row in rows:
            name, count, last_ts, avg_dur, success_sum, in_tok, out_tok = row
            last_iso = (
                datetime.fromtimestamp(last_ts).isoformat() if last_ts else None
            )
            tools[name] = {
                "call_count": count,
                "last_used": last_iso,
                "avg_duration_ms": round(avg_dur or 0, 2),
                "success_rate": round((success_sum or 0) / max(1, count), 4),
                "total_tokens": (in_tok or 0) + (out_tok or 0),
            }
        return tools

    def get_never_used_tools(
        self, all_tool_names: list[str]
    ) -> list[str]:
        """Given a list of all registered tool names, return those never called.

        Args:
            all_tool_names: Complete list of registered tool names.

        Returns:
            List of tool names that have zero calls in the database.
        """
        used = set(self.get_all_tool_stats().keys())
        return sorted([t for t in all_tool_names if t not in used])

    def get_gana_stats(self) -> dict[str, Any]:
        """Get per-Gana aggregation statistics."""
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        c.execute(
            "SELECT gana, COUNT(*), AVG(duration_ms), SUM(success), "
            "SUM(input_tokens + output_tokens) "
            "FROM tool_calls WHERE gana IS NOT NULL "
            "GROUP BY gana ORDER BY COUNT(*) DESC"
        )
        rows = c.fetchall()
        conn.close()

        ganas = {}
        for row in rows:
            gana, count, avg_dur, success_sum, total_tok = row
            ganas[gana] = {
                "call_count": count,
                "avg_duration_ms": round(avg_dur or 0, 2),
                "success_rate": round((success_sum or 0) / max(1, count), 4),
                "total_tokens": total_tok or 0,
            }
        return ganas

    def get_recent_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent tool calls as an activity feed.

        Args:
            limit: Maximum number of recent calls to return.

        Returns:
            List of call records, most recent first.
        """
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        c.execute(
            "SELECT timestamp_iso, tool_name, gana, duration_ms, success, "
            "error_code, input_tokens, output_tokens, locality "
            "FROM tool_calls ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = c.fetchall()
        conn.close()

        return [
            {
                "timestamp": row[0],
                "tool": row[1],
                "gana": row[2],
                "duration_ms": row[3],
                "success": bool(row[4]),
                "error_code": row[5],
                "input_tokens": row[6],
                "output_tokens": row[7],
                "locality": row[8],
            }
            for row in rows
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get overall usage summary statistics."""
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        c.execute(
            "SELECT COUNT(*), AVG(duration_ms), SUM(success), "
            "SUM(input_tokens), SUM(output_tokens), "
            "MIN(timestamp), MAX(timestamp) "
            "FROM tool_calls"
        )
        row = c.fetchone()

        c.execute("SELECT COUNT(DISTINCT tool_name) FROM tool_calls")
        distinct_tools = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT gana) FROM tool_calls WHERE gana IS NOT NULL")
        distinct_ganas = c.fetchone()[0]

        conn.close()

        if not row or row[0] == 0:
            return {
                "total_calls": 0,
                "distinct_tools_used": 0,
                "distinct_ganas_used": 0,
                "avg_duration_ms": 0.0,
                "success_rate": 0.0,
                "total_tokens": 0,
                "first_call": None,
                "last_call": None,
            }

        total, avg_dur, success_sum, in_tok, out_tok, first_ts, last_ts = row
        return {
            "total_calls": total,
            "distinct_tools_used": distinct_tools,
            "distinct_ganas_used": distinct_ganas,
            "avg_duration_ms": round(avg_dur or 0, 2),
            "success_rate": round((success_sum or 0) / max(1, total), 4),
            "total_tokens": (in_tok or 0) + (out_tok or 0),
            "first_call": (
                datetime.fromtimestamp(first_ts).isoformat() if first_ts else None
            ),
            "last_call": (
                datetime.fromtimestamp(last_ts).isoformat() if last_ts else None
            ),
        }

    def get_usage_heatmap(self, days: int = 7) -> dict[str, Any]:
        """Get usage data for heatmap visualization.

        Args:
            days: Number of days to look back.

        Returns:
            Dict mapping date strings to call counts.
        """
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        cutoff = time.time() - (days * 86400)
        c.execute(
            "SELECT date(timestamp_iso) as day, COUNT(*) "
            "FROM tool_calls WHERE timestamp >= ? "
            "GROUP BY day ORDER BY day",
            (cutoff,),
        )
        rows = c.fetchall()
        conn.close()

        return {row[0]: row[1] for row in rows}

    def get_top_tools(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get the most-called tools.

        Args:
            limit: Maximum number of tools to return.

        Returns:
            List of tool stats dicts, sorted by call count descending.
        """
        all_stats = self.get_all_tool_stats()
        sorted_tools = sorted(
            all_stats.items(), key=lambda x: x[1]["call_count"], reverse=True
        )[:limit]
        return [
            {"tool": name, **stats} for name, stats in sorted_tools
        ]

    def get_error_summary(self) -> dict[str, Any]:
        """Get error statistics across all tools."""
        conn = safe_connect(str(self.db_path), timeout=5)
        c = conn.cursor()

        c.execute(
            "SELECT tool_name, error_code, COUNT(*) "
            "FROM tool_calls WHERE success = 0 "
            "GROUP BY tool_name, error_code ORDER BY COUNT(*) DESC"
        )
        rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM tool_calls WHERE success = 0")
        total_errors = c.fetchone()[0]

        conn.close()

        errors_by_tool: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tool, code, count = row
            errors_by_tool.setdefault(tool, []).append(
                {"error_code": code, "count": count}
            )

        return {
            "total_errors": total_errors,
            "errors_by_tool": errors_by_tool,
        }

    def reset(self) -> None:
        """Clear all usage data. Use with caution."""
        conn = safe_connect(str(self.db_path), timeout=5)
        conn.execute("DELETE FROM tool_calls")
        conn.commit()
        conn.close()
        logger.info("ToolUsageTracker data cleared.")


# ── Singleton ─────────────────────────────────────────────────────────

_tracker: ToolUsageTracker | None = None


def get_tool_usage_tracker() -> ToolUsageTracker:
    """Get the global ToolUsageTracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = ToolUsageTracker()
    return _tracker


def reset_tool_usage_tracker() -> None:
    """Reset the singleton (for testing)."""
    global _tracker
    _tracker = None
