//! Self-Play Training Loop — Sutton's second scaling method (learning).
//!
//! Implements the closed-loop self-play cycle:
//! 1. **Propose** a task (grounded in memory — friction entries, knowledge gaps)
//! 2. **Solve** the task (model attempts to solve)
//! 3. **Verify** the outcome (code executor, tool result, self-verification)
//! 4. **Collect** training samples (prompt, response, label)
//! 5. **Fine-tune** (LoRA adapter update)
//! 6. **Hot-swap** (load new adapter, continue)
//!
//! Research basis:
//! - AZR (NeurIPS 2025): Self-play with zero external data
//! - SSP (2025): Co-evolution of proposer and solver
//! - RISE (NeurIPS 2025): Simultaneous training of solving and verification
//! - VPR (2026): Dense turn-level supervision from symbolic oracles

#![allow(clippy::significant_drop_tightening)]

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::time::Instant;

use crate::router::{TierHandler, TrainingDataCollector, TrainingSample};

// ── Task Types ────────────────────────────────────────────────────────

/// The type of self-play task to generate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TaskType {
    /// Code generation task (produce code that compiles/tests)
    CodeGeneration,
    /// Tool dispatch task (select the right tool for a query)
    ToolDispatch,
    /// Reasoning task (answer a question with verifiable logic)
    Reasoning,
    /// Memory task (recall, consolidate, or associate)
    Memory,
    /// Creative task (generate novel combinations)
    Creative,
}

impl TaskType {
    /// All task types.
    #[must_use]
    pub const fn all() -> [Self; 5] {
        [
            Self::CodeGeneration,
            Self::ToolDispatch,
            Self::Reasoning,
            Self::Memory,
            Self::Creative,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::CodeGeneration => "code_generation",
            Self::ToolDispatch => "tool_dispatch",
            Self::Reasoning => "reasoning",
            Self::Memory => "memory",
            Self::Creative => "creative",
        }
    }
}

impl std::fmt::Display for TaskType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.name())
    }
}

// ── Task ──────────────────────────────────────────────────────────────

/// A self-play task proposed by the proposer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelfPlayTask {
    /// The prompt to solve
    pub prompt: String,
    /// The type of task
    pub task_type: TaskType,
    /// Expected answer or verification criteria
    pub expected: String,
    /// Difficulty level (0.0 = trivial, 1.0 = frontier)
    pub difficulty: f32,
    /// Source grounding (e.g., "friction:hash123", "gap:memory_456")
    pub grounding: String,
}

/// A solution produced by the solver.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Solution {
    /// The model's response
    pub output: String,
    /// Confidence reported by the solver
    pub confidence: f32,
    /// Which inference tier produced this
    pub tier: String,
    /// Time taken to produce the solution
    pub duration_ms: u64,
}

/// Verification result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    /// Whether the solution is correct
    pub correct: bool,
    /// Verification score (0.0 = completely wrong, 1.0 = perfect)
    pub score: f32,
    /// Feedback for improvement (empty if correct)
    pub feedback: String,
    /// Which verifier was used
    pub verifier: String,
}

/// Result of a single self-play cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleResult {
    /// The task that was proposed
    pub task: SelfPlayTask,
    /// The solution that was produced
    pub solution: Solution,
    /// The verification result
    pub verification: VerificationResult,
    /// Whether a training sample was collected
    pub collected: bool,
    /// Whether a LoRA update was triggered
    pub adapter_updated: bool,
    /// Cycle duration in ms
    pub duration_ms: u64,
}

/// Aggregate statistics for the self-play loop.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SelfPlayStats {
    /// Total cycles completed
    pub cycles: u64,
    /// Total tasks proposed
    pub tasks_proposed: u64,
    /// Total solutions verified correct
    pub verified_correct: u64,
    /// Total solutions verified incorrect
    pub verified_incorrect: u64,
    /// Total training samples collected
    pub samples_collected: u64,
    /// Total LoRA adapter updates
    pub adapter_updates: u64,
    /// Per-task-type success rates
    pub success_by_type: HashMap<String, (u64, u64)>,
    /// Average difficulty of proposed tasks
    pub avg_difficulty: f32,
    /// Recent accuracy trend (last N cycles)
    pub accuracy_trend: Vec<f32>,
}

impl SelfPlayStats {
    /// Overall accuracy (correct / total).
    #[must_use]
    pub fn accuracy(&self) -> f32 {
        let total = self.verified_correct + self.verified_incorrect;
        if total == 0 {
            return 0.0;
        }
        self.verified_correct as f32 / total as f32
    }

    /// Record a cycle result.
    pub fn record(&mut self, result: &CycleResult) {
        self.cycles += 1;
        self.tasks_proposed += 1;
        if result.verification.correct {
            self.verified_correct += 1;
        } else {
            self.verified_incorrect += 1;
        }
        if result.collected {
            self.samples_collected += 1;
        }
        if result.adapter_updated {
            self.adapter_updates += 1;
        }

        let key = result.task.task_type.name().to_string();
        let (correct, total) = self.success_by_type.entry(key).or_insert((0, 0));
        *total += 1;
        if result.verification.correct {
            *correct += 1;
        }

        // Update rolling average difficulty
        let n = self.cycles as f32;
        self.avg_difficulty = self.avg_difficulty.mul_add(n - 1.0, result.task.difficulty) / n;

        // Update accuracy trend (keep last 100)
        self.accuracy_trend.push(if result.verification.correct {
            1.0
        } else {
            0.0
        });
        if self.accuracy_trend.len() > 100 {
            self.accuracy_trend.remove(0);
        }
    }
}

// ── Task Proposer ─────────────────────────────────────────────────────

/// A task proposer generates self-play tasks grounded in memory.
///
/// The proposer uses the bicameral right hemisphere (creative) to generate
/// tasks. Tasks are grounded in:
/// - Recent friction entries (system failures → "fix this" tasks)
/// - Knowledge gaps (unanswered queries → "answer this" tasks)
/// - Co-usage patterns (tools used together → "compose these" tasks)
pub struct TaskProposer {
    /// Handler for generating tasks (typically right hemisphere / LLM)
    handler: Box<dyn TierHandler>,
    /// Seed prompts for each task type
    seed_prompts: HashMap<TaskType, Vec<String>>,
    /// Whether to use memory grounding
    grounded: bool,
}

