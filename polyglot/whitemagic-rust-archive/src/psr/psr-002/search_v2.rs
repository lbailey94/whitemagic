//! Full-text search with BM25 ranking
//! Migrated from Python with performance optimizations

use pyo3::prelude::*;
use rusqlite::Connection;
use std::sync::{Arc, Mutex};
use rayon::prelude::*;

#[pyclass]
pub struct Search {
    pool: Arc<Mutex<Vec<Connection>>>,
    #[allow(dead_code)]
    db_path: String,
}

#[pymethods]
impl Search {
    #[new]
    fn new(db_path: String, pool_size: Option<usize>) -> PyResult<Self> {
        let size = pool_size.unwrap_or(4);
        let mut pool = Vec::with_capacity(size);
        
        // Create connection pool
        for _ in 0..size {
            let conn = Connection::open(&db_path)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to open database: {}", e)
                ))?;
            
            // Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL", [])
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to set WAL mode: {}", e)
                ))?;
            
            pool.push(conn);
        }
        
        Ok(Self {
            pool: Arc::new(Mutex::new(pool)),
            db_path,
        })
    }
    
    /// Full-text search with BM25 ranking
    /// 
    /// Args:
    ///     query: Search query string
    ///     tags: Optional list of tags to filter by
    ///     memory_type: Optional memory type filter
    ///     min_importance: Minimum importance score (0.0-1.0)
    ///     limit: Maximum number of results
    /// 
    /// Returns:
    ///     List of memory IDs matching the query
    fn search(
        &self,
        query: String,
        tags: Option<Vec<String>>,
        memory_type: Option<String>,
        min_importance: Option<f64>,
        limit: Option<usize>
    ) -> PyResult<Vec<String>> {
        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];
        
        // Build SQL query with BM25 ranking
        let mut sql = String::from(
            "SELECT id FROM memories_fts 
             WHERE memories_fts MATCH ? 
             ORDER BY bm25(memories_fts, 10.0, 1.0, 5.0)"
        );
        
        // Add filters
        let mut params_vec: Vec<Box<dyn rusqlite::ToSql>> = vec![
            Box::new(query.clone())
        ];
        
        if let Some(ref t) = tags {
            if !t.is_empty() {
                sql.push_str(" AND tags IN (");
                sql.push_str(&vec!["?"; t.len()].join(","));
                sql.push_str(")");
                for tag in t {
                    params_vec.push(Box::new(tag.clone()));
                }
            }
        }
        
        if let Some(ref mt) = memory_type {
            sql.push_str(" AND memory_type = ?");
            params_vec.push(Box::new(mt.clone()));
        }
        
        if let Some(mi) = min_importance {
            sql.push_str(" AND importance >= ?");
            params_vec.push(Box::new(mi));
        }
        
        // Add limit
        let lim = limit.unwrap_or(10);
        sql.push_str(" LIMIT ?");
        params_vec.push(Box::new(lim as i64));
        
        // Execute query
        let mut stmt = conn.prepare(&sql)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to prepare query: {}", e)
            ))?;
        
        let params_refs: Vec<&dyn rusqlite::ToSql> = params_vec
            .iter()
            .map(|p| p.as_ref())
            .collect();
        
        let rows = stmt.query_map(params_refs.as_slice(), |row| {
            row.get::<_, String>(0)
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Query failed: {}", e)
        ))?;
        
        let mut results = Vec::new();
        for row in rows {
            if let Ok(id) = row {
                results.push(id);
            }
        }
        
        Ok(results)
    }
    
    /// Parallel batch search
    /// 
    /// Processes multiple queries in parallel using Rayon
    fn batch_search(
        &self,
        queries: Vec<String>,
        limit: Option<usize>
    ) -> PyResult<Vec<Vec<String>>> {
        let results: Vec<Vec<String>> = queries
            .par_iter()
            .map(|q| {
                self.search(
                    q.clone(),
                    None,
                    None,
                    None,
                    limit
                ).unwrap_or_default()
            })
            .collect();
        
        Ok(results)
    }
    
    /// Get search statistics
    fn get_stats(&self) -> PyResult<(usize, usize)> {
        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];
        
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM memories_fts",
            [],
            |row| row.get(0)
        ).unwrap_or(0);
        
        Ok((pool.len(), count as usize))
    }
}
