//! Persistent daemon mode — always-on consciousness with autonomous cycles.
//!
//! The daemon runs the 7 autonomous cycles (Connect, Compress, Emergence,
//! Prune, Improve, Redteam, Sensorimotor) on a configurable schedule,
//! along with the dream cycle and brain-wave eco mode transitions.
//!
//! Unlike `wm serve` which is request/response, the daemon thinks,
//! dreams, and self-organizes continuously between requests.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::time::Duration;

use wm_bicameral::{
    ExactMatchVerifier, LoRAAdapterManager, ScenarioEngine, ScenarioEvaluator, SelfPlayConfig,
    SelfPlayLoop, TaskProposer, TaskSolver, world_model_from_env,
};
use wm_cognitive::{AutonomousCycleRunner, CycleContext, CycleStatus, CycleType};

use crate::McpServer;

/// Current unix time in seconds.
fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

/// Persist the daemon-owned `LearnedCycleStrategy` next to the other
/// mutable-state JSON files. Shared by the periodic checkpoint and
/// graceful shutdown so both paths write the same file.
fn save_learned_cycles(runner: &AutonomousCycleRunner, store_dir: &std::path::Path) {
    if let Some(learned) = runner.learned() {
        let path = store_dir.join("mutable_learned_cycles.json");
        match serde_json::to_string_pretty(learned) {
            Ok(json) => {
                if let Err(e) = std::fs::write(&path, json) {
                    tracing::warn!(error = %e, "Failed to save LearnedCycleStrategy");
                } else {
                    tracing::info!("Saved LearnedCycleStrategy to disk");
                }
            }
            Err(e) => tracing::warn!(error = %e, "Failed to serialize LearnedCycleStrategy"),
        }
    }
}

/// Run a fallible closure that may panic, recovering with a logged error.
///
/// Hardening: a panic inside one autonomous component must not take down
/// the whole daemon — the watchdog recovers, logs, and the loop continues.
#[allow(clippy::single_match_else)]
fn resilient<T>(component: &str, f: impl FnOnce() -> T) -> Option<T> {
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)) {
        Ok(value) => Some(value),
        Err(_) => {
            tracing::error!(
                component,
                "Component panicked — recovered by daemon watchdog, continuing"
            );
            None
        }
    }
}

/// Configuration for the daemon's cycle schedule.
#[derive(Debug, Clone)]
pub struct DaemonConfig {
    /// Interval between full cycle sweeps (all 7 cycles).
    pub cycle_interval: Duration,
    /// Interval between dream cycle runs.
    pub dream_interval: Duration,
    /// Interval between brain-wave recompute ticks.
    pub brain_wave_interval: Duration,
    /// Interval between homeostasis refreshes.
    pub homeostasis_interval: Duration,
    /// Minimum health score to run cycles.
    pub min_health_score: f32,
    /// Interval between RSI Phase 4 code generation cycles (0 = disabled).
    pub codegen_interval: Duration,
    /// Whether to auto-apply code patches that pass tests.
    pub codegen_auto_apply: bool,
    /// Interval between dedicated Research cycles (0 = run with regular cycle sweep).
    pub research_interval: Duration,
    /// Interval between self-play training cycles (0 = disabled).
    pub selfplay_interval: Duration,
    /// Maximum time the main loop may go without a tick before the watchdog
    /// declares it stalled and forces a restart (0 = watchdog disabled).
    pub watchdog_timeout: Duration,
    /// Interval between mutable-state checkpoints (0 = disabled; graceful
    /// shutdown still saves). A SIGKILL loses learning since the last
    /// checkpoint rather than since process start.
    pub checkpoint_interval: Duration,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        Self {
            cycle_interval: Duration::from_secs(300),      // 5 minutes
            dream_interval: Duration::from_secs(600),      // 10 minutes
            brain_wave_interval: Duration::from_secs(30),  // 30 seconds
            homeostasis_interval: Duration::from_secs(60), // 1 minute
            min_health_score: 0.3,
            codegen_interval: Duration::from_secs(0), // disabled by default
            codegen_auto_apply: false,
            research_interval: Duration::from_secs(0), // 0 = run with regular cycle sweep
            selfplay_interval: Duration::from_secs(0), // 0 = disabled
            watchdog_timeout: Duration::from_secs(60), // 1 minute without a tick = stalled
            checkpoint_interval: Duration::from_secs(300), // 5 minutes
        }
    }
}