impl TaskProposer {
    /// Create a new task proposer with the given handler.
    #[must_use]
    pub fn new(handler: Box<dyn TierHandler>) -> Self {
        Self {
            handler,
            seed_prompts: default_seed_prompts(),
            grounded: true,
        }
    }

    /// Create a proposer that doesn't ground in memory (for testing).
    #[must_use]
    pub fn ungrounded(handler: Box<dyn TierHandler>) -> Self {
        Self {
            handler,
            seed_prompts: default_seed_prompts(),
            grounded: false,
        }
    }

    /// Propose a task of the given type, optionally grounded in memory context.
    pub fn propose(
        &self,
        task_type: TaskType,
        memory_context: &str,
    ) -> Result<SelfPlayTask, String> {
        let empty_seeds = Vec::new();
        let seeds = self.seed_prompts.get(&task_type).unwrap_or(&empty_seeds);
        let seed = seeds.first().cloned().unwrap_or_default();

        let prompt = if self.grounded && !memory_context.is_empty() {
            format!(
                "Based on the following context, generate a {task_type} task.\n\
                 Context:\n{memory_context}\n\n\
                 Seed idea: {seed}\n\n\
                 Output a JSON object with 'prompt', 'expected', and 'difficulty' (0.0-1.0)."
            )
        } else {
            format!(
                "Generate a {task_type} task.\n\
                 Seed idea: {seed}\n\n\
                 Output a JSON object with 'prompt', 'expected', and 'difficulty' (0.0-1.0)."
            )
        };

        let (response, _confidence) = self.handler.handle(&prompt, 500)?;

        // Parse the response as a task
        parse_task(&response, task_type)
    }

    /// Propose a task from friction entries (grounded in system failures).
    pub fn propose_from_friction(&self, friction_summary: &str) -> Result<SelfPlayTask, String> {
        let prompt = format!(
            "A system encountered these friction points:\n{friction_summary}\n\n\
             Generate a task that would help the system learn to avoid these failures.\n\
             Output a JSON object with 'prompt', 'expected', and 'difficulty' (0.0-1.0)."
        );

        let (response, _) = self.handler.handle(&prompt, 500)?;
        // Friction tasks are typically code generation or reasoning
        parse_task(&response, TaskType::CodeGeneration)
    }
}

// ── Solver ────────────────────────────────────────────────────────────

/// A task solver attempts to solve a self-play task.
///
/// Uses the bicameral left hemisphere (deterministic) for solving.
pub struct TaskSolver {
    handler: Box<dyn TierHandler>,
}

impl TaskSolver {
    /// Create a new solver with the given handler.
    #[must_use]
    pub fn new(handler: Box<dyn TierHandler>) -> Self {
        Self { handler }
    }

    /// Solve a task and return the solution.
    pub fn solve(&self, task: &SelfPlayTask) -> Result<Solution, String> {
        let start = Instant::now();
        let prompt = format!(
            "Solve the following task:\n{}\n\n\
             Provide a clear, correct answer.",
            task.prompt
        );

        let (output, confidence) = self.handler.handle(&prompt, 1000)?;
        let duration = start.elapsed();

        Ok(Solution {
            output,
            confidence,
            tier: self.handler.name().to_string(),
            duration_ms: duration.as_millis() as u64,
        })
    }
}

// ── Verifier ──────────────────────────────────────────────────────────

/// Trait for verifying self-play solutions.
pub trait Verifier: Send + Sync {
    /// Verify a solution against a task.
    fn verify(&self, task: &SelfPlayTask, solution: &Solution) -> VerificationResult;

    /// Name of this verifier.
    fn name(&self) -> &'static str;
}

/// Self-verification verifier (RISE-inspired).
///
/// The model critiques its own solution, calibrated by historical accuracy.
pub struct SelfVerifier {
    handler: Box<dyn TierHandler>,
    /// Historical accuracy for calibration
    historical_accuracy: f32,
}

impl SelfVerifier {
    /// Create a new self-verifier.
    #[must_use]
    pub fn new(handler: Box<dyn TierHandler>, historical_accuracy: f32) -> Self {
        Self {
            handler,
            historical_accuracy,
        }
    }

    /// Update the historical accuracy.
    pub const fn update_accuracy(&mut self, accuracy: f32) {
        self.historical_accuracy = accuracy;
    }
}

impl Verifier for SelfVerifier {
    fn verify(&self, task: &SelfPlayTask, solution: &Solution) -> VerificationResult {
        let prompt = format!(
            "Task: {}\n\n\
             Expected: {}\n\n\
             Proposed solution: {}\n\n\
             Is the solution correct? Output JSON: {{\"correct\": true/false, \"score\": 0.0-1.0, \"feedback\": \"...\"}}",
            task.prompt, task.expected, solution.output
        );

        match self.handler.handle(&prompt, 300) {
            Ok((response, _)) => {
                let parsed = parse_verification(&response);
                // Calibrate: if historical accuracy is low, be more skeptical
                let calibrated_score = parsed.score * self.historical_accuracy.max(0.5);
                VerificationResult {
                    correct: parsed.correct && calibrated_score > 0.3,
                    score: calibrated_score,
                    feedback: parsed.feedback,
                    verifier: "self".to_string(),
                }
            }
            Err(e) => VerificationResult {
                correct: false,
                score: 0.0,
                feedback: format!("Verification error: {e}"),
                verifier: "self".to_string(),
            },
        }
    }

    fn name(&self) -> &'static str {
        "self"
    }
}

/// Exact-match verifier — checks if the solution contains the expected answer.
#[derive(Default)]
pub struct ExactMatchVerifier;

impl ExactMatchVerifier {
    /// Create a new exact-match verifier.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }
}

