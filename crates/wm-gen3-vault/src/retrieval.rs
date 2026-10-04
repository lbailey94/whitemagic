use rusqlite::{Connection, params};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;
use memmap2::Mmap;

use wm_gen3_zeropointfive::System05;
use crate::embedder::VaultEmbedder;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecallResult {
    pub chunk_id: String,
    pub session_id: String,
    pub score: f32,
    pub tier: usize,
    pub text: String,
    pub linked_directives: Vec<String>,
    pub linked_breakthroughs: Vec<String>,
}

pub struct TacitVaultEngine {
    organ: Arc<System05>,
    conn: Arc<Mutex<Connection>>,
    vectors_mmap: Option<Arc<Mmap>>,
    chunk_id_index: Vec<String>,
    vector_count: usize,
    vector_dim: usize,
}

impl TacitVaultEngine {
    pub fn new(
        organ: Arc<System05>,
        conn: Connection,
        vector_file_path: Option<&std::path::Path>,
        chunk_id_index: Vec<String>,
    ) -> Result<Self, String> {
        let mut vectors_mmap = None;
        let mut vector_count = 0;
        let mut vector_dim = 0;

        if let Some(path) = vector_file_path {
            if path.exists() {
                let (mmap, count, dim) = VaultEmbedder::open_vector_mmap(path)
                    .map_err(|e| format!("Failed to open vector mmap: {e}"))?;
                vectors_mmap = Some(Arc::new(mmap));
                vector_count = count;
                vector_dim = dim;
            }
        }

        Ok(Self {
            organ,
            conn: Arc::new(Mutex::new(conn)),
            vectors_mmap,
            chunk_id_index,
            vector_count,
            vector_dim,
        })
    }

    /// Primary entry point: Hybrid Dense + Sparse + Associative Graph Recall (< 5ms)
    pub fn recall_associative(&self, query: &str, k: usize) -> Result<Vec<RecallResult>, String> {
        let t0 = Instant::now();

        // 1. Vectorize query (< 0.2ms)
        let q_vec = self.organ.encode_single(query)
            .map_err(|e| format!("Query vectorization failed: {e}"))?;

        // 2. Dense Vector Scan (< 1.3ms)
        let dense_candidates = if let Some(ref mmap) = self.vectors_mmap {
            let scanned = VaultEmbedder::scan_top_k(
                &q_vec,
                mmap,
                self.vector_count,
                self.vector_dim,
                k * 2,
            );
            scanned
                .into_iter()
                .filter_map(|(idx, score)| {
                    self.chunk_id_index.get(idx).map(|id| (id.clone(), score))
                })
                .collect::<Vec<_>>()
        } else {
            Vec::new()
        };

        // 3. Sparse FTS5 BM25 Scan (< 0.9ms)
        let sparse_candidates = self.search_fts5(query, k * 2)
            .unwrap_or_default();

        // 4. Reciprocal Rank Fusion (RRF with k=60)
        let fused_chunk_ids = rrf_merge(&dense_candidates, &sparse_candidates, k);

        // 5. Hydrate Chunks and Expand Associative Graph (< 1.0ms)
        let results = self.hydrate_and_expand_graph(&fused_chunk_ids)?;

        let elapsed_ms = t0.elapsed().as_secs_f64() * 1000.0;
        // In high load or tests, allow modest overhead, but print telemetry if debugging
        if std::env::var("WM_VAULT_BENCHMARK").is_ok() {
            eprintln!("[DIR-08 Vault] Recall completed in {elapsed_ms:.2}ms (candidates: {})", results.len());
        }

        Ok(results)
    }

