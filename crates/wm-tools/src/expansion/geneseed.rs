//! 🧬 Geneseed Codebase Vault Miner & Ingestion Engine
//!
//! High-performance Rust implementation for mining optimization patterns
//! from git repository history. Analyzes commits, diffs, and architectural longevity.
//! Ports proven patterns into the Geneseed Vault (`Galaxy::Codex` / `Galaxy::Research`).

#![forbid(unsafe_code)]

use async_trait::async_trait;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::Path;
use std::process::Command;
use std::sync::Arc;
use wm_core::{Context, CoreError, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;
use wm_memory::memory::{Memory, Tier};
use wm_memory::typology::MemoryClass;

use super::common::parse_galaxy;

/// A mined optimization pattern from git history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationPattern {
    pub pattern_id: String,
    pub pattern_type: String, // 'performance', 'refactor', 'bugfix', 'feature'
    pub commit_hash: String,
    pub commit_message: String,
    pub author: String,
    pub timestamp: String,
    pub files_changed: Vec<String>,
    pub lines_added: i32,
    pub lines_removed: i32,
    pub confidence: f64,
    pub longevity_days: i32, // Days since commit (older = more proven)
}

/// High-level git repository longevity and pattern statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneseedStats {
    pub total_commits: i32,
    pub optimization_commits: i32,
    pub refactor_commits: i32,
    pub bugfix_commits: i32,
    pub feature_commits: i32,
    pub total_files_tracked: i32,
    pub avg_commit_age_days: f64,
}

fn unix_ts_to_date(ts: i64) -> String {
    if ts <= 0 {
        return "unknown".to_string();
    }
    let days = (ts as u64) / 86400;
    let year = 1970u64 + days * 10000 / 3652425;
    let day_of_year = days - (year - 1970) * 3652425 / 10000;
    let months = [31u64, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut rem = day_of_year;
    let mut month = 1u64;
    for &days_in_month in &months {
        if rem < days_in_month {
            break;
        }
        rem -= days_in_month;
        month += 1;
    }
    let day = rem + 1;
    format!("{year}-{month:02}-{day:02}")
}

#[allow(clippy::too_many_arguments)]
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
    let longevity_days = ((now - timestamp).max(0) / 86400) as i32;

    let (pattern_type, base_confidence): (&str, f64) = if message_lower.contains("perf")
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
        return None;
    };

    let longevity_boost = (f64::from(longevity_days) / 365.0).min(0.2);
    let total_changes = added + removed;
    let size_factor: f64 = if total_changes < 10 {
        0.9
    } else if total_changes < 100 {
        1.1
    } else if total_changes < 500 {
        1.0
    } else {
        0.8
    };

    let confidence = (base_confidence + longevity_boost) * size_factor;
    if confidence < min_confidence {
        return None;
    }

    Some(OptimizationPattern {
        pattern_id: format!("{pattern_type}_{}", &hash[..8.min(hash.len())]),
        pattern_type: pattern_type.to_string(),
        commit_hash: hash,
        commit_message: message,
        author,
        timestamp: unix_ts_to_date(timestamp),
        files_changed: files,
        lines_added: added,
        lines_removed: removed,
        confidence,
        longevity_days,
    })
}

