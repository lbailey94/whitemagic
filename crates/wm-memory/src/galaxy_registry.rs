//! Dynamic galaxy management — project-scoped galaxy creation.
//!
//! Phase 6.8: Extends the fixed 14-galaxy taxonomy with a dynamic
//! registry for project-scoped galaxies. Custom galaxies are stored
//! as LMDB named databases alongside the built-in ones.

use lmdb::{Cursor, Database, DatabaseFlags, Environment, Transaction, WriteFlags};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use wm_core::{CoreError, Galaxy, Result};

/// Metadata for a dynamic (custom) galaxy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GalaxyMetadata {
    /// Unique galaxy name (used as LMDB sub-database name)
    pub name: String,
    /// Human-readable description
    pub description: String,
    /// Project scope (empty = global)
    pub project: String,
    /// Creation timestamp
    pub created_at: i64,
    /// Whether this galaxy is read-only
    pub read_only: bool,
}

/// Registry for dynamic galaxies — allows creating custom galaxies
/// beyond the fixed 14 built-in ones.
///
/// Custom galaxy metadata is stored in a dedicated LMDB sub-database
/// called `_galaxy_registry`. Each custom galaxy gets its own LMDB
/// sub-database for storing memories.
pub struct GalaxyRegistry {
    /// Registry sub-database (stores GalaxyMetadata entries)
    registry_db: Database,
    /// Cache of opened custom galaxy databases
    db_cache: HashMap<String, Database>,
}

impl GalaxyRegistry {
    /// Open or create a galaxy registry in the given LMDB environment.
    pub fn open(env: &Environment) -> Result<Self> {
        let registry_db = env
            .create_db(Some("_galaxy_registry"), DatabaseFlags::default())
            .map_err(|e| CoreError::Memory(format!("LMDB create_db for galaxy registry: {e}")))?;

        Ok(Self {
            registry_db,
            db_cache: HashMap::new(),
        })
    }

