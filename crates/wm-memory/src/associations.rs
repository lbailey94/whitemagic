//! Cross-galaxy association links with typed edges and Hebbian dynamics.
//!
//! Associations connect memories across galaxies via weighted, typed edges.
//! Stored in the Associations galaxy with a composite key (`source_id` + `target_id`).
//! Link weights strengthen with co-activation (Hebbian learning) and decay
//! over time when not re-activated.

use chrono::{DateTime, Utc};
use lmdb::{Cursor, Database, DatabaseFlags, Environment, Transaction, WriteFlags};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use wm_core::{CoreError, Galaxy, Result};

/// Typed association between two memories.
///
/// Replaces the legacy `association_type: String` with a typed enum.
/// The string field is kept for backward compatibility but auto-populated
/// from the `LinkType::as_str()` method.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LinkType {
    /// General semantic relatedness
    #[default]
    Related,
    /// Target extends/refines source
    Extends,
    /// Target contradicts source
    Contradicts,
    /// Target supersedes/replaces source
    Supersedes,
    /// Temporal sequence (source before target)
    Temporal,
    /// Causal relationship (source causes target)
    Causal,
    /// Cascade / chain reaction
    Cascade,
}

impl LinkType {
    /// All variants in canonical order.
    #[must_use]
    pub const fn all() -> &'static [Self] {
        &[
            Self::Related,
            Self::Extends,
            Self::Contradicts,
            Self::Supersedes,
            Self::Temporal,
            Self::Causal,
            Self::Cascade,
        ]
    }

    /// String label for JSON / display / backward compat.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Related => "related",
            Self::Extends => "extends",
            Self::Contradicts => "contradicts",
            Self::Supersedes => "supersedes",
            Self::Temporal => "temporal",
            Self::Causal => "causal",
            Self::Cascade => "cascade",
        }
    }

    /// Parse a string into a LinkType, falling back to Related for unknown strings.
    #[must_use]
    pub fn from_str_lossy(s: &str) -> Self {
        match s {
            "related" => Self::Related,
            "extends" => Self::Extends,
            "contradicts" => Self::Contradicts,
            "supersedes" => Self::Supersedes,
            "temporal" => Self::Temporal,
            "causal" => Self::Causal,
            "cascade" => Self::Cascade,
            _ => Self::Related,
        }
    }
}

/// An association between two memories.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Association {
    /// Source memory UUID
    pub source: Uuid,
    /// Target memory UUID
    pub target: Uuid,
    /// Legacy association type string (auto-populated from `link_type`)
    #[serde(default = "default_association_type")]
    pub association_type: String,
    /// Weight / strength (0.0 to 1.0) — dynamic, Hebbian
    pub weight: f32,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    // ── Phase 6.2: Typed links + Hebbian dynamics ────────────────────
    /// Typed link kind
    #[serde(default)]
    pub link_type: LinkType,
    /// Number of co-activations (Hebbian counter)
    #[serde(default)]
    pub co_activation_count: u32,
    /// Last time this link was activated (for decay computation)
    #[serde(default = "default_last_activated")]
    pub last_activated_at: DateTime<Utc>,
    /// Decay half-life in days for the link weight
    #[serde(default = "default_link_half_life_days")]
    pub decay_half_life_days: f32,
}

fn default_association_type() -> String {
    "related".to_string()
}

fn default_last_activated() -> DateTime<Utc> {
    Utc::now()
}

const fn default_link_half_life_days() -> f32 {
    90.0
}

impl Association {
    /// Create a new typed association.
    #[must_use]
    pub fn new(source: Uuid, target: Uuid, link_type: LinkType, weight: f32) -> Self {
        let now = Utc::now();
        Self {
            source,
            target,
            association_type: link_type.as_str().to_string(),
            weight: weight.clamp(0.0, 1.0),
            created_at: now,
            link_type,
            co_activation_count: 0,
            last_activated_at: now,
            decay_half_life_days: default_link_half_life_days(),
        }
    }

    /// Create a new association with a custom decay half-life.
    #[must_use]
    pub const fn with_half_life_days(mut self, days: f32) -> Self {
        self.decay_half_life_days = days.max(1.0);
        self
    }

    /// Hebbian co-activation — strengthens the link weight.
    ///
    /// Boosts `weight` by `0.1 * (1.0 - current_weight)` (diminishing returns),
    /// increments `co_activation_count`, and updates `last_activated_at`.
    pub fn activate(&mut self) {
        let now = Utc::now();
        self.co_activation_count += 1;
        self.last_activated_at = now;

        // Hebbian boost: diminishing returns as weight approaches 1.0
        let boost = 0.1 * (1.0 - self.weight);
        self.weight = (self.weight + boost).clamp(0.0, 1.0);
    }