/// Mine optimization patterns from git history at `repo_path`.
pub fn mine_geneseed_patterns(
    repo_path: &Path,
    min_confidence: f64,
    max_commits: usize,
) -> wm_core::Result<Vec<OptimizationPattern>> {
    if !repo_path.exists() {
        return Err(CoreError::NotFound(format!(
            "Repository directory not found: {}",
            repo_path.display()
        )));
    }

    let output = Command::new("git")
        .args([
            "log",
            &format!("--max-count={max_commits}"),
            "--pretty=format:%H|%an|%at|%s",
            "--numstat",
        ])
        .current_dir(repo_path)
        .output()
        .map_err(|e| CoreError::Tool(format!("Git command failed: {e}")))?;

    if !output.status.success() {
        return Err(CoreError::Tool("Git log command failed".into()));
    }

    let log_output = String::from_utf8_lossy(&output.stdout);
    let mut patterns = Vec::new();
    let mut current_commit: Option<(String, String, i64, String)> = None;
    let mut files_changed: Vec<String> = Vec::new();
    let mut lines_added = 0i32;
    let mut lines_removed = 0i32;

    let now_timestamp = i64::try_from(
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    )
    .unwrap_or(0);

    for line in log_output.lines() {
        if line.contains('|') && !line.starts_with(|c: char| c.is_ascii_digit()) {
            if let Some((hash, author, timestamp, message)) = current_commit.take() {
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
            let parts: Vec<&str> = line.splitn(4, '|').collect();
            if parts.len() >= 4 {
                current_commit = Some((
                    parts[0].to_string(),
                    parts[1].to_string(),
                    parts[2].parse().unwrap_or(0),
                    parts[3].to_string(),
                ));
                files_changed.clear();
                lines_added = 0;
                lines_removed = 0;
            }
        } else if !line.is_empty() && line.chars().next().is_some_and(|c| c.is_ascii_digit()) {
            let parts: Vec<&str> = line.splitn(3, '\t').collect();
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

/// Compute high-level pattern statistics for a git repository.
pub fn get_geneseed_stats(repo_path: &Path) -> wm_core::Result<GeneseedStats> {
    if !repo_path.exists() {
        return Err(CoreError::NotFound(format!(
            "Repository directory not found: {}",
            repo_path.display()
        )));
    }

    let output = Command::new("git")
        .args(["rev-list", "--count", "HEAD"])
        .current_dir(repo_path)
        .output()
        .map_err(|e| CoreError::Tool(format!("Git rev-list failed: {e}")))?;

    let total_commits = String::from_utf8_lossy(&output.stdout)
        .trim()
        .parse::<i32>()
        .unwrap_or(0);

    let output = Command::new("git")
        .args(["log", "--pretty=format:%s", "--max-count=1000"])
        .current_dir(repo_path)
        .output()
        .map_err(|e| CoreError::Tool(format!("Git log messages failed: {e}")))?;

    let messages = String::from_utf8_lossy(&output.stdout);
    let mut optimization_commits = 0i32;
    let mut refactor_commits = 0i32;
    let mut bugfix_commits = 0i32;
    let mut feature_commits = 0i32;

    for msg in messages.lines() {
        let msg_lower = msg.to_lowercase();
        if msg_lower.contains("perf") || msg_lower.contains("optim") {
            optimization_commits += 1;
        } else if msg_lower.contains("refactor") || msg_lower.contains("cleanup") {
            refactor_commits += 1;
        } else if msg_lower.contains("fix") || msg_lower.contains("bug") {
            bugfix_commits += 1;
        } else if msg_lower.contains("feat") || msg_lower.contains("add") {
            feature_commits += 1;
        }
    }

    let output = Command::new("git")
        .args(["ls-files"])
        .current_dir(repo_path)
        .output()
        .map_err(|e| CoreError::Tool(format!("Git ls-files failed: {e}")))?;

    let total_files =
        i32::try_from(String::from_utf8_lossy(&output.stdout).lines().count()).unwrap_or(0);

    let output = Command::new("git")
        .args(["log", "--pretty=format:%at", "--max-count=100"])
        .current_dir(repo_path)
        .output()
        .map_err(|e| CoreError::Tool(format!("Git log timestamps failed: {e}")))?;

    let timestamps = String::from_utf8_lossy(&output.stdout);
    let now = Utc::now().timestamp();
    let mut total_age = 0.0;
    let mut count = 0;

    for ts_str in timestamps.lines() {
        if let Ok(ts) = ts_str.parse::<i64>() {
            let age_days = (now - ts).max(0) as f64 / 86400.0;
            total_age += age_days;
            count += 1;
        }
    }

    let avg_commit_age_days = if count > 0 {
        total_age / f64::from(count)
    } else {
        0.0
    };

    Ok(GeneseedStats {
        total_commits,
        optimization_commits,
        refactor_commits,
        bugfix_commits,
        feature_commits,
        total_files_tracked: total_files,
        avg_commit_age_days,
    })
}

/// Store mined patterns into the Geneseed Vault in LMDB.
pub fn store_patterns_in_vault(
    store: &MemoryStore,
    patterns: &[OptimizationPattern],
    galaxy: Galaxy,
) -> wm_core::Result<usize> {
    let mut stored = 0usize;

    for p in patterns {
        let title = format!("Geneseed Pattern: {} ({})", p.pattern_id, p.pattern_type);
        let files_list = p
            .files_changed
            .iter()
            .take(5)
            .cloned()
            .collect::<Vec<_>>()
            .join(", ");
        let content = format!(
            "### {}\n\n- **Pattern Type**: `{}`\n- **Commit**: `{}` ({})\n- **Author**: {}\n- **Longevity**: {} days (provenance score)\n- **Confidence**: {:.2}\n- **Impact**: +{} / -{} lines\n- **Primary Files**: {}\n\n> {}",
            title,
            p.pattern_type,
            &p.commit_hash[..8.min(p.commit_hash.len())],
            p.timestamp,
            p.author,
            p.longevity_days,
            p.confidence,
            p.lines_added,
            p.lines_removed,
            files_list,
            p.commit_message
        );

        let mut mem = Memory::new(galaxy, content);
        mem.metadata.importance = (p.confidence as f32).clamp(0.4, 0.95);
        mem.metadata.class = Some(MemoryClass::Knowledge);
        mem.metadata.tier = Tier::Semantic;
        mem.metadata.tags = vec![
            "geneseed:pattern".into(),
            format!("pattern_type:{}", p.pattern_type),
            format!("commit:{}", &p.commit_hash[..8.min(p.commit_hash.len())]),
            format!("longevity:{}d", p.longevity_days),
        ];

        store.put(galaxy, &mem)?;
        stored += 1;
    }

    Ok(stored)
}

// ── Tools ──────────────────────────────────────────────────────────────

pub struct GeneseedMineTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GeneseedMineTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Filesystem, Resource::Process],
                writes: vec![Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for GeneseedMineTool {
    fn name(&self) -> &str {
        "geneseed.mine"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Mine optimization patterns from git history and optionally store them in the Geneseed Vault."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let repo_path_str = args.get("repo_path").and_then(Value::as_str).unwrap_or(".");
        let min_confidence = args
            .get("min_confidence")
            .and_then(Value::as_f64)
            .unwrap_or(0.5);
        let max_commits = args
            .get("max_commits")
            .and_then(Value::as_u64)
            .unwrap_or(250) as usize;
        let store_in_vault = args
            .get("store_in_vault")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let galaxy_str = args.get("vault_galaxy").and_then(Value::as_str);

        let galaxy = match galaxy_str {
            Some(g) => parse_galaxy(g)?,
            None => Galaxy::Codex,
        };

        let repo_path = Path::new(repo_path_str);
        let patterns = mine_geneseed_patterns(repo_path, min_confidence, max_commits)?;

        let stored_count = if store_in_vault {
            store_patterns_in_vault(&self.store, &patterns, galaxy)?
        } else {
            0
        };

        Ok(json!({
            "status": "success",
            "repo_path": repo_path.display().to_string(),
            "patterns_mined": patterns.len(),
            "stored_in_vault": store_in_vault,
            "stored_count": stored_count,
            "vault_galaxy": galaxy.db_name(),
            "patterns": patterns.iter().take(20).collect::<Vec<_>>()
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

pub struct GeneseedStatsTool {
    _store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GeneseedStatsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            _store: store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Filesystem, Resource::Process]),
        }
    }
}

#[async_trait]
impl Tool for GeneseedStatsTool {
    fn name(&self) -> &str {
        "geneseed.stats"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Retrieve repository-level pattern and architectural longevity statistics."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let repo_path_str = args.get("repo_path").and_then(Value::as_str).unwrap_or(".");
        let repo_path = Path::new(repo_path_str);
        let stats = get_geneseed_stats(repo_path)?;

        Ok(json!({
            "status": "success",
            "repo_path": repo_path.display().to_string(),
            "total_commits": stats.total_commits,
            "optimization_commits": stats.optimization_commits,
            "refactor_commits": stats.refactor_commits,
            "bugfix_commits": stats.bugfix_commits,
            "feature_commits": stats.feature_commits,
            "total_files_tracked": stats.total_files_tracked,
            "avg_commit_age_days": stats.avg_commit_age_days
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classify_commit_heuristics() {
        let now = 1757100000;
        let ts = now - (100 * 86400); // 100 days old

        // Performance commit
        let p = classify_commit(
            "abc123456789".into(),
            "maintainer".into(),
            ts,
            "perf: optimize LMDB batch reads and vector cache".into(),
            vec!["store.rs".into()],
            45,
            12,
            now,
            0.5,
        );
        assert!(p.is_some());
        let pattern = p.unwrap();
        assert_eq!(pattern.pattern_type, "performance");
        assert_eq!(pattern.longevity_days, 100);
        assert!(pattern.confidence > 0.8);

        // Feature commit
        let f = classify_commit(
            "def987654321".into(),
            "maintainer".into(),
            ts,
            "feat: add new holographic coordinate mapper".into(),
            vec!["coords.rs".into()],
            150,
            10,
            now,
            0.3,
        );
        assert!(f.is_some());
        let feat = f.unwrap();
        assert_eq!(feat.pattern_type, "feature");
    }

    #[test]
    fn test_store_patterns_in_vault() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let pattern = OptimizationPattern {
            pattern_id: "performance_12345678".into(),
            pattern_type: "performance".into(),
            commit_hash: "1234567890abcdef".into(),
            commit_message: "perf(cache): vector caching layer".into(),
            author: "maintainer".into(),
            timestamp: "2026-06-01".into(),
            files_changed: vec!["cache.rs".into()],
            lines_added: 30,
            lines_removed: 5,
            confidence: 0.92,
            longevity_days: 90,
        };

        let stored = store_patterns_in_vault(&store, &[pattern], Galaxy::Codex).unwrap();
        assert_eq!(stored, 1);

        let mems = store.scan(Galaxy::Codex, 10).unwrap();
        assert_eq!(mems.len(), 1);
        assert!(mems[0].content.contains("Geneseed Pattern"));
        assert_eq!(mems[0].metadata.class, Some(MemoryClass::Knowledge));
        assert!(
            mems[0]
                .metadata
                .tags
                .contains(&"geneseed:pattern".to_string())
        );
    }
}
