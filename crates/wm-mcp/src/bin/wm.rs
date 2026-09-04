//! `WhiteMagic` CLI — `wm` command
//!
//! Entry point for the `WhiteMagic` v5 CLI tool.

use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "wm", version = env!("CARGO_PKG_VERSION"), about = "WhiteMagic — local-first memory and session continuity for coding agents")]
struct Cli {
    /// Path to a TOML config file. Overrides default config location.
    #[arg(long, global = true)]
    config: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run the MCP server (JSON-RPC over stdio or HTTP/SSE)
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
        /// Tool surface profile: full | curated | minimal. When omitted,
        /// `wm serve` uses curated (the product surface) unless
        /// WM_TOOL_PROFILE / WM_TOOL_ALLOWLIST is set. Full is the
        /// archive/research surface.
        #[arg(long)]
        profile: Option<String>,
        /// Transport: stdio (default) or sse
        #[arg(long, default_value = "stdio")]
        transport: String,
        /// Bind address for --transport sse (e.g. 127.0.0.1:18789)
        #[arg(long)]
        bind: Option<String>,
        /// Federate over backing stores instead of opening one: comma-separated
        /// name=endpoint pairs (e.g. "dev=http://127.0.0.1:18790,vault=http://127.0.0.1:18789").
        /// One wm meta-tool; read routes fan out across scopes, everything else
        /// pins to the explicit scope= or the home scope (WM_PROJECT).
        #[arg(long)]
        federate: Option<String>,
        /// Join the Sangha mesh: enable the TCP/UDP transport (R0). Identity
        /// comes from WM_MESH_KEY; `sangha.mesh.*` tools live on --profile full.
        #[arg(long)]
        mesh: bool,
        /// Bind address for the mesh transport (default 0.0.0.0:7369 or
        /// WM_MESH_BIND; a 0.0.0.0 bind announces 127.0.0.1 to peers).
        #[arg(long)]
        mesh_bind: Option<String>,
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
        /// Audit live network posture by observation (no store required):
        /// read the socket tables, attribute sockets to WhiteMagic processes
        /// and the fleet transport, flag non-LAN egress (board item 2).
        #[arg(long)]
        network: bool,
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
        /// Mutable-state checkpoint interval in seconds (0 = disabled; default 300)
        #[arg(long)]
        checkpoint_interval: Option<u64>,
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
    /// Ingest documents and session transcripts into a knowledge store
    ///
    /// Harvests markdown/text/jsonl files under --source, chunks them, and
    /// writes them into the store with provenance tags. Idempotent via a
    /// per-file SHA-256 ledger at <store>/ingest_ledger.jsonl — re-runs are
    /// no-ops for unchanged files. Credential-shaped filenames (.env*, keys)
    /// are never ingested. See planning/SESSION_Knowledge_Ingest.md.
    Ingest {
        /// Source directory to harvest
        #[arg(long)]
        source: PathBuf,
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Dry run — report without writing or creating the store
        #[arg(long)]
        dry_run: bool,
        /// Only consider the first N files (walk order)
        #[arg(long, default_value_t = 0)]
        limit: usize,
        /// Override target galaxy (default: sessions for transcripts,
        /// research for documents)
        #[arg(long)]
        galaxy: Option<String>,
    },
    /// Bridge opencode session data into whitemagic (digest or export)
    ///
    /// Reads an opencode session DB (live local, or another seat's lane
    /// snapshot .tar.gz — the first .db member is extracted to a cache) and
    /// either prints a per-session digest (markdown or JSON) or emits
    /// `session.import`-compatible JSONL. Read-only on the source DB; a
    /// single deferred read transaction keeps scans consistent against a
    /// live opencode without blocking it. Ids are UUIDv5-deterministic, so
    /// re-importing an export is an idempotent upsert.
    Opencode {
        #[command(subcommand)]
        command: OpencodeCommands,
    },
    /// Seal the store directory with an HMAC-SHA256 integrity manifest
    ///
    /// Computes a digest for every file in the store and writes `seal.json`.
    /// A per-install secret key is generated at `.seal_key` on first use.
    /// Run `wm verify` afterwards to detect tampering or corruption.
    ///
    /// This is corruption / casual-tamper detection, not a root of trust.
    /// An adversary who can replace both `.seal_key` and `seal.json` wins.
    Seal {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Verify the store directory against a previously written seal manifest
    ///
    /// Recomputes HMAC digests and reports any mismatched, missing, or extra
    /// files. Exits with code 1 if verification fails.
    Verify {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Merkle-anchor the store's record attestations (Track F Slice A, D5)
    ///
    /// Verifies every attestation in the `attestations` DBI, computes a
    /// Merkle root over the validly-signed set (valid + stale + missing —
    /// staleness is lifecycle, not forgery; only a bad signature excludes
    /// a leaf), and prints the report as JSON. With --publish, appends the
    /// report to a chained external JSONL log (prev_hash per record, same
    /// pattern as karma.anchor's publish_path — the log is the persistence;
    /// put it somewhere versioned for out-of-band verifiability).
    ///
    /// Takes the LMDB lock — stop the store's server unit first (same
    /// posture as `wm trust`). Exits with code 1 when any signature is
    /// invalid: tamper evidence is loud, never advisory.
    Anchor {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Append the anchor report to this chained JSONL log
        #[arg(long)]
        publish: Option<PathBuf>,
    },
    /// Back up the FULL store (LMDB + indexes + all JSON state) for disaster recovery
    ///
    /// Copies the entire store root into a timestamped backup directory and
    /// writes a SHA256SUMS manifest. Stop the server first: a live LMDB
    /// environment can produce a torn copy. This is disaster-recovery
    /// backup, not the transaction snapshot/rollback feature (which is
    /// in-store and short-lived). Seal/verify protects integrity of files as
    /// sealed; it does not recover data — this command does.
    Backup {
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Destination parent directory (default: ~/whitemagic-backups)
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Restore the full store from a `wm backup` archive
    ///
    /// Verifies the backup's SHA256SUMS manifest, then replaces the target
    /// store root. Refuses to overwrite an existing store unless --force is
    /// given. The Tantivy index travels inside the backup; run 'wm reindex'
    /// only if doctor reports index drift after restore.
    Restore {
        /// Path to the backup directory created by 'wm backup'
        #[arg(long)]
        backup: PathBuf,
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Overwrite an existing store directory
        #[arg(long)]
        force: bool,
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
    /// Repair gate-failing memory content in place (V8 drift fix)
    ///
    /// Control characters are replaced with spaces and the sanitization gate
    /// re-run; rows that pass are rewritten under the same id and indexed.
    /// Majority-binary content is left untouched (the documented permanent
    /// reserve). DRY-RUN by default — take a `wm backup` before --apply;
    /// this rewrites LMDB rows.
    RepairContent {
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Only repair these galaxies (repeatable; default: all memory galaxies)
        #[arg(long)]
        galaxy: Vec<String>,
        /// Apply the repair (default: dry-run report only)
        #[arg(long)]
        apply: bool,
    },
    /// Session continuity over LMDB directly — CLI parity for the MCP
    /// session routes (board item 1): the continuity promise must not
    /// depend on MCP transport health. Shares the exact tool
    /// implementations the server dispatches to.
    Session {
        #[command(subcommand)]
        command: SessionCommands,
    },
    /// Survey or correct memory source-trust provenance (V8.1 groundwork)
    ///
    /// source_trust semantics: 1.0 = user-confirmed, 0.7 = tool-ingested
    /// neutral, lower = unverified. Heritage ingests carry the defaults
    /// (user/1.0) and over-state trust — survey first, then correct a
    /// reviewed population before enabling WM_TRUST_WEIGHT.
    Trust {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        #[command(subcommand)]
        command: TrustCommand,
    },
}

#[derive(clap::Subcommand)]
enum OpencodeCommands {
    /// Print a per-session digest table (markdown, or --json) for this seat
    /// or a lane snapshot (--db path/to/opencode-snapshot-*.tar.gz)
    Digest {
        /// opencode session DB (default: ~/.local/share/opencode/opencode.db)
        #[arg(long)]
        db: Option<PathBuf>,
        /// Only sessions updated on/after YYYY-MM-DD (UTC)
        #[arg(long)]
        since: Option<String>,
        /// Emit JSON instead of the markdown table
        #[arg(long)]
        json: bool,
    },
    /// Emit session.import-compatible JSONL (session_start + session_turn)
    Export {
        /// opencode session DB (default: ~/.local/share/opencode/opencode.db)
        #[arg(long)]
        db: Option<PathBuf>,
        /// Only these sessions (id/slug prefix; repeatable)
        #[arg(long = "session")]
        session: Vec<String>,
        /// Write JSONL here instead of stdout
        #[arg(long)]
        out: Option<PathBuf>,
        /// Device tag embedded in titles and tags (default: this hostname)
        #[arg(long)]
        device: Option<String>,
    },
}

#[derive(clap::Subcommand)]
enum TrustCommand {
    /// Count memories by (source, trust) per galaxy — read-only
    Survey,
    /// Sessions-galaxy archaeology probe: authorship + turn shapes (Phase 4.5)
    Sessions,
    /// Re-stamp source_trust on a selected population (dry-run unless --apply)
    Correct {
        /// Match memories whose source equals this value (e.g. "user")
        #[arg(long)]
        source: Option<String>,
        /// Restrict to one galaxy (e.g. codex)
        #[arg(long)]
        galaxy: Option<String>,
        /// Only memories created before this RFC 3339 timestamp
        #[arg(long)]
        created_before: Option<String>,
        /// Only memories carrying this tag
        #[arg(long)]
        tag: Option<String>,
        /// New source_trust value, 0.0-1.0 (0.7 = tool-ingested neutral)
        #[arg(long)]
        set_trust: f32,
        /// Actually write (default: dry-run report only)
        #[arg(long)]
        apply: bool,
    },
}

/// Subcommands for `wm session` — each maps 1:1 onto an MCP session route
/// and carries its own `--store` override.
#[derive(Subcommand)]
enum SessionCommands {
    /// Start a new session (session.start parity)
    Start {
        /// Session title
        #[arg(long)]
        title: String,
        /// User identifier
        #[arg(long, default_value = "default")]
        user: String,
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Record a conversation turn (session.record parity)
    Record {
        /// Turn content
        #[arg(long)]
        content: String,
        /// Author role: user | ai
        #[arg(long, default_value = "user")]
        role: String,
        /// Turn type (message, decision, breakthrough, question, answer, code_change, error, summary, context)
        #[arg(long, default_value = "message")]
        turn_type: String,
        /// Importance 0.0-1.0
        #[arg(long, default_value_t = 0.5)]
        importance: f64,
        /// Target session id (default: most recent session)
        #[arg(long)]
        session_id: Option<String>,
        /// Memory id of an earlier turn this record corrects/replaces
        #[arg(long)]
        supersedes: Option<String>,
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Save a structured checkpoint (session.checkpoint parity)
    Checkpoint {
        /// Target session id (default: most recent session)
        #[arg(long)]
        session_id: Option<String>,
        /// Checkpoint label
        #[arg(long, default_value = "checkpoint")]
        label: String,
        /// Repository root for git auto-capture (default: WM_PROJECT_ROOT env)
        #[arg(long)]
        root: Option<String>,
        /// Manual commit hash (auto-captured from git when available)
        #[arg(long)]
        commit: Option<String>,
        /// Manual branch name
        #[arg(long)]
        branch: Option<String>,
        /// Whether the test suite was green at checkpoint time
        #[arg(long)]
        tests_green: Option<bool>,
        /// Ordered next-step strings for the next session (repeatable)
        #[arg(long = "next-queue")]
        next_queue: Vec<String>,
        /// Open concerns worth surfacing on resume (repeatable)
        #[arg(long = "open-flag")]
        open_flags: Vec<String>,
        /// Claimed scope (code.claim lease_id) that remains held
        #[arg(long)]
        lease_id: Option<String>,
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Recall where the previous session left off (session.continuity parity)
    Continuity {
        /// Number of prior turns to show
        #[arg(long, default_value_t = 10)]
        n: usize,
        /// Current session id to exclude
        #[arg(long)]
        session_id: Option<String>,
        /// Time-range floor (epoch seconds | RFC 3339 | YYYY-MM-DD)
        #[arg(long)]
        since: Option<String>,
        /// Time-range ceiling (epoch seconds | RFC 3339 | YYYY-MM-DD)
        #[arg(long)]
        until: Option<String>,
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
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

/// Best-effort hostname for bridge device tags.
fn detect_hostname() -> String {
    if let Ok(h) = std::env::var("HOSTNAME") {
        if !h.trim().is_empty() {
            return h.trim().to_string();
        }
    }
    for path in ["/proc/sys/kernel/hostname", "/etc/hostname"] {
        if let Ok(s) = std::fs::read_to_string(path) {
            let h = s.trim();
            if !h.is_empty() {
                return h.to_string();
            }
        }
    }
    "unknown".to_string()
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
            transport,
            bind,
            federate,
            mesh,
            mesh_bind,
        } => {
            // Federated gateway mode: one wm meta-tool over backing stores.
            // No store is opened here — the backings own theirs (proxy beats
            // in-process mounting; each backing keeps its own governance).
            if let Some(fed_spec) = &federate {
                if wm_mcp::landlock_sandbox::requested() {
                    // v0 confines writes to a store root; the gateway opens
                    // none. The v1 per-tool pathway (EffectRow.sandbox) is
                    // the seam for proxy-surface confinement.
                    tracing::warn!(
                        "WM_LANDLOCK=1 is not yet supported in federate mode — \
                         continuing unconfined (v0 applies to store-opening serve)"
                    );
                }
                let scopes = wm_mcp::gateway::parse_federate_spec(fed_spec)?;
                let home = std::env::var("WM_PROJECT").ok().filter(|s| !s.is_empty());
                let contract_path = std::env::var("WM_GATEWAY_CONTRACT_PATH").map_or_else(
                    |_| default_store_path().join("gateway_contract.json"),
                    PathBuf::from,
                );
                let gateway = std::sync::Arc::new(wm_mcp::gateway::Gateway::new(
                    &scopes,
                    home,
                    Box::new(wm_mcp::gateway::HttpBacking::new()),
                    contract_path,
                ));
                let rt = tokio::runtime::Runtime::new()?;
                match transport.as_str() {
                    "stdio" => gateway.run_stdio()?,
                    "sse" => {
                        let addr = bind
                            .ok_or_else(|| {
                                anyhow::anyhow!(
                                    "--transport sse requires --bind (e.g. 127.0.0.1:18795)"
                                )
                            })?
                            .parse::<std::net::SocketAddr>()?;
                        tracing::info!(%addr, "Starting federated gateway over HTTP/SSE");
                        rt.block_on(std::sync::Arc::clone(&gateway).run_http(addr))?;
                    }
                    other => {
                        anyhow::bail!("Unknown transport '{other}' (expected stdio or sse)");
                    }
                }
                rt.shutdown_timeout(std::time::Duration::from_millis(500));
                return Ok(());
            }

            // Resolve the tool surface profile with explicit precedence:
            // WM_TOOL_ALLOWLIST > --profile flag > WM_TOOL_PROFILE > curated.
            // `wm serve` with no flag and no env is the product surface.
            // `wm daemon` and library constructors still default to full
            // (cycle tools live outside curated). The resolved name is
            // exported so `tool_profile_from_env()` sees the winning value.
            let env_profile = std::env::var("WM_TOOL_PROFILE").ok();
            let env_allowlist = std::env::var("WM_TOOL_ALLOWLIST").ok();
            let resolved = if profile.is_none() && env_profile.is_none() && env_allowlist.is_none()
            {
                &wm_tools::profiles::PROFILE_CURATED
            } else {
                wm_tools::profiles::resolve_tool_profile(
                    profile.as_deref(),
                    env_profile.as_deref(),
                    env_allowlist.as_deref(),
                )
            };
            // `std::env::set_var` is unsafe in Rust 2024 (not thread-safe);
            // main() is single-threaded here, before any runtime is spawned.
            #[allow(unsafe_code)]
            unsafe {
                std::env::set_var("WM_TOOL_PROFILE", resolved.name);
            }
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");
            std::fs::create_dir_all(&lmdb_path)?;

            // Landlock v0 (Phase 5): whole-process FS confinement, opt-in via
            // WM_LANDLOCK=1. Write-class rights are confined to the store
            // root; reads stay free. This must run on the main thread BEFORE
            // the tokio runtime spawns — workers inherit the spawning
            // thread's restriction. Every outcome is non-fatal: unsupported
            // kernels continue unconfined, loudly.
            let landlock_report = if wm_mcp::landlock_sandbox::requested() {
                let report = wm_mcp::landlock_sandbox::restrict_to_store_root(&store_path);
                match report.outcome {
                    wm_mcp::landlock_sandbox::LandlockOutcome::Enforced => tracing::info!(
                        store_root = %report.store_root,
                        "Landlock enforced — write-class FS rights confined to the store root"
                    ),
                    other => tracing::warn!(
                        outcome = other.as_str(),
                        detail = %report.detail,
                        "Landlock v0 degraded — process is NOT fully confined"
                    ),
                }
                wm_mcp::landlock_sandbox::persist_report(&store_path, &report);
                Some(report)
            } else {
                None
            };

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

            if let Some(report) = landlock_report {
                server.set_landlock_report(report);
            }

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

            // Sangha mesh transport (R0): --mesh flag or WM_MESH=1. The node
            // spawns on this runtime before the server loop starts, so the
            // background tasks (TCP serve, beacon listener, auto-join) live
            // as long as the process.
            if mesh || wm_sangha::mesh_node::env_requested() {
                let keypair = wm_mcp::server::mesh_signing_key();
                let config = wm_sangha::MeshNodeConfig::from_env(mesh_bind.as_deref(), &keypair);
                match rt.block_on(wm_sangha::MeshNode::start(config, keypair)) {
                    Ok(node) => {
                        tracing::info!(
                            peer_id = %node.peer_id(),
                            "Sangha mesh enabled — sangha.mesh.* tools are on \
                             --profile full; identity is stable only with WM_MESH_KEY"
                        );
                        server.install_mesh_node(node);
                    }
                    Err(e) => {
                        // Loud but non-fatal: the server stays up without the
                        // mesh, mirroring the Landlock degradation doctrine.
                        tracing::warn!(
                            "mesh transport failed to start ({e}) — continuing unmeshed"
                        );
                    }
                }
            }

            match transport.as_str() {
                "sse" => {
                    let addr = bind
                        .ok_or_else(|| {
                            anyhow::anyhow!(
                                "--transport sse requires --bind (e.g. 127.0.0.1:18789)"
                            )
                        })?
                        .parse::<std::net::SocketAddr>()?;
                    tracing::info!(%addr, "Starting MCP server over HTTP/SSE");
                    rt.block_on(async { server.run_sse(addr).await })?;
                }
                "stdio" => {
                    rt.block_on(async { server.run_async().await })?;
                }
                other => {
                    anyhow::bail!("Unknown transport '{other}' (expected stdio or sse)");
                }
            }
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
            network,
        } => {
            // Posture-by-observation is store-independent: `--network` runs
            // the socket audit alone and never opens the LMDB env.
            let issues = if network {
                println!("=== WhiteMagic Doctor — Network Posture ===");
                println!();
                let issues = run_network_audit();
                println!();
                println!("=== Doctor Summary ===");
                if issues == 0 {
                    println!("Network posture clean — local-only asserted by observation.");
                } else {
                    println!("{issues} issue(s) found — exit code 1.");
                }
                issues
            } else {
                run_doctor(store, check_integrity, repair)?
            };
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
            checkpoint_interval,
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
            if let Some(secs) = checkpoint_interval {
                daemon_cfg.checkpoint_interval = std::time::Duration::from_secs(secs);
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
        Commands::Ingest {
            source,
            store,
            dry_run,
            limit,
            galaxy,
        } => {
            let store_path = store.unwrap_or_else(default_store_path);
            wm_mcp::ingest::run_ingest(&source, &store_path, dry_run, limit, galaxy.as_deref())?;
        }
        Commands::Opencode { command } => match command {
            OpencodeCommands::Digest { db, since, json } => {
                let db_path = db.unwrap_or_else(wm_mcp::opencode::default_opencode_db);
                wm_mcp::opencode::run_digest(&db_path, since.as_deref(), json)?;
            }
            OpencodeCommands::Export {
                db,
                session,
                out,
                device,
            } => {
                let db_path = db.unwrap_or_else(wm_mcp::opencode::default_opencode_db);
                let device = device.unwrap_or_else(detect_hostname);
                wm_mcp::opencode::run_export(&db_path, &session, out.as_deref(), &device)?;
            }
        },
        Commands::Reindex {
            store,
            no_backup,
            galaxy,
            dry_run,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_reindex(&store_path, !no_backup, &galaxy, dry_run)?;
        }
        Commands::RepairContent {
            store,
            galaxy,
            apply,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_repair_content(&store_path, &galaxy, apply)?;
        }
        Commands::Session { command } => {
            run_session_command(command)?;
        }
        Commands::Seal { store } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_seal(&store_path)?;
        }
        Commands::Trust { store, command } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_trust(&store_path, command)?;
        }
        Commands::Verify { store } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_verify(&store_path)?;
        }
        Commands::Anchor { store, publish } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_anchor(&store_path, publish.as_deref())?;
        }
        Commands::Backup { store, out } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_backup(&store_path, out.as_deref())?;
        }
        Commands::Restore {
            backup,
            store,
            force,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_restore(&backup, &store_path, force)?;
        }
    }

    Ok(())
}

/// Rebuild the Tantivy index from LMDB (`wm reindex`).
/// Survey or correct source-trust provenance (`wm trust`).
///
/// Takes the LMDB lock — stop the store's server unit first.
fn run_trust(store_path: &std::path::Path, command: TrustCommand) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.join("data.mdb").exists() {
        anyhow::bail!("No LMDB data found at {}.", lmdb_path.display());
    }
    let store = wm_memory::MemoryStore::open_default(&lmdb_path).map_err(|e| {
        anyhow::anyhow!(
            "Could not take the LMDB lock at {} — a server may be running \
             (stop the store's wm-serve unit first). Error: {e}",
            lmdb_path.display()
        )
    })?;
    match command {
        TrustCommand::Survey => {
            let report = wm_mcp::trust_admin::survey(&store);
            println!("{}", serde_json::to_string_pretty(&report)?);
        }
        TrustCommand::Sessions => {
            let report = wm_mcp::trust_admin::sessions_profile(&store);
            println!("{}", serde_json::to_string_pretty(&report)?);
        }
        TrustCommand::Correct {
            source,
            galaxy,
            created_before,
            tag,
            set_trust,
            apply,
        } => {
            let galaxy = galaxy
                .as_deref()
                .map(|g| {
                    wm_tools::expansion::common::parse_galaxy(g)
                        .map_err(|e| anyhow::anyhow!("unknown galaxy '{g}': {e}"))
                })
                .transpose()?;
            let created_before = created_before
                .as_deref()
                .map(|ts| {
                    chrono::DateTime::parse_from_rfc3339(ts)
                        .map(|d| d.with_timezone(&chrono::Utc))
                        .map_err(|e| anyhow::anyhow!("created_before must be RFC 3339: {e}"))
                })
                .transpose()?;
            let criteria = wm_mcp::trust_admin::CorrectionCriteria {
                source,
                galaxy,
                created_before,
                tag,
            };
            let report = wm_mcp::trust_admin::correct(&store, &criteria, set_trust, apply)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            if report.dry_run {
                println!(
                    "\nDry run — nothing written. Re-run with --apply to set trust to {}.",
                    report.set_trust
                );
            }
        }
    }
    Ok(())
}

/// Rebuild the Tantivy index from LMDB (`wm reindex`).
/// Back up the full store root (`wm backup`).
fn run_backup(
    store_path: &std::path::Path,
    out_parent: Option<&std::path::Path>,
) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.join("data.mdb").exists() {
        anyhow::bail!(
            "No LMDB data found at {}. Stop the server, then retry.",
            lmdb_path.display()
        );
    }

    // Live-server detection: opening the environment takes the LMDB write
    // lock. If a server is running this fails instead of producing a torn
    // copy.
    match wm_memory::MemoryStore::open_default(&lmdb_path) {
        Ok(store) => drop(store),
        Err(e) => anyhow::bail!(
            "Could not take the LMDB lock at {} — a server may be running. \
             Stop it before backing up. (underlying error: {e})",
            lmdb_path.display()
        ),
    }

    let dest_parent = out_parent.map_or_else(
        || dirs_home().join("whitemagic-backups"),
        std::path::PathBuf::from,
    );
    let ts = chrono::Utc::now().format("%Y%m%dT%H%M%SZ");
    let dest = dest_parent.join(format!("whitemagic-backup-{ts}"));
    let data_dest = dest.join("data");
    std::fs::create_dir_all(&data_dest)?;

    let mut files = Vec::new();
    copy_tree(store_path, &data_dest, &mut files)?;
    files.sort();

    // SHA256SUMS manifest over every copied file (paths relative to data/).
    use sha2::Digest;
    use std::fmt::Write as _;
    let mut sums = String::new();
    for rel in &files {
        let abs = data_dest.join(rel);
        let digest: String = {
            let mut hasher = sha2::Sha256::new();
            let bytes = std::fs::read(&abs)?;
            hasher.update(&bytes);
            hex(&hasher.finalize())
        };
        let _ = writeln!(sums, "{digest}  data/{rel}");
    }
    std::fs::write(dest.join("SHA256SUMS"), sums)?;

    // Envelope v2 (S4): a self-describing backup. Same envelope module the
    // session export/import path uses — one validator, three uses.
    let envelope = wm_memory::envelope::EnvelopeHeader::new("store_backup", files.len());
    std::fs::write(
        dest.join("envelope.json"),
        serde_json::to_string_pretty(&envelope)?,
    )?;

    println!(
        "Backed up {} files ({} bytes) to {}",
        files.len(),
        total_size(&data_dest),
        dest.display()
    );
    println!("Manifest: {}", dest.join("SHA256SUMS").display());
    println!();
    println!("Restore with:");
    println!(
        "  wm restore --backup {} [--store <store-root>] [--force]",
        dest.display()
    );
    println!("Keep backups on a different disk or machine than the live store.");
    Ok(())
}

/// Restore the full store root from a backup (`wm restore`).
fn run_restore(
    backup: &std::path::Path,
    store_path: &std::path::Path,
    force: bool,
) -> anyhow::Result<()> {
    let sums_path = backup.join("SHA256SUMS");
    let data_src = backup.join("data");
    if !sums_path.exists() || !data_src.exists() {
        anyhow::bail!(
            "Not a whitemagic backup: {} must contain 'data/' and 'SHA256SUMS'.",
            backup.display()
        );
    }

    // Verify BEFORE touching the target.
    use sha2::Digest;
    let mut manifest_count = 0usize;
    for line in std::fs::read_to_string(&sums_path)?.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        manifest_count += 1;
        let (expected, manifest_path) = line
            .split_once("  ")
            .ok_or_else(|| anyhow::anyhow!("bad SHA256SUMS line: {line}"))?;
        // Manifest paths are relative to the backup root with a data/ prefix,
        // so `sha256sum -c` works from the backup directory itself.
        let rel = manifest_path.strip_prefix("data/").ok_or_else(|| {
            anyhow::anyhow!("bad SHA256SUMS path (missing data/ prefix): {manifest_path}")
        })?;
        let abs = data_src.join(rel);
        let actual = {
            let mut hasher = sha2::Sha256::new();
            hasher.update(std::fs::read(&abs)?);
            hex(&hasher.finalize())
        };
        if actual != expected {
            anyhow::bail!(
                "Backup verification FAILED for {manifest_path}: expected {expected}, got {actual}. Aborting restore."
            );
        }
    }

    let envelope_path = backup.join("envelope.json");
    if envelope_path.exists() {
        // Envelope v2 (S4): validate a self-describing backup.
        let env_text = std::fs::read_to_string(&envelope_path)?;
        let header: wm_memory::envelope::EnvelopeHeader =
            serde_json::from_str(&env_text).map_err(|e| {
                anyhow::anyhow!("Backup envelope.json is corrupt ({e}). Aborting restore.")
            })?;
        if header.format_version > wm_memory::envelope::ENVELOPE_FORMAT_VERSION {
            anyhow::bail!(
                "Backup envelope format_version {} is newer than this build supports ({}). \
                 Upgrade `wm` before restoring — refusing a partial restore.",
                header.format_version,
                wm_memory::envelope::ENVELOPE_FORMAT_VERSION
            );
        }
        if header.count != manifest_count {
            eprintln!(
                "WARN: envelope declares {} files but SHA256SUMS lists {manifest_count}; \
                 restoring what the manifest verifies",
                header.count
            );
        }
        println!(
            "Backup envelope: v{} {} by {} at {}",
            header.format_version, header.kind, header.generator, header.created_at
        );
    } else {
        println!("Note: pre-envelope backup (no envelope.json) — SHA256SUMS verification only.");
    }

    if store_path.exists() {
        if !force {
            anyhow::bail!(
                "Target store {} already exists. Use --force to overwrite (the existing store will be REPLACED).",
                store_path.display()
            );
        }
        std::fs::remove_dir_all(store_path)?;
    }
    if let Some(parent) = store_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    copy_tree(&data_src, store_path, &mut Vec::new())?;

    println!(
        "Restored {} from {}",
        store_path.display(),
        backup.display()
    );
    println!("Run 'wm doctor' to confirm health.");
    println!(
        "If doctor reports index drift, run 'wm reindex --store {}'.",
        store_path.display()
    );
    Ok(())
}

/// Recursively copy `src` into `dst`, collecting paths relative to `dst`.
fn copy_tree(
    src: &std::path::Path,
    dst: &std::path::Path,
    collected: &mut Vec<String>,
) -> anyhow::Result<()> {
    fn walk(
        src: &std::path::Path,
        dst: &std::path::Path,
        rel: &str,
        collected: &mut Vec<String>,
    ) -> anyhow::Result<()> {
        std::fs::create_dir_all(dst)?;
        for entry in std::fs::read_dir(src)? {
            let entry = entry?;
            let file_type = entry.file_type()?;
            let name = entry.file_name().to_string_lossy().to_string();
            let child_rel = if rel.is_empty() {
                name.clone()
            } else {
                format!("{rel}/{name}")
            };
            let src_child = entry.path();
            let dst_child = dst.join(&name);
            if file_type.is_dir() {
                walk(&src_child, &dst_child, &child_rel, collected)?;
            } else if !file_type.is_symlink() {
                // Never follow or preserve symlinks inside a store.
                std::fs::copy(&src_child, &dst_child)?;
                collected.push(child_rel);
            }
        }
        Ok(())
    }
    walk(src, dst, "", collected)
}

fn hex(bytes: &[u8]) -> String {
    bytes
        .iter()
        .fold(String::with_capacity(bytes.len() * 2), |mut acc, b| {
            use std::fmt::Write as _;
            let _ = write!(acc, "{b:02x}");
            acc
        })
}

fn total_size(root: &std::path::Path) -> u64 {
    fn walk(dir: &std::path::Path) -> u64 {
        let mut total = 0;
        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten() {
                match entry.file_type() {
                    Ok(t) if t.is_dir() => total += walk(&entry.path()),
                    Ok(_) => total += entry.metadata().map_or(0, |m| m.len()),
                    Err(_) => {}
                }
            }
        }
        total
    }
    walk(root)
}