impl Verifier for ExactMatchVerifier {
    fn verify(&self, task: &SelfPlayTask, solution: &Solution) -> VerificationResult {
        let expected_lower = task.expected.to_lowercase();
        let output_lower = solution.output.to_lowercase();

        let correct = output_lower.contains(&expected_lower);
        let score = if correct { 1.0 } else { 0.0 };

        VerificationResult {
            correct,
            score,
            feedback: if correct {
                String::new()
            } else {
                format!(
                    "Expected to find '{expected}' in output",
                    expected = task.expected
                )
            },
            verifier: "exact_match".to_string(),
        }
    }

    fn name(&self) -> &'static str {
        "exact_match"
    }
}

/// Tool result verifier — checks if a tool dispatch succeeded.
#[derive(Default)]
pub struct ToolResultVerifier;

impl ToolResultVerifier {
    /// Create a new tool result verifier.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }
}

impl Verifier for ToolResultVerifier {
    fn verify(&self, task: &SelfPlayTask, solution: &Solution) -> VerificationResult {
        // For tool dispatch tasks, the solution should contain a tool name
        // and the expected should be the correct tool name
        let correct = solution.output.contains(&task.expected);
        let score = if correct { 1.0 } else { 0.0 };

        VerificationResult {
            correct,
            score,
            feedback: if correct {
                String::new()
            } else {
                format!(
                    "Expected tool '{expected}', got '{output}'",
                    expected = task.expected,
                    output = solution.output
                )
            },
            verifier: "tool_result".to_string(),
        }
    }

    fn name(&self) -> &'static str {
        "tool_result"
    }
}

// ── LoRA Adapter Manager ──────────────────────────────────────────────

/// Manages LoRA adapters for hot-swap during self-play training.
///
/// In production, this would interface with llama.cpp's LoRA training
/// pipeline. In the current implementation, it tracks adapter versions
/// and exports training data when enough samples are collected.
pub struct LoRAAdapterManager {
    /// Path to the adapter directory
    adapter_dir: std::path::PathBuf,
    /// Current adapter version (0 = base model, no adapter)
    current_version: u32,
    /// Minimum samples before triggering an update
    min_samples: usize,
    /// Whether hot-swap is enabled (requires llama.cpp backend)
    hot_swap_enabled: bool,
    /// History of adapter updates
    update_history: Vec<AdapterUpdate>,
}

/// Record of a single adapter update.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdapterUpdate {
    /// Version number of the new adapter
    pub version: u32,
    /// Number of training samples used
    pub samples_used: usize,
    /// Timestamp of the update
    pub timestamp: u64,
    /// Training loss (if available)
    pub loss: Option<f32>,
}

impl LoRAAdapterManager {
    /// Create a new adapter manager.
    #[must_use]
    pub const fn new(adapter_dir: std::path::PathBuf) -> Self {
        Self {
            adapter_dir,
            current_version: 0,
            min_samples: 1000,
            hot_swap_enabled: false,
            update_history: Vec::new(),
        }
    }

    /// Create an adapter manager with custom settings.
    #[must_use]
    pub const fn with_config(
        adapter_dir: std::path::PathBuf,
        min_samples: usize,
        hot_swap_enabled: bool,
    ) -> Self {
        Self {
            adapter_dir,
            current_version: 0,
            min_samples,
            hot_swap_enabled,
            update_history: Vec::new(),
        }
    }

    /// Current adapter version.
    #[must_use]
    pub const fn current_version(&self) -> u32 {
        self.current_version
    }

    /// Whether enough samples are available for an update.
    #[must_use]
    pub const fn ready_for_update(&self, sample_count: usize) -> bool {
        sample_count >= self.min_samples
    }

    /// Minimum samples for an update.
    #[must_use]
    pub const fn min_samples(&self) -> usize {
        self.min_samples
    }

    /// Whether hot-swap is enabled.
    #[must_use]
    pub const fn hot_swap_enabled(&self) -> bool {
        self.hot_swap_enabled
    }

    /// Trigger an adapter update with the given training data.
    ///
    /// In the current implementation, this exports the data to a file
    /// and increments the version counter. In production, this would
    /// call llama.cpp's LoRA training pipeline.
    pub fn update(&mut self, training_data: &str) -> Result<AdapterUpdate, String> {
        self.current_version += 1;
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_secs());

        // Write training data to adapter directory
        let filename = format!("adapter_v{}_train.jsonl", self.current_version);
        let filepath = self.adapter_dir.join(&filename);
        std::fs::create_dir_all(&self.adapter_dir)
            .map_err(|e| format!("Failed to create adapter dir: {e}"))?;
        std::fs::write(&filepath, training_data)
            .map_err(|e| format!("Failed to write training data: {e}"))?;

        let update = AdapterUpdate {
            version: self.current_version,
            samples_used: training_data.lines().count(),
            timestamp,
            loss: None,
        };

        tracing::info!(
            version = self.current_version,
            samples = update.samples_used,
            "LoRA adapter updated"
        );

        self.update_history.push(update.clone());
        Ok(update)
    }

    /// Get the update history.
    #[must_use]
    pub fn update_history(&self) -> &[AdapterUpdate] {
        &self.update_history
    }
}

// ── Self-Play Loop ────────────────────────────────────────────────────

/// Configuration for the self-play loop.
#[derive(Debug, Clone)]
pub struct SelfPlayConfig {
    /// Minimum samples before triggering a LoRA update
    pub min_samples_for_update: usize,
    /// Maximum cycles per run
    pub max_cycles_per_run: usize,
    /// Whether to use self-verification (RISE)
    pub self_verification: bool,
    /// Whether to use exact-match verification for simple tasks
    pub exact_match_for_simple: bool,
    /// Task types to cycle through
    pub task_types: Vec<TaskType>,
}

impl Default for SelfPlayConfig {
    fn default() -> Self {
        Self {
            min_samples_for_update: 1000,
            max_cycles_per_run: 10,
            self_verification: true,
            exact_match_for_simple: true,
            task_types: TaskType::all().to_vec(),
        }
    }
}

