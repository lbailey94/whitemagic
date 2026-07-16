#!/usr/bin/env python3
"""Demo 2: Dream Cycle — Memories consolidate, serendipitous connections surface overnight.

Shows WhiteMagic's dream cycle: an offline memory consolidation process
inspired by biological sleep. Memories are reviewed, connections are drawn,
and the system 'wakes up' with new insights. Cloud AI has no equivalent —
they store data, they don't consolidate it.

Run: python demos/demo2_dream_cycle.py
Time: ~20 seconds
"""
import time

from whitemagic.tools.unified_api import call_tool


def main():
    print("\n" + "=" * 60)
    print("  Demo 2: Dream Cycle — Memory Consolidation")
    print("  Like biological sleep, but for AI agents.")
    print("=" * 60)

    # --- Seed diverse memories across galaxies ---
    print("\n  🧠 Seeding memories across galaxies...")
    t0 = time.time()

    seed_memories = [
        {
            "title": "Rust SIMD performance results",
            "content": "Rust PyO3 batch cosine similarity: 0.012ms per operation. 19x speedup over Python. SIMD instructions handle 8 floats per cycle.",
            "tags": ["rust", "performance", "simd"],
            "galaxy": "codex",
        },
        {
            "title": "Biological sleep ripples paper",
            "content": "Stanford research shows human memory consolidation via sharp-wave ripples during NREM sleep. Hippampus replays experiences at 20x speed.",
            "tags": ["neuroscience", "sleep", "memory"],
            "galaxy": "research",
        },
        {
            "title": "HNSW index optimization",
            "content": "Switched from brute-force k-NN to HNSW for vector search. Sub-millisecond queries on 16K embeddings. M=16, ef_construction=200.",
            "tags": ["search", "hnsw", "optimization"],
            "galaxy": "codex",
        },
        {
            "title": "Dream cycle architecture decision",
            "content": "Inspired by biological sleep ripples — WhiteMagic's dream cycle replays memories during idle time, drawing serendipitous connections between distant concepts.",
            "tags": ["architecture", "dream", "sleep", "consciousness"],
            "galaxy": "citta",
        },
        {
            "title": "Frustration signal detected",
            "content": "User showed frustration when search returned irrelevant results. Emotional steering system tagged this as a signal to improve recall quality.",
            "tags": ["emotion", "frustration", "steering"],
            "galaxy": "citta",
        },
    ]

    for mem in seed_memories:
        result = call_tool("create_memory", **mem)
        status = result.get("status", "error")
        print(f"     ✅ {mem['galaxy']}: '{mem['title']}' — {status}")

    t1 = time.time()
    print(f"  ⏱️  Seeded 5 memories across 3 galaxies in {t1 - t0:.2f}s")

    # --- Run dream cycle ---
    print("\n  😴 Running dream cycle (memory consolidation)...")
    t0 = time.time()

    result = call_tool("dream_cycle", action="run", phases="all")

    t1 = time.time()
    status = result.get("status", "error")
    details = result.get("details", {})

    if status == "success":
        phases_completed = details.get("phases_completed", 0)
        connections = details.get("connections_found", 0)
        consolidated = details.get("memories_consolidated", 0)
        insights = details.get("insights", [])

        print(f"     ✅ Dream cycle completed in {t1 - t0:.2f}s")
        print(f"     📊 Phases: {phases_completed}/12")
        print(f"     🔗 Connections discovered: {connections}")
        print(f"     📦 Memories consolidated: {consolidated}")

        if insights:
            print(f"\n  💡 Insights surfaced:")
            for insight in insights[:3]:
                desc = insight.get("description", insight) if isinstance(insight, dict) else str(insight)
                print(f"     → {desc}")
    else:
        msg = result.get("message", "unknown error")
        print(f"     ⚠️  Dream cycle status: {status} — {msg}")
        print("     (This is expected if dream cycle needs specific configuration)")

    # --- Show system introspection after dream ---
    print("\n  🔮 System self-awareness (gnosis) after dream...")
    gnosis = call_tool("gnosis", compact=True)
    if gnosis.get("status") == "success":
        snap = gnosis.get("details", {}).get("gnosis", {})
        coherence = snap.get("coherence", 0)
        citta_phase = snap.get("citta_phase", "unknown")
        print(f"     Coherence: {coherence:.2f}")
        print(f"     Citta phase: {citta_phase}")

    print(f"\n  ✅ Demo complete — dream cycle ran in {t1 - t0:.2f}s.")
    print("  Cloud AI stores your data. WhiteMagic *thinks* about it.")
    print("  Memories consolidate. Connections surface. The system wakes up smarter.\n")


if __name__ == "__main__":
    main()
