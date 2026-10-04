//! Associative Tuple Space for microsecond inter-agent generative coordination.
//!
//! Based on David Gelernter's Linda coordination model (1985), agents coordinate
//! via atomic operations on typed data tuples (`out`, `in`, `rd`) residing in memory or `/dev/shm`,
//! bypassing natural language chat serialization for operational handshakes.

use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use uuid::Uuid;

/// Typed payload categories for coordination tuples.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TupleKind {
    /// Mutual exclusion or resource reservation claim.
    Claim {
        resource: String,
        holder: String,
        ttl_ms: u64,
    },
    /// Operational task dispatch.
    Task {
        task_id: Uuid,
        action: String,
        target: String,
        #[serde(with = "serde_bytes_vec")]
        payload: Vec<u8>,
    },
    /// Counterfactual authority and capability grant.
    AuthorityGrant {
        task_id: Uuid,
        granter: String,
        capability_mask: u64,
        #[serde(with = "serde_token_32")]
        landlock_token: [u8; 32],
    },
    /// Execution result and certification notice.
    ResultNotice {
        task_id: Uuid,
        success: bool,
        output_summary: String,
        duration_ms: u64,
    },
    /// Direct stigmergic sync tuple.
    PheromoneSync {
        resource: String,
        intensity: f64,
        issuer: String,
    },
    /// Generic string-tagged tuple.
    Generic {
        tag: String,
        payload: String,
    },
}

mod serde_bytes_vec {
    use super::hex;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(bytes: &Vec<u8>, s: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if s.is_human_readable() {
            s.serialize_str(&hex::encode(bytes))
        } else {
            bytes.serialize(s)
        }
    }

    pub fn deserialize<'de, D>(d: D) -> Result<Vec<u8>, D::Error>
    where
        D: Deserializer<'de>,
    {
        if d.is_human_readable() {
            let s = String::deserialize(d)?;
            hex::decode(&s).map_err(serde::de::Error::custom)
        } else {
            Vec::<u8>::deserialize(d)
        }
    }
}

mod serde_token_32 {
    use super::hex;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(token: &[u8; 32], s: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if s.is_human_readable() {
            s.serialize_str(&hex::encode(token))
        } else {
            token.serialize(s)
        }
    }

    pub fn deserialize<'de, D>(d: D) -> Result<[u8; 32], D::Error>
    where
        D: Deserializer<'de>,
    {
        if d.is_human_readable() {
            let s = String::deserialize(d)?;
            let vec = hex::decode(&s).map_err(serde::de::Error::custom)?;
            if vec.len() != 32 {
                return Err(serde::de::Error::custom("expected 32 bytes for landlock_token"));
            }
            let mut arr = [0u8; 32];
            arr.copy_from_slice(&vec);
            Ok(arr)
        } else {
            <[u8; 32]>::deserialize(d)
        }
    }
}

// Minimal hex helper without pulling extra dependencies
mod hex {
    pub fn encode(data: &[u8]) -> String {
        let mut s = String::with_capacity(data.len() * 2);
        for &b in data {
            s.push_str(&format!("{b:02x}"));
        }
        s
    }

    pub fn decode(s: &str) -> Result<Vec<u8>, &'static str> {
        if s.len() % 2 != 0 {
            return Err("odd hex string length");
        }
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|_| "invalid hex char"))
            .collect()
    }
}

/// A single typed tuple in the tuple space.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Tuple {
    /// Unique identifier for this tuple.
    pub id: Uuid,
    /// Typed kind and payload.
    pub kind: TupleKind,
    /// Unix creation timestamp in milliseconds.
    pub created_at_ms: u64,
    /// Unix expiration timestamp in milliseconds (0 = indefinite).
    pub expires_at_ms: u64,
}

impl Tuple {
    /// Creates a new tuple with the given kind and time-to-live in milliseconds.
    pub fn new(kind: TupleKind, ttl_ms: u64) -> Self {
        let now_ms = Utc::now().timestamp_millis().max(0) as u64;
        let expires_at_ms = if ttl_ms == 0 { 0 } else { now_ms + ttl_ms };
        Self {
            id: Uuid::new_v4(),
            kind,
            created_at_ms: now_ms,
            expires_at_ms,
        }
    }

    /// Checks if the tuple has expired.
    #[must_use]
    pub fn is_expired(&self, now_ms: u64) -> bool {
        self.expires_at_ms > 0 && now_ms > self.expires_at_ms
    }
}

/// Associative query pattern for matching tuples.
#[derive(Debug, Clone, Default)]
pub struct TuplePattern {
    /// Match specific kind discriminator.
    pub kind_filter: Option<String>,
    /// Match resource exact or prefix.
    pub resource_match: Option<String>,
    /// Match holder or issuer.
    pub holder_match: Option<String>,
    /// Match specific task ID.
    pub task_id_match: Option<Uuid>,
    /// Match generic tag.
    pub tag_match: Option<String>,
}

