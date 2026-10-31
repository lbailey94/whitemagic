//! wm-gen3-core::engram — The WM-Engram Tier -1 Sub-Microsecond Multi-Head Index.
//!
//! Provides:
//! 1. O(1) multi-head normalized token and N-gram index (unigrams, bigrams, date tokens).
//! 2. Reciprocal Rank Fusion (RRF k=60) combining lexical, semantic, and engram channels.
//! 3. Deterministic temporal date grounding (YYYY-MM-DD extraction and exact anchoring).

#![forbid(unsafe_code)]

use std::collections::HashMap;

/// RRF constant k = 60 (standard Cormack & Clarke TREC baseline).
pub const RRF_K: f32 = 60.0;

/// Canonical prime hash moduli for K=8 multi-head engram projections.
pub const ENGRAM_PRIMES: [u64; 8] = [31, 37, 41, 43, 47, 53, 59, 61];

/// Extracts normalized unigrams, bigrams, and temporal date tokens from tokens.
#[must_use]
pub fn extract_engram_keys(tokens: &[String]) -> Vec<String> {
    let mut keys = Vec::with_capacity(tokens.len() * 2);
    // Unigrams
    for t in tokens {
        keys.push(t.clone());
    }
    // Bigrams
    for w in tokens.windows(2) {
        keys.push(format!("{}_{}", w[0], w[1]));
    }
    // Trigrams for short high-precision sequences
    for w in tokens.windows(3) {
        keys.push(format!("{}_{}_{}", w[0], w[1], w[2]));
    }
    keys
}

/// Detects if a query contains an explicit ISO date (e.g. "2026-10-01") or historical keywords.
#[must_use]
pub fn extract_temporal_anchor(query: &str) -> Option<String> {
    let words: Vec<&str> = query
        .split(|c: char| c.is_whitespace() || c == ',' || c == ';')
        .collect();
    for w in words {
        let clean = w.trim_matches(|c: char| !c.is_alphanumeric() && c != '-');
        if clean.len() == 10 {
            let bytes = clean.as_bytes();
            if bytes[4] == b'-'
                && bytes[7] == b'-'
                && bytes[0..4].iter().all(u8::is_ascii_digit)
                && bytes[5..7].iter().all(u8::is_ascii_digit)
                && bytes[8..10].iter().all(u8::is_ascii_digit)
            {
                return Some(clean.to_string());
            }
        }
    }
    None
}

/// Checks whether a query explicitly asks for historical, past, or superseded state.
#[must_use]
pub fn is_historical_query(query: &str) -> bool {
    let lower = query.to_lowercase();
    let words: Vec<&str> = lower
        .split(|c: char| !c.is_alphanumeric() && c != '-' && c != '_')
        .filter(|w| !w.is_empty())
        .collect();

    let has_date = extract_temporal_anchor(query).is_some();
    let has_past_tense = words.contains(&"was")
        || words.contains(&"were")
        || words.contains(&"previous")
        || words.contains(&"previously")
        || words.contains(&"prior")
        || words.contains(&"past")
        || words.contains(&"former")
        || words.contains(&"formerly")
        || words.contains(&"historical")
        || words.contains(&"deprecated")
        || words.contains(&"superseded")
        || words.contains(&"old")
        || words.contains(&"earlier")
        || words.contains(&"initial")
        || words.contains(&"original");

    has_date || has_past_tense
}

/// Reciprocal Rank Fusion (RRF) combiner:
/// Combines ranked candidate lists (e.g. Lexical, Semantic, Engram) into a single score map.
#[must_use]
pub fn fuse_rrf(ranked_lists: &[Vec<u64>]) -> HashMap<u64, f32> {
    let mut scores: HashMap<u64, f32> = HashMap::new();
    for list in ranked_lists {
        for (rank, &id) in list.iter().enumerate() {
            let rrf_inc = 1.0 / (RRF_K + (rank + 1) as f32);
            *scores.entry(id).or_default() += rrf_inc;
        }
    }
    scores
}

/// Computes an 8-head rolling prime polynomial hash for a normalized token.
#[must_use]
pub fn multi_head_hash(token: &str) -> [u64; 8] {
    let mut hashes = [0u64; 8];
    for (i, &prime) in ENGRAM_PRIMES.iter().enumerate() {
        let mut h = 0u64;
        for &b in token.as_bytes() {
            h = h.wrapping_mul(prime).wrapping_add(b as u64);
        }
        hashes[i] = h;
    }
    hashes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engram_temporal_detection() {
        assert_eq!(
            extract_temporal_anchor("what was harbor import format on 2026-10-01"),
            Some("2026-10-01".to_string())
        );
        assert!(is_historical_query(
            "what was harbor import format on 2026-10-01"
        ));
        assert!(is_historical_query(
            "what is harbor import format current on 2026-10-22"
        ));
        assert!(!is_historical_query("what is harbor import format current"));
    }

    #[test]
    fn test_rrf_fusion() {
        let l1 = vec![101, 102, 103];
        let l2 = vec![102, 101, 104];
        let fused = fuse_rrf(&[l1, l2]);
        // 102 was rank 2 then rank 1 -> 1/(60+2) + 1/(60+1)
        // 101 was rank 1 then rank 2 -> identical score
        assert!(fused[&101] > fused[&103]);
        assert!(fused[&102] > fused[&104]);
    }
}
