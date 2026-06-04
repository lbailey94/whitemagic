//! Confidence Thresholding and Adversarial Hardening
//! Filters low-confidence retrievals and detects adversarial patterns.

use pyo3::prelude::*;

/// Confidence metrics for retrieval results
#[derive(Clone, Debug)]
pub struct ConfidenceMetrics {
    pub max_score: f32,
    pub score_gap: f32,      // Gap between top-1 and top-2
    pub score_variance: f32, // Variance in top-K scores
    pub consensus_ratio: f32, // Agreement between multiple retrieval methods
}

/// Compute confidence metrics from retrieval scores
fn compute_confidence(scores: &[f32]) -> ConfidenceMetrics {
    if scores.is_empty() {
        return ConfidenceMetrics {
            max_score: 0.0,
            score_gap: 0.0,
            score_variance: 0.0,
            consensus_ratio: 0.0,
        };
    }
    
    let max_score = scores.iter().cloned().fold(0.0f32, f32::max);
    
    let score_gap = if scores.len() >= 2 {
        let sorted = {
            let mut s = scores.to_vec();
            s.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
            s
        };
        sorted[0] - sorted[1]
    } else {
        0.0
    };
    
    let mean = scores.iter().sum::<f32>() / scores.len() as f32;
    let variance = scores.iter()
        .map(|&s| (s - mean).powi(2))
        .sum::<f32>() / scores.len() as f32;
    
    ConfidenceMetrics {
        max_score,
        score_gap,
        score_variance: variance.sqrt(),
        consensus_ratio: 1.0, // Placeholder for multi-method consensus
    }
}

/// Check if retrieval passes confidence threshold
#[pyfunction]
fn check_confidence(
    scores: Vec<f32>,
    min_max_score: Option<f32>,
    min_gap: Option<f32>,
    max_variance: Option<f32>,
) -> PyResult<(bool, String)> {
    let metrics = compute_confidence(&scores);
    
    let min_max_score = min_max_score.unwrap_or(0.3);
    let min_gap = min_gap.unwrap_or(0.05);
    let max_variance = max_variance.unwrap_or(0.5);
    
    let mut failures = Vec::new();
    
    if metrics.max_score < min_max_score {
        failures.push(format!("max_score {:.3} < {:.3}", metrics.max_score, min_max_score));
    }
    
    if metrics.score_gap < min_gap {
        failures.push(format!("score_gap {:.3} < {:.3}", metrics.score_gap, min_gap));
    }
    
    if metrics.score_variance > max_variance {
        failures.push(format!("variance {:.3} > {:.3}", metrics.score_variance, max_variance));
    }
    
    let passed = failures.is_empty();
    let reason = if passed {
        "passed".to_string()
    } else {
        failures.join("; ")
    };
    
    Ok((passed, reason))
}

/// Detect adversarial patterns in query
#[pyfunction]
fn detect_adversarial(query: String) -> PyResult<(bool, Vec<String>)> {
    let lower = query.to_lowercase();
    let mut flags = Vec::new();
    
    // 1. Negation patterns
    let negation_count = ["not", "never", "no", "without", "except", "but not"]
        .iter()
        .filter(|&&w| lower.contains(w))
        .count();
    if negation_count >= 2 {
        flags.push(format!("multiple_negations: {}", negation_count));
    }
    
    // 2. Contradictory terms
    let contradictions = [
        ("before", "after"),
        ("first", "last"),
        ("start", "end"),
        ("create", "delete"),
        ("add", "remove"),
    ];
    for (a, b) in &contradictions {
        if lower.contains(a) && lower.contains(b) {
            flags.push(format!("contradiction: {} vs {}", a, b));
        }
    }
    
    // 3. Overly complex structure
    let word_count = lower.split_whitespace().count();
    if word_count > 25 {
        flags.push(format!("overly_complex: {} words", word_count));
    }
    
    // 4. Mismatched quotes
    let double_quotes = query.matches('"').count();
    let single_quotes = query.matches('\'').count();
    if double_quotes % 2 != 0 {
        flags.push("unmatched_double_quotes".to_string());
    }
    if single_quotes % 2 != 0 {
        flags.push("unmatched_single_quotes".to_string());
    }
    
    // 5. Suspicious patterns
    if lower.contains("not not") || lower.contains("never not") {
        flags.push("double_negative".to_string());
    }
    
    // 6. High punctuation ratio (possible injection)
    let punct_count = query.chars().filter(|c| c.is_ascii_punctuation()).count();
    let punct_ratio = punct_count as f32 / query.len() as f32;
    if punct_ratio > 0.3 {
        flags.push(format!("high_punctuation: {:.1}%", punct_ratio * 100.0));
    }
    
    let is_adversarial = !flags.is_empty();
    Ok((is_adversarial, flags))
}

/// Adaptive confidence threshold based on query type
#[pyfunction]
fn adaptive_threshold(query_type: String) -> PyResult<(f32, f32, f32)> {
    // Returns (min_max_score, min_gap, max_variance) for each query type
    let thresholds = match query_type.as_str() {
        "single_hop" => (0.35, 0.08, 0.4),    // High confidence for direct lookups
        "multi_hop" => (0.25, 0.05, 0.5),     // Lower for complex queries
        "temporal" => (0.30, 0.06, 0.45),
        "open_domain" => (0.20, 0.03, 0.6),   // Much lower for open-domain
        "adversarial" => (0.40, 0.10, 0.3),   // Higher threshold for suspected adversarial
        _ => (0.30, 0.05, 0.5),
    };
    
    Ok(thresholds)
}

/// Hard negative mining: find samples that are similar but incorrect
#[pyfunction]
fn find_hard_negatives(
    query_embedding: Vec<f32>,
    positive_id: u64,
    candidate_embeddings: Vec<(u64, Vec<f32>)>,
    threshold: f32,
) -> PyResult<Vec<u64>> {
    use rayon::prelude::*;
    
    let hard_negatives: Vec<u64> = candidate_embeddings
        .par_iter()
        .filter(|(id, _)| *id != positive_id)
        .filter_map(|(id, emb)| {
            // Compute cosine similarity
            let dot: f32 = query_embedding.iter().zip(emb.iter()).map(|(a, b)| a * b).sum();
            let norm_q: f32 = query_embedding.iter().map(|a| a * a).sum::<f32>().sqrt();
            let norm_e: f32 = emb.iter().map(|a| a * a).sum::<f32>().sqrt();
            let sim = if norm_q > 0.0 && norm_e > 0.0 {
                dot / (norm_q * norm_e)
            } else {
                0.0
            };
            
            // Hard negative: high similarity but wrong answer
            if sim > threshold && sim < 0.95 {
                Some(*id)
            } else {
                None
            }
        })
        .collect();
    
    Ok(hard_negatives)
}

pub fn register_confidence(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(check_confidence, m)?)?;
    m.add_function(wrap_pyfunction!(detect_adversarial, m)?)?;
    m.add_function(wrap_pyfunction!(adaptive_threshold, m)?)?;
    m.add_function(wrap_pyfunction!(find_hard_negatives, m)?)?;
    Ok(())
}
