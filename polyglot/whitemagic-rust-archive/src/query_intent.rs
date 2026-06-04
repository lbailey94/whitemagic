//! Query Intent Classification for Adaptive Retrieval
//! Detects query type to route to appropriate retrieval strategy.
//! Uses lightweight ML inference with hand-tuned weights (no model loading overhead).

use pyo3::prelude::*;

/// Query intent types matching LoCoMo benchmark categories
#[derive(Clone, Copy, Debug)]
pub enum QueryIntent {
    SingleHop,      // Direct lookup by title/content
    MultiHop,       // Requires connecting multiple facts
    Temporal,       // Time-based or sequence queries
    OpenDomain,     // Broad, non-specific queries
    Adversarial,    // Misleading or tricky phrasing
    Unknown,
}

/// Feature extraction for intent classification
fn extract_intent_features(query: &str) -> Vec<f32> {
    let lower = query.to_lowercase();
    let words: Vec<&str> = lower.split_whitespace().collect();
    let mut features = vec![0.0f32; 20];
    
    // 1. Question word indicators
    features[0] = if lower.starts_with("what") { 1.0 } else { 0.0 };
    features[1] = if lower.starts_with("how") { 1.0 } else { 0.0 };
    features[2] = if lower.starts_with("when") { 1.0 } else { 0.0 };
    features[3] = if lower.starts_with("where") { 1.0 } else { 0.0 };
    features[4] = if lower.starts_with("who") { 1.0 } else { 0.0 };
    features[5] = if lower.starts_with("why") { 1.0 } else { 0.0 };
    
    // 2. Temporal indicators
    let temporal_words = ["before", "after", "during", "while", "then", "first", "last", 
                          "previous", "next", "earlier", "later", "time", "date", "day", 
                          "month", "year", "chronological", "sequence", "order"];
    features[6] = temporal_words.iter().filter(|&&w| lower.contains(w)).count() as f32;
    
    // 3. Multi-hop indicators (connecting words)
    let connective_words = ["and", "then", "after", "which", "that", "leading", "causing",
                           "resulting", "because", "therefore", "thus", "consequently"];
    features[7] = connective_words.iter().filter(|&&w| lower.contains(w)).count() as f32;
    
    // 4. Open-domain indicators (broad/vague terms)
    let vague_words = ["tell me about", "explain", "describe", "what is", "information",
                      "details", "overview", "summary", "topic", "subject"];
    features[8] = vague_words.iter().filter(|&&w| lower.contains(w)).count() as f32;
    
    // 5. Adversarial indicators (negation, contradiction)
    let negation_words = ["not", "never", "no", "without", "except", "but not", 
                          "didn't", "doesn't", "wasn't", "isn't"];
    features[9] = negation_words.iter().filter(|&&w| lower.contains(w)).count() as f32;
    
    // 6. Length features
    features[10] = words.len() as f32;
    features[11] = (words.len() as f32).ln_1p();
    
    // 7. Complexity features
    let avg_word_len: f32 = words.iter().map(|w| w.len()).sum::<usize>() as f32 / words.len().max(1) as f32;
    features[12] = avg_word_len;
    features[13] = words.iter().filter(|w| w.len() > 8).count() as f32; // Long words
    
    // 8. Specificity indicators
    features[14] = words.iter().filter(|w| w.chars().next().map(|c| c.is_uppercase()).unwrap_or(false)).count() as f32;
    
    // 9. Punctuation features
    features[15] = query.chars().filter(|&c| c == '?').count() as f32;
    features[16] = query.chars().filter(|&c| c == '"').count() as f32;
    
    // 10. Query structure
    features[17] = if lower.contains("the") { 1.0 } else { 0.0 }; // Definite article = more specific
    features[18] = words.iter().filter(|w| w.parse::<f64>().is_ok()).count() as f32; // Numbers
    
    // 11. Memory density (quoted content)
    features[19] = query.matches('"').count() as f32 / 2.0;
    
    features
}

