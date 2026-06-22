//! 🧠 Recursive Intelligence Engine - Pattern Mining
//!
//! Rust implementation for high-performance pattern discovery in event sequences.
//! Handles n-gram, temporal, and causal pattern mining.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct EventPattern {
    #[pyo3(get)]
    pub pattern_id: String,
    #[pyo3(get)]
    pub sequence: Vec<String>,
    #[pyo3(get)]
    pub frequency: i64,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub pattern_type: String,
}

/// Find n-gram patterns in event sequence
#[pyfunction]
pub fn find_ngram_patterns(events: Vec<String>, n: usize, min_frequency: i64) -> Vec<EventPattern> {
    let mut sequence_counts: HashMap<Vec<String>, i64> = HashMap::new();

    // Extract sequences
    for i in 0..events.len().saturating_sub(n - 1) {
        let sequence: Vec<String> = events[i..i + n].to_vec();
        *sequence_counts.entry(sequence).or_insert(0) += 1;
    }

    // Create patterns for frequent sequences
    let mut patterns = Vec::new();
    for (sequence, count) in sequence_counts.iter() {
        if *count >= min_frequency {
            let pattern_id = format!("ngram_{}_{}", n, hash_sequence(sequence));
            patterns.push(EventPattern {
                pattern_id,
                sequence: sequence.clone(),
                frequency: *count,
                confidence: (*count as f64 / 100.0).min(1.0),
                pattern_type: format!("{}-gram", n),
            });
        }
    }

    patterns
}

/// Find temporal co-occurrence patterns
#[pyfunction]
pub fn find_temporal_patterns(
    events: Vec<String>,
    timestamps: Vec<f64>, // Unix timestamps in seconds
    time_window_secs: f64,
    min_frequency: i64,
) -> Vec<EventPattern> {
    let mut co_occurrence: HashMap<(String, String), i64> = HashMap::new();

    for i in 0..events.len() {
        for j in (i + 1)..events.len() {
            if timestamps[j] - timestamps[i] > time_window_secs {
                break;
            }

            // Sort pair for consistent ordering
            let pair = if events[i] <= events[j] {
                (events[i].clone(), events[j].clone())
            } else {
                (events[j].clone(), events[i].clone())
            };
            *co_occurrence.entry(pair).or_insert(0) += 1;
        }
    }

    let mut patterns = Vec::new();
    for ((event_a, event_b), count) in co_occurrence.iter() {
        if *count >= min_frequency {
            let pattern_id = format!(
                "temporal_{}_{}",
                event_a.replace(" ", "_"),
                event_b.replace(" ", "_")
            );
            patterns.push(EventPattern {
                pattern_id,
                sequence: vec![event_a.clone(), event_b.clone()],
                frequency: *count,
                confidence: (*count as f64 / 50.0).min(1.0),
                pattern_type: "temporal_co_occurrence".to_string(),
            });
        }
    }

    patterns
}

/// Find causal patterns (event A → event B with high probability)
#[pyfunction]
pub fn find_causal_patterns(
    events: Vec<String>,
    min_frequency: i64,
    min_probability: f64,
) -> Vec<EventPattern> {
    let mut causal_counts: HashMap<String, (i64, HashMap<String, i64>)> = HashMap::new();

    for i in 0..events.len().saturating_sub(1) {
        let event_a = &events[i];
        let event_b = &events[i + 1];

        let entry = causal_counts
            .entry(event_a.clone())
            .or_insert((0, HashMap::new()));
        entry.0 += 1;
        *entry.1.entry(event_b.clone()).or_insert(0) += 1;
    }

    let mut patterns = Vec::new();
    for (event_a, (total, followed_by)) in causal_counts.iter() {
        if *total < min_frequency {
            continue;
        }

        for (event_b, count) in followed_by.iter() {
            let probability = *count as f64 / *total as f64;

            if probability > min_probability {
                let pattern_id = format!(
                    "causal_{}_{}",
                    event_a.replace(" ", "_"),
                    event_b.replace(" ", "_")
                );
                patterns.push(EventPattern {
                    pattern_id,
                    sequence: vec![event_a.clone(), event_b.clone()],
                    frequency: *count,
                    confidence: probability,
                    pattern_type: "causal".to_string(),
                });
            }
        }
    }

    patterns
}

/// Batch pattern discovery - find all patterns at once
#[pyfunction]
pub fn discover_all_patterns(
    events: Vec<String>,
    timestamps: Vec<f64>,
    min_frequency: i64,
) -> Vec<EventPattern> {
    let mut all_patterns = Vec::new();

    // N-gram patterns (2, 3, 4)
    for n in 2..=4 {
        let patterns = find_ngram_patterns(events.clone(), n, min_frequency);
        all_patterns.extend(patterns);
    }

    // Temporal patterns (1 second window)
    if events.len() == timestamps.len() && !timestamps.is_empty() {
        let patterns = find_temporal_patterns(events.clone(), timestamps, 1.0, min_frequency);
        all_patterns.extend(patterns);
    }

    // Causal patterns (>70% probability)
    let patterns = find_causal_patterns(events, min_frequency, 0.7);
    all_patterns.extend(patterns);

    all_patterns
}

/// Calculate system coherence from patterns
#[pyfunction]
pub fn calculate_coherence(patterns: Vec<EventPattern>) -> f64 {
    if patterns.is_empty() {
        return 0.0;
    }

    let total_confidence: f64 = patterns.iter().map(|p| p.confidence).sum();
    total_confidence / patterns.len() as f64
}

// Helper function to hash a sequence
fn hash_sequence(seq: &[String]) -> u64 {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    for s in seq {
        s.hash(&mut hasher);
    }
    hasher.finish()
}

// ---------------------------------------------------------------------------
// Python module registration
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
pub fn recursive_intelligence(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EventPattern>()?;
    m.add_function(wrap_pyfunction!(find_ngram_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(find_temporal_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(find_causal_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(discover_all_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_coherence, m)?)?;
    Ok(())
}
