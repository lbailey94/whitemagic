//! Imagination engine tools — scenario generation, prediction, and reflection.
//!
//! Gana::ThreeStars — "Imagination, scenario planning, counterfactual reflection"
//!
//! Tools:
//! - `imagine.scenario` — Generate scenarios for a given state + goal
//! - `imagine.predict` — Predict outcome of a specific action
//! - `imagine.reflect` — Counterfactual reflection on past decisions

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_bicameral::{
    ScenarioEngine, ScenarioEvaluator, WorldModel,
    simulation_bridge::{SimulationBridge, SimulationBridgeConfig},
    world_model_from_env,
};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_memory::MemoryStore;

// ── WorldModel factory ────────────────────────────────────────────────

/// Build a WorldModel from env-configured LLM handlers, falling back to stubs.
fn build_world_model() -> WorldModel {
    world_model_from_env()
}

// ── imagine.scenario ──────────────────────────────────────────────────

/// Imagination scenario tool — generates scenarios for a given state + goal.
///
/// Uses the bicameral world model to imagine multiple possible actions,
/// predict their outcomes, and evaluate them. Optionally enriches with
/// simulation data (MC rollout, forecasting, sensitivity analysis).
pub struct ImagineScenarioTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ImagineScenarioTool {
    /// Create a new imagination scenario tool.
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("universal".into())]),
        }
    }

    fn gather_context(&self, query: &str, limit: usize) -> String {
        let topic_lower = query.to_lowercase();
        let topic_words: Vec<&str> = topic_lower.split_whitespace().collect();

        let mut context_parts: Vec<String> = Vec::new();
        for galaxy in wm_core::Galaxy::memory_galaxies() {
            if let Ok(mems) = self.store.scan(galaxy, limit) {
                for mem in mems {
                    // model_exclude memories never enter scenario context.
                    if mem.metadata.model_exclude {
                        continue;
                    }
                    let content_lower = mem.content.to_lowercase();
                    if topic_words.iter().any(|w| content_lower.contains(w)) {
                        context_parts.push(format!("- {}", mem.content));
                        if context_parts.len() >= 20 {
                            break;
                        }
                    }
                }
            }
            if context_parts.len() >= 20 {
                break;
            }
        }
        context_parts.join("\n")
    }
}

#[async_trait]
#[async_trait]
impl Tool for ImagineScenarioTool {
    fn name(&self) -> &str {
        "imagine.scenario"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Generate and evaluate scenarios for a given state and goal using the bicameral imagination engine"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let state = args
            .get("state")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("state (string) required".into()))?;

        let goal = args
            .get("goal")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("goal (string) required".into()))?;

        let scan_limit = args
            .get("scan_limit")
            .and_then(Value::as_u64)
            .unwrap_or(200) as usize;

        let enrich_sim = args
            .get("enrich_simulation")
            .and_then(Value::as_bool)
            .unwrap_or(false);

        let mc_samples = args.get("mc_samples").and_then(Value::as_u64).unwrap_or(10) as usize;

        // Gather memory context
        let memory_context = self.gather_context(goal, scan_limit);

        // Build scenario engine and generate scenarios
        let world_model = build_world_model();
        let scenario_engine =
            ScenarioEngine::with_defaults(world_model, ScenarioEvaluator::with_defaults());
        let scenarios = scenario_engine.imagine(state, goal, &memory_context);

        if scenarios.is_empty() {
            return Ok(json!({
                "status": "no_scenarios",
                "state": state,
                "goal": goal,
                "scenarios": [],
            }));
        }

        // Optionally enrich with simulation data
        let scenarios_json: Vec<Value> = if enrich_sim {
            let world_model = build_world_model();
            let bridge_config = SimulationBridgeConfig {
                mc_samples,
                sensitivity_samples: 50,
                cf_bootstrap: 50,
                ..Default::default()
            };
            let mut bridge = SimulationBridge::new(bridge_config);
            scenarios
                .iter()
                .map(|s| {
                    let history: Vec<f64> = vec![f64::from(s.score), f64::from(s.score)];
                    let enriched = bridge.enrich_scenario(&world_model, s, &history);
                    enriched.to_json()
                })
                .collect()
        } else {
            scenarios
                .iter()
                .map(|s| {
                    json!({
                        "action": s.action,
                        "score": s.score,
                        "risk": s.risk,
                        "novelty": s.novelty,
                        "rationale": s.rationale,
                        "trajectory_steps": s.trajectory.len(),
                    })
                })
                .collect()
        };

        // Select best scenario
        let best = scenario_engine.select_balanced(&scenarios, 0.05);

        Ok(json!({
            "status": "ok",
            "state": state,
            "goal": goal,
            "scenario_count": scenarios.len(),
            "best_action": best.map(|s| s.action.clone()),
            "best_score": best.map(|s| s.score),
            "scenarios": scenarios_json,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── imagine.predict ───────────────────────────────────────────────────

/// Imagination predict tool — predicts the outcome of a specific action.
///
/// Uses the bicameral world model to predict what would happen if a
/// specific action is taken from a given state.
pub struct ImaginePredictTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl ImaginePredictTool {
    /// Create a new imagination predict tool.
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("universal".into())]),
        }
    }
}

