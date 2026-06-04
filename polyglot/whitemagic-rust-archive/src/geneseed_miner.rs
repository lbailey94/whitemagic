//! 🧬 Geneseed Codebase Vault Miner - Git History Pattern Extraction
//!
//! High-performance Rust implementation for mining optimization patterns
//! from git repository history. Analyzes commits, diffs, and evolution.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct OptimizationPattern {
    #[pyo3(get)]
    pub pattern_id: String,
    #[pyo3(get)]
    pub pattern_type: String,  // 'performance', 'refactor', 'bugfix', 'feature'
    #[pyo3(get)]
    pub commit_hash: String,
    #[pyo3(get)]
    pub commit_message: String,
    #[pyo3(get)]
    pub author: String,
    #[pyo3(get)]
    pub timestamp: String,
    #[pyo3(get)]
    pub files_changed: Vec<String>,
    #[pyo3(get)]
    pub lines_added: i32,
    #[pyo3(get)]
    pub lines_removed: i32,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub longevity_days: i32,  // Days since commit (older = more proven)
}

#[pymethods]
impl OptimizationPattern {
    fn __repr__(&self) -> String {
        format!(
            "OptimizationPattern(id={}, type={}, confidence={:.2})",
            self.pattern_id, self.pattern_type, self.confidence
        )
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct GeneseedStats {
    #[pyo3(get)]
    pub total_commits: i32,
    #[pyo3(get)]
    pub optimization_commits: i32,
    #[pyo3(get)]
    pub refactor_commits: i32,
    #[pyo3(get)]
    pub bugfix_commits: i32,
    #[pyo3(get)]
    pub total_files_tracked: i32,
    #[pyo3(get)]
    pub avg_commit_age_days: f64,
}

#[pymethods]
impl GeneseedStats {
    fn __repr__(&self) -> String {
        format!(
            "GeneseedStats(commits={}, optimizations={}, avg_age={:.1}d)",
            self.total_commits, self.optimization_commits, self.avg_commit_age_days
        )
    }
}

/// Mine optimization patterns from git repository history
#[pyfunction]
pub fn mine_geneseed_patterns(
    repo_path: String,
    min_confidence: f64,
    max_commits: i32,
) -> PyResult<Vec<OptimizationPattern>> {
    let path = Path::new(&repo_path);
    
    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Repository not found: {}", repo_path)
        ));
    }
    
    // Get git log with stats
    let output = Command::new("git")
        .args(&[
            "log",
            &format!("--max-count={}", max_commits),
            "--pretty=format:%H|%an|%at|%s",
            "--numstat",
        ])
        .current_dir(path)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Git command failed: {}", e)
        ))?;
    
    if !output.status.success() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "Git log command failed"
        ));
    }
    
    let log_output = String::from_utf8_lossy(&output.stdout);
    let mut patterns = Vec::new();
    let mut current_commit: Option<(String, String, i64, String)> = None;
    let mut files_changed = Vec::new();
    let mut lines_added = 0i32;
    let mut lines_removed = 0i32;
    
    let now_timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64;
    
    for line in log_output.lines() {
        if line.contains('|') && !line.starts_with(char::is_numeric) {
            // Commit header line: hash|author|timestamp|message
            if let Some((hash, author, timestamp, message)) = current_commit.take() {
                // Process previous commit
                if let Some(pattern) = classify_commit(
                    hash,
                    author,
                    timestamp,
                    message,
                    files_changed.clone(),
                    lines_added,
                    lines_removed,
                    now_timestamp,
                    min_confidence,
                ) {
                    patterns.push(pattern);
                }
            }
            
            // Parse new commit
            let parts: Vec<&str> = line.split('|').collect();
            if parts.len() >= 4 {
                current_commit = Some((
                    parts[0].to_string(),
                    parts[1].to_string(),
                    parts[2].parse().unwrap_or(0),
                    parts[3..].join("|"),
                ));
                files_changed.clear();
                lines_added = 0;
                lines_removed = 0;
            }
        } else if !line.is_empty() && line.chars().next().map_or(false, |c| c.is_numeric()) {
            // Numstat line: added\tremoved\tfilename
            let parts: Vec<&str> = line.split('\t').collect();
            if parts.len() >= 3 {
                if let Ok(added) = parts[0].parse::<i32>() {
                    lines_added += added;
                }
                if let Ok(removed) = parts[1].parse::<i32>() {
                    lines_removed += removed;
                }
                files_changed.push(parts[2].to_string());
            }
        }
    }
    
    // Process last commit
    if let Some((hash, author, timestamp, message)) = current_commit {
        if let Some(pattern) = classify_commit(
            hash,
            author,
            timestamp,
            message,
            files_changed,
            lines_added,
            lines_removed,
            now_timestamp,
            min_confidence,
        ) {
            patterns.push(pattern);
        }
    }
    
    Ok(patterns)
}

