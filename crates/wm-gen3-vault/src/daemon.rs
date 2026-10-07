use rusqlite::params;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

use crate::chunker::Chunker;
use crate::embedder::VaultEmbedder;
use crate::extractor::OpencodeExtractor;
use crate::graph::CausalGraphBuilder;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct VaultSyncState {
    pub last_synced_session_time: i64,
    pub last_synced_message_time: i64,
    pub total_chunks_indexed: usize,
    pub total_nodes_indexed: usize,
    pub total_edges_indexed: usize,
}

pub struct VaultDaemon {
    opencode_path: PathBuf,
    vault_db_path: PathBuf,
    vector_file_path: PathBuf,
    state_file_path: PathBuf,
    embedder: Option<VaultEmbedder>,
}

impl VaultDaemon {
    pub fn new<P: AsRef<Path>>(
        opencode_path: P,
        vault_dir: P,
        embedder: Option<VaultEmbedder>,
    ) -> Self {
        let opencode_path = opencode_path.as_ref().to_path_buf();
        let vault_dir = vault_dir.as_ref();
        let vault_db_path = vault_dir.join("tacit_vault.db");
        let vector_file_path = vault_dir.join("vault_vectors.bin");
        let state_file_path = vault_dir.join("sync_state.json");

        Self {
            opencode_path,
            vault_db_path,
            vector_file_path,
            state_file_path,
            embedder,
        }
    }

    /// Load or initialize persistent sync state
    pub fn load_state(&self) -> VaultSyncState {
        if let Ok(bytes) = std::fs::read(&self.state_file_path) {
            serde_json::from_slice(&bytes).unwrap_or_default()
        } else {
            VaultSyncState::default()
        }
    }

    /// Save state file atomically
    pub fn save_state(&self, state: &VaultSyncState) -> std::io::Result<()> {
        let json = serde_json::to_vec_pretty(state)?;
        std::fs::write(&self.state_file_path, json)
    }

    /// Run an incremental sync pass over opencode.db
    pub fn run_sync_pass(&self, max_sessions: Option<usize>) -> Result<VaultSyncState, String> {
        let mut state = self.load_state();
        let extractor = OpencodeExtractor::open(&self.opencode_path)
            .map_err(|e| format!("Failed to open opencode.db: {e}"))?;

        let mut vault_conn = crate::schema::open_vault_db(&self.vault_db_path)
            .map_err(|e| format!("Failed to open vault db: {e}"))?;

        let all_sessions = extractor
            .list_sessions()
            .map_err(|e| format!("Failed to list sessions: {e}"))?;

        // Filter sessions newer than last_synced_session_time
        let mut pending_sessions: Vec<_> = all_sessions
            .into_iter()
            .filter(|s| s.time_created >= state.last_synced_session_time)
            .collect();

        if let Some(limit) = max_sessions {
            pending_sessions.truncate(limit);
        }

        let mut all_new_chunks = Vec::new();

        for raw_sess in &pending_sessions {
            let turns = extractor
                .extract_session_turns(&raw_sess.id)
                .unwrap_or_default();

            if turns.is_empty() {
                continue;
            }

            // Record session metadata
            let _ = vault_conn.execute(
                r#"
                INSERT OR REPLACE INTO vault_sessions
                (session_id, title, project_id, time_created, time_updated, total_messages, total_turns, total_cost, primary_domain, gestalt_digest)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)
                "#,
                params![
                    raw_sess.id,
                    raw_sess.title,
                    raw_sess.project_id,
                    raw_sess.time_created,
                    raw_sess.time_updated,
                    raw_sess.tokens_input + raw_sess.tokens_output,
                    turns.len() as i64,
                    raw_sess.cost,
                    "general",
                    ""
                ],
            );

            // Chunk turns
            let chunks = Chunker::chunk_session(&raw_sess.id, &raw_sess.title, &turns);

            // Mine causal graph
            let (nodes, edges) = CausalGraphBuilder::mine_session_graph(&raw_sess.id, &turns);
            let _ = CausalGraphBuilder::persist_graph(&mut vault_conn, &nodes, &edges);
            state.total_nodes_indexed += nodes.len();
            state.total_edges_indexed += edges.len();

            // Insert chunks & FTS5
            let tx = vault_conn
                .transaction()
                .map_err(|e| format!("TX error: {e}"))?;
            {
                let mut chunk_stmt = tx.prepare_cached(
                    r#"
                    INSERT OR REPLACE INTO vault_chunks
                    (chunk_id, session_id, tier, start_seq, end_seq, token_count, content_hash, chunk_text, time_created)
                    VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
                    "#,
                ).map_err(|e| format!("Prepare chunk error: {e}"))?;

                let mut fts_stmt = tx
                    .prepare_cached(
                        r#"
                    INSERT INTO vault_fts (chunk_id, session_id, tier, chunk_text)
                    VALUES (?1, ?2, ?3, ?4)
                    "#,
                    )
                    .map_err(|e| format!("Prepare fts error: {e}"))?;

                for chunk in &chunks {
                    chunk_stmt
                        .execute(params![
                            chunk.chunk_id,
                            chunk.session_id,
                            chunk.tier as i64,
                            chunk.start_seq,
                            chunk.end_seq,
                            chunk.token_count as i64,
                            chunk.content_hash,
                            chunk.chunk_text,
                            chunk.time_created
                        ])
                        .map_err(|e| format!("Exec chunk: {e}"))?;

                    fts_stmt
                        .execute(params![
                            chunk.chunk_id,
                            chunk.session_id,
                            chunk.tier as i64,
                            chunk.chunk_text
                        ])
                        .map_err(|e| format!("Exec fts: {e}"))?;
                }
            }
            tx.commit().map_err(|e| format!("Commit error: {e}"))?;

            all_new_chunks.extend(chunks);

            if raw_sess.time_created > state.last_synced_session_time {
                state.last_synced_session_time = raw_sess.time_created;
            }
        }

        // Batch encode vectors if embedder is available
        if let Some(ref embedder) = self.embedder {
            if !all_new_chunks.is_empty() {
                let texts: Vec<String> = all_new_chunks
                    .iter()
                    .map(|c| c.chunk_text.clone())
                    .collect();
                if let Ok(vectors) = embedder.encode_batch(&texts) {
                    let _ = VaultEmbedder::write_vector_file(
                        &self.vector_file_path,
                        &vectors,
                        embedder.dimension(),
                    );
                }
            }
        }

        state.total_chunks_indexed += all_new_chunks.len();
        let _ = self.save_state(&state);

        Ok(state)
    }
}
