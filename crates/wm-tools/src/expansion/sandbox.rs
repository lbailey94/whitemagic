//! Sandbox tools — `sandbox.set_limits`, `sandbox.limits`.
//!
//! Runtime tuning of the resource-limit layer (per-minute write / spawn /
//! network budgets, novelty thresholds, human-review requirement). Ports
//! the v26 `sandbox.set_limits` surface onto the v5 `ResourceRules`
//! config, which the dispatch pipeline reads on every evaluation.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_governance::ResourceRules;

fn u32_limit(args: &Value, key: &str) -> wm_core::Result<Option<u32>> {
    let Some(raw) = args.get(key) else {
        return Ok(None);
    };
    let value = raw.as_u64().ok_or_else(|| {
        CoreError::Tool(format!(
            "sandbox.set_limits rejected '{key}': expected a non-negative integer, got {raw}"
        ))
    })?;
    u32::try_from(value).map(Some).map_err(|_| {
        CoreError::Tool(format!(
            "sandbox.set_limits rejected '{key}': {value} exceeds the supported maximum {}",
            u32::MAX
        ))
    })
}

fn usize_limit(args: &Value, key: &str) -> wm_core::Result<Option<usize>> {
    let Some(raw) = args.get(key) else {
        return Ok(None);
    };
    let value = raw.as_u64().ok_or_else(|| {
        CoreError::Tool(format!(
            "sandbox.set_limits rejected '{key}': expected a non-negative integer, got {raw}"
        ))
    })?;
    usize::try_from(value).map(Some).map_err(|_| {
        CoreError::Tool(format!(
            "sandbox.set_limits rejected '{key}': {value} exceeds the supported maximum {}",
            usize::MAX
        ))
    })
}

fn bool_limit(args: &Value, key: &str) -> wm_core::Result<Option<bool>> {
    let Some(raw) = args.get(key) else {
        return Ok(None);
    };
    raw.as_bool().map(Some).ok_or_else(|| {
        CoreError::Tool(format!(
            "sandbox.set_limits rejected '{key}': expected a boolean, got {raw}"
        ))
    })
}

