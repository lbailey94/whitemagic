//! Convergence Detector — Multi-Domain Signal Convergence Scoring
//!
//! Detects when N independent signals from different domains converge on the
//! same underlying claim. The convergence score is driven by:
//!
//!   1. **Count**: How many independent sources agree.
//!   2. **Domain diversity**: More domains = stronger signal (4 ai_governance
//!      sources are weaker than 1 ai_governance + 1 geopolitics + 1 hardware).
//!   3. **Confidence**: Source-weighted mean probability.
//!   4. **Lead spread**: A cluster that spans many months across sources is
//!      stronger than one where all sources appeared on the same day.
//!
//! The output `ConvergenceCluster` mirrors what `TemporalForecastDB` can
//! consume to create new predictions or boost confidence on existing ones.
//!
//! Python API:
//!   `detect_convergence(signals_json, threshold) -> str` (JSON clusters)
//!   `convergence_score(signals_json) -> f64`

use pyo3::prelude::*;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/// A single input signal fed to the convergence detector.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct ConvergenceSignal {
    /// Unique signal ID (UUID or arbitrary string).
    #[pyo3(get, set)]
    pub id: String,
    /// Human-readable claim text.
    #[pyo3(get, set)]
    pub claim: String,
    /// Domain tag (e.g. "ai_governance", "ai_hardware", "geopolitics").
    #[pyo3(get, set)]
    pub domain: String,
    /// Source date as ISO-8601 string (YYYY-MM-DD).
    #[pyo3(get, set)]
    pub source_date: String,
    /// Predicted probability in [0, 1].
    #[pyo3(get, set)]
    pub confidence: f64,
    /// Optional reference (URL, archive ID, file path).
    #[pyo3(get, set)]
    pub source_ref: String,
}

#[pymethods]
impl ConvergenceSignal {
    #[new]
    #[pyo3(signature = (id, claim, domain, source_date, confidence, source_ref="".to_string()))]
    fn new(
        id: String,
        claim: String,
        domain: String,
        source_date: String,
        confidence: f64,
        source_ref: String,
    ) -> Self {
        Self { id, claim, domain, source_date, confidence, source_ref }
    }
}

/// A cluster of signals that have converged on the same underlying claim.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct ConvergenceCluster {
    /// Representative claim (highest-confidence signal in the cluster).
    #[pyo3(get)]
    pub claim: String,
    /// Number of independent signals in the cluster.
    #[pyo3(get)]
    pub signal_count: usize,
    /// Number of distinct domains represented.
    #[pyo3(get)]
    pub domain_count: usize,
    /// List of domain tags in the cluster.
    #[pyo3(get)]
    pub domains: Vec<String>,
    /// Convergence score in [0, ∞). Higher = stronger convergence.
    #[pyo3(get)]
    pub convergence_score: f64,
    /// Confidence-weighted mean of source probabilities.
    #[pyo3(get)]
    pub weighted_confidence: f64,
    /// Earliest source date in the cluster (ISO-8601).
    #[pyo3(get)]
    pub earliest_date: String,
    /// Latest source date in the cluster (ISO-8601).
    #[pyo3(get)]
    pub latest_date: String,
    /// Lead spread in days (latest − earliest source date).
    #[pyo3(get)]
    pub lead_spread_days: i64,
    /// IDs of all signals in the cluster.
    #[pyo3(get)]
    pub signal_ids: Vec<String>,
}

#[pymethods]
impl ConvergenceCluster {
    fn __repr__(&self) -> String {
        format!(
            "ConvergenceCluster(score={:.3}, signals={}, domains={}, claim={:?})",
            self.convergence_score, self.signal_count, self.domain_count, self.claim
        )
    }
}

// ---------------------------------------------------------------------------
// Core algorithm
// ---------------------------------------------------------------------------

/// Compute a keyword fingerprint for a claim string.
/// Returns a sorted Vec of lowercase alphanumeric words ≥4 chars,
/// excluding common stopwords.
fn fingerprint(text: &str) -> Vec<String> {
    const STOPWORDS: &[&str] = &[
        "the", "and", "for", "with", "that", "this", "from", "have",
        "will", "are", "was", "has", "its", "via", "per", "into",
        "over", "each", "any", "all", "can", "not", "but", "also",
    ];
    let mut words: Vec<String> = text
        .to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|w| w.len() >= 4 && !STOPWORDS.contains(w))
        .map(String::from)
        .collect();
    words.sort_unstable();
    words.dedup();
    words
}