fn dirs_home() -> std::path::PathBuf {
    std::env::var("HOME").map_or_else(|_| std::path::PathBuf::from("."), std::path::PathBuf::from)
}

/// Seal the store directory (`wm seal`).
fn run_seal(store_path: &std::path::Path) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.exists() {
        anyhow::bail!(
            "No store found at {}. Run 'wm serve' first.",
            lmdb_path.display()
        );
    }
    let manifest = wm_mcp::seal::seal_store(&lmdb_path)?;
    println!(
        "Sealed {} files at {}",
        manifest.files.len(),
        manifest.sealed_at
    );
    println!("Manifest: {}", lmdb_path.join("seal.json").display());
    println!("Run 'wm verify' to check integrity.");
    Ok(())
}

/// Verify the store directory (`wm verify`).
fn run_verify(store_path: &std::path::Path) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.exists() {
        anyhow::bail!(
            "No store found at {}. Run 'wm serve' first.",
            lmdb_path.display()
        );
    }
    let report = wm_mcp::seal::verify_store(&lmdb_path)?;
    if report.is_ok() {
        println!("OK — {} files verified, no discrepancies.", report.matched);
    } else {
        println!("VERIFY FAILED:");
        println!("  matched:    {}", report.matched);
        if !report.mismatched.is_empty() {
            println!("  mismatched: {}", report.mismatched.len());
            for f in &report.mismatched {
                println!("    - {f}");
            }
        }
        if !report.missing.is_empty() {
            println!("  missing:    {}", report.missing.len());
            for f in &report.missing {
                println!("    - {f}");
            }
        }
        if !report.extra.is_empty() {
            println!("  extra:      {}", report.extra.len());
            for f in &report.extra {
                println!("    + {f}");
            }
        }
        std::process::exit(1);
    }
    Ok(())
}