    /// Apply exponential decay to link weight based on time since last activation.
    ///
    /// `weight *= 0.5 ^ (days_since_activation / decay_half_life_days)`
    pub fn decay(&mut self, now: DateTime<Utc>) {
        let days_since = ((now - self.last_activated_at).num_seconds() as f32) / 86_400.0;
        if days_since <= 0.0 {
            return;
        }
        let half_life = self.decay_half_life_days.max(1.0);
        let factor = 0.5_f32.powf(days_since / half_life);
        self.weight = (self.weight * factor).clamp(0.0, 1.0);
    }

    /// Whether this link has decayed below a pruning threshold.
    #[must_use]
    pub fn should_prune(&self, threshold: f32) -> bool {
        self.weight < threshold
    }

    /// Encode the composite key: source(16) + target(16) = 32 bytes.
    #[must_use]
    pub fn encode_key(&self) -> Vec<u8> {
        let mut key = Vec::with_capacity(32);
        key.extend_from_slice(self.source.as_bytes());
        key.extend_from_slice(self.target.as_bytes());
        key
    }

    /// Encode a key from source and target UUIDs.
    #[must_use]
    pub fn encode_key_pair(source: Uuid, target: Uuid) -> Vec<u8> {
        let mut key = Vec::with_capacity(32);
        key.extend_from_slice(source.as_bytes());
        key.extend_from_slice(target.as_bytes());
        key
    }
}

/// Manages cross-galaxy associations in the Associations galaxy.
pub struct AssociationStore {
    db: Database,
}

impl AssociationStore {
    /// Open the association store from an LMDB environment.
    pub fn open(env: &Environment) -> Result<Self> {
        let db = env
            .create_db(
                Some(Galaxy::Associations.db_name()),
                DatabaseFlags::default(),
            )
            .map_err(|e| CoreError::Memory(format!("LMDB create_db for associations: {e}")))?;
        Ok(Self { db })
    }