impl Default for ImaginePredictTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for ImaginePredictTool {
    fn name(&self) -> &str {
        "imagine.predict"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Predict the outcome of a specific action from a given state using the bicameral world model"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let state = args
            .get("state")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("state (string) required".into()))?;

        let action = args
            .get("action")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("action (string) required".into()))?;

        let goal = args
            .get("goal")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("goal (string) required".into()))?;

        let world_model = build_world_model();
        let prediction = world_model.predict(state, action, goal);

        let best = prediction.best();

        let mut alternatives: Vec<Value> = Vec::new();
        if prediction.left.description != best.description {
            alternatives.push(json!({
                "description": prediction.left.description,
                "confidence": prediction.left.confidence,
                "source": "left",
            }));
        }
        if let Some(ref right) = prediction.right {
            if right.description != best.description {
                alternatives.push(json!({
                    "description": right.description,
                    "confidence": right.confidence,
                    "source": "right",
                }));
            }
        }

        Ok(json!({
            "status": "ok",
            "state": state,
            "action": action,
            "goal": goal,
            "best_prediction": {
                "description": best.description,
                "confidence": best.confidence,
                "changes": best.changes,
                "risks": best.risks,
                "goal_progress": best.goal_progress,
            },
            "alternatives": alternatives,
            "has_consensus": prediction.has_consensus(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── imagine.reflect ───────────────────────────────────────────────────

/// Imagination reflect tool — counterfactual reflection on past decisions.
///
/// Given a past state, the action taken, and an alternative action,
/// predicts what would have happened with the alternative.
pub struct ImagineReflectTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl ImagineReflectTool {
    /// Create a new imagination reflect tool.
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("universal".into())]),
        }
    }
}

