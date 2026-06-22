//! Database Manager - Connection Pooling (PSR-001)
//! Target: 20-50× speedup with connection pooling

use pyo3::prelude::*;
use rusqlite::{Connection, OpenFlags};
use std::sync::Arc;
use parking_lot::Mutex;
use std::collections::VecDeque;

#[pyclass]
pub struct PyDBManager {
    pool: Arc<Mutex<VecDeque<Connection>>>,
    db_path: String,
    max_connections: usize,
}

#[pymethods]
impl PyDBManager {
    #[new]
    fn new(db_path: String, max_connections: Option<usize>) -> PyResult<Self> {
        let max_conn = max_connections.unwrap_or(10);
        let pool = Arc::new(Mutex::new(VecDeque::with_capacity(max_conn)));
        
        Ok(Self {
            pool,
            db_path,
            max_connections: max_conn,
        })
    }

    fn get_connection(&self) -> PyResult<usize> {
        let mut pool = self.pool.lock();
        
        if let Some(_conn) = pool.pop_front() {
            Ok(pool.len())
        } else if pool.len() < self.max_connections {
            let _conn = Connection::open_with_flags(
                &self.db_path,
                OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
            ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to open connection: {}", e)
            ))?;
            
            Ok(pool.len())
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Connection pool exhausted"
            ))
        }
    }

    fn pool_size(&self) -> usize {
        self.pool.lock().len()
    }

    fn max_size(&self) -> usize {
        self.max_connections
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_manager_creation() {
        let manager = PyDBManager::new(":memory:".to_string(), Some(5)).unwrap();
        assert_eq!(manager.max_size(), 5);
    }

    #[test]
    fn test_pool_size() {
        let manager = PyDBManager::new(":memory:".to_string(), Some(10)).unwrap();
        assert_eq!(manager.pool_size(), 0);
    }
}
