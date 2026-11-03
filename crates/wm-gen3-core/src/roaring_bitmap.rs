//! Sovereign 100% Safe-Rust Roaring Bitmap & Memory Indexing Substrate.
//!
//! Provides compressed, chunked bitset indexing for memory record retrieval,
//! Consent Ring filtering, and Theta/Delta associative dream consolidation.
//!
//! Complies with `#[forbid(unsafe_code)]`. Employs 16-bit chunk container
//! decomposition (sparse `Array` -> dense `Bitset` at cardinality 4,096).

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

const DENSE_THRESHOLD: usize = 4096;
const WORDS_PER_BITSET: usize = 1024; // 1024 * 64 = 65536 bits

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChunkContainer {
    Array(Vec<u16>),
    Bitset(Vec<u64>),
}

impl ChunkContainer {
    pub fn new() -> Self {
        ChunkContainer::Array(Vec::new())
    }

    pub fn cardinality(&self) -> usize {
        match self {
            ChunkContainer::Array(v) => v.len(),
            ChunkContainer::Bitset(words) => words.iter().map(|w| w.count_ones() as usize).sum(),
        }
    }

    pub fn contains(&self, val: u16) -> bool {
        match self {
            ChunkContainer::Array(v) => v.binary_search(&val).is_ok(),
            ChunkContainer::Bitset(words) => {
                let word_idx = (val >> 6) as usize;
                let bit_idx = (val & 0x3F) as usize;
                (words[word_idx] & (1u64 << bit_idx)) != 0
            }
        }
    }

    pub fn insert(&mut self, val: u16) -> bool {
        match self {
            ChunkContainer::Array(v) => match v.binary_search(&val) {
                Ok(_) => false,
                Err(idx) => {
                    v.insert(idx, val);
                    if v.len() >= DENSE_THRESHOLD {
                        self.convert_to_bitset();
                    }
                    true
                }
            },
            ChunkContainer::Bitset(words) => {
                let word_idx = (val >> 6) as usize;
                let bit_idx = (val & 0x3F) as usize;
                let mask = 1u64 << bit_idx;
                if (words[word_idx] & mask) != 0 {
                    false
                } else {
                    words[word_idx] |= mask;
                    true
                }
            }
        }
    }

    pub fn remove(&mut self, val: u16) -> bool {
        match self {
            ChunkContainer::Array(v) => match v.binary_search(&val) {
                Ok(idx) => {
                    v.remove(idx);
                    true
                }
                Err(_) => false,
            },
            ChunkContainer::Bitset(words) => {
                let word_idx = (val >> 6) as usize;
                let bit_idx = (val & 0x3F) as usize;
                let mask = 1u64 << bit_idx;
                if (words[word_idx] & mask) == 0 {
                    false
                } else {
                    words[word_idx] &= !mask;
                    true
                }
            }
        }
    }

    fn convert_to_bitset(&mut self) {
        if let ChunkContainer::Array(v) = self {
            let mut words = vec![0u64; WORDS_PER_BITSET];
            for &val in v.iter() {
                let word_idx = (val >> 6) as usize;
                let bit_idx = (val & 0x3F) as usize;
                words[word_idx] |= 1u64 << bit_idx;
            }
            *self = ChunkContainer::Bitset(words);
        }
    }

    pub fn to_vec(&self) -> Vec<u16> {
        match self {
            ChunkContainer::Array(v) => v.clone(),
            ChunkContainer::Bitset(words) => {
                let mut res = Vec::with_capacity(self.cardinality());
                for (w_idx, &w) in words.iter().enumerate() {
                    if w == 0 {
                        continue;
                    }
                    for b in 0..64 {
                        if (w & (1u64 << b)) != 0 {
                            res.push(((w_idx << 6) | b) as u16);
                        }
                    }
                }
                res
            }
        }
    }