/// Merkle-anchor the store's record attestations (`wm anchor`).
///
/// Takes the LMDB lock — stop the store's server unit first (same posture
/// as `wm trust`).
fn run_anchor(
    store_path: &std::path::Path,
    publish: Option<&std::path::Path>,
) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.join("data.mdb").exists() {
        anyhow::bail!("No LMDB data found at {}.", lmdb_path.display());
    }
    let store = wm_memory::MemoryStore::open_default(&lmdb_path).map_err(|e| {
        anyhow::anyhow!(
            "Could not take the LMDB lock at {} — a server may be running \
             (stop the store's wm-serve unit first). Error: {e}",
            lmdb_path.display()
        )
    })?;
    let report = wm_mcp::anchor::anchor_report(&store).map_err(|e| anyhow::anyhow!("{e}"))?;
    let invalid = report
        .get("invalid")
        .and_then(serde_json::Value::as_u64)
        .unwrap_or(0);
    println!("{}", serde_json::to_string_pretty(&report)?);
    if let Some(path) = publish {
        wm_mcp::anchor::append_anchor_log(path, &report).map_err(|e| anyhow::anyhow!("{e}"))?;
        eprintln!("Published anchor to {}", path.display());
    }
    if invalid > 0 {
        anyhow::bail!("{invalid} attestation signature(s) INVALID — see report above");
    }
    Ok(())
}

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

