//! OSS bounty scanner — `oss.bounty.scan` / `oss.bounty.status`.
//!
//! Rust port of the archived `oss_scanner.py`: scans GitHub repos/orgs for
//! bounty-labeled issues (Algora / Opire) via the `gh` CLI. Read-only;
//! spawning `gh` is the only effect. If `gh` is unavailable the scan
//! reports the reason instead of failing silently.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde::Deserialize;
use serde_json::{Value, json};
use std::process::Command;
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};

const ALGORA_LABELS: &[&str] = &["bounty", "algora", "algora-bounty"];
const OPIRE_LABELS: &[&str] = &["opire", "opire-bounty", "bounty"];

#[derive(Debug, Deserialize)]
struct GhLabel {
    name: String,
}

#[derive(Debug, Deserialize)]
struct GhIssue {
    number: u64,
    title: String,
    url: String,
    #[serde(default)]
    labels: Vec<GhLabel>,
    #[serde(default)]
    body: String,
}

#[derive(Debug, Deserialize)]
struct GhRepo {
    #[serde(rename = "nameWithOwner")]
    name_with_owner: String,
}

fn gh_command(args: &[&str]) -> Option<String> {
    // Prefer `timeout 30 gh ...` so a hung CLI cannot stall dispatch.
    let output = Command::new("timeout")
        .arg("30")
        .arg("gh")
        .args(args)
        .output()
        .or_else(|_| Command::new("gh").args(args).output())
        .ok()?;
    if !output.status.success() {
        return None;
    }
    String::from_utf8(output.stdout).ok()
}

fn gh_available() -> bool {
    gh_command(&["--version"]).is_some()
}

fn detect_platform(labels: &[String]) -> Option<&'static str> {
    for label in labels {
        if OPIRE_LABELS.contains(&label.as_str()) {
            return Some("opire");
        }
        if ALGORA_LABELS.contains(&label.as_str()) {
            return Some("algora");
        }
    }
    None
}

fn extract_amount(body: &str) -> Option<String> {
    let bytes = body.as_bytes();
    for (i, b) in bytes.iter().enumerate() {
        if *b == b'$' {
            let mut j = i + 1;
            let mut num = String::new();
            while j < bytes.len() && (bytes[j].is_ascii_digit() || bytes[j] == b',') {
                num.push(bytes[j] as char);
                j += 1;
            }
            let cleaned = num.replace(',', "");
            if !cleaned.is_empty() {
                return Some(format!("${cleaned}"));
            }
        }
    }
    // "500 USD" / "Bounty: 500"
    let tokens: Vec<&str> = body.split_whitespace().collect();
    for (i, token) in tokens.iter().enumerate() {
        let cleaned: String = token.chars().filter(char::is_ascii_digit).collect();
        if cleaned.is_empty() {
            continue;
        }
        let next_usd = tokens
            .get(i + 1)
            .is_some_and(|t| t.eq_ignore_ascii_case("usd") || t.eq_ignore_ascii_case("usdc"));
        let prev_bounty = i > 0
            && tokens[i - 1]
                .trim_end_matches(':')
                .eq_ignore_ascii_case("bounty");
        if next_usd || prev_bounty {
            return Some(format!("${cleaned}"));
        }
    }
    None
}

fn scan_repo(repo: &str) -> Result<Vec<Value>, String> {
    let output = gh_command(&[
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--label",
        "bounty",
        "--limit",
        "50",
        "--json",
        "number,title,url,labels,body",
    ])
    .ok_or_else(|| format!("gh issue list failed for {repo}"))?;
    let issues: Vec<GhIssue> =
        serde_json::from_str(&output).map_err(|e| format!("gh JSON parse: {e}"))?;
    Ok(issues
        .into_iter()
        .map(|issue| {
            let labels: Vec<String> = issue
                .labels
                .into_iter()
                .map(|l| l.name.to_lowercase())
                .collect();
            let platform = detect_platform(&labels);
            let amount = extract_amount(&issue.body);
            json!({
                "repo": repo,
                "issue_number": issue.number,
                "title": issue.title,
                "url": issue.url,
                "labels": labels,
                "bounty_platform": platform,
                "bounty_amount": amount,
                "body_snippet": issue.body.chars().take(200).collect::<String>(),
            })
        })
        .collect())
}

