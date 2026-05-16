"""
CODEX Pipeline v0.2.0 — Chunk → Embed → Graph

Five-stage pipeline that converts raw corpora (SD card transcripts, LIBRARY
documents, essay frameworks, session summaries, message board docs) into
semantic embeddings, graph clusters, and exportable knowledge artifacts.

Stages:
  1. extract  — Parse raw source files into normalized documents
  2. chunk    — Split documents into hierarchical chunks with speaker-turn preservation
  3. embed    — Generate vector embeddings for each chunk
  4. index    — Build graph, run Louvain clustering, detect communities
  5. export   — Produce sphere-nodes.json, Vaya Vida manifest, search indexes
"""