    /// Create or update an association.
    pub fn put(&self, env: &Environment, assoc: &Association) -> Result<()> {
        let key = assoc.encode_key();
        let val = rmp_serde::to_vec(assoc)
            .map_err(|e| CoreError::Memory(format!("serialize association: {e}")))?;

        let mut tx = env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn: {e}")))?;
        tx.put(self.db, &key, &val, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("LMDB put association: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
        Ok(())
    }

    /// Get an association between two specific memories.
    pub fn get(
        &self,
        env: &Environment,
        source: Uuid,
        target: Uuid,
    ) -> Result<Option<Association>> {
        let key = Association::encode_key_pair(source, target);
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;
        match tx.get(self.db, &key) {
            Ok(bytes) => {
                let assoc: Association = rmp_serde::from_slice(bytes)
                    .map_err(|e| CoreError::Memory(format!("deserialize association: {e}")))?;
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
                Ok(Some(assoc))
            }
            Err(lmdb::Error::NotFound) => {
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!("LMDB get association: {e}"))),
        }
    }

    /// Delete an association.
    pub fn delete(&self, env: &Environment, source: Uuid, target: Uuid) -> Result<bool> {
        let key = Association::encode_key_pair(source, target);
        let mut tx = env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn: {e}")))?;
        let exists = tx.get(self.db, &key).is_ok();
        if exists {
            tx.del(self.db, &key, None)
                .map_err(|e| CoreError::Memory(format!("LMDB del association: {e}")))?;
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
        Ok(exists)
    }

    /// Find all associations where the given UUID is the source.
    pub fn find_from(&self, env: &Environment, source: Uuid) -> Result<Vec<Association>> {
        let prefix = source.as_bytes();
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(self.db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor: {e}")))?;

        let mut results = Vec::new();
        for (key, val) in cursor.iter() {
            if key.len() >= 16 && &key[..16] == prefix {
                if let Ok(assoc) = rmp_serde::from_slice::<Association>(val) {
                    results.push(assoc);
                }
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
        Ok(results)
    }

    /// Find all associations where the given UUID is the target.
    pub fn find_to(&self, env: &Environment, target: Uuid) -> Result<Vec<Association>> {
        let suffix = target.as_bytes();
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(self.db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor: {e}")))?;

        let mut results = Vec::new();
        for (key, val) in cursor.iter() {
            if key.len() >= 32 && &key[16..32] == suffix {
                if let Ok(assoc) = rmp_serde::from_slice::<Association>(val) {
                    results.push(assoc);
                }
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
        Ok(results)
    }

    /// Count all associations.
    pub fn count(&self, env: &Environment) -> Result<usize> {
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(self.db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor: {e}")))?;
        let count = cursor.iter().count();
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;
        Ok(count)
    }

    /// Find all direct circular associations (A→B and B→A both exist).
    ///
    /// Circular links can artificially inflate importance in retention
    /// calculations. This method scans all associations and returns pairs
    /// of UUIDs where both directions exist, allowing the retention engine
    /// to avoid double-counting.
    pub fn find_cycles(&self, env: &Environment) -> Result<Vec<(Uuid, Uuid)>> {
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(self.db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor: {e}")))?;

        // Collect all (source, target) pairs
        let mut pairs: Vec<(Uuid, Uuid)> = Vec::new();
        let mut seen: std::collections::HashSet<[u8; 32]> = std::collections::HashSet::new();
        for (key, _val) in cursor.iter() {
            if key.len() == 32 {
                let mut arr = [0u8; 32];
                arr.copy_from_slice(key);
                if seen.insert(arr) {
                    let src = Uuid::from_bytes(arr[..16].try_into().unwrap());
                    let tgt = Uuid::from_bytes(arr[16..32].try_into().unwrap());
                    pairs.push((src, tgt));
                }
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit: {e}")))?;

        // Find cycles: for each (A, B), check if (B, A) also exists
        let pair_set: std::collections::HashSet<[u8; 32]> = pairs
            .iter()
            .map(|(s, t)| {
                let mut arr = [0u8; 32];
                arr[..16].copy_from_slice(s.as_bytes());
                arr[16..32].copy_from_slice(t.as_bytes());
                arr
            })
            .collect();

        let cycles: Vec<(Uuid, Uuid)> = pairs
            .into_iter()
            .filter(|(s, t)| {
                // Check if reverse (t, s) exists, but avoid reporting both directions
                let mut reverse = [0u8; 32];
                reverse[..16].copy_from_slice(t.as_bytes());
                reverse[16..32].copy_from_slice(s.as_bytes());
                pair_set.contains(&reverse) && s < t // only report once per pair
            })
            .collect();

        Ok(cycles)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn open_store() -> (tempfile::TempDir, Environment, AssociationStore) {
        let tmp = tempdir().unwrap();
        let env = Environment::new()
            .set_map_size(1024 * 1024)
            .set_max_dbs(16)
            .open(tmp.path())
            .unwrap();
        let store = AssociationStore::open(&env).unwrap();
        (tmp, env, store)
    }

    #[test]
    fn put_and_get_association() {
        let (_tmp, env, store) = open_store();
        let src = Uuid::new_v4();
        let tgt = Uuid::new_v4();
        let assoc = Association::new(src, tgt, LinkType::Related, 0.8);
        store.put(&env, &assoc).unwrap();

        let got = store.get(&env, src, tgt).unwrap();
        assert!(got.is_some());
        let got = got.unwrap();
        assert_eq!(got.association_type, "related");
        assert_eq!(got.link_type, LinkType::Related);
    }

    #[test]
    fn find_from_and_to() {
        let (_tmp, env, store) = open_store();
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        let c = Uuid::new_v4();

        store
            .put(&env, &Association::new(a, b, LinkType::Related, 0.5))
            .unwrap();
        store
            .put(&env, &Association::new(a, c, LinkType::Causal, 0.7))
            .unwrap();
        store
            .put(&env, &Association::new(b, c, LinkType::Related, 0.3))
            .unwrap();

        let from_a = store.find_from(&env, a).unwrap();
        assert_eq!(from_a.len(), 2);

        let to_c = store.find_to(&env, c).unwrap();
        assert_eq!(to_c.len(), 2);
    }

    #[test]
    fn delete_association() {
        let (_tmp, env, store) = open_store();
        let src = Uuid::new_v4();
        let tgt = Uuid::new_v4();
        store
            .put(&env, &Association::new(src, tgt, LinkType::Related, 0.5))
            .unwrap();
        assert!(store.delete(&env, src, tgt).unwrap());
        assert!(store.get(&env, src, tgt).unwrap().is_none());
    }

    #[test]
    fn count_associations() {
        let (_tmp, env, store) = open_store();
        assert_eq!(store.count(&env).unwrap(), 0);
        store
            .put(
                &env,
                &Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.5),
            )
            .unwrap();
        store
            .put(
                &env,
                &Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.5),
            )
            .unwrap();
        assert_eq!(store.count(&env).unwrap(), 2);
    }

    // ── Phase 6.2: LinkType + Hebbian tests ────────────────────────────

    #[test]
    fn link_type_default_is_related() {
        assert_eq!(LinkType::default(), LinkType::Related);
    }

    #[test]
    fn link_type_all_has_7_variants() {
        assert_eq!(LinkType::all().len(), 7);
    }

    #[test]
    fn link_type_as_str_matches_expected() {
        assert_eq!(LinkType::Related.as_str(), "related");
        assert_eq!(LinkType::Extends.as_str(), "extends");
        assert_eq!(LinkType::Contradicts.as_str(), "contradicts");
        assert_eq!(LinkType::Supersedes.as_str(), "supersedes");
        assert_eq!(LinkType::Temporal.as_str(), "temporal");
        assert_eq!(LinkType::Causal.as_str(), "causal");
        assert_eq!(LinkType::Cascade.as_str(), "cascade");
    }

    #[test]
    fn link_type_from_str_lossy_roundtrip() {
        for &lt in LinkType::all() {
            assert_eq!(LinkType::from_str_lossy(lt.as_str()), lt);
        }
        assert_eq!(LinkType::from_str_lossy("unknown"), LinkType::Related);
    }

    #[test]
    fn link_type_serde_roundtrip() {
        for &lt in LinkType::all() {
            let json = serde_json::to_string(&lt).unwrap();
            let back: LinkType = serde_json::from_str(&json).unwrap();
            assert_eq!(lt, back);
        }
    }

    #[test]
    fn new_association_populates_association_type_from_link_type() {
        let assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Causal, 0.5);
        assert_eq!(assoc.association_type, "causal");
        assert_eq!(assoc.link_type, LinkType::Causal);
    }

    #[test]
    fn new_association_has_hebbian_defaults() {
        let assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.5);
        assert_eq!(assoc.co_activation_count, 0);
        assert!((assoc.decay_half_life_days - 90.0).abs() < f32::EPSILON);
        // last_activated_at should be ~now
        let now = Utc::now();
        let diff = (now - assoc.last_activated_at).num_seconds().abs();
        assert!(diff < 5);
    }

    #[test]
    fn activate_boosts_weight() {
        let mut assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.3);
        let initial = assoc.weight;
        assoc.activate();
        assert!(assoc.weight > initial);
        assert_eq!(assoc.co_activation_count, 1);
    }

    #[test]
    fn activate_has_diminishing_returns() {
        let mut assoc_high =
            Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.9);
        assoc_high.activate();
        let boost_high = 0.1 * (1.0 - 0.9);
        assert!((assoc_high.weight - (0.9 + boost_high)).abs() < 1e-5);

        let mut assoc_low =
            Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.1);
        assoc_low.activate();
        let boost_low = 0.1 * (1.0 - 0.1);
        assert!((assoc_low.weight - (0.1 + boost_low)).abs() < 1e-5);
    }

    #[test]
    fn activate_weight_caps_at_1() {
        let mut assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.99);
        for _ in 0..100 {
            assoc.activate();
        }
        assert!(assoc.weight > 0.999);
        assert!(assoc.weight <= 1.0);
    }

    #[test]
    fn decay_reduces_weight_over_time() {
        let mut assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 1.0);
        assoc.decay_half_life_days = 30.0;
        assoc.last_activated_at = Utc::now() - chrono::Duration::days(30);

        assoc.decay(Utc::now());
        // After one half-life, weight should be ~0.5
        assert!((assoc.weight - 0.5).abs() < 0.01);
    }

    #[test]
    fn decay_zero_time_is_noop() {
        let mut assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.7);
        let w = assoc.weight;
        assoc.decay(Utc::now());
        assert!((assoc.weight - w).abs() < f32::EPSILON);
    }

    #[test]
    fn decay_uses_per_link_half_life() {
        let mut short = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 1.0);
        short.decay_half_life_days = 7.0;
        short.last_activated_at = Utc::now() - chrono::Duration::days(7);

        let mut long = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 1.0);
        long.decay_half_life_days = 365.0;
        long.last_activated_at = Utc::now() - chrono::Duration::days(7);

        short.decay(Utc::now());
        long.decay(Utc::now());
        assert!(short.weight < long.weight);
    }

    #[test]
    fn should_prune_detects_low_weight() {
        let assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.05);
        assert!(assoc.should_prune(0.1));
        assert!(!assoc.should_prune(0.01));
    }

