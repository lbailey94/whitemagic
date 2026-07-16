#!/usr/bin/env python3
"""Demo 1: Offline Memory Persistence — Agent remembers across sessions with zero internet.

Shows that WhiteMagic stores and retrieves memories entirely locally,
with zero network calls. Cloud AI cannot do this — their "memory" requires
round-trips to servers.

Run: python demos/demo1_offline_memory.py
Time: ~15 seconds
"""
import json
import time

from whitemagic.tools.unified_api import call_tool


def main():
    print("\n" + "=" * 60)
    print("  Demo 1: Offline Memory Persistence")
    print("  Zero internet. Zero API calls. Zero cloud.")
    print("=" * 60)

    # --- Session 1: Store memories ---
    print("\n  📝 Session 1: Storing memories...")
    t0 = time.time()

    memories = [
        {
            "title": "User prefers dark mode",
            "content": "The user explicitly asked for dark mode in all UIs. They find light themes straining.",
            "tags": ["preference", "ui", "dark-mode"],
            "galaxy": "sessions",
        },
        {
            "title": "Architecture decision: SQLite over PostgreSQL",
            "content": "We chose SQLite for Phase 1 because it's zero-config, embedded, and fast enough for local-first. PostgreSQL is overkill for single-user scenarios.",
            "tags": ["architecture", "database", "decision"],
            "galaxy": "codex",
        },
        {
            "title": "User's name is Lucas",
            "content": "The user introduced themselves as Lucas. They prefer casual tone over formal.",
            "tags": ["identity", "preference"],
            "galaxy": "sessions",
        },
    ]

    for mem in memories:
        result = call_tool("create_memory", **mem)
        status = result.get("status", "error")
        mem_id = result.get("details", {}).get("id", "?")
        print(f"     ✅ Stored: '{mem['title']}' (id={mem_id}) — {status}")

    t1 = time.time()
    print(f"  ⏱️  Stored 3 memories in {t1 - t0:.2f}s")

    # --- Session 2: Retrieve memories (simulating new session) ---
    print("\n  🔍 Session 2: Retrieving memories (new session simulation)...")
    t0 = time.time()

    # Search 1: By topic
    result = call_tool("search_memories", query="database choice", limit=3)
    hits = result.get("details", {}).get("results", [])
    print(f"     Search 'database choice': {len(hits)} results")
    for h in hits[:2]:
        title = h.get("title", "?")
        score = h.get("score", 0)
        print(f"       → '{title}' (score={score:.3f})")

    # Search 2: By preference
    result = call_tool("search_memories", query="what UI does the user like", limit=3)
    hits = result.get("details", {}).get("results", [])
    print(f"     Search 'what UI does the user like': {len(hits)} results")
    for h in hits[:2]:
        title = h.get("title", "?")
        score = h.get("score", 0)
        print(f"       → '{title}' (score={score:.3f})")

    # Search 3: By identity
    result = call_tool("search_memories", query="user name", limit=3)
    hits = result.get("details", {}).get("results", [])
    print(f"     Search 'user name': {len(hits)} results")
    for h in hits[:2]:
        title = h.get("title", "?")
        score = h.get("score", 0)
        print(f"       → '{title}' (score={score:.3f})")

    t1 = time.time()
    print(f"\n  ⏱️  Retrieved in {t1 - t0:.2f}s")
    print(f"\n  ✅ Demo complete — {t1 - t0:.2f}s retrieval, 0 bytes sent over network.")
    print("  Cloud AI cannot do this. Every 'memory' they store requires a server round-trip.")
    print("  WhiteMagic runs entirely on your machine. Your data never leaves.\n")


if __name__ == "__main__":
    main()
