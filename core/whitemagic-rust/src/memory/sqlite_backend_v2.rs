//! sqlite_backend - Rust Migration
//! High-performance database operations with connection pooling
//! Target: 20-50× speedup over Python

use pyo3::prelude::*;
use rusqlite::Connection;
use std::sync::{Arc, Mutex};

#[pyclass]
pub struct SqliteBackendV2 {
    #[allow(dead_code)]
    db_path: String,
    pool: Arc<Mutex<Vec<Connection>>>,
}

#[pymethods]
impl SqliteBackendV2 {
    #[new]
    fn new(db_path: String, pool_size: Option<usize>) -> PyResult<Self> {
        let size = pool_size.unwrap_or(4);
        let mut pool = Vec::with_capacity(size);
        
        for _ in 0..size {
            let conn = Connection::open(&db_path)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to open database: {}", e)
                ))?;
            
            conn.execute("PRAGMA journal_mode=WAL", [])
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to set WAL mode: {}", e)
                ))?;
            
            pool.push(conn);
        }
        
        Ok(Self {
            db_path,
            pool: Arc::new(Mutex::new(pool)),
        })
    }
    
    fn execute(&self, query: String) -> PyResult<usize> {
        let pool = self.pool.lock().unwrap();
        let conn = &pool[0];
        
        conn.execute(&query, [])
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Query failed: {}", e)
            ))
    }
}
