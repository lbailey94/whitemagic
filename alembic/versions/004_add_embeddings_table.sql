-- Add embeddings table for Tier 2 caching
-- Optional: Requires pgvector extension

-- Enable pgvector extension (run manually if needed)
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id VARCHAR(255) UNIQUE NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    content_hash VARCHAR(64) NOT NULL,
    model VARCHAR(100) NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_embeddings_memory_id ON memory_embeddings(memory_id);

-- Vector similarity index (IVFFlat)
-- CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON memory_embeddings
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE memory_embeddings IS 'Cached embeddings for semantic search (Tier 2)';