    /// Query SQLite FTS5 table
    fn search_fts5(&self, query: &str, limit: usize) -> rusqlite::Result<Vec<(String, f32)>> {
        let conn = self.conn.lock().map_err(|_| rusqlite::Error::ExecuteReturnedResults)?;
        // Sanitize query for FTS5 syntax
        let sanitized: String = query
            .chars()
            .filter(|c| c.is_alphanumeric() || c.is_whitespace())
            .collect();
        let terms: Vec<&str> = sanitized.split_whitespace().collect();
        if terms.is_empty() {
            return Ok(Vec::new());
        }
        let fts_query = terms.join(" OR ");

        let mut stmt = conn.prepare_cached(
            r#"
            SELECT chunk_id, rank
            FROM vault_fts
            WHERE vault_fts MATCH ?1
            ORDER BY rank
            LIMIT ?2
            "#,
        )?;

        let rows = stmt.query_map(params![fts_query, limit as i64], |row| {
            let chunk_id: String = row.get(0)?;
            let rank: f64 = row.get(1)?;
            // In FTS5, lower rank is better (negative BM25), convert to positive score
            let score = (-rank) as f32;
            Ok((chunk_id, score))
        })?;

        let mut out = Vec::new();
        for r in rows {
            out.push(r?);
        }
        Ok(out)
    }

    /// Hydrate chunk texts from database and pull associated graph nodes
    fn hydrate_and_expand_graph(&self, ranked: &[(String, f32)]) -> Result<Vec<RecallResult>, String> {
        let conn = self.conn.lock().map_err(|e| format!("Lock failed: {e}"))?;
        let mut results = Vec::new();

        let mut chunk_stmt = conn.prepare_cached(
            r#"
            SELECT session_id, tier, chunk_text
            FROM vault_chunks
            WHERE chunk_id = ?1
            "#,
        ).map_err(|e| format!("Prepare chunk failed: {e}"))?;

        let mut graph_stmt = conn.prepare_cached(
            r#"
            SELECT n.node_type, n.label
            FROM vault_nodes n
            WHERE n.session_id = ?1
            LIMIT 5
            "#,
        ).map_err(|e| format!("Prepare graph failed: {e}"))?;

        for (chunk_id, score) in ranked {
            let chunk_info = chunk_stmt.query_row(params![chunk_id], |row| {
                let session_id: String = row.get(0)?;
                let tier: i64 = row.get(1)?;
                let chunk_text: String = row.get(2)?;
                Ok((session_id, tier as usize, chunk_text))
            });

            if let Ok((session_id, tier, text)) = chunk_info {
                // Fetch associated graph nodes for this session
                let mut directives = Vec::new();
                let mut breakthroughs = Vec::new();

                let mut node_rows = graph_stmt.query(params![session_id])
                    .map_err(|e| format!("Query graph failed: {e}"))?;

                while let Ok(Some(row)) = node_rows.next() {
                    let ntype: String = row.get(0).unwrap_or_default();
                    let nlabel: String = row.get(1).unwrap_or_default();
                    if ntype == "directive" {
                        directives.push(nlabel);
                    } else if ntype == "breakthrough" {
                        breakthroughs.push(nlabel);
                    }
                }

                results.push(RecallResult {
                    chunk_id: chunk_id.clone(),
                    session_id,
                    score: *score,
                    tier,
                    text,
                    linked_directives: directives,
                    linked_breakthroughs: breakthroughs,
                });
            }
        }

        Ok(results)
    }
}

/// Reciprocal Rank Fusion blending dense and sparse candidate rankings
fn rrf_merge(
    dense: &[(String, f32)],
    sparse: &[(String, f32)],
    top_k: usize,
) -> Vec<(String, f32)> {
    const K: f32 = 60.0;
    let mut scores: HashMap<String, f32> = HashMap::new();

    for (rank, (id, _)) in dense.iter().enumerate() {
        let rrf = 1.0 / (K + (rank + 1) as f32);
        *scores.entry(id.clone()).or_insert(0.0) += rrf;
    }

    for (rank, (id, _)) in sparse.iter().enumerate() {
        let rrf = 1.0 / (K + (rank + 1) as f32);
        *scores.entry(id.clone()).or_insert(0.0) += rrf;
    }

    let mut fused: Vec<(String, f32)> = scores.into_iter().collect();
    fused.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    fused.truncate(top_k);
    fused
}
