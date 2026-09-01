//! Memory lifecycle — consolidation and mindful forgetting.
//!
//! Consolidation boosts importance of frequently-accessed memories.
//! Mindful forgetting decays importance over time and removes memories
//! that fall below a threshold.

use crate::MemoryStore;

use chrono::Utc;
use uuid::Uuid;
use wm_core::{Galaxy, Result};

/// Configuration for the memory lifecycle.
#[derive(Debug, Clone)]
pub struct LifecycleConfig {
    /// Importance threshold below which memories are candidates for forgetting.
    pub forget_threshold: f32,
    /// Decay factor applied per day since last access.
    pub daily_decay_factor: f32,
    /// Boost factor applied per access (consolidation).
    pub access_boost: f32,
    /// Maximum importance cap.
    pub max_importance: f32,
    /// Recency boost: memories accessed in the last N hours get a boost.
    pub recency_window_hours: i64,
    /// Recency boost amount.
    pub recency_boost: f32,
}

impl Default for LifecycleConfig {
    fn default() -> Self {
        Self {
            forget_threshold: 0.1,
            daily_decay_factor: 0.95, // 5% decay per day
            access_boost: 0.05,       // +5% per access
            max_importance: 1.0,
            recency_window_hours: 24,
            recency_boost: 0.1,
        }
    }
}

/// Runs memory lifecycle operations on a `MemoryStore`.
pub struct Lifecycle {
    config: LifecycleConfig,
}

/// Result of a consolidation pass on a single galaxy.
#[derive(Debug, Clone)]
pub struct ConsolidationResult {
    /// Galaxy processed
    pub galaxy: Galaxy,
    /// Memories examined
    pub examined: usize,
    /// Memories boosted
    pub boosted: usize,
    /// Memories decayed
    pub decayed: usize,
}

/// Result of a mindful forgetting pass on a single galaxy.
#[derive(Debug, Clone)]
pub struct ForgettingResult {
    /// Galaxy processed
    pub galaxy: Galaxy,
    /// Memories examined
    pub examined: usize,
    /// Memories forgotten (deleted)
    pub forgotten: usize,
    /// IDs of forgotten memories
    pub forgotten_ids: Vec<Uuid>,
}

impl Lifecycle {
    /// Create a new lifecycle manager with the given config.
    #[must_use]
    pub const fn new(config: LifecycleConfig) -> Self {
        Self { config }
    }

    /// Create with default config.
    #[must_use]
    pub fn default_config() -> Self {
        Self::new(LifecycleConfig::default())
    }

    /// Consolidate memories in a galaxy — boost frequently-accessed and recent memories.
    pub fn consolidate(&self, store: &MemoryStore, galaxy: Galaxy) -> Result<ConsolidationResult> {
        let memories = store.scan(galaxy, 10_000)?;
        let now = Utc::now();
        let mut examined = 0;
        let mut boosted = 0;
        let mut decayed = 0;

        for mut mem in memories {
            examined += 1;
            let original_importance = mem.metadata.importance;

            // Skip protected memories from consolidation changes
            if mem.metadata.is_protected {
                continue;
            }

            // Access-based boost
            if mem.metadata.access_count > 0 {
                let boost = self.config.access_boost * mem.metadata.access_count as f32;
                mem.metadata.importance += boost;
            }

            // Recency boost
            let hours_since_access = (now - mem.metadata.accessed_at).num_hours();
            if hours_since_access < self.config.recency_window_hours {
                mem.metadata.importance += self.config.recency_boost;
            }

            // Daily decay — uses per-memory half_life_days if configured
            let days_since_access = (now - mem.metadata.accessed_at).num_days();
            if days_since_access > 0 {
                let decay = self
                    .config
                    .daily_decay_factor
                    .powi(days_since_access as i32);
                mem.metadata.importance *= decay;
            }

            // Apply neuro_score decay based on per-memory half-life
            mem.decay(now);

            // Clamp
            mem.metadata.importance = mem
                .metadata
                .importance
                .clamp(0.0, self.config.max_importance);

            if mem.metadata.importance > original_importance {
                boosted += 1;
            } else if mem.metadata.importance < original_importance {
                decayed += 1;
            }

            // Write back if changed
            if (mem.metadata.importance - original_importance).abs() > f32::EPSILON {
                store.put(galaxy, &mem)?;
            }
        }

        Ok(ConsolidationResult {
            galaxy,
            examined,
            boosted,
            decayed,
        })
    }

    /// Run mindful forgetting on a galaxy — delete memories below the importance threshold.
    pub fn forget(&self, store: &MemoryStore, galaxy: Galaxy) -> Result<ForgettingResult> {
        let memories = store.scan(galaxy, 10_000)?;
        let mut examined = 0;
        let mut forgotten = 0;
        let mut forgotten_ids = Vec::new();

        for mem in memories {
            examined += 1;
            if mem.should_forget(self.config.forget_threshold) {
                let id = mem.metadata.id;
                store.delete(galaxy, id)?;
                forgotten += 1;
                forgotten_ids.push(id);
            }
        }

        Ok(ForgettingResult {
            galaxy,
            examined,
            forgotten,
            forgotten_ids,
        })
    }

