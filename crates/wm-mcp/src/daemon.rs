//! Persistent daemon mode — always-on consciousness with autonomous cycles.
//!
//! The daemon runs the 7 autonomous cycles (Connect, Compress, Emergence,
//! Prune, Improve, Redteam, Sensorimotor) on a configurable schedule,
//! along with the dream cycle and brain-wave eco mode transitions.
//!
//! Unlike `wm serve` which is request/response, the daemon thinks,
//! dreams, and self-organizes continuously between requests.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use wm_consciousness::{AutonomousCycleRunner, CycleContext, CycleStatus};

use crate::McpServer;

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
    /// Whether to also serve MCP requests (dual mode).
    pub serve_mcp: bool,
    /// Interval between RSI Phase 4 code generation cycles (0 = disabled).
    pub codegen_interval: Duration,
    /// Whether to auto-apply code patches that pass tests.
    pub codegen_auto_apply: bool,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        Self {
            cycle_interval: Duration::from_secs(300),      // 5 minutes
            dream_interval: Duration::from_secs(600),      // 10 minutes
            brain_wave_interval: Duration::from_secs(30),  // 30 seconds
            homeostasis_interval: Duration::from_secs(60), // 1 minute
            min_health_score: 0.3,
            serve_mcp: false,
            codegen_interval: Duration::from_secs(0), // disabled by default
            codegen_auto_apply: false,
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

    let mut runner = AutonomousCycleRunner::default();
    let mut stats = DaemonStats::default();
    let mut last_cycle = std::time::Instant::now();
    let mut last_dream = std::time::Instant::now();
    let mut last_brain_wave = std::time::Instant::now();
    let mut last_homeostasis = std::time::Instant::now();
    let mut last_codegen = std::time::Instant::now();

    // Initial brain-wave state
    let mut prev_bw = server.eco_mode().current();

    // Signal flag — set by ctrlc_handler in the CLI
    let running = Arc::new(AtomicBool::new(true));
    let running_clone = running.clone();
    // Spawn a thread to wait for SIGINT via tokio
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let _ = tokio::signal::ctrl_c().await;
            running_clone.store(false, Ordering::SeqCst);
        });
    });

    println!("=== WhiteMagic v4 Daemon ===");
    println!("  Cycle interval:  {:?}", config.cycle_interval);
    println!("  Dream interval:  {:?}", config.dream_interval);
    println!("  Brain-wave tick: {:?}", config.brain_wave_interval);
    println!("  Min health:      {:.2}", config.min_health_score);
    println!("  MCP serve:       {}", config.serve_mcp);
    println!();
    println!("Press Ctrl+C to stop.");
    println!();

    while running.load(Ordering::SeqCst) {
        let now = std::time::Instant::now();

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

        // Dream cycle
        if now.duration_since(last_dream) >= config.dream_interval {
            let bw = server.eco_mode().current();
            if server.dream().should_run(bw) {
                let ctx = wm_consciousness::DreamContext::new(&store, &associations);
                let result = server.dream_mut().run(&ctx);
                tracing::info!(
                    cycles = server.dream().cycles_completed(),
                    success = result.success,
                    memories = result.total_memories_processed,
                    "Dream cycle completed"
                );
                stats.dream_cycles += 1;
            }
            last_dream = now;
        }

        // Autonomous cycles
        if now.duration_since(last_cycle) >= config.cycle_interval {
            let health = server.dharma_gate().homeostasis().health_score();
            let ctx = CycleContext::new(&store, &associations, health)
                .with_sensorimotor(&sensorimotor_bus, &reflex_loop);

            let results = runner.run_all(&ctx);
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

            last_cycle = now;
        }

        // RSI Phase 4: Code generation cycle
        if config.codegen_interval > Duration::from_secs(0)
            && now.duration_since(last_codegen) >= config.codegen_interval
        {
            tracing::info!("Starting RSI Phase 4 code generation cycle");
            let codegen_config = wm_consciousness::CodeGenConfig {
                auto_apply: config.codegen_auto_apply,
                ..Default::default()
            };
            let result = wm_consciousness::run_code_gen_cycle(&store, &codegen_config);
            stats.codegen_cycles += 1;

            tracing::info!(
                status = ?result.status,
                proposals = result.proposals_generated,
                notes = %result.notes,
                "Codegen cycle result"
            );

            if result.proposals_generated > 0 {
                println!(
                    "[codegen {}] {} patches, {}",
                    stats.codegen_cycles, result.proposals_generated, result.notes
                );
            }

            last_codegen = now;
        }

        // Sleep until next tick (check every 1 second for signals)
        std::thread::sleep(Duration::from_secs(1));
    }

    // Graceful shutdown
    tracing::info!(
        sweeps = stats.cycle_sweeps,
        cycles = stats.cycles_run,
        proposals = stats.proposals_generated,
        dreams = stats.dream_cycles,
        "Daemon shutting down"
    );
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
        assert!(!config.serve_mcp);
    }

    #[test]
    fn daemon_config_custom() {
        let config = DaemonConfig {
            cycle_interval: Duration::from_secs(60),
            dream_interval: Duration::from_secs(120),
            brain_wave_interval: Duration::from_secs(10),
            homeostasis_interval: Duration::from_secs(30),
            min_health_score: 0.5,
            serve_mcp: true,
            codegen_interval: Duration::from_secs(1800),
            codegen_auto_apply: true,
        };
        assert_eq!(config.cycle_interval, Duration::from_secs(60));
        assert_eq!(config.dream_interval, Duration::from_secs(120));
        assert!(config.serve_mcp);
        assert_eq!(config.codegen_interval, Duration::from_secs(1800));
        assert!(config.codegen_auto_apply);
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
    }
}