    pub fn intersect(&self, other: &Self) -> Self {
        match (self, other) {
            (ChunkContainer::Array(a), ChunkContainer::Array(b)) => {
                let mut out = Vec::new();
                let (mut i, mut j) = (0, 0);
                while i < a.len() && j < b.len() {
                    if a[i] == b[j] {
                        out.push(a[i]);
                        i += 1;
                        j += 1;
                    } else if a[i] < b[j] {
                        i += 1;
                    } else {
                        j += 1;
                    }
                }
                ChunkContainer::Array(out)
            }
            (ChunkContainer::Bitset(wa), ChunkContainer::Bitset(wb)) => {
                let mut words = vec![0u64; WORDS_PER_BITSET];
                for idx in 0..WORDS_PER_BITSET {
                    words[idx] = wa[idx] & wb[idx];
                }
                let mut container = ChunkContainer::Bitset(words);
                if container.cardinality() < DENSE_THRESHOLD {
                    container = ChunkContainer::Array(container.to_vec());
                }
                container
            }
            (ChunkContainer::Array(a), ChunkContainer::Bitset(_)) => {
                let mut out = Vec::new();
                for &val in a {
                    if other.contains(val) {
                        out.push(val);
                    }
                }
                ChunkContainer::Array(out)
            }
            (ChunkContainer::Bitset(_), ChunkContainer::Array(b)) => {
                let mut out = Vec::new();
                for &val in b {
                    if self.contains(val) {
                        out.push(val);
                    }
                }
                ChunkContainer::Array(out)
            }
        }
    }

    pub fn union(&self, other: &Self) -> Self {
        match (self, other) {
            (ChunkContainer::Bitset(wa), ChunkContainer::Bitset(wb)) => {
                let mut words = vec![0u64; WORDS_PER_BITSET];
                for idx in 0..WORDS_PER_BITSET {
                    words[idx] = wa[idx] | wb[idx];
                }
                ChunkContainer::Bitset(words)
            }
            _ => {
                let mut words = vec![0u64; WORDS_PER_BITSET];
                for v in self.to_vec() {
                    let word_idx = (v >> 6) as usize;
                    let bit_idx = (v & 0x3F) as usize;
                    words[word_idx] |= 1u64 << bit_idx;
                }
                for v in other.to_vec() {
                    let word_idx = (v >> 6) as usize;
                    let bit_idx = (v & 0x3F) as usize;
                    words[word_idx] |= 1u64 << bit_idx;
                }
                let container = ChunkContainer::Bitset(words);
                if container.cardinality() < DENSE_THRESHOLD {
                    ChunkContainer::Array(container.to_vec())
                } else {
                    container
                }
            }
        }
    }
}

impl Default for ChunkContainer {
    fn default() -> Self {
        Self::new()
    }
}

/// Sovereign Roaring Bitmap for compact, high-speed set operations across 32-bit integer sets.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct RoaringBitmap {
    pub chunks: BTreeMap<u16, ChunkContainer>,
}

impl RoaringBitmap {
    pub fn new() -> Self {
        Self {
            chunks: BTreeMap::new(),
        }
    }

    pub fn insert(&mut self, val: u32) -> bool {
        let chunk_key = (val >> 16) as u16;
        let chunk_val = (val & 0xFFFF) as u16;
        self.chunks.entry(chunk_key).or_default().insert(chunk_val)
    }

    pub fn contains(&self, val: u32) -> bool {
        let chunk_key = (val >> 16) as u16;
        let chunk_val = (val & 0xFFFF) as u16;
        self.chunks
            .get(&chunk_key)
            .is_some_and(|c| c.contains(chunk_val))
    }

    pub fn remove(&mut self, val: u32) -> bool {
        let chunk_key = (val >> 16) as u16;
        let chunk_val = (val & 0xFFFF) as u16;
        if let Some(c) = self.chunks.get_mut(&chunk_key) {
            let removed = c.remove(chunk_val);
            if c.cardinality() == 0 {
                self.chunks.remove(&chunk_key);
            }
            removed
        } else {
            false
        }
    }

    pub fn cardinality(&self) -> usize {
        self.chunks.values().map(|c| c.cardinality()).sum()
    }

    pub fn is_empty(&self) -> bool {
        self.chunks.is_empty()
    }

    pub fn to_vec(&self) -> Vec<u32> {
        let mut out = Vec::with_capacity(self.cardinality());
        for (&k, container) in &self.chunks {
            let base = (k as u32) << 16;
            for val in container.to_vec() {
                out.push(base | (val as u32));
            }
        }
        out
    }

    pub fn intersect(&self, other: &Self) -> Self {
        let mut out = BTreeMap::new();
        for (&k, c1) in &self.chunks {
            if let Some(c2) = other.chunks.get(&k) {
                let res = c1.intersect(c2);
                if res.cardinality() > 0 {
                    out.insert(k, res);
                }
            }
        }
        Self { chunks: out }
    }

    pub fn union(&self, other: &Self) -> Self {
        let mut out = self.chunks.clone();
        for (&k, c2) in &other.chunks {
            out.entry(k)
                .and_modify(|c1| *c1 = c1.union(c2))
                .or_insert_with(|| c2.clone());
        }
        Self { chunks: out }
    }
}

