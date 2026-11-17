//! Probabilistic `SurpriseGate` (`HyperLogLog14` + `CountMinSketch`) and
//! sliding-window `NoveltyGate` (`SHA-256` + token Jaccard) (`#![forbid(unsafe_code)]`).
//!
//! Ported cleanly from Gen 4 (`WMgen4/src/memory_algebra.rs`) to filter repetitive
//! boilerplate turns during intake without breaking canonical exact-hash invariants.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashSet, VecDeque};

#[inline]
fn splitmix64(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

#[inline]
fn hash_bytes_with_seed(data: &[u8], seed: u64) -> u64 {
    let mut h = 0xCBF2_9CE4_8422_2325u64 ^ splitmix64(seed);
    for &b in data {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0000_0100_0000_01B3);
    }
    splitmix64(h)
}

/// 14-bit Precision HyperLogLog (`m = 16,384` `u8` registers = `16 KiB` L1-resident cardinality sketch).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperLogLog14 {
    registers: Vec<u8>,
}

impl Default for HyperLogLog14 {
    fn default() -> Self {
        Self::new()
    }
}

impl HyperLogLog14 {
    pub const P: u32 = 14;
    pub const M: usize = 1 << Self::P;

    #[must_use]
    pub fn new() -> Self {
        Self {
            registers: vec![0u8; Self::M],
        }
    }

    pub fn insert(&mut self, item: &[u8]) {
        let h = hash_bytes_with_seed(item, 0xA11C_E42B_1337_5151);
        let idx = (h >> (64 - Self::P)) as usize;
        let w = (h << Self::P) | (1u64 << (Self::P - 1));
        let rho = (w.leading_zeros() as u8).saturating_add(1);
        if rho > self.registers[idx] {
            self.registers[idx] = rho;
        }
    }

    #[must_use]
    pub fn estimate(&self) -> f64 {
        let m = Self::M as f64;
        let alpha_m = 0.7213 / (1.0 + 1.079 / m);
        let mut sum_inv = 0.0f64;
        let mut zeros = 0usize;
        for &r in &self.registers {
            if r == 0 {
                zeros += 1;
            }
            sum_inv += 2.0f64.powi(-i32::from(r));
        }
        let raw = alpha_m * m * m / sum_inv;
        if raw <= 2.5 * m && zeros > 0 {
            m * (m / (zeros as f64)).ln()
        } else {
            raw
        }
    }
}

/// `4 × 1024` Count-Min Sketch (`16 KiB` L1-resident streaming frequency sketch).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CountMinSketch {
    pub depth: usize,
    pub width: usize,
    counts: Vec<u32>,
    seeds: [u64; 4],
    pub total: u64,
}

impl Default for CountMinSketch {
    fn default() -> Self {
        Self::new(1024)
    }
}

impl CountMinSketch {
    #[must_use]
    pub fn new(width: usize) -> Self {
        let w = width.max(64);
        Self {
            depth: 4,
            width: w,
            counts: vec![0u32; 4 * w],
            seeds: [
                0x243F_6A88_85A3_08D3,
                0x1319_8A2E_0370_7344,
                0xA409_3822_299F_31D0,
                0x082E_FA98_EC4E_6C89,
            ],
            total: 0,
        }
    }

    pub fn observe(&mut self, item: &[u8]) -> u32 {
        self.total = self.total.saturating_add(1);
        let mut min_est = u32::MAX;
        for row in 0..self.depth {
            let col = (hash_bytes_with_seed(item, self.seeds[row]) as usize) % self.width;
            let idx = row * self.width + col;
            self.counts[idx] = self.counts[idx].saturating_add(1);
            min_est = min_est.min(self.counts[idx]);
        }
        min_est
    }

    #[must_use]
    pub fn estimate(&self, item: &[u8]) -> u32 {
        let mut min_est = u32::MAX;
        for row in 0..self.depth {
            let col = (hash_bytes_with_seed(item, self.seeds[row]) as usize) % self.width;
            min_est = min_est.min(self.counts[row * self.width + col]);
        }
        min_est
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurpriseObservation {
    pub frequency_after: u32,
    pub estimated_cardinality: f64,
    pub surprise_bits: f32,
    pub normalized_surprise: f32,
    pub admit_memory: bool,
}

/// Probabilistic `SurpriseGate` backed by `HyperLogLog14` + `CountMinSketch`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurpriseGate {
    pub hll: HyperLogLog14,
    pub cms: CountMinSketch,
    pub surprise_threshold: f32,
}

impl Default for SurpriseGate {
    fn default() -> Self {
        Self::new(0.45)
    }
}

impl SurpriseGate {
    #[must_use]
    pub fn new(surprise_threshold: f32) -> Self {
        Self {
            hll: HyperLogLog14::new(),
            cms: CountMinSketch::new(1024),
            surprise_threshold: surprise_threshold.clamp(0.0, 1.0),
        }
    }

