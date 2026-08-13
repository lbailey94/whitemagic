//! `WhiteMagic` CLI — `wm` command
//!
//! Entry point for the `WhiteMagic` v5 CLI tool.

use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "wm", version = "5.8.0", about = "WhiteMagic v5 — Cognitive OS")]
struct Cli {
    /// Path to a TOML config file. Overrides default config location.
    #[arg(long, global = true)]
    config: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run the MCP server (JSON-RPC over stdio)
    Serve {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Max requests served per connection before refusing (0 = unlimited, default 10000)
        #[arg(long, default_value_t = wm_mcp::DEFAULT_MAX_REQUESTS_PER_SESSION)]
        max_requests: u64,
        /// Time-windowed rate cap (requests/minute, 0 = unlimited, default 600)
        #[arg(long, default_value_t = wm_mcp::DEFAULT_RATE_LIMIT_RPM)]
        rate_limit: u64,
        /// Open the tantivy index read-only: no exclusive lock, writes fail
        /// with a clear error. Lets multiple processes share the store.
        #[arg(long)]
        readonly: bool,
        /// Tool surface profile: full | curated | minimal. Curated exposes
        /// the memory-hierarchy surface (memory, session, claims,
        /// transactions); full exposes all tools. When omitted, the
        /// WM_TOOL_PROFILE / WM_TOOL_ALLOWLIST environment variables are
        /// used instead.
        #[arg(long)]
        profile: Option<String>,
    },
    /// Generate or show configuration
    Config {
        /// Print a sample config.toml to stdout
        #[arg(long)]
        sample: bool,
        /// Write a sample config.toml to the default config path
        #[arg(long)]
        init: bool,
        /// Path to the LMDB store directory (for --init)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Run the built-in quickstart demo
    Quickstart,
    /// Diagnose system issues
    Doctor {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Check LMDB integrity (scan all galaxies for corruption)
        #[arg(long)]
        check_integrity: bool,
        /// Repair corrupted entries (implies --check-integrity)
        #[arg(long)]
        repair: bool,
    },
    /// Show resource usage and brain-wave state
    Stats {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Show polyglot acceleration status
    Polyglot,
    /// Export collected training data for LoRA fine-tuning
    ExportTrainingData {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Output file path (default: stdout)
        #[arg(long)]
        output: Option<PathBuf>,
        /// Export format: jsonl, llama_cpp, or chat (default: jsonl)
        #[arg(long, default_value = "jsonl")]
        format: String,
        /// Include negative (failed verification) samples
        #[arg(long)]
        include_negative: bool,
    },
    /// Run as a persistent daemon — always-on consciousness with autonomous cycles
    Daemon {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Interval between full cycle sweeps in seconds (overrides config)
        #[arg(long)]
        cycle_interval: Option<u64>,
        /// Interval between dream cycle runs in seconds (overrides config)
        #[arg(long)]
        dream_interval: Option<u64>,
        /// Minimum health score to run cycles (overrides config)
        #[arg(long)]
        min_health: Option<f32>,
        /// Interval between RSI Phase 4 codegen cycles in seconds (0 = disabled)
        #[arg(long)]
        codegen_interval: Option<u64>,
        /// Auto-apply code patches that pass tests (dangerous)
        #[arg(long)]
        codegen_auto_apply: bool,
        /// Interval between dedicated Research cycles in seconds (0 = run with regular cycle sweep)
        #[arg(long)]
        research_interval: Option<u64>,
        /// Interval between self-play training cycles in seconds (0 = disabled)
        #[arg(long)]
        selfplay_interval: Option<u64>,
        /// Watchdog stall timeout in seconds (0 = disabled; force-restart on daemon hang)
        #[arg(long)]
        watchdog_timeout: Option<u64>,
    },
    /// Show current brain-wave state (shorthand for stats)
    BrainWave {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Migrate legacy v26 SQLite memories into the v5 LMDB store
    Migrate {
        /// Path to v26 galaxies directory (containing per-galaxy subdirs with whitemagic.db)
        #[arg(long)]
        v2_dir: Option<PathBuf>,
        /// Path to a single v26 SQLite database
        #[arg(long)]
        v2_db: Option<PathBuf>,
        /// Path to the v5 LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Dry run — report what would be migrated without writing
        #[arg(long)]
        dry_run: bool,
        /// Only migrate memories from this galaxy name (e.g. "codex")
        #[arg(long)]
        galaxy: Option<String>,
    },
    /// Rebuild the Tantivy full-text index from LMDB
    ///
    /// Purges stale index entries and skips binary/garbage content via the
    /// same sanitization gate used at write time. The current index directory
    /// is backed up automatically unless --no-backup is given.
    Reindex {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Skip the automatic backup of the current index directory
        #[arg(long)]
        no_backup: bool,
        /// Only reindex these galaxies (repeatable; default: all)
        #[arg(long)]
        galaxy: Vec<String>,
        /// Simulate: report what would be indexed without touching the index
        #[arg(long)]
        dry_run: bool,
    },
}

fn default_store_path() -> PathBuf {
    std::env::var("XDG_DATA_HOME").map_or_else(
        |_| {
            std::env::var("HOME").map_or_else(
                |_| PathBuf::from(".whitemagic"),
                |home| {
                    PathBuf::from(home)
                        .join(".local")
                        .join("share")
                        .join("whitemagic")
                },
            )
        },
        |xdg| PathBuf::from(xdg).join("whitemagic"),
    )
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    // Initialize logging (only to stderr — stdout is for JSON-RPC)
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .with_writer(std::io::stderr)
        .init();

    // Load configuration (config file + env overrides)
    let wm_config = wm_mcp::config::WmConfig::load(cli.config.as_ref());
    // Export config values to env vars so subsystems pick them up
    wm_config.export_to_env();

    match cli.command {
        Commands::Serve {
            store,
            max_requests,
            rate_limit,
            readonly,
            profile,
        } => {
            // Resolve the tool surface profile with explicit precedence:
            // WM_TOOL_ALLOWLIST > --profile flag > WM_TOOL_PROFILE > full.
            // The resolved name is exported so the server's
            // `tool_profile_from_env()` sees the winning value. Previously
            // the CLI unconditionally overwrote WM_TOOL_PROFILE with its
            // default, breaking the documented environment path.
            let resolved = wm_tools::profiles::resolve_tool_profile(
                profile.as_deref(),
                std::env::var("WM_TOOL_PROFILE").ok().as_deref(),
                std::env::var("WM_TOOL_ALLOWLIST").ok().as_deref(),
            );
            // `std::env::set_var` is unsafe in Rust 2024 (not thread-safe);
            // main() is single-threaded here, before any runtime is spawned.
            #[allow(unsafe_code)]
            unsafe {
                std::env::set_var("WM_TOOL_PROFILE", resolved.name);
            }
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");
            std::fs::create_dir_all(&lmdb_path)?;

            let dispatch_cfg = wm_dispatch::RateLimiterConfig::from_env();
            tracing::info!(
                global_rpm = dispatch_cfg.global_rpm,
                tool_rpm = dispatch_cfg.default_tool_rpm,
                burst = dispatch_cfg.burst_allowance,
                "Dispatch rate limits (WM_DISPATCH_* or defaults)"
            );

            tracing::info!("Starting MCP server, store: {}", lmdb_path.display());

            let mut server = match wm_mcp::McpServer::with_defaults_mode(&lmdb_path, readonly) {
                Ok(s) => s,
                Err(e) => {
                    tracing::warn!(
                        "Normal open failed ({e}). Attempting recovery with AutoRepairAndGrow..."
                    );
                    // Try recovery: open store with auto-repair + map size growth
                    let _recovered_store = wm_memory::open_with_recovery(
                        &lmdb_path,
                        1024 * 1024 * 1024,
                        wm_memory::RecoveryStrategy::AutoRepairAndGrow,
                    )?;
                    // Now retry server creation
                    wm_mcp::McpServer::with_defaults_mode(&lmdb_path, readonly)?
                }
            };

            // Boundary hardening: enforce per-session request budget
            server.set_request_budget(max_requests);
            tracing::info!(
                max_requests,
                "Request budget enforced — server refuses requests beyond the per-connection cap"
            );

            // Boundary hardening: time-windowed rate limit
            server.set_rate_limit(rate_limit);
            tracing::info!(
                rate_limit,
                "Rate limit enforced — bursts beyond {rate_limit} requests/min are throttled"
            );

            // Use tokio runtime for async event loop with brain-wave eco mode
            let rt = tokio::runtime::Runtime::new()?;
            rt.block_on(async { server.run_async().await })?;
            // run_async may exit on SIGTERM/SIGINT while a stdin read is still
            // parked on tokio's blocking thread pool; Runtime::drop would wait
            // for it indefinitely. Force shutdown with a bounded timeout instead.
            rt.shutdown_timeout(std::time::Duration::from_millis(500));
        }
        Commands::Quickstart => {
            let rt = tokio::runtime::Runtime::new()?;
            rt.block_on(async { run_quickstart().await })?;
        }
        Commands::Doctor {
            store,
            check_integrity,
            repair,
        } => {
            let issues = run_doctor(store, check_integrity, repair)?;
            if issues > 0 {
                std::process::exit(1);
            }
        }
        Commands::Stats { store } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");
            if !lmdb_path.exists() {
                println!(
                    "No store found at {}. Run 'wm serve' first.",
                    lmdb_path.display()
                );
                return Ok(());
            }
            // Read-only diagnostics — no exclusive index lock so this works
            // while the daemon (or another serve instance) holds the store.
            let server = wm_mcp::McpServer::with_defaults_mode(&lmdb_path, true)?;
            let eco = server.eco_mode();
            println!("=== Brain-Wave Eco Mode ===");
            println!("State: {}", eco.current());
            println!("Idle: {:.1}s", eco.idle_duration().as_secs_f64());
            println!("Total events: {}", eco.metrics().total_events());
            println!();
            println!("Subsystem flags:");
            let flags = eco.subsystems();
            println!("  memory_read:  {}", flags.memory_read);
            println!("  memory_write: {}", flags.memory_write);
            println!("  search:       {}", flags.search);
            println!("  karma:        {}", flags.karma);
            println!("  dharma:       {}", flags.dharma);
            println!("  citta:        {}", flags.citta);
            println!("  dream:        {}", flags.dream);
            println!("  embeddings:   {}", flags.embeddings);
            println!("  inference:    {}", flags.inference);
            println!();
            println!("=== Citta (Consciousness) ===");
            let citta = server.citta();
            println!("Heartbeats: {}", citta.heartbeats());
            println!("Coherence: {:.3}", citta.vector.coherence());
            println!("Valence: {:.3}", citta.vector.valence());
            println!("Magnitude: {:.3}", citta.vector.magnitude());
            if let Some(reading) = citta.last_coherence() {
                println!("Last significant reading: score={:.3}", reading.score);
            }
            println!();
            println!("=== Smarana (Retention) ===");
            println!("Score: {:.3}", citta.smarana.score());
            println!("Total recalls: {}", citta.smarana.total());
            println!();
            println!("=== Apotheosis (Self-Improvement) ===");
            println!("Score: {:.3}", citta.apotheosis.score());
            println!("Evaluations: {}", citta.apotheosis.evaluations());
            println!("Trend: {:.4}", citta.apotheosis.trend());
            println!("Improving: {}", citta.apotheosis.is_improving());
            println!();
            println!("=== Dream Cycle ===");
            let dream = server.dream();
            println!("Cycles completed: {}", dream.cycles_completed());
            println!("Consolidated: {}", dream.consolidation.consolidated());
            println!("Skipped: {}", dream.consolidation.skipped());
        }
        Commands::Polyglot => {
            run_polyglot();
        }
        Commands::ExportTrainingData {
            store,
            output,
            format,
            include_negative,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");
            if !lmdb_path.exists() {
                println!(
                    "No store found at {}. Run 'wm serve' first.",
                    lmdb_path.display()
                );
                return Ok(());
            }

            let server = match wm_mcp::McpServer::with_defaults_mode(&lmdb_path, true) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening server: {e}");
                    return Ok(());
                }
            };

            let bicameral = server.bicameral();
            let engine = bicameral
                .lock()
                .map_err(|e| anyhow::anyhow!("bicameral lock: {e}"))?;

            let data = if engine.has_router() {
                match format.as_str() {
                    "llama_cpp" => engine.export_training_data_llama_cpp(),
                    "chat" => engine.export_training_data_chat(),
                    _ => engine.export_training_data(include_negative),
                }
            } else {
                println!("No router attached — no training data available.");
                return Ok(());
            };

            if data.is_empty() {
                println!("No training data collected yet.");
                println!(
                    "Training data is collected during self-verification in the inference router."
                );
                return Ok(());
            }

            let sample_count = data.lines().count();
            match output {
                Some(path) => {
                    std::fs::write(&path, &data)?;
                    println!("Exported {sample_count} samples to {}", path.display());
                }
                None => {
                    println!("{data}");
                }
            }
        }
        Commands::Config {
            sample,
            init,
            store,
        } => {
            if sample {
                print!("{}", wm_mcp::config::WmConfig::sample_toml());
                return Ok(());
            }
            if init {
                let store_path = store.unwrap_or_else(|| wm_config.store_path());
                std::fs::create_dir_all(&store_path)?;
                let config_path = store_path.join("config.toml");
                if config_path.exists() {
                    println!("Config already exists at {}", config_path.display());
                    return Ok(());
                }
                std::fs::write(&config_path, wm_mcp::config::WmConfig::sample_toml())?;
                println!("Created sample config at {}", config_path.display());
                println!("Edit it to configure LLM endpoints, embedder, and daemon schedules.");
                return Ok(());
            }
            // No flags: show current effective config
            println!("# Effective WhiteMagic Configuration");
            println!("# (config file + env var overrides)\n");
            let toml_str =
                toml::to_string_pretty(&wm_config).unwrap_or_else(|e| format!("Error: {e}"));
            println!("{toml_str}");
            println!("# Store path: {}", wm_config.store_path().display());
        }
        Commands::Daemon {
            store,
            cycle_interval,
            dream_interval,
            min_health,
            codegen_interval,
            codegen_auto_apply,
            research_interval,
            selfplay_interval,
            watchdog_timeout,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");
            std::fs::create_dir_all(&lmdb_path)?;

            tracing::info!("Starting daemon, store: {}", lmdb_path.display());

            let mut server = match wm_mcp::McpServer::with_defaults(&lmdb_path) {
                Ok(s) => s,
                Err(e) => {
                    tracing::warn!(
                        "Normal open failed ({e}). Attempting recovery with AutoRepairAndGrow..."
                    );
                    let _recovered_store = wm_memory::open_with_recovery(
                        &lmdb_path,
                        1024 * 1024 * 1024,
                        wm_memory::RecoveryStrategy::AutoRepairAndGrow,
                    )?;
                    wm_mcp::McpServer::with_defaults(&lmdb_path)?
                }
            };

            // Start with config file values, then apply CLI overrides
            let mut daemon_cfg = wm_config.daemon_durations();
            if let Some(secs) = cycle_interval {
                daemon_cfg.cycle_interval = std::time::Duration::from_secs(secs);
            }
            if let Some(secs) = dream_interval {
                daemon_cfg.dream_interval = std::time::Duration::from_secs(secs);
            }
            if let Some(h) = min_health {
                daemon_cfg.min_health_score = h;
            }
            if let Some(secs) = codegen_interval {
                daemon_cfg.codegen_interval = std::time::Duration::from_secs(secs);
            }
            if codegen_auto_apply {
                daemon_cfg.codegen_auto_apply = true;
            }
            if let Some(secs) = research_interval {
                daemon_cfg.research_interval = std::time::Duration::from_secs(secs);
            }
            if let Some(secs) = selfplay_interval {
                daemon_cfg.selfplay_interval = std::time::Duration::from_secs(secs);
            }
            if let Some(secs) = watchdog_timeout {
                daemon_cfg.watchdog_timeout = std::time::Duration::from_secs(secs);
            }

            wm_mcp::daemon::run_daemon(&mut server, &daemon_cfg)?;
        }
        Commands::BrainWave { store } => {
            run_brain_wave(store);
        }
        Commands::Migrate {
            v2_dir,
            v2_db,
            store,
            dry_run,
            galaxy,
        } => {
            let store_path = store.unwrap_or_else(default_store_path);
            wm_mcp::migrate::run_migration(
                v2_dir.as_deref(),
                v2_db.as_deref(),
                &store_path,
                dry_run,
                galaxy.as_deref(),
            )?;
        }
        Commands::Reindex {
            store,
            no_backup,
            galaxy,
            dry_run,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_reindex(&store_path, !no_backup, &galaxy, dry_run)?;
        }
    }