    #[test]
    fn with_half_life_days_clamps_to_min_1() {
        let assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Related, 0.5)
            .with_half_life_days(0.1);
        assert!((assoc.decay_half_life_days - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn serde_backward_compat_missing_hebbian_fields() {
        // Old-format association without Phase 6.2 fields
        let old_json = serde_json::json!({
            "source": Uuid::new_v4().to_string(),
            "target": Uuid::new_v4().to_string(),
            "association_type": "related",
            "weight": 0.5,
            "created_at": "2025-01-01T00:00:00Z",
        });

        let assoc: Association = serde_json::from_value(old_json).unwrap();
        assert_eq!(assoc.link_type, LinkType::Related);
        assert_eq!(assoc.co_activation_count, 0);
        assert!((assoc.decay_half_life_days - 90.0).abs() < f32::EPSILON);
    }

    #[test]
    fn msgpack_roundtrip_preserves_hebbian_fields() {
        let mut assoc = Association::new(Uuid::new_v4(), Uuid::new_v4(), LinkType::Causal, 0.6)
            .with_half_life_days(14.0);
        assoc.activate();
        assoc.activate();

        let bytes = rmp_serde::to_vec(&assoc).unwrap();
        let back: Association = rmp_serde::from_slice(&bytes).unwrap();

        assert_eq!(back.link_type, LinkType::Causal);
        assert_eq!(back.association_type, "causal");
        assert!((back.weight - assoc.weight).abs() < 1e-5);
        assert_eq!(back.co_activation_count, 2);
        assert!((back.decay_half_life_days - 14.0).abs() < f32::EPSILON);
    }

    #[test]
    fn lmdb_roundtrip_preserves_hebbian_fields() {
        let (_tmp, env, store) = open_store();
        let src = Uuid::new_v4();
        let tgt = Uuid::new_v4();

        let mut assoc =
            Association::new(src, tgt, LinkType::Contradicts, 0.4).with_half_life_days(7.0);
        assoc.activate();

        store.put(&env, &assoc).unwrap();
        let back = store.get(&env, src, tgt).unwrap().unwrap();

        assert_eq!(back.link_type, LinkType::Contradicts);
        assert_eq!(back.association_type, "contradicts");
        assert_eq!(back.co_activation_count, 1);
        assert!((back.decay_half_life_days - 7.0).abs() < f32::EPSILON);
    }

    #[test]
    fn find_cycles_detects_circular_links() {
        let (_tmp, env, store) = open_store();
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();

        // Create circular: A→B and B→A
        store
            .put(&env, &Association::new(a, b, LinkType::Related, 1.0))
            .unwrap();
        store
            .put(&env, &Association::new(b, a, LinkType::Related, 1.0))
            .unwrap();

        let cycles = store.find_cycles(&env).unwrap();
        assert_eq!(cycles.len(), 1, "Should detect one cycle pair");
        let (s, t) = cycles[0];
        // The pair should be (min(a,b), max(a,b)) due to s < t filter
        assert!(s < t);
        assert!((s == a && t == b) || (s == b && t == a));
    }

    #[test]
    fn find_cycles_no_cycles_when_unidirectional() {
        let (_tmp, env, store) = open_store();
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        let c = Uuid::new_v4();

        // Only unidirectional links — no cycles
        store
            .put(&env, &Association::new(a, b, LinkType::Related, 0.5))
            .unwrap();
        store
            .put(&env, &Association::new(b, c, LinkType::Causal, 0.7))
            .unwrap();
        store
            .put(&env, &Association::new(a, c, LinkType::Extends, 0.3))
            .unwrap();

        let cycles = store.find_cycles(&env).unwrap();
        assert!(
            cycles.is_empty(),
            "Unidirectional links should not be cycles"
        );
    }

    #[test]
    fn find_cycles_detects_multiple_cycles() {
        let (_tmp, env, store) = open_store();
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        let c = Uuid::new_v4();
        let d = Uuid::new_v4();

        // Two separate cycles: A↔B and C↔D
        store
            .put(&env, &Association::new(a, b, LinkType::Related, 0.5))
            .unwrap();
        store
            .put(&env, &Association::new(b, a, LinkType::Related, 0.5))
            .unwrap();
        store
            .put(&env, &Association::new(c, d, LinkType::Related, 0.5))
            .unwrap();
        store
            .put(&env, &Association::new(d, c, LinkType::Related, 0.5))
            .unwrap();

        let cycles = store.find_cycles(&env).unwrap();
        assert_eq!(cycles.len(), 2, "Should detect two cycle pairs");
    }

    #[test]
    fn find_cycles_empty_store() {
        let (_tmp, env, store) = open_store();
        let cycles = store.find_cycles(&env).unwrap();
        assert!(cycles.is_empty());
    }
}
