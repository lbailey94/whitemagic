//! 🎯 Pattern Scorer - High-Performance Multi-Factor Confidence Scoring
//!
//! Rust implementation for scoring patterns with:
//! - Cross-validation (40%): Multiple independent sources
//! - Outcome (30%): Measured improvements/importance
//! - Frequency (20%): Occurrence count
//! - Longevity (10%): Time in production
//!
//! 10-50x faster than Python implementation.

use pyo3::prelude::*;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};

/// Scoring configuration
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoringConfig {
    #[pyo3(get, set)]
    pub cv_weight: f64,
    
    #[pyo3(get, set)]
    pub outcome_weight: f64,
    
    #[pyo3(get, set)]
    pub frequency_weight: f64,
    
    #[pyo3(get, set)]
    pub longevity_weight: f64,
    
    #[pyo3(get, set)]
    pub cross_source_boost: f64,
}

#[pymethods]
impl ScoringConfig {
    #[new]
    fn new() -> Self {
        Self::default()
    }
}

impl Default for ScoringConfig {
    fn default() -> Self {
        Self {
            cv_weight: 0.4,
            outcome_weight: 0.3,
            frequency_weight: 0.2,
            longevity_weight: 0.1,
            cross_source_boost: 0.15,
        }
    }
}

/// Scored pattern with detailed breakdown
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredPattern {
    #[pyo3(get)]
    pub pattern_id: String,
    
    #[pyo3(get)]
    pub pattern_type: String,
    
    #[pyo3(get)]
    pub sources: Vec<String>,
    
    #[pyo3(get)]
    pub cv_score: f64,
    
    #[pyo3(get)]
    pub outcome_score: f64,
    
    #[pyo3(get)]
    pub frequency_score: f64,
    
    #[pyo3(get)]
    pub longevity_score: f64,
    
    #[pyo3(get)]
    pub final_confidence: f64,
    
    #[pyo3(get)]
    pub cross_validated: bool,
    
    #[pyo3(get)]
    pub metadata: String,
}

#[pymethods]
impl ScoredPattern {
    fn __repr__(&self) -> String {
        format!(
            "ScoredPattern(id='{}', confidence={:.2}%, cv={:.2}%, outcome={:.2}%, freq={:.2}%, long={:.2}%)",
            self.pattern_id,
            self.final_confidence * 100.0,
            self.cv_score * 100.0,
            self.outcome_score * 100.0,
            self.frequency_score * 100.0,
            self.longevity_score * 100.0
        )
    }
    
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON error: {}", e)))
    }
}

/// Score a single pattern (used internally)
fn score_pattern(
    pattern_id: String,
    pattern_type: String,
    sources: Vec<String>,
    cv_raw: f64,
    outcome_raw: f64,
    frequency_raw: f64,
    longevity_raw: f64,
    config: &ScoringConfig,
) -> ScoredPattern {
    // Normalize scores to 0-1 range
    let cv_score = cv_raw.min(1.0).max(0.0);
    let outcome_score = outcome_raw.min(1.0).max(0.0);
    let frequency_score = frequency_raw.min(1.0).max(0.0);
    let longevity_score = longevity_raw.min(1.0).max(0.0);
    
    // Calculate weighted final confidence
    let final_confidence = 
        config.cv_weight * cv_score +
        config.outcome_weight * outcome_score +
        config.frequency_weight * frequency_score +
        config.longevity_weight * longevity_score;
    
    // Cross-validated if multiple sources
    let cross_validated = sources.len() > 1;
    
    ScoredPattern {
        pattern_id,
        pattern_type,
        sources,
        cv_score,
        outcome_score,
        frequency_score,
        longevity_score,
        final_confidence,
        cross_validated,
        metadata: String::new(),
    }
}