    /// Run a full lifecycle pass: consolidate then forget, across all galaxies.
    pub fn run_full_cycle(
        &self,
        store: &MemoryStore,
    ) -> Result<(Vec<ConsolidationResult>, Vec<ForgettingResult>)> {
        let mut consol_results = Vec::new();
        let mut forget_results = Vec::new();

        for galaxy in wm_core::Galaxy::all() {
            // Skip system galaxies
            match galaxy {
                Galaxy::Substrate | Galaxy::Dharma | Galaxy::Karma | Galaxy::Embeddings => continue,
                _ => {}
            }
            let count = store.count(galaxy).unwrap_or(0);
            if count == 0 {
                continue;
            }
            consol_results.push(self.consolidate(store, galaxy)?);
            forget_results.push(self.forget(store, galaxy)?);
        }

        Ok((consol_results, forget_results))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Memory;
    use tempfile::tempdir;

    fn test_store() -> MemoryStore {
        let tmp = tempdir().unwrap();
        MemoryStore::open_default(tmp.path()).unwrap()
    }

    #[test]
    fn consolidate_boosts_accessed_memories() {
        let store = test_store();
        let galaxy = Galaxy::Codex;

        // Create a memory and simulate access
        let mut mem = Memory::new(galaxy, "frequently accessed".into());
        mem.metadata.access_count = 5;
        store.put(galaxy, &mem).unwrap();

        let lifecycle = Lifecycle::default_config();
        let result = lifecycle.consolidate(&store, galaxy).unwrap();

        assert_eq!(result.examined, 1);
        assert!(result.boosted >= 1);

        // Verify importance was boosted
        let retrieved = store.get(galaxy, mem.metadata.id).unwrap().unwrap();
        assert!(retrieved.metadata.importance > 0.5);
    }

    #[test]
    fn forget_removes_low_importance() {
        let store = test_store();
        let galaxy = Galaxy::Codex;

        // Create a low-importance memory
        let mem = Memory::new(galaxy, "unimportant".into()).with_importance(0.05);
        store.put(galaxy, &mem).unwrap();

        let lifecycle = Lifecycle::default_config();
        let result = lifecycle.forget(&store, galaxy).unwrap();

        assert_eq!(result.forgotten, 1);
        assert!(store.get(galaxy, mem.metadata.id).unwrap().is_none());
    }

    #[test]
    fn forget_keeps_important_memories() {
        let store = test_store();
        let galaxy = Galaxy::Codex;

        let mem = Memory::new(galaxy, "important".into()).with_importance(0.9);
        store.put(galaxy, &mem).unwrap();

        let lifecycle = Lifecycle::default_config();
        let result = lifecycle.forget(&store, galaxy).unwrap();

        assert_eq!(result.forgotten, 0);
        assert!(store.get(galaxy, mem.metadata.id).unwrap().is_some());
    }

    #[test]
    fn full_cycle_processes_all_galaxies() {
        let store = test_store();

        // Add memories to a couple galaxies
        let mem1 = Memory::new(Galaxy::Codex, "codex memory".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        let mem2 = Memory::new(Galaxy::Research, "research memory".into());
        store.put(Galaxy::Research, &mem2).unwrap();

        let lifecycle = Lifecycle::default_config();
        let (consol, _forget) = lifecycle.run_full_cycle(&store).unwrap();

        assert!(consol.iter().any(|c| c.galaxy == Galaxy::Codex));
        assert!(consol.iter().any(|c| c.galaxy == Galaxy::Research));
    }

    #[test]
    fn consolidate_skips_protected_memories() {
        let store = test_store();
        let galaxy = Galaxy::Codex;

        let mut mem = Memory::new(galaxy, "protected".into());
        mem.metadata.is_protected = true;
        mem.metadata.importance = 0.5;
        let id = mem.metadata.id;
        store.put(galaxy, &mem).unwrap();

        let lifecycle = Lifecycle::default_config();
        let _result = lifecycle.consolidate(&store, galaxy).unwrap();

        // Importance should be unchanged
        let back = store.get(galaxy, id).unwrap().unwrap();
        assert!((back.metadata.importance - 0.5).abs() < f32::EPSILON);
    }

    #[test]
    fn forget_respects_is_protected() {
        let store = test_store();
        let galaxy = Galaxy::Codex;

        let mem = Memory::new(galaxy, "protected low".into())
            .with_importance(0.01)
            .with_protection(true);
        let id = mem.metadata.id;
        store.put(galaxy, &mem).unwrap();

        let lifecycle = Lifecycle::default_config();
        let result = lifecycle.forget(&store, galaxy).unwrap();

        assert_eq!(result.forgotten, 0);
        assert!(store.get(galaxy, id).unwrap().is_some());
    }
}