/// Daemon statistics — tracks what the daemon has been doing.
#[derive(Debug, Default)]
pub struct DaemonStats {
    /// Total cycle sweeps completed.
    pub cycle_sweeps: u64,
    /// Total cycles run (across all types).
    pub cycles_run: u64,
    /// Total proposals generated.
    pub proposals_generated: u64,
    /// Total cycles suspended (non-novel output).
    pub cycles_suspended: u64,
    /// Total dream cycles completed.
    pub dream_cycles: u64,
    /// Total brain-wave transitions.
    pub brain_wave_transitions: u64,
    /// Total RSI Phase 4 code generation cycles.
    pub codegen_cycles: u64,
    /// Total code patches applied.
    pub codegen_patches_applied: u64,
    /// Total dedicated Research cycles run.
    pub research_cycles: u64,
    /// Total hypotheses generated by Research cycles.
    pub research_hypotheses: u64,
    /// Total self-play training cycles run.
    pub selfplay_cycles: u64,
    /// Total training samples collected by self-play.
    pub selfplay_samples: u64,
    /// Total LoRA adapter updates from self-play.
    pub selfplay_adapter_updates: u64,
}

/// Run the persistent daemon.
///
/// This function blocks until the process receives SIGINT or SIGTERM.
/// It runs autonomous cycles, dream cycles, and brain-wave management
/// on their respective schedules.
pub fn run_daemon(server: &mut McpServer, config: &DaemonConfig) -> anyhow::Result<()> {
    tracing::info!(
        "Starting WhiteMagic daemon — cycle_interval={:?}, dream_interval={:?}",
        config.cycle_interval,
        config.dream_interval
    );

    let store = server.store_arc();
    let associations = server.associations().clone();
    let sensorimotor_bus = server.sensorimotor_bus().clone();
    let reflex_loop = server.reflex_loop().clone();

    let mut runner =
        AutonomousCycleRunner::default().with_learned(wm_core::LearnedCycleStrategy::new());

    // Load LearnedCycleStrategy from disk (Phase 6 persistence)
    let store_dir = store.path();
    let cycle_strategy_path = store_dir.join("mutable_learned_cycles.json");
    if cycle_strategy_path.exists() {
        if let Ok(json) = std::fs::read_to_string(&cycle_strategy_path) {
            if let Ok(learned) = serde_json::from_str::<wm_core::LearnedCycleStrategy>(&json) {
                runner.set_learned(learned);
                tracing::info!("Loaded LearnedCycleStrategy from disk");
            }
        }
    }

    let mut stats = DaemonStats::default();
    let mut last_cycle = std::time::Instant::now();
    let mut last_dream = std::time::Instant::now();
    let mut last_brain_wave = std::time::Instant::now();
    let mut last_homeostasis = std::time::Instant::now();
    let mut last_codegen = std::time::Instant::now();
    let mut last_research = std::time::Instant::now();
    let mut last_selfplay = std::time::Instant::now();
    let mut last_checkpoint = std::time::Instant::now();

    // Build imagination engine for Research cycle and dream cycle integration
    let world_model = world_model_from_env();
    let evaluator = ScenarioEvaluator::with_defaults();
    let scenario_engine = ScenarioEngine::with_defaults(world_model, evaluator);
    tracing::info!(
        left = scenario_engine.world_model().left_name(),
        right = ?scenario_engine.world_model().right_name(),
        "Imagination engine initialized for daemon"
    );

    // Initial brain-wave state
    let mut prev_bw = server.eco_mode().current();

    // Signal flag — set by ctrlc_handler in the CLI
    let running = Arc::new(AtomicBool::new(true));
    let running_clone = running.clone();
    // Spawn a thread to wait for SIGINT or SIGTERM. SIGTERM is the
    // standard shutdown signal for Docker/systemd deployments; handling
    // it gracefully (flush karma + save learned state) prevents data
    // loss on `docker stop` / `systemctl stop`.
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            #[cfg(unix)]
            {
                let mut sigterm =
                    tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
                        .expect("failed to register SIGTERM handler");
                tokio::select! {
                    _ = tokio::signal::ctrl_c() => {
                        tracing::info!("SIGINT received — initiating graceful shutdown");
                    }
                    _ = sigterm.recv() => {
                        tracing::info!("SIGTERM received — initiating graceful shutdown");
                    }
                }
            }
            #[cfg(not(unix))]
            {
                let _ = tokio::signal::ctrl_c().await;
                tracing::info!("SIGINT received — initiating graceful shutdown");
            }
            running_clone.store(false, Ordering::SeqCst);
        });
    });

    println!("=== WhiteMagic Daemon ===");
    println!("  Cycle interval:  {:?}", config.cycle_interval);
    println!("  Dream interval:  {:?}", config.dream_interval);
    println!("  Brain-wave tick: {:?}", config.brain_wave_interval);
    println!("  Min health:      {:.2}", config.min_health_score);
    if config.research_interval > Duration::from_secs(0) {
        println!("  Research interval: {:?}", config.research_interval);
    }
    if config.selfplay_interval > Duration::from_secs(0) {
        println!("  Self-play interval: {:?}", config.selfplay_interval);
    }
    if config.watchdog_timeout > Duration::from_secs(0) {
        println!(
            "  Watchdog:        {:?} (force-restart on stall)",
            config.watchdog_timeout
        );
    }
    if config.checkpoint_interval > Duration::from_secs(0) {
        println!("  Checkpoint:      {:?}", config.checkpoint_interval);
    }
    println!();
    println!("Press Ctrl+C to stop.");
    println!();

    // ── Watchdog ──────────────────────────────────────────────────────────
    // A dedicated thread watches the main loop's heartbeat. If the loop
    // stops ticking (stalled cycle, deadlock, runaway blocking call), the
    // watchdog logs CRITICAL, gives the loop a grace window to run its
    // graceful shutdown path, then force-exits so a supervisor (Docker
    // restart / systemd Restart=always) brings the daemon back.
    let last_tick = Arc::new(AtomicU64::new(now_secs()));
    let hung = Arc::new(AtomicBool::new(false));
    if config.watchdog_timeout > Duration::from_secs(0) {
        let last_tick = last_tick.clone();
        let hung = hung.clone();
        let timeout = config.watchdog_timeout;
        let check_interval = Duration::from_secs(1).min(timeout);
        std::thread::spawn(move || {
            loop {
                std::thread::sleep(check_interval);
                let last = last_tick.load(Ordering::Relaxed);
                let elapsed = now_secs().saturating_sub(last);
                if elapsed >= timeout.as_secs().max(1) {
                    tracing::error!(
                        stalled_for_secs = elapsed,
                        timeout_secs = timeout.as_secs(),
                        "Daemon watchdog: main loop stalled — forcing shutdown for supervisor restart"
                    );
                    hung.store(true, Ordering::SeqCst);
                    // Grace window: main loop may still be responsive enough to
                    // save state; after this, hard-exit regardless.
                    std::thread::sleep(Duration::from_secs(10));
                    std::process::exit(1);
                }
            }
        });
    }

    while running.load(Ordering::SeqCst) && !hung.load(Ordering::SeqCst) {
        let now = std::time::Instant::now();
        // Heartbeat — tells the watchdog the loop is alive
        last_tick.store(now_secs(), Ordering::Relaxed);

        // Brain-wave recompute
        if now.duration_since(last_brain_wave) >= config.brain_wave_interval {
            let new_bw = server.eco_mode_mut().recompute();
            if new_bw != prev_bw {
                tracing::info!(brain_wave = %new_bw, "Brain-wave transition");
                stats.brain_wave_transitions += 1;
                prev_bw = new_bw;
            }
            last_brain_wave = now;
        }

        // Homeostasis refresh
        if now.duration_since(last_homeostasis) >= config.homeostasis_interval {
            server.refresh_homeostasis();
            server.refresh_self_model();
            last_homeostasis = now;
        }

        // Dream cycle (with imagination engine for counterfactual replay;
        // S7: Yama attached so dream-phase writes — the distillation in
        // phase_narrative — share the live write budget with the tool
        // path, scaled by health and the current brain wave)
        if now.duration_since(last_dream) >= config.dream_interval {
            let bw = server.eco_mode().current();
            if server.dream().should_run(bw) {
                // Owned Arc handle: the context shares the live Yama
                // budget instance without borrowing the server, so
                // dream_mut() below stays free to mutate.
                let yama = server.resource_rules_arc();
                let ctx = wm_cognitive::DreamContext::new(&store, &associations)
                    .with_imagination(&scenario_engine)
                    .with_yama(yama.as_ref(), server.dharma_gate().homeostasis(), bw);
                if let Some(result) = resilient("dream_cycle", || server.dream_mut().run(&ctx)) {
                    tracing::info!(
                        cycles = server.dream().cycles_completed(),
                        success = result.success,
                        memories = result.total_memories_processed,
                        "Dream cycle completed"
                    );
                    stats.dream_cycles += 1;
                }
            }
            last_dream = now;
        }

        // Autonomous cycles (with imagination engine for Research cycle)
        if now.duration_since(last_cycle) >= config.cycle_interval {
            let health = server.dharma_gate().homeostasis().health_score();
            let ctx = CycleContext::new(&store, &associations, health)
                .with_sensorimotor(&sensorimotor_bus, &reflex_loop)
                .with_imagination(&scenario_engine)
                .with_dynamic_galaxies(server.dynamic_galaxies());

            if let Some(results) = resilient("cycle_sweep", || runner.run_all(&ctx)) {
                stats.cycle_sweeps += 1;

                for result in &results {
                    stats.cycles_run += 1;
                    stats.proposals_generated += result.proposals_generated as u64;
                    if result.status == CycleStatus::Suspended {
                        stats.cycles_suspended += 1;
                    }

                    let status_icon = match result.status {
                        CycleStatus::Completed => "OK",
                        CycleStatus::NoProposals => "--",
                        CycleStatus::Suspended => "~~",
                        CycleStatus::SkippedHealth => "SKIP",
                        CycleStatus::SkippedTimeBudget => "TIME",
                        CycleStatus::Error => "ERR",
                    };

                    tracing::info!(
                        cycle = result.cycle.name(),
                        status = status_icon,
                        proposals = result.proposals_generated,
                        duration_ms = result.duration_ms,
                        notes = %result.notes,
                        "Cycle result"
                    );
                }

                // WS-4: Proactive Improvement Surfacing — persist Improve
                // proposals as Codex memories with rsi:proposal:active tags so
                // `improve.proposals` can surface them. (Previously done on the
                // request path in the MCP server; moved here with the cycle
                // scheduler.)
                for result in &results {
                    for proposal in &result.improvements {
                        let content = format!(
                            "## Improvement Proposal\n\n\
                             **Category:** {}\n\n\
                             **Severity:** {}\n\n\
                             **Target:** {}\n\n\
                             **Problem:** {}\n\n\
                             **Recommended action:** {}\n\n\
                             **Pattern count:** {}",
                            proposal.category,
                            proposal.severity,
                            proposal.target,
                            proposal.problem,
                            proposal.recommended_action,
                            proposal.pattern_count,
                        );
                        let mut memory = wm_memory::Memory::new(wm_core::Galaxy::Codex, content);
                        let signature = format!(
                            "{}:{}:{}",
                            proposal.category, proposal.target, proposal.severity
                        );
                        memory.metadata.tags = vec![
                            "rsi:proposal".to_string(),
                            "rsi:proposal:active".to_string(),
                            format!("rsi:proposal:sig:{signature}"),
                            format!("rsi:severity:{}", proposal.severity),
                            format!("rsi:category:{}", proposal.category),
                            format!("rsi:tool:{}", proposal.target),
                        ];
                        memory.metadata.source = "auto".to_string();
                        memory.metadata.source_trust = 0.8;
                        memory.metadata.importance = match proposal.severity.as_str() {
                            "high" => 0.9,
                            "medium" => 0.6,
                            _ => 0.3,
                        };
                        if let Err(e) = store.put(wm_core::Galaxy::Codex, &memory) {
                            tracing::warn!("Failed to store proposal memory: {e}");
                        }
                    }
                }

                // Print summary
                println!(
                    "[sweep {}] {} cycles, {} proposals, {} suspended, {} dreams, {} bw-transitions",
                    stats.cycle_sweeps,
                    stats.cycles_run,
                    stats.proposals_generated,
                    stats.cycles_suspended,
                    stats.dream_cycles,
                    stats.brain_wave_transitions
                );
            }

            last_cycle = now;
        }

        // RSI Phase 4: Code generation cycle
        if config.codegen_interval > Duration::from_secs(0)
            && now.duration_since(last_codegen) >= config.codegen_interval
        {
            tracing::info!("Starting RSI Phase 4 code generation cycle");
            let codegen_config = wm_cognitive::CodeGenConfig {
                auto_apply: config.codegen_auto_apply,
                ..Default::default()
            };
            let result = resilient("codegen_cycle", || {
                wm_cognitive::run_code_gen_cycle(&store, &codegen_config)
            });
            if result.is_some() {
                stats.codegen_cycles += 1;
            }

            tracing::info!(
                status = ?result.as_ref().map(|r| &r.status),
                proposals = result.as_ref().map_or(0, |r| r.proposals_generated),
                notes = %result.as_ref().map_or("panicked", |r| r.notes.as_str()),
                "Codegen cycle result"
            );

            if let Some(result) = result {
                if result.proposals_generated > 0 {
                    println!(
                        "[codegen {}] {} patches, {}",
                        stats.codegen_cycles, result.proposals_generated, result.notes
                    );
                }
            }

            last_codegen = now;
        }

        // Dedicated Research cycle (imagination engine)
        if config.research_interval > Duration::from_secs(0)
            && now.duration_since(last_research) >= config.research_interval
        {
            let health = server.dharma_gate().homeostasis().health_score();
            let ctx =
                CycleContext::new(&store, &associations, health).with_imagination(&scenario_engine);

            let result = resilient("research_cycle", || {
                runner.run_cycle(CycleType::Research, &ctx)
            });
            if let Some(result) = result {
                stats.research_cycles += 1;
                stats.research_hypotheses += result.proposals_generated as u64;

                tracing::info!(
                    status = ?result.status,
                    hypotheses = result.proposals_generated,
                    duration_ms = result.duration_ms,
                    notes = %result.notes,
                    "Dedicated Research cycle completed"
                );

                if result.proposals_generated > 0 {
                    println!(
                        "[research {}] {} hypotheses, {}",
                        stats.research_cycles, result.proposals_generated, result.notes
                    );
                }
            }

            last_research = now;
        }

        // Self-play training cycle
        if config.selfplay_interval > Duration::from_secs(0)
            && now.duration_since(last_selfplay) >= config.selfplay_interval
        {
            // Build self-play loop with LLM handlers from env (falls back to stubs)
            let store_path = store.path();
            let adapter_dir = store_path.join("lora_adapters");
            let (proposer_handler, solver_handler) = wm_bicameral::self_play_handlers_from_env();
            let proposer = TaskProposer::ungrounded(proposer_handler);
            let solver = TaskSolver::new(solver_handler);
            let verifier = Box::new(ExactMatchVerifier::new());
            let adapter = LoRAAdapterManager::with_config(adapter_dir, 1000, false);
            let mut sp_loop = SelfPlayLoop::new(
                proposer,
                solver,
                verifier,
                adapter,
                SelfPlayConfig::default(),
            );

            // Gather memory context for grounding
            let mut context_parts = Vec::new();
            for galaxy in wm_core::Galaxy::memory_galaxies() {
                if let Ok(mems) = store.scan(galaxy, 5) {
                    for mem in mems.iter().take(2) {
                        context_parts.push(format!("- {}", mem.content));
                    }
                }
            }
            let context = context_parts.join("\n");

            if let Some(results) = resilient("selfplay_cycle", || sp_loop.run(&context)) {
                let sp_stats = sp_loop.stats();
                stats.selfplay_cycles += results.len() as u64;
                stats.selfplay_samples += sp_stats.samples_collected;
                stats.selfplay_adapter_updates += sp_stats.adapter_updates;

                let correct = results.iter().filter(|r| r.verification.correct).count();
                tracing::info!(
                    cycles = results.len(),
                    correct,
                    samples = sp_stats.samples_collected,
                    adapter_version = sp_loop.adapter_version(),
                    "Self-play training cycle completed"
                );

                println!(
                    "[selfplay {}] {} cycles, {} correct, {} samples, adapter v{}",
                    stats.selfplay_cycles,
                    results.len(),
                    correct,
                    sp_stats.samples_collected,
                    sp_loop.adapter_version()
                );
            }

            last_selfplay = now;
        }

        // Periodic mutable-state checkpoint — closes the SIGKILL-loses-
        // learning window to `checkpoint_interval` instead of process lifetime.
        if config.checkpoint_interval > Duration::from_secs(0)
            && now.duration_since(last_checkpoint) >= config.checkpoint_interval
        {
            save_learned_cycles(&runner, store_dir);
            server.save_mutable_state();
            tracing::info!("Mutable-state checkpoint written");
            last_checkpoint = now;

            // Heal index drift accumulated since startup: session tools,
            // dream consolidation, and research cycles write LMDB without
            // per-write indexing, so a long-running daemon would otherwise
            // hide new memories from search until the next restart.
            if let Some(engine) = server.search_engine() {
                match wm_memory::reindex::heal_index_drift(server.store(), engine) {
                    Ok(Some(report)) => tracing::info!(
                        galaxies = report.galaxies.len(),
                        indexed = report.indexed,
                        "Periodic index-drift heal rebuilt drifted galaxies"
                    ),
                    Ok(None) => {}
                    Err(e) => tracing::warn!(
                        error = %e,
                        "Periodic index-drift heal failed — run 'wm reindex --store <path>' manually"
                    ),
                }
            }
        }

        // Sleep until next tick (check every 1 second for signals)
        std::thread::sleep(Duration::from_secs(1));
    }

    // If the watchdog declared the daemon hung, report the failure so a
    // supervisor (Docker restart / systemd Restart=always) restarts us.
    if hung.load(Ordering::SeqCst) {
        tracing::error!(
            "Daemon watchdog triggered — shutting down with failure for supervisor restart"
        );
    }

    // Graceful shutdown — save mutable structures to disk
    tracing::info!(
        sweeps = stats.cycle_sweeps,
        cycles = stats.cycles_run,
        proposals = stats.proposals_generated,
        dreams = stats.dream_cycles,
        "Daemon shutting down"
    );

    save_learned_cycles(&runner, store_dir);

    // Flush karma ledger to persist any pending batched entries
    if let Some(karma) = server.karma_ledger() {
        if let Err(e) = karma.flush() {
            tracing::warn!(error = %e, "Failed to flush karma ledger on shutdown");
        } else {
            tracing::info!("Karma ledger flushed on shutdown");
        }
    }

    // Save server-owned mutable structures (GanaRegistry, DynamicGalaxyRegistry, LearnedDreamCycle)
    server.save_mutable_state();

    println!();
    println!("=== Daemon Shutdown ===");
    println!("  Cycle sweeps:     {}", stats.cycle_sweeps);
    println!("  Total cycles:     {}", stats.cycles_run);
    println!("  Proposals:        {}", stats.proposals_generated);
    println!("  Suspended:        {}", stats.cycles_suspended);
    println!("  Dream cycles:     {}", stats.dream_cycles);
    println!("  BW transitions:   {}", stats.brain_wave_transitions);
    println!("  Codegen cycles:   {}", stats.codegen_cycles);
    println!("  Patches applied:  {}", stats.codegen_patches_applied);
    if stats.research_cycles > 0 {
        println!("  Research cycles:  {}", stats.research_cycles);
        println!("  Hypotheses:       {}", stats.research_hypotheses);
    }
    if stats.selfplay_cycles > 0 {
        println!("  Self-play cycles: {}", stats.selfplay_cycles);
        println!("  SP samples:       {}", stats.selfplay_samples);
        println!("  SP adapter upds:  {}", stats.selfplay_adapter_updates);
    }

    if hung.load(Ordering::SeqCst) {
        anyhow::bail!("daemon watchdog triggered — main loop stalled; restart for recovery")
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn daemon_config_default() {
        let config = DaemonConfig::default();
        assert_eq!(config.cycle_interval, Duration::from_secs(300));
        assert_eq!(config.dream_interval, Duration::from_secs(600));
        assert_eq!(config.brain_wave_interval, Duration::from_secs(30));
        assert!((config.min_health_score - 0.3).abs() < 0.01);
        assert_eq!(config.watchdog_timeout, Duration::from_secs(60));
    }

    #[test]
    fn daemon_config_custom() {
        let config = DaemonConfig {
            cycle_interval: Duration::from_secs(60),
            dream_interval: Duration::from_secs(120),
            brain_wave_interval: Duration::from_secs(10),
            homeostasis_interval: Duration::from_secs(30),
            min_health_score: 0.5,
            codegen_interval: Duration::from_secs(1800),
            codegen_auto_apply: true,
            research_interval: Duration::from_secs(600),
            selfplay_interval: Duration::from_secs(900),
            watchdog_timeout: Duration::from_secs(120),
            checkpoint_interval: Duration::from_secs(180),
        };
        assert_eq!(config.cycle_interval, Duration::from_secs(60));
        assert_eq!(config.dream_interval, Duration::from_secs(120));
        assert_eq!(config.codegen_interval, Duration::from_secs(1800));
        assert!(config.codegen_auto_apply);
        assert_eq!(config.research_interval, Duration::from_secs(600));
        assert_eq!(config.selfplay_interval, Duration::from_secs(900));
        assert_eq!(config.watchdog_timeout, Duration::from_secs(120));
        assert_eq!(config.checkpoint_interval, Duration::from_secs(180));
    }

    #[test]
    fn daemon_config_default_checkpoint_is_five_minutes() {
        let config = DaemonConfig::default();
        assert_eq!(config.checkpoint_interval, Duration::from_secs(300));
    }

    #[test]
    fn resilient_recovers_from_panic() {
        let result = resilient("test", || -> u32 { panic!("boom") });
        assert!(result.is_none());
    }

    #[test]
    fn resilient_returns_value() {
        let result = resilient("test", || 42u32);
        assert_eq!(result, Some(42));
    }

    #[test]
    fn daemon_stats_default() {
        let stats = DaemonStats::default();
        assert_eq!(stats.cycle_sweeps, 0);
        assert_eq!(stats.cycles_run, 0);
        assert_eq!(stats.proposals_generated, 0);
        assert_eq!(stats.dream_cycles, 0);
        assert_eq!(stats.brain_wave_transitions, 0);
        assert_eq!(stats.codegen_cycles, 0);
        assert_eq!(stats.codegen_patches_applied, 0);
        assert_eq!(stats.selfplay_cycles, 0);
        assert_eq!(stats.selfplay_samples, 0);
        assert_eq!(stats.selfplay_adapter_updates, 0);
    }
}