/// Jaccard similarity between two keyword fingerprints.
fn jaccard(a: &[String], b: &[String]) -> f64 {
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    let set_a: HashSet<&str> = a.iter().map(String::as_str).collect();
    let set_b: HashSet<&str> = b.iter().map(String::as_str).collect();
    let intersection = set_a.intersection(&set_b).count();
    let union = set_a.union(&set_b).count();
    if union == 0 { 0.0 } else { intersection as f64 / union as f64 }
}

/// Parse ISO-8601 date string "YYYY-MM-DD" → days since epoch (rough).
fn date_to_days(s: &str) -> i64 {
    let parts: Vec<&str> = s.splitn(3, '-').collect();
    if parts.len() < 3 {
        return 0;
    }
    let y: i64 = parts[0].parse().unwrap_or(2025);
    let m: i64 = parts[1].parse().unwrap_or(1);
    let d: i64 = parts[2].parse().unwrap_or(1);
    // Rough days since 2000-01-01
    (y - 2000) * 365 + m * 30 + d
}

/// Compute domain diversity bonus: unique domains / total signals, in [0, 1].
fn domain_diversity(domains: &[String]) -> f64 {
    let unique: HashSet<&str> = domains.iter().map(String::as_str).collect();
    if domains.is_empty() {
        return 0.0;
    }
    unique.len() as f64 / domains.len() as f64
}

/// Core convergence scoring formula.
/// score = (signal_count^0.75) * (1 + domain_diversity) * weighted_confidence * (1 + spread_bonus)
fn compute_score(
    signal_count: usize,
    domains: &[String],
    weighted_confidence: f64,
    lead_spread_days: i64,
) -> f64 {
    let count_factor = (signal_count as f64).powf(0.75);
    let diversity_bonus = 1.0 + domain_diversity(domains);
    let spread_bonus = (lead_spread_days as f64 / 30.0).min(2.0) * 0.1; // max 0.2
    count_factor * diversity_bonus * weighted_confidence * (1.0 + spread_bonus)
}

