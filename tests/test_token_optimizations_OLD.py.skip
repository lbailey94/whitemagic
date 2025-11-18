#!/usr/bin/env python3
"""
Test script to demonstrate token optimization savings.

Compares baseline (load all full) vs optimized (tiered loading).
"""

import time
from pathlib import Path

from whitemagic import MemoryManager
from whitemagic.optimized_context import OptimizedMemoryLoader
from whitemagic.smart_read import SessionContext, read_file_smart


def count_tokens_rough(text: str) -> int:
    """Rough token estimation (words * 1.3)."""
    return int(len(text.split()) * 1.3)


def test_baseline_loading(manager: MemoryManager):
    """Baseline: Load all memories in full."""
    print("\n📊 BASELINE: Loading all memories (full content)")
    print("-" * 60)

    start = time.time()
    # Load all memories fully
    all_memories = manager.list_all_memories()
    context_parts = []
    for mem_type in ["short_term", "long_term"]:
        for mem in all_memories.get(mem_type, []):
            filepath = manager.base_dir / mem["path"]
            if filepath.exists():
                context_parts.append(filepath.read_text())
    context_str = "\n\n".join(context_parts)
    elapsed = time.time() - start

    tokens = count_tokens_rough(context_str)

    print(f"✓ Loaded in {elapsed:.2f}s")
    print(f"✓ Total tokens: {tokens:,}")
    print(f"✓ Size: {len(context_str):,} characters")

    return tokens, elapsed


def test_optimized_tier0(loader: OptimizedMemoryLoader):
    """Tier 0: Titles + tags only."""
    print("\n📊 OPTIMIZED TIER 0: Titles + tags scan")
    print("-" * 60)

    start = time.time()
    result = loader.get_context(tier=0)
    elapsed = time.time() - start

    tokens = result.get("estimated_tokens", 0)

    print(f"✓ Loaded in {elapsed:.2f}s")
    print(f"✓ Estimated tokens: {int(tokens):,}")
    print(f"✓ Memories: {result['memory_count']}")

    return tokens, elapsed


def test_optimized_tier1(loader: OptimizedMemoryLoader, query: str = None):
    """Tier 1: Summaries + selective full."""
    print(f"\n📊 OPTIMIZED TIER 1: Summaries{' + query' if query else ''}")
    print("-" * 60)

    start = time.time()
    result = loader.get_context(tier=1, query=query)
    elapsed = time.time() - start

    tokens = result.get("estimated_tokens", 0)

    print(f"✓ Loaded in {elapsed:.2f}s")
    print(f"✓ Estimated tokens: {int(tokens):,}")
    print(f"✓ Memories: {result['memory_count']}")
    print(f"✓ Full loaded: {result.get('full_loaded', 0)}")

    return tokens, elapsed


def test_session_cache():
    """Test session caching prevents duplicate reads."""
    print("\n📊 SESSION CACHE: Deduplication test")
    print("-" * 60)

    ctx = SessionContext()
    test_file = Path(__file__).parent / "README.md"

    if not test_file.exists():
        print("⚠ README.md not found, skipping cache test")
        return

    # First read (from disk)
    start1 = time.time()
    content1, meta1 = read_file_smart(test_file, ctx)
    elapsed1 = time.time() - start1
    tokens1 = count_tokens_rough(content1)

    print(f"✓ First read (disk): {elapsed1*1000:.1f}ms, {tokens1:,} tokens")
    print(f"  Source: {meta1['source']}")

    # Second read (from cache)
    start2 = time.time()
    content2, meta2 = read_file_smart(test_file, ctx)
    elapsed2 = time.time() - start2

    print(f"✓ Second read (cache): {elapsed2*1000:.1f}ms, {tokens1:,} tokens")
    print(f"  Source: {meta2['source']}")
    print(f"✓ Cache speedup: {elapsed1/elapsed2:.1f}x faster")


def main():
    """Run all optimization tests."""
    print("\n" + "=" * 60)
    print("🚀 TOKEN OPTIMIZATION TEST SUITE")
    print("=" * 60)

    # Initialize
    manager = MemoryManager()
    loader = OptimizedMemoryLoader(manager)

    # Ensure summaries are cached (first-time setup)
    print("\n⏳ Ensuring summary cache is populated...")
    loader.ensure_all_summaries()
    print("✓ Summary cache ready\n")

    # Run tests
    baseline_tokens, baseline_time = test_baseline_loading(manager)
    tier0_tokens, tier0_time = test_optimized_tier0(loader)
    tier1_tokens, tier1_time = test_optimized_tier1(loader)
    tier1_query_tokens, tier1_query_time = test_optimized_tier1(loader, query="v2.2")

    test_session_cache()

    # Summary
    print("\n" + "=" * 60)
    print("📈 TOKEN SAVINGS SUMMARY")
    print("=" * 60)

    print(f"\nBaseline (full load): {baseline_tokens:,} tokens")
    print(
        f"Tier 0 (scan):        {int(tier0_tokens):,} tokens ({100*(1-tier0_tokens/baseline_tokens):.1f}% reduction)"
    )
    print(
        f"Tier 1 (balanced):    {int(tier1_tokens):,} tokens ({100*(1-tier1_tokens/baseline_tokens):.1f}% reduction)"
    )
    print(
        f"Tier 1 + query:       {int(tier1_query_tokens):,} tokens ({100*(1-tier1_query_tokens/baseline_tokens):.1f}% reduction)"
    )

    print("\n🎯 EFFECTIVENESS:")
    print(f"  • Best case (Tier 0):     {baseline_tokens/tier0_tokens:.1f}x more efficient")
    print(f"  • Typical use (Tier 1):   {baseline_tokens/tier1_tokens:.1f}x more efficient")
    print(f"  • Query mode:             {baseline_tokens/tier1_query_tokens:.1f}x more efficient")

    # Get optimization stats
    stats = loader.get_stats()
    print("\n📊 CACHE STATS:")
    print(f"  • Summary cache: {stats}")

    print("\n" + "=" * 60)
    print("✓ All tests complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
