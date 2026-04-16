-- WhiteMagic v21.1 Schema Migration
-- Adds galaxy namespace support and memory relationships
-- Generated: 2026-04-14

-- Add galaxy column to memories table for namespace isolation
ALTER TABLE memories ADD COLUMN galaxy TEXT DEFAULT 'default';

-- Create index for efficient galaxy-scoped queries
CREATE INDEX idx_memories_galaxy ON memories(galaxy);
CREATE INDEX idx_memories_galaxy_type ON memories(galaxy, memory_type);
CREATE INDEX idx_memories_galaxy_created ON memories(galaxy, created_at);

-- Create memory relationships table for enhanced graph connections
CREATE TABLE memory_relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,  -- 'parent', 'child', 'reference', 'contradicts', 'supports'
    strength REAL DEFAULT 0.5,  -- 0.0 to 1.0
    galaxy TEXT DEFAULT 'default',
    metadata TEXT,  -- JSON for additional properties
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate relationships
    UNIQUE(source_id, target_id, relation_type)
);

-- Create indexes for relationship queries
CREATE INDEX idx_relationships_source ON memory_relationships(source_id);
CREATE INDEX idx_relationships_target ON memory_relationships(target_id);
CREATE INDEX idx_relationships_type ON memory_relationships(relation_type);
CREATE INDEX idx_relationships_galaxy ON memory_relationships(galaxy);

-- Create query cache table for expensive operations
CREATE TABLE query_cache (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT,
    results TEXT,  -- JSON results
    galaxy TEXT DEFAULT 'default',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,  -- When cache entry should be invalidated
    hit_count INTEGER DEFAULT 0  -- Track cache effectiveness
);

CREATE INDEX idx_query_cache_expires ON query_cache(expires_at);
CREATE INDEX idx_query_cache_galaxy ON query_cache(galaxy);

-- Create trigger to auto-update memory_relationships.updated_at
CREATE TRIGGER trg_relationships_updated_at 
AFTER UPDATE ON memory_relationships
BEGIN
    UPDATE memory_relationships 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Migration metadata
INSERT OR REPLACE INTO schema_migrations (version, applied_at, description)
VALUES ('v21.1', datetime('now'), 'Add galaxy namespace and memory_relationships table');

-- Statistics for verification
SELECT 
    'memories with galaxy' as metric,
    COUNT(*) as count 
FROM memories 
WHERE galaxy IS NOT NULL;

SELECT 
    'galaxy distribution' as metric,
    galaxy,
    COUNT(*) as count 
FROM memories 
GROUP BY galaxy;
