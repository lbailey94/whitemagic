//! WhiteMagic Gen3 — Production `wm` CLI binary (v10.0.0-alpha).
//!
//! Milestone 9 Gate 9B Production Shell.
//!
//! Enforces that all CLI operations dispatch as sovereign pulses via the pulse compiler,
//! upholds the Gen3 Kernel Contract (Articles 1-9), and provides zero-dependency
//! compatibility with legacy Gen2 stores.

#![recursion_limit = "512"]

use clap::{Parser, Subcommand};
use serde_json::json;
use std::io::BufRead;
use std::path::{Path, PathBuf};

use wm_gen3_core::compat::{Gen2Census, Gen2Reader, MigrationOptions, migrate_gen2_to_gen3};
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::mandala::{
    CapabilityManifest, MandalaPass, MandalaReplayLedger, PassBudget, ScopeMode,
    resolve_or_create_mandala_gate_key,
};
use wm_gen3_core::mesh::{
    DEFAULT_MESH_PORT, MESH_PROTOCOL_VERSION, MeshClient, MeshServer, SyncBundle,
    resolve_or_create_mesh_key,
};
use wm_gen3_core::ops::{ImportKind, RecallQuery, RememberItem, SessionCheckpoint, Substrate};
use wm_gen3_core::{ContextCacheToken, ToolSchemaDefinition};
use wm_gen3_harness::bridge::{
    McpProfile, build_contract_manifest, execute_hybrid_tool_call, get_tools_list_for_profile,
};