/// The self-play training loop.
///
/// Cycles through: propose → solve → verify → collect → (optionally) fine-tune.
/// The loop improves the system with compute, not code.
pub struct SelfPlayLoop {
    /// Task proposer (creative / right hemisphere)
    proposer: TaskProposer,
    /// Task solver (deterministic / left hemisphere)
    solver: TaskSolver,
    /// Verifier (self-verification, exact-match, or tool-result)
    verifier: Box<dyn Verifier>,
    /// Training data collector (ring buffer)
    collector: TrainingDataCollector,
    /// LoRA adapter manager
    adapter: LoRAAdapterManager,
    /// Configuration
    pub config: SelfPlayConfig,
    /// Aggregate statistics
    stats: SelfPlayStats,
    /// Current task type index (cycles through config.task_types)
    task_type_idx: usize,
}

impl SelfPlayLoop {
    /// Create a new self-play loop.
    #[must_use]
    pub fn new(
        proposer: TaskProposer,
        solver: TaskSolver,
        verifier: Box<dyn Verifier>,
        adapter: LoRAAdapterManager,
        config: SelfPlayConfig,
    ) -> Self {
        Self {
            proposer,
            solver,
            verifier,
            collector: TrainingDataCollector::default_capacity(),
            adapter,
            config,
            stats: SelfPlayStats::default(),
            task_type_idx: 0,
        }
    }

    /// Run a single self-play cycle.
    pub fn run_cycle(&mut self, memory_context: &str) -> CycleResult {
        let start = Instant::now();

        // 1. Select task type (round-robin)
        let task_type = self.config.task_types[self.task_type_idx % self.config.task_types.len()];
        self.task_type_idx += 1;

        // 2. Propose a task
        let task = match self.proposer.propose(task_type, memory_context) {
            Ok(t) => t,
            Err(e) => {
                return CycleResult {
                    task: SelfPlayTask {
                        prompt: format!("(proposer error: {e})"),
                        task_type,
                        expected: String::new(),
                        difficulty: 0.0,
                        grounding: String::new(),
                    },
                    solution: Solution {
                        output: String::new(),
                        confidence: 0.0,
                        tier: "error".to_string(),
                        duration_ms: 0,
                    },
                    verification: VerificationResult {
                        correct: false,
                        score: 0.0,
                        feedback: e,
                        verifier: "none".to_string(),
                    },
                    collected: false,
                    adapter_updated: false,
                    duration_ms: start.elapsed().as_millis() as u64,
                };
            }
        };

        // 3. Solve the task
        let solution = match self.solver.solve(&task) {
            Ok(s) => s,
            Err(e) => {
                return CycleResult {
                    task,
                    solution: Solution {
                        output: format!("(solver error: {e})"),
                        confidence: 0.0,
                        tier: "error".to_string(),
                        duration_ms: 0,
                    },
                    verification: VerificationResult {
                        correct: false,
                        score: 0.0,
                        feedback: e,
                        verifier: "none".to_string(),
                    },
                    collected: false,
                    adapter_updated: false,
                    duration_ms: start.elapsed().as_millis() as u64,
                };
            }
        };

        // 4. Verify the outcome
        let verification = self.verifier.verify(&task, &solution);

        // 5. Collect training sample
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_secs());

        self.collector.add(TrainingSample {
            prompt: task.prompt.clone(),
            response: solution.output.clone(),
            raw_confidence: solution.confidence,
            verified_correct: verification.correct,
            tier: solution.tier.clone(),
            task_type: task.task_type.name().to_string(),
            timestamp,
        });

        // 6. If enough samples, trigger LoRA update
        let adapter_updated = if self.adapter.ready_for_update(self.collector.len()) {
            let data = self.collector.export_llama_cpp();
            match self.adapter.update(&data) {
                Ok(_) => {
                    self.collector.clear();
                    true
                }
                Err(e) => {
                    tracing::warn!("LoRA update failed: {e}");
                    false
                }
            }
        } else {
            false
        };

        let result = CycleResult {
            task,
            solution,
            verification,
            collected: true,
            adapter_updated,
            duration_ms: start.elapsed().as_millis() as u64,
        };

        self.stats.record(&result);
        result
    }

    /// Run multiple cycles (up to config.max_cycles_per_run).
    pub fn run(&mut self, memory_context: &str) -> Vec<CycleResult> {
        let max = self.config.max_cycles_per_run;
        let mut results = Vec::with_capacity(max);
        for _ in 0..max {
            let result = self.run_cycle(memory_context);
            let success = result.verification.correct;
            results.push(result);
            // Stop early if we're in a failure loop
            if !success
                && results.len() > 3
                && results
                    .iter()
                    .rev()
                    .take(3)
                    .all(|r| !r.verification.correct)
            {
                tracing::warn!("Self-play loop stopping early: 3 consecutive failures");
                break;
            }
        }
        results
    }

    /// Get aggregate statistics.
    #[must_use]
    pub const fn stats(&self) -> &SelfPlayStats {
        &self.stats
    }

    /// Get the training data collector.
    #[must_use]
    pub const fn collector(&self) -> &TrainingDataCollector {
        &self.collector
    }

    /// Get the LoRA adapter manager.
    #[must_use]
    pub const fn adapter(&self) -> &LoRAAdapterManager {
        &self.adapter
    }

    /// Get the current adapter version.
    #[must_use]
    pub const fn adapter_version(&self) -> u32 {
        self.adapter.current_version()
    }

    /// Number of collected training samples.
    #[must_use]
    pub fn sample_count(&self) -> usize {
        self.collector.len()
    }

    /// Export training data in JSONL format.
    #[must_use]
    pub fn export_training_data(&self, include_negative: bool) -> String {
        self.collector.export_jsonl(include_negative)
    }

    /// Export training data in llama.cpp format.
    #[must_use]
    pub fn export_llama_cpp(&self) -> String {
        self.collector.export_llama_cpp()
    }
}

// ── Helpers ───────────────────────────────────────────────────────────