/// Classify query intent using weighted scoring
fn classify_intent(features: &[f32]) -> QueryIntent {
    // Hand-tuned weights based on LoCoMo analysis
    let temporal_score = features[2] * 0.4 + features[6] * 0.3 + features[19] * 0.2;
    let multihop_score = features[7] * 0.3 + features[10] * 0.05 + features[14] * 0.1;
    let opendomain_score = features[8] * 0.4 + features[10] * 0.02 + features[17] * -0.1;
    let adversarial_score = features[9] * 0.3 + features[15] * 0.1 + features[16] * 0.1;
    let singlehop_score = features[14] * 0.3 + features[17] * 0.2 + features[18] * 0.1;
    
    let scores = [
        ("temporal", temporal_score),
        ("multihop", multihop_score),
        ("opendomain", opendomain_score),
        ("adversarial", adversarial_score),
        ("singlehop", singlehop_score),
    ];
    
    // Find max score
    let max = scores.iter().max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal)).unwrap();
    
    // Threshold-based classification
    if max.1 < 0.3 {
        QueryIntent::Unknown
    } else {
        match max.0 {
            "temporal" => QueryIntent::Temporal,
            "multihop" => QueryIntent::MultiHop,
            "opendomain" => QueryIntent::OpenDomain,
            "adversarial" => QueryIntent::Adversarial,
            _ => QueryIntent::SingleHop,
        }
    }
}

/// Python-exposed intent classification
#[pyfunction]
fn classify_query_intent(query: String) -> PyResult<String> {
    let features = extract_intent_features(&query);
    let intent = classify_intent(&features);
    
    let result = match intent {
        QueryIntent::SingleHop => "single_hop",
        QueryIntent::MultiHop => "multi_hop",
        QueryIntent::Temporal => "temporal",
        QueryIntent::OpenDomain => "open_domain",
        QueryIntent::Adversarial => "adversarial",
        QueryIntent::Unknown => "unknown",
    };
    
    Ok(result.to_string())
}

/// Batch classify multiple queries (parallel)
#[pyfunction]
fn classify_query_intent_batch(queries: Vec<String>) -> PyResult<Vec<String>> {
    use rayon::prelude::*;
    
    let results: Vec<_> = queries.par_iter()
        .map(|q| {
            let features = extract_intent_features(q);
            let intent = classify_intent(&features);
            match intent {
                QueryIntent::SingleHop => "single_hop".to_string(),
                QueryIntent::MultiHop => "multi_hop".to_string(),
                QueryIntent::Temporal => "temporal".to_string(),
                QueryIntent::OpenDomain => "open_domain".to_string(),
                QueryIntent::Adversarial => "adversarial".to_string(),
                QueryIntent::Unknown => "unknown".to_string(),
            }
        })
        .collect();
    
    Ok(results)
}

/// Get intent scores for all types (for confidence thresholding)
#[pyfunction]
fn classify_query_intent_with_scores(query: String) -> PyResult<Vec<(String, f32)>> {
    let features = extract_intent_features(&query);
    
    let temporal_score = features[2] * 0.4 + features[6] * 0.3 + features[19] * 0.2;
    let multihop_score = features[7] * 0.3 + features[10] * 0.05 + features[14] * 0.1;
    let opendomain_score = features[8] * 0.4 + features[10] * 0.02 + features[17] * -0.1;
    let adversarial_score = features[9] * 0.3 + features[15] * 0.1 + features[16] * 0.1;
    let singlehop_score = features[14] * 0.3 + features[17] * 0.2 + features[18] * 0.1;
    
    let mut results = vec![
        ("temporal".to_string(), temporal_score),
        ("multi_hop".to_string(), multihop_score),
        ("open_domain".to_string(), opendomain_score),
        ("adversarial".to_string(), adversarial_score),
        ("single_hop".to_string(), singlehop_score),
    ];
    
    // Normalize to probabilities
    let sum: f32 = results.iter().map(|(_, s)| s.exp()).sum();
    for (_, score) in &mut results {
        *score = score.exp() / sum;
    }
    
    // Sort by score descending
    results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    
    Ok(results)
}

pub fn register_query_intent(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(classify_query_intent, m)?)?;
    m.add_function(wrap_pyfunction!(classify_query_intent_batch, m)?)?;
    m.add_function(wrap_pyfunction!(classify_query_intent_with_scores, m)?)?;
    Ok(())
}