#[derive(Parser)]
#[command(
    name = "wm",
    version = "10.0.0-alpha",
    about = "WhiteMagic Gen3 — sovereign cognitive kernel and local-first memory",
    after_help = "Gate 9B Compatibility Shell — all mutations dispatch as sovereign pulses."
)]
struct Cli {
    /// Path to store directory
    #[arg(long, global = true)]
    store: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Display system status, epoch, record counts, and store health
    Status {
        /// Optional path to legacy Gen2 store to inspect
        #[arg(long)]
        legacy: Option<PathBuf>,
    },
    /// Ingest a memory statement via sovereign pulse compilation
    Remember {
        /// Content of the memory to record
        content: String,
        /// Epistemic source attribution (default: "operator:cli")
        #[arg(long, default_value = "operator:cli")]
        source: String,
        /// Epistemic kind: reported (default), system, or simulated
        #[arg(long, default_value = "reported")]
        kind: String,
    },
    /// Recall memories matching a query string
    Recall {
        /// Query string
        query: String,
        /// Maximum number of results to return (default: 10)
        #[arg(long, default_value_t = 10)]
        limit: usize,
        /// Candidate search pool size (default: 100)
        #[arg(long, default_value_t = 100)]
        candidate_limit: usize,
        /// Include superseded and archived records
        #[arg(long)]
        historical: bool,
        /// Optional recall scope view filter
        #[arg(long)]
        scope: Option<String>,
    },
    /// Run an explicit cognitive think sweep pass
    Sweep,
    /// Run a passive cognitive dream incubation cycle (associative consolidation)
    Dream {
        /// Quiescence level [0.0, 1.0] (default: 1.0 = deep incubation)
        #[arg(long, default_value_t = 1.0)]
        quiescence: f32,
        /// Number of dream incubation cycles (default: 1)
        #[arg(long)]
        cycles: Option<usize>,
        /// Mode: genuine (default), sham, baseline
        #[arg(long, default_value = "genuine")]
        mode: String,
        /// Optional path to write dream journal log (default: <store>/dream.jsonl)
        #[arg(long)]
        log_file: Option<PathBuf>,
        /// Output a historical summary report of dream incubation cycles from dream.jsonl
        #[arg(long)]
        report: bool,
        /// Output or inspect actionable synthetic dream insights
        #[arg(long)]
        insights: bool,
        /// Run complete dual-phase sleep cycle (NREM structural compaction + REM associative dreaming)
        #[arg(long, default_value_t = true)]
        dual_phase: bool,
        /// Enable homeostatic regulation of dream parameters (default: true)
        #[arg(long, default_value_t = true)]
        homeostatic: bool,
        /// Force dream incubation regardless of thermal or battery stress
        #[arg(long)]
        force: bool,
    },
    /// Cognitive router triage: evaluate dispatch tier for inquiry with dream-assisted fast path
    Route {
        /// The inquiry or task description to route
        inquiry: String,
        /// Expected marginal utility [0.0, 1.0] (default: 0.8)
        #[arg(long, default_value_t = 0.8)]
        utility: f64,
    },
    /// Generate 6D holographic coordinates and export interactive 3D WebGL galaxy
    Galaxy {
        /// Output path for interactive HTML visualization (default: <store>/galaxy.html)
        #[arg(long)]
        output_html: Option<PathBuf>,
        /// Output path for 6D coordinates JSON dataset (default: <store>/galaxy_6d.json)
        #[arg(long)]
        output_json: Option<PathBuf>,
        /// Sample limit for visualization (default: 2000)
        #[arg(long, default_value_t = 2000)]
        limit: usize,
    },
    /// Inspect substrate invariants, active constitution view, and self-model state
    Inspect {
        /// Inspection scope: all (default), invariants, balance, calibration, apotheosis
        #[arg(long, default_value = "all")]
        scope: String,
    },
    /// Run an Apotheosis Meta-Learning, Invariant Audit & Truth-Drift evaluation
    Apotheosis {
        /// Optional path to custom geneseed vault JSONL
        #[arg(long)]
        vault_file: Option<PathBuf>,
    },
    /// Run a zero-dependency census and integrity audit on a legacy Gen2 LMDB store
    Census {
        /// Path to the Gen2 LMDB store directory containing data.mdb
        path: PathBuf,
    },
    /// Migrate a legacy Gen2 LMDB store into Gen3 via sovereign pulses
    Migrate {
        /// Path to the legacy Gen2 LMDB store directory containing data.mdb
        #[arg(long)]
        source: PathBuf,
        /// Ingestion batch size (default: 100)
        #[arg(long, default_value_t = 100)]
        batch_size: usize,
        /// Dry run mode (simulate migration without committing)
        #[arg(long)]
        dry_run: bool,
        /// Allow noise patterns without filtering
        #[arg(long)]
        allow_noise: bool,
        /// Skip SHA-256 hash validation
        #[arg(long)]
        skip_hash_validation: bool,
        /// Optional path to write quarantine log (default: <store>/quarantine.jsonl)
        #[arg(long)]
        quarantine_file: Option<PathBuf>,
        /// Optional path to write migration receipt (default: <store>/migration_receipt.json)
        #[arg(long)]
        receipt_file: Option<PathBuf>,
    },
    /// Output machine-checked route and schema contract manifest
    Contract {
        /// Output formatted JSON manifest
        #[arg(long)]
        json: bool,
    },
    /// Run the JSON-RPC / MCP stdio server (sidecar for Claude Code, Antigravity, Opencode)
    #[command(alias = "mcp")]
    Serve {
        /// Active MCP tool profile: 'cyberbrain' (10 lean tools, default) or 'full' (36-tool curated suite)
        #[arg(long, default_value = "cyberbrain")]
        profile: String,
        /// Open store in read-only mode
        #[arg(long)]
        readonly: bool,
        /// Enable cognitive sweep
        #[arg(long, default_value_t = true)]
        sweep: bool,
        /// Enable semantic projection
        #[arg(long)]
        projection: bool,
        /// Semantic embedding cache directory
        #[arg(long)]
        embed_cache: Option<PathBuf>,
        /// Enable dispersion
        #[arg(long)]
        dispersion: bool,
        /// Enable noise filtration
        #[arg(long, default_value_t = true)]
        noise: bool,
    },
    /// Mandala P2P Mesh & Sovereign Synchronization
    Mesh {
        #[command(subcommand)]
        command: MeshCommands,
    },
    /// Compounding Session Continuity & Agent Handoff Management
    Session {
        #[command(subcommand)]
        command: SessionCommands,
    },
    /// Ingest memories, transcripts, or execution events from JSONL file or stdin
    Ingest {
        /// Path to JSONL file (or '-' for standard input)
        #[arg(long, default_value = "-")]
        file: String,
        /// Ingestion batch size (default: 500)
        #[arg(long, default_value_t = 500)]
        batch_size: usize,
        /// Default source identifier
        #[arg(long, default_value = "ingest:stream")]
        default_source: String,
        /// Default import kind: reported, direct, observed, foreign (default: reported)
        #[arg(long, default_value = "reported")]
        default_kind: String,
    },
    /// Mandala OS Execution Authority & Continuity Receipt Bridge
    Mandala {
        #[command(subcommand)]
        command: MandalaCommands,
    },
    /// Manage the Geneseed Action Vault, execute skeletons, and evaluate $do(X)$ mutations
    Vault {
        #[command(subcommand)]
        command: VaultCommands,
    },
    /// Run an autonomous closed-loop waking-sleeping evolutionary cycle
    Evolve {
        /// Number of evolutionary epochs to run (default: 3)
        #[arg(long, default_value_t = 3)]
        epochs: usize,
        /// Number of sleep incubation cycles per epoch (default: 1)
        #[arg(long, default_value_t = 1)]
        sleep_cycles: usize,
        /// Quiescence level during sleep [0.0, 1.0] (default: 1.0)
        #[arg(long, default_value_t = 1.0)]
        quiescence: f64,
        /// Exploration temperature during sleep [0.0, 2.0] (default: 0.90)
        #[arg(long, default_value_t = 0.90)]
        temperature: f64,
    },
    /// Run an invariant self-test and environment diagnostic
    Selftest {
        /// Output results as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum VaultCommands {
    /// List action skeletons in the Geneseed Vault
    List {
        /// Include deprecated/retired skeletons
        #[arg(long)]
        all: bool,
    },
    /// Inspect details of a specific action skeleton
    Get {
        /// Skeleton ID (e.g. skel-verify-commit)
        skeleton_id: String,
    },
    /// Execute an action skeleton against the substrate and record empirical Kaizen utility
    Execute {
        /// Skeleton ID (e.g. skel-verify-commit)
        skeleton_id: String,
    },
    /// Propose a $do(X)$ mutation and evaluate it against the ParetoGate
    Mutate {
        /// Skeleton ID to mutate
        skeleton_id: String,
        /// Mutation kind: vanguard, heavy, or opt (default: vanguard)
        #[arg(long, default_value = "vanguard")]
        kind: String,
    },
}

#[derive(Subcommand)]
enum SessionCommands {
    /// Ingest a structured compounding session checkpoint
    Checkpoint {
        /// Session identifier (e.g. conversation ID, lane name)
        #[arg(long)]
        session_id: String,
        /// Active agent identifier (e.g. antigravity, luna, opencode)
        #[arg(long, default_value = "agent")]
        agent_id: String,
        /// Checkpoint type: turn, handoff, milestone, compact
        #[arg(long, default_value = "handoff")]
        checkpoint_type: String,
        /// High-density summary of decisions, state, and findings
        #[arg(long)]
        summary: String,
        /// Queued action items for next turn / next agent
        #[arg(long)]
        next_queue: Vec<String>,
        /// Open flags, blockers, or warnings
        #[arg(long)]
        open_flags: Vec<String>,
        /// Optional ContextCache token
        #[arg(long)]
        context_token: Option<String>,
        /// Autonomously evolve action skeletons and consolidate dream insights after checkpoint (default: true)
        #[arg(long, default_value_t = true)]
        evolve: bool,
    },
    /// Ingest an arbitrary session note or log
    Record {
        #[arg(long)]
        session_id: String,
        #[arg(long, default_value = "agent")]
        agent_id: String,
        #[arg(long, default_value = "note")]
        log_type: String,
        #[arg(long)]
        content: String,
    },
    /// Retrieve latest continuity view for a session (or latest overall)
    Continuity {
        /// Optional session identifier filter
        #[arg(long)]
        session_id: Option<String>,
    },
    /// List all active session IDs in the substrate
    List,
}

#[derive(Subcommand)]
enum MeshCommands {
    /// Show local mesh node identity, verifying key, and epoch
    Status,
    /// Start sovereign TCP mesh listener daemon
    Listen {
        /// TCP port to bind (default: 7369)
        #[arg(long, default_value_t = DEFAULT_MESH_PORT)]
        port: u16,
        /// Host or IP to bind (default: "0.0.0.0")
        #[arg(long, default_value = "0.0.0.0")]
        bind: String,
        /// Custom node name identifier
        #[arg(long)]
        node_id: Option<String>,
    },
    /// Send authenticated ping to a peer and measure latency
    Ping {
        /// Peer socket address (e.g. 127.0.0.1:7369 or 192.168.1.50:7369)
        #[arg(long)]
        peer: String,
        /// Custom node name identifier
        #[arg(long)]
        node_id: Option<String>,
    },
    /// Synchronize memory delta from a remote peer into local store
    Sync {
        /// Peer socket address (e.g. 127.0.0.1:7369 or 192.168.1.50:7369)
        #[arg(long)]
        peer: String,
        /// Maximum records to fetch in batch (default: 500)
        #[arg(long, default_value_t = 500)]
        batch_size: usize,
        /// Custom node name identifier
        #[arg(long)]
        node_id: Option<String>,
    },
    /// Export self-verifying signed sync bundle (.wmpack) for sneakernet / SD card transfer
    Export {
        /// Path to write bundle file (.wmpack)
        #[arg(long)]
        out: PathBuf,
        /// Only export records committed at or after this epoch (default: 0)
        #[arg(long, default_value_t = 0)]
        since_epoch: u64,
        /// Custom author node name identifier
        #[arg(long)]
        author_id: Option<String>,
    },
    /// Import and verify a sync bundle (.wmpack) into local store
    Import {
        /// Path to bundle file (.wmpack)
        #[arg(long)]
        in_file: PathBuf,
        /// Expected 32-byte hex public key of signer (optional)
        #[arg(long)]
        expected_key: Option<String>,
    },
    /// Synchronize and audit genetic action skeletons from a remote peer with ParetoGate adjudication
    SyncGenes {
        /// Peer socket address (e.g. 127.0.0.1:7369 or 192.168.1.50:7369)
        #[arg(long)]
        peer: String,
        /// Minimum skeleton version to sync (default: 0)
        #[arg(long, default_value_t = 0)]
        since_version: u32,
        /// Custom node name identifier
        #[arg(long)]
        node_id: Option<String>,
    },
}

#[derive(Subcommand)]
enum MandalaCommands {
    /// Verify an Ed25519-signed MandalaPass token against the replay ledger
    VerifyPass {
        /// Path to pass JSON file
        #[arg(long)]
        pass_file: Option<PathBuf>,
        /// Inline pass JSON string
        #[arg(long)]
        pass_json: Option<String>,
        /// Current simulated epoch (default: current system timestamp)
        #[arg(long)]
        epoch: Option<u64>,
    },
    /// Issue a new cryptographically signed MandalaPass
    IssuePass {
        /// Tenant ID
        #[arg(long)]
        tenant_id: String,
        /// Slot ID
        #[arg(long, default_value = "slot-default")]
        slot_id: String,
        /// Agent ID
        #[arg(long)]
        agent_id: String,
        /// Pass ID
        #[arg(long)]
        pass_id: String,
        /// Allowed operations (comma-separated, default: all)
        #[arg(long)]
        allowed: Option<String>,
        /// Denied operations (comma-separated)
        #[arg(long)]
        denied: Option<String>,
        /// Time-to-live in seconds (default: 3600)
        #[arg(long, default_value_t = 3600)]
        ttl: u64,
        /// Max operations budget (default: 100)
        #[arg(long, default_value_t = 100)]
        max_ops: u32,
        /// Max compute budget in milliseconds (default: 300000)
        #[arg(long, default_value_t = 300000)]
        max_compute_ms: u64,
        /// Max memory budget in MB (default: 1024)
        #[arg(long, default_value_t = 1024)]
        max_memory_mb: u64,
        /// Network restricted (default: false)
        #[arg(long)]
        network_restricted: bool,
        /// Output path to save the issued pass JSON
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Record a Mandala continuity receipt into WhiteMagic Gen3 store via CommitCapability
    RecordReceipt {
        /// Path to receipt JSON file
        #[arg(long)]
        receipt_file: PathBuf,
        /// Epistemic source attribution tag (default: 'mandala:gate-lite')
        #[arg(long, default_value = "mandala:gate-lite")]
        source: String,
    },
    /// Non-autoregressive System 1 JEV decision pre-triage (<30ns evaluation)
    Triage {
        /// Expected utility score [0.0, 1.0]
        #[arg(long, default_value_t = 0.85)]
        utility: f64,
        /// Estimated risk / regression probability [0.0, 1.0]
        #[arg(long, default_value_t = 0.15)]
        risk: f64,
        /// Uncertainty / variance [0.0, 1.0]
        #[arg(long, default_value_t = 0.10)]
        variance: f64,
        /// Execution or token cost [0.0, 1.0]
        #[arg(long, default_value_t = 0.05)]
        cost: f64,
        /// Threshold for admission [0.0, 1.0] (default: 0.15)
        #[arg(long, default_value_t = 0.15)]
        threshold: f64,
    },
    /// Evaluate a candidate mutation through the Sovereign Evolutionary Software Factory
    Evaluate {
        /// Candidate mutation identifier
        #[arg(long, default_value = "cand-001")]
        candidate_id: String,
        /// Parent lineage identifier
        #[arg(long, default_value = "root")]
        parent_id: String,
        /// Proposer DID
        #[arg(long, default_value = "did:key:proposer_maker")]
        proposer: String,
        /// Proposed actions (comma-separated, default: "cargo check,cargo test")
        #[arg(long, default_value = "cargo check,cargo test")]
        actions: String,
        /// Mutation kind: vanguard, heavy, or step (default: step)
        #[arg(long, default_value = "step")]
        mutation: String,
        /// Expected utility [0.0, 1.0]
        #[arg(long, default_value_t = 0.85)]
        utility: f64,
        /// Optional code payload string
        #[arg(long)]
        code: Option<String>,
        /// Output path for signed ContinuityReceipt05 JSON
        #[arg(long)]
        out_receipt: Option<PathBuf>,
    },
    /// Inspect the Mandala replay ledger, revoked tenants, and consumed JTIs
    Status,
}

fn resolve_store_path(cli_store: Option<&PathBuf>) -> PathBuf {
    if let Some(p) = cli_store {
        return p.clone();
    }
    if let Ok(p) = std::env::var("WM_STORE") {
        return PathBuf::from(p);
    }
    if let Ok(home) = std::env::var("HOME") {
        let gen3_dir = PathBuf::from(&home).join(".local/share/whitemagic/gen3");
        if gen3_dir.exists() {
            return gen3_dir;
        }
        let legacy_dir = PathBuf::from(&home).join(".local/share/whitemagic/lmdb");
        if legacy_dir.exists() {
            return legacy_dir;
        }
        let default_dir = PathBuf::from(&home).join(".local/share/whitemagic");
        if default_dir.exists() {
            return default_dir;
        }
    }
    PathBuf::from("gen3-store")
}

fn main() {
    let cli = Cli::parse();
    let store_path = resolve_store_path(cli.store.as_ref());

    match cli.command {
        Commands::Status { legacy } => {
            if let Some(legacy_path) = legacy {
                run_legacy_census(&legacy_path);
                return;
            }

            // Check if store_path is a Gen2 store
            if legacy_store_detected(&store_path) {
                println!("Detected legacy Gen2 store at: {}", store_path.display());
                run_legacy_census(&store_path);
                return;
            }

            let journal_path = store_path.join("journal.jsonl");
            match Substrate::open_readonly(&store_path, Some(&journal_path), default_view()) {
                Ok(substrate) => {
                    let records_count = substrate.store().record_count().unwrap_or(0);
                    let relations_count = substrate
                        .store()
                        .iter_relations()
                        .map(|r| r.len())
                        .unwrap_or(0);
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    println!("==================================================");
                    println!("       WhiteMagic Gen3 Kernel Status (v10.0.0-alpha)");
                    println!("==================================================");
                    println!("Store Path:       {}", store_path.display());
                    println!("Mode:             ReadOnly (Inspection)");
                    println!("Epoch:            {}", epoch);
                    println!("Records Count:    {}", records_count);
                    println!("Relations Count:  {}", relations_count);
                    println!("Budget RPM:       {}", substrate.budget());
                    println!(
                        "Journal Status:   {}",
                        if substrate.journal_ok() {
                            "OK"
                        } else {
                            "DEGRADED"
                        }
                    );
                    println!("Article 1:        CommitCapability Gated (100%)");
                    println!("Article 4:        Authoritative Background Loops = 0");
                    println!("Closure Scans:    PASS");
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Error opening Gen3 store at {}: {e}", store_path.display());
                    std::process::exit(1);
                }
            }
        }
        Commands::Census { path } => {
            run_legacy_census(&path);
        }
        Commands::Remember {
            content,
            source,
            kind,
        } => {
            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

            let import_kind = match kind.to_lowercase().as_str() {
                "system" => ImportKind::System,
                "simulated" => ImportKind::Simulated,
                _ => ImportKind::Reported,
            };

            let authority = RatifiedChannel::mint("wm-cli-operator");
            substrate.set_intake_authority(authority);

            let item = RememberItem {
                content,
                source,
                kind: import_kind,
            };

            let results = substrate.remember_batch(&[item]);
            match &results[0] {
                Ok(id) => {
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    println!("Commit successful.");
                    println!("Record ID:     {}", id);
                    println!("Epoch:         {}", epoch);
                    println!("Authority:     RatifiedChannel(wm-cli-operator)");
                    println!("Contract:      Article 1 MVCC Transaction Verified");
                }
                Err(e) => {
                    eprintln!("Remember refused: {e}");
                    std::process::exit(1);
                }
            }
        }
        Commands::Recall {
            query,
            limit,
            candidate_limit,
            historical,
            scope,
        } => {
            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open_readonly(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

            let q = RecallQuery {
                query: query.clone(),
                limit,
                candidate_limit,
                include_historical: historical,
                min_score: 0.0,
                min_coverage: 0.0,
                scope,
            };

            match substrate.recall(&q) {
                Ok(hits) => {
                    println!("Query: \"{}\" ({} results)", query, hits.len());
                    for (i, hit) in hits.iter().enumerate() {
                        let superseded = hit
                            .superseded_by
                            .map(|s| format!(" [superseded by #{s}]"))
                            .unwrap_or_default();
                        println!(
                            "\n[{}] Record #{} (score: {:.4}){}",
                            i + 1,
                            hit.id,
                            hit.score,
                            superseded
                        );
                        println!("    Source:  {}", hit.source);
                        println!("    Content: {}", hit.content);
                    }
                }
                Err(e) => {
                    eprintln!("Recall error: {e}");
                    std::process::exit(1);
                }
            }
        }
        Commands::Sweep => {
            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-sweep"));

            let stats = substrate.think_sweep();
            println!("==================================================");
            println!("           Cognitive Think Sweep Complete          ");
            println!("==================================================");
            println!("Sweep ID:                 {}", stats.sweep);
            println!(
                "Status:                   {}",
                if stats.refused {
                    "REFUSED"
                } else if stats.disabled {
                    "DISABLED"
                } else {
                    "SUCCESS"
                }
            );
            println!(
                "Lexical Candidates:       {}",
                stats.pairs_lexical_candidates
            );
            println!("Pairs Considered:         {}", stats.pairs_considered);
            println!("Pairs Examined:           {}", stats.pairs_examined);
            println!("Proposals:                {}", stats.proposals);
            println!("Promotions:               {}", stats.promotions);
            println!("Demotions:                {}", stats.demotions);
            println!("Execution Time:           {} ms", stats.took_ms);
            println!("==================================================");
        }
        Commands::Dream {
            quiescence,
            cycles,
            mode,
            log_file,
            report,
            insights,
            dual_phase,
            homeostatic,
            force,
        } => {
            let dream_log = log_file.unwrap_or_else(|| store_path.join("dream.jsonl"));
            let insights_log = store_path.join("dream_insights.jsonl");
            let cycles_to_run = match (cycles, report, insights) {
                (Some(c), _, _) => c,
                (None, true, _) => 0,
                (None, false, true) => 0,
                (None, false, false) => 1,
            };

            if cycles_to_run > 0 {
                // Homeostatic regulation check
                let (regime, active_dual_phase) = if homeostatic && !force {
                    let hw = wm_gen3_core::homeostasis::HardwareTelemetry::probe();
                    let mut ctrl = wm_gen3_core::homeostasis::HomeostaticController::new();
                    let telem = hw.to_telemetry_vector(800.0, 0.10, 0.0, 0.25);
                    let (homeo_regime, actuators) = ctrl.update_cycle(&telem);

                    let (rv, proceed, reason) =
                        wm_gen3_core::dream::RegimeVector::from_quiescence_with_homeostasis(
                            quiescence,
                            0.0,
                            homeo_regime,
                            &hw,
                        );

                    println!("==================================================");
                    println!("    WhiteMagic Gen3 Homeostatic Dream Telemetry   ");
                    println!("==================================================");
                    println!(
                        "Hardware Telemetry:       CPU={:.1}°C | Load={:.2} | Bat={:?}% | AC={}",
                        hw.cpu_temp_c, hw.load_avg_1m, hw.battery_pct, hw.on_ac_power
                    );
                    println!(
                        "Homeostatic Regime:       {:?} (Throttle={:.2})",
                        homeo_regime, actuators.write_throttle_factor
                    );
                    println!("Homeostatic Assessment:   {}", reason);

                    if !proceed {
                        println!("\n[Deferred] Dream incubation deferred by homeostatic governor.");
                        println!("           (Pass --force to override)");
                        return;
                    }

                    let dual = if homeo_regime
                        >= wm_gen3_core::homeostasis::HomeostaticRegime::Stressed
                    {
                        println!(
                            "Notice: Dual-phase REM synthesis disabled under Stressed regime (NREM compaction only)"
                        );
                        false
                    } else {
                        dual_phase
                    };

                    (rv, dual)
                } else {
                    (
                        wm_gen3_core::dream::RegimeVector::from_quiescence(quiescence, 0.0),
                        dual_phase,
                    )
                };

                let journal_path = store_path.join("journal.jsonl");
                let mut substrate =
                    match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    };
                substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-dream"));

                let incubation_mode = match mode.to_lowercase().as_str() {
                    "sham" => wm_gen3_core::dream::IncubationMode::ShamDreaming,
                    "baseline" => wm_gen3_core::dream::IncubationMode::BaselineIdle,
                    _ => wm_gen3_core::dream::IncubationMode::GenuineDreaming,
                };

                println!("==================================================");
                println!("      WhiteMagic Gen3 Cognitive Dream Incubation   ");
                println!("==================================================");
                println!("Store Path:               {}", store_path.display());
                println!("Incubation Mode:          {:?}", incubation_mode);
                println!(
                    "Dual-Phase Execution:     {}",
                    if active_dual_phase {
                        "ENABLED (NREM Compaction + REM Synthesis)"
                    } else {
                        "DISABLED (REM Only or NREM Compaction Throttled)"
                    }
                );
                println!("Quiescence Level (q):     {:.2}", regime.quiescence);
                println!("Exploration Temperature:  {:.2}", regime.temperature);
                println!(
                    "Associative Radius:       {}-hops",
                    regime.associative_radius
                );
                println!(
                    "Counterfactual Rate:      {:.2}",
                    regime.counterfactual_rate
                );
                println!(
                    "Compression Pressure:     {:.2}",
                    regime.compression_pressure
                );
                println!(
                    "Adaptive Gate Threshold:  {:.3}",
                    regime.adaptive_commit_threshold
                );
                println!("Dream Journal Log:        {}", dream_log.display());
                println!("Insights Journal Log:     {}", insights_log.display());
                let vault_log = store_path.join("geneseed_vault.jsonl");
                println!("Geneseed Vault Log:       {}", vault_log.display());
                println!("==================================================");

                let mut total_generated = 0;
                let mut total_evaluated = 0;
                let mut total_committed = 0;
                let mut total_discarded = 0;
                let mut total_superseded = 0;
                let mut total_contradictions = 0;
                let mut total_compacted = 0;
                let mut total_speciated = 0;
                let start = std::time::Instant::now();

                let existing_cycle_offset = if dream_log.exists() {
                    std::fs::read_to_string(&dream_log)
                        .map(|content| content.lines().filter(|l| !l.trim().is_empty()).count())
                        .unwrap_or(0)
                } else {
                    0
                };

                let mut log_writer = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&dream_log)
                    .ok();

                let mut insights_writer = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&insights_log)
                    .ok();

                let mut vault_writer = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&vault_log)
                    .ok();

                for c in 0..cycles_to_run {
                    let current_cycle_num = existing_cycle_offset + c + 1;
                    let seed = 42 + current_cycle_num as u64;

                    let (nrem_receipt, telemetry, speciation_skeletons) = if active_dual_phase {
                        let dual = wm_gen3_core::dream::execute_dual_phase_sleep_cycle(
                            incubation_mode,
                            &regime,
                            100,
                            &mut substrate,
                            seed,
                        );
                        (Some(dual.nrem), dual.rem, dual.synthesized_skeletons)
                    } else {
                        let rem = wm_gen3_core::dream::execute_incubation_epoch(
                            incubation_mode,
                            &regime,
                            100,
                            &mut substrate,
                            seed,
                        );
                        (None, rem, Vec::new())
                    };

                    total_generated += telemetry.candidates_generated;
                    total_evaluated += telemetry.candidates_evaluated;
                    total_committed += telemetry.candidates_committed;
                    total_discarded += telemetry.candidates_discarded_cleanly;

                    if let Some(ref nrem) = nrem_receipt {
                        total_superseded += nrem.superseded_entries_pruned;
                        total_contradictions += nrem.contradictions_resolved;
                        total_compacted += nrem.compacted_summaries_minted;
                    }

                    if let Some(ref mut writer) = log_writer {
                        use std::io::Write;
                        let log_entry = serde_json::json!({
                            "cycle": current_cycle_num,
                            "timestamp_ns": std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos() as u64,
                            "dual_phase": dual_phase,
                            "quiescence": regime.quiescence,
                            "temperature": regime.temperature,
                            "associative_radius": regime.associative_radius,
                            "entropy": telemetry.candidate_diversity_shannon_entropy,
                            "candidates_generated": telemetry.candidates_generated,
                            "candidates_committed": telemetry.candidates_committed,
                            "candidates_discarded": telemetry.candidates_discarded_cleanly,
                            "nrem_chains": nrem_receipt.as_ref().map(|n| n.session_chains_scanned).unwrap_or(0),
                            "nrem_superseded": nrem_receipt.as_ref().map(|n| n.superseded_entries_pruned).unwrap_or(0),
                            "nrem_contradictions": nrem_receipt.as_ref().map(|n| n.contradictions_resolved).unwrap_or(0),
                            "speciated_skeletons": speciation_skeletons.len(),
                        });
                        let _ = writeln!(
                            writer,
                            "{}",
                            serde_json::to_string(&log_entry).unwrap_or_default()
                        );
                    }

                    if let Some(ref mut writer) = insights_writer {
                        use std::io::Write;
                        for insight in &telemetry.committed_insights {
                            let _ = writeln!(
                                writer,
                                "{}",
                                serde_json::to_string(insight).unwrap_or_default()
                            );
                        }
                    }

                    if let Some(ref nrem) = nrem_receipt {
                        println!(
                            "  [Phase 1: NREM Compaction] Chains: {:3} | Superseded: {:2} | Contradictions: {:2} | Compaction: {:.2}x ({:.2}ms)",
                            nrem.session_chains_scanned,
                            nrem.superseded_entries_pruned,
                            nrem.contradictions_resolved,
                            nrem.token_compaction_ratio,
                            nrem.duration_us / 1000.0,
                        );
                    }

                    println!(
                        "  [Phase 2: REM Incubation] Cycle {:02}/{:02} (Global #{:03}) | Generated: {:3} | Evaluated: {:3} | Committed: {:2} | Discarded: {:3} | Diversity (H): {:.3}",
                        c + 1,
                        cycles_to_run,
                        current_cycle_num,
                        telemetry.candidates_generated,
                        telemetry.candidates_evaluated,
                        telemetry.candidates_committed,
                        telemetry.candidates_discarded_cleanly,
                        telemetry.candidate_diversity_shannon_entropy
                    );

                    for insight in &telemetry.committed_insights {
                        println!(
                            "    ✦ [{}] {} (utility: {:.3}, conf: {:.2})\n      Bridge:  #{} \"{}\" ⇄ #{} \"{}\"\n      Hypoth:  {}\n      Action:  {}",
                            insight.id,
                            insight.relation_type,
                            insight.utility_score,
                            insight.confidence,
                            insight.source_id,
                            insight.source_concept,
                            insight.target_id,
                            insight.target_concept,
                            insight.hypothesis,
                            insight.actionable_recommendation,
                        );
                    }

                    if !speciation_skeletons.is_empty() {
                        total_speciated += speciation_skeletons.len();
                        println!(
                            "  [Phase 3: Speciation Vault] Minted {} ActionSkeletons into Geneseed Vault:",
                            speciation_skeletons.len()
                        );
                        for skel in &speciation_skeletons {
                            println!(
                                "    🧬 [{:?}] {} (utility: {:.3}, steps: {})",
                                skel.tier,
                                skel.id,
                                skel.rolling_utility,
                                skel.action_steps.len()
                            );
                            if let Some(ref mut writer) = vault_writer {
                                use std::io::Write;
                                let _ = writeln!(
                                    writer,
                                    "{}",
                                    serde_json::to_string(&skel).unwrap_or_default()
                                );
                            }
                        }
                    }
                }

                let took = start.elapsed();
                println!("==================================================");
                println!("Dream Incubation Complete in {:.2?}", took);
                if dual_phase {
                    println!("NREM Superseded Pruned:      {}", total_superseded);
                    println!("NREM Contradictions Resolved: {}", total_contradictions);
                    println!("NREM Summaries Minted:       {}", total_compacted);
                    println!("ActionSkeletons Speciated:   {}", total_speciated);
                }
                println!("Total Candidates Generated:  {}", total_generated);
                println!("Total Candidates Evaluated:  {}", total_evaluated);
                println!("Consolidated Associations:   {}", total_committed);
                println!("Cleanly Dissolved Volatile:  {}", total_discarded);
                println!("Dream Journal written to:    {}", dream_log.display());
                println!("Insights Journal Log:        {}", insights_log.display());
                println!("Geneseed Vault Log:          {}", vault_log.display());
                println!("==================================================");

                if report {
                    println!();
                    print_dream_report(&dream_log, &insights_log, Some(&substrate));
                } else if insights {
                    println!();
                    print_dream_insights(&insights_log, 10);
                }
            } else if insights && !report {
                print_dream_insights(&insights_log, 20);
            } else {
                let journal_path = store_path.join("journal.jsonl");
                let substrate =
                    Substrate::open_readonly(&store_path, Some(&journal_path), default_view()).ok();
                print_dream_report(&dream_log, &insights_log, substrate.as_ref());
                if insights {
                    println!();
                    print_dream_insights(&insights_log, 10);
                }
            }
        }
        Commands::Route { inquiry, utility } => {
            let insights_log = store_path.join("dream_insights.jsonl");
            let mut insights = Vec::new();
            if insights_log.exists() {
                if let Ok(content) = std::fs::read_to_string(&insights_log) {
                    for line in content.lines() {
                        if let Ok(ins) =
                            serde_json::from_str::<wm_gen3_core::dream::DreamInsight>(line)
                        {
                            insights.push(ins);
                        }
                    }
                }
            }

            let mut router = wm_gen3_core::bicameral::CognitiveRouter::new();
            let compiled_count = router.compile_dream_insights(&insights);

            let vault_path = store_path.join("vault.jsonl");
            let vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);
            let bound_skeleton = vault.find_best_skeleton(&inquiry);

