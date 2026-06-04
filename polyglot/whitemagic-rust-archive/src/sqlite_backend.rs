//! SQLite Backend - Database Operations (PSR-001)
//! Target: 20-50× speedup over Python sqlite3

use pyo3::prelude::*;
use rusqlite::{Connection, params};
use std::sync::{Arc, Mutex};

#[pyclass]
pub struct PySQLiteBackend {
    conn: Arc<Mutex<Connection>>,
}

#[pymethods]
impl PySQLiteBackend {
    #[new]
    fn new(db_path: String) -> PyResult<Self> {
        let conn = Connection::open(&db_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to open database: {}", e)
            ))?;
        
        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    fn execute(&self, sql: String, params_list: Vec<String>) -> PyResult<usize> {
        let conn = self.conn.lock()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;
        
        let params_refs: Vec<&dyn rusqlite::ToSql> = params_list
            .iter()
            .map(|s| s as &dyn rusqlite::ToSql)
            .collect();
        
        conn.execute(&sql, params_refs.as_slice())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Execute failed: {}", e)
            ))
    }

    fn query_one(&self, sql: String) -> PyResult<Option<String>> {
        let conn = self.conn.lock()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;
        
        let mut stmt = conn.prepare(&sql)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Prepare failed: {}", e)
            ))?;
        
        let result = stmt.query_row([], |row| row.get::<_, String>(0));
        
        match result {
            Ok(val) => Ok(Some(val)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Query failed: {}", e)
            )),
        }
    }

    #[pyo3(signature = (id, content, memory_type, created_at, updated_at, accessed_at, access_count, emotional_valence, importance, neuro_score, novelty_score, recall_count, half_life_days, is_protected, metadata, title, galactic_distance, retention_score, last_retention_sweep=None, content_hash=None, event_time=None, ingestion_time=String::new(), is_private=0, model_exclude=0))]
    fn store_memory(
        &self,
        id: String,
        content: String,
        memory_type: String,
        created_at: String,
        updated_at: String,
        accessed_at: String,
        access_count: i64,
        emotional_valence: f64,
        importance: f64,
        neuro_score: f64,
        novelty_score: f64,
        recall_count: i64,
        half_life_days: f64,
        is_protected: i64,
        metadata: String,
        title: String,
        galactic_distance: f64,
        retention_score: f64,
        last_retention_sweep: Option<String>,
        content_hash: Option<String>,
        event_time: Option<String>,
        ingestion_time: String,
        is_private: i64,
        model_exclude: i64,
    ) -> PyResult<bool> {
        let conn = self.conn.lock()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        conn.execute(
            "INSERT OR REPLACE INTO memories (
                id, content, memory_type, created_at, updated_at, accessed_at,
                access_count, emotional_valence, importance,
                neuro_score, novelty_score, recall_count, half_life_days, is_protected,
                metadata, title,
                galactic_distance, retention_score, last_retention_sweep,
                content_hash, event_time, ingestion_time,
                is_private, model_exclude
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24)",
            params![
                id, content, memory_type, created_at, updated_at, accessed_at,
                access_count, emotional_valence, importance,
                neuro_score, novelty_score, recall_count, half_life_days, is_protected,
                metadata, title,
                galactic_distance, retention_score, last_retention_sweep,
                content_hash, event_time, ingestion_time,
                is_private, model_exclude
            ],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Store failed: {}", e)
        ))?;

        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    #[test]
    fn test_connection() {
        let conn = Connection::open_in_memory().unwrap();
        assert!(conn.is_autocommit());
    }

    #[test]
    fn test_create_table() {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)",
            [],
        ).unwrap();
    }

    #[test]
    fn test_insert_and_query() {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)",
            [],
        ).unwrap();
        
        conn.execute(
            "INSERT INTO test (id, name) VALUES (?1, ?2)",
            params![1, "Alice"],
        ).unwrap();
        
        let name: String = conn.query_row(
            "SELECT name FROM test WHERE id = ?1",
            params![1],
            |row| row.get(0),
        ).unwrap();
        
        assert_eq!(name, "Alice");
    }

    #[test]
    fn test_batch_transaction() {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value INTEGER)",
            [],
        ).unwrap();
        
        let tx = conn.unchecked_transaction().unwrap();
        for i in 0..1000 {
            tx.execute(
                "INSERT INTO test (id, value) VALUES (?1, ?2)",
                params![i, i * 2],
            ).unwrap();
        }
        tx.commit().unwrap();
        
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM test",
            [],
            |row| row.get(0),
        ).unwrap();
        
        assert_eq!(count, 1000);
    }
}

// ---------------------------------------------------------------------------
// PyO3 module registration
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
pub fn register_sqlite_backend(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySQLiteBackend>()?;
    Ok(())
}
