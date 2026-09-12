//! Circuit-breaker operator tools — status (read-only) and reset (confirm-gated).
//!
//! The registry lives inside the dispatch pipeline; these tools share it so an
//! operator can see open/half-open tools and clear a wedged breaker without
//! restarting the server. Reset is deliberately **not** flagged destructive:
//! it is the recovery path, and AHIMSA strict mode (system stress) blocks
//! destructive actions — the reset must stay available exactly when the
//! system is stressed. An explicit `confirm: true` is required instead, and
//! the tool declares no writes (it mutates only in-memory breaker state).

#![forbid(unsafe_code)]

use async_trait::async_trait;
use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_dispatch::CircuitBreakerRegistry;

use super::common::{bool_prop, schema, str_prop};

/// `breaker.status` — read-only snapshot of the dispatch circuit breakers.
pub struct BreakerStatusTool {
    breakers: Arc<CircuitBreakerRegistry>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BreakerStatusTool {
    #[must_use]
    pub fn new(breakers: Arc<CircuitBreakerRegistry>) -> Self {
        Self {
            breakers,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for BreakerStatusTool {
    fn name(&self) -> &str {
        "breaker.status"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    fn description(&self) -> &str {
        "Read-only circuit-breaker snapshot: open and half-open tool routes and non-zero trip counts. Env-tunable via WM_BREAKER_THRESHOLD / WM_BREAKER_WINDOW_MS / WM_BREAKER_COOLDOWN_MS."
    }
    fn input_schema(&self) -> Value {
        schema(&json!({}), &[])
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "breaker": self.breakers.snapshot(),
        }))
    }
}

/// `breaker.reset` — operator recovery: close one breaker or all of them.
pub struct BreakerResetTool {
    breakers: Arc<CircuitBreakerRegistry>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BreakerResetTool {
    #[must_use]
    pub fn new(breakers: Arc<CircuitBreakerRegistry>) -> Self {
        Self {
            breakers,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
impl Tool for BreakerResetTool {
    fn name(&self) -> &str {
        "breaker.reset"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    fn description(&self) -> &str {
        "Close circuit breakers after a recovery (requires confirm: true). Pass tool: \"<route>\" for one breaker or all: true for every tracked breaker. Not destructive: recovery must remain available under stress; it writes no data."
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "tool": str_prop("Tool route whose breaker to reset (e.g. code.community)"),
                "all": bool_prop("Reset every tracked breaker"),
                "confirm": bool_prop("Must be true — explicit operator recovery"),
            }),
            &["confirm"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let confirm = args
            .get("confirm")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        if !confirm {
            return Ok(json!({
                "status": "error",
                "error": "breaker.reset requires confirm: true (explicit operator recovery)",
            }));
        }

        if args.get("all").and_then(Value::as_bool).unwrap_or(false) {
            let before = self.breakers.snapshot();
            let mut cleared: Vec<String> = Vec::new();
            for key in ["open", "half_open"] {
                if let Some(names) = before[key].as_array() {
                    cleared.extend(names.iter().filter_map(Value::as_str).map(str::to_string));
                }
            }
            let count = self.breakers.reset_all();
            return Ok(json!({
                "status": "success",
                "reset": count,
                "cleared": cleared,
            }));
        }

        if let Some(name) = args.get("tool").and_then(Value::as_str) {
            let previous = self.breakers.state(name);
            self.breakers.reset(name);
            return Ok(json!({
                "status": "success",
                "tool": name,
                "previous_state": format!("{previous:?}"),
            }));
        }

        Ok(json!({
            "status": "error",
            "error": "provide tool: \"<route>\" or all: true",
        }))
    }
}

/// Register both breaker operator tools.
#[must_use]
pub fn register_breakers(
    registry: &wm_dispatch::ToolRegistry,
    breakers: Arc<CircuitBreakerRegistry>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(BreakerStatusTool::new(breakers.clone())))
        .register(Arc::new(BreakerResetTool::new(breakers)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use wm_dispatch::{BreakerConfig, BreakerState};

    fn test_registry() -> Arc<CircuitBreakerRegistry> {
        Arc::new(CircuitBreakerRegistry::new(BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        }))
    }

    #[tokio::test]
    async fn status_reports_open_breakers() {
        let registry = test_registry();
        registry.record_failure("flaky.tool");
        let tool = BreakerStatusTool::new(registry);
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let out = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(out["status"], "success");
        assert_eq!(out["breaker"]["open"], json!(["flaky.tool"]));
        assert_eq!(out["breaker"]["trips"]["flaky.tool"], 1);
    }

    #[tokio::test]
    async fn reset_requires_confirm_and_then_clears() {
        let registry = test_registry();
        registry.record_failure("flaky.tool");
        let tool = BreakerResetTool::new(registry.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        let denied = tool
            .call(&mut ctx, json!({"tool": "flaky.tool"}))
            .await
            .unwrap();
        assert_eq!(denied["status"], "error");
        assert_eq!(registry.state("flaky.tool"), BreakerState::Open);

        let done = tool
            .call(&mut ctx, json!({"tool": "flaky.tool", "confirm": true}))
            .await
            .unwrap();
        assert_eq!(done["status"], "success");
        assert_eq!(done["previous_state"], "Open");
        assert_eq!(registry.state("flaky.tool"), BreakerState::Closed);
    }

    #[tokio::test]
    async fn reset_all_clears_every_breaker() {
        let registry = test_registry();
        registry.record_failure("tool.a");
        registry.record_failure("tool.b");
        let tool = BreakerResetTool::new(registry.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        let out = tool
            .call(&mut ctx, json!({"all": true, "confirm": true}))
            .await
            .unwrap();
        assert_eq!(out["status"], "success");
        assert_eq!(out["reset"], 2);
        assert_eq!(registry.state("tool.a"), BreakerState::Closed);
        assert_eq!(registry.state("tool.b"), BreakerState::Closed);
    }

    #[tokio::test]
    async fn reset_without_target_is_an_error() {
        let registry = test_registry();
        let tool = BreakerResetTool::new(registry);
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let out = tool.call(&mut ctx, json!({"confirm": true})).await.unwrap();
        assert_eq!(out["status"], "error");
    }
}
