//! Associative Tuple Space for microsecond inter-agent generative coordination.
//!
//! Based on David Gelernter's Linda coordination model (1985), agents coordinate
//! via atomic operations on typed data tuples (`out`, `in`, `rd`) residing in memory or `/dev/shm`,
//! bypassing natural language chat serialization for operational handshakes.

use serde::ser::{SerializeSeq, SerializeStruct};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::ops::Bound;
use std::path::{Path, PathBuf};
use uuid::Uuid;

use crate::temporal::utc_now_millis;

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
    Generic { tag: String, payload: String },
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
                return Err(serde::de::Error::custom(
                    "expected 32 bytes for landlock_token",
                ));
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
        let now_ms = utc_now_millis();
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

    /// Convert to RawTuple for zero-copy POSIX shared memory substrate.
    pub fn to_raw(&self) -> wm_gen3_shm::RawTuple {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let (
            kind_discriminator,
            resource_path,
            tag,
            payload,
            landlock_token,
            capability_mask,
            holder_issuer,
        ) = match &self.kind {
            TupleKind::Claim {
                resource, holder, ..
            } => (
                1,
                resource.clone(),
                "claim:exclusive".to_string(),
                Vec::new(),
                [0u8; 32],
                0,
                holder.clone(),
            ),
            TupleKind::Task {
                task_id: _,
                action,
                target,
                payload,
            } => (
                2,
                target.clone(),
                format!("task:{action}"),
                payload.clone(),
                [0u8; 32],
                0,
                String::new(),
            ),
            TupleKind::AuthorityGrant {
                task_id: _,
                granter,
                capability_mask,
                landlock_token,
            } => (
                3,
                String::new(),
                "authority:grant".to_string(),
                Vec::new(),
                *landlock_token,
                *capability_mask,
                granter.clone(),
            ),
            TupleKind::ResultNotice {
                task_id: _,
                success,
                output_summary,
                duration_ms,
            } => {
                let payload_bytes =
                    serde_json::to_vec(&(success, duration_ms, output_summary)).unwrap_or_default();
                (
                    4,
                    String::new(),
                    "result:notice".to_string(),
                    payload_bytes,
                    [0u8; 32],
                    0,
                    String::new(),
                )
            }
            TupleKind::PheromoneSync {
                resource,
                intensity,
                issuer,
            } => {
                let payload_bytes = intensity.to_le_bytes().to_vec();
                (
                    5,
                    resource.clone(),
                    "pheromone:sync".to_string(),
                    payload_bytes,
                    [0u8; 32],
                    0,
                    issuer.clone(),
                )
            }
            TupleKind::Generic { tag, payload } => (
                6,
                String::new(),
                tag.clone(),
                payload.as_bytes().to_vec(),
                [0u8; 32],
                0,
                String::new(),
            ),
        };

        let mut r_hasher = DefaultHasher::new();
        resource_path.hash(&mut r_hasher);
        let resource_hash = r_hasher.finish();

        let mut h_hasher = DefaultHasher::new();
        holder_issuer.hash(&mut h_hasher);
        let holder_issuer_hash = h_hasher.finish();

        wm_gen3_shm::RawTuple {
            id: self.id,
            kind_discriminator,
            resource_hash,
            holder_issuer_hash,
            resource_path,
            tag,
            payload,
            created_at_ms: self.created_at_ms,
            expires_at_ms: self.expires_at_ms,
            landlock_token,
            capability_mask,
        }
    }

    /// Construct Tuple from RawTuple.
    pub fn from_raw(raw: &wm_gen3_shm::RawTuple) -> Self {
        let kind = match raw.kind_discriminator {
            1 => TupleKind::Claim {
                resource: raw.resource_path.clone(),
                holder: String::new(),
                ttl_ms: raw.expires_at_ms.saturating_sub(raw.created_at_ms),
            },
            2 => {
                let action = raw
                    .tag
                    .strip_prefix("task:")
                    .unwrap_or(&raw.tag)
                    .to_string();
                TupleKind::Task {
                    task_id: raw.id,
                    action,
                    target: raw.resource_path.clone(),
                    payload: raw.payload.clone(),
                }
            }
            3 => TupleKind::AuthorityGrant {
                task_id: raw.id,
                granter: String::new(),
                capability_mask: raw.capability_mask,
                landlock_token: raw.landlock_token,
            },
            4 => {
                if let Ok((success, duration_ms, output_summary)) =
                    serde_json::from_slice::<(bool, u64, String)>(&raw.payload)
                {
                    TupleKind::ResultNotice {
                        task_id: raw.id,
                        success,
                        output_summary,
                        duration_ms,
                    }
                } else {
                    TupleKind::ResultNotice {
                        task_id: raw.id,
                        success: true,
                        output_summary: String::from_utf8_lossy(&raw.payload).into_owned(),
                        duration_ms: 0,
                    }
                }
            }
            5 => {
                let intensity = if raw.payload.len() >= 8 {
                    let mut b = [0u8; 8];
                    b.copy_from_slice(&raw.payload[..8]);
                    f64::from_le_bytes(b)
                } else {
                    1.0
                };
                TupleKind::PheromoneSync {
                    resource: raw.resource_path.clone(),
                    intensity,
                    issuer: String::new(),
                }
            }
            _ => TupleKind::Generic {
                tag: raw.tag.clone(),
                payload: String::from_utf8_lossy(&raw.payload).into_owned(),
            },
        };

        Tuple {
            id: raw.id,
            kind,
            created_at_ms: raw.created_at_ms,
            expires_at_ms: raw.expires_at_ms,
        }
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
            TupleKind::Claim {
                resource, holder, ..
            } => {
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
            TupleKind::Task {
                task_id, target, ..
            } => {
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
            TupleKind::AuthorityGrant {
                task_id, granter, ..
            } => {
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
            TupleKind::PheromoneSync {
                resource, issuer, ..
            } => {
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

/// The Linda associative tuple space with secondary indexes and O(1) FIFO tombstone head.
#[derive(Debug, Clone, Default, Deserialize)]
#[serde(from = "TupleSpaceSerde")]
pub struct TupleSpace {
    slots: Vec<Option<Tuple>>,
    live_count: usize,
    head: usize,
    by_resource: BTreeMap<String, Vec<usize>>,
    by_task_id: HashMap<Uuid, Vec<usize>>,
    by_tag: HashMap<String, Vec<usize>>,
}

#[derive(Deserialize)]
struct TupleSpaceSerde {
    tuples: Vec<Tuple>,
}

struct LiveTuples<'a>(&'a [Option<Tuple>]);

impl Serialize for LiveTuples<'_> {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let count = self.0.iter().filter(|s| s.is_some()).count();
        let mut seq = serializer.serialize_seq(Some(count))?;
        for t in self.0.iter().flatten() {
            seq.serialize_element(t)?;
        }
        seq.end()
    }
}

impl Serialize for TupleSpace {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let mut st = serializer.serialize_struct("TupleSpace", 1)?;
        let slice = self.slots.get(self.head..).unwrap_or(&[]);
        st.serialize_field("tuples", &LiveTuples(slice))?;
        st.end()
    }
}

impl From<TupleSpaceSerde> for TupleSpace {
    fn from(raw: TupleSpaceSerde) -> Self {
        let mut space = Self {
            slots: raw.tuples.into_iter().map(Some).collect(),
            live_count: 0,
            head: 0,
            by_resource: BTreeMap::new(),
            by_task_id: HashMap::new(),
            by_tag: HashMap::new(),
        };
        space.live_count = space.slots.len();
        for idx in 0..space.slots.len() {
            space.index_slot(idx);
        }
        space
    }
}

impl TupleSpace {
    /// Creates an empty tuple space.
    pub fn new() -> Self {
        Self {
            slots: Vec::new(),
            live_count: 0,
            head: 0,
            by_resource: BTreeMap::new(),
            by_task_id: HashMap::new(),
            by_tag: HashMap::new(),
        }
    }

    fn insert_resource_index(
        by_resource: &mut BTreeMap<String, Vec<usize>>,
        key: &str,
        idx: usize,
    ) {
        if let Some(bucket) = by_resource.get_mut(key) {
            bucket.push(idx);
        } else {
            by_resource.insert(key.to_owned(), vec![idx]);
        }
    }

    fn insert_tag_index(by_tag: &mut HashMap<String, Vec<usize>>, key: &str, idx: usize) {
        if let Some(bucket) = by_tag.get_mut(key) {
            bucket.push(idx);
        } else {
            by_tag.insert(key.to_owned(), vec![idx]);
        }
    }

    fn index_slot(&mut self, idx: usize) {
        let Some(tuple) = self.slots[idx].as_ref() else {
            return;
        };
        match &tuple.kind {
            TupleKind::Claim { resource, .. } | TupleKind::PheromoneSync { resource, .. } => {
                Self::insert_resource_index(&mut self.by_resource, resource, idx);
            }
            TupleKind::Task {
                task_id, target, ..
            } => {
                Self::insert_resource_index(&mut self.by_resource, target, idx);
                self.by_task_id.entry(*task_id).or_default().push(idx);
            }
            TupleKind::AuthorityGrant { task_id, .. } | TupleKind::ResultNotice { task_id, .. } => {
                self.by_task_id.entry(*task_id).or_default().push(idx);
            }
            TupleKind::Generic { tag, .. } => {
                Self::insert_tag_index(&mut self.by_tag, tag, idx);
            }
        }
    }

    fn advance_head(&mut self) {
        while self.slots.get(self.head).is_some_and(Option::is_none) {
            self.head += 1;
        }
    }

    fn reset_empty(&mut self) {
        self.slots.clear();
        self.live_count = 0;
        self.head = 0;
        self.by_resource.clear();
        self.by_task_id.clear();
        self.by_tag.clear();
    }

    fn compact(&mut self) {
        if self.live_count == 0 {
            self.reset_empty();
            return;
        }
        let mut compacted = Vec::with_capacity(self.live_count);
        for slot in self.slots.drain(self.head..) {
            if slot.is_some() {
                compacted.push(slot);
            }
        }
        self.slots = compacted;
        self.head = 0;
        self.by_resource.clear();
        self.by_task_id.clear();
        self.by_tag.clear();
        for idx in 0..self.slots.len() {
            self.index_slot(idx);
        }
    }

    fn can_use_resource_index(pattern: &TuplePattern) -> bool {
        pattern.resource_match.is_some()
            && matches!(
                pattern.kind_filter.as_deref(),
                Some("Claim" | "Task" | "PheromoneSync")
            )
    }

    fn can_use_task_id_index(pattern: &TuplePattern) -> bool {
        pattern.task_id_match.is_some()
            && matches!(
                pattern.kind_filter.as_deref(),
                Some("Task" | "AuthorityGrant" | "ResultNotice")
            )
    }

    fn can_use_tag_index(pattern: &TuplePattern) -> bool {
        pattern.tag_match.is_some() && pattern.kind_filter.as_deref() == Some("Generic")
    }

    /// Linda `out(tuple)`: Non-blocking atomic deposit of a tuple into the space.
    pub fn out(&mut self, tuple: Tuple) -> Uuid {
        let id = tuple.id;
        let idx = self.slots.len();
        self.slots.push(Some(tuple));
        self.live_count += 1;
        self.index_slot(idx);
        id
    }

    /// Linda `in(pattern)`: Atomically extracts and removes the first matching unexpired tuple.
    pub fn in_matching(&mut self, pattern: &TuplePattern, now_ms: u64) -> Option<Tuple> {
        let found_idx = if Self::can_use_resource_index(pattern) {
            let rm = pattern.resource_match.as_deref().unwrap_or("");
            let mut best: Option<usize> = None;
            for (_, indices) in self
                .by_resource
                .range::<str, _>((Bound::Included(rm), Bound::Unbounded))
                .take_while(|(k, _)| k.starts_with(rm))
            {
                for &idx in indices {
                    if let Some(best_idx) = best {
                        if idx >= best_idx {
                            break;
                        }
                    }
                    if let Some(t) = self.slots.get(idx).and_then(Option::as_ref) {
                        if !t.is_expired(now_ms) && pattern.matches(t) {
                            best = Some(idx);
                            break;
                        }
                    }
                }
            }
            best
        } else if Self::can_use_task_id_index(pattern) {
            pattern.task_id_match.and_then(|tid| {
                self.by_task_id.get(&tid).and_then(|indices| {
                    indices.iter().copied().find(|&idx| {
                        self.slots
                            .get(idx)
                            .and_then(Option::as_ref)
                            .is_some_and(|t| !t.is_expired(now_ms) && pattern.matches(t))
                    })
                })
            })
        } else if Self::can_use_tag_index(pattern) {
            pattern.tag_match.as_deref().and_then(|tag| {
                self.by_tag.get(tag).and_then(|indices| {
                    indices.iter().copied().find(|&idx| {
                        self.slots
                            .get(idx)
                            .and_then(Option::as_ref)
                            .is_some_and(|t| !t.is_expired(now_ms) && pattern.matches(t))
                    })
                })
            })
        } else {
            self.slots
                .iter()
                .enumerate()
                .skip(self.head)
                .find_map(|(idx, slot)| {
                    slot.as_ref()
                        .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
                        .map(|_| idx)
                })
        }?;

        let taken = self.slots[found_idx].take()?;
        self.live_count -= 1;
        if found_idx == self.head {
            self.advance_head();
        }
        if self.live_count == 0 {
            self.reset_empty();
        } else if self.slots.len() > 2048 && self.live_count * 4 < self.slots.len() {
            self.compact();
        }
        Some(taken)
    }

    /// Linda `rd(pattern)`: Non-destructively reads all unexpired tuples matching the pattern.
    pub fn rd_matching(&self, pattern: &TuplePattern, now_ms: u64) -> Vec<Tuple> {
        if Self::can_use_resource_index(pattern) {
            let rm = pattern.resource_match.as_deref().unwrap_or("");
            let mut matched_buckets = self
                .by_resource
                .range::<str, _>((Bound::Included(rm), Bound::Unbounded))
                .take_while(|(k, _)| k.starts_with(rm))
                .map(|(_, indices)| indices);
            let Some(first_bucket) = matched_buckets.next() else {
                return Vec::new();
            };
            if let Some(second_bucket) = matched_buckets.next() {
                let mut matched_indices = Vec::new();
                for bucket in std::iter::once(first_bucket)
                    .chain(std::iter::once(second_bucket))
                    .chain(matched_buckets)
                {
                    for &idx in bucket {
                        if let Some(t) = self.slots.get(idx).and_then(Option::as_ref) {
                            if !t.is_expired(now_ms) && pattern.matches(t) {
                                matched_indices.push(idx);
                            }
                        }
                    }
                }
                matched_indices.sort_unstable();
                return matched_indices
                    .into_iter()
                    .filter_map(|idx| self.slots[idx].clone())
                    .collect();
            }
            return first_bucket
                .iter()
                .filter_map(|&idx| {
                    self.slots
                        .get(idx)
                        .and_then(Option::as_ref)
                        .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
                        .cloned()
                })
                .collect();
        }
        if Self::can_use_task_id_index(pattern) {
            return pattern
                .task_id_match
                .and_then(|tid| self.by_task_id.get(&tid))
                .map(|indices| {
                    indices
                        .iter()
                        .filter_map(|&idx| {
                            self.slots
                                .get(idx)
                                .and_then(Option::as_ref)
                                .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
                                .cloned()
                        })
                        .collect()
                })
                .unwrap_or_default();
        }
        if Self::can_use_tag_index(pattern) {
            return pattern
                .tag_match
                .as_deref()
                .and_then(|tag| self.by_tag.get(tag))
                .map(|indices| {
                    indices
                        .iter()
                        .filter_map(|&idx| {
                            self.slots
                                .get(idx)
                                .and_then(Option::as_ref)
                                .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
                                .cloned()
                        })
                        .collect()
                })
                .unwrap_or_default();
        }
        self.slots
            .get(self.head..)
            .unwrap_or(&[])
            .iter()
            .filter_map(|slot| slot.as_ref())
            .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
            .cloned()
            .collect()
    }

    /// Counts active matching tuples.
    pub fn count(&self, pattern: &TuplePattern, now_ms: u64) -> usize {
        if Self::can_use_resource_index(pattern) {
            let rm = pattern.resource_match.as_deref().unwrap_or("");
            let mut n = 0usize;
            for (_, indices) in self
                .by_resource
                .range::<str, _>((Bound::Included(rm), Bound::Unbounded))
                .take_while(|(k, _)| k.starts_with(rm))
            {
                for &idx in indices {
                    if let Some(t) = self.slots.get(idx).and_then(Option::as_ref) {
                        if !t.is_expired(now_ms) && pattern.matches(t) {
                            n += 1;
                        }
                    }
                }
            }
            return n;
        }
        if Self::can_use_task_id_index(pattern) {
            return pattern
                .task_id_match
                .and_then(|tid| self.by_task_id.get(&tid))
                .map(|indices| {
                    indices
                        .iter()
                        .filter(|&&idx| {
                            self.slots
                                .get(idx)
                                .and_then(Option::as_ref)
                                .is_some_and(|t| !t.is_expired(now_ms) && pattern.matches(t))
                        })
                        .count()
                })
                .unwrap_or(0);
        }
        if Self::can_use_tag_index(pattern) {
            return pattern
                .tag_match
                .as_deref()
                .and_then(|tag| self.by_tag.get(tag))
                .map(|indices| {
                    indices
                        .iter()
                        .filter(|&&idx| {
                            self.slots
                                .get(idx)
                                .and_then(Option::as_ref)
                                .is_some_and(|t| !t.is_expired(now_ms) && pattern.matches(t))
                        })
                        .count()
                })
                .unwrap_or(0);
        }
        self.slots
            .get(self.head..)
            .unwrap_or(&[])
            .iter()
            .filter_map(|slot| slot.as_ref())
            .filter(|t| !t.is_expired(now_ms) && pattern.matches(t))
            .count()
    }

    /// Purges all expired tuples.
    pub fn purge_expired(&mut self, now_ms: u64) -> usize {
        let mut purged = 0usize;
        for slot in self.slots.get_mut(self.head..).unwrap_or(&mut []) {
            if let Some(t) = slot.as_ref() {
                if t.is_expired(now_ms) {
                    *slot = None;
                    purged += 1;
                }
            }
        }
        if purged > 0 {
            self.live_count -= purged;
            self.compact();
        }
        purged
    }

    /// Returns the total number of tuples currently in the space.
    pub fn len(&self) -> usize {
        self.live_count
    }

    /// Checks if the space is empty.
    pub fn is_empty(&self) -> bool {
        self.live_count == 0
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
            Self::from_json(json)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
        } else {
            Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "unrecognized tuple space format",
            ))
        }
    }

    /// Atomically persists the tuple space to a shared memory path or disk file.
    pub fn save_to_path(
        &self,
        path: impl AsRef<Path>,
        binary_msgpack: bool,
    ) -> std::io::Result<()> {
        let path = path.as_ref();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let bytes = if binary_msgpack {
            self.to_msgpack().map_err(std::io::Error::other)?
        } else {
            self.to_json().map_err(std::io::Error::other)?.into_bytes()
        };
        let tmp_path = PathBuf::from(format!("{}.tmp.{}", path.display(), Uuid::new_v4()));
        std::fs::write(&tmp_path, bytes)?;
        std::fs::rename(tmp_path, path)?;
        Ok(())
    }

    /// Connect to a named zero-copy POSIX shared memory substrate.
    pub fn open_shm(name: &str) -> std::io::Result<wm_gen3_shm::ShmTupleSpace> {
        let substrate = wm_gen3_shm::ShmSubstrate::open_or_create(name)?;
        Ok(wm_gen3_shm::ShmTupleSpace::new(std::sync::Arc::new(
            substrate,
        )))
    }

    /// Attach to an inherited shared memory file descriptor (for Landlock sandboxes).
    #[cfg(unix)]
    pub fn attach_shm_fd(
        fd: std::os::unix::io::RawFd,
        is_owner: bool,
    ) -> std::io::Result<wm_gen3_shm::ShmTupleSpace> {
        let substrate = wm_gen3_shm::ShmSubstrate::from_raw_fd(fd, is_owner)?;
        Ok(wm_gen3_shm::ShmTupleSpace::new(std::sync::Arc::new(
            substrate,
        )))
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
        let rd_claims =
            space.rd_matching(&TuplePattern::claim_for("SharedWorkspace/bridge.py"), now);
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
        if let TupleKind::Task {
            task_id: tid,
            action,
            ..
        } = taken_tuple.kind
        {
            assert_eq!(tid, task_id);
            assert_eq!(action, "verify_endpoint");
        } else {
            panic!("Expected Task tuple");
        }

        // Now task is gone from the space
        assert_eq!(
            space.count(&TuplePattern::task_for("SharedWorkspace/bridge.py"), now),
            0
        );

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

    #[test]
    fn test_indexed_prefix_fifo_and_unfiltered_fallback() {
        let now = 10_000;
        let mut space = TupleSpace::new();
        space.out(Tuple {
            id: Uuid::from_u128(1),
            kind: TupleKind::Claim {
                resource: "crates/a/z.rs".into(),
                holder: "opencode".into(),
                ttl_ms: 60_000,
            },
            created_at_ms: now,
            expires_at_ms: now + 60_000,
        });
        space.out(Tuple {
            id: Uuid::from_u128(2),
            kind: TupleKind::Generic {
                tag: "note".into(),
                payload: "{}".into(),
            },
            created_at_ms: now,
            expires_at_ms: now + 60_000,
        });
        space.out(Tuple {
            id: Uuid::from_u128(3),
            kind: TupleKind::Claim {
                resource: "crates/a/a.rs".into(),
                holder: "opencode".into(),
                ttl_ms: 60_000,
            },
            created_at_ms: now,
            expires_at_ms: now + 60_000,
        });

        // Prefix match across multiple keys preserves exact FIFO insertion order (z.rs before a.rs)
        let pref = TuplePattern::claim_for("crates/a/");
        let rds = space.rd_matching(&pref, now);
        assert_eq!(rds.len(), 2);
        assert_eq!(rds[0].id, Uuid::from_u128(1));
        assert_eq!(rds[1].id, Uuid::from_u128(3));

        // JSON + MessagePack round-trip preserves indexes and counts
        let j = space.to_json().expect("json");
        let mut rt = TupleSpace::from_json(&j).expect("from json");
        assert_eq!(rt.count(&TuplePattern::claim_for("crates/a/"), now), 2);
        let mp = space.to_msgpack().expect("msgpack");
        let rt_mp = TupleSpace::from_msgpack(&mp).expect("from msgpack");
        assert_eq!(rt_mp.count(&TuplePattern::claim_for("crates/a/"), now), 2);
        let first_pop = rt.in_matching(&TuplePattern::claim_for("crates/a/"), now);
        assert_eq!(first_pop.map(|t| t.id), Some(Uuid::from_u128(1)));

        // Pattern without kind_filter still matches Generic tuples identically to TuplePattern::matches
        let kindless = TuplePattern {
            resource_match: Some("crates/".into()),
            ..Default::default()
        };
        assert_eq!(space.count(&kindless, now), 3);
    }
}
