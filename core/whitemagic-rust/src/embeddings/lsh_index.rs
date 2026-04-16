//! LSH (Locality-Sensitive Hashing) Index for O(N) duplicate detection
//!
//! This module implements LSH bucketing to reduce duplicate detection from O(N²) to O(N).
//! Instead of comparing all pairs, we hash signatures into buckets and only compare
//! candidates that fall into the same bucket.

use std::collections::{HashMap, HashSet};
use serde::Serialize;

/// LSH Index for fast candidate retrieval
pub struct LSHIndex {
    buckets: HashMap<Vec<u64>, Vec<usize>>,
    num_bands: usize,
    rows_per_band: usize,
}

impl LSHIndex {
    /// Create a new LSH index
    /// 
    /// The number of bands is optimized for the given number of hash functions.
    /// More bands = higher recall, fewer bands = higher precision.
    pub fn new(num_hashes: usize) -> Self {
        // Optimal bands: sqrt(num_hashes) balances false positives/negatives
        let num_bands = (num_hashes as f64).sqrt() as usize;
        let rows_per_band = num_hashes / num_bands;
        
        LSHIndex {
            buckets: HashMap::new(),
            num_bands,
            rows_per_band,
        }
    }
    
    /// Insert a signature into the index
    pub fn insert(&mut self, idx: usize, signature: &[u64]) {
        // Hash each band and insert into corresponding bucket
        for band in 0..self.num_bands {
            let start = band * self.rows_per_band;
            let end = (start + self.rows_per_band).min(signature.len());
            
            if start >= signature.len() {
                break;
            }
            
            let band_hash = signature[start..end].to_vec();
            self.buckets
                .entry(band_hash)
                .or_insert_with(Vec::new)
                .push(idx);
        }
    }
    
    /// Query for candidate indices that might be similar
    /// 
    /// Returns all indices that share at least one band with the query signature.
    /// This is much faster than comparing all pairs (O(N) vs O(N²)).
    pub fn query_candidates(&self, signature: &[u64]) -> HashSet<usize> {
        let mut candidates = HashSet::new();
        
        for band in 0..self.num_bands {
            let start = band * self.rows_per_band;
            let end = (start + self.rows_per_band).min(signature.len());
            
            if start >= signature.len() {
                break;
            }
            
            let band_hash = &signature[start..end];
            if let Some(bucket) = self.buckets.get(band_hash) {
                candidates.extend(bucket.iter().copied());
            }
        }
        
        candidates
    }
    
    /// Get statistics about the index
    pub fn stats(&self) -> LSHStats {
        let total_buckets = self.buckets.len();
        let total_entries: usize = self.buckets.values().map(|v| v.len()).sum();
        let avg_bucket_size = if total_buckets > 0 {
            total_entries as f64 / total_buckets as f64
        } else {
            0.0
        };
        
        LSHStats {
            num_bands: self.num_bands,
            rows_per_band: self.rows_per_band,
            total_buckets,
            total_entries,
            avg_bucket_size,
        }
    }
}

/// Statistics about an LSH index
#[derive(Debug, Clone, Serialize)]
pub struct LSHStats {
    pub num_bands: usize,
    pub rows_per_band: usize,
    pub total_buckets: usize,
    pub total_entries: usize,
    pub avg_bucket_size: f64,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_lsh_index_creation() {
        let index = LSHIndex::new(128);
        assert_eq!(index.num_bands, 11);  // sqrt(128) ≈ 11
        assert_eq!(index.rows_per_band, 11);  // 128 / 11 ≈ 11
    }
    
    #[test]
    fn test_lsh_insert_and_query() {
        let mut index = LSHIndex::new(128);
        
        // Create two similar signatures
        let sig1: Vec<u64> = (0..128).map(|i| i as u64).collect();
        let sig2: Vec<u64> = (0..128).map(|i| i as u64).collect();
        let sig3: Vec<u64> = (0..128).map(|i| (i * 2) as u64).collect();
        
        index.insert(0, &sig1);
        index.insert(1, &sig2);
        index.insert(2, &sig3);
        
        // Query with sig1 should find sig2 (identical) but maybe not sig3
        let candidates = index.query_candidates(&sig1);
        assert!(candidates.contains(&0));  // Should find itself
        assert!(candidates.contains(&1));  // Should find identical signature
    }
    
    #[test]
    fn test_lsh_stats() {
        let mut index = LSHIndex::new(128);
        
        let sig: Vec<u64> = (0..128).map(|i| i as u64).collect();
        index.insert(0, &sig);
        
        let stats = index.stats();
        assert!(stats.total_buckets > 0);
        assert!(stats.total_entries > 0);
    }
}