/// Default seed prompts for each task type.
fn default_seed_prompts() -> HashMap<TaskType, Vec<String>> {
    let mut map = HashMap::new();
    map.insert(
        TaskType::CodeGeneration,
        vec![
            "Write a function that reverses a list in Rust".to_string(),
            "Implement a binary search algorithm".to_string(),
            "Write a function to check if a string is a palindrome".to_string(),
            "Implement a simple hash map from scratch".to_string(),
            "Write a function to find the nth Fibonacci number".to_string(),
        ],
    );
    map.insert(
        TaskType::ToolDispatch,
        vec![
            "Which tool should I use to create a memory?".to_string(),
            "How do I search for memories by content?".to_string(),
            "What tool consolidates duplicate memories?".to_string(),
            "Which tool shows the current brain-wave state?".to_string(),
            "How do I list all tools?".to_string(),
        ],
    );
    map.insert(
        TaskType::Reasoning,
        vec![
            "Explain why LMDB is faster than SQLite for read-heavy workloads".to_string(),
            "What are the trade-offs of async vs sync dispatch?".to_string(),
            "Why does the bitter lesson suggest search over heuristics?".to_string(),
            "Explain the relationship between Gana taxonomy and tool routing".to_string(),
            "Why is conformal calibration better than fixed thresholds?".to_string(),
        ],
    );
    map.insert(
        TaskType::Memory,
        vec![
            "Consolidate these three memories about Rust into one summary".to_string(),
            "What memories are associated with the tag 'database'?".to_string(),
            "Find memories in the Codex galaxy that mention LMDB".to_string(),
            "Which memories should be forgotten based on low significance?".to_string(),
            "Create an association between the Rust memory and the LMDB memory".to_string(),
        ],
    );
    map.insert(
        TaskType::Creative,
        vec![
            "Propose a new tool that combines memory search with association mining".to_string(),
            "Design a new dream cycle phase that uses the imagination engine".to_string(),
            "Suggest a novel Gana category for tools that don't fit existing categories"
                .to_string(),
            "Invent a new autonomous cycle type that leverages self-play".to_string(),
            "Design a karma weighting scheme that rewards successful self-play".to_string(),
        ],
    );
    map
}

/// Parse a task from an LLM response.
fn parse_task(response: &str, task_type: TaskType) -> Result<SelfPlayTask, String> {
    // Try to parse as JSON first
    if let Ok(json) = serde_json::from_str::<serde_json::Value>(response) {
        let prompt = json
            .get("prompt")
            .and_then(|v| v.as_str())
            .unwrap_or(response)
            .to_string();
        let expected = json
            .get("expected")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let difficulty = json
            .get("difficulty")
            .and_then(Value::as_f64)
            .unwrap_or(0.5) as f32;

        return Ok(SelfPlayTask {
            prompt,
            task_type,
            expected,
            difficulty: difficulty.clamp(0.0, 1.0),
            grounding: "llm_generated".to_string(),
        });
    }

    // Fallback: use the response as the prompt directly
    Ok(SelfPlayTask {
        prompt: response.to_string(),
        task_type,
        expected: String::new(),
        difficulty: 0.5,
        grounding: "fallback".to_string(),
    })
}