    Ok(())
}

/// Rebuild the Tantivy index from LMDB (`wm reindex`).
fn run_reindex(
    store_path: &std::path::Path,
    backup: bool,
    galaxy_filter: &[String],
    dry_run: bool,
) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.exists() {
        anyhow::bail!(
            "No store found at {}. Run 'wm serve' first.",
            lmdb_path.display()
        );
    }
    let tantivy_path = wm_memory::reindex::tantivy_path_for(&lmdb_path);
    if !tantivy_path.exists() {
        return Err(wm_memory::reindex::missing_index_error(&lmdb_path).into());
    }

    if backup && !dry_run {
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| anyhow::anyhow!("clock error: {e}"))?
            .as_secs();
        let backup_path = lmdb_path.join(format!("tantivy.bak.{ts}"));
        std::fs::create_dir_all(&backup_path)?;
        copy_dir(&tantivy_path, &backup_path)?;
        println!("Backup written to {}", backup_path.display());
    }

    let store = wm_memory::MemoryStore::open_default(&lmdb_path)?;

    let scope = if galaxy_filter.is_empty() {
        "all galaxies".to_string()
    } else {
        format!("galaxies: {}", galaxy_filter.join(", "))
    };

    if dry_run {
        // Rebuild into a throwaway index in a temp dir — the live index is
        // never opened or modified.
        let tmp = std::env::temp_dir().join(format!("wm-reindex-dry-{}", std::process::id()));
        std::fs::create_dir_all(&tmp)?;
        let result = (|| -> anyhow::Result<wm_memory::IndexRebuildReport> {
            let search = wm_memory::SearchEngine::open(&tmp)?;
            Ok(wm_memory::rebuild_index(&store, &search, galaxy_filter)?)
        })();
        let _ = std::fs::remove_dir_all(&tmp);
        let report = result?;
        println!(
            "Dry run (live index untouched): scanned={} indexed={} skipped={} ({scope})",
            report.scanned, report.indexed, report.skipped
        );
        for g in &report.galaxies {
            if g.scanned > 0 || g.skipped > 0 {
                println!(
                    "  {:12} scanned={:7} indexed={:7} skipped={:5}",
                    g.galaxy, g.scanned, g.indexed, g.skipped
                );
            }
        }
        return Ok(());
    }

    let search = wm_memory::SearchEngine::open(&tantivy_path)?;
    println!(
        "Rebuilding Tantivy index from LMDB ({scope}) — this can take a minute on large stores..."
    );
    let report = wm_memory::rebuild_index(&store, &search, galaxy_filter)?;
    println!(
        "Rebuild complete: scanned={} indexed={} skipped={}",
        report.scanned, report.indexed, report.skipped
    );
    for g in &report.galaxies {
        if g.scanned > 0 || g.skipped > 0 {
            println!(
                "  {:12} scanned={:7} indexed={:7} skipped={:5}",
                g.galaxy, g.scanned, g.indexed, g.skipped
            );
        }
    }
    Ok(())
}

