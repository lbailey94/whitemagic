"""Tiered backend system for WhiteMagic memory.

Tier 0: Per-galaxy SQLite (default, local-first, WAL mode)
Tier 1: DuckDB (analytical, columnar, cross-galaxy queries)
Tier 2: PostgreSQL (optional, localhost, true concurrency)
"""