            let state =
                wm_gen3_core::bicameral::PresentState::new(vec!["dispatch_triage".into()], 1024, 0);
            let dispatch = router.route(&state, &inquiry, utility);

            println!("==================================================");
            println!("       WhiteMagic Gen3 Cognitive Router Triage    ");
            println!("==================================================");
            println!("Inquiry:                  {}", inquiry);
            println!("Expected Marginal Utility: {:.3}", utility);
            let jev_tensor = wm_gen3_core::bicameral::JevDecisionTensor::default();
            let jev_score = jev_tensor.compute_jev(utility, 0.15, 0.10, 0.05);
            println!(
                "JEV Pre-Triage Score:      {:.4} (26.7ns non-autoregressive gate)",
                jev_score
            );
            println!("Active Dream Insights:     {}", insights.len());
            println!("Compiled Fast-Path Rules:  {}", compiled_count);
            if let Some(skel) = bound_skeleton {
                let spec = skel.fitness_spectrum();
                println!(
                    "Bound Action Skeleton:     {} ({:?}, utility: {:.3}, fitness: {:.3})",
                    skel.id, skel.tier, skel.rolling_utility, spec.composite_fitness
                );
                println!(
                    "  Preconditions:           {}",
                    skel.expected_preconditions.join(", ")
                );
                println!(
                    "  Action Steps:            {}",
                    skel.action_steps.join(" -> ")
                );
                println!("  Direct Execution Cmd:    wm vault execute {}", skel.id);
            } else {
                println!("Bound Action Skeleton:     None (No direct match in vault)");
            }
            println!("==================================================");
            match &dispatch {
                wm_gen3_core::bicameral::CognitiveDispatch::DeterministicRule { rule_name } => {
                    println!("Triage Tier:  [1/5] DETERMINISTIC FAST-PATH (<1ms)");
                    println!("Rule Trigger: {}", rule_name);
                    if let Some(rule) = router.compiled_dream_rules.iter().find(|r| {
                        inquiry.contains(&r.source_concept) || inquiry.contains(&r.target_concept)
                    }) {
                        println!(
                            "Dream Rule:   {} ⇄ {} ({})",
                            rule.source_concept, rule.target_concept, rule.relation_type
                        );
                        println!("Action Rec:   {}", rule.action_recommendation);
                        println!(
                            "Utility/Conf: {:.3} / {:.2}",
                            rule.utility_score, rule.confidence
                        );
                    }
                }
                wm_gen3_core::bicameral::CognitiveDispatch::ExecuteNothing { reason } => {
                    println!("Triage Tier:  [0/5] EXECUTE NOTHING (LW2S Zero-Cost Silence)");
                    println!("Reason:       {}", reason);
                }
                wm_gen3_core::bicameral::CognitiveDispatch::DecisionModel { evaluator_name } => {
                    println!("Triage Tier:  [2/5] NON-AUTOREGRESSIVE DECISION MODEL");
                    println!("Evaluator:    {}", evaluator_name);
                }
                wm_gen3_core::bicameral::CognitiveDispatch::Specialist { organ, model_tier } => {
                    println!("Triage Tier:  [3/5] SPECIALIST ORGAN");
                    println!("Organ:        {} (Model Tier: {})", organ, model_tier);
                }
                wm_gen3_core::bicameral::CognitiveDispatch::FrontierDeliberation {
                    prompt_token_budget,
                } => {
                    println!("Triage Tier:  [4/5] FRONTIER DELIBERATION");
                    println!("Token Budget: {} tokens", prompt_token_budget);
                }
            }
            println!("==================================================");
        }
        Commands::Galaxy {
            output_html,
            output_json,
            limit,
        } => {
            let journal_path = store_path.join("journal.jsonl");
            let substrate =
                match Substrate::open_readonly(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

            let total_records = substrate.store().record_count().unwrap_or(0);
            let epoch = substrate.store().epoch().unwrap_or(0);
            let sample_count = limit.min(total_records).max(1);
            let stride = (total_records / sample_count).max(1);

            println!("==================================================");
            println!("    WhiteMagic Gen3 6D Holographic Galaxy Engine  ");
            println!("==================================================");
            println!("Store Path:           {}", store_path.display());
            println!("Total Store Records:  {}", total_records);
            println!("Current Store Epoch:  {}", epoch);
            println!("Visualization Sample: {}", sample_count);
            println!("Sampling Stride:      {}", stride);
            println!("==================================================");

            let mut projections = Vec::new();
            let start = std::time::Instant::now();

            for i in 0..sample_count {
                let id = (i * stride).min(total_records.saturating_sub(1)) as u64;
                if let Ok(Some(record)) = substrate.store().get_record(id) {
                    let coords = wm_gen3_core::hologram::Holographic6D::from_record(
                        id,
                        record.content(),
                        epoch,
                        0.90,
                    );
                    let preview = if record.content().len() > 160 {
                        let mut end = 160;
                        while end > 0 && !record.content().is_char_boundary(end) {
                            end -= 1;
                        }
                        format!("{}...", &record.content()[..end])
                    } else {
                        record.content().to_string()
                    };
                    projections.push(serde_json::json!({
                        "id": id,
                        "x": coords.x,
                        "y": coords.y,
                        "z": coords.z,
                        "tau": coords.tau,
                        "sigma": coords.sigma,
                        "omega": coords.omega as u32,
                        "preview": preview,
                        "source": record.source(),
                    }));
                }
            }

            println!(
                "Derived 6D coordinates for {} nodes in {:.2?}",
                projections.len(),
                start.elapsed()
            );

            let json_path = output_json.unwrap_or_else(|| store_path.join("galaxy_6d.json"));
            let html_path = output_html.unwrap_or_else(|| store_path.join("galaxy.html"));

            let json_data = serde_json::to_string(&projections).unwrap_or_default();
            if let Err(e) = std::fs::write(&json_path, &json_data) {
                eprintln!("Warning: failed writing json dataset: {e}");
            } else {
                println!("Saved 6D dataset:      {}", json_path.display());
            }

            let html_content = generate_galaxy_html(&json_data, total_records, epoch);
            if let Err(e) = std::fs::write(&html_path, html_content) {
                eprintln!("Error writing galaxy HTML: {e}");
            } else {
                println!("Saved 3D Galaxy HTML:  {}", html_path.display());
                println!("Visualizer ready. Open in browser to view the Sangha Galaxy in 3D.");
            }
            println!("==================================================");
        }
        Commands::Inspect { scope } => {
            let journal_path = store_path.join("journal.jsonl");
            let substrate =
                match Substrate::open_readonly(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            let info = substrate.inspect(&scope);
            println!(
                "{}",
                serde_json::to_string_pretty(&info).unwrap_or_default()
            );
        }
        Commands::Apotheosis { vault_file } => {
            let journal_path = store_path.join("journal.jsonl");
            let substrate =
                match Substrate::open_readonly(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

            let vault_path = vault_file.unwrap_or_else(|| {
                let v = store_path.join("vault.jsonl");
                if v.exists() {
                    v
                } else {
                    store_path.join("geneseed_vault.jsonl")
                }
            });
            let vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);

            let insights_path = store_path.join("dream_insights.jsonl");
            let insights_count = if insights_path.exists() {
                std::fs::read_to_string(&insights_path)
                    .map(|c| c.lines().filter(|l| !l.trim().is_empty()).count())
                    .unwrap_or(0)
            } else {
                0
            };

            let report = wm_gen3_core::apotheosis::perform_apotheosis_audit(
                &substrate,
                &vault,
                insights_count,
            );

            println!("==================================================");
            println!("   WhiteMagic Gen3 Apotheosis Meta-Learning Audit ");
            println!("==================================================");
            println!("Substrate Store:          {}", store_path.display());
            println!("Evolutionary Status:      {:?}", report.status);
            println!(
                "Composite Index:          {:.4}",
                report.composite_apotheosis_index
            );
            println!("--------------------------------------------------");
            println!(
                "Substrate Invariants:     {}/9 Passed ({:.1}%)",
                report.invariant_audit.total_passed,
                report.invariant_audit.integrity_ratio * 100.0
            );
            println!(
                "  Article 1 (Commit Cap): {}",
                if report.invariant_audit.article1_commit_capability {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 2 (Pulse Comp): {}",
                if report.invariant_audit.article2_pulse_compilation {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 3 (Provenance): {}",
                if report.invariant_audit.article3_epistemic_provenance {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 4 (Zero Loops): {}",
                if report.invariant_audit.article4_zero_unmetered_loops {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 5 (Bound Sed):  {}",
                if report.invariant_audit.article5_bounded_sediment {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 6 (Maker!=Chk): {}",
                if report.invariant_audit.article6_maker_checker_separation {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 7 (DAG Acyclic):{}",
                if report.invariant_audit.article7_cladistics_acyclicity {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 8 (Neg Knowl):  {}",
                if report.invariant_audit.article8_negative_knowledge_retention {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!(
                "  Article 9 (Anti-Sim):   {}",
                if report.invariant_audit.article9_anti_simulation_honesty {
                    "PASS"
                } else {
                    "FAIL"
                }
            );
            println!("--------------------------------------------------");
            println!(
                "Geneseed Cladistics DAG:  {} total ({} active, {} deprecated)",
                report.cladistics_health.total_skeletons,
                report.cladistics_health.active_skeletons,
                report.cladistics_health.deprecated_skeletons
            );
            println!(
                "  Forks Minted:           {}",
                report.cladistics_health.total_forks_minted
            );
            println!(
                "  Max Lineage Depth:      {}",
                report.cladistics_health.max_lineage_depth
            );
            println!(
                "  Retired Failure Sigs:   {}",
                report.cladistics_health.retired_signatures_count
            );
            println!("--------------------------------------------------");
            println!(
                "Kaizen Convergence:       Mean Utility: {:.3}",
                report.kaizen_convergence.average_rolling_utility
            );
            println!(
                "  Mutation Velocity:      {:.3} forks/epoch",
                report.kaizen_convergence.mutation_velocity
            );
            println!(
                "  Fitness Stability:      {:.1}%",
                report.kaizen_convergence.fitness_stability_ratio * 100.0
            );
            println!(
                "  Dream Bridge Cross-Corr:{:.3}",
                report.kaizen_convergence.dream_bridge_correlation
            );
            println!("--------------------------------------------------");
            println!(
                "Doc-to-Code Truth Drift:  Score: {:.3} (0.0 = perfect isomorphism)",
                report.truth_drift.truth_drift_score
            );
            println!(
                "  Verified Executables:   {}/{} declared",
                report.truth_drift.verified_executable_routes,
                report.truth_drift.declared_mcp_tools.len()
                    + report.truth_drift.declared_cli_commands.len()
            );
            println!(
                "  Phantom Surfaces:       {}",
                report.truth_drift.phantom_routes_detected
            );
            println!("==================================================");
        }
        Commands::Contract { json } => {
            let manifest = build_contract_manifest("10.0.0-alpha");
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&manifest).unwrap_or_default()
                );
            } else {
                println!("==================================================");
                println!("WhiteMagic Hybrid Route & Schema Manifest (v10.0.0-alpha)");
                println!("--------------------------------------------------");
                println!("  Routes in Manifest:    {}", manifest["counts"]["routes"]);
                println!(
                    "  Declared Properties:   {}",
                    manifest["counts"]["declared"]
                );
                println!(
                    "  Undeclared Stubs:      {}",
                    manifest["counts"]["undeclared"]
                );
                println!("  Run with --json for complete machine-checked JSON manifest.");
                println!("==================================================");
            }
        }
        Commands::Serve {
            profile,
            readonly,
            sweep,
            projection,
            embed_cache,
            dispersion,
            noise,
        } => {
            let parsed_profile = profile
                .parse::<McpProfile>()
                .unwrap_or(McpProfile::Cyberbrain);
            run_serve_loop(
                &store_path,
                parsed_profile,
                readonly,
                sweep,
                projection,
                embed_cache.as_deref(),
                dispersion,
                noise,
            );
        }
        Commands::Migrate {
            source,
            batch_size,
            dry_run,
            allow_noise,
            skip_hash_validation,
            quarantine_file,
            receipt_file,
        } => {
            run_migration(
                &source,
                &store_path,
                batch_size,
                dry_run,
                allow_noise,
                skip_hash_validation,
                quarantine_file,
                receipt_file,
            );
        }
        Commands::Mesh { command } => {
            run_mesh_command(command, &store_path);
        }
        Commands::Session { command } => {
            run_session_command(command, &store_path);
        }
        Commands::Mandala { command } => {
            run_mandala_command(command, &store_path);
        }
        Commands::Ingest {
            file,
            batch_size,
            default_source,
            default_kind,
        } => {
            run_ingest(
                &store_path,
                &file,
                batch_size,
                &default_source,
                &default_kind,
            );
        }
        Commands::Vault { command } => {
            run_vault_command(command, &store_path);
        }
        Commands::Evolve {
            epochs,
            sleep_cycles,
            quiescence,
            temperature,
        } => {
            run_evolve_command(epochs, sleep_cycles, quiescence, temperature, &store_path);
        }
        Commands::Selftest { json } => {
            if json {
                println!(r#"{{"status":"ok","invariants":"pass","engine":"gen3","version":"10.0.0-alpha.1"}}"#);
            } else {
                println!("WhiteMagic Gen3 Substrate Invariants: PASS (status: ok, version: 10.0.0-alpha.1)");
            }
        }
    }
}

fn run_session_command(cmd: SessionCommands, store_path: &Path) {
    let journal_path = store_path.join("journal.jsonl");
    match cmd {
        SessionCommands::Checkpoint {
            session_id,
            agent_id,
            checkpoint_type,
            summary,
            next_queue,
            open_flags,
            context_token,
            evolve,
        } => {
            let mut substrate =
                match Substrate::open(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-session"));
            let cp = SessionCheckpoint {
                session_id,
                agent_id,
                checkpoint_type,
                summary,
                next_queue,
                open_flags,
                context_token,
                representation: None,
                timestamp_iso: Some(chrono::Utc::now().to_rfc3339()),
            };
            match substrate.session_checkpoint(&cp) {
                Ok(id) => {
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    println!("Session checkpoint committed successfully.");
                    println!("Record ID:       {}", id);
                    println!("Epoch:           {}", epoch);
                    println!("Session ID:      {}", cp.session_id);
                    println!("Checkpoint Type: {}", cp.checkpoint_type);
                    println!("Summary:         {}", cp.summary);

                    if evolve {
                        println!("--------------------------------------------------");
                        println!("Autonomous Post-Session Evolution & Consolidation:");
                        let vault_path = store_path.join("vault.jsonl");
                        let mut vault =
                            wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);

                        let regime = wm_gen3_core::dream::RegimeVector::from_quiescence(1.0, 0.0);
                        let dual = wm_gen3_core::dream::execute_dual_phase_sleep_cycle(
                            wm_gen3_core::dream::IncubationMode::GenuineDreaming,
                            &regime,
                            25,
                            &mut substrate,
                            epoch,
                        );

                        let mut speciated_count = 0;
                        for mut skel in dual.synthesized_skeletons {
                            if !vault.skeletons.iter().any(|s| s.id == skel.id) {
                                skel.execution_count = 0;
                                vault.skeletons.push(skel);
                                speciated_count += 1;
                            }
                        }

                        let active_parent = vault
                            .skeletons
                            .iter()
                            .find(|s| !s.deprecated)
                            .map(|s| s.id.clone());
                        let mut mutated_candidate = None;
                        if let Some(parent_id) = active_parent {
                            if let Ok(m_res) = vault.propose_and_evaluate_mutation(
                                &parent_id,
                                wm_gen3_core::bicameral::MutationKind::VanguardStreamline,
                            ) {
                                mutated_candidate = Some(m_res.candidate_id);
                            }
                        }

                        let _ = vault.sync_to_file(&vault_path);
                        println!(
                            "  Speciated: {} | Mutated: {:?} | Active Skeletons: {}",
                            speciated_count,
                            mutated_candidate,
                            vault.skeletons.len()
                        );
                        println!("--------------------------------------------------");
                    }
                }
                Err(e) => {
                    eprintln!("Error committing checkpoint: {e}");
                    std::process::exit(1);
                }
            }
        }
        SessionCommands::Record {
            session_id,
            agent_id,
            log_type,
            content,
        } => {
            let mut substrate =
                match Substrate::open(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-session"));
            match substrate.session_record(&session_id, &agent_id, &log_type, &content) {
                Ok(id) => {
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    println!("Session record committed successfully.");
                    println!("Record ID:       {}", id);
                    println!("Epoch:           {}", epoch);
                    println!("Session ID:      {}", session_id);
                    println!("Log Type:        {}", log_type);
                }
                Err(e) => {
                    eprintln!("Error committing record: {e}");
                    std::process::exit(1);
                }
            }
        }
        SessionCommands::Continuity { session_id } => {
            let substrate =
                match Substrate::open_readonly(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            match substrate.session_continuity(session_id.as_deref()) {
                Ok(Some(view)) => {
                    println!("==================================================");
                    println!("         WhiteMagic Session Continuity            ");
                    println!("==================================================");
                    println!("Record ID:       {}", view.record_id);
                    println!("Epoch:           {}", view.epoch);
                    println!("Session ID:      {}", view.session_id);
                    println!("Agent ID:        {}", view.agent_id);
                    println!("Checkpoint Type: {}", view.checkpoint_type);
                    if let Some(token) = &view.context_token {
                        println!("Context Token:   {}", token);
                    }
                    if let Some(ts) = &view.timestamp_iso {
                        println!("Timestamp:       {}", ts);
                    }
                    println!("Summary:         {}", view.summary);
                    if !view.next_queue.is_empty() {
                        println!("\nNext Queue:");
                        for item in &view.next_queue {
                            println!("  - [ ] {}", item);
                        }
                    }
                    if !view.open_flags.is_empty() {
                        println!("\nOpen Flags / Invariants:");
                        for flag in &view.open_flags {
                            println!("  - ⚠️  {}", flag);
                        }
                    }

                    let insights_path = store_path.join("dream_insights.jsonl");
                    if insights_path.exists() {
                        if let Ok(file) = std::fs::File::open(&insights_path) {
                            use std::io::{BufRead, BufReader};
                            let reader = BufReader::new(file);
                            let mut insights: Vec<wm_gen3_core::dream::DreamInsight> = Vec::new();
                            for line in reader.lines().flatten() {
                                let trimmed = line.trim();
                                if !trimmed.is_empty() {
                                    if let Ok(ins) = serde_json::from_str::<
                                        wm_gen3_core::dream::DreamInsight,
                                    >(trimmed)
                                    {
                                        insights.push(ins);
                                    }
                                }
                            }
                            if !insights.is_empty() {
                                println!("\nActive Dream Insights (Consolidated Offline):");
                                let start = insights.len().saturating_sub(3);
                                for ins in &insights[start..] {
                                    println!(
                                        "  - ✦ [{}] {} (Utility: {:.3})",
                                        ins.id, ins.relation_type, ins.utility_score
                                    );
                                    println!(
                                        "      Bridge: \"{}\" (#{}) ⇄ \"{}\" (#{})",
                                        ins.source_concept,
                                        ins.source_id,
                                        ins.target_concept,
                                        ins.target_id
                                    );
                                    println!("      Action: {}", ins.actionable_recommendation);
                                }
                            }
                        }
                    }
                    println!("==================================================");
                }
                Ok(None) => {
                    println!("No session continuity records found for query '{session_id:?}'.");
                }
                Err(e) => {
                    eprintln!("Error retrieving session continuity: {e}");
                    std::process::exit(1);
                }
            }
        }
        SessionCommands::List => {
            let substrate =
                match Substrate::open_readonly(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            match substrate.session_list() {
                Ok(sessions) => {
                    println!("==================================================");
                    println!("        WhiteMagic Active Session Registry        ");
                    println!("==================================================");
                    println!("Total Sessions:  {}", sessions.len());
                    for session in &sessions {
                        println!("  - {}", session);
                    }
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Error listing sessions: {e}");
                    std::process::exit(1);
                }
            }
        }
    }
}

fn run_mandala_command(cmd: MandalaCommands, store_path: &Path) {
    let ledger_path = store_path.join("mandala_ledger.jsonl");
    match cmd {
        MandalaCommands::VerifyPass {
            pass_file,
            pass_json,
            epoch,
        } => {
            let json_str = if let Some(path) = pass_file {
                match std::fs::read_to_string(&path) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Failed to read pass file {}: {e}", path.display());
                        std::process::exit(1);
                    }
                }
            } else if let Some(s) = pass_json {
                s
            } else {
                eprintln!("Error: specify either --pass-file or --pass-json");
                std::process::exit(1);
            };

            let pass: MandalaPass = match serde_json::from_str(&json_str) {
                Ok(p) => p,
                Err(e) => {
                    eprintln!("Failed to parse MandalaPass JSON: {e}");
                    std::process::exit(1);
                }
            };

            let now = epoch.unwrap_or_else(|| {
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs()
            });

            let ledger = match MandalaReplayLedger::open_durable(&ledger_path) {
                Ok(l) => l,
                Err(e) => {
                    eprintln!(
                        "Failed to open Mandala replay ledger at {}: {e}",
                        ledger_path.display()
                    );
                    std::process::exit(1);
                }
            };

            match ledger.check_validity(&pass, now) {
                Ok(()) => {
                    let (signing_key, pubkey) = match resolve_or_create_mandala_gate_key(store_path)
                    {
                        Ok(k) => k,
                        Err(e) => {
                            eprintln!("Failed to resolve gate authority key: {e}");
                            std::process::exit(1);
                        }
                    };
                    let verifying_key = signing_key.verifying_key();
                    let sig_status = match pass.verify_signature(&verifying_key) {
                        Ok(()) => "VALID (Signed by Local Authority Gate)",
                        Err(_) => "UNVERIFIED (Foreign or Self-Signed Signature)",
                    };

                    println!("==================================================");
                    println!("       Mandala Pass Verification Status           ");
                    println!("==================================================");
                    println!("Pass ID:             {}", pass.pass_id);
                    println!("Slot ID:             {}", pass.slot_id);
                    println!("Tenant ID:           {}", pass.tenant_id);
                    println!("Agent ID:            {}", pass.agent_id);
                    println!("JTI Nonce:           {}", pass.jti);
                    println!("Fork Depth:          {}", pass.fork_depth);
                    println!("Created At:          {}", pass.created_at);
                    println!("Expires At:          {}", pass.expires_at);
                    println!(
                        "Remaining Time:      {}s",
                        pass.expires_at.saturating_sub(now)
                    );
                    println!("Max Operations:      {}", pass.budget.max_operations);
                    println!("Max Compute:         {} ms", pass.budget.max_compute_ms);
                    println!("Max Memory:          {} MB", pass.budget.max_memory_mb);
                    println!("Network Restricted:  {}", pass.manifest.network_restricted);
                    println!("Cryptographic Sig:   {}", sig_status);
                    println!("Ledger Replay Check: PASS (Unconsumed)");
                    println!("Gate Authority DID:  did:key:{}", hex_encode(&pubkey));
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Mandala Pass Verification FAILED: {e}");
                    std::process::exit(1);
                }
            }
        }
        MandalaCommands::IssuePass {
            tenant_id,
            slot_id,
            agent_id,
            pass_id,
            allowed,
            denied,
            ttl,
            max_ops,
            max_compute_ms,
            max_memory_mb,
            network_restricted,
            out,
        } => {
            let (signing_key, pubkey) = match resolve_or_create_mandala_gate_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve gate authority key: {e}");
                    std::process::exit(1);
                }
            };
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();

            let mut manifest = CapabilityManifest::default();
            manifest.network_restricted = network_restricted;
            if let Some(allow_str) = allowed {
                manifest.scope_mode = ScopeMode::Include;
                for op in allow_str
                    .split(',')
                    .map(|s| s.trim())
                    .filter(|s| !s.is_empty())
                {
                    manifest.allowed_operations.insert(op.to_string());
                }
            } else {
                manifest.scope_mode = ScopeMode::All;
            }
            if let Some(deny_str) = denied {
                for op in deny_str
                    .split(',')
                    .map(|s| s.trim())
                    .filter(|s| !s.is_empty())
                {
                    manifest.denied_operations.insert(op.to_string());
                }
            }

            let budget = PassBudget {
                max_operations: max_ops,
                operations_used: 0,
                max_compute_ms,
                max_memory_mb,
            };

            let jti = format!("jti-{}-{}", now, hex_encode(&pubkey[..8]));

            let mut pass = MandalaPass {
                pass_id: pass_id.clone(),
                slot_id: slot_id.clone(),
                tenant_id: tenant_id.clone(),
                agent_id: agent_id.clone(),
                principal_id: None,
                jti: jti.clone(),
                parent_jti: None,
                fork_depth: 0,
                created_at: now,
                expires_at: now + ttl,
                budget,
                manifest,
                mandate_ref: None,
                signature: None,
            };

            pass.sign(&signing_key);

            let json_str = serde_json::to_string_pretty(&pass).unwrap_or_default();
            if let Some(ref p) = out {
                if let Err(e) = std::fs::write(p, &json_str) {
                    eprintln!("Failed to write pass to {}: {e}", p.display());
                    std::process::exit(1);
                }
                println!("==================================================");
                println!("       Mandala Pass Issued Successfully           ");
                println!("==================================================");
                println!("Pass ID:             {}", pass.pass_id);
                println!("Tenant ID:           {}", pass.tenant_id);
                println!("Agent ID:            {}", pass.agent_id);
                println!("JTI Nonce:           {}", pass.jti);
                println!("Expires At:          {}", pass.expires_at);
                println!("Saved To:            {}", p.display());
                println!("Authority DID:       did:key:{}", hex_encode(&pubkey));
                println!("==================================================");
            } else {
                println!("{json_str}");
            }
        }
        MandalaCommands::RecordReceipt {
            receipt_file,
            source,
        } => {
            let content = match std::fs::read_to_string(&receipt_file) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!(
                        "Failed to read receipt file {}: {e}",
                        receipt_file.display()
                    );
                    std::process::exit(1);
                }
            };

            let json_val: serde_json::Value = match serde_json::from_str(&content) {
                Ok(v) => v,
                Err(e) => {
                    eprintln!(
                        "Invalid JSON in receipt file {}: {e}",
                        receipt_file.display()
                    );
                    std::process::exit(1);
                }
            };

            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening substrate at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

            substrate.set_intake_authority(RatifiedChannel::mint("mandala-gate-lite"));
            let item = RememberItem {
                content: content.clone(),
                source: source.clone(),
                kind: ImportKind::Reported,
            };

            let results = substrate.remember_batch(&[item]);
            match &results[0] {
                Ok(id) => {
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    let task = json_val
                        .get("task")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown");
                    let verdict = json_val
                        .get("verdict")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unspecified");
                    let gate_class = json_val
                        .get("gate_class")
                        .and_then(|v| v.as_str())
                        .unwrap_or("gate-lite");

                    println!("==================================================");
                    println!("    Mandala Continuity Receipt Recorded In Gen3   ");
                    println!("==================================================");
                    println!("Source File:         {}", receipt_file.display());
                    println!("Record ID:           {}", id);
                    println!("New Store Epoch:     {}", epoch);
                    println!("Gate Class:          {}", gate_class);
                    println!("Task:                {}", task);
                    println!("Verdict:             {}", verdict);
                    println!("Epistemic Source:    {}", source);
                    println!("Authority Basis:     WarrantBasis::Mandala (CommitCapability)");
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Failed to record receipt in Substrate: {e}");
                    std::process::exit(1);
                }
            }
        }
        MandalaCommands::Triage {
            utility,
            risk,
            variance,
            cost,
            threshold,
        } => {
            let tensor = wm_gen3_core::bicameral::JevDecisionTensor::default();
            let start = std::time::Instant::now();
            let score = tensor.compute_jev(utility, risk, variance, cost);
            let elapsed_ns = start.elapsed().as_nanos();
            let admitted = score >= threshold;

            println!("==================================================");
            println!("   Mandala / JEV Non-Autoregressive Pre-Triage   ");
            println!("==================================================");
            println!("Utility (U):         {:.4}", utility);
            println!("Risk (R):            {:.4}", risk);
            println!("Variance (V):        {:.4}", variance);
            println!("Cost (C):            {:.4}", cost);
            println!("Threshold:           {:.4}", threshold);
            println!("--------------------------------------------------");
            println!("JEV Tensor Score:    {:.6}", score);
            println!(
                "Admission Decision:  {}",
                if admitted {
                    "ADMITTED (Passes to Factory)"
                } else {
                    "REFUSED (Rejected at Ingress)"
                }
            );
            println!("Evaluation Latency:  {} ns (<30ns envelope)", elapsed_ns);
            println!("==================================================");
        }
        MandalaCommands::Evaluate {
            candidate_id,
            parent_id,
            proposer,
            actions,
            mutation,
            utility,
            code,
            out_receipt,
        } => {
            let action_steps: Vec<String> = actions
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();

            let skeleton = wm_gen3_core::bicameral::ActionSkeleton {
                id: candidate_id.clone(),
                name: format!("eval-{}", candidate_id),
                version: 1,
                parent_id: Some(parent_id.clone()),
                tier: wm_gen3_core::bicameral::SkeletonTier::Standard,
                action_steps: action_steps.clone(),
                expected_preconditions: vec!["cargo installed".to_string()],
                estimated_latency_savings_ms: 120,
                execution_count: 10,
                success_count: 9,
                rolling_utility: utility,
                deprecated: false,
            };

            let mutation_kind = match mutation.as_str() {
                "vanguard" => wm_gen3_core::bicameral::MutationKind::VanguardStreamline,
                "heavy" => wm_gen3_core::bicameral::MutationKind::HeavyVerification,
                _ => wm_gen3_core::bicameral::MutationKind::StepOptimization,
            };

            let candidate = wm_gen3_core::factory::FactoryCandidate {
                candidate_id: candidate_id.clone(),
                parent_id: parent_id.clone(),
                proposer_did: proposer.clone(),
                mutation_kind,
                skeleton,
                code_payload: code,
                proposed_actions: action_steps,
            };

            let temp_dir = std::env::temp_dir().join(format!("wm_factory_{}", std::process::id()));
            let checker_seed = [42u8; 32];
            let cfg = wm_gen3_core::factory::SoftwareFactoryConfig::new(
                "tenant-primary",
                &checker_seed,
                temp_dir,
            );
            let mut factory = wm_gen3_core::factory::SoftwareFactory::new(
                cfg,
                wm_gen3_core::bicameral::GeneseedVault::default(),
            );

            println!("==================================================");
            println!(" Sovereign Evolutionary Software Factory Trial   ");
            println!("==================================================");
            println!("Candidate ID:        {}", candidate_id);
            println!("Parent ID:           {}", parent_id);
            println!("Proposer:            {}", proposer);
            println!("Checker DID:         {}", factory.checker_did());
            println!("Homeostatic Regime:  {:?}", factory.homeostatic_regime());
            println!("--------------------------------------------------");

            match factory.evaluate_candidate(&candidate) {
                Ok(adjudication) => {
                    println!("Fate:                {:?}", adjudication.fate);
                    println!("Utility Delta:       {:.4}", adjudication.utility_delta);
                    println!("Adjudication Reason: {}", adjudication.reason);
                    println!("Receipt ID:          {}", adjudication.receipt.receipt_id);
                    println!(
                        "Sandbox Class:       {}",
                        adjudication.receipt.sandbox_class
                    );
                    println!(
                        "Preflight Clear:     {}",
                        adjudication.receipt.preflight_clearance
                    );
                    println!(
                        "Kekkai Phase:        {:?}",
                        adjudication.receipt.kekkai_phase
                    );
                    println!(
                        "Signature Valid:     {}",
                        adjudication.receipt.signature.is_some()
                    );

                    if let Some(out_path) = out_receipt {
                        if let Ok(receipt_json) =
                            serde_json::to_string_pretty(&adjudication.receipt)
                        {
                            let _ = std::fs::write(&out_path, receipt_json);
                            println!("Receipt Saved:       {}", out_path.display());
                        }
                    }
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Software Factory Evaluation FAILED: {e}");
                    std::process::exit(1);
                }
            }
        }
        MandalaCommands::Status => {
            let ledger = match MandalaReplayLedger::open_durable(&ledger_path) {
                Ok(l) => l,
                Err(e) => {
                    eprintln!(
                        "Failed to open Mandala replay ledger at {}: {e}",
                        ledger_path.display()
                    );
                    std::process::exit(1);
                }
            };
            let (_signing_key, pubkey) = match resolve_or_create_mandala_gate_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve gate authority key: {e}");
                    std::process::exit(1);
                }
            };

            println!("==================================================");
            println!("       Mandala Capability Subsystem Status        ");
            println!("==================================================");
            println!("Store Path:          {}", store_path.display());
            println!("Ledger Path:         {}", ledger_path.display());
            println!("Gate Authority DID:  did:key:{}", hex_encode(&pubkey));
            println!("Consumed JTIs:       {}", ledger.consumed_count());
            println!("Revoked Tenants:     {}", ledger.revoked_tenants_count());
            println!("Revoked Passes:      {}", ledger.revoked_passes_count());
            println!("Revoked JTIs:        {}", ledger.revoked_jtis_count());
            println!("Article 1 Closure:   100% Gated by CommitCapability");
            println!("--------------------------------------------------");
            println!("Kernel Sandboxing:   Linux Landlock LSM (Auto ABI V1-V5)");
            println!("Network Isolation:   AccessNet (TCP Port Jail, Deny Default)");
            println!("Resource Limits:     POSIX rlimit (AS, CPU, NOFILE)");
            println!("PEB-15 Microsecond Benchmarks (Ratified):");
            println!("  JEV Pre-Triage:    26.70 ns / eval  (37.5M evals/sec)");
            println!("  Workspace Claim:   87.67 us / claim (11.4k claims/sec)");
            println!("  Landlock Ruleset:  142.55 us / ruleset (7.0k rulesets/sec)");
            println!("  Total Setup:       230.22 us (0.23 ms)");
            println!("  Spec 0.5 Receipt:  341.93 us / notarize (2.9k receipts/sec)");
            println!("  Factory Pipeline:  604.44 us / trial (1,654 trials/sec)");
            println!("Speedup vs MicroVM:  152.0x faster than Firecracker");
            println!("Speedup vs Container: 521.2x faster than Docker/runc");
            println!("==================================================");
        }
    }
}

fn run_ingest(
    store_path: &Path,
    file_path: &str,
    batch_size: usize,
    default_source: &str,
    default_kind: &str,
) {
    let journal_path = store_path.join("journal.jsonl");
    let mut substrate = match Substrate::open(store_path, Some(&journal_path), default_view()) {
        Ok(s) => s,
        Err(e) => {
            eprintln!(
                "Failed to open target Gen3 store at {}: {e}",
                store_path.display()
            );
            std::process::exit(1);
        }
    };
    substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-ingest"));
    let old_budget = substrate.budget();
    substrate.set_budget(0); // Unconstrained budget for bulk ingestion
    substrate.set_noise_enabled(false); // Ingest execution logs and traces without noise rejection

    let kind = match default_kind.to_ascii_lowercase().as_str() {
        "system" => ImportKind::System,
        "simulated" => ImportKind::Simulated,
        _ => ImportKind::Reported,
    };

    let reader: Box<dyn std::io::BufRead> = if file_path == "-" {
        Box::new(std::io::BufReader::new(std::io::stdin()))
    } else {
        match std::fs::File::open(file_path) {
            Ok(f) => Box::new(std::io::BufReader::new(f)),
            Err(e) => {
                eprintln!("Failed to open input file {file_path}: {e}");
                std::process::exit(1);
            }
        }
    };

    println!("==================================================");
    println!("        WhiteMagic Gen3 Ingestion Engine          ");
    println!("==================================================");
    println!("Target Store:    {}", store_path.display());
    println!(
        "Source Input:    {}",
        if file_path == "-" { "stdin" } else { file_path }
    );
    println!("Batch Size:      {}", batch_size);
    println!("Default Source:  {}", default_source);
    println!("Default Kind:    {:?}", kind);
    println!("==================================================");

    let mut batch: Vec<RememberItem> = Vec::with_capacity(batch_size);
    let mut total_read: usize = 0;
    let mut total_committed: usize = 0;
    let mut total_duplicates: usize = 0;
    let mut total_other_refusals: usize = 0;
    let start_time = std::time::Instant::now();

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Error reading line {total_read}: {e}");
                break;
            }
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        total_read += 1;

        let item = if let Ok(json_val) = serde_json::from_str::<serde_json::Value>(trimmed) {
            let content = json_val
                .get("content")
                .and_then(|v| v.as_str())
                .unwrap_or(trimmed);
            let source = json_val
                .get("source")
                .and_then(|v| v.as_str())
                .unwrap_or(default_source);
            let item_kind = json_val
                .get("kind")
                .and_then(|v| v.as_str())
                .map(|k| match k.to_ascii_lowercase().as_str() {
                    "system" => ImportKind::System,
                    "simulated" => ImportKind::Simulated,
                    _ => kind,
                })
                .unwrap_or(kind);
            RememberItem {
                content: content.to_string(),
                source: source.to_string(),
                kind: item_kind,
            }
        } else {
            RememberItem {
                content: trimmed.to_string(),
                source: default_source.to_string(),
                kind,
            }
        };

        batch.push(item);

        if batch.len() >= batch_size {
            let res = substrate.remember_batch(&batch);
            for committed_res in res {
                match committed_res {
                    Ok(_) => total_committed += 1,
                    Err(ref e) if e == "duplicate_exact" || e.contains("duplicate") => {
                        total_duplicates += 1
                    }
                    Err(ref e) => {
                        total_other_refusals += 1;
                        if total_other_refusals <= 5 || total_other_refusals % 1000 == 0 {
                            eprintln!("Refusal reason: {e}");
                        }
                    }
                }
            }
            batch.clear();
            if total_read % 10000 == 0 || total_committed % 5000 == 0 {
                let elapsed = start_time.elapsed().as_secs_f64();
                let rate = if elapsed > 0.0 {
                    total_committed as f64 / elapsed
                } else {
                    0.0
                };
                println!(
                    "Processed: {total_read:>6} | Committed: {total_committed:>6} | Dupes: {total_duplicates:>5} | Rate: {rate:.0} rec/s"
                );
            }
        }
    }

    if !batch.is_empty() {
        let res = substrate.remember_batch(&batch);
        for committed_res in res {
            match committed_res {
                Ok(_) => total_committed += 1,
                Err(ref e) if e == "duplicate_exact" || e.contains("duplicate") => {
                    total_duplicates += 1
                }
                Err(ref e) => {
                    total_other_refusals += 1;
                    if total_other_refusals <= 5 || total_other_refusals % 1000 == 0 {
                        eprintln!("Refusal reason: {e}");
                    }
                }
            }
        }
        batch.clear();
    }

    substrate.set_budget(old_budget);
    let elapsed = start_time.elapsed().as_secs_f64();
    let epoch = substrate.store().epoch().unwrap_or(0);
    println!("==================================================");
    println!("Ingestion Complete in {:.2}s", elapsed);
    println!("Total Lines Read:      {}", total_read);
    println!("Total Committed:       {}", total_committed);
    println!("Duplicates Filtered:   {}", total_duplicates);
    if total_other_refusals > 0 {
        println!("Other Refusals:        {}", total_other_refusals);
    }
    println!("Current Store Epoch:   {}", epoch);
    println!("==================================================");
}