/// Recursively copy a directory (std has no built-in recursive copy).
fn copy_dir(src: &std::path::Path, dst: &std::path::Path) -> std::io::Result<()> {
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        let target = dst.join(entry.file_name());
        if ty.is_dir() {
            std::fs::create_dir_all(&target)?;
            copy_dir(&entry.path(), &target)?;
        } else {
            std::fs::copy(entry.path(), &target)?;
        }
    }
    Ok(())
}

fn run_doctor(store: Option<PathBuf>, check_integrity: bool, repair: bool) -> anyhow::Result<u32> {
    let store_path = store.unwrap_or_else(default_store_path);
    let lmdb_path = store_path.join("lmdb");
    let mut issues = 0u32;

    println!("=== WhiteMagic v5 Doctor ===");
    println!();

    // 1. LMDB store check
    if !lmdb_path.exists() {
        println!("[FAIL] LMDB store not found at {}", lmdb_path.display());
        println!("  Run 'wm serve' to initialize the store.");
        return Ok(1);
    }
    println!("[OK]   LMDB store: {}", lmdb_path.display());

    // 1a. Integrity check (if requested)
    if check_integrity || repair {
        println!();
        println!("--- Integrity Check ---");
        let server = match wm_mcp::McpServer::with_defaults_mode(&lmdb_path, true) {
            Ok(s) => s,
            Err(e) => {
                println!("[FAIL] Cannot open server: {e}");
                return Ok(1);
            }
        };
        let report = wm_memory::check_integrity(server.store())?;
        println!("{}", report.summary());
        for gi in &report.galaxies {
            if gi.corrupted > 0 {
                println!(
                    "  [WARN] {}: {} corrupted out of {} entries",
                    gi.galaxy, gi.corrupted, gi.total
                );
                issues += 1;
            } else if gi.total > 0 {
                println!("  [OK]   {}: {} entries, all valid", gi.galaxy, gi.total);
            }
        }

        if repair && !report.is_clean {
            println!();
            println!("--- Repair ---");
            // Drop the server to get exclusive access
            drop(server);
            // Open store directly for repair
            let mut store_obj = wm_memory::MemoryStore::open_default(&lmdb_path)?;
            let repair_report = wm_memory::repair(&mut store_obj, &lmdb_path)?;
            println!("  Quarantined: {} entries", repair_report.quarantined);
            println!(
                "  Indexes rebuilt: {} entries",
                repair_report.indexes_rebuilt
            );
            if let Some(ref path) = repair_report.quarantine_path {
                println!("  Quarantine file: {path}");
            }
            if let Some(ref path) = repair_report.backup_path {
                println!("  Backup: {path}");
            }
            println!("  {}", repair_report.integrity.summary());
        }
        println!();
    }

    let server = match wm_mcp::McpServer::with_defaults_mode(&lmdb_path, true) {
        Ok(s) => s,
        Err(e) => {
            println!("[FAIL] Cannot open server: {e}");
            return Ok(1);
        }
    };

    // 2. Galaxy health
    let mut total_memories = 0usize;
    let mut galaxies_with_data = 0usize;
    let mut galaxy_details = Vec::new();
    for galaxy in wm_core::Galaxy::all() {
        let count = server.store().count(galaxy).unwrap_or(0);
        if count > 0 {
            total_memories += count;
            galaxies_with_data += 1;
            galaxy_details.push(format!("  {}={}", galaxy.db_name(), count));
        }
    }
    println!("[OK]   Galaxies with data: {galaxies_with_data}, total memories: {total_memories}");
    if !galaxy_details.is_empty() {
        for detail in &galaxy_details {
            println!("{detail}");
        }
    }

    // 3. Tantivy search index
    let tantivy_path = lmdb_path.join("tantivy");
    if tantivy_path.exists() {
        println!("[OK]   Tantivy index: {}", tantivy_path.display());
    } else {
        println!("[WARN] Tantivy index not found (search will be unavailable)");
        issues += 1;
    }

    // 4. Brain-wave state
    let eco = server.eco_mode();
    println!("[OK]   Brain-wave state: {}", eco.current());
    println!("       Idle: {:.1}s", eco.idle_duration().as_secs_f64());
    println!("       Total events: {}", eco.metrics().total_events());

    // 5. Subsystem flags
    let flags = eco.subsystems();
    println!("[OK]   Subsystem flags:");
    println!("       memory_read:  {}", flags.memory_read);
    println!("       memory_write: {}", flags.memory_write);
    println!("       search:       {}", flags.search);
    println!("       karma:        {}", flags.karma);
    println!("       dharma:       {}", flags.dharma);
    println!("       citta:        {}", flags.citta);
    println!("       dream:        {}", flags.dream);

    // 6. Citta coherence
    let citta = server.citta();
    let coherence = citta.vector.coherence();
    let coherence_status = if coherence >= 0.7 {
        "COHERENT"
    } else if coherence >= 0.3 {
        "MODERATE"
    } else {
        "LOW"
    };
    println!("[OK]   Citta coherence: {coherence:.3} ({coherence_status})");
    println!("       Valence: {:.3}", citta.vector.valence());
    println!("       Heartbeats: {}", citta.heartbeats());

    // 7. Dream cycle
    let dream = server.dream();
    println!(
        "[OK]   Dream cycle: {} completed, {} consolidated, {} skipped",
        dream.cycles_completed(),
        dream.consolidation.consolidated(),
        dream.consolidation.skipped()
    );

    // 8. Tool registry
    let registry = server.registry();
    let all_tools = registry.all();
    println!("[OK]   Tool registry: {} tools registered", all_tools.len());

    // 9. Karma chain integrity
    let karma_path = lmdb_path.join("data.mdb");
    if karma_path.exists() {
        println!("[OK]   Karma chain: LMDB data file present");
    }

    // 10. Conformal calibration health
    let conformal_path = store_path.join("conformal_store.json");
    if conformal_path.exists() {
        match std::fs::read_to_string(&conformal_path) {
            Ok(contents) => match serde_json::from_str::<serde_json::Value>(&contents) {
                Ok(json) => {
                    let mut store = wm_tools::expansion::conformal::ConformalStore::new();
                    match store.from_json(&json) {
                        Ok(()) => {
                            let clf = store.classifier.as_ref();
                            let reg = store.regressor.as_ref();
                            let aps = store.aps.as_ref();

                            let clf_ok = clf.is_some();
                            let reg_ok = reg.is_some();

                            println!(
                                "[{}] Conformal calibration: {}",
                                if clf_ok || reg_ok { "OK" } else { "WARN" },
                                conformal_path.display()
                            );
                            println!(
                                "       Classifier: {}, samples: {}",
                                if clf_ok {
                                    format!(
                                        "fitted (alpha={:.2})",
                                        clf.map_or(
                                            0.0,
                                            wm_conformal::SplitConformalClassifier::alpha
                                        )
                                    )
                                } else {
                                    "not fitted".into()
                                },
                                store.classifier_samples()
                            );
                            println!(
                                "       Regressor:  {}, samples: {}",
                                if reg_ok {
                                    format!(
                                        "fitted (alpha={:.2})",
                                        reg.map_or(
                                            0.0,
                                            wm_conformal::SplitConformalRegressor::alpha
                                        )
                                    )
                                } else {
                                    "not fitted".into()
                                },
                                store.regressor_samples()
                            );
                            println!(
                                "       APS:        {}",
                                if aps.is_some() {
                                    "fitted (adaptive prediction sets)"
                                } else {
                                    "not fitted"
                                }
                            );
                            if !clf_ok && !reg_ok {
                                if store.classifier_samples() > 0 || store.regressor_samples() > 0 {
                                    println!(
                                        "       [WARN] Calibration samples exist but nothing is fitted — run conformal.fit_classifier / conformal.fit_regressor, then conformal.export"
                                    );
                                    issues += 1;
                                } else {
                                    println!(
                                        "       [INFO] No calibration fitted yet — calibrate via conformal.fit_classifier / conformal.fit_regressor"
                                    );
                                }
                            }
                        }
                        Err(e) => {
                            println!("[WARN] Conformal state corrupt (parse failed: {e})");
                            issues += 1;
                        }
                    }
                }
                Err(e) => {
                    println!("[WARN] Conformal state unparseable: {e}");
                    issues += 1;
                }
            },
            Err(e) => {
                println!("[WARN] Cannot read conformal state: {e}");
                issues += 1;
            }
        }
    } else {
        println!("[INFO] No conformal calibration state persisted (conformal_store.json)");
        println!("       Calibrate via conformal.fit_classifier/fit_regressor, then persist:");
        println!("       conformal.export > {}", conformal_path.display());
    }

    // 11. Live calibration drift health (from persisted self-model metrics)
    //     conformal.monitor / simulation.calibrate feed empirical coverage and
    //     Brier scores into the self-model; the server persists it on shutdown
    //     to `<store_root>/self_model.json`. The doctor reads the latest
    //     values and applies the same alert thresholds as the alert engine.
    let self_model_path = store_path.join("self_model.json");
    if self_model_path.exists() {
        match std::fs::read_to_string(&self_model_path) {
            Ok(contents) => match serde_json::from_str::<serde_json::Value>(&contents) {
                Ok(json) => {
                    let samples = json
                        .get("samples")
                        .and_then(serde_json::Value::as_array)
                        .cloned()
                        .unwrap_or_default();
                    for (key, name, warning, critical, higher_is_better) in [
                        ("conformal_coverage", "Conformal coverage", 0.85, 0.80, true),
                        ("brier_score", "Brier score", 0.15, 0.30, false),
                    ] {
                        let values: Vec<f64> = samples
                            .iter()
                            .filter_map(|s| {
                                if s.get("kind").and_then(serde_json::Value::as_str) == Some(key) {
                                    s.get("value").and_then(serde_json::Value::as_f64)
                                } else {
                                    None
                                }
                            })
                            .collect();
                        if values.is_empty() {
                            println!("[INFO] {name}: no samples recorded yet");
                            println!(
                                "       Run conformal.monitor (coverage) / simulation.calibrate (Brier) to build history"
                            );
                            continue;
                        }
                        let latest = *values.last().unwrap_or(&0.0);
                        let bad = if higher_is_better {
                            latest < critical
                        } else {
                            latest > critical
                        };
                        let warn = if higher_is_better {
                            latest < warning
                        } else {
                            latest > warning
                        };
                        println!(
                            "[{}] {name}: latest {latest:.3} ({} samples, {} trend)",
                            if bad {
                                "FAIL"
                            } else if warn {
                                "WARN"
                            } else {
                                "OK"
                            },
                            values.len(),
                            if values.len() >= 2 {
                                let a = values[values.len() - 2];
                                if latest > a {
                                    "rising"
                                } else if latest < a {
                                    "falling"
                                } else {
                                    "flat"
                                }
                            } else {
                                "n/a"
                            }
                        );
                        if bad {
                            println!(
                                "       [WARN] Below/above the {critical} critical threshold — calibration may have drifted; run conformal.monitor to evaluate live coverage"
                            );
                            issues += 1;
                        }
                    }
                }
                Err(e) => {
                    println!("[WARN] Self-model state unparseable: {e}");
                    issues += 1;
                }
            },
            Err(e) => {
                println!("[WARN] Cannot read self-model state: {e}");
                issues += 1;
            }
        }
    } else {
        println!("[INFO] No self-model state persisted (self_model.json)");
        println!(
            "       Feed conformal.monitor / simulation.calibrate, then let the server save on shutdown"
        );
    }

    println!();
    println!("=== Doctor Summary ===");
    if issues == 0 {
        println!("All systems healthy.");
    } else {
        println!("{issues} issue(s) found — exit code 1.");
    }

    Ok(issues)
}