/// Parse a verification response.
fn parse_verification(response: &str) -> VerificationResult {
    if let Ok(json) = serde_json::from_str::<serde_json::Value>(response) {
        let correct = json
            .get("correct")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let score = json
            .get("score")
            .and_then(Value::as_f64)
            .unwrap_or(if correct { 1.0 } else { 0.0 }) as f32;
        let feedback = json
            .get("feedback")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        return VerificationResult {
            correct,
            score,
            feedback,
            verifier: "self".to_string(),
        };
    }

    // Fallback: check for "correct" or "incorrect" in the response
    let lower = response.to_lowercase();
    let correct = lower.contains("correct") && !lower.contains("incorrect");
    VerificationResult {
        correct,
        score: if correct { 0.8 } else { 0.2 },
        feedback: response.to_string(),
        verifier: "self".to_string(),
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    /// Stub handler that returns canned responses.
    struct StubHandler {
        response: String,
        confidence: f32,
    }

    impl TierHandler for StubHandler {
        fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            Ok((self.response.clone(), self.confidence))
        }
        fn name(&self) -> &'static str {
            "stub"
        }
    }

    #[test]
    fn task_type_all_has_5() {
        assert_eq!(TaskType::all().len(), 5);
    }

    #[test]
    fn task_type_names() {
        assert_eq!(TaskType::CodeGeneration.name(), "code_generation");
        assert_eq!(TaskType::ToolDispatch.name(), "tool_dispatch");
        assert_eq!(TaskType::Reasoning.name(), "reasoning");
        assert_eq!(TaskType::Memory.name(), "memory");
        assert_eq!(TaskType::Creative.name(), "creative");
    }

    #[test]
    fn self_play_stats_accuracy() {
        let mut stats = SelfPlayStats::default();
        assert_eq!(stats.accuracy(), 0.0);

        // Record 3 correct, 1 incorrect
        let make_result = |correct: bool| CycleResult {
            task: SelfPlayTask {
                prompt: "test".to_string(),
                task_type: TaskType::Reasoning,
                expected: "answer".to_string(),
                difficulty: 0.5,
                grounding: "test".to_string(),
            },
            solution: Solution {
                output: "answer".to_string(),
                confidence: 0.9,
                tier: "stub".to_string(),
                duration_ms: 10,
            },
            verification: VerificationResult {
                correct,
                score: if correct { 1.0 } else { 0.0 },
                feedback: String::new(),
                verifier: "test".to_string(),
            },
            collected: true,
            adapter_updated: false,
            duration_ms: 10,
        };

        stats.record(&make_result(true));
        stats.record(&make_result(true));
        stats.record(&make_result(true));
        stats.record(&make_result(false));

        assert_eq!(stats.cycles, 4);
        assert_eq!(stats.verified_correct, 3);
        assert_eq!(stats.verified_incorrect, 1);
        assert!((stats.accuracy() - 0.75).abs() < 0.01);
    }

    #[test]
    fn task_proposer_generates_task() {
        let handler = Box::new(StubHandler {
            response: r#"{"prompt": "What is 2+2?", "expected": "4", "difficulty": 0.1}"#
                .to_string(),
            confidence: 0.9,
        });
        let proposer = TaskProposer::ungrounded(handler);
        let task = proposer.propose(TaskType::Reasoning, "").unwrap();
        assert_eq!(task.prompt, "What is 2+2?");
        assert_eq!(task.expected, "4");
        assert!((task.difficulty - 0.1).abs() < 0.01);
    }

    #[test]
    fn task_proposer_fallback_on_non_json() {
        let handler = Box::new(StubHandler {
            response: "What is the meaning of life?".to_string(),
            confidence: 0.5,
        });
        let proposer = TaskProposer::ungrounded(handler);
        let task = proposer.propose(TaskType::Reasoning, "").unwrap();
        assert_eq!(task.prompt, "What is the meaning of life?");
        assert_eq!(task.task_type, TaskType::Reasoning);
    }

    #[test]
    fn solver_produces_solution() {
        let handler = Box::new(StubHandler {
            response: "The answer is 42.".to_string(),
            confidence: 0.95,
        });
        let solver = TaskSolver::new(handler);
        let task = SelfPlayTask {
            prompt: "What is the answer?".to_string(),
            task_type: TaskType::Reasoning,
            expected: "42".to_string(),
            difficulty: 0.3,
            grounding: "test".to_string(),
        };
        let solution = solver.solve(&task).unwrap();
        assert_eq!(solution.output, "The answer is 42.");
        assert!((solution.confidence - 0.95).abs() < 0.01);
    }

    #[test]
    fn exact_match_verifier_correct() {
        let verifier = ExactMatchVerifier::new();
        let task = SelfPlayTask {
            prompt: "What is 2+2?".to_string(),
            task_type: TaskType::Reasoning,
            expected: "4".to_string(),
            difficulty: 0.1,
            grounding: "test".to_string(),
        };
        let solution = Solution {
            output: "The answer is 4.".to_string(),
            confidence: 0.9,
            tier: "stub".to_string(),
            duration_ms: 10,
        };
        let result = verifier.verify(&task, &solution);
        assert!(result.correct);
        assert!((result.score - 1.0).abs() < 0.01);
    }

    #[test]
    fn exact_match_verifier_incorrect() {
        let verifier = ExactMatchVerifier::new();
        let task = SelfPlayTask {
            prompt: "What is 2+2?".to_string(),
            task_type: TaskType::Reasoning,
            expected: "4".to_string(),
            difficulty: 0.1,
            grounding: "test".to_string(),
        };
        let solution = Solution {
            output: "The answer is 5.".to_string(),
            confidence: 0.9,
            tier: "stub".to_string(),
            duration_ms: 10,
        };
        let result = verifier.verify(&task, &solution);
        assert!(!result.correct);
        assert!((result.score - 0.0).abs() < 0.01);
        assert!(!result.feedback.is_empty());
    }

    #[test]
    fn tool_result_verifier() {
        let verifier = ToolResultVerifier::new();
        let task = SelfPlayTask {
            prompt: "Which tool creates a memory?".to_string(),
            task_type: TaskType::ToolDispatch,
            expected: "memory.create".to_string(),
            difficulty: 0.2,
            grounding: "test".to_string(),
        };
        let solution = Solution {
            output: "Use memory.create to create a memory".to_string(),
            confidence: 0.9,
            tier: "stub".to_string(),
            duration_ms: 10,
        };
        let result = verifier.verify(&task, &solution);
        assert!(result.correct);
    }

    #[test]
    fn self_verifier_parses_json() {
        let handler = Box::new(StubHandler {
            response: r#"{"correct": true, "score": 0.9, "feedback": ""}"#.to_string(),
            confidence: 0.8,
        });
        let verifier = SelfVerifier::new(handler, 0.8);
        let task = SelfPlayTask {
            prompt: "test".to_string(),
            task_type: TaskType::Reasoning,
            expected: "answer".to_string(),
            difficulty: 0.5,
            grounding: "test".to_string(),
        };
        let solution = Solution {
            output: "answer".to_string(),
            confidence: 0.9,
            tier: "stub".to_string(),
            duration_ms: 10,
        };
        let result = verifier.verify(&task, &solution);
        assert!(result.correct);
        assert!((result.score - 0.72).abs() < 0.01); // 0.9 * 0.8
    }

    #[test]
    fn self_verifier_fallback_on_non_json() {
        let handler = Box::new(StubHandler {
            response: "The solution is correct.".to_string(),
            confidence: 0.8,
        });
        let verifier = SelfVerifier::new(handler, 1.0);
        let task = SelfPlayTask {
            prompt: "test".to_string(),
            task_type: TaskType::Reasoning,
            expected: "answer".to_string(),
            difficulty: 0.5,
            grounding: "test".to_string(),
        };
        let solution = Solution {
            output: "answer".to_string(),
            confidence: 0.9,
            tier: "stub".to_string(),
            duration_ms: 10,
        };
        let result = verifier.verify(&task, &solution);
        assert!(result.correct);
    }

    #[test]
    fn lora_adapter_manager_update() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = LoRAAdapterManager::new(tmp.path().to_path_buf());
        assert_eq!(manager.current_version(), 0);

        let update = manager.update("test data\nline 2\n").unwrap();
        assert_eq!(update.version, 1);
        assert_eq!(update.samples_used, 2);
        assert_eq!(manager.current_version(), 1);
        assert_eq!(manager.update_history().len(), 1);
    }

    #[test]
    fn lora_adapter_manager_ready_for_update() {
        let manager = LoRAAdapterManager::with_config(
            std::path::PathBuf::from("/tmp/test_adapters"),
            100,
            false,
        );
        assert!(!manager.ready_for_update(50));
        assert!(manager.ready_for_update(100));
        assert!(manager.ready_for_update(200));
    }

    #[test]
    fn self_play_loop_single_cycle() {
        let proposer_handler = Box::new(StubHandler {
            response: r#"{"prompt": "What is 3+3?", "expected": "6", "difficulty": 0.15}"#
                .to_string(),
            confidence: 0.9,
        });
        let solver_handler = Box::new(StubHandler {
            response: "The answer is 6.".to_string(),
            confidence: 0.95,
        });

        let tmp = tempfile::tempdir().unwrap();
        let adapter = LoRAAdapterManager::with_config(tmp.path().to_path_buf(), 10000, false);

        let mut loop_ = SelfPlayLoop::new(
            TaskProposer::ungrounded(proposer_handler),
            TaskSolver::new(solver_handler),
            Box::new(ExactMatchVerifier::new()),
            adapter,
            SelfPlayConfig::default(),
        );

        let result = loop_.run_cycle("");
        assert!(result.verification.correct);
        assert!(result.collected);
        assert_eq!(loop_.sample_count(), 1);
        assert_eq!(loop_.stats().cycles, 1);
        assert_eq!(loop_.stats().verified_correct, 1);
    }

    #[test]
    fn self_play_loop_multiple_cycles() {
        let proposer_handler = Box::new(StubHandler {
            response: r#"{"prompt": "What is 1+1?", "expected": "2", "difficulty": 0.1}"#
                .to_string(),
            confidence: 0.9,
        });
        let solver_handler = Box::new(StubHandler {
            response: "The answer is 2.".to_string(),
            confidence: 0.95,
        });

        let tmp = tempfile::tempdir().unwrap();
        let adapter = LoRAAdapterManager::with_config(tmp.path().to_path_buf(), 10000, false);

        let config = SelfPlayConfig {
            max_cycles_per_run: 5,
            ..Default::default()
        };

        let mut loop_ = SelfPlayLoop::new(
            TaskProposer::ungrounded(proposer_handler),
            TaskSolver::new(solver_handler),
            Box::new(ExactMatchVerifier::new()),
            adapter,
            config,
        );

        let results = loop_.run("");
        assert_eq!(results.len(), 5);
        assert!(results.iter().all(|r| r.verification.correct));
        assert_eq!(loop_.sample_count(), 5);
    }

    #[test]
    fn self_play_loop_triggers_adapter_update() {
        let proposer_handler = Box::new(StubHandler {
            response: r#"{"prompt": "What is 5+5?", "expected": "10", "difficulty": 0.2}"#
                .to_string(),
            confidence: 0.9,
        });
        let solver_handler = Box::new(StubHandler {
            response: "The answer is 10.".to_string(),
            confidence: 0.95,
        });

        let tmp = tempfile::tempdir().unwrap();
        let adapter = LoRAAdapterManager::with_config(tmp.path().to_path_buf(), 3, false);

        let config = SelfPlayConfig {
            max_cycles_per_run: 5,
            ..Default::default()
        };

        let mut loop_ = SelfPlayLoop::new(
            TaskProposer::ungrounded(proposer_handler),
            TaskSolver::new(solver_handler),
            Box::new(ExactMatchVerifier::new()),
            adapter,
            config,
        );

        // Run 5 cycles — should trigger adapter update after 3 samples
        let results = loop_.run("");
        assert_eq!(results.len(), 5);
        assert!(results.iter().any(|r| r.adapter_updated));
        assert!(loop_.adapter_version() > 0);
    }

    #[test]
    fn self_play_loop_stops_on_consecutive_failures() {
        let proposer_handler = Box::new(StubHandler {
            response: r#"{"prompt": "What is 9+9?", "expected": "18", "difficulty": 0.3}"#
                .to_string(),
            confidence: 0.9,
        });
        // Solver always gives wrong answer
        let solver_handler = Box::new(StubHandler {
            response: "The answer is 42.".to_string(),
            confidence: 0.5,
        });

        let tmp = tempfile::tempdir().unwrap();
        let adapter = LoRAAdapterManager::with_config(tmp.path().to_path_buf(), 10000, false);

        let config = SelfPlayConfig {
            max_cycles_per_run: 10,
            ..Default::default()
        };

        let mut loop_ = SelfPlayLoop::new(
            TaskProposer::ungrounded(proposer_handler),
            TaskSolver::new(solver_handler),
            Box::new(ExactMatchVerifier::new()),
            adapter,
            config,
        );

        let results = loop_.run("");
        // Should stop after 3 consecutive failures (not all 10)
        assert!(results.len() <= 4);
        assert!(results.iter().all(|r| !r.verification.correct));
    }

    #[test]
    fn self_play_loop_export_training_data() {
        let proposer_handler = Box::new(StubHandler {
            response: r#"{"prompt": "What is 7+7?", "expected": "14", "difficulty": 0.25}"#
                .to_string(),
            confidence: 0.9,
        });
        let solver_handler = Box::new(StubHandler {
            response: "The answer is 14.".to_string(),
            confidence: 0.95,
        });

        let tmp = tempfile::tempdir().unwrap();
        let adapter = LoRAAdapterManager::with_config(tmp.path().to_path_buf(), 10000, false);

        let mut loop_ = SelfPlayLoop::new(
            TaskProposer::ungrounded(proposer_handler),
            TaskSolver::new(solver_handler),
            Box::new(ExactMatchVerifier::new()),
            adapter,
            SelfPlayConfig::default(),
        );

        loop_.run_cycle("");
        loop_.run_cycle("");

        let data = loop_.export_training_data(false);
        assert!(!data.is_empty());
        assert_eq!(data.lines().count(), 2);
    }

    #[test]
    fn self_play_loop_task_type_rotation() {
        let proposer_handler = Box::new(StubHandler {
            response: r#"{"prompt": "test", "expected": "test", "difficulty": 0.5}"#.to_string(),
            confidence: 0.9,
        });
        let solver_handler = Box::new(StubHandler {
            response: "test".to_string(),
            confidence: 0.9,
        });

        let tmp = tempfile::tempdir().unwrap();
        let adapter = LoRAAdapterManager::with_config(tmp.path().to_path_buf(), 10000, false);

        let config = SelfPlayConfig {
            max_cycles_per_run: 1,
            task_types: TaskType::all().to_vec(),
            ..Default::default()
        };

        let mut loop_ = SelfPlayLoop::new(
            TaskProposer::ungrounded(proposer_handler),
            TaskSolver::new(solver_handler),
            Box::new(ExactMatchVerifier::new()),
            adapter,
            config,
        );

        // Run 5 cycles and check task type rotation
        let r1 = loop_.run_cycle("");
        let r2 = loop_.run_cycle("");
        let r3 = loop_.run_cycle("");
        let r4 = loop_.run_cycle("");
        let r5 = loop_.run_cycle("");

        assert_eq!(r1.task.task_type, TaskType::CodeGeneration);
        assert_eq!(r2.task.task_type, TaskType::ToolDispatch);
        assert_eq!(r3.task.task_type, TaskType::Reasoning);
        assert_eq!(r4.task.task_type, TaskType::Memory);
        assert_eq!(r5.task.task_type, TaskType::Creative);
    }

    #[test]
    fn self_play_stats_success_by_type() {
        let mut stats = SelfPlayStats::default();

        let make = |tt: TaskType, correct: bool| CycleResult {
            task: SelfPlayTask {
                prompt: "test".to_string(),
                task_type: tt,
                expected: "x".to_string(),
                difficulty: 0.5,
                grounding: "test".to_string(),
            },
            solution: Solution {
                output: "x".to_string(),
                confidence: 0.9,
                tier: "stub".to_string(),
                duration_ms: 1,
            },
            verification: VerificationResult {
                correct,
                score: if correct { 1.0 } else { 0.0 },
                feedback: String::new(),
                verifier: "test".to_string(),
            },
            collected: true,
            adapter_updated: false,
            duration_ms: 1,
        };

        stats.record(&make(TaskType::CodeGeneration, true));
        stats.record(&make(TaskType::CodeGeneration, true));
        stats.record(&make(TaskType::CodeGeneration, false));
        stats.record(&make(TaskType::Reasoning, true));

        let cg = stats.success_by_type.get("code_generation").unwrap();
        assert_eq!(cg.0, 2); // correct
        assert_eq!(cg.1, 3); // total

        let r = stats.success_by_type.get("reasoning").unwrap();
        assert_eq!(r.0, 1);
        assert_eq!(r.1, 1);
    }

    #[test]
    fn self_play_stats_accuracy_trend() {
        let mut stats = SelfPlayStats::default();
        let make = |correct: bool| CycleResult {
            task: SelfPlayTask {
                prompt: "test".to_string(),
                task_type: TaskType::Reasoning,
                expected: "x".to_string(),
                difficulty: 0.5,
                grounding: "test".to_string(),
            },
            solution: Solution {
                output: "x".to_string(),
                confidence: 0.9,
                tier: "stub".to_string(),
                duration_ms: 1,
            },
            verification: VerificationResult {
                correct,
                score: if correct { 1.0 } else { 0.0 },
                feedback: String::new(),
                verifier: "test".to_string(),
            },
            collected: true,
            adapter_updated: false,
            duration_ms: 1,
        };

        for _ in 0..5 {
            stats.record(&make(true));
        }
        assert_eq!(stats.accuracy_trend.len(), 5);
        assert!(stats.accuracy_trend.iter().all(|&v| v == 1.0));
    }

    #[test]
    fn self_play_stats_avg_difficulty() {
        let mut stats = SelfPlayStats::default();
        let make = |diff: f32| CycleResult {
            task: SelfPlayTask {
                prompt: "test".to_string(),
                task_type: TaskType::Reasoning,
                expected: "x".to_string(),
                difficulty: diff,
                grounding: "test".to_string(),
            },
            solution: Solution {
                output: "x".to_string(),
                confidence: 0.9,
                tier: "stub".to_string(),
                duration_ms: 1,
            },
            verification: VerificationResult {
                correct: true,
                score: 1.0,
                feedback: String::new(),
                verifier: "test".to_string(),
            },
            collected: true,
            adapter_updated: false,
            duration_ms: 1,
        };

        stats.record(&make(0.2));
        stats.record(&make(0.4));
        stats.record(&make(0.6));
        assert!((stats.avg_difficulty - 0.4).abs() < 0.01);
    }

    #[test]
    fn parse_task_json() {
        let task = parse_task(
            r#"{"prompt": "test prompt", "expected": "test answer", "difficulty": 0.7}"#,
            TaskType::CodeGeneration,
        )
        .unwrap();
        assert_eq!(task.prompt, "test prompt");
        assert_eq!(task.expected, "test answer");
        assert!((task.difficulty - 0.7).abs() < 0.01);
    }

    #[test]
    fn parse_task_difficulty_clamped() {
        let task = parse_task(
            r#"{"prompt": "test", "expected": "", "difficulty": 5.0}"#,
            TaskType::Reasoning,
        )
        .unwrap();
        assert!((task.difficulty - 1.0).abs() < 0.01);
    }

    #[test]
    fn parse_verification_json() {
        let result = parse_verification(r#"{"correct": false, "score": 0.3, "feedback": "wrong"}"#);
        assert!(!result.correct);
        assert!((result.score - 0.3).abs() < 0.01);
        assert_eq!(result.feedback, "wrong");
    }

    #[test]
    fn parse_verification_fallback() {
        let result = parse_verification("This solution is correct.");
        assert!(result.correct);
    }

    #[test]
    fn cycle_result_serialization() {
        let result = CycleResult {
            task: SelfPlayTask {
                prompt: "test".to_string(),
                task_type: TaskType::Reasoning,
                expected: "answer".to_string(),
                difficulty: 0.5,
                grounding: "test".to_string(),
            },
            solution: Solution {
                output: "answer".to_string(),
                confidence: 0.9,
                tier: "stub".to_string(),
                duration_ms: 42,
            },
            verification: VerificationResult {
                correct: true,
                score: 1.0,
                feedback: String::new(),
                verifier: "exact_match".to_string(),
            },
            collected: true,
            adapter_updated: false,
            duration_ms: 100,
        };
        let json = serde_json::to_string(&result).unwrap();
        let back: CycleResult = serde_json::from_str(&json).unwrap();
        assert_eq!(back.task.prompt, "test");
        assert!(back.verification.correct);
    }
}