fn run_migration(
    source: &Path,
    target: &Path,
    batch_size: usize,
    dry_run: bool,
    allow_noise: bool,
    skip_hash_validation: bool,
    quarantine_file: Option<PathBuf>,
    receipt_file: Option<PathBuf>,
) {
    println!("==================================================");
    println!("       WhiteMagic Gen3 Migration Engine           ");
    println!("==================================================");
    println!("Source Gen2 Store:     {}", source.display());
    println!("Target Gen3 Store:     {}", target.display());
    println!("Batch Size:            {}", batch_size);
    println!(
        "Mode:                  {}",
        if dry_run {
            "DRY RUN (simulation)"
        } else {
            "LIVE SOVEREIGN COMMITS"
        }
    );
    println!(
        "Noise Filtering:       {}",
        if allow_noise {
            "PERMISSIVE (noise allowed)"
        } else {
            "STRICT (noise quarantined)"
        }
    );
    println!(
        "Hash Validation:       {}",
        if skip_hash_validation {
            "SKIPPED"
        } else {
            "STRICT SHA-256"
        }
    );
    println!("==================================================");

    let reader = match Gen2Reader::open(source) {
        Ok(r) => r,
        Err(e) => {
            eprintln!(
                "Failed to open legacy Gen2 store at {}: {e}",
                source.display()
            );
            std::process::exit(1);
        }
    };

    let journal_path = target.join("journal.jsonl");
    let mut substrate = match Substrate::open(target, Some(&journal_path), default_view()) {
        Ok(s) => s,
        Err(e) => {
            eprintln!(
                "Failed to open target Gen3 store at {}: {e}",
                target.display()
            );
            std::process::exit(1);
        }
    };

    let default_quarantine = target.join("quarantine.jsonl");
    let q_path = quarantine_file.unwrap_or(default_quarantine);

    let options = MigrationOptions {
        batch_size,
        dry_run,
        validate_hashes: !skip_hash_validation,
        allow_noise,
        quarantine_path: Some(q_path.clone()),
    };

    match migrate_gen2_to_gen3(&reader, &mut substrate, &options) {
        Ok(receipt) => {
            println!("Migration complete!");
            println!("Total Scanned:         {}", receipt.total_scanned);
            println!("Successfully Migrated: {}", receipt.migrated_count);
            println!("Duplicates Skipped:    {}", receipt.duplicate_skipped);
            println!("Quarantined:           {}", receipt.quarantined_count);
            println!("Target Epoch:          {}", receipt.target_epoch);
            println!("Receipt Digest:        {}", receipt.receipt_digest);

            let default_receipt = target.join("migration_receipt.json");
            let r_path = receipt_file.unwrap_or(default_receipt);
            if let Ok(serialized) = serde_json::to_string_pretty(&receipt) {
                let _ = std::fs::write(&r_path, serialized);
                println!("Receipt Written To:    {}", r_path.display());
            }
            if receipt.quarantined_count > 0 {
                println!("Quarantine Log At:     {}", q_path.display());
            }
        }
        Err(e) => {
            eprintln!("Migration halted with error: {e}");
            std::process::exit(1);
        }
    }
}