    /// Register a new custom galaxy.
    ///
    /// Creates the LMDB sub-database and stores metadata.
    /// Returns error if the name conflicts with a built-in galaxy
    /// or an existing custom galaxy.
    pub fn create(
        &mut self,
        env: &Environment,
        name: &str,
        description: &str,
        project: &str,
    ) -> Result<GalaxyMetadata> {
        // Check for conflict with built-in galaxies
        if Galaxy::all().iter().any(|g| g.db_name() == name) {
            return Err(CoreError::Memory(format!(
                "galaxy name '{name}' conflicts with built-in galaxy"
            )));
        }

        // Check for existing custom galaxy
        if self.get(env, name)?.is_some() {
            return Err(CoreError::Memory(format!("galaxy '{name}' already exists")));
        }

        // Create the LMDB sub-database
        let _db = env
            .create_db(Some(name), DatabaseFlags::default())
            .map_err(|e| CoreError::Memory(format!("LMDB create_db for '{name}': {e}")))?;

        // Store metadata
        let metadata = GalaxyMetadata {
            name: name.to_string(),
            description: description.to_string(),
            project: project.to_string(),
            created_at: chrono::Utc::now().timestamp(),
            read_only: false,
        };

        let val = rmp_serde::to_vec(&metadata)
            .map_err(|e| CoreError::Memory(format!("serialize galaxy metadata: {e}")))?;

        let mut tx = env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn: {e}")))?;
        tx.put(self.registry_db, &name, &val, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("LMDB put galaxy metadata: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;

        Ok(metadata)
    }

    /// Get metadata for a custom galaxy by name.
    pub fn get(&self, env: &Environment, name: &str) -> Result<Option<GalaxyMetadata>> {
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;
        match tx.get(self.registry_db, &name) {
            Ok(bytes) => {
                let metadata: GalaxyMetadata = rmp_serde::from_slice(bytes)
                    .map_err(|e| CoreError::Memory(format!("deserialize galaxy metadata: {e}")))?;
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
                Ok(Some(metadata))
            }
            Err(lmdb::Error::NotFound) => {
                let _ = tx.commit();
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!("LMDB get galaxy metadata: {e}"))),
        }
    }

    /// List all registered custom galaxies.
    pub fn list(&self, env: &Environment) -> Result<Vec<GalaxyMetadata>> {
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;

        let mut cursor = tx
            .open_ro_cursor(self.registry_db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor: {e}")))?;

        let mut galaxies = Vec::new();
        for (key, val) in cursor.iter() {
            if let Ok(metadata) = rmp_serde::from_slice::<GalaxyMetadata>(val) {
                galaxies.push(metadata);
            }
            let _ = key;
        }

        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
        Ok(galaxies)
    }

    /// Delete a custom galaxy's metadata from the registry.
    ///
    /// Cannot delete built-in galaxies. The LMDB sub-database itself
    /// remains (dropping databases requires unsafe LMDB API), but the
    /// metadata is removed so the galaxy is no longer listed.
    pub fn delete(&mut self, env: &Environment, name: &str) -> Result<()> {
        // Check for conflict with built-in galaxies
        if Galaxy::all().iter().any(|g| g.db_name() == name) {
            return Err(CoreError::Memory(format!(
                "cannot delete built-in galaxy '{name}'"
            )));
        }

        // Check it exists
        if self.get(env, name)?.is_none() {
            return Err(CoreError::Memory(format!("galaxy '{name}' does not exist")));
        }

        // Delete metadata from registry
        let mut tx = env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn: {e}")))?;
        tx.del(self.registry_db, &name, None)
            .map_err(|e| CoreError::Memory(format!("LMDB del galaxy metadata: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;

        // Remove from cache
        self.db_cache.remove(name);
        Ok(())
    }

    /// Open a custom galaxy's LMDB database handle.
    pub fn galaxy_db(&mut self, env: &Environment, name: &str) -> Result<Database> {
        if let Some(db) = self.db_cache.get(name) {
            return Ok(*db);
        }

        let db = env
            .open_db(Some(name))
            .map_err(|e| CoreError::Memory(format!("LMDB open_db for galaxy '{name}': {e}")))?;
        self.db_cache.insert(name.to_string(), db);
        Ok(db)
    }

    /// Check if a galaxy name (built-in or custom) exists.
    pub fn exists(&self, env: &Environment, name: &str) -> bool {
        // Check built-in
        if Galaxy::all().iter().any(|g| g.db_name() == name) {
            return true;
        }
        // Check custom
        self.get(env, name).is_ok_and(|opt| opt.is_some())
    }

    /// Count of custom (non-built-in) galaxies.
    pub fn count(&self, env: &Environment) -> usize {
        self.list(env).map_or(0, |v| v.len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn test_registry() -> (tempfile::TempDir, Environment, GalaxyRegistry) {
        let tmp = tempdir().unwrap();
        let env = Environment::new()
            .set_map_size(1024 * 1024)
            .set_max_dbs(32)
            .open(tmp.path())
            .unwrap();
        let registry = GalaxyRegistry::open(&env).unwrap();
        (tmp, env, registry)
    }

    #[test]
    fn create_custom_galaxy() {
        let (_tmp, env, mut registry) = test_registry();
        let meta = registry
            .create(&env, "project_alpha", "Alpha project memories", "alpha")
            .unwrap();
        assert_eq!(meta.name, "project_alpha");
        assert_eq!(meta.description, "Alpha project memories");
        assert_eq!(meta.project, "alpha");
    }

    #[test]
    fn get_custom_galaxy() {
        let (_tmp, env, mut registry) = test_registry();
        registry
            .create(&env, "project_beta", "Beta project", "beta")
            .unwrap();

        let meta = registry.get(&env, "project_beta").unwrap();
        assert!(meta.is_some());
        assert_eq!(meta.unwrap().name, "project_beta");
    }

    #[test]
    fn get_nonexistent_returns_none() {
        let (_tmp, env, registry) = test_registry();
        assert!(registry.get(&env, "nonexistent").unwrap().is_none());
    }

    #[test]
    fn list_custom_galaxies() {
        let (_tmp, env, mut registry) = test_registry();
        registry.create(&env, "galaxy_a", "A", "proj").unwrap();
        registry.create(&env, "galaxy_b", "B", "proj").unwrap();

        let list = registry.list(&env).unwrap();
        assert_eq!(list.len(), 2);
    }

    #[test]
    fn reject_builtin_galaxy_name() {
        let (_tmp, env, mut registry) = test_registry();
        let result = registry.create(&env, "codex", "duplicate", "");
        assert!(result.is_err(), "should reject built-in galaxy name");
    }

    #[test]
    fn reject_duplicate_custom_galaxy() {
        let (_tmp, env, mut registry) = test_registry();
        registry.create(&env, "custom", "first", "").unwrap();
        let result = registry.create(&env, "custom", "second", "");
        assert!(result.is_err(), "should reject duplicate name");
    }

    #[test]
    fn delete_custom_galaxy() {
        let (_tmp, env, mut registry) = test_registry();
        registry.create(&env, "to_delete", "temporary", "").unwrap();
        assert!(registry.get(&env, "to_delete").unwrap().is_some());

        registry.delete(&env, "to_delete").unwrap();
        assert!(registry.get(&env, "to_delete").unwrap().is_none());
    }

    #[test]
    fn cannot_delete_builtin_galaxy() {
        let (_tmp, env, mut registry) = test_registry();
        let result = registry.delete(&env, "codex");
        assert!(result.is_err(), "should not delete built-in galaxy");
    }

    #[test]
    fn exists_checks_builtin_and_custom() {
        let (_tmp, env, mut registry) = test_registry();
        assert!(
            registry.exists(&env, "codex"),
            "should find built-in galaxy"
        );
        assert!(
            !registry.exists(&env, "custom"),
            "should not find nonexistent"
        );

        registry.create(&env, "custom", "test", "").unwrap();
        assert!(registry.exists(&env, "custom"), "should find custom galaxy");
    }

    #[test]
    fn galaxy_db_opens_handle() {
        let (_tmp, env, mut registry) = test_registry();
        registry.create(&env, "test_db", "test", "").unwrap();
        let db = registry.galaxy_db(&env, "test_db").unwrap();
        let _ = db;
    }

    #[test]
    fn count_custom_galaxies() {
        let (_tmp, env, mut registry) = test_registry();
        assert_eq!(registry.count(&env), 0);

        registry.create(&env, "g1", "", "").unwrap();
        registry.create(&env, "g2", "", "").unwrap();
        assert_eq!(registry.count(&env), 2);
    }

    #[test]
    fn galaxy_metadata_serializes() {
        let meta = GalaxyMetadata {
            name: "test".into(),
            description: "test galaxy".into(),
            project: "proj".into(),
            created_at: 1700000000,
            read_only: false,
        };
        let bytes = rmp_serde::to_vec(&meta).unwrap();
        let decoded: GalaxyMetadata = rmp_serde::from_slice(&bytes).unwrap();
        assert_eq!(decoded.name, "test");
        assert_eq!(decoded.project, "proj");
    }
}