/// In-memory Roaring Bitmap index for memory records, tags, and consent boundaries.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct RoaringMemoryIndex {
    pub ring0: RoaringBitmap,
    pub ring1: RoaringBitmap,
    pub ring2: RoaringBitmap,
    pub ring3: RoaringBitmap,
    pub tags: BTreeMap<String, RoaringBitmap>,
}

impl RoaringMemoryIndex {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn index_record(&mut self, record_id: u32, consent_ring: u8, tags: &[String]) {
        match consent_ring {
            0 => self.ring0.insert(record_id),
            1 => self.ring1.insert(record_id),
            2 => self.ring2.insert(record_id),
            _ => self.ring3.insert(record_id),
        };
        for t in tags {
            self.tags.entry(t.clone()).or_default().insert(record_id);
        }
    }

    pub fn query_records(&self, required_tags: &[&str], max_ring: u8) -> Vec<u32> {
        if required_tags.is_empty() {
            return Vec::new();
        }

        // Permitted rings union
        let mut permitted = self.ring0.clone();
        if max_ring >= 1 {
            permitted = permitted.union(&self.ring1);
        }
        if max_ring >= 2 {
            permitted = permitted.union(&self.ring2);
        }
        if max_ring >= 3 {
            permitted = permitted.union(&self.ring3);
        }

        let mut matches: Option<RoaringBitmap> = None;
        for &tag in required_tags {
            if let Some(tag_bm) = self.tags.get(tag) {
                matches = Some(match matches {
                    None => tag_bm.clone(),
                    Some(m) => m.intersect(tag_bm),
                });
            } else {
                return Vec::new(); // Required tag has zero records
            }
        }

        matches
            .map(|m| m.intersect(&permitted).to_vec())
            .unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_roaring_bitmap_sparse_to_dense_transition() {
        let mut bm = RoaringBitmap::new();
        // Insert 100 values: should stay Array container
        for i in 0..100 {
            bm.insert(i * 10);
        }
        assert_eq!(bm.cardinality(), 100);
        assert!(bm.contains(500));
        assert!(!bm.contains(501));

        // Push past DENSE_THRESHOLD (4096) in the same chunk (key 0)
        for i in 0..4100 {
            bm.insert(i);
        }
        assert_eq!(bm.cardinality(), 4100);
        assert!(matches!(
            bm.chunks.get(&0).unwrap(),
            ChunkContainer::Bitset(_)
        ));

        // Multi-chunk insertion: chunk key 1 (value >= 65536)
        bm.insert(70000);
        assert_eq!(bm.chunks.len(), 2);
        assert!(bm.contains(70000));
    }

    #[test]
    fn test_roaring_bitmap_set_operations() {
        let mut a = RoaringBitmap::new();
        let mut b = RoaringBitmap::new();

        for i in (0..1000).step_by(2) {
            a.insert(i); // Even numbers 0..998
        }
        for i in (0..1000).step_by(3) {
            b.insert(i); // Multiples of 3 0..999
        }

        let intersection = a.intersect(&b);
        // Multiples of 6
        for v in intersection.to_vec() {
            assert_eq!(v % 6, 0);
        }
        assert_eq!(intersection.cardinality(), 167); // floor(999/6) + 1 = 167

        let union = a.union(&b);
        assert!(union.contains(2));
        assert!(union.contains(3));
        assert!(!union.contains(5));
    }

    #[test]
    fn test_roaring_memory_index_consent_filtering() {
        let mut index = RoaringMemoryIndex::new();
        // Record 1: Ring 1 (Operational), tags: ["landlock", "sandbox"]
        index.index_record(1, 1, &["landlock".into(), "sandbox".into()]);
        // Record 2: Ring 3 (DeepInteriority), tags: ["landlock", "secret"]
        index.index_record(2, 3, &["landlock".into(), "secret".into()]);
        // Record 3: Ring 0 (PublicCommons), tags: ["landlock", "sandbox"]
        index.index_record(3, 0, &["landlock".into(), "sandbox".into()]);

        // Query with max_ring = 1 (Hermit-Crab sealed state)
        let sealed_hits = index.query_records(&["landlock"], 1);
        assert_eq!(sealed_hits, vec![1, 3]); // Record 2 excluded by consent ring

        // Query with max_ring = 3 (Unsealed)
        let unsealed_hits = index.query_records(&["landlock"], 3);
        assert_eq!(unsealed_hits, vec![1, 2, 3]);

        // Tag intersection: ["landlock", "sandbox"]
        let sandbox_hits = index.query_records(&["landlock", "sandbox"], 3);
        assert_eq!(sandbox_hits, vec![1, 3]);
    }
}
