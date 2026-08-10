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
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_governance::ResourceRules;

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
        let mut cfg = self.rules.config();
        let mut changed: Vec<&'static str> = Vec::new();
        if let Some(v) = args.get("max_writes_per_minute").and_then(Value::as_u64) {
            cfg.max_writes_per_minute = v as u32;
            changed.push("max_writes_per_minute");
        }
        if let Some(v) = args.get("max_spawns_per_minute").and_then(Value::as_u64) {
            cfg.max_spawns_per_minute = v as u32;
            changed.push("max_spawns_per_minute");
        }
        if let Some(v) = args.get("max_network_per_minute").and_then(Value::as_u64) {
            cfg.max_network_per_minute = v as u32;
            changed.push("max_network_per_minute");
        }
        if let Some(v) = args.get("novelty_window").and_then(Value::as_u64) {
            cfg.novelty_window = v as usize;
            changed.push("novelty_window");
        }
        if let Some(v) = args.get("max_repeats").and_then(Value::as_u64) {
            cfg.max_repeats = v as u32;
            changed.push("max_repeats");
        }
        if let Some(v) = args.get("require_human_review").and_then(Value::as_bool) {
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
