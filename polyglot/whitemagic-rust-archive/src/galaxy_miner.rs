//! 🌌 Galaxy Pattern Miner - High-Performance Archive Analysis
//!
//! Rust implementation for mining patterns from galaxy archive DBs.
//! Handles 111K+ memories efficiently with parallel processing.

use pyo3::prelude::*;
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct AccessPattern {
    #[pyo3(get)]
    pub pattern_id: String,
    #[pyo3(get)]
    pub pattern_type: String,
    #[pyo3(get)]
    pub memory_ids: Vec<String>,
    #[pyo3(get)]
    pub frequency: i64,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub source_galaxy: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct SemanticCluster {
    #[pyo3(get)]
    pub cluster_id: String,
    #[pyo3(get)]
    pub memory_ids: Vec<String>,
    #[pyo3(get)]
    pub common_tags: Vec<String>,
    #[pyo3(get)]
    pub avg_importance: f64,
    #[pyo3(get)]
    pub size: usize,
}

/// Mine access patterns from a galaxy database
#[pyfunction]
pub fn mine_access_patterns(db_path: &str, min_frequency: i64) -> PyResult<Vec<AccessPattern>> {
    let conn = Connection::open(db_path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("DB open failed: {}", e))
    })?;

    let mut stmt = conn
        .prepare(
            "SELECT id, access_count, accessed_at 
         FROM memories 
         WHERE access_count >= ?1 
         AND memory_type != 'quarantined'
         ORDER BY access_count DESC 
         LIMIT 1000",
        )
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query failed: {}", e))
        })?;

    let mut memory_ids = Vec::new();
    let mut total_access = 0i64;
    let mut count = 0i64;

    let rows = stmt
        .query_map([min_frequency], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
        })
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query map failed: {}", e))
        })?;

    for (id, access_count) in rows.flatten() {
        memory_ids.push(id);
        total_access += access_count;
        count += 1;
    }

    if memory_ids.is_empty() {
        return Ok(Vec::new());
    }

    let avg_access = total_access / count.max(1);
    let confidence = (count as f64 / 100.0).min(1.0);
    let galaxy_name = Path::new(db_path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    Ok(vec![AccessPattern {
        pattern_id: format!("freq_access_{}", galaxy_name.replace(".db", "")),
        pattern_type: "frequent_access".to_string(),
        memory_ids,
        frequency: avg_access,
        confidence,
        source_galaxy: galaxy_name,
    }])
}

/// Mine cache candidates from a galaxy database
#[pyfunction]
pub fn mine_cache_candidates(
    db_path: &str,
    min_access: i64,
    min_importance: f64,
) -> PyResult<Vec<AccessPattern>> {
    let conn = Connection::open(db_path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("DB open failed: {}", e))
    })?;

    let mut stmt = conn
        .prepare(
            "SELECT id, access_count, importance 
         FROM memories 
         WHERE access_count >= ?1 
         AND importance >= ?2
         AND memory_type != 'quarantined'
         ORDER BY access_count * importance DESC 
         LIMIT 500",
        )
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query failed: {}", e))
        })?;

    let mut memory_ids = Vec::new();
    let mut total_access = 0i64;
    let mut total_importance = 0.0f64;
    let mut count = 0i64;

    let rows = stmt
        .query_map(rusqlite::params![min_access, min_importance], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, f64>(2)?,
            ))
        })
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query map failed: {}", e))
        })?;

    for (id, access_count, importance) in rows.flatten() {
        memory_ids.push(id);
        total_access += access_count;
        total_importance += importance;
        count += 1;
    }

    if memory_ids.is_empty() {
        return Ok(Vec::new());
    }

    let avg_access = total_access / count.max(1);
    let avg_importance = total_importance / count.max(1) as f64;
    let confidence = ((avg_access as f64 * avg_importance) / 10.0).min(1.0);
    let galaxy_name = Path::new(db_path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    Ok(vec![AccessPattern {
        pattern_id: format!("cache_candidates_{}", galaxy_name.replace(".db", "")),
        pattern_type: "cache_candidate".to_string(),
        memory_ids,
        frequency: avg_access,
        confidence,
        source_galaxy: galaxy_name,
    }])
}