fn classify_commit(
    hash: String,
    author: String,
    timestamp: i64,
    message: String,
    files: Vec<String>,
    added: i32,
    removed: i32,
    now: i64,
    min_confidence: f64,
) -> Option<OptimizationPattern> {
    let message_lower = message.to_lowercase();
    let longevity_days = ((now - timestamp) / 86400) as i32;
    
    // Pattern classification based on commit message keywords
    let (pattern_type, base_confidence) = if message_lower.contains("perf")
        || message_lower.contains("optim")
        || message_lower.contains("speed")
        || message_lower.contains("faster")
        || message_lower.contains("cache")
    {
        ("performance", 0.8)
    } else if message_lower.contains("refactor")
        || message_lower.contains("cleanup")
        || message_lower.contains("simplify")
    {
        ("refactor", 0.6)
    } else if message_lower.contains("fix")
        || message_lower.contains("bug")
        || message_lower.contains("issue")
    {
        ("bugfix", 0.5)
    } else if message_lower.contains("feat")
        || message_lower.contains("add")
        || message_lower.contains("implement")
    {
        ("feature", 0.4)
    } else {
        return None;  // Skip non-pattern commits
    };
    
    // Adjust confidence based on longevity (older = more proven)
    let longevity_boost = (longevity_days as f64 / 365.0).min(0.2);
    
    // Adjust confidence based on change size (moderate changes = better)
    let total_changes = added + removed;
    let size_factor = if total_changes < 10 {
        0.9  // Too small
    } else if total_changes < 100 {
        1.1  // Sweet spot
    } else if total_changes < 500 {
        1.0  // Good
    } else {
        0.8  // Too large
    };
    
    let confidence = (base_confidence + longevity_boost) * size_factor;
    
    if confidence < min_confidence {
        return None;
    }
    
    let timestamp_str = chrono::DateTime::from_timestamp(timestamp, 0)
        .map(|dt| dt.format("%Y-%m-%d %H:%M:%S").to_string())
        .unwrap_or_else(|| "unknown".to_string());
    
    Some(OptimizationPattern {
        pattern_id: format!("{}_{}", pattern_type, &hash[..8]),
        pattern_type: pattern_type.to_string(),
        commit_hash: hash,
        commit_message: message,
        author,
        timestamp: timestamp_str,
        files_changed: files,
        lines_added: added,
        lines_removed: removed,
        confidence,
        longevity_days,
    })
}

/// Get repository statistics
#[pyfunction]
pub fn get_geneseed_stats(repo_path: String) -> PyResult<GeneseedStats> {
    let path = Path::new(&repo_path);
    
    if !path.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
            format!("Repository not found: {}", repo_path)
        ));
    }
    
    // Count total commits
    let output = Command::new("git")
        .args(&["rev-list", "--count", "HEAD"])
        .current_dir(path)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Git command failed: {}", e)
        ))?;
    
    let total_commits = String::from_utf8_lossy(&output.stdout)
        .trim()
        .parse::<i32>()
        .unwrap_or(0);
    
    // Get commit messages for classification
    let output = Command::new("git")
        .args(&["log", "--pretty=format:%s", "--max-count=1000"])
        .current_dir(path)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Git command failed: {}", e)
        ))?;
    
    let messages = String::from_utf8_lossy(&output.stdout);
    let mut optimization_commits = 0;
    let mut refactor_commits = 0;
    let mut bugfix_commits = 0;
    
    for msg in messages.lines() {
        let msg_lower = msg.to_lowercase();
        if msg_lower.contains("perf") || msg_lower.contains("optim") {
            optimization_commits += 1;
        }
        if msg_lower.contains("refactor") || msg_lower.contains("cleanup") {
            refactor_commits += 1;
        }
        if msg_lower.contains("fix") || msg_lower.contains("bug") {
            bugfix_commits += 1;
        }
    }
    
    // Count tracked files
    let output = Command::new("git")
        .args(&["ls-files"])
        .current_dir(path)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Git command failed: {}", e)
        ))?;
    
    let total_files = String::from_utf8_lossy(&output.stdout)
        .lines()
        .count() as i32;
    
    // Get average commit age
    let output = Command::new("git")
        .args(&["log", "--pretty=format:%at", "--max-count=100"])
        .current_dir(path)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Git command failed: {}", e)
        ))?;
    
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64;
    
    let timestamps: Vec<i64> = String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.parse().ok())
        .collect();
    
    let avg_age_days = if !timestamps.is_empty() {
        let total_age: i64 = timestamps.iter().map(|&ts| now - ts).sum();
        (total_age / timestamps.len() as i64) as f64 / 86400.0
    } else {
        0.0
    };
    
    Ok(GeneseedStats {
        total_commits,
        optimization_commits,
        refactor_commits,
        bugfix_commits,
        total_files_tracked: total_files,
        avg_commit_age_days: avg_age_days,
    })
}
