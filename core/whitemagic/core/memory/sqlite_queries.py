"""SQL query constants extracted from sqlite_backend.py (PSR-011)."""

FTS_SEARCH_QUERY = """
    SELECT m.id, m.title, m.content, m.importance,
           bm25(memories_fts, 10.0, 1.0, 5.0) as rank
    FROM memories_fts JOIN memories m ON memories_fts.rowid = m.rowid
    WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?
"""

STORE_MEMORY_QUERY = """
    INSERT OR REPLACE INTO memories
    (id, title, content, importance, memory_type, tags, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

GET_ASSOCIATIONS_QUERY = """
    SELECT a.target_id, a.association_type, a.strength, m.title
    FROM associations a JOIN memories m ON a.target_id = m.id
    WHERE a.source_id = ? ORDER BY a.strength DESC LIMIT ?
"""

VECTOR_SEARCH_QUERY = """
    SELECT memory_id, embedding FROM embeddings
    WHERE memory_id IN (SELECT id FROM memories WHERE memory_type != 'quarantined')
"""