/// `sandbox.set_limits` — update resource limits at runtime.
pub struct SandboxSetLimitsTool {
    rules: Arc<ResourceRules>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SandboxSetLimitsTool {
    #[must_use]
    pub fn new(rules: Arc<ResourceRules>) -> Self {
        Self {
            rules,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SandboxSetLimitsTool {
    fn name(&self) -> &str {
        "sandbox.set_limits"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Update sandbox resource limits at runtime: max_writes_per_minute, max_spawns_per_minute, max_network_per_minute, novelty_window, max_repeats, require_human_review. All fields optional — provided ones are applied, others keep current values."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let writes = u32_limit(&args, "max_writes_per_minute")?;
        let spawns = u32_limit(&args, "max_spawns_per_minute")?;
        let network = u32_limit(&args, "max_network_per_minute")?;
        let novelty = usize_limit(&args, "novelty_window")?;
        let repeats = u32_limit(&args, "max_repeats")?;
        let review = bool_limit(&args, "require_human_review")?;

        let mut cfg = self.rules.config();
        let mut changed: Vec<&'static str> = Vec::new();
        if let Some(v) = writes {
            cfg.max_writes_per_minute = v;
            changed.push("max_writes_per_minute");
        }
        if let Some(v) = spawns {
            cfg.max_spawns_per_minute = v;
            changed.push("max_spawns_per_minute");
        }
        if let Some(v) = network {
            cfg.max_network_per_minute = v;
            changed.push("max_network_per_minute");
        }
        if let Some(v) = novelty {
            cfg.novelty_window = v;
            changed.push("novelty_window");
        }
        if let Some(v) = repeats {
            cfg.max_repeats = v;
            changed.push("max_repeats");
        }
        if let Some(v) = review {
            cfg.require_human_review = v;
            changed.push("require_human_review");
        }
        self.rules.set_config(cfg);
        let cfg = self.rules.config();
        Ok(json!({
            "status": "success",
            "changed": changed,
            "limits": {
                "max_writes_per_minute": cfg.max_writes_per_minute,
                "max_spawns_per_minute": cfg.max_spawns_per_minute,
                "max_network_per_minute": cfg.max_network_per_minute,
                "novelty_window": cfg.novelty_window,
                "max_repeats": cfg.max_repeats,
                "require_human_review": cfg.require_human_review,
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `sandbox.limits` — show the current sandbox limits.
pub struct SandboxLimitsTool {
    rules: Arc<ResourceRules>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SandboxLimitsTool {
    #[must_use]
    pub fn new(rules: Arc<ResourceRules>) -> Self {
        Self {
            rules,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::DharmaRules]),
        }
    }
}

#[async_trait]
impl Tool for SandboxLimitsTool {
    fn name(&self) -> &str {
        "sandbox.limits"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Show the current sandbox resource limits"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let cfg = self.rules.config();
        Ok(json!({
            "status": "success",
            "limits": {
                "max_writes_per_minute": cfg.max_writes_per_minute,
                "max_spawns_per_minute": cfg.max_spawns_per_minute,
                "max_network_per_minute": cfg.max_network_per_minute,
                "novelty_window": cfg.novelty_window,
                "max_repeats": cfg.max_repeats,
                "require_human_review": cfg.require_human_review,
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the sandbox tools (2).
#[must_use]
pub fn register_sandbox(
    registry: &wm_dispatch::ToolRegistry,
    rules: Option<&Arc<ResourceRules>>,
) -> wm_dispatch::ToolRegistry {
    match rules {
        Some(rules) => registry
            .register(Arc::new(SandboxSetLimitsTool::new(rules.clone())))
            .register(Arc::new(SandboxLimitsTool::new(rules.clone()))),
        None => registry.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::{BrainWave, Context};
    use wm_governance::{Homeostasis, ResourceVerdict};

    fn rules() -> Arc<ResourceRules> {
        Arc::new(ResourceRules::default())
    }

    fn evaluate(
        rules: &ResourceRules,
        tool: &str,
        hash: u64,
        write: bool,
        spawn: bool,
        network: bool,
    ) -> ResourceVerdict {
        rules.evaluate(
            tool,
            hash,
            write,
            spawn,
            network,
            true,
            &Homeostasis::default(),
            BrainWave::Gamma,
        )
    }

    #[tokio::test]
    async fn limits_roundtrip_reports_changed_and_current_values() {
        let rules = rules();
        let setter = SandboxSetLimitsTool::new(rules.clone());
        let out = setter
            .call(
                &mut Context::default(),
                json!({"max_writes_per_minute": 42, "require_human_review": true}),
            )
            .await
            .unwrap();
        assert_eq!(out["status"], "success");
        assert_eq!(
            out["changed"],
            json!(["max_writes_per_minute", "require_human_review"])
        );
        assert_eq!(out["limits"]["max_writes_per_minute"], 42);
        assert_eq!(out["limits"]["require_human_review"], true);
        let reader = SandboxLimitsTool::new(rules.clone());
        let show = reader
            .call(&mut Context::default(), json!({}))
            .await
            .unwrap();
        assert_eq!(show["limits"], out["limits"]);
    }

    #[tokio::test]
    async fn invalid_fields_reject_the_whole_call_atomically() {
        let rules = rules();
        let before = rules.config();
        let setter = SandboxSetLimitsTool::new(rules.clone());
        let error = setter
            .call(
                &mut Context::default(),
                json!({"max_writes_per_minute": 7, "require_human_review": "yes"}),
            )
            .await
            .unwrap_err()
            .to_string();
        assert!(error.contains("require_human_review"), "{error}");
        assert_eq!(
            rules.config().max_writes_per_minute,
            before.max_writes_per_minute
        );
        assert_eq!(
            rules.config().require_human_review,
            before.require_human_review
        );
    }

    #[tokio::test]
    async fn oversized_values_are_rejected_not_truncated() {
        let rules = rules();
        let before = rules.config();
        let setter = SandboxSetLimitsTool::new(rules.clone());
        let error = setter
            .call(
                &mut Context::default(),
                json!({"max_writes_per_minute": u64::from(u32::MAX) + 1}),
            )
            .await
            .unwrap_err()
            .to_string();
        assert!(error.contains("max_writes_per_minute"), "{error}");
        assert_eq!(
            rules.config().max_writes_per_minute,
            before.max_writes_per_minute
        );
    }

    #[tokio::test]
    async fn unspecified_fields_keep_their_values() {
        let rules = rules();
        let setter = SandboxSetLimitsTool::new(rules.clone());
        setter
            .call(&mut Context::default(), json!({"max_spawns_per_minute": 3}))
            .await
            .unwrap();
        let cfg = rules.config();
        let default = ResourceRules::default().config();
        assert_eq!(cfg.max_spawns_per_minute, 3);
        assert_eq!(cfg.max_writes_per_minute, default.max_writes_per_minute);
        assert_eq!(cfg.novelty_window, default.novelty_window);
        assert_eq!(cfg.require_human_review, default.require_human_review);
    }

    #[tokio::test]
    async fn configured_write_budget_is_enforced_by_evaluation() {
        let rules = rules();
        SandboxSetLimitsTool::new(rules.clone())
            .call(&mut Context::default(), json!({"max_writes_per_minute": 1}))
            .await
            .unwrap();
        assert_eq!(
            evaluate(&rules, "probe-a", 1, true, false, false),
            ResourceVerdict::Allow
        );
        assert!(evaluate(&rules, "probe-b", 2, true, false, false).blocks());
    }

    #[tokio::test]
    async fn configured_spawn_and_network_budgets_are_enforced() {
        let rules = rules();
        SandboxSetLimitsTool::new(rules.clone())
            .call(
                &mut Context::default(),
                json!({"max_spawns_per_minute": 1, "max_network_per_minute": 1}),
            )
            .await
            .unwrap();
        assert_eq!(
            evaluate(&rules, "spawn-a", 11, false, true, false),
            ResourceVerdict::Allow
        );
        assert!(evaluate(&rules, "spawn-b", 12, false, true, false).blocks());
        assert_eq!(
            evaluate(&rules, "net-a", 13, false, false, true),
            ResourceVerdict::Allow
        );
        assert!(evaluate(&rules, "net-b", 14, false, false, true).blocks());
    }

    #[tokio::test]
    async fn zero_write_budget_is_honored_as_a_lockout() {
        let rules = rules();
        SandboxSetLimitsTool::new(rules.clone())
            .call(&mut Context::default(), json!({"max_writes_per_minute": 0}))
            .await
            .unwrap();
        let verdict = evaluate(&rules, "probe-a", 1, true, false, false);
        assert!(verdict.blocks(), "{verdict:?}");
    }
}
