//! `WhiteMagic` CLI — `wm` command
//!
//! Entry point for the `WhiteMagic` v5 CLI tool.

use clap::{Parser, Subcommand};
use std::io::IsTerminal;
use std::path::{Path, PathBuf};

/// Open the server for `wm serve`. Read-only operation is intentionally a
/// fail-closed preservation mode: it must use the existing readonly open
/// paths and never turn an open failure into repair, growth, or creation.
fn open_server_for_serve(
    lmdb_path: &Path,
    readonly: bool,
    preservation_readonly: bool,
) -> anyhow::Result<wm_mcp::McpServer> {
    if readonly {
        return wm_mcp::McpServer::with_defaults_mode_preservation(
            lmdb_path,
            true,
            preservation_readonly,
        );
    }

    std::fs::create_dir_all(lmdb_path)?;
    match wm_mcp::McpServer::with_defaults_mode(lmdb_path, false) {
        Ok(server) => Ok(server),
        Err(e) => {
            tracing::warn!(
                "Normal open failed ({e}). Attempting recovery with AutoRepairAndGrow..."
            );
            recover_writable_store(lmdb_path)?;
            Ok(wm_mcp::McpServer::with_defaults_mode(lmdb_path, false)?)
        }
    }
}

fn recover_writable_store(lmdb_path: &Path) -> anyhow::Result<()> {
    #[cfg(test)]
    WRITABLE_RECOVERY_CALLS.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    let _recovered_store = wm_memory::open_with_recovery(
        lmdb_path,
        1024 * 1024 * 1024,
        wm_memory::RecoveryStrategy::AutoRepairAndGrow,
    )?;
    Ok(())
}

#[cfg(test)]
static WRITABLE_RECOVERY_CALLS: std::sync::atomic::AtomicUsize =
    std::sync::atomic::AtomicUsize::new(0);