impl Default for ImagineReflectTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for ImagineReflectTool {
    fn name(&self) -> &str {
        "imagine.reflect"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Counterfactual reflection: compare actual action outcome vs alternative action using the bicameral world model"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let past_state = args
            .get("past_state")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("past_state (string) required".into())
            })?;

        let actual_action = args
            .get("actual_action")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("actual_action (string) required".into())
            })?;

        let alternative_action = args
            .get("alternative_action")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("alternative_action (string) required".into())
            })?;

        let goal = args
            .get("goal")
            .and_then(Value::as_str)
            .unwrap_or("improve outcome");

        let world_model = build_world_model();
        let scenario_engine =
            ScenarioEngine::with_defaults(world_model, ScenarioEvaluator::with_defaults());
        let reflection =
            scenario_engine.reflect(past_state, actual_action, alternative_action, goal);

        Ok(json!({
            "status": "ok",
            "past_state": past_state,
            "actual_action": actual_action,
            "alternative_action": alternative_action,
            "actual_outcome": {
                "description": reflection.actual_prediction.description,
                "confidence": reflection.actual_prediction.confidence,
                "goal_progress": reflection.actual_prediction.goal_progress,
            },
            "counterfactual_outcome": {
                "description": reflection.counterfactual_prediction.description,
                "confidence": reflection.counterfactual_prediction.confidence,
                "goal_progress": reflection.counterfactual_prediction.goal_progress,
            },
            "would_have_been_better": reflection.would_have_been_better,
            "lesson": reflection.lesson,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register imagination tools into a registry.
pub fn register_imagination(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(ImagineScenarioTool::new(store.clone())))
        .register(Arc::new(ImaginePredictTool::new()))
        .register(Arc::new(ImagineReflectTool::new()))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        Arc::new(MemoryStore::open(dir.path(), 1024 * 1024).unwrap())
    }

    #[tokio::test]
    async fn imagine_scenario_tool_name() {
        let store = make_store();
        let tool = ImagineScenarioTool::new(store);
        assert_eq!(tool.name(), "imagine.scenario");
        assert_eq!(tool.gana(), Gana::ThreeStars);
    }

    #[tokio::test]
    async fn imagine_predict_tool_name() {
        let tool = ImaginePredictTool::new();
        assert_eq!(tool.name(), "imagine.predict");
        assert_eq!(tool.gana(), Gana::ThreeStars);
    }

    #[tokio::test]
    async fn imagine_reflect_tool_name() {
        let tool = ImagineReflectTool::new();
        assert_eq!(tool.name(), "imagine.reflect");
        assert_eq!(tool.gana(), Gana::ThreeStars);
    }

    #[tokio::test]
    async fn imagine_scenario_generates_scenarios() {
        let store = make_store();
        let tool = ImagineScenarioTool::new(store);
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "state": "system is slow",
                    "goal": "improve performance",
                }),
            )
            .await;
        assert!(result.is_ok());
        let val = result.unwrap();
        assert_eq!(val["status"], "ok");
        assert!(val["scenario_count"].as_u64().is_some());
    }

    #[tokio::test]
    async fn imagine_scenario_missing_state() {
        let store = make_store();
        let tool = ImagineScenarioTool::new(store);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"goal": "test"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn imagine_scenario_missing_goal() {
        let store = make_store();
        let tool = ImagineScenarioTool::new(store);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"state": "test"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn imagine_predict_returns_prediction() {
        let tool = ImaginePredictTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "state": "idle system",
                    "action": "run optimization",
                    "goal": "improve speed",
                }),
            )
            .await;
        assert!(result.is_ok());
        let val = result.unwrap();
        assert_eq!(val["status"], "ok");
        assert!(val["best_prediction"]["description"].as_str().is_some());
    }

    #[tokio::test]
    async fn imagine_predict_missing_action() {
        let tool = ImaginePredictTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"state": "test", "goal": "test"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn imagine_reflect_returns_reflection() {
        let tool = ImagineReflectTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "past_state": "system running",
                    "actual_action": "did nothing",
                    "alternative_action": "optimized cache",
                    "goal": "improve speed",
                }),
            )
            .await;
        assert!(result.is_ok());
        let val = result.unwrap();
        assert_eq!(val["status"], "ok");
        assert!(val["actual_outcome"]["description"].as_str().is_some());
        assert!(
            val["counterfactual_outcome"]["description"]
                .as_str()
                .is_some()
        );
    }

    #[tokio::test]
    async fn imagine_reflect_missing_alternative() {
        let tool = ImagineReflectTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "past_state": "test",
                    "actual_action": "test",
                }),
            )
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn register_imagination_registers_three_tools() {
        let store = make_store();
        let registry = wm_dispatch::ToolRegistry::new();
        let registry = register_imagination(&registry, &store);
        assert!(registry.get("imagine.scenario").is_some());
        assert!(registry.get("imagine.predict").is_some());
        assert!(registry.get("imagine.reflect").is_some());
    }
}