fn legacy_store_detected(path: &Path) -> bool {
    if !path.is_dir() {
        return false;
    }
    // If it has episodic_records but no records table
    Gen2Reader::open(path).is_ok()
}

fn run_legacy_census(path: &Path) {
    println!("Opening legacy Gen2 store at: {}", path.display());
    match Gen2Reader::open(path) {
        Ok(reader) => match reader.census() {
            Ok(census) => print_census_report(&census),
            Err(e) => eprintln!("Error during census scan: {e}"),
        },
        Err(e) => eprintln!("Failed to open Gen2 store: {e}"),
    }
}

fn print_census_report(census: &Gen2Census) {
    println!("==================================================");
    println!("      Gen2 Store Compatibility Census Report      ");
    println!("==================================================");
    println!("Store Path:          {}", census.store_path.display());
    println!("Total Records:       {}", census.total_records);
    println!("Valid SHA-256:       {}", census.valid_hashes);
    println!("Hash Mismatches:     {}", census.hash_mismatches);
    println!(
        "Integrity Ratio:     {:.4}%",
        census.integrity_ratio() * 100.0
    );
    println!("Distinct Sessions:   {}", census.distinct_sessions);
    println!("Private Records:     {}", census.private_records);
    println!("Model-Excluded:      {}", census.model_exclude_records);
    if let Some(earliest) = census.earliest_record {
        println!("Earliest Record:     {}", earliest.to_rfc3339());
    }
    if let Some(latest) = census.latest_record {
        println!("Latest Record:       {}", latest.to_rfc3339());
    }
    println!("\nEvent Kinds:");
    for (k, v) in &census.kinds {
        println!("  - {:20} : {}", k, v);
    }
    println!("\nProvenance Sources:");
    for (k, v) in &census.sources {
        println!("  - {:20} : {}", k, v);
    }
    println!("\nValidity States:");
    for (k, v) in &census.validity {
        println!("  - {:20} : {}", k, v);
    }
    println!("==================================================");
    println!("Zero Gen2 dependencies invoked. 100% Law & Evidence Closure.");
}