/// Run the content-repair pass (`wm repair-content`).
///
/// Dry-run by default: reports what WOULD be repaired without touching the
/// store. With `--apply`, rows are rewritten in place and indexed — take a
/// `wm backup` first. Galaxies filter via repeatable `--galaxy` (db names,
/// e.g. `research`); default is all memory galaxies.
fn run_repair_content(
    store_path: &std::path::Path,
    galaxy_filter: &[String],
    apply: bool,
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

    let galaxies: Vec<wm_core::Galaxy> = if galaxy_filter.is_empty() {
        wm_core::Galaxy::memory_galaxies().to_vec()
    } else {
        galaxy_filter
            .iter()
            .map(|s| {
                wm_core::Galaxy::from_db_name(&s.to_lowercase())
                    .or_else(|| wm_core::Galaxy::from_db_name(s))
                    .ok_or_else(|| anyhow::anyhow!("unknown galaxy: {s}"))
            })
            .collect::<anyhow::Result<Vec<_>>>()?
    };

    let store = wm_memory::MemoryStore::open_default(&lmdb_path)?;
    let search = wm_memory::SearchEngine::open(&tantivy_path)?;

    if !apply {
        // Dry-run: classify without writing. The skip-reserve is exactly
        // the population repair would consider; report the majority-text
        // split by evaluating the same cleaner.
        let mut repairable = 0usize;
        let mut unrepairable = 0usize;
        let mut total_skipped = 0usize;
        for galaxy in &galaxies {
            for mem in store.scan_all(*galaxy)? {
                if wm_memory::sanitize_content_for_index(&mem.content).is_some() {
                    continue;
                }
                total_skipped += 1;
                let total = mem.content.chars().count();
                let printable = mem.content.chars().filter(|c| !c.is_control()).count();
                let cleaned: String = mem
                    .content
                    .chars()
                    .map(|c| {
                        if c.is_control() && c != '\n' && c != '\t' && c != '\r' {
                            ' '
                        } else {
                            c
                        }
                    })
                    .collect();
                if total > 0
                    && (printable as f32 / total as f32) >= 0.5
                    && wm_memory::sanitize_content_for_index(&cleaned).is_some()
                {
                    repairable += 1;
                } else {
                    unrepairable += 1;
                }
            }
        }
        println!(
            "Dry run (store untouched): {total_skipped} gate-failing docs — \
             {repairable} repairable, {unrepairable} true-binary (would stay \
             unindexed)"
        );
        println!("Run with --apply to repair in place (take a 'wm backup' first).");
        return Ok(());
    }

    println!(
        "Repairing gate-failing content in place across {} galaxies — this \
         rewrites LMDB rows and reindexes them...",
        galaxies.len()
    );
    let report = wm_memory::repair_content(&store, &search, &galaxies)?;
    println!(
        "Repair complete: scanned={} repaired={} unrepairable={} already_clean={}",
        report.scanned, report.repaired, report.unrepairable, report.already_clean
    );
    for g in &report.galaxies {
        if g.repaired > 0 || g.unrepairable > 0 {
            println!(
                "  {:12} scanned={:7} repaired={:7} unrepairable={:5} clean={:7}",
                g.galaxy, g.scanned, g.repaired, g.unrepairable, g.already_clean
            );
        }
    }
    println!(
        "A read-only server on this store should restart to observe the \
         rebuilt index."
    );
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

/// Human-readable byte size (KB/MB/GB with one decimal).
fn format_bytes(bytes: u64) -> String {
    let units = ["B", "KB", "MB", "GB", "TB"];
    let mut value = bytes as f64;
    let mut unit = 0usize;
    while value >= 1024.0 && unit < units.len() - 1 {
        value /= 1024.0;
        unit += 1;
    }
    if unit == 0 {
        format!("{bytes} B")
    } else {
        format!("{value:.1} {}", units[unit])
    }
}

/// `wm session` — CLI parity for the MCP session routes (board item 1).
/// The Mac had to hand-roll JSON-RPC over stdio to keep continuity alive
/// when MCP dropped twice in one session; these subcommands share the exact
/// tool implementations the server routes to over a direct LMDB open, so
/// the session rhythm survives transport failure. Mirrors migrate.rs's
/// multi-process-safe `MemoryStore::open` (4 GiB map) — short transactions
/// coexist with a live daemon via LMDB's writer lock.
fn run_session_command(command: SessionCommands) -> anyhow::Result<()> {
    use wm_core::{BrainWave, Context, Tool};
    use wm_tools::expansion::{
        SessionCheckpointTool, SessionContinuityTool, SessionRecordTool, SessionStartTool,
    };

    let store_root = match &command {
        SessionCommands::Start { store, .. }
        | SessionCommands::Record { store, .. }
        | SessionCommands::Checkpoint { store, .. }
        | SessionCommands::Continuity { store, .. } => {
            store.clone().unwrap_or_else(default_store_path)
        }
    };
    let lmdb_path = store_root.join("lmdb");
    if !lmdb_path.exists() {
        anyhow::bail!(
            "LMDB store not found at {} — pass --store or start 'wm serve' first",
            lmdb_path.display()
        );
    }
    let store = std::sync::Arc::new(wm_memory::MemoryStore::open(
        &lmdb_path,
        4 * 1024 * 1024 * 1024,
    )?);

    let rt = tokio::runtime::Runtime::new()?;
    let result = rt.block_on(async {
        let mut ctx = Context::new(BrainWave::Beta);
        match command {
            SessionCommands::Start { title, user, .. } => {
                SessionStartTool::new(store)
                    .call(&mut ctx, serde_json::json!({"title": title, "user": user}))
                    .await
            }
            SessionCommands::Record {
                content,
                role,
                turn_type,
                importance,
                session_id,
                supersedes,
                ..
            } => {
                let mut args = serde_json::json!({
                    "content": content,
                    "role": role,
                    "turn_type": turn_type,
                    "importance": importance,
                });
                if let Some(sid) = session_id {
                    args["session_id"] = serde_json::json!(sid);
                }
                if let Some(old) = supersedes {
                    args["supersedes"] = serde_json::json!(old);
                }
                SessionRecordTool::new(store).call(&mut ctx, args).await
            }
            SessionCommands::Checkpoint {
                session_id,
                label,
                root,
                commit,
                branch,
                tests_green,
                next_queue,
                open_flags,
                lease_id,
                ..
            } => {
                // Only provided fields are passed — explicit arguments win,
                // absent keys stay absent (the tool's own handoff semantics).
                let mut args = serde_json::json!({ "label": label });
                if let Some(v) = session_id {
                    args["session_id"] = serde_json::json!(v);
                }
                if let Some(v) = root {
                    args["root"] = serde_json::json!(v);
                }
                if let Some(v) = commit {
                    args["commit"] = serde_json::json!(v);
                }
                if let Some(v) = branch {
                    args["branch"] = serde_json::json!(v);
                }
                if let Some(v) = tests_green {
                    args["tests_green"] = serde_json::json!(v);
                }
                if !next_queue.is_empty() {
                    args["next_queue"] = serde_json::json!(next_queue);
                }
                if !open_flags.is_empty() {
                    args["open_flags"] = serde_json::json!(open_flags);
                }
                if let Some(v) = lease_id {
                    args["lease_id"] = serde_json::json!(v);
                }
                SessionCheckpointTool::new(store).call(&mut ctx, args).await
            }
            SessionCommands::Continuity {
                n,
                session_id,
                since,
                until,
                ..
            } => {
                let mut args = serde_json::json!({ "n": n });
                if let Some(v) = session_id {
                    args["current_session_id"] = serde_json::json!(v);
                }
                if let Some(v) = since {
                    args["since"] = serde_json::json!(v);
                }
                if let Some(v) = until {
                    args["until"] = serde_json::json!(v);
                }
                SessionContinuityTool::new(store).call(&mut ctx, args).await
            }
        }
    })?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}

/// Run the live network posture audit and print it in doctor voice.
/// Returns the issue count (each non-LAN egress violation is an issue).
fn run_network_audit() -> u32 {
    let posture = wm_mcp::network_audit::audit();
    if !posture.platform_supported {
        println!(
            "[INFO] Network posture: /proc socket tables unavailable — local-only cannot \
             be asserted by observation on this platform"
        );
        return 0;
    }
    if posture.subjects.is_empty() {
        println!(
            "[INFO] Network posture: no WhiteMagic processes or fleet transport observed \
             running — nothing to grade"
        );
        return 0;
    }

    let mut issues = 0u32;
    let mut established_total = 0usize;
    for subject in &posture.subjects {
        established_total += subject.established_remote.len();
        let kind = if subject.is_fleet_transport() {
            "fleet transport"
        } else {
            "whitemagic"
        };
        let violations: Vec<_> = posture
            .violations
            .iter()
            .filter(|v| v.pid == subject.pid)
            .collect();
        if violations.is_empty() {
            println!(
                "[OK]   {kind} {}: pid {} — {} established (all LAN/loopback), {} non-loopback listener(s)",
                subject.comm,
                subject.pid,
                subject.established_remote.len(),
                subject.lan_listeners.len()
            );
        } else {
            issues += violations.len() as u32;
            println!(
                "[WARN] {kind} {}: pid {} — non-LAN egress observed",
                subject.comm, subject.pid
            );
            for v in &violations {
                println!(
                    "       established to {}:{} — outside the LAN fence",
                    v.remote.addr, v.remote.port
                );
            }
        }
        for listener in &subject.lan_listeners {
            println!(
                "       listener {}:{} (LAN inbound exposure — disclosed, egress is what grades)",
                listener.addr, listener.port
            );
        }
    }
    println!(
        "[{}] Network posture: {established_total} established socket(s) observed, {issues} non-LAN egress violation(s) — local-only asserted by observation, not assumed from config",
        if issues == 0 { "OK" } else { "WARN" }
    );
    println!(
        "       scope: WhiteMagic processes + fleet transport (syncthing); the egress lesson (defaults are privacy decisions) verified live"
    );
    issues
}

fn run_doctor(store: Option<PathBuf>, check_integrity: bool, repair: bool) -> anyhow::Result<u32> {
    let store_path = store.unwrap_or_else(default_store_path);
    let lmdb_path = store_path.join("lmdb");
    let mut issues = 0u32;

    println!("=== WhiteMagic Doctor ===");
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

    // 3. Tantivy search index — check directory, then consistency with LMDB
    let tantivy_path = lmdb_path.join("tantivy");
    if tantivy_path.exists() {
        println!("[OK]   Tantivy index: {}", tantivy_path.display());

        // Consistency check: compare LMDB memory counts to Tantivy doc counts.
        // If they differ, the index is stale (best-effort indexing failures,
        // skipped sanitization, or orphan documents from failed deletes).
        match wm_memory::SearchEngine::open_readonly(&tantivy_path) {
            Ok(search) => {
                let consistency = wm_memory::check_consistency(server.store(), &search);
                if consistency.has_drift {
                    // Truthfulness layer: classify the gap — docs the index
                    // gate refuses are a documented reserve, not healable
                    // drift. Only a nonzero healable gap warns.
                    let class = wm_memory::classify_drift(server.store(), &search);
                    if class.healable_total == 0 {
                        println!(
                            "[OK]   Index consistency: LMDB={} Tantivy={} — no healable \
                             drift; {} docs in the sanitization-skip reserve (never \
                             indexable as-is)",
                            consistency.total_lmdb,
                            consistency.total_tantivy,
                            class.skip_reserve_total
                        );
                        for g in class.galaxies.iter().filter(|g| g.skip_reserve > 0) {
                            println!(
                                "       {} — {} skip-reserve docs ('wm repair-content' \
                                 to clean)",
                                g.galaxy, g.skip_reserve
                            );
                        }
                    } else {
                        let drifted: Vec<_> =
                            consistency.galaxies.iter().filter(|g| g.drift).collect();
                        println!(
                            "[WARN] Index consistency: {} galaxy(ies) drifted \
                             (LMDB={}, Tantivy={}, healable={}, skip-reserve={})",
                            drifted.len(),
                            consistency.total_lmdb,
                            consistency.total_tantivy,
                            class.healable_total,
                            class.skip_reserve_total
                        );
                        for g in &drifted {
                            println!(
                                "       {} — LMDB={}, Tantivy={} (run 'wm reindex' to \
                                 rebuild)",
                                g.galaxy, g.lmdb_count, g.tantivy_count
                            );
                        }
                        issues += 1;
                    }
                } else {
                    println!(
                        "[OK]   Index consistency: LMDB={} Tantivy={} (no drift)",
                        consistency.total_lmdb, consistency.total_tantivy
                    );
                }

                // Index health: report failures if any
                let health = search.health().snapshot();
                let failures = health
                    .get("failures")
                    .and_then(serde_json::Value::as_u64)
                    .unwrap_or(0);
                if failures > 0 {
                    let last_error = health
                        .get("last_error")
                        .and_then(serde_json::Value::as_str)
                        .unwrap_or("unknown");
                    println!(
                        "[WARN] Index health: {failures} failure(s) since startup — last error: {last_error}"
                    );
                    issues += 1;
                } else {
                    let successes = health
                        .get("successes")
                        .and_then(serde_json::Value::as_u64)
                        .unwrap_or(0);
                    println!("[OK]   Index health: {successes} successful operations, 0 failures");
                }
            }
            Err(e) => {
                println!("[WARN] Cannot open Tantivy index for consistency check: {e}");
                issues += 1;
            }
        }
    } else {
        println!("[WARN] Tantivy index not found (search will be unavailable)");
        issues += 1;
    }

    // 3b. Resource budgets — the Yama limits gating every dispatch. Effective
    // limits scale with homeostasis health, which is why bulk operations slow
    // down on a loaded box (the "18/18 per minute" effect). Surfaces the
    // maintenance override so it is never mysterious mid-run.
    {
        use wm_mcp::input_validation::{MAX_PARAMS_SIZE, MAX_REQUEST_SIZE};
        let cfg = wm_mcp::server::resource_rules_config_from_env();
        // Sample homeostasis the way the pipeline does: cpu from loadavg,
        // memory pressure from MemAvailable/MemTotal.
        let mut cpu_load = 0.0f32;
        if let Ok(la) = std::fs::read_to_string("/proc/loadavg") {
            if let Some(f1) = la.split_whitespace().next() {
                if let Ok(v) = f1.parse::<f32>() {
                    let ncpu = std::thread::available_parallelism().map_or(4.0, |n| n.get() as f32);
                    cpu_load = (v / ncpu).min(1.0);
                }
            }
        }
        let mut mem_pressure = 0.0f32;
        if let Ok(mi) = std::fs::read_to_string("/proc/meminfo") {
            let get_kb = |label: &str| -> Option<u64> {
                mi.lines().find(|l| l.starts_with(label)).and_then(|l| {
                    l.split_whitespace()
                        .nth(1)
                        .and_then(|v| v.parse::<u64>().ok())
                })
            };
            if let (Some(total), Some(avail)) = (get_kb("MemTotal:"), get_kb("MemAvailable:")) {
                if total > 0 {
                    mem_pressure = (1.0 - (avail as f32 / total as f32)).clamp(0.0, 1.0);
                }
            }
        }
        let homeo = wm_governance::Homeostasis {
            cpu_load,
            memory_pressure: mem_pressure,
            active: false,
        };
        let scale = homeo.health_score().clamp(0.1, 1.0);
        let eff_w = ((cfg.max_writes_per_minute as f32) * scale) as u32;
        let eff_s = ((cfg.max_spawns_per_minute as f32) * scale) as u32;
        let eff_n = ((cfg.max_network_per_minute as f32) * scale) as u32;
        println!(
            "[OK]   Resource budgets (Yama): writes {eff_w}/min, spawns {eff_s}/min, network {eff_n}/min"
        );
        println!(
            "       config: writes {}/{}/min, spawns {}/{}/min, network {}/default/min; health {:.2} (cpu {:.2}, mem {:.2})",
            cfg.max_writes_per_minute,
            if std::env::var("WM_RESOURCE_MAX_WRITES_PER_MIN").is_ok() {
                "env"
            } else {
                "default"
            },
            cfg.max_spawns_per_minute,
            if std::env::var("WM_DISPATCH_TOOL_RPM").is_ok() {
                "env"
            } else {
                "default"
            },
            cfg.max_network_per_minute,
            scale,
            cpu_load,
            mem_pressure
        );
        println!(
            "       bulk ops: memory.batch_delete (confirm-gated) | maintenance envs: WM_RESOURCE_MAX_WRITES_PER_MIN, WM_DISPATCH_TOOL_RPM, WM_DISPATCH_GLOBAL_RPM | caps: request {MAX_REQUEST_SIZE}B, params {MAX_PARAMS_SIZE}B"
        );
        println!("       doc: docs/BULK_OPERATIONS.md");
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

    // 11b. Store seal — corruption / casual-tamper detection only.
    let seal_manifest = lmdb_path.join("seal.json");
    if seal_manifest.exists() {
        match std::fs::read_to_string(&seal_manifest) {
            Ok(contents) => match serde_json::from_str::<serde_json::Value>(&contents) {
                Ok(json) => {
                    let sealed_at = json
                        .get("sealed_at")
                        .and_then(serde_json::Value::as_str)
                        .unwrap_or("unknown");
                    let file_count = json
                        .get("files")
                        .and_then(serde_json::Value::as_object)
                        .map_or(0, serde_json::Map::len);
                    println!("[OK]   Store seal: {file_count} files, sealed at {sealed_at}");
                    println!(
                        "       Run 'wm verify --store {}' to check integrity.",
                        store_path.display()
                    );
                    println!(
                        "       HMAC only — an adversary who can replace .seal_key and seal.json wins."
                    );
                }
                Err(e) => {
                    println!("[WARN] Store seal present but unparseable: {e}");
                    issues += 1;
                }
            },
            Err(e) => {
                println!("[WARN] Cannot read store seal: {e}");
                issues += 1;
            }
        }
    } else {
        println!("[INFO] No store seal (run 'wm seal' to write an HMAC integrity manifest)");
    }

    // 11b. Write budget (Phase 3 irony tax) — how much the store is
    //      costing the SSD, today vs its own 30-day norm. Read-only:
    //      the doctor samples sizes but never persists a ledger.
    println!();
    let mut ledger = wm_substrate::write_budget::WriteBudgetLedger::load(&store_path);
    let wb = ledger.fresh_report();
    if wb.days_tracked == 0 {
        println!("[INFO] Write budget: no ledger yet (first writable server session records it)");
    } else {
        let vs_avg = if wb.avg_30d_bytes > 0 {
            format!(
                " ({:.0}% of 30-day avg)",
                100.0 * wb.today_bytes as f64 / wb.avg_30d_bytes as f64
            )
        } else {
            String::new()
        };
        println!(
            "[OK]   Write budget: {} today{}",
            format_bytes(wb.today_bytes),
            vs_avg
        );
        if let Some(y) = wb.yesterday_bytes {
            println!(
                "       Yesterday: {} · 30-day avg: {}",
                format_bytes(y),
                format_bytes(wb.avg_30d_bytes)
            );
        }
        if let Some((day, bytes)) = &wb.busiest_day {
            println!("       Busiest day: {day} ({})", format_bytes(*bytes));
        }
        println!(
            "       Store size: LMDB {} + Tantivy {} across {} tracked day(s)",
            format_bytes(wb.lmdb_bytes),
            format_bytes(wb.tantivy_bytes),
            wb.days_tracked
        );
    }
    println!("       Ledger: {}", ledger.ledger_path().display());

    // 11c. Profile contract (Phase 5 surface-drift watch item) — does the
    //      last server start on this store advertise the surface its
    //      declared profile covers? The server persists the contract at
    //      startup; the doctor grades it read-only.
    println!();
    let contract_path = store_path.join("profile_contract.json");
    if contract_path.exists() {
        let parsed = std::fs::read_to_string(&contract_path)
            .map_err(anyhow::Error::from)
            .and_then(|body| {
                serde_json::from_str::<wm_tools::profiles::ProfileContract>(&body)
                    .map_err(anyhow::Error::from)
            });
        match parsed {
            Ok(c) if c.ok => {
                println!(
                    "[OK]   Profile contract: {} surface, {} tools (verified {})",
                    c.profile, c.registered_count, c.verified_at
                );
                if !c.destructive_tools.is_empty() {
                    println!(
                        "       Destructive on surface (confirm-gated): {}",
                        c.destructive_tools.join(", ")
                    );
                }
            }
            Ok(c) => {
                println!(
                    "[FAIL] Profile contract violation ({}): declared {} tools, registered {}",
                    c.profile, c.expected_count, c.registered_count
                );
                if !c.dead_prefixes.is_empty() {
                    println!("       Dead prefixes: {}", c.dead_prefixes.join(", "));
                }
                if !c.unexpected_tools.is_empty() {
                    println!("       Unexpected tools: {}", c.unexpected_tools.join(", "));
                }
                issues += 1;
            }
            Err(e) => {
                println!("[WARN] Profile contract unreadable: {e}");
                issues += 1;
            }
        }
    } else {
        println!(
            "[INFO] Profile contract: none on file (no writable server start since the feature landed)"
        );
    }

    // 11d. Landlock v0 state (Phase 5 kernel-side slice) — did the last
    //      serve start on this store apply the whole-process ruleset?
    //      The server persists its report at startup; the doctor grades it
    //      read-only. Degradation is never silent: anything short of full
    //      enforcement counts as an issue when the flag was requested.
    println!();
    match wm_mcp::landlock_sandbox::load_report(&store_path) {
        Some(report)
            if report.enabled
                && report.outcome == wm_mcp::landlock_sandbox::LandlockOutcome::Enforced =>
        {
            println!(
                "[OK]   Landlock: enforced — write-class FS rights confined to {} (verified {})",
                report.store_root, report.requested_at
            );
        }
        Some(report) if report.enabled => {
            println!(
                "[WARN] Landlock requested but not fully enforced ({}): {}",
                report.outcome.as_str(),
                report.detail
            );
            issues += 1;
        }
        Some(report) => {
            println!(
                "[INFO] Landlock: {} ({})",
                report.detail, report.requested_at
            );
        }
        None => {
            println!("[INFO] Landlock: not enabled (opt in with WM_LANDLOCK=1)");
        }
    }

    // 11e. Gateway contract (Phase 5 federated gateway) — did the last
    //      wm-gateway start probe a healthy fleet? Same doctrine as the
    //      profile contract: the server persists at startup, the doctor
    //      grades read-only. Absent file = the gateway hasn't run (INFO);
    //      a contract that is not ok counts as an issue (drift is loud).
    println!();
    let gateway_path = std::env::var("WM_GATEWAY_CONTRACT_PATH").map_or_else(
        |_| default_store_path().join("gateway_contract.json"),
        PathBuf::from,
    );
    if gateway_path.exists() {
        match std::fs::read_to_string(&gateway_path)
            .map_err(anyhow::Error::from)
            .and_then(|body| {
                serde_json::from_str::<wm_mcp::gateway::GatewayContract>(&body)
                    .map_err(anyhow::Error::from)
            }) {
            Ok(c) if c.ok && c.all_reachable => {
                let scopes: Vec<&str> = c.scopes.iter().map(|s| s.name.as_str()).collect();
                println!(
                    "[OK]   Gateway contract: {} reachable, home {} (verified {})",
                    scopes.join("/"),
                    c.home.as_deref().unwrap_or("(none)"),
                    c.verified_at
                );
                let readonly: Vec<&str> = c
                    .scopes
                    .iter()
                    .filter(|s| s.disclosure.readonly == Some(true))
                    .map(|s| s.name.as_str())
                    .collect();
                if !readonly.is_empty() {
                    println!("       Read-only scopes: {}", readonly.join(", "));
                }
            }
            Ok(c) => {
                let unreachable: Vec<&str> = c
                    .scopes
                    .iter()
                    .filter(|s| !s.disclosure.reachable)
                    .map(|s| s.name.as_str())
                    .collect();
                println!(
                    "[FAIL] Gateway contract not ok (all_reachable={}): unreachable scopes: {}",
                    c.all_reachable,
                    unreachable.join(", ")
                );
                issues += 1;
            }
            Err(e) => {
                println!("[WARN] Gateway contract unreadable: {e}");
                issues += 1;
            }
        }
    } else {
        println!(
            "[INFO] Gateway contract: none on file (no wm-gateway start since the feature landed)"
        );
    }

    // 11f. Network posture (board item 2) — "local-only" is asserted by
    //      observing the live socket tables, attributing sockets to
    //      WhiteMagic processes + the fleet transport, and grading egress.
    //      Read-only /proc observation; feeds off the egress lesson (item 8).
    println!();
    issues += run_network_audit();

    // 11g. Recall-route honesty (V8 ship list #1/#6) — disclose which
    //      route memory.search will take in this deployment and what
    //      quality to expect from it. The hybrid route requires a real
    //      embedder; without one the default route is the episodic
    //      deterministic machinery, and the measured gap is what
    //      route-honesty exists to surface (LongMemEval-S 50q, S8
    //      protocol 2026-09-01: episodic 0.86 R@1 vs BM25 fallback 0.64).
    println!();
    let embedder_env = std::env::var("WM_EMBEDDER_BACKEND")
        .ok()
        .map(|backend| format!("onnx backend {backend}"))
        .or_else(|| {
            std::env::var("WM_EMBEDDER_ENDPOINT")
                .ok()
                .map(|endpoint| format!("endpoint {endpoint}"))
        });
    if let Some(description) = embedder_env {
        println!(
            "[OK]   Recall route: hybrid fusion (real embedder per this invocation's env: {description}) — memory.search runs BM25+vector fusion"
        );
    } else {
        let episodic_count = server.store_arc().episodic().record_count().unwrap_or(0);
        let cache_count = server.store_arc().embedding_cache_count().unwrap_or(0);
        let cache_note = if cache_count > 0 {
            format!(", embedding cache: {cache_count} vectors")
        } else {
            String::new()
        };
        if episodic_count > 0 {
            println!(
                "[OK]   Recall route: episodic deterministic default (stub embedder, {episodic_count} episodic records mirror the memory lane{cache_note}) — measured R@1 0.86 (LongMemEval-S 50q, S8 protocol 2026-09-01)"
            );
        } else {
            println!(
                "[WARN] Recall route: BM25 full-text fallback (stub embedder, episodic lane empty) — measured R@1 0.64 vs 0.86 on the episodic route (LongMemEval-S 50q, S8 protocol 2026-09-01); memory writes populate the episodic mirror, which upgrades the default route"
            );
            issues += 1;
        }
    }

    // 11h. Firebreak (fix-queue P1.4+P1.6) — the promoted Jan-11
    //      forbidden-command guardrail plus the bulk-scope law. Static
    //      grading: the veto arms with every pipeline (armed unless
    //      WM_FIREBREAK=0), so the doctor reports arm state, pattern
    //      coverage, and scope-registry size. Disarming is visible here
    //      and counts as an issue — a disarmed guardrail is a finding,
    //      not a configuration.
    println!();
    {
        let firebreak = wm_governance::Firebreak::promoted();
        let (forbidden, dangerous, caution) = firebreak.pattern_counts();
        if firebreak.is_armed() {
            println!(
                "[OK]   Firebreak: armed — {forbidden} forbidden / {dangerous} dangerous / {caution} caution patterns, {} scope-registry entries (Jan-11 guardrail promotion)",
                wm_governance::SCOPE_REGISTRY.len()
            );
        } else {
            println!(
                "[WARN] Firebreak: DISARMED (WM_FIREBREAK=0) — forbidden-command veto and bulk-scope law off; {forbidden}/{dangerous}/{caution} patterns compiled but not enforcing"
            );
            issues += 1;
        }
    }

    // 12. Write-audit journal — misdeclarations become visible here.
    //     The journal is append-only and lives in the Karma LMDB galaxy;
    //     the doctor opens it directly (read-only) from the store.
    println!();
    let journal = match wm_governance::WriteAuditJournal::new(server.store_arc()) {
        Ok(j) => j,
        Err(e) => {
            println!("[WARN] Write-audit journal unavailable: {e}");
            issues += 1;
            println!();
            println!("=== Doctor Summary ===");
            if issues == 0 {
                println!("All systems healthy.");
            } else {
                println!("{issues} issue(s) found — exit code 1.");
            }
            return Ok(issues);
        }
    };
    let journal_entries = journal.scan_entries().map_or(0, |e| e.len());
    match journal.misdeclarations() {
        Ok(mis) => {
            // S11b: attribution coverage — how much of the journal actually
            // names its actor. Labeled 0% on an old store is honest, not a
            // failure; 0% on a new one means dispatches run without
            // identity in their Context.
            let scan = journal.scan_entries().unwrap_or_default();
            let labeled = scan
                .iter()
                .filter(|e| e.actor_user.is_some() || e.actor_session.is_some())
                .count();
            let coverage = if journal_entries == 0 {
                "n/a".to_string()
            } else {
                format!("{labeled}/{journal_entries}")
            };
            println!(
                "[{}] Write-audit journal: {journal_entries} entries (actor labeled: {coverage}), {} undeclared-mutation entries",
                if mis.is_empty() { "OK" } else { "WARN" },
                mis.len()
            );
            if !mis.is_empty() {
                issues += 1;
                for entry in mis.iter().take(5) {
                    let when = i64::try_from(entry.timestamp)
                        .ok()
                        .and_then(|t| chrono::DateTime::<chrono::Utc>::from_timestamp(t, 0))
                        .map_or_else(|| entry.timestamp.to_string(), |d| d.to_rfc3339());
                    // S11b: name the actor when the journal has one — the
                    // first question any investigation asks.
                    let actor = match (&entry.actor_user, &entry.actor_session) {
                        (Some(u), Some(s)) => format!("{u}@{s}"),
                        (Some(u), None) => u.clone(),
                        (None, Some(s)) => format!("session {s}"),
                        (None, None) => "unknown actor".to_string(),
                    };
                    println!(
                        "       [WARN] '{}' by {actor} mutated the store without declaring writes (entry {}, {} store writes, {when})",
                        entry.tool, entry.id, entry.store_write_delta
                    );
                }
                if mis.len() > 5 {
                    println!(
                        "       ... and {} more — inspect with diagnostics",
                        mis.len() - 5
                    );
                }
            }
        }
        Err(e) => {
            println!("[WARN] Write-audit journal unreadable: {e}");
            issues += 1;
        }
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
    // G1.5 product quickstart: demonstrate the headline outcome — a decision
    // recorded in one session survives a full process restart and is
    // retrieved in the next session. Runs against an ISOLATED demo store so
    // a pre-existing user store is never polluted.
    let demo_store = default_store_path().parent().map_or_else(
        || PathBuf::from(".whitemagic-quickstart"),
        |p| p.join("whitemagic-quickstart"),
    );
    let lmdb_path = demo_store.join("lmdb");
    std::fs::create_dir_all(&lmdb_path)?;

    println!("=== WhiteMagic Quickstart ===");
    println!();
    println!("This demo uses an isolated store (your real data is untouched):");
    println!("  {}", demo_store.display());
    println!();
    println!("--- Process 1: record a project decision ---");
    println!();

    let decision = String::from(
        "Use SQLite for the report cache: the dataset fits in memory and we need ad-hoc queries.",
    );

    // Process 1: initialize, start a session, record a decision, checkpoint.
    {
        let mut server = wm_mcp::McpServer::with_defaults(&lmdb_path)?;

        let start_request = serde_json::json!({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "wm", "arguments": {
                "route": "session.start",
                "args": {"title": "WhiteMagic quickstart"}
            }}
        });
        let response = server.handle_request(&start_request.to_string()).await;
        if response.contains("\"error\"") {
            anyhow::bail!("session.start failed: {response}");
        }
        println!("  Session started.");

        let record_request = serde_json::json!({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "wm", "arguments": {
                "route": "session.record",
                "args": {
                    "content": decision,
                    "role": "user",
                    "turn_type": "decision",
                    "importance": 0.9
                }
            }}
        });
        let response = server.handle_request(&record_request.to_string()).await;
        if response.contains("\"error\"") {
            anyhow::bail!("session.record failed: {response}");
        }
        println!("  Decision recorded:");
        println!("    \"{decision}\"");

        let checkpoint_request = serde_json::json!({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "wm", "arguments": {
                "route": "session.checkpoint",
                "args": {}
            }}
        });
        let _ = server.handle_request(&checkpoint_request.to_string()).await;
        println!("  Session checkpointed.");
        // Dropping the server closes the store — the process boundary the
        // second process must survive.
    }

    println!();
    println!("--- Process stopped. Starting Process 2 on the same store ---");
    println!();

    // Process 2: a fresh server instance reopens the store from disk.
    {
        let mut server = wm_mcp::McpServer::with_defaults(&lmdb_path)?;

        let continuity_request = serde_json::json!({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "wm", "arguments": {
                "route": "session.continuity",
                "args": {"n": 5}
            }}
        });
        let response = server.handle_request(&continuity_request.to_string()).await;
        let resp: serde_json::Value = serde_json::from_str(&response).unwrap_or_default();
        let text = resp
            .pointer("/result/content/0/text")
            .and_then(|t| t.as_str())
            .unwrap_or("{}");
        let continuity: serde_json::Value = serde_json::from_str(text).unwrap_or_default();

        if continuity
            .get("previous_session")
            .is_some_and(|v| !v.is_null())
        {
            println!(
                "  Continuity recovered prior session {}.",
                continuity["previous_session"].as_str().unwrap_or("?")
            );
            if let Some(turns) = continuity.get("turns").and_then(|t| t.as_array()) {
                for turn in turns.iter().take(3) {
                    let role = turn.get("role").and_then(|r| r.as_str()).unwrap_or("?");
                    let content = turn.get("content").and_then(|c| c.as_str()).unwrap_or("");
                    println!("    [{role}] {content}");
                }
            }
        } else {
            println!("  (No prior session found — continuity returned nothing)");
        }

        println!();
        println!("  Progressive replay (token budget 400):");
        let replay_request = serde_json::json!({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "wm", "arguments": {
                "route": "session.replay",
                "args": {"mode": "progressive", "token_budget": 400}
            }}
        });
        let response = server.handle_request(&replay_request.to_string()).await;
        let resp: serde_json::Value = serde_json::from_str(&response).unwrap_or_default();
        if resp.get("result").is_some() {
            println!("    Replay succeeded within budget.");
        } else {
            println!(
                "    (Replay error: {})",
                response.chars().take(120).collect::<String>()
            );
        }
    }

    println!();
    println!("=== Quickstart Complete ===");
    println!();
    println!("The decision survived a full process restart. That is the product:");
    println!("record context now, recover it next session.");
    println!();
    println!("Demo store (safe to delete): {}", demo_store.display());
    println!("  rm -rf {}", demo_store.display());
    println!();
    println!("Next steps:");
    println!("  1. Point your MCP client at:  wm serve --profile curated");
    println!(
        "     (uses your real store at {} )",
        default_store_path().display()
    );
    println!("  2. Start sessions and record decisions as you work.");
    println!("  3. Before each new session, ask for continuity.");
    println!("  4. Back up the whole store directory regularly.");
    println!("  5. Run 'wm doctor' any time for a health check.");

    Ok(())
}

fn run_polyglot() {
    println!("=== WhiteMagic Polyglot Status ===");
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
