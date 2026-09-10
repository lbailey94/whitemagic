//! Bounty evidence packager — `bounty.evidence.*`.
//!
//! Turns a candidate finding into a structured, reproducible evidence pack
//! (markdown) and runs a preflight against the rejection taxonomy, so weak
//! reports never reach a program (the acceptance bottleneck).
//!
//! Tools: `bounty.evidence.package`, `bounty.evidence.taxonomy`.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fmt::Write as _;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

fn slugify(input: &str) -> String {
    let mut out = String::new();
    let mut last_dash = false;
    for ch in input.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
            last_dash = false;
        } else if !last_dash && !out.is_empty() {
            out.push('-');
            last_dash = true;
        }
    }
    let trimmed = out.trim_matches('-').to_string();
    if trimmed.is_empty() {
        "finding".to_string()
    } else {
        trimmed.chars().take(64).collect()
    }
}

fn sha256_hex(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    hasher.finalize().iter().fold(String::new(), |mut acc, b| {
        use std::fmt::Write;
        let _ = write!(acc, "{b:02x}");
        acc
    })
}

fn mitigation_for(reason: &str) -> &'static str {
    match reason {
        "not_reproducible" => "Attach exact minimal repro steps + a runnable PoC.",
        "out_of_scope" => "Cite the scope section that covers the asset; leave an audit trail.",
        "duplicate" => "Search program disclosures + your ledger before writing.",
        "expected_behavior" => "Show why the behavior is unintended (policy/docs/security intent).",
        "insufficient_impact" => "Tie the finding to concrete user/asset/network harm.",
        "already_known" => "Check advisories, changelogs, and known-issue lists first.",
        "report_quality" => "Use the evidence pack structure; state uncertainty explicitly.",
        "third_party" => "Confirm asset ownership and program coverage before testing.",
        _ => "Ask the triager for the reason and record it in the bounty ledger.",
    }
}