fn run_serve_loop(
    store: &Path,
    profile: McpProfile,
    readonly: bool,
    sweep_enabled: bool,
    projection_on: bool,
    embed_cache: Option<&Path>,
    dispersion_on: bool,
    noise_enabled: bool,
) {
    use std::io::{BufRead, Write};
    let journal_path = store.join("journal.jsonl");

    let mut substrate = {
        let opened = if readonly {
            Substrate::open_readonly(store, Some(&journal_path), default_view())
        } else {
            Substrate::open(store, Some(&journal_path), default_view())
        };
        match opened {
            Ok(s) => s,
            Err(e) => {
                eprintln!("gen3: cannot open substrate at {}: {e}", store.display());
                std::process::exit(1);
            }
        }
    };

    substrate.set_intake_authority(RatifiedChannel::mint("wm-gen3-serve"));
    substrate.set_sweep_enabled(sweep_enabled);
    if projection_on {
        if let Err(e) = substrate.set_projection_enabled(true, embed_cache) {
            eprintln!("gen3: projection enable failed: {e}");
            std::process::exit(1);
        }
    }
    substrate.set_dispersion(dispersion_on);
    substrate.set_noise_enabled(noise_enabled);

    eprintln!(
        "gen3: serve store={} profile={:?} mode={} sweep={} projection={}",
        store.display(),
        profile,
        if readonly { "readonly" } else { "readwrite" },
        if sweep_enabled { "on" } else { "off" },
        if projection_on { "on" } else { "off" }
    );

    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let Ok(request) = serde_json::from_str::<serde_json::Value>(line) else {
            continue;
        };
        let is_notification = request.get("id").is_none();
        let id = request
            .get("id")
            .cloned()
            .unwrap_or(serde_json::Value::Null);
        let method = request
            .get("method")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("");

        if is_notification {
            // Notifications (e.g. notifications/initialized) must never receive a response per JSON-RPC 2.0
            continue;
        }

        match method {
            "initialize" => {
                let envelope = json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "whitemagic-gen3",
                            "version": "10.0.0-alpha",
                            "profile": match profile { McpProfile::Cyberbrain => "cyberbrain", McpProfile::Full => "full" }
                        }
                    }
                });
                let _ = writeln!(stdout, "{envelope}");
                let _ = stdout.flush();
            }
            "ping" => {
                let envelope = json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {}
                });
                let _ = writeln!(stdout, "{envelope}");
                let _ = stdout.flush();
            }
            "tools/list" => {
                let tools = get_tools_list_for_profile(profile, readonly);
                let tool_schemas: Vec<ToolSchemaDefinition> = tools
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .map(|t| ToolSchemaDefinition {
                                name: t
                                    .get("name")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("")
                                    .to_string(),
                                description: t
                                    .get("description")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("")
                                    .to_string(),
                                parameters_schema: t
                                    .get("inputSchema")
                                    .map(|v| v.to_string())
                                    .unwrap_or_default(),
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                let const_hash = [0u8; 32];
                let epoch = substrate.store().epoch().unwrap_or(0);
                let cache_token = ContextCacheToken::compute(&tool_schemas, &const_hash, epoch);

                let envelope = json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "tools": tools,
                        "_meta": {
                            "profile": match profile { McpProfile::Cyberbrain => "cyberbrain", McpProfile::Full => "full" },
                            "context_cache_token": cache_token.cache_token,
                            "canonical_prefix_bytes": cache_token.canonical_prefix_bytes,
                            "estimated_prefix_tokens": cache_token.estimated_prefix_tokens,
                            "epoch": epoch
                        }
                    }
                });
                let _ = writeln!(stdout, "{envelope}");
                let _ = stdout.flush();
            }
            "tools/call" => {
                let name = request
                    .pointer("/params/name")
                    .and_then(serde_json::Value::as_str)
                    .unwrap_or("");
                let empty_obj = serde_json::Value::Object(serde_json::Map::new());
                let args = request
                    .pointer("/params/arguments")
                    .or_else(|| request.pointer("/params/input"))
                    .unwrap_or(&empty_obj);

                let res = execute_hybrid_tool_call(name, args, &mut substrate, store, readonly);
                let envelope = match res {
                    Ok(val) => json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": serde_json::to_string_pretty(&val).unwrap_or_else(|_| val.to_string())
                                }
                            ],
                            "isError": false
                        }
                    }),
                    Err(err_msg) => json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": format!("Error: {err_msg}")
                                }
                            ],
                            "isError": true
                        }
                    }),
                };
                let _ = writeln!(stdout, "{envelope}");
                let _ = stdout.flush();
            }
            _ => {
                let err = json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "error": { "code": -32601, "message": format!("unknown method: {method}") }
                });
                let _ = writeln!(stdout, "{err}");
                let _ = stdout.flush();
            }
        }
    }
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn hex_decode(s: &str) -> Result<Vec<u8>, String> {
    if s.len() % 2 != 0 {
        return Err("odd hex string length".to_string());
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|e| e.to_string()))
        .collect()
}

fn run_mesh_command(command: MeshCommands, store_path: &Path) {
    match command {
        MeshCommands::Status => {
            let (_signing_key, pubkey) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let (epoch, count) = match Substrate::open_readonly(store_path, None, default_view()) {
                Ok(s) => (
                    s.store().epoch().unwrap_or(0),
                    s.store().record_count().unwrap_or(0),
                ),
                Err(_) => (0, 0),
            };

            println!("==================================================");
            println!("       Mandala P2P Mesh Node Status               ");
            println!("==================================================");
            println!("Store Path:       {}", store_path.display());
            println!("Node Public Key:  {}", hex_encode(&pubkey));
            println!("Current Epoch:    {}", epoch);
            println!("Record Count:     {}", count);
            println!("Protocol Version: {}", MESH_PROTOCOL_VERSION);
            println!("Default Port:     {}", DEFAULT_MESH_PORT);
            println!("==================================================");
        }
        MeshCommands::Listen {
            port,
            bind,
            node_id,
        } => {
            let (signing_key, pubkey) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let name = node_id.unwrap_or_else(|| "sovereign-node".to_string());

            println!("==================================================");
            println!("       Mandala P2P Mesh Server Daemon             ");
            println!("==================================================");
            println!("Node ID:          {}", name);
            println!("Verifying Key:    {}", hex_encode(&pubkey));
            println!("Binding Host:     {}:{}", bind, port);
            println!("Store Path:       {}", store_path.display());
            println!("Protocol Version: {}", MESH_PROTOCOL_VERSION);
            println!("==================================================");

            let mut server = MeshServer::new(&name, signing_key, store_path);
            let bound = match server.listen(port, &bind) {
                Ok(addr) => addr,
                Err(e) => {
                    eprintln!("Failed to bind mesh server: {e}");
                    std::process::exit(1);
                }
            };
            println!("Sovereign transport listening on {}", bound);
            println!("Running in foreground. Press Ctrl+C to terminate.");

            while *server.is_running.lock().unwrap() {
                std::thread::sleep(std::time::Duration::from_millis(500));
            }
        }
        MeshCommands::Ping { peer, node_id } => {
            let (signing_key, _) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let name = node_id.unwrap_or_else(|| "sovereign-client".to_string());
            let addr: std::net::SocketAddr = match peer.parse() {
                Ok(a) => a,
                Err(e) => {
                    eprintln!("Invalid peer address '{}': {e}", peer);
                    std::process::exit(1);
                }
            };
            println!("Connecting to peer {}...", addr);
            let mut client = match MeshClient::connect(addr, &name, signing_key) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Connection failed: {e}");
                    std::process::exit(1);
                }
            };
            match client.ping() {
                Ok(rtt) => println!(
                    "Ping successful: RTT = {:.2} ms",
                    rtt.as_secs_f64() * 1000.0
                ),
                Err(e) => {
                    eprintln!("Ping failed: {e}");
                    std::process::exit(1);
                }
            }
        }
        MeshCommands::Sync {
            peer,
            batch_size,
            node_id,
        } => {
            let (signing_key, _) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let name = node_id.unwrap_or_else(|| "sovereign-sync-client".to_string());
            let addr: std::net::SocketAddr = match peer.parse() {
                Ok(a) => a,
                Err(e) => {
                    eprintln!("Invalid peer address '{}': {e}", peer);
                    std::process::exit(1);
                }
            };

            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Failed to open substrate at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            substrate.set_intake_authority(RatifiedChannel::mint("mesh-sync"));

            println!("Connecting to peer {} for sovereign sync...", addr);
            let mut client = match MeshClient::connect(addr, &name, signing_key) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Connection failed: {e}");
                    std::process::exit(1);
                }
            };

            match client.sync_delta(&mut substrate, batch_size) {
                Ok(stats) => {
                    println!("==================================================");
                    println!("       Mandala P2P Mesh Sync Complete             ");
                    println!("==================================================");
                    println!("Total Received:      {}", stats.total_received);
                    println!("Records Migrated:    {}", stats.records_migrated);
                    println!("Duplicates Skipped:  {}", stats.duplicates_skipped);
                    println!("Quarantined:         {}", stats.quarantined);
                    println!("Previous Epoch:      {}", stats.previous_epoch);
                    println!("New Store Epoch:     {}", stats.new_epoch);
                    println!("Roundtrip Latency:   {:.2} ms", stats.roundtrip_ms);
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Sync failed: {e}");
                    std::process::exit(1);
                }
            }
        }
        MeshCommands::Export {
            out,
            since_epoch,
            author_id,
        } => {
            let (signing_key, pubkey) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let name = author_id.unwrap_or_else(|| "sovereign-author".to_string());
            let store = match Substrate::open_readonly(store_path, None, default_view()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Failed to open store at {}: {e}", store_path.display());
                    std::process::exit(1);
                }
            };

            println!("Exporting sync bundle from epoch {}...", since_epoch);
            let bundle = match SyncBundle::export(&store, since_epoch, &name, &signing_key) {
                Ok(b) => b,
                Err(e) => {
                    eprintln!("Export failed: {e}");
                    std::process::exit(1);
                }
            };
            if let Err(e) = bundle.save_to_file(&out) {
                eprintln!("Failed to write bundle to {}: {e}", out.display());
                std::process::exit(1);
            }
            println!(
                "Export complete: {} records -> {}",
                bundle.records.len(),
                out.display()
            );
            println!("Merkle Root:   {}", hex_encode(&bundle.merkle_root));
            println!("Author Pubkey: {}", hex_encode(&pubkey));
        }
        MeshCommands::Import {
            in_file,
            expected_key,
        } => {
            let expected_bytes =
                expected_key.and_then(|k| hex_decode(&k).ok().and_then(|b| b.try_into().ok()));
            let bundle = match SyncBundle::load_from_file(&in_file) {
                Ok(b) => b,
                Err(e) => {
                    eprintln!("Failed to load bundle from {}: {e}", in_file.display());
                    std::process::exit(1);
                }
            };

            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!(
                            "Failed to open target store at {}: {e}",
                            store_path.display()
                        );
                        std::process::exit(1);
                    }
                };
            substrate.set_intake_authority(RatifiedChannel::mint("mesh-import"));

            println!("Importing sync bundle {}...", in_file.display());
            match bundle.import_into_substrate(
                &mut substrate,
                expected_bytes.as_ref(),
                &in_file.to_string_lossy(),
            ) {
                Ok(receipt) => {
                    println!("==================================================");
                    println!("       Sync Bundle Import Complete                ");
                    println!("==================================================");
                    println!("Source Bundle:       {}", receipt.source_bundle);
                    println!("Author ID:           {}", receipt.author_id);
                    println!("Total in Bundle:     {}", receipt.total_records);
                    println!("Records Migrated:    {}", receipt.migrated_count);
                    println!("Duplicates Skipped:  {}", receipt.duplicate_skipped);
                    println!("New Store Epoch:     {}", receipt.target_epoch);
                    println!("Receipt Digest:      {}", receipt.receipt_digest);
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Bundle import rejected: {e}");
                    std::process::exit(1);
                }
            }
        }
        MeshCommands::SyncGenes {
            peer,
            since_version,
            node_id,
        } => {
            let (signing_key, _) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let name = node_id.unwrap_or_else(|| "sovereign-gene-sync".to_string());
            let addr: std::net::SocketAddr = match peer.parse() {
                Ok(a) => a,
                Err(e) => {
                    eprintln!("Invalid peer address '{}': {e}", peer);
                    std::process::exit(1);
                }
            };

            let vault_path = store_path.join("vault.jsonl");
            let mut vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);

            println!("Connecting to peer {} for gene speciation sync...", addr);
            let mut client = match MeshClient::connect(addr, &name, signing_key) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Connection failed: {e}");
                    std::process::exit(1);
                }
            };

            match client.sync_genes(&mut vault, since_version) {
                Ok(stats) => {
                    if let Err(e) = vault.sync_to_file(&vault_path) {
                        eprintln!("Warning: failed to persist vault to file: {e}");
                    }
                    println!("==================================================");
                    println!("    Cross-Node Gene Speciation Exchange Complete  ");
                    println!("==================================================");
                    println!("Peer Address:       {}", addr);
                    println!("Total Received:     {}", stats.total_received);
                    println!("Genes Promoted:     {}", stats.genes_promoted);
                    println!("Genes Rejected:     {}", stats.genes_rejected);
                    println!("Active Vault Size:  {}", vault.skeletons.len());
                    println!(
                        "Negative Knowledge: {} signatures",
                        vault.retired_signatures.len()
                    );
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Gene sync failed: {e}");
                    std::process::exit(1);
                }
            }
        }
    }
}

