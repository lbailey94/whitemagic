//! Self-play training tools — Sutton's second scaling method (learning).
//!
//! Gana::Ox — "Self-play training, LoRA adapter management, learning"
//!
//! Tools:
//! - `selfplay.run` — Run N self-play cycles (propose → solve → verify → collect)
//! - `selfplay.status` — Get self-play loop statistics
//! - `selfplay.export` — Export collected training data

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::{Arc, Mutex};
use wm_bicameral::{
    ExactMatchVerifier, LoRAAdapterManager, SelfPlayConfig, SelfPlayLoop, TaskProposer, TaskSolver,
    TierHandler,
};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_memory::MemoryStore;

// ── Stub TierHandler for self-play (when no LLM is available) ──────────

/// A simple stub handler that produces canned responses for self-play.
/// In production, the proposer uses the right hemisphere and the solver
/// uses the left hemisphere.
pub struct StubSelfPlayHandler {
    name: &'static str,
}

impl StubSelfPlayHandler {
    /// Create a new stub handler with the given name.
    #[must_use]
    pub const fn new(name: &'static str) -> Self {
        Self { name }
    }
}

impl TierHandler for StubSelfPlayHandler {
    fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        Ok((
            r#"{"prompt": "What is 2+2?", "expected": "4", "difficulty": 0.1}"#.to_string(),
            0.5,
        ))
    }

    fn name(&self) -> &'static str {
        self.name
    }
}

/// Build a SelfPlayLoop from environment configuration.
#[must_use]
pub fn build_self_play_loop(store_path: &std::path::Path) -> SelfPlayLoop {
    let adapter_dir = store_path.join("lora_adapters");

    // In production, these would be real LLM handlers.
    // For now, use stubs that produce reasonable test tasks.
    let proposer_handler = Box::new(StubSelfPlayHandler::new("stub_proposer"));
    let solver_handler = Box::new(StubSelfPlayHandler::new("stub_solver"));

    let proposer = TaskProposer::ungrounded(proposer_handler);
    let solver = TaskSolver::new(solver_handler);
    let verifier = Box::new(ExactMatchVerifier::new());
    let adapter = LoRAAdapterManager::with_config(adapter_dir, 1000, false);

    SelfPlayLoop::new(
        proposer,
        solver,
        verifier,
        adapter,
        SelfPlayConfig::default(),
    )
}

// ── Shared self-play state ────────────────────────────────────────────

/// Shared self-play loop state, protected by a mutex.
pub type SharedSelfPlayLoop = Arc<Mutex<Option<SelfPlayLoop>>>;

/// Create a new shared self-play loop state (initially empty).
#[must_use]
pub fn new_shared_loop() -> SharedSelfPlayLoop {
    Arc::new(Mutex::new(None))
}

// ── selfplay.run ──────────────────────────────────────────────────────

/// Run self-play cycles.
///
/// Executes the propose → solve → verify → collect loop N times.
/// If a LoRA update threshold is reached, triggers an adapter update.
pub struct SelfPlayRunTool {
    store: Arc<MemoryStore>,
    loop_state: SharedSelfPlayLoop,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfPlayRunTool {
    /// Create a new self-play run tool.
    pub fn new(store: Arc<MemoryStore>, loop_state: SharedSelfPlayLoop) -> Self {
        Self {
            store,
            loop_state,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("research".into())]),
        }
    }
}

#[async_trait]
impl Tool for SelfPlayRunTool {
    fn name(&self) -> &str {
        "selfplay.run"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Run self-play training cycles (propose → solve → verify → collect training data)"
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let num_cycles = args.get("cycles").and_then(Value::as_u64).unwrap_or(1) as usize;

        let memory_context = args
            .get("memory_context")
            .and_then(Value::as_str)
            .unwrap_or("");

        // Gather memory context if not provided
        let context = if memory_context.is_empty() {
            self.gather_memory_context()
        } else {
            memory_context.to_string()
        };

        // Get or create the self-play loop
        let mut loop_guard = self
            .loop_state
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-play loop lock: {e}")))?;
        if loop_guard.is_none() {
            // Build a new loop using the store path
            let store_path = self
                .store
                .path()
                .parent()
                .unwrap_or_else(|| std::path::Path::new("."));
            *loop_guard = Some(build_self_play_loop(store_path));
        }

        let loop_ = loop_guard.as_mut().unwrap();
        loop_.config.max_cycles_per_run = num_cycles;

        let results = loop_.run(&context);
        let stats = loop_.stats().clone();

        let cycle_results: Vec<Value> = results
            .iter()
            .map(|r| {
                json!({
                    "task_type": r.task.task_type.name(),
                    "prompt": r.task.prompt,
                    "difficulty": r.task.difficulty,
                    "solution": r.solution.output,
                    "confidence": r.solution.confidence,
                    "verified_correct": r.verification.correct,
                    "verification_score": r.verification.score,
                    "verifier": r.verification.verifier,
                    "collected": r.collected,
                    "adapter_updated": r.adapter_updated,
                    "duration_ms": r.duration_ms,
                })
            })
            .collect();

        Ok(json!({
            "cycles_run": results.len(),
            "results": cycle_results,
            "stats": {
                "total_cycles": stats.cycles,
                "verified_correct": stats.verified_correct,
                "verified_incorrect": stats.verified_incorrect,
                "accuracy": stats.accuracy(),
                "samples_collected": stats.samples_collected,
                "adapter_updates": stats.adapter_updates,
                "avg_difficulty": stats.avg_difficulty,
                "adapter_version": loop_.adapter_version(),
            },
        }))
    }
}

