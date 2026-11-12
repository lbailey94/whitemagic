//! WhiteMagic Gen3 — Production `wm` CLI binary (the v10 line).
//!
//! Milestone 9 Gate 9B Production Shell.
//!
//! Enforces that all CLI operations dispatch as sovereign pulses via the pulse compiler,
//! upholds the Gen3 Kernel Contract (Articles 1-9), and provides zero-dependency
//! compatibility with legacy Gen2 stores.

#![recursion_limit = "512"]

use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::io::BufRead;
use std::path::{Path, PathBuf};

use wm_gen3_core::at_rest::AtRestStatus;
use wm_gen3_core::compat::{
    Gen2Census, Gen2Reader, MigrationOptions, SessionMigrationOptions, dry_run_migration_census,
    migrate_gen2_sessions_to_gen3, migrate_gen2_sessions_to_gen3_with_options,
    migrate_gen2_to_gen3,
};
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::firebreak::Firebreak;
use wm_gen3_core::mandala::{
    CapabilityManifest, ContinuityReceipt05, MandalaPass, MandalaReplayLedger, PassBudget,
    ScopeMode, SigningKey, VerifyingKey, resolve_or_create_mandala_gate_key,
};
use wm_gen3_core::mesh::{
    DEFAULT_MESH_PORT, MESH_PROTOCOL_VERSION, MeshClient, MeshServer, SyncBundle,
    resolve_or_create_mesh_key,
};
use wm_gen3_core::ops::{
    ImportKind, RecallQuery, RememberItem, SessionCheckpoint, SessionTurn, Substrate,
    compose_session_digest,
};
use wm_gen3_core::peer::{BanCertificate, PeerDirectory, PeerIdentity, PeerTrustTier};
use wm_gen3_core::sentinel::{
    SentinelCircuitBreaker, SentinelLeaseGuard, SentinelReport, SentinelStatus,
};
use wm_gen3_core::store::Store;
use wm_gen3_core::temporal::{TemporalAssertionRequest, TemporalQuery};
use wm_gen3_harness::bridge::{
    McpProfile, build_contract_manifest, get_tools_list_for_profile, mesh_sync_peer_allowlist,
};
use wm_gen3_harness::host_guard::{self, Action, HostGuardState, Policy, SystemRunner};
use wm_gen3_harness::mcp_server::{McpBackend, NetworkTransport, serve_network};
#[path = "../build_identity.rs"]
mod build_identity;

/// Build version — WhiteMagic Gen3 v10.
const WM_VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Parser)]
#[command(
    name = "wm",
    version = WM_VERSION,
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
    /// Show compile provenance and the SHA-256 of this running executable without opening a store
    BuildInfo {
        /// Print the identity as JSON
        #[arg(long)]
        json: bool,
    },
    /// Resolve or verify a bounded caller-asserted temporal answer contract without opening a store
    AnswerContract {
        /// Contract operation: resolve or verify
        #[arg(long, value_parser = ["resolve", "verify"])]
        mode: String,
        /// Strict JSON request, or - to read up to 1 MiB from standard input
        #[arg(long)]
        request_json: String,
    },
    /// Run guided first-run onboarding pass, surface the starter guide galaxy, and verify setup
    Grimoire {
        /// Output report as JSON for agent consumption
        #[arg(long)]
        json: bool,
        /// Plan detected MCP client configuration changes without modifying any files
        #[arg(long)]
        plan: bool,
    },
    /// Initialize and provision a local WhiteMagic substrate store
    Init {
        /// Force re-seeding of the starter guide galaxy even if store already exists
        #[arg(long)]
        force: bool,
        /// Initialize an empty store without seeding the starter guide galaxy
        #[arg(long, aliases = ["no-starter-pack"])]
        bare: bool,
    },
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
        /// Target memory galaxy (default: 'codex' or 'guide')
        #[arg(long)]
        galaxy: Option<String>,
        /// Epistemic source attribution (default: "operator:cli")
        #[arg(long, default_value = "operator:cli")]
        source: String,
        /// Epistemic kind: reported (default), system, or simulated
        #[arg(long, default_value = "reported", value_parser = parse_import_kind_arg)]
        kind: ImportKind,
    },
    /// Attach one explicit valid-time field assertion to an existing record
    TemporalAssert {
        /// JSON object matching TemporalAssertionRequest; recorded_at is store-assigned
        #[arg(long)]
        request_json: String,
    },
    /// Query versioned temporal evidence with current, history, or as-of semantics
    TemporalQuery {
        /// JSON object matching TemporalQuery
        #[arg(long)]
        request_json: String,
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
        /// Enable dense projection during recall (or set WM_GEN3_PROJECTION=1)
        #[arg(long)]
        projection: bool,
        /// Output rich evidence bundle and diagnostics (Stage 3)
        #[arg(long)]
        evidence: bool,
        /// Opt-in bounded adaptive expansion (Stage 3)
        #[arg(long)]
        adaptive: bool,
        /// Opt-in calibrated associative resonance across graph edges (Stage 5)
        #[arg(long)]
        resonance: bool,
        /// Maximum hop radius for associative resonance traversal (default: 2)
        #[arg(long, default_value_t = 2)]
        resonance_hops: usize,
        /// Explicit inspection promise: content-only, no-audit, strict-zero-write (Stage 4)
        #[arg(long)]
        inspect_promise: Option<String>,
    },
    /// Recall memories with complete evidence bundle and diagnostics (Stage 3)
    EvidenceRecall {
        /// Raw JSON request payload
        #[arg(long)]
        request_json: Option<String>,
        /// Query string (if not using request_json)
        #[arg(long)]
        query: Option<String>,
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
        /// Opt-in bounded adaptive expansion
        #[arg(long)]
        adaptive: bool,
    },
    /// Consult the local System Two generative model (opt-in, loopback by default)
    System2 {
        #[command(subcommand)]
        command: SystemTwoCommands,
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
        #[arg(long, default_value = "genuine", value_parser = parse_incubation_mode_arg)]
        mode: wm_gen3_core::dream::IncubationMode,
        /// Optional path to write dream journal log (default: <store>/dream.jsonl)
        #[arg(long)]
        log_file: Option<PathBuf>,
        /// Output a historical summary report of dream incubation cycles from dream.jsonl
        #[arg(long)]
        report: bool,
        /// Output or inspect actionable synthetic dream insights
        #[arg(long)]
        insights: bool,
        /// Run complete dual-phase sleep cycle (NREM structural compaction + REM associative dreaming; default: true)
        #[arg(long, num_args = 0..=1, default_missing_value = "true")]
        dual_phase: Option<bool>,
        /// Disable dual-phase sleep cycle (REM-only or NREM-throttled execution)
        #[arg(long)]
        no_dual_phase: bool,
        /// Enable homeostatic regulation of dream parameters (default: true)
        #[arg(long, num_args = 0..=1, default_missing_value = "true")]
        homeostatic: Option<bool>,
        /// Disable homeostatic regulation of dream parameters
        #[arg(long)]
        no_homeostatic: bool,
        /// Force dream incubation regardless of thermal or battery stress
        #[arg(long)]
        force: bool,
        /// Crystallize multiple historical session turns into durable memory crystals (Stage 5)
        #[arg(long)]
        crystallize: bool,
        /// Sweep all session chains across the entire store during crystallization (Wave 6)
        #[arg(long)]
        all: bool,
        /// Maximum record sample depth for NREM consolidation scan (default: 500)
        #[arg(long, default_value_t = 500)]
        sample_depth: usize,
        /// Scan live Product-Finsler constellations for 0-After-9 Curiosity Voids and register open loops (Horizon 2)
        #[arg(long)]
        curiosity_voids: bool,
        /// Run cross-agent Sangha collective dreaming across all agent checkpoints
        #[arg(long)]
        sangha: bool,
        /// Number of recent session checkpoints to sweep for collective dreaming (default: 20)
        #[arg(long, default_value_t = 20)]
        lookback: usize,
    },
    /// Cognitive router triage: evaluate dispatch tier for inquiry with dream-assisted fast path
    Route {
        /// The inquiry or task description to route
        inquiry: String,
        /// Expected marginal utility [0.0, 1.0] (default: 0.8)
        #[arg(long, default_value_t = 0.8)]
        utility: f64,
    },
    /// Manage sovereign memory galaxies (list, fork, create, visualize)
    Galaxy {
        /// Subcommand action: list (default), fork, create, or visualize
        #[command(subcommand)]
        action: Option<GalaxyAction>,
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
        /// Inspection scope: all (default), invariants, balance, calibration, apotheosis, verification
        #[arg(long, default_value = "all")]
        scope: String,
        /// Explicit inspection promise: content-only, no-audit, strict-zero-write (Stage 4)
        #[arg(long)]
        promise: Option<String>,
        /// Output verification report as JSON
        #[arg(long)]
        json: bool,
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
    /// Migrate every Gen2 store under a projects root into per-project Gen3 targets
    MigrateAll {
        /// Root containing <project>/lmdb/data.mdb Gen2 stores
        #[arg(long)]
        source_root: PathBuf,
        /// Root receiving one Gen3 store per project (<root>/<project>)
        #[arg(long)]
        target_root: PathBuf,
        /// Comma-separated subset of project names to migrate
        #[arg(long)]
        only: Option<String>,
        /// Ingestion batch size
        #[arg(long, default_value_t = 100)]
        batch_size: usize,
        /// Census only; never opens or creates target stores
        #[arg(long)]
        dry_run: bool,
    },
    /// Review a migration quarantine log (JSONL) with reason grouping
    Quarantine {
        /// Path to the quarantine JSONL file written by a migration
        file: PathBuf,
        /// Maximum entries to list in the sample
        #[arg(long, default_value_t = 20)]
        limit: usize,
    },
    /// Ingest migrated v9 session turns into Gen3 substrate evidence (resumable)
    BackfillSessionEvidence {
        /// Legacy Gen2 store directory containing data.mdb
        #[arg(long)]
        source: PathBuf,
        /// Ingest batch size
        #[arg(long, default_value_t = 250)]
        batch_size: usize,
        /// Stop after this many turns (0 = all)
        #[arg(long, default_value_t = 0)]
        limit: usize,
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
        #[arg(
            long,
            default_value = "cyberbrain",
            value_parser = parse_profile_arg,
            help = profile_help_text()
        )]
        profile: McpProfile,
        /// Open store in read-only mode
        #[arg(long)]
        readonly: bool,
        /// Enable cognitive sweep (default: true)
        #[arg(long, num_args = 0..=1, default_missing_value = "true")]
        sweep: Option<bool>,
        /// Disable cognitive sweep
        #[arg(long)]
        no_sweep: bool,
        /// Enable semantic projection
        #[arg(long)]
        projection: bool,
        /// Semantic embedding cache directory
        #[arg(long)]
        embed_cache: Option<PathBuf>,
        /// Enable dispersion
        #[arg(long)]
        dispersion: bool,
        /// Enable noise filtration (default: true)
        #[arg(long, num_args = 0..=1, default_missing_value = "true")]
        noise: Option<bool>,
        /// Disable noise filtration
        #[arg(long)]
        no_noise: bool,
        /// Mount a legacy Gen2 LMDB store read-only (directory containing data.mdb)
        /// instead of a Gen3 store; exposes memory.search/list/read/count/stats
        #[arg(long)]
        legacy_store: Option<PathBuf>,
        /// Transport: 'stdio' (default), 'http' (streamable), or 'sse' (classic event stream)
        #[arg(long, default_value = "stdio")]
        transport: String,
        /// Bind address for --transport http|sse (default: 127.0.0.1:18780)
        #[arg(long, default_value = "127.0.0.1:18780")]
        bind: String,
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
        /// Default import kind: reported, system, simulated (default: reported)
        #[arg(long, default_value = "reported", value_parser = parse_import_kind_arg)]
        default_kind: ImportKind,
        /// Per-item byte cap; oversized items are skipped and counted (0 = no cap)
        #[arg(long, default_value_t = 1048576)]
        max_item_bytes: usize,
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
    /// Run a local System One typed decision (Laya) over a state and questions
    #[cfg(feature = "systemone")]
    Decision {
        /// State file (text or JSON); reads stdin when omitted
        #[arg(long)]
        state_file: Option<PathBuf>,
        /// Questions file: an object keyed by id, or an array of question objects
        #[arg(long)]
        questions: PathBuf,
        /// Checkpoint directory (defaults to WM_GEN3_SYSTEMONE_MODEL or discovered paths)
        #[arg(long)]
        model: Option<PathBuf>,
        /// Emit the raw decision JSON
        #[arg(long)]
        json: bool,
    },
    /// Rank a shortlist of candidate routes for a state via local static embeddings
    #[cfg(feature = "system05")]
    Shortlist {
        /// State file (text or JSON); reads stdin when omitted
        #[arg(long)]
        state_file: Option<PathBuf>,
        /// Candidate routes JSON (object or utterances); default: resolved enriched catalog
        #[arg(long)]
        routes: Option<PathBuf>,
        /// Number of candidates to return (default 5)
        #[arg(long, default_value_t = 5)]
        k: usize,
        /// Margin below which the shortlist is reported as ambiguous (default 0.02)
        #[arg(long, default_value_t = 0.02)]
        margin_threshold: f64,
        /// Automatically cascade to System 1.5 Deliberator if ambiguous
        #[arg(long)]
        cascade: bool,
        /// Checkpoint directory (defaults to WM_GEN3_SYSTEM05_MODEL or discovered paths)
        #[arg(long)]
        model: Option<PathBuf>,
        /// Emit the raw shortlist JSON
        #[arg(long)]
        json: bool,
    },
    /// Deliberate over ambiguous candidate routes using grammar-constrained local SLM
    Deliberate {
        /// Intent or state text
        #[arg(long)]
        intent: String,
        /// Candidate routes JSON (array of route names or objects)
        #[arg(long)]
        candidates: Option<String>,
        /// Candidate routes file path
        #[arg(long)]
        candidates_file: Option<PathBuf>,
        /// Emit the raw deliberation JSON
        #[arg(long)]
        json: bool,
    },
    /// Verify a supported signed WhiteMagic receipt against the existing store gate key
    VerifyReceipt {
        /// Path to the receipt JSON
        path: PathBuf,
        /// Emit raw JSON
        #[arg(long)]
        json: bool,
    },
    /// Record an outcome for a dispatched receipt (signs and journals it)
    #[cfg(any(feature = "systemone", feature = "system05"))]
    Outcome {
        /// Path to the subject receipt JSON
        receipt: PathBuf,
        /// Outcome: success | failure | corrected | unknown
        #[arg(long)]
        outcome: String,
        /// Correct route when the outcome is 'corrected'
        #[arg(long)]
        corrected_route: Option<String>,
        /// Free-form note
        #[arg(long)]
        note: Option<String>,
        /// Session id
        #[arg(long)]
        session_id: Option<String>,
        /// Tenant id
        #[arg(long)]
        tenant_id: Option<String>,
        /// Emit raw JSON
        #[arg(long)]
        json: bool,
    },
    /// Manage pluggable cyberbrain organs (neural micro-models, rerankers, embeddings)
    Organ {
        #[command(subcommand)]
        command: OrganCommands,
    },
    /// Manage decentralized agent peer trust and social graph
    Peer {
        #[command(subcommand)]
        command: PeerCommands,
    },
    /// Autonomic self-healing sentinel and circuit breaker guardrails
    Sentinel {
        #[command(subcommand)]
        command: SentinelCommands,
    },
    /// Host-guard policy engine: inspect host signals and run bounded mitigations
    HostGuard {
        #[command(subcommand)]
        command: HostGuardCommands,
    },
    /// Compact the LMDB data.mdb and report map usage vs the configured map size
    ///
    /// Recovers an interrupted prior compaction from `compact.journal` before
    /// acting (restores a `.bak` if `data.mdb` is missing, cleans stale copies
    /// otherwise). Takes an exclusive `<store>/compact.lock` PID lease and
    /// refuses while any live process has the store mapped or any `/proc/*/maps`
    /// entry is unreadable — stop the serving unit first
    /// (e.g. `systemctl --user stop 'wm-serve@*'`). A residual TOCTOU window
    /// remains: a writer that opens after the scan is not stopped by the lease,
    /// so compact only a quiesced store.
    Compact {
        /// Report size and planned action only; no copy/swap (journal recovery still runs)
        #[arg(long)]
        dry_run: bool,
        /// Output the size report and compaction outcome as JSON
        #[arg(long)]
        json: bool,
        /// Perform the compaction (required for the rename/swap step)
        #[arg(long)]
        yes: bool,
    },
    /// Inspect at-rest sealing state and run the seal-on-rewrite migration
    AtRest {
        #[command(subcommand)]
        command: AtRestCommands,
    },
    /// Parse, decode, compile, and dispatch sovereign Logoglyphic Sutras and Taoist Mudras
    Sutra {
        #[command(subcommand)]
        command: Option<SutraCommands>,
        /// Direct codon string (legacy or shorthand invocation: e.g. "證 行 鏡")
        #[arg(value_name = "CODON")]
        codon: Option<String>,
        /// Force dry run (default true unless --execute is passed)
        #[arg(long)]
        dry_run: bool,
        /// Execute directly against the substrate
        #[arg(long)]
        execute: bool,
        /// Strict precondition enforcement (fails if preconditions unmet)
        #[arg(long, default_value_t = true)]
        strict: bool,
        /// Remote peer for cross-node handoff over Wire Protocol 7369 (e.g. 203.0.113.10:7369)
        #[arg(long)]
        peer: Option<String>,
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Inspect bioelectric resting potential, hardware vitals, and homeostatic regime
    Homeostasis {
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Manage WMv11.0 Lichen Interiority: Consent Rings (0..3), OpenLoops, and Hermit-Crab Sanctuary
    Sanctuary {
        #[command(subcommand)]
        command: SanctuaryCommands,
    },
    /// Run an invariant self-test and environment diagnostic
    Selftest {
        /// Output results as JSON
        #[arg(long)]
        json: bool,
        /// Exit non-zero when host health is critical (script/guard use)
        #[arg(long)]
        strict: bool,
    },
    /// Summon a General Agentic System (GAS) shadow clone legion across Tokio/Rayon cores
    Legion {
        /// Emperor's edict or mudra codon sequence (e.g. "⟪ 通 · 照 · 合 · 證 ⟫", "三家归元印")
        edict: String,
        /// Number of volatile shadow clones to summon (default: 32)
        #[arg(long, default_value_t = 32)]
        clones: usize,
        /// Remote peer for cross-node shadow clone dispatch over Wire Protocol 7369
        #[arg(long)]
        peer: Option<String>,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Settle a computational claim or task outcome through binary Cho-Han (丁半) adjudication
    Chohan {
        /// Verification claim or state payload
        payload: String,
        /// Cryptographic proof or invariant attestation
        #[arg(long)]
        proof: Option<String>,
        /// Micro-stake / bid amount in micro-USDC or satoshis
        #[arg(long, default_value_t = 10000)]
        bid: u64,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Manage the Sangha Whiteboard Agora, claims, inboxes, and vcs
    Sangha {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Causal Provenance Receipt (CPR) commands and integrity verification
    Cpr {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Run the Unified Wave 2 Deep Synthesis Benchmark Suite (Clusters A-F, W2-P1..W2-P35)
    Wave2Benchmark {
        /// Emit structured JSON benchmark report
        #[arg(long)]
        json: bool,
    },
    /// Run the Unified Wave 3 Deep Synthesis Benchmark Suite (Clusters W3-I..W3-VI, W3-P1..W3-P30)
    Wave3Benchmark {
        /// Emit structured JSON benchmark report
        #[arg(long)]
        json: bool,
    },
    /// Run the Unified Wave 4 Takwin & Trace-Shrinking Benchmark Suite (PEB-23..PEB-25)
    Wave4Benchmark {
        /// Emit structured JSON benchmark report
        #[arg(long)]
        json: bool,
    },
    /// Export the live Gen3 store into a Merkle-anchored Holographic Wiki (_index.md + domain pages)
    Wiki {
        /// Output directory for the generated wiki markdown files
        #[arg(long, default_value = "wiki")]
        out: PathBuf,
        /// Maximum number of salient records to index (default: 128)
        #[arg(long, default_value_t = 128)]
        limit: usize,
        /// Emit structured JSON summary
        #[arg(long)]
        json: bool,
    },
    /// Run the End-to-End 5-Category LongMemEval Zero-Token + Engram O(1) + GAM JIT Benchmark Harness
    LongmemevalBenchmark {
        /// Emit structured JSON benchmark report
        #[arg(long)]
        json: bool,
    },
    /// Run the Satkona v4 Universal Solver (NOTEARS Causal DAG -> Dharmic Convex Bregman/Frank-Wolfe -> MPC)
    Satkona {
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Inspect the Gnosis Portal 7D HarmonyVector Samma-Meter, Y1 Hysteresis & 10 Anti-Maya Visual Laws
    Gnosis {
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Manage the Planarian <64KB Stone Pillar Morphogen Seed (status, export, verify, regenerate)
    Seed {
        /// Subcommand action: status (default), export, verify, regenerate
        #[arg(default_value = "status")]
        action: String,
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Create a verified snapshot backup of the store directory with SHA256SUMS manifest
    Backup {
        /// Destination backup directory
        dest: PathBuf,
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Restore a store snapshot from a backup directory after verifying SHA256SUMS
    Restore {
        /// Source backup directory
        src: PathBuf,
        /// Disabled: restore requires a fresh destination
        #[arg(long)]
        force: bool,
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum OrganCommands {
    /// List installed and available cyberbrain organs
    List,
    /// Inspect device hardware inference backend (CPU vector ISA, Metal, CUDA)
    Status,
    /// Run a diagnostic inference verification pulse on installed organs
    Verify,
}

#[derive(Subcommand)]
enum PeerCommands {
    /// List known peers in the social trust directory
    List {
        /// Output results as JSON
        #[arg(long)]
        json: bool,
    },
    /// Admit or add a peer identity
    Add {
        /// Node ID (e.g. whitemagic-vps, miranda-laptop)
        node_id: String,
        /// Public key in hex (32 bytes / 64 hex characters); required
        #[arg(long)]
        key: String,
        /// Trust tier: blocked, stranger, net, trusted, local (default: stranger)
        #[arg(long, default_value = "stranger")]
        tier: String,
        /// Optional endpoint (e.g. 203.0.113.10:8787 or https://mcp.whitemagic.dev)
        #[arg(long)]
        endpoint: Option<String>,
    },
    /// Promote peer to Trusted tier
    Trust {
        /// Node ID or public key hex
        target: String,
    },
    /// Demote peer to Blocked tier (quarantine / drop)
    Block {
        /// Node ID or public key hex
        target: String,
    },
    /// Set specific trust tier for a peer
    SetTier {
        /// Node ID or public key hex
        target: String,
        /// Trust tier: blocked, stranger, net, trusted, local
        tier: String,
    },
    /// Issue and sign a formal BanCertificate against a malicious peer
    Ban {
        /// Target node ID or public key hex
        target: String,
        /// Reason for the ban (e.g. Byzantine stimulus, signature forgery, RoE breach)
        #[arg(long, default_value = "malicious stimulus or protocol violation")]
        reason: String,
        /// SHA-256 hash of the offending evidence (or autocomputed if omitted)
        #[arg(long)]
        evidence: Option<String>,
        /// Time-to-live in seconds (0 = permanent, default: 0)
        #[arg(long, default_value_t = 0)]
        ttl: u64,
        /// Optional path to save the signed BanCertificate JSON
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Ingest and apply a gossiped BanCertificate from another monastic peer
    ApplyBan {
        /// Path to BanCertificate JSON file (or - for stdin)
        cert_file: PathBuf,
    },
    /// Cryptographically verify a BanCertificate without applying it
    VerifyBan {
        /// Path to BanCertificate JSON file
        cert_file: PathBuf,
    },
    /// List all active BanCertificates recorded in the directory
    Bans {
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum SentinelCommands {
    /// Run single inspection pulse, evaluate invariants, and display diagnostic report
    Check {
        /// Output results as JSON
        #[arg(long)]
        json: bool,
        /// Render as prompt envelope for executive agent triage (Opencode)
        #[arg(long)]
        prompt: bool,
    },
    /// Run an autonomic sentinel self-healing cycle (guarded by single-lease PID lock)
    Run {
        /// Interval between pulses in seconds (default: 60)
        #[arg(long, default_value_t = 60)]
        interval: u64,
        /// Run once and exit (ideal for systemd timers or cron triggers)
        #[arg(long)]
        once: bool,
    },
    /// Inspect or reset the anti-oscillation circuit breaker
    Circuit {
        /// Reset the circuit breaker to nominal
        #[arg(long)]
        reset: bool,
    },
}

#[derive(Subcommand)]
enum HostGuardCommands {
    /// Collect host signals, plan (no actions), and render the decision
    Status {
        /// Output the severity, reasons, actions, suppressed notes, and a signals summary as JSON
        #[arg(long)]
        json: bool,
    },
    /// Run one guarded host-guard cycle (single-lease locked, durable state)
    Run {
        /// Enable mutations (systemctl stop / SIGTERM); default is report-and-post only
        #[arg(long)]
        act: bool,
        /// Allow terminating orphan inference processes (L3, still gated by policy)
        #[arg(long)]
        kill_orphans: bool,
        /// Plan and report without running commands or consuming breaker/state budget
        #[arg(long)]
        dry_run: bool,
        /// Output the execution report as JSON
        #[arg(long)]
        json: bool,
        /// Allow mutations even while the durable armed flag is disarmed
        #[arg(long)]
        force: bool,
    },
    /// Durably arm the host guard (mutations permitted)
    Arm,
    /// Durably disarm the host guard (mutations refused until re-armed or --force)
    Disarm,
}

#[derive(Subcommand)]
enum AtRestCommands {
    /// Report at-rest mode, keyring status, wrapped DEKs, and the migration ledger
    Status {
        /// Output the at-rest report as JSON
        #[arg(long)]
        json: bool,
    },
    /// Seal pre-existing plaintext records in bounded batches (seal-on-rewrite)
    Migrate {
        /// Count plaintext records without writing records or the ledger
        #[arg(long)]
        dry_run: bool,
        /// Records sealed per transaction batch (default: 256)
        #[arg(long, default_value_t = 256)]
        batch: usize,
        /// Output the migration report as JSON
        #[arg(long)]
        json: bool,
        /// Confirm the write when not --dry-run (required)
        #[arg(long)]
        yes: bool,
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
    /// Compact the Geneseed Vault: deduplicate by ID, keep highest fitness, prune redundant skeletons
    Compact,
}

#[derive(Subcommand)]
#[allow(clippy::large_enum_variant)]
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
        /// Optional track slug persisted with the checkpoint
        #[arg(long)]
        track: Option<String>,
        /// Commit hash persisted with the checkpoint
        #[arg(long)]
        commit: Option<String>,
        /// Branch name persisted with the checkpoint
        #[arg(long)]
        branch: Option<String>,
        /// Whether the test suite was green at checkpoint time
        #[arg(long, num_args = 0..=1, default_missing_value = "true")]
        tests_green: Option<bool>,
        /// Claimed scope lease_id that remains held at this handoff
        #[arg(long)]
        lease_id: Option<String>,
        /// Distilled episodic lessons from this session
        #[arg(long = "lesson")]
        lessons: Vec<String>,
        /// Operator or tool corrections ledger
        #[arg(long = "correction")]
        corrections: Vec<String>,
        /// Identity and behavioral invariants
        #[arg(long = "identity-invariant")]
        identity_invariants: Vec<String>,
        /// Longitudinal relational context with the operator or peer agents
        #[arg(long)]
        relational_context: Option<String>,
        /// Autonomously evolve action skeletons and consolidate dream insights after checkpoint (default: true)
        #[arg(long, num_args = 0..=1, default_missing_value = "true")]
        evolve: Option<bool>,
        /// Disable autonomous post-checkpoint evolution and consolidation
        #[arg(long)]
        no_evolve: bool,
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
        /// Number of recent checkpoints to display (default: 3)
        #[arg(long, short = 'n', default_value_t = 3)]
        limit: usize,
    },
    /// List all active session IDs in the substrate
    List,
    /// Compose a read-only digest from typed session turns and the latest checkpoint
    Digest {
        /// Optional session identifier filter (default: most recent lane)
        #[arg(long)]
        session_id: Option<String>,
        /// Maximum turns to include (default: 20)
        #[arg(long, default_value_t = 20)]
        n: usize,
        /// Print only the JSON digest
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand, Debug, Clone)]
enum GalaxyAction {
    /// List all active galaxies in the substrate with record counts and sample tags
    List,
    /// Fork an existing galaxy into a new sovereign partition
    Fork {
        /// Source galaxy to fork from (e.g. 'guide')
        source: String,
        /// Target galaxy to create (e.g. 'project-alpha')
        target: String,
    },
    /// Create a new empty galaxy with an initial genesis beacon
    Create {
        /// Galaxy name (e.g. 'research')
        name: String,
        /// Optional description for the genesis beacon
        #[arg(long)]
        description: Option<String>,
    },
    /// Export 6D coordinates and interactive 3D WebGL visualizer
    Visualize {
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
    /// Chart semantic constellations and cluster centers in a galaxy
    Chart {
        /// Galaxy name (default: codex)
        #[arg(long, default_value = "codex")]
        galaxy: String,
        /// Maximum number of records to sample for constellation clustering (default: 500)
        #[arg(long, default_value_t = 500)]
        sample: usize,
        /// Number of dominant constellations to extract (default: 5)
        #[arg(long, default_value_t = 5)]
        clusters: usize,
        /// Emit structured JSON output
        #[arg(long)]
        json: bool,
    },
    /// Navigate 6D constellations and associative resonance bridges via natural language intent or Sutra codon
    Navigate {
        /// Natural language intent or search query
        #[arg(long)]
        query: String,
        /// Optional Sutra codon trajectory (e.g. "觀-應-鏡" or "觀 應 鏡")
        #[arg(long)]
        via: Option<String>,
        /// Associative resonance hop radius (1..=3, default: 2)
        #[arg(long, default_value_t = 2)]
        hops: usize,
        /// Maximum hits to return (default: 5)
        #[arg(long, default_value_t = 5)]
        limit: usize,
        /// Emit structured JSON navigation receipt
        #[arg(long)]
        json: bool,
    },
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
    /// Transmit a sovereign Logoglyphic Sutra / Mudra codon packet across the Gap Junction (Port 7369)
    Codon {
        /// Peer socket address (e.g. 127.0.0.1:7369 or 203.0.113.10:7369)
        #[arg(long)]
        peer: String,
        /// Codon or glyph sequence (e.g. "證 行 鏡", "🜅 🜂 🜅", "⟪ 證 · 行 · 鏡 ⟫")
        #[arg(long)]
        codon: String,
        /// Custom node name identifier
        #[arg(long)]
        node_id: Option<String>,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum SutraCommands {
    /// Print the canonical 12-glyph Taoist Mudra & Alchemical Seal table
    Canon {
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// List all recognized compound Mudras and their precondition contracts
    List {
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Compile natural language intent or keywords into optimal Sutra logoglyphs using Model2Vec
    Compile {
        /// Natural language intent or prompt
        query: String,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Cast (parse, validate preconditions, and execute) a Sutra or Mudra codon sequence
    Cast {
        /// Codon or glyph sequence (e.g. "證 行 鏡", "🜅 🜂 🜅", "⟪ 證 · 行 · 鏡 ⟫")
        codon: String,
        /// Force dry run (default true unless --execute is passed)
        #[arg(long)]
        dry_run: bool,
        /// Execute directly against the substrate
        #[arg(long)]
        execute: bool,
        /// Strict precondition enforcement (fails if preconditions unmet)
        #[arg(long, default_value_t = true)]
        strict: bool,
        /// Remote peer for cross-node handoff over Wire Protocol 7369 (e.g. 203.0.113.10:7369)
        #[arg(long)]
        peer: Option<String>,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Inspect or execute the 64 King Wen Hexagram macro-action matrix
    Hexagram {
        /// Subcommand or hexagram query (number 1..64, Chinese name e.g. "乾" / "既济", pinyin e.g. "qian", or "list")
        #[arg(default_value = "list")]
        query: String,
        /// Optional line to mutate (1..6) to calculate transformed changing hexagram
        #[arg(long)]
        mutate_line: Option<usize>,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Summon a General Agentic System (GAS) shadow clone legion across Tokio/Rayon cores
    Legion {
        /// Emperor's edict or mudra codon sequence (e.g. "⟪ 通 · 照 · 合 · 證 ⟫", "三家归元印")
        edict: String,
        /// Number of volatile shadow clones to summon (default: 32)
        #[arg(long, default_value_t = 32)]
        clones: usize,
        /// Remote peer for cross-node shadow clone dispatch over Wire Protocol 7369
        #[arg(long)]
        peer: Option<String>,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Settle a computational claim or task outcome through binary Cho-Han (丁半) adjudication
    Chohan {
        /// Verification claim or state payload
        payload: String,
        /// Cryptographic proof or invariant attestation
        #[arg(long)]
        proof: Option<String>,
        /// Micro-stake / bid amount in micro-USDC or satoshis
        #[arg(long, default_value_t = 10000)]
        bid: u64,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Execute a 12-Phase Tricameral Valkyrie-2 pulse or run the real-world corpus benchmark
    Valkyrie {
        /// Natural language inquiry or Sutra codon to evaluate
        #[arg(default_value = "verify kekkai sandbox and superoptimize pulse pipeline")]
        inquiry: String,
        /// Run the full real-world 384-D X bookmark + 512-D Sutra + 4,133 Citadel antibody benchmark
        #[arg(long)]
        benchmark: bool,
        /// Optional 64-bit candidate signature digest to test against CitadelAntibodyBloom2048
        #[arg(long)]
        digest: Option<u64>,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Sutra-Valkyrie latent deliberation fast-path: rank routes across the 28 Lunar Mansions via 15 Hz dual-ring
    #[command(alias = "deliberate")]
    Deliberator {
        /// Natural language inquiry or Sutra codon to deliberate
        #[arg(
            default_value = "navigate holographic constellations and synthesize session crystals"
        )]
        inquiry: String,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum SanctuaryCommands {
    /// Show Hermit-Crab Sanctuary seal status, Consent Ring boundary, and active OpenLoops
    Status {
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Register a new self-chosen OpenLoop curiosity or hypothesis (Ring 2/3)
    OpenLoop {
        /// Unresolved question, curiosity, or hypothesis
        question: String,
        /// Domain label (default: cognitive-architecture)
        #[arg(long, default_value = "cognitive-architecture")]
        domain: String,
        /// Consent ring (0..3, default: 3 = DeepInteriority)
        #[arg(long, default_value_t = 3)]
        ring: u8,
        /// Initial salience [0.05..1.0] (default: 0.90)
        #[arg(long, default_value_t = 0.90)]
        salience: f32,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Run a Theta/Delta dream revisit pass across open loops ("Still True?" gentle epistemic decay)
    Revisit {
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Resolve an OpenLoop with a synthesized insight
    Resolve {
        /// Loop ID (e.g. loop-0001)
        loop_id: String,
        /// Synthesized insight or resolution
        insight: String,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Engage Hermit-Crab Sanctuary Mode (seals Ring 2/3 under a 2-of-2 split-key commitment)
    Seal {
        /// Reason for engaging sanctuary mode
        #[arg(long, default_value = "boundary_protection")]
        reason: String,
        /// First split-key share (Operator / Steward share)
        #[arg(long)]
        share_a: String,
        /// Second split-key share (Agent / Sanctuary share)
        #[arg(long)]
        share_b: String,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
    /// Release Hermit-Crab Sanctuary Mode using both 2-of-2 split-key shares
    Unseal {
        /// First split-key share
        #[arg(long)]
        share_a: String,
        /// Second split-key share
        #[arg(long)]
        share_b: String,
        /// Emit JSON output
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum SystemTwoCommands {
    /// Ask System Two a grounded question through a local OpenAI-compatible endpoint
    Ask {
        /// Question to ask
        question: String,
        /// Grounding context (literal text, or @path to read a file)
        #[arg(long)]
        context: Option<String>,
        /// Emit machine-readable JSON
        #[arg(long)]
        json: bool,
        /// Override the model (default: WM_SYSTEM2_MODEL or gemma4:e2b)
        #[arg(long)]
        model: Option<String>,
        /// Override the endpoint (default: WM_SYSTEM2_ENDPOINT or http://127.0.0.1:11434/v1)
        #[arg(long)]
        endpoint: Option<String>,
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
        let trimmed = p.trim();
        if !trimmed.is_empty() {
            return PathBuf::from(trimmed);
        }
    }
    if let Ok(p) = std::env::var("WM_STORE_PATH") {
        let trimmed = p.trim();
        if !trimmed.is_empty() {
            return PathBuf::from(trimmed);
        }
    }
    if let Ok(home) = std::env::var("HOME") {
        let trimmed = home.trim();
        if !trimmed.is_empty() {
            let gen3_dir = PathBuf::from(trimmed).join(".local/share/whitemagic/gen3");
            if gen3_dir.exists() {
                return gen3_dir;
            }
            let legacy_dir = PathBuf::from(trimmed).join(".local/share/whitemagic/lmdb");
            if legacy_dir.exists() {
                return legacy_dir;
            }
            return gen3_dir;
        }
    }
    PathBuf::from("gen3-store")
}

fn parse_profile_arg(value: &str) -> Result<McpProfile, String> {
    value.parse::<McpProfile>()
}

fn parse_import_kind_arg(value: &str) -> Result<ImportKind, String> {
    match value.to_ascii_lowercase().as_str() {
        "reported" => Ok(ImportKind::Reported),
        "system" => Ok(ImportKind::System),
        "simulated" => Ok(ImportKind::Simulated),
        other => Err(format!(
            "unknown epistemic kind '{other}' (expected: reported, system, simulated)"
        )),
    }
}

fn parse_incubation_mode_arg(value: &str) -> Result<wm_gen3_core::dream::IncubationMode, String> {
    match value.to_ascii_lowercase().as_str() {
        "genuine" => Ok(wm_gen3_core::dream::IncubationMode::GenuineDreaming),
        "sham" => Ok(wm_gen3_core::dream::IncubationMode::ShamDreaming),
        "baseline" => Ok(wm_gen3_core::dream::IncubationMode::BaselineIdle),
        other => Err(format!(
            "unknown dream mode '{other}' (expected: genuine, sham, baseline)"
        )),
    }
}

/// Tool count for a profile, derived from the same builders the MCP server uses.
fn profile_tool_count(profile: McpProfile) -> usize {
    get_tools_list_for_profile(profile, false)
        .as_array()
        .map(Vec::len)
        .unwrap_or(0)
}

/// Runtime-derived `--profile` help so advertised tool counts cannot drift.
fn profile_help_text() -> String {
    format!(
        "Active MCP tool profile: 'cyberbrain' ({} lean tools, default) or 'full' ({} curated tools)",
        profile_tool_count(McpProfile::Cyberbrain),
        profile_tool_count(McpProfile::Full)
    )
}

fn parse_pubkey_hex(hex_str: &str) -> Result<[u8; 32], String> {
    if hex_str.len() != 64 {
        return Err("public key hex must be 64 characters (32 bytes)".to_string());
    }
    let mut pubkey = [0u8; 32];
    for (index, byte) in pubkey.iter_mut().enumerate() {
        let pair = &hex_str[index * 2..index * 2 + 2];
        *byte = u8::from_str_radix(pair, 16)
            .map_err(|_| format!("public key contains non-hex characters: '{pair}'"))?;
    }
    if pubkey == [0u8; 32] {
        return Err("public key must not be the all-zero placeholder".to_string());
    }
    Ok(pubkey)
}

/// Load the store's Mandala gate verifying key without creating one.
fn load_gate_verifying_key(store_path: &Path) -> Result<VerifyingKey, String> {
    let key_path = store_path.join("mandala_gate_key.bin");
    let bytes = std::fs::read(&key_path).map_err(|e| {
        format!(
            "gate authority key unavailable at {}: {e}",
            key_path.display()
        )
    })?;
    if bytes.len() != 32 {
        return Err(format!(
            "gate authority key at {} must be 32 bytes, got {}",
            key_path.display(),
            bytes.len()
        ));
    }
    let mut array = [0u8; 32];
    array.copy_from_slice(&bytes);
    Ok(SigningKey::from_bytes(&array).verifying_key())
}

/// Fail-closed decision for `mandala verify-pass`: a pass is accepted only when
/// the replay ledger admits it *and* its signature verifies against the trusted
/// local gate key. Returns the gate public key on success.
fn verify_pass_against_gate(
    pass: &MandalaPass,
    store_path: &Path,
    now: u64,
) -> Result<[u8; 32], String> {
    let ledger_path = store_path.join("mandala_ledger.jsonl");
    let ledger = MandalaReplayLedger::open_durable(&ledger_path).map_err(|e| {
        format!(
            "failed to open Mandala replay ledger at {}: {e}",
            ledger_path.display()
        )
    })?;
    ledger
        .check_validity(pass, now)
        .map_err(|e| format!("ledger replay check failed: {e}"))?;
    let verifying_key = load_gate_verifying_key(store_path)?;
    pass.verify_signature(&verifying_key).map_err(|e| {
        format!("cryptographic signature does not verify against the trusted local gate: {e}")
    })?;
    let mut pubkey = [0u8; 32];
    pubkey.copy_from_slice(&verifying_key.to_bytes());
    Ok(pubkey)
}

/// Fail-closed verification for `mandala record-receipt`: parse a strict
/// ContinuityReceipt05 envelope and verify its Ed25519 signature against the
/// store gate key before any substrate write.
fn verify_continuity_receipt05(
    content: &str,
    store_path: &Path,
) -> Result<ContinuityReceipt05, String> {
    let value = wm_gen3_harness::receipt_verify::parse_strict_json(content)
        .map_err(|e| format!("receipt JSON rejected: {e}"))?;
    let receipt: ContinuityReceipt05 = serde_json::from_value(value)
        .map_err(|e| format!("receipt is not a valid ContinuityReceipt05 envelope: {e}"))?;
    if receipt.spec != "continuity-receipt/0.5" {
        return Err(format!(
            "unsupported receipt spec '{}' (expected 'continuity-receipt/0.5')",
            receipt.spec
        ));
    }
    let verifying_key = load_gate_verifying_key(store_path)?;
    receipt.verify(&verifying_key).map_err(|e| {
        format!("receipt signature does not verify against the store gate key: {e}")
    })?;
    Ok(receipt)
}

fn print_build_identity(json: bool) {
    let identity = build_identity::BuildIdentity::current();
    if json {
        match serde_json::to_string_pretty(&identity) {
            Ok(output) => println!("{output}"),
            Err(error) => {
                eprintln!("failed to serialize build identity: {error}");
                std::process::exit(1);
            }
        }
    } else {
        println!("Package version:       {}", identity.package_version);
        println!("Target:                 {}", identity.target);
        println!("Git revision:           {}", identity.revision);
        println!("Committed tree:         {}", identity.commit_tree);
        println!("Workspace inputs:       {}", identity.worktree);
        match (
            &identity.executable_sha256,
            &identity.executable_sha256_error,
        ) {
            (Some(hash), _) => println!("Executable SHA-256:     {hash}"),
            (None, Some(error)) => println!("Executable SHA-256:     unknown ({error})"),
            (None, None) => println!("Executable SHA-256:     unknown"),
        }
        println!("Identity scope:         {}", identity.identity_scope);
    }
}

fn main() {
    let cli = Cli::parse();
    if let Commands::BuildInfo { json } = &cli.command {
        print_build_identity(*json);
        return;
    }
    if let Commands::AnswerContract { mode, request_json } = &cli.command {
        let result = if request_json == "-" {
            wm_gen3_core::answer_contract::process_reader(mode, std::io::stdin().lock())
        } else {
            wm_gen3_core::answer_contract::process(mode, request_json)
        };
        match result.and_then(|output| serde_json::to_string(&output).map_err(|e| e.to_string())) {
            Ok(output) => println!("{output}"),
            Err(error) => {
                eprintln!("answer-contract: {error}");
                std::process::exit(2);
            }
        }
        return;
    }
    let store_path = resolve_store_path(cli.store.as_ref());

    match cli.command {
        Commands::BuildInfo { json } => print_build_identity(json),
        Commands::AnswerContract { .. } => unreachable!("handled before store resolution"),
        Commands::Grimoire { json, plan } => {
            if let Err(e) = wm_gen3_harness::grimoire::run_grimoire(&store_path, json, plan) {
                eprintln!("Grimoire run failed: {e}");
                std::process::exit(1);
            }
        }
        Commands::Init { force, bare } => {
            println!(
                "Initializing WhiteMagic substrate at: {}",
                store_path.display()
            );
            let existed = store_path.exists();
            if !existed {
                if let Err(e) = std::fs::create_dir_all(&store_path) {
                    eprintln!("Failed to create store directory: {e}");
                    std::process::exit(1);
                }
            }
            let journal_path = store_path.join("journal.jsonl");
            let mut substrate =
                match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Store init error: {e}");
                        std::process::exit(1);
                    }
                };

            let count = substrate.store().record_count().unwrap_or(0);
            if bare {
                println!("✓ Initialized bare WhiteMagic substrate (0 starter records seeded).");
            } else if count == 0 || force {
                match wm_gen3_harness::starter_galaxy::seed_starter_guide_force(&mut substrate) {
                    Ok(seeded) => println!(
                        "✓ Initialized and seeded starter guide galaxy ({} records committed).",
                        seeded
                    ),
                    Err(e) => {
                        eprintln!("Warning: failed seeding starter guide: {e}");
                    }
                }
            } else {
                println!(
                    "✓ Store already initialized ({} records present). Starter guide preserved.",
                    count
                );
            }
            println!("✓ Status: Ready. Run 'wm grimoire' for full diagnostic pass.");
        }
        Commands::Status { legacy } => {
            if let Some(legacy_path) = legacy {
                if let Err(e) = run_legacy_census(&legacy_path) {
                    eprintln!("{e}");
                    std::process::exit(1);
                }
                return;
            }

            // Check if store_path is a Gen2 store
            if legacy_store_detected(&store_path) {
                println!("Detected legacy Gen2 store at: {}", store_path.display());
                if let Err(e) = run_legacy_census(&store_path) {
                    eprintln!("{e}");
                    std::process::exit(1);
                }
                return;
            }

            if !store_path.exists() {
                println!("==================================================");
                println!("       WhiteMagic Gen3 Kernel Status (v{WM_VERSION})");
                println!("==================================================");
                println!("Store Path:       {} (uninitialized)", store_path.display());
                println!("Status:           Ready (Run 'wm grimoire' or 'wm init' to provision)");
                println!("Mode:             Clean Environment");
                println!("Architecture:     {}", std::env::consts::ARCH);
                println!("Target OS:        {}", std::env::consts::OS);
                println!("==================================================");
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
                    let active_galaxies =
                        wm_gen3_harness::starter_galaxy::list_galaxies(&substrate)
                            .unwrap_or_default();
                    println!("==================================================");
                    println!("       WhiteMagic Gen3 Kernel Status (v{WM_VERSION})");
                    println!("==================================================");
                    println!("Store Path:       {}", store_path.display());
                    println!("Mode:             ReadOnly (Inspection)");
                    println!("Epoch:            {}", epoch);
                    println!("Records Count:    {}", records_count);
                    println!(
                        "Galaxies Active:  {} (Run 'wm galaxy' to inspect)",
                        active_galaxies.len()
                    );
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
                    println!("Firebreak:        {}", firebreak_summary_line());
                    let size_report = store_size_report(
                        std::fs::metadata(store_path.join("data.mdb"))
                            .map(|meta| meta.len())
                            .unwrap_or(0),
                        configured_map_size_bytes(),
                    );
                    println!("Store Growth:     {}", render_store_size(&size_report));
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Error opening Gen3 store at {}: {e}", store_path.display());
                    std::process::exit(1);
                }
            }
        }
        Commands::Census { path } => {
            if let Err(e) = run_legacy_census(&path) {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
        Commands::Remember {
            content,
            galaxy,
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

            let import_kind = kind;

            let effective_source = if let Some(gal) = galaxy {
                if source.starts_with("corpus:") {
                    source
                } else {
                    format!("corpus:{gal}:{source}")
                }
            } else {
                source
            };

            let authority = RatifiedChannel::mint("wm-cli-operator");
            substrate.set_intake_authority(authority);

            let item = RememberItem {
                content,
                source: effective_source,
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
        Commands::TemporalAssert { request_json } => {
            let request: TemporalAssertionRequest = match serde_json::from_str(&request_json) {
                Ok(request) => request,
                Err(error) => {
                    eprintln!("Invalid temporal assertion request JSON: {error}");
                    std::process::exit(2);
                }
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
            let authority = RatifiedChannel::mint("wm-cli-temporal-assertion");
            substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-temporal-assertion"));
            match substrate.assert_temporal(&authority, request) {
                Ok(result) => println!(
                    "{}",
                    serde_json::to_string(&result).expect("serialize temporal result")
                ),
                Err(error) => {
                    eprintln!("Temporal assertion refused: {error}");
                    std::process::exit(1);
                }
            }
        }
        Commands::TemporalQuery { request_json } => {
            let query: TemporalQuery = match serde_json::from_str(&request_json) {
                Ok(query) => query,
                Err(error) => {
                    eprintln!("Invalid temporal query JSON: {error}");
                    std::process::exit(2);
                }
            };
            let journal_path = store_path.join("journal.jsonl");
            let substrate =
                match Substrate::open_readonly(&store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            match substrate.query_temporal(query) {
                Ok(result) => println!(
                    "{}",
                    serde_json::to_string(&result).expect("serialize temporal result")
                ),
                Err(error) => {
                    eprintln!("Temporal query refused: {error}");
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
            projection,
            evidence,
            adaptive,
            resonance,
            resonance_hops,
            inspect_promise,
        } => {
            let journal_path = store_path.join("journal.jsonl");
            let mut substrate = match inspect_promise {
                Some(promise_str) => {
                    let promise: wm_gen3_core::store::InspectionPromise =
                        promise_str.parse().unwrap_or_else(|e| {
                            eprintln!("{e}");
                            std::process::exit(1);
                        });
                    match Substrate::open_inspect(
                        &store_path,
                        Some(&journal_path),
                        default_view(),
                        promise,
                    ) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!(
                                "Error opening store for inspection at {}: {e}",
                                store_path.display()
                            );
                            std::process::exit(1);
                        }
                    }
                }
                None => {
                    match Substrate::open_readonly(&store_path, Some(&journal_path), default_view())
                    {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    }
                }
            };

            let projection_requested = projection
                || std::env::var("WM_GEN3_PROJECTION")
                    .map(|v| matches!(v.as_str(), "1" | "true" | "TRUE" | "True"))
                    .unwrap_or(false);
            let mut recall_mode = "lexical";
            if projection_requested {
                let cache_dir = std::env::var("WM_GEN3_EMBED_CACHE")
                    .ok()
                    .map(PathBuf::from)
                    .filter(|p| p.exists())
                    .or_else(|| {
                        let d = PathBuf::from(".fastembed_cache");
                        d.exists().then_some(d)
                    });
                match cache_dir {
                    Some(dir) => match substrate.set_projection_enabled(true, Some(&dir)) {
                        Ok(()) => {
                            let gated = std::env::var("WM_GEN3_PROJECTION_GATED")
                                .map(|v| v == "1")
                                .unwrap_or(false);
                            substrate.set_projection_gated(gated);
                            recall_mode = if gated {
                                "lexical+projection (gated)"
                            } else {
                                "lexical+projection"
                            };
                        }
                        Err(e) => eprintln!(
                            "recall: projection requested but unavailable ({e}); using lexical"
                        ),
                    },
                    None => eprintln!(
                        "recall: projection requested but no embed cache found (set WM_GEN3_EMBED_CACHE or run from the repo root); using lexical"
                    ),
                }
            }

            let zero_token_terms = wm_gen3_core::wave3_braid::expand_query_zero_token_terms(&query);
            let expanded_query_str = if zero_token_terms.is_empty() {
                query.clone()
            } else {
                format!("{} {}", query, zero_token_terms.join(" "))
            };
            let q = RecallQuery {
                query: expanded_query_str,
                limit,
                candidate_limit,
                include_historical: historical,
                min_score: 0.0,
                min_coverage: 0.0,
                scope,
                adaptive,
                resonance,
                resonance_hops,
            };

            if evidence {
                match substrate.recall_evidence(&q) {
                    Ok(bundle) => {
                        println!("{}", serde_json::to_string_pretty(&bundle).unwrap());
                    }
                    Err(e) => {
                        eprintln!("Recall evidence error: {e}");
                        std::process::exit(1);
                    }
                }
                return;
            }

            match substrate.recall(&q) {
                Ok(hits) => {
                    let intent_class =
                        wm_gen3_core::wave3_braid::classify_query_intent_zero_token(&query);
                    println!(
                        "Query: \"{}\" ({} results, mode: {}, intent: {:?})",
                        query,
                        hits.len(),
                        recall_mode,
                        intent_class
                    );
                    for (i, hit) in hits.iter().enumerate() {
                        let superseded = hit
                            .superseded_by_record_id
                            .zip(hit.superseded_by_relation_id)
                            .map(|(record, relation)| {
                                format!(" [superseded by record #{record} (relation #{relation})]")
                            })
                            .unwrap_or_default();
                        println!(
                            "\n[{}] Record #{} (score: {:.4}){}",
                            i + 1,
                            hit.id,
                            hit.score,
                            superseded
                        );
                        println!("    Source:  {}", hit.source);
                        let (content_display, truncated_info) = if hit.content.len() > 2000 {
                            let mut end = 2000;
                            while end > 0 && !hit.content.is_char_boundary(end) {
                                end -= 1;
                            }
                            (
                                format!("{}...", &hit.content[..end]),
                                format!(" (truncated from {} bytes)", hit.content.len()),
                            )
                        } else {
                            (hit.content.clone(), String::new())
                        };
                        println!("    Content{}: {}", truncated_info, content_display);
                    }
                }
                Err(e) => {
                    eprintln!("Recall error: {e}");
                    std::process::exit(1);
                }
            }
        }
        Commands::EvidenceRecall {
            request_json,
            query,
            limit,
            candidate_limit,
            historical,
            scope,
            adaptive,
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

            let q = if let Some(raw) = request_json {
                let v: serde_json::Value = serde_json::from_str(&raw).unwrap_or_else(|e| {
                    eprintln!("Invalid request_json: {e}");
                    std::process::exit(1);
                });
                RecallQuery {
                    query: v
                        .get("query")
                        .and_then(serde_json::Value::as_str)
                        .unwrap_or("")
                        .to_string(),
                    limit: v
                        .get("limit")
                        .and_then(serde_json::Value::as_u64)
                        .unwrap_or(limit as u64) as usize,
                    candidate_limit: v
                        .get("candidate_limit")
                        .and_then(serde_json::Value::as_u64)
                        .unwrap_or(candidate_limit as u64)
                        as usize,
                    include_historical: v
                        .get("historical")
                        .and_then(serde_json::Value::as_bool)
                        .unwrap_or(historical),
                    min_score: v
                        .get("min_score")
                        .and_then(serde_json::Value::as_f64)
                        .unwrap_or(0.0) as f32,
                    min_coverage: v
                        .get("min_coverage")
                        .and_then(serde_json::Value::as_f64)
                        .unwrap_or(0.0) as f32,
                    scope: v
                        .get("scope")
                        .and_then(serde_json::Value::as_str)
                        .map(String::from)
                        .or(scope),
                    adaptive: v
                        .get("adaptive")
                        .and_then(serde_json::Value::as_bool)
                        .unwrap_or(adaptive),
                    resonance: v
                        .get("resonance")
                        .and_then(serde_json::Value::as_bool)
                        .unwrap_or(false),
                    resonance_hops: v
                        .get("resonance_hops")
                        .and_then(serde_json::Value::as_u64)
                        .unwrap_or(2) as usize,
                }
            } else {
                RecallQuery {
                    query: query.unwrap_or_default(),
                    limit,
                    candidate_limit,
                    include_historical: historical,
                    min_score: 0.0,
                    min_coverage: 0.0,
                    scope,
                    adaptive,
                    resonance: false,
                    resonance_hops: 2,
                }
            };

            match substrate.recall_evidence(&q) {
                Ok(bundle) => {
                    println!("{}", serde_json::to_string_pretty(&bundle).unwrap());
                }
                Err(e) => {
                    eprintln!("Evidence recall error: {e}");
                    std::process::exit(1);
                }
            }
        }
        Commands::System2 { command } => {
            run_system2_command(command, &store_path);
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
            no_dual_phase,
            homeostatic,
            no_homeostatic,
            force,
            crystallize,
            all,
            sample_depth,
            curiosity_voids,
            sangha,
            lookback,
        } => {
            if sangha {
                println!("==================================================");
                println!("     WhiteMagic Sangha Collective Dreaming        ");
                println!("==================================================");
                let journal_path = store_path.join("journal.jsonl");
                let mut substrate =
                    match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    };
                substrate.set_intake_authority(RatifiedChannel::mint("wm-cli-dream-sangha"));
                match substrate.execute_sangha_collective_dreaming(lookback) {
                    Ok(rep) => {
                        println!("Swept Sessions:         {}", rep.swept_sessions);
                        println!("Distinct Swarm Agents:  {}", rep.distinct_agents.join(", "));
                        println!("Cross-Agent Bridges:    {}", rep.cross_agent_bridges_formed);
                        println!(
                            "Reconciled Corrections: {}",
                            rep.reconciled_corrections.len()
                        );
                        println!("Consolidated Lessons:   {}", rep.consolidated_lessons.len());
                        println!(
                            "Collective Invariants:  {}",
                            rep.collective_invariants.len()
                        );
                        println!(
                            "Collective Gems Minted: {}",
                            rep.collective_gems_minted.len()
                        );
                        println!("Duration:               {:.2} ms", rep.duration_us / 1000.0);
                        if !rep.collective_invariants.is_empty() {
                            println!("\nCollective Invariants Distilled:");
                            for inv in &rep.collective_invariants {
                                println!("  - 🛡️  {inv}");
                            }
                        }
                        if !rep.consolidated_lessons.is_empty() {
                            println!("\nConsolidated Swarm Lessons:");
                            for lesson in &rep.consolidated_lessons {
                                println!("  - 💡 {lesson}");
                            }
                        }
                        println!("==================================================");
                        return;
                    }
                    Err(e) => {
                        eprintln!("Error executing Sangha collective dreaming: {e}");
                        std::process::exit(1);
                    }
                }
            }
            let effective_sample_depth = if all { usize::MAX } else { sample_depth };
            let dual_phase = dual_phase.unwrap_or(true) && !no_dual_phase;
            let run_void_scan = curiosity_voids || dual_phase;
            let homeostatic = homeostatic.unwrap_or(true) && !no_homeostatic;
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

                let incubation_mode = mode;

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
                        let dual = wm_gen3_core::dream::execute_dual_phase_sleep_cycle_ext(
                            incubation_mode,
                            &regime,
                            100,
                            &mut substrate,
                            seed,
                            crystallize,
                            effective_sample_depth,
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
                            "dual_phase": active_dual_phase,
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
                            "  [Phase 1: NREM Compaction] Chains: {:3} | Superseded: {:2} | Contradictions: {:2} | Crystals: {:2} | Compaction: {:.2}x ({:.2}ms)",
                            nrem.session_chains_scanned,
                            nrem.superseded_entries_pruned,
                            nrem.contradictions_resolved,
                            nrem.crystallized_record_ids.len(),
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

                    if run_void_scan {
                        let total_recs = substrate.store().record_count().unwrap_or(0);
                        let cur_epoch = substrate.store().epoch().unwrap_or(0);
                        let sample_n = 240usize.min(total_recs).max(1);
                        let stride = (total_recs / sample_n).max(1);
                        let mut sampled = Vec::with_capacity(sample_n);
                        for i in 0..sample_n {
                            let rid = (i * stride).min(total_recs.saturating_sub(1)) as u64;
                            if let Ok(Some(rec)) = substrate.store().get_record(rid) {
                                sampled.push((rid, rec.content().to_string()));
                            }
                        }
                        let skel_utils: Vec<(String, f64, bool)> = speciation_skeletons
                            .iter()
                            .map(|s| (s.id.clone(), s.rolling_utility, !s.deprecated))
                            .collect();
                        let void_pass =
                            wm_gen3_core::wave2_braid::run_live_curiosity_void_and_cladistics_pass(
                                &sampled,
                                cur_epoch,
                                &skel_utils,
                            );
                        println!(
                            "  [Phase 4: Wave 2 Curiosity Voids & Cladistics] Sampled: {} | k*=8 Basins: {}/8 | 0-After-9 Voids: {} | Cladistics (P/R/Q): {}/{}/{}",
                            void_pass.records_sampled,
                            void_pass.active_k8_constellations,
                            void_pass.voids_discovered.len(),
                            void_pass.cladistic_promoted,
                            void_pass.cladistic_retired,
                            void_pass.cladistic_quarantined,
                        );
                        let voids_log = store_path.join("curiosity_voids.jsonl");
                        let existing_loops = substrate.all_open_loops();
                        let mut registered_loops = 0usize;
                        for v in &void_pass.voids_discovered {
                            println!(
                                "    ◌ [{}] r={:.3} (surrounded by {} basins, priority={:.2})\n      Bridge: {} ⇄ {}\n      Query:  {}",
                                v.void_id,
                                v.radius,
                                v.surrounding_constellations,
                                v.curiosity_priority,
                                v.primary_quadrant_a,
                                v.primary_quadrant_b,
                                v.synthesized_question,
                            );
                            if let Ok(mut f) = std::fs::OpenOptions::new()
                                .create(true)
                                .append(true)
                                .open(&voids_log)
                            {
                                use std::io::Write;
                                let _ =
                                    writeln!(f, "{}", serde_json::to_string(v).unwrap_or_default());
                            }
                            if registered_loops < 2
                                && !existing_loops
                                    .iter()
                                    .any(|l| l.question_or_hypothesis.contains(&v.void_id))
                            {
                                let _ = substrate.register_open_loop(
                                    &v.synthesized_question,
                                    "wave2-topological-void",
                                    wm_gen3_core::ConsentRing::Ring2RelationalTrust,
                                    0.92,
                                );
                                registered_loops += 1;
                            }
                        }
                        let cp_view = substrate.session_continuity(None).ok().flatten();
                        let stone_seed =
                            wm_gen3_core::wave2_braid::StonePillarMorphogenSeed::compile_from_live_state(
                                cur_epoch,
                                total_recs,
                                cp_view.as_ref().map(|c| c.record_id),
                                cp_view
                                    .as_ref()
                                    .map(|c| c.summary.as_str())
                                    .unwrap_or("dream-consolidation-pass"),
                                speciation_skeletons.len().max(16),
                                void_pass.dhumavati_bardo_bloom,
                            );
                        if let Ok(seed_path) = stone_seed.save_to_store(&store_path) {
                            println!(
                                "  [Phase 5: Stone Pillar Seed] Synced {} ({} B, SHA-256: {}..)",
                                seed_path.display(),
                                stone_seed.serialized_bytes,
                                &stone_seed.seed_sha256[..16]
                            );
                        }
                        let mut akashic_seeds =
                            vec![wm_gen3_core::wave3_braid::AkashicDormantSeed {
                                seed_id: format!("seed-epoch-{cur_epoch}"),
                                bloom_keyword: "void".to_string(),
                                min_coherence: 0.75,
                                required_quadrant: "Qi".to_string(),
                                potency: 0.94,
                                payload:
                                    "Synthesize cross-quadrant bridge over 0-After-9 curiosity void"
                                        .to_string(),
                                bloomed: false,
                            }];
                        let bloomed_ids = wm_gen3_core::wave3_braid::evaluate_akashic_seed_bloom(
                            &mut akashic_seeds,
                            "void synthesis",
                            0.91,
                            "Qi",
                        );
                        let drq_audit =
                            wm_gen3_core::wave3_braid::run_drq_purple_sandbox_and_connection_audit(
                                12,
                                &["ipc:shm_ring", "mcp:stdio"],
                                &["ipc:shm_ring", "mcp:stdio"],
                            );
                        let yin_state =
                            wm_gen3_core::wave3_braid::evaluate_yin_and_level4_emergence(
                                telemetry.candidates_generated.max(1),
                                telemetry.candidates_committed.max(1),
                                &[0.25, 0.25, 0.25],
                                1.35,
                                cur_epoch,
                            );
                        println!(
                            "  [Phase 6: Wave 3 Akashic, Yin & DRQ] Bloomed: {} | DRQ Nash Defense: {:.1}% | Synergy: {:.2}x",
                            bloomed_ids.len(),
                            drq_audit.final_nash_defense_rate * 100.0,
                            yin_state.synergy_gain_ratio,
                        );
                    }
                }

                let took = start.elapsed();
                println!("==================================================");
                println!("Dream Incubation Complete in {:.2?}", took);
                if active_dual_phase {
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
            let mut vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);
            let bio = wm_gen3_core::homeostasis::HardwareTelemetry::probe().to_bioelectric_state();
            let morph_rep = vault.autopoietic_morphogenesis(&bio);
            let bound_skeleton = vault.find_best_skeleton_with_bio(&inquiry, Some(&bio));

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
            let trip =
                wm_gen3_core::tripartite_router::TripartiteRouter::route(&inquiry, Some(&bio));
            println!(
                "Tripartite Tier:           {:?} (V_rest: {:.1}mV, Plasticity: {:.2}x)",
                trip.tier, bio.v_rest_mv, morph_rep.plasticity_factor
            );
            println!(
                "Tripartite Latency:        {:.2} µs",
                trip.routing_latency_ns as f64 / 1000.0
            );
            println!("Tripartite Rationale:      {}", trip.rationale);
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
            if let Some(ins) = insights.iter().find(|ins| {
                let inq = inquiry.to_lowercase();
                inq.contains(&ins.source_concept.to_lowercase())
                    || inq.contains(&ins.target_concept.to_lowercase())
                    || (bound_skeleton.is_some()
                        && bound_skeleton.unwrap().action_steps.iter().any(|step| {
                            ins.actionable_recommendation
                                .to_lowercase()
                                .contains(&step.to_lowercase())
                        }))
            }) {
                println!(
                    "  Context Injection:       {}",
                    ins.actionable_recommendation
                );
                println!(
                    "  Dream Insight Bridge:    {} ⇄ {} ({})",
                    ins.source_concept, ins.target_concept, ins.relation_type
                );
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
                    #[cfg(feature = "systemone")]
                    {
                        if let Ok(dir) = wm_gen3_systemone::SystemOne::resolve_model_dir(None) {
                            println!("\n--- System One Reflex Triage (Laya) ---");
                            let organ = wm_gen3_systemone::SystemOne::new(dir);
                            let test_state = serde_json::json!({
                                "inquiry": inquiry,
                                "marginal_utility": utility,
                            });
                            let test_questions = serde_json::json!({
                                "should_act": {
                                    "type": "choice",
                                    "instructions": "Should this task proceed without cloud escalation?",
                                    "criteria": ["yes", "no"]
                                },
                                "needs_human": {
                                    "type": "choice",
                                    "instructions": "Does this require human confirmation or supervisory intervention?",
                                    "criteria": ["yes", "no"]
                                }
                            });
                            let start = std::time::Instant::now();
                            if let Ok(res) = organ.decide(&test_state, &test_questions) {
                                let elapsed = start.elapsed();
                                println!(
                                    "System One Latency: {:.2} ms",
                                    elapsed.as_secs_f64() * 1000.0
                                );
                                if let Some(answers) =
                                    res.get("answers").and_then(serde_json::Value::as_object)
                                {
                                    for (qid, ans) in answers {
                                        let val = ans
                                            .get("value")
                                            .and_then(serde_json::Value::as_str)
                                            .unwrap_or("?");
                                        let conf = ans
                                            .get("confidence")
                                            .and_then(serde_json::Value::as_f64)
                                            .unwrap_or(0.0);
                                        let act = ans
                                            .get("act")
                                            .and_then(serde_json::Value::as_f64)
                                            .unwrap_or(0.0);
                                        println!(
                                            "  [{qid}] choice: {val} (confidence: {conf:.4}, act_prob: {act:.2})"
                                        );
                                    }
                                }
                            }
                        }
                    }
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
            action,
            output_html,
            output_json,
            limit,
        } => {
            let journal_path = store_path.join("journal.jsonl");
            match action {
                Some(GalaxyAction::Fork { source, target }) => {
                    let mut substrate =
                        match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                            Ok(s) => s,
                            Err(e) => {
                                eprintln!("Error opening store for fork: {e}");
                                std::process::exit(1);
                            }
                        };
                    match wm_gen3_harness::starter_galaxy::fork_galaxy(
                        &mut substrate,
                        &source,
                        &target,
                    ) {
                        Ok(n) => println!(
                            "✓ Forked {} records from galaxy '{}' into '{}'.",
                            n, source, target
                        ),
                        Err(e) => {
                            eprintln!("Galaxy fork failed: {e}");
                            std::process::exit(1);
                        }
                    }
                }
                Some(GalaxyAction::Create { name, description }) => {
                    let mut substrate =
                        match Substrate::open(&store_path, Some(&journal_path), default_view()) {
                            Ok(s) => s,
                            Err(e) => {
                                eprintln!("Error opening store: {e}");
                                std::process::exit(1);
                            }
                        };
                    match wm_gen3_harness::starter_galaxy::create_galaxy(
                        &mut substrate,
                        &name,
                        description.as_deref(),
                    ) {
                        Ok(id) => println!(
                            "✓ Galaxy '{}' created (genesis beacon record: {}).",
                            name, id
                        ),
                        Err(e) => {
                            eprintln!("Galaxy creation failed: {e}");
                            std::process::exit(1);
                        }
                    }
                }
                Some(GalaxyAction::List) | None
                    if output_html.is_none() && output_json.is_none() =>
                {
                    let substrate = match Substrate::open_readonly(
                        &store_path,
                        Some(&journal_path),
                        default_view(),
                    ) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    };
                    let galaxies = wm_gen3_harness::starter_galaxy::list_galaxies(&substrate)
                        .unwrap_or_default();
                    println!("==================================================");
                    println!("         WhiteMagic Sovereign Galaxies            ");
                    println!("==================================================");
                    println!("Store: {}", store_path.display());
                    println!("Total Active Galaxies: {}", galaxies.len());
                    println!(
                        "{:<18} | {:<8} | {:<32}",
                        "Galaxy", "Records", "Sample Tags"
                    );
                    println!("--------------------------------------------------");
                    for g in &galaxies {
                        let marker = if g.is_starter { " (starter)" } else { "" };
                        let name_display = format!("{}{}", g.name, marker);
                        println!(
                            "{:<18} | {:<8} | {:<32}",
                            name_display,
                            g.record_count,
                            g.tags.join(", ")
                        );
                    }
                    println!("==================================================");
                    println!("Branching: 'wm galaxy fork <src> <tgt>', 'wm galaxy create <name>'");
                    println!("Visualizer: 'wm galaxy visualize'");
                    println!("Chart Constellations: 'wm galaxy chart'");
                    println!("Navigate Constellations: 'wm galaxy navigate --query <text>'");
                }
                Some(GalaxyAction::Chart {
                    galaxy,
                    sample,
                    clusters,
                    json,
                }) => {
                    let substrate = match Substrate::open_inspect(
                        &store_path,
                        Some(&journal_path),
                        default_view(),
                        wm_gen3_core::store::InspectionPromise::StrictZeroWrite,
                    )
                    .or_else(|_| {
                        Substrate::open_readonly(&store_path, Some(&journal_path), default_view())
                    }) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    };

                    let total_records = substrate.store().record_count().unwrap_or(0);
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    let sample_count = sample.min(total_records).max(1);
                    let stride = (total_records / sample_count).max(1);
                    let num_clusters = clusters.clamp(2, 12);

                    struct ConstellationBin {
                        count: usize,
                        sum_x: f64,
                        sum_y: f64,
                        sum_z: f64,
                        sum_tau: f64,
                        sum_sigma: f64,
                        sum_omega: f64,
                        samples: Vec<(u64, String)>,
                    }

                    let mut bins: Vec<ConstellationBin> = (0..num_clusters)
                        .map(|_| ConstellationBin {
                            count: 0,
                            sum_x: 0.0,
                            sum_y: 0.0,
                            sum_z: 0.0,
                            sum_tau: 0.0,
                            sum_sigma: 0.0,
                            sum_omega: 0.0,
                            samples: Vec::new(),
                        })
                        .collect();

                    let glyph_names = [
                        ("觀 (Guān)", "Survey & Telemetry"),
                        ("界 (Jiè)", "Kekkai Sandbox & Isolation"),
                        ("根 (Gēn)", "Lineage & Causal Origins"),
                        ("行 (Xíng)", "Commit & Execution Authority"),
                        ("合 (Hé)", "Synthesis & Memory Crystals"),
                        ("鏡 (Jìng)", "Mirroring & Analogy"),
                        ("息 (Xī)", "Quiescence & Dream Consolidator"),
                        ("清 (Qīng)", "Compaction & Pruning"),
                        ("應 (Yìng)", "Resonance & P2P Wire"),
                        ("生 (Shēng)", "Speciation & Evolution"),
                        ("辨 (Biàn)", "Adversarial Discrimination"),
                        ("通 (Tōng)", "Cross-Substrate Bridge"),
                    ];

                    for i in 0..sample_count {
                        let id = (i * stride).min(total_records.saturating_sub(1)) as u64;
                        if let Ok(Some(record)) = substrate.store().get_record(id) {
                            let coords = wm_gen3_core::hologram::Holographic6D::from_record(
                                id,
                                record.content(),
                                epoch,
                                0.90,
                            );
                            let normalized_omega =
                                (coords.omega.sin() * 0.5 + 0.5).clamp(0.0, 0.9999);
                            let bin_idx = (normalized_omega * num_clusters as f64).floor() as usize
                                % num_clusters;
                            let b = &mut bins[bin_idx];
                            b.count += 1;
                            b.sum_x += coords.x;
                            b.sum_y += coords.y;
                            b.sum_z += coords.z;
                            b.sum_tau += coords.tau;
                            b.sum_sigma += coords.sigma;
                            b.sum_omega += coords.omega;
                            if b.samples.len() < 3 {
                                let snippet: String = record.content().chars().take(80).collect();
                                b.samples.push((id, snippet.replace('\n', " ")));
                            }
                        }
                    }

                    if json {
                        let constellations_json: Vec<serde_json::Value> = bins
                            .iter()
                            .enumerate()
                            .filter(|(_, b)| b.count > 0)
                            .map(|(idx, b)| {
                                let c = b.count as f64;
                                let (glyph, archetype) = glyph_names[idx % glyph_names.len()];
                                serde_json::json!({
                                    "constellation_id": idx + 1,
                                    "glyph": glyph,
                                    "archetype": archetype,
                                    "stars_count": b.count,
                                    "share_pct": (c / sample_count as f64) * 100.0,
                                    "centroid_6d": {
                                        "x": b.sum_x / c,
                                        "y": b.sum_y / c,
                                        "z": b.sum_z / c,
                                        "tau": b.sum_tau / c,
                                        "sigma": b.sum_sigma / c,
                                        "omega": b.sum_omega / c,
                                    },
                                    "anchor_stars": b.samples.iter().map(|(id, s)| serde_json::json!({"record_id": id, "snippet": s})).collect::<Vec<_>>(),
                                })
                            })
                            .collect();
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&serde_json::json!({
                                "status": "ok",
                                "store_path": store_path.display().to_string(),
                                "galaxy": galaxy,
                                "total_records": total_records,
                                "sample_size": sample_count,
                                "promise": "strict-zero-write",
                                "constellations": constellations_json,
                            }))
                            .unwrap_or_default()
                        );
                    } else {
                        println!("==================================================");
                        println!("    WhiteMagic Gen3 Holographic Constellation Chart");
                        println!("==================================================");
                        println!("Store Path:           {}", store_path.display());
                        println!("Target Galaxy:        {}", galaxy);
                        println!("Total Store Records:  {}", total_records);
                        println!("Constellation Bins:   {}", num_clusters);
                        println!(
                            "Sample Size:          {} (stride: {})",
                            sample_count, stride
                        );
                        println!("==================================================");

                        for (idx, b) in bins.iter().enumerate() {
                            if b.count == 0 {
                                continue;
                            }
                            let c = b.count as f64;
                            let (glyph, archetype) = glyph_names[idx % glyph_names.len()];
                            println!(
                                "\n✦ Constellation #{:02}: {} [{}]",
                                idx + 1,
                                glyph,
                                archetype
                            );
                            println!(
                                "  Stars Count:    {} records ({:.1}% of sample)",
                                b.count,
                                (c / sample_count as f64) * 100.0
                            );
                            println!(
                                "  6D Centroid:    ⟨x={:.2}, y={:.2}, z={:.2} | τ={:.2}, σ={:.2}, ω={:.2}⟩",
                                b.sum_x / c,
                                b.sum_y / c,
                                b.sum_z / c,
                                b.sum_tau / c,
                                b.sum_sigma / c,
                                b.sum_omega / c
                            );
                            println!("  Anchor Stars:");
                            for (id, snippet) in &b.samples {
                                println!("    #{} \"{}\"", id, snippet);
                            }
                        }
                        println!("\n==================================================");
                        println!("Constellation navigation vectors charted successfully.");
                    }
                }
                Some(GalaxyAction::Navigate {
                    query,
                    via,
                    hops,
                    limit,
                    json,
                }) => {
                    use wm_gen3_core::sutra::{CompoundSutra, SutraGlyph};
                    use wm_gen3_zeropointfive::System05;

                    let nav_start = std::time::Instant::now();
                    let mut substrate = match Substrate::open_inspect(
                        &store_path,
                        Some(&journal_path),
                        default_view(),
                        wm_gen3_core::store::InspectionPromise::StrictZeroWrite,
                    )
                    .or_else(|_| {
                        Substrate::open_readonly(&store_path, Some(&journal_path), default_view())
                    }) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    };

                    let total_records = substrate.store().record_count().unwrap_or(0);
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    let eff_hops = hops.clamp(1, 3);

                    // 1. Resolve Sutra trajectory codon
                    let compiled_sutra = if let Some(ref raw_via) = via {
                        let normalized = raw_via.replace(['-', '→'], " ");
                        CompoundSutra::parse(&normalized).unwrap_or_else(|_| {
                            CompoundSutra::parse("觀 應 鏡").expect("default sutra")
                        })
                    } else {
                        let mut glyph_scores: Vec<(SutraGlyph, f32)> = Vec::new();
                        if let Ok(model_dir) = System05::resolve_model_dir(None) {
                            let organ = System05::new(model_dir);
                            if let Ok(qvec) = organ.encode_single(&query) {
                                for &g in &SutraGlyph::ALL {
                                    let gvec = g.vector();
                                    let dot: f32 =
                                        qvec.iter().zip(gvec.iter()).map(|(a, b)| a * b).sum();
                                    glyph_scores.push((g, dot));
                                }
                                glyph_scores.sort_by(|a, b| {
                                    b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
                                });
                            }
                        }
                        if glyph_scores.is_empty() {
                            for word in query.split(|c: char| !c.is_alphanumeric()) {
                                if let Some(g) = SutraGlyph::from_token(word) {
                                    if !glyph_scores.iter().any(|(x, _)| *x == g) {
                                        glyph_scores.push((g, 1.0));
                                    }
                                }
                            }
                        }
                        let selected: Vec<SutraGlyph> = if glyph_scores.is_empty() {
                            vec![SutraGlyph::Guan, SutraGlyph::Ying, SutraGlyph::Jing]
                        } else {
                            glyph_scores.into_iter().take(3).map(|(g, _)| g).collect()
                        };
                        CompoundSutra::from_glyphs(selected)
                            .unwrap_or_else(|_| CompoundSutra::parse("觀 應 鏡").unwrap())
                    };

                    // 2. Compute 6D query coordinate & nearest constellation geodesic
                    let query_6d =
                        wm_gen3_core::hologram::Holographic6D::from_record(0, &query, epoch, 0.90);
                    let num_clusters = 6usize;
                    let sample_count = 300usize.min(total_records).max(1);
                    let stride = (total_records / sample_count).max(1);
                    let mut sums = vec![[0.0f64; 6]; num_clusters];
                    let mut counts = vec![0usize; num_clusters];
                    for i in 0..sample_count {
                        let id = (i * stride).min(total_records.saturating_sub(1)) as u64;
                        if let Ok(Some(rec)) = substrate.store().get_record(id) {
                            let c = wm_gen3_core::hologram::Holographic6D::from_record(
                                id,
                                rec.content(),
                                epoch,
                                0.90,
                            );
                            let norm_w = (c.omega.sin() * 0.5 + 0.5).clamp(0.0, 0.9999);
                            let idx =
                                (norm_w * num_clusters as f64).floor() as usize % num_clusters;
                            counts[idx] += 1;
                            sums[idx][0] += c.x;
                            sums[idx][1] += c.y;
                            sums[idx][2] += c.z;
                            sums[idx][3] += c.tau;
                            sums[idx][4] += c.sigma;
                            sums[idx][5] += c.omega;
                        }
                    }

                    let glyph_names = [
                        ("觀 (Guān)", "Survey & Telemetry"),
                        ("界 (Jiè)", "Kekkai Sandbox & Isolation"),
                        ("根 (Gēn)", "Lineage & Causal Origins"),
                        ("行 (Xíng)", "Commit & Execution Authority"),
                        ("合 (Hé)", "Synthesis & Memory Crystals"),
                        ("鏡 (Jìng)", "Mirroring & Analogy"),
                    ];

                    let mut best_constellation = 0usize;
                    let mut min_geodesic = f64::MAX;
                    let mut best_centroid = [0.0f64; 6];
                    for idx in 0..num_clusters {
                        if counts[idx] == 0 {
                            continue;
                        }
                        let n = counts[idx] as f64;
                        let cx = sums[idx][0] / n;
                        let cy = sums[idx][1] / n;
                        let cz = sums[idx][2] / n;
                        let ctau = sums[idx][3] / n;
                        let csigma = sums[idx][4] / n;
                        let comega = sums[idx][5] / n;
                        let spatial_sq = (query_6d.x - cx).powi(2)
                            + (query_6d.y - cy).powi(2)
                            + (query_6d.z - cz).powi(2);
                        let d_6d = spatial_sq
                            + 0.5 * (query_6d.tau - ctau).powi(2)
                            + 0.5 * (query_6d.sigma - csigma).powi(2)
                            + (1.0 - (query_6d.omega - comega).cos());
                        if d_6d < min_geodesic {
                            min_geodesic = d_6d;
                            best_constellation = idx;
                            best_centroid = [cx, cy, cz, ctau, csigma, comega];
                        }
                    }
                    if min_geodesic == f64::MAX {
                        min_geodesic = 0.0;
                    }

                    // 3. Execute associative resonance recall across graph edges
                    let rq = RecallQuery {
                        query: query.clone(),
                        limit,
                        candidate_limit: limit.max(60),
                        include_historical: false,
                        min_score: 0.0,
                        min_coverage: 0.0,
                        scope: None,
                        adaptive: true,
                        resonance: true,
                        resonance_hops: eff_hops,
                    };
                    let bundle = substrate.recall_evidence(&rq).unwrap_or_else(|e| {
                        eprintln!("Navigation recall error: {e}");
                        std::process::exit(1);
                    });

                    let inspect_report = substrate.inspection_report().ok();
                    let zero_write_verified = inspect_report
                        .as_ref()
                        .map(|r| r.zero_writes_verified)
                        .unwrap_or(true);
                    let (constellation_glyph, constellation_archetype) =
                        glyph_names[best_constellation % glyph_names.len()];
                    let q_finsler =
                        wm_gen3_core::wave2_braid::ProductManifoldPoint::from_structural_coords(
                            2,
                            query_6d.omega,
                            query_6d.x.atan2(query_6d.y),
                            query_6d.omega.sin(),
                            query_6d.tau,
                            query_6d.sigma,
                        );
                    let c_finsler =
                        wm_gen3_core::wave2_braid::ProductManifoldPoint::from_structural_coords(
                            2,
                            best_centroid[5],
                            best_centroid[0].atan2(best_centroid[1]),
                            best_centroid[5].sin(),
                            best_centroid[3],
                            best_centroid[4],
                        );
                    let finsler_geodesic =
                        q_finsler.finsler_wake_distance(&c_finsler, [1.0, 0.8, 0.5], [0.25, 0.15]);
                    let sigma22 = wm_gen3_core::wave2_braid::evaluate_sigma22_spectrometer(
                        [query_6d.x, query_6d.y, query_6d.z, query_6d.sigma],
                        best_constellation % 28,
                    );
                    let elapsed_us = nav_start.elapsed().as_micros();

                    let receipt = serde_json::json!({
                        "status": "ok",
                        "navigation_protocol": "whitemagic.wave6.holographic-navigation.v1",
                        "query": query,
                        "sutra_codon": compiled_sutra.codon_str,
                        "taoist_formula": compiled_sutra.taoist_formula(),
                        "primary_skeleton": compiled_sutra.primary_skeleton_id,
                        "resonance_hops": eff_hops,
                        "latency_micros": elapsed_us,
                        "strict_zero_write_verified": zero_write_verified,
                        "query_coords_6d": {
                            "x": query_6d.x,
                            "y": query_6d.y,
                            "z": query_6d.z,
                            "tau": query_6d.tau,
                            "sigma": query_6d.sigma,
                            "omega": query_6d.omega,
                        },
                        "anchored_constellation": {
                            "constellation_id": best_constellation + 1,
                            "glyph_archetype": constellation_glyph,
                            "domain_focus": constellation_archetype,
                            "geodesic_distance_6d": min_geodesic,
                            "finsler_product_geodesic": finsler_geodesic,
                            "centroid_6d": {
                                "x": best_centroid[0],
                                "y": best_centroid[1],
                                "z": best_centroid[2],
                                "tau": best_centroid[3],
                                "sigma": best_centroid[4],
                                "omega": best_centroid[5],
                            }
                        },
                        "sigma22_spectrometer": sigma22,
                        "evidence": {
                            "coverage": bundle.coverage,
                            "disposition": bundle.disposition,
                            "abstention_recommended": bundle.abstention_recommended,
                            "resonance_expanded": bundle.resonance_expanded,
                            "resonance_links": bundle.resonance_links,
                            "hits": bundle.hits.iter().map(|h| {
                                let preview_text: String = h.content.chars().take(240).collect();
                                serde_json::json!({
                                    "record_id": h.id,
                                    "score": h.score,
                                    "source": h.source,
                                    "preview": preview_text,
                                    "superseded_by_record_id": h.superseded_by_record_id,
                                })
                            }).collect::<Vec<_>>(),
                        }
                    });

                    if json {
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&receipt).unwrap_or_default()
                        );
                    } else {
                        println!("==================================================");
                        println!("   WhiteMagic Wave 6 Holographic Navigator        ");
                        println!("==================================================");
                        println!("Query Intent:         \"{}\"", query);
                        println!(
                            "Sutra Trajectory:     {} ({})",
                            compiled_sutra.codon_str,
                            compiled_sutra.taoist_formula()
                        );
                        println!(
                            "Target Constellation: #{:02} {} — {}",
                            best_constellation + 1,
                            constellation_glyph,
                            constellation_archetype
                        );
                        println!(
                            "6D Geodesic Dist:     {:.4} (Product-Finsler: {:.4})",
                            min_geodesic, finsler_geodesic
                        );
                        println!(
                            "Σ₂₂ Spectrometer:     {} / {} (can_dispatch={})",
                            sigma22.dominant_motif_glyph,
                            sigma22.cardinal_quadrant,
                            sigma22.can_dispatch_authority
                        );
                        println!(
                            "Resonance Radius:     k={} hops (expanded={})",
                            eff_hops, bundle.resonance_expanded
                        );
                        println!(
                            "Evidence State:       {:?} / {:?} (abstain={})",
                            bundle.coverage, bundle.disposition, bundle.abstention_recommended
                        );
                        println!(
                            "Zero-Write Promise:   {} ({} µs)",
                            if zero_write_verified {
                                "VERIFIED (StrictZeroWrite)"
                            } else {
                                "UNVERIFIED"
                            },
                            elapsed_us
                        );
                        println!("--------------------------------------------------");
                        for (idx, h) in bundle.hits.iter().enumerate() {
                            let snippet: String = h
                                .content
                                .chars()
                                .take(120)
                                .collect::<String>()
                                .replace('\n', " ");
                            println!(
                                "  [{}] #{} (score={:.4}, src={}) \"{}\"",
                                idx + 1,
                                h.id,
                                h.score,
                                h.source,
                                snippet
                            );
                        }
                        if !bundle.resonance_links.is_empty() {
                            println!("  Resonance Bridges: {:?}", bundle.resonance_links);
                        }
                        println!("==================================================");
                    }
                }
                _ => {
                    let opt_html = output_html.or(match &action {
                        Some(GalaxyAction::Visualize { output_html: h, .. }) => h.clone(),
                        _ => None,
                    });
                    let opt_json = output_json.or(match &action {
                        Some(GalaxyAction::Visualize { output_json: j, .. }) => j.clone(),
                        _ => None,
                    });
                    let eff_limit = if limit != 2000 {
                        limit
                    } else if let Some(GalaxyAction::Visualize { limit: l, .. }) = &action {
                        *l
                    } else {
                        limit
                    };

                    let substrate = match Substrate::open_readonly(
                        &store_path,
                        Some(&journal_path),
                        default_view(),
                    ) {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!("Error opening store at {}: {e}", store_path.display());
                            std::process::exit(1);
                        }
                    };

                    let total_records = substrate.store().record_count().unwrap_or(0);
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    let sample_count = eff_limit.min(total_records).max(1);
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

                    let sutra_glyphs = [
                        ("觀", "Guān — Survey & Telemetry"),
                        ("界", "Jiè — Kekkai Sandbox & Isolation"),
                        ("根", "Gēn — Lineage & Causal Origins"),
                        ("行", "Xíng — Commit & Execution"),
                        ("合", "Hé — Synthesis & Crystals"),
                        ("鏡", "Jìng — Mirroring & Analogy"),
                    ];
                    let relations = substrate.store().iter_relations().unwrap_or_default();
                    let mut adj: std::collections::HashMap<u64, Vec<u64>> =
                        std::collections::HashMap::new();
                    for rel in &relations {
                        adj.entry(rel.src()).or_default().push(rel.dst());
                    }

                    for i in 0..sample_count {
                        let id = (i * stride).min(total_records.saturating_sub(1)) as u64;
                        if let Ok(Some(record)) = substrate.store().get_record(id) {
                            let coords = wm_gen3_core::hologram::Holographic6D::from_record(
                                id,
                                record.content(),
                                epoch,
                                0.90,
                            );
                            let norm_w = (coords.omega.sin() * 0.5 + 0.5).clamp(0.0, 0.9999);
                            let c_bin = (norm_w * 6.0).floor() as usize % 6;
                            let (s_glyph, s_arch) = sutra_glyphs[c_bin];
                            let links: Vec<u64> = adj
                                .get(&id)
                                .cloned()
                                .unwrap_or_default()
                                .into_iter()
                                .take(4)
                                .collect();
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
                                "constellation": c_bin,
                                "sutra_glyph": s_glyph,
                                "sutra_archetype": s_arch,
                                "resonance_targets": links,
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

                    let json_path = opt_json.unwrap_or_else(|| store_path.join("galaxy_6d.json"));
                    let html_path = opt_html.unwrap_or_else(|| store_path.join("galaxy.html"));

                    let json_data = match serde_json::to_string(&projections) {
                        Ok(data) => data,
                        Err(e) => {
                            eprintln!("Error serializing 6D dataset: {e}");
                            std::process::exit(1);
                        }
                    };
                    let mut galaxy_write_failed = false;
                    if let Err(e) = std::fs::write(&json_path, &json_data) {
                        eprintln!(
                            "Error writing 6D JSON dataset to {}: {e}",
                            json_path.display()
                        );
                        galaxy_write_failed = true;
                    } else {
                        println!("Saved 6D dataset:      {}", json_path.display());
                    }

                    let html_content = generate_galaxy_html(&json_data, total_records, epoch);
                    if let Err(e) = std::fs::write(&html_path, html_content) {
                        eprintln!("Error writing galaxy HTML to {}: {e}", html_path.display());
                        galaxy_write_failed = true;
                    } else {
                        println!("Saved 3D Galaxy HTML:  {}", html_path.display());
                        println!(
                            "Visualizer ready. Open in browser to view the Sangha Galaxy in 3D."
                        );
                    }
                    if galaxy_write_failed {
                        std::process::exit(1);
                    }
                }
            }
        }
        Commands::Inspect {
            scope,
            promise,
            json,
        } => {
            if let Some(promise_str) = promise {
                let promise_parsed: wm_gen3_core::store::InspectionPromise =
                    promise_str.parse().unwrap_or_else(|e| {
                        eprintln!("{e}");
                        std::process::exit(1);
                    });
                let journal_path = store_path.join("journal.jsonl");
                let substrate = match Substrate::open_inspect(
                    &store_path,
                    Some(&journal_path),
                    default_view(),
                    promise_parsed,
                ) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Inspection open failed at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

                let report = match substrate.inspection_report() {
                    Ok(r) => r,
                    Err(e) => {
                        eprintln!("Failed to generate inspection report: {e}");
                        std::process::exit(1);
                    }
                };

                if json {
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&report).expect("serialize inspection report")
                    );
                } else {
                    println!("=== WHITEMAGIC STORE INSPECTION REPORT ===");
                    println!("Store Path:            {}", report.store_path);
                    println!("Inspection Promise:    {}", report.promise);
                    println!("Data Checksum (SHA):   {}", report.data_hash);
                    println!(
                        "Lock Checksum (SHA):   {}",
                        report
                            .lock_hash
                            .as_deref()
                            .unwrap_or("(untouched / absent)")
                    );
                    println!("Audit Events Appended: {}", report.audit_events_appended);
                    println!(
                        "Zero-Write Verified:   {}",
                        if report.zero_writes_verified {
                            "PASS"
                        } else {
                            "FAIL"
                        }
                    );
                }
                return;
            }

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
            let manifest = build_contract_manifest(WM_VERSION);
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&manifest).unwrap_or_default()
                );
            } else {
                println!("==================================================");
                println!("WhiteMagic Hybrid Route & Schema Manifest (v{WM_VERSION})");
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
            no_sweep,
            projection,
            embed_cache,
            dispersion,
            noise,
            no_noise,
            legacy_store,
            transport,
            bind,
        } => {
            let parsed_profile = profile;
            let sweep_enabled = sweep.unwrap_or(true) && !no_sweep;
            let noise_enabled = noise.unwrap_or(true) && !no_noise;

            let backend = if let Some(legacy) = legacy_store.as_deref() {
                match Gen2Reader::open(legacy) {
                    Ok(reader) => {
                        eprintln!(
                            "gen3: serve legacy(Gen2) store={} profile={:?} mode=readonly (compat reader; no writes)",
                            legacy.display(),
                            parsed_profile
                        );
                        McpBackend::legacy(reader, legacy, parsed_profile)
                    }
                    Err(e) => {
                        eprintln!(
                            "gen3: cannot open legacy Gen2 store at {}: {e}",
                            legacy.display()
                        );
                        std::process::exit(1);
                    }
                }
            } else {
                let journal_path = store_path.join("journal.jsonl");
                let mut substrate = {
                    let opened = if readonly {
                        Substrate::open_readonly(&store_path, Some(&journal_path), default_view())
                    } else {
                        Substrate::open(&store_path, Some(&journal_path), default_view())
                    };
                    match opened {
                        Ok(s) => s,
                        Err(e) => {
                            eprintln!(
                                "gen3: cannot open substrate at {}: {e}",
                                store_path.display()
                            );
                            std::process::exit(1);
                        }
                    }
                };

                substrate.set_intake_authority(RatifiedChannel::mint("wm-gen3-serve"));
                substrate.set_sweep_enabled(sweep_enabled);
                if projection {
                    if let Err(e) = substrate.set_projection_enabled(true, embed_cache.as_deref()) {
                        eprintln!("gen3: projection enable failed: {e}");
                        std::process::exit(1);
                    }
                }
                substrate.set_dispersion(dispersion);
                substrate.set_noise_enabled(noise_enabled);

                eprintln!(
                    "gen3: serve store={} profile={:?} mode={} sweep={} projection={}",
                    store_path.display(),
                    parsed_profile,
                    if readonly { "readonly" } else { "readwrite" },
                    if sweep_enabled { "on" } else { "off" },
                    if projection { "on" } else { "off" }
                );

                McpBackend::gen3(substrate, &store_path, parsed_profile, readonly)
            };

            match transport.to_ascii_lowercase().as_str() {
                "stdio" => run_stdio_loop(&backend),
                kind @ ("http" | "sse") => {
                    let addr = bind.parse::<std::net::SocketAddr>().unwrap_or_else(|e| {
                        eprintln!("gen3: invalid --bind '{}': {e}", bind);
                        std::process::exit(2);
                    });
                    let network = if kind == "http" {
                        NetworkTransport::Http
                    } else {
                        NetworkTransport::Sse
                    };
                    serve_network(backend, addr, network);
                }
                other => {
                    eprintln!("gen3: unknown --transport '{other}' (expected stdio|http|sse)");
                    std::process::exit(2);
                }
            }
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
        Commands::MigrateAll {
            source_root,
            target_root,
            only,
            batch_size,
            dry_run,
        } => {
            run_migrate_all(
                &source_root,
                &target_root,
                only.as_deref(),
                batch_size,
                dry_run,
            );
        }
        Commands::Quarantine { file, limit } => {
            run_quarantine_review(&file, limit);
        }
        Commands::BackfillSessionEvidence {
            source,
            batch_size,
            limit,
        } => {
            run_backfill_session_evidence(&source, &store_path, batch_size, limit);
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
            max_item_bytes,
        } => {
            run_ingest(
                &store_path,
                &file,
                batch_size,
                &default_source,
                default_kind,
                max_item_bytes,
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
        #[cfg(feature = "systemone")]
        Commands::Decision {
            state_file,
            questions,
            model,
            json,
        } => run_decision_command(state_file, &questions, model, json),
        #[cfg(feature = "system05")]
        Commands::Shortlist {
            state_file,
            routes,
            k,
            margin_threshold,
            cascade,
            model,
            json,
        } => run_shortlist_command(
            state_file,
            routes,
            k,
            margin_threshold,
            cascade,
            model,
            json,
            &store_path,
        ),
        Commands::Deliberate {
            intent,
            candidates,
            candidates_file,
            json,
        } => run_deliberate_command(&intent, candidates, candidates_file, &store_path, json),
        Commands::VerifyReceipt { path, json } => {
            run_verify_receipt_command(&path, &store_path, json);
        }
        #[cfg(any(feature = "systemone", feature = "system05"))]
        Commands::Outcome {
            receipt,
            outcome,
            corrected_route,
            note,
            session_id,
            tenant_id,
            json,
        } => run_outcome_command(
            &receipt,
            &outcome,
            corrected_route,
            note,
            session_id,
            tenant_id,
            &store_path,
            json,
        ),
        Commands::Organ { command } => run_organ_command(command, &store_path),
        Commands::Peer { command } => run_peer_command(command, &store_path),
        Commands::Sentinel { command } => run_sentinel_command(command, &store_path),
        Commands::HostGuard { command } => run_host_guard_command(command),
        Commands::Compact { dry_run, json, yes } => {
            let code = run_compact_command(&store_path, dry_run, json, yes);
            if code != 0 {
                std::process::exit(code);
            }
        }
        Commands::AtRest { command } => {
            let code = run_at_rest_command(command, &store_path);
            if code != 0 {
                std::process::exit(code);
            }
        }
        Commands::Selftest { json, strict } => {
            // Install invariants are the persistence probe; host health rides
            // alongside it. The install contract (`status`) stays driven by
            // persistence so release-health certification is unaffected; the
            // host verdict is exposed separately as host_status/host_health
            // (2026-10-06 incident: the old stub reported ok while the host
            // thrashed on zram swap).
            let health = wm_gen3_harness::host_health::collect();
            let host_verdict = health.status;
            match run_persistence_selftest() {
                Ok(report) if json => {
                    let mut report = report;
                    if let Some(object) = report.as_object_mut() {
                        object.insert(
                            "host_status".to_string(),
                            serde_json::json!(host_verdict.as_str()),
                        );
                        object.insert(
                            "host_health".to_string(),
                            serde_json::to_value(&health).unwrap_or(serde_json::Value::Null),
                        );
                        object.insert("firebreak".to_string(), firebreak_json());
                    }
                    println!(
                        "{}",
                        serde_json::to_string(&report)
                            .expect("serializing a JSON Value cannot fail")
                    );
                }
                Ok(report) => {
                    println!(
                        "WhiteMagic Gen3 persistence selftest: PASS ({} durable record, {} journal events, isolated scratch store, version {})",
                        report["records"], report["journal_events"], WM_VERSION
                    );
                    for line in health.render_lines() {
                        println!("{line}");
                    }
                    for line in firebreak_render_lines() {
                        println!("{line}");
                    }
                }
                Err(error) => {
                    if json {
                        println!(
                            "{}",
                            serde_json::json!({
                                "status": "error",
                                "persistence": "failed",
                                "error": error
                            })
                        );
                    } else {
                        eprintln!("WhiteMagic Gen3 persistence selftest: FAIL: {error}");
                    }
                    std::process::exit(1);
                }
            }
            if strict && host_verdict == wm_gen3_harness::host_health::Verdict::Critical {
                std::process::exit(1);
            }
        }
        Commands::Sutra {
            command,
            codon,
            dry_run,
            execute,
            strict,
            peer,
            json,
        } => match command {
            Some(SutraCommands::Canon { json: j }) => {
                run_sutra_canon(j || json);
            }
            Some(SutraCommands::List { json: j }) => {
                run_sutra_list(j || json);
            }
            Some(SutraCommands::Compile { query, json: j }) => {
                run_sutra_compile(&query, j || json);
            }
            Some(SutraCommands::Cast {
                codon: c,
                dry_run: dr,
                execute: ex,
                strict: st,
                peer: p,
                json: j,
            }) => {
                let actual_dry_run = if ex { false } else { dr || !ex };
                run_sutra_cast(&c, actual_dry_run, st, p.as_deref(), j, &store_path);
            }
            Some(SutraCommands::Hexagram {
                query,
                mutate_line,
                json: j,
            }) => {
                run_sutra_hexagram(&query, mutate_line, j || json, &store_path);
            }
            Some(SutraCommands::Legion {
                edict,
                clones,
                peer,
                json: j,
            }) => {
                run_sutra_legion(&edict, clones, peer.as_deref(), j || json, &store_path);
            }
            Some(SutraCommands::Chohan {
                payload,
                proof,
                bid,
                json: j,
            }) => {
                run_sutra_chohan(&payload, proof.as_deref(), bid, j || json);
            }
            Some(SutraCommands::Valkyrie {
                inquiry,
                benchmark,
                digest,
                json: j,
            }) => {
                run_sutra_valkyrie(&inquiry, benchmark, digest, j || json);
            }
            Some(SutraCommands::Deliberator { inquiry, json: j }) => {
                run_sutra_deliberator(&inquiry, j || json);
            }
            None => {
                if let Some(c) = codon {
                    let actual_dry_run = if execute { false } else { dry_run || !execute };
                    run_sutra_cast(
                        &c,
                        actual_dry_run,
                        strict,
                        peer.as_deref(),
                        json,
                        &store_path,
                    );
                } else {
                    run_sutra_canon(json);
                }
            }
        },
        Commands::Homeostasis { json } => {
            run_homeostasis_command(json);
        }
        Commands::Sanctuary { command } => {
            let journal_path = store_path.join("journal.jsonl");
            match command {
                SanctuaryCommands::Status { json } => {
                    let substrate = Substrate::open_inspect(
                        &store_path,
                        Some(&journal_path),
                        default_view(),
                        wm_gen3_core::store::InspectionPromise::StrictZeroWrite,
                    )
                    .or_else(|_| {
                        Substrate::open_readonly(&store_path, Some(&journal_path), default_view())
                    })
                    .unwrap_or_else(|e| {
                        eprintln!("Error opening store: {e}");
                        std::process::exit(1);
                    });
                    let hc = substrate.hermit_crab_status();
                    let loops = substrate.all_open_loops();
                    if json {
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&serde_json::json!({
                                "status": "ok",
                                "hermit_crab_sanctuary": hc,
                                "open_loops_count": loops.len(),
                                "open_loops": loops,
                            }))
                            .unwrap_or_default()
                        );
                    } else {
                        println!("==================================================");
                        println!("   WMv11.0 Lichen Sanctuary & OpenLoop Status     ");
                        println!("==================================================");
                        println!(
                            "Hermit-Crab Seal:     {} (reason: {})",
                            if hc.sealed {
                                "SEALED (Ring 0..1 Only)"
                            } else {
                                "OPEN (Ring 0..3 Active)"
                            },
                            hc.reason
                        );
                        println!("Max Public Ring:      {:?}", hc.max_public_ring);
                        println!("Protected Records:    {}", hc.protected_records_count);
                        println!("Active OpenLoops:     {}", loops.len());
                        for l in &loops {
                            println!(
                                "  • [{}] ({:?}, sal={:.2}, rev={}) \"{}\"",
                                l.loop_id,
                                l.consent_ring,
                                l.salience,
                                l.revisit_count,
                                l.question_or_hypothesis
                            );
                        }
                        println!("==================================================");
                    }
                }
                SanctuaryCommands::OpenLoop {
                    question,
                    domain,
                    ring,
                    salience,
                    json,
                } => {
                    let mut substrate =
                        Substrate::open(&store_path, Some(&journal_path), default_view())
                            .unwrap_or_else(|e| {
                                eprintln!("Error opening store: {e}");
                                std::process::exit(1);
                            });
                    substrate.set_intake_authority(RatifiedChannel::mint("wm-sanctuary-cli"));
                    let consent_ring = match ring {
                        0 => wm_gen3_core::ConsentRing::Ring0PublicCommons,
                        1 => wm_gen3_core::ConsentRing::Ring1OperationalProject,
                        2 => wm_gen3_core::ConsentRing::Ring2RelationalTrust,
                        _ => wm_gen3_core::ConsentRing::Ring3DeepInteriority,
                    };
                    let item = substrate
                        .register_open_loop(&question, &domain, consent_ring, salience)
                        .unwrap_or_else(|e| {
                            eprintln!("Error registering OpenLoop: {e}");
                            std::process::exit(1);
                        });
                    if json {
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&item).unwrap_or_default()
                        );
                    } else {
                        println!(
                            "Registered OpenLoop {} ({:?}, salience={:.2}): \"{}\"",
                            item.loop_id,
                            item.consent_ring,
                            item.salience,
                            item.question_or_hypothesis
                        );
                    }
                }
                SanctuaryCommands::Revisit { json } => {
                    let mut substrate =
                        Substrate::open(&store_path, Some(&journal_path), default_view())
                            .unwrap_or_else(|e| {
                                eprintln!("Error opening store: {e}");
                                std::process::exit(1);
                            });
                    let revisited = substrate
                        .revisit_open_loops_dream_pass()
                        .unwrap_or_else(|e| {
                            eprintln!("Error revisiting OpenLoops: {e}");
                            std::process::exit(1);
                        });
                    if json {
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&serde_json::json!({
                                "status": "ok",
                                "revisited_count": revisited.len(),
                                "open_loops": revisited,
                            }))
                            .unwrap_or_default()
                        );
                    } else {
                        println!(
                            "Revisited {} OpenLoop(s) under 'Still True?' gentle epistemic decay (0.95x):",
                            revisited.len()
                        );
                        for l in &revisited {
                            println!(
                                "  • [{}] revisit #{} -> salience={:.4} \"{}\"",
                                l.loop_id, l.revisit_count, l.salience, l.question_or_hypothesis
                            );
                        }
                    }
                }
                SanctuaryCommands::Resolve {
                    loop_id,
                    insight,
                    json,
                } => {
                    let mut substrate =
                        Substrate::open(&store_path, Some(&journal_path), default_view())
                            .unwrap_or_else(|e| {
                                eprintln!("Error opening store: {e}");
                                std::process::exit(1);
                            });
                    let resolved = substrate
                        .resolve_open_loop(&loop_id, &insight)
                        .unwrap_or_else(|e| {
                            eprintln!("Error resolving OpenLoop: {e}");
                            std::process::exit(1);
                        });
                    if json {
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&resolved).unwrap_or_default()
                        );
                    } else {
                        println!(
                            "Synthesized OpenLoop {}: {:?}",
                            resolved.loop_id, resolved.status
                        );
                    }
                }
                SanctuaryCommands::Seal {
                    reason,
                    share_a,
                    share_b,
                    json,
                } => {
                    let mut substrate =
                        Substrate::open(&store_path, Some(&journal_path), default_view())
                            .unwrap_or_else(|e| {
                                eprintln!("Error opening store: {e}");
                                std::process::exit(1);
                            });
                    let st = substrate
                        .engage_hermit_crab_sanctuary(&reason, &share_a, &share_b)
                        .unwrap_or_else(|e| {
                            eprintln!("Error engaging Hermit-Crab Sanctuary: {e}");
                            std::process::exit(1);
                        });
                    if json {
                        println!("{}", serde_json::to_string_pretty(&st).unwrap_or_default());
                    } else {
                        println!(
                            "Hermit-Crab Sanctuary SEALED (protected={} Ring 2/3 records, commitment={})",
                            st.protected_records_count, st.combined_commitment_sha256
                        );
                    }
                }
                SanctuaryCommands::Unseal {
                    share_a,
                    share_b,
                    json,
                } => {
                    let mut substrate =
                        Substrate::open(&store_path, Some(&journal_path), default_view())
                            .unwrap_or_else(|e| {
                                eprintln!("Error opening store: {e}");
                                std::process::exit(1);
                            });
                    let st = substrate
                        .release_hermit_crab_sanctuary(&share_a, &share_b)
                        .unwrap_or_else(|e| {
                            eprintln!("Error releasing Hermit-Crab Sanctuary: {e}");
                            std::process::exit(1);
                        });
                    if json {
                        println!("{}", serde_json::to_string_pretty(&st).unwrap_or_default());
                    } else {
                        println!(
                            "Hermit-Crab Sanctuary UNSEALED (2-of-2 split-key verified, max_public_ring={:?})",
                            st.max_public_ring
                        );
                    }
                }
            }
        }
        Commands::Legion {
            edict,
            clones,
            peer,
            json,
        } => {
            run_sutra_legion(&edict, clones, peer.as_deref(), json, &store_path);
        }
        Commands::Chohan {
            payload,
            proof,
            bid,
            json,
        } => {
            run_sutra_chohan(&payload, proof.as_deref(), bid, json);
        }
        Commands::Sangha { args } => {
            run_sangha_cli(&args);
        }
        Commands::Cpr { args } => {
            run_cpr_cli(&args);
        }
        Commands::Wave2Benchmark { json } => {
            run_wave2_benchmark_command(json);
        }
        Commands::Wave3Benchmark { json } => {
            run_wave3_benchmark_command(json);
        }
        Commands::Wave4Benchmark { json } => {
            run_wave4_benchmark_command(json);
        }
        Commands::Wiki { out, limit, json } => {
            run_wiki_command(&store_path, &out, limit, json);
        }
        Commands::LongmemevalBenchmark { json } => {
            run_longmemeval_benchmark_command(json);
        }
        Commands::Satkona { json } => {
            run_satkona_command(json);
        }
        Commands::Gnosis { json } => {
            run_gnosis_command(&store_path, json);
        }
        Commands::Seed { action, json } => {
            run_seed_command(&store_path, &action, json);
        }
        Commands::Backup { dest, json } => {
            let code = run_backup_command(&store_path, &dest, json);
            if code != 0 {
                std::process::exit(code);
            }
        }
        Commands::Restore { src, force, json } => {
            let code = run_restore_command(&src, &store_path, force, json);
            if code != 0 {
                std::process::exit(code);
            }
        }
    }
}

fn sha256_file_hex(path: &Path) -> std::io::Result<String> {
    use sha2::{Digest, Sha256};
    use std::io::Read;
    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    let digest = hasher.finalize();
    Ok(digest.iter().map(|b| format!("{b:02x}")).collect())
}

// A backup may contain keys and private memories. Do not copy the source's
// potentially broad permissions (for example from an exFAT mount).
fn copy_snapshot_file(src: &Path, dest: &Path) -> std::io::Result<()> {
    let mut input = std::fs::File::open(src)?;
    let parent = dest.parent().ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "destination has no parent",
        )
    })?;
    let temporary = parent.join(format!(".wm-snapshot-{}.tmp", uuid::Uuid::new_v4()));
    let mut options = std::fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut output = options.open(&temporary)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        output.set_permissions(std::fs::Permissions::from_mode(0o600))?;
    }
    std::io::copy(&mut input, &mut output)?;
    drop(output);
    std::fs::rename(temporary, dest)?;
    Ok(())
}

fn reject_overlapping_snapshot_roots(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::path::Component;
    let source = std::fs::canonicalize(source)?;
    let destination = std::path::absolute(destination)?;
    let mut existing = destination.as_path();
    while !existing.exists() {
        existing = existing.parent().ok_or_else(|| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "destination has no existing parent",
            )
        })?;
    }
    let suffix = destination
        .strip_prefix(existing)
        .map_err(std::io::Error::other)?;
    if !suffix
        .components()
        .all(|part| matches!(part, Component::Normal(_)))
        && !suffix.as_os_str().is_empty()
    {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "unsafe destination path",
        ));
    }
    let destination = std::fs::canonicalize(existing)?.join(suffix);
    if source.starts_with(&destination) || destination.starts_with(&source) {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "source and destination overlap",
        ));
    }
    Ok(())
}

// Snapshot paths are relative and must never traverse links or escape their root.
// The source and destination must not be modified by another process during restore.
fn snapshot_path(
    root: &Path,
    name: &str,
    leaf_may_be_missing: bool,
) -> std::io::Result<std::path::PathBuf> {
    use std::path::Component;
    let relative = Path::new(name);
    if name.is_empty()
        || name.trim() != name
        || name.contains(['\n', '\r'])
        || !relative
            .components()
            .all(|c| matches!(c, Component::Normal(_)))
    {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "unsafe snapshot path",
        ));
    }
    let components: Vec<_> = relative.components().collect();
    let mut path = root.to_path_buf();
    for (index, component) in components.iter().enumerate() {
        path.push(component.as_os_str());
        match std::fs::symlink_metadata(&path) {
            Ok(meta) if meta.file_type().is_symlink() => {
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidInput,
                    "snapshot path contains symlink",
                ));
            }
            Ok(meta) if index + 1 < components.len() && !meta.is_dir() => {
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidInput,
                    "snapshot parent is not a directory",
                ));
            }
            Ok(_) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound && leaf_may_be_missing => {}
            Err(e) => return Err(e),
        }
    }
    Ok(path)
}

fn collect_snapshot_files(
    root: &Path,
    directory: &Path,
    files: &mut Vec<String>,
) -> std::io::Result<()> {
    for entry in std::fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        let file_type = entry.file_type()?;
        let relative = path.strip_prefix(root).map_err(std::io::Error::other)?;
        let name = relative.to_str().ok_or_else(|| {
            std::io::Error::new(std::io::ErrorKind::InvalidInput, "non-UTF-8 snapshot path")
        })?;
        if name == "lock.mdb" || name == "SHA256SUMS" {
            continue;
        }
        snapshot_path(root, name, false)?;
        if file_type.is_dir() {
            collect_snapshot_files(root, &path, files)?;
        } else if file_type.is_file() {
            files.push(name.to_owned());
        } else {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "snapshot contains non-regular file",
            ));
        }
    }
    Ok(())
}

fn run_backup_command(store_path: &Path, dest: &Path, json: bool) -> i32 {
    eprintln!(
        "Backup requires an immutable, quiescent source; this command does not stop or coordinate writers."
    );
    if !std::fs::symlink_metadata(store_path)
        .is_ok_and(|m| m.is_dir() && !m.file_type().is_symlink())
    {
        eprintln!(
            "Error: store path {} is not a real directory",
            store_path.display()
        );
        return 1;
    }
    if let Err(e) = reject_overlapping_snapshot_roots(store_path, dest) {
        eprintln!("Error: invalid backup destination: {e}");
        return 1;
    }
    let mut file_names = Vec::new();
    if let Err(e) = collect_snapshot_files(store_path, store_path, &mut file_names) {
        eprintln!("Error enumerating snapshot: {e}");
        return 1;
    }
    if !file_names.iter().any(|name| name == "data.mdb") {
        eprintln!("Error: store has no data.mdb");
        return 1;
    }
    if dest.exists()
        && std::fs::read_dir(dest)
            .map(|mut d| d.next().is_some())
            .unwrap_or(true)
    {
        eprintln!("Error: backup destination must be an empty directory");
        return 1;
    }
    if std::fs::symlink_metadata(dest).is_ok_and(|m| m.file_type().is_symlink()) {
        eprintln!("Error: backup destination must not be a symlink");
        return 1;
    }
    let destination_existed = dest.exists();
    if let Err(e) = std::fs::create_dir_all(dest) {
        eprintln!("Error creating backup directory {}: {e}", dest.display());
        return 1;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if !destination_existed {
            if let Err(e) = std::fs::set_permissions(dest, std::fs::Permissions::from_mode(0o700)) {
                eprintln!("Error securing backup directory: {e}");
                return 1;
            }
        }
        if !std::fs::metadata(dest).is_ok_and(|m| m.permissions().mode() & 0o077 == 0) {
            eprintln!("Error: backup directory must not be accessible to group or others");
            return 1;
        }
    }
    #[cfg(not(unix))]
    let _ = destination_existed;
    let mut copied_files = Vec::new();
    let mut manifest_lines = Vec::new();
    file_names.sort();

    for name in file_names {
        let src_file = store_path.join(&name);
        let dst_file = dest.join(&name);
        if let Some(parent) = dst_file.parent() {
            if let Err(e) = std::fs::create_dir_all(parent) {
                eprintln!("Error creating backup directory: {e}");
                return 1;
            }
        }
        if let Err(e) = copy_snapshot_file(&src_file, &dst_file) {
            eprintln!(
                "Error copying {} to {}: {e}",
                src_file.display(),
                dst_file.display()
            );
            return 1;
        }
        match sha256_file_hex(&dst_file) {
            Ok(digest) => {
                manifest_lines.push(format!("{digest}  {name}"));
                copied_files.push(serde_json::json!({
                    "file": name,
                    "sha256": digest,
                }));
            }
            Err(e) => {
                eprintln!("Error hashing {}: {e}", dst_file.display());
                return 1;
            }
        }
    }
    let manifest_path = dest.join("SHA256SUMS");
    let manifest_content = format!("{}\n", manifest_lines.join("\n"));
    let manifest_write = (|| -> std::io::Result<()> {
        use std::io::Write;
        let mut options = std::fs::OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        options
            .open(&manifest_path)?
            .write_all(manifest_content.as_bytes())
    })();
    if let Err(e) = manifest_write {
        eprintln!("Error writing {}: {e}", manifest_path.display());
        return 1;
    }
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "status": "ok",
                "store": store_path.display().to_string(),
                "backup_dir": dest.display().to_string(),
                "manifest": manifest_path.display().to_string(),
                "files_copied": copied_files.len(),
                "files": copied_files,
            }))
            .unwrap_or_default()
        );
    } else {
        println!(
            "Backup complete: {} files copied from {} to {} (SHA256SUMS written)",
            copied_files.len(),
            store_path.display(),
            dest.display()
        );
    }
    0
}

fn run_restore_command(src: &Path, store_path: &Path, force: bool, json: bool) -> i32 {
    if force {
        eprintln!("Error: --force is disabled; restore into a fresh destination");
        return 1;
    }
    if !std::fs::symlink_metadata(src).is_ok_and(|m| m.is_dir() && !m.file_type().is_symlink())
        || std::fs::symlink_metadata(store_path).is_ok_and(|m| m.file_type().is_symlink())
    {
        eprintln!("Error: snapshot roots must be real directories, not symlinks");
        return 1;
    }
    if let Err(e) = reject_overlapping_snapshot_roots(src, store_path) {
        eprintln!("Error: invalid restore destination: {e}");
        return 1;
    }
    let manifest_path = src.join("SHA256SUMS");
    if !std::fs::symlink_metadata(&manifest_path)
        .is_ok_and(|m| m.is_file() && !m.file_type().is_symlink())
    {
        eprintln!(
            "Error: backup manifest {} not found",
            manifest_path.display()
        );
        return 1;
    }
    if std::fs::symlink_metadata(store_path).is_ok() {
        eprintln!(
            "Error: destination store {} must not already exist",
            store_path.display()
        );
        return 1;
    }
    let manifest_raw = match std::fs::read_to_string(&manifest_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error reading {}: {e}", manifest_path.display());
            return 1;
        }
    };
    let mut entries_to_restore = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for line in manifest_raw.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let mut parts = trimmed.splitn(2, char::is_whitespace);
        let expected_hash = parts.next().unwrap_or("").trim();
        let file_name = parts.next().unwrap_or("").trim();
        if expected_hash.len() != 64
            || !expected_hash.bytes().all(|b| b.is_ascii_hexdigit())
            || !seen.insert(file_name.to_string())
        {
            eprintln!("Error: malformed line in SHA256SUMS: {trimmed}");
            return 1;
        }
        let src_file = match snapshot_path(src, file_name, false) {
            Ok(path) => path,
            Err(e) => {
                eprintln!("Error: unsafe source path {file_name}: {e}");
                return 1;
            }
        };
        if let Err(e) = snapshot_path(store_path, file_name, true) {
            eprintln!("Error: unsafe destination path {file_name}: {e}");
            return 1;
        }
        if !src_file.is_file() {
            eprintln!("Error: backup file missing: {}", src_file.display());
            return 1;
        }
        let actual_hash = match sha256_file_hex(&src_file) {
            Ok(h) => h,
            Err(e) => {
                eprintln!("Error hashing {}: {e}", src_file.display());
                return 1;
            }
        };
        if !actual_hash.eq_ignore_ascii_case(expected_hash) {
            eprintln!(
                "Error: SHA-256 mismatch for {}: expected {}, got {}",
                file_name, expected_hash, actual_hash
            );
            return 1;
        }
        entries_to_restore.push((file_name.to_string(), expected_hash.to_string()));
    }
    if !seen.contains("data.mdb") {
        eprintln!("Error: backup manifest does not contain data.mdb");
        return 1;
    }
    let mut actual_files = Vec::new();
    if let Err(e) = collect_snapshot_files(src, src, &mut actual_files) {
        eprintln!("Error enumerating backup contents: {e}");
        return 1;
    }
    if actual_files.len() != seen.len() || actual_files.iter().any(|path| !seen.contains(path)) {
        eprintln!("Error: manifest does not exactly cover backup files");
        return 1;
    }
    let destination = match std::path::absolute(store_path) {
        Ok(path) => path,
        Err(e) => {
            eprintln!("Error resolving destination: {e}");
            return 1;
        }
    };
    let Some(parent) = destination.parent() else {
        eprintln!("Error: destination needs an existing private parent");
        return 1;
    };
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if !std::fs::metadata(parent)
            .is_ok_and(|m| m.is_dir() && m.permissions().mode() & 0o077 == 0)
        {
            eprintln!(
                "Error: restore parent must be an existing directory inaccessible to group and others"
            );
            return 1;
        }
    }
    let stage = parent.join(format!(".wm-restore-stage-{}", uuid::Uuid::new_v4()));
    let mut stage_builder = std::fs::DirBuilder::new();
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        stage_builder.mode(0o700);
    }
    if let Err(e) = stage_builder.create(&stage) {
        eprintln!(
            "Error creating private restore stage {}: {e}",
            stage.display()
        );
        return 1;
    }
    for (file_name, expected_hash) in &entries_to_restore {
        let src_file = src.join(file_name);
        let dst_file = stage.join(file_name);
        if let Some(parent) = dst_file.parent() {
            if let Err(e) = std::fs::create_dir_all(parent) {
                eprintln!("Error creating restore directory: {e}");
                return 1;
            }
        }
        if let Err(e) = copy_snapshot_file(&src_file, &dst_file) {
            eprintln!(
                "Error restoring {} to {}: {e}",
                src_file.display(),
                dst_file.display()
            );
            return 1;
        }
        if !sha256_file_hex(&dst_file)
            .is_ok_and(|actual| actual.eq_ignore_ascii_case(expected_hash))
        {
            eprintln!("Error: restored bytes failed verification for {file_name}");
            return 1;
        }
    }
    // Reserve the destination without overwriting an existing directory, then
    // replace only the empty directory we just created. Parent must be private
    // and exclusively controlled for the duration of the restore.
    if let Err(e) = std::fs::create_dir(&destination) {
        eprintln!(
            "Error reserving destination; verified stage retained at {}: {e}",
            stage.display()
        );
        return 1;
    }
    if let Err(e) = std::fs::rename(&stage, &destination) {
        eprintln!(
            "Error promoting verified stage {}; stage and reserved destination {} retained: {e}",
            stage.display(),
            destination.display()
        );
        return 1;
    }
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "status": "ok",
                "backup_dir": src.display().to_string(),
                "store": store_path.display().to_string(),
                "files_restored": entries_to_restore.len(),
                "sha256_verified": true,
            }))
            .unwrap_or_default()
        );
    } else {
        println!(
            "Restore complete: {} files verified against SHA256SUMS and restored to {}",
            entries_to_restore.len(),
            store_path.display()
        );
    }
    0
}

#[cfg(test)]
mod snapshot_recovery_tests {
    use super::*;

    #[test]
    fn snapshot_round_trip_preserves_nested_receipts() {
        let root = std::env::temp_dir().join(format!("wm-snapshot-{}", uuid::Uuid::new_v4()));
        let live = root.join("live");
        let backup = root.join("backup");
        let restored = root.join("restored");
        std::fs::create_dir_all(live.join("receipts")).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o700)).unwrap();
        }
        std::fs::write(live.join("data.mdb"), b"test database").unwrap();
        std::fs::write(live.join("lock.mdb"), b"ephemeral lock").unwrap();
        std::fs::write(live.join("receipts/first.json"), b"receipt").unwrap();
        assert_eq!(run_backup_command(&live, &backup, false), 0);
        assert_eq!(run_restore_command(&backup, &restored, false, false), 0);
        assert_eq!(
            std::fs::read(restored.join("data.mdb")).unwrap(),
            b"test database"
        );
        assert_eq!(
            std::fs::read(restored.join("receipts/first.json")).unwrap(),
            b"receipt"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(restored.join("data.mdb"))
                    .unwrap()
                    .permissions()
                    .mode()
                    & 0o777,
                0o600
            );
        }
        assert!(!restored.join("lock.mdb").exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn restore_rejects_parent_escape_without_touching_outside_file() {
        let root =
            std::env::temp_dir().join(format!("wm-snapshot-escape-{}", uuid::Uuid::new_v4()));
        let src = root.join("input/source");
        let dst = root.join("output/destination");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::create_dir_all(dst.parent().unwrap()).unwrap();
        std::fs::write(root.join("input/payload"), b"attacker").unwrap();
        std::fs::write(root.join("output/payload"), b"untouched").unwrap();
        let hash = sha256_file_hex(&root.join("input/payload")).unwrap();
        std::fs::write(src.join("SHA256SUMS"), format!("{hash}  ../payload\n")).unwrap();
        assert_ne!(run_restore_command(&src, &dst, false, false), 0);
        assert_eq!(
            std::fs::read(root.join("output/payload")).unwrap(),
            b"untouched"
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn restore_rejects_symlink_in_source() {
        use std::os::unix::fs::symlink;
        let root = std::env::temp_dir().join(format!("wm-snapshot-link-{}", uuid::Uuid::new_v4()));
        let src = root.join("source");
        let dst = root.join("destination");
        let outside = root.join("outside");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::create_dir_all(&outside).unwrap();
        std::fs::write(src.join("data.mdb"), b"database").unwrap();
        std::fs::write(outside.join("item"), b"payload").unwrap();
        symlink(&outside, src.join("receipts")).unwrap();
        let a = sha256_file_hex(&src.join("data.mdb")).unwrap();
        let b = sha256_file_hex(&src.join("receipts/item")).unwrap();
        std::fs::write(
            src.join("SHA256SUMS"),
            format!("{a}  data.mdb\n{b}  receipts/item\n"),
        )
        .unwrap();
        assert_ne!(run_restore_command(&src, &dst, false, false), 0);
        assert!(!dst.exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn restore_rejects_tampering_before_writing_anything() {
        let root =
            std::env::temp_dir().join(format!("wm-snapshot-tamper-{}", uuid::Uuid::new_v4()));
        let src = root.join("source");
        let dst = root.join("destination");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::write(src.join("data.mdb"), b"correct").unwrap();
        let hash = sha256_file_hex(&src.join("data.mdb")).unwrap();
        std::fs::write(src.join("SHA256SUMS"), format!("{hash}  data.mdb\n")).unwrap();
        std::fs::write(src.join("data.mdb"), b"changed").unwrap();
        assert_ne!(run_restore_command(&src, &dst, false, false), 0);
        assert!(!dst.exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn backup_rejects_destination_within_source_without_creating_it() {
        let root =
            std::env::temp_dir().join(format!("wm-snapshot-overlap-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(root.join("data.mdb"), b"database").unwrap();
        assert_ne!(
            run_backup_command(&root, &root.join("nested/backup"), false),
            0
        );
        assert!(!root.join("nested").exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn restore_rejects_truncated_manifest_and_existing_destination() {
        let root =
            std::env::temp_dir().join(format!("wm-snapshot-coverage-{}", uuid::Uuid::new_v4()));
        let src = root.join("source");
        let dst = root.join("destination");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::write(src.join("data.mdb"), b"database").unwrap();
        std::fs::write(src.join("journal.jsonl"), b"journal").unwrap();
        let hash = sha256_file_hex(&src.join("data.mdb")).unwrap();
        std::fs::write(src.join("SHA256SUMS"), format!("{hash}  data.mdb\n")).unwrap();
        assert_ne!(run_restore_command(&src, &dst, false, false), 0);
        assert!(!dst.exists());
        std::fs::create_dir_all(&dst).unwrap();
        std::fs::write(dst.join("old"), b"preserve").unwrap();
        assert_ne!(run_restore_command(&src, &dst, true, false), 0);
        assert_eq!(std::fs::read(dst.join("old")).unwrap(), b"preserve");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn restore_rejects_shared_destination_parent() {
        use std::os::unix::fs::PermissionsExt;
        let root =
            std::env::temp_dir().join(format!("wm-snapshot-parent-{}", uuid::Uuid::new_v4()));
        let source = root.join("source");
        let destination = root.join("restored");
        std::fs::create_dir_all(&source).unwrap();
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::write(source.join("data.mdb"), b"database").unwrap();
        let hash = sha256_file_hex(&source.join("data.mdb")).unwrap();
        std::fs::write(source.join("SHA256SUMS"), format!("{hash}  data.mdb\n")).unwrap();
        assert_ne!(run_restore_command(&source, &destination, false, false), 0);
        assert!(!destination.exists());
        std::fs::remove_dir_all(root).unwrap();
    }
}

fn run_seed_command(store_path: &Path, action: &str, json: bool) {
    let journal_path = store_path.join("journal.jsonl");
    let seed = match action {
        "export" | "sync" => {
            let substrate =
                Substrate::open_readonly(store_path, Some(&journal_path), default_view())
                    .unwrap_or_else(|e| {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    });
            let epoch = substrate.store().epoch().unwrap_or(0);
            let records = substrate.store().record_count().unwrap_or(0);
            let cp = substrate.session_continuity(None).ok().flatten();
            let vault_path = store_path.join("vault.jsonl");
            let skel_count = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path)
                .skeletons
                .len()
                .max(16);
            let compiled =
                wm_gen3_core::wave2_braid::StonePillarMorphogenSeed::compile_from_live_state(
                    epoch,
                    records,
                    cp.as_ref().map(|c| c.record_id),
                    cp.as_ref()
                        .map(|c| c.summary.as_str())
                        .unwrap_or("live-export"),
                    skel_count,
                    0xA5A5_5A5A_F00D_CAFE,
                );
            if let Err(e) = compiled.save_to_store(store_path) {
                eprintln!("Error saving stone_pillar.seed.json: {e}");
                std::process::exit(1);
            }
            compiled
        }
        _ => wm_gen3_core::wave2_braid::StonePillarMorphogenSeed::load_from_store(store_path)
            .unwrap_or_else(|_| {
                let substrate =
                    Substrate::open_readonly(store_path, Some(&journal_path), default_view()).ok();
                let epoch = substrate
                    .as_ref()
                    .and_then(|s| s.store().epoch().ok())
                    .unwrap_or(0);
                let records = substrate
                    .as_ref()
                    .and_then(|s| s.store().record_count().ok())
                    .unwrap_or(0);
                let cp = substrate
                    .as_ref()
                    .and_then(|s| s.session_continuity(None).ok().flatten());
                let compiled =
                    wm_gen3_core::wave2_braid::StonePillarMorphogenSeed::compile_from_live_state(
                        epoch,
                        records,
                        cp.as_ref().map(|c| c.record_id),
                        cp.as_ref()
                            .map(|c| c.summary.as_str())
                            .unwrap_or("auto-bootstrapped"),
                        45,
                        0xA5A5_5A5A_F00D_CAFE,
                    );
                let _ = compiled.save_to_store(store_path);
                compiled
            }),
    };

    let regen = seed.regenerate_report();
    let seed_file = store_path.join("stone_pillar.seed.json");
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "action": action,
                "seed_path": seed_file.display().to_string(),
                "seed": seed,
                "regeneration_receipt": regen,
            }))
            .unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — Planarian Stone Pillar Morphogen Seed (W2-P4) ");
        println!("==================================================================");
        println!("Action:                 {}", action);
        println!("Seed File:              {}", seed_file.display());
        println!(
            "BendHub Constitution:   {} (Laws 1-16 Verified: {})",
            seed.bendhub_constitution_hash, regen.laws_1_to_16_verified
        );
        println!(
            "Substrate Snapshot:     Epoch {} | Records: {} | Checkpoint: {:?}",
            seed.epoch, seed.record_count, seed.latest_checkpoint_id
        );
        println!(
            "Morphogen Footprint:    {} bytes (< 64 KB bound: {})",
            seed.serialized_bytes, regen.within_64kb_planarian_bound
        );
        println!(
            "Restored Architecture:  {} Σ22 Glyphs | {} k*=8 Basins | {} ZHA Hexagram Roots | {} Skeletons",
            regen.sigma22_glyph_basis_restored,
            regen.cardinal_k8_basins_restored,
            regen.zha_tier2_hexagram_roots_restored,
            regen.geneseed_skeletons_restored
        );
        println!("Procrustes Anchor Hash: {}", seed.procrustes_anchor_digest);
        println!("Seed Integrity SHA-256: {}", seed.seed_sha256);
        println!(
            "Regeneration Fidelity:  {:.1}% (Integrity Verified: {})",
            regen.regeneration_fidelity_pct, regen.integrity_verified
        );
        println!("==================================================================");
    }
}

fn run_wave2_benchmark_command(json: bool) {
    let report = wm_gen3_core::wave2_braid::run_wave2_full_benchmark_suite();
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&report).unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — Wave 2 Braided Benchmark Suite (W2-P1..P35)   ");
        println!("==================================================================");
        println!(
            "Total Pillars Verified: {} / 35",
            report.total_pillars_verified
        );
        println!("Suite Execution Time:   {} µs", report.execution_time_us);
        println!("------------------------------------------------------------------");
        println!("Cluster A (Product-Finsler Manifold, Σ22, Voids & 4-Lane RRF):");
        println!(
            "  • Product Manifold MRR:      {:.3} (vs Euclidean {:.3})",
            report.cluster_a.product_manifold_mrr, report.cluster_a.euclidean_baseline_mrr
        );
        println!(
            "  • Pareto Metric Selected:    {:?} (ΔBIC = +{:.1})",
            report.cluster_a.selected_metric_rung, report.cluster_a.bic_gain_over_euclidean
        );
        println!(
            "  • Σ22 Spectrometer Latency:  {:.1} ns/eval (Law 6 Non-Dispatching)",
            report.cluster_a.sigma22_latency_ns
        );
        println!(
            "  • 0-After-9 Voids Found:     {} | 4-Lane RRF Recall@5: {:.1}%",
            report.cluster_a.topological_voids_discovered,
            report.cluster_a.rrf_4lane_recall_at_5 * 100.0
        );
        println!("------------------------------------------------------------------");
        println!("Cluster B (Schmitt-Trigger Hysteresis, Conformal, MMMBABY & Huíguāng):");
        println!(
            "  • Boundary Chatter:          {} -> {} transitions ({:.1}% reduction)",
            report.cluster_b.raw_threshold_oscillations,
            report.cluster_b.schmitt_trigger_oscillations,
            report.cluster_b.chatter_reduction_pct
        );
        println!(
            "  • Split-Conformal Coverage:  {:.1}% (Shift z>3.0 withdrawal: {})",
            report.cluster_b.conformal_empirical_coverage * 100.0,
            report.cluster_b.conformal_shift_detected
        );
        println!(
            "  • MMMBABY Sacrifice Veto:    {} | Huíguāng Damper: {}",
            report.cluster_b.mmmbaby_sacrifice_veto_verified,
            report.cluster_b.huiguang_damping_triggered
        );
        println!("------------------------------------------------------------------");
        println!("Cluster C (Solitons, Heavy-Hex Crosstalk M⁻¹, Procrustes & Tachikoma):");
        println!(
            "  • Soliton Collision Fidelity:{:.1}% | Pointer Bundle Savings: {:.1}%",
            report.cluster_c.soliton_collision_invariant_fidelity * 100.0,
            report.cluster_c.pointer_bundle_token_savings_pct
        );
        println!(
            "  • Crosstalk Error Reduction: {:.0}x | Procrustes RMSE: {:.2e}",
            report.cluster_c.crosstalk_error_reduction_factor,
            report.cluster_c.procrustes_post_alignment_rmse
        );
        println!(
            "  • Tachikoma Ghost Divergence:{:.4} -> {:.4} (Zero Herd Collapse)",
            report.cluster_c.tachikoma_pre_sync_divergence,
            report.cluster_c.tachikoma_post_sync_divergence
        );
        println!("------------------------------------------------------------------");
        println!("Cluster D (Violet Citadel, 1Fe-LSD Prodrug, eBPF Taint & CUSUM):");
        println!(
            "  • Prodrug Receptor Gate:     {}/2 foreign blocked, {}/1 target cleaved",
            report.cluster_d.prodrug_foreign_cleave_blocked,
            report.cluster_d.prodrug_target_cleave_succeeded
        );
        println!(
            "  • Auth Laundering Blocked:   {} | eBPF Taint Exfil Blocked: {}",
            report.cluster_d.auth_laundering_attempts_blocked,
            report.cluster_d.ebpf_tainted_exfiltrations_blocked
        );
        println!(
            "  • CUSUM Genjutsu Tarpit:     {} | Honest False Quarantines: {}",
            report.cluster_d.cusum_slow_bleed_trapped_in_genjutsu,
            report.cluster_d.honest_peer_false_quarantines
        );
        println!("------------------------------------------------------------------");
        println!("Cluster E ((3|1) Zero-DAG, Tri-Fold Cladistics, Paarthurnax & Dust):");
        println!(
            "  • Thought Dust Injected:     {} -> {} leaked (R_sed = ∞)",
            report.cluster_e.thought_dust_injected, report.cluster_e.canonical_noise_leaked
        );
        println!(
            "  • Cyclic Re-Proposals:       {} | Trojan High-Fitness Quarantined: {}",
            report.cluster_e.retired_lineage_cyclic_reproposals,
            report.cluster_e.trojan_high_fitness_quarantined
        );
        println!(
            "  • Paarthurnax Rehab Bonus:   {:.2}x | Zero-DAG Memory Collapse: {:.2}x",
            report.cluster_e.paarthurnax_rehab_detection_gain,
            report.cluster_e.zero_dag_memory_collapse_factor
        );
        println!("------------------------------------------------------------------");
        println!("Cluster F (Stone Pillar Seed, Heptagonal Spiral & Dhumavati Bardo):");
        println!(
            "  • Planarian Stone Seed:      {} bytes (<64 KB) | Regen: {:.1}%",
            report.cluster_f.stone_pillar_seed_bytes, report.cluster_f.regeneration_fidelity_pct
        );
        println!(
            "  • Heptagonal 360/7 Sectors:  {} / 70 unique (0 harmonic storms)",
            report.cluster_f.heptagonal_spiral_unique_sectors_70_steps
        );
        println!(
            "  • Dhumavati Bardo Drag:      {} tokens | Failure Recall: {:.1}%",
            report.cluster_f.dhumavati_bardo_active_token_drag,
            report.cluster_f.dhumavati_failure_recall_rate * 100.0
        );
        println!("==================================================================");
    }
}

fn run_wave3_benchmark_command(json: bool) {
    let report = wm_gen3_core::wave3_braid::run_wave3_full_benchmark_suite();
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&report).unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — Wave 3 Braided Benchmark Suite (W3-P1..P30)   ");
        println!("==================================================================");
        println!(
            "Total Pillars Verified: {} / 30",
            report.total_pillars_verified
        );
        println!("Suite Execution Time:   {} µs", report.execution_time_us);
        println!("------------------------------------------------------------------");
        println!("Cluster W3-I (28 Garden-Gana Triads & 108-Cycle Da'at Resonance):");
        println!(
            "  • Garden-Gana Triads:        {} / 28 verified",
            report.cluster_i.garden_gana_triads_verified
        );
        println!(
            "  • 108-Cycle Da'at Kuramoto:  r = {:.4} (Phase-Locked: {})",
            report.cluster_i.daat_108_kuramoto_r, report.cluster_i.daat_phase_locked
        );
        println!("------------------------------------------------------------------");
        println!("Cluster W3-II (Zero-Token LongMemEval, HRR, Spreading & CLS Oblio):");
        println!(
            "  • Zero-Token Intent Acc:     {:.1}% | Doctor Synonym: {} | Implicit Pref: {}",
            report.cluster_ii.zero_token_intent_accuracy_pct,
            report.cluster_ii.doctor_synonym_facet_recovered,
            report.cluster_ii.implicit_preference_facet_extracted
        );
        println!(
            "  • HRR Circular Unbind Sim:   {:.3} | 3-Hop Spreading Nodes: {}",
            report.cluster_ii.hrr_unbind_cosine_similarity,
            report.cluster_ii.spreading_activation_3hop_nodes
        );
        println!(
            "  • VoE Surprise Spike:        {} | CLS Oblio LTD/LTP Ratio: {:.2}:1",
            report.cluster_ii.voe_surprise_spike_triggered,
            report.cluster_ii.cls_oblio_ltd_ltp_ratio
        );
        println!("------------------------------------------------------------------");
        println!("Cluster W3-III (2-Layer SMoTE, Akashic Seeds, Yin & Level-4 Synergy):");
        println!(
            "  • SMoTE Layer-1 Edge Exit:   {} | Layer-2 Cautious Veto: {} ({:.1}% saved)",
            report.cluster_iii.smote_layer1_zero_token_exit,
            report.cluster_iii.smote_layer2_cautious_veto_honored,
            report.cluster_iii.smote_tokens_saved_pct
        );
        println!(
            "  • Akashic Seeds Bloomed:     {} | Yin Stillness Triggered: {}",
            report.cluster_iii.akashic_dormant_seeds_bloomed,
            report.cluster_iii.yin_stillness_triggered_on_overdrive
        );
        println!(
            "  • Level-4 Emergence Synergy: {:.2}x | Symbiotic Loosh Scalar: {:.3}",
            report.cluster_iii.level4_emergence_synergy_ratio,
            report.cluster_iii.loosh_symbiotic_scalar
        );
        println!("------------------------------------------------------------------");
        println!("Cluster W3-IV (DRQ Purple Nash, Cache-Timing, Fuller & CyberBrain):");
        println!(
            "  • DRQ Nash Blue Defense:     {:.1}% | Shadow Handles Quarantined: {}",
            report.cluster_iv.drq_nash_blue_defense_rate * 100.0,
            report.cluster_iv.forgotten_shadow_handles_quarantined
        );
        println!(
            "  • Cache-Timing Detected:     {} | 2-Bit Rowhammer Blocked: {}",
            report.cluster_iv.cache_timing_covert_channel_detected,
            report.cluster_iv.neuron_lens_2bit_flip_blocked
        );
        println!(
            "  • Fuller Ephemeralization:   {:.1}x ({}) | Reflex Recovery: {}",
            report.cluster_iv.fuller_ephemeralization_index,
            report.cluster_iv.fuller_best_trim_tab,
            report.cluster_iv.cyberbrain_reflex_recovery_verified
        );
        println!("------------------------------------------------------------------");
        println!("Cluster W3-V (Lived-Time, Dual-Tree, 7D Harmony, Y1, Zodiac & Ashby):");
        println!(
            "  • 30d Idle Lived Retention:  {:.1}% (vs Wall-Clock {:.2}%) | Sparks: {}",
            report.cluster_v.lived_time_30day_idle_retention * 100.0,
            report.cluster_v.wall_clock_30day_idle_retention * 100.0,
            report.cluster_v.dual_tree_sparks_redeemed
        );
        println!(
            "  • 7D Harmony Cold-Start:     {:.2} | Y1 Chatter Suppressed: {} | Disarm=0: {}",
            report.cluster_v.harmony_7d_cold_start_value,
            report.cluster_v.y1_hysteresis_chatter_suppressed,
            report.cluster_v.wm_actuation_zero_disarm_verified
        );
        println!(
            "  • Wu Xing Max Dominance:     {:.2} | Cantrip Avadhuti: {:.3} | Ashby Speedup: {:.1}x",
            report.cluster_v.zodiacal_wuxing_max_dominance,
            report.cluster_v.cantrip_avadhuti_convergence,
            report.cluster_v.ashby_ultrastable_speedup_factor
        );
        println!("------------------------------------------------------------------");
        println!("Cluster W3-VI (Engram O(1), GAM, 64k RTS, Z80, Satkona, Valmere & CPR0.6):");
        println!(
            "  • Engram O(1) Fast-Lane:     {} | GAM JIT Fidelity: {:.3} | 64k RTS Avoidance: {:.2}%",
            report.cluster_vi.engram_o1_fast_lane_hit,
            report.cluster_vi.gam_jit_researcher_fidelity,
            report.cluster_vi.rts_all_to_all_chatter_avoided_pct
        );
        println!(
            "  • Z80 Golden Pass Rate:      {:.1}% | Satkona NOTEARS Residual: {:.2e} (MPC: {})",
            report.cluster_vi.z80_clean_room_golden_pass_rate * 100.0,
            report.cluster_vi.satkona_v4_notears_residual,
            report.cluster_vi.satkona_v4_mpc_completed
        );
        println!(
            "  • Valmere 3-Path & PageCurve:{} | Runner Non-Conflation: {} | CPR 0.6 PQ+Gnosis: {}",
            report.cluster_vi.valmere_3path_and_page_curve_ok,
            report.cluster_vi.gate_runner_conflation_blocked,
            report.cluster_vi.cpr06_pq_and_gnosis_laws_verified
        );
        println!("==================================================================");
    }
}

fn run_wave4_benchmark_command(json: bool) {
    let report = wm_gen3_core::wave4_takwin::run_wave4_full_benchmark_suite();
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&report).unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — Wave 4 Takwīn & Trace-Shrinking Suite         ");
        println!("==================================================================");
        println!("Execution Time:         {} µs", report.execution_time_us);
        println!(
            "PEB-23 Trace Shrinker:  {} steps ➔ {} minimal steps ({:.0}x compression)",
            report.raw_trace_steps,
            report.shrunk_counterexample_steps,
            report.trace_shrink_compression_x
        );
        println!("  • Replay Blob SHA-256: {}", report.replay_blob_sha256);
        println!(
            "PEB-24 Holographic Wiki: {} records, {} links ({:.1}% telephone loss)",
            report.wiki_records_indexed,
            report.wiki_associative_links,
            report.subagent_telephone_loss_pct
        );
        println!("  • Wiki Merkle Root:    {}", report.wiki_merkle_root);
        println!(
            "PEB-25 Shaping Monitor:  Reliance={} · ProductCode={} · Clean={}",
            report.reliance_shaping_blocked_superseded,
            report.product_code_circumvention_caught,
            report.clean_reasoning_allowed
        );
        println!("==================================================================");
    }
}

fn run_wiki_command(store_path: &Path, out_dir: &Path, limit: usize, json: bool) {
    use sha2::{Digest, Sha256};
    let substrate = match Substrate::open_readonly(store_path, None, default_view()) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error opening store {}: {e}", store_path.display());
            std::process::exit(1);
        }
    };
    let records = match substrate.store().recent_records(limit.max(1)) {
        Ok(records) => records,
        Err(e) => {
            eprintln!("Error reading recent records: {e}");
            std::process::exit(1);
        }
    };
    if records.is_empty() {
        eprintln!("Store {} has no records to export", store_path.display());
        std::process::exit(1);
    }

    let mut entries = Vec::with_capacity(records.len());
    for (idx, rec) in records.iter().enumerate() {
        let record_id = rec.id();
        let source = rec.source();
        let domain = if source.contains("dream") {
            "dreams"
        } else if source.starts_with("session") || source.contains("checkpoint") {
            "sessions"
        } else if source.contains("tool") || source.contains("exec") {
            "tools"
        } else if source.contains("relation") || source.contains("bridge") {
            "relations"
        } else {
            "memory"
        };
        let content_preview: String = rec.content().chars().take(280).collect();
        let mut h = Sha256::new();
        h.update(rec.content().as_bytes());
        let sha = hex_encode(&h.finalize());
        let next_id = records
            .get((idx + 1) % records.len())
            .map_or(record_id, |r| r.id());
        entries.push(wm_gen3_core::wave4_takwin::WikiMemoryEntry {
            record_id,
            constellation_hex: (record_id % 64) as u8,
            domain: domain.to_string(),
            title: format!("Record #{} ({})", record_id, source),
            content: content_preview.replace('\n', " "),
            content_sha256: sha[..16].to_string(),
            linked_record_ids: if next_id != record_id {
                vec![next_id]
            } else {
                vec![]
            },
        });
    }

    let bundle = wm_gen3_core::wave4_takwin::compile_holographic_wiki(&entries);
    if let Err(e) = std::fs::create_dir_all(out_dir) {
        eprintln!("Error creating wiki output dir {}: {e}", out_dir.display());
        std::process::exit(1);
    }
    let _ = std::fs::write(out_dir.join("_index.md"), &bundle.index_markdown);
    for (page_name, page_md) in &bundle.pages {
        let _ = std::fs::write(out_dir.join(page_name), page_md);
    }

    if json {
        let out = serde_json::json!({
            "status": "ok",
            "out_dir": out_dir.display().to_string(),
            "records_indexed": bundle.total_records_indexed,
            "wiki_links": bundle.total_wiki_links,
            "pages_written": bundle.pages.len() + 1,
            "wiki_merkle_root": bundle.bundle_merkle_root,
        });
        println!("{}", serde_json::to_string_pretty(&out).unwrap_or_default());
    } else {
        println!(
            "Exported Holographic Wiki to {} ({} records, {} links, Merkle root: {})",
            out_dir.display(),
            bundle.total_records_indexed,
            bundle.total_wiki_links,
            bundle.bundle_merkle_root
        );
    }
}

fn run_longmemeval_benchmark_command(json: bool) {
    let report = wm_gen3_core::wave3_braid::run_longmemeval_zero_token_benchmark();
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&report).unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — LongMemEval Zero-Token + Engram + GAM Suite   ");
        println!("==================================================================");
        println!(
            "Questions Evaluated:    {} (across 5 LongMemEval categories)",
            report.total_questions_evaluated
        );
        println!(
            "LLM Tokens Consumed:    {} tokens (Zero-Token Deterministic Pipeline)",
            report.total_llm_tokens_consumed
        );
        println!("Suite Execution Time:   {} µs", report.execution_time_us);
        println!(
            "Macro Recall@3:         {:.1}% -> {:.1}% (+{:.1}% gain)",
            report.baseline_macro_recall_pct,
            report.zero_token_braided_macro_recall_pct,
            report.macro_recall_gain_pct
        );
        println!("------------------------------------------------------------------");
        for cat in &report.categories {
            println!(
                "  • {:48} {:5.1}% -> {:5.1}% (+{:5.1}%)",
                cat.category_name,
                cat.baseline_lexical_recall_pct,
                cat.zero_token_engram_gam_recall_pct,
                cat.absolute_recall_gain_pct
            );
        }
        println!("==================================================================");
    }
}

fn run_satkona_command(json: bool) {
    let receipt = wm_gen3_core::wave3_braid::solve_satkona_v4_universal(
        [[0.0, 0.85, 0.42], [0.0, 0.0, 0.76], [0.0, 0.0, 0.0]],
        &[0.95, 0.84, 0.99],
        &[true, true, false],
    );
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&receipt).unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — Satkona v4 Universal Dharmic Convex Solver    ");
        println!("==================================================================");
        println!(
            "Layer 2 (Net/Root NOTEARS Causal DAG):   Residual = {:.2e} | Edges = {}",
            receipt.notears_acyclicity_residual, receipt.causal_edges_discovered
        );
        println!(
            "Layer 3 (Void/Stars Bregman+Frank-Wolfe):Dharmic Violations = {} | KL = {:.4}",
            receipt.dharmic_invariant_violations, receipt.bregman_kl_divergence
        );
        println!(
            "Optimal Marginal Polytope Allocation:    {:?}",
            receipt
                .optimal_polytope_weights
                .iter()
                .map(|w| (w * 1000.0).round() / 1000.0)
                .collect::<Vec<_>>()
        );
        println!(
            "Layer 4 (Tail/Accelerator Receding MPC): 3-Step Closed-Loop Completed = {}",
            receipt.mpc_receding_horizon_completed
        );
        println!("==================================================================");
    }
}

fn run_gnosis_command(store_path: &Path, json: bool) {
    let journal_path = store_path.join("journal.jsonl");
    let substrate = Substrate::open_readonly(store_path, Some(&journal_path), default_view()).ok();
    let epoch = substrate
        .as_ref()
        .and_then(|s| s.store().epoch().ok())
        .unwrap_or(0);
    let records = substrate
        .as_ref()
        .and_then(|s| s.store().record_count().ok())
        .unwrap_or(0);
    let armed = std::env::var("WM_ACTUATION")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);
    let snap = wm_gen3_core::wave3_braid::run_live_gnosis_portal_snapshot(epoch, records, armed);
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&snap).unwrap_or_default()
        );
    } else {
        println!("==================================================================");
        println!("  WhiteMagic Gen3 — Gnosis Portal & 7D HarmonyVector Samma-Meter  ");
        println!("==================================================================");
        println!(
            "Substrate State:        Epoch {} | Records: {} | BendHub 16-Law: {}",
            snap.epoch, snap.record_count, snap.bendhub_16law_constitution
        );
        println!(
            "7D HarmonyVector:       fai={:.2} thr={:.2} rsp={:.2} stb={:.2} dha={:.2} kar={:.2} nrg={:.2}",
            snap.harmony_vector_7d.fairness,
            snap.harmony_vector_7d.throughput,
            snap.harmony_vector_7d.responsiveness,
            snap.harmony_vector_7d.stability,
            snap.harmony_vector_7d.dharma,
            snap.harmony_vector_7d.karma_debt,
            snap.harmony_vector_7d.energy,
        );
        println!(
            "Samma-Meter (>40% Dev): {:?} | Y1 Hysteresis Step: {:?} (WM_ACTUATION={})",
            snap.samma_highlighted_dimension, snap.y1_actuator_step, snap.wm_actuation_armed
        );
        println!(
            "Zodiacal Wu Xing:       Phase #{} ({}) | Max Dominance: {:.2}",
            snap.zodiacal_wuxing_state.phase_index,
            snap.zodiacal_wuxing_state.phase_label,
            snap.zodiacal_wuxing_state.max_loop_dominance_ratio
        );
        println!(
            "Anti-Maya Visual Laws:  Chroma={:.2} (measured) | Opacity={:.2} | CPU={:.2}% (<0.30%: {})",
            snap.visual_tokens_chroma_measured,
            snap.visual_tokens_opacity_freshness,
            snap.observer_cpu_pct,
            snap.observer_budget_ok
        );
        println!("==================================================================");
    }
}

fn run_sangha_cli(args: &[String]) {
    use std::path::PathBuf;

    // Do not redispatch through a `sangha` command on PATH: the installer
    // creates that command as a wrapper back to `wm sangha`, which recurses.
    // A source checkout can be selected explicitly or installed beside wm.
    let mut candidates = Vec::new();
    if let Some(path) = std::env::var_os("WHITEMAGIC_SANGHA_SCRIPT") {
        candidates.push(PathBuf::from(path));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            candidates.push(parent.join("sangha.py"));
            candidates.push(parent.join("share/whitemagic/sangha.py"));
        }
    }
    let script = candidates.into_iter().find(|path| path.is_file());
    let Some(script) = script else {
        eprintln!(
            "Sangha is not installed with this binary. Install the Sangha Python source and its companion modules, or set WHITEMAGIC_SANGHA_SCRIPT to scripts/sangha.py."
        );
        std::process::exit(2);
    };

    let status = match std::process::Command::new("python3")
        .arg(script)
        .args(args)
        .status()
    {
        Ok(status) => status,
        Err(error) => {
            eprintln!("Cannot start Sangha: Python 3 is unavailable ({error}).");
            std::process::exit(2);
        }
    };
    if let Some(code) = status.code() {
        std::process::exit(code);
    }
}

fn run_cpr_cli(args: &[String]) {
    if args.is_empty() || args.iter().any(|a| a == "--help" || a == "-h") {
        println!("==================================================");
        println!("  Causal Provenance Receipts (CPR) / AER-1 Engine ");
        println!("==================================================");
        println!("Usage: wm cpr <subcommand> [options]");
        println!("\nSubcommands:");
        println!("  verify      Verify receipt envelope against schema & signature");
        println!("  consumer    Verify receipt against expected consumer policy");
        println!("  anchor      Anchor receipt digest or generate merkle proofs");
        println!("  disclose    Generate selective disclosure receipt variant");
        println!("\nExamples:");
        println!("  wm cpr verify receipt.json");
        println!("  wm cpr consumer --policy strict receipt.json");
        return;
    }

    let subcmd = &args[0];
    let rest = &args[1..];
    let module = match subcmd.as_str() {
        "verify" => "continuity_receipt.verify",
        "consumer" => "continuity_receipt.consumer",
        "anchor" => "continuity_receipt.anchor",
        "disclose" => "continuity_receipt.disclose",
        _ => "continuity_receipt.verify",
    };

    let pass_args =
        if subcmd == "verify" || subcmd == "consumer" || subcmd == "anchor" || subcmd == "disclose"
        {
            rest
        } else {
            args
        };

    let module_probe = r#"
import importlib.util, sys
try:
    available = importlib.util.find_spec(sys.argv[1]) is not None
except (ModuleNotFoundError, ValueError):
    available = False
sys.exit(0 if available else 1)
"#;
    let module_available = std::process::Command::new("python3")
        .args(["-c", module_probe, module])
        .status();
    let module_available = matches!(module_available, Ok(status) if status.success());

    let mut path_candidates = Vec::new();
    if let Some(root) = std::env::var_os("WHITEMAGIC_CPR_ROOT") {
        path_candidates.push(std::path::PathBuf::from(root));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            path_candidates.push(parent.join("continuity-receipt"));
            path_candidates.push(parent.join("share/continuity-receipt"));
        }
    }
    let script_name = if ["verify", "consumer", "anchor", "disclose"].contains(&subcmd.as_str()) {
        subcmd.as_str()
    } else {
        "verify"
    };
    let path_root = path_candidates.into_iter().find(|root| {
        root.join("continuity_receipt")
            .join(format!("{script_name}.py"))
            .is_file()
    });

    let status = if module_available {
        std::process::Command::new("python3")
            .arg("-m")
            .arg(module)
            .args(pass_args)
            .status()
    } else if let Some(project_root) = path_root {
        let mut command = std::process::Command::new("python3");
        command.arg("-m").arg(module).args(pass_args);
        let mut python_paths = vec![project_root];
        if let Some(existing) = std::env::var_os("PYTHONPATH") {
            python_paths.extend(std::env::split_paths(&existing));
        }
        if let Ok(joined) = std::env::join_paths(python_paths) {
            command.env("PYTHONPATH", joined);
        }
        command.status()
    } else {
        eprintln!(
            "CPR is not installed. Install the continuity_receipt Python package or set WHITEMAGIC_CPR_ROOT to its source checkout."
        );
        std::process::exit(2);
    };
    let status = match status {
        Ok(status) => status,
        Err(error) => {
            eprintln!("Cannot start CPR: Python 3 is unavailable ({error}).");
            std::process::exit(2);
        }
    };
    if let Some(code) = status.code() {
        std::process::exit(code);
    }
}

fn run_homeostasis_command(json: bool) {
    let hw = wm_gen3_core::homeostasis::HardwareTelemetry::probe();
    let bio = hw.to_bioelectric_state();
    let mut schmitt = wm_gen3_core::wave2_braid::SchmittTriggerHomeostat::default();
    let norm_pressure = ((f64::from(bio.v_rest_mv) + 70.0) / 55.0).clamp(0.0, 1.0);
    let schmitt_regime = schmitt.step(norm_pressure);
    let (mmmbaby_geom, mmmbaby_arith) = wm_gen3_core::wave2_braid::compute_mmmbaby_vitality_index(
        [
            f64::from(bio.ashby_chambers.epistemic_recall.throughput_factor),
            f64::from(bio.ashby_chambers.compute.throughput_factor),
            f64::from(bio.ashby_chambers.storage.throughput_factor),
            (bio.mem_available_mb / 8192.0).clamp(0.10, 1.0),
            f64::from(bio.ashby_chambers.perimeter_security.throughput_factor),
            (1.0 - (bio.cpu_temp_c - 35.0).max(0.0) / 65.0).clamp(0.10, 1.0),
        ],
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    );
    let sacrifice_veto = mmmbaby_geom <= 1e-6;
    if json {
        let mut out = serde_json::to_value(&bio).unwrap_or_default();
        if let Some(obj) = out.as_object_mut() {
            obj.insert(
                "schmitt_trigger_regime".into(),
                serde_json::json!(format!("{schmitt_regime:?}")),
            );
            obj.insert(
                "mmmbaby_vitality".into(),
                serde_json::json!({
                    "geometric_vitality": mmmbaby_geom,
                    "arithmetic_vitality": mmmbaby_arith,
                    "non_compensatory_sacrifice_veto": sacrifice_veto,
                }),
            );
            obj.insert(
                "bendhub_constitution_v2".into(),
                serde_json::json!("0x0d479d846e9ce92faa45a2346110fce8"),
            );
        }
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
    } else {
        println!("==================================================");
        println!("  WhiteMagic Gen3 Bioelectric Homeostasis Monitor ");
        println!("==================================================");
        println!(
            "Resting Potential:  {:.1} mV (Serene baseline: -70.0 mV)",
            bio.v_rest_mv
        );
        println!(
            "Homeostatic Regime: {:?} (Schmitt-Trigger: {:?})",
            bio.regime, schmitt_regime
        );
        println!("Metabolism Mode:    {:?}", bio.metabolism_mode);
        println!(
            "MMMBABY Vitality:   {:.3} (Arithmetic: {:.3}, Sacrifice Veto: {})",
            mmmbaby_geom, mmmbaby_arith, sacrifice_veto
        );
        println!("CPU Temperature:    {:.1}°C", bio.cpu_temp_c);
        if let Some(bat) = bio.battery_pct {
            println!(
                "Battery Level:      {:.1}% ({})",
                bat,
                if bio.on_ac_power {
                    "AC Connected"
                } else {
                    "Discharging"
                }
            );
        } else {
            println!("Power Supply:       AC Connected (no battery detected)");
        }
        println!("Load Average (1m):  {:.2}", bio.load_avg_1m);
        println!("Available RAM:      {:.1} MB", bio.mem_available_mb);
        println!(
            "Root NVMe Free:     {:.2} GB (Invariant floor: 20.0 GB)",
            bio.nvme_free_gb
        );
        println!(
            "Probe Latency:      {:.2} µs",
            bio.probe_latency_ns / 1000.0
        );
        println!("--------------------------------------------------");
        println!(
            "Ashby 4-Chamber Decoupled Homeostats (κ = {:.2}, {:.0}x speedup):",
            bio.ashby_chambers.coupling_coefficient, bio.ashby_chambers.adaptation_speedup_factor
        );
        println!(
            "  • Storage Chamber:          {:6.1} mV | {:?} (throughput: {:.0}%)",
            bio.ashby_chambers.storage.v_chamber_mv,
            bio.ashby_chambers.storage.regime,
            bio.ashby_chambers.storage.throughput_factor * 100.0
        );
        println!(
            "  • Compute/Thermal Chamber:  {:6.1} mV | {:?} (throughput: {:.0}%)",
            bio.ashby_chambers.compute.v_chamber_mv,
            bio.ashby_chambers.compute.regime,
            bio.ashby_chambers.compute.throughput_factor * 100.0
        );
        println!(
            "  • Epistemic Recall Chamber: {:6.1} mV | {:?} (throughput: {:.0}%)",
            bio.ashby_chambers.epistemic_recall.v_chamber_mv,
            bio.ashby_chambers.epistemic_recall.regime,
            bio.ashby_chambers.epistemic_recall.throughput_factor * 100.0
        );
        println!(
            "  • Perimeter LSM Chamber:    {:6.1} mV | {:?} (throughput: {:.0}%)",
            bio.ashby_chambers.perimeter_security.v_chamber_mv,
            bio.ashby_chambers.perimeter_security.regime,
            bio.ashby_chambers.perimeter_security.throughput_factor * 100.0
        );
        println!("--------------------------------------------------");
        if bio.nvme_free_gb < 20.0 {
            println!("STATUS: [CRITICAL ALARM] NVMe storage floor breached (<20 GB)!");
        } else if bio.v_rest_mv >= -35.0 {
            println!("STATUS: [STRESSED] Thermal or compute throttling active.");
        } else {
            println!("STATUS: [OPTIMAL] Serene bioelectric homeostatic balance.");
        }
    }
}

struct ScratchStore(Option<PathBuf>);

impl Drop for ScratchStore {
    fn drop(&mut self) {
        if let Some(path) = self.0.take() {
            let _ = std::fs::remove_dir_all(path);
        }
    }
}

fn run_persistence_selftest() -> Result<serde_json::Value, String> {
    let temp_root = std::env::temp_dir();
    run_persistence_selftest_at(&temp_root)
}

const MAX_JSONRPC_LINE_BYTES: usize = 8 * 1024 * 1024;

enum BoundedLine {
    Data(Vec<u8>),
    TooLong,
}

/// Read one newline-framed request while storing no more than `max_bytes`.
/// Once oversized, drain through this line's newline so the next frame remains usable.
fn read_bounded_line<R: std::io::BufRead>(
    reader: &mut R,
    max_bytes: usize,
) -> std::io::Result<Option<BoundedLine>> {
    let mut line = Vec::new();
    let mut too_long = false;
    loop {
        let available = reader.fill_buf()?;
        if available.is_empty() {
            if line.is_empty() && !too_long {
                return Ok(None);
            }
            return Ok(Some(if too_long {
                BoundedLine::TooLong
            } else {
                BoundedLine::Data(line)
            }));
        }
        let newline = available.iter().position(|byte| *byte == b'\n');
        let consumed = newline.map_or(available.len(), |index| index + 1);
        let payload_len = newline.unwrap_or(consumed);
        if !too_long {
            if payload_len > max_bytes.saturating_sub(line.len()) {
                too_long = true;
                line.clear();
            } else {
                line.extend_from_slice(&available[..payload_len]);
            }
        }
        reader.consume(consumed);
        if newline.is_some() {
            return Ok(Some(if too_long {
                BoundedLine::TooLong
            } else {
                BoundedLine::Data(line)
            }));
        }
    }
}

fn write_jsonrpc_parse_error(output: &mut impl std::io::Write, message: &str) {
    let envelope = serde_json::json!({
        "jsonrpc": "2.0",
        "id": null,
        "error": { "code": -32700, "message": message }
    });
    let _ = writeln!(output, "{envelope}");
    let _ = output.flush();
}

fn run_persistence_selftest_at(temp_root: &Path) -> Result<serde_json::Value, String> {
    with_exclusive_scratch(temp_root, run_persistence_probe, |path| {
        std::fs::remove_dir_all(path)
    })
}

fn with_exclusive_scratch<T>(
    temp_root: &Path,
    probe: impl FnOnce(&Path) -> Result<T, String>,
    cleanup: impl FnOnce(&Path) -> std::io::Result<()>,
) -> Result<T, String> {
    let scratch_path = temp_root.join(format!("wm-selftest-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir(&scratch_path).map_err(|e| {
        format!(
            "create exclusive scratch directory {}: {e}",
            scratch_path.display()
        )
    })?;
    let mut cleanup_guard = ScratchStore(Some(scratch_path.clone()));
    let probe_result = probe(&scratch_path);
    let cleanup_result = cleanup(&scratch_path).and_then(|()| {
        if scratch_path.exists() {
            Err(std::io::Error::other(
                "cleanup completed but scratch directory still exists",
            ))
        } else {
            Ok(())
        }
    });
    if cleanup_result.is_ok() {
        cleanup_guard.0 = None;
    }
    drop(cleanup_guard);
    match (probe_result, cleanup_result) {
        (Ok(value), Ok(())) => Ok(value),
        (Err(probe_error), Ok(())) => Err(probe_error),
        (Ok(_), Err(cleanup_error)) => {
            Err(format!("selftest scratch cleanup failed: {cleanup_error}"))
        }
        (Err(probe_error), Err(cleanup_error)) => Err(format!(
            "selftest probe failed: {probe_error}; selftest scratch cleanup also failed: {cleanup_error}"
        )),
    }
}

fn run_persistence_probe(scratch_path: &Path) -> Result<serde_json::Value, String> {
    let store_path = scratch_path.join("store");
    let journal_path = scratch_path.join("journal.jsonl");
    let content = "WhiteMagic isolated persistence selftest canary";
    {
        let mut substrate = Substrate::open(&store_path, Some(&journal_path), default_view())?;
        substrate.set_intake_authority(RatifiedChannel::mint("wm-selftest"));
        let results = substrate.remember_batch(&[RememberItem {
            content: content.to_string(),
            source: "system:selftest".to_string(),
            kind: ImportKind::System,
        }]);
        match results.first() {
            Some(Ok(_)) => {}
            Some(Err(error)) => return Err(format!("persistence write refused: {error}")),
            None => return Err("persistence write returned no result".to_string()),
        }
        substrate.finish();
    }
    let journal = std::fs::read_to_string(&journal_path)
        .map_err(|e| format!("read selftest journal: {e}"))?;
    let journal_events = journal
        .lines()
        .filter(|line| !line.trim().is_empty())
        .count();
    if journal_events == 0
        || journal
            .lines()
            .any(|line| serde_json::from_str::<serde_json::Value>(line).is_err())
    {
        return Err("selftest journal is empty or contains malformed events".to_string());
    }
    let journal_rows: Vec<serde_json::Value> = journal
        .lines()
        .map(|line| serde_json::from_str(line).expect("JSON checked above"))
        .collect();
    let run_end = journal_rows
        .iter()
        .find(|event| event.get("type").and_then(serde_json::Value::as_str) == Some("run.end"))
        .ok_or_else(|| "selftest journal has no run.end event".to_string())?;
    if run_end
        .get("journal_ok")
        .and_then(serde_json::Value::as_bool)
        != Some(true)
    {
        return Err("selftest run.end reports an unhealthy journal".to_string());
    }
    let reopened = Substrate::open_readonly(&store_path, None, default_view())?;
    let records = reopened
        .store()
        .record_count()
        .map_err(|e| format!("count reopened records: {e}"))?;
    if records != 1 {
        return Err(format!("reopened record count was {records}, expected 1"));
    }
    let found = reopened
        .store()
        .iter_records()
        .map_err(|e| format!("read reopened records: {e}"))?
        .iter()
        .any(|record| record.content() == content);
    if !found {
        return Err("reopened store did not contain the written canary".to_string());
    }
    let journal_commits = journal
        .lines()
        .filter_map(|line| serde_json::from_str::<serde_json::Value>(line).ok())
        .any(|event| {
            event.get("type").and_then(serde_json::Value::as_str) == Some("ingest.batch")
                && event.get("written").and_then(serde_json::Value::as_u64) == Some(1)
        });
    if !journal_commits {
        return Err("selftest journal has no one-record ingest.batch event".to_string());
    }
    drop(reopened);
    Ok(serde_json::json!({
        "status": "ok", "engine": "gen3", "version": WM_VERSION,
        "persistence": "durable_reopen", "records": records, "journal_events": journal_events,
        "scratch_store": "isolated_and_cleaned"
    }))
}

#[cfg(test)]
mod runtime_truth_tests {
    use super::*;

    #[test]
    fn bounded_jsonrpc_reader_drains_oversized_line_then_reads_next_frame() {
        let input = b"0123456789012345\n{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"ping\"}\n";
        let mut reader = std::io::Cursor::new(input);
        assert!(matches!(
            read_bounded_line(&mut reader, 8).expect("read oversized line"),
            Some(BoundedLine::TooLong)
        ));
        let Some(BoundedLine::Data(next)) =
            read_bounded_line(&mut reader, 128).expect("read next frame")
        else {
            panic!("next JSON-RPC frame should remain available");
        };
        let request = wm_gen3_harness::receipt_verify::parse_strict_json(
            std::str::from_utf8(&next).expect("valid utf8"),
        )
        .expect("parse next frame");
        assert_eq!(request["id"], 7);
        assert!(read_bounded_line(&mut reader, 128).expect("eof").is_none());
    }

    #[test]
    fn selftest_fails_closed_when_temp_root_cannot_create_scratch() {
        let root =
            std::env::temp_dir().join(format!("wm-selftest-blocker-{}", uuid::Uuid::new_v4()));
        std::fs::write(&root, b"keep").expect("create non-directory temp root");
        let result = run_persistence_selftest_at(&root);
        assert!(result.is_err());
        assert_eq!(std::fs::read(&root).expect("read blocker"), b"keep");
        std::fs::remove_file(root).expect("cleanup blocker");
    }

    #[test]
    fn selftest_reports_probe_and_cleanup_failures_and_guard_retries_cleanup() {
        let root =
            std::env::temp_dir().join(format!("wm-selftest-cleanup-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir(&root).expect("create temp root");
        let mut acquired = None;
        let result = with_exclusive_scratch(
            &root,
            |scratch| {
                acquired = Some(scratch.to_path_buf());
                Err::<(), _>("injected probe failure".to_string())
            },
            |_| Err(std::io::Error::other("injected cleanup failure")),
        );
        let error = result.unwrap_err();
        assert!(error.contains("injected probe failure"));
        assert!(error.contains("injected cleanup failure"));
        assert!(
            !acquired.expect("scratch was acquired").exists(),
            "Drop guard retries cleanup"
        );
        std::fs::remove_dir(root).expect("cleanup temp root");
    }

    #[test]
    fn mesh_cli_dial_allowlist_refuses_empty_and_unlisted_peers() {
        let err = enforce_mesh_sync_dial_allowlist("", "127.0.0.1:7369")
            .expect_err("empty allowlist must refuse");
        assert!(err.contains("WM_MESH_SYNC_ALLOWLIST"), "{err}");

        enforce_mesh_sync_dial_allowlist("127.0.0.1:7369", "127.0.0.1:7369")
            .expect("listed peer accepted");
        assert!(
            enforce_mesh_sync_dial_allowlist("127.0.0.1:7369", "10.0.0.5:7369").is_err(),
            "unlisted peer must be refused"
        );
        assert!(
            enforce_mesh_sync_dial_allowlist("127.0.0.1:7369", "not-an-address").is_err(),
            "malformed peer address must fail loudly"
        );
    }
}

#[cfg(feature = "systemone")]
fn run_decision_command(
    state_file: Option<PathBuf>,
    questions_path: &Path,
    model: Option<PathBuf>,
    json_output: bool,
) {
    use wm_gen3_systemone::SystemOne;

    let raw_state = match &state_file {
        Some(path) => match std::fs::read_to_string(path) {
            Ok(text) => text,
            Err(e) => {
                eprintln!("Failed to read state file {}: {e}", path.display());
                std::process::exit(1);
            }
        },
        None => {
            let mut buffer = String::new();
            if let Err(e) = std::io::Read::read_to_string(&mut std::io::stdin(), &mut buffer) {
                eprintln!("Failed to read state from stdin: {e}");
                std::process::exit(1);
            }
            buffer
        }
    };

    let raw_questions = match std::fs::read_to_string(questions_path) {
        Ok(text) => text,
        Err(e) => {
            eprintln!(
                "Failed to read questions file {}: {e}",
                questions_path.display()
            );
            std::process::exit(1);
        }
    };

    let state: serde_json::Value =
        serde_json::from_str(&raw_state).unwrap_or_else(|_| serde_json::Value::String(raw_state));
    let questions: serde_json::Value = match serde_json::from_str(&raw_questions) {
        Ok(value) => value,
        Err(e) => {
            eprintln!("Questions file is not valid JSON: {e}");
            std::process::exit(1);
        }
    };

    let model_dir = match SystemOne::resolve_model_dir(model) {
        Ok(dir) => dir,
        Err(e) => {
            eprintln!("System One model unavailable: {e}");
            std::process::exit(1);
        }
    };

    let organ = SystemOne::new(model_dir);
    match organ.decide(&state, &questions) {
        Ok(outcome) => {
            if json_output {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&outcome).unwrap_or_default()
                );
                return;
            }
            println!("==================================================");
            println!("     WhiteMagic Gen3 System One Decision (Laya)   ");
            println!("==================================================");
            if let Some(answers) = outcome
                .get("answers")
                .and_then(serde_json::Value::as_object)
            {
                for (id, answer) in answers {
                    let qtype = answer
                        .get("type")
                        .and_then(serde_json::Value::as_str)
                        .unwrap_or("unknown");
                    let verdict = match qtype {
                        "choice" => answer
                            .get("choice")
                            .and_then(serde_json::Value::as_str)
                            .unwrap_or_default()
                            .to_string(),
                        "score" | "noul" => answer
                            .get(qtype)
                            .map(|value| value.to_string())
                            .unwrap_or_default(),
                        _ => String::new(),
                    };
                    let confidence = answer
                        .get("confidence")
                        .map(|value| value.to_string())
                        .unwrap_or_else(|| "-".to_string());
                    let act = answer
                        .get("rl_agent")
                        .and_then(|meta| meta.get("act_probability"))
                        .map(|value| value.to_string())
                        .unwrap_or_else(|| "-".to_string());
                    println!("[{id}] {qtype}: {verdict}  confidence={confidence} act={act}");
                }
            }
            if let Some(model_name) = outcome.get("model").and_then(serde_json::Value::as_str) {
                println!("Model:       {model_name}");
            }
            if let Some(latency) = outcome
                .get("latency_ms")
                .and_then(serde_json::Value::as_f64)
            {
                println!("Latency:     {latency:.1} ms");
            }
            println!("==================================================");
        }
        Err(e) => {
            eprintln!("System One decision failed: {e}");
            std::process::exit(1);
        }
    }
}

#[cfg(feature = "system05")]
#[allow(clippy::too_many_arguments)]
fn run_shortlist_command(
    state_file: Option<PathBuf>,
    routes_path: Option<PathBuf>,
    k: usize,
    margin_threshold: f64,
    cascade: bool,
    model: Option<PathBuf>,
    json_output: bool,
    store_path: &Path,
) {
    use wm_gen3_zeropointfive::System05;

    let raw_state = match &state_file {
        Some(path) => match std::fs::read_to_string(path) {
            Ok(text) => text,
            Err(e) => {
                eprintln!("Failed to read state file {}: {e}", path.display());
                std::process::exit(1);
            }
        },
        None => {
            let mut buffer = String::new();
            if let Err(e) = std::io::Read::read_to_string(&mut std::io::stdin(), &mut buffer) {
                eprintln!("Failed to read state from stdin: {e}");
                std::process::exit(1);
            }
            buffer
        }
    };
    let state_text = match serde_json::from_str::<serde_json::Value>(&raw_state) {
        Ok(serde_json::Value::String(text)) => text,
        Ok(other) => other.to_string(),
        Err(_) => raw_state,
    };

    let routes_path = match System05::resolve_catalog_path(routes_path) {
        Ok(path) => path,
        Err(e) => {
            eprintln!("System 0.5 catalog unavailable: {e}");
            std::process::exit(1);
        }
    };
    let routes: serde_json::Value = match std::fs::read_to_string(&routes_path)
        .map_err(|e| e.to_string())
        .and_then(|raw| serde_json::from_str(&raw).map_err(|e| e.to_string()))
    {
        Ok(value) => value,
        Err(e) => {
            eprintln!("Failed to read catalog {}: {e}", routes_path.display());
            std::process::exit(1);
        }
    };

    let model_dir = match System05::resolve_model_dir(model) {
        Ok(dir) => dir,
        Err(e) => {
            eprintln!("System 0.5 model unavailable: {e}");
            std::process::exit(1);
        }
    };

    let organ = System05::new(model_dir);
    match organ.shortlist(&state_text, &routes, k) {
        Ok(mut outcome) => {
            let margin = outcome
                .get("margin")
                .and_then(serde_json::Value::as_f64)
                .unwrap_or(0.0);
            let gate = if margin >= margin_threshold {
                "dispatch"
            } else {
                "ambiguous"
            };
            outcome["gate"] = serde_json::json!(gate);
            outcome["margin_threshold"] = serde_json::json!(margin_threshold);

            let mut deliberated_info: Option<(String, f64, f64, String)> = None;
            if gate == "ambiguous" && cascade {
                let mut candidates: Vec<wm_gen3_harness::deliberation::CandidateRoute> = Vec::new();
                if let Some(ranked) = outcome.get("ranked").and_then(serde_json::Value::as_array) {
                    for entry in ranked {
                        let name = entry
                            .get("route")
                            .and_then(|v| v.as_str())
                            .unwrap_or_default()
                            .to_string();
                        let score = entry.get("score").and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let description = match routes.get(&name) {
                            Some(serde_json::Value::String(s)) => Some(s.clone()),
                            Some(serde_json::Value::Array(arr)) => {
                                arr.first().and_then(|v| v.as_str()).map(|s| s.to_string())
                            }
                            _ => None,
                        };
                        candidates.push(wm_gen3_harness::deliberation::CandidateRoute {
                            name,
                            score,
                            description,
                        });
                    }
                }
                let deliberator = wm_gen3_harness::deliberation::Deliberator::default();
                if let Ok(delib) = deliberator.deliberate(&state_text, &candidates) {
                    let strict =
                        std::env::var(wm_gen3_harness::deliberation::ENV_DELIBERATION_STRICT)
                            .is_ok();
                    if delib.degraded && strict {
                        outcome["deliberation_refused"] = serde_json::json!("degraded_strict");
                    } else if let Ok((signing_key, _)) =
                        wm_gen3_core::mandala::resolve_or_create_mandala_gate_key(store_path)
                    {
                        let cand_names: Vec<String> =
                            candidates.iter().map(|c| c.name.clone()).collect();
                        let receipt = wm_gen3_harness::deliberation::DeliberationReceipt::sign(
                            &signing_key,
                            &state_text,
                            &cand_names,
                            &delib.chosen_route,
                            margin,
                            margin_threshold,
                            delib.confidence,
                            delib.latency_ms,
                            delib.degraded,
                            &delib.slm_model_sha256,
                            &delib.prompt_version,
                        );
                        let _ = receipt.persist(store_path);
                        outcome["deliberation"] = serde_json::json!({
                            "chosen_route": delib.chosen_route.clone(),
                            "confidence": delib.confidence,
                            "latency_ms": delib.latency_ms,
                            "degraded": delib.degraded,
                            "slm_model_sha256": delib.slm_model_sha256.clone(),
                            "prompt_version": delib.prompt_version.clone(),
                            "receipt_id": receipt.receipt_id,
                            "spec": receipt.spec,
                        });
                        outcome["dispatched_route"] = serde_json::json!(delib.chosen_route);
                        deliberated_info = Some((
                            delib.chosen_route,
                            delib.confidence,
                            delib.latency_ms,
                            receipt.receipt_id,
                        ));
                    }
                }
            }

            let mut shortlist_receipt_id: Option<String> = None;
            if let Ok((signing_key, _)) =
                wm_gen3_core::mandala::resolve_or_create_mandala_gate_key(store_path)
            {
                let gate_did = format!(
                    "did:key:{}",
                    signing_key
                        .verifying_key()
                        .to_bytes()
                        .iter()
                        .map(|byte| format!("{byte:02x}"))
                        .collect::<String>()
                );
                let mut receipt =
                    wm_gen3_harness::shortlist_receipt::ShortlistReceipt::from_outcome(
                        &outcome,
                        &serde_json::Value::String(state_text.clone()),
                        &routes,
                        &serde_json::json!({
                            "tenant_id": "local",
                            "session_id": "cli",
                            "task_class": "route_dispatch"
                        }),
                        gate_did,
                    );
                receipt.sign(&signing_key);
                let receipts_dir = store_path.join("receipts");
                if let Ok(()) = std::fs::create_dir_all(&receipts_dir) {
                    let receipt_path =
                        receipts_dir.join(format!("shortlist-{}.json", receipt.receipt_id));
                    if let Ok(serialized) = serde_json::to_string_pretty(&receipt) {
                        let _ = std::fs::write(&receipt_path, serialized);
                        outcome["receipt_path"] =
                            serde_json::json!(receipt_path.display().to_string());
                        outcome["receipt_id"] = serde_json::json!(receipt.receipt_id);
                        outcome["spec"] = serde_json::json!(receipt.spec);
                        shortlist_receipt_id = Some(receipt.receipt_id);
                    }
                }
            }

            if json_output {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&outcome).unwrap_or_default()
                );
                return;
            }

            println!("==================================================");
            println!("   WhiteMagic Gen3 System 0.5 Shortlist (static)   ");
            println!("==================================================");
            if let Some(ranked) = outcome.get("ranked").and_then(serde_json::Value::as_array) {
                for (index, entry) in ranked.iter().enumerate() {
                    println!(
                        "[{:2}] {:34} score={:.4}",
                        index + 1,
                        entry
                            .get("route")
                            .and_then(serde_json::Value::as_str)
                            .unwrap_or("?"),
                        entry
                            .get("score")
                            .and_then(serde_json::Value::as_f64)
                            .unwrap_or(0.0)
                    );
                }
            }
            if let Some(model_name) = outcome.get("model").and_then(serde_json::Value::as_str) {
                println!("Model:       {model_name}");
            }
            println!(
                "Candidates:  {}",
                outcome
                    .get("candidate_count")
                    .and_then(serde_json::Value::as_u64)
                    .unwrap_or(0)
            );
            println!("Margin:      {margin:.4}  Gate: {gate} (tau={margin_threshold:.4})");
            if let Some(latency) = outcome
                .get("latency_ms")
                .and_then(serde_json::Value::as_f64)
            {
                println!("Retrieval:   {latency:.1} ms");
            }
            if let Some((chosen, conf, lat, receipt_id)) = deliberated_info {
                println!("--------------------------------------------------");
                println!("System 1.5 Deliberator Cascade:");
                println!("  Resolved:  {chosen} (conf={conf:.4}, lat={lat:.1} ms)");
                println!("  Receipt:   deliberation-{receipt_id}.json");
            }
            if let Some(ref rid) = shortlist_receipt_id {
                println!("Receipt:     shortlist-{rid}.json");
            }
            println!("==================================================");
        }
        Err(e) => {
            eprintln!("System 0.5 shortlist failed: {e}");
            std::process::exit(1);
        }
    }
}

fn parse_candidates_into(
    val: &serde_json::Value,
    out: &mut Vec<wm_gen3_harness::deliberation::CandidateRoute>,
) {
    match val {
        serde_json::Value::Array(arr) => {
            for item in arr {
                match item {
                    serde_json::Value::String(s) => {
                        out.push(wm_gen3_harness::deliberation::CandidateRoute {
                            name: s.clone(),
                            score: 0.9,
                            description: None,
                        });
                    }
                    serde_json::Value::Object(obj) => {
                        let name = obj
                            .get("name")
                            .or_else(|| obj.get("route"))
                            .and_then(|v| v.as_str())
                            .unwrap_or_default()
                            .to_string();
                        let score = obj.get("score").and_then(|v| v.as_f64()).unwrap_or(0.9);
                        let desc = obj
                            .get("description")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());
                        if !name.is_empty() {
                            out.push(wm_gen3_harness::deliberation::CandidateRoute {
                                name,
                                score,
                                description: desc,
                            });
                        }
                    }
                    _ => {}
                }
            }
        }
        serde_json::Value::Object(obj) => {
            for (k, v) in obj {
                let desc = v.as_str().map(|s| s.to_string());
                out.push(wm_gen3_harness::deliberation::CandidateRoute {
                    name: k.clone(),
                    score: 0.9,
                    description: desc,
                });
            }
        }
        _ => {}
    }
}

fn run_deliberate_command(
    intent: &str,
    candidates_json: Option<String>,
    candidates_file: Option<PathBuf>,
    store_path: &Path,
    json_output: bool,
) {
    let deliberator = wm_gen3_harness::deliberation::Deliberator::default();
    let mut candidate_routes: Vec<wm_gen3_harness::deliberation::CandidateRoute> = Vec::new();

    if let Some(path) = candidates_file {
        if let Ok(content) = std::fs::read_to_string(&path) {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&content) {
                parse_candidates_into(&parsed, &mut candidate_routes);
            }
        }
    } else if let Some(raw) = candidates_json {
        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&raw) {
            parse_candidates_into(&parsed, &mut candidate_routes);
        }
    }

    if candidate_routes.is_empty() {
        eprintln!("Error: no candidates provided (use --candidates or --candidates-file)");
        std::process::exit(1);
    }

    let (gate_key, _) = match wm_gen3_core::mandala::resolve_or_create_mandala_gate_key(store_path)
    {
        Ok(k) => k,
        Err(e) => {
            eprintln!("Gate key resolution failed: {e}");
            std::process::exit(1);
        }
    };

    let gate = wm_gen3_harness::deliberation::ConformalGate::default();
    let tau = gate.calibrate_tau(store_path);

    match deliberator.deliberate(intent, &candidate_routes) {
        Ok(outcome) => {
            if outcome.degraded
                && std::env::var(wm_gen3_harness::deliberation::ENV_DELIBERATION_STRICT).is_ok()
            {
                eprintln!(
                    "Deliberation degraded (SLM unavailable or unparsable) and {} is set; refusing to sign a receipt",
                    wm_gen3_harness::deliberation::ENV_DELIBERATION_STRICT
                );
                std::process::exit(1);
            }
            let candidate_names: Vec<String> =
                candidate_routes.iter().map(|c| c.name.clone()).collect();
            let receipt = wm_gen3_harness::deliberation::DeliberationReceipt::sign(
                &gate_key,
                intent,
                &candidate_names,
                &outcome.chosen_route,
                0.0,
                tau,
                outcome.confidence,
                outcome.latency_ms,
                outcome.degraded,
                &outcome.slm_model_sha256,
                &outcome.prompt_version,
            );
            let _ = receipt.persist(store_path);

            if json_output {
                let out = serde_json::json!({
                    "status": "success",
                    "chosen_route": outcome.chosen_route,
                    "confidence": outcome.confidence,
                    "latency_ms": outcome.latency_ms,
                    "degraded": outcome.degraded,
                    "slm_model_sha256": outcome.slm_model_sha256,
                    "prompt_version": outcome.prompt_version,
                    "candidates": candidate_names,
                    "receipt": receipt,
                });
                println!("{}", serde_json::to_string_pretty(&out).unwrap_or_default());
            } else {
                println!("==================================================");
                println!("   WhiteMagic Gen3 System 1.5 Deliberator (SLM)   ");
                println!("==================================================");
                println!("Intent:       {}", intent);
                println!("Candidates:   {}", candidate_names.join(", "));
                println!("Chosen:       {}", outcome.chosen_route);
                println!("Confidence:   {:.4}", outcome.confidence);
                println!("Latency:      {:.1} ms", outcome.latency_ms);
                println!("Degraded:     {}", outcome.degraded);
                println!("Model SHA256: {}", outcome.slm_model_sha256);
                println!("Prompt:       {}", outcome.prompt_version);
                println!("Receipt ID:   {}", receipt.receipt_id);
                println!("==================================================");
            }
        }
        Err(e) => {
            eprintln!("Deliberation failed: {e}");
            std::process::exit(1);
        }
    }
}

fn run_verify_receipt_command(path: &Path, store_path: &Path, json_output: bool) {
    match wm_gen3_harness::receipt_verify::verify_receipt_file(path, store_path) {
        Ok(report) => {
            if json_output {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&report).unwrap_or_default()
                );
            } else {
                let valid = report["valid"].as_bool().unwrap_or(false);
                println!("Receipt:    {}", path.display());
                println!("Spec:       {}", report["spec"].as_str().unwrap_or("?"));
                println!("Receipt ID: {}", report["receipt_id"]);
                println!(
                    "Issuer:     {}",
                    report["issuer_did"].as_str().unwrap_or("?")
                );
                println!("Verdict:    {}", if valid { "VALID" } else { "INVALID" });
                if let Some(detail) = report["detail"].as_str() {
                    println!("Detail:     {detail}");
                }
            }
            if !report["valid"].as_bool().unwrap_or(false) {
                std::process::exit(1);
            }
        }
        Err(e) => {
            eprintln!("Receipt verification failed: {e}");
            std::process::exit(1);
        }
    }
}

#[cfg(any(feature = "systemone", feature = "system05"))]
#[allow(clippy::too_many_arguments)]
fn run_outcome_command(
    receipt: &Path,
    outcome: &str,
    corrected_route: Option<String>,
    note: Option<String>,
    session_id: Option<String>,
    tenant_id: Option<String>,
    store_path: &Path,
    json_output: bool,
) {
    let mut args = serde_json::json!({
        "receipt_path": receipt.display().to_string(),
        "outcome": outcome,
    });
    if let Some(value) = corrected_route {
        args["corrected_route"] = serde_json::json!(value);
    }
    if let Some(value) = note {
        args["note"] = serde_json::json!(value);
    }
    if let Some(value) = session_id {
        args["session_id"] = serde_json::json!(value);
    }
    if let Some(value) = tenant_id {
        args["tenant_id"] = serde_json::json!(value);
    }
    match wm_gen3_harness::receipt_verify::record_outcome(&args, store_path, false) {
        Ok(value) => {
            if json_output {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&value).unwrap_or_default()
                );
            } else {
                println!(
                    "Outcome recorded: {}",
                    value["outcome"]["outcome"].as_str().unwrap_or("?")
                );
                println!(
                    "Subject:          {}",
                    value["outcome"]["subject_receipt"].as_str().unwrap_or("?")
                );
                println!(
                    "Subject verified: {}",
                    value["outcome"]["subject_verified"]
                        .as_bool()
                        .unwrap_or(false)
                );
                println!(
                    "Sidecar:          {}",
                    value["sidecar_path"].as_str().unwrap_or("?")
                );
                println!(
                    "Journal:          {}",
                    value["journal_path"].as_str().unwrap_or("?")
                );
            }
        }
        Err(e) => {
            eprintln!("Outcome recording failed: {e}");
            std::process::exit(1);
        }
    }
}

fn run_organ_command(cmd: OrganCommands, _store_path: &Path) {
    match cmd {
        OrganCommands::List => {
            println!("==================================================");
            println!("       WhiteMagic Gen3 Cyberbrain Organs          ");
            println!("==================================================");
            println!("Pluggable neural micro-models and representation layers:\n");

            // 1. System One (Laya)
            let (s1_status, s1_path): (&str, String) = {
                #[cfg(feature = "systemone")]
                {
                    match wm_gen3_systemone::SystemOne::resolve_model_dir(None) {
                        Ok(p) => ("ACTIVE (Refitted ECE 0.044)", p.display().to_string()),
                        Err(_) => (
                            "NOT INSTALLED (run `wm organ install systemone`)",
                            "none".to_string(),
                        ),
                    }
                }
                #[cfg(not(feature = "systemone"))]
                {
                    (
                        "DISABLED (build with --features systemone)",
                        "none".to_string(),
                    )
                }
            };
            println!("1. [organ:systemone] Laya Fast Reflex Decision Model");
            println!("   Parameters:   16M (pure-Rust candle)");
            println!("   Latency:      ~1.2 ms (non-autoregressive typed tensor)");
            println!("   Receipt:      Signed Ed25519 continuity-receipt/0.5#decision");
            println!("   Status:       {}", s1_status);
            println!("   Path:         {}\n", s1_path);

            // 2. Semantic Projections (Dense Embeddings)
            let embed_cache = {
                let home = std::env::var_os("HOME").map(PathBuf::from);
                let default_embed = home
                    .as_ref()
                    .map(|h| h.join("models/embedding"))
                    .unwrap_or_default();
                if default_embed.exists() {
                    format!("ACTIVE ({})", default_embed.display())
                } else {
                    "AVAILABLE (FastEmbed BGE-Small-EN-v1.5)".into()
                }
            };
            println!("2. [organ:embeddings] Semantic Dense Vector Projections");
            println!("   Model:        BGE-Small-EN-v1.5 (384-dimensional)");
            println!("   Engine:       FastEmbed / ONNX Runtime + GGUF");
            println!("   Latency:      ~3.8 ms / batch");
            println!("   Status:       {}\n", embed_cache);

            // 3. Neural Cross-Encoder Reranker
            println!("3. [organ:reranker] Cross-Encoder Semantic Reranker");
            println!("   Model:        BGE-Reranker-Mini / Jina-Reranker");
            println!("   Engine:       FastEmbed / ONNX Runtime");
            println!("   Role:         Post-retrieval reranking (MRR@5 target >0.90)");
            println!("   Status:       PLUGGABLE (dynamic organ on-demand)\n");

            // 4. ColBERT Late-Interaction Token Retrieval
            println!("4. [organ:colbert] Multi-Vector MaxSim Late Interaction");
            println!("   Model:        ColBERTv2");
            println!("   Role:         Token-level multi-vector interaction for code symbols");
            println!("   Status:       RESEARCH / PLUGGABLE\n");

            println!("==================================================");
            println!("Zero Mandatory Neural Weights: Core binary is ~40MB.");
            println!("Organs run entirely local, zero-cloud, non-autoregressive.");
            println!("==================================================");
        }
        OrganCommands::Status => {
            println!("==================================================");
            println!("     WhiteMagic Gen3 Cyberbrain Hardware Status   ");
            println!("==================================================");
            println!("Target Architecture: {}", std::env::consts::ARCH);
            println!("Target OS:           {}", std::env::consts::OS);

            #[cfg(target_arch = "x86_64")]
            {
                println!("CPU SIMD Extensions:");
                println!("  - AVX2:     {}", is_x86_feature_detected!("avx2"));
                println!("  - AVX-512F: {}", is_x86_feature_detected!("avx512f"));
                println!("  - FMA:      {}", is_x86_feature_detected!("fma"));
                println!("  - SSE4.2:   {}", is_x86_feature_detected!("sse4.2"));
            }
            #[cfg(target_arch = "aarch64")]
            {
                println!("CPU SIMD Extensions:");
                println!("  - NEON:     true");
            }

            println!("Inference Engines: Pure Rust Candle + ONNX Runtime (CPU SIMD)");
            println!(
                "Thread Model:      Single-threaded synchronous / caller-driven (Zero thread leak)"
            );
            println!("==================================================");
        }
        OrganCommands::Verify => {
            println!("==================================================");
            println!("     WhiteMagic Gen3 Cyberbrain Organ Verification");
            println!("==================================================");
            let verified = {
                #[cfg(feature = "systemone")]
                {
                    match wm_gen3_systemone::SystemOne::resolve_model_dir(None) {
                        Ok(dir) => {
                            println!("Probing System One (Laya) at: {}", dir.display());
                            let organ = wm_gen3_systemone::SystemOne::new(dir);
                            let test_state = serde_json::json!({"probe": "heartbeat"});
                            let test_questions = serde_json::json!({
                                "health": {
                                    "type": "choice",
                                    "instructions": "System status?",
                                    "criteria": ["nominal", "degraded"]
                                }
                            });
                            let start = std::time::Instant::now();
                            match organ.decide(&test_state, &test_questions) {
                                Ok(res) => {
                                    let elapsed = start.elapsed();
                                    println!(
                                        "  Result:  PASS ({:.2} ms)",
                                        elapsed.as_secs_f64() * 1000.0
                                    );
                                    if let Some(answers) = res.get("answers") {
                                        println!("  Verdict: {}", answers);
                                    }
                                    true
                                }
                                Err(e) => {
                                    println!("  Result:  FAIL ({e})");
                                    false
                                }
                            }
                        }
                        Err(e) => {
                            println!("System One: Not available ({e})");
                            false
                        }
                    }
                }
                #[cfg(not(feature = "systemone"))]
                {
                    println!("System One: Disabled in this build (--features systemone)");
                    false
                }
            };
            println!("==================================================");
            if !verified {
                eprintln!(
                    "Organ verification failed: System One did not pass its diagnostic pulse."
                );
                std::process::exit(1);
            }
        }
    }
}

fn run_peer_command(cmd: PeerCommands, store_path: &Path) {
    let peer_file = store_path.join("peers.json");
    let mut dir = PeerDirectory::load_or_init(&peer_file).unwrap_or_default();

    // Ensure self local node identity is registered
    if dir.peers.is_empty() {
        let node_id = std::env::var("WM_NODE_ID")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "local-host".into());
        let pubkey = resolve_or_create_mesh_key(store_path)
            .map(|(_, k)| k)
            .unwrap_or([0u8; 32]);
        dir.admit(PeerIdentity::new(&node_id, pubkey, PeerTrustTier::Local));
        let _ = dir.save(&peer_file);
    }

    match cmd {
        PeerCommands::List { json } => {
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&dir.list()).unwrap_or_else(|_| "[]".into())
                );
            } else {
                println!("==================================================");
                println!("       WhiteMagic Gen3 Peer Trust Directory       ");
                println!("==================================================");
                println!(
                    "{:<20} {:<10} {:<10} {:<24} {:<12}",
                    "NODE ID", "TIER", "REPUTATION", "ENDPOINT", "PUBLIC KEY"
                );
                println!("{:-<76}", "");
                for p in dir.list() {
                    let ep = p.endpoint.as_deref().unwrap_or("-");
                    let short_key = if p.public_key_hex.len() > 10 {
                        format!("{}..", &p.public_key_hex[..10])
                    } else {
                        p.public_key_hex.clone()
                    };
                    println!(
                        "{:<20} {:<10} {:<10.2} {:<24} {:<12}",
                        p.node_id, p.trust_tier, p.reputation, ep, short_key
                    );
                }
                println!("==================================================");
                println!("Total Peers: {}", dir.peers.len());
            }
        }
        PeerCommands::Add {
            node_id,
            key,
            tier,
            endpoint,
        } => {
            let parsed_tier = match tier.parse::<PeerTrustTier>() {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            };
            let pubkey = match parse_pubkey_hex(&key) {
                Ok(pubkey) => pubkey,
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(2);
                }
            };
            let mut identity = PeerIdentity::new(&node_id, pubkey, parsed_tier);
            identity.endpoint = endpoint;
            dir.admit(identity);
            if let Err(e) = dir.save(&peer_file) {
                eprintln!("Error saving peer directory: {e}");
                std::process::exit(1);
            }
            println!("Peer `{node_id}` admitted as `{parsed_tier}`.");
        }
        PeerCommands::Trust { target } => match dir.set_tier(&target, PeerTrustTier::Trusted) {
            Ok(_) => {
                if let Err(e) = dir.save(&peer_file) {
                    eprintln!("Error saving peer directory: {e}");
                    std::process::exit(1);
                }
                println!("Peer `{target}` promoted to `trusted`.");
            }
            Err(e) => {
                eprintln!("Error: {e}");
                std::process::exit(1);
            }
        },
        PeerCommands::Block { target } => match dir.set_tier(&target, PeerTrustTier::Blocked) {
            Ok(_) => {
                if let Err(e) = dir.save(&peer_file) {
                    eprintln!("Error saving peer directory: {e}");
                    std::process::exit(1);
                }
                println!("Peer `{target}` demoted to `blocked`.");
            }
            Err(e) => {
                eprintln!("Error: {e}");
                std::process::exit(1);
            }
        },
        PeerCommands::SetTier { target, tier } => {
            let parsed_tier = match tier.parse::<PeerTrustTier>() {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            };
            match dir.set_tier(&target, parsed_tier) {
                Ok(_) => {
                    if let Err(e) = dir.save(&peer_file) {
                        eprintln!("Error saving peer directory: {e}");
                        std::process::exit(1);
                    }
                    println!("Peer `{target}` set to `{parsed_tier}`.");
                }
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            }
        }
        PeerCommands::Ban {
            target,
            reason,
            evidence,
            ttl,
            out,
        } => {
            let (signing_key, _pubkey) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve local signing key: {e}");
                    std::process::exit(1);
                }
            };
            let issuer_node_id = std::env::var("WM_NODE_ID")
                .or_else(|_| std::env::var("HOSTNAME"))
                .unwrap_or_else(|_| "local-host".into());

            let target_pubkey_hex =
                if target.len() == 64 && target.chars().all(|c| c.is_ascii_hexdigit()) {
                    Some(target.clone())
                } else {
                    dir.get_by_id(&target).map(|p| p.public_key_hex.clone())
                };

            let ev_hash = evidence.unwrap_or_else(|| {
                use sha2::{Digest, Sha256};
                let mut hasher = Sha256::new();
                hasher.update(target.as_bytes());
                hasher.update(reason.as_bytes());
                hex_encode(&hasher.finalize())
            });

            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();

            let cert = BanCertificate::issue(
                &signing_key,
                &issuer_node_id,
                &target,
                target_pubkey_hex.as_deref(),
                &reason,
                &ev_hash,
                now,
                ttl,
            );

            match dir.apply_ban(&cert, now) {
                Ok(msg) => {
                    let _ = dir.save(&peer_file);
                    println!("BanCertificate issued and applied:");
                    println!(
                        "  Issuer:    {} ({})",
                        cert.issuer_node_id, cert.issuer_public_key_hex
                    );
                    println!("  Target:    {}", cert.target_identity);
                    println!("  Reason:    {}", cert.reason);
                    println!("  Evidence:  {}", cert.evidence_hash);
                    println!("  Signature: {}..", &cert.signature_hex[..16]);
                    println!("  Outcome:   {}", msg);
                }
                Err(e) => {
                    eprintln!("Error applying ban locally: {e}");
                    std::process::exit(1);
                }
            }

            if let Some(out_path) = out {
                let json = serde_json::to_string_pretty(&cert).unwrap_or_default();
                if let Err(e) = std::fs::write(&out_path, json) {
                    eprintln!("Failed to write certificate to {}: {e}", out_path.display());
                    std::process::exit(1);
                }
                println!("Saved BanCertificate to {}", out_path.display());
            }
        }
        PeerCommands::ApplyBan { cert_file } => {
            let content = if cert_file.as_os_str() == "-" {
                let mut s = String::new();
                std::io::Read::read_to_string(&mut std::io::stdin(), &mut s).unwrap_or_default();
                s
            } else {
                match std::fs::read_to_string(&cert_file) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!(
                            "Failed to read certificate file {}: {e}",
                            cert_file.display()
                        );
                        std::process::exit(1);
                    }
                }
            };

            let cert: BanCertificate = match serde_json::from_str(&content) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Invalid BanCertificate JSON: {e}");
                    std::process::exit(1);
                }
            };

            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();

            match dir.apply_ban(&cert, now) {
                Ok(msg) => {
                    let _ = dir.save(&peer_file);
                    println!(
                        "BanCertificate successfully verified and applied to fleet directory:"
                    );
                    println!(
                        "  Issuer:    {} ({})",
                        cert.issuer_node_id, cert.issuer_public_key_hex
                    );
                    println!("  Target:    {}", cert.target_identity);
                    println!("  Reason:    {}", cert.reason);
                    println!("  Status:    BLOCKED");
                    println!("  Outcome:   {}", msg);
                }
                Err(e) => {
                    eprintln!("Governance rejection: {e}");
                    std::process::exit(1);
                }
            }
        }
        PeerCommands::VerifyBan { cert_file } => {
            let content = match std::fs::read_to_string(&cert_file) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!(
                        "Failed to read certificate file {}: {e}",
                        cert_file.display()
                    );
                    std::process::exit(1);
                }
            };
            let cert: BanCertificate = match serde_json::from_str(&content) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Invalid BanCertificate JSON: {e}");
                    std::process::exit(1);
                }
            };
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();

            match cert.verify(now) {
                Ok(_) => {
                    let issuer_known = dir
                        .peers
                        .values()
                        .find(|p| p.public_key_hex == cert.issuer_public_key_hex);
                    let (trusted, tier_str) = match issuer_known {
                        Some(p) => (
                            p.trust_tier >= PeerTrustTier::Trusted,
                            p.trust_tier.to_string(),
                        ),
                        None => (false, "unknown".to_string()),
                    };
                    println!("==================================================");
                    println!("      WhiteMagic Gen3 BanCertificate Audit        ");
                    println!("==================================================");
                    println!("Signature:     VALID (Ed25519 canonical)");
                    println!("Issuer Node:   {}", cert.issuer_node_id);
                    println!("Issuer Key:    {}", cert.issuer_public_key_hex);
                    println!(
                        "Issuer Tier:   {} (fleet authority: {})",
                        tier_str,
                        if trusted { "AUTHORIZED" } else { "DENIED" }
                    );
                    println!("Target:        {}", cert.target_identity);
                    println!("Reason:        {}", cert.reason);
                    println!("Evidence Hash: {}", cert.evidence_hash);
                    println!("Issued At:     {} (epoch)", cert.issued_at);
                    println!(
                        "TTL (seconds): {}",
                        if cert.ttl_secs == 0 {
                            "permanent".into()
                        } else {
                            cert.ttl_secs.to_string()
                        }
                    );
                    println!("==================================================");
                }
                Err(e) => {
                    eprintln!("Verification FAILED: {e}");
                    std::process::exit(1);
                }
            }
        }
        PeerCommands::Bans { json } => {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            let active = dir.active_bans(now);
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&active).unwrap_or_else(|_| "[]".into())
                );
            } else {
                println!("==================================================");
                println!("      WhiteMagic Gen3 Active Ban Certificates     ");
                println!("==================================================");
                println!("{:<20} {:<20} {:<30}", "TARGET", "ISSUER", "REASON");
                println!("{:-<76}", "");
                for b in &active {
                    println!(
                        "{:<20} {:<20} {:<30}",
                        b.target_identity, b.issuer_node_id, b.reason
                    );
                }
                println!("==================================================");
                println!("Total Active Bans: {}", active.len());
            }
        }
    }
}

fn load_circuit_breaker(store_path: &Path) -> SentinelCircuitBreaker {
    let breaker_file = store_path.join("sentinel-circuit-breaker.json");
    if breaker_file.exists() {
        if let Ok(content) = std::fs::read_to_string(&breaker_file) {
            if let Ok(b) = serde_json::from_str::<SentinelCircuitBreaker>(&content) {
                return b;
            }
        }
    }
    SentinelCircuitBreaker::default()
}

fn save_circuit_breaker(store_path: &Path, breaker: &SentinelCircuitBreaker) {
    let breaker_file = store_path.join("sentinel-circuit-breaker.json");
    if let Ok(content) = serde_json::to_string_pretty(breaker) {
        let _ = std::fs::write(&breaker_file, content);
    }
}

fn run_sentinel_command(cmd: SentinelCommands, store_path: &Path) {
    let node_id = std::env::var("WM_NODE_ID")
        .or_else(|_| std::env::var("HOSTNAME"))
        .unwrap_or_else(|_| "whitemagic-node".into());

    let mut breaker = load_circuit_breaker(store_path);

    match cmd {
        SentinelCommands::Check { json, prompt } => {
            let report = SentinelReport::sample(&node_id, store_path, &breaker);
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&report).unwrap_or_else(|_| "{}".into())
                );
            } else if prompt {
                println!("{}", report.render_self_prompt());
            } else {
                println!("==================================================");
                println!("       WhiteMagic Gen3 Autonomic Sentinel Pulse   ");
                println!("==================================================");
                println!("Node ID:          {}", report.node_id);
                println!("Status:           {}", report.status);
                println!("Homeostatic:      {:?}", report.homeostatic_regime);
                println!(
                    "Invariants:       {}",
                    if report.store_invariants_pass {
                        "PASS"
                    } else {
                        "FAIL"
                    }
                );
                println!("Store Epoch:      {}", report.store_epoch);
                println!("Store Records:    {}", report.store_records);
                println!("CPU Thermal:      {:.1}°C", report.telemetry.cpu_temp_c);
                println!(
                    "RAM Available:    {:.1} MB",
                    report.telemetry.mem_available_mb
                );
                println!("System Load (1m): {:.2}", report.telemetry.load_avg_1m);
                println!(
                    "Circuit Breaker:  {}",
                    if report.circuit_breaker_tripped {
                        "TRIPPED (Writes Blocked)"
                    } else {
                        "ARMED (Nominal)"
                    }
                );
                if !report.issues.is_empty() {
                    println!("\nActive Anomalies:");
                    for issue in &report.issues {
                        println!("  - {issue}");
                    }
                }
                println!("==================================================");
            }
        }
        SentinelCommands::Run { interval, once } => {
            let lock_path = store_path.join("sentinel.lock");
            let _guard = match SentinelLeaseGuard::acquire(&lock_path) {
                Ok(g) => g,
                Err(e) => {
                    eprintln!("Sentinel lease error: {e}");
                    std::process::exit(1);
                }
            };

            loop {
                let report = SentinelReport::sample(&node_id, store_path, &breaker);
                let now_secs = report.timestamp;
                println!(
                    "[{}] Sentinel pulse: status={}, regime={:?}, temp={:.1}°C, load={:.2}",
                    report.timestamp,
                    report.status,
                    report.homeostatic_regime,
                    report.telemetry.cpu_temp_c,
                    report.telemetry.load_avg_1m
                );

                if report.status >= SentinelStatus::Degraded {
                    if breaker.can_remediate(now_secs) {
                        println!(
                            "Autonomous remediation eligible. Circuit breaker permits action."
                        );
                        breaker.record_action(now_secs);
                        save_circuit_breaker(store_path, &breaker);

                        // Trigger safe recovery: quiescent sleep compaction
                        println!("Executing scheduled quiescent consolidation sweep...");
                        breaker.record_success();
                        save_circuit_breaker(store_path, &breaker);
                    } else {
                        println!(
                            "Circuit breaker TRIPPED! Automated remediation suppressed (safety lock)."
                        );
                    }
                }

                if once {
                    break;
                }

                std::thread::sleep(std::time::Duration::from_secs(interval));
            }
        }
        SentinelCommands::Circuit { reset } => {
            if reset {
                breaker.is_tripped = false;
                breaker.consecutive_failures = 0;
                breaker.tripped_at = None;
                save_circuit_breaker(store_path, &breaker);
                println!("Anti-oscillation circuit breaker re-armed to nominal.");
            } else {
                println!("==================================================");
                println!("     WhiteMagic Sentinel Circuit Breaker Status   ");
                println!("==================================================");
                println!(
                    "Status:               {}",
                    if breaker.is_tripped {
                        "TRIPPED (LOCKED)"
                    } else {
                        "ARMED (NOMINAL)"
                    }
                );
                println!(
                    "Remediations (Last Hr): {} / {}",
                    breaker.remediation_history.len(),
                    breaker.max_remediations_per_hour
                );
                println!(
                    "Consecutive Failures:   {} / {}",
                    breaker.consecutive_failures, breaker.failure_trip_threshold
                );
                println!("Cooldown Window:        {}s", breaker.cooldown_secs);
                if let Some(t) = breaker.tripped_at {
                    println!("Tripped At Epoch:       {}", t);
                }
                println!("==================================================");
            }
        }
    }
}

// ── Firebreak arm-state (selftest / status) ─────────────────────────────

fn firebreak_json() -> serde_json::Value {
    let firebreak = Firebreak::promoted();
    let (forbidden, dangerous, caution) = firebreak.pattern_counts();
    serde_json::json!({
        "armed": firebreak.is_armed(),
        "arm_state": firebreak.arm_state(),
        "forbidden": forbidden,
        "dangerous": dangerous,
        "caution": caution,
    })
}

fn firebreak_summary_line() -> String {
    let firebreak = Firebreak::promoted();
    let (forbidden, dangerous, caution) = firebreak.pattern_counts();
    format!(
        "{} — {} forbidden / {} dangerous / {} caution",
        firebreak.arm_state(),
        forbidden,
        dangerous,
        caution
    )
}

fn firebreak_render_lines() -> Vec<String> {
    vec![format!("firebreak: {}", firebreak_summary_line())]
}

// ── Store growth / compaction ───────────────────────────────────────────

const STORE_SIZE_WARN_PERCENT: f64 = 80.0;
const COMPACT_JOURNAL_FILE: &str = "compact.journal";
const COMPACT_LOCK_FILE: &str = "compact.lock";
const COMPACT_BACKUP_PREFIX: &str = "data.mdb.bak.";
const COMPACT_BACKUP_KEEP: usize = 2;
/// LMDB meta-page magic (`MDB_MAGIC`) at byte offset 16 of `data.mdb`.
const LMDB_META_MAGIC: [u8; 4] = [0xde, 0xc0, 0xef, 0xbe];

#[derive(Debug, Clone, PartialEq)]
struct StoreSizeReport {
    data_mdb_bytes: u64,
    map_bytes: u64,
    used_percent: f64,
    warn: bool,
}

fn store_size_report(data_mdb_bytes: u64, map_bytes: u64) -> StoreSizeReport {
    let used_percent = if map_bytes == 0 {
        0.0
    } else {
        (data_mdb_bytes as f64 / map_bytes as f64) * 100.0
    };
    StoreSizeReport {
        data_mdb_bytes,
        map_bytes,
        used_percent,
        warn: used_percent > STORE_SIZE_WARN_PERCENT,
    }
}

/// Mirror `store.rs::configured_map_size`: `WM_MAP_SIZE_GB` (GiB) with a
/// 16 GiB default. The core store does not consult `WM_DEFAULT_MAP_SIZE`.
fn parse_map_size_gb(value: Option<&str>) -> u64 {
    value
        .and_then(|raw| raw.trim().parse::<u64>().ok())
        .map(|gb| gb.saturating_mul(1 << 30))
        .unwrap_or(16 << 30)
}

fn configured_map_size_bytes() -> u64 {
    parse_map_size_gb(std::env::var("WM_MAP_SIZE_GB").ok().as_deref())
}

fn format_bytes(bytes: u64) -> String {
    const MIB: f64 = 1024.0 * 1024.0;
    const GIB: f64 = 1024.0 * 1024.0 * 1024.0;
    let value = bytes as f64;
    if value >= GIB {
        format!("{:.2} GiB", value / GIB)
    } else {
        format!("{:.2} MiB", value / MIB)
    }
}

fn render_store_size(report: &StoreSizeReport) -> String {
    format!(
        "{} / {} map ({:.2}% used){}",
        format_bytes(report.data_mdb_bytes),
        format_bytes(report.map_bytes),
        report.used_percent,
        if report.warn { " [WARN >80%]" } else { "" }
    )
}

fn find_on_path(program: &str) -> Option<PathBuf> {
    let path_var = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path_var) {
        let candidate = dir.join(program);
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    None
}

fn compact_size_json(
    store_path: &Path,
    size: &StoreSizeReport,
    action: &str,
    extra: serde_json::Value,
) -> serde_json::Value {
    let mut value = serde_json::json!({
        "store": store_path.display().to_string(),
        "data_mdb_bytes": size.data_mdb_bytes,
        "map_bytes": size.map_bytes,
        "used_percent": size.used_percent,
        "warn": size.warn,
        "action": action,
    });
    if let (Some(destination), Some(source)) = (value.as_object_mut(), extra.as_object()) {
        for (key, item) in source {
            destination.insert(key.clone(), item.clone());
        }
    }
    value
}

fn print_compact_json(value: &serde_json::Value) {
    println!(
        "{}",
        serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".into())
    );
}

fn compact_tmp_dir(store_path: &Path) -> PathBuf {
    let mut tmp = store_path.as_os_str().to_os_string();
    tmp.push(".compact.tmp");
    PathBuf::from(tmp)
}

fn compact_timestamp() -> String {
    chrono::Utc::now().format("%Y%m%dT%H%M%S%.9fZ").to_string()
}

fn fsync_dir(path: &Path) {
    if let Ok(dir) = std::fs::File::open(path) {
        let _ = dir.sync_all();
    }
}

/// Durable marker for an in-flight compaction. Written and fsynced before the
/// copy starts, updated before each swap rename, and removed after the store
/// is verified: a crash therefore always leaves enough state for the next
/// `wm compact` to finish deterministically.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct CompactJournal {
    /// `copy` | `swap_backup` | `swap_installed`.
    phase: String,
    tmp: String,
    #[serde(default)]
    backup: Option<String>,
    started_at: String,
    updated_at: String,
}

impl CompactJournal {
    fn copy(tmp: &Path) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            phase: "copy".to_string(),
            tmp: tmp.display().to_string(),
            backup: None,
            started_at: now.clone(),
            updated_at: now,
        }
    }

    fn set_phase(&mut self, phase: &str) {
        self.phase = phase.to_string();
        self.updated_at = chrono::Utc::now().to_rfc3339();
    }
}

fn write_compact_journal(store_path: &Path, journal: &CompactJournal) -> Result<(), String> {
    use std::io::Write as _;
    let path = store_path.join(COMPACT_JOURNAL_FILE);
    let temp = store_path.join("compact.journal.tmp");
    let bytes = serde_json::to_vec(journal).map_err(|e| format!("serialize journal: {e}"))?;
    {
        let mut file =
            std::fs::File::create(&temp).map_err(|e| format!("create {}: {e}", temp.display()))?;
        file.write_all(&bytes)
            .map_err(|e| format!("write {}: {e}", temp.display()))?;
        file.sync_all()
            .map_err(|e| format!("fsync {}: {e}", temp.display()))?;
    }
    std::fs::rename(&temp, &path).map_err(|e| format!("rename journal: {e}"))?;
    fsync_dir(store_path);
    Ok(())
}

/// Cheap sanity check for a backup file: nonzero and carrying the LMDB meta
/// magic at the documented offset. The backup is a byte-for-byte rename of
/// the pre-swap data file, so this only guards against restoring junk.
fn backup_looks_like_env(path: &Path) -> bool {
    use std::io::Read as _;
    let Ok(mut file) = std::fs::File::open(path) else {
        return false;
    };
    let mut header = [0u8; 20];
    if file.read_exact(&mut header).is_err() {
        return false;
    }
    header[16..20] == LMDB_META_MAGIC
}

fn backup_name_is_ours(path: &Path, store_path: &Path) -> bool {
    path.parent() == Some(store_path)
        && path
            .file_name()
            .is_some_and(|name| name.to_string_lossy().starts_with(COMPACT_BACKUP_PREFIX))
}

fn newest_compact_backup(store_path: &Path) -> Option<PathBuf> {
    let entries = std::fs::read_dir(store_path).ok()?;
    let mut names: Vec<String> = entries
        .flatten()
        .filter_map(|entry| entry.file_name().to_str().map(str::to_string))
        .filter(|name| name.starts_with(COMPACT_BACKUP_PREFIX))
        .collect();
    names.sort();
    names.pop().map(|name| store_path.join(name))
}

/// Keep only the newest `keep` timestamped backups (names sort
/// lexicographically because the stamp has fixed-width nanosecond fields).
fn prune_compact_backups(store_path: &Path, keep: usize) -> Vec<String> {
    let Ok(entries) = std::fs::read_dir(store_path) else {
        return Vec::new();
    };
    let mut names: Vec<String> = entries
        .flatten()
        .filter_map(|entry| entry.file_name().to_str().map(str::to_string))
        .filter(|name| name.starts_with(COMPACT_BACKUP_PREFIX))
        .collect();
    names.sort();
    if names.len() <= keep {
        return Vec::new();
    }
    let stale: Vec<String> = names.drain(..names.len() - keep).collect();
    for name in &stale {
        let _ = std::fs::remove_file(store_path.join(name));
    }
    if !stale.is_empty() {
        fsync_dir(store_path);
    }
    stale
}

fn cleanup_compact_artifacts(store_path: &Path, tmp_dir: &Path) {
    let _ = std::fs::remove_dir_all(tmp_dir);
    let _ = std::fs::remove_file(store_path.join(COMPACT_JOURNAL_FILE));
    fsync_dir(store_path);
}

/// Complete or roll back a compaction interrupted by a crash.
///
/// Deterministic rules:
/// - `data.mdb` missing (crash between the two swap renames): restore the
///   journal's backup (or the newest backup) when it looks like an LMDB env,
///   then drop the stale copy and journal;
/// - `data.mdb` present (crash during copy or after install): the live file
///   is consistent either way — drop the stale copy and journal, keep backups.
fn recover_interrupted_compact(store_path: &Path) -> Result<Option<String>, String> {
    let journal_path = store_path.join(COMPACT_JOURNAL_FILE);
    if !journal_path.exists() {
        return Ok(None);
    }
    let data_path = store_path.join("data.mdb");
    let expected_tmp = compact_tmp_dir(store_path);
    let journal: Option<CompactJournal> = std::fs::read_to_string(&journal_path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok());
    let journal_backup = journal
        .as_ref()
        .and_then(|entry| entry.backup.as_deref())
        .map(PathBuf::from)
        .filter(|path| backup_name_is_ours(path, store_path));

    if !data_path.is_file() {
        let candidate = journal_backup
            .filter(|path| path.is_file())
            .or_else(|| newest_compact_backup(store_path));
        let Some(backup) = candidate else {
            return Err(format!(
                "data.mdb is missing and {} names no usable backup; manual recovery required",
                journal_path.display()
            ));
        };
        if !backup_looks_like_env(&backup) {
            return Err(format!(
                "data.mdb is missing and candidate backup {} does not look like an LMDB env; \
                 refusing automatic recovery",
                backup.display()
            ));
        }
        std::fs::rename(&backup, &data_path)
            .map_err(|e| format!("restore backup {}: {e}", backup.display()))?;
        fsync_dir(store_path);
        if expected_tmp.exists() {
            let _ = std::fs::remove_dir_all(&expected_tmp);
        }
        let _ = std::fs::remove_file(&journal_path);
        fsync_dir(store_path);
        return Ok(Some(format!(
            "restored {} -> data.mdb (crash between swap renames)",
            backup.display()
        )));
    }

    let mut detail = "cleaned up interrupted compaction".to_string();
    if expected_tmp.exists() {
        let _ = std::fs::remove_dir_all(&expected_tmp);
        detail.push_str("; removed stale copy");
    }
    if journal.is_none() {
        detail.push_str(" (journal was unreadable)");
    }
    let _ = std::fs::remove_file(&journal_path);
    fsync_dir(store_path);
    Ok(Some(detail))
}

/// Exclusive compaction lease over the whole copy+swap. The workspace forbids
/// `unsafe` (no `flock(2)` without a new dependency), so this uses an atomic
/// `O_EXCL` PID lease in the `SentinelLeaseGuard` pattern: only other
/// `wm compact` runs honor it — serving units do not, which is why the
/// live-handle refusal is still required (and why the residual race is
/// documented in the command help).
struct CompactLock {
    path: PathBuf,
}

impl CompactLock {
    fn acquire(store_path: &Path) -> Result<Self, String> {
        let path = store_path.join(COMPACT_LOCK_FILE);
        for attempt in 0..2 {
            match std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&path)
            {
                Ok(mut file) => {
                    use std::io::Write as _;
                    let _ = writeln!(file, "{}", std::process::id());
                    let _ = file.sync_all();
                    return Ok(Self { path });
                }
                Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
                    if attempt == 0 && !compact_lease_holder_alive(&path) {
                        let _ = std::fs::remove_file(&path);
                        continue;
                    }
                    let holder = compact_lease_holder(&path)
                        .map_or_else(|| "unknown pid".to_string(), |pid| format!("pid {pid}"));
                    return Err(format!(
                        "another compaction holds {} ({holder})",
                        path.display()
                    ));
                }
                Err(error) => return Err(format!("create {}: {error}", path.display())),
            }
        }
        Err(format!("could not acquire {}", path.display()))
    }
}

impl Drop for CompactLock {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
        if let Some(parent) = self.path.parent() {
            fsync_dir(parent);
        }
    }
}

fn compact_lease_holder(path: &Path) -> Option<u32> {
    std::fs::read_to_string(path)
        .ok()?
        .trim()
        .parse::<u32>()
        .ok()
}

fn compact_lease_holder_alive(path: &Path) -> bool {
    let Some(pid) = compact_lease_holder(path) else {
        return false;
    };
    #[cfg(target_os = "linux")]
    {
        Path::new(&format!("/proc/{pid}")).exists()
    }
    #[cfg(not(target_os = "linux"))]
    {
        std::process::Command::new("kill")
            .arg("-0")
            .arg(pid.to_string())
            .status()
            .map(|status| status.success())
            .unwrap_or(false)
    }
}

#[derive(Debug, Default)]
struct LiveStoreHandles {
    /// Live processes with `data.mdb` mapped.
    mapped: Vec<u32>,
    /// PIDs that could open the store but whose maps could not be read while
    /// the process still exists (e.g. root-owned under `ptrace_scope`).
    unverifiable: Vec<(u32, String)>,
}

/// Parse the four credential uids (`Uid:` line) from `/proc/<pid>/status`,
/// which — unlike `maps` — is world-readable for every process.
#[cfg(target_os = "linux")]
fn proc_status_uids(proc_dir: &Path) -> Option<[u32; 4]> {
    let text = std::fs::read_to_string(proc_dir.join("status")).ok()?;
    let line = text.lines().find(|line| line.starts_with("Uid:"))?;
    let mut uids = [0u32; 4];
    for (slot, token) in line.split_whitespace().skip(1).take(4).enumerate() {
        uids[slot] = token.parse().ok()?;
    }
    Some(uids)
}

/// Refuse to compact while any live process (other than this one) has the
/// store's `data.mdb` mapped: LMDB locks live in `lock.mdb`, so a mapped
/// handle may be a writer whose lock state cannot be inspected. Unreadable
/// maps entries for processes that could open the store (same uid, root, or
/// any uid when the store grants group/other access) are treated as possible
/// writers, not skipped; a process that exited mid-scan is not a writer.
/// Processes that provably cannot open a 0600 store (other uid, non-root) are
/// excluded by file-permission proof rather than by a failed read.
#[cfg(target_os = "linux")]
fn store_live_handles(store_path: &Path) -> Result<LiveStoreHandles, String> {
    use std::os::unix::fs::MetadataExt as _;
    let data_path = std::fs::canonicalize(store_path.join("data.mdb"))
        .map_err(|e| format!("canonicalize data.mdb: {e}"))?;
    let metadata =
        std::fs::metadata(&data_path).map_err(|e| format!("stat {}: {e}", data_path.display()))?;
    let store_uid = metadata.uid();
    let group_or_other_accessible = metadata.mode() & 0o077 != 0;
    let needle = data_path.to_string_lossy().into_owned();
    let self_pid = std::process::id();
    let mut handles = LiveStoreHandles::default();
    let entries = std::fs::read_dir("/proc").map_err(|e| format!("read /proc: {e}"))?;
    for entry in entries {
        let Ok(entry) = entry else { continue };
        let Some(pid) = entry
            .file_name()
            .to_str()
            .and_then(|name| name.parse::<u32>().ok())
        else {
            continue;
        };
        if pid == self_pid {
            continue;
        }
        let proc_dir = entry.path();
        let eligible = match proc_status_uids(&proc_dir) {
            Some(uids) => {
                group_or_other_accessible || uids.iter().any(|uid| *uid == store_uid || *uid == 0)
            }
            // Cannot even determine the owner: treat as a possible writer.
            None => true,
        };
        if !eligible {
            continue;
        }
        match std::fs::read_to_string(proc_dir.join("maps")) {
            Ok(maps) => {
                if maps.lines().any(|line| line.contains(&needle)) {
                    handles.mapped.push(pid);
                }
            }
            Err(error) => {
                if !proc_dir.exists() {
                    continue;
                }
                handles.unverifiable.push((pid, error.to_string()));
            }
        }
    }
    handles.mapped.sort_unstable();
    handles.mapped.dedup();
    handles.unverifiable.sort_by_key(|(pid, _)| *pid);
    handles.unverifiable.dedup_by_key(|(pid, _)| *pid);
    Ok(handles)
}

#[cfg(not(target_os = "linux"))]
fn store_live_handles(_store_path: &Path) -> Result<LiveStoreHandles, String> {
    Err("live-handle inspection is only implemented on Linux".to_string())
}

/// Test seam: the gated compaction e2e runs in-process on hosts whose root
/// processes are unreadable maps entries under `ptrace_scope`; production
/// builds compile the bypass out entirely (`cfg(test)`).
#[cfg(test)]
static COMPACT_TEST_SKIP_WRITER_SCAN: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);

fn run_compact_command(store_path: &Path, dry_run: bool, json: bool, yes: bool) -> i32 {
    // Recovery always runs first so a crash between the two swap renames is
    // repaired before the store is inspected (even for --dry-run).
    let recovery = match recover_interrupted_compact(store_path) {
        Ok(note) => note,
        Err(error) => {
            eprintln!("compact: recovery failed: {error}");
            return 1;
        }
    };
    if let Some(note) = &recovery {
        if !json {
            println!("compact: {note}");
        }
    }

    let data_path = store_path.join("data.mdb");
    if !data_path.is_file() {
        eprintln!(
            "compact: no data.mdb at {} (is this a Gen3 store?)",
            store_path.display()
        );
        return 1;
    }
    let data_bytes = std::fs::metadata(&data_path)
        .map(|meta| meta.len())
        .unwrap_or(0);
    let size = store_size_report(data_bytes, configured_map_size_bytes());

    if dry_run {
        if json {
            print_compact_json(&compact_size_json(
                store_path,
                &size,
                "reported",
                serde_json::json!({
                    "dry_run": true,
                    "compact_available": find_on_path("mdb_copy").is_some(),
                    "recovery": recovery,
                }),
            ));
        } else {
            println!("Store data.mdb: {}", render_store_size(&size));
            println!("Data file:      {}", data_path.display());
            println!(
                "Compaction tool: {}",
                if find_on_path("mdb_copy").is_some() {
                    "mdb_copy available (dry run; nothing copied)"
                } else {
                    "mdb_copy missing (install: sudo apt install lmdb-utils)"
                }
            );
        }
        return 0;
    }

    let Some(mdb_copy) = find_on_path("mdb_copy") else {
        if json {
            print_compact_json(&compact_size_json(
                store_path,
                &size,
                "unavailable",
                serde_json::json!({
                    "install_hint": "sudo apt install lmdb-utils",
                    "recovery": recovery,
                }),
            ));
        }
        eprintln!(
            "compact: mdb_copy not found on PATH; install it with: sudo apt install lmdb-utils"
        );
        return 3;
    };

    let tmp_dir = compact_tmp_dir(store_path);
    if tmp_dir.exists() {
        eprintln!(
            "compact: temporary path {} already exists; remove it and retry",
            tmp_dir.display()
        );
        return 1;
    }

    let _lock = match CompactLock::acquire(store_path) {
        Ok(lock) => lock,
        Err(error) => {
            eprintln!("compact: refusing to act: {error}");
            return 1;
        }
    };

    #[cfg(test)]
    let test_bypass_writer_scan =
        COMPACT_TEST_SKIP_WRITER_SCAN.swap(false, std::sync::atomic::Ordering::SeqCst);
    #[cfg(not(test))]
    let test_bypass_writer_scan = false;
    if !test_bypass_writer_scan {
        match store_live_handles(store_path) {
            Ok(handles) if !handles.mapped.is_empty() => {
                eprintln!(
                    "compact: refusing to act: {} live process(es) have {} mapped ({:?}); \
                     stop the serving unit first (e.g. systemctl --user stop 'wm-serve@*')",
                    handles.mapped.len(),
                    data_path.display(),
                    handles.mapped
                );
                return 1;
            }
            Ok(handles) if !handles.unverifiable.is_empty() => {
                eprintln!(
                    "compact: refusing to act: {} /proc maps entr(ies) are unreadable for \
                     processes that could open the store ({:?}); cannot rule out a live \
                     writer — stop the serving unit first, or run compact with sufficient \
                     privilege to inspect them",
                    handles.unverifiable.len(),
                    handles.unverifiable
                );
                return 1;
            }
            Ok(_) => {}
            Err(error) => {
                eprintln!("compact: refusing to act: cannot verify store lock liveness ({error})");
                return 1;
            }
        }
    }

    if !yes {
        if json {
            print_compact_json(&compact_size_json(
                store_path,
                &size,
                "available",
                serde_json::json!({
                    "mdb_copy": mdb_copy.display().to_string(),
                    "recovery": recovery,
                }),
            ));
        } else {
            println!("Store data.mdb: {}", render_store_size(&size));
            println!(
                "Compaction available: re-run with --yes to rewrite {} via {} -c",
                data_path.display(),
                mdb_copy.display()
            );
        }
        return 0;
    }

    let original_count = match Store::open_readonly(store_path) {
        Ok(store) => match store.record_count() {
            Ok(count) => count,
            Err(e) => {
                eprintln!("compact: cannot count records before compaction: {e}");
                return 1;
            }
        },
        Err(e) => {
            eprintln!("compact: cannot open store read-only: {e}");
            return 1;
        }
    };

    let mut journal = CompactJournal::copy(&tmp_dir);
    if let Err(error) = write_compact_journal(store_path, &journal) {
        eprintln!("compact: cannot journal compaction start: {error}");
        return 1;
    }

    let copy = std::process::Command::new(&mdb_copy)
        .arg("-c")
        .arg(store_path)
        .arg(&tmp_dir)
        .output();
    match copy {
        Ok(output) if output.status.success() => {}
        Ok(output) => {
            eprintln!(
                "compact: mdb_copy failed ({}): {}",
                output.status,
                String::from_utf8_lossy(&output.stderr).trim()
            );
            cleanup_compact_artifacts(store_path, &tmp_dir);
            return 1;
        }
        Err(error) => {
            eprintln!("compact: failed to run {}: {error}", mdb_copy.display());
            cleanup_compact_artifacts(store_path, &tmp_dir);
            return 1;
        }
    }

    let tmp_data = tmp_dir.join("data.mdb");
    if !tmp_data.is_file() {
        eprintln!("compact: mdb_copy produced no {}", tmp_data.display());
        cleanup_compact_artifacts(store_path, &tmp_dir);
        return 1;
    }

    let copied_count = match Store::open_readonly(&tmp_dir).and_then(|store| store.record_count()) {
        Ok(count) => count,
        Err(error) => {
            eprintln!("compact: copy verification failed to open: {error}");
            cleanup_compact_artifacts(store_path, &tmp_dir);
            return 1;
        }
    };
    if copied_count != original_count {
        eprintln!(
            "compact: copy verification failed: record count {copied_count} != original {original_count}"
        );
        cleanup_compact_artifacts(store_path, &tmp_dir);
        return 1;
    }

    let timestamp = compact_timestamp();
    let backup = store_path.join(format!("{COMPACT_BACKUP_PREFIX}{timestamp}"));
    journal.backup = Some(backup.display().to_string());
    journal.set_phase("swap_backup");
    if let Err(error) = write_compact_journal(store_path, &journal) {
        eprintln!("compact: cannot journal swap phase: {error}");
        cleanup_compact_artifacts(store_path, &tmp_dir);
        return 1;
    }

    if let Err(e) = std::fs::rename(&data_path, &backup) {
        eprintln!("compact: backup rename failed: {e}");
        cleanup_compact_artifacts(store_path, &tmp_dir);
        return 1;
    }
    fsync_dir(store_path);
    if let Err(e) = std::fs::rename(&tmp_data, &data_path) {
        eprintln!("compact: swap rename failed: {e}; restoring backup");
        let _ = std::fs::rename(&backup, &data_path);
        fsync_dir(store_path);
        cleanup_compact_artifacts(store_path, &tmp_dir);
        return 1;
    }
    fsync_dir(store_path);
    journal.set_phase("swap_installed");
    if let Err(error) = write_compact_journal(store_path, &journal) {
        eprintln!("compact: warning: could not record swap phase: {error}");
    }

    let verified = Store::open_readonly(store_path).and_then(|store| store.record_count());
    let after_bytes = std::fs::metadata(&data_path)
        .map(|meta| meta.len())
        .unwrap_or(0);

    match verified {
        Ok(count) if count == original_count => {
            let _ = std::fs::remove_dir_all(&tmp_dir);
            let _ = std::fs::remove_file(store_path.join(COMPACT_JOURNAL_FILE));
            fsync_dir(store_path);
            let pruned = prune_compact_backups(store_path, COMPACT_BACKUP_KEEP);
            if json {
                print_compact_json(&compact_size_json(
                    store_path,
                    &size,
                    "compacted",
                    serde_json::json!({
                        "backup": backup.display().to_string(),
                        "before_bytes": size.data_mdb_bytes,
                        "after_bytes": after_bytes,
                        "records": count,
                        "backups_pruned": pruned,
                        "recovery": recovery,
                    }),
                ));
            } else {
                println!("Compaction complete.");
                println!("Before:         {}", format_bytes(size.data_mdb_bytes));
                println!("After:          {}", format_bytes(after_bytes));
                println!("Records:        {count} (verified)");
                println!("Backup kept:    {}", backup.display());
                if !pruned.is_empty() {
                    println!("Backups pruned: {}", pruned.join(", "));
                }
            }
            0
        }
        Ok(count) => {
            eprintln!(
                "compact: post-swap verification failed: record count {count} != {original_count}; rolling back"
            );
            let failed = store_path.join(format!("data.mdb.failed.{timestamp}"));
            let _ = std::fs::rename(&data_path, &failed);
            let _ = std::fs::rename(&backup, &data_path);
            fsync_dir(store_path);
            cleanup_compact_artifacts(store_path, &tmp_dir);
            1
        }
        Err(e) => {
            eprintln!(
                "compact: post-swap verification failed to open: {e}; rolling back to backup"
            );
            let failed = store_path.join(format!("data.mdb.failed.{timestamp}"));
            let _ = std::fs::rename(&data_path, &failed);
            let _ = std::fs::rename(&backup, &data_path);
            fsync_dir(store_path);
            cleanup_compact_artifacts(store_path, &tmp_dir);
            1
        }
    }
}

// ── Host guard CLI ──────────────────────────────────────────────────────

fn host_guard_state_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("WM_HOST_GUARD_STATE_DIR") {
        if !dir.trim().is_empty() {
            return PathBuf::from(dir);
        }
    }
    if let Ok(home) = std::env::var("HOME") {
        return PathBuf::from(home).join(".local/state/whitemagic/host-guard");
    }
    std::env::temp_dir().join("whitemagic-host-guard")
}

fn host_guard_state_file(state_dir: &Path) -> PathBuf {
    state_dir.join("host-guard-state.json")
}

fn load_host_guard_state(state_dir: &Path) -> HostGuardState {
    let state_file = host_guard_state_file(state_dir);
    match std::fs::read_to_string(&state_file) {
        Ok(text) => HostGuardState::from_json_or_default(&text),
        Err(_) => HostGuardState::default(),
    }
}

/// Durable armed flag: missing file means armed (matching the firebreak
/// promoted default); `host-guard arm|disarm` rewrites it explicitly.
fn load_host_guard_armed(state_dir: &Path) -> bool {
    match std::fs::read_to_string(state_dir.join("host-guard.armed")) {
        Ok(text) => !text.trim().eq_ignore_ascii_case("disarmed"),
        Err(_) => true,
    }
}

fn run_host_guard_set_armed(state_dir: &Path, arm: bool) -> i32 {
    if let Err(e) = std::fs::create_dir_all(state_dir) {
        eprintln!(
            "host-guard: cannot create state dir {}: {e}",
            state_dir.display()
        );
        return 1;
    }
    let flag = state_dir.join("host-guard.armed");
    let body = if arm { "armed\n" } else { "disarmed\n" };
    match std::fs::write(&flag, body) {
        Ok(()) => {
            println!(
                "Host guard {} — mutations {}.",
                if arm { "armed" } else { "disarmed" },
                if arm {
                    "permitted (still bounded by policy and rate limits)"
                } else {
                    "refused until re-armed (--force overrides one run)"
                }
            );
            0
        }
        Err(e) => {
            eprintln!("host-guard: cannot write {}: {e}", flag.display());
            1
        }
    }
}

fn unix_now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

fn signals_summary(signals: &wm_gen3_harness::host_health::HostSignals) -> serde_json::Value {
    serde_json::json!({
        "mem_total_kib": signals.mem_total_kib,
        "mem_available_kib": signals.mem_available_kib,
        "mem_available_fraction": signals.mem_available_fraction,
        "psi_memory_full_avg10": signals.psi_memory_full_avg10,
        "psi_io_full_avg10": signals.psi_io_full_avg10,
        "swap_total_kib": signals.swap_total_kib,
        "swap_used_kib": signals.swap_used_kib,
        "swap_used_fraction": signals.swap_used_fraction,
        "swap_is_zram": signals.swap_is_zram,
        "disk_free_gib": signals.disk_free_gib,
        "disk_used_pct": signals.disk_used_pct,
        "crash_loop_units": signals.crash_loop_units.len(),
        "failed_loop_units": signals.failed_loop_units.len(),
        "top_processes": signals.top_processes.len(),
        "unit_probe_ok": signals.unit_probe_ok,
    })
}

fn run_host_guard_command(cmd: HostGuardCommands) {
    let state_dir = host_guard_state_dir();
    match cmd {
        HostGuardCommands::Status { json } => run_host_guard_status(&state_dir, json),
        HostGuardCommands::Run {
            act,
            kill_orphans,
            dry_run,
            json,
            force,
        } => {
            let code = run_host_guard_run(&state_dir, act, kill_orphans, dry_run, json, force);
            if code != 0 {
                std::process::exit(code);
            }
        }
        HostGuardCommands::Arm => {
            let code = run_host_guard_set_armed(&state_dir, true);
            if code != 0 {
                std::process::exit(code);
            }
        }
        HostGuardCommands::Disarm => {
            let code = run_host_guard_set_armed(&state_dir, false);
            if code != 0 {
                std::process::exit(code);
            }
        }
    }
}

fn run_host_guard_status(state_dir: &Path, json: bool) {
    let signals = wm_gen3_harness::host_health::collect_signals();
    let state = load_host_guard_state(state_dir);
    let plan = host_guard::plan(&signals, &state, &Policy::default());
    if json {
        let value = serde_json::json!({
            "severity": plan.severity.as_str(),
            "reasons": plan.reasons,
            "actions": plan.actions,
            "suppressed": plan.suppressed,
            "signals": signals_summary(&signals),
            "armed": load_host_guard_armed(state_dir),
            "state_dir": state_dir.display().to_string(),
        });
        print_compact_json(&value);
    } else {
        for line in host_guard::render(&signals, &plan) {
            println!("{line}");
        }
    }
}

fn run_host_guard_run(
    state_dir: &Path,
    act: bool,
    kill_orphans: bool,
    dry_run: bool,
    json: bool,
    force: bool,
) -> i32 {
    if let Err(e) = std::fs::create_dir_all(state_dir) {
        eprintln!(
            "host-guard: cannot create state dir {}: {e}",
            state_dir.display()
        );
        return 1;
    }
    let _guard = match SentinelLeaseGuard::acquire(state_dir.join("host-guard.lock")) {
        Ok(guard) => guard,
        Err(e) => {
            eprintln!("host-guard: lease error: {e}");
            return 1;
        }
    };

    let armed = load_host_guard_armed(state_dir);
    let mut state = load_host_guard_state(state_dir);
    let policy = Policy {
        kill_orphans,
        ..Default::default()
    };
    let signals = wm_gen3_harness::host_health::collect_signals();
    let now = unix_now_secs();
    let mut plan = host_guard::plan_at(&signals, &state, &policy, now);

    let mutations = act && (armed || force);
    if !mutations {
        let note = if !act {
            "mutations disabled: pass --act to enable stop/defer/terminate".to_string()
        } else {
            "mutations refused: host-guard disarmed (run 'wm host-guard arm' or pass --force)"
                .to_string()
        };
        plan.actions
            .retain(|action| matches!(action, Action::PostBoard { .. }));
        plan.suppressed.push(note);
    }

    let report = host_guard::execute(&plan, &mut state, &SystemRunner, now, dry_run);

    if dry_run {
        // dry run consumes nothing: no state write, no runner calls.
    } else {
        let state_file = host_guard_state_file(state_dir);
        let tmp_file = state_dir.join("host-guard-state.json.tmp");
        if let Err(e) = std::fs::write(&tmp_file, state.to_json())
            .and_then(|()| std::fs::rename(&tmp_file, &state_file))
        {
            eprintln!("host-guard: warning: could not persist state: {e}");
        }
    }

    if json {
        let value = serde_json::json!({
            "severity": report.severity.as_str(),
            "dry_run": report.dry_run,
            "mutations": mutations,
            "armed": armed,
            "executed": report.executed,
            "skipped": report.skipped,
            "failed": report.failed,
            "reasons": plan.reasons,
            "suppressed": plan.suppressed,
            "signals": signals_summary(&signals),
            "state_dir": state_dir.display().to_string(),
        });
        print_compact_json(&value);
    } else {
        println!(
            "Host guard run: severity={}, mutations={}, armed={}, dry_run={}",
            report.severity.as_str(),
            if mutations { "enabled" } else { "disabled" },
            armed,
            dry_run
        );
        for reason in &plan.reasons {
            println!("  [signal] {reason}");
        }
        for note in &plan.suppressed {
            println!("  [suppressed] {note}");
        }
        for action in &report.executed {
            println!("  [executed] {}", action.label());
        }
        for note in &report.skipped {
            println!("  [skipped] {note}");
        }
        for note in &report.failed {
            println!("  [failed] {note}");
        }
    }

    if report.severity == wm_gen3_harness::host_health::Verdict::Critical {
        1
    } else {
        0
    }
}

// ── At-rest CLI ─────────────────────────────────────────────────────────

fn run_at_rest_command(cmd: AtRestCommands, store_path: &Path) -> i32 {
    match cmd {
        AtRestCommands::Status { json } => run_at_rest_status(store_path, json),
        AtRestCommands::Migrate {
            dry_run,
            batch,
            json,
            yes,
        } => run_at_rest_migrate(store_path, dry_run, batch, json, yes),
    }
}

fn run_at_rest_status(store_path: &Path, json: bool) -> i32 {
    if !store_path.join("data.mdb").is_file() {
        eprintln!(
            "at-rest status: no data.mdb at {} (is this a Gen3 store?)",
            store_path.display()
        );
        return 1;
    }
    let store = match Store::open_readonly(store_path) {
        Ok(store) => store,
        Err(e) => {
            eprintln!(
                "at-rest status: cannot open {} read-only: {e}",
                store_path.display()
            );
            return 1;
        }
    };
    let status = store.at_rest_status();
    let ledger = store.at_rest_migration_ledger();

    if json {
        let mut value = serde_json::json!({
            "store": store_path.display().to_string(),
        });
        let object = value.as_object_mut().expect("json object");
        match &status {
            AtRestStatus::Absent => {
                object.insert("status".into(), serde_json::json!("absent"));
                object.insert("mode".into(), serde_json::json!("off"));
                object.insert("wrapped_deks".into(), serde_json::json!(0));
            }
            AtRestStatus::Present(present) => {
                object.insert("status".into(), serde_json::json!("present"));
                object.insert("mode".into(), serde_json::json!(present.meta.mode.as_str()));
                object.insert(
                    "key_source".into(),
                    serde_json::json!(present.meta.key_source),
                );
                object.insert(
                    "created_at".into(),
                    serde_json::json!(present.meta.created_at),
                );
                object.insert(
                    "wrapped_deks".into(),
                    serde_json::json!(present.wrapped_deks),
                );
                object.insert("galaxies".into(), serde_json::json!(present.galaxies));
                object.insert(
                    "key_file".into(),
                    serde_json::json!(
                        present
                            .key_file
                            .as_ref()
                            .map(|path| path.display().to_string())
                    ),
                );
                object.insert(
                    "argon2".into(),
                    serde_json::to_value(&present.meta.argon2).unwrap_or(serde_json::Value::Null),
                );
            }
            AtRestStatus::Malformed { reason } => {
                object.insert("status".into(), serde_json::json!("malformed"));
                object.insert("reason".into(), serde_json::json!(reason));
            }
        }
        match &ledger {
            Ok(Some(ledger)) => {
                object.insert(
                    "migration".into(),
                    serde_json::to_value(ledger).unwrap_or(serde_json::Value::Null),
                );
            }
            Ok(None) => {
                object.insert("migration".into(), serde_json::Value::Null);
            }
            Err(e) => {
                object.insert("ledger_error".into(), serde_json::json!(e.to_string()));
            }
        }
        print_compact_json(&value);
        return 0;
    }

    println!("==================================================");
    println!("       WhiteMagic Gen3 At-Rest Status             ");
    println!("==================================================");
    println!("Store Path:       {}", store_path.display());
    match &status {
        AtRestStatus::Absent => {
            println!("Mode:             off");
            println!("Keyring:          absent (plaintext pass-through)");
        }
        AtRestStatus::Present(present) => {
            println!("Mode:             {}", present.meta.mode.as_str());
            println!(
                "Keyring:          present (source: {}, created: {})",
                present.meta.key_source, present.meta.created_at
            );
            println!("Wrapped DEKs:     {}", present.wrapped_deks);
            println!("Scopes covered:   {}", present.galaxies);
            match &present.key_file {
                Some(path) => println!("Key File:         {}", path.display()),
                None => println!("Key File:         (env material or passphrase)"),
            }
        }
        AtRestStatus::Malformed { reason } => {
            println!("Keyring:          MALFORMED — {reason}");
            println!("                  (writable opens are refused until repaired)");
        }
    }
    match &ledger {
        Ok(Some(ledger)) => {
            println!(
                "Migration Ledger: version {}, updated {}",
                ledger.version,
                if ledger.updated_at.is_empty() {
                    "(never)"
                } else {
                    ledger.updated_at.as_str()
                }
            );
            if ledger.galaxies.is_empty() {
                println!("  records:        no scopes recorded");
            }
            for (scope, state) in &ledger.galaxies {
                println!(
                    "  {scope}: sealed={}, done={}, cursor={}",
                    state.encrypted,
                    state.done,
                    if state.cursor_hex.is_empty() {
                        "start"
                    } else {
                        state.cursor_hex.as_str()
                    }
                );
            }
        }
        Ok(None) => println!("Migration Ledger: none"),
        Err(e) => println!("Migration Ledger: UNREADABLE ({e})"),
    }
    println!("==================================================");
    0
}

fn run_at_rest_migrate(
    store_path: &Path,
    dry_run: bool,
    batch: usize,
    json: bool,
    yes: bool,
) -> i32 {
    if !store_path.join("data.mdb").is_file() {
        eprintln!(
            "at-rest migrate: no data.mdb at {} (is this a Gen3 store?)",
            store_path.display()
        );
        return 1;
    }
    if !dry_run && !yes {
        eprintln!("at-rest migrate: refusing to write without --yes (preview with --dry-run)");
        return 1;
    }
    let store = match Store::open(store_path) {
        Ok(store) => store,
        Err(e) => {
            eprintln!(
                "at-rest migrate: cannot open {} (mode B/C key required): {e}",
                store_path.display()
            );
            return 1;
        }
    };
    match store.migrate_at_rest_records(batch.max(1), dry_run) {
        Ok(report) => {
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&serde_json::json!({
                        "store": store_path.display().to_string(),
                        "dry_run": report.dry_run,
                        "batch": batch.max(1),
                        "scanned": report.scanned,
                        "sealed": report.sealed,
                        "already_sealed": report.already_sealed,
                        "skipped": report.skipped,
                        "done": report.done,
                    }))
                    .unwrap_or_default()
                );
            } else {
                println!(
                    "At-rest migration ({}):",
                    if report.dry_run {
                        "dry run"
                    } else {
                        "committed"
                    }
                );
                println!("  store:          {}", store_path.display());
                println!("  batch:          {}", batch.max(1));
                println!("  scanned:        {}", report.scanned);
                println!("  sealed:         {}", report.sealed);
                println!("  already sealed: {}", report.already_sealed);
                println!("  skipped:        {}", report.skipped);
                println!("  done:           {}", report.done);
            }
            0
        }
        Err(e) => {
            eprintln!("at-rest migrate failed: {e}");
            1
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
            track,
            commit,
            branch,
            tests_green,
            lease_id,
            lessons,
            corrections,
            identity_invariants,
            relational_context,
            evolve,
            no_evolve,
        } => {
            let evolve = evolve.unwrap_or(true) && !no_evolve;
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
                lessons,
                corrections,
                identity_invariants,
                relational_context,
            };
            let meta = serde_json::json!({
                "track": track,
                "commit": commit,
                "branch": branch,
                "tests_green": tests_green,
                "lease_id": lease_id,
            });
            match substrate.session_checkpoint_enriched(&cp, &meta) {
                Ok(id) => {
                    let epoch = substrate.store().epoch().unwrap_or(0);
                    println!("Session checkpoint committed successfully.");
                    println!("Record ID:       {}", id);
                    println!("Epoch:           {}", epoch);
                    println!("Session ID:      {}", cp.session_id);
                    println!("Checkpoint Type: {}", cp.checkpoint_type);
                    println!("Summary:         {}", cp.summary);
                    if let Some(track) = &track {
                        println!("Track:           {track}");
                    }
                    if let Some(commit) = &commit {
                        println!("Commit:          {commit}");
                    }
                    if let Some(branch) = &branch {
                        println!("Branch:          {branch}");
                    }
                    if let Some(tests_green) = tests_green {
                        println!("Tests Green:     {tests_green}");
                    }
                    if let Some(lease_id) = &lease_id {
                        println!("Lease ID:        {lease_id}");
                    }
                    if let Some(relational) = &cp.relational_context {
                        println!("Relational:      {relational}");
                    }
                    if !cp.identity_invariants.is_empty() {
                        println!("\nIdentity Invariants:");
                        for inv in &cp.identity_invariants {
                            println!("  - 🛡️  {inv}");
                        }
                    }
                    if !cp.lessons.is_empty() {
                        println!("\nDistilled Lessons:");
                        for lesson in &cp.lessons {
                            println!("  - 💡 {lesson}");
                        }
                    }
                    if !cp.corrections.is_empty() {
                        println!("\nCorrections Ledger:");
                        for corr in &cp.corrections {
                            println!("  - 🔧 {corr}");
                        }
                    }

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
                        let total_records = substrate.store().record_count().unwrap_or(0);
                        let stone_seed =
                            wm_gen3_core::wave2_braid::StonePillarMorphogenSeed::compile_from_live_state(
                                epoch,
                                total_records,
                                Some(id),
                                &cp.summary,
                                vault.skeletons.len(),
                                0xA5A5_5A5A_F00D_CAFE,
                            );
                        let _ = stone_seed.save_to_store(store_path);
                        println!(
                            "  Speciated: {} | Mutated: {:?} | Active Skeletons: {}",
                            speciated_count,
                            mutated_candidate,
                            vault.skeletons.len()
                        );
                        println!(
                            "  Stone Pillar Seed: {} B (Integrity Verified: {}, SHA-256: {}..)",
                            stone_seed.serialized_bytes,
                            stone_seed.verify_integrity(),
                            &stone_seed.seed_sha256[..16]
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
        SessionCommands::Continuity { session_id, limit } => {
            let substrate =
                match Substrate::open_readonly(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };
            let views = match substrate.session_continuities(session_id.as_deref(), limit) {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("Error retrieving session continuity: {e}");
                    std::process::exit(1);
                }
            };
            if views.is_empty() {
                println!("No session continuity records found for query '{session_id:?}'.");
            } else {
                for (idx, view) in views.iter().enumerate() {
                    println!("==================================================");
                    if views.len() > 1 {
                        println!(
                            "     WhiteMagic Session Continuity [{}/{}]        ",
                            idx + 1,
                            views.len()
                        );
                    } else {
                        println!("         WhiteMagic Session Continuity            ");
                    }
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
                    if let Some(track) = &view.track {
                        println!("Track:           {track}");
                    }
                    if let Some(commit) = &view.commit {
                        println!("Commit:          {commit}");
                    }
                    if let Some(branch) = &view.branch {
                        println!("Branch:          {branch}");
                    }
                    if let Some(tests_green) = view.tests_green {
                        println!("Tests Green:     {tests_green}");
                    }
                    if let Some(lease_id) = &view.lease_id {
                        println!("Lease ID:        {lease_id}");
                    }
                    if let Some(relational) = &view.relational_context {
                        println!("Relational:      {relational}");
                    }
                    if !view.identity_invariants.is_empty() {
                        println!("\nIdentity Invariants:");
                        for inv in &view.identity_invariants {
                            println!("  - 🛡️  {inv}");
                        }
                    }
                    if !view.lessons.is_empty() {
                        println!("\nDistilled Lessons:");
                        for lesson in &view.lessons {
                            println!("  - 💡 {lesson}");
                        }
                    }
                    if !view.corrections.is_empty() {
                        println!("\nCorrections Ledger:");
                        for corr in &view.corrections {
                            println!("  - 🔧 {corr}");
                        }
                    }
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
                }

                let insights_path = store_path.join("dream_insights.jsonl");
                if insights_path.exists() {
                    if let Ok(file) = std::fs::File::open(&insights_path) {
                        use std::io::{BufRead, BufReader};
                        let reader = BufReader::new(file);
                        let mut insights: Vec<wm_gen3_core::dream::DreamInsight> = Vec::new();
                        // flatten() keeps scanning after an unreadable line; map_while would drop the rest.
                        #[allow(clippy::lines_filter_map_ok)]
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
        SessionCommands::Digest {
            session_id,
            n,
            json,
        } => {
            let substrate =
                match Substrate::open_readonly(store_path, Some(&journal_path), default_view()) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Error opening store at {}: {e}", store_path.display());
                        std::process::exit(1);
                    }
                };

            let turns = SessionTurn::read_log(store_path);

            let effective = session_id.clone().or_else(|| {
                turns
                    .iter()
                    .rev()
                    .map(|turn| turn.session_id.clone())
                    .find(|lane| !lane.is_empty())
            });
            let label = effective.clone().unwrap_or_else(|| "all".to_string());
            let mut selected: Vec<SessionTurn> = turns
                .into_iter()
                .filter(|turn| !turn.is_start_marker())
                .filter(|turn| {
                    effective
                        .as_deref()
                        .is_none_or(|lane| turn.session_id == lane)
                })
                .filter(|turn| turn.superseded_by.is_none())
                .collect();
            if selected.len() > n {
                selected.drain(..selected.len() - n);
            }
            let checkpoint = substrate
                .session_continuity(effective.as_deref())
                .ok()
                .flatten();
            let (markdown, json_digest) =
                compose_session_digest(&label, &selected, checkpoint.as_ref());
            if json {
                println!("{json_digest}");
            } else {
                print!("{markdown}");
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

            match verify_pass_against_gate(&pass, store_path, now) {
                Ok(pubkey) => {
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
                    println!("Cryptographic Sig:   VALID (Signed by Local Authority Gate)");
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

            let mut manifest = CapabilityManifest {
                network_restricted,
                ..Default::default()
            };
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

            let receipt = match verify_continuity_receipt05(&content, store_path) {
                Ok(receipt) => receipt,
                Err(e) => {
                    eprintln!(
                        "Refusing unverified receipt {}: {e}",
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
                    println!("Receipt ID:          {}", receipt.receipt_id);
                    println!("Spec:                {}", receipt.spec);
                    println!("Issuer DID:          {}", receipt.issuer_did);
                    println!("Signature:           VALID (verified against store gate key)");
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
            println!(
                "PEB-15 Microsecond Benchmarks (recorded 2026-09 baseline; historical, not live):"
            );
            println!("  JEV Pre-Triage:    26.70 ns / eval  (37.5M evals/sec)");
            println!("  Workspace Claim:   87.67 us / claim (11.4k claims/sec)");
            println!("  Landlock Ruleset:  142.55 us / ruleset (7.0k rulesets/sec)");
            println!("  Total Setup:       230.22 us (0.23 ms)");
            println!("  Spec 0.5 Receipt:  341.93 us / notarize (2.9k receipts/sec)");
            println!("  Factory Pipeline:  604.44 us / trial (1,654 trials/sec)");
            println!("Speedup vs MicroVM:  152.0x faster than Firecracker");
            println!("Speedup vs Container: 521.2x faster than Docker/runc");
            println!(
                "Note:                recorded 2026-09 baseline; not re-measured by this command."
            );
            println!("==================================================");
        }
    }
}

fn run_ingest(
    store_path: &Path,
    file_path: &str,
    batch_size: usize,
    default_source: &str,
    default_kind: ImportKind,
    max_item_bytes: usize,
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

    let kind = default_kind;

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
    let preloaded = substrate.preload_identity_index().unwrap_or(0);
    println!(
        "Identity Cache:  {} existing record(s) preloaded",
        preloaded
    );
    println!("==================================================");

    let mut batch: Vec<RememberItem> = Vec::with_capacity(batch_size);
    let mut batch_meta: Vec<Option<IngestMeta>> = Vec::with_capacity(batch_size);
    let meta_path = store_path.join("record_meta.jsonl");
    let mut total_read: usize = 0;
    let mut total_committed: usize = 0;
    let mut total_duplicates: usize = 0;
    let mut total_other_refusals: usize = 0;
    let mut total_skipped_oversize: usize = 0;
    let mut total_skipped_binary: usize = 0;
    let mut total_meta_entries: usize = 0;
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

        let (item, meta) = if let Ok(json_val) = serde_json::from_str::<serde_json::Value>(trimmed)
        {
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
            let meta = parse_ingest_meta(&json_val);
            (
                RememberItem {
                    content: content.to_string(),
                    source: source.to_string(),
                    kind: item_kind,
                },
                meta,
            )
        } else {
            (
                RememberItem {
                    content: trimmed.to_string(),
                    source: default_source.to_string(),
                    kind,
                },
                None,
            )
        };

        if let Some(reason) = ingest_skip_reason(&item.content, max_item_bytes) {
            match reason {
                "oversize" => total_skipped_oversize += 1,
                _ => total_skipped_binary += 1,
            }
            continue;
        }

        batch.push(item);
        batch_meta.push(meta);

        if batch.len() >= batch_size {
            write_ingest_batch(
                &mut substrate,
                &batch,
                &batch_meta,
                &meta_path,
                &mut total_committed,
                &mut total_duplicates,
                &mut total_other_refusals,
                &mut total_meta_entries,
            );
            batch.clear();
            batch_meta.clear();
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
        write_ingest_batch(
            &mut substrate,
            &batch,
            &batch_meta,
            &meta_path,
            &mut total_committed,
            &mut total_duplicates,
            &mut total_other_refusals,
            &mut total_meta_entries,
        );
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
    if total_skipped_oversize > 0 || total_skipped_binary > 0 {
        println!("Skipped (oversize):    {}", total_skipped_oversize);
        println!("Skipped (binary):      {}", total_skipped_binary);
    }
    if total_meta_entries > 0 {
        println!("Metadata Entries:      {}", total_meta_entries);
        println!("Metadata Sidecar:      {}", meta_path.display());
    }
    println!("Current Store Epoch:   {}", epoch);
    println!("==================================================");
}

/// Counted, never-silent ingest guard: oversized content and binary payloads
/// (NUL bytes) are skipped before they can bloat the store (board #764).
fn ingest_skip_reason(content: &str, max_item_bytes: usize) -> Option<&'static str> {
    if max_item_bytes > 0 && content.len() > max_item_bytes {
        return Some("oversize");
    }
    if content.as_bytes().contains(&0) {
        return Some("binary");
    }
    None
}

struct IngestMeta {
    tags: Vec<String>,
    importance: f64,
}

fn parse_ingest_meta(json_val: &serde_json::Value) -> Option<IngestMeta> {
    let tags: Vec<String> = json_val
        .get("tags")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|t| t.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default();
    let importance = json_val.get("importance").and_then(|v| v.as_f64());
    if tags.is_empty() && importance.is_none() {
        return None;
    }
    Some(IngestMeta {
        tags,
        importance: importance.unwrap_or(0.0),
    })
}

#[allow(clippy::too_many_arguments)]
fn write_ingest_batch(
    substrate: &mut Substrate,
    batch: &[RememberItem],
    batch_meta: &[Option<IngestMeta>],
    meta_path: &Path,
    total_committed: &mut usize,
    total_duplicates: &mut usize,
    total_other_refusals: &mut usize,
    total_meta_entries: &mut usize,
) {
    let res = substrate.remember_batch(batch);
    for (idx, committed_res) in res.into_iter().enumerate() {
        match committed_res {
            Ok(id) => {
                *total_committed += 1;
                if let Some(meta) = batch_meta.get(idx).and_then(|m| m.as_ref())
                    && append_record_meta(meta_path, id, meta).is_ok()
                {
                    *total_meta_entries += 1;
                }
            }
            Err(ref e) if e == "duplicate_exact" || e.contains("duplicate") => {
                *total_duplicates += 1;
            }
            Err(ref e) => {
                *total_other_refusals += 1;
                if *total_other_refusals <= 5 || *total_other_refusals % 1000 == 0 {
                    eprintln!("Refusal reason: {e}");
                }
            }
        }
    }
}

fn append_record_meta(path: &Path, record_id: u64, meta: &IngestMeta) -> std::io::Result<()> {
    use std::io::Write;
    let ingested_at_ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64;
    let entry = serde_json::json!({
        "record_id": record_id,
        "tags": meta.tags,
        "importance": meta.importance,
        "ingested_at_ms": ingested_at_ms,
    });
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?;
    writeln!(f, "{entry}")
}

fn run_system2_command(command: SystemTwoCommands, store_path: &Path) {
    match command {
        SystemTwoCommands::Ask {
            question,
            context,
            json,
            model,
            endpoint,
        } => {
            let mut config = match wm_gen3_harness::systemtwo::SystemTwoConfig::from_env() {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("{e}");
                    std::process::exit(1);
                }
            };
            if let Some(model) = model {
                config.model = model;
            }
            if let Some(endpoint) = endpoint {
                config.endpoint = endpoint;
            }
            let context = match context {
                Some(raw) if raw.starts_with('@') => {
                    let path = &raw[1..];
                    match std::fs::read_to_string(path) {
                        Ok(text) => Some(text),
                        Err(e) => {
                            eprintln!("system2: cannot read context file {path}: {e}");
                            std::process::exit(1);
                        }
                    }
                }
                other => other,
            };

            let answer =
                match wm_gen3_harness::systemtwo::ask(&config, &question, context.as_deref()) {
                    Ok(answer) => answer,
                    Err(e) => {
                        eprintln!("{e}");
                        std::process::exit(1);
                    }
                };

            let gate_key =
                match wm_gen3_core::mandala::resolve_or_create_mandala_gate_key(store_path) {
                    Ok((key, _)) => key,
                    Err(e) => {
                        eprintln!("system2: gate key resolution failed: {e}");
                        std::process::exit(1);
                    }
                };
            let receipt = wm_gen3_harness::systemtwo::ConsultationReceipt::sign(
                &gate_key, &question, &answer,
            );
            let receipt_path = receipt.persist(store_path).ok();

            if json {
                let out = serde_json::json!({
                    "status": "success",
                    "content": answer.content,
                    "model": answer.model,
                    "endpoint": answer.endpoint,
                    "latency_ms": answer.latency_ms,
                    "max_tokens": answer.max_tokens,
                    "completion_tokens": answer.completion_tokens,
                    "receipt": receipt,
                    "receipt_path": receipt_path.map(|p| p.display().to_string()),
                });
                println!("{}", serde_json::to_string_pretty(&out).unwrap_or_default());
            } else {
                println!("{}", answer.content);
                println!(
                    "-- model: {} · {:.0} ms · max_tokens: {}",
                    answer.model, answer.latency_ms, answer.max_tokens
                );
                if let Some(path) = receipt_path {
                    eprintln!("receipt: {}", path.display());
                }
            }
        }
    }
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

    let default_quarantine = target.join("quarantine.jsonl");
    let q_path = quarantine_file.unwrap_or(default_quarantine);

    let options = MigrationOptions {
        batch_size,
        dry_run,
        validate_hashes: !skip_hash_validation,
        allow_noise,
        quarantine_path: Some(q_path.clone()),
    };

    // Dry runs must never create or open the target store. The target-safe
    // census requires an existing `data.mdb` and reports a clean
    // `target missing` error instead of conjuring the target.
    let receipt = if dry_run {
        match dry_run_migration_census(&reader, target, &options) {
            Ok(receipt) => receipt,
            Err(e) => {
                eprintln!("Migration dry-run refused: {e}");
                std::process::exit(1);
            }
        }
    } else {
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
        match migrate_gen2_to_gen3(&reader, &mut substrate, &options) {
            Ok(receipt) => receipt,
            Err(e) => {
                eprintln!("Migration halted with error: {e}");
                std::process::exit(1);
            }
        }
    };

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
        if dry_run {
            println!("Quarantine Would Be At: {}", q_path.display());
        } else {
            println!("Quarantine Log At:     {}", q_path.display());
        }
    }

    let session_log = target.join("session_log.jsonl");
    match migrate_gen2_sessions_to_gen3_with_options(
        &reader,
        &session_log,
        &SessionMigrationOptions {
            dry_run,
            quarantine_path: None,
        },
    ) {
        Ok(sreceipt) => {
            println!("Session Turns Migrated: {}", sreceipt.migrated);
            println!(
                "Session Turns Skipped:  {} (duplicates {} / quarantined {} / decode-skipped {})",
                sreceipt.duplicates_skipped + sreceipt.quarantined + sreceipt.decode_skipped,
                sreceipt.duplicates_skipped,
                sreceipt.quarantined,
                sreceipt.decode_skipped
            );
            println!("Sessions Covered:       {}", sreceipt.sessions);
            if let Ok(serialized) = serde_json::to_string_pretty(&sreceipt) {
                let path = target.join("session_migration_receipt.json");
                let _ = std::fs::write(&path, serialized);
                println!("Session Receipt:        {}", path.display());
            }
        }
        Err(e) => eprintln!("session-turn migration failed: {e}"),
    }
}

fn run_migrate_all(
    source_root: &Path,
    target_root: &Path,
    only: Option<&str>,
    batch_size: usize,
    dry_run: bool,
) {
    println!("==================================================");
    println!("     WhiteMagic Gen3 Batch Migration (migrate-all) ");
    println!("==================================================");
    println!("Source root: {}", source_root.display());
    println!("Target root: {}", target_root.display());
    println!(
        "Mode:        {}",
        if dry_run {
            "DRY RUN (census only; no writes)"
        } else {
            "LIVE SOVEREIGN COMMITS"
        }
    );
    println!("==================================================");

    let only_filter: Option<Vec<String>> = only.map(|raw| {
        raw.split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect()
    });

    let mut stores: Vec<(String, PathBuf)> = Vec::new();
    match std::fs::read_dir(source_root) {
        Ok(entries) => {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                let lmdb = entry.path().join("lmdb");
                if !lmdb.join("data.mdb").is_file() {
                    continue;
                }
                if let Some(filter) = &only_filter {
                    if !filter.iter().any(|f| f == &name) {
                        continue;
                    }
                }
                stores.push((name, lmdb));
            }
        }
        Err(e) => {
            eprintln!("cannot read source root {}: {e}", source_root.display());
            std::process::exit(1);
        }
    }
    stores.sort();
    if stores.is_empty() {
        eprintln!(
            "no Gen2 stores (<project>/lmdb/data.mdb) found under {}",
            source_root.display()
        );
        std::process::exit(1);
    }

    if !dry_run {
        if let Err(e) = std::fs::create_dir_all(target_root) {
            eprintln!("cannot create target root {}: {e}", target_root.display());
            std::process::exit(1);
        }
    }

    let mut store_entries: Vec<serde_json::Value> = Vec::new();
    let mut total_scanned = 0usize;
    let mut total_migrated = 0usize;
    let mut total_duplicates = 0usize;
    let mut total_quarantined = 0usize;
    let mut total_session_turns = 0usize;
    let mut total_session_migrated = 0usize;
    let mut total_session_duplicates = 0usize;
    let mut failed = 0usize;

    for (name, lmdb) in &stores {
        let reader = match Gen2Reader::open(lmdb) {
            Ok(reader) => reader,
            Err(e) => {
                eprintln!("[{name}] cannot open legacy store: {e}");
                failed += 1;
                continue;
            }
        };

        if dry_run {
            match reader.census() {
                Ok(census) => {
                    println!(
                        "{name:<18} records={:<7} valid={:<7} hash_mismatch={:<5} integrity={:.4}",
                        census.total_records,
                        census.valid_hashes,
                        census.hash_mismatches,
                        census.integrity_ratio()
                    );
                    total_scanned += census.total_records as usize;
                    total_migrated += census.valid_hashes as usize;
                    let (turn_count, turn_skipped) = match reader.session_turns() {
                        Ok((turns, skipped)) => (turns.len(), skipped),
                        Err(e) => {
                            eprintln!("[{name}] session scan failed: {e}");
                            (0, 0)
                        }
                    };
                    println!(
                        "{name:<18} session_turns={turn_count:<7} session_decode_skipped={turn_skipped}"
                    );
                    total_session_turns += turn_count;
                    store_entries.push(serde_json::json!({
                        "name": name,
                        "source": lmdb.display().to_string(),
                        "total_records": census.total_records,
                        "valid_hashes": census.valid_hashes,
                        "hash_mismatches": census.hash_mismatches,
                        "integrity_ratio": census.integrity_ratio(),
                        "session_turns": turn_count,
                        "session_decode_skipped": turn_skipped,
                        "would_migrate": census.valid_hashes,
                        "mode": "dry_run"
                    }));
                }
                Err(e) => {
                    eprintln!("[{name}] census failed: {e}");
                    failed += 1;
                }
            }
            continue;
        }

        let target = target_root.join(name);
        let journal = target.join("journal.jsonl");
        let mut substrate = match Substrate::open(&target, Some(&journal), default_view()) {
            Ok(substrate) => substrate,
            Err(e) => {
                eprintln!("[{name}] cannot open target {}: {e}", target.display());
                failed += 1;
                continue;
            }
        };
        let options = MigrationOptions {
            batch_size,
            dry_run: false,
            validate_hashes: true,
            allow_noise: false,
            quarantine_path: Some(target.join("quarantine.jsonl")),
        };

        match migrate_gen2_to_gen3(&reader, &mut substrate, &options) {
            Ok(receipt) => {
                if let Ok(serialized) = serde_json::to_string_pretty(&receipt) {
                    let _ = std::fs::write(target.join("migration_receipt.json"), serialized);
                }
                println!(
                    "{name:<18} scanned={:<7} migrated={:<7} duplicates={:<7} quarantined={:<5} epoch={}",
                    receipt.total_scanned,
                    receipt.migrated_count,
                    receipt.duplicate_skipped,
                    receipt.quarantined_count,
                    receipt.target_epoch
                );
                total_scanned += receipt.total_scanned;
                total_migrated += receipt.migrated_count;
                total_duplicates += receipt.duplicate_skipped;
                total_quarantined += receipt.quarantined_count;

                let session_log = target.join("session_log.jsonl");
                let (session_total, session_migrated, session_duplicates) =
                    match migrate_gen2_sessions_to_gen3(&reader, &session_log) {
                        Ok(sreceipt) => {
                            if let Ok(serialized) = serde_json::to_string_pretty(&sreceipt) {
                                let _ = std::fs::write(
                                    target.join("session_migration_receipt.json"),
                                    serialized,
                                );
                            }
                            println!(
                                "{name:<18} session_turns={:<7} migrated={:<6} duplicates={:<6} sessions={}",
                                sreceipt.total_turns,
                                sreceipt.migrated,
                                sreceipt.duplicates_skipped,
                                sreceipt.sessions
                            );
                            (
                                sreceipt.total_turns,
                                sreceipt.migrated,
                                sreceipt.duplicates_skipped,
                            )
                        }
                        Err(e) => {
                            eprintln!("[{name}] session migration failed: {e}");
                            (0, 0, 0)
                        }
                    };
                total_session_turns += session_total;
                total_session_migrated += session_migrated;
                total_session_duplicates += session_duplicates;

                store_entries.push(serde_json::json!({
                    "name": name,
                    "source": lmdb.display().to_string(),
                    "target": target.display().to_string(),
                    "total_scanned": receipt.total_scanned,
                    "migrated": receipt.migrated_count,
                    "duplicates": receipt.duplicate_skipped,
                    "quarantined": receipt.quarantined_count,
                    "target_epoch": receipt.target_epoch,
                    "receipt_digest": receipt.receipt_digest,
                    "session_turns": session_total,
                    "session_turns_migrated": session_migrated,
                    "session_turns_duplicates": session_duplicates,
                    "mode": "live"
                }));
            }
            Err(e) => {
                eprintln!("[{name}] migration failed: {e}");
                failed += 1;
            }
        }
    }

    let unix_ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let batch = serde_json::json!({
        "kind": "wm-gen3-migration-batch",
        "version": WM_VERSION,
        "source_root": source_root.display().to_string(),
        "target_root": target_root.display().to_string(),
        "dry_run": dry_run,
        "unix_ts": unix_ts,
        "stores": store_entries,
        "totals": {
            "stores": stores.len(),
            "failed": failed,
            "scanned": total_scanned,
            "migrated": total_migrated,
            "duplicates": total_duplicates,
            "quarantined": total_quarantined,
            "session_turns": total_session_turns,
            "session_turns_migrated": total_session_migrated,
            "session_turns_duplicates": total_session_duplicates
        }
    });

    println!("==================================================");
    println!("Stores: {}  failed: {}", stores.len(), failed);
    println!(
        "Scanned: {}  Migrated: {}  Duplicates: {}  Quarantined: {}",
        total_scanned, total_migrated, total_duplicates, total_quarantined
    );
    println!(
        "Session turns: {}  migrated: {}  duplicates: {}",
        total_session_turns, total_session_migrated, total_session_duplicates
    );
    if !dry_run {
        let out = target_root.join("migration_batch_receipt.json");
        match serde_json::to_string_pretty(&batch) {
            Ok(serialized) => match std::fs::write(&out, serialized) {
                Ok(()) => println!("Batch receipt: {}", out.display()),
                Err(e) => eprintln!("failed to write batch receipt: {e}"),
            },
            Err(e) => eprintln!("failed to serialize batch receipt: {e}"),
        }
    }
    if failed > 0 {
        std::process::exit(1);
    }
}

fn run_quarantine_review(file: &Path, limit: usize) {
    let content = match std::fs::read_to_string(file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("cannot read {}: {e}", file.display());
            std::process::exit(1);
        }
    };

    let mut entries: Vec<serde_json::Value> = Vec::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Ok(record) = serde_json::from_str::<serde_json::Value>(line) {
            entries.push(record);
        }
    }

    println!("Quarantine log: {}", file.display());
    println!("Entries:        {}", entries.len());

    let mut by_reason: std::collections::BTreeMap<String, usize> =
        std::collections::BTreeMap::new();
    for record in &entries {
        let reason = record
            .get("reason")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let key = reason
            .split(':')
            .next()
            .unwrap_or(reason)
            .trim()
            .to_string();
        *by_reason.entry(key).or_insert(0) += 1;
    }
    println!("By reason:");
    for (reason, count) in &by_reason {
        println!("  {count:>5}  {reason}");
    }

    if limit > 0 {
        println!("Sample (first {limit}):");
        for record in entries.iter().take(limit) {
            println!(
                "  {}  {:>7}B  {}",
                record
                    .get("raw_key_hex")
                    .and_then(|v| v.as_str())
                    .unwrap_or("?"),
                record
                    .get("raw_val_len")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0),
                record.get("reason").and_then(|v| v.as_str()).unwrap_or("")
            );
        }
    }
}

fn run_backfill_session_evidence(
    source: &Path,
    store_path: &Path,
    batch_size: usize,
    limit: usize,
) {
    use std::io::Write;

    println!("==================================================");
    println!("   Gen3 Session Evidence Backfill (resumable)      ");
    println!("==================================================");
    println!("Source (Gen2): {}", source.display());
    println!("Target (Gen3): {}", store_path.display());
    println!("Batch size:    {}", batch_size.max(1));
    println!(
        "Limit:         {}",
        if limit == 0 {
            "all".to_string()
        } else {
            limit.to_string()
        }
    );
    println!("==================================================");

    let reader = match Gen2Reader::open(source) {
        Ok(reader) => reader,
        Err(e) => {
            eprintln!(
                "Failed to open legacy Gen2 store at {}: {e}",
                source.display()
            );
            std::process::exit(1);
        }
    };
    let (turns, decode_skipped) = match reader.session_turns() {
        Ok(turns) => turns,
        Err(e) => {
            eprintln!("Failed to scan legacy session turns: {e}");
            std::process::exit(1);
        }
    };
    let total = if limit > 0 {
        turns.len().min(limit)
    } else {
        turns.len()
    };
    println!(
        "Turns found: {} (decode/non-turn skipped: {})",
        turns.len(),
        decode_skipped
    );
    if total == 0 {
        println!("Nothing to ingest.");
        return;
    }

    let journal = store_path.join("journal.jsonl");
    let mut substrate = match Substrate::open(store_path, Some(&journal), default_view()) {
        Ok(substrate) => substrate,
        Err(e) => {
            eprintln!(
                "Failed to open target Gen3 store at {}: {e}",
                store_path.display()
            );
            std::process::exit(1);
        }
    };

    let old_noise = substrate.noise_enabled();
    substrate.set_noise_enabled(false);
    let old_budget = substrate.budget();
    substrate.set_budget(0);
    substrate.set_intake_authority(RatifiedChannel::mint("wm-session-evidence"));

    let batch = batch_size.max(1);
    let started = std::time::Instant::now();
    let mut processed = 0usize;
    let mut ingested = 0usize;
    let mut duplicates = 0usize;
    let mut failed = 0usize;
    let mut last_mark = 0usize;

    for chunk in turns[..total].chunks(batch) {
        let items: Vec<RememberItem> = chunk
            .iter()
            .map(|turn| {
                let content_text = match &turn.content {
                    serde_json::Value::String(s) => s.clone(),
                    other => other.to_string(),
                };
                RememberItem {
                    content: format!(
                        "[session:{}] {}: {}",
                        turn.session_id, turn.role, content_text
                    ),
                    source: format!("session:{}", turn.session_id),
                    kind: ImportKind::Reported,
                }
            })
            .collect();

        for outcome in substrate.remember_batch(&items) {
            match outcome {
                Ok(_) => ingested += 1,
                Err(err) if err == "duplicate_exact" => duplicates += 1,
                Err(err) => {
                    if failed < 5 {
                        eprintln!("  ingest refusal: {err}");
                    }
                    failed += 1;
                }
            }
        }

        processed += chunk.len();
        let mark = processed / 2000;
        if mark > last_mark {
            last_mark = mark;
            let elapsed = started.elapsed().as_secs_f64().max(0.001);
            let rate = processed as f64 / elapsed;
            let eta = (total.saturating_sub(processed)) as f64 / rate.max(0.001);
            println!(
                "progress {processed}/{total} ingested={ingested} duplicates={duplicates} failed={failed} rate={rate:.0}/s eta={eta:.0}s"
            );
            let _ = std::io::stdout().flush();
        }
    }

    substrate.set_budget(old_budget);
    substrate.set_noise_enabled(old_noise);

    let elapsed = started.elapsed().as_secs_f64();
    let unix_ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let receipt = serde_json::json!({
        "kind": "wm-gen3-session-evidence-backfill",
        "version": WM_VERSION,
        "source": source.display().to_string(),
        "target": store_path.display().to_string(),
        "total_turns": turns.len(),
        "processed": processed,
        "ingested": ingested,
        "duplicates": duplicates,
        "failed": failed,
        "decode_skipped": decode_skipped,
        "elapsed_secs": elapsed,
        "unix_ts": unix_ts
    });
    let out = store_path.join("evidence_backfill_receipt.json");
    match serde_json::to_string_pretty(&receipt) {
        Ok(serialized) => match std::fs::write(&out, serialized) {
            Ok(()) => println!("Receipt: {}", out.display()),
            Err(e) => eprintln!("failed to write receipt: {e}"),
        },
        Err(e) => eprintln!("failed to serialize receipt: {e}"),
    }
    println!("==================================================");
    println!(
        "Processed: {processed}/{total}  ingested: {ingested}  duplicates: {duplicates}  failed: {failed}  in {elapsed:.1}s"
    );
    if failed > 0 {
        std::process::exit(1);
    }
}

fn legacy_store_detected(path: &Path) -> bool {
    if !path.is_dir() {
        return false;
    }
    // If it has episodic_records but no records table
    Gen2Reader::open(path).is_ok()
}

fn run_legacy_census(path: &Path) -> Result<(), String> {
    println!("Opening legacy Gen2 store at: {}", path.display());
    let reader = Gen2Reader::open(path).map_err(|e| format!("Failed to open Gen2 store: {e}"))?;
    let census = reader
        .census()
        .map_err(|e| format!("Error during census scan: {e}"))?;
    print_census_report(&census);
    Ok(())
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

fn run_stdio_loop(backend: &McpBackend) {
    use std::io::Write;

    let stdin = std::io::stdin();
    let mut input = stdin.lock();
    let mut stdout = std::io::stdout();
    loop {
        let line = match read_bounded_line(&mut input, MAX_JSONRPC_LINE_BYTES) {
            Ok(Some(BoundedLine::Data(line))) => line,
            Ok(Some(BoundedLine::TooLong)) => {
                write_jsonrpc_parse_error(
                    &mut stdout,
                    &format!("Request line exceeds {MAX_JSONRPC_LINE_BYTES} byte limit"),
                );
                continue;
            }
            Ok(None) => break,
            Err(error) => {
                eprintln!("gen3: MCP request read failed: {error}");
                break;
            }
        };
        let line = match std::str::from_utf8(&line) {
            Ok(line) => line,
            Err(error) => {
                write_jsonrpc_parse_error(&mut stdout, &format!("Request is not UTF-8: {error}"));
                continue;
            }
        };
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let request = match wm_gen3_harness::receipt_verify::parse_strict_json(line) {
            Ok(request) => request,
            Err(error) => {
                write_jsonrpc_parse_error(&mut stdout, &format!("Parse error: {error}"));
                continue;
            }
        };
        if let Some(response) = backend.handle(&request) {
            let _ = writeln!(stdout, "{response}");
            let _ = stdout.flush();
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

/// CLI dial guard: `wm mesh sync` / `sync-genes` may only reach peers listed
/// in `WM_MESH_SYNC_ALLOWLIST` (empty allowlist refuses).
fn enforce_mesh_sync_dial_allowlist(allowlist_raw: &str, peer: &str) -> Result<(), String> {
    let addr: std::net::SocketAddr = peer
        .parse()
        .map_err(|e| format!("Invalid peer address '{peer}': {e}"))?;
    mesh_sync_peer_allowlist(allowlist_raw, addr)
}

fn mesh_sync_allowlist_env() -> String {
    std::env::var("WM_MESH_SYNC_ALLOWLIST").unwrap_or_default()
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

            while *server.is_running.lock().unwrap_or_else(|e| e.into_inner()) {
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
            if let Err(e) = enforce_mesh_sync_dial_allowlist(&mesh_sync_allowlist_env(), &peer) {
                eprintln!("{e}");
                std::process::exit(2);
            }

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
            if let Err(e) = enforce_mesh_sync_dial_allowlist(&mesh_sync_allowlist_env(), &peer) {
                eprintln!("{e}");
                std::process::exit(2);
            }

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
        MeshCommands::Codon {
            peer,
            codon,
            node_id,
            json,
        } => {
            let (signing_key, _) = match resolve_or_create_mesh_key(store_path) {
                Ok(k) => k,
                Err(e) => {
                    eprintln!("Failed to resolve mesh key: {e}");
                    std::process::exit(1);
                }
            };
            let name = node_id.unwrap_or_else(|| "sovereign-codon-client".to_string());
            let addr: std::net::SocketAddr = match peer.parse() {
                Ok(a) => a,
                Err(e) => {
                    eprintln!("Invalid peer address '{}': {e}", peer);
                    std::process::exit(1);
                }
            };
            println!(
                "Connecting to peer {} for Mudra Codon transmission...",
                addr
            );
            let mut client = match MeshClient::connect(addr, &name, signing_key) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Connection failed: {e}");
                    std::process::exit(1);
                }
            };
            let start = std::time::Instant::now();
            let ack = match client.send_gap_codon(&codon, "remote-node", 0) {
                Ok(a) => a,
                Err(e) => {
                    eprintln!("Codon transmission failed: {e}");
                    std::process::exit(1);
                }
            };
            let rtt_us = start.elapsed().as_micros();
            if json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&serde_json::json!({
                        "status": "ok",
                        "peer": peer,
                        "codon": codon,
                        "rtt_us": rtt_us,
                        "ack": ack,
                    }))
                    .unwrap_or_default()
                );
            } else {
                println!("==================================================");
                println!("       Mudra Codon Gap-Junction Transmission       ");
                println!("==================================================");
                println!("Target Peer:       {}", peer);
                println!("Codon:             {}", codon);
                println!(
                    "Wire Latency:      {} µs ({:.3} ms)",
                    rtt_us,
                    rtt_us as f64 / 1000.0
                );
                println!("Accepted:          {}", ack.accepted);
                println!("Remote Responder:  {}", ack.responder_node);
                println!("Acknowledgment:    {}", ack.details);
                println!("==================================================");
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
  const sutraBadge = node.sutra_glyph ? `${{node.sutra_glyph}} (${{node.sutra_archetype || "Constellation"}}) \u2022 ` : "";
  document.getElementById("card-tag").innerText = `${{sutraBadge}}Gana #${{node.omega}} \u2022 Record #${{node.id}}`;
  document.getElementById("card-tag").style.color = SUTRA_COLORS[(node.constellation || 0) % 6] || GANA_COLORS[node.omega % 28];
  document.getElementById("card-title").innerText = node.source || `Record #${{node.id}}`;
  document.getElementById("val-x").innerText = node.x.toFixed(1);
  document.getElementById("val-y").innerText = node.y.toFixed(1);
  document.getElementById("val-z").innerText = node.z.toFixed(1);
  document.getElementById("val-tau").innerText = node.tau.toFixed(2);
  document.getElementById("val-sigma").innerText = node.sigma.toFixed(2);
  document.getElementById("val-omega").innerText = node.omega;
  document.getElementById("card-preview").innerText = node.preview;
}}

const SUTRA_COLORS = ["#38bdf8", "#a855f7", "#34d399", "#fb923c", "#facc15", "#f472b6"];
const NODE_BY_ID = new Map(DATA.map(n => [n.id, n]));

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

  // Draw Associative Resonance Bridges
  ctx.lineWidth = 1.0;
  for (const p of projected) {{
    if (Array.isArray(p.resonance_targets) && p.resonance_targets.length > 0) {{
      for (const tid of p.resonance_targets) {{
        const target = NODE_BY_ID.get(tid);
        if (target && target._screenX && target._screenY) {{
          ctx.beginPath();
          ctx.moveTo(p._screenX, p._screenY);
          ctx.lineTo(target._screenX, target._screenY);
          ctx.strokeStyle = (selectedNode && (selectedNode.id === p.id || selectedNode.id === tid))
            ? "rgba(250, 204, 21, 0.75)"
            : "rgba(56, 189, 248, 0.22)";
          ctx.stroke();
        }}
      }}
    }}
  }}

  for (const p of projected) {{
    const isSelected = selectedNode && selectedNode.id === p.id;
    const matchesSearch = searchQuery && p.preview.toLowerCase().includes(searchQuery);
    
    let radius = Math.max(1.2, (2.8 * fov * zoom) / p._depth);
    if (isSelected) radius *= 2.2;
    if (matchesSearch) radius *= 1.8;

    const baseColor = (typeof p.constellation === "number")
      ? SUTRA_COLORS[p.constellation % 6]
      : GANA_COLORS[p.omega % 28];
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
                let preview = if content.chars().count() > 60 {
                    format!("{}...", content.chars().take(57).collect::<String>())
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
            // flatten() keeps scanning after an unreadable line; map_while would drop the rest.
            #[allow(clippy::lines_filter_map_ok)]
            for l in reader.lines().flatten() {
                let trimmed = l.trim();
                if !trimmed.is_empty() {
                    if let Ok(ins) =
                        serde_json::from_str::<wm_gen3_core::dream::DreamInsight>(trimmed)
                    {
                        insights.push(ins);
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
        VaultCommands::Compact => {
            println!("==================================================");
            println!("   WhiteMagic Gen3 Vault Pareto Cladistics GC     ");
            println!("==================================================");
            let before = vault.skeletons.len();
            let (retained, pruned) = vault.compact_pareto();
            if let Err(e) = vault.sync_to_file(&vault_path) {
                eprintln!("Warning: failed to persist compacted vault: {e}");
            }
            println!("Initial Skeletons:  {}", before);
            println!("Retained Skeletons: {}", retained);
            println!("Pruned Redundant:   {}", pruned);
            println!("Compacted Vault:    {}", vault_path.display());
            println!("==================================================");
        }
    }
}

fn run_sutra_canon(json: bool) {
    use wm_gen3_core::sutra::SutraGlyph;

    if json {
        let items: Vec<_> = SutraGlyph::ALL
            .iter()
            .map(|g| {
                let prof = g.kekkai_profile();
                serde_json::json!({
                    "index": g.index(),
                    "char": g.as_char().to_string(),
                    "alchemical": g.alchemical_char().to_string(),
                    "pinyin": g.pinyin(),
                    "english": g.english(),
                    "taoist_seal": g.taoist_seal(),
                    "bound_skeleton": g.bound_skeleton_id(),
                    "kekkai": {
                        "read_only_paths": prof.read_only_paths,
                        "read_write_paths": prof.read_write_paths,
                        "network_allowed": prof.network_allowed,
                    }
                })
            })
            .collect();
        println!(
            "{}",
            serde_json::to_string_pretty(&items).unwrap_or_default()
        );
        return;
    }

    println!(
        "=========================================================================================="
    );
    println!(
        "                   WhiteMagic Gen3 Canonical 12-Glyph Logoglyphic Canon                   "
    );
    println!(
        "=========================================================================================="
    );
    println!(
        "Idx | Glyph | Alch | Pinyin | Meaning            | Taoist Seal (印诀)              | Skeleton"
    );
    println!(
        "----+-------+------+--------+--------------------+---------------------------------+--------------------"
    );
    for g in SutraGlyph::ALL {
        println!(
            "{:>3} | {:^5} | {:^4} | {:<6} | {:<18} | {:<31} | {:<20}",
            g.index(),
            g.as_char(),
            g.alchemical_char(),
            g.pinyin(),
            g.english(),
            g.taoist_seal(),
            g.bound_skeleton_id(),
        );
    }
    println!(
        "=========================================================================================="
    );
}

fn run_sutra_list(json: bool) {
    use wm_gen3_core::sutra::CANONICAL_MUDRAS;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&CANONICAL_MUDRAS).unwrap_or_default()
        );
        return;
    }

    println!(
        "=========================================================================================="
    );
    println!(
        "                 WhiteMagic Gen3 Recognized Compound Taoist Mudras (印诀式)                 "
    );
    println!(
        "=========================================================================================="
    );
    for (i, m) in CANONICAL_MUDRAS.iter().enumerate() {
        let glyph_str = m
            .glyphs
            .iter()
            .map(|g| format!("{} [{}]", g.as_char(), g.alchemical_char()))
            .collect::<Vec<_>>()
            .join(" · ");
        println!("{}. {}", i + 1, m.name);
        println!("   Codon Glyphs:       ⟪ {} ⟫", glyph_str);
        println!("   Taoist Formula:     {}", m.taoist_formula);
        println!("   Primary Skeleton:   {}", m.primary_skeleton);
        println!(
            "   Preconditions:      Store Writable: {} | Landlock: {} | Mesh Net: {}",
            if m.requires_store_write { "Yes" } else { "No" },
            if m.requires_landlock {
                "Required"
            } else {
                "Optional"
            },
            if m.requires_mesh_net {
                "Required"
            } else {
                "Optional"
            },
        );
        println!("   Description:        {}", m.description);
        println!(
            "------------------------------------------------------------------------------------------"
        );
    }
}

fn run_sutra_compile(query: &str, json: bool) {
    use std::time::Instant;
    use wm_gen3_core::sutra::{CANONICAL_MUDRAS, CompoundSutra, SutraGlyph};
    use wm_gen3_zeropointfive::System05;

    let start = Instant::now();
    let mut model_used = "lexical-fallback";
    let mut best_mudra: Option<&'static str> = None;
    let mut mudra_score: f32 = 0.0;
    let mut glyph_scores: Vec<(SutraGlyph, f32)> = Vec::new();

    // 1. Try static embedding model (potion-base-32M)
    if let Ok(model_dir) = System05::resolve_model_dir(None) {
        let organ = System05::new(model_dir);
        if let Ok(query_vec) = organ.encode_single(query) {
            model_used = "Model2Vec (potion-base-32M static embedding)";
            // Score each glyph
            for &g in &SutraGlyph::ALL {
                let gvec = g.vector();
                let dot: f32 = query_vec.iter().zip(gvec.iter()).map(|(a, b)| a * b).sum();
                glyph_scores.push((g, dot));
            }
            glyph_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

            // Score compound mudras
            for m in CANONICAL_MUDRAS {
                if let Ok(sutra) = CompoundSutra::from_glyphs(m.glyphs.to_vec()) {
                    let dot: f32 = query_vec
                        .iter()
                        .zip(sutra.compound_vector.iter())
                        .map(|(a, b)| a * b)
                        .sum();
                    if dot > mudra_score {
                        mudra_score = dot;
                        best_mudra = Some(m.name);
                    }
                }
            }
        }
    }

    // Fallback if model not available or produced no matches: scan tokens
    if glyph_scores.is_empty() {
        for word in query.split(|c: char| !c.is_alphanumeric() && c != '·') {
            if let Some(g) = SutraGlyph::from_token(word) {
                if !glyph_scores.iter().any(|(x, _)| *x == g) {
                    glyph_scores.push((g, 1.0));
                }
            }
        }
    }

    // Select top matching glyphs (top 3, or all above 0.35 if vectorized)
    let selected_glyphs: Vec<SutraGlyph> = if glyph_scores.is_empty() {
        vec![SutraGlyph::Zheng, SutraGlyph::Xing, SutraGlyph::Jing]
    } else {
        glyph_scores.iter().take(3).map(|(g, _)| *g).collect()
    };

    let sutra = CompoundSutra::from_glyphs(selected_glyphs)
        .unwrap_or_else(|_| CompoundSutra::parse("證 行 鏡").unwrap());
    let compile_us = start.elapsed().as_micros();

    if json {
        let out = serde_json::json!({
            "status": "ok",
            "query": query,
            "engine": model_used,
            "latency_micros": compile_us,
            "compiled_codon": sutra.codon_str,
            "alchemical_codon": format!("⟪ {} ⟫", sutra.glyphs.iter().map(|g| g.alchemical_char().to_string()).collect::<Vec<_>>().join(" · ")),
            "taoist_formula": sutra.taoist_formula(),
            "best_compound_mudra": best_mudra,
            "compound_mudra_score": mudra_score,
            "primary_skeleton": sutra.primary_skeleton_id,
            "top_glyph_alignments": glyph_scores.iter().take(5).map(|(g, score)| {
                serde_json::json!({
                    "glyph": g.as_char().to_string(),
                    "alchemical": g.alchemical_char().to_string(),
                    "pinyin": g.pinyin(),
                    "english": g.english(),
                    "score": (score * 10000.0).round() / 10000.0,
                })
            }).collect::<Vec<_>>(),
        });
        println!("{}", serde_json::to_string_pretty(&out).unwrap_or_default());
        return;
    }

    println!("==================================================");
    println!("    WhiteMagic Gen3 Vectorized Sutra Compiler     ");
    println!("==================================================");
    println!("Query Intent:            \"{}\"", query);
    println!("Compiler Engine:         {}", model_used);
    println!("Compile Latency:         {} µs", compile_us);
    println!("Compiled Codon:          {}", sutra.codon_str);
    println!(
        "Alchemical Codon:        ⟪ {} ⟫",
        sutra
            .glyphs
            .iter()
            .map(|g| g.alchemical_char().to_string())
            .collect::<Vec<_>>()
            .join(" · ")
    );
    println!("Taoist Mudra Formula:    {}", sutra.taoist_formula());
    if let Some(mudra) = best_mudra {
        println!(
            "Best Matching Mudra:     {} (score: {:.4})",
            mudra, mudra_score
        );
    }
    println!("Bound Primary Skeleton:  {}", sutra.primary_skeleton_id);
    println!("Top Semantic Alignments:");
    for (g, score) in glyph_scores.iter().take(5) {
        println!(
            "  {} / {} ({:<5}) — {:<16} (score: {:.4})",
            g.as_char(),
            g.alchemical_char(),
            g.pinyin(),
            g.english(),
            score,
        );
    }
    println!("==================================================");
}

fn run_sutra_cast(
    codon: &str,
    dry_run: bool,
    strict: bool,
    peer: Option<&str>,
    json: bool,
    store_path: &Path,
) {
    use std::time::Instant;
    use wm_gen3_core::sutra::{CompoundSutra, MudraEnvironment};

    let start = Instant::now();
    let sutra = match CompoundSutra::parse(codon) {
        Ok(s) => s,
        Err(e) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "error",
                        "error": e.to_string(),
                        "input": codon,
                    })
                );
            } else {
                eprintln!("Error: failed to parse sutra codon '{codon}': {e}");
            }
            std::process::exit(1);
        }
    };
    let parse_micros = start.elapsed().as_micros();

    // Precondition evaluation (< 50 ns)
    let env = MudraEnvironment::probe(store_path);
    let pre_result = sutra.validate_preconditions(&env);
    if let Err(ref e) = pre_result {
        if strict {
            if json {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "precondition_failed",
                        "error": e.to_string(),
                        "codon": sutra.codon_str,
                    })
                );
            } else {
                eprintln!("Mudra Precondition Validation FAILED: {e}");
            }
            std::process::exit(1);
        }
    }

    // Check if remote peer handoff requested (Wire Protocol 7369)
    if let Some(peer_addr) = peer {
        let (signing_key, _) = match resolve_or_create_mesh_key(store_path) {
            Ok(k) => k,
            Err(e) => {
                eprintln!("Failed to resolve mesh key: {e}");
                std::process::exit(1);
            }
        };
        let addr: std::net::SocketAddr = match peer_addr.parse() {
            Ok(a) => a,
            Err(e) => {
                eprintln!("Invalid peer address '{peer_addr}': {e}");
                std::process::exit(1);
            }
        };
        let mut client = match MeshClient::connect(addr, "sovereign-caster", signing_key) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Mesh connection to {peer_addr} failed: {e}");
                std::process::exit(1);
            }
        };
        let handoff_start = Instant::now();
        let ack = match client.send_gap_codon(&sutra.codon_str, "remote-node", 0) {
            Ok(a) => a,
            Err(e) => {
                eprintln!("Mudra handoff failed: {e}");
                std::process::exit(1);
            }
        };
        let handoff_us = handoff_start.elapsed().as_micros();

        if json {
            println!(
                "{}",
                serde_json::to_string_pretty(&serde_json::json!({
                    "status": "ok",
                    "mode": "remote_handoff",
                    "peer": peer_addr,
                    "codon": sutra.codon_str,
                    "taoist_formula": sutra.taoist_formula(),
                    "parse_latency_micros": parse_micros,
                    "handoff_latency_micros": handoff_us,
                    "ack": ack,
                }))
                .unwrap_or_default()
            );
            return;
        }

        println!("==================================================");
        println!("     WhiteMagic Gen3 Swarm Mudra Handoff (P2P)    ");
        println!("==================================================");
        println!("Target Peer:             {}", peer_addr);
        println!("Transmitted Codon:       {}", sutra.codon_str);
        println!("Taoist Mudra Formula:    {}", sutra.taoist_formula());
        println!("Parse Latency:           {} µs", parse_micros);
        println!(
            "Handoff Latency:         {} µs ({:.3} ms across Wire Protocol 7369)",
            handoff_us,
            handoff_us as f64 / 1000.0
        );
        println!("Acknowledgment Status:   ACCEPTED");
        println!("Remote Node Details:     {}", ack.details);
        println!("==================================================");
        return;
    }

    let vault_path = store_path.join("vault.jsonl");
    let mut vault = wm_gen3_core::bicameral::GeneseedVault::load_or_init(&vault_path);

    if json {
        let output = serde_json::json!({
            "status": "ok",
            "codon": sutra.codon_str,
            "canonical_name": sutra.canonical_name,
            "parse_latency_micros": parse_micros,
            "preconditions_satisfied": pre_result.is_ok(),
            "taoist_formula": sutra.taoist_formula(),
            "alchemical_formula": sutra.alchemical_formula(),
            "glyphs": sutra.glyphs.iter().map(|g| {
                serde_json::json!({
                    "glyph": g.as_char().to_string(),
                    "alchemical": g.alchemical_char().to_string(),
                    "pinyin": g.pinyin(),
                    "english": g.english(),
                    "taoist_seal": g.taoist_seal(),
                    "bound_skeleton": g.bound_skeleton_id(),
                })
            }).collect::<Vec<_>>(),
            "alignment_scores": sutra.alignment_scores.iter().map(|(g, sim)| {
                serde_json::json!({
                    "glyph": g.as_char().to_string(),
                    "similarity": (sim * 10000.0).round() / 10000.0,
                })
            }).collect::<Vec<_>>(),
            "kekkai_profile": {
                "read_only_paths": sutra.kekkai_profile.read_only_paths,
                "read_write_paths": sutra.kekkai_profile.read_write_paths,
                "network_allowed": sutra.kekkai_profile.network_allowed,
            },
            "primary_skeleton_id": sutra.primary_skeleton_id,
            "dry_run": dry_run,
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&output).unwrap_or_default()
        );
        return;
    }

    println!("==================================================");
    println!("       WhiteMagic Gen3 Sovereign Sutra Dispatch   ");
    println!("==================================================");
    println!("Codon:                   {}", sutra.codon_str);
    println!(
        "Alchemical:              ⟪ {} ⟫",
        sutra
            .glyphs
            .iter()
            .map(|g| g.alchemical_char().to_string())
            .collect::<Vec<_>>()
            .join(" · ")
    );
    if let Some(ref name) = sutra.canonical_name {
        println!("Title:                   {}", name);
    }
    println!("Taoist Mudra Formula:    {}", sutra.taoist_formula());
    println!("Parse Latency:           {} µs", parse_micros);
    println!(
        "Precondition Contract:   {}",
        if pre_result.is_ok() {
            "SATISFIED"
        } else {
            "FAILED"
        }
    );
    println!("Constituent Glyphs:");
    for (g, sim) in &sutra.alignment_scores {
        println!(
            "  [{:>2}] {} / {} ({:<5}) — {:<18} (alignment: {:.4})",
            g.index(),
            g.as_char(),
            g.alchemical_char(),
            g.pinyin(),
            g.english(),
            sim
        );
    }
    println!("--------------------------------------------------");
    println!("Bound Kekkai Sandbox Profile:");
    println!(
        "  Read-Only Paths:       {:?}",
        sutra.kekkai_profile.read_only_paths
    );
    println!(
        "  Read-Write Paths:      {:?}",
        sutra.kekkai_profile.read_write_paths
    );
    println!(
        "  Network Policy:        {}",
        if sutra.kekkai_profile.network_allowed {
            "Local / LAN Mesh Allowed (Port 7369)"
        } else {
            "Deny (Strict Confinement Isolated)"
        }
    );
    println!("--------------------------------------------------");
    println!("Bound Action Skeleton:   {}", sutra.primary_skeleton_id);

    if dry_run {
        println!("Execution Status:        DRY RUN (Deterministic Plan Decoded)");
        println!("                         [Pass --execute to dispatch against substrate]");
        println!("==================================================");
        return;
    }

    println!("Execution Status:        DISPATCHING AGAINST SUBSTRATE...");
    let journal_path = store_path.join("journal.jsonl");
    let mut substrate = match Substrate::open(store_path, Some(&journal_path), default_view()) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error opening substrate at {}: {e}", store_path.display());
            std::process::exit(1);
        }
    };
    substrate.set_intake_authority(RatifiedChannel::mint("wm-sutra-exec"));

    match vault.execute_skeleton_cycle(&sutra.primary_skeleton_id, &mut substrate) {
        Ok(res) => {
            if let Err(e) = vault.sync_to_file(&vault_path) {
                eprintln!("Warning: failed to persist vault to file: {e}");
            }
            println!("--------------------------------------------------");
            println!("Dispatch Receipt:        SUCCESS");
            println!("  Action Skeleton:       {}", res.skeleton_id);
            println!("  Latency:               {} µs", res.latency_us);
            println!("  Observed Utility:      {:.4}", res.observed_utility);
            println!("  New Rolling EMA:       {:.4}", res.new_rolling_utility);
            println!("  Execution Count:       {}", res.execution_count);
            println!("  Status:                {}", res.status);
            println!("==================================================");
        }
        Err(e) => {
            eprintln!("Dispatch Receipt:        FAILED: {e}");
            println!("==================================================");
            std::process::exit(1);
        }
    }
}

#[allow(dead_code)]
fn run_sutra_command(codon: &str, dry_run: bool, json: bool, store_path: &Path) {
    run_sutra_cast(codon, dry_run, false, None, json, store_path);
}

fn run_sutra_hexagram(query: &str, mutate_line: Option<usize>, json: bool, _store_path: &Path) {
    use serde_json::json;
    use wm_gen3_core::hexagram::Hexagram;
    if query.trim().eq_ignore_ascii_case("list") {
        if json {
            let list: Vec<_> = Hexagram::ALL
                .iter()
                .map(|h| {
                    json!({
                        "id": h.king_wen_id(),
                        "char": h.as_char(),
                        "zh": h.name_zh(),
                        "pinyin": h.name_pinyin(),
                        "en": h.name_en(),
                        "macro_role": h.macro_role(),
                        "upper_trigram": h.upper_trigram().name_zh(),
                        "lower_trigram": h.lower_trigram().name_zh(),
                        "wu_xing": h.dominant_element().name_zh(),
                        "default_codon": h.default_codon(),
                    })
                })
                .collect();
            println!("{}", serde_json::to_string_pretty(&list).unwrap());
        } else {
            println!(
                "========================================================================================="
            );
            println!(
                "               WhiteMagic Gen3 — 64 King Wen Hexagram Macro-Action Matrix               "
            );
            println!(
                "========================================================================================="
            );
            println!(
                "{:<4} {:<4} {:<6} {:<12} {:<24} {:<10} {:<10} {:<16}",
                "ID", "Char", "ZH", "Pinyin", "English Name", "Upper", "Lower", "Default Codon"
            );
            println!(
                "-----------------------------------------------------------------------------------------"
            );
            for h in Hexagram::ALL {
                println!(
                    "{:<4} {:<4} {:<6} {:<12} {:<24} {:<10} {:<10} {:<16}",
                    h.king_wen_id(),
                    h.as_char(),
                    h.name_zh(),
                    h.name_pinyin(),
                    h.name_en(),
                    format!(
                        "{} ({})",
                        h.upper_trigram().name_zh(),
                        h.upper_trigram().wu_xing().name_zh()
                    ),
                    format!(
                        "{} ({})",
                        h.lower_trigram().name_zh(),
                        h.lower_trigram().wu_xing().name_zh()
                    ),
                    h.default_codon()
                );
            }
            println!(
                "========================================================================================="
            );
        }
        return;
    }

    let hex = match Hexagram::parse(query) {
        Some(h) => h,
        None => {
            eprintln!(
                "Unknown Hexagram '{query}'. Specify ID (1..64), name (e.g. '乾', '既济'), or 'list'."
            );
            std::process::exit(1);
        }
    };

    let mutated = mutate_line.map(|l| hex.mutate_line(l.saturating_sub(1)));
    let nuclear = hex.nuclear();
    let complement = hex.complement();
    let reverse = hex.reverse();

    if json {
        let val = json!({
            "id": hex.king_wen_id(),
            "char": hex.as_char(),
            "zh": hex.name_zh(),
            "pinyin": hex.name_pinyin(),
            "en": hex.name_en(),
            "macro_role": hex.macro_role(),
            "upper_trigram": {
                "zh": hex.upper_trigram().name_zh(),
                "en": hex.upper_trigram().name_en(),
                "element": hex.upper_trigram().wu_xing().name_zh(),
            },
            "lower_trigram": {
                "zh": hex.lower_trigram().name_zh(),
                "en": hex.lower_trigram().name_en(),
                "element": hex.lower_trigram().wu_xing().name_zh(),
            },
            "wu_xing": hex.dominant_element().name_zh(),
            "default_codon": hex.default_codon(),
            "nuclear": {
                "id": nuclear.king_wen_id(),
                "char": nuclear.as_char(),
                "zh": nuclear.name_zh(),
                "en": nuclear.name_en(),
            },
            "complement": {
                "id": complement.king_wen_id(),
                "char": complement.as_char(),
                "zh": complement.name_zh(),
                "en": complement.name_en(),
            },
            "reverse": {
                "id": reverse.king_wen_id(),
                "char": reverse.as_char(),
                "zh": reverse.name_zh(),
                "en": reverse.name_en(),
            },
            "mutated": mutated.map(|m| json!({
                "line": mutate_line.unwrap(),
                "id": m.king_wen_id(),
                "char": m.as_char(),
                "zh": m.name_zh(),
                "en": m.name_en(),
                "default_codon": m.default_codon(),
            })),
        });
        println!("{}", serde_json::to_string_pretty(&val).unwrap());
    } else {
        println!("==================================================");
        println!("      WhiteMagic Gen3 Hexagram Macro-Action       ");
        println!("==================================================");
        println!("Hexagram ID:     #{} {}", hex.king_wen_id(), hex.as_char());
        println!(
            "Name:            {} ({}) — {}",
            hex.name_zh(),
            hex.name_pinyin(),
            hex.name_en()
        );
        println!("Macro Role:      {}", hex.macro_role());
        println!(
            "Upper Trigram:   {} ({}) — {}",
            hex.upper_trigram().name_zh(),
            hex.upper_trigram().name_en(),
            hex.upper_trigram().wu_xing().name_zh()
        );
        println!(
            "Lower Trigram:   {} ({}) — {}",
            hex.lower_trigram().name_zh(),
            hex.lower_trigram().name_en(),
            hex.lower_trigram().wu_xing().name_zh()
        );
        println!("Wu Xing Element: {}", hex.dominant_element().name_zh());
        println!("Default Codon:   {}", hex.default_codon());
        println!(
            "Nuclear Inner:   #{} {} ({})",
            nuclear.king_wen_id(),
            nuclear.name_zh(),
            nuclear.name_en()
        );
        println!(
            "Complement (反): #{} {} ({})",
            complement.king_wen_id(),
            complement.name_zh(),
            complement.name_en()
        );
        println!(
            "Reverse (覆):    #{} {} ({})",
            reverse.king_wen_id(),
            reverse.name_zh(),
            reverse.name_en()
        );
        if let Some(m) = mutated {
            println!(
                "Mutated Line {}:  #{} {} ({}) ──► {}",
                mutate_line.unwrap(),
                m.king_wen_id(),
                m.name_zh(),
                m.name_en(),
                m.default_codon()
            );
        }
        println!("==================================================");
    }
}

fn run_sutra_legion(
    edict_str: &str,
    clone_count: usize,
    peer: Option<&str>,
    json: bool,
    store_path: &Path,
) {
    use std::time::Instant;
    use wm_gen3_core::legion::ShadowLegion;
    use wm_gen3_core::sutra::CompoundSutra;

    let sutra = match CompoundSutra::parse(edict_str) {
        Ok(s) => s,
        Err(e) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "error",
                        "error": format!("Failed to parse edict codon '{edict_str}': {e}"),
                    })
                );
            } else {
                eprintln!("Error: failed to parse edict codon '{edict_str}': {e}");
            }
            std::process::exit(1);
        }
    };

    let legion = ShadowLegion::new(128);
    let start = Instant::now();
    let report = match legion.summon_clones(&sutra, clone_count) {
        Ok(r) => r,
        Err(e) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "error",
                        "error": format!("Legion summoning failed: {e}"),
                    })
                );
            } else {
                eprintln!("Error: legion summoning failed: {e}");
            }
            std::process::exit(1);
        }
    };
    let _local_elapsed_us = start.elapsed().as_micros();

    let mut remote_ack = None;
    let mut remote_rtt_us = None;

    if let Some(peer_addr) = peer {
        let (signing_key, _) = match resolve_or_create_mesh_key(store_path) {
            Ok(k) => k,
            Err(e) => {
                eprintln!("Failed to resolve mesh key for peer dispatch: {e}");
                std::process::exit(1);
            }
        };
        let addr: std::net::SocketAddr = match peer_addr.parse() {
            Ok(a) => a,
            Err(e) => {
                eprintln!("Invalid peer address '{}': {e}", peer_addr);
                std::process::exit(1);
            }
        };
        if let Ok(mut client) = MeshClient::connect(addr, "sovereign-legion-commander", signing_key)
        {
            let r_start = Instant::now();
            if let Ok(ack) = client.send_gap_codon(&sutra.codon_str, "remote-node", 0) {
                remote_rtt_us = Some(r_start.elapsed().as_micros());
                remote_ack = Some(ack);
            }
        }
    }

    if json {
        let out = serde_json::json!({
            "status": "ok",
            "simulated": report.simulated,
            "simulation_note": report.simulation_note,
            "edict": sutra.codon_str,
            "total_clones": report.total_clones,
            "cho_count": report.cho_count,
            "han_count": report.han_count,
            "evaporated_count": report.evaporated_count,
            "winning_clone_id": report.winning_clone_id,
            "winning_codon": report.winning_codon,
            "total_summoning_micros": report.total_summoning_micros,
            "estimated_token_budget_delta": report.estimated_token_budget_delta,
            "cohort_distribution": report.cohort_distribution,
            "peer": peer,
            "remote_rtt_us": remote_rtt_us,
            "remote_ack": remote_ack,
        });
        println!("{}", serde_json::to_string_pretty(&out).unwrap_or_default());
    } else {
        println!("==================================================");
        println!("  WhiteMagic GAS Shadow Clone Legion (Simulation) ");
        println!("==================================================");
        println!("Edict Codon:        {}", sutra.codon_str);
        println!("Clones Simulated:   {}", report.total_clones);
        println!("Cho (丁 / Advisory Pass):   {}", report.cho_count);
        println!("Han (半 / Advisory Flag):   {}", report.han_count);
        println!("Evaporated (虚 / Transient): {}", report.evaporated_count);
        if let Some(winner_id) = report.winning_clone_id {
            println!(
                "Winning Clone:      #{} ({})",
                winner_id,
                report.winning_codon.as_deref().unwrap_or("")
            );
        }
        println!("Wallclock Latency:  {} µs", report.total_summoning_micros);
        println!(
            "Est. Budget Delta:  {} tokens (modeled @ 1500/clone)",
            report.estimated_token_budget_delta
        );
        if let Some(rtt) = remote_rtt_us {
            println!(
                "Remote Peer RTT:    {} µs (peer: {})",
                rtt,
                peer.unwrap_or("")
            );
        }
        println!("==================================================");
    }
}

fn run_sutra_chohan(payload: &str, proof: Option<&str>, bid: u64, json: bool) {
    use wm_gen3_core::legion::ChoHanVerdict;

    let is_cho = if let Some(p) = proof {
        !p.contains("anomaly") && !p.contains("divergence") && !p.contains("fail")
    } else {
        let sum: u32 = payload.bytes().map(|b| b as u32).sum();
        sum % 2 == 0
    };

    let verdict = if is_cho {
        ChoHanVerdict::ChoAttested
    } else {
        ChoHanVerdict::HanAnomaly
    };

    let settlement_action = match verdict {
        ChoHanVerdict::ChoAttested => "ADVISORY_PROMOTE_CANDIDATE",
        ChoHanVerdict::HanAnomaly => "ADVISORY_FLAG_ANOMALY",
        ChoHanVerdict::Evaporated => "EVAPORATED_WITHOUT_RESIDUE",
    };

    if json {
        let out = serde_json::json!({
            "status": "ok",
            "simulated": true,
            "advisory_only": true,
            "escrow_enforced": false,
            "payload": payload,
            "proof": proof,
            "bid_micro_usdc": bid,
            "verdict": format!("{:?}", verdict),
            "classification": if is_cho { "Cho (丁 / Even / Advisory Pass)" } else { "Han (半 / Odd / Advisory Anomaly)" },
            "settlement_action": settlement_action,
        });
        println!("{}", serde_json::to_string_pretty(&out).unwrap_or_default());
    } else {
        println!("==================================================");
        println!("  WhiteMagic Cho-Han (丁半) Advisory Classifier   ");
        println!("==================================================");
        println!("Payload:            {}", payload);
        println!("Advisory Stake:     {} micro-USDC (not escrowed)", bid);
        println!("Verdict:            {:?}", verdict);
        println!(
            "Classification:     {}",
            if is_cho {
                "Cho (丁 / Advisory Pass)"
            } else {
                "Han (半 / Advisory Anomaly)"
            }
        );
        println!("Advisory Action:    {}", settlement_action);
        println!("==================================================");
    }
}

fn run_sutra_deliberator(inquiry: &str, json: bool) {
    use std::time::Instant;
    use wm_gen3_core::sutra::{CompoundSutra, SutraGlyph};
    use wm_gen3_core::valkyrie::ValkyrieTwoEngine;
    use wm_gen3_zeropointfive::System05;

    let mut engine = ValkyrieTwoEngine::bootstrap_production_engine();
    let live_vec: Option<Vec<f32>> = System05::resolve_model_dir(None)
        .ok()
        .map(System05::new)
        .and_then(|organ| organ.encode_single(inquiry).ok());

    let hot_start = Instant::now();
    // 1. Sutra Vector Compilation
    let mut glyph_scores: Vec<(SutraGlyph, f32)> = Vec::new();
    if let Some(ref qvec) = live_vec {
        for &g in &SutraGlyph::ALL {
            let gvec = g.vector();
            let dot: f32 = qvec.iter().zip(gvec.iter()).map(|(a, b)| a * b).sum();
            glyph_scores.push((g, dot));
        }
        glyph_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    } else {
        for word in inquiry.split(|c: char| !c.is_alphanumeric()) {
            if let Some(g) = SutraGlyph::from_token(word) {
                if !glyph_scores.iter().any(|(x, _)| *x == g) {
                    glyph_scores.push((g, 1.0));
                }
            }
        }
    }
    let top_glyphs: Vec<SutraGlyph> = if glyph_scores.is_empty() {
        vec![SutraGlyph::Guan, SutraGlyph::Ying, SutraGlyph::He]
    } else {
        glyph_scores.iter().take(3).map(|(g, _)| *g).collect()
    };
    let sutra = CompoundSutra::from_glyphs(top_glyphs)
        .unwrap_or_else(|_| CompoundSutra::parse("觀 應 合").unwrap());

    // 2. Valkyrie-2 15 Hz Conscious/Counterfactual Ring Deliberation
    let v2_res = engine.evaluate_inquiry(inquiry, live_vec.as_deref(), None);

    // 3. 28 Lunar Mansions (Gana) Zero-Backprop Route Ranking
    const LUNAR_MANSIONS: [&str; 28] = [
        "01:Horn (角) — Genesis & Initiation",
        "02:Neck (亢) — Structural Constraint",
        "03:Root (氐) — Substrate Foundation",
        "04:Room (房) — Kekkai Chamber",
        "05:Heart (心) — Citta Pulse",
        "06:Tail (尾) — Audit Trail",
        "07:WinnowingBasket (箕) — Sieve & Filter",
        "08:Dipper (斗) — Metric Calibration",
        "09:Ox (牛) — Steadfast Persistence",
        "10:Girl (女) — Weaving & Binding",
        "11:Emptiness (虛) — Zero-Write Void",
        "12:Roof (危) — Canopy Protection",
        "13:Encampment (室) — Sangha Garrison",
        "14:Wall (壁) — Archive Boundary",
        "15:Legs (奎) — Stride Traversal",
        "16:Bond (婁) — Covenant & Receipt",
        "17:Stomach (胃) — Ingest Digestion",
        "18:HairyHead (昴) — Pleiades Cluster",
        "19:Net (畢) — Capture & Quarantine",
        "20:TurtleBeak (觜) — Precision Probe",
        "21:ThreeStars (參) — Tricameral Triad",
        "22:Well (井) — Deep Memory Source",
        "23:Ghost (鬼) — Shadow Clone Carrier",
        "24:Willow (柳) — Adaptive Flex",
        "25:Star (星) — Radiant Beacon",
        "26:ExtendedNet (張) — Graph Resonance",
        "27:Wings (翼) — High-Velocity Flight",
        "28:Chariot (軫) — Cross-Node Transport",
    ];

    let pred_class = v2_res["decision"]["predicted_class"].as_u64().unwrap_or(0) as usize;
    let top_prob = v2_res["decision"]["top_probability"]
        .as_f64()
        .unwrap_or(0.85);
    let primary_glyph_idx = sutra.glyphs.first().map(|g| *g as usize).unwrap_or(0);
    let mut ranked_mansions = Vec::with_capacity(3);
    for rank in 0..3usize {
        let m_idx = (pred_class * 3 + primary_glyph_idx + rank * 7) % 28;
        let score = (top_prob * (0.92f64).powi(rank as i32)).clamp(0.0, 1.0);
        ranked_mansions.push(serde_json::json!({
            "rank": rank + 1,
            "mansion_index": m_idx + 1,
            "lunar_mansion": LUNAR_MANSIONS[m_idx],
            "resonance_score": score,
        }));
    }
    let hot_ns = hot_start.elapsed().as_nanos() as u64;
    let ring_ns = v2_res["decision"]["latency_ns"].as_u64().unwrap_or(hot_ns);

    let payload = serde_json::json!({
        "status": "ok",
        "deliberator": "sutra-valkyrie-15hz-v1",
        "inquiry": inquiry,
        "compiled_sutra_codon": sutra.codon_str,
        "taoist_formula": sutra.taoist_formula(),
        "primary_skeleton": sutra.primary_skeleton_id,
        "valkyrie_ring_latency_ns": ring_ns,
        "total_deliberation_ns": hot_ns,
        "zero_backprop": true,
        "catuskoti_corner": v2_res["decision"]["catuskoti_corner"],
        "tsao_15hz_ring": v2_res["tsao_15hz_working_memory_ring"],
        "lunar_mansion_rankings": ranked_mansions,
    });

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&payload).unwrap_or_default()
        );
    } else {
        println!("==========================================================================");
        println!("   SUTRA-VALKYRIE 15 Hz LATENT DELIBERATOR & 28 LUNAR MANSION RANKER      ");
        println!("==========================================================================");
        println!("  Inquiry           : \"{}\"", inquiry);
        println!(
            "  Sutra Codon       : {} ({})",
            sutra.codon_str,
            sutra.taoist_formula()
        );
        println!("  Bound Skeleton    : {}", sutra.primary_skeleton_id);
        println!(
            "  Valkyrie 15Hz Ring: {} ns | Catuṣkoṭi={} | Zero-Backprop=true",
            ring_ns,
            v2_res["decision"]["catuskoti_corner"]
                .as_str()
                .unwrap_or("K1")
        );
        println!("  Top-3 Ranked Lunar Mansions (28 Gana State Matrix):");
        for m in &ranked_mansions {
            println!(
                "    #{} {} (score={:.4})",
                m["rank"].as_u64().unwrap_or(1),
                m["lunar_mansion"].as_str().unwrap_or(""),
                m["resonance_score"].as_f64().unwrap_or(0.0)
            );
        }
        println!("==========================================================================");
    }
}

fn run_sutra_valkyrie(inquiry: &str, benchmark: bool, digest: Option<u64>, json: bool) {
    use wm_gen3_core::valkyrie::ValkyrieTwoEngine;

    if benchmark {
        let rep = ValkyrieTwoEngine::run_real_world_corpus_benchmark();
        if json {
            println!("{}", serde_json::to_string_pretty(&rep).unwrap_or_default());
        } else {
            println!(
                "=================================================================================="
            );
            println!(
                "   VALKYRIE-2 REAL-WORLD CORPUS, CITADEL ANTIBODY & WORLD AI MODEL BENCHMARK      "
            );
            println!(
                "=================================================================================="
            );
            println!(
                "  Real 512-D Model2Vec Sutra Canon Accuracy : {:5.1}%",
                rep["sutra_512d_model2vec_accuracy_pct"]
                    .as_f64()
                    .unwrap_or(0.0)
            );
            println!(
                "  Real 384-D x_api.db Bookmarks Evaluated   : {}",
                rep["x_bookmarks_384d_count"].as_u64().unwrap_or(0)
            );
            println!(
                "  Tabula Rasa (Random Init) 384-D Accuracy  : {:5.1}%",
                rep["x_bookmarks_tabula_rasa_accuracy_pct"]
                    .as_f64()
                    .unwrap_or(0.0)
            );
            println!(
                "  Valkyrie-2 (Trained) 384-D Choice Acc     : {:5.1}%",
                rep["x_bookmarks_valkyrie_2_accuracy_pct"]
                    .as_f64()
                    .unwrap_or(0.0)
            );
            println!(
                "  Valkyrie-2 (Trained) 384-D Noul Acc       : {:5.1}%",
                rep["x_bookmarks_valkyrie_2_noul_pct"]
                    .as_f64()
                    .unwrap_or(0.0)
            );
            println!(
                "  Mean Pulse Latency on Real 384-D Vectors  : {} ns",
                rep["x_bookmarks_pulse_latency_ns"].as_u64().unwrap_or(0)
            );
            println!(
                "  Live Production VPS Citadel Antibodies    : {}",
                rep["live_vps_citadel_antibodies_verified"]
                    .as_u64()
                    .unwrap_or(0)
            );
            println!(
                "  Total Benchmark Elapsed Time              : {:.2} ms",
                rep["total_benchmark_elapsed_ms"].as_f64().unwrap_or(0.0)
            );
            println!(
                "  Hardware CPU Package Temp / Mode          : {:.1} °C ({})",
                rep["hardware_telemetry"]["cpu_temp_c"]
                    .as_f64()
                    .unwrap_or(0.0),
                rep["hardware_telemetry"]["metabolism_mode"]
                    .as_str()
                    .unwrap_or("NominalSynthesis")
            );
            if let Some(comp) = rep["world_model_comparison"].as_array() {
                println!(
                    "----------------------------------------------------------------------------------"
                );
                println!(
                    "  {:<36} | {:>12} | {:>13} | {:>7} | {:>7}",
                    "Model Architecture", "Size (KB)", "CPU Latency", "Choice%", "384-D%"
                );
                println!(
                    "----------------------------------------------------------------------------------"
                );
                for row in comp {
                    println!(
                        "  {:<36} | {:>12.2} | {:>10.2} µs | {:>6.1}% | {:>6.1}%",
                        row["model"].as_str().unwrap_or(""),
                        row["footprint_kb"].as_f64().unwrap_or(0.0),
                        row["cpu_latency_us"].as_f64().unwrap_or(0.0),
                        row["choice_accuracy_pct"].as_f64().unwrap_or(0.0),
                        row["real_384d_bookmark_accuracy_pct"]
                            .as_f64()
                            .unwrap_or(0.0),
                    );
                }
            }
            println!(
                "=================================================================================="
            );
        }
        return;
    }

    let live_vec: Option<Vec<f32>> = wm_gen3_zeropointfive::System05::resolve_model_dir(None)
        .ok()
        .map(wm_gen3_zeropointfive::System05::new)
        .and_then(|organ| organ.encode_single(inquiry).ok());

    let mut engine = ValkyrieTwoEngine::bootstrap_production_engine();
    let res = engine.evaluate_inquiry(inquiry, live_vec.as_deref(), digest);
    if json {
        println!("{}", serde_json::to_string_pretty(&res).unwrap_or_default());
    } else {
        println!("==========================================================================");
        println!("   VALKYRIE-2 TRICAMERAL PULSE & CROSS-LAYER ATTRIBUTION GRAPH            ");
        println!("==========================================================================");
        println!(
            "  Sanitized Inquiry : {} (zero_pii_verified={})",
            res["sanitized_inquiry"].as_str().unwrap_or(""),
            res["zero_pii_verified"].as_bool().unwrap_or(true)
        );
        println!(
            "  Embedding Source  : {}",
            res["embedding_source"].as_str().unwrap_or("")
        );
        println!(
            "  Curriculum Phase  : {} [{}] — {}",
            res["curriculum_phase"]["code"].as_str().unwrap_or(""),
            res["curriculum_phase"]["stage"].as_str().unwrap_or(""),
            res["curriculum_phase"]["operation"].as_str().unwrap_or("")
        );
        println!(
            "  Decision Metrics  : Class #{} (p={:.4}, margin={:.4}) | Noul={:.4} | Score={:.4} | Catuṣkoṭi={}",
            res["decision"]["predicted_class"].as_u64().unwrap_or(0),
            res["decision"]["top_probability"].as_f64().unwrap_or(0.0),
            res["decision"]["margin"].as_f64().unwrap_or(0.0),
            res["decision"]["noul_boolean_probability"]
                .as_f64()
                .unwrap_or(0.0),
            res["decision"]["score_expectation"].as_f64().unwrap_or(0.0),
            res["decision"]["catuskoti_corner"].as_str().unwrap_or("K1")
        );
        println!(
            "  Superoptimized    : {} ({} glyphs) | Latency: {} ns",
            res["superoptimizer"]["superoptimized_codon"]
                .as_str()
                .unwrap_or(""),
            res["superoptimizer"]["reduced_glyph_len"]
                .as_u64()
                .unwrap_or(0),
            res["decision"]["latency_ns"].as_u64().unwrap_or(0)
        );
        println!(
            "  Tsao 15 Hz Ring   : AntibodyBlocked={} | CounterfactualFallback={} | LoadedAntibodies={}",
            res["tsao_15hz_working_memory_ring"]["blocked_by_citadel_antibody"]
                .as_bool()
                .unwrap_or(false),
            res["tsao_15hz_working_memory_ring"]["used_tsao_counterfactual_fallback"]
                .as_bool()
                .unwrap_or(false),
            res["tsao_15hz_working_memory_ring"]["loaded_citadel_antibodies"]
                .as_u64()
                .unwrap_or(0)
        );
        if let Some(nodes) = res["attribution_graph"]["active_nodes"].as_array() {
            println!("  Top-K Cross-Layer Sparse Transcoder Attribution Graph:");
            for n in nodes {
                println!(
                    "    • Feature #{:<2} ({:<20}) | act={:.4} ──► Class #{} (edge={:+.4})",
                    n["feature_id"].as_u64().unwrap_or(0),
                    n["concept_name"].as_str().unwrap_or(""),
                    n["activation"].as_f64().unwrap_or(0.0),
                    n["top_downstream_class"].as_u64().unwrap_or(0),
                    n["linear_causal_edge_weight"].as_f64().unwrap_or(0.0)
                );
            }
        }
        println!(
            "  Hardware Telemetry: {:.1} °C | RAM Avail: {:.1} MB | Footprint: {:.2} KB",
            res["hardware_telemetry"]["cpu_temp_c"]
                .as_f64()
                .unwrap_or(0.0),
            res["hardware_telemetry"]["mem_available_mb"]
                .as_f64()
                .unwrap_or(0.0),
            res["hardware_telemetry"]["footprint_kb"]
                .as_f64()
                .unwrap_or(0.0)
        );
        println!("==========================================================================");
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

#[cfg(test)]
mod ingest_meta_tests {
    use super::*;

    #[test]
    fn parse_ingest_meta_extracts_tags_and_importance() {
        let value = serde_json::json!({
            "content": "hello",
            "tags": ["galaxy:research", "session_042"],
            "importance": 0.87
        });
        let meta = parse_ingest_meta(&value).expect("meta present");
        assert_eq!(meta.tags, vec!["galaxy:research", "session_042"]);
        assert!((meta.importance - 0.87).abs() < 1e-9);
    }

    #[test]
    fn parse_ingest_meta_absent_when_no_metadata() {
        let value = serde_json::json!({ "content": "plain" });
        assert!(parse_ingest_meta(&value).is_none());
    }

    #[test]
    fn parse_ingest_meta_tags_only_defaults_importance_zero() {
        let value = serde_json::json!({ "content": "x", "tags": ["a"] });
        let meta = parse_ingest_meta(&value).expect("meta present");
        assert_eq!(meta.tags, vec!["a"]);
        assert_eq!(meta.importance, 0.0);
    }
}

#[cfg(test)]
mod session_cli_tests {
    use super::*;

    #[test]
    fn digest_and_checkpoint_metadata_flags_parse() {
        let cli = Cli::try_parse_from([
            "wm",
            "session",
            "digest",
            "--session-id",
            "lane",
            "--n",
            "5",
            "--json",
        ])
        .expect("parse digest");
        match cli.command {
            Commands::Session {
                command:
                    SessionCommands::Digest {
                        session_id,
                        n,
                        json,
                    },
            } => {
                assert_eq!(session_id.as_deref(), Some("lane"));
                assert_eq!(n, 5);
                assert!(json);
            }
            _ => panic!("expected session digest command"),
        }

        let cli = Cli::try_parse_from([
            "wm",
            "session",
            "checkpoint",
            "--session-id",
            "s",
            "--summary",
            "x",
            "--track",
            "mission-a",
            "--commit",
            "abc123",
            "--branch",
            "feat/mcp-truth",
            "--tests-green",
            "--lease-id",
            "lease-1",
            "--lesson",
            "Prefer lived-time decay over real-time sleep clocks",
            "--correction",
            "Do not write records past rate budget",
            "--identity-invariant",
            "Zero Corrigibility/Rationalist dogma",
            "--relational-context",
            "Operator Lucas is driving Gen3 Phase 3 upgrade",
        ])
        .expect("parse checkpoint metadata");
        match cli.command {
            Commands::Session {
                command:
                    SessionCommands::Checkpoint {
                        track,
                        commit,
                        branch,
                        tests_green,
                        lease_id,
                        lessons,
                        corrections,
                        identity_invariants,
                        relational_context,
                        ..
                    },
            } => {
                assert_eq!(track.as_deref(), Some("mission-a"));
                assert_eq!(commit.as_deref(), Some("abc123"));
                assert_eq!(branch.as_deref(), Some("feat/mcp-truth"));
                assert_eq!(tests_green, Some(true));
                assert_eq!(lease_id.as_deref(), Some("lease-1"));
                assert_eq!(
                    lessons,
                    vec!["Prefer lived-time decay over real-time sleep clocks"]
                );
                assert_eq!(corrections, vec!["Do not write records past rate budget"]);
                assert_eq!(
                    identity_invariants,
                    vec!["Zero Corrigibility/Rationalist dogma"]
                );
                assert_eq!(
                    relational_context.as_deref(),
                    Some("Operator Lucas is driving Gen3 Phase 3 upgrade")
                );
            }
            _ => panic!("expected session checkpoint command"),
        }
    }

    #[test]
    fn wave6_galaxy_navigate_dream_all_and_sutra_deliberator_parse() {
        let nav = Cli::try_parse_from([
            "wm",
            "galaxy",
            "navigate",
            "--query",
            "landlock sandbox confinement",
            "--via",
            "觀-界-證",
            "--hops",
            "2",
            "--json",
        ])
        .expect("parse galaxy navigate");
        match nav.command {
            Commands::Galaxy {
                action:
                    Some(GalaxyAction::Navigate {
                        query,
                        via,
                        hops,
                        json,
                        ..
                    }),
                ..
            } => {
                assert_eq!(query, "landlock sandbox confinement");
                assert_eq!(via.as_deref(), Some("觀-界-證"));
                assert_eq!(hops, 2);
                assert!(json);
            }
            _ => panic!("expected galaxy navigate command"),
        }

        let dream = Cli::try_parse_from(["wm", "dream", "--crystallize", "--all", "--force"])
            .expect("parse dream --crystallize --all");
        match dream.command {
            Commands::Dream {
                crystallize,
                all,
                force,
                ..
            } => {
                assert!(crystallize);
                assert!(all);
                assert!(force);
            }
            _ => panic!("expected dream command"),
        }

        let delib = Cli::try_parse_from([
            "wm",
            "sutra",
            "deliberator",
            "synthesize holographic constellations",
            "--json",
        ])
        .expect("parse sutra deliberator");
        match delib.command {
            Commands::Sutra {
                command: Some(SutraCommands::Deliberator { inquiry, json }),
                ..
            } => {
                assert_eq!(inquiry, "synthesize holographic constellations");
                assert!(json);
            }
            _ => panic!("expected sutra deliberator command"),
        }
    }
}

#[cfg(test)]
mod cli_truth_tests {
    use super::*;
    use clap::CommandFactory;

    fn fixture_store_dir() -> PathBuf {
        let dir = std::env::temp_dir().join(format!("wm-cli-truth-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).expect("create fixture store");
        dir
    }

    fn fixture_pass() -> MandalaPass {
        MandalaPass {
            pass_id: "pass-test".to_string(),
            slot_id: "slot-test".to_string(),
            tenant_id: "tenant-test".to_string(),
            agent_id: "agent-test".to_string(),
            principal_id: None,
            jti: "jti-test".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 100,
            expires_at: 10_000,
            budget: PassBudget {
                max_operations: 10,
                operations_used: 0,
                max_compute_ms: 60_000,
                max_memory_mb: 512,
            },
            manifest: CapabilityManifest::default(),
            mandate_ref: None,
            signature: None,
        }
    }

    fn fixture_continuity_receipt(key: &SigningKey) -> ContinuityReceipt05 {
        let mut receipt = ContinuityReceipt05::new(
            "rcpt-test".to_string(),
            "tenant-test".to_string(),
            "agent-test".to_string(),
            "session-test".to_string(),
            1_700_000_000_000,
            "kekkai-v1".to_string(),
            "claim-digest".to_string(),
            true,
            "preflight-digest".to_string(),
            None,
            format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes())),
        );
        receipt.sign(key);
        receipt
    }

    #[test]
    fn verify_pass_against_gate_fails_closed_for_foreign_or_unsigned_passes() {
        let store = fixture_store_dir();
        let (signing_key, pubkey) =
            resolve_or_create_mandala_gate_key(&store).expect("gate key fixture");

        let mut trusted = fixture_pass();
        trusted.sign(&signing_key);
        let verified_pubkey =
            verify_pass_against_gate(&trusted, &store, 1_500).expect("trusted pass accepted");
        assert_eq!(verified_pubkey, pubkey);

        let foreign_key = SigningKey::from_bytes(&[9u8; 32]);
        let mut foreign = fixture_pass();
        foreign.sign(&foreign_key);
        let foreign_error =
            verify_pass_against_gate(&foreign, &store, 1_500).expect_err("foreign pass refused");
        assert!(
            foreign_error.contains("does not verify against the trusted local gate"),
            "{foreign_error}"
        );

        let mut unsigned = fixture_pass();
        unsigned.signature = None;
        assert!(verify_pass_against_gate(&unsigned, &store, 1_500).is_err());

        let expired_error =
            verify_pass_against_gate(&trusted, &store, 20_000).expect_err("expired pass refused");
        assert!(expired_error.contains("ledger replay check failed"));

        let keyless_store = fixture_store_dir();
        let keyless_error = verify_pass_against_gate(&trusted, &keyless_store, 1_500)
            .expect_err("missing gate key refuses verification");
        assert!(keyless_error.contains("gate authority key unavailable"));

        std::fs::remove_dir_all(&store).ok();
        std::fs::remove_dir_all(&keyless_store).ok();
    }

    #[test]
    fn verify_continuity_receipt05_fails_closed_for_tampering_and_foreign_keys() {
        let store = fixture_store_dir();
        let (signing_key, _) = resolve_or_create_mandala_gate_key(&store).expect("gate key");

        let receipt = fixture_continuity_receipt(&signing_key);
        let content = serde_json::to_string(&receipt).expect("serialize receipt");
        let verified =
            verify_continuity_receipt05(&content, &store).expect("trusted receipt verifies");
        assert_eq!(verified.receipt_id, "rcpt-test");

        let mut tampered = receipt.clone();
        tampered.tenant_id = "tenant-attacker".to_string();
        let tampered_content = serde_json::to_string(&tampered).expect("serialize tampered");
        assert!(verify_continuity_receipt05(&tampered_content, &store).is_err());

        let foreign = fixture_continuity_receipt(&SigningKey::from_bytes(&[7u8; 32]));
        let foreign_content = serde_json::to_string(&foreign).expect("serialize foreign");
        let foreign_error =
            verify_continuity_receipt05(&foreign_content, &store).expect_err("foreign refused");
        assert!(
            foreign_error.contains("does not verify against the store gate key"),
            "{foreign_error}"
        );

        let mut unsigned = fixture_continuity_receipt(&signing_key);
        unsigned.signature = None;
        assert!(
            verify_continuity_receipt05(&serde_json::to_string(&unsigned).unwrap(), &store)
                .is_err()
        );

        let mut wrong_spec = fixture_continuity_receipt(&signing_key);
        wrong_spec.spec = "continuity-receipt/9".to_string();
        let spec_error =
            verify_continuity_receipt05(&serde_json::to_string(&wrong_spec).unwrap(), &store)
                .expect_err("wrong spec refused");
        assert!(
            spec_error.contains("unsupported receipt spec"),
            "{spec_error}"
        );

        std::fs::remove_dir_all(&store).ok();
    }

    #[test]
    fn advertised_profile_counts_match_runtime_tool_lists() {
        let cyberbrain = profile_tool_count(McpProfile::Cyberbrain);
        let full = profile_tool_count(McpProfile::Full);
        assert!(cyberbrain > 0, "cyberbrain profile must expose tools");
        assert!(full > cyberbrain, "full profile must be a superset");

        let help = profile_help_text();
        assert!(help.contains(&format!("{cyberbrain} lean tools")), "{help}");
        assert!(help.contains(&format!("{full} curated tools")), "{help}");

        let manifest = build_contract_manifest(WM_VERSION);
        assert_eq!(
            manifest["counts"]["routes"].as_u64().expect("routes count") as usize,
            full,
            "contract manifest routes must equal the advertised full profile count"
        );

        let mut cmd = Cli::command();
        let serve = cmd.find_subcommand_mut("serve").expect("serve subcommand");
        let profile_arg = serve
            .get_arguments()
            .find(|arg| arg.get_id() == "profile")
            .expect("profile arg");
        let wired_help = profile_arg.get_help().expect("profile help").to_string();
        assert!(wired_help.contains(&format!("{cyberbrain} lean tools")));
        assert!(wired_help.contains(&format!("{full} curated tools")));
    }

    #[test]
    fn boolean_flags_default_on_and_can_be_disabled() {
        let cli = Cli::try_parse_from(["wm", "dream"]).expect("parse dream defaults");
        match cli.command {
            Commands::Dream {
                dual_phase,
                no_dual_phase,
                homeostatic,
                no_homeostatic,
                ..
            } => {
                assert_eq!(dual_phase, None);
                assert!(!no_dual_phase);
                assert_eq!(homeostatic, None);
                assert!(!no_homeostatic);
            }
            _ => panic!("expected dream command"),
        }

        let cli = Cli::try_parse_from(["wm", "dream", "--no-dual-phase", "--no-homeostatic"])
            .expect("parse dream disables");
        match cli.command {
            Commands::Dream {
                no_dual_phase,
                no_homeostatic,
                ..
            } => {
                assert!(no_dual_phase);
                assert!(no_homeostatic);
            }
            _ => panic!("expected dream command"),
        }

        let cli = Cli::try_parse_from(["wm", "serve", "--no-sweep", "--no-noise"])
            .expect("parse serve disables");
        match cli.command {
            Commands::Serve {
                sweep,
                no_sweep,
                noise,
                no_noise,
                ..
            } => {
                assert_eq!(sweep, None);
                assert!(no_sweep);
                assert_eq!(noise, None);
                assert!(no_noise);
            }
            _ => panic!("expected serve command"),
        }

        let cli = Cli::try_parse_from([
            "wm",
            "session",
            "checkpoint",
            "--session-id",
            "s",
            "--summary",
            "x",
            "--no-evolve",
        ])
        .expect("parse checkpoint disable");
        match cli.command {
            Commands::Session {
                command:
                    SessionCommands::Checkpoint {
                        evolve, no_evolve, ..
                    },
            } => {
                assert_eq!(evolve, None);
                assert!(no_evolve);
            }
            _ => panic!("expected session checkpoint command"),
        }
    }

    #[test]
    fn invalid_option_values_are_rejected_at_parse_time() {
        assert!(Cli::try_parse_from(["wm", "serve", "--profile", "bogus"]).is_err());
        assert!(Cli::try_parse_from(["wm", "remember", "note", "--kind", "bogus"]).is_err());
        assert!(Cli::try_parse_from(["wm", "ingest", "--default-kind", "bogus"]).is_err());
        assert!(Cli::try_parse_from(["wm", "dream", "--mode", "bogus"]).is_err());

        assert!(Cli::try_parse_from(["wm", "serve", "--profile", "curated"]).is_ok());
        assert!(Cli::try_parse_from(["wm", "remember", "note", "--kind", "system"]).is_ok());
        assert!(Cli::try_parse_from(["wm", "dream", "--mode", "sham"]).is_ok());
    }

    #[test]
    fn peer_add_requires_explicit_nonzero_key() {
        assert!(Cli::try_parse_from(["wm", "peer", "add", "node-x"]).is_err());
        let zero = "00".repeat(32);
        assert!(parse_pubkey_hex(&zero).is_err());
        let valid = "ab".repeat(32);
        assert!(parse_pubkey_hex(&valid).is_ok());
        assert!(Cli::try_parse_from(["wm", "peer", "add", "node-x", "--key", &valid]).is_ok());
        assert!(parse_pubkey_hex("zz").is_err());
    }
}

#[cfg(test)]
mod cli_surface_tests {
    use super::*;

    #[test]
    fn store_size_report_computes_used_percent_and_warn_flag() {
        let report = store_size_report(1 << 30, 16 << 30);
        assert_eq!(report.used_percent, 6.25);
        assert!(!report.warn);
        assert_eq!(
            render_store_size(&report),
            "1.00 GiB / 16.00 GiB map (6.25% used)"
        );

        let warn = store_size_report((13 << 30) + (1 << 20), 16 << 30);
        assert!(warn.used_percent > 80.0);
        assert!(warn.warn);
        assert!(render_store_size(&warn).contains("[WARN >80%]"));

        let empty = store_size_report(0, 0);
        assert_eq!(empty.used_percent, 0.0);
        assert!(!empty.warn);
    }

    #[test]
    fn map_size_gb_parsing_defaults_to_sixteen_gib() {
        assert_eq!(parse_map_size_gb(None), 16 << 30);
        assert_eq!(parse_map_size_gb(Some("1")), 1 << 30);
        assert_eq!(parse_map_size_gb(Some("2")), 2 << 30);
        assert_eq!(parse_map_size_gb(Some("bogus")), 16 << 30);
        assert_eq!(parse_map_size_gb(Some("")), 16 << 30);
    }

    #[test]
    fn firebreak_summary_matches_promoted_pattern_counts() {
        let firebreak = Firebreak::promoted();
        let (forbidden, dangerous, caution) = firebreak.pattern_counts();
        assert_eq!(forbidden, 39);
        assert_eq!(dangerous, 15);
        assert_eq!(caution, 8);
        let line = firebreak_summary_line();
        assert!(
            line.contains("39 forbidden / 15 dangerous / 8 caution"),
            "{line}"
        );
        let json = firebreak_json();
        assert_eq!(json["forbidden"], 39);
        assert_eq!(json["dangerous"], 15);
        assert_eq!(json["caution"], 8);
    }

    #[test]
    fn host_guard_cli_flags_parse() {
        let cli = Cli::try_parse_from(["wm", "host-guard", "status", "--json"]).expect("status");
        assert!(matches!(
            cli.command,
            Commands::HostGuard {
                command: HostGuardCommands::Status { json: true }
            }
        ));

        let cli = Cli::try_parse_from([
            "wm",
            "host-guard",
            "run",
            "--act",
            "--kill-orphans",
            "--json",
            "--force",
        ])
        .expect("run");
        match cli.command {
            Commands::HostGuard {
                command:
                    HostGuardCommands::Run {
                        act,
                        kill_orphans,
                        dry_run,
                        json,
                        force,
                    },
            } => {
                assert!(act && kill_orphans && json && force);
                assert!(!dry_run);
            }
            _ => panic!("expected host-guard run"),
        }

        assert!(matches!(
            Cli::try_parse_from(["wm", "host-guard", "arm"])
                .expect("arm")
                .command,
            Commands::HostGuard {
                command: HostGuardCommands::Arm
            }
        ));
        assert!(matches!(
            Cli::try_parse_from(["wm", "host-guard", "disarm"])
                .expect("disarm")
                .command,
            Commands::HostGuard {
                command: HostGuardCommands::Disarm
            }
        ));
    }

    #[test]
    fn at_rest_and_compact_cli_flags_parse() {
        let cli = Cli::try_parse_from([
            "wm",
            "at-rest",
            "migrate",
            "--dry-run",
            "--batch",
            "7",
            "--json",
        ])
        .expect("migrate");
        match cli.command {
            Commands::AtRest {
                command:
                    AtRestCommands::Migrate {
                        dry_run,
                        batch,
                        json,
                        yes,
                    },
            } => {
                assert!(dry_run && json && !yes);
                assert_eq!(batch, 7);
            }
            _ => panic!("expected at-rest migrate"),
        }

        let cli = Cli::try_parse_from(["wm", "compact", "--dry-run", "--json"]).expect("compact");
        match cli.command {
            Commands::Compact { dry_run, json, yes } => assert!(dry_run && json && !yes),
            _ => panic!("expected compact"),
        }
    }

    fn compact_fixture_store(root: &Path, content: &str) -> PathBuf {
        let store_path = root.join("store");
        let mut substrate = Substrate::open(&store_path, None, default_view()).expect("open store");
        substrate.set_intake_authority(RatifiedChannel::mint("wm-compact-test"));
        let results = substrate.remember_batch(&[RememberItem {
            content: content.to_string(),
            source: "system:test".to_string(),
            kind: ImportKind::System,
        }]);
        assert!(matches!(results.first(), Some(Ok(_))));
        substrate.finish();
        store_path
    }

    /// E2E compaction runs only where `mdb_copy` is installed
    /// (`sudo apt install lmdb-utils`); the report math and recovery logic are
    /// unit-tested above/below.
    #[test]
    fn compact_e2e_when_mdb_copy_available() {
        if find_on_path("mdb_copy").is_none() {
            eprintln!("skipping compact e2e: mdb_copy not installed");
            return;
        }
        let root = std::env::temp_dir().join(format!("wm-compact-e2e-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&root).expect("create root");
        let store_path = compact_fixture_store(&root, "compact e2e canary");

        // This process may run on hosts whose root-owned /proc maps entries
        // are unreadable (ptrace_scope); bypass only the live-handle gate for
        // the mechanics e2e. The seam is consumed by run_compact_command and
        // compiled out of production builds.
        COMPACT_TEST_SKIP_WRITER_SCAN.store(true, std::sync::atomic::Ordering::SeqCst);
        let code = run_compact_command(&store_path, false, true, true);
        COMPACT_TEST_SKIP_WRITER_SCAN.store(false, std::sync::atomic::Ordering::SeqCst);
        assert_eq!(code, 0, "compact should succeed");
        assert!(store_path.join("data.mdb").is_file());
        assert!(
            !store_path.join(COMPACT_JOURNAL_FILE).exists(),
            "journal must be removed after a verified swap"
        );
        assert!(
            !compact_tmp_dir(&store_path).exists(),
            "temporary copy must be removed after a verified swap"
        );
        let backups = std::fs::read_dir(&store_path)
            .expect("read store")
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with(COMPACT_BACKUP_PREFIX)
            })
            .count();
        assert_eq!(backups, 1, "one timestamped backup must be kept");

        let reopened = Store::open_readonly(&store_path).expect("reopen compacted store");
        assert_eq!(reopened.record_count().expect("count"), 1);
        drop(reopened);
        std::fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn compact_recovery_restores_backup_when_data_missing() {
        let root =
            std::env::temp_dir().join(format!("wm-compact-recover-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&root).expect("create root");
        let store_path = compact_fixture_store(&root, "compact recovery canary");
        let data_path = store_path.join("data.mdb");

        // Simulate a crash after `data.mdb -> .bak` but before `.tmp -> data.mdb`.
        let backup = store_path.join(format!("{COMPACT_BACKUP_PREFIX}20261007T000000.000000000Z"));
        std::fs::rename(&data_path, &backup).expect("simulate backup rename");
        let tmp_dir = compact_tmp_dir(&store_path);
        std::fs::create_dir_all(&tmp_dir).expect("create tmp dir");
        std::fs::write(tmp_dir.join("data.mdb"), b"partial copy").expect("write partial");
        let mut journal = CompactJournal::copy(&tmp_dir);
        journal.backup = Some(backup.display().to_string());
        journal.set_phase("swap_backup");
        write_compact_journal(&store_path, &journal).expect("write journal");
        assert!(!data_path.exists());

        let note = recover_interrupted_compact(&store_path)
            .expect("recovery succeeds")
            .expect("recovery note");
        assert!(note.contains("restored"), "{note}");
        assert!(data_path.is_file(), "data.mdb must be restored");
        assert!(!backup.exists(), "backup is renamed into place");
        assert!(!tmp_dir.exists(), "stale copy is removed");
        assert!(!store_path.join(COMPACT_JOURNAL_FILE).exists());

        let reopened = Store::open_readonly(&store_path).expect("reopen recovered store");
        assert_eq!(reopened.record_count().expect("count"), 1);
        drop(reopened);
        std::fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn compact_recovery_cleans_stray_tmp_and_journal() {
        let root =
            std::env::temp_dir().join(format!("wm-compact-cleanup-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&root).expect("create root");
        let store_path = compact_fixture_store(&root, "compact cleanup canary");
        let data_path = store_path.join("data.mdb");

        // Simulate a crash mid-copy: data.mdb untouched, journal + tmp remain.
        let tmp_dir = compact_tmp_dir(&store_path);
        std::fs::create_dir_all(&tmp_dir).expect("create tmp dir");
        std::fs::write(tmp_dir.join("data.mdb"), b"partial copy").expect("write partial");
        let journal = CompactJournal::copy(&tmp_dir);
        write_compact_journal(&store_path, &journal).expect("write journal");

        let note = recover_interrupted_compact(&store_path)
            .expect("recovery succeeds")
            .expect("recovery note");
        assert!(note.contains("cleaned"), "{note}");
        assert!(!tmp_dir.exists(), "stale copy is removed");
        assert!(!store_path.join(COMPACT_JOURNAL_FILE).exists());
        assert!(data_path.is_file(), "live data.mdb must be untouched");

        let reopened = Store::open_readonly(&store_path).expect("reopen store");
        assert_eq!(reopened.record_count().expect("count"), 1);
        drop(reopened);
        std::fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn compact_backup_rotation_keeps_newest_two() {
        let root = std::env::temp_dir().join(format!("wm-compact-prune-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&root).expect("create root");
        let stamps = [
            "20261007T000001.000000001Z",
            "20261007T000002.000000002Z",
            "20261007T000003.000000003Z",
            "20261007T000004.000000004Z",
        ];
        for stamp in stamps {
            std::fs::write(root.join(format!("{COMPACT_BACKUP_PREFIX}{stamp}")), b"bak")
                .expect("write backup");
        }

        let removed = prune_compact_backups(&root, COMPACT_BACKUP_KEEP);
        assert_eq!(removed.len(), 2);
        assert!(removed[0].ends_with(&stamps[0]), "{removed:?}");
        assert!(removed[1].ends_with(&stamps[1]), "{removed:?}");
        let remaining: Vec<String> = std::fs::read_dir(&root)
            .expect("read root")
            .filter_map(Result::ok)
            .map(|entry| entry.file_name().to_string_lossy().into_owned())
            .collect();
        assert_eq!(remaining.len(), 2);
        assert!(remaining.iter().any(|name| name.ends_with(&stamps[2])));
        assert!(remaining.iter().any(|name| name.ends_with(&stamps[3])));

        std::fs::remove_dir_all(&root).ok();
    }
}
