//! SQLite Accelerator — High-performance batch operations for WhiteMagic memory DB
//!
//! Accelerates the hot paths in Python's `sqlite_backend.py`:
//! - Batch galactic distance updates (107K memories)
//! - Batch FTS search with galactic weighting
//! - Batch memory stats aggregation
//! - Batch tag operations
//!
//! Uses rusqlite directly for zero-copy row iteration and prepared
//! statement caching. Connection pooling via r2d2 is NOT used here
//! because we operate on the same DB file as Python — instead we open
//! a single WAL-mode connection per call and close it promptly.
//!
//! Note: This does NOT replace Python's SQLiteBackend class. It provides
//! parallel acceleration functions that Python calls for batch operations.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Open a WAL-mode SQLite connection with performance pragmas
fn open_db(db_path: &str) -> Result<rusqlite::Connection, String> {
    let conn = rusqlite::Connection::open(db_path)
        .map_err(|e| format!("SQLite open error: {}", e))?;
    conn.execute_batch(
        "PRAGMA journal_mode = WAL;
         PRAGMA synchronous = NORMAL;
         PRAGMA busy_timeout = 5000;
         PRAGMA cache_size = -16384;"  // 16MB cache
    ).map_err(|e| format!("PRAGMA error: {}", e))?;
    Ok(conn)
}

/// Open a read-only SQLite connection with minimal pragmas.
/// Skips WAL mode switch (reads work fine on WAL-mode DBs without setting it).
/// This avoids the expensive PRAGMA journal_mode = WAL roundtrip.
fn open_db_readonly(db_path: &str) -> Result<rusqlite::Connection, String> {
    let conn = rusqlite::Connection::open_with_flags(
        db_path,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY | rusqlite::OpenFlags::SQLITE_OPEN_NO_MUTEX,
    ).map_err(|e| format!("SQLite open readonly error: {}", e))?;
    conn.execute_batch(
        "PRAGMA busy_timeout = 5000;
         PRAGMA cache_size = -16384;"
    ).map_err(|e| format!("PRAGMA error: {}", e))?;
    Ok(conn)
}