/// Cluster signals by Jaccard similarity ≥ threshold.
/// Returns groups of signal indices (union-find style greedy clustering).
fn cluster_by_similarity(
    fingerprints: &[Vec<String>],
    threshold: f64,
) -> Vec<Vec<usize>> {
    let n = fingerprints.len();
    let mut labels: Vec<Option<usize>> = vec![None; n];
    let mut next_cluster = 0usize;

    for i in 0..n {
        if labels[i].is_none() {
            labels[i] = Some(next_cluster);
            next_cluster += 1;
        }
        let ci = labels[i].unwrap();
        for j in (i + 1)..n {
            if jaccard(&fingerprints[i], &fingerprints[j]) >= threshold {
                match labels[j] {
                    None => labels[j] = Some(ci),
                    Some(cj) if cj != ci => {
                        // Merge: relabel all cj → ci
                        for lbl in labels.iter_mut() {
                            if *lbl == Some(cj) {
                                *lbl = Some(ci);
                            }
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    let mut groups: HashMap<usize, Vec<usize>> = HashMap::new();
    for (i, lbl) in labels.iter().enumerate() {
        groups.entry(lbl.unwrap_or(i)).or_default().push(i);
    }
    groups.into_values().collect()
}

/// Build a `ConvergenceCluster` from a group of signal indices.
fn build_cluster(signals: &[ConvergenceSignal], indices: &[usize]) -> ConvergenceCluster {
    let members: Vec<&ConvergenceSignal> = indices.iter().map(|&i| &signals[i]).collect();

    let domains: Vec<String> = members.iter().map(|s| s.domain.clone()).collect();
    let signal_count = members.len();
    let domain_count = domains.iter().collect::<HashSet<_>>().len();

    // Confidence-weighted mean
    let total_conf: f64 = members.iter().map(|s| s.confidence).sum();
    let weighted_confidence = if signal_count > 0 { total_conf / signal_count as f64 } else { 0.0 };

    // Date range
    let dates: Vec<i64> = members.iter().map(|s| date_to_days(&s.source_date)).collect();
    let min_days = dates.iter().copied().min().unwrap_or(0);
    let max_days = dates.iter().copied().max().unwrap_or(0);
    let lead_spread_days = max_days - min_days;

    let earliest_date = members
        .iter()
        .min_by_key(|s| date_to_days(&s.source_date))
        .map(|s| s.source_date.clone())
        .unwrap_or_default();
    let latest_date = members
        .iter()
        .max_by_key(|s| date_to_days(&s.source_date))
        .map(|s| s.source_date.clone())
        .unwrap_or_default();

    // Representative claim = highest confidence member
    let claim = members
        .iter()
        .max_by(|a, b| a.confidence.partial_cmp(&b.confidence).unwrap())
        .map(|s| s.claim.clone())
        .unwrap_or_default();

    let convergence_score =
        compute_score(signal_count, &domains, weighted_confidence, lead_spread_days);

    let signal_ids: Vec<String> = members.iter().map(|s| s.id.clone()).collect();

    ConvergenceCluster {
        claim,
        signal_count,
        domain_count,
        domains,
        convergence_score,
        weighted_confidence,
        earliest_date,
        latest_date,
        lead_spread_days,
        signal_ids,
    }
}

// ---------------------------------------------------------------------------
// Python API
// ---------------------------------------------------------------------------

/// Detect convergence clusters from a JSON array of signal objects.
///
/// Args:
///     signals_json: JSON string, array of objects with fields:
///                   id, claim, domain, source_date, confidence, source_ref
///     threshold:    Jaccard similarity threshold in [0, 1] (default 0.25)
///     min_signals:  Minimum cluster size to include in output (default 2)
///
/// Returns:
///     JSON string with array of ConvergenceCluster objects, sorted by
///     convergence_score descending.
#[pyfunction]
#[pyo3(signature = (signals_json, threshold=0.25, min_signals=2))]
pub fn detect_convergence(
    signals_json: &str,
    threshold: f64,
    min_signals: usize,
) -> PyResult<String> {
    let signals: Vec<ConvergenceSignal> = serde_json::from_str(signals_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse error: {}", e))
    })?;

    if signals.is_empty() {
        return Ok("[]".to_string());
    }

    // Compute fingerprints in parallel
    let fingerprints: Vec<Vec<String>> =
        signals.par_iter().map(|s| fingerprint(&s.claim)).collect();

    // Cluster
    let groups = cluster_by_similarity(&fingerprints, threshold);

    // Build clusters in parallel, filter by min_signals
    let mut clusters: Vec<ConvergenceCluster> = groups
        .par_iter()
        .filter(|g| g.len() >= min_signals)
        .map(|g| build_cluster(&signals, g))
        .collect();

    // Sort by score descending
    clusters.sort_by(|a, b| b.convergence_score.partial_cmp(&a.convergence_score).unwrap());

    serde_json::to_string(&clusters).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
    })
}

/// Compute the single strongest convergence score across all clusters.
/// Returns 0.0 if no clusters meet the default threshold.
#[pyfunction]
#[pyo3(signature = (signals_json, threshold=0.25))]
pub fn convergence_score(signals_json: &str, threshold: f64) -> PyResult<f64> {
    let result = detect_convergence(signals_json, threshold, 2)?;
    let clusters: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap_or_default();
    Ok(clusters
        .first()
        .and_then(|c| c["convergence_score"].as_f64())
        .unwrap_or(0.0))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_signal(id: &str, claim: &str, domain: &str, date: &str, conf: f64) -> ConvergenceSignal {
        ConvergenceSignal {
            id: id.to_string(),
            claim: claim.to_string(),
            domain: domain.to_string(),
            source_date: date.to_string(),
            confidence: conf,
            source_ref: String::new(),
        }
    }

    #[test]
    fn test_fingerprint_basic() {
        let fp = fingerprint("AI governance policy layer for agents");
        assert!(fp.contains(&"governance".to_string()));
        assert!(fp.contains(&"agents".to_string()));
        assert!(fp.contains(&"policy".to_string()));
    }

    #[test]
    fn test_jaccard_identical() {
        let a = fingerprint("cryptographic audit trail for AI actions");
        let b = fingerprint("cryptographic audit trail for AI actions");
        assert!((jaccard(&a, &b) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_jaccard_disjoint() {
        let a = fingerprint("neural network training optimization");
        let b = fingerprint("geopolitical sovereignty governance policy");
        assert!(jaccard(&a, &b) < 0.15);
    }

    #[test]
    fn test_convergence_same_domain() {
        let signals = vec![
            make_signal("s1", "cryptographic audit ledger for AI model lineage", "ai_governance", "2025-06-01", 0.8),
            make_signal("s2", "cryptographic audit trail ledger model provenance", "ai_governance", "2025-09-01", 0.75),
            make_signal("s3", "blockchain audit trail model lineage transparency", "ai_governance", "2025-11-01", 0.7),
        ];
        let json = serde_json::to_string(&signals).unwrap();
        let result = detect_convergence(&json, 0.15, 2).unwrap();
        let clusters: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        assert!(!clusters.is_empty(), "Expected at least one cluster");
        let top = &clusters[0];
        assert!(top["signal_count"].as_u64().unwrap() >= 2);
    }

    #[test]
    fn test_convergence_multi_domain_boosts_score() {
        let single_domain_signals = vec![
            make_signal("a1", "isolated policy sandbox intercepting tool calls", "ai_governance", "2025-05-01", 0.8),
            make_signal("a2", "isolated policy sandbox intercepting tool calls", "ai_governance", "2025-07-01", 0.75),
        ];
        let multi_domain_signals = vec![
            make_signal("b1", "isolated policy sandbox intercepting tool calls", "ai_governance", "2025-05-01", 0.8),
            make_signal("b2", "isolated policy sandbox intercepting tool calls", "ai_hardware", "2025-07-01", 0.75),
        ];

        let j1 = serde_json::to_string(&single_domain_signals).unwrap();
        let j2 = serde_json::to_string(&multi_domain_signals).unwrap();
        let s1 = convergence_score(&j1, 0.3).unwrap();
        let s2 = convergence_score(&j2, 0.3).unwrap();
        assert!(s2 > s1, "Multi-domain should score higher: {} vs {}", s2, s1);
    }

    #[test]
    fn test_no_clusters_below_threshold() {
        let signals = vec![
            make_signal("x1", "quantum vacuum energy extraction device", "physics", "2025-01-01", 0.3),
            make_signal("x2", "large language model fine-tuning efficiency", "ai_research", "2025-01-02", 0.7),
        ];
        let json = serde_json::to_string(&signals).unwrap();
        let result = detect_convergence(&json, 0.5, 2).unwrap();
        let clusters: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        assert!(clusters.is_empty(), "Unrelated signals should not cluster");
    }

    #[test]
    fn test_empty_input() {
        let result = detect_convergence("[]", 0.25, 2).unwrap();
        assert_eq!(result, "[]");
    }

    #[test]
    fn test_single_signal_no_cluster() {
        let signals = vec![make_signal("z1", "unique singular claim about something", "general", "2025-01-01", 0.5)];
        let json = serde_json::to_string(&signals).unwrap();
        let result = detect_convergence(&json, 0.25, 2).unwrap();
        let clusters: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        assert!(clusters.is_empty());
    }

    #[test]
    fn test_score_increases_with_count() {
        let base_claim = "agent identity coherence persistent cross-session";
        let two = vec![
            make_signal("c1", base_claim, "agent_architecture", "2025-10-01", 0.7),
            make_signal("c2", base_claim, "agent_architecture", "2025-11-01", 0.7),
        ];
        let four = vec![
            make_signal("c1", base_claim, "agent_architecture", "2025-10-01", 0.7),
            make_signal("c2", base_claim, "agent_architecture", "2025-11-01", 0.7),
            make_signal("c3", base_claim, "ai_governance", "2025-12-01", 0.7),
            make_signal("c4", base_claim, "ai_hardware", "2026-01-01", 0.7),
        ];
        let j2 = serde_json::to_string(&two).unwrap();
        let j4 = serde_json::to_string(&four).unwrap();
        let s2 = convergence_score(&j2, 0.4).unwrap();
        let s4 = convergence_score(&j4, 0.4).unwrap();
        assert!(s4 > s2, "4 signals should score higher than 2: {} vs {}", s4, s2);
    }
}