/// Batch score patterns (parallel processing)
#[pyfunction]
pub fn batch_score_patterns(
    patterns_json: &str,
    config: Option<ScoringConfig>,
) -> PyResult<Vec<ScoredPattern>> {
    let config = config.unwrap_or_default();
    
    // Parse input patterns
    #[derive(Deserialize)]
    struct PatternInput {
        pattern_id: String,
        pattern_type: String,
        sources: Vec<String>,
        cv_raw: f64,
        outcome_raw: f64,
        frequency_raw: f64,
        longevity_raw: f64,
    }
    
    let patterns: Vec<PatternInput> = serde_json::from_str(patterns_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid JSON: {}", e)))?;
    
    // Parallel scoring
    let scored: Vec<ScoredPattern> = patterns
        .par_iter()
        .map(|p| {
            score_pattern(
                p.pattern_id.clone(),
                p.pattern_type.clone(),
                p.sources.clone(),
                p.cv_raw,
                p.outcome_raw,
                p.frequency_raw,
                p.longevity_raw,
                &config,
            )
        })
        .collect();
    
    Ok(scored)
}

/// Score galaxy patterns (optimized for galaxy archive data)
#[pyfunction]
pub fn score_galaxy_patterns(
    tags_json: &str,
    config: Option<ScoringConfig>,
) -> PyResult<Vec<ScoredPattern>> {
    let config = config.unwrap_or_default();
    
    // Parse galaxy tag data
    #[derive(Deserialize)]
    struct GalaxyTag {
        tag: String,
        cluster_count: usize,
        total_size: usize,
        avg_importance: f64,
    }
    
    let tags: Vec<GalaxyTag> = serde_json::from_str(tags_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid JSON: {}", e)))?;
    
    // Parallel scoring
    let scored: Vec<ScoredPattern> = tags
        .par_iter()
        .map(|tag| {
            // CV score: max at 5 clusters
            let cv_score = (tag.cluster_count as f64 / 5.0).min(1.0);
            
            // Outcome score: importance normalized to 1.0
            let outcome_score = (tag.avg_importance / 1.0).min(1.0);
            
            // Frequency score: max at 100 memories
            let frequency_score = (tag.total_size as f64 / 100.0).min(1.0);
            
            // Longevity score: archive data = proven
            let longevity_score = 0.8;
            
            // Sources
            let sources: Vec<String> = (0..tag.cluster_count)
                .map(|i| format!("cluster_{}", i))
                .collect();
            
            score_pattern(
                format!("galaxy_{}", tag.tag),
                "semantic_cluster".to_string(),
                sources,
                cv_score,
                outcome_score,
                frequency_score,
                longevity_score,
                &config,
            )
        })
        .collect();
    
    Ok(scored)
}

/// Score geneseed patterns (optimized for git commit data)
#[pyfunction]
pub fn score_geneseed_patterns(
    commits_json: &str,
    config: Option<ScoringConfig>,
) -> PyResult<Vec<ScoredPattern>> {
    let config = config.unwrap_or_default();
    
    // Parse geneseed commit data
    #[derive(Deserialize)]
    struct GeneseedCommit {
        pattern_id: String,
        pattern_type: String,
        commit_hash: String,
        confidence: f64,
        longevity_days: u32,
        lines_changed: usize,
    }
    
    let commits: Vec<GeneseedCommit> = serde_json::from_str(commits_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid JSON: {}", e)))?;
    
    // Parallel scoring
    let scored: Vec<ScoredPattern> = commits
        .par_iter()
        .map(|commit| {
            // CV score: single source but git is authoritative
            let cv_score = 0.6;
            
            // Outcome score: use pattern's built-in confidence
            let outcome_score = commit.confidence;
            
            // Frequency score: based on change size
            let frequency_score = if commit.lines_changed < 10 {
                0.3
            } else if commit.lines_changed < 100 {
                1.0
            } else if commit.lines_changed < 500 {
                0.8
            } else {
                0.5
            };
            
            // Longevity score: max at 365 days
            let longevity_score = (commit.longevity_days as f64 / 365.0).min(1.0);
            
            score_pattern(
                commit.pattern_id.clone(),
                format!("geneseed_{}", commit.pattern_type),
                vec![commit.commit_hash[..8].to_string()],
                cv_score,
                outcome_score,
                frequency_score,
                longevity_score,
                &config,
            )
        })
        .collect();
    
    Ok(scored)
}

/// Apply cross-source boost to patterns (parallel)
#[pyfunction]
pub fn apply_cross_source_boost(
    mut patterns: Vec<ScoredPattern>,
    matching_tags: Vec<String>,
    config: Option<ScoringConfig>,
) -> Vec<ScoredPattern> {
    let config = config.unwrap_or_default();
    let matching_set: std::collections::HashSet<String> = matching_tags.into_iter().collect();
    
    patterns.par_iter_mut().for_each(|pattern| {
        // Extract tag from pattern_id
        let tag = pattern.pattern_id.strip_prefix("galaxy_").unwrap_or(&pattern.pattern_id);
        
        if matching_set.contains(tag) {
            // Boost confidence
            pattern.final_confidence = (pattern.final_confidence + config.cross_source_boost).min(1.0);
            pattern.cv_score = (pattern.cv_score + 0.2).min(1.0);
            pattern.cross_validated = true;
        }
    });
    
    patterns
}

/// Filter and sort patterns by confidence
#[pyfunction]
pub fn filter_patterns(
    patterns: Vec<ScoredPattern>,
    min_confidence: f64,
    max_count: Option<usize>,
) -> Vec<ScoredPattern> {
    let mut filtered: Vec<ScoredPattern> = patterns
        .into_iter()
        .filter(|p| p.final_confidence >= min_confidence)
        .collect();
    
    // Sort by confidence (descending)
    filtered.sort_by(|a, b| b.final_confidence.partial_cmp(&a.final_confidence).unwrap());
    
    // Limit count if specified
    if let Some(max) = max_count {
        filtered.truncate(max);
    }
    
    filtered
}

/// Get scoring statistics
#[pyfunction]
pub fn get_scoring_stats(patterns: Vec<ScoredPattern>) -> PyResult<String> {
    let total = patterns.len();
    
    if total == 0 {
        return Ok(serde_json::json!({
            "total": 0,
            "avg_confidence": 0.0,
        }).to_string());
    }
    
    let ultra_high = patterns.iter().filter(|p| p.final_confidence >= 0.77).count();
    let high = patterns.iter().filter(|p| p.final_confidence >= 0.6 && p.final_confidence < 0.77).count();
    let medium = patterns.iter().filter(|p| p.final_confidence >= 0.5 && p.final_confidence < 0.6).count();
    let cross_validated = patterns.iter().filter(|p| p.cross_validated).count();
    
    let avg_confidence = patterns.iter().map(|p| p.final_confidence).sum::<f64>() / total as f64;
    let avg_cv = patterns.iter().map(|p| p.cv_score).sum::<f64>() / total as f64;
    let avg_outcome = patterns.iter().map(|p| p.outcome_score).sum::<f64>() / total as f64;
    let avg_frequency = patterns.iter().map(|p| p.frequency_score).sum::<f64>() / total as f64;
    let avg_longevity = patterns.iter().map(|p| p.longevity_score).sum::<f64>() / total as f64;
    
    let stats = serde_json::json!({
        "total": total,
        "ultra_high_confidence": ultra_high,
        "high_confidence": high,
        "medium_confidence": medium,
        "cross_validated": cross_validated,
        "avg_confidence": avg_confidence,
        "avg_cv_score": avg_cv,
        "avg_outcome_score": avg_outcome,
        "avg_frequency_score": avg_frequency,
        "avg_longevity_score": avg_longevity,
    });
    
    Ok(stats.to_string())
}
