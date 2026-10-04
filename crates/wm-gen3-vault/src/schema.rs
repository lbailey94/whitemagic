use rusqlite::{Connection, Result};
use std::path::Path;

/// Open or initialize the companion tacit vault SQLite database.
pub fn open_vault_db<P: AsRef<Path>>(path: P) -> Result<Connection> {
    let conn = Connection::open(path)?;

    // Configure high-performance PRAGMAs
    conn.execute_batch(
        r#"
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA mmap_size = 268435456;
        PRAGMA temp_store = MEMORY;
        PRAGMA cache_size = -65536;
        PRAGMA foreign_keys = ON;
        "#,
    )?;

    init_vault_schema(&conn)?;
    Ok(conn)
}

/// Initialize the complete relational, graph, and FTS5 schema for the tacit vault.
pub fn init_vault_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        r#"
        -- Core Session Registry
        CREATE TABLE IF NOT EXISTS vault_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            project_id TEXT,
            time_created INTEGER NOT NULL,
            time_updated INTEGER NOT NULL,
            total_messages INTEGER NOT NULL,
            total_turns INTEGER NOT NULL,
            total_cost REAL,
            primary_domain TEXT,
            gestalt_digest TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_v_sessions_ts ON vault_sessions(time_created);
        CREATE INDEX IF NOT EXISTS idx_v_sessions_dom ON vault_sessions(primary_domain);

        -- Cleansed Normalized Turns
        CREATE TABLE IF NOT EXISTS vault_turns (
            turn_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            role TEXT NOT NULL,          -- 'user' | 'assistant' | 'system'
            turn_type TEXT NOT NULL,      -- 9 types: message, decision, breakthrough, question, answer, code_change, error, summary, context
            clean_text TEXT NOT NULL,
            importance REAL NOT NULL,     -- 0.0 to 1.0
            valence REAL DEFAULT 0.0,    -- -1.0 to 1.0
            time_created INTEGER NOT NULL,
            raw_message_id TEXT,
            FOREIGN KEY(session_id) REFERENCES vault_sessions(session_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_v_turns_sess_seq ON vault_turns(session_id, seq);
        CREATE INDEX IF NOT EXISTS idx_v_turns_type ON vault_turns(turn_type);
        CREATE INDEX IF NOT EXISTS idx_v_turns_importance ON vault_turns(importance);

        -- Multi-Resolution Indexable Chunks
        CREATE TABLE IF NOT EXISTS vault_chunks (
            chunk_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            tier INTEGER NOT NULL,        -- 0: Turn, 1: Dyad, 2: Episode, 3: Gestalt
            start_seq INTEGER NOT NULL,
            end_seq INTEGER NOT NULL,
            token_count INTEGER NOT NULL,
            content_hash TEXT NOT NULL,   -- SHA256 hex
            chunk_text TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            FOREIGN KEY(session_id) REFERENCES vault_sessions(session_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_v_chunks_sess ON vault_chunks(session_id);
        CREATE INDEX IF NOT EXISTS idx_v_chunks_tier ON vault_chunks(tier);

        -- SQLite FTS5 Full-Text Search Virtual Table
        CREATE VIRTUAL TABLE IF NOT EXISTS vault_fts USING fts5(
            chunk_id UNINDEXED,
            session_id UNINDEXED,
            tier UNINDEXED,
            chunk_text,
            tokenize='unicode61 remove_diacritics 2'
        );

        -- Dense Static Embeddings metadata table
        CREATE TABLE IF NOT EXISTS vault_embeddings (
            chunk_id TEXT PRIMARY KEY,
            model_id TEXT NOT NULL,
            dimension INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(chunk_id) REFERENCES vault_chunks(chunk_id) ON DELETE CASCADE
        );

        -- Associative Graph Nodes
        CREATE TABLE IF NOT EXISTS vault_nodes (
            node_id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,      -- 'directive' | 'problem' | 'breakthrough' | 'artifact' | 'concept'
            label TEXT NOT NULL,
            summary TEXT NOT NULL,
            session_id TEXT NOT NULL,
            chunk_id TEXT,
            time_created INTEGER NOT NULL,
            metadata TEXT,                -- JSON string
            FOREIGN KEY(session_id) REFERENCES vault_sessions(session_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_v_nodes_type ON vault_nodes(node_type);
        CREATE INDEX IF NOT EXISTS idx_v_nodes_sess ON vault_nodes(session_id);

        -- Associative Graph Edges
        CREATE TABLE IF NOT EXISTS vault_edges (
            edge_id TEXT PRIMARY KEY,
            src_id TEXT NOT NULL,
            dst_id TEXT NOT NULL,
            relation_kind TEXT NOT NULL,  -- 'causal' | 'supersedes' | 'associates'
            weight REAL NOT NULL DEFAULT 1.0,
            sign INTEGER NOT NULL DEFAULT 1,
            cost REAL NOT NULL DEFAULT 0.1,
            trust REAL NOT NULL DEFAULT 1.0,
            rule_id TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(src_id) REFERENCES vault_nodes(node_id) ON DELETE CASCADE,
            FOREIGN KEY(dst_id) REFERENCES vault_nodes(node_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_v_edges_src ON vault_edges(src_id);
        CREATE INDEX IF NOT EXISTS idx_v_edges_dst ON vault_edges(dst_id);
        CREATE INDEX IF NOT EXISTS idx_v_edges_kind ON vault_edges(relation_kind);
        "#,
    )?;
    Ok(())
}