// ── Tools ──────────────────────────────────────────────────────────────

/// `oss.bounty.scan` — scan a repo or org for bounty issues.
pub struct OssBountyScanTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl Default for OssBountyScanTool {
    fn default() -> Self {
        Self::new()
    }
}

impl OssBountyScanTool {
    /// Create the scanner tool.
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Network],
                spawns: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for OssBountyScanTool {
    fn name(&self) -> &str {
        "oss.bounty.scan"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Scan GitHub for bounty-labeled issues via the gh CLI. Args: repo (owner/name) or org (name). Read-only; requires the gh CLI to be installed and authenticated."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        if !gh_available() {
            return Ok(json!({
                "status": "error",
                "message": "gh CLI not available; install/authenticate gh to scan OSS bounties",
            }));
        }
        if let Some(repo) = args.get("repo").and_then(Value::as_str) {
            let issues = scan_repo(repo)
                .map_err(|e| CoreError::Internal(format!("oss scan failed: {e}")))?;
            return Ok(
                json!({"status": "success", "repo": repo, "count": issues.len(), "issues": issues}),
            );
        }
        if let Some(org) = args.get("org").and_then(Value::as_str) {
            let repos_json = gh_command(&[
                "repo",
                "list",
                org,
                "--limit",
                "100",
                "--json",
                "nameWithOwner",
            ])
            .ok_or_else(|| CoreError::Internal(format!("gh repo list failed for {org}")))?;
            let repos: Vec<GhRepo> = serde_json::from_str(&repos_json)
                .map_err(|e| CoreError::Internal(format!("gh JSON parse: {e}")))?;
            let mut all = Vec::new();
            for repo in repos {
                if let Ok(mut issues) = scan_repo(&repo.name_with_owner) {
                    all.append(&mut issues);
                }
            }
            return Ok(json!({"status": "success", "org": org, "count": all.len(), "issues": all}));
        }
        Err(CoreError::InvalidArgs(
            "provide repo (owner/name) or org (name)".into(),
        ))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `oss.bounty.status` — gh availability + label taxonomy.
pub struct OssBountyStatusTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl Default for OssBountyStatusTool {
    fn default() -> Self {
        Self::new()
    }
}

impl OssBountyStatusTool {
    /// Create the status tool.
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow {
                spawns: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for OssBountyStatusTool {
    fn name(&self) -> &str {
        "oss.bounty.status"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "OSS bounty scanner status: gh CLI availability + Algora/Opire label taxonomy."
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "gh_available": gh_available(),
            "algora_labels": ALGORA_LABELS,
            "opire_labels": OPIRE_LABELS,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the OSS bounty surface (2 tools).
#[must_use]
pub fn register_oss_bounty(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    registry
        .register(std::sync::Arc::new(OssBountyScanTool::new()))
        .register(std::sync::Arc::new(OssBountyStatusTool::new()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn platform_detection_order() {
        assert_eq!(detect_platform(&["opire".into()]), Some("opire"));
        assert_eq!(detect_platform(&["algora".into()]), Some("algora"));
        assert_eq!(detect_platform(&["bounty".into()]), Some("opire"));
        assert_eq!(detect_platform(&["chore".into()]), None);
    }

    #[test]
    fn amount_extraction_variants() {
        assert_eq!(
            extract_amount("Fix this. $500 reward").as_deref(),
            Some("$500")
        );
        assert_eq!(
            extract_amount("Reward: 1,200 USD").as_deref(),
            Some("$1200")
        );
        assert_eq!(
            extract_amount("Bounty: 250 for the fix").as_deref(),
            Some("$250")
        );
        assert_eq!(extract_amount("no money here"), None);
    }

    #[test]
    fn gh_issue_json_parses() {
        let sample = r#"[
            {"number": 7, "title": "Fix parser", "url": "https://github.com/a/b/issues/7",
             "labels": [{"name": "Bounty"}], "body": "Bounty: $300"}
        ]"#;
        let issues: Vec<GhIssue> = serde_json::from_str(sample).unwrap();
        assert_eq!(issues.len(), 1);
        assert_eq!(issues[0].labels[0].name.to_lowercase(), "bounty");
        assert_eq!(extract_amount(&issues[0].body).as_deref(), Some("$300"));
    }
}