async fn run_quickstart() -> anyhow::Result<()> {
    let store_path = default_store_path();
    let lmdb_path = store_path.join("lmdb");
    std::fs::create_dir_all(&lmdb_path)?;

    println!("=== WhiteMagic v5 Quickstart ===");
    println!();
    println!("Initializing store at {}...", lmdb_path.display());

    let mut server = wm_mcp::McpServer::with_defaults(&lmdb_path)?;

    // Step 1: Create memories — dispatched through the server's pipeline so
    // the Tantivy index is populated. (Direct LMDB writes left the index
    // empty and step 3's search returned nothing on a fresh store.)
    println!();
    println!("--- Step 1: Create memories ---");

    let memories = [
        (
            "Rust is a systems programming language focused on safety and speed.",
            vec!["programming", "rust"],
        ),
        (
            "LMDB is a lightning-fast embedded key-value store using mmap.",
            vec!["database", "lmdb"],
        ),
        (
            "Tantivy is a full-text search engine written in Rust.",
            vec!["search", "rust"],
        ),
    ];

    for (content, tags) in &memories {
        let create_request = serde_json::json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "wm",
                "arguments": {
                    "route": "memory.create",
                    "args": {"galaxy": "codex", "content": content, "tags": tags}
                }
            }
        });
        let response = server.handle_request(&create_request.to_string()).await;
        let resp: serde_json::Value = serde_json::from_str(&response).unwrap_or_default();
        if let Some(text) = resp
            .get("result")
            .and_then(|r| r.get("content"))
            .and_then(|c| c.get(0))
            .and_then(|c| c.get("text"))
            .and_then(|t| t.as_str())
        {
            if let Ok(created) = serde_json::from_str::<serde_json::Value>(text) {
                if created.get("status").and_then(|s| s.as_str()) == Some("success") {
                    let id = created.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("  Created: [{id}] \"{}\"", &content[..50]);
                    continue;
                }
            }
        }
        println!("  (Failed to create: \"{}\")", &content[..50]);
    }

    {
        let store = server.store();
        // Step 2: List memories
        println!();
        println!("--- Step 2: List memories in Codex galaxy ---");
        let list = store.scan(wm_core::Galaxy::Codex, 100)?;
        println!("  Total: {} memories", list.len());
    }

    // Step 3: Search (via MCP protocol to reuse the server's already-open SearchEngine)
    println!();
    println!("--- Step 3: Full-text search for 'rust' ---");
    let search_request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "wm",
            "arguments": {
                "route": "memory.search",
                "args": {"query": "rust", "limit": 10}
            }
        }
    });
    let response = server.handle_request(&search_request.to_string()).await;
    let resp: serde_json::Value = serde_json::from_str(&response).unwrap_or_default();
    if let Some(result) = resp.get("result") {
        if let Some(content) = result
            .get("content")
            .and_then(|c| c.get(0))
            .and_then(|c| c.get("text"))
        {
            if let Ok(text) =
                serde_json::from_str::<serde_json::Value>(content.as_str().unwrap_or("{}"))
            {
                if let Some(results) = text.get("results").and_then(|r| r.as_array()) {
                    println!("  Found {} results:", results.len());
                    for r in results.iter().take(10) {
                        let score = r
                            .get("score")
                            .and_then(serde_json::Value::as_f64)
                            .unwrap_or(0.0);
                        let galaxy = r.get("galaxy").and_then(|g| g.as_str()).unwrap_or("?");
                        let preview = r
                            .get("content_preview")
                            .and_then(|c| c.as_str())
                            .unwrap_or("");
                        println!(
                            "    score={:.3} galaxy={} preview=\"{}\"",
                            score,
                            galaxy,
                            &preview.chars().take(60).collect::<String>()
                        );
                    }
                } else {
                    println!("  (Search returned no results — index may still be building)");
                }
            } else {
                println!("  (Search returned unexpected response format)");
            }
        }
    } else if let Some(error) = resp.get("error") {
        let msg = error
            .get("message")
            .and_then(|m| m.as_str())
            .unwrap_or("unknown");
        println!("  (Search error: {msg})");
    } else {
        println!("  (Search returned no response)");
    }

    // Step 4: Galaxy stats
    println!();
    println!("--- Step 4: Galaxy statistics ---");
    {
        let store = server.store();
        for galaxy in wm_core::Galaxy::all() {
            let count = store.count(galaxy).unwrap_or(0);
            if count > 0 {
                println!("  {}: {} memories", galaxy.db_name(), count);
            }
        }
    }

    // Step 5: Consciousness dashboard
    println!();
    println!("--- Step 5: Consciousness dashboard ---");
    let eco = server.eco_mode();
    println!("  Brain-wave: {}", eco.current());
    let citta = server.citta();
    println!("  Citta coherence: {:.3}", citta.vector.coherence());
    println!("  Citta valence: {:.3}", citta.vector.valence());

    // Step 6: Tool count
    println!();
    println!("--- Step 6: Available tools ---");
    let registry = server.registry();
    let all_tools = registry.all();
    println!("  {} tools registered", all_tools.len());
    println!("  Sample tools:");
    for tool in all_tools.iter().take(10) {
        println!("    {} ({:?})", tool.name(), tool.gana());
    }
    if all_tools.len() > 10 {
        println!("    ... and {} more", all_tools.len() - 10);
    }

    println!();
    println!("=== Quickstart Complete ===");
    println!("Store: {}", lmdb_path.display());
    println!("Run 'wm serve' to start the MCP server.");
    println!("Run 'wm stats' to see the full consciousness dashboard.");
    println!("Run 'wm doctor' for a health check.");

    Ok(())
}