impl TuplePattern {
    /// Match any claim.
    pub fn any_claim() -> Self {
        Self {
            kind_filter: Some("Claim".into()),
            ..Default::default()
        }
    }

    /// Match a claim for a specific resource.
    pub fn claim_for(resource: impl Into<String>) -> Self {
        Self {
            kind_filter: Some("Claim".into()),
            resource_match: Some(resource.into()),
            ..Default::default()
        }
    }

    /// Match any task for a target resource.
    pub fn task_for(target: impl Into<String>) -> Self {
        Self {
            kind_filter: Some("Task".into()),
            resource_match: Some(target.into()),
            ..Default::default()
        }
    }

    /// Match an authority grant for a specific task ID.
    pub fn authority_for_task(task_id: Uuid) -> Self {
        Self {
            kind_filter: Some("AuthorityGrant".into()),
            task_id_match: Some(task_id),
            ..Default::default()
        }
    }

    /// Match a result notice for a specific task ID.
    pub fn result_for_task(task_id: Uuid) -> Self {
        Self {
            kind_filter: Some("ResultNotice".into()),
            task_id_match: Some(task_id),
            ..Default::default()
        }
    }

    /// Tests whether a tuple satisfies this pattern.
    #[must_use]
    pub fn matches(&self, tuple: &Tuple) -> bool {
        match &tuple.kind {
            TupleKind::Claim { resource, holder, .. } => {
                if let Some(kf) = &self.kind_filter {
                    if kf != "Claim" {
                        return false;
                    }
                }
                if let Some(rm) = &self.resource_match {
                    if !resource.starts_with(rm) && resource != rm {
                        return false;
                    }
                }
                if let Some(hm) = &self.holder_match {
                    if holder != hm {
                        return false;
                    }
                }
                true
            }
            TupleKind::Task { task_id, target, .. } => {
                if let Some(kf) = &self.kind_filter {
                    if kf != "Task" {
                        return false;
                    }
                }
                if let Some(tm) = &self.task_id_match {
                    if task_id != tm {
                        return false;
                    }
                }
                if let Some(rm) = &self.resource_match {
                    if !target.starts_with(rm) && target != rm {
                        return false;
                    }
                }
                true
            }
            TupleKind::AuthorityGrant { task_id, granter, .. } => {
                if let Some(kf) = &self.kind_filter {
                    if kf != "AuthorityGrant" {
                        return false;
                    }
                }
                if let Some(tm) = &self.task_id_match {
                    if task_id != tm {
                        return false;
                    }
                }
                if let Some(hm) = &self.holder_match {
                    if granter != hm {
                        return false;
                    }
                }
                true
            }
            TupleKind::ResultNotice { task_id, .. } => {
                if let Some(kf) = &self.kind_filter {
                    if kf != "ResultNotice" {
                        return false;
                    }
                }
                if let Some(tm) = &self.task_id_match {
                    if task_id != tm {
                        return false;
                    }
                }
                true
            }
            TupleKind::PheromoneSync { resource, issuer, .. } => {
                if let Some(kf) = &self.kind_filter {
                    if kf != "PheromoneSync" {
                        return false;
                    }
                }
                if let Some(rm) = &self.resource_match {
                    if !resource.starts_with(rm) && resource != rm {
                        return false;
                    }
                }
                if let Some(hm) = &self.holder_match {
                    if issuer != hm {
                        return false;
                    }
                }
                true
            }
            TupleKind::Generic { tag, .. } => {
                if let Some(kf) = &self.kind_filter {
                    if kf != "Generic" {
                        return false;
                    }
                }
                if let Some(tm) = &self.tag_match {
                    if tag != tm {
                        return false;
                    }
                }
                true
            }
        }
    }
}

/// The Linda associative tuple space.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TupleSpace {
    tuples: Vec<Tuple>,
}

impl TupleSpace {
    /// Creates an empty tuple space.
    pub fn new() -> Self {
        Self { tuples: Vec::new() }
    }

    /// Linda `out(tuple)`: Non-blocking atomic deposit of a tuple into the space.
    pub fn out(&mut self, tuple: Tuple) -> Uuid {
        let id = tuple.id;
        self.tuples.push(tuple);
        id
    }

    /// Linda `in(pattern)`: Atomically extracts and removes the first matching unexpired tuple.
    pub fn in_matching(&mut self, pattern: &TuplePattern, now_ms: u64) -> Option<Tuple> {
        let idx = self.tuples.iter().position(|t| !t.is_expired(now_ms) && pattern.matches(t))?;
        Some(self.tuples.remove(idx))
    }

    /// Linda `rd(pattern)`: Non-destructively reads all unexpired tuples matching the pattern.
    pub fn rd_matching(&self, pattern: &TuplePattern, now_ms: u64) -> Vec<Tuple> {
        self.tuples
            .iter()
            .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
            .cloned()
            .collect()
    }