/// Mine semantic clusters from a galaxy database
#[pyfunction]
pub fn mine_semantic_clusters(
    db_path: &str,
    min_cluster_size: usize,
) -> PyResult<Vec<SemanticCluster>> {
    let conn = Connection::open(db_path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("DB open failed: {}", e))
    })?;

    let mut stmt = conn
        .prepare(
            "SELECT m.id, GROUP_CONCAT(t.tag, ',') as tags, m.importance
         FROM memories m
         JOIN tags t ON m.id = t.memory_id
         WHERE m.memory_type != 'quarantined'
         GROUP BY m.id
         HAVING tags IS NOT NULL
         LIMIT 10000",
        )
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query failed: {}", e))
        })?;

    let mut tag_to_memories: HashMap<String, Vec<(String, f64)>> = HashMap::new();

    let rows = stmt
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, f64>(2)?,
            ))
        })
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query map failed: {}", e))
        })?;

    for (memory_id, tags_str, importance) in rows.flatten() {
        for tag in tags_str.split(',') {
            let tag = tag.trim();
            if !tag.is_empty() {
                tag_to_memories
                    .entry(tag.to_string())
                    .or_default()
                    .push((memory_id.clone(), importance));
            }
        }
    }

    let mut clusters = Vec::new();

    for (tag, memories) in tag_to_memories.iter() {
        if memories.len() >= min_cluster_size {
            let memory_ids: Vec<String> = memories.iter().map(|(id, _)| id.clone()).collect();
            let avg_importance =
                memories.iter().map(|(_, imp)| imp).sum::<f64>() / memories.len() as f64;

            clusters.push(SemanticCluster {
                cluster_id: format!("semantic_{}", tag),
                memory_ids,
                common_tags: vec![tag.clone()],
                avg_importance,
                size: memories.len(),
            });
        }
    }

    Ok(clusters)
}

/// Get database statistics quickly
#[pyfunction]
pub fn get_galaxy_stats(db_path: &str) -> PyResult<HashMap<String, i64>> {
    let conn = Connection::open(db_path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("DB open failed: {}", e))
    })?;

    let mut stats = HashMap::new();

    // Total memories
    let total: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM memories WHERE memory_type != 'quarantined'",
            [],
            |row| row.get(0),
        )
        .unwrap_or(0);
    stats.insert("total_memories".to_string(), total);

    // High access memories
    let high_access: i64 = conn.query_row(
        "SELECT COUNT(*) FROM memories WHERE access_count >= 10 AND memory_type != 'quarantined'",
        [],
        |row| row.get(0)
    ).unwrap_or(0);
    stats.insert("high_access_memories".to_string(), high_access);

    // High importance memories
    let high_importance: i64 = conn.query_row(
        "SELECT COUNT(*) FROM memories WHERE importance >= 0.7 AND memory_type != 'quarantined'",
        [],
        |row| row.get(0)
    ).unwrap_or(0);
    stats.insert("high_importance_memories".to_string(), high_importance);

    // Total tags
    let total_tags: i64 = conn
        .query_row("SELECT COUNT(DISTINCT tag) FROM tags", [], |row| row.get(0))
        .unwrap_or(0);
    stats.insert("total_tags".to_string(), total_tags);

    Ok(stats)
}

// ---------------------------------------------------------------------------
// Python module registration
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
pub fn galaxy_miner(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AccessPattern>()?;
    m.add_class::<SemanticCluster>()?;
    m.add_function(wrap_pyfunction!(mine_access_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(mine_cache_candidates, m)?)?;
    m.add_function(wrap_pyfunction!(mine_semantic_clusters, m)?)?;
    m.add_function(wrap_pyfunction!(get_galaxy_stats, m)?)?;
    Ok(())
}
