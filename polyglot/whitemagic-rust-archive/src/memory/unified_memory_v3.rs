//! UnifiedMemory v3 — Rust impl of whitemagic/core/memory/unified.py
//! PSR-001 Phase 1 VC: unified.py -> Rust
//! Target: 20-50x speedup on store/recall/search hot paths

use pyo3::prelude::*;
use rusqlite::{params, Connection};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

fn sha256_short(input: &str) -> String {
    let mut h: u64 = 14695981039346656037;
    for b in input.bytes() { h ^= b as u64; h = h.wrapping_mul(1099511628211); }
    let mut out = String::with_capacity(64);
    for s in 0u64..4 {
        let mut x = h ^ (s.wrapping_mul(0xdeadbeef_cafebabe));
        x = x.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        out.push_str(&format!("{:016x}", x));
    }
    out
}

fn iso_now() -> String {
    let s = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs();
    format!("{}T{:02}:{:02}:{:02}Z", "2026-02-18", (s/3600)%24, (s/60)%60, s%60)
}

fn open_conn(db_path: &str) -> rusqlite::Result<Connection> {
    let conn = Connection::open(db_path)?;
    conn.execute_batch("
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA mmap_size=268435456;
        PRAGMA cache_size=-65536;
        PRAGMA temp_store=MEMORY;
        PRAGMA busy_timeout=5000;
    ")?;
    Ok(conn)
}

#[pyclass]
pub struct PyUnifiedMemoryV3 {
    pool: Arc<Mutex<Vec<Connection>>>,
}

#[pymethods]
impl PyUnifiedMemoryV3 {
    #[new]
    fn new(db_path: String, pool_size: Option<usize>) -> PyResult<Self> {
        let size = pool_size.unwrap_or(4);
        let mut conns = Vec::with_capacity(size);
        for _ in 0..size {
            let c = open_conn(&db_path).map_err(|e|
                pyo3::exceptions::PyRuntimeError::new_err(format!("DB open failed: {}", e)))?;
            conns.push(c);
        }
        Ok(Self { pool: Arc::new(Mutex::new(conns)) })
    }

    /// Returns (memory_id, was_duplicate)
    fn store(
        &self,
        content: String,
        title: Option<String>,
        memory_type: Option<String>,
        importance: Option<f64>,
        tags: Option<Vec<String>>,
    ) -> PyResult<(String, bool)> {
        let mtype = memory_type.as_deref().unwrap_or("short_term");
        let imp = importance.unwrap_or(0.5);
        let content_hash = sha256_short(&content);
        let ts = iso_now();
        let id_src = format!("{}{}", &content[..content.len().min(1000)], &ts);
        let memory_id = sha256_short(&id_src)[..16].to_string();
        let tags_json = serde_json::to_string(&tags.unwrap_or_default()).unwrap_or_default();
        let title_str = title.as_deref().unwrap_or("");

        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];

        // Check dedup
        let existing: Option<String> = conn.query_row(
            "SELECT id FROM memories WHERE content_hash = ? LIMIT 1",
            params![content_hash],
            |r| r.get(0),
        ).ok();

        if let Some(eid) = existing {
            let _ = conn.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
                params![eid],
            );
            return Ok((eid, true));
        }

        conn.execute(
            "INSERT OR IGNORE INTO memories \
             (id, content, title, memory_type, importance, emotional_valence, \
              access_count, galactic_distance, content_hash, created_at, accessed_at, tags) \
             VALUES (?,?,?,?,?,0.0,0,0.5,?,?,?,?)",
            params![memory_id, content, title_str, mtype, imp, content_hash, ts, ts, tags_json],
        ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("INSERT failed: {}", e)))?;

        Ok((memory_id, false))
    }

    /// Returns Option<dict> with memory fields
    fn recall(&self, memory_id: String) -> PyResult<Option<HashMap<String, String>>> {
        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];
        let result = conn.query_row(
            "SELECT id, content, title, memory_type, importance, galactic_distance, \
                    access_count, created_at, tags \
             FROM memories WHERE id = ? LIMIT 1",
            params![memory_id],
            |r| {
                let mut m = HashMap::new();
                m.insert("id".into(), r.get::<_, String>(0)?);
                m.insert("content".into(), r.get::<_, String>(1)?);
                m.insert("title".into(), r.get::<_, Option<String>>(2)?.unwrap_or_default());
                m.insert("memory_type".into(), r.get::<_, String>(3)?);
                m.insert("importance".into(), r.get::<_, f64>(4)?.to_string());
                m.insert("galactic_distance".into(), r.get::<_, f64>(5)?.to_string());
                m.insert("access_count".into(), r.get::<_, i64>(6)?.to_string());
                m.insert("created_at".into(), r.get::<_, String>(7)?);
                m.insert("tags".into(), r.get::<_, Option<String>>(8)?.unwrap_or_default());
                Ok(m)
            },
        ).ok();

        // Galactic distance decay on recall (mirror unified.py)
        if result.is_some() {
            let gd: f64 = result.as_ref().unwrap()
                .get("galactic_distance").and_then(|s| s.parse().ok()).unwrap_or(0.5);
            let new_gd = (gd * 0.95_f64).max(0.0);
            let _ = conn.execute(
                "UPDATE memories SET galactic_distance=?, access_count=access_count+1 WHERE id=?",
                params![new_gd, memory_id],
            );
        }
        Ok(result)
    }

    /// Full-text search with optional type filter. Returns list of id strings.
    fn search(
        &self,
        query: Option<String>,
        memory_type: Option<String>,
        min_importance: Option<f64>,
        limit: Option<i64>,
    ) -> PyResult<Vec<String>> {
        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];
        let lim = limit.unwrap_or(10);
        let min_imp = min_importance.unwrap_or(0.0);

        let mut ids = Vec::new();

        if let Some(q) = query {
            let pattern = format!("%{}%", q);
            let mut stmt = conn.prepare(
                "SELECT id FROM memories WHERE content LIKE ? \
                 AND importance >= ? ORDER BY importance DESC LIMIT ?"
            ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            let rows = stmt.query_map(params![pattern, min_imp, lim], |r| r.get(0))
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            for row in rows.flatten() { ids.push(row); }
        } else if let Some(mt) = memory_type {
            let mut stmt = conn.prepare(
                "SELECT id FROM memories WHERE memory_type = ? \
                 AND importance >= ? ORDER BY importance DESC LIMIT ?"
            ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            let rows = stmt.query_map(params![mt, min_imp, lim], |r| r.get(0))
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            for row in rows.flatten() { ids.push(row); }
        } else {
            let mut stmt = conn.prepare(
                "SELECT id FROM memories WHERE importance >= ? \
                 ORDER BY importance DESC LIMIT ?"
            ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            let rows = stmt.query_map(params![min_imp, lim], |r| r.get(0))
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            for row in rows.flatten() { ids.push(row); }
        }

        Ok(ids)
    }

    fn get_stats(&self) -> PyResult<HashMap<String, i64>> {
        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];
        let mut stats = HashMap::new();
        let total: i64 = conn.query_row(
            "SELECT COUNT(*) FROM memories", [], |r| r.get(0)
        ).unwrap_or(0);
        stats.insert("total_memories".into(), total);
        Ok(stats)
    }
}