fn to_array_strings(value: Option<&Value>) -> Vec<String> {
    value
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

fn preflight(args: &Value) -> Value {
    let steps = to_array_strings(args.get("steps"));
    let evidence = to_array_strings(args.get("evidence"));
    let summary = args.get("summary").and_then(Value::as_str).unwrap_or("");
    let impact = args.get("impact").and_then(Value::as_str).unwrap_or("");
    let poc = args.get("poc").and_then(Value::as_str).unwrap_or_default();
    let uncertainty = args
        .get("uncertainty")
        .and_then(Value::as_str)
        .unwrap_or("");
    let scope_ref = args.get("scope_ref").and_then(Value::as_str).unwrap_or("");

    let checks = json!({
        "reproducible_steps": !steps.is_empty() && !poc.trim().is_empty(),
        "minimal_repro": !steps.is_empty() && steps.len() <= 10,
        "impact_stated": !impact.trim().is_empty(),
        "summary_stated": !summary.trim().is_empty(),
        "evidence_attached": !evidence.is_empty(),
        "scope_referenced": !scope_ref.trim().is_empty(),
        "uncertainty_disclosed": !uncertainty.trim().is_empty(),
    });
    let passed = checks.as_object().map_or(0, |o| {
        o.values().filter(|v| v.as_bool() == Some(true)).count()
    });
    let total = checks.as_object().map_or(0, serde_json::Map::len);
    let readiness = if total > 0 {
        passed as f64 / total as f64
    } else {
        0.0
    };
    json!({
        "checks": checks,
        "passed": passed,
        "total": total,
        "readiness": readiness,
        "ready_to_submit": passed == total,
    })
}

fn render_markdown(args: &Value, pre: &Value) -> String {
    let s = |k: &str| {
        args.get(k)
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string()
    };
    let steps = to_array_strings(args.get("steps"));
    let evidence = to_array_strings(args.get("evidence"));

    let mut md = String::new();
    let _ = write!(md, "# {}\n\n", s("title"));
    let _ = writeln!(md, "- **Platform:** {}", s("platform"));
    let _ = writeln!(md, "- **Target:** {}", s("target"));
    let _ = writeln!(md, "- **Severity:** {}", s("severity"));
    let _ = writeln!(md, "- **Scope reference:** {}", s("scope_ref"));
    let _ = write!(md, "- **Packaged (unix):** {}\n\n", now_unix());
    let _ = write!(md, "## Summary\n\n{}\n\n", s("summary"));
    let _ = write!(md, "## Impact\n\n{}\n\n", s("impact"));
    md.push_str("## Reproduction steps\n\n");
    if steps.is_empty() {
        md.push_str("_none provided_\n\n");
    } else {
        for (i, step) in steps.iter().enumerate() {
            let _ = writeln!(md, "{}. {step}", i + 1);
        }
        md.push('\n');
    }
    md.push_str("## Proof of concept\n\n```\n");
    md.push_str(&s("poc"));
    md.push_str("\n```\n\n");
    md.push_str("## Evidence\n\n");
    if evidence.is_empty() {
        md.push_str("_none attached_\n\n");
    } else {
        for item in &evidence {
            let _ = writeln!(md, "- {item}");
        }
        md.push('\n');
    }
    let _ = write!(md, "## Uncertainty / limits\n\n{}\n\n", s("uncertainty"));
    md.push_str("## Preflight\n\n");
    if let Some(checks) = pre["checks"].as_object() {
        for (name, ok) in checks {
            let _ = writeln!(
                md,
                "- [{}] {name}",
                if ok.as_bool() == Some(true) { "x" } else { " " }
            );
        }
    }
    let _ = write!(
        md,
        "\n_Readiness: {} / {} checks passed._\n",
        pre["passed"], pre["total"]
    );
    md
}

// ── bounty.evidence.taxonomy ───────────────────────────────────────────

/// `bounty.evidence.taxonomy` — rejection reasons + mitigations.
pub struct EvidenceTaxonomyTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl Default for EvidenceTaxonomyTool {
    fn default() -> Self {
        Self::new()
    }
}

impl EvidenceTaxonomyTool {
    /// Create the taxonomy tool.
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for EvidenceTaxonomyTool {
    fn name(&self) -> &str {
        "bounty.evidence.taxonomy"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Rejection-reason taxonomy with mitigation guidance (compounding loop input)."
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let reasons: Vec<Value> = crate::expansion::bounty_ledger::REJECTION_REASONS
            .iter()
            .map(|r| json!({"reason": r, "mitigation": mitigation_for(r)}))
            .collect();
        Ok(json!({"status": "success", "reasons": reasons}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── bounty.evidence.package ────────────────────────────────────────────

/// `bounty.evidence.package` — write a structured evidence pack.
pub struct EvidencePackageTool {
    dir: PathBuf,
    stats: ToolStats,
    effects: EffectRow,
}

impl EvidencePackageTool {
    /// Create the packager rooted at `dir`.
    #[must_use]
    pub fn new(dir: PathBuf) -> Self {
        Self {
            dir,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Filesystem],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for EvidencePackageTool {
    fn name(&self) -> &str {
        "bounty.evidence.package"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Write a structured evidence pack (markdown) for a finding. Args: title, platform, target, severity, summary, impact, steps (array), poc (string), evidence (array), uncertainty, scope_ref. Returns path, sha256, and preflight readiness."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        for required in ["title", "platform", "target", "summary", "impact"] {
            if args
                .get(required)
                .and_then(Value::as_str)
                .is_none_or(|v| v.trim().is_empty())
            {
                return Err(CoreError::InvalidArgs(format!(
                    "{required} is required (non-empty string)"
                )));
            }
        }
        let pre = preflight(&args);
        let markdown = render_markdown(&args, &pre);
        let digest = sha256_hex(&markdown);

        let title = args
            .get("title")
            .and_then(Value::as_str)
            .unwrap_or("finding");
        let filename = format!("{}-{}.md", slugify(title), now_unix());
        let path = self.dir.join(&filename);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| {
                CoreError::Internal(format!("evidence dir {}: {e}", parent.display()))
            })?;
        }
        std::fs::write(&path, &markdown)
            .map_err(|e| CoreError::Internal(format!("evidence write {}: {e}", path.display())))?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
        }

        Ok(json!({
            "status": "success",
            "path": path.display().to_string(),
            "sha256": digest,
            "bytes": markdown.len(),
            "preflight": pre,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the evidence surface (2 tools) rooted at `evidence_dir`.
#[must_use]
pub fn register_bounty_evidence(
    registry: &wm_dispatch::ToolRegistry,
    evidence_dir: PathBuf,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(std::sync::Arc::new(EvidenceTaxonomyTool::new()))
        .register(std::sync::Arc::new(EvidencePackageTool::new(evidence_dir)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugify_sanitizes() {
        assert_eq!(slugify("MCP Tool Shadowing!"), "mcp-tool-shadowing");
        assert_eq!(slugify("   "), "finding");
        assert_eq!(slugify("a".repeat(100).as_str()).len(), 64);
    }

    #[test]
    fn preflight_scores_completeness() {
        let complete = json!({
            "summary": "s", "impact": "i", "poc": "p",
            "steps": ["1", "2"], "evidence": ["log"], "uncertainty": "u",
            "scope_ref": "scope §2"
        });
        let pre = preflight(&complete);
        assert_eq!(pre["ready_to_submit"], true);
        assert_eq!(pre["passed"], pre["total"]);

        let thin = json!({"summary": "s"});
        let pre = preflight(&thin);
        assert_eq!(pre["ready_to_submit"], false);
    }

    #[test]
    fn markdown_contains_structure_and_digest() {
        let args = json!({
            "title": "Test Finding", "platform": "0din", "target": "t",
            "severity": "medium", "summary": "s", "impact": "i",
            "steps": ["do x"], "poc": "print(1)", "evidence": ["trace"],
            "uncertainty": "unknown", "scope_ref": "§1"
        });
        let pre = preflight(&args);
        let md = render_markdown(&args, &pre);
        for needle in [
            "# Test Finding",
            "## Reproduction steps",
            "## Proof of concept",
            "## Preflight",
            "Readiness:",
        ] {
            assert!(md.contains(needle), "missing {needle}");
        }
        assert_eq!(sha256_hex(&md).len(), 64);
    }
}