    pub fn observe(&mut self, key: &[u8]) -> SurpriseObservation {
        let prior_freq = self.cms.estimate(key);
        let prior_total = self.cms.total.max(1) as f64;
        let p_prior = (f64::from(prior_freq) + 0.5) / (prior_total + 1.0);
        let bits = (-p_prior.log2()).max(0.0) as f32;
        let max_bits = ((prior_total + 1.0) / 0.5).log2().max(1.0) as f32;
        let norm = (bits / max_bits).clamp(0.0, 1.0);

        self.hll.insert(key);
        let after = self.cms.observe(key);
        SurpriseObservation {
            frequency_after: after,
            estimated_cardinality: self.hll.estimate(),
            surprise_bits: bits,
            normalized_surprise: norm,
            admit_memory: norm >= self.surprise_threshold,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoveltyDecision {
    pub is_novel: bool,
    pub exact_duplicate: bool,
    pub max_jaccard: f32,
    pub sha256_hex: String,
}

/// Exact SHA-256 + sliding-window token Jaccard consolidation novelty gate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoveltyGate {
    pub jaccard_threshold: f32,
    pub max_window: usize,
    seen_hashes: HashSet<[u8; 32]>,
    recent_token_sets: VecDeque<HashSet<String>>,
}

impl Default for NoveltyGate {
    fn default() -> Self {
        Self::new(0.80, 256)
    }
}

impl NoveltyGate {
    #[must_use]
    pub fn new(jaccard_threshold: f32, max_window: usize) -> Self {
        Self {
            jaccard_threshold: jaccard_threshold.clamp(0.0, 1.0),
            max_window: max_window.max(8),
            seen_hashes: HashSet::new(),
            recent_token_sets: VecDeque::new(),
        }
    }

    fn tokenize(text: &str) -> HashSet<String> {
        text.split(|c: char| !c.is_alphanumeric())
            .filter(|t| !t.is_empty())
            .map(|t| t.to_ascii_lowercase())
            .collect()
    }

    pub fn evaluate_and_record(&mut self, text: &str) -> NoveltyDecision {
        let mut hasher = Sha256::new();
        hasher.update(text.as_bytes());
        let digest: [u8; 32] = hasher.finalize().into();
        let sha256_hex: String = digest.iter().map(|b| format!("{b:02x}")).collect();

        if self.seen_hashes.contains(&digest) {
            return NoveltyDecision {
                is_novel: false,
                exact_duplicate: true,
                max_jaccard: 1.0,
                sha256_hex,
            };
        }

        let tokens = Self::tokenize(text);
        let mut max_j = 0.0f32;
        for prev in &self.recent_token_sets {
            if tokens.is_empty() && prev.is_empty() {
                max_j = 1.0;
                break;
            }
            let inter = tokens.intersection(prev).count();
            let union = tokens.len() + prev.len() - inter;
            if union > 0 {
                max_j = max_j.max((inter as f32) / (union as f32));
            }
        }

        let is_novel = max_j < self.jaccard_threshold;
        if is_novel {
            self.seen_hashes.insert(digest);
            if self.recent_token_sets.len() >= self.max_window {
                self.recent_token_sets.pop_front();
            }
            self.recent_token_sets.push_back(tokens);
        }

        NoveltyDecision {
            is_novel,
            exact_duplicate: false,
            max_jaccard: max_j,
            sha256_hex,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn surprise_gate_and_novelty_gate_suppress_boilerplate() {
        let mut sg = SurpriseGate::new(0.40);
        assert!(sg.observe(b"first-unique-event").admit_memory);
        for _ in 0..8 {
            let _ = sg.observe(b"noisy-heartbeat-event");
        }
        let obs = sg.observe(b"noisy-heartbeat-event");
        assert!(!obs.admit_memory);
        assert!(obs.estimated_cardinality >= 1.5);

        let mut ng = NoveltyGate::new(0.75, 16);
        let d1 = ng.evaluate_and_record("Landlock LSM blocks /etc/shadow access on Gen3");
        assert!(d1.is_novel && !d1.exact_duplicate);

        let d2 = ng.evaluate_and_record("Landlock LSM blocks /etc/shadow access on Gen3");
        assert!(!d2.is_novel && d2.exact_duplicate);

        let d3 = ng.evaluate_and_record("Landlock LSM blocks /etc/shadow reads on Gen3");
        assert!(!d3.is_novel && !d3.exact_duplicate && d3.max_jaccard >= 0.75);

        let d4 = ng.evaluate_and_record("Base USDC settlement receipt verified via Ed25519");
        assert!(d4.is_novel);
    }
}
