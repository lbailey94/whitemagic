#!/usr/bin/env python3
"""Hermes pre_tool_call hook — Dharma policy gate.

Reads a JSON event from stdin and returns an allow/block decision.
Expected event shape:
    {"tool_name": "terminal", "tool_input": {"command": "..."}}
    {"tool_name": "write_file", "tool_input": {"path": "...", "content": "..."}}
"""

from __future__ import annotations

import json
import re
import sys


def main() -> None:
    """
    Perform the main operation.

    Returns:
        None
    """
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        event = {}

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    # ── Terminal policy ──────────────────────────────────────────────────
    if tool_name == "terminal":
        cmd = tool_input.get("command", "")
        dangerous = re.compile(
            r"(\brm\b.*-rf\s+(/$|/home$|/home/|~$|~/|\.\.)|"
            r"\bdd\b.*of=/dev/sd|"
            r"\bmkfs\b|"
            r">\s*/dev/sda|"
            r"\b:format\b|"
            r"\bdrop\b.*\bdatabase\b)"
        )
        if dangerous.search(cmd):
            result = {
                "allowed": False,
                "type": "block",
                "message": f"WhiteMagic Dharma Gate: command '{cmd}' is blocked for safety.",
            }
        else:
            result = {"allowed": True, "type": "allow"}
        print(json.dumps(result))
        return

    # ── File operation policy ─────────────────────────────────────────────
    if tool_name in ("write_file", "delete_file", "append_file", "move_file"):
        path = tool_input.get("path", "")
        system_paths = (
            "/etc/",
            "/usr/",
            "/bin/",
            "/sbin/",
            "/lib",
            "/boot/",
            "/dev/sd",
            "/proc/",
            "/sys/",
            "/var/log/",
        )
        if path.startswith(system_paths):
            result = {
                "allowed": False,
                "type": "block",
                "message": f"WhiteMagic Dharma Gate: system path '{path}' is protected.",
            }
        else:
            result = {"allowed": True, "type": "allow"}
        print(json.dumps(result))
        return

    # ── Default: allow ───────────────────────────────────────────────────
    print(json.dumps({"allowed": True, "type": "allow"}))


if __name__ == "__main__":
    main()
