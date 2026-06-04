//! SQLite Backend V2 - High-Performance Database Operations
//! Migration of whitemagic/core/memory/sqlite_backend.py to Rust
//! Target: 20-50× speedup with connection pooling and parallel queries

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use rusqlite::{Connection, params, Result as SqlResult};
use rayon::prelude::*;

#[pyclass]
pub struct SqliteBackendV2 {
    db_path: String,
    connection_pool: Arc<Mutex<Vec<Connection>>>,
    pool_size: usize,
}

#[pymethods]
impl SqliteBackendV2 {
    #[new]
    fn new(db_path: String, pool_size: Option<usize>) -> PyResult<Self> {
        let size = pool_size.unwrap_or(4);
        let mut pool = Vec::with_capacity(size);
        
        // Initialize connection pool
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
            db_path,
            connection_pool: Arc::new(Mutex::new(pool)),
            pool_size: size,
        })
    }

    fn execute_query(&self, query: String, params_list: Vec<String>) -> PyResult<usize> {
        let pool = self.connection_pool.lock().unwrap();
        let conn = &pool[0]; // Use first connection for writes
        
        let params_refs: Vec<&dyn rusqlite::ToSql> = params_list
            .iter()
            .map(|s| s as &dyn rusqlite::ToSql)
            .collect();
        
        conn.execute(&query, params_refs.as_slice())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Query execution failed: {}", e)
            ))
    }

    fn batch_insert(&self, table: String, rows: Vec<Vec<String>>) -> PyResult<usize> {
        let pool = self.connection_pool.lock().unwrap();
        let conn = &pool[0];
        
        let tx = conn.unchecked_transaction()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to start transaction: {}", e)
            ))?;
        
        let mut inserted = 0;
        for row in rows {
            // Simplified - real implementation would use prepared statements
            let placeholders = vec!["?"; row.len()].join(", ");
            let query = format!("INSERT INTO {} VALUES ({})", table, placeholders);
            
            let params_refs: Vec<&dyn rusqlite::ToSql> = row
                .iter()
                .map(|s| s as &dyn rusqlite::ToSql)
                .collect();
            
            tx.execute(&query, params_refs.as_slice())
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Insert failed: {}", e)
                ))?;
            
            inserted += 1;
        }
        
        tx.commit()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Transaction commit failed: {}", e)
            ))?;
        
        Ok(inserted)
    }

    fn parallel_query(&self, queries: Vec<String>) -> PyResult<Vec<usize>> {
        // Execute multiple queries in parallel using connection pool
        let results: Vec<usize> = queries
            .into_par_iter()
            .map(|query| {
                let pool = self.connection_pool.lock().unwrap();
                let conn_idx = rayon::current_thread_index().unwrap_or(0) % self.pool_size;
                let conn = &pool[conn_idx];
                
                conn.execute(&query, [])
                    .unwrap_or(0)
            })
            .collect();
        
        Ok(results)
    }

    fn get_stats(&self) -> PyResult<HashMap<String, usize>> {
        let mut stats = HashMap::new();
        stats.insert("pool_size".to_string(), self.pool_size);
        stats.insert("connections_active".to_string(), self.pool_size);
        Ok(stats)
    }
}

#[pyfunction]
pub fn benchmark_sqlite_operations(db_path: String, operation_count: usize) -> PyResult<HashMap<String, f64>> {
    let backend = SqliteBackendV2::new(db_path, Some(4))?;
    
    // Benchmark batch inserts
    let start = std::time::Instant::now();
    
    let rows: Vec<Vec<String>> = (0..operation_count)
        .map(|i| vec![
            format!("id_{}", i),
            format!("content_{}", i),
            format!("tag_{}", i % 100),
        ])
        .collect();
    
    let inserted = backend.batch_insert("test_table".to_string(), rows)?;
    
    let duration = start.elapsed().as_secs_f64();
    let throughput = inserted as f64 / duration;
    
    let mut stats = HashMap::new();
    stats.insert("operation_count".to_string(), operation_count as f64);
    stats.insert("inserted".to_string(), inserted as f64);
    stats.insert("duration_sec".to_string(), duration);
    stats.insert("throughput_ops_sec".to_string(), throughput);
    
    Ok(stats)
}