/// Update galactic distances for a batch of memories.
/// Much faster than Python's one-at-a-time UPDATE loop.
///
/// Input: JSON array of {"id": str, "galactic_distance": f64, "retention_score": f64}
#[pyfunction]
pub fn sqlite_batch_update_galactic(
    db_path: &str,
    updates_json: &str,
) -> PyResult<String> {
    #[derive(Deserialize)]
    struct GalacticUpdate {
        id: String,
        galactic_distance: f64,
        retention_score: f64,
    }

    let updates: Vec<GalacticUpdate> = serde_json::from_str(updates_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse: {}", e)))?;

    let conn = open_db(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;

    let tx = conn.unchecked_transaction()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Transaction: {}", e)))?;

    {
        let mut stmt = tx.prepare_cached(
            "UPDATE memories SET galactic_distance = ?1, retention_score = ?2, last_retention_sweep = datetime('now') WHERE id = ?3"
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare: {}", e)))?;

        for u in &updates {
            stmt.execute(rusqlite::params![u.galactic_distance, u.retention_score, u.id])
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Execute: {}", e)))?;
        }
    }

    tx.commit()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Commit: {}", e)))?;

    #[derive(Serialize)]
    struct BatchResult { updated: usize }
    serde_json::to_string(&BatchResult { updated: updates.len() })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON: {}", e)))
}

/// Apply decay drift to all unprotected memories: distance += drift_amount.
/// Clamps to [0.0, 1.0]. Returns count of affected rows.
#[pyfunction]
pub fn sqlite_decay_drift(
    db_path: &str,
    drift_amount: f64,
    max_distance: f64,
) -> PyResult<String> {
    let conn = open_db(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;

    let affected = conn.execute(
        "UPDATE memories SET galactic_distance = MIN(?1, galactic_distance + ?2) WHERE is_protected = 0 AND galactic_distance < ?1",
        rusqlite::params![max_distance, drift_amount],
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Execute: {}", e)))?;

    #[derive(Serialize)]
    struct DriftResult { affected: usize, drift_amount: f64 }
    serde_json::to_string(&DriftResult { affected, drift_amount })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON: {}", e)))
}

#[derive(Serialize)]
struct SearchResult {
    id: String,
    title: String,
    content_preview: String,
    importance: f64,
    galactic_distance: f64,
    memory_type: String,
    score: f64,
}

/// Fast FTS5 search with galactic distance weighting.
/// Returns JSON array of SearchResult sorted by weighted relevance.
#[pyfunction]
pub fn sqlite_fts_search(
    db_path: &str,
    query: &str,
    limit: usize,
    min_importance: f64,
) -> PyResult<String> {
    let conn = open_db_readonly(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;

    // Build FTS query: multi-word → phrase OR individual keywords
    let fts_query = if query.contains(' ') && !query.starts_with('"') {
        let keywords: Vec<&str> = query.split_whitespace().collect();
        format!("\"{}\" OR {}", query, keywords.join(" OR "))
    } else {
        query.to_string()
    };

    let mut stmt = conn.prepare_cached(
        "SELECT m.id, m.title, SUBSTR(m.content, 1, 200) as content_preview,
                m.importance, COALESCE(m.galactic_distance, 0.5) as galactic_distance,
                m.memory_type,
                (ABS(fts.rank) * (0.5 + COALESCE(m.galactic_distance, 0.5))) as score
         FROM memories m
         JOIN (
             SELECT id, rank FROM memories_fts WHERE memories_fts MATCH ?1
             ORDER BY rank LIMIT ?2
         ) fts ON m.id = fts.id
         WHERE m.importance >= ?3
         ORDER BY score ASC, m.importance DESC
         LIMIT ?4"
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare: {}", e)))?;

    let results: Vec<SearchResult> = stmt.query_map(
        rusqlite::params![fts_query, limit * 3, min_importance, limit],
        |row| {
            Ok(SearchResult {
                id: row.get(0)?,
                title: row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                content_preview: row.get::<_, Option<String>>(2)?.unwrap_or_default(),
                importance: row.get(3)?,
                galactic_distance: row.get(4)?,
                memory_type: row.get::<_, Option<String>>(5)?.unwrap_or_default(),
                score: row.get(6)?,
            })
        }
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query: {}", e)))?
    .filter_map(|r| r.ok())
    .collect();

    serde_json::to_string(&results)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON: {}", e)))
}

#[derive(Serialize)]
struct ZoneStats {
    total: usize,
    core: usize,       // 0.0 - 0.15
    inner_rim: usize,  // 0.15 - 0.40
    mid_band: usize,   // 0.40 - 0.65
    outer_rim: usize,  // 0.65 - 0.85
    far_edge: usize,   // 0.85 - 1.0
    protected: usize,
    avg_importance: f64,
    avg_galactic_distance: f64,
}

/// Get galactic zone distribution stats from the database.
#[pyfunction]
pub fn sqlite_zone_stats(db_path: &str) -> PyResult<String> {
    let conn = open_db_readonly(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;

    let stats = conn.query_row(
        "SELECT
            COUNT(*) as total,
            SUM(CASE WHEN COALESCE(galactic_distance, 0.5) < 0.15 THEN 1 ELSE 0 END) as core,
            SUM(CASE WHEN COALESCE(galactic_distance, 0.5) >= 0.15 AND COALESCE(galactic_distance, 0.5) < 0.40 THEN 1 ELSE 0 END) as inner_rim,
            SUM(CASE WHEN COALESCE(galactic_distance, 0.5) >= 0.40 AND COALESCE(galactic_distance, 0.5) < 0.65 THEN 1 ELSE 0 END) as mid_band,
            SUM(CASE WHEN COALESCE(galactic_distance, 0.5) >= 0.65 AND COALESCE(galactic_distance, 0.5) < 0.85 THEN 1 ELSE 0 END) as outer_rim,
            SUM(CASE WHEN COALESCE(galactic_distance, 0.5) >= 0.85 THEN 1 ELSE 0 END) as far_edge,
            SUM(CASE WHEN is_protected = 1 THEN 1 ELSE 0 END) as protected,
            AVG(importance) as avg_importance,
            AVG(COALESCE(galactic_distance, 0.5)) as avg_galactic_distance
         FROM memories",
        [],
        |row| {
            Ok(ZoneStats {
                total: row.get::<_, i64>(0)? as usize,
                core: row.get::<_, i64>(1)? as usize,
                inner_rim: row.get::<_, i64>(2)? as usize,
                mid_band: row.get::<_, i64>(3)? as usize,
                outer_rim: row.get::<_, i64>(4)? as usize,
                far_edge: row.get::<_, i64>(5)? as usize,
                protected: row.get::<_, i64>(6)? as usize,
                avg_importance: row.get::<_, f64>(7).unwrap_or(0.0),
                avg_galactic_distance: row.get::<_, f64>(8).unwrap_or(0.5),
            })
        }
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query: {}", e)))?;

    serde_json::to_string(&stats)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON: {}", e)))
}

#[derive(Serialize)]
struct MemoryExport {
    id: String,
    content: String,
    importance: f64,
    galactic_distance: f64,
    access_count: i64,
    tags: Vec<String>,
}

/// Export memories for batch processing (association mining, consolidation).
/// Returns JSON array of lightweight memory records.
#[pyfunction]
pub fn sqlite_export_for_mining(
    db_path: &str,
    max_distance: f64,
    min_importance: f64,
    limit: usize,
) -> PyResult<String> {
    let conn = open_db_readonly(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;

    // Fetch memories
    let mut stmt = conn.prepare_cached(
        "SELECT id, content, importance, COALESCE(galactic_distance, 0.5), COALESCE(access_count, 0)
         FROM memories
         WHERE COALESCE(galactic_distance, 0.5) <= ?1 AND importance >= ?2
         ORDER BY importance DESC
         LIMIT ?3"
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare: {}", e)))?;

    let memories: Vec<(String, String, f64, f64, i64)> = stmt.query_map(
        rusqlite::params![max_distance, min_importance, limit],
        |row| Ok((row.get(0)?, row.get::<_, Option<String>>(1)?.unwrap_or_default(), row.get(2)?, row.get(3)?, row.get(4)?))
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query: {}", e)))?
    .filter_map(|r| r.ok())
    .collect();

    // Fetch tags for all matching memories
    let memory_ids: Vec<&str> = memories.iter().map(|m| m.0.as_str()).collect();

    let mut tag_stmt = conn.prepare_cached(
        "SELECT memory_id, tag FROM tags WHERE memory_id = ?1"
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare tags: {}", e)))?;

    let mut tag_map: std::collections::HashMap<String, Vec<String>> = std::collections::HashMap::new();
    for id in &memory_ids {
        if let Ok(rows) = tag_stmt.query_map(rusqlite::params![id], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        }) {
            for row in rows.filter_map(|r| r.ok()) {
                tag_map.entry(row.0).or_default().push(row.1);
            }
        }
    }

    let exports: Vec<MemoryExport> = memories.into_iter().map(|(id, content, importance, gd, ac)| {
        let tags = tag_map.remove(&id).unwrap_or_default();
        MemoryExport { id, content, importance, galactic_distance: gd, access_count: ac, tags }
    }).collect();

    serde_json::to_string(&exports)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON: {}", e)))
}

/// Hybrid search result combining FTS5 rank + cosine similarity + galactic weighting.
#[derive(Serialize)]
struct HybridSearchResult {
    id: String,
    title: String,
    content_preview: String,
    importance: f64,
    galactic_distance: f64,
    memory_type: String,
    fts_score: f64,
    cosine_score: f64,
    combined_score: f64,
}

/// Hybrid search: FTS5 full-text + embedding cosine similarity in one call.
///
/// This eliminates the Python N+1 pattern where:
///   1. Python runs FTS5 query → gets IDs
///   2. Python loads embeddings for each ID (N queries)
///   3. Python computes cosine similarity (Python loop or numpy)
///   4. Python combines scores
///
/// Instead, Rust does all 4 steps in one call with zero Python overhead.
///
/// Args:
///   db_path: path to SQLite database
///   query: FTS5 search query
///   query_embedding: flat f32 query embedding (dim floats)
///   dim: embedding dimension (e.g. 384)
///   limit: max results
///   min_importance: minimum importance filter
///   fts_weight: weight for FTS score (default 0.4)
///   cosine_weight: weight for cosine score (default 0.4)
///   galactic_weight: weight for galactic distance (default 0.2)
///
/// Returns: JSON array of HybridSearchResult sorted by combined_score DESC
#[pyfunction]
pub fn sqlite_hybrid_search(
    db_path: &str,
    query: &str,
    query_embedding: Vec<f32>,
    dim: usize,
    limit: usize,
    min_importance: f64,
    fts_weight: f64,
    cosine_weight: f64,
    galactic_weight: f64,
) -> PyResult<String> {
    if query_embedding.len() != dim || dim == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("query_embedding len {} != dim {}", query_embedding.len(), dim)
        ));
    }

    let conn = open_db_readonly(db_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;

    // Step 1: FTS5 search to get candidate IDs + ranks
    let fts_query = if query.contains(' ') && !query.starts_with('"') {
        let keywords: Vec<&str> = query.split_whitespace().collect();
        format!("\"{}\" OR {}", query, keywords.join(" OR "))
    } else {
        query.to_string()
    };

    // Fetch FTS candidates with memory metadata (fetch 3x limit for cosine re-ranking)
    let fts_limit = (limit * 3).max(50);
    let mut stmt = conn.prepare_cached(
        "SELECT m.id, m.title, SUBSTR(m.content, 1, 200) as content_preview,
                m.importance, COALESCE(m.galactic_distance, 0.5) as galactic_distance,
                m.memory_type,
                ABS(fts.rank) as fts_rank
         FROM memories m
         JOIN (
             SELECT id, rank FROM memories_fts WHERE memories_fts MATCH ?1
             ORDER BY rank LIMIT ?2
         ) fts ON m.id = fts.id
         WHERE m.importance >= ?3
         ORDER BY fts.rank ASC
         LIMIT ?4"
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare FTS: {}", e)))?;

    let candidates: Vec<(String, String, String, f64, f64, String, f64)> = stmt.query_map(
        rusqlite::params![fts_query, fts_limit, min_importance, fts_limit],
        |row| {
            Ok((
                row.get(0)?,
                row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                row.get::<_, Option<String>>(2)?.unwrap_or_default(),
                row.get(3)?,
                row.get(4)?,
                row.get::<_, Option<String>>(5)?.unwrap_or_default(),
                row.get::<_, f64>(6).unwrap_or(0.0),
            ))
        }
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("FTS query: {}", e)))?
    .filter_map(|r| r.ok())
    .collect();

    if candidates.is_empty() {
        return Ok("[]".to_string());
    }

    // Step 2: Load embeddings for all candidate IDs in one query
    let candidate_ids: Vec<&str> = candidates.iter().map(|c| c.0.as_str()).collect();
    let placeholders: Vec<String> = (0..candidate_ids.len()).map(|_| "?".to_string()).collect();
    let placeholder_str = placeholders.join(",");

    let sql = format!(
        "SELECT memory_id, embedding FROM memory_embeddings WHERE memory_id IN ({})",
        placeholder_str
    );

    let mut embed_stmt = conn.prepare(&sql)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare embeddings: {}", e)))?;

    // Build params for IN clause
    let params: Vec<&dyn rusqlite::ToSql> = candidate_ids.iter().map(|id| id as &dyn rusqlite::ToSql).collect();

    let mut embed_map: std::collections::HashMap<String, Vec<f32>> = std::collections::HashMap::new();
    let embed_rows = embed_stmt.query_map(params.as_slice(), |row| {
        let id: String = row.get(0)?;
        let blob: Vec<u8> = row.get(1)?;
        Ok((id, blob))
    }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Embedding query: {}", e)))?;

    for row in embed_rows.filter_map(|r| r.ok()) {
        let (id, blob) = row;
        // Unpack f32 from blob (little-endian)
        let embedding: Vec<f32> = blob.chunks_exact(4)
            .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
            .collect();
        embed_map.insert(id, embedding);
    }

    // Step 3: Compute cosine similarity for each candidate that has an embedding
    // Normalize query embedding
    let q_norm: f32 = query_embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
    let q_normalized: Vec<f32> = if q_norm > 1e-8 {
        query_embedding.iter().map(|x| x / q_norm).collect()
    } else {
        query_embedding.clone()
    };

    // Find max FTS rank for normalization
    let max_fts = candidates.iter().map(|c| c.6).fold(0.0f64, f64::max).max(1e-8);

    let mut results: Vec<HybridSearchResult> = Vec::new();

    for (id, title, content_preview, importance, galactic_distance, memory_type, fts_rank) in &candidates {
        let cosine_score = if let Some(embedding) = embed_map.get(id) {
            if embedding.len() == dim {
                // Cosine similarity (dot product of normalized vectors)
                let e_norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
                if e_norm > 1e-8 {
                    let dot: f32 = q_normalized.iter()
                        .zip(embedding.iter())
                        .map(|(q, e)| q * (e / e_norm))
                        .sum();
                    dot as f64
                } else {
                    0.0
                }
            } else {
                0.0
            }
        } else {
            // No embedding — use 0.5 as neutral cosine score
            0.5
        };

        // Normalize FTS score to [0, 1]
        let fts_score_norm = (*fts_rank / max_fts).min(1.0);

        // Combined score: weighted sum of FTS, cosine, and galactic proximity (1 - distance)
        let galactic_proximity = 1.0 - *galactic_distance;
        let combined = fts_weight * fts_score_norm
            + cosine_weight * cosine_score
            + galactic_weight * galactic_proximity;

        results.push(HybridSearchResult {
            id: id.clone(),
            title: title.clone(),
            content_preview: content_preview.clone(),
            importance: *importance,
            galactic_distance: *galactic_distance,
            memory_type: memory_type.clone(),
            fts_score: fts_score_norm,
            cosine_score,
            combined_score: combined,
        });
    }

    // Step 4: Sort by combined score descending and take top `limit`
    results.sort_by(|a, b| b.combined_score.partial_cmp(&a.combined_score).unwrap_or(std::cmp::Ordering::Equal));
    results.truncate(limit);

    serde_json::to_string(&results)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON: {}", e)))
}

#[cfg(test)]
mod tests {
    #[allow(unused_imports)]
    use super::*;

    #[test]
    fn test_open_db_memory() {
        // Test with in-memory DB
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, importance REAL DEFAULT 0.5,
                                    galactic_distance REAL DEFAULT 0.5, is_protected INTEGER DEFAULT 0,
                                    access_count INTEGER DEFAULT 0, memory_type TEXT DEFAULT 'SHORT_TERM',
                                    title TEXT);
             INSERT INTO memories (id, content, importance, galactic_distance) VALUES ('m1', 'test', 0.8, 0.3);
             INSERT INTO memories (id, content, importance, galactic_distance) VALUES ('m2', 'hello', 0.5, 0.7);"
        ).unwrap();

        // Test zone counting
        let total: i64 = conn.query_row("SELECT COUNT(*) FROM memories", [], |r| r.get(0)).unwrap();
        assert_eq!(total, 2);
    }

    #[test]
    fn test_fts_query_building() {
        let query = "memory consolidation";
        let fts = if query.contains(' ') && !query.starts_with('"') {
            let kws: Vec<&str> = query.split_whitespace().collect();
            format!("\"{}\" OR {}", query, kws.join(" OR "))
        } else {
            query.to_string()
        };
        assert_eq!(fts, "\"memory consolidation\" OR memory OR consolidation");
    }
}