fn run_polyglot() {
    println!("=== WhiteMagic v5 Polyglot Status ===");
    println!();

    let runtimes: &[(&str, &str, &str)] = &[
        (
            "Julia",
            "jlrs",
            "Embedded via jlrs (in-process, no subprocess)",
        ),
        (
            "Haskell",
            "FFI",
            "Compiled to native library, called via C ABI",
        ),
        (
            "Zig",
            "C ABI",
            "Compiled to native library, called via C ABI",
        ),
        (
            "Koka",
            "C ABI",
            "Compiled to native library, called via C ABI",
        ),
    ];

    for (name, bridge, desc) in runtimes {
        let status = check_polyglot_runtime(name);
        let icon = if status { "[OK]" } else { "[--]" };
        println!("{icon} {name} ({bridge})");
        println!("     {desc}");
        if status {
            println!("     Status: Available");
        } else {
            println!(
                "     Status: Not built (run with --features wm-polyglot/{})",
                name.to_lowercase()
            );
        }
        println!();
    }

    println!("=== Polyglot Summary ===");
    let available = runtimes
        .iter()
        .filter(|(n, _, _)| check_polyglot_runtime(n))
        .count();
    println!("{}/{} runtimes available", available, runtimes.len());
    println!();
    println!("To build with polyglot support:");
    println!("  cargo build --release --features wm-polyglot/julia");
    println!("  cargo build --release --features wm-mcp/python");
}