#[derive(Parser)]
#[command(
    name = "wm",
    version = env!("CARGO_PKG_VERSION"),
    about = "WhiteMagic — local-first memory and session continuity for coding agents",
    after_help = "Lab & advanced commands (geneseed, daemon, polyglot, seal, verify, anchor, trust, migrate, …) are hidden from this list but fully runnable — see 'wm help --all'."
)]
struct Cli {
    /// Path to a TOML config file. Overrides default config location.
    #[arg(long, global = true)]
    config: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Print this executable build provenance without opening a store
    BuildInfo,
    /// Read a running HTTP server capability manifest without opening its store
    Manifest {
        /// Explicit server base URL (e.g. http://127.0.0.1:18795)
        #[arg(long)]
        endpoint: String,
    },
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
        /// Preserve a frozen evaluator tree: require readonly and suppress
        /// all server-owned diagnostic persistence inside the snapshot root.
        #[arg(long, requires = "readonly")]
        preservation_readonly: bool,
        /// Tool surface profile: full | curated | minimal. When omitted,
        /// `wm serve` uses curated (the product surface) unless
        /// WM_TOOL_PROFILE / WM_TOOL_PACK / WM_TOOL_ALLOWLIST is set. Full is
        /// the archive/research surface.
        #[arg(long)]
        profile: Option<String>,
        /// Task-focused tool pack: continuity | research | coding | ops.
        /// Wins over --profile; WM_TOOL_ALLOWLIST still wins over both.
        #[arg(long)]
        pack: Option<String>,
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
        /// Print the product sample config.toml to stdout
        #[arg(long)]
        sample: bool,
        /// Print the full sample (daemon schedules, hemispheres, cloud LLM)
        #[arg(long)]
        sample_full: bool,
        /// Write a sample config.toml to the default config path
        #[arg(long)]
        init: bool,
        /// Path to the LMDB store directory (for --init)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Run the built-in quickstart demo
    Quickstart {
        /// Show subsystem diagnostics (the demo is quiet by default — it is
        /// the product's first impression)
        #[arg(long)]
        verbose: bool,
    },
    /// Run a five-second end-to-end invariant check on a throwaway store
    Selftest {
        /// Machine-readable report
        #[arg(long)]
        json: bool,
        /// Show subsystem diagnostics (quiet by default, like quickstart)
        #[arg(long)]
        verbose: bool,
    },
    /// Human-facing health summary (store, counts, index, backup, update)
    Status {
        /// Store root (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Machine-readable report
        #[arg(long)]
        json: bool,
    },
    /// Guided first-run: inspect host, verify substrate, check release,
    /// configure the agent, calibrate memory, teach the vocabulary, and
    /// demonstrate restart continuity (agent-first; `--json` for machines)
    Grimoire {
        /// Machine-readable report
        #[arg(long)]
        json: bool,
        /// Apply configuration changes (patch detected client configs)
        #[arg(long)]
        write: bool,
        /// Show subsystem diagnostics (quiet by default, like quickstart)
        #[arg(long)]
        verbose: bool,
    },
    /// Configure an MCP client to use WhiteMagic (JSON, JSONC, and TOML
    /// configs can be patched; the change is always shown first)
    Setup {
        /// Client id: opencode | claude | cursor | windsurf | codex (omit to list)
        client: Option<String>,
        /// Apply the change (JSON/JSONC/TOML; timestamped backup first)
        #[arg(long)]
        write: bool,
        /// Remove WhiteMagic's own entry from the client config (backup first)
        #[arg(long)]
        remove: bool,
        /// Path written into the client config (default: this executable)
        #[arg(long)]
        binary: Option<PathBuf>,
    },
    /// Detect installed MCP clients and wire WhiteMagic into each in one
    /// command (dry run by default; timestamped backups on --write)
    Connect {
        /// Apply changes to every detected client
        #[arg(long)]
        write: bool,
        /// Path written into client configs (default: this executable)
        #[arg(long)]
        binary: Option<PathBuf>,
    },
    /// Update against GitHub Releases (canonical): `check` is notify-only
    /// (no installation), `install` downloads, verifies, and swaps the
    /// binary, `rollback` restores the previous one.
    Update {
        #[command(subcommand)]
        action: UpdateAction,
    },
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
        /// Run Kaizen correlation analysis across memories
        #[arg(long)]
        kaizen: bool,
        /// Grade optional/experimental subsystems (calibration state,
        /// embedder route quality, …) as issues too. Default doctor grades
        /// the supported product surface only (first-run feedback, 2026-09-13).
        #[arg(long)]
        deep: bool,
    },
    /// Analyze git history and mine codebase patterns with longevity scores (read-only)
    #[command(hide = true)]
    Geneseed {
        /// Path to the git repository (default: current directory)
        #[arg(long, default_value = ".")]
        repo: PathBuf,
        /// Maximum number of commits to scan
        #[arg(long, default_value_t = 500)]
        max_commits: usize,
        /// Minimum confidence threshold
        #[arg(long, default_value_t = 0.6)]
        min_confidence: f64,
        /// Show stats only
        #[arg(long)]
        stats_only: bool,
    },
    /// Show resource usage and brain-wave state
    Stats {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Show estimated per-tool activity for the last 7 daily rollups
        /// (persisted; accumulates one row per service day) instead of the
        /// all-time persisted table
        #[arg(long)]
        week: bool,
    },
    /// Telemetry schema, local funnel status, and display-only preview
    ///
    /// Records are local; nothing is transmitted. `schema` publishes the
    /// record/retention/redaction contract; `status` shows local install
    /// funnel evidence (channel, first launch, milestones, active days);
    /// `preview` shows exactly what a future opt-in transmission would carry
    /// from this store.
    Telemetry {
        #[command(subcommand)]
        command: TelemetryCommands,
    },
    /// Emit the machine-checked route/schema contract catalog
    ///
    /// Builds the full registry from this exact binary revision and reports
    /// each route's declared input schema; `--check` verifies the curated
    /// unconditional-read list (v0 of the P1 `wm-contract` work).
    Contract {
        /// Machine-readable JSON (the full manifest)
        #[arg(long)]
        json: bool,
        /// Verify the curated unconditional-read list; exit 1 on violations
        #[arg(long)]
        check: bool,
        /// Write the manifest JSON to this path (implies building the full manifest)
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Write a sanitized local support bundle (report.json + README.txt)
    ///
    /// Read-only: memory content, queries, credentials, and raw paths are
    /// excluded; nothing is transmitted.
    Report {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Output directory (default: ./wm-report-<UTC date>)
        #[arg(long)]
        out: Option<PathBuf>,
        /// Print the report JSON to stdout instead of writing a bundle
        #[arg(long)]
        json: bool,
    },
    /// Show polyglot acceleration status
    #[command(hide = true)]
    Polyglot,
    /// Export collected training data for LoRA fine-tuning
    #[command(hide = true)]
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
    #[command(hide = true)]
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
        /// Interval between Citta 4-phase cognitive heartbeat cycles in seconds (0 = disabled)
        #[arg(long)]
        citta_interval: Option<u64>,
        /// Interval between watchdog audits of uncommitted crash-barrier operations in seconds (0 = disabled)
        #[arg(long)]
        watchdog_audit_interval: Option<u64>,
    },
    /// Show current brain-wave state (shorthand for stats)
    #[command(hide = true)]
    BrainWave {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Migrate legacy v26 SQLite memories into the v5 LMDB store
    #[command(hide = true)]
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
        /// Wait up to N seconds for a busy store (live serve) before failing
        #[arg(long, default_value_t = 0)]
        wait: u64,
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
        /// Redact credential-shaped content (PEM keys, prefixed tokens,
        /// assignment values) and ingest it instead of skipping the file
        #[arg(long)]
        redact: bool,
        /// Wait up to N seconds for a busy store (live serve) before failing
        #[arg(long, default_value_t = 0)]
        wait: u64,
        /// Ingest files whose NAME looks credential-bearing (secrets.txt)
        /// instead of skipping them; requires --redact so credential-shaped
        /// content is scrubbed before storage
        #[arg(long)]
        include_credential_files: bool,
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
    #[command(hide = true)]
    Opencode {
        #[command(subcommand)]
        command: OpencodeCommands,
    },
    /// Seal the LMDB store core with an HMAC-SHA256 integrity manifest
    ///
    /// Computes a digest for every file in the LMDB data tree and writes
    /// `seal.json`. Files added under the store ROOT (outside `lmdb/`) are
    /// not covered — use `wm backup` for whole-store recovery.
    /// A per-install secret key is generated at `.seal_key` on first use.
    /// Run `wm verify` afterwards to detect tampering or corruption.
    ///
    /// This is corruption / casual-tamper detection, not a root of trust.
    /// An adversary who can replace both `.seal_key` and `seal.json` wins.
    #[command(hide = true)]
    Seal {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Verify the LMDB store core against a previously written seal manifest
    ///
    /// Recomputes HMAC digests over the LMDB data tree and reports
    /// mismatched, missing, or extra files THERE — it is a store-core
    /// integrity seal, not a whole-store-root guarantee (`wm backup` is the
    /// full-store disaster-recovery mechanism). Exits with code 1 if
    /// verification fails.
    #[command(hide = true)]
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
    #[command(hide = true)]
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
    #[command(hide = true)]
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
    /// Redact credential-shaped content from stored memories in place
    ///
    /// Retrofit for content written before `wm ingest --redact` existed (or
    /// by other write paths): scans memories for credential-shaped spans
    /// (PEM keys, prefixed tokens, assignment values) and rewrites matching
    /// rows with `[REDACTED:<kind>]` markers, chaining the revision history
    /// and reindexing them. DRY-RUN by default — a `--tag` filter scopes the
    /// pass (e.g. `source:convo-harvest-20260911`).
    #[command(hide = true)]
    RedactContent {
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Only redact these galaxies (repeatable; default: all memory galaxies)
        #[arg(long)]
        galaxy: Vec<String>,
        /// Only redact memories carrying this exact tag (e.g. source:my-export)
        #[arg(long)]
        tag: Option<String>,
        /// Wait up to N seconds for a busy store (live serve) before failing
        #[arg(long, default_value_t = 0)]
        wait: u64,
        /// Apply the redaction (default: dry-run report only)
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
    /// At-rest keyring operations (Q39 slice B)
    ///
    /// `wm at-rest migrate` seals pre-existing plaintext records under the
    /// store's galaxy DEKs (encrypt-on-rewrite, bounded batches, crash-safe
    /// `migration:v1` ledger in the keyring DBI). Requires an unlocked
    /// keyring: run with the same WM_AT_REST_MODE/key source as the server.
    /// Takes the LMDB lock — stop the store's server unit first.
    #[command(hide = true)]
    AtRest {
        #[command(subcommand)]
        command: AtRestCommands,
    },
    /// Survey or correct memory source-trust provenance (V8.1 groundwork)
    ///
    /// source_trust semantics: 1.0 = user-confirmed, 0.7 = tool-ingested
    /// neutral, lower = unverified. Heritage ingests carry the defaults
    /// (user/1.0) and over-state trust — survey first, then correct a
    /// reviewed population before enabling WM_TRUST_WEIGHT.
    #[command(hide = true)]
    Trust {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        #[command(subcommand)]
        command: TrustCommand,
    },
}

#[derive(clap::Subcommand)]
enum AtRestCommands {
    /// Seal pre-existing plaintext records under the galaxy DEKs
    ///
    /// Encrypt-on-rewrite migration (Q39 slice B): walks each record galaxy
    /// in bounded LMDB batches, seals plaintext records under the galaxy
    /// DEK, and records progress in the keyring `migration:v1` ledger.
    /// Idempotent and crash-safe — re-running resumes from the ledger and
    /// skips already-sealed records. Refuses plaintext (`off`) stores: there
    /// is no keyring to seal under (the no-op is reported, not an error).
    Migrate {
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Only migrate these galaxies (repeatable; default: all record galaxies)
        #[arg(long)]
        galaxy: Vec<String>,
        /// Records per LMDB write transaction (default: 256)
        #[arg(long, default_value_t = wm_memory::DEFAULT_MIGRATION_BATCH)]
        batch: usize,
        /// Report what would be migrated without writing anything
        #[arg(long)]
        dry_run: bool,
        /// Wait up to N seconds for a busy store (live serve) before failing
        #[arg(long, default_value_t = 0)]
        wait: u64,
    },
    /// Show the `migration:v1` ledger state without writing anything
    Status {
        /// Path to the store root directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Machine-readable JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(clap::Subcommand)]
enum TelemetryCommands {
    /// Publish the telemetry record/retention/redaction contract
    Schema {
        /// Machine-readable JSON
        #[arg(long)]
        json: bool,
    },
    /// Show local install-funnel evidence (read-only; works with no store)
    Status {
        /// Store root (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Machine-readable JSON
        #[arg(long)]
        json: bool,
    },
    /// Show what an opt-in transmission would carry from this store
    /// (display-only; no network I/O, nothing written)
    Preview {
        /// Path to the LMDB store directory (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Maximum records to preview
        #[arg(long, default_value_t = 5)]
        limit: usize,
        /// Machine-readable JSON
        #[arg(long)]
        json: bool,
    },
    /// Opt in to sharing the local install funnel — prints the exact funnel/1
    /// payload first; nothing is sent without that confirmation
    Enable {
        /// The explicit opt-in signal (required: consent must be deliberate)
        #[arg(long)]
        share: bool,
        /// Store root (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
        /// Skip the interactive confirmation (non-TTY scripts; the payload
        /// is still printed)
        #[arg(long)]
        yes: bool,
    },
    /// Stop sending the install funnel (local milestone recording continues)
    Disable {
        /// Store root (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
    },
    /// Rotate the install id (the old id is retired)
    ResetId {
        /// Store root (default: ~/.local/share/whitemagic)
        #[arg(long)]
        store: Option<PathBuf>,
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

/// Importance parser for CLI parity with `session.record`/`memory.create`.
///
/// Non-finite and out-of-range values are caller errors, never silently
/// normalized — serde_json maps NaN to null, which would otherwise fall
/// back to the 0.5 default (2026-09-19 review).
fn parse_importance_arg(value: &str) -> Result<f64, String> {
    let parsed: f64 = value
        .parse()
        .map_err(|_| format!("importance must be a number in 0.0-1.0, got: {value}"))?;
    if !parsed.is_finite() || !(0.0..=1.0).contains(&parsed) {
        return Err(format!(
            "importance must be a number in 0.0-1.0, got: {value}"
        ));
    }
    Ok(parsed)
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
        #[arg(long, default_value_t = 0.5, value_parser = parse_importance_arg)]
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

const fn signature_label(status: wm_mcp::update::SignatureStatus) -> &'static str {
    use wm_mcp::update::SignatureStatus;
    match status {
        SignatureStatus::Verified => "verified (Ed25519)",
        SignatureStatus::NoKey => "UNVERIFIED (no pinned key; --insecure-checksum)",
        SignatureStatus::Missing => "missing signature (transport only)",
        SignatureStatus::Invalid => "INVALID",
    }
}

/// Fetch a release manifest, verify its signature policy, and refuse loudly
/// on anything short of the requested assurance level.
fn load_verified_manifest(
    url: &str,
    insecure_checksum: bool,
) -> anyhow::Result<(
    wm_mcp::update::ReleaseManifest,
    wm_mcp::update::SignatureStatus,
)> {
    use wm_mcp::update::{self, SignatureStatus};
    let text = update::fetch_manifest_text(url, std::time::Duration::from_secs(15))?;
    let manifest: update::ReleaseManifest = serde_json::from_str(&text)?;
    let sig =
        update::fetch_manifest_text(&format!("{url}.sig"), std::time::Duration::from_secs(10))
            .ok()
            .map(|s| s.trim().to_string());
    let key = update::release_public_key();
    let status = update::verify_manifest(text.as_bytes(), sig.as_deref(), key.as_deref());
    if matches!(status, SignatureStatus::Invalid) {
        anyhow::bail!("release manifest signature is INVALID — do not use this release");
    }
    if matches!(status, SignatureStatus::NoKey) && !insecure_checksum {
        anyhow::bail!(
            "no pinned release key in this build (set WM_RELEASE_PUBKEY or rebuild with it); \
             re-run with --insecure-checksum for transport-integrity only"
        );
    }
    Ok((manifest, status))
}

/// A manifest fetch failure is an ordinary state for a local-first tool:
/// report it calmly (structured under `--json`, exit 2) instead of
/// surfacing a transport error chain. Signature failures stay loud.
fn is_fetch_failure(err: &anyhow::Error) -> bool {
    err.chain()
        .any(|cause| cause.to_string().contains("manifest fetch failed"))
}

fn offline_update_message(current: &str) -> String {
    format!(
        "Could not check for updates: network unavailable.\n\n\
         WhiteMagic {current} remains unchanged.\n\n\
         Try again later."
    )
}

fn offline_update_exit(json: bool, current: &str, detail: &str) -> ! {
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "status": "offline",
                "current": current,
                "detail": detail,
                "hint": "try again later; WhiteMagic is unchanged",
            }))
            .unwrap_or_default()
        );
    } else {
        println!("{}", offline_update_message(current));
    }
    std::process::exit(2);
}

#[derive(Subcommand)]
enum UpdateAction {
    /// Check for a newer signed release (notify-only, no installation)
    Check {
        /// Override the manifest URL
        #[arg(long)]
        manifest_url: Option<String>,
        /// Machine-readable result
        #[arg(long)]
        json: bool,
        /// Verify transport integrity only (no pinned key available); loud
        #[arg(long)]
        insecure_checksum: bool,
    },
    /// Download, verify, selftest, and atomically install the latest release
    Install {
        /// Override the manifest URL
        #[arg(long)]
        manifest_url: Option<String>,
        /// Verify transport integrity only (no pinned key available); loud
        #[arg(long)]
        insecure_checksum: bool,
        /// Verify and selftest without swapping the binary
        #[arg(long)]
        dry_run: bool,
    },
    /// Restore the binary saved by the last `wm update install`
    Rollback,
}

/// Print persisted tool-usage rows (calls, success rate, latency) in a
/// stable, human-scannable table.
fn print_usage_rows(rows: &[wm_mcp::stats_view::ToolUsageRow]) {
    println!(
        "  {:<28} {:>8} {:>9} {:>10} {:>10}",
        "tool", "calls", "success", "avg ms", "peak ms"
    );
    for row in rows {
        let success_rate = if row.calls == 0 {
            0.0
        } else {
            (row.successes as f64 / row.calls as f64) * 100.0
        };
        println!(
            "  {:<28} {:>8} {:>8.1}% {:>10.2} {:>10.2}",
            row.name, row.calls, success_rate, row.avg_ms, row.peak_ms
        );
    }
}

fn main() {
    if let Err(err) = run() {
        // Display, not Debug: expected refusals (store lock held by another
        // process, malformed args) must stay a single human line. The
        // default anyhow termination prints `{:?}`, which appends a
        // "Stack backtrace" section whenever RUST_BACKTRACE is set —
        // expected contention must never look like a crash (2026-09-15 audit).
        eprintln!("Error: {err}");
        std::process::exit(1);
    }
}

/// Hidden lab/advanced commands (name, one-line about) as clap knows them.
fn lab_commands() -> Vec<(String, String)> {
    use clap::CommandFactory;
    Cli::command()
        .get_subcommands()
        .filter(|c| c.is_hide_set())
        .map(|c| {
            (
                c.get_name().to_string(),
                c.get_about().map(ToString::to_string).unwrap_or_default(),
            )
        })
        .collect()
}

/// `wm help --all` — the default help plus the hidden lab/advanced surface.
///
/// The existence of complexity does not mean complexity needs to be
/// presented: the default `wm --help` shows the product loop, and this door
/// keeps the laboratory one command away (2026-09-17 reviewer finding).
fn print_full_help() {
    use clap::CommandFactory;
    let mut cmd = Cli::command();
    let _ = cmd.print_help();
    let lab = lab_commands();
    println!("\nLab & advanced (hidden above; all runnable):\n");
    let width = lab.iter().map(|(name, _)| name.len()).max().unwrap_or(0);
    for (name, about) in &lab {
        println!("  {name:<width$}  {about}");
    }
    println!("\nThe product loop is: install → grimoire → connect → work → resume.");
}

fn run() -> anyhow::Result<()> {
    // `wm help --all`: clap's own help subcommand takes no flags, and the
    // lab/advanced commands are hidden from the default listing. Pre-parsed
    // so the full surface stays one command away.
    let argv: Vec<String> = std::env::args().collect();
    if argv.get(1).map(String::as_str) == Some("help")
        && argv.get(2).map(String::as_str) == Some("--all")
    {
        print_full_help();
        return Ok(());
    }
    let cli = Cli::parse();

    // Initialize logging (only to stderr — stdout is for JSON-RPC).
    // Quickstart is the product's first impression: quiet (errors only)
    // unless --verbose, regardless of ambient RUST_LOG (a sandbox that
    // exports RUST_LOG=warn otherwise turns a working demo into a wall of
    // subsystem warnings — first-run feedback, 2026-09-13).
    let log_filter = match &cli.command {
        Commands::Quickstart { verbose: false }
        | Commands::Selftest { verbose: false, .. }
        | Commands::Grimoire { verbose: false, .. } => tracing_subscriber::EnvFilter::new("error"),
        Commands::Quickstart { verbose: true }
        | Commands::Selftest { verbose: true, .. }
        | Commands::Grimoire { verbose: true, .. } => {
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"))
        }
        // Machine modes: stdout is the JSON contract, so stderr stays
        // errors-only. Unrelated subsystem warnings (mesh/Sangha identity,
        // Tantivy probes) belong in human runs (review round 2). Selftest
        // and Grimoire are covered by the quiet arms above (--verbose is the
        // only opt-in there).
        Commands::Status { json: true, .. }
        | Commands::Contract { json: true, .. }
        | Commands::Report { json: true, .. }
        | Commands::Update {
            action: UpdateAction::Check { json: true, .. },
        } => tracing_subscriber::EnvFilter::new("error"),
        _ => tracing_subscriber::EnvFilter::from_default_env(),
    };
    tracing_subscriber::fmt()
        .with_env_filter(log_filter)
        .with_writer(std::io::stderr)
        .init();

    // Load configuration (config file + env overrides)
    let wm_config = wm_mcp::config::WmConfig::load(cli.config.as_ref());
    // Export config values to env vars so subsystems pick them up
    wm_config.export_to_env();

    match cli.command {
        Commands::BuildInfo => println!(
            "{}",
            serde_json::to_string_pretty(&wm_mcp::manifest::build_info())?
        ),
        Commands::Manifest { endpoint } => {
            let body = ureq::get(format!("{}/manifest", endpoint.trim_end_matches('/')))
                .call()?
                .body_mut()
                .read_to_string()?;
            let value: serde_json::Value = serde_json::from_str(&body)?;
            println!("{}", serde_json::to_string_pretty(&value)?);
        }
        Commands::Serve {
            store,
            max_requests,
            rate_limit,
            readonly,
            preservation_readonly,
            profile,
            pack,
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

            // Resolve the tool surface with explicit precedence:
            // WM_TOOL_ALLOWLIST > --pack / WM_TOOL_PACK > --profile /
            // WM_TOOL_PROFILE > curated. `wm serve` with no flag and no env is
            // the product surface. `wm daemon` and library constructors still
            // default to full (cycle tools live outside curated). The
            // resolved identity is exported so `tool_profile_from_env()` sees
            // the winning value.
            let env_profile = std::env::var("WM_TOOL_PROFILE").ok();
            let env_allowlist = std::env::var("WM_TOOL_ALLOWLIST").ok();
            let env_pack = std::env::var("WM_TOOL_PACK").ok();
            if let Some(name) = pack.as_deref() {
                if wm_tools::profiles::pack_from_name(name).is_none() {
                    anyhow::bail!(
                        "unknown tool pack '{name}' — available: {}",
                        wm_tools::profiles::pack_names().join(", ")
                    );
                }
            }
            let resolved = if profile.is_none()
                && pack.is_none()
                && env_profile.is_none()
                && env_allowlist.is_none()
                && env_pack.is_none()
            {
                &wm_tools::profiles::PROFILE_CURATED
            } else {
                wm_tools::profiles::resolve_tool_surface(
                    profile.as_deref(),
                    env_profile.as_deref(),
                    env_allowlist.as_deref(),
                    pack.as_deref().or(env_pack.as_deref()),
                )
            };
            // `std::env::set_var` is unsafe in Rust 2024 (not thread-safe);
            // main() is single-threaded here, before any runtime is spawned.
            #[allow(unsafe_code)]
            unsafe {
                if let Some(pack_name) = resolved.name.strip_prefix("pack:") {
                    std::env::set_var("WM_TOOL_PACK", pack_name);
                    std::env::remove_var("WM_TOOL_PROFILE");
                } else {
                    std::env::set_var("WM_TOOL_PROFILE", resolved.name);
                }
            }
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");

            // Landlock v0 (Phase 5): whole-process FS confinement, opt-in via
            // WM_LANDLOCK=1. Write-class rights are confined to the store
            // root; reads stay free. This must run on the main thread BEFORE
            // the tokio runtime spawns — workers inherit the spawning
            // thread's restriction. Every outcome is non-fatal: unsupported
            // kernels continue unconfined, loudly. Under --readonly the
            // ruleset still applies; only the on-disk report is suppressed
            // (the in-memory report stays served via /status), so a frozen
            // store is never written to.
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
                if !readonly {
                    wm_mcp::landlock_sandbox::persist_report(&store_path, &report);
                }
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

            let mut server = open_server_for_serve(&lmdb_path, readonly, preservation_readonly)?;

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
                let mut config =
                    wm_sangha::MeshNodeConfig::from_env(mesh_bind.as_deref(), &keypair);
                if config.authority_file.is_none() {
                    // Per-store authority side map: action-class mesh traffic
                    // is default-deny until a grant is provisioned here.
                    config.authority_file = Some(store_path.join("mesh_authority.json"));
                }
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
        Commands::Quickstart { .. } => {
            let rt = tokio::runtime::Runtime::new()?;
            rt.block_on(async { run_quickstart().await })?;
        }
        Commands::Selftest { json, .. } => {
            let rt = tokio::runtime::Runtime::new()?;
            let report = rt.block_on(async { wm_mcp::selftest::run().await })?;
            if json {
                println!("{}", serde_json::to_string_pretty(&report)?);
            } else {
                println!("wm selftest {}", report.version);
                for c in &report.checks {
                    println!(
                        "  {} {:<20} {} ({} ms)",
                        if c.ok { "OK  " } else { "FAIL" },
                        c.name,
                        c.detail,
                        c.ms
                    );
                }
                let (passed, total) = report.score();
                println!("{passed}/{total} passed in {} ms", report.total_ms);
            }
            if !report.passed() {
                std::process::exit(1);
            }
        }
        Commands::Status { store, json } => {
            let root = store.unwrap_or_else(default_store_path);
            let report = wm_mcp::status::collect(&root);
            if json {
                println!("{}", serde_json::to_string_pretty(&report)?);
            } else {
                for line in report.lines() {
                    println!("{line}");
                }
                if report.state == "not_initialized" {
                    println!();
                    println!("No working store yet — this is a fresh install.");
                    println!();
                    println!("Verify WhiteMagic (throwaway demo store):");
                    println!("  wm quickstart");
                    println!();
                    println!("Initialize normal use (your store is created on first run):");
                    println!("  wm serve --profile curated");
                    println!();
                    println!("Wire an MCP client:");
                    println!("  wm connect            # wire every detected client");
                    println!("  wm setup              # list clients / per-client setup");
                    println!();
                    println!("Load your data (optional, local-only, idempotent):");
                    println!("  wm ingest --source <folder> --dry-run   # preview files");
                    println!("  wm ingest --source <folder> --redact    # write; re-runs resume");
                } else if !report.store_ok {
                    println!();
                    println!(
                        "The store at {} exists but could not be read — run 'wm doctor' \
                         for a diagnosis.",
                        report.store_path
                    );
                }
            }
        }
        Commands::Grimoire { json, write, .. } => {
            let rt = tokio::runtime::Runtime::new()?;
            let report = rt.block_on(async {
                wm_mcp::grimoire::run(wm_mcp::grimoire::Options {
                    store: default_store_path(),
                    write,
                    check_release: true,
                })
                .await
            })?;
            if json {
                println!("{}", serde_json::to_string_pretty(&report)?);
            } else {
                use wm_mcp::grimoire::StepStatus;
                println!("=== WhiteMagic Grimoire ===");
                println!();
                for s in &report.steps {
                    println!(
                        "  {} {:<11} {}",
                        match s.status {
                            StepStatus::Ok => "[OK]  ",
                            StepStatus::Warn => "[WARN]",
                            StepStatus::Skip => "[SKIP]",
                            StepStatus::Fail => "[FAIL]",
                        },
                        s.name,
                        s.detail
                    );
                }
                println!();
                println!("Core habits (explicit route= is the contract):");
                for (phrase, route) in wm_mcp::grimoire::VOCABULARY {
                    println!("  {phrase:<42} {route}");
                }
                println!();
                if report.environment_ok {
                    if report.core_ready {
                        println!(
                            "WhiteMagic ready and wired. Elapsed: {} ms.",
                            report.total_ms
                        );
                    } else {
                        println!(
                            "Environment OK — no step failed. Not fully activated yet: \
                             wire a client with 'wm connect --write'. Elapsed: {} ms.",
                            report.total_ms
                        );
                    }
                } else {
                    println!(
                        "WhiteMagic needs attention (see [FAIL] steps). Elapsed: {} ms.",
                        report.total_ms
                    );
                }
            }
            if !report.environment_ok {
                std::process::exit(1);
            }
        }
        Commands::Setup {
            client,
            write,
            remove,
            binary,
        } => {
            let exe = match binary {
                Some(p) => p,
                None => std::env::current_exe()?,
            };
            match client {
                None => {
                    println!("=== WhiteMagic Setup ===");
                    println!();
                    println!("Supported clients:");
                    for spec in wm_mcp::setup::specs() {
                        let state = if spec.config_path.exists() {
                            "config found"
                        } else {
                            "config not found"
                        };
                        println!(
                            "  {:<9} {:<16} {} ({state})",
                            spec.id,
                            spec.label,
                            spec.config_path.display()
                        );
                    }
                    println!();
                    println!(
                        "Usage: wm setup <client> [--write] [--remove]  (binary: {})",
                        exe.display()
                    );
                    println!(
                        "Tip: run 'wm connect --write' to configure every detected client in one command."
                    );
                    println!(
                        "Contract: explicit routes are the contract — the wm meta-tool takes route=\"...\" for dependable behavior."
                    );
                }
                Some(id) => match wm_mcp::setup::find(&id) {
                    None => anyhow::bail!(
                        "unknown client '{id}' (expected: opencode, claude, cursor, windsurf, codex)"
                    ),
                    Some(spec) => {
                        if remove {
                            let (msg, backup) = wm_mcp::setup::remove(&spec)?;
                            println!("{msg}");
                            if let Some(b) = backup {
                                println!("backup:  {}", b.display());
                            }
                            return Ok(());
                        }
                        println!("{} ({})", spec.label, spec.id);
                        println!("  config:  {}", spec.config_path.display());
                        println!("  binary:  {}", exe.display());
                        println!(
                            "  status:  {}",
                            if spec.config_path.exists() {
                                "existing config found"
                            } else {
                                "no config yet"
                            }
                        );
                        println!();
                        println!("Proposed addition:");
                        println!("{}", wm_mcp::setup::proposal(&spec, &exe));
                        println!();
                        if let Some(note) = wm_mcp::setup::read_only_note() {
                            println!("Note: {note}");
                            println!();
                        }
                        if let Some(note) = std::env::current_dir()
                            .ok()
                            .and_then(|cwd| wm_mcp::setup::project_isolation_note(&cwd))
                        {
                            println!("Warning: {note}");
                            println!();
                        }
                        if write {
                            let (msg, backup) = wm_mcp::setup::write(&spec, &exe)?;
                            println!("{msg}");
                            if let Some(b) = backup {
                                println!("backup:  {}", b.display());
                            }
                            println!("Next: restart {} and run 'wm selftest'.", spec.label);
                            println!(
                                "Contract: explicit routes are the contract — call the wm meta-tool with route=\"...\" for dependable behavior."
                            );
                        } else {
                            println!(
                                "Dry run. Re-run with --write to patch this config (timestamped backup first)."
                            );
                        }
                    }
                },
            }
        }
        Commands::Connect { write, binary } => {
            let exe = match binary {
                Some(p) => p,
                None => std::env::current_exe()?,
            };
            println!("=== WhiteMagic Connect ===");
            println!("Scanning for installed MCP clients (config or config dir present)...");
            println!("binary:  {}", exe.display());
            println!();
            let outcomes = wm_mcp::setup::connect(&exe, write);
            if outcomes.is_empty() {
                println!("No installed clients detected.");
                println!("Run 'wm setup' to see every supported client and its config path.");
            } else {
                for o in &outcomes {
                    let detail = match &o.action {
                        wm_mcp::setup::ConnectAction::Configured => {
                            "already configured".to_string()
                        }
                        wm_mcp::setup::ConnectAction::Written => "configured".to_string(),
                        wm_mcp::setup::ConnectAction::Proposed => {
                            "found — re-run with --write to configure".to_string()
                        }
                        wm_mcp::setup::ConnectAction::Failed(e) => format!("write failed: {e}"),
                    };
                    println!("  {:<9} {:<16} {detail}", o.id, o.label);
                    if let Some(b) = &o.backup {
                        println!("             backup: {}", b.display());
                    }
                }
                if let Some(note) = wm_mcp::setup::read_only_note() {
                    println!();
                    println!("Note: {note}");
                }
                if let Some(note) = std::env::current_dir()
                    .ok()
                    .and_then(|cwd| wm_mcp::setup::project_isolation_note(&cwd))
                {
                    println!();
                    println!("Warning: {note}");
                }
                println!();
                if write {
                    println!("Restart the configured clients, then run 'wm selftest'.");
                } else {
                    println!("Dry run — no files changed. Re-run 'wm connect --write' to apply.");
                }
            }
            println!(
                "Contract: explicit routes are the contract — call the wm meta-tool with route=\"...\" for dependable behavior."
            );
            let failed = outcomes
                .iter()
                .filter(|o| matches!(o.action, wm_mcp::setup::ConnectAction::Failed(_)))
                .count();
            if failed > 0 {
                eprintln!("\n\u{2716} {failed} client(s) failed to configure — exiting non-zero.");
                std::process::exit(1);
            }
            if write {
                // Config parses are necessary but not sufficient: prove the
                // wired command actually serves (initialize + tools/list) in
                // an isolated HOME, so "connected" is a tested claim.
                match wm_mcp::setup::verify_mcp_session(&exe) {
                    Ok(tools) => println!(
                        "Connection test passed — initialize + tools/list OK ({tools} tools exposed)."
                    ),
                    Err(e) => {
                        eprintln!("Connection test FAILED — {e}");
                        std::process::exit(1);
                    }
                }
            }
        }
        Commands::Update { action } => match action {
            UpdateAction::Check {
                manifest_url,
                json,
                insecure_checksum,
            } => {
                use wm_mcp::update;
                let url = manifest_url.unwrap_or_else(|| update::DEFAULT_MANIFEST_URL.to_string());
                let (manifest, status) = match load_verified_manifest(&url, insecure_checksum) {
                    Ok(v) => v,
                    Err(e) if is_fetch_failure(&e) => {
                        offline_update_exit(json, env!("CARGO_PKG_VERSION"), &e.to_string())
                    }
                    Err(e) => return Err(e),
                };
                let current = env!("CARGO_PKG_VERSION");
                let available = manifest.version != current;
                let exe = std::env::current_exe()?;
                let installed_via = update::detect_installed_via(&exe);
                let root = default_store_path();
                let mut state =
                    update::read_install_state(&root).unwrap_or_else(|| update::InstallState {
                        schema: 1,
                        installed_via: installed_via.to_string(),
                        version: current.to_string(),
                        previous: None,
                        channel: manifest.channel.clone(),
                        update_policy: "notify".to_string(),
                        last_check: None,
                        latest_seen: None,
                    });
                state.last_check = Some(chrono::Utc::now().to_rfc3339());
                state.latest_seen = Some(manifest.version.clone());
                state.channel.clone_from(&manifest.channel);
                let _ = update::write_install_state(&root, &state);

                let sig_label = signature_label(status);
                if json {
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&serde_json::json!({
                            "current": current,
                            "latest": manifest.version,
                            "available": available,
                            "channel": manifest.channel,
                            "published": manifest.published,
                            "signature": sig_label,
                            "installed_via": installed_via,
                            "manifest_url": url,
                        }))?
                    );
                } else {
                    println!("WhiteMagic {current} ({installed_via})");
                    println!("Channel:  {}", manifest.channel);
                    println!("Manifest: {url}");
                    println!("Signature: {sig_label}");
                    println!();
                    if available {
                        println!("Update available: {} -> {}", current, manifest.version);
                        if let Some(notes) = &manifest.notes {
                            println!("{notes}");
                        }
                        println!();
                        match installed_via {
                            "cargo" => println!("Update with: cargo install whitemagic --locked"),
                            "homebrew" => println!("Update with: brew upgrade whitemagic"),
                            "npm" => println!("Update with: npm update -g whitemagic-mcp"),
                            _ => println!(
                                "Update with: rerun the release installer, or download from the release page"
                            ),
                        }
                    } else {
                        println!("Up to date.");
                    }
                }
            }
            UpdateAction::Install {
                manifest_url,
                insecure_checksum,
                dry_run,
            } => {
                use wm_mcp::update;
                let url = manifest_url.unwrap_or_else(|| update::DEFAULT_MANIFEST_URL.to_string());
                let (manifest, status) = match load_verified_manifest(&url, insecure_checksum) {
                    Ok(v) => v,
                    Err(e) if is_fetch_failure(&e) => {
                        offline_update_exit(false, env!("CARGO_PKG_VERSION"), &e.to_string())
                    }
                    Err(e) => return Err(e),
                };
                let exe = std::env::current_exe()?;
                let installed_via = update::detect_installed_via(&exe);
                if installed_via != "release-binary" {
                    anyhow::bail!(
                        "this installation is managed by {installed_via} — update with its \
                         package manager (run 'wm update check' for the exact command)"
                    );
                }
                let current = env!("CARGO_PKG_VERSION");
                if manifest.version == current {
                    println!("WhiteMagic {current} is up to date.");
                    return Ok(());
                }
                let Some(target) = update::current_target() else {
                    anyhow::bail!("no release artifact mapping for this platform");
                };
                let Some(artifact) = manifest.targets.get(target) else {
                    anyhow::bail!(
                        "release {} publishes no artifact for {target}",
                        manifest.version
                    );
                };
                println!("Manifest:  {url} [{}]", signature_label(status));
                println!("Updating:  {current} -> {}", manifest.version);
                let temp = update::sibling(&exe, &format!("new-{}", std::process::id()));
                println!("Downloading {}", artifact.url);
                let bytes = match update::download_to(
                    &artifact.url,
                    &temp,
                    std::time::Duration::from_secs(300),
                ) {
                    Ok(n) => n,
                    Err(e) => {
                        let _ = std::fs::remove_file(&temp);
                        return Err(e);
                    }
                };
                println!("  {bytes} bytes; verifying sha256");
                let digest = update::sha256_file(&temp)?;
                if !digest.eq_ignore_ascii_case(&artifact.sha256) {
                    let _ = std::fs::remove_file(&temp);
                    anyhow::bail!(
                        "sha256 mismatch: manifest says {} but download hashed {digest}",
                        artifact.sha256
                    );
                }
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt as _;
                    std::fs::set_permissions(&temp, std::fs::Permissions::from_mode(0o755))?;
                }
                println!(
                    "Verified sha256 ({}…); running candidate `wm selftest`",
                    &digest[..12]
                );
                let report = match update::install_from_file(
                    &exe,
                    &temp,
                    &manifest.version,
                    &default_store_path(),
                    dry_run,
                ) {
                    Ok(r) => r,
                    Err(e) => {
                        let _ = std::fs::remove_file(&temp);
                        return Err(e);
                    }
                };
                println!(
                    "{}",
                    serde_json::to_string_pretty(&serde_json::json!({
                        "from": report.from,
                        "to": report.to,
                        "backup": report.backup,
                        "selftest_ok": report.selftest_ok,
                        "dry_run": report.dry_run,
                        "swapped": report.swapped,
                        "signature": signature_label(status),
                    }))?
                );
                if report.swapped {
                    println!("Update committed. Roll back with 'wm update rollback'.");
                } else {
                    println!("Dry run complete — nothing was swapped.");
                }
            }
            UpdateAction::Rollback => {
                let exe = std::env::current_exe()?;
                let version = wm_mcp::update::rollback_install(&exe, &default_store_path())?;
                println!("Rolled back to WhiteMagic {version}.");
            }
        },
        Commands::Doctor {
            store,
            check_integrity,
            repair,
            network,
            kaizen,
            deep,
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
                run_doctor(store, check_integrity, repair, kaizen, deep)?
            };
            if issues > 0 {
                std::process::exit(1);
            }
        }
        Commands::Geneseed {
            repo,
            max_commits,
            min_confidence,
            stats_only,
        } => {
            println!("=== WhiteMagic Geneseed Miner ===");
            println!("Repository: {}", repo.display());
            if stats_only {
                let stats = wm_tools::expansion::geneseed::get_geneseed_stats(&repo)
                    .map_err(|e| anyhow::anyhow!("{e}"))?;
                println!("Total commits analyzed: {}", stats.total_commits);
                println!("Optimization commits:   {}", stats.optimization_commits);
                println!("Refactor commits:       {}", stats.refactor_commits);
                println!("Bugfix commits:         {}", stats.bugfix_commits);
                println!("Feature commits:        {}", stats.feature_commits);
                println!("Tracked files:          {}", stats.total_files_tracked);
                println!(
                    "Average commit age:     {:.1} days",
                    stats.avg_commit_age_days
                );
            } else {
                let patterns = wm_tools::expansion::geneseed::mine_geneseed_patterns(
                    &repo,
                    min_confidence,
                    max_commits,
                )
                .map_err(|e| anyhow::anyhow!("{e}"))?;
                println!(
                    "Discovered {} codebase patterns (confidence >= {:.2}):",
                    patterns.len(),
                    min_confidence
                );
                println!();
                println!(
                    "{:<24} {:<14} {:<12} {:<10} {:<30}",
                    "PATTERN ID", "TYPE", "LONGEVITY", "CONFIDENCE", "MESSAGE"
                );
                println!("{}", "-".repeat(95));
                for p in patterns.iter().take(30) {
                    let msg = p.commit_message.lines().next().unwrap_or("");
                    let msg_short = if msg.len() > 28 { &msg[..28] } else { msg };
                    println!(
                        "{:<24} {:<14} {:<10}d {:<10.2} {:<30}",
                        p.pattern_id, p.pattern_type, p.longevity_days, p.confidence, msg_short
                    );
                }
            }
        }
        Commands::Stats { store, week } => {
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
            println!();
            // Cross-process usage: the persisted snapshot, not this fresh
            // process's zeroed counters (P1, 2026-09-15).
            if week {
                let history = wm_mcp::stats_view::load_history(&lmdb_path);
                let rows = wm_mcp::stats_view::weekly_deltas(&history, 7);
                println!("=== Tool Usage (last ~7 daily rollups) ===");
                if history.is_empty() {
                    println!("No daily rollups yet — history accumulates one row per service day.");
                } else if rows.is_empty() {
                    println!("No tool calls recorded across {} rollup(s).", history.len());
                } else {
                    print_usage_rows(&rows);
                    println!(
                        "Estimated from the last {} of {} daily rollup(s); counter resets at each server restart are counted from zero.",
                        history.len().min(7),
                        history.len()
                    );
                }
            } else {
                println!("=== Tool Usage (persisted, cumulative) ===");
                match wm_mcp::stats_view::load_tool_stats_checked(&lmdb_path) {
                    Err(error) => println!("Persisted usage {error}"),
                    Ok(rows) if rows.is_empty() => {
                        println!(
                            "No persisted usage yet — call some tools, then let the server checkpoint or stop it cleanly."
                        );
                    }
                    Ok(rows) => print_usage_rows(&rows),
                }
            }
        }
        Commands::Contract { json, check, out } => {
            let tmp = std::env::temp_dir().join(format!("wm-contract-{}", std::process::id()));
            let lmdb = tmp.join("lmdb");
            std::fs::create_dir_all(&lmdb)?;
            let manifest = {
                let server = wm_mcp::McpServer::with_defaults(&lmdb)?;
                wm_mcp::contract::build_manifest(server.registry(), env!("CARGO_PKG_VERSION"))
            };
            let _ = std::fs::remove_dir_all(&tmp);
            let violations = wm_mcp::contract::check_known_unconditional_reads(&manifest);
            if let Some(path) = out {
                std::fs::write(&path, serde_json::to_string_pretty(&manifest)?)?;
                println!("Manifest written to {}", path.display());
            }
            if json {
                println!("{}", serde_json::to_string_pretty(&manifest)?);
            } else {
                // Success is explicit: `--check` in CI reads exit 0 either
                // way, but a human running it should see the contract held
                // (2026-09-19 review: silent success looked like a no-op).
                println!(
                    "Route schema manifest: {} routes ({} declared, {} undeclared)",
                    manifest["counts"]["routes"],
                    manifest["counts"]["declared"],
                    manifest["counts"]["undeclared"]
                );
                if violations.is_empty() {
                    println!("Contract OK — 0 violations (curated unconditional-read check)");
                } else {
                    for violation in &violations {
                        println!("  [FAIL] {violation}");
                    }
                }
            }
            if check && !violations.is_empty() {
                std::process::exit(1);
            }
        }
        Commands::Report { store, out, json } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let rt = tokio::runtime::Runtime::new()?;
            if json {
                let report = rt.block_on(wm_mcp::report::build(&store_path));
                println!("{}", serde_json::to_string_pretty(&report)?);
            } else {
                let out_dir = out.unwrap_or_else(|| {
                    PathBuf::from(format!(
                        "wm-report-{}",
                        chrono::Utc::now().format("%Y-%m-%d")
                    ))
                });
                let path = rt.block_on(wm_mcp::report::write_bundle(&store_path, &out_dir))?;
                println!("Sanitized support bundle written to {}", path.display());
                println!(
                    "  report.json  — version, platform, store health, index drift, selftest, env allowlist"
                );
                println!("  README.txt   — what is included and what is excluded");
                println!("Nothing was transmitted; review the bundle before sharing it.");
            }
        }
        Commands::Telemetry { command } => match command {
            TelemetryCommands::Schema { json } => {
                if json {
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&wm_mcp::telemetry_view::schema_json())?
                    );
                } else {
                    for line in wm_mcp::telemetry_view::schema_lines() {
                        println!("{line}");
                    }
                }
            }
            TelemetryCommands::Status { store, json } => {
                let store_path = store.unwrap_or_else(default_store_path);
                let status = wm_mcp::telemetry_view::load_funnel_status(&store_path);
                if json {
                    println!("{}", serde_json::to_string_pretty(&status)?);
                } else {
                    println!("=== Telemetry Funnel (local only; nothing is transmitted) ===");
                    println!(
                        "Store: {} ({})",
                        store_path.display(),
                        if status["store_present"].as_bool().unwrap_or(false) {
                            "store present"
                        } else {
                            "no store yet"
                        }
                    );
                    let channel = status["channel"].as_str().unwrap_or("unknown");
                    match status["channel_ref"].as_str() {
                        Some(reference) => println!("Channel: {channel} (ref: {reference})"),
                        None => println!("Channel: {channel}"),
                    }
                    println!(
                        "First launch: {}",
                        status["first_launch"].as_str().unwrap_or("none recorded")
                    );
                    let milestones = status["milestones"]
                        .as_array()
                        .map(|items| {
                            items
                                .iter()
                                .filter_map(serde_json::Value::as_str)
                                .collect::<Vec<_>>()
                                .join(", ")
                        })
                        .filter(|joined| !joined.is_empty())
                        .unwrap_or_else(|| "none yet".to_string());
                    println!("Milestones: {milestones}");
                    let active_days = status["active_days"]
                        .as_array()
                        .map(|items| {
                            items
                                .iter()
                                .filter_map(serde_json::Value::as_u64)
                                .map(|day| format!("d{day}"))
                                .collect::<Vec<_>>()
                                .join(", ")
                        })
                        .filter(|joined| !joined.is_empty())
                        .unwrap_or_else(|| "none yet".to_string());
                    println!("Active days: {active_days}");
                    println!(
                        "Transport: {}",
                        status["transport"].as_str().unwrap_or("none")
                    );
                }
            }
            TelemetryCommands::Preview { store, limit, json } => {
                let store_path = store.unwrap_or_else(|| wm_config.store_path());
                let lmdb_path = store_path.join("lmdb");
                let records = wm_mcp::telemetry_view::load_recent_telemetry(&lmdb_path, limit);
                let (payload, redactions) = wm_mcp::telemetry_view::build_preview(&records);
                if !json {
                    println!("=== Telemetry Preview (display-only; nothing is sent) ===");
                    println!("Store: {}", lmdb_path.display());
                    println!("Records: {}", records.len());
                    if redactions.is_empty() {
                        println!("Redaction pass: clean (no credential-shaped spans found)");
                    } else {
                        println!(
                            "Redaction pass: scrubbed {} credential-span class(es) — a firing redaction inside content-free telemetry is itself a finding",
                            redactions.len()
                        );
                    }
                    println!();
                }
                println!("{}", serde_json::to_string_pretty(&payload)?);
            }
            TelemetryCommands::Enable { share, store, yes } => {
                if !share {
                    eprintln!(
                        "Refusing to enable: pass --share to opt in (consent must be deliberate). Nothing was sent."
                    );
                    return Ok(());
                }
                let store_path = store.unwrap_or_else(default_store_path);
                let mut share = wm_tools::expansion::funnel_share::read_share(&store_path);
                if share.install_id.is_none() {
                    share.install_id = Some(wm_tools::expansion::funnel_share::new_install_id());
                }
                let state =
                    wm_tools::expansion::funnel::read_state(&store_path).unwrap_or_default();
                let counts = wm_memory::MemoryStore::open_inspection(store_path.join("lmdb"))
                    .map(|opened| wm_tools::expansion::funnel_share::local_counts(&opened))
                    .unwrap_or_default();
                let Some(envelope) = wm_tools::expansion::funnel_share::build_envelope(
                    &store_path,
                    &state,
                    &share,
                    counts,
                ) else {
                    eprintln!("Could not build the funnel/1 payload (no install id).");
                    return Ok(());
                };
                println!("=== Install-funnel sharing (opt-in) ===");
                println!("This is the exact payload sent when milestones change:");
                println!("{}", serde_json::to_string_pretty(&envelope)?);
                println!();
                println!("Content-free: no memory text, prompts, paths, hostnames, or IPs. The");
                println!("install_id is a random identifier — `wm telemetry reset-id` rotates it,");
                println!("`wm telemetry disable` stops sending.");
                println!(
                    "Endpoint: {}",
                    wm_tools::expansion::funnel_share::endpoint()
                );
                let confirmed = if yes {
                    true
                } else if std::io::stdin().is_terminal() {
                    print!("Type 'yes' to opt in: ");
                    std::io::Write::flush(&mut std::io::stdout())?;
                    let mut line = String::new();
                    std::io::stdin().read_line(&mut line)?;
                    line.trim().eq_ignore_ascii_case("yes")
                } else {
                    eprintln!(
                        "Refusing to enable from a non-interactive shell without --yes: an agent may not consent for a human."
                    );
                    return Ok(());
                };
                if !confirmed {
                    println!("Not enabled — nothing was sent.");
                    return Ok(());
                }
                let enabled = wm_tools::expansion::funnel_share::enable_with(
                    &store_path,
                    share.install_id.take(),
                )?;
                let Some(envelope) = wm_tools::expansion::funnel_share::build_envelope(
                    &store_path,
                    &state,
                    &enabled,
                    counts,
                ) else {
                    return Ok(());
                };
                let result = wm_tools::expansion::funnel_share::send_envelope(
                    &store_path,
                    &envelope,
                    &wm_tools::expansion::funnel_share::UreqPoster,
                );
                if result == "ok" {
                    println!("Sharing enabled — first payload sent.");
                } else {
                    println!(
                        "Sharing enabled — first send did not complete ({result}); the payload is spooled and retried once on the next launch."
                    );
                }
                if let Some(id) = enabled.install_id.as_deref() {
                    println!("Install id: {id}");
                }
            }
            TelemetryCommands::Disable { store } => {
                let store_path = store.unwrap_or_else(default_store_path);
                let state = wm_tools::expansion::funnel_share::disable(&store_path)?;
                println!("Install-funnel sharing disabled. No further payloads will be sent.");
                println!(
                    "Local milestone recording continues (WM_FUNNEL_DISABLED=1 stops that too)."
                );
                if let Some(id) = state.install_id.as_deref() {
                    println!("Install id retained: {id} (rotate with `wm telemetry reset-id`)");
                }
            }
            TelemetryCommands::ResetId { store } => {
                let store_path = store.unwrap_or_else(default_store_path);
                let previous =
                    wm_tools::expansion::funnel_share::read_share(&store_path).install_id;
                let state = wm_tools::expansion::funnel_share::reset_id(&store_path)?;
                println!("Install id rotated — the previous id is retired.");
                if let Some(previous) = previous {
                    println!("Previous: {previous}");
                }
                if let Some(next) = state.install_id.as_deref() {
                    println!("Current:  {next}");
                }
            }
        },
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
            sample_full,
            init,
            store,
        } => {
            let sample_text = || {
                if sample_full {
                    wm_mcp::config::WmConfig::sample_toml_full()
                } else {
                    wm_mcp::config::WmConfig::sample_toml()
                }
            };
            if sample {
                print!("{}", sample_text());
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
                std::fs::write(&config_path, sample_text())?;
                println!("Created sample config at {}", config_path.display());
                if sample_full {
                    println!("Full sample: daemon schedules, hemisphere and cloud LLM settings.");
                } else {
                    println!(
                        "Edit it to set the store path, embedder, or LLM endpoint — \
                         'wm config --sample-full' shows every option."
                    );
                }
                return Ok(());
            }
            // `--sample-full` prints the research sample (the 9.1.9 tester
            // found it fell through to the effective-config dump because
            // only `--sample` was checked). `--init --sample-full` is handled
            // above — init wins when both are present.
            if sample_full {
                print!("{}", sample_text());
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
            citta_interval,
            watchdog_audit_interval,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            let lmdb_path = store_path.join("lmdb");
            std::fs::create_dir_all(&lmdb_path)?;

            // Landlock v0: confine write-class FS rights to the store root
            // when requested. Applied on the main thread before the daemon
            // spawns any runtime or worker threads (thread-local restriction,
            // inherited by descendants) — same contract as `serve`.
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
                        "Landlock v0 degraded — daemon is NOT fully confined"
                    ),
                }
                wm_mcp::landlock_sandbox::persist_report(&store_path, &report);
                Some(report)
            } else {
                None
            };

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

            if let Some(report) = landlock_report {
                server.set_landlock_report(report);
            }

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
            if let Some(secs) = citta_interval {
                daemon_cfg.citta_interval = std::time::Duration::from_secs(secs);
            }
            if let Some(secs) = watchdog_audit_interval {
                daemon_cfg.watchdog_audit_interval = std::time::Duration::from_secs(secs);
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
            wait,
        } => {
            let store_path = store.unwrap_or_else(default_store_path);
            wm_mcp::migrate::run_migration(
                v2_dir.as_deref(),
                v2_db.as_deref(),
                &store_path,
                dry_run,
                galaxy.as_deref(),
                wait,
            )?;
        }
        Commands::Ingest {
            source,
            store,
            dry_run,
            limit,
            galaxy,
            redact,
            wait,
            include_credential_files,
        } => {
            let store_path = store.unwrap_or_else(default_store_path);
            wm_mcp::ingest::run_ingest(
                &source,
                &store_path,
                dry_run,
                limit,
                galaxy.as_deref(),
                redact,
                wait,
                include_credential_files,
            )?;
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
        Commands::RedactContent {
            store,
            galaxy,
            tag,
            wait,
            apply,
        } => {
            let store_path = store.unwrap_or_else(|| wm_config.store_path());
            run_redact_content(&store_path, &galaxy, tag.as_deref(), apply, wait)?;
        }
        Commands::Session { command } => {
            run_session_command(command)?;
        }
        Commands::AtRest { command } => match command {
            AtRestCommands::Migrate {
                store,
                galaxy,
                batch,
                dry_run,
                wait,
            } => {
                let store_path = store.unwrap_or_else(|| wm_config.store_path());
                run_at_rest_migrate(&store_path, &galaxy, batch, dry_run, wait)?;
            }
            AtRestCommands::Status { store, json } => {
                let store_path = store.unwrap_or_else(|| wm_config.store_path());
                run_at_rest_status(&store_path, json)?;
            }
        },
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
    // The write env-open does not fail on a held lock — it wedges on an
    // internal mutex (9.1.6). Probe non-blocking first so the documented
    // "a server may be running" refusal actually fires.
    if let Err(e) = wm_memory::MemoryStore::probe_write_lock(store_path) {
        anyhow::bail!(
            "Could not take the LMDB lock at {} — a server may be running \
             (stop the store's wm-serve unit first). Underlying: {e}",
            lmdb_path.display()
        );
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

    // The write env-open does not fail on a held lock — it wedges on an
    // internal mutex (9.1.6). Probe non-blocking first so the documented
    // "a server may be running" refusal actually fires.
    if let Err(e) = wm_memory::MemoryStore::probe_write_lock(store_path) {
        anyhow::bail!(
            "Could not take the LMDB lock at {} — a server may be running. \
             Stop it before backing up. Underlying: {e}",
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

    // Envelope v2 (S4): a self-describing backup. Same envelope module the
    // session export/import path uses — one validator, three uses. Written
    // before the manifest so its digest covers the final bytes.
    let envelope = wm_memory::envelope::EnvelopeHeader::new("store_backup", files.len());
    let envelope_path = dest.join("envelope.json");
    std::fs::write(&envelope_path, serde_json::to_string_pretty(&envelope)?)?;

    // SHA256SUMS manifest over every copied file (paths relative to data/),
    // plus the root-level envelope.json entry (Q07-F1): the backup's own
    // label is inside the integrity story too, and `sha256sum -c` still
    // works from the backup directory.
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
    let envelope_digest: String = {
        let mut hasher = sha2::Sha256::new();
        hasher.update(std::fs::read(&envelope_path)?);
        hex(&hasher.finalize())
    };
    let _ = writeln!(sums, "{envelope_digest}  envelope.json");
    std::fs::write(dest.join("SHA256SUMS"), sums)?;

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
    let mut data_count = 0usize;
    for line in std::fs::read_to_string(&sums_path)?.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let (expected, manifest_path) = line
            .split_once("  ")
            .ok_or_else(|| anyhow::anyhow!("bad SHA256SUMS line: {line}"))?;
        // Manifest paths are relative to the backup root with a data/ prefix
        // (store files) or the bare root-level `envelope.json` entry
        // (Q07-F1), so `sha256sum -c` works from the backup directory itself.
        let abs = if manifest_path == "envelope.json" {
            backup.join("envelope.json")
        } else {
            let rel = manifest_path.strip_prefix("data/").ok_or_else(|| {
                anyhow::anyhow!(
                    "bad SHA256SUMS path (expected data/ prefix or envelope.json): {manifest_path}"
                )
            })?;
            data_count += 1;
            data_src.join(rel)
        };
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
        if header.count != data_count {
            eprintln!(
                "WARN: envelope declares {} data files but SHA256SUMS lists {data_count}; \
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

    // Store ownership is not negotiable: `--force` overwrites an existing
    // *idle* store, it never overrides a live writer. Same non-blocking
    // probe as backup/trust (9.1.6): swapping the store root underneath a
    // running server replaces LMDB/Tantivy files while the process still
    // holds mappings, which is how a "successful" restore corrupts the
    // search index (independent review, 2026-09-17).
    if store_path.join("lmdb").join("data.mdb").exists() {
        if let Err(e) = wm_memory::MemoryStore::probe_write_lock(store_path) {
            // A missing lock file means no live LMDB writer exists to hold it.
            if e.kind() != std::io::ErrorKind::NotFound {
                anyhow::bail!(
                    "Refusing to restore over {} — a server (or another writer) owns the \
                     store. Stop it first (e.g. systemctl --user stop wm-serve@<name>). \
                     --force overwrites an existing idle store; it never overrides store \
                     ownership. Underlying: {e}",
                    store_path.display()
                );
            }
        }
    }

    if store_path.exists() && !force {
        anyhow::bail!(
            "Target store {} already exists. Use --force to overwrite (the existing store will be REPLACED).",
            store_path.display()
        );
    }
    if let Some(parent) = store_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    // Prepare on the target filesystem while the previous target remains intact.
    // Restore is an offline operation: callers must exclude concurrent writers.
    let parent = store_path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| std::path::Path::new("."));
    let candidate = tempfile::Builder::new()
        .prefix(".wm-restore-candidate-")
        .tempdir_in(parent)?;
    copy_tree(&data_src, candidate.path(), &mut Vec::new())?;

    // Older backups can be byte-exact yet lack named databases this build
    // expects (2026-09-14 drill: a 9.0.0 backup had no `cold_storage`).
    // Complete the schema in place before declaring the restore usable.
    // The LMDB environment lives in the store root's `lmdb/` subdirectory.
    let lmdb_dir = candidate.path().join("lmdb");
    let schema_path = if lmdb_dir.is_dir() {
        lmdb_dir
    } else {
        candidate.path().to_path_buf()
    };
    match wm_memory::MemoryStore::ensure_schema(&schema_path) {
        Ok(created) if !created.is_empty() => println!(
            "Schema completed: created {} missing database(s): {}",
            created.len(),
            created.join(", ")
        ),
        Ok(_) => {}
        Err(e) => {
            anyhow::bail!(
                "Restore candidate schema completion failed: {e}. \
                 Existing target {} was not replaced.",
                store_path.display()
            );
        }
    }

    promote_restore_candidate(candidate.path(), store_path)?;

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

/// Offline same-filesystem promotion. The rollback directory is uniquely reserved;
/// it is never auto-deleted while it contains the old target after an error.
fn promote_restore_candidate(
    candidate: &std::path::Path,
    target: &std::path::Path,
) -> anyhow::Result<()> {
    promote_restore_candidate_with(candidate, target, |from, to| std::fs::rename(from, to))
}

fn promote_restore_candidate_with(
    candidate: &std::path::Path,
    target: &std::path::Path,
    promote: impl FnOnce(&std::path::Path, &std::path::Path) -> std::io::Result<()>,
) -> anyhow::Result<()> {
    if !target.exists() {
        return Ok(promote(candidate, target)?);
    }
    let parent = target
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| std::path::Path::new("."));
    let rollback = tempfile::Builder::new()
        .prefix(".wm-restore-rollback-")
        .tempdir_in(parent)?;
    let old = rollback.path().join("previous");
    std::fs::rename(target, &old)?;
    if let Err(error) = promote(candidate, target) {
        if let Err(recovery) = std::fs::rename(&old, target) {
            let retained = rollback.keep();
            anyhow::bail!(
                "Restore promotion failed: {error}; rollback failed: {recovery}. Previous target retained at {}",
                retained.join("previous").display()
            );
        }
        anyhow::bail!("Restore promotion failed: {error}; previous target restored unchanged.");
    }
    // Cleanup failure is not failed promotion: new target is usable, old retained.
    if let Err(error) = std::fs::remove_dir_all(&old) {
        let retained = rollback.keep();
        eprintln!(
            "WARN: restore promoted successfully; previous target cleanup failed: {error}; inspect {}",
            retained.display()
        );
    }
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
/// Parse the `--galaxy` filter for at-rest migration, defaulting to every
/// record galaxy.
fn at_rest_galaxies(filter: &[String]) -> anyhow::Result<Vec<wm_core::Galaxy>> {
    if filter.is_empty() {
        return Ok(wm_memory::RECORD_GALAXIES.to_vec());
    }
    let mut galaxies = Vec::new();
    for name in filter {
        let lower = name.to_lowercase();
        let galaxy = wm_core::Galaxy::from_db_name(&lower)
            .or_else(|| wm_core::Galaxy::from_db_name(name))
            .ok_or_else(|| anyhow::anyhow!("unknown galaxy '{name}'"))?;
        if !wm_memory::RECORD_GALAXIES.contains(&galaxy) {
            anyhow::bail!(
                "galaxy '{name}' is not a record galaxy (karma, dharma, associations, and \
                 embeddings store non-record data and are never migrated)"
            );
        }
        galaxies.push(galaxy);
    }
    Ok(galaxies)
}

/// `wm at-rest migrate` — Q39 slice B encrypt-on-rewrite migration.
fn run_at_rest_migrate(
    store_path: &std::path::Path,
    galaxy_filter: &[String],
    batch: usize,
    dry_run: bool,
    wait: u64,
) -> anyhow::Result<()> {
    let at_rest_config = wm_memory::AtRestConfig::from_env().map_err(|e| anyhow::anyhow!("{e}"))?;
    run_at_rest_migrate_with_config(
        store_path,
        galaxy_filter,
        batch,
        dry_run,
        wait,
        &at_rest_config,
    )
}

/// Testable core of `wm at-rest migrate` with an explicit at-rest config.
fn run_at_rest_migrate_with_config(
    store_path: &std::path::Path,
    galaxy_filter: &[String],
    batch: usize,
    dry_run: bool,
    wait: u64,
    at_rest_config: &wm_memory::AtRestConfig,
) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.join("data.mdb").exists() {
        anyhow::bail!("No LMDB data found at {}.", lmdb_path.display());
    }
    let galaxies = at_rest_galaxies(galaxy_filter)?;
    // A live server holds the Tantivy writer lock (and the LMDB lock); fail
    // fast with holder names instead of hanging on the open.
    wm_mcp::store_busy::ensure_store_available(store_path, wait)?;

    if dry_run {
        // Dry-run opens read-only: the keyring status (mode + coverage) is
        // readable without resolving the RK, and nothing is written.
        let store = wm_memory::MemoryStore::open_inspection(&lmdb_path)
            .map_err(|e| anyhow::anyhow!("{e}"))?;
        match store.at_rest_status() {
            wm_memory::AtRestStatus::Absent => {
                if at_rest_config.mode() == wm_memory::AtRestMode::Off {
                    println!(
                        "Dry run: no keyring at {} and WM_AT_REST_MODE=off — nothing to migrate \
                         (plaintext pass-through).",
                        lmdb_path.display()
                    );
                } else {
                    println!(
                        "Dry run: no keyring at {} yet, but mode '{}' is configured — the first \
                         writable open would initialize the keyring and seal plaintext records in \
                         {} record galaxies (batch {batch}).",
                        lmdb_path.display(),
                        at_rest_config.mode(),
                        galaxies.len()
                    );
                    for galaxy in &galaxies {
                        let count = store.count(*galaxy).unwrap_or(0);
                        println!("  {}: {count} entries", galaxy.db_name());
                    }
                    println!(
                        "Run without --dry-run (with the store's key source set) to initialize \
                         and migrate; take a `wm backup` first."
                    );
                }
            }
            wm_memory::AtRestStatus::Malformed { reason } => {
                anyhow::bail!("keyring is malformed ({reason}) — repair it before migrating");
            }
            wm_memory::AtRestStatus::Present(present) => {
                println!(
                    "Dry run: keyring mode '{}', {}/{} galaxy DEKs wrapped — would seal plaintext \
                     records in {} record galaxies (batch {batch}).",
                    present.meta.mode,
                    present.wrapped_deks,
                    present.galaxies,
                    galaxies.len()
                );
                let counts = wm_memory::at_rest_record_counts(&store).unwrap_or_default();
                for galaxy in &galaxies {
                    if let Some(c) = counts.iter().find(|c| c.galaxy == galaxy.db_name()) {
                        println!(
                            "  {}: {} plaintext, {} sealed, {} non-record rows",
                            galaxy.db_name(),
                            c.plaintext,
                            c.sealed,
                            c.non_record
                        );
                    } else {
                        println!("  {}: 0 entries", galaxy.db_name());
                    }
                }
                println!(
                    "Run without --dry-run (with the store's key source set) to apply; take a \
                     `wm backup` first."
                );
            }
        }
        return Ok(());
    }

    // The migration needs an unlocked keyring: open with the supplied
    // at-rest configuration (from the environment in the CLI path). An `off`
    // config on a keyring store is refused by the split-brain guard; a
    // keyring-absent store reports the no-op.
    //
    // The write open wedges (not fails) on a held LMDB writer lock (9.1.6):
    // probe non-blocking first so the documented "stop the server" refusal
    // actually fires instead of hanging.
    if let Err(e) = wm_memory::MemoryStore::probe_write_lock(store_path) {
        anyhow::bail!(
            "Could not take the LMDB lock at {} — a server may be running \
             (stop the store's wm-serve unit first). Underlying: {e}",
            lmdb_path.display()
        );
    }
    let store = wm_memory::MemoryStore::open_with_at_rest(
        &lmdb_path,
        wm_memory::MemoryStore::default_map_size(),
        at_rest_config,
    )
    .map_err(|e| anyhow::anyhow!("{e}"))?;
    if store.at_rest_status() == wm_memory::AtRestStatus::Absent {
        println!(
            "No keyring at {} — nothing to migrate (plaintext pass-through).",
            lmdb_path.display()
        );
        return Ok(());
    }

    let report = wm_memory::migrate_at_rest_records(&store, &galaxies, batch)
        .map_err(|e| anyhow::anyhow!("{e}"))?;
    for galaxy in &report.galaxies {
        println!(
            "{}: sealed {} ({} already sealed, {} undecodable, {} non-record rows){}",
            galaxy.galaxy,
            galaxy.encrypted,
            galaxy.already_sealed,
            galaxy.undecodable,
            galaxy.skipped_non_record,
            if galaxy.done { " — done" } else { "" }
        );
    }
    println!(
        "Migrated {} record(s) across {} galaxy(ies){}.",
        report.total_encrypted,
        report.galaxies.len(),
        if report.all_done() {
            " — all selected galaxies complete"
        } else {
            " — re-run to continue (crash-safe ledger)"
        }
    );
    Ok(())
}

/// `wm at-rest status` — read the migration ledger without writing.
fn run_at_rest_status(store_path: &std::path::Path, json: bool) -> anyhow::Result<()> {
    let lmdb_path = store_path.join("lmdb");
    if !lmdb_path.join("data.mdb").exists() {
        anyhow::bail!("No LMDB data found at {}.", lmdb_path.display());
    }
    let store =
        wm_memory::MemoryStore::open_inspection(&lmdb_path).map_err(|e| anyhow::anyhow!("{e}"))?;
    let ledger = wm_memory::migration_ledger(&store).map_err(|e| anyhow::anyhow!("{e}"))?;
    if json {
        let payload = serde_json::json!({
            "at_rest": match store.at_rest_status() {
                wm_memory::AtRestStatus::Absent => serde_json::json!({"mode": "off", "keyring": false}),
                wm_memory::AtRestStatus::Malformed { reason } => {
                    serde_json::json!({"keyring": true, "malformed": reason})
                }
                wm_memory::AtRestStatus::Present(present) => serde_json::json!({
                    "keyring": true,
                    "mode": present.meta.mode.as_str(),
                    "wrapped_deks": present.wrapped_deks,
                    "galaxies": present.galaxies,
                }),
            },
            "migration": ledger,
        });
        println!("{}", serde_json::to_string_pretty(&payload)?);
        return Ok(());
    }
    match &ledger {
        None => println!(
            "No keyring at {} — plaintext pass-through; no migration state.",
            lmdb_path.display()
        ),
        Some(ledger) if ledger.galaxies.is_empty() => {
            println!("Keyring present; no migration has run yet (no `migration:v1` ledger rows).");
        }
        Some(ledger) => {
            let mode = match store.at_rest_status() {
                wm_memory::AtRestStatus::Present(present) => present.meta.mode.to_string(),
                wm_memory::AtRestStatus::Malformed { reason } => format!("malformed ({reason})"),
                wm_memory::AtRestStatus::Absent => "off".to_string(),
            };
            println!(
                "Migration ledger (mode {mode}, updated {}):",
                ledger.updated_at
            );
            for (name, state) in &ledger.galaxies {
                if state.done {
                    println!("  {name}: {} sealed, done", state.encrypted);
                } else {
                    println!(
                        "  {name}: {} sealed, resume cursor {}",
                        state.encrypted, state.cursor_hex
                    );
                }
            }
        }
    }
    Ok(())
}

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
    // The write env-open does not fail on a held lock — it wedges on an
    // internal mutex (9.1.6). Probe non-blocking first so the documented
    // "a server may be running" refusal actually fires.
    if let Err(e) = wm_memory::MemoryStore::probe_write_lock(store_path) {
        anyhow::bail!(
            "Could not take the LMDB lock at {} — a server may be running \
             (stop the store's wm-serve unit first). Underlying: {e}",
            lmdb_path.display()
        );
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

    // Same non-blocking guard as backup/trust: a live server owns the store
    // and its search index, so reindexing under it would wedge on the LMDB
    // open and race the writer lock.
    if let Err(e) = wm_memory::MemoryStore::probe_write_lock(store_path) {
        anyhow::bail!(
            "Could not take the LMDB lock at {} — a server may be running \
             (stop the store's wm-serve unit first). Underlying: {e}",
            lmdb_path.display()
        );
    }

    if backup && !dry_run {
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| anyhow::anyhow!("clock error: {e}"))?
            .as_secs();
        // Collision-safe: claim the directory exclusively so two reindexes
        // in the same second cannot silently merge into one backup (the
        // second would overwrite the first's files). On a taken name the
        // suffix counts up: tantivy.bak.<ts>-1, -2, …
        let mut attempt = 0u32;
        let backup_path = loop {
            let candidate = if attempt == 0 {
                lmdb_path.join(format!("tantivy.bak.{ts}"))
            } else {
                lmdb_path.join(format!("tantivy.bak.{ts}-{attempt}"))
            };
            match std::fs::create_dir(&candidate) {
                Ok(()) => break candidate,
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => attempt += 1,
                Err(e) => return Err(e.into()),
            }
        };
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

    println!(
        "Rebuilding Tantivy index from LMDB ({scope}) — this can take a minute on large stores..."
    );
    let report = rebuild_index_recovering(&store, &tantivy_path, galaxy_filter)?;
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

/// Rebuild the search index from LMDB, recovering from an index that cannot
/// be opened (or opens but cannot be rebuilt): quarantine it, create a fresh
/// index, rebuild, and verify against the canonical LMDB store.
///
/// The LMDB store is canonical; the search index is a disposable
/// accelerator. This is the shared recovery path for `wm reindex` and
/// `wm doctor --repair` (review round 2, 2026-09-17).
fn rebuild_index_recovering(
    store: &wm_memory::MemoryStore,
    tantivy_path: &std::path::Path,
    galaxy_filter: &[String],
) -> anyhow::Result<wm_memory::IndexRebuildReport> {
    let (mut search, quarantined) = wm_memory::reindex::open_or_quarantine(tantivy_path)?;
    if let Some(path) = quarantined {
        println!(
            "Index could not be opened — quarantined to {}",
            path.display()
        );
    }
    let report = match wm_memory::rebuild_index(store, &search, galaxy_filter) {
        Ok(report) => report,
        Err(error) => {
            // An index can open and still be unusable (e.g. meta.json
            // references a segment file that is missing — the failure lands
            // at commit). Quarantine and retry once on a fresh index.
            drop(search);
            let quarantine = wm_memory::reindex::quarantine_and_recreate(tantivy_path)?;
            println!(
                "Rebuild against the open index failed ({error}); quarantined {} and \
                 retrying on a fresh index.",
                quarantine.display()
            );
            search = wm_memory::SearchEngine::open(tantivy_path)?;
            wm_memory::rebuild_index(store, &search, galaxy_filter)?
        }
    };

    // Verify: the index must now match what a rebuild would produce. A
    // remaining gap inside the sanitization-skip reserve is documented
    // behaviour, not drift.
    let consistency = wm_memory::check_consistency(store, &search);
    let class = wm_memory::classify_drift(store, &search);
    if class.healable_total > 0 {
        anyhow::bail!(
            "Rebuild finished but verification found healable drift: LMDB={} Tantivy={} \
             (healable={}). The LMDB store is canonical and intact; report this as a bug.",
            consistency.total_lmdb,
            consistency.total_tantivy,
            class.healable_total
        );
    }
    if class.skip_reserve_total > 0 {
        println!(
            "Verified: LMDB={} Tantivy={} — no healable drift ({} docs in the \
             sanitization-skip reserve)",
            consistency.total_lmdb, consistency.total_tantivy, class.skip_reserve_total
        );
    } else {
        println!(
            "Verified: LMDB={} Tantivy={} — no drift",
            consistency.total_lmdb, consistency.total_tantivy
        );
    }
    Ok(report)
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
                    && wm_memory::printable_ratio(&mem.content) >= 0.5
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

/// Run the credential-redaction retrofit (`wm redact-content`).
///
/// Dry-run by default: reports what WOULD be redacted without touching the
/// store. With `--apply`, matching rows are rewritten in place (same id,
/// revision-chained) and reindexed — take a `wm backup` first. Galaxies
/// filter via repeatable `--galaxy`; `--tag` scopes to memories carrying an
/// exact tag (e.g. `source:convo-harvest-20260911`).
fn run_redact_content(
    store_path: &std::path::Path,
    galaxy_filter: &[String],
    tag: Option<&str>,
    apply: bool,
    wait_secs: u64,
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

    wm_mcp::store_busy::ensure_store_available(store_path, wait_secs)?;

    let store = wm_memory::MemoryStore::open_default(&lmdb_path)?;
    let search = wm_memory::SearchEngine::open(&tantivy_path)?;

    let report = wm_memory::redact::redact_store_content(&store, &search, &galaxies, tag, apply)?;

    let kinds = if report.kinds.is_empty() {
        String::new()
    } else {
        report
            .kinds
            .iter()
            .map(|(k, v)| format!("{k}={v}"))
            .collect::<Vec<_>>()
            .join(" ")
    };

    if !apply {
        println!(
            "Dry run (store untouched): scanned={} would_redact={} already_clean={} filtered_out={}",
            report.scanned, report.redacted, report.already_clean, report.filtered_out
        );
        if !kinds.is_empty() {
            println!("Kinds: {kinds}");
        }
        println!("Run with --apply to redact in place (take a 'wm backup' first).");
        return Ok(());
    }

    println!(
        "Redaction complete: scanned={} redacted={} already_clean={} filtered_out={}",
        report.scanned, report.redacted, report.already_clean, report.filtered_out
    );
    if !kinds.is_empty() {
        println!("Kinds: {kinds}");
    }
    for g in &report.galaxies {
        if g.redacted > 0 {
            println!(
                "  {:12} scanned={:7} redacted={:7} clean={:7} filtered={:6}",
                g.galaxy, g.scanned, g.redacted, g.already_clean, g.filtered_out
            );
        }
    }
    println!(
        "A read-only server on this store should restart to observe the \
         reindexed store."
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

/// Attach write-time indexing to the CLI session path (2026-09-17 reviewer
/// finding): the MCP server indexes every session write immediately; the CLI
/// must do the same or `wm status` reports the very next write as index
/// drift. A live server holds the Tantivy writer lock and a blind open blocks
/// behind it, so probe first and disclose the degraded case honestly.
fn open_session_search(
    store_root: &Path,
    lmdb_path: &Path,
) -> Option<std::sync::Arc<wm_memory::SearchEngine>> {
    if !wm_mcp::store_busy::store_holders(store_root).is_empty() {
        eprintln!(
            "note: a live server holds this store's search index — records will not be \
             indexed until it restarts; run 'wm reindex' if search misses them"
        );
        return None;
    }
    let tantivy_path = wm_memory::reindex::tantivy_path_for(lmdb_path);
    if let Err(e) = std::fs::create_dir_all(&tantivy_path) {
        eprintln!(
            "warning: search index directory not creatable ({e}) — records will not be indexed"
        );
        return None;
    }
    match wm_memory::SearchEngine::open(&tantivy_path) {
        Ok(engine) => Some(std::sync::Arc::new(engine)),
        Err(e) => {
            eprintln!(
                "warning: search index not opened ({e}) — records will not be indexed; \
                 run 'wm reindex' once the store is free"
            );
            None
        }
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
        // CLI parity (2026-09-17 reviewer finding): `--store <fresh-path>` is
        // an explicit instruction, and the MCP path initializes a store when
        // the server starts — the CLI must not refuse what the transport
        // accepts. Reads stay side-effect-free: continuity on an
        // uninitialized store answers truthfully without creating anything.
        if let SessionCommands::Continuity { .. } = &command {
            let hint = format!(
                "store not initialized at {} — run 'wm session start --store <path>' \
                 or start 'wm serve' first",
                lmdb_path.display()
            );
            println!(
                "{}",
                serde_json::to_string_pretty(&serde_json::json!({
                    "status": "success",
                    "previous_session": null,
                    "turns": [],
                    "count": 0,
                    "message": "no previous session found",
                    "hint": hint,
                }))?
            );
            return Ok(());
        }
        eprintln!("initializing new store at {}", store_root.display());
    }
    let store = std::sync::Arc::new(wm_memory::MemoryStore::open(
        &lmdb_path,
        4 * 1024 * 1024 * 1024,
    )?);
    let search = open_session_search(&store_root, &lmdb_path);

    let rt = tokio::runtime::Runtime::new()?;
    let result = rt.block_on(async {
        let mut ctx = Context::new(BrainWave::Beta);
        match command {
            SessionCommands::Start { title, user, .. } => {
                SessionStartTool::new(store)
                    .with_search(search)
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
                SessionRecordTool::new(store)
                    .with_search(search)
                    .call(&mut ctx, args)
                    .await
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
                SessionCheckpointTool::new(store)
                    .with_search(search)
                    .call(&mut ctx, args)
                    .await
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

/// Collector sent-log feed summary: `(records, age_seconds)`, or `None` when
/// the ring is absent. The collector only runs for instrumented captures, so
/// absence is disclosure (INFO), never an issue.
fn yama_feed_summary(path: &std::path::Path) -> Option<(usize, u64)> {
    let meta = std::fs::metadata(path).ok()?;
    let age = meta
        .modified()
        .ok()
        .and_then(|m| m.elapsed().ok())
        .map_or(0, |d| d.as_secs());
    let records = std::fs::read_to_string(path).map_or(0, |body| {
        body.lines().filter(|l| !l.trim().is_empty()).count()
    });
    Some((records, age))
}

/// A collector feed older than this is disclosed as stale (15 minutes).
const YAMA_FEED_STALE_SECONDS: u64 = 900;

/// Rendered `wm doctor` at-rest disclosure (pure: data in, text out — no I/O).
struct AtRestDisclosure {
    /// Complete text including the `[OK]/[INFO]/[WARN]` prefix and detail
    /// lines (trailing newline included).
    text: String,
    /// True when the disclosure is an issue the doctor must count.
    issue: bool,
}

/// RK-source disclosure for a parsed keyring: how the root key was obtained
/// at initialization, plus the key-file path when the store/environment
/// still knows it. Key values are never disclosed.
fn at_rest_key_source_line(present: &wm_memory::AtRestStatusPresent) -> String {
    match (present.meta.key_source.as_str(), present.key_file.as_ref()) {
        ("generated_key_file", Some(path)) => format!(
            "RK source: generated_key_file — key file {}",
            path.display()
        ),
        ("key_file", Some(path)) => {
            format!(
                "RK source: key_file — configured key file {}",
                path.display()
            )
        }
        ("key_file", None) => "RK source: key_file — configured with WM_AT_REST_KEY_FILE \
                               (path not recorded in the keyring meta)"
            .to_string(),
        ("env_root_key", _) => {
            "RK source: env_root_key — WM_AT_REST_ROOT_KEY (value never disclosed)".to_string()
        }
        ("argon2id_passphrase", _) => {
            "RK source: argon2id_passphrase — WM_AT_REST_PASSPHRASE (value never disclosed)"
                .to_string()
        }
        (other, Some(path)) => format!("RK source: {other} — key file {}", path.display()),
        (other, None) => format!("RK source: {other}"),
    }
}

/// Format the section-11i at-rest disclosure for a keyring status (Q39
/// slice A/B). Every rendered line is honest about what is actually
/// encrypted: counts come from the WMEN magic only (never decryption), and
/// a partial wrapped-DEK count or unreadable ledger is a WARN + issue
/// (writable opens refuse until repaired — fail-closed).
fn format_at_rest_disclosure(
    status: &wm_memory::AtRestStatus,
    store_root: &Path,
    counts: Option<&[wm_memory::GalaxyAtRestCounts]>,
    ledger: Option<&wm_memory::MigrationLedger>,
) -> AtRestDisclosure {
    use wm_memory::{AtRestMode, AtRestStatus};
    let keyring_path = store_root.join("lmdb");
    match status {
        AtRestStatus::Absent => AtRestDisclosure {
            text: "[INFO] At-rest: plaintext pass-through (WM_AT_REST_MODE=off) — records are \
                   NOT encrypted;\n       at-rest protection is filesystem permissions only. \
                   Enable keyfile/passphrase mode with the WM_AT_REST_* knobs (AGENTS.md).\n"
                .to_string(),
            issue: false,
        },
        AtRestStatus::Present(present) => {
            let keyring = keyring_path.display();
            let coverage = format!(
                "{}/{} galaxy DEKs wrapped",
                present.wrapped_deks, present.galaxies
            );
            let source = at_rest_key_source_line(present);
            let partial = present.wrapped_deks < present.galaxies;
            let prefix = if partial { "[WARN]" } else { "[OK]  " };
            let partial_suffix = if partial {
                " — PARTIAL keyring; writable opens refuse (fail-closed) until the missing \
                 wrapped DEKs are repaired"
            } else {
                ""
            };
            // Slice-B record inventory: sealed vs plaintext per galaxy, plus
            // the migration ledger state. Pure formatting — the caller
            // supplies read-only counts.
            use std::fmt::Write as _;
            let mut inventory = String::new();
            if let Some(counts) = counts {
                let sealed: u64 = counts.iter().map(|c| c.sealed).sum();
                let plaintext: u64 = counts.iter().map(|c| c.plaintext).sum();
                let _ = write!(
                    inventory,
                    "\n       Records (12 record galaxies): {sealed} sealed, {plaintext} plaintext \
                     (WMEN magic only)"
                );
                if plaintext > 0 {
                    let per_galaxy = counts
                        .iter()
                        .filter(|c| c.plaintext > 0)
                        .map(|c| format!("{}={}", c.galaxy, c.plaintext))
                        .collect::<Vec<_>>()
                        .join(", ");
                    let _ = write!(inventory, "\n       Plaintext by galaxy: {per_galaxy}");
                }
            }
            if let Some(ledger) = ledger {
                if ledger.galaxies.is_empty() {
                    inventory
                        .push_str("\n       Migration: no run yet (migration:v1 ledger empty)");
                } else {
                    let mut parts = Vec::new();
                    for (name, state) in &ledger.galaxies {
                        parts.push(format!(
                            "{name}: {}{}",
                            state.encrypted,
                            if state.done {
                                " done"
                            } else {
                                " (resume pending)"
                            }
                        ));
                    }
                    let _ = write!(
                        inventory,
                        "\n       Migration: {} (updated {})",
                        parts.join(", "),
                        ledger.updated_at
                    );
                }
            }
            match present.meta.mode {
                AtRestMode::Keyfile => AtRestDisclosure {
                    text: format!(
                        "{prefix} At-rest: mode B (keyfile) — {coverage} (keyring: {keyring})\
                         {partial_suffix}\n       {source}{inventory}\n       Physical-purge only \
                         — never crypto-erasure on mode B; record sealing is Q39 slice B \
                         (WMEN envelope).\n"
                    ),
                    issue: partial,
                },
                AtRestMode::Passphrase => {
                    let argon = present.meta.argon2.as_ref().map_or_else(
                        || "argon2id parameters missing from meta".to_string(),
                        |a| {
                            format!(
                                "argon2id m={} KiB, t={}, p={}, v={}",
                                a.m_cost_kib, a.t_cost, a.p_cost, a.version
                            )
                        },
                    );
                    AtRestDisclosure {
                        text: format!(
                            "{prefix} At-rest: mode C (passphrase) — {coverage} (keyring: \
                             {keyring}){partial_suffix}\n       {source}\n       {argon}\
                             {inventory}\n       Passphrase crypto-erasure is not yet \
                             advertised — record sealing is Q39 slice B (WMEN envelope).\n"
                        ),
                        issue: partial,
                    }
                }
                AtRestMode::Off => AtRestDisclosure {
                    text: format!(
                        "[WARN] At-rest: keyring present at {keyring} but its meta records mode \
                         'off' — contradictory state; writable opens refuse (fail-closed) until \
                         the keyring is repaired.\n"
                    ),
                    issue: true,
                },
            }
        }
        AtRestStatus::Malformed { reason } => AtRestDisclosure {
            text: format!(
                "[WARN] At-rest: keyring present at {} but its meta is malformed: {reason}\n       \
                 Fail-closed: writable opens refuse until the keyring is repaired (read-only \
                 inspection still works).\n",
                keyring_path.display()
            ),
            issue: true,
        },
    }
}

#[allow(clippy::fn_params_excessive_bools)] // doctor flags are naturally booleans
fn run_doctor(
    store: Option<PathBuf>,
    check_integrity: bool,
    repair: bool,
    kaizen: bool,
    deep: bool,
) -> anyhow::Result<u32> {
    let store_path = store.unwrap_or_else(default_store_path);
    let lmdb_path = store_path.join("lmdb");
    let mut issues = 0u32;
    let mut optional_suppressed = 0u32;

    println!("=== WhiteMagic Doctor ===");
    println!();

    // 1. LMDB store check — a missing store is the normal state on a fresh
    // install, not a failure. Point at the real first step (`wm quickstart`)
    // instead of `wm serve` (which blocks on stdio).
    if !lmdb_path.exists() {
        println!(
            "[INFO] No store at {} yet — this is normal on a fresh install.",
            lmdb_path.display()
        );
        println!("       Run 'wm quickstart' for the 30-second two-process demo (isolated store),");
        println!(
            "       or 'wm serve' to start an MCP server (it creates the store on first use)."
        );
        println!();
        println!("=== Doctor Summary ===");
        println!("Fresh install — nothing to check yet. 'wm quickstart' is the verification step.");
        return Ok(0);
    }
    println!("[OK]   LMDB store: {}", lmdb_path.display());

    // 1a. Search-index open check / recovery: a Tantivy index that cannot be
    // opened used to fail every doctor run (the readonly server open) before
    // it could diagnose or repair anything. LMDB is canonical — with
    // --repair, quarantine the broken index and rebuild from LMDB.
    let tantivy_path = lmdb_path.join("tantivy");
    if tantivy_path.exists() {
        // Quiet open: this process exits before later writes could matter;
        // the loud disclosure belongs to the long-lived read-only server.
        if let Err(open_error) = wm_memory::SearchEngine::open_readonly_quiet(&tantivy_path) {
            println!();
            println!("--- Search Index ---");
            println!(
                "[WARN] Tantivy index at {} cannot be opened: {open_error}",
                tantivy_path.display()
            );
            if repair {
                let store = wm_memory::MemoryStore::open_inspection(&lmdb_path)?;
                let report = rebuild_index_recovering(&store, &tantivy_path, &[])?;
                println!(
                    "Index rebuilt from canonical LMDB: scanned={} indexed={} skipped={}",
                    report.scanned, report.indexed, report.skipped
                );
            } else {
                println!(
                    "       Run 'wm reindex --store {}' (or 'wm doctor --repair') to \
                     rebuild it from the canonical LMDB store.",
                    store_path.display()
                );
            }
        }
    }

    // 1b. Integrity check (if requested)
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
        match wm_memory::SearchEngine::open_readonly_quiet(&tantivy_path) {
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

    // 8. Tool surface — one canonical accounting from the capability
    // manifest (registry entries → full-profile routes → active-profile
    // routes → MCP tools); keeps doctor, selftest, and tools/list from
    // disagreeing about what a "tool" is.
    let manifest = server.capability_manifest();
    let count = |key: &str| {
        manifest["counts"]
            .get(key)
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(0)
    };
    let profile = manifest["configuration"]["profile"]
        .as_str()
        .unwrap_or("active");
    let entrypoints = count("mcp_entrypoints");
    let mcp = if entrypoints > 0 {
        entrypoints.to_string()
    } else {
        "handshake-time".to_string()
    };
    println!(
        "[OK]   Tool surface: {} registry entries → {} full-profile routes → {} active-profile routes ({profile}) → {mcp} MCP tools; +1 meta-router",
        count("boundary_registry_including_meta"),
        count("full_pre_profile"),
        count("profile_pre_meta"),
    );

    // 9. Karma chain integrity — deep verification (recomputes payload hashes)
    let karma_path = lmdb_path.join("data.mdb");
    if karma_path.exists() {
        match server.karma_ledger() {
            Some(ledger) => match ledger.verify_integrity_deep() {
                Ok(report) if report.chain.valid => {
                    println!(
                        "[OK]   Karma chain: {} entries deep-verified, {} legacy (linkage-only){}",
                        report.entries_deep_verified,
                        report.legacy_entries,
                        if report.fully_deep {
                            ""
                        } else {
                            " — historical entries predate deep verification"
                        }
                    );
                }
                Ok(report) => {
                    println!(
                        "[FAIL] Karma chain: tamper detected at entry {:?} — {}",
                        report.chain.broken_at,
                        report
                            .chain
                            .violation
                            .as_deref()
                            .unwrap_or("unknown violation")
                    );
                }
                Err(e) => {
                    println!("[WARN] Karma chain: deep verification could not run: {e}");
                }
            },
            None => println!(
                "[INFO] Karma chain: ledger not enabled in this server (optional governance subsystem)"
            ),
        }
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
                                if clf_ok || reg_ok { "OK" } else { "INFO" },
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
                                    if deep {
                                        println!(
                                            "       [WARN] Calibration samples exist but nothing is fitted — run conformal.fit_classifier / conformal.fit_regressor, then conformal.export"
                                        );
                                        issues += 1;
                                    } else {
                                        println!(
                                            "       [INFO] Calibration samples exist but nothing is fitted (optional subsystem) — run 'wm doctor --deep' to grade"
                                        );
                                        optional_suppressed += 1;
                                    }
                                } else {
                                    println!(
                                        "       [INFO] No calibration fitted yet — calibrate via conformal.fit_classifier / conformal.fit_regressor"
                                    );
                                }
                            }
                        }
                        Err(e) => {
                            if deep {
                                println!("[WARN] Conformal state corrupt (parse failed: {e})");
                                issues += 1;
                            } else {
                                println!(
                                    "[INFO] Conformal state unreadable (optional subsystem) — run 'wm doctor --deep' to grade"
                                );
                                optional_suppressed += 1;
                            }
                        }
                    }
                }
                Err(e) => {
                    if deep {
                        println!("[WARN] Conformal state unparseable: {e}");
                        issues += 1;
                    } else {
                        println!(
                            "[INFO] Conformal state unparseable (optional subsystem) — run 'wm doctor --deep' to grade"
                        );
                        optional_suppressed += 1;
                    }
                }
            },
            Err(e) => {
                if deep {
                    println!("[WARN] Cannot read conformal state: {e}");
                    issues += 1;
                } else {
                    println!(
                        "[INFO] Cannot read conformal state (optional subsystem) — run 'wm doctor --deep' to grade"
                    );
                    optional_suppressed += 1;
                }
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
                // P-PROV-5 surface pin: disclose what binary produced this
                // surface and its pin so a reviewed release can be pinned
                // externally (rug-pull tripwire — any surface change repins).
                if let Some(pin) = c.surface_hash.as_deref() {
                    println!(
                        "       Surface pin: {} ({} tools, built {})",
                        &pin[..pin.len().min(16)],
                        c.registered_count,
                        c.binary_version.as_deref().unwrap_or("unknown binary")
                    );
                }
                // Binary/store skew notice (informational, not a violation):
                // the last server start on this store ran a different build
                // than this doctor binary, so the surface may have changed
                // under you — check the pin against the reviewed release.
                if c.binary_version.as_deref() != Some(env!("CARGO_PKG_VERSION")) {
                    println!(
                        "[INFO] Profile contract was written by build {} (doctor is {}) — surface may differ; compare pins",
                        c.binary_version.as_deref().unwrap_or("unknown"),
                        env!("CARGO_PKG_VERSION")
                    );
                }
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
    //      read-only. Degradation is never silent: `partial` is INFO (the
    //      expected outcome on older ABIs — the ruleset still bites), and a
    //      real application failure is a WARN that counts as an issue.
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
            // `partial` is the honest outcome on older Landlock ABIs (e.g. the
            // VM kernel): the ruleset still bites, just on a subset of rights.
            // It is INFO, not an issue — only a real failure is WARN.
            let partial = report.outcome == wm_mcp::landlock_sandbox::LandlockOutcome::Partial;
            if partial {
                println!(
                    "[INFO] Landlock: partial — write-class FS rights confined on the supported rights subset ({})",
                    report.detail
                );
            } else {
                println!(
                    "[WARN] Landlock requested but not fully enforced ({}): {}",
                    report.outcome.as_str(),
                    report.detail
                );
                issues += 1;
            }
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

    // 11d-2. Subprocess sandbox (B2) — which OS runner would wrap external
    //        commands right now? Detection is live (WM_SANDBOX_RUNNER →
    //        PATH lookup, same as the dispatch path); the per-server
    //        dispatch/degraded counters are disclosed via `/status`.
    println!();
    match wm_core::sandbox::detect_runner() {
        Some(info) => println!(
            "[OK]   Subprocess sandbox: runner {} (source: {}) — Sandbox::Subprocess tools wrap spawns",
            info.path.display(),
            info.source.as_str()
        ),
        None => println!(
            "[INFO] Subprocess sandbox: no runner resolved (set WM_SANDBOX_RUNNER or install \
             mandala-sandbox on PATH) — declared spawns run unconfined"
        ),
    }

    // 11d-3. Yama bridge (observe) — the collector's sent-log ring is the
    //        local feed Lakshmi reads mirror-first. Absence is disclosure
    //        (the collector only runs for instrumented S4-style captures),
    //        never an issue; a stale ring is called stale, not healthy.
    println!();
    let feed_path = std::env::var("WM_YAMA_FEED_PATH").map_or_else(
        |_| {
            PathBuf::from(std::env::var("HOME").unwrap_or_default())
                .join(".local/share/yama-collector/sent.jsonl")
        },
        PathBuf::from,
    );
    match yama_feed_summary(&feed_path) {
        Some((records, age)) if age <= YAMA_FEED_STALE_SECONDS => println!(
            "[OK]   Yama bridge: collector feed {records} record(s), last write {age}s ago ({})",
            feed_path.display()
        ),
        Some((records, age)) => println!(
            "[INFO] Yama bridge: collector feed stale — {records} record(s), last write {age}s ago ({})",
            feed_path.display()
        ),
        None => println!(
            "[INFO] Yama bridge: no collector feed at {} (collector not running — observation records land only during instrumented runs)",
            feed_path.display()
        ),
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
    //      The probe is real (fixed 2026-09-12): the configured embedder
    //      is constructed and asked for one vector — env presence alone is
    //      not a claim, and a dead endpoint used to still print [OK].
    println!();
    {
        let embedder = wm_memory::create_embedder();
        let backend = embedder.backend_name();
        if backend == "stub" {
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
            } else if deep {
                println!(
                    "[WARN] Recall route: BM25 full-text fallback (stub embedder, episodic lane empty) — measured R@1 0.64 vs 0.86 on the episodic route (LongMemEval-S 50q, S8 protocol 2026-09-01); memory writes populate the episodic mirror, which upgrades the default route"
                );
                issues += 1;
            } else {
                println!(
                    "[INFO] Recall route: BM25 full-text fallback (stub embedder, episodic lane empty) — memory writes populate the episodic mirror, which upgrades the default route; run 'wm doctor --deep' to grade route quality"
                );
                optional_suppressed += 1;
            }
        } else {
            let started = std::time::Instant::now();
            match embedder.embed("wm doctor recall-route probe") {
                Ok(vector) => {
                    let elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
                    let vectors = server
                        .store_arc()
                        .count(wm_core::Galaxy::Embeddings)
                        .unwrap_or(0);
                    let cache_count = server.store_arc().embedding_cache_count().unwrap_or(0);
                    println!(
                        "[OK]   Recall route: hybrid fusion — backend '{backend}' ({}, dim {}) answered a real probe in {elapsed_ms:.0} ms; stored vectors: {vectors}, content-hash cache: {cache_count}",
                        embedder.cache_namespace(),
                        vector.len(),
                    );
                    if vectors == 0 {
                        println!(
                            "[INFO]         no per-memory vectors on this store yet — hybrid results fall back to the episodic lane until writes or memory.reembed populate them"
                        );
                    }
                }
                Err(error) => {
                    println!(
                        "[WARN] Recall route: embedder backend '{backend}' is configured but the probe failed: {error} — hybrid will fall back to the episodic lane"
                    );
                    issues += 1;
                }
            }
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

    // 11i. At-rest key mode (Q39 slice A/B) — per-store disclosure of the
    //      keyring mode plus the slice-B record inventory (sealed vs
    //      plaintext by WMEN magic) and migration ledger state. Read-only:
    //      the status reads the keyring meta row only; the RK is never
    //      resolved and nothing is created or written here.
    println!();
    {
        let status = server.store().at_rest_status();
        let counts = if matches!(status, wm_memory::AtRestStatus::Present(_)) {
            wm_memory::at_rest_record_counts(server.store()).ok()
        } else {
            None
        };
        let ledger = if matches!(status, wm_memory::AtRestStatus::Present(_)) {
            wm_memory::migration_ledger(server.store()).ok().flatten()
        } else {
            None
        };
        let disclosure =
            format_at_rest_disclosure(&status, &store_path, counts.as_deref(), ledger.as_ref());
        print!("{}", disclosure.text);
        if disclosure.issue {
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
            let actor_name = |e: &wm_governance::WriteAuditEntry| -> String {
                // The first question any investigation asks is "which
                // agent" — user, session, AND compartment (the compartment
                // was recorded but never rendered before this fix).
                match (&e.actor_user, &e.actor_session, &e.actor_compartment) {
                    (None, None, None) => "unknown actor".to_string(),
                    (u, s, c) => {
                        let mut name = match (u, s) {
                            (Some(u), Some(s)) => format!("{u}@{s}"),
                            (Some(u), None) => u.clone(),
                            (None, Some(s)) => format!("session {s}"),
                            (None, None) => "unknown".to_string(),
                        };
                        if let Some(c) = c {
                            name.push('[');
                            name.push_str(c);
                            name.push(']');
                        }
                        name
                    }
                }
            };
            let labeled = scan
                .iter()
                .filter(|e| actor_name(e) != "unknown actor")
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
            if journal_entries > 0 && labeled == 0 {
                println!(
                    "       [INFO] no entries name an actor (expected on pre-S11b stores; new stores at 0% mean dispatches run without identity)"
                );
            }
            if !scan.is_empty() {
                // Top actors + compartment distribution + confirm audit —
                // the per-actor breakdown the healthy path never showed.
                let mut by_actor: std::collections::HashMap<String, usize> =
                    std::collections::HashMap::new();
                let mut by_compartment: std::collections::HashMap<String, usize> =
                    std::collections::HashMap::new();
                let mut destructive = 0usize;
                let mut unconfirmed = 0usize;
                for e in &scan {
                    *by_actor.entry(actor_name(e)).or_insert(0) += 1;
                    *by_compartment
                        .entry(
                            e.actor_compartment
                                .clone()
                                .unwrap_or_else(|| "undeclared".to_string()),
                        )
                        .or_insert(0) += 1;
                    if e.confirmed.is_some() {
                        destructive += 1;
                        if e.confirmed == Some(false) {
                            unconfirmed += 1;
                        }
                    }
                }
                let mut top: Vec<(&String, &usize)> = by_actor.iter().collect();
                top.sort_by(|a, b| b.1.cmp(a.1).then_with(|| a.0.cmp(b.0)));
                let top_str = top
                    .iter()
                    .take(5)
                    .map(|(name, n)| format!("{name}×{n}"))
                    .collect::<Vec<_>>()
                    .join(", ");
                println!("       top actors: {top_str}");
                let mut compartments: Vec<(&String, &usize)> = by_compartment.iter().collect();
                compartments.sort_by(|a, b| b.1.cmp(a.1).then_with(|| a.0.cmp(b.0)));
                let comp_str = compartments
                    .iter()
                    .map(|(name, n)| format!("{name}×{n}"))
                    .collect::<Vec<_>>()
                    .join(", ");
                println!("       compartments: {comp_str}");
                println!(
                    "       destructive dispatches: {destructive} (unconfirmed: {unconfirmed})"
                );
            }
            if !mis.is_empty() {
                issues += 1;
                for entry in mis.iter().take(5) {
                    let when = i64::try_from(entry.timestamp)
                        .ok()
                        .and_then(|t| chrono::DateTime::<chrono::Utc>::from_timestamp(t, 0))
                        .map_or_else(|| entry.timestamp.to_string(), |d| d.to_rfc3339());
                    // S11b: name the actor when the journal has one — the
                    // first question any investigation asks.
                    let actor = actor_name(entry);
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

    // 13. Kaizen Correlation Insights (if requested)
    if kaizen {
        println!();
        println!("--- Kaizen Correlation Insights ---");
        let tool = wm_tools::expansion::correlation::KaizenCorrelateTool::new(server.store_arc());
        let mut ctx = wm_core::Context::default();
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()?;
        let res = rt.block_on(wm_core::Tool::call(&tool, &mut ctx, serde_json::json!({})));
        match res {
            Ok(v) => {
                if let Some(corrs) = v.get("correlations").and_then(serde_json::Value::as_array) {
                    println!("[OK]   Computed correlations across {} pairs:", corrs.len());
                    for c in corrs {
                        let vx = c
                            .get("variable_x")
                            .and_then(serde_json::Value::as_str)
                            .unwrap_or("x");
                        let vy = c
                            .get("variable_y")
                            .and_then(serde_json::Value::as_str)
                            .unwrap_or("y");
                        let r = c
                            .get("pearson_r")
                            .and_then(serde_json::Value::as_f64)
                            .unwrap_or(0.0);
                        let strength = c
                            .get("strength")
                            .and_then(serde_json::Value::as_str)
                            .unwrap_or("");
                        println!("       {vx:<16} vs {vy:<16}: r = {r:+.3} ({strength})");
                    }
                }
                if let Some(insights) = v
                    .get("workflow_guidance")
                    .and_then(serde_json::Value::as_array)
                {
                    for insight in insights {
                        if let Some(s) = insight.as_str() {
                            println!("       [GUIDE] {s}");
                        }
                    }
                }
            }
            Err(e) => {
                println!("[WARN] Kaizen correlation evaluation: {e}");
            }
        }
    }

    println!();
    println!("=== Doctor Summary ===");
    if issues == 0 {
        println!("All systems healthy.");
        if optional_suppressed > 0 {
            println!(
                "{optional_suppressed} optional subsystem note(s) suppressed — run 'wm doctor --deep' to grade them."
            );
        }
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
    println!("  5. If something looks wrong, run 'wm doctor --deep' for the full gate.");
    println!("  6. Load notes, docs, or transcripts: 'wm ingest --source <folder>' —");
    println!("     dry-run first; --redact scrubs credential-shaped content; local-only.");

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

#[cfg(test)]
mod restore_preservation_tests {
    use super::*;
    use wm_memory::{Memory, MemoryStore};

    fn backup_fixture(source: &std::path::Path, out: &std::path::Path) -> std::path::PathBuf {
        run_backup(source, Some(out)).unwrap();
        std::fs::read_dir(out)
            .unwrap()
            .next()
            .unwrap()
            .unwrap()
            .path()
    }

    /// Q07-F1: `envelope.json` is inside the integrity manifest — tampering
    /// with the backup label is detected before restore reads it.
    #[test]
    fn envelope_json_tamper_is_detected_by_the_manifest() {
        let tmp = tempfile::tempdir().unwrap();
        let source = tmp.path().join("source");
        let store = MemoryStore::open_default(source.join("lmdb")).unwrap();
        let mut record = Memory::new(wm_core::Galaxy::Codex, "envelope tamper fixture".into());
        record.metadata.id = uuid::Uuid::from_u128(0x931);
        store.put(wm_core::Galaxy::Codex, &record).unwrap();
        drop(store);

        let backup = backup_fixture(&source, &tmp.path().join("backups"));
        let sums = std::fs::read_to_string(backup.join("SHA256SUMS")).unwrap();
        assert!(
            sums.lines().any(|line| line.ends_with("  envelope.json")),
            "envelope.json must be covered by SHA256SUMS:\n{sums}"
        );

        // Tamper with the label only: change created_at, keep data files.
        let envelope_path = backup.join("envelope.json");
        let mut envelope: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&envelope_path).unwrap()).unwrap();
        envelope["created_at"] = serde_json::json!("1999-01-01T00:00:00Z");
        std::fs::write(
            &envelope_path,
            serde_json::to_string_pretty(&envelope).unwrap(),
        )
        .unwrap();

        let target = tmp.path().join("target");
        let error = run_restore(&backup, &target, true).unwrap_err();
        assert!(
            error.to_string().contains("envelope.json"),
            "tampered envelope must be named in the failure: {error}"
        );
        assert!(
            !target.join("lmdb").join("data.mdb").exists(),
            "a failed verification must not write the target"
        );
    }

    /// Q07 residual: tombstone / backup-expiry semantics.
    ///
    /// Whitemagic has no tombstone propagation: a backup is a **point-in-time**
    /// snapshot. Restoring a pre-deletion snapshot legitimately resurrects the
    /// deleted record; a snapshot taken after the deletion does not contain it.
    /// This test pins that documented semantics (and `run_restore`'s clean
    /// refusal on a missing/expired snapshot dir) instead of leaving the
    /// behavior untested.
    #[test]
    fn backup_restore_has_point_in_time_tombstone_semantics() {
        let tmp = tempfile::tempdir().unwrap();
        let source = tmp.path().join("source");
        let store = MemoryStore::open_default(source.join("lmdb")).unwrap();
        let mut record = Memory::new(
            wm_core::Galaxy::Codex,
            "pre-deletion acknowledged record".into(),
        );
        record.metadata.id = uuid::Uuid::from_u128(0x9A1);
        store.put(wm_core::Galaxy::Codex, &record).unwrap();
        drop(store);

        let pre_deletion = backup_fixture(&source, &tmp.path().join("backups-pre"));

        // Delete after the snapshot; the live store no longer has it.
        let store = MemoryStore::open_default(source.join("lmdb")).unwrap();
        assert!(
            store
                .delete(wm_core::Galaxy::Codex, record.metadata.id)
                .unwrap()
        );
        assert!(
            store
                .get(wm_core::Galaxy::Codex, record.metadata.id)
                .unwrap()
                .is_none(),
            "record must be gone from the live store"
        );
        drop(store);

        let post_deletion = backup_fixture(&source, &tmp.path().join("backups-post"));

        // Point-in-time restore of the pre-deletion snapshot resurrects it.
        let target_pre = tmp.path().join("restored-pre");
        run_restore(&pre_deletion, &target_pre, true).unwrap();
        let restored = MemoryStore::open_default(target_pre.join("lmdb")).unwrap();
        assert!(
            restored
                .get(wm_core::Galaxy::Codex, record.metadata.id)
                .unwrap()
                .is_some(),
            "pre-deletion snapshot restore is point-in-time (no tombstone propagation) — documented semantics"
        );

        // The post-deletion snapshot reflects the deletion.
        let target_post = tmp.path().join("restored-post");
        run_restore(&post_deletion, &target_post, true).unwrap();
        let restored = MemoryStore::open_default(target_post.join("lmdb")).unwrap();
        assert!(
            restored
                .get(wm_core::Galaxy::Codex, record.metadata.id)
                .unwrap()
                .is_none(),
            "post-deletion snapshot must not contain the deleted record"
        );

        // An expired/pruned snapshot path refuses cleanly (backup-expiry).
        let missing = tmp.path().join("pruned-by-retention");
        assert!(
            run_restore(&missing, &tmp.path().join("restored-missing"), true).is_err(),
            "restore of a pruned/expired snapshot must refuse cleanly"
        );
    }

    #[test]
    fn forced_schema_failure_preserves_previous_target() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("target");
        let store = MemoryStore::open_default(target.join("lmdb")).unwrap();
        let mut original = Memory::new(
            wm_core::Galaxy::Codex,
            "previous acknowledged original".into(),
        );
        original.metadata.id = uuid::Uuid::from_u128(0x901);
        store.put(wm_core::Galaxy::Codex, &original).unwrap();
        drop(store);
        let before = std::fs::read(target.join("lmdb/data.mdb")).unwrap();
        let backup = tmp.path().join("invalid-backup");
        std::fs::create_dir_all(backup.join("data/lmdb")).unwrap();
        let bytes = b"not an LMDB environment";
        std::fs::write(backup.join("data/lmdb/data.mdb"), bytes).unwrap();
        use sha2::Digest;
        std::fs::write(
            backup.join("SHA256SUMS"),
            format!(
                "{}  data/lmdb/data.mdb\n",
                hex(&sha2::Sha256::digest(bytes))
            ),
        )
        .unwrap();
        assert!(run_restore(&backup, &target, true).is_err());
        assert!(
            std::fs::read(target.join("lmdb/data.mdb")).unwrap() == before,
            "previous acknowledged LMDB changed after rejected restore"
        );
        let reopened = MemoryStore::open_default(target.join("lmdb")).unwrap();
        assert_eq!(
            reopened
                .get(wm_core::Galaxy::Codex, original.metadata.id)
                .unwrap()
                .unwrap()
                .content,
            original.content
        );
        assert!(!std::fs::read_dir(tmp.path()).unwrap().any(|e| {
            e.unwrap()
                .file_name()
                .to_string_lossy()
                .starts_with(".wm-restore-")
        }));
    }

    #[test]
    fn failed_promotion_rolls_back_previous_tree() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("target");
        let candidate = tmp.path().join("candidate");
        std::fs::create_dir(&target).unwrap();
        std::fs::create_dir(&candidate).unwrap();
        std::fs::write(target.join("original"), "acknowledged").unwrap();
        std::fs::write(candidate.join("new"), "replacement").unwrap();
        let error = promote_restore_candidate_with(&candidate, &target, |_, _| {
            Err(std::io::Error::other("synthetic promotion refusal"))
        })
        .unwrap_err();
        assert!(
            error
                .to_string()
                .contains("previous target restored unchanged")
        );
        assert_eq!(
            std::fs::read_to_string(target.join("original")).unwrap(),
            "acknowledged"
        );
        assert!(!target.join("new").exists());
        assert!(candidate.join("new").exists());
    }

    #[test]
    fn failed_rollback_retains_previous_tree_and_reports_location() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("target");
        let candidate = tmp.path().join("candidate");
        std::fs::create_dir(&target).unwrap();
        std::fs::create_dir(&candidate).unwrap();
        std::fs::write(target.join("original"), "acknowledged").unwrap();
        let error = promote_restore_candidate_with(&candidate, &target, |_, to| {
            std::fs::create_dir(to)?;
            std::fs::write(to.join("synthetic-conflict"), "block rollback")?;
            Err(std::io::Error::other("synthetic promotion refusal"))
        })
        .unwrap_err();
        assert!(error.to_string().contains("rollback failed"));
        assert!(!error.to_string().contains("restored unchanged"));
        let retained = std::fs::read_dir(tmp.path())
            .unwrap()
            .map(|e| e.unwrap().path())
            .find(|p| {
                p.file_name()
                    .unwrap()
                    .to_string_lossy()
                    .starts_with(".wm-restore-rollback-")
            })
            .unwrap();
        assert!(error.to_string().contains(&retained.display().to_string()));
        assert_eq!(
            std::fs::read_to_string(retained.join("previous/original")).unwrap(),
            "acknowledged"
        );
    }

    #[tokio::test]
    async fn restore_compares_authoritative_records_revisions_associations_and_session_partition() {
        let tmp = tempfile::tempdir().unwrap();
        let source = tmp.path().join("source");
        let target = tmp.path().join("target");
        let store = std::sync::Arc::new(MemoryStore::open_default(source.join("lmdb")).unwrap());
        let mut original = Memory::new(
            wm_core::Galaxy::Codex,
            "orchidquasar original\n完整 🪷".into(),
        );
        original.metadata.id = uuid::Uuid::from_u128(0x902);
        let mut private = Memory::new(wm_core::Galaxy::Codex, "private lotus source".into())
            .with_privacy(true, true);
        private.metadata.id = uuid::Uuid::from_u128(0x903);
        store.put(wm_core::Galaxy::Codex, &original).unwrap();
        store.put(wm_core::Galaxy::Codex, &private).unwrap();
        let old = Memory::new(wm_core::Galaxy::Codex, "orchidquasar initial".into());
        let intermediate = Memory::new(wm_core::Galaxy::Codex, "orchidquasar corrected".into());
        for (old, new) in [
            (
                &old.metadata.content_hash,
                &intermediate.metadata.content_hash,
            ),
            (
                &intermediate.metadata.content_hash,
                &original.metadata.content_hash,
            ),
        ] {
            store
                .record_revision(
                    wm_core::Galaxy::Codex,
                    original.metadata.id,
                    old,
                    new,
                    wm_memory::revision::RevisionActor::default(),
                )
                .unwrap();
        }
        let revisions = store
            .revisions(wm_core::Galaxy::Codex, original.metadata.id)
            .unwrap();
        assert!(
            wm_memory::revision::verify_chain(&revisions, &original.metadata.content_hash).valid
        );
        let assoc = wm_memory::Association::new(
            original.metadata.id,
            private.metadata.id,
            wm_memory::LinkType::Related,
            0.75,
        );
        wm_memory::AssociationStore::open(store.env())
            .unwrap()
            .put(store.env(), &assoc)
            .unwrap();
        use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
        let sessions = [uuid::Uuid::from_u128(0x910), uuid::Uuid::from_u128(0x911)];
        let mut records = Vec::new();
        for (i, session) in sessions.into_iter().enumerate() {
            let mut record = EpisodicRecord::new(
                Some(session),
                1,
                EpisodicKind::UserStatement,
                format!("session {i} byte exact 🪷"),
                Provenance::new(ProvenanceSource::User),
            );
            record.id = uuid::Uuid::from_u128(0x920 + i as u128);
            store.episodic().append(&record).unwrap();
            records.push(record);
        }
        use wm_core::Tool;
        use wm_tools::expansion::session_ops::{SessionRecordTool, SessionReplayTool};
        let recorder = SessionRecordTool::new(store.clone());
        let replay = SessionReplayTool::new(store.clone());
        let mut expected_replays = Vec::new();
        for session in sessions {
            let mut start = Memory::new(wm_core::Galaxy::Sessions, serde_json::json!({"type": "session_start", "title": "synthetic restore session", "user": "fixture"}).to_string());
            start.metadata.id = session;
            start.metadata.tags = vec!["session".into(), "start".into()];
            store.put(wm_core::Galaxy::Sessions, &start).unwrap();
            recorder.call(&mut wm_core::Context::default(), serde_json::json!({"session_id": session.to_string(), "content": format!("original replay turn {session} 🪷"), "role": "user"})).await.unwrap();
            expected_replays.push(
                replay
                    .call(
                        &mut wm_core::Context::default(),
                        serde_json::json!({"session_id": session.to_string(), "mode": "lossless"}),
                    )
                    .await
                    .unwrap(),
            );
        }
        drop(recorder);
        drop(replay);
        drop(store);
        let backup_started = std::time::Instant::now();
        let backup = backup_fixture(&source, &tmp.path().join("backups"));
        println!(
            "BATCH1_MEASURE backup_ms={:.3}",
            backup_started.elapsed().as_secs_f64() * 1000.0
        );
        std::fs::create_dir(&target).unwrap();
        std::fs::write(target.join("old-target"), "replace me").unwrap();
        let restore_started = std::time::Instant::now();
        run_restore(&backup, &target, true).unwrap();
        println!(
            "BATCH1_MEASURE restore_ms={:.3}",
            restore_started.elapsed().as_secs_f64() * 1000.0
        );
        assert!(!target.join("old-target").exists());
        let restored = std::sync::Arc::new(MemoryStore::open_default(target.join("lmdb")).unwrap());
        for memory in [&original, &private] {
            assert_eq!(
                serde_json::to_value(
                    restored
                        .get(wm_core::Galaxy::Codex, memory.metadata.id)
                        .unwrap()
                        .unwrap()
                )
                .unwrap(),
                serde_json::to_value(memory).unwrap()
            );
        }
        assert_eq!(
            restored
                .revisions(wm_core::Galaxy::Codex, original.metadata.id)
                .unwrap(),
            revisions
        );
        let restored_assoc = wm_memory::AssociationStore::open(restored.env())
            .unwrap()
            .get(restored.env(), original.metadata.id, private.metadata.id)
            .unwrap()
            .unwrap();
        assert_eq!(
            serde_json::to_value(restored_assoc).unwrap(),
            serde_json::to_value(assoc).unwrap()
        );
        for record in records {
            let partition = restored.episodic().scan(record.session_id, 10).unwrap();
            assert!(partition.iter().any(|item| item.id == record.id));
            assert_eq!(
                serde_json::to_value(partition.iter().find(|item| item.id == record.id).unwrap())
                    .unwrap(),
                serde_json::to_value(record).unwrap()
            );
        }
        let replay = SessionReplayTool::new(restored.clone());
        for (session, expected) in sessions.into_iter().zip(expected_replays) {
            assert_eq!(
                replay
                    .call(
                        &mut wm_core::Context::default(),
                        serde_json::json!({"session_id": session.to_string(), "mode": "lossless"})
                    )
                    .await
                    .unwrap(),
                expected
            );
        }
        let index_started = std::time::Instant::now();
        std::fs::create_dir_all(target.join("lmdb/tantivy")).unwrap();
        let search = wm_memory::SearchEngine::open(target.join("lmdb/tantivy")).unwrap();
        wm_memory::rebuild_index(&restored, &search, &[]).unwrap();
        assert!(
            search
                .search("orchidquasar", 10)
                .unwrap()
                .iter()
                .any(|r| r.memory_id == original.metadata.id.to_string())
        );
        println!(
            "BATCH1_MEASURE index_and_search_ms={:.3}",
            index_started.elapsed().as_secs_f64() * 1000.0
        );
    }
}

#[cfg(test)]
mod readonly_startup_tests {
    use super::*;
    use std::sync::atomic::Ordering;

    #[test]
    fn readonly_serve_missing_store_fails_without_creation_or_recovery() {
        let tmp = tempfile::tempdir().unwrap();
        let missing = tmp.path().join("missing-lmdb");
        WRITABLE_RECOVERY_CALLS.store(0, Ordering::SeqCst);

        let error = match open_server_for_serve(&missing, true, false) {
            Ok(_) => panic!("readonly startup unexpectedly opened a missing store"),
            Err(error) => error,
        };

        assert!(
            error.to_string().contains("does not exist"),
            "unexpected error: {error:#}"
        );
        assert!(!missing.exists(), "readonly startup created {missing:?}");
        assert_eq!(
            WRITABLE_RECOVERY_CALLS.load(Ordering::SeqCst),
            0,
            "readonly open failure must not enter writable recovery"
        );
    }

    #[test]
    fn readonly_serve_missing_index_fails_without_creation_or_recovery() {
        let tmp = tempfile::tempdir().unwrap();
        let lmdb = tmp.path().join("lmdb");
        drop(wm_memory::MemoryStore::open_default(&lmdb).unwrap());
        let missing_index = lmdb.join("tantivy");
        assert!(!missing_index.exists());
        WRITABLE_RECOVERY_CALLS.store(0, Ordering::SeqCst);

        let error = match open_server_for_serve(&lmdb, true, false) {
            Ok(_) => panic!("readonly startup unexpectedly created a missing index"),
            Err(error) => error,
        };

        assert!(
            error
                .to_string()
                .contains("Tantivy index directory does not exist"),
            "unexpected error: {error:#}"
        );
        assert!(
            !missing_index.exists(),
            "readonly startup created missing index directory {missing_index:?}"
        );
        assert_eq!(WRITABLE_RECOVERY_CALLS.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn readonly_serve_preserves_authoritative_files() {
        let tmp = tempfile::tempdir().unwrap();
        let lmdb = tmp.path().join("lmdb");
        drop(open_server_for_serve(&lmdb, false, false).unwrap());

        let primary = lmdb.join("data.mdb");
        let metadata = lmdb.join("tantivy/meta.json");
        let primary_before = std::fs::read(&primary).unwrap();
        let metadata_before = std::fs::read(&metadata).unwrap();

        drop(open_server_for_serve(&lmdb, true, false).unwrap());

        assert_eq!(std::fs::read(&primary).unwrap(), primary_before);
        assert_eq!(std::fs::read(&metadata).unwrap(), metadata_before);
    }

    #[test]
    fn doctor_readonly_inspection_preserves_store_and_index() {
        let tmp = tempfile::tempdir().unwrap();
        let store = tmp.path().join("store");
        let lmdb = store.join("lmdb");
        drop(open_server_for_serve(&lmdb, false, false).unwrap());

        fn snapshot(
            dir: &std::path::Path,
            base: &std::path::Path,
        ) -> Vec<(String, Option<Vec<u8>>)> {
            let mut out = Vec::new();
            for entry in std::fs::read_dir(dir).unwrap() {
                let path = entry.unwrap().path();
                if path.is_dir() {
                    out.extend(snapshot(&path, base));
                } else {
                    let rel = path.strip_prefix(base).unwrap().display().to_string();
                    let bytes = if rel.ends_with("lock.mdb") {
                        None
                    } else {
                        Some(std::fs::read(&path).unwrap())
                    };
                    out.push((rel, bytes));
                }
            }
            out.sort();
            out
        }

        let before = snapshot(&store, &store);
        let result = run_doctor(Some(store.clone()), false, false, false, false).unwrap();
        let after = snapshot(&store, &store);

        assert_eq!(
            after, before,
            "readonly doctor inspection mutated the store or index"
        );
        assert_eq!(
            result, 0,
            "doctor graded a clean readonly store as unhealthy"
        );
    }

    #[test]
    fn yama_feed_summary_reports_records_and_age() {
        let tmp = tempfile::tempdir().unwrap();
        let feed = tmp.path().join("sent.jsonl");
        assert!(yama_feed_summary(&feed).is_none());
        std::fs::write(&feed, "{\"a\":1}\n\n{\"b\":2}\n").unwrap();
        let (records, age) = yama_feed_summary(&feed).unwrap();
        assert_eq!(records, 2);
        assert!(age < 60, "fresh feed should report an age under a minute");
    }

    #[test]
    fn writable_serve_still_creates_a_new_store() {
        let tmp = tempfile::tempdir().unwrap();
        let lmdb = tmp.path().join("lmdb");

        drop(open_server_for_serve(&lmdb, false, false).unwrap());

        assert!(lmdb.join("data.mdb").is_file());
        assert!(lmdb.join("tantivy/meta.json").is_file());
    }
}

#[cfg(test)]
mod offline_update_tests {
    use super::*;

    #[test]
    fn fetch_failures_are_classified_as_offline() {
        let fetch = anyhow::anyhow!("manifest fetch failed: connection refused");
        assert!(is_fetch_failure(&fetch));
        let sig =
            anyhow::anyhow!("release manifest signature is INVALID — do not use this release");
        assert!(!is_fetch_failure(&sig));
    }

    #[test]
    fn offline_message_is_calm_and_keeps_the_install() {
        let msg = offline_update_message("9.1.4");
        assert!(msg.contains("network unavailable"));
        assert!(msg.contains("WhiteMagic 9.1.4 remains unchanged"));
        assert!(!msg.to_lowercase().contains("backtrace"));
        assert!(!msg.contains("Error:"));
    }
}

#[cfg(test)]
mod session_cli_tests {
    use super::*;
    use wm_core::Galaxy;

    fn fresh_store_root(tmp: &std::path::Path) -> std::path::PathBuf {
        tmp.join("fresh-store")
    }

    /// Reviewer finding (2026-09-17): the CLI refused `--store <fresh>` with
    /// an LMDB-not-found error even though the flag was explicitly passed and
    /// the MCP path initializes stores implicitly. Session writes auto-init.
    #[test]
    fn session_cli_initializes_explicit_fresh_store() {
        let tmp = tempfile::tempdir().unwrap();
        let root = fresh_store_root(tmp.path());
        run_session_command(SessionCommands::Start {
            title: "first run".into(),
            user: "tester".into(),
            store: Some(root.clone()),
        })
        .unwrap();

        let lmdb = root.join("lmdb");
        assert!(lmdb.exists(), "session start must initialize the store");
        let store = wm_memory::MemoryStore::open_default(&lmdb).unwrap();
        let starts = store
            .scan_all(Galaxy::Sessions)
            .unwrap()
            .iter()
            .filter(|m| m.metadata.tags.contains(&"start".to_string()))
            .count();
        assert_eq!(starts, 1, "the session marker must be stored");
    }

    /// Reads stay side-effect-free: continuity on an uninitialized store
    /// answers truthfully and creates nothing.
    #[test]
    fn session_cli_continuity_on_missing_store_creates_nothing() {
        let tmp = tempfile::tempdir().unwrap();
        let root = fresh_store_root(tmp.path());
        run_session_command(SessionCommands::Continuity {
            n: 10,
            session_id: None,
            since: None,
            until: None,
            store: Some(root.clone()),
        })
        .unwrap();
        assert!(
            !root.exists(),
            "continuity on a missing store must not create one: {root:?}"
        );
    }

    /// Reviewer finding (2026-09-17): CLI session writes skipped write-time
    /// indexing, so `wm status` reported index drift right after a supported
    /// workflow. The CLI now attaches the search engine like the server does.
    #[test]
    fn session_cli_writes_are_indexed_at_write_time() {
        let tmp = tempfile::tempdir().unwrap();
        let root = fresh_store_root(tmp.path());
        run_session_command(SessionCommands::Start {
            title: "index parity".into(),
            user: "tester".into(),
            store: Some(root.clone()),
        })
        .unwrap();
        run_session_command(SessionCommands::Record {
            content: "amber lighthouse protocol engaged".into(),
            role: "ai".into(),
            turn_type: "decision".into(),
            importance: 0.7,
            session_id: None,
            supersedes: None,
            store: Some(root.clone()),
        })
        .unwrap();

        let tantivy = wm_memory::reindex::tantivy_path_for(&root.join("lmdb"));
        let search = wm_memory::SearchEngine::open_readonly(&tantivy).unwrap();
        let docs = search.count_docs_in_galaxy("sessions").unwrap();
        assert!(
            docs >= 1,
            "CLI session write must be indexed immediately (docs={docs})"
        );
    }
}

#[cfg(test)]
mod at_rest_cli_tests {
    use super::*;
    use wm_memory::{AtRestConfig, MemoryStore};

    const TEST_MAP: usize = 16 * 1024 * 1024;

    fn fresh_root(tmp: &std::path::Path) -> std::path::PathBuf {
        tmp.join("store")
    }

    fn plant_plaintext(root: &std::path::Path, count: usize) -> Vec<uuid::Uuid> {
        let lmdb = root.join("lmdb");
        let store = MemoryStore::open_with_at_rest(&lmdb, TEST_MAP, &AtRestConfig::off()).unwrap();
        let mut ids = Vec::new();
        for i in 0..count {
            let mem = wm_memory::Memory::new(wm_core::Galaxy::Codex, format!("legacy {i}"));
            ids.push(mem.metadata.id);
            store.put(wm_core::Galaxy::Codex, &mem).unwrap();
        }
        ids
    }

    fn sealed_count(root: &std::path::Path, hex_key: &str) -> usize {
        let lmdb = root.join("lmdb");
        let store = MemoryStore::open_with_at_rest(
            &lmdb,
            TEST_MAP,
            &AtRestConfig::keyfile_with_root_key(hex_key.to_string()),
        )
        .unwrap();
        store
            .scan_all(wm_core::Galaxy::Codex)
            .unwrap()
            .into_iter()
            .filter(|m| {
                store
                    .get_raw(wm_core::Galaxy::Codex, m.metadata.id.as_bytes())
                    .unwrap()
                    .is_some_and(|raw| raw.starts_with(b"WMEN"))
            })
            .count()
    }

    #[test]
    fn migrate_seals_plaintext_records_and_status_reports_the_ledger() {
        let tmp = tempfile::tempdir().unwrap();
        let root = fresh_root(tmp.path());
        let ids = plant_plaintext(&root, 6);
        let hex_key = "cc".repeat(32);

        run_at_rest_migrate_with_config(
            &root,
            &[],
            4,
            false,
            0,
            &AtRestConfig::keyfile_with_root_key(hex_key.clone()),
        )
        .unwrap();

        assert_eq!(
            sealed_count(&root, &hex_key),
            6,
            "all records must be sealed"
        );
        drop(ids);

        // Status is read-only and reports the completed ledger.
        run_at_rest_status(&root, true).unwrap();
    }

    #[test]
    fn migrate_refuses_a_plaintext_store_without_a_keyring_as_a_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let root = fresh_root(tmp.path());
        plant_plaintext(&root, 2);

        run_at_rest_migrate_with_config(&root, &[], 0, false, 0, &AtRestConfig::off()).unwrap();
        // Nothing sealed, nothing created.
        let lmdb = root.join("lmdb");
        let store = MemoryStore::open_inspection(&lmdb).unwrap();
        assert_eq!(store.at_rest_status(), wm_memory::AtRestStatus::Absent);
    }

    #[test]
    fn migrate_dry_run_writes_nothing() {
        let tmp = tempfile::tempdir().unwrap();
        let root = fresh_root(tmp.path());
        let ids = plant_plaintext(&root, 3);
        let lmdb = root.join("lmdb");
        // Keyring store: initialize first with a writable keyfile open.
        drop(MemoryStore::open_with_at_rest(&lmdb, TEST_MAP, &AtRestConfig::keyfile()).unwrap());
        let before = std::fs::metadata(lmdb.join("data.mdb")).unwrap().len();

        run_at_rest_migrate_with_config(&root, &[], 0, true, 0, &AtRestConfig::keyfile()).unwrap();

        // Records remain plaintext and no ledger exists.
        let store = MemoryStore::open_inspection(&lmdb).unwrap();
        assert!(
            wm_memory::migration_ledger(&store)
                .unwrap()
                .unwrap()
                .galaxies
                .is_empty()
        );
        let raw = store
            .get_raw(wm_core::Galaxy::Codex, ids[0].as_bytes())
            .unwrap()
            .unwrap();
        assert!(!raw.starts_with(b"WMEN"), "dry run must not seal records");
        let after = std::fs::metadata(lmdb.join("data.mdb")).unwrap().len();
        assert_eq!(after, before, "dry run must not write the store");
    }

    #[test]
    fn galaxy_filter_rejects_non_record_galaxies() {
        let error = at_rest_galaxies(&["karma".to_string()]).unwrap_err();
        assert!(error.to_string().contains("not a record galaxy"), "{error}");
        assert_eq!(
            at_rest_galaxies(&["codex".to_string()]).unwrap(),
            vec![wm_core::Galaxy::Codex]
        );
        assert_eq!(
            at_rest_galaxies(&[]).unwrap().len(),
            wm_memory::RECORD_GALAXIES.len()
        );
    }
}

#[cfg(test)]
mod help_surface_tests {
    use super::*;
    use clap::CommandFactory;

    /// Reviewer finding (2026-09-17): `wm --help` presented the Gen1/lab
    /// machinery (geneseed, daemon, brain waves, anchoring, trust, …) with
    /// the same weight as the product loop. The lab is hidden from the
    /// default listing but stays fully runnable and listed by `wm help --all`.
    #[test]
    fn lab_commands_are_hidden_from_help_but_still_runnable() {
        let cmd = Cli::command();
        for name in [
            "geneseed",
            "polyglot",
            "export-training-data",
            "daemon",
            "brain-wave",
            "migrate",
            "opencode",
            "seal",
            "verify",
            "anchor",
            "repair-content",
            "redact-content",
            "trust",
        ] {
            let sub = cmd
                .find_subcommand(name)
                .unwrap_or_else(|| panic!("{name} must stay runnable"));
            assert!(
                sub.is_hide_set(),
                "{name} must be hidden from the default help"
            );
        }
        for name in [
            "serve",
            "grimoire",
            "connect",
            "session",
            "ingest",
            "backup",
            "restore",
            "status",
            "quickstart",
            "selftest",
            "doctor",
            "update",
            "setup",
            "report",
            "reindex",
        ] {
            let sub = cmd
                .find_subcommand(name)
                .unwrap_or_else(|| panic!("{name} must stay visible"));
            assert!(
                !sub.is_hide_set(),
                "{name} is product surface and must not be hidden"
            );
        }
    }

    #[test]
    fn help_all_lists_every_hidden_command_with_an_about() {
        let lab = lab_commands();
        assert!(
            lab.iter().any(|(name, _)| name == "geneseed"),
            "the lab list must include geneseed"
        );
        assert!(
            lab.iter().any(|(name, _)| name == "trust"),
            "the lab list must include trust"
        );
        assert!(
            lab.iter().all(|(_, about)| !about.is_empty()),
            "every hidden command needs a one-line about for 'wm help --all'"
        );
        assert!(
            lab.len() >= 13,
            "the hidden lab surface shrank unexpectedly: {lab:?}"
        );
    }
}

#[cfg(test)]
mod at_rest_doctor_tests {
    use super::*;
    use wm_memory::{Argon2Params, AtRestMode, AtRestStatus, AtRestStatusPresent, KeyringMeta};

    fn present_with(
        mode: AtRestMode,
        argon2: Option<Argon2Params>,
        key_source: &str,
        key_file: Option<&str>,
        wrapped_deks: usize,
    ) -> AtRestStatus {
        AtRestStatus::Present(AtRestStatusPresent {
            meta: KeyringMeta {
                format_version: wm_memory::KEYRING_FORMAT_VERSION,
                mode,
                key_source: key_source.to_string(),
                created_at: "2026-09-18T00:00:00Z".to_string(),
                argon2,
            },
            wrapped_deks,
            galaxies: 16,
            key_file: key_file.map(std::path::PathBuf::from),
        })
    }

    fn present(mode: AtRestMode, argon2: Option<Argon2Params>) -> AtRestStatus {
        present_with(
            mode,
            argon2,
            "generated_key_file",
            Some("/store/.at_rest_key"),
            16,
        )
    }

    #[test]
    fn formatter_off_is_honest_plaintext() {
        let disclosure =
            format_at_rest_disclosure(&AtRestStatus::Absent, Path::new("/store"), None, None);
        assert!(disclosure.text.starts_with("[INFO]"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("plaintext pass-through"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("NOT encrypted"),
            "{}",
            disclosure.text
        );
        assert!(!disclosure.issue);
    }

    #[test]
    fn formatter_keyfile_discloses_mode_b_and_no_crypto_erasure() {
        let disclosure = format_at_rest_disclosure(
            &present(AtRestMode::Keyfile, None),
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[OK]"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("mode B (keyfile)"),
            "{}",
            disclosure.text
        );
        assert!(disclosure.text.contains("16/16"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("RK source: generated_key_file"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("never crypto-erasure on mode B"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("Physical-purge only"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("Q39 slice B"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("/store/.at_rest_key"),
            "{}",
            disclosure.text
        );
        assert!(
            !disclosure.text.contains("/store/lmdb/.at_rest_key"),
            "generated key file is disclosed at the store root, not inside lmdb: {}",
            disclosure.text
        );
        assert!(!disclosure.issue);
    }

    #[test]
    fn formatter_passphrase_discloses_argon2_and_not_advertised() {
        let argon = Argon2Params {
            m_cost_kib: 19_456,
            t_cost: 2,
            p_cost: 1,
            version: 0x13,
            salt_hex: "00".repeat(16),
        };
        let disclosure = format_at_rest_disclosure(
            &present_with(
                AtRestMode::Passphrase,
                Some(argon),
                "argon2id_passphrase",
                None,
                16,
            ),
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[OK]"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("mode C (passphrase)"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("argon2id m=19456"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("RK source: argon2id_passphrase"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("not yet advertised"),
            "{}",
            disclosure.text
        );
        assert!(!disclosure.issue);
    }

    #[test]
    fn formatter_env_root_key_source_is_disclosed() {
        let disclosure = format_at_rest_disclosure(
            &present_with(AtRestMode::Keyfile, None, "env_root_key", None, 16),
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[OK]"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("RK source: env_root_key"),
            "{}",
            disclosure.text
        );
        assert!(
            !disclosure.text.contains("external key source"),
            "the key source must be named, not hidden: {}",
            disclosure.text
        );
        assert!(!disclosure.issue);
    }

    #[test]
    fn formatter_configured_key_file_source_discloses_path() {
        let disclosure = format_at_rest_disclosure(
            &present_with(
                AtRestMode::Keyfile,
                None,
                "key_file",
                Some("/etc/whitemagic/at_rest.key"),
                16,
            ),
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[OK]"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("RK source: key_file"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("/etc/whitemagic/at_rest.key"),
            "{}",
            disclosure.text
        );
        let without_path = format_at_rest_disclosure(
            &present_with(AtRestMode::Keyfile, None, "key_file", None, 16),
            Path::new("/store"),
            None,
            None,
        );
        assert!(
            without_path
                .text
                .contains("configured with WM_AT_REST_KEY_FILE")
                && without_path.text.contains("path not recorded"),
            "{}",
            without_path.text
        );
        assert!(!disclosure.issue);
    }

    #[test]
    fn formatter_partial_dek_coverage_warns_and_is_an_issue() {
        let disclosure = format_at_rest_disclosure(
            &present_with(
                AtRestMode::Keyfile,
                None,
                "generated_key_file",
                Some("/store/.at_rest_key"),
                12,
            ),
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[WARN]"), "{}", disclosure.text);
        assert!(disclosure.text.contains("12/16"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("PARTIAL keyring"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("writable opens refuse"),
            "{}",
            disclosure.text
        );
        assert!(disclosure.issue);

        let passphrase_partial = format_at_rest_disclosure(
            &present_with(
                AtRestMode::Passphrase,
                Some(Argon2Params {
                    m_cost_kib: 19_456,
                    t_cost: 2,
                    p_cost: 1,
                    version: 0x13,
                    salt_hex: "00".repeat(16),
                }),
                "argon2id_passphrase",
                None,
                3,
            ),
            Path::new("/store"),
            None,
            None,
        );
        assert!(
            passphrase_partial.text.starts_with("[WARN]"),
            "{}",
            passphrase_partial.text
        );
        assert!(passphrase_partial.issue);
    }

    #[test]
    fn formatter_present_mode_off_warns_and_is_an_issue() {
        let disclosure = format_at_rest_disclosure(
            &present_with(AtRestMode::Off, None, "generated_key_file", None, 0),
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[WARN]"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("mode 'off'"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("writable opens refuse"),
            "{}",
            disclosure.text
        );
        assert!(disclosure.issue);
    }

    #[test]
    fn formatter_malformed_warns_and_is_an_issue() {
        let disclosure = format_at_rest_disclosure(
            &AtRestStatus::Malformed {
                reason: "meta row does not parse".to_string(),
            },
            Path::new("/store"),
            None,
            None,
        );
        assert!(disclosure.text.starts_with("[WARN]"), "{}", disclosure.text);
        assert!(disclosure.text.contains("malformed"), "{}", disclosure.text);
        assert!(
            disclosure.text.contains("meta row does not parse"),
            "{}",
            disclosure.text
        );
        assert!(disclosure.issue);
    }

    #[test]
    fn formatter_discloses_record_inventory_and_migration_state() {
        let counts = vec![
            wm_memory::GalaxyAtRestCounts {
                galaxy: "codex".into(),
                sealed: 12,
                plaintext: 3,
                non_record: 0,
            },
            wm_memory::GalaxyAtRestCounts {
                galaxy: "sessions".into(),
                sealed: 5,
                plaintext: 0,
                non_record: 1,
            },
        ];
        let mut ledger = wm_memory::MigrationLedger::default();
        ledger.galaxies.insert(
            "codex".to_string(),
            wm_memory::MigrationGalaxyState {
                encrypted: 12,
                cursor_hex: "aa".into(),
                done: false,
            },
        );
        let disclosure = format_at_rest_disclosure(
            &present(AtRestMode::Keyfile, None),
            Path::new("/store"),
            Some(&counts),
            Some(&ledger),
        );
        assert!(
            disclosure
                .text
                .contains("12 record galaxies): 17 sealed, 3 plaintext"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("Plaintext by galaxy: codex=3"),
            "{}",
            disclosure.text
        );
        assert!(
            disclosure.text.contains("codex: 12 (resume pending)"),
            "{}",
            disclosure.text
        );
        assert!(
            !disclosure
                .text
                .contains("crypto-erasure on mode B is available"),
            "{}",
            disclosure.text
        );
        assert!(!disclosure.issue);

        // A fully-done ledger renders as done, and zero plaintext renders
        // without the per-galaxy breakdown line.
        let done = format_at_rest_disclosure(
            &present(AtRestMode::Passphrase, None),
            Path::new("/store"),
            Some(&[wm_memory::GalaxyAtRestCounts {
                galaxy: "codex".into(),
                sealed: 9,
                plaintext: 0,
                non_record: 0,
            }]),
            Some(&{
                let mut l = wm_memory::MigrationLedger::default();
                l.galaxies.insert(
                    "codex".to_string(),
                    wm_memory::MigrationGalaxyState {
                        encrypted: 9,
                        cursor_hex: String::new(),
                        done: true,
                    },
                );
                l
            }),
        );
        assert!(done.text.contains("codex: 9 done"), "{}", done.text);
        assert!(!done.text.contains("Plaintext by galaxy"), "{}", done.text);
    }

    /// The doctor must read an at-rest store without resolving the RK on the
    /// read path, without mutating the store (including the key file), and
    /// without grading a healthy keyfile store as an issue.
    #[test]
    fn doctor_preserves_an_at_rest_store() {
        let tmp = tempfile::tempdir().unwrap();
        let store = tmp.path().join("store");
        let lmdb = store.join("lmdb");
        // Full schema (galaxies, indexes, Tantivy) first, then initialize the
        // keyring on a writable at-rest open — the doctor opens inspection-only.
        drop(open_server_for_serve(&lmdb, false, false).unwrap());
        drop(
            wm_memory::MemoryStore::open_with_at_rest(
                &lmdb,
                16 * 1024 * 1024,
                &wm_memory::AtRestConfig::keyfile(),
            )
            .unwrap(),
        );

        fn snapshot(
            dir: &std::path::Path,
            base: &std::path::Path,
        ) -> Vec<(String, Option<Vec<u8>>)> {
            let mut out = Vec::new();
            for entry in std::fs::read_dir(dir).unwrap() {
                let path = entry.unwrap().path();
                if path.is_dir() {
                    out.extend(snapshot(&path, base));
                } else {
                    let rel = path.strip_prefix(base).unwrap().display().to_string();
                    let bytes = if rel.ends_with("lock.mdb") {
                        None
                    } else {
                        Some(std::fs::read(&path).unwrap())
                    };
                    out.push((rel, bytes));
                }
            }
            out.sort();
            out
        }

        let before = snapshot(&store, &store);
        let result = run_doctor(Some(store.clone()), false, false, false, false).unwrap();
        let after = snapshot(&store, &store);

        assert_eq!(
            result, 0,
            "a healthy mode-B keyring store must not be graded as an issue"
        );
        assert_eq!(
            after, before,
            "read-only doctor inspection mutated an at-rest store or its key file"
        );
    }
}