impl SelfPlayRunTool {
    fn gather_memory_context(&self) -> String {
        let mut parts = Vec::new();
        for galaxy in wm_core::Galaxy::memory_galaxies() {
            if let Ok(mems) = self.store.scan(galaxy, 10) {
                for mem in mems.iter().take(3) {
                    // model_exclude memories never enter task context.
                    if mem.metadata.model_exclude {
                        continue;
                    }
                    parts.push(format!("- {}", mem.content));
                }
            }
        }
        if parts.is_empty() {
            String::new()
        } else {
            parts.join("\n")
        }
    }
}

// ── selfplay.status ───────────────────────────────────────────────────

/// Get self-play loop statistics.
pub struct SelfPlayStatusTool {
    loop_state: SharedSelfPlayLoop,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfPlayStatusTool {
    /// Create a new self-play status tool.
    pub fn new(loop_state: SharedSelfPlayLoop) -> Self {
        Self {
            loop_state,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for SelfPlayStatusTool {
    fn name(&self) -> &str {
        "selfplay.status"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get self-play training loop statistics and status"
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let loop_guard = self
            .loop_state
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-play loop lock: {e}")))?;

        if let Some(loop_) = loop_guard.as_ref() {
            let stats = loop_.stats();
            Ok(json!({
                "initialized": true,
                "total_cycles": stats.cycles,
                "verified_correct": stats.verified_correct,
                "verified_incorrect": stats.verified_incorrect,
                "accuracy": stats.accuracy(),
                "samples_collected": stats.samples_collected,
                "adapter_updates": stats.adapter_updates,
                "adapter_version": loop_.adapter_version(),
                "sample_count": loop_.sample_count(),
                "avg_difficulty": stats.avg_difficulty,
                "accuracy_trend": stats.accuracy_trend,
                "success_by_type": stats.success_by_type,
            }))
        } else {
            Ok(json!({
                "initialized": false,
                "message": "Self-play loop not yet initialized. Run selfplay.run to start.",
            }))
        }
    }
}

// ── selfplay.export ───────────────────────────────────────────────────

/// Export collected training data from the self-play loop.
pub struct SelfPlayExportTool {
    loop_state: SharedSelfPlayLoop,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfPlayExportTool {
    /// Create a new self-play export tool.
    pub fn new(loop_state: SharedSelfPlayLoop) -> Self {
        Self {
            loop_state,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for SelfPlayExportTool {
    fn name(&self) -> &str {
        "selfplay.export"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Export collected self-play training data (JSONL or llama.cpp format)"
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let format = args
            .get("format")
            .and_then(Value::as_str)
            .unwrap_or("jsonl");

        let include_negative = args
            .get("include_negative")
            .and_then(Value::as_bool)
            .unwrap_or(false);

        let loop_guard = self
            .loop_state
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-play loop lock: {e}")))?;

        if let Some(loop_) = loop_guard.as_ref() {
            let data = match format {
                "llama_cpp" => loop_.export_llama_cpp(),
                _ => loop_.export_training_data(include_negative),
            };

            let sample_count = data.lines().count();

            Ok(json!({
                "format": format,
                "sample_count": sample_count,
                "data": data,
            }))
        } else {
            Ok(json!({
                "format": format,
                "sample_count": 0,
                "data": "",
                "message": "Self-play loop not yet initialized.",
            }))
        }
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all self-play tools into a registry.
pub fn register_self_play(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    loop_state: SharedSelfPlayLoop,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(SelfPlayRunTool::new(
            store.clone(),
            loop_state.clone(),
        )))
        .register(Arc::new(SelfPlayStatusTool::new(loop_state.clone())))
        .register(Arc::new(SelfPlayExportTool::new(loop_state)))
}