const fn check_polyglot_runtime(name: &str) -> bool {
    // Check if the polyglot crate was compiled with this runtime
    // For now, all are false since wm-polyglot is Phase 7
    let _ = name;
    false
}

fn run_brain_wave(store: Option<PathBuf>) {
    let store_path = store.unwrap_or_else(default_store_path);
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.exists() {
        println!(
            "No store found at {}. Run 'wm serve' first.",
            lmdb_path.display()
        );
        return;
    }

    let server = match wm_mcp::McpServer::with_defaults_mode(&lmdb_path, true) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error opening server: {e}");
            return;
        }
    };

    let eco = server.eco_mode();
    println!("=== Brain-Wave State ===");
    println!("State: {}", eco.current());
    println!("Idle: {:.1}s", eco.idle_duration().as_secs_f64());
    println!("Total events: {}", eco.metrics().total_events());
    println!();

    let flags = eco.subsystems();
    println!("Subsystem flags:");
    println!("  memory_read:  {}", flags.memory_read);
    println!("  memory_write: {}", flags.memory_write);
    println!("  search:       {}", flags.search);
    println!("  karma:        {}", flags.karma);
    println!("  dharma:       {}", flags.dharma);
    println!("  citta:        {}", flags.citta);
    println!("  dream:        {}", flags.dream);
    println!("  embeddings:   {}", flags.embeddings);
    println!("  inference:    {}", flags.inference);
    println!();

    let citta = server.citta();
    println!("Citta coherence: {:.3}", citta.vector.coherence());
    println!("Citta valence:   {:.3}", citta.vector.valence());
    println!("Heartbeats:      {}", citta.heartbeats());
}