    /// Counts active matching tuples.
    pub fn count(&self, pattern: &TuplePattern, now_ms: u64) -> usize {
        self.tuples
            .iter()
            .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
            .count()
    }

    /// Purges all expired tuples.
    pub fn purge_expired(&mut self, now_ms: u64) -> usize {
        let before = self.tuples.len();
        self.tuples.retain(|t| !t.is_expired(now_ms));
        before - self.tuples.len()
    }

    /// Returns the total number of tuples currently in the space.
    pub fn len(&self) -> usize {
        self.tuples.len()
    }

    /// Checks if the space is empty.
    pub fn is_empty(&self) -> bool {
        self.tuples.is_empty()
    }

    /// Serializes to JSON.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }

    /// Deserializes from JSON.
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    /// Serializes to binary MessagePack using `rmp_serde`.
    pub fn to_msgpack(&self) -> Result<Vec<u8>, rmp_serde::encode::Error> {
        rmp_serde::to_vec(self)
    }

    /// Deserializes from binary MessagePack.
    pub fn from_msgpack(bytes: &[u8]) -> Result<Self, rmp_serde::decode::Error> {
        rmp_serde::from_slice(bytes)
    }

    /// Loads the tuple space from a shared memory or disk file.
    pub fn load_from_path(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref();
        if !path.exists() {
            return Ok(Self::new());
        }
        let data = std::fs::read(path)?;
        // Try MessagePack first, fallback to JSON
        if let Ok(space) = Self::from_msgpack(&data) {
            Ok(space)
        } else if let Ok(json) = std::str::from_utf8(&data) {
            Self::from_json(json).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
        } else {
            Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "unrecognized tuple space format"))
        }
    }

    /// Atomically persists the tuple space to a shared memory path or disk file.
    pub fn save_to_path(&self, path: impl AsRef<Path>, binary_msgpack: bool) -> std::io::Result<()> {
        let path = path.as_ref();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let bytes = if binary_msgpack {
            self.to_msgpack()
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?
        } else {
            self.to_json()
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?
                .into_bytes()
        };
        let tmp_path = PathBuf::from(format!("{}.tmp.{}", path.display(), Uuid::new_v4()));
        std::fs::write(&tmp_path, bytes)?;
        std::fs::rename(tmp_path, path)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tuple_space_lifecycle() {
        let now = 100_000;
        let mut space = TupleSpace::new();

        // 1. Agent A deposits an exclusive file Claim
        let claim_tuple = Tuple {
            id: Uuid::new_v4(),
            kind: TupleKind::Claim {
                resource: "SharedWorkspace/bridge.py".into(),
                holder: "opencode".into(),
                ttl_ms: 30_000,
            },
            created_at_ms: now,
            expires_at_ms: now + 30_000,
        };
        space.out(claim_tuple);

        // 2. Querying claims
        assert_eq!(space.count(&TuplePattern::any_claim(), now), 1);
        let rd_claims = space.rd_matching(&TuplePattern::claim_for("SharedWorkspace/bridge.py"), now);
        assert_eq!(rd_claims.len(), 1);

        // 3. Agent B dispatches a Task
        let task_id = Uuid::new_v4();
        let task_tuple = Tuple {
            id: Uuid::new_v4(),
            kind: TupleKind::Task {
                task_id,
                action: "verify_endpoint".into(),
                target: "SharedWorkspace/bridge.py".into(),
                payload: b"/api/rooms".to_vec(),
            },
            created_at_ms: now,
            expires_at_ms: now + 60_000,
        };
        space.out(task_tuple);

        // 4. Agent A takes the Task (in_matching) -> atomic consumption
        let taken = space.in_matching(&TuplePattern::task_for("SharedWorkspace/bridge.py"), now);
        assert!(taken.is_some());
        let taken_tuple = taken.unwrap();
        if let TupleKind::Task { task_id: tid, action, .. } = taken_tuple.kind {
            assert_eq!(tid, task_id);
            assert_eq!(action, "verify_endpoint");
        } else {
            panic!("Expected Task tuple");
        }

        // Now task is gone from the space
        assert_eq!(space.count(&TuplePattern::task_for("SharedWorkspace/bridge.py"), now), 0);

        // 5. Expiration purge
        assert_eq!(space.len(), 1); // claim is still there
        let purged = space.purge_expired(now + 40_000);
        assert_eq!(purged, 1);
        assert_eq!(space.len(), 0);
    }

    #[test]
    fn test_msgpack_roundtrip() {
        let mut space = TupleSpace::new();
        let tuple = Tuple::new(
            TupleKind::AuthorityGrant {
                task_id: Uuid::new_v4(),
                granter: "antigravity".into(),
                capability_mask: 0b1101,
                landlock_token: [7u8; 32],
            },
            60_000,
        );
        space.out(tuple);

        let bytes = space.to_msgpack().expect("serialization should succeed");
        let decoded = TupleSpace::from_msgpack(&bytes).expect("deserialization should succeed");
        assert_eq!(decoded.len(), 1);
    }
}