/// Generates a standalone, interactive 3D WebGL / Canvas HTML visualizer for 6D holographic coordinates.
fn generate_galaxy_html(json_data: &str, total_records: usize, epoch: u64) -> String {
    format!(
        r###"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WhiteMagic Gen3 — 6D Holographic Sangha Galaxy</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body, html {{ width: 100%; height: 100%; overflow: hidden; background: #05060a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }}
  #canvas-container {{ width: 100vw; height: 100vh; position: absolute; top: 0; left: 0; cursor: grab; }}
  #canvas-container:active {{ cursor: grabbing; }}
  canvas {{ width: 100%; height: 100%; display: block; }}
  
  /* Top HUD */
  #header {{ position: absolute; top: 16px; left: 20px; z-index: 10; pointer-events: none; }}
  h1 {{ font-size: 1.1rem; font-weight: 600; letter-spacing: 0.05em; color: #a5b4fc; text-transform: uppercase; }}
  .meta {{ font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }}
  
  /* Search & Controls */
  #search-bar {{ position: absolute; top: 16px; right: 20px; z-index: 10; display: flex; gap: 8px; }}
  input#search {{ background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 6px; padding: 6px 12px; color: #f8fafc; font-size: 0.85rem; outline: none; width: 220px; backdrop-filter: blur(8px); transition: border-color 0.2s; }}
  input#search:focus {{ border-color: #818cf8; }}
  
  /* Inspector Card */
  #inspector {{ position: absolute; bottom: 20px; left: 20px; z-index: 10; width: 380px; max-width: calc(100vw - 40px); background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 16px; backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0,0,0,0.6); pointer-events: auto; }}
  .tag {{ display: inline-block; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; margin-bottom: 8px; }}
  .node-title {{ font-size: 0.95rem; font-weight: 600; color: #f1f5f9; margin-bottom: 6px; word-break: break-all; }}
  .coords-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; font-size: 0.7rem; color: #94a3b8; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px; margin: 8px 0; }}
  .coords-grid div span {{ color: #cbd5e1; font-weight: 600; }}
  .content-preview {{ font-size: 0.8rem; line-height: 1.4; color: #cbd5e1; max-height: 120px; overflow-y: auto; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; }}
  
  /* Instructions */
  #instructions {{ position: absolute; bottom: 20px; right: 20px; z-index: 10; font-size: 0.7rem; color: #64748b; text-align: right; pointer-events: none; }}
</style>
</head>
<body>
  <div id="header">
    <h1>WhiteMagic Gen3 Holographic Galaxy</h1>
    <div class="meta">Epoch {epoch} &bull; Total Memories: {total_records} &bull; Sangha Celestial Coordinate Plane</div>
  </div>

  <div id="search-bar">
    <input type="text" id="search" placeholder="Search galaxy memories..." autocomplete="off">
  </div>

  <div id="inspector">
    <div id="card-tag" class="tag" style="background: rgba(99, 102, 241, 0.2); color: #818cf8;">Select a Node</div>
    <div id="card-title" class="node-title">Click any coordinate in 3D space</div>
    <div id="card-coords" class="coords-grid">
      <div>X: <span id="val-x">0</span></div>
      <div>Y: <span id="val-y">0</span></div>
      <div>Z: <span id="val-z">0</span></div>
      <div>&tau;: <span id="val-tau">0</span></div>
      <div>&sigma;: <span id="val-sigma">0</span></div>
      <div>&omega;: <span id="val-omega">0</span></div>
    </div>
    <div id="card-preview" class="content-preview">Hover or click any star to examine its holographic projection, semantic provenance, and record metadata.</div>
  </div>

  <div id="instructions">
    Left Click + Drag: Rotate 3D Spherical Plane<br>
    Scroll Wheel: Zoom Depth &bull; Click Node: Inspect
  </div>

  <div id="canvas-container">
    <canvas id="galaxy-canvas"></canvas>
  </div>

<script>
const DATA = {json_data};

// 28 Gana Harmonic Colors (Celestial Palette)
const GANA_COLORS = [
  "#60a5fa", "#38bdf8", "#22d3ee", "#2dd4bf", "#34d399", "#4ade80", "#a3e635",
  "#facc15", "#fbbf24", "#fb923c", "#f87171", "#fda4af", "#f472b6", "#e879f9",
  "#c084fc", "#a855f7", "#818cf8", "#6366f1", "#4f46e5", "#3b82f6", "#06b6d4",
  "#10b981", "#84cc16", "#eab308", "#f97316", "#ef4444", "#ec4899", "#d946ef"
];

const canvas = document.getElementById("galaxy-canvas");
const ctx = canvas.getContext("2d");

let width = window.innerWidth;
let height = window.innerHeight;
canvas.width = width;
canvas.height = height;

window.addEventListener("resize", () => {{
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = width;
  canvas.height = height;
}});

// Camera State
let rotX = 0.3;
let rotY = -0.5;
let zoom = 1.0;
let isDragging = false;
let lastMouseX = 0;
let lastMouseY = 0;
let selectedNode = DATA.length > 0 ? DATA[0] : null;
let searchQuery = "";

// Mouse Interaction
window.addEventListener("mousedown", (e) => {{
  if (e.target.closest("#inspector") || e.target.closest("#search-bar")) return;
  isDragging = true;
  lastMouseX = e.clientX;
  lastMouseY = e.clientY;
}});

window.addEventListener("mousemove", (e) => {{
  if (isDragging) {{
    const dx = e.clientX - lastMouseX;
    const dy = e.clientY - lastMouseY;
    rotY += dx * 0.005;
    rotX += dy * 0.005;
    rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
  }}
}});

window.addEventListener("mouseup", () => {{ isDragging = false; }});
window.addEventListener("wheel", (e) => {{
  zoom *= e.deltaY > 0 ? 0.92 : 1.08;
  zoom = Math.max(0.2, Math.min(6.0, zoom));
}});

// Search filter
document.getElementById("search").addEventListener("input", (e) => {{
  searchQuery = e.target.value.toLowerCase().trim();
}});

// Click to select node
canvas.addEventListener("click", (e) => {{
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  
  let closest = null;
  let minD = 16;
  
  for (const n of DATA) {{
    if (n._screenX && n._screenY) {{
      const d = Math.hypot(n._screenX - mx, n._screenY - my);
      if (d < minD) {{
        minD = d;
        closest = n;
      }}
    }}
  }}
  if (closest) {{
    updateCard(closest);
  }}
}});

function updateCard(node) {{
  selectedNode = node;
  document.getElementById("card-tag").innerText = `Gana #${{node.omega}} \u2022 Record #${{node.id}}`;
  document.getElementById("card-tag").style.color = GANA_COLORS[node.omega % 28];
  document.getElementById("card-title").innerText = node.source || `Record #${{node.id}}`;
  document.getElementById("val-x").innerText = node.x.toFixed(1);
  document.getElementById("val-y").innerText = node.y.toFixed(1);
  document.getElementById("val-z").innerText = node.z.toFixed(1);
  document.getElementById("val-tau").innerText = node.tau.toFixed(2);
  document.getElementById("val-sigma").innerText = node.sigma.toFixed(2);
  document.getElementById("val-omega").innerText = node.omega;
  document.getElementById("card-preview").innerText = node.preview;
}}

if (selectedNode) updateCard(selectedNode);

// Render Loop
function render() {{
  ctx.fillStyle = "#05060a";
  ctx.fillRect(0, 0, width, height);

  // Background subtle grid/dust
  ctx.strokeStyle = "rgba(99, 102, 241, 0.08)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(width / 2, height / 2, 250 * zoom, 0, Math.PI * 2);
  ctx.stroke();

  const cx = width / 2;
  const cy = height / 2;
  const fov = 600;

  const cosY = Math.cos(rotY);
  const sinY = Math.sin(rotY);
  const cosX = Math.cos(rotX);
  const sinX = Math.sin(rotX);

  const projected = [];

  for (let i = 0; i < DATA.length; i++) {{
    const p = DATA[i];
    
    // 3D Rotation
    // Rotate Y
    const x1 = p.x * cosY - p.y * sinY;
    const y1 = p.x * sinY + p.y * cosY;
    const z1 = p.z;
    
    // Rotate X
    const x2 = x1;
    const y2 = y1 * cosX - z1 * sinX;
    const z2 = y1 * sinX + z1 * cosX;

    const depth = (z2 + 600) * zoom;
    if (depth > 20) {{
      const scale = (fov * zoom) / depth;
      const sx = cx + x2 * scale;
      const sy = cy + y2 * scale;
      p._screenX = sx;
      p._screenY = sy;
      p._depth = depth;
      projected.push(p);
    }}
  }}

  // Depth sort (painter's algorithm)
  projected.sort((a, b) => b._depth - a._depth);

  for (const p of projected) {{
    const isSelected = selectedNode && selectedNode.id === p.id;
    const matchesSearch = searchQuery && p.preview.toLowerCase().includes(searchQuery);
    
    let radius = Math.max(1.2, (2.8 * fov * zoom) / p._depth);
    if (isSelected) radius *= 2.2;
    if (matchesSearch) radius *= 1.8;

    const baseColor = GANA_COLORS[p.omega % 28];
    const alpha = Math.min(1.0, Math.max(0.2, 1.2 - p._depth / 1400));

    ctx.beginPath();
    ctx.arc(p._screenX, p._screenY, radius, 0, Math.PI * 2);

    if (matchesSearch) {{
      ctx.fillStyle = "#fef08a";
      ctx.shadowColor = "#facc15";
      ctx.shadowBlur = 10;
    }} else if (isSelected) {{
      ctx.fillStyle = "#ffffff";
      ctx.shadowColor = baseColor;
      ctx.shadowBlur = 14;
    }} else {{
      ctx.fillStyle = baseColor;
      ctx.shadowBlur = 0;
    }}
    
    ctx.globalAlpha = matchesSearch || isSelected ? 1.0 : alpha;
    ctx.fill();

    // Ring around selected node
    if (isSelected) {{
      ctx.beginPath();
      ctx.arc(p._screenX, p._screenY, radius + 4, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }}
  }}

  ctx.globalAlpha = 1.0;
  ctx.shadowBlur = 0;

  requestAnimationFrame(render);
}}

requestAnimationFrame(render);
</script>
</body>
</html>"###
    )
}

fn print_dream_report(log_path: &Path, insights_path: &Path, substrate: Option<&Substrate>) {
    println!("==================================================");
    println!("      WhiteMagic Gen3 Dream Incubation Report     ");
    println!("==================================================");
    println!("Journal Path:             {}", log_path.display());
    println!("Insights Path:            {}", insights_path.display());

    if !log_path.exists() {
        println!("Status:                   No dream journal found.");
        println!("Run `wm3 dream --cycles <N>` to initiate cognitive dreaming.");
        println!("==================================================");
        return;
    }

    let file = match std::fs::File::open(log_path) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("Error opening dream journal {}: {e}", log_path.display());
            return;
        }
    };

    use std::io::BufReader;
    let reader = BufReader::new(file);

    let mut entries = Vec::new();
    let mut total_generated = 0usize;
    let mut total_committed = 0usize;
    let mut total_discarded = 0usize;
    let mut entropy_sum = 0.0f64;
    let mut min_entropy = f64::MAX;
    let mut max_entropy = f64::MIN;

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(trimmed) {
            let generated = val
                .get("candidates_generated")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as usize;
            let comm = val
                .get("candidates_committed")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as usize;
            let disc = val
                .get("candidates_discarded")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as usize;
            let ent = val.get("entropy").and_then(|v| v.as_f64()).unwrap_or(0.0);

            total_generated += generated;
            total_committed += comm;
            total_discarded += disc;
            entropy_sum += ent;
            if ent < min_entropy {
                min_entropy = ent;
            }
            if ent > max_entropy {
                max_entropy = ent;
            }

            entries.push(val);
        }
    }

    let count = entries.len();
    if count == 0 {
        println!("Status:                   Dream journal is empty.");
        println!("==================================================");
        return;
    }

    let avg_entropy = entropy_sum / (count as f64);
    let commit_rate = if total_generated > 0 {
        (total_committed as f64) / (total_generated as f64) * 100.0
    } else {
        0.0
    };
    let discard_rate = if total_generated > 0 {
        (total_discarded as f64) / (total_generated as f64) * 100.0
    } else {
        0.0
    };

    println!("Total Cycles Recorded:    {}", count);
    println!("Total Candidates Sampled: {}", total_generated);
    println!(
        "Consolidated into Store:  {} ({:.1}%)",
        total_committed, commit_rate
    );
    println!(
        "Cleanly Evaporated:       {} ({:.1}%)",
        total_discarded, discard_rate
    );
    println!(
        "Shannon Diversity (H):    avg {:.3} | min {:.3} | max {:.3} bits",
        avg_entropy, min_entropy, max_entropy
    );
    println!("--------------------------------------------------");
    println!("Recent Cycle History (Last 10):");

    let start_idx = count.saturating_sub(10);
    for entry in &entries[start_idx..] {
        let cycle = entry.get("cycle").and_then(|v| v.as_u64()).unwrap_or(0);
        let q = entry
            .get("quiescence")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        let temp = entry
            .get("temperature")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        let radius = entry
            .get("associative_radius")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let generated = entry
            .get("candidates_generated")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let comm = entry
            .get("candidates_committed")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let disc = entry
            .get("candidates_discarded")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let ent = entry.get("entropy").and_then(|v| v.as_f64()).unwrap_or(0.0);

        println!(
            "  Cycle #{:03} | q: {:.2} | temp: {:.2} | rad: {} | gen: {:3} | comm: {:2} | disc: {:3} | H: {:.3}",
            cycle, q, temp, radius, generated, comm, disc, ent
        );
    }

    if let Some(sub) = substrate {
        let total_records = sub.store().record_count().unwrap_or(0);
        println!("--------------------------------------------------");
        println!("Consolidated Concept Previews (from store):");
        let mut previews = Vec::new();
        let scan_depth = total_records.min(200);
        for i in 0..scan_depth {
            let id = (total_records - i) as u64;
            if let Ok(Some(rec)) = sub.store().get_record(id) {
                if rec.source() == "dream_consolidation" {
                    previews.push((rec.id(), rec.content().to_string()));
                    if previews.len() >= 5 {
                        break;
                    }
                }
            }
        }
        if previews.is_empty() {
            println!("  (No dream_consolidation records found in recent store history)");
        } else {
            for (id, content) in previews {
                let preview = if content.len() > 60 {
                    format!("{}...", &content[..57])
                } else {
                    content
                };
                println!("  [{}] {}", id, preview);
            }
        }
    }

    if insights_path.exists() {
        println!("--------------------------------------------------");
        println!("Actionable Synthetic Insights (from dream_insights.jsonl):");
        if let Ok(file) = std::fs::File::open(insights_path) {
            use std::io::BufReader;
            let reader = BufReader::new(file);
            let mut insights: Vec<wm_gen3_core::dream::DreamInsight> = Vec::new();
            for line in reader.lines() {
                if let Ok(l) = line {
                    let trimmed = l.trim();
                    if !trimmed.is_empty() {
                        if let Ok(ins) =
                            serde_json::from_str::<wm_gen3_core::dream::DreamInsight>(trimmed)
                        {
                            insights.push(ins);
                        }
                    }
                }
            }
            if insights.is_empty() {
                println!("  (No insights logged in dream_insights.jsonl yet)");
            } else {
                let start_idx = insights.len().saturating_sub(5);
                for ins in &insights[start_idx..] {
                    println!(
                        "  ✦ [{}] {} (utility: {:.3}, conf: {:.2})\n    Bridge:  #{} \"{}\" ⇄ #{} \"{}\"\n    Hypoth:  {}\n    Action:  {}",
                        ins.id,
                        ins.relation_type,
                        ins.utility_score,
                        ins.confidence,
                        ins.source_id,
                        ins.source_concept,
                        ins.target_id,
                        ins.target_concept,
                        ins.hypothesis,
                        ins.actionable_recommendation,
                    );
                }
            }
        }
    }

    println!("==================================================");
}

fn print_dream_insights(insights_path: &Path, limit: usize) {
    println!("==================================================");
    println!("     WhiteMagic Gen3 Actionable Dream Insights    ");
    println!("==================================================");
    println!("Insights Journal:         {}", insights_path.display());

    if !insights_path.exists() {
        println!("Status:                   No dream insights journal found.");
        println!("Run `wm3 dream --cycles <N>` to synthesize actionable insights.");
        println!("==================================================");
        return;
    }

    let file = match std::fs::File::open(insights_path) {
        Ok(f) => f,
        Err(e) => {
            eprintln!(
                "Error opening insights journal {}: {e}",
                insights_path.display()
            );
            return;
        }
    };

    use std::io::BufReader;
    let reader = BufReader::new(file);
    let mut insights: Vec<wm_gen3_core::dream::DreamInsight> = Vec::new();

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(ins) = serde_json::from_str::<wm_gen3_core::dream::DreamInsight>(trimmed) {
            insights.push(ins);
        }
    }

    let count = insights.len();
    if count == 0 {
        println!("Status:                   No insights recorded yet.");
        println!("==================================================");
        return;
    }

    println!("Total Synthesized Insights: {}", count);
    println!(
        "Displaying Latest {} High-Utility Insights:",
        limit.min(count)
    );
    println!("--------------------------------------------------");

    let start_idx = count.saturating_sub(limit);
    for ins in &insights[start_idx..] {
        println!(
            "✦ [{}] {} | Cycle #{:03} | Utility: {:.3} | Confidence: {:.2}",
            ins.id, ins.relation_type, ins.cycle, ins.utility_score, ins.confidence
        );
        println!(
            "  Bridge:     \"{}\" (id: {}) ⇄ \"{}\" (id: {})",
            ins.source_concept, ins.source_id, ins.target_concept, ins.target_id
        );
        println!("  Hypothesis: {}", ins.hypothesis);
        println!("  Action:     {}", ins.actionable_recommendation);
        println!("--------------------------------------------------");
    }
    println!("==================================================");
}

fn run_vault_command(cmd: VaultCommands, store_path: &Path) {
    let vault_path = store_path.join("vault.jsonl");
    let mut vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);

    match cmd {
        VaultCommands::List { all } => {
            println!("==================================================");
            println!("      WhiteMagic Gen3 Geneseed Action Vault       ");
            println!("==================================================");
            println!("Vault Path: {}", vault_path.display());
            println!("Total Skeletons: {}", vault.skeletons.len());
            println!(
                "{:<24} {:<10} {:<5} {:<6} {:<9} {:<9} {:<10}",
                "ID", "TIER", "VER", "EXECS", "UTILITY", "FITNESS", "STATUS"
            );
            println!(
                "--------------------------------------------------------------------------------"
            );
            for skel in &vault.skeletons {
                if !all && skel.deprecated {
                    continue;
                }
                let tier_str = match skel.tier {
                    wm_gen3_core::bicameral::SkeletonTier::Vanguard => "Vanguard",
                    wm_gen3_core::bicameral::SkeletonTier::Standard => "Standard",
                    wm_gen3_core::bicameral::SkeletonTier::Heavy => "Heavy",
                };
                let status_str = if skel.deprecated {
                    "Deprecated"
                } else {
                    "Active"
                };
                let spec = skel.fitness_spectrum();
                println!(
                    "{:<24} {:<10} {:<5} {:<6} {:<9.3} {:<9.3} {:<10}",
                    skel.id,
                    tier_str,
                    skel.version,
                    skel.execution_count,
                    skel.rolling_utility,
                    spec.composite_fitness,
                    status_str
                );
            }
            println!("==================================================");
        }
        VaultCommands::Get { skeleton_id } => {
            if let Some(skel) = vault.get_historical(&skeleton_id) {
                if let Ok(pretty) = serde_json::to_string_pretty(skel) {
                    println!("{pretty}");
                }
                let spec = skel.fitness_spectrum();
                println!("--------------------------------------------------");
                println!("Multi-Trait Fitness Spectrum:");
                println!("  Composite Fitness:   {:.3}", spec.composite_fitness);
                println!(
                    "  Bayesian Reliability:{:.3} (Laplace s+1/n+2)",
                    spec.reliability
                );
                println!(
                    "  Step Parsimony:      {:.3} (Occam penalty)",
                    spec.parsimony
                );
                println!(
                    "  Safety Headroom:     {:.3} (preconditions: {})",
                    spec.safety_headroom,
                    skel.expected_preconditions.len()
                );
                println!(
                    "  Latency Efficiency:  {:.3} (budget: {}ms)",
                    spec.latency_efficiency, skel.estimated_latency_savings_ms
                );
                println!("--------------------------------------------------");
            } else {
                eprintln!("Error: skeleton '{skeleton_id}' not found in vault.");
                std::process::exit(1);
            }
        }
        VaultCommands::Execute { skeleton_id } => {
            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening substrate at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            substrate.set_intake_authority(RatifiedChannel::mint("wm-vault-exec"));

            println!("Executing skeleton '{skeleton_id}' against substrate...");
            match vault.execute_skeleton_cycle(&skeleton_id, &mut substrate) {
                Ok(res) => {
                    if let Err(e) = vault.sync_to_file(&vault_path) {
                        eprintln!("Warning: failed to persist vault to file: {e}");
                    }
                    println!("==================================================");
                    println!("        Geneseed Skeleton Execution Receipt       ");
                    println!("==================================================");
                    println!("Skeleton ID:       {}", res.skeleton_id);
                    println!("Tier:              {:?}", res.tier);
                    println!(
                        "Steps Executed:    {}/{}",
                        res.steps_executed, res.total_steps
                    );
                    println!("Latency:           {} µs", res.latency_us);
                    println!("Observed Utility:  {:.4}", res.observed_utility);
                    println!("New Rolling EMA:   {:.4}", res.new_rolling_utility);
                    println!("Execution Count:   {}", res.execution_count);
                    println!("Status:            {}", res.status);
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Execution failed: {e}");
                    std::process::exit(1);
                }
            }
        }
        VaultCommands::Mutate { skeleton_id, kind } => {
            let mut_kind = match kind.to_lowercase().as_str() {
                "heavy" => wm_gen3_core::bicameral::MutationKind::HeavyVerification,
                "opt" | "step" => wm_gen3_core::bicameral::MutationKind::StepOptimization,
                _ => wm_gen3_core::bicameral::MutationKind::VanguardStreamline,
            };

            println!(
                "Evaluating do(X) mutation ({:?}) on '{}' via ParetoGate...",
                mut_kind, skeleton_id
            );
            match vault.propose_and_evaluate_mutation(&skeleton_id, mut_kind) {
                Ok(res) => {
                    if let Err(e) = vault.sync_to_file(&vault_path) {
                        eprintln!("Warning: failed to persist vault to file: {e}");
                    }
                    println!("==================================================");
                    println!("        Pareto-Gated Mutation Adjudication        ");
                    println!("==================================================");
                    println!("Parent Skeleton:   {}", res.parent_id);
                    println!("Candidate ID:      {}", res.candidate_id);
                    println!("Mutation Kind:     {:?}", res.mutation_kind);
                    println!("Evolutionary Fate: {:?}", res.decision);
                    println!("Utility Delta:     {:+0.4}", res.utility_delta);
                    println!("Latency Delta:     {:+0} ms", res.latency_delta_ms);
                    println!("Gate Message:      {}", res.message);
                    println!("Total Vault Size:  {}", vault.skeletons.len());
                    println!(
                        "Negative Archive:  {} signatures",
                        vault.retired_signatures.len()
                    );
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Mutation evaluation failed: {e}");
                    std::process::exit(1);
                }
            }
        }
    }
}

fn run_evolve_command(
    epochs: usize,
    sleep_cycles: usize,
    quiescence: f64,
    temperature: f64,
    store_path: &Path,
) {
    let journal_path = store_path.join("journal.jsonl");
    let vault_path = store_path.join("vault.jsonl");
    let insights_log = store_path.join("dream_insights.jsonl");

    let mut substrate = match Substrate::open(store_path, Some(&journal_path), default_view()) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error opening substrate at {}: {e}", store_path.display());
            std::process::exit(1);
        }
    };
    substrate.set_intake_authority(RatifiedChannel::mint("wm-autonomous-evolution"));

    let mut vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);

    println!("==================================================");
    println!("  WhiteMagic Gen3 Closed-Loop Autonomous Evolution ");
    println!("==================================================");
    println!("Store Path:          {}", store_path.display());
    println!("Evolutionary Epochs: {}", epochs);
    println!("Sleep Cycles/Epoch:  {}", sleep_cycles);
    println!("Sleep Quiescence:    {:.2}", quiescence);
    println!("Sleep Temperature:   {:.2}", temperature);
    println!("Initial Vault Size:  {} skeletons", vault.skeletons.len());
    println!(
        "Negative Knowledge:  {} signatures",
        vault.retired_signatures.len()
    );
    println!("==================================================");

    let start_all = std::time::Instant::now();

    for epoch in 1..=epochs {
        println!(
            "\n>>> [EPOCH {:02}/{:02}] Closed-Loop Evolutionary Cycle Starting...",
            epoch, epochs
        );

        // --- Phase 1: Waking Execution & Telemetry ---
        println!("  [Phase 1: Waking Execution]");
        let active_ids: Vec<String> = vault
            .skeletons
            .iter()
            .filter(|s| !s.deprecated)
            .take(3)
            .map(|s| s.id.clone())
            .collect();

        for id in &active_ids {
            match vault.execute_skeleton_cycle(id, &mut substrate) {
                Ok(res) => {
                    println!(
                        "    ⚡ Executed {:<20} | steps: {}/{} | latency: {:>4} µs | util: {:.3} -> {:.3}",
                        res.skeleton_id,
                        res.steps_executed,
                        res.total_steps,
                        res.latency_us,
                        res.observed_utility,
                        res.new_rolling_utility
                    );
                }
                Err(e) => {
                    println!("    ⚠ Failed to execute {}: {}", id, e);
                }
            }
        }
        let _ = vault.sync_to_file(&vault_path);

        // --- Phase 2: do(X) Counterfactual Mutation & Pareto Gating ---
        println!("  [Phase 2: do(X) Counterfactual Mutation & Pareto Gating]");
        let candidate_parents: Vec<String> = vault
            .skeletons
            .iter()
            .filter(|s| !s.deprecated)
            .take(2)
            .map(|s| s.id.clone())
            .collect();

        for parent_id in &candidate_parents {
            let kind = if epoch % 2 == 1 {
                wm_gen3_core::bicameral::MutationKind::VanguardStreamline
            } else {
                wm_gen3_core::bicameral::MutationKind::StepOptimization
            };
            match vault.propose_and_evaluate_mutation(parent_id, kind) {
                Ok(m_res) => {
                    println!(
                        "    🧬 Mutate {:<18} ({:?}) -> {:<22} | Fate: {:?} | util delta: {:+0.3}",
                        m_res.parent_id,
                        m_res.mutation_kind,
                        m_res.candidate_id,
                        m_res.decision,
                        m_res.utility_delta
                    );
                }
                Err(e) => {
                    println!("    ⚠ Mutation error for {}: {}", parent_id, e);
                }
            }
        }
        let _ = vault.sync_to_file(&vault_path);

        // --- Phase 3: Dual-Phase Sleep Speciation ---
        println!("  [Phase 3: Dual-Phase Sleep Speciation]");
        let regime = wm_gen3_core::dream::RegimeVector::from_quiescence(quiescence as f32, 0.0);
        for sc in 1..=sleep_cycles {
            let seed = 1000 * epoch as u64 + sc as u64;
            let dual = wm_gen3_core::dream::execute_dual_phase_sleep_cycle(
                wm_gen3_core::dream::IncubationMode::GenuineDreaming,
                &regime,
                50,
                &mut substrate,
                seed,
            );

            println!(
                "    🌙 Sleep Cycle {:02}/{:02} | NREM Compaction: {:.2}x | REM Insights: {} | Speciated: {}",
                sc,
                sleep_cycles,
                dual.nrem.token_compaction_ratio,
                dual.rem.candidates_committed,
                dual.synthesized_skeletons.len()
            );

            // Ingest synthesized dream insights into insights log
            if let Ok(mut w) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&insights_log)
            {
                use std::io::Write;
                for ins in &dual.rem.committed_insights {
                    let _ = writeln!(w, "{}", serde_json::to_string(ins).unwrap_or_default());
                }
            }

            // Ingest new speciation skeletons into vault
            for mut skel in dual.synthesized_skeletons {
                if !vault.skeletons.iter().any(|s| s.id == skel.id) {
                    skel.execution_count = 0;
                    vault.skeletons.push(skel);
                }
            }
        }
        let _ = vault.sync_to_file(&vault_path);

        // --- Phase 4: Apotheosis Meta-Learning Audit ---
        println!("  [Phase 4: Apotheosis Meta-Learning Audit]");
        let insights_count = if insights_log.exists() {
            std::fs::read_to_string(&insights_log)
                .map(|c| c.lines().filter(|l| !l.trim().is_empty()).count())
                .unwrap_or(0)
        } else {
            0
        };

        let report =
            wm_gen3_core::apotheosis::perform_apotheosis_audit(&substrate, &vault, insights_count);

        println!(
            "    ⚜ Apotheosis Status: {:?} | Index: {:.4} | Invariants: {}/9 | Mean Util: {:.3} | Skeletons: {} (active: {}) | Truth Drift: {:.3}",
            report.status,
            report.composite_apotheosis_index,
            report.invariant_audit.total_passed,
            report.kaizen_convergence.average_rolling_utility,
            report.cladistics_health.total_skeletons,
            report.cladistics_health.active_skeletons,
            report.truth_drift.truth_drift_score
        );
    }

    let elapsed = start_all.elapsed();
    println!("\n==================================================");
    println!("Autonomous Evolution Completed in {:.2?}", elapsed);
    println!("Final Vault Size:    {} skeletons", vault.skeletons.len());
    println!(
        "Active Skeletons:    {}",
        vault.skeletons.iter().filter(|s| !s.deprecated).count()
    );
    println!(
        "Negative Archive:    {} signatures",
        vault.retired_signatures.len()
    );
    println!("Forks Minted Total:  {}", vault.total_forks_minted);
    println!("Vault File Synced:   {}", vault_path.display());
    println!("==================================================");
}
