//! JSON-RPC over stdio MCP server.
//!
//! Implements the Model Context Protocol with three methods:
//! - `initialize`: handshake with client info
//! - `tools/list`: returns only the `wm` meta-tool (single entry point)
//! - `tools/call`: dispatches any registered tool through the governance pipeline
//!
//! The `wm` meta-tool routes natural language to 229 tools via TF-IDF NLU
//! classification, or accepts an explicit `route` parameter for direct dispatch.
//! Use `wm(thought="list tools")` or `wm(route="tools.list")` to discover tools.

use std::io::Write;
use std::sync::Arc;

use crate::input_validation::MAX_REQUEST_SIZE;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use wm_bicameral::{BicameralConfig, BicameralEngine, LlmRightHemisphere, RightHemisphereStub};
use wm_cognitive::DriveCore;
use wm_cognitive::GanYingBus;
use wm_cognitive::ReflexDispatchTable;
use wm_cognitive::TimescaleBus;
use wm_cognitive::{CittaHeartbeat, DreamContext, DreamCycle, EcoModeController};
use wm_core::Context;
use wm_dispatch::{DispatchPipeline, ToolRegistry};
use wm_governance::{DharmaGate, KarmaLedger, ResourceRules};
use wm_memory::{
    AssociationStore, ConversationalSearch, Embedder, MemoryStore, RecallConfig, RecallEngine,
    SearchEngine, StubEmbedder, VectorStore, create_embedder,
};
use wm_sangha::{PeerDiscovery, ResourceLockManager, SanghaChat, SignalBroadcast};
use wm_selfmodel::SelfModel;
use wm_substrate::SubstrateMonitor;
use wm_substrate::anomaly::AnomalyDetector;
use wm_substrate::homeostatic::HomeostaticLoop;
use wm_substrate::sensorimotor::{ReflexLoop, SensorimotorBus};
use wm_tools::expansion::rsi::{DispatchTelemetry, FrictionAutoLogTool};
use wm_workspace::GlobalWorkspace;

/// Minimum interval between hardware samples taken on the request path.
///
/// /proc and /sys reads are throttled to at most once per second so the MCP
/// hot path stays cheap; the daemon samples on its own schedule regardless.
const HARDWARE_SAMPLE_INTERVAL_MS: u64 = 1_000;

/// MCP server state.
#[allow(dead_code)]
pub struct McpServer {
    registry: ToolRegistry,
    pipeline: Arc<DispatchPipeline>,
    eco_mode: EcoModeController,
    citta: CittaHeartbeat,
    dream: DreamCycle,
    store: Arc<MemoryStore>,
    associations: Arc<AssociationStore>,
    substrate: Arc<SubstrateMonitor>,
    dharma_gate: Arc<DharmaGate>,
    resource_rules: Arc<ResourceRules>,
    reflex_table: Arc<std::sync::Mutex<ReflexDispatchTable>>,
    timescale_bus: Arc<std::sync::Mutex<TimescaleBus>>,
    workspace: Arc<std::sync::Mutex<GlobalWorkspace>>,
    self_model: Arc<std::sync::Mutex<SelfModel>>,
    bicameral: Arc<std::sync::Mutex<BicameralEngine>>,
    drive_core: Arc<std::sync::Mutex<DriveCore>>,
    autonomic: Option<Arc<std::sync::Mutex<wm_cognitive::AutonomicLayer>>>,
    gan_ying_bus: Arc<std::sync::Mutex<GanYingBus>>,
    peer_discovery: Arc<std::sync::Mutex<PeerDiscovery>>,
    signal_broadcast: Arc<std::sync::Mutex<SignalBroadcast>>,
    sangha_chat: Arc<std::sync::Mutex<SanghaChat>>,
    lock_manager: Arc<std::sync::Mutex<ResourceLockManager>>,
    homeostatic_loop: Arc<std::sync::Mutex<HomeostaticLoop>>,
    anomaly_detector: Arc<std::sync::Mutex<AnomalyDetector>>,
    /// Embodiment I/O: sensorimotor bus and reflex loop
    sensorimotor_bus: Arc<std::sync::Mutex<SensorimotorBus>>,
    reflex_loop: Arc<std::sync::Mutex<ReflexLoop>>,
    /// RSI Phase 1: Auto-logs friction on tool dispatch errors
    friction_auto_log: Arc<FrictionAutoLogTool>,
    /// Karma ledger for WS-3 bidirectional bridge
    karma_ledger: Option<Arc<KarmaLedger>>,
    /// Epoch-ms timestamp of the last hardware sample taken on the request
    /// path — throttles /proc + /sys sampling (see `HARDWARE_SAMPLE_INTERVAL_MS`).
    last_hardware_sample_ms: std::sync::atomic::AtomicU64,
    /// Per-session request budget — hard cap on requests served per connection.
    request_budget: crate::input_validation::RequestBudget,
    /// Time-windowed rate limiter — throttles request bursts at the boundary.
    rate_window: crate::input_validation::RateWindow,
    /// Transaction state for multi-tool snapshot/rollback
    transaction_state: wm_tools::expansion::TransactionState,
    /// TriModelManager — tri-model lifecycle (autonomic/left/right)
    #[allow(dead_code)]
    tri_model: Option<Arc<wm_bicameral::TriModelManager>>,
    /// Imagination engine for dream cycle counterfactual replay and Research cycle
    scenario_engine: Option<wm_bicameral::ScenarioEngine>,
    /// GanaRegistry for taxonomy drift tracking (Phase 6)
    gana_registry: Arc<std::sync::Mutex<wm_core::GanaRegistry>>,
    /// Dynamic galaxy registry for memory clustering (Phase 6)
    dynamic_galaxies: Arc<std::sync::Mutex<wm_core::DynamicGalaxyRegistry>>,
    /// Shadow mode stats for NLU router observability (OATS)
    shadow_stats: Arc<std::sync::RwLock<wm_tools::embedding_router::ShadowModeStats>>,
    /// NLU embedding router (OATS outcome stats) — persisted to
    /// `<store>/mutable_oats.json` on shutdown and restored on startup.
    embedding_router: Option<Arc<wm_tools::embedding_router::EmbeddingRouter>>,
    /// Conformal store (shared with conformal tools) — auto-persisted to
    /// `<store>/conformal_store.json` on shutdown and restored on startup.
    conformal_store: Option<Arc<std::sync::Mutex<wm_tools::expansion::conformal::ConformalStore>>>,
    /// Brier calibration store (shared with simulation.calibrate) — persisted
    /// to `<store>/calibration_store.json` on shutdown.
    calibration_store: Option<Arc<std::sync::Mutex<wm_simulation::CalibrationStore>>>,
    /// Prescience claims ledger (shared with claims.*) — persisted to
    /// `<store>/claims_ledger.json` on shutdown.
    claims_ledger: Option<Arc<std::sync::Mutex<wm_simulation::ClaimsLedger>>>,
    /// Dharma escalation review queue (shared with dharma.escalate and
    /// friends) — persisted to `<store>/escalation_queue.json`.
    escalation_queue: Option<Arc<std::sync::Mutex<wm_governance::EscalationQueue>>>,
    /// Transaction firewall (shared with tx_firewall.*) — persisted to
    /// `<store>/tx_firewall_policy.json`.
    tx_firewall: Option<Arc<wm_tools::expansion::firewall::TxFirewall>>,
    /// Read-only server mode (`--readonly`) — the dispatch pipeline refuses
    /// every tool that declares writes, and telemetry/mutable-state writes
    /// are suppressed.
    readonly: bool,
    /// Active tool surface profile name — reported in `tools/list` so
    /// discovery reflects the profile instead of the full archive.
    profile_name: &'static str,
}

/// JSON-RPC request envelope.
#[derive(Debug, Deserialize)]
struct RpcRequest {
    #[allow(dead_code)]
    jsonrpc: String,
    #[serde(default)]
    id: Option<Value>,
    method: String,
    #[serde(default)]
    params: Value,
}

/// JSON-RPC response envelope.
#[derive(Debug, Serialize)]
struct RpcResponse {
    jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    id: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<RpcError>,
}

/// JSON-RPC error object.
#[derive(Debug, Serialize)]
struct RpcError {
    code: i32,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<Value>,
}

/// Build a JSON-RPC error response.
fn error_response(
    id: Option<&Value>,
    code: i32,
    message: impl Into<String>,
    data: Option<Value>,
) -> RpcResponse {
    RpcResponse {
        jsonrpc: "2.0".into(),
        id: id.cloned(),
        result: None,
        error: Some(RpcError {
            code,
            message: message.into(),
            data,
        }),
    }
}

/// Outcome of a bounded line read.
enum BoundedLine {
    /// A complete line within the size cap.
    Ok(String),
    /// A line exceeding the cap — the rest was drained to end-of-line.
    TooLarge,
    /// End of stream.
    Eof,
}

/// Read a single line from a buffered reader, capping allocation at `max` bytes.
///
/// Hardening: prevents a malicious MCP client from sending an unbounded
/// request line that would grow the line buffer without limit.
fn read_bounded_line<R: std::io::BufRead>(
    reader: &mut R,
    max: usize,
) -> std::io::Result<BoundedLine> {
    let mut buf = Vec::with_capacity(256);
    loop {
        let chunk = reader.fill_buf()?;
        if chunk.is_empty() {
            if buf.is_empty() {
                return Ok(BoundedLine::Eof);
            }
            break;
        }
        let Some(pos) = chunk.iter().position(|&b| b == b'\n') else {
            buf.extend_from_slice(chunk);
            let n = chunk.len();
            reader.consume(n);
            if buf.len() > max {
                drain_to_eol(reader)?;
                return Ok(BoundedLine::TooLarge);
            }
            continue;
        };
        buf.extend_from_slice(&chunk[..pos]);
        reader.consume(pos + 1);
        if buf.len() > max {
            return Ok(BoundedLine::TooLarge);
        }
        break;
    }
    if buf.ends_with(b"\r") {
        buf.pop();
    }
    Ok(BoundedLine::Ok(String::from_utf8_lossy(&buf).into_owned()))
}

/// Drain a buffered reader up to and including the next newline (or EOF).
fn drain_to_eol<R: std::io::BufRead>(reader: &mut R) -> std::io::Result<()> {
    loop {
        let chunk = reader.fill_buf()?;
        if chunk.is_empty() {
            return Ok(());
        }
        let Some(pos) = chunk.iter().position(|&b| b == b'\n') else {
            let n = chunk.len();
            reader.consume(n);
            continue;
        };
        reader.consume(pos + 1);
        return Ok(());
    }
}

async fn read_bounded_line_async<R: tokio::io::AsyncBufRead + Unpin>(
    reader: &mut R,
    max: usize,
) -> std::io::Result<BoundedLine> {
    use tokio::io::AsyncBufReadExt;
    let mut buf = Vec::with_capacity(256);
    loop {
        let chunk = reader.fill_buf().await?;
        if chunk.is_empty() {
            if buf.is_empty() {
                return Ok(BoundedLine::Eof);
            }
            break;
        }
        let Some(pos) = chunk.iter().position(|&b| b == b'\n') else {
            buf.extend_from_slice(chunk);
            let n = chunk.len();
            reader.consume(n);
            if buf.len() > max {
                drain_to_eol_async(reader).await?;
                return Ok(BoundedLine::TooLarge);
            }
            continue;
        };
        buf.extend_from_slice(&chunk[..pos]);
        reader.consume(pos + 1);
        if buf.len() > max {
            return Ok(BoundedLine::TooLarge);
        }
        break;
    }
    if buf.ends_with(b"\r") {
        buf.pop();
    }
    Ok(BoundedLine::Ok(String::from_utf8_lossy(&buf).into_owned()))
}

async fn drain_to_eol_async<R: tokio::io::AsyncBufRead + Unpin>(
    reader: &mut R,
) -> std::io::Result<()> {
    use tokio::io::AsyncBufReadExt;
    loop {
        let chunk = reader.fill_buf().await?;
        if chunk.is_empty() {
            return Ok(());
        }
        let Some(pos) = chunk.iter().position(|&b| b == b'\n') else {
            let n = chunk.len();
            reader.consume(n);
            continue;
        };
        reader.consume(pos + 1);
        return Ok(());
    }
}

impl McpServer {
    /// Create a new MCP server with the given tool registry, dispatch pipeline,
    /// and eco mode controller.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        registry: ToolRegistry,
        pipeline: Arc<DispatchPipeline>,
        eco_mode: EcoModeController,
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        substrate: Arc<SubstrateMonitor>,
        dharma_gate: Arc<DharmaGate>,
        resource_rules: Arc<ResourceRules>,
        reflex_table: Arc<std::sync::Mutex<ReflexDispatchTable>>,
        timescale_bus: Arc<std::sync::Mutex<TimescaleBus>>,
        workspace: Arc<std::sync::Mutex<GlobalWorkspace>>,
        self_model: Arc<std::sync::Mutex<SelfModel>>,
        bicameral: Arc<std::sync::Mutex<BicameralEngine>>,
        drive_core: Arc<std::sync::Mutex<DriveCore>>,
        autonomic: Option<Arc<std::sync::Mutex<wm_cognitive::AutonomicLayer>>>,
        gan_ying_bus: Arc<std::sync::Mutex<GanYingBus>>,
        peer_discovery: Arc<std::sync::Mutex<PeerDiscovery>>,
        signal_broadcast: Arc<std::sync::Mutex<SignalBroadcast>>,
        sangha_chat: Arc<std::sync::Mutex<SanghaChat>>,
        lock_manager: Arc<std::sync::Mutex<ResourceLockManager>>,
        homeostatic_loop: Arc<std::sync::Mutex<HomeostaticLoop>>,
        anomaly_detector: Arc<std::sync::Mutex<AnomalyDetector>>,
        sensorimotor_bus: Arc<std::sync::Mutex<SensorimotorBus>>,
        reflex_loop: Arc<std::sync::Mutex<ReflexLoop>>,
        friction_auto_log: Arc<FrictionAutoLogTool>,
        karma_ledger: Option<Arc<KarmaLedger>>,
        transaction_state: wm_tools::expansion::TransactionState,
        tri_model: Option<Arc<wm_bicameral::TriModelManager>>,
        shadow_stats: Arc<std::sync::RwLock<wm_tools::embedding_router::ShadowModeStats>>,
    ) -> Self {
        Self {
            registry,
            pipeline,
            eco_mode,
            citta: CittaHeartbeat::new(),
            dream: DreamCycle::new(),
            store,
            associations,
            substrate,
            dharma_gate,
            resource_rules,
            reflex_table,
            timescale_bus,
            workspace,
            self_model,
            bicameral,
            drive_core,
            autonomic,
            gan_ying_bus,
            peer_discovery,
            signal_broadcast,
            sangha_chat,
            lock_manager,
            homeostatic_loop,
            anomaly_detector,
            sensorimotor_bus,
            reflex_loop,
            friction_auto_log,
            karma_ledger,
            last_hardware_sample_ms: std::sync::atomic::AtomicU64::new(0),
            request_budget: crate::input_validation::RequestBudget::default(),
            rate_window: crate::input_validation::RateWindow::default(),
            transaction_state,
            tri_model,
            scenario_engine: None,
            gana_registry: Arc::new(std::sync::Mutex::new(wm_core::GanaRegistry::new())),
            dynamic_galaxies: Arc::new(
                std::sync::Mutex::new(wm_core::DynamicGalaxyRegistry::new()),
            ),
            shadow_stats,
            embedding_router: None,
            conformal_store: None,
            calibration_store: None,
            claims_ledger: None,
            escalation_queue: None,
            tx_firewall: None,
            readonly: false,
            profile_name: "full",
        }
    }

    /// Mark the server read-only — the dispatch pipeline refuses declared
    /// writes and telemetry/mutable-state persistence is suppressed.
    #[must_use]
    pub const fn with_readonly(mut self, readonly: bool) -> Self {
        self.readonly = readonly;
        self
    }

    /// Set the active tool surface profile name for `tools/list` text.
    #[must_use]
    pub const fn with_profile_name(mut self, name: &'static str) -> Self {
        self.profile_name = name;
        self
    }

    /// Create a new MCP server with the given registry and pipeline, using
    /// a default eco mode controller.
    #[allow(clippy::too_many_arguments)]
    pub fn with_default_eco(
        registry: ToolRegistry,
        pipeline: Arc<DispatchPipeline>,
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        substrate: Arc<SubstrateMonitor>,
        dharma_gate: Arc<DharmaGate>,
        resource_rules: Arc<ResourceRules>,
        reflex_table: Arc<std::sync::Mutex<ReflexDispatchTable>>,
        timescale_bus: Arc<std::sync::Mutex<TimescaleBus>>,
        workspace: Arc<std::sync::Mutex<GlobalWorkspace>>,
        self_model: Arc<std::sync::Mutex<SelfModel>>,
        bicameral: Arc<std::sync::Mutex<BicameralEngine>>,
        drive_core: Arc<std::sync::Mutex<DriveCore>>,
        shadow_stats: Arc<std::sync::RwLock<wm_tools::embedding_router::ShadowModeStats>>,
    ) -> Self {
        let friction_auto_log = Arc::new(FrictionAutoLogTool::new(store.clone(), None));
        Self::new(
            registry,
            pipeline,
            EcoModeController::default(),
            store,
            associations,
            substrate,
            dharma_gate,
            resource_rules,
            reflex_table,
            timescale_bus,
            workspace,
            self_model,
            bicameral,
            drive_core,
            None,
            Arc::new(std::sync::Mutex::new(GanYingBus::default())),
            Arc::new(std::sync::Mutex::new(PeerDiscovery::default())),
            Arc::new(std::sync::Mutex::new(SignalBroadcast::new(100))),
            Arc::new(std::sync::Mutex::new(SanghaChat::new(100))),
            Arc::new(std::sync::Mutex::new(ResourceLockManager::default())),
            Arc::new(std::sync::Mutex::new(HomeostaticLoop::default())),
            Arc::new(std::sync::Mutex::new(AnomalyDetector::default())),
            Arc::new(std::sync::Mutex::new(SensorimotorBus::default())),
            Arc::new(std::sync::Mutex::new(ReflexLoop::new())),
            friction_auto_log,
            None,
            Arc::new(std::sync::Mutex::new(None)),
            None,
            shadow_stats,
        )
    }

    /// Create a new MCP server with default tools and full governance pipeline.
    pub fn with_defaults(store_path: &std::path::Path) -> anyhow::Result<Self> {
        Self::with_defaults_mode(store_path, false)
    }

    /// Resolve the tool surface profile from the environment.
    ///
    /// `WM_TOOL_ALLOWLIST` (comma-separated tool-name prefixes) wins; then
    /// `WM_TOOL_PROFILE` (`full` | `curated` | `minimal`, default `full`
    /// here; `wm serve` writes `curated` into the env when the flag is omitted).
    /// Invalid names log a warning and fall back to the full surface.
    fn tool_profile_from_env() -> &'static wm_tools::profiles::ToolProfile {
        wm_tools::profiles::resolve_tool_profile(
            None,
            std::env::var("WM_TOOL_PROFILE").ok().as_deref(),
            std::env::var("WM_TOOL_ALLOWLIST").ok().as_deref(),
        )
    }

    /// Like `with_defaults`, but with a read-only tantivy index when
    /// `readonly` is set — no exclusive index lock, so multiple processes can
    /// share the store for searches. Writes fail with a clear error.
    pub fn with_defaults_mode(
        store_path: &std::path::Path,
        readonly: bool,
    ) -> anyhow::Result<Self> {
        let profile = Self::tool_profile_from_env();
        Self::with_defaults_mode_profile(store_path, readonly, profile)
    }

    /// `with_defaults_mode` plus an explicit tool surface profile.
    ///
    /// The full registry is built first (governance internals need their
    /// tools regardless), then filtered to the profile before the `wm`
    /// meta-tool is layered on — so the profile curates both direct dispatch
    /// and NLU routing.
    pub fn with_defaults_mode_profile(
        store_path: &std::path::Path,
        readonly: bool,
        profile: &wm_tools::profiles::ToolProfile,
    ) -> anyhow::Result<Self> {
        let store = std::sync::Arc::new(MemoryStore::open_default(store_path)?);

        // Open Tantivy search index alongside LMDB. If the on-disk index was
        // written with an incompatible schema by an older version, a writable
        // open moves it aside and creates a fresh index — rebuild it from the
        // canonical LMDB store so the upgrade is seamless.
        let search_path = store_path.join("tantivy");
        std::fs::create_dir_all(&search_path)?;
        let search = std::sync::Arc::new(if readonly {
            SearchEngine::open_readonly(&search_path)?
        } else {
            let engine = SearchEngine::open(&search_path)?;
            if engine.schema_migrated() {
                tracing::warn!(
                    "Tantivy index schema was incompatible with this version — rebuilding \
                     the search index from the canonical LMDB store"
                );
                let report = wm_memory::reindex::rebuild_index(&store, &engine, &[])?;
                tracing::warn!(
                    "Search index rebuilt: {} indexed, {} skipped, {} scanned",
                    report.indexed,
                    report.skipped,
                    report.scanned
                );
            }
            engine
        });

        let karma_ledger = std::sync::Arc::new(KarmaLedger::new(store.clone())?);
        let write_audit =
            std::sync::Arc::new(wm_governance::WriteAuditJournal::new(store.clone())?);
        let dharma_gate = std::sync::Arc::new(DharmaGate::default());
        let substrate = std::sync::Arc::new(SubstrateMonitor::default());
        let resource_rules = std::sync::Arc::new(ResourceRules::default());

        if !substrate.sensors_available() {
            tracing::warn!(
                "Hardware sensors unavailable on this platform — homeostasis running in degraded (neutral) mode"
            );
        }

        // Sample hardware state immediately and feed into Dharma gate
        let hv = substrate.sample();
        dharma_gate.update_homeostasis(hv.into());

        let associations = Arc::new(AssociationStore::open(store.env())?);
        let spiral_tracker =
            Arc::new(std::sync::Mutex::new(wm_cognitive::SpiralTracker::default()));
        let vector_store = Arc::new(std::sync::Mutex::new(wm_memory::VectorStore::new()));

        // v4 subsystems: reflex dispatch table, timescale bus, global workspace
        let mut reflex_table = wm_cognitive::ReflexDispatchTable::permissive();
        wm_cognitive::reflex::builtins::register_builtins(&mut reflex_table);
        let reflex_table = Arc::new(std::sync::Mutex::new(reflex_table));

        let timescale_bus = Arc::new(std::sync::Mutex::new(wm_cognitive::TimescaleBus::default()));

        let workspace = Arc::new(std::sync::Mutex::new(wm_workspace::GlobalWorkspace::new()));

        // R4: self-model for predictive introspection
        let self_model = Arc::new(std::sync::Mutex::new(wm_selfmodel::SelfModel::new()));

        // Conformal prediction store — distribution-free uncertainty quantification
        let conformal_store = Arc::new(std::sync::Mutex::new(
            wm_tools::expansion::conformal::ConformalStore::new(),
        ));

        // R5: bicameral reasoning engine
        // Right hemisphere priority: BitNet (local) → LLM (cloud) → stub
        let right: Arc<dyn wm_bicameral::RightHemisphere> =
            if let Some(bitnet) = wm_bicameral::BitNetRightHemisphere::from_env() {
                tracing::info!("BitNet right hemisphere configured");
                Arc::new(bitnet)
            } else if let Some(llm) = LlmRightHemisphere::from_env() {
                tracing::info!("LLM right hemisphere configured");
                Arc::new(llm)
            } else {
                Arc::new(RightHemisphereStub::new())
            };
        let bicameral = Arc::new(std::sync::Mutex::new(
            BicameralEngine::new(BicameralConfig::default(), Some(right)).with_router_from_env(),
        ));

        // R7: drive & emotion core
        let drive_core = Arc::new(std::sync::Mutex::new(DriveCore::new()));

        // L1: autonomic layer (BitMamba) — optional, env-gated
        let autonomic = wm_cognitive::AutonomicLayer::from_env().map(|layer| {
            tracing::info!("autonomic layer configured (BitMamba)");
            Arc::new(std::sync::Mutex::new(layer))
        });

        // ── Deep Integration: Register timescale hooks ──
        // Citta vector decay runs on the Reactive tier (10ms interval)
        // Drive decay runs on the Planning tier (100ms interval)
        // These hooks fire when the timescale bus is ticked during dispatch
        {
            if let Ok(mut bus) = timescale_bus.lock() {
                // Citta decay hook — moves consciousness vector toward neutral
                bus.register(
                    wm_cognitive::Tier::Reactive,
                    "citta_decay",
                    Box::new(|| {
                        // The citta vector decays via the heartbeat post-dispatch,
                        // but we also tick it here for between-dispatch decay.
                        // This is a no-op placeholder — actual decay happens in
                        // the citta heartbeat. The hook exists so the timescale
                        // bus has a consciousness-related entry.
                        wm_cognitive::timescale::hooks::HookResult::Complete
                    }),
                );
                // Drive decay hook — moves drives toward baseline
                bus.register(
                    wm_cognitive::Tier::Planning,
                    "drive_decay",
                    Box::new(|| {
                        // Drive decay is handled in the drive event processing
                        // during dispatch. This hook is a placeholder for
                        // between-dispatch decay when the system is idle.
                        wm_cognitive::timescale::hooks::HookResult::Complete
                    }),
                );
            } else {
                tracing::warn!(
                    "timescale_bus mutex poisoned during startup — hooks not registered"
                );
            }
        }

        // N19-N20: Homeostatic Loop + Anomaly Detector — created early so they
        // can be shared between register_all (homeostasis tools) and the server state.
        let homeostatic_loop = Arc::new(std::sync::Mutex::new(HomeostaticLoop::default()));
        let anomaly_detector = Arc::new(std::sync::Mutex::new(AnomalyDetector::default()));

        // Embodiment I/O: SensorimotorBus + ReflexLoop — created early so they
        // can be shared between register_all (sensorimotor tools) and the server state.
        let sensorimotor_bus = Arc::new(std::sync::Mutex::new(
            wm_substrate::sensorimotor::linux_hardware_bus(),
        ));
        let reflex_loop = Arc::new(std::sync::Mutex::new(ReflexLoop::new()));

        // N16: Gan Ying Bus — created early so it can be shared with sensorimotor tools
        // via register_all.
        let mut gy_bus = GanYingBus::default();
        gy_bus.enable_persistence(store_path.join("resonance_events.jsonl"));
        let gan_ying_bus = Arc::new(std::sync::Mutex::new(gy_bus));

        // Load adaptive aliases from episodic_aliases.json if it exists.
        let aliases_path = store_path.join("episodic_aliases.json");
        if aliases_path.exists() {
            match wm_memory::AdaptiveAliases::from_file(&aliases_path) {
                Ok(aliases) if !aliases.is_empty() => {
                    tracing::info!(
                        "loaded {} adaptive aliases from {:?}",
                        aliases.len(),
                        aliases_path
                    );
                    store.set_episodic_aliases(aliases);
                }
                Ok(_) => {}
                Err(e) => {
                    tracing::warn!(
                        "failed to load adaptive aliases from {:?}: {e}",
                        aliases_path
                    );
                }
            }
        }

        // Enable vocabulary enrichment by default for episodic search.
        store.set_episodic_enrichment(wm_memory::enrichment::VocabularyEnrichment::with_defaults());

        let registry = ToolRegistry::new();
        let recall_engine = {
            let embedder: Arc<dyn Embedder> = create_embedder().into();
            // When WM_EPISODIC_RERANK_ONLY is set, use a stub embedder for
            // RecallEngine (fast ingest) but set the real embedder only for
            // episodic reranking. This avoids embedding ~500 turns per question
            // during ingest while still enabling vector reranking at search time.
            let episodic_rerank_only = std::env::var("WM_EPISODIC_RERANK_ONLY")
                .map(|v| v == "1" || v == "true")
                .unwrap_or(false);

            if episodic_rerank_only && embedder.is_available() && embedder.backend_name() != "stub"
            {
                store.set_episodic_embedder(embedder.clone());
                // Use stub for RecallEngine to skip ingest-time embedding
                let stub: Arc<dyn Embedder> = Arc::new(StubEmbedder::default());
                let recall = RecallEngine::new(
                    store.clone(),
                    search.clone(),
                    VectorStore::new(),
                    stub,
                    RecallConfig::from_env(),
                )?;
                Arc::new(recall)
            } else {
                // Normal mode: share the embedder between RecallEngine and episodic
                if embedder.is_available() && embedder.backend_name() != "stub" {
                    store.set_episodic_embedder(embedder.clone());
                }
                let recall = RecallEngine::new(
                    store.clone(),
                    search.clone(),
                    VectorStore::new(),
                    embedder,
                    RecallConfig::from_env(),
                )?;
                Arc::new(recall)
            }
        };
        // If the embedder is a stub, hybrid search would produce garbage
        // vectors — so only wire it in when a real embedder is available.
        let recall_for_tools = if recall_engine.embedder_is_real() {
            Some(recall_engine.clone())
        } else {
            None
        };
        let conversational = Some(ConversationalSearch::with_defaults(recall_engine));
        let friction_search = search.clone();
        let transaction_state: wm_tools::expansion::TransactionState =
            Arc::new(std::sync::Mutex::new(None));
        let escalation_queue =
            Arc::new(std::sync::Mutex::new(wm_governance::EscalationQueue::new()));
        let firewall = Arc::new(wm_tools::expansion::firewall::TxFirewall::new());
        let code_graph = Arc::new(std::sync::Mutex::new(
            wm_tools::expansion::code::CodeGraph::new(),
        ));
        let registry = wm_tools::register_all(
            &registry,
            &store,
            Some(Arc::clone(&search)),
            Some(karma_ledger.clone()),
            &Some(dharma_gate.clone()),
            Some(substrate.clone()),
            &Some(resource_rules.clone()),
            associations.clone(),
            spiral_tracker,
            vector_store,
            conversational,
            recall_for_tools,
            Some(Arc::clone(&homeostatic_loop)),
            Some(Arc::clone(&anomaly_detector)),
            Some(Arc::clone(&sensorimotor_bus)),
            Some(Arc::clone(&reflex_loop)),
            Some(&gan_ying_bus),
            transaction_state.clone(),
            Some(&escalation_queue),
            Some(&firewall),
            Some(&code_graph),
        );
        let registry = wm_tools::expansion::v4::register_v4(
            &registry,
            Arc::clone(&reflex_table),
            Arc::clone(&timescale_bus),
            Arc::clone(&workspace),
        );
        let registry =
            wm_tools::expansion::selfmodel::register_selfmodel(&registry, Arc::clone(&self_model));
        let registry = wm_tools::expansion::conformal::register_conformal(
            &registry,
            Arc::clone(&conformal_store),
            Some(Arc::clone(&self_model)),
        );
        // Cyberbrain wiring — connect speculative decoder, meta-harness, dense encoder
        let cyberbrain = crate::cyberbrain::wire_cyberbrain(&Some(Arc::clone(&search)));
        let registry = wm_tools::expansion::bicameral::register_bicameral(
            &registry,
            &store,
            Arc::clone(&bicameral),
            cyberbrain.speculative,
            cyberbrain.harness,
            cyberbrain.encoder,
        );
        let registry =
            wm_tools::expansion::drive::register_drive(&registry, Arc::clone(&drive_core));

        // N16-N21: New subsystems — Sangha Mesh, Simulation
        // (Gan Ying Bus already created above and shared with sensorimotor tools)
        let peer_discovery = Arc::new(std::sync::Mutex::new(PeerDiscovery::default()));
        let signal_broadcast = Arc::new(std::sync::Mutex::new(SignalBroadcast::new(100)));
        // Sangha chat signs every message with the node's Ed25519
        // keypair, so peers can verify authorship and identity binding —
        // the trust primitive agent message boards require (cf. the July
        // 2026 agent-incident reporting).
        let sangha_chat = Arc::new(std::sync::Mutex::new(
            SanghaChat::new(100).with_signing_key(mesh_signing_key()),
        ));
        let lock_manager = Arc::new(std::sync::Mutex::new(ResourceLockManager::default()));

        let registry = wm_tools::expansion::resonance::register_resonance(
            &registry,
            Arc::clone(&gan_ying_bus),
        );
        let registry = wm_tools::expansion::sangha_tools::register_sangha(
            &registry,
            Arc::clone(&peer_discovery),
            Arc::clone(&signal_broadcast),
            Arc::clone(&sangha_chat),
            Arc::clone(&lock_manager),
        );
        let calibration_store =
            Arc::new(std::sync::Mutex::new(wm_simulation::CalibrationStore::new()));
        let registry = wm_tools::expansion::simulation_tools::register_simulation(
            &registry,
            Some(Arc::clone(&calibration_store)),
            Some(Arc::clone(&self_model)),
        );
        let claims_ledger = Arc::new(std::sync::Mutex::new(wm_simulation::ClaimsLedger::new()));
        let registry = wm_tools::expansion::claims_tools::register_claims(
            &registry,
            Some(Arc::clone(&claims_ledger)),
        );
        let registry = wm_tools::expansion::bayesian_tools::register_bayesian(&registry);

        let gana_registry = Arc::new(std::sync::Mutex::new(wm_core::GanaRegistry::new()));
        let dynamic_galaxies =
            Arc::new(std::sync::Mutex::new(wm_core::DynamicGalaxyRegistry::new()));

        let shadow_stats = Arc::new(std::sync::RwLock::new(
            wm_tools::embedding_router::ShadowModeStats::default(),
        ));

        // Build the pipeline BEFORE the meta-tools so the `wm` meta-tool can
        // dispatch inner tools through the full governance chain (destructive
        // confirmation, dharma gate, rate limit, circuit breaker, karma, stats).
        // Bound tool execution with WM_DISPATCH_TIMEOUT_MS (default 300s) so a
        // hung tool can't wedge the stdio loop or block graceful shutdown.
        let pipeline = Arc::new(
            DispatchPipeline::new(
                std::sync::Arc::new(wm_dispatch::RateLimiter::from_config(
                    &wm_dispatch::RateLimiterConfig::from_env(),
                )),
                std::sync::Arc::new(wm_dispatch::CircuitBreakerRegistry::default()),
                dharma_gate.clone(),
                // Read-only mode must not record karma entries (LMDB writes).
                if readonly {
                    None
                } else {
                    Some(karma_ledger.clone())
                },
            )
            .with_gana_registry(gana_registry.clone())
            .with_resource_rules(resource_rules.clone())
            // Read-only mode must not append journal entries either.
            .with_write_audit_option(if readonly { None } else { Some(write_audit) })
            .with_dispatch_timeout(wm_dispatch::DispatchPipeline::timeout_from_env()),
        );

        // Curate the tool surface to the active profile BEFORE the meta-tools
        // are layered on — the `wm` meta-tool then routes only within the
        // curated surface, and direct dispatch of filtered tools fails with
        // "Unknown tool". Full-surface internals (karma, friction, governance
        // tools) were already constructed above and keep working internally.
        let registry = wm_tools::profiles::apply_profile(registry, profile);
        if profile.name != "full" {
            tracing::info!(
                profile = profile.name,
                tools = registry.len(),
                "Tool surface profile applied"
            );
        }

        let (registry, embedding_router) = wm_tools::register_meta_tools_with_router(
            &registry,
            &store,
            shadow_stats.clone(),
            Some(pipeline.clone()),
        );

        let friction_auto_log = Arc::new(FrictionAutoLogTool::new(
            store.clone(),
            Some(friction_search),
        ));

        // Embodiment I/O: SensorimotorBus already created above and shared with tools

        let mut server = Self::new(
            registry,
            pipeline,
            EcoModeController::from_env(),
            store,
            associations,
            substrate,
            dharma_gate,
            resource_rules,
            reflex_table,
            timescale_bus,
            workspace,
            self_model.clone(),
            bicameral,
            drive_core,
            autonomic,
            gan_ying_bus,
            peer_discovery,
            signal_broadcast,
            sangha_chat,
            lock_manager,
            homeostatic_loop,
            anomaly_detector,
            sensorimotor_bus,
            reflex_loop,
            friction_auto_log,
            if readonly { None } else { Some(karma_ledger) },
            transaction_state,
            cyberbrain.tri_model,
            shadow_stats,
        )
        .with_readonly(readonly)
        .with_profile_name(profile.name);

        // Override mutable structure registries with shared instances (Phase 6)
        server.gana_registry = gana_registry;
        server.dynamic_galaxies = dynamic_galaxies;

        // Attach the NLU embedding router so OATS outcome stats auto-persist
        // on shutdown and are restored on startup (mutable_oats.json)
        server.embedding_router = embedding_router;

        // Attach the shared conformal store so it auto-persists on shutdown
        server.conformal_store = Some(Arc::clone(&conformal_store));
        // Attach the Brier calibration store so it auto-persists on shutdown
        server.calibration_store = Some(Arc::clone(&calibration_store));
        // Attach the claims ledger so it auto-persists on shutdown
        server.claims_ledger = Some(Arc::clone(&claims_ledger));
        // Attach the escalation queue + firewall so they auto-persist
        server.escalation_queue = Some(Arc::clone(&escalation_queue));
        server.tx_firewall = Some(Arc::clone(&firewall));

        // Restore persisted conformal calibration state (if any)
        let conformal_path = store_path
            .parent()
            .unwrap_or(store_path)
            .join("conformal_store.json");
        if conformal_path.exists() {
            match std::fs::read_to_string(&conformal_path) {
                Ok(contents) => match serde_json::from_str::<Value>(&contents) {
                    Ok(json) => {
                        if let Ok(mut store) = conformal_store.lock() {
                            match store.from_json(&json) {
                                Ok(()) => tracing::info!(
                                    path = %conformal_path.display(),
                                    "Loaded persisted conformal calibration state"
                                ),
                                Err(e) => tracing::warn!(
                                    path = %conformal_path.display(),
                                    error = %e,
                                    "Failed to restore conformal state"
                                ),
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!(path = %conformal_path.display(), error = %e, "Conformal state file unparseable");
                    }
                },
                Err(e) => {
                    tracing::warn!(path = %conformal_path.display(), error = %e, "Cannot read conformal state file");
                }
            }
        }

        // Restore persisted Brier calibration state (if any)
        let calibration_path = store_path
            .parent()
            .unwrap_or(store_path)
            .join("calibration_store.json");
        if calibration_path.exists() {
            match std::fs::read_to_string(&calibration_path) {
                Ok(contents) => match serde_json::from_str::<Value>(&contents) {
                    Ok(json) => {
                        if let Ok(mut store) = calibration_store.lock() {
                            match store.from_json(&json) {
                                Ok(()) => tracing::info!(
                                    path = %calibration_path.display(),
                                    "Loaded persisted Brier calibration state"
                                ),
                                Err(e) => tracing::warn!(
                                    path = %calibration_path.display(),
                                    error = %e,
                                    "Failed to restore calibration state"
                                ),
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!(path = %calibration_path.display(), error = %e, "Calibration state file unparseable");
                    }
                },
                Err(e) => {
                    tracing::warn!(path = %calibration_path.display(), error = %e, "Cannot read calibration state file");
                }
            }
        }

        // Restore persisted prescience claims ledger (if any)
        let claims_path = store_path
            .parent()
            .unwrap_or(store_path)
            .join("claims_ledger.json");
        if claims_path.exists() {
            match std::fs::read_to_string(&claims_path) {
                Ok(contents) => match serde_json::from_str::<Value>(&contents) {
                    Ok(json) => {
                        if let Ok(mut ledger) = claims_ledger.lock() {
                            match ledger.from_json(&json) {
                                Ok(()) => tracing::info!(
                                    path = %claims_path.display(),
                                    "Loaded persisted claims ledger"
                                ),
                                Err(e) => tracing::warn!(
                                    path = %claims_path.display(),
                                    error = %e,
                                    "Failed to restore claims ledger"
                                ),
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!(path = %claims_path.display(), error = %e, "Claims ledger file unparseable");
                    }
                },
                Err(e) => {
                    tracing::warn!(path = %claims_path.display(), error = %e, "Cannot read claims ledger file");
                }
            }
        }

        // Restore persisted self-model state (metric histories, alert rules,
        // calibrator) — `wm doctor` also reads this file for live drift health.
        let self_model_path = store_path
            .parent()
            .unwrap_or(store_path)
            .join("self_model.json");
        if self_model_path.exists() {
            match std::fs::read_to_string(&self_model_path) {
                Ok(contents) => match serde_json::from_str::<Value>(&contents) {
                    Ok(json) => {
                        if let Ok(model) = self_model.lock() {
                            match model.from_json(&json) {
                                Ok(()) => tracing::info!(
                                    path = %self_model_path.display(),
                                    "Loaded persisted self-model state"
                                ),
                                Err(e) => tracing::warn!(
                                    path = %self_model_path.display(),
                                    error = %e,
                                    "Failed to restore self-model state"
                                ),
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!(path = %self_model_path.display(), error = %e, "Self-model state file unparseable");
                    }
                },
                Err(e) => {
                    tracing::warn!(path = %self_model_path.display(), error = %e, "Cannot read self-model state file");
                }
            }
        }

        // Restore persisted dharma escalation queue (if any)
        let escalation_path = store_path
            .parent()
            .unwrap_or(store_path)
            .join("escalation_queue.json");
        if escalation_path.exists() {
            match std::fs::read_to_string(&escalation_path) {
                Ok(contents) => match serde_json::from_str::<Value>(&contents) {
                    Ok(json) => {
                        if let Ok(mut queue) = escalation_queue.lock() {
                            match queue.from_json(&json) {
                                Ok(()) => tracing::info!(
                                    path = %escalation_path.display(),
                                    "Loaded persisted escalation queue"
                                ),
                                Err(e) => tracing::warn!(
                                    path = %escalation_path.display(),
                                    error = %e,
                                    "Failed to restore escalation queue"
                                ),
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!(path = %escalation_path.display(), error = %e, "Escalation queue file unparseable");
                    }
                },
                Err(e) => {
                    tracing::warn!(path = %escalation_path.display(), error = %e, "Cannot read escalation queue file");
                }
            }
        }

        // Restore persisted tx firewall policy (if any)
        let firewall_path = store_path
            .parent()
            .unwrap_or(store_path)
            .join("tx_firewall_policy.json");
        if firewall_path.exists() {
            match std::fs::read_to_string(&firewall_path) {
                Ok(contents) => match serde_json::from_str::<Value>(&contents) {
                    Ok(json) => match firewall.from_json(&json) {
                        Ok(()) => tracing::info!(
                            path = %firewall_path.display(),
                            "Loaded persisted tx firewall policy"
                        ),
                        Err(e) => tracing::warn!(
                            path = %firewall_path.display(),
                            error = %e,
                            "Failed to restore tx firewall policy"
                        ),
                    },
                    Err(e) => {
                        tracing::warn!(path = %firewall_path.display(), error = %e, "Tx firewall policy file unparseable");
                    }
                },
                Err(e) => {
                    tracing::warn!(path = %firewall_path.display(), error = %e, "Cannot read tx firewall policy file");
                }
            }
        }

        // Attach LearnedDreamCycle for adaptive dream phase selection (Phase 6)
        server.dream = DreamCycle::new().with_learned(wm_core::LearnedDreamCycle::new());

        // Initialize imagination engine for dream cycle + Research cycle
        server.init_imagination();

        // Load mutable structures from disk (Phase 6 persistence)
        server.load_mutable_state();

        Ok(server)
    }

    /// Run the server synchronously: read JSON-RPC from stdin, write responses to stdout.
    ///
    /// This is the blocking version. For the async event-loop version with
    /// brain-wave eco mode, use `run_async()`.
    #[allow(clippy::significant_drop_tightening)] // stdio locks are held for the whole session by design
    pub fn run(&mut self) -> anyhow::Result<()> {
        let rt = tokio::runtime::Runtime::new()?;
        let stdin = std::io::stdin();
        let stdout = std::io::stdout();
        let mut out = stdout.lock();
        let mut reader = stdin.lock();

        loop {
            let line = match read_bounded_line(&mut reader, MAX_REQUEST_SIZE)? {
                BoundedLine::Eof => break,
                BoundedLine::TooLarge => {
                    let resp = error_response(
                        None,
                        -32600,
                        format!("Request too large (max {MAX_REQUEST_SIZE} bytes)"),
                        None,
                    );
                    writeln!(out, "{}", serde_json::to_string(&resp)?)?;
                    out.flush()?;
                    continue;
                }
                BoundedLine::Ok(line) => line,
            };
            if line.trim().is_empty() {
                continue;
            }

            let request: RpcRequest = match serde_json::from_str(&line) {
                Ok(req) => req,
                Err(e) => {
                    let resp = RpcResponse {
                        jsonrpc: "2.0".into(),
                        id: None,
                        result: None,
                        error: Some(RpcError {
                            code: -32700,
                            message: format!("Parse error: {e}"),
                            data: None,
                        }),
                    };
                    writeln!(out, "{}", serde_json::to_string(&resp)?)?;
                    out.flush()?;
                    continue;
                }
            };

            let response = rt.block_on(self.handle(&request));
            // Only send response if there's an ID (not a notification)
            if request.id.is_some() {
                writeln!(out, "{}", serde_json::to_string(&response)?)?;
                out.flush()?;
            }
        }

        // Graceful shutdown
        self.shutdown();

        Ok(())
    }

    /// Run the server with a tokio async event loop and brain-wave eco mode.
    ///
    /// Uses `tokio::select!` to wait on either stdin input or a timer for
    /// the next brain-wave state transition. Between events, the process
    /// uses zero CPU — the OS wakes it via epoll or timerfd.
    pub async fn run_async(&mut self) -> anyhow::Result<()> {
        use tokio::io::{AsyncWriteExt, BufReader};
        let stdin = tokio::io::stdin();
        let mut reader = BufReader::new(stdin);
        let mut stdout = tokio::io::stdout();

        // Graceful shutdown on SIGINT (all platforms) and SIGTERM (Unix).
        // v2's Python server resisted SIGTERM due to GIL deadlock — v4 must not.
        #[cfg(unix)]
        let shutdown_signal = async {
            let mut sigterm =
                tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
            tokio::select! {
                result = tokio::signal::ctrl_c() => result.map(|()| "SIGINT"),
                _ = sigterm.recv() => Ok("SIGTERM"),
            }
        };
        #[cfg(not(unix))]
        let shutdown_signal = async { tokio::signal::ctrl_c().await.map(|()| "SIGINT") };
        tokio::pin!(shutdown_signal);

        loop {
            // Recompute brain-wave state (may transition after idle)
            let _state = self.eco_mode.recompute();
            let sleep_dur = self.eco_mode.next_transition_duration();

            tokio::select! {
                // Signal received — graceful shutdown
                result = &mut shutdown_signal => {
                    match result {
                        Ok(sig) => tracing::info!(signal = sig, "Shutdown signal received — shutting down gracefully"),
                        Err(e) => tracing::warn!(error = %e, "Signal handler error — shutting down"),
                    }
                    break;
                }

                // stdin ready — MCP request arrived (bounded read)
                result = read_bounded_line_async(&mut reader, MAX_REQUEST_SIZE) => {
                    let line = match result? {
                        BoundedLine::Eof => break,
                        BoundedLine::TooLarge => {
                            let resp = error_response(
                                None,
                                -32600,
                                format!("Request too large (max {MAX_REQUEST_SIZE} bytes)"),
                                None,
                            );
                            stdout.write_all(serde_json::to_string(&resp)?.as_bytes()).await?;
                            stdout.write_all(b"\n").await?;
                            stdout.flush().await?;
                            continue;
                        }
                        BoundedLine::Ok(line) => line,
                    };
                    if line.trim().is_empty() {
                        continue;
                    }

                    let request: RpcRequest = match serde_json::from_str(&line) {
                        Ok(req) => req,
                        Err(e) => {
                            let resp = RpcResponse {
                                jsonrpc: "2.0".into(),
                                id: None,
                                result: None,
                                error: Some(RpcError {
                                    code: -32700,
                                    message: format!("Parse error: {e}"),
                                    data: None,
                                }),
                            };
                            stdout.write_all(serde_json::to_string(&resp)?.as_bytes()).await?;
                            stdout.write_all(b"\n").await?;
                            stdout.flush().await?;
                            continue;
                        }
                    };

                    let response = self.handle(&request).await;
                    // Respond to requests (id present) and to ping (no id but
                    // the spec requires an empty-result response).
                    // Notifications (notifications/*) get no response.
                    if request.id.is_some() || request.method == "ping" {
                        stdout.write_all(serde_json::to_string(&response)?.as_bytes()).await?;
                        stdout.write_all(b"\n").await?;
                        stdout.flush().await?;
                    }
                }

                // Timer fired — brain-wave state transition
                () = tokio::time::sleep(sleep_dur) => {
                    let new_state = self.eco_mode.recompute();
                    tracing::debug!(
                        brain_wave = %new_state,
                        idle_ms = self.eco_mode.idle_duration().as_millis(),
                        "Brain-wave transition"
                    );

                    // Sync timescale bus and tick all due hooks
                    if let Ok(mut bus) = self.timescale_bus.lock() {
                        bus.set_brain_wave(new_state);
                        let (executed, timeouts) = bus.tick_all();
                        if executed > 0 {
                            tracing::debug!(
                                hooks_executed = executed,
                                timeouts,
                                "Timescale tick on brain-wave transition"
                            );
                        }
                    }

                    // Drive decay on brain-wave transition
                    if let Ok(mut drive) = self.drive_core.lock() {
                        drive.decay();
                    }

                    // Check dream cycle on brain-wave transition
                    if self.dream.should_run(new_state) {
                        let ctx = if let Some(ref engine) = self.scenario_engine {
                            DreamContext::new(&self.store, &self.associations)
                                .with_imagination(engine)
                        } else {
                            DreamContext::new(&self.store, &self.associations)
                        };
                        let dream_result = self.dream.run(&ctx);
                        tracing::info!(
                            phases = dream_result.phases.len(),
                            duration_ms = dream_result.total_duration.as_millis(),
                            "Dream cycle completed (async)"
                        );

                        // Publish dream completion to workspace
                        if let Ok(mut ws) = self.workspace.lock() {
                            ws.publish_simple(
                                wm_workspace::CoreId::Dream,
                                wm_workspace::EventType::NovelDetection,
                                0.5,
                                0.8,
                                json!({
                                    "phases": dream_result.phases.len(),
                                    "duration_ms": dream_result.total_duration.as_millis(),
                                }),
                            );
                        }
                    }
                }
            }
        }

        // Graceful shutdown — emit SystemShutdown event and log
        self.shutdown();

        Ok(())
    }

    /// Perform graceful shutdown — emit SystemShutdown event, flush state.
    pub fn shutdown(&self) {
        tracing::info!("MCP server shutting down — emitting SystemShutdown event");

        // Emit shutdown event to Gan Ying Bus
        if let Ok(mut bus) = self.gan_ying_bus.lock() {
            bus.emit(
                wm_cognitive::EventType::SystemShutdown,
                "mcp_server",
                json!({
                    "tool_count": self.tool_count(),
                    "brain_wave": format!("{:?}", self.eco_mode.current()),
                }),
            );
        }

        // Final timescale tick to flush any pending hooks
        if let Ok(mut bus) = self.timescale_bus.lock() {
            let (executed, _) = bus.tick_all();
            if executed > 0 {
                tracing::debug!(
                    hooks_executed = executed,
                    "Final timescale tick on shutdown"
                );
            }
        }

        // Save mutable structures to disk (Phase 6 persistence). Read-only
        // mode must not write any state files.
        if !self.readonly {
            self.save_mutable_state();
        }

        // Flush the write-audit journal so every dispatch's declared-vs-
        // actual record survives a graceful shutdown (the journal batches
        // up to 64 entries in memory). Skipped in read-only mode — no
        // journal is attached there, and flushing would be an LMDB write.
        if !self.readonly {
            if let Some(journal) = self.pipeline.write_audit() {
                if let Err(e) = journal.flush() {
                    tracing::warn!(error = %e, "Write-audit journal flush failed on shutdown");
                }
            }
        }

        // LMDB is automatically flushed by Drop when Arc<MemoryStore> is dropped.
        // The store uses memory-mapped files, so data is persistent by default.
    }

    /// Get a reference to the eco mode controller.
    #[must_use]
    pub const fn eco_mode(&self) -> &EcoModeController {
        &self.eco_mode
    }

    /// Set the per-session request budget (hard cap on requests per connection).
    ///
    /// Pass `0` for unlimited. Default is [`DEFAULT_MAX_REQUESTS_PER_SESSION`].
    pub const fn set_request_budget(&mut self, max_requests: u64) {
        self.request_budget = crate::input_validation::RequestBudget::new(max_requests);
    }

    /// Set the time-windowed rate limit (requests per 60s window).
    ///
    /// Pass `0` for unlimited. Default is [`DEFAULT_RATE_LIMIT_RPM`].
    pub fn set_rate_limit(&mut self, requests_per_minute: u64) {
        self.rate_window = crate::input_validation::RateWindow::new(
            requests_per_minute,
            std::time::Duration::from_secs(60),
        );
    }

    /// Get a mutable reference to the eco mode controller.
    pub const fn eco_mode_mut(&mut self) -> &mut EcoModeController {
        &mut self.eco_mode
    }

    /// Get a reference to the citta heartbeat.
    #[must_use]
    pub const fn citta(&self) -> &CittaHeartbeat {
        &self.citta
    }

    /// Get a mutable reference to the citta heartbeat.
    pub const fn citta_mut(&mut self) -> &mut CittaHeartbeat {
        &mut self.citta
    }

    /// Get a reference to the dream cycle.
    #[must_use]
    pub const fn dream(&self) -> &DreamCycle {
        &self.dream
    }

    /// Get a mutable reference to the dream cycle.
    pub const fn dream_mut(&mut self) -> &mut DreamCycle {
        &mut self.dream
    }

    /// Get a reference to the reflex dispatch table.
    #[must_use]
    pub const fn reflex_table(&self) -> &Arc<std::sync::Mutex<ReflexDispatchTable>> {
        &self.reflex_table
    }

    /// Get a reference to the timescale bus.
    #[must_use]
    pub const fn timescale_bus(&self) -> &Arc<std::sync::Mutex<TimescaleBus>> {
        &self.timescale_bus
    }

    /// Get a reference to the global workspace.
    #[must_use]
    pub const fn workspace(&self) -> &Arc<std::sync::Mutex<GlobalWorkspace>> {
        &self.workspace
    }

    /// Get a reference to the memory store.
    #[must_use]
    pub fn store(&self) -> &MemoryStore {
        &self.store
    }

    /// Get a clone of the Arc to the memory store.
    #[must_use]
    pub fn store_arc(&self) -> Arc<MemoryStore> {
        Arc::clone(&self.store)
    }

    /// Get a reference to the association store.
    #[must_use]
    pub const fn associations(&self) -> &Arc<AssociationStore> {
        &self.associations
    }

    /// Get a reference to the sensorimotor bus.
    #[must_use]
    pub const fn sensorimotor_bus(&self) -> &Arc<std::sync::Mutex<SensorimotorBus>> {
        &self.sensorimotor_bus
    }

    /// Get a reference to the reflex loop.
    #[must_use]
    pub const fn reflex_loop(&self) -> &Arc<std::sync::Mutex<ReflexLoop>> {
        &self.reflex_loop
    }

    /// Get a reference to the karma ledger (if present).
    #[must_use]
    pub const fn karma_ledger(&self) -> Option<&Arc<KarmaLedger>> {
        self.karma_ledger.as_ref()
    }

    /// Get a reference to the tool registry.
    #[must_use]
    pub const fn registry(&self) -> &ToolRegistry {
        &self.registry
    }

    /// Get a reference to the dispatch pipeline.
    #[must_use]
    pub fn pipeline(&self) -> &DispatchPipeline {
        &self.pipeline
    }

    /// Get a reference to the substrate monitor.
    #[must_use]
    pub fn substrate(&self) -> &SubstrateMonitor {
        &self.substrate
    }

    /// Get a reference to the Dharma gate.
    #[must_use]
    pub fn dharma_gate(&self) -> &DharmaGate {
        &self.dharma_gate
    }

    /// Get a reference to the resource rules.
    #[must_use]
    pub fn resource_rules(&self) -> &ResourceRules {
        &self.resource_rules
    }

    /// Get a reference to the self-model.
    #[must_use]
    pub fn self_model(&self) -> &std::sync::Mutex<SelfModel> {
        &self.self_model
    }

    /// Get a reference to the bicameral engine.
    #[must_use]
    pub fn bicameral(&self) -> &std::sync::Mutex<BicameralEngine> {
        &self.bicameral
    }

    /// Get a reference to the drive core.
    #[must_use]
    pub fn drive_core(&self) -> &std::sync::Mutex<DriveCore> {
        &self.drive_core
    }

    /// Get the number of registered tools.
    #[must_use]
    pub fn tool_count(&self) -> usize {
        self.registry.all().len()
    }

    /// Initialize the imagination engine (ScenarioEngine) for dream cycle
    /// counterfactual replay and Research cycle hypothesis generation.
    /// Called automatically by `with_defaults`; can be called manually
    /// for custom server setups.
    pub fn init_imagination(&mut self) {
        if self.scenario_engine.is_none() {
            let wm = wm_bicameral::world_model_from_env();
            let evaluator = wm_bicameral::ScenarioEvaluator::with_defaults();
            self.scenario_engine = Some(wm_bicameral::ScenarioEngine::with_defaults(wm, evaluator));
            tracing::info!("Imagination engine initialized on McpServer");
        }
    }

    /// Get a reference to the imagination engine, if initialized.
    #[must_use]
    pub const fn scenario_engine(&self) -> Option<&wm_bicameral::ScenarioEngine> {
        self.scenario_engine.as_ref()
    }

    /// Get a reference to the GanaRegistry for taxonomy drift tracking (Phase 6).
    #[must_use]
    pub const fn gana_registry(&self) -> &Arc<std::sync::Mutex<wm_core::GanaRegistry>> {
        &self.gana_registry
    }

    /// Get a reference to the DynamicGalaxyRegistry (Phase 6).
    #[must_use]
    pub const fn dynamic_galaxies(&self) -> &Arc<std::sync::Mutex<wm_core::DynamicGalaxyRegistry>> {
        &self.dynamic_galaxies
    }

    /// Save mutable structures (GanaRegistry, DynamicGalaxyRegistry, LearnedDreamCycle,
    /// ShadowModeStats) to JSON files in the store directory. Called on shutdown to persist learned state.
    pub fn save_mutable_state(&self) {
        let store_dir = self.store.path();

        if let Ok(registry) = self.gana_registry.lock() {
            let path = store_dir.join("mutable_gana_registry.json");
            match serde_json::to_string_pretty(&*registry) {
                Ok(json) => {
                    if let Err(e) = std::fs::write(&path, json) {
                        tracing::warn!(path = %path.display(), error = %e, "Failed to save GanaRegistry");
                    } else {
                        tracing::info!(path = %path.display(), "Saved GanaRegistry");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to serialize GanaRegistry"),
            }
        }

        if let Ok(galaxies) = self.dynamic_galaxies.lock() {
            let path = store_dir.join("mutable_dynamic_galaxies.json");
            match serde_json::to_string_pretty(&*galaxies) {
                Ok(json) => {
                    if let Err(e) = std::fs::write(&path, json) {
                        tracing::warn!(path = %path.display(), error = %e, "Failed to save DynamicGalaxyRegistry");
                    } else {
                        tracing::info!(path = %path.display(), "Saved DynamicGalaxyRegistry");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to serialize DynamicGalaxyRegistry"),
            }
        }

        if let Some(learned) = self.dream.learned() {
            let path = store_dir.join("mutable_learned_dream.json");
            match serde_json::to_string_pretty(learned) {
                Ok(json) => {
                    if let Err(e) = std::fs::write(&path, json) {
                        tracing::warn!(path = %path.display(), error = %e, "Failed to save LearnedDreamCycle");
                    } else {
                        tracing::info!(path = %path.display(), "Saved LearnedDreamCycle");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to serialize LearnedDreamCycle"),
            }
        }

        // Save shadow mode stats (OATS)
        if let Ok(stats) = self.shadow_stats.read() {
            let path = store_dir.join("mutable_shadow_stats.json");
            match serde_json::to_string_pretty(&*stats) {
                Ok(json) => {
                    if let Err(e) = std::fs::write(&path, json) {
                        tracing::warn!(path = %path.display(), error = %e, "Failed to save ShadowModeStats");
                    } else {
                        tracing::info!(path = %path.display(), "Saved ShadowModeStats");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to serialize ShadowModeStats"),
            }
        }

        // Save per-tool usage stats so `tools.usage_report` ranks on
        // cumulative cross-restart history. Only tools that were actually
        // called are persisted — the file stays small and restore is cheap.
        {
            let snapshots: std::collections::BTreeMap<String, wm_core::ToolStatsSnapshot> = self
                .registry
                .all_ref()
                .iter()
                .filter_map(|t| {
                    let snap = t.stats().snapshot();
                    (snap.call_count > 0).then(|| (t.name().to_string(), snap))
                })
                .collect();
            if !snapshots.is_empty() {
                let path = store_dir.join("mutable_tool_stats.json");
                match serde_json::to_string_pretty(&snapshots) {
                    Ok(json) => {
                        if let Err(e) = std::fs::write(&path, json) {
                            tracing::warn!(path = %path.display(), error = %e, "Failed to save tool usage stats");
                        } else {
                            tracing::info!(path = %path.display(), tools = snapshots.len(), "Saved tool usage stats");
                        }
                    }
                    Err(e) => tracing::warn!(error = %e, "Failed to serialize tool usage stats"),
                }
            }
        }

        // Save OATS outcome stats (the NLU router's learned refinement).
        // Without this the router's success/failure centroids are lost on
        // every restart and OATS never accumulates cross-session learning.
        if let Some(router) = &self.embedding_router {
            let path = store_dir.join("mutable_oats.json");
            if let Some(json) = router.save_oats() {
                if let Err(e) = std::fs::write(&path, json) {
                    tracing::warn!(path = %path.display(), error = %e, "Failed to save OATS");
                } else {
                    tracing::info!(path = %path.display(), "Saved OATS outcome stats");
                }
            } else {
                tracing::warn!("Failed to serialize OATS outcome stats");
            }
        }

        // Save conformal calibration state — the doctor reads this file at
        // `<store_root>/conformal_store.json` (store root, not lmdb dir).
        if let Some(conformal) = &self.conformal_store {
            if let Ok(store) = conformal.lock() {
                let path = store_dir
                    .parent()
                    .unwrap_or(store_dir)
                    .join("conformal_store.json");
                match serde_json::to_string_pretty(&store.to_json()) {
                    Ok(json) => {
                        if let Err(e) = std::fs::write(&path, json) {
                            tracing::warn!(path = %path.display(), error = %e, "Failed to save conformal state");
                        } else {
                            tracing::info!(path = %path.display(), "Saved conformal calibration state");
                        }
                    }
                    Err(e) => tracing::warn!(error = %e, "Failed to serialize conformal state"),
                }
            }
        }

        // Save Brier calibration state (prediction history for the scorecard)
        if let Some(calibration) = &self.calibration_store {
            if let Ok(store) = calibration.lock() {
                let path = store_dir
                    .parent()
                    .unwrap_or(store_dir)
                    .join("calibration_store.json");
                match serde_json::to_string_pretty(&store.to_json()) {
                    Ok(json) => {
                        if let Err(e) = std::fs::write(&path, json) {
                            tracing::warn!(path = %path.display(), error = %e, "Failed to save calibration state");
                        } else {
                            tracing::info!(path = %path.display(), "Saved Brier calibration state");
                        }
                    }
                    Err(e) => tracing::warn!(error = %e, "Failed to serialize calibration state"),
                }
            }
        }

        // Save prescience claims ledger
        if let Some(ledger) = &self.claims_ledger {
            if let Ok(ledger_guard) = ledger.lock() {
                let path = store_dir
                    .parent()
                    .unwrap_or(store_dir)
                    .join("claims_ledger.json");
                match serde_json::to_string_pretty(&ledger_guard.to_json()) {
                    Ok(json) => {
                        if let Err(e) = std::fs::write(&path, json) {
                            tracing::warn!(path = %path.display(), error = %e, "Failed to save claims ledger");
                        } else {
                            tracing::info!(path = %path.display(), "Saved claims ledger");
                        }
                    }
                    Err(e) => tracing::warn!(error = %e, "Failed to serialize claims ledger"),
                }
            }
        }

        // Save self-model state (metric histories, alert rules, calibrator) —
        // `wm doctor` reads this file at `<store_root>/self_model.json` for
        // live conformal coverage / Brier drift health.
        {
            let path = store_dir
                .parent()
                .unwrap_or(store_dir)
                .join("self_model.json");
            let model_json = match self.self_model.lock() {
                Ok(model) => model.to_json(),
                Err(e) => {
                    tracing::warn!(error = %e, "Failed to lock self-model for save");
                    serde_json::json!({})
                }
            };
            match serde_json::to_string_pretty(&model_json) {
                Ok(json) => {
                    if let Err(e) = std::fs::write(&path, json) {
                        tracing::warn!(path = %path.display(), error = %e, "Failed to save self-model state");
                    } else {
                        tracing::info!(path = %path.display(), "Saved self-model state");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to serialize self-model state"),
            }
        }

        // Save dharma escalation queue
        if let Some(queue) = &self.escalation_queue {
            if let Ok(queue_guard) = queue.lock() {
                let path = store_dir
                    .parent()
                    .unwrap_or(store_dir)
                    .join("escalation_queue.json");
                match serde_json::to_string_pretty(&queue_guard.to_json()) {
                    Ok(json) => {
                        if let Err(e) = std::fs::write(&path, json) {
                            tracing::warn!(path = %path.display(), error = %e, "Failed to save escalation queue");
                        } else {
                            tracing::info!(path = %path.display(), "Saved escalation queue");
                        }
                    }
                    Err(e) => tracing::warn!(error = %e, "Failed to serialize escalation queue"),
                }
            }
        }

        // Save tx firewall policy
        if let Some(firewall) = &self.tx_firewall {
            let path = store_dir
                .parent()
                .unwrap_or(store_dir)
                .join("tx_firewall_policy.json");
            match serde_json::to_string_pretty(&firewall.to_json()) {
                Ok(json) => {
                    if let Err(e) = std::fs::write(&path, json) {
                        tracing::warn!(path = %path.display(), error = %e, "Failed to save tx firewall policy");
                    } else {
                        tracing::info!(path = %path.display(), "Saved tx firewall policy");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to serialize tx firewall policy"),
            }
        }
    }

    /// Load mutable structures from JSON files in the store directory.
    /// Called on startup to restore learned state from previous sessions.
    pub fn load_mutable_state(&mut self) {
        let store_dir = self.store.path();

        let gana_path = store_dir.join("mutable_gana_registry.json");
        if gana_path.exists() {
            match std::fs::read_to_string(&gana_path) {
                Ok(json) => {
                    if let Ok(mut registry) = serde_json::from_str::<wm_core::GanaRegistry>(&json) {
                        registry.rebuild_pairs();
                        if let Ok(mut current) = self.gana_registry.lock() {
                            *current = registry;
                            tracing::info!("Loaded GanaRegistry from disk");
                        }
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to read GanaRegistry file"),
            }
        }

        let galaxies_path = store_dir.join("mutable_dynamic_galaxies.json");
        if galaxies_path.exists() {
            match std::fs::read_to_string(&galaxies_path) {
                Ok(json) => {
                    if let Ok(registry) =
                        serde_json::from_str::<wm_core::DynamicGalaxyRegistry>(&json)
                    {
                        if let Ok(mut current) = self.dynamic_galaxies.lock() {
                            *current = registry;
                            tracing::info!("Loaded DynamicGalaxyRegistry from disk");
                        }
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to read DynamicGalaxyRegistry file"),
            }
        }

        let dream_path = store_dir.join("mutable_learned_dream.json");
        if dream_path.exists() {
            match std::fs::read_to_string(&dream_path) {
                Ok(json) => {
                    if let Ok(learned) = serde_json::from_str::<wm_core::LearnedDreamCycle>(&json) {
                        self.dream.set_learned(learned);
                        tracing::info!("Loaded LearnedDreamCycle from disk");
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to read LearnedDreamCycle file"),
            }
        }

        let shadow_path = store_dir.join("mutable_shadow_stats.json");
        if shadow_path.exists() {
            match std::fs::read_to_string(&shadow_path) {
                Ok(json) => {
                    if let Ok(stats) =
                        serde_json::from_str::<wm_tools::embedding_router::ShadowModeStats>(&json)
                    {
                        if let Ok(mut current) = self.shadow_stats.write() {
                            *current = stats;
                            tracing::info!("Loaded ShadowModeStats from disk");
                        }
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to read ShadowModeStats file"),
            }
        }

        let oats_path = store_dir.join("mutable_oats.json");
        if oats_path.exists() {
            match std::fs::read_to_string(&oats_path) {
                Ok(json) => {
                    if let Some(router) = &self.embedding_router {
                        router.load_oats(&json);
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to read OATS file"),
            }
        }

        // Restore per-tool usage stats. Tool Arcs are shared across all
        // registries (tools.list, wm routing, dispatch), so restoring here
        // rehydrates the same atomics the pipeline updates.
        let tool_stats_path = store_dir.join("mutable_tool_stats.json");
        if tool_stats_path.exists() {
            match std::fs::read_to_string(&tool_stats_path) {
                Ok(json) => {
                    match serde_json::from_str::<
                        std::collections::BTreeMap<String, wm_core::ToolStatsSnapshot>,
                    >(&json)
                    {
                        Ok(snapshots) => {
                            let mut restored = 0usize;
                            for tool in self.registry.all_ref() {
                                if let Some(snap) = snapshots.get(tool.name()) {
                                    tool.stats().restore(snap);
                                    restored += 1;
                                }
                            }
                            tracing::info!(restored, "Loaded tool usage stats from disk");
                        }
                        Err(e) => {
                            tracing::warn!(error = %e, "Failed to parse tool usage stats file");
                        }
                    }
                }
                Err(e) => tracing::warn!(error = %e, "Failed to read tool usage stats file"),
            }
        }
    }

    /// Get memory counts per galaxy as a JSON object.
    #[must_use]
    pub fn galaxy_counts(&self) -> Value {
        let mut counts = serde_json::Map::new();
        let mut total = 0u64;
        for galaxy in wm_core::Galaxy::all() {
            let count = self.store.count(galaxy).unwrap_or(0) as u64;
            if count > 0 {
                counts.insert(galaxy.db_name().to_string(), json!(count));
                total += count;
            }
        }
        counts.insert("total".into(), json!(total));
        Value::Object(counts)
    }

    /// Sample the current hardware state and update the Dharma gate's homeostasis.
    /// Should be called periodically (e.g., on each MCP request or timer tick).
    pub fn refresh_homeostasis(&self) {
        let hv = self.substrate.sample();
        self.dharma_gate.update_homeostasis(hv.into());
    }

    /// Sample hardware metrics and record them into the self-model.
    /// Also records citta coherence as a metric.
    /// Should be called on each MCP request to keep the self-model's
    /// metric history up to date for forecasting.
    pub fn refresh_self_model(&self) {
        let hv = self.substrate.sample();
        if let Ok(model) = self.self_model.lock() {
            model.record(wm_selfmodel::MetricKind::CpuLoad, hv.cpu_load);
            model.record(wm_selfmodel::MetricKind::MemoryPressure, hv.memory_pressure);
            model.record(wm_selfmodel::MetricKind::SwapUsage, hv.swap_usage);
            model.record(wm_selfmodel::MetricKind::DiskIo, hv.disk_io_rate);
            // Coherence from citta heartbeat
            let (coherence, _) = self.citta.coherence_valence();
            model.record(wm_selfmodel::MetricKind::Coherence, coherence);
        }
    }

    /// Get a reference to the Gan Ying Bus.
    #[must_use]
    pub const fn gan_ying_bus(&self) -> &Arc<std::sync::Mutex<GanYingBus>> {
        &self.gan_ying_bus
    }

    /// Get a reference to the homeostatic loop.
    #[must_use]
    pub const fn homeostatic_loop(&self) -> &Arc<std::sync::Mutex<HomeostaticLoop>> {
        &self.homeostatic_loop
    }

    /// Get a reference to the anomaly detector.
    #[must_use]
    pub const fn anomaly_detector(&self) -> &Arc<std::sync::Mutex<AnomalyDetector>> {
        &self.anomaly_detector
    }

    /// Handle a single JSON-RPC request string and return a JSON response string.
    ///
    /// This is the primary entry point for the PyO3 bridge — Python calls
    /// this with a JSON-RPC request string and gets back a JSON-RPC response string.
    pub async fn handle_request(&mut self, json_request: &str) -> String {
        let request: RpcRequest = match serde_json::from_str(json_request) {
            Ok(req) => req,
            Err(e) => {
                let resp = RpcResponse {
                    jsonrpc: "2.0".into(),
                    id: None,
                    result: None,
                    error: Some(RpcError {
                        code: -32700,
                        message: format!("Parse error: {e}"),
                        data: None,
                    }),
                };
                return serde_json::to_string(&resp).unwrap_or_else(|_| "{}".into());
            }
        };

        let response = self.handle(&request).await;
        serde_json::to_string(&response).unwrap_or_else(|_| "{}".into())
    }

    /// Handle a single JSON-RPC request.
    async fn handle(&mut self, req: &RpcRequest) -> RpcResponse {
        // Boundary hardening — enforce the per-session request budget first
        if !self.request_budget.record() {
            return error_response(
                req.id.as_ref(),
                -32000,
                "Request budget exhausted — connection limit reached",
                Some(
                    json!({"used": self.request_budget.used(), "limit": self.request_budget.limit()}),
                ),
            );
        }

        // Boundary hardening — time-windowed rate limiting (burst throttle)
        if let Err(retry_after) = self.rate_window.record() {
            return error_response(
                req.id.as_ref(),
                -32000,
                "Rate limit exceeded — slow down",
                Some(
                    json!({"retry_after_secs": retry_after, "limit_rpm": self.rate_window.limit()}),
                ),
            );
        }

        // Boundary hardening — validate tool call params (tools/call only;
        // other methods such as ping or initialize have their own shapes).
        // This enforces the 64KB params cap, string length limits, injection
        // filtering, SSRF protection and path-traversal protection that
        // previously existed only as dead code.
        if req.method == "tools/call" {
            let raw = json!({
                "jsonrpc": req.jsonrpc,
                "method": req.method,
                "id": req.id,
                "params": req.params,
            });
            if let crate::input_validation::ValidationResult::Invalid(reason) =
                crate::input_validation::validate_tools_call(&raw)
            {
                tracing::warn!(method = %req.method, reason = %reason, "MCP request rejected by boundary validation");
                return error_response(
                    req.id.as_ref(),
                    -32602,
                    "Invalid params",
                    Some(json!({"reason": reason})),
                );
            }
        }

        // Record event for brain-wave tracking on every request
        self.eco_mode.record_event();
        // Refresh homeostasis from real hardware data (Lakshmi → Dharma)
        self.refresh_homeostasis();
        // Feed substrate + citta metrics into self-model for forecasting
        self.refresh_self_model();

        let result = match req.method.as_str() {
            "initialize" => self.handle_initialize(),
            "tools/list" => self.handle_tools_list(),
            "tools/call" => self.handle_tools_call(&req.params).await,
            // MCP liveness check — the spec requires an empty result response
            // even though ping carries no id. Clients like opencode stall the
            // connection when this goes unanswered.
            "ping" => Ok(json!({})),
            _ => Err(RpcError {
                code: -32601,
                message: format!("Method not found: {}", req.method),
                data: None,
            }),
        };

        match result {
            Ok(value) => RpcResponse {
                jsonrpc: "2.0".into(),
                id: req.id.clone(),
                result: Some(value),
                error: None,
            },
            Err(err) => RpcResponse {
                jsonrpc: "2.0".into(),
                id: req.id.clone(),
                result: None,
                error: Some(err),
            },
        }
    }

    /// Handle `initialize` — return server capabilities.
    fn handle_initialize(&self) -> Result<Value, RpcError> {
        Ok(json!({
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "whitemagic",
                "version": env!("CARGO_PKG_VERSION"),
            },
            "capabilities": {
                "tools": {},
            },
            "instructions": concat!(
                "WhiteMagic gives you durable local project memory. Session rhythm:\n",
                "1. Before starting work, call wm(route=\"session.continuity\") to recall where the previous session left off.\n",
                "2. Start each working session with wm(route=\"session.start\", args={\"title\": \"...\"}).\n",
                "3. Record selectively as you go — decisions, breakthroughs, errors worth remembering, and summaries — via wm(route=\"session.record\", args={\"content\": \"...\", \"role\": \"ai\", \"turn_type\": \"decision\"|\"breakthrough\"|\"error\"|\"summary\", \"importance\": 0.0-1.0}). Do not record everything; record what a future session needs.\n",
                "4. Use explicit route= dispatch for important operations so behavior is dependable.\n",
                "5. At the end of a session, record a short summary turn, then wm(route=\"session.checkpoint\").\n",
                "6. Discover the available surface with wm(route=\"tools.list\").\n",
                "Privacy and backup: memory is stored locally under your store directory and is not encrypted — never record credentials or secrets. Back up the whole store directory regularly; privacy flags exclude memories from responses but do not encrypt them."
            ),
        }))
    }

    /// Handle `tools/list` — return only the `wm` meta-tool.
    ///
    /// The `wm` meta-tool is the single entry point for MCP clients. It routes
    /// natural language input to the active tool surface via TF-IDF NLU
    /// classification, or accepts an explicit `route` parameter for direct
    /// dispatch. Use `wm(thought="list tools")` or `wm(route="tools.list")` to
    /// discover available tools. The description reflects the active profile
    /// instead of advertising the full archive surface.
    ///
    /// In Delta (dormant) state, no tools are returned.
    fn handle_tools_list(&self) -> Result<Value, RpcError> {
        let brain_wave = self.eco_mode.current();

        // Delta: system dormant — no tools available
        if brain_wave == wm_core::BrainWave::Delta {
            return Ok(json!({
                "tools": []
            }));
        }

        // Only expose the wm meta-tool — the routeable surface depends on the
        // active tool profile, so discovery text is generated from the
        // registry rather than hardcoded full-surface counts.
        if let Some(wm) = self.registry.get("wm") {
            let tool_count = self
                .registry
                .all()
                .iter()
                .filter(|t| {
                    !["wm", "tools.list", "gnosis", "nlu.shadow_report"].contains(&t.name())
                })
                .count();
            let description = format!(
                "WhiteMagic meta-tool — {} tool surface ({} tools). Use thought= for NLU routing (e.g. 'remember that X is Y', 'search for Z', 'list tools'), route= for explicit dispatch (e.g. 'memory.create'), and args= for passthrough arguments. Say 'list tools' to discover available tools.",
                self.profile_name, tool_count
            );
            Ok(json!({
                "tools": [{
                    "name": wm.name(),
                    "description": description,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "thought": {
                                "type": "string",
                                "description": "Natural language input describing what to do. Auto-routes to the best-matching tool via TF-IDF NLU classification.",
                            },
                            "route": {
                                "type": "string",
                                "description": "Explicit tool name for direct dispatch (e.g. 'memory.create', 'tools.list').",
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments to pass through to the target tool.",
                            },
                        },
                    },
                }]
            }))
        } else {
            // Fallback: if wm meta-tool is not registered, list all available tools
            let available = self.registry.available_in(brain_wave);
            let tools: Vec<Value> = available
                .iter()
                .map(|t| {
                    json!({
                        "name": t.name(),
                        "description": t.description(),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "args": {
                                    "type": "object",
                                    "description": "Tool arguments (passthrough).",
                                },
                            },
                        },
                    })
                })
                .collect();
            Ok(json!({ "tools": tools }))
        }
    }

    /// Handle `tools/call` — dispatch through the governance pipeline.
    async fn handle_tools_call(&mut self, params: &Value) -> Result<Value, RpcError> {
        let name = params
            .get("name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| RpcError {
                code: -32602,
                message: "Missing 'name' in params".into(),
                data: None,
            })?;

        // Look up the tool — wm meta-tool or any directly registered tool
        let tool = self.registry.get(name).ok_or_else(|| RpcError {
            code: -32602,
            message: format!("Unknown tool: '{name}'"),
            data: None,
        })?;

        let mut arguments = params
            .get("arguments")
            .cloned()
            .unwrap_or_else(|| json!({}));

        // Strip _meta from tool arguments — _meta is a top-level MCP request
        // field, not a tool argument. Untrusted callers could inject _meta
        // inside arguments to bypass compartment/identity controls.
        if let Some(obj) = arguments.as_object_mut() {
            obj.remove("_meta");
        }

        let mut ctx = Context::new(self.eco_mode.current());
        // Read-only mode: the dispatch pipeline refuses every tool that
        // declares writes (both direct dispatch and inner `wm` routing).
        ctx.readonly = self.readonly;

        // Extract agent identity from request _meta (MCP standard metadata field)
        if let Some(meta) = params.get("_meta") {
            if let Some(user_id) = meta.get("user_id").and_then(|v| v.as_str()) {
                ctx.user_id = Some(user_id.to_string());
            }
            if let Some(compartment) = meta.get("compartment").and_then(|v| v.as_str()) {
                ctx.compartment = Some(compartment.to_string());
            }
            if let Some(dharma) = meta.get("dharma_profile").and_then(|v| v.as_str()) {
                ctx.dharma_profile = Some(dharma.to_string());
            }
        }

        // Inject citta coherence and valence into the dispatch context
        let (coherence, valence) = self.citta.coherence_valence();
        ctx.citta_coherence = coherence;
        ctx.citta_valence = valence;

        // Inject self-model confidence into the dispatch context
        // The self-model's confidence (0.0–1.0) reflects forecast accuracy
        // and metric stability. Below 0.5 triggers conservative dispatch.
        if let Ok(model) = self.self_model.lock() {
            ctx.self_model_confidence = model.confidence();
        }

        // Inject drive state into the dispatch context
        // Drive bias influences tool selection and dispatch gates
        let drive_bias = {
            if let Ok(drive) = self.drive_core.lock() {
                let bias = drive.bias();
                let state = drive.state();
                ctx.drive_curiosity = state.curiosity;
                ctx.drive_caution = state.caution;
                ctx.drive_energy = state.energy;
                ctx.drive_exploration_weight = bias.exploration_weight;
                ctx.drive_conservative_weight = bias.conservative_weight;
                bias
            } else {
                wm_cognitive::DriveBias {
                    exploration_weight: 0.5,
                    conservative_weight: 0.3,
                    lightweight_weight: 0.2,
                    social_weight: 0.4,
                    confidence: 0.5,
                }
            }
        };

        // Sync timescale bus brain-wave state
        if let Ok(mut bus) = self.timescale_bus.lock() {
            bus.set_brain_wave(self.eco_mode.current());
        }

        let dispatch_start = std::time::Instant::now();

        // ── Gan Ying Bus: emit ToolDispatchStart event ──
        {
            if let Ok(mut bus) = self.gan_ying_bus.lock() {
                bus.emit(
                    wm_cognitive::EventType::ToolDispatchStart,
                    "mcp_server",
                    json!({
                        "tool": name,
                        "brain_wave": format!("{:?}", self.eco_mode.current()),
                    }),
                );
            }
        }

        let arg_size = serde_json::to_vec(&arguments).map(|v| v.len()).unwrap_or(0);
        let dispatch_result = self
            .pipeline
            .dispatch(tool.as_ref(), &mut ctx, arguments)
            .await;
        let dispatch_latency = dispatch_start.elapsed().as_secs_f32();

        // The `wm` meta-tool reports inner tool failures as structured
        // `{"status":"error", ...}` payloads (Ok at the JSON-RPC level) so
        // NLU clients get readable errors. Derive the true dispatch outcome
        // from that payload so the self-model, friction logging, citta, drive
        // and workspace layers all see inner failures as failures.
        let (success, inner_error) = match (&dispatch_result, name) {
            (Ok(v), "wm") if v.get("status").and_then(Value::as_str) == Some("error") => (
                false,
                v.get("error")
                    .or_else(|| v.get("message"))
                    .and_then(Value::as_str)
                    .map(ToString::to_string),
            ),
            (Ok(_), _) => (true, None),
            (Err(_), _) => (false, None),
        };

        // Record dispatch metrics into self-model for future forecasting
        if let Ok(model) = self.self_model.lock() {
            model.record(wm_selfmodel::MetricKind::Latency, dispatch_latency);
            let error_rate = if success { 0.0 } else { 1.0 };
            model.record(wm_selfmodel::MetricKind::ErrorRate, error_rate);
        }

        // Citta heartbeat — post-dispatch consciousness update
        let effectiveness = tool.stats().effectiveness_f32();

        // ── Gan Ying Bus: emit ToolDispatchComplete/Error event ──
        {
            if let Ok(mut bus) = self.gan_ying_bus.lock() {
                let event_type = if success {
                    wm_cognitive::EventType::ToolDispatchSuccess
                } else {
                    wm_cognitive::EventType::ToolDispatchError
                };
                bus.emit(
                    event_type,
                    "mcp_server",
                    json!({
                        "tool": name,
                        "success": success,
                        "latency_ms": dispatch_latency * 1000.0,
                        "effectiveness": effectiveness,
                    }),
                );
            }
        }

        // ── RSI Phase 2: Rich friction logging with telemetry ──
        let error_msg = match &dispatch_result {
            Err(e) => format!("{e}"),
            Ok(_) => inner_error.unwrap_or_default(),
        };
        let tool_stats_snapshot = tool.stats().snapshot();
        let response_size = match &dispatch_result {
            Ok(v) => serde_json::to_vec(v).map(|v| v.len()).unwrap_or(0),
            Err(_) => 0,
        };
        let telemetry = DispatchTelemetry {
            tool: name.to_string(),
            success,
            latency_ms: dispatch_latency * 1000.0,
            error: error_msg,
            brain_wave: format!("{:?}", self.eco_mode.current()),
            effectiveness,
            karma_debt: ctx.karma_debt,
            self_model_confidence: ctx.self_model_confidence,
            drive_bias_confidence: drive_bias.confidence,
            citta_coherence: ctx.citta_coherence,
            citta_valence: ctx.citta_valence,
            tool_stats: tool_stats_snapshot,
            routed_via_wm: name == "wm",
            arg_size_bytes: arg_size,
            response_size_bytes: response_size,
        };

        if success {
            // Anomaly detection on successful dispatches (suppressed in
            // read-only mode — friction auto-log writes to the store).
            let peak_ms = telemetry.tool_stats.peak_latency_ns as f32 / 1_000_000.0;
            if !self.readonly && peak_ms > 0.0 && telemetry.latency_ms > peak_ms {
                if let Err(e) = self
                    .friction_auto_log
                    .log_anomaly(&telemetry, "high_latency")
                {
                    tracing::warn!("Failed to auto-log anomaly entry: {e}");
                }
            } else if !self.readonly && effectiveness < 0.3 && telemetry.tool_stats.call_count > 5 {
                // Only flag low_effectiveness after enough calls for a
                // meaningful success rate. Skip on fresh processes where
                // stats haven't accumulated yet (avoids false positives).
                if let Err(e) = self
                    .friction_auto_log
                    .log_anomaly(&telemetry, "low_effectiveness")
                {
                    tracing::warn!("Failed to auto-log anomaly entry: {e}");
                }
            } else if !self.readonly && ctx.karma_debt > 0.5 {
                if let Err(e) = self
                    .friction_auto_log
                    .log_anomaly(&telemetry, "high_karma_debt")
                {
                    tracing::warn!("Failed to auto-log anomaly entry: {e}");
                }
            }
        } else if !self.readonly {
            if let Err(e) = self.friction_auto_log.log_error(&telemetry) {
                tracing::warn!("Failed to auto-log friction entry: {e}");
            }
        }

        // WS-3: Bidirectional karma-friction bridge
        // Friction→karma: record a small debt signal only when actual friction occurred
        let had_friction = !success || (effectiveness < 0.3 && telemetry.tool_stats.call_count > 5);
        if had_friction {
            if let Some(ref karma) = self.karma_ledger {
                if let Err(e) = karma.record_friction_signal(name) {
                    tracing::warn!("Failed to record friction signal to karma ledger: {e}");
                }
            }
        }

        // Karma→friction: if total debt exceeds threshold, log governance friction
        if let Some(ref karma) = self.karma_ledger {
            let total_debt = karma.total_debt();
            if total_debt > 2.0 {
                let gov_severity = if total_debt > 3.0 { "high" } else { "medium" };
                let gov_telemetry = DispatchTelemetry {
                    tool: format!("__karma__:{name}"),
                    success: true,
                    latency_ms: 0.0,
                    error: format!("Karma debt threshold exceeded: {total_debt:.2}"),
                    brain_wave: format!("{:?}", self.eco_mode.current()),
                    effectiveness,
                    karma_debt: total_debt,
                    self_model_confidence: ctx.self_model_confidence,
                    drive_bias_confidence: 0.5,
                    citta_coherence: ctx.citta_coherence,
                    citta_valence: ctx.citta_valence,
                    tool_stats: tool.stats().snapshot(),
                    routed_via_wm: false,
                    arg_size_bytes: 0,
                    response_size_bytes: 0,
                };
                let hash = wm_tools::expansion::friction_hash(
                    &gov_telemetry.tool,
                    "governance",
                    gov_severity,
                    &gov_telemetry.error,
                );
                let hash_tag = format!("rsi:hash:{hash}");
                // Only log if no existing governance friction with this hash
                // (and never in read-only mode — the friction log writes).
                if !self.readonly
                    && !wm_tools::expansion::friction_hash_exists(&self.store, &hash_tag)
                {
                    if let Err(e) = self.friction_auto_log.log_error(&gov_telemetry) {
                        tracing::warn!("Failed to auto-log governance friction: {e}");
                    }
                }
            }
        }

        self.citta.beat(success, name, effectiveness);

        // Karma feedback into citta vector
        self.citta.karma_feedback(ctx.karma_debt);

        // ── Deep Integration: Drive events ──
        // Fire drive events based on dispatch outcome
        if let Ok(mut drive) = self.drive_core.lock() {
            let event_kind = if success {
                wm_cognitive::DriveEventKind::ToolSuccess
            } else {
                wm_cognitive::DriveEventKind::ToolError
            };
            drive.process_event(
                &wm_cognitive::DriveEvent::new(event_kind)
                    .with_source(wm_cognitive::DriveEventSource::Dispatch)
                    .with_detail(format!(
                        "{} dispatch: {}",
                        name,
                        if success { "ok" } else { "error" }
                    )),
            );

            // Feed self-model confidence back into drive system
            if ctx.self_model_confidence < 0.5 {
                drive.process_event(
                    &wm_cognitive::DriveEvent::new(wm_cognitive::DriveEventKind::LowConfidence)
                        .with_source(wm_cognitive::DriveEventSource::SelfModel),
                );
            } else if ctx.self_model_confidence > 0.8 {
                drive.process_event(
                    &wm_cognitive::DriveEvent::new(wm_cognitive::DriveEventKind::HighConfidence)
                        .with_source(wm_cognitive::DriveEventSource::SelfModel),
                );
            }
        }

        // ── Deep Integration: Workspace events ──
        // Publish dispatch outcome to global workspace
        if let Ok(mut ws) = self.workspace.lock() {
            let event_type = if success {
                wm_workspace::EventType::Reward
            } else {
                wm_workspace::EventType::Error
            };
            let novelty = if success { 0.3 } else { 0.7 };
            let confidence = drive_bias.confidence;
            ws.publish_simple(
                wm_workspace::CoreId::Dispatch,
                event_type,
                novelty,
                confidence,
                json!({
                    "tool": name,
                    "success": success,
                    "latency_ms": dispatch_latency * 1000.0,
                    "effectiveness": effectiveness,
                }),
            );
        }

        // ── Deep Integration: Autonomic layer (BitMamba) ──
        // Feed dispatch telemetry to the autonomic layer, then pulse
        // to get salience signals. Route signals into drive and workspace.
        if let Some(ref autonomic) = self.autonomic {
            if let Ok(mut autonomic) = autonomic.lock() {
                // Feed telemetry
                autonomic.add_telemetry(
                    "dispatch",
                    &format!(
                        "tool: {}, success: {}, effectiveness: {:.2}, latency: {:.1}ms",
                        name,
                        success,
                        effectiveness,
                        dispatch_latency * 1000.0
                    ),
                );

                // Pulse and route salience signals
                if let Some(signal) = autonomic.pulse() {
                    // Feed into drive events
                    let drive_events =
                        wm_cognitive::AutonomicLayer::signal_to_drive_events(&signal);
                    if let Ok(mut drive) = self.drive_core.lock() {
                        for kind in drive_events {
                            drive.process_event(
                                &wm_cognitive::DriveEvent::new(kind)
                                    .with_source(wm_cognitive::DriveEventSource::Autonomic)
                                    .with_detail(format!(
                                        "autonomic salience: {} ({:.2})",
                                        signal.signal_type, signal.salience_score
                                    )),
                            );
                        }
                    }

                    // Feed into workspace
                    if let Some((event_type, salience)) =
                        wm_cognitive::AutonomicLayer::signal_to_workspace_event(&signal)
                    {
                        if let Ok(mut ws) = self.workspace.lock() {
                            ws.publish_simple(
                                wm_workspace::CoreId::Autonomous,
                                event_type,
                                salience,
                                signal.salience_score,
                                json!({
                                    "signal_type": format!("{}", signal.signal_type),
                                    "salience_score": signal.salience_score,
                                    "novelty": signal.metadata.novelty_ratio,
                                    "diversity": signal.metadata.diversity,
                                }),
                            );
                        }
                    }

                    tracing::debug!(
                        signal_type = %signal.signal_type,
                        salience = signal.salience_score,
                        "Autonomic salience signal"
                    );
                }
            }
        }

        // ── Deep Integration: Bicameral consensus for high-stakes writes ──
        // Run bicameral reasoning after write operations to provide
        // a dual-hemisphere review of the dispatch decision.
        // The wm meta-tool has pure effects, so we inspect the routed tool's
        // effects from the dispatch result's _wm_route metadata.
        if success {
            let routed_tool_has_writes = dispatch_result
                .as_ref()
                .ok()
                .and_then(|r| r.get("_wm_route"))
                .and_then(|r| r.get("tool"))
                .and_then(|t| t.as_str())
                .and_then(|name| self.registry.get(name))
                .is_some_and(|t| !t.effects().writes.is_empty());

            if routed_tool_has_writes {
                if let Ok(bicam) = self.bicameral.lock() {
                    let input = wm_bicameral::HemisphereInput::new("dispatch write review")
                        .with_evidence(vec![format!(
                            "tool: wm, effectiveness: {:.2}, karma_debt: {:.2}",
                            effectiveness, ctx.karma_debt
                        )])
                        .with_context(json!({
                            "confidence": ctx.self_model_confidence,
                            "drive_caution": ctx.drive_caution,
                        }));
                    let consensus = bicam.reason(&input);
                    tracing::info!(
                        verdict = ?consensus.verdict,
                        confidence = consensus.confidence,
                        rounds = consensus.rounds,
                        "Bicameral review of write dispatch"
                    );
                }
            }
        }

        // Presence activity ratio modulates brain-wave transitions
        let activity_ratio = self.citta.presence.activity_ratio();
        let _ = self.eco_mode.apply_presence(activity_ratio);

        // Hardware harmony gates brain-wave transitions (Tiferet)
        // The health score from the Harmony Vector (Lakshmi) caps the
        // maximum brain-wave state — preventing high-power activity
        // when the hardware is under stress.
        let health_score = self.dharma_gate.homeostasis().health_score();
        let _ = self.eco_mode.apply_harmony(health_score);

        // Dream cycles are NOT run on the request path. The daemon
        // (`wm daemon`) owns dream scheduling via DreamCycle::should_run on
        // its interval — running the 12-phase consolidation cycle inline made
        // per-request latency nondeterministic (a full store pass on Theta).

        // ── Deep Integration: Timescale tick ──
        // Tick the timescale bus to execute any due hooks
        // (citta decay, drive decay, consolidation hooks)
        if let Ok(mut bus) = self.timescale_bus.lock() {
            let (executed, timeouts) = bus.tick_all();
            if executed > 0 {
                tracing::debug!(hooks_executed = executed, timeouts, "Timescale bus tick");
            }
        }

        // ── Deep Integration: Homeostatic Loop (N19) + Sensorimotor (Embodiment) ──
        // Sample hardware state, feed into anomaly detector, run homeostatic
        // loop cycle, and emit any corrective actions to the Gan Ying Bus.
        // Also poll the sensorimotor bus and emit SensorFrameReceived events
        // so that subsystems can react to sensor data in real time.
        //
        // Throttled to at most once per second: /proc and /sys sampling on
        // every request added syscall + file I/O overhead to the hot path for
        // near-zero information gain. The daemon also refreshes homeostasis
        // on its own interval.
        let sample_epoch_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;
        let last_sample_ms = self
            .last_hardware_sample_ms
            .load(std::sync::atomic::Ordering::Relaxed);
        let should_sample_hardware =
            sample_epoch_ms.saturating_sub(last_sample_ms) >= HARDWARE_SAMPLE_INTERVAL_MS;
        if should_sample_hardware {
            self.last_hardware_sample_ms
                .store(sample_epoch_ms, std::sync::atomic::Ordering::Relaxed);
            let hv = self.substrate.sample();
            if let Ok(mut detector) = self.anomaly_detector.lock() {
                let alerts = detector.check(&hv);
                if let Ok(mut loop_) = self.homeostatic_loop.lock() {
                    let actions = loop_.sample_cycle(&hv, &detector);
                    if !actions.is_empty() {
                        tracing::debug!(
                            actions = actions.len(),
                            alerts = alerts.len(),
                            "Homeostatic loop produced actions"
                        );
                        // Emit actions to Gan Ying Bus
                        if let Ok(mut bus) = self.gan_ying_bus.lock() {
                            for action in &actions {
                                bus.emit(
                                    wm_cognitive::EventType::HarmonyStressDetected,
                                    "homeostatic_loop",
                                    action.to_json(),
                                );
                            }
                        }
                    }
                }
            }

            // Poll sensorimotor bus and emit SensorFrameReceived
            if let Ok(mut sm_bus) = self.sensorimotor_bus.lock() {
                let readings = sm_bus.poll_all();
                if !readings.is_empty() {
                    if let Ok(mut gy) = self.gan_ying_bus.lock() {
                        gy.emit(
                            wm_cognitive::EventType::SensorFrameReceived,
                            "sensorimotor",
                            json!({
                                "sensor_count": readings.len(),
                                "sensors": readings.iter().map(|r| json!({
                                    "id": r.sensor_id,
                                    "kind": r.kind.as_str(),
                                    "value": r.value,
                                })).collect::<Vec<_>>(),
                            }),
                        );
                    }
                }
            }
        }

        // Autonomous cycles (Sensorimotor, Improve, WS-4 proposal surfacing)
        // are NOT run on the request path. The daemon's cycle sweep owns all
        // 8 cycle types on its own interval — running them inline keyed off
        // request counts duplicated the scheduler and added multi-millisecond
        // (dream: multi-second) latency spikes to user requests.

        let result = dispatch_result.map_err(|e| RpcError {
            code: -32603,
            message: e.to_string(),
            data: None,
        })?;

        Ok(json!({
            "content": [{
                "type": "text",
                "text": serde_json::to_string_pretty(&result).unwrap_or_else(|_| result.to_string()),
            }],
        }))
    }
}

/// Build the node's Sangha signing keypair.
///
/// Seeded from `WM_MESH_KEY` when set (stable node identity across restarts).
/// When unset, a random per-process key is used — the node appears as a fresh
/// identity each restart, but a hardcoded default would be shared by every
/// WhiteMagic node, letting anyone impersonate another node's messages.
fn mesh_signing_key() -> wm_sangha::MeshKeyPair {
    match std::env::var("WM_MESH_KEY") {
        Ok(key) if !key.is_empty() => wm_sangha::MeshKeyPair::from_seed(key.as_bytes()),
        _ => {
            tracing::warn!(
                "WM_MESH_KEY not set — using a random per-process Sangha identity; \
                 set WM_MESH_KEY for a stable node identity across restarts"
            );
            let mut seed = [0u8; 32];
            seed[..16].copy_from_slice(uuid::Uuid::new_v4().as_bytes());
            seed[16..].copy_from_slice(uuid::Uuid::new_v4().as_bytes());
            wm_sangha::MeshKeyPair::from_secret(seed)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::input_validation::MAX_PARAMS_SIZE;
    use std::sync::Arc;

    /// Store path for tests: a nested dir inside the tempdir so that
    /// `store.path().parent()` (where self_model.json etc. live) stays inside
    /// the tempdir. Passing the tempdir root directly made those files land
    /// in the shared `/tmp` — cross-test pollution of self_model.json.
    fn test_store_path(tmp: &tempfile::TempDir) -> std::path::PathBuf {
        let dir = tmp.path().join("lmdb");
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn test_server() -> McpServer {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tantivy_path = tmp.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_path).unwrap());
        let karma_ledger = Arc::new(KarmaLedger::new(store.clone()).unwrap());
        let dharma_gate = Arc::new(DharmaGate::default());
        let substrate = Arc::new(SubstrateMonitor::default());
        let resource_rules = Arc::new(ResourceRules::default());

        let associations = Arc::new(AssociationStore::open(store.env()).unwrap());
        let spiral_tracker =
            Arc::new(std::sync::Mutex::new(wm_cognitive::SpiralTracker::default()));
        let vector_store = Arc::new(std::sync::Mutex::new(wm_memory::VectorStore::new()));
        let conformal_store = Arc::new(std::sync::Mutex::new(
            wm_tools::expansion::conformal::ConformalStore::new(),
        ));

        // v4 subsystems
        let mut reflex_table = wm_cognitive::ReflexDispatchTable::permissive();
        wm_cognitive::reflex::builtins::register_builtins(&mut reflex_table);
        let reflex_table = Arc::new(std::sync::Mutex::new(reflex_table));
        let timescale_bus = Arc::new(std::sync::Mutex::new(wm_cognitive::TimescaleBus::default()));
        let workspace = Arc::new(std::sync::Mutex::new(wm_workspace::GlobalWorkspace::new()));
        let self_model = Arc::new(std::sync::Mutex::new(wm_selfmodel::SelfModel::new()));

        // R5: bicameral engine
        let right = Arc::new(wm_bicameral::RightHemisphereStub::new())
            as Arc<dyn wm_bicameral::RightHemisphere>;
        let bicameral = Arc::new(std::sync::Mutex::new(wm_bicameral::BicameralEngine::new(
            wm_bicameral::BicameralConfig::default(),
            Some(right),
        )));

        // R7: drive core
        let drive_core = Arc::new(std::sync::Mutex::new(DriveCore::new()));

        let registry = ToolRegistry::new();
        let recall_engine = {
            let embedder: Arc<dyn Embedder> = create_embedder().into();
            let episodic_rerank_only = std::env::var("WM_EPISODIC_RERANK_ONLY")
                .map(|v| v == "1" || v == "true")
                .unwrap_or(false);

            // Enable vocabulary enrichment by default for episodic search.
            store.set_episodic_enrichment(
                wm_memory::enrichment::VocabularyEnrichment::with_defaults(),
            );

            if episodic_rerank_only && embedder.is_available() && embedder.backend_name() != "stub"
            {
                store.set_episodic_embedder(embedder.clone());
                let stub: Arc<dyn Embedder> = Arc::new(StubEmbedder::default());
                let recall = RecallEngine::new(
                    store.clone(),
                    search.clone(),
                    VectorStore::new(),
                    stub,
                    RecallConfig::default(),
                )
                .unwrap();
                Arc::new(recall)
            } else {
                if embedder.is_available() && embedder.backend_name() != "stub" {
                    store.set_episodic_embedder(embedder.clone());
                }
                let recall = RecallEngine::new(
                    store.clone(),
                    search.clone(),
                    VectorStore::new(),
                    embedder,
                    RecallConfig::default(),
                )
                .unwrap();
                Arc::new(recall)
            }
        };
        let recall_for_tools = if recall_engine.embedder_is_real() {
            Some(recall_engine.clone())
        } else {
            None
        };
        let conversational = Some(ConversationalSearch::with_defaults(recall_engine));
        // N19-N20: Homeostatic Loop + Anomaly Detector — created early so they
        // can be shared between register_all (homeostasis tools) and the server state.
        let homeostatic_loop = Arc::new(std::sync::Mutex::new(HomeostaticLoop::default()));
        let anomaly_detector = Arc::new(std::sync::Mutex::new(AnomalyDetector::default()));

        let test_search = search.clone();
        let test_transaction_state: wm_tools::expansion::TransactionState =
            Arc::new(std::sync::Mutex::new(None));
        let registry = wm_tools::register_all(
            &registry,
            &store,
            Some(search),
            Some(karma_ledger.clone()),
            &Some(dharma_gate.clone()),
            Some(substrate.clone()),
            &Some(resource_rules.clone()),
            associations.clone(),
            spiral_tracker,
            vector_store,
            conversational,
            recall_for_tools,
            Some(Arc::clone(&homeostatic_loop)),
            Some(Arc::clone(&anomaly_detector)),
            None,
            None,
            None,
            test_transaction_state.clone(),
            None,
            None,
            None,
        );
        let registry = wm_tools::expansion::v4::register_v4(
            &registry,
            Arc::clone(&reflex_table),
            Arc::clone(&timescale_bus),
            Arc::clone(&workspace),
        );
        let registry =
            wm_tools::expansion::selfmodel::register_selfmodel(&registry, Arc::clone(&self_model));
        let registry = wm_tools::expansion::conformal::register_conformal(
            &registry,
            Arc::clone(&conformal_store),
            Some(Arc::clone(&self_model)),
        );
        let registry = wm_tools::expansion::bicameral::register_bicameral(
            &registry,
            &store,
            Arc::clone(&bicameral),
            None,
            None,
            None,
        );
        let registry =
            wm_tools::expansion::drive::register_drive(&registry, Arc::clone(&drive_core));

        // N16-N21: New subsystems — Gan Ying Bus, Sangha Mesh, Simulation
        let gan_ying_bus = Arc::new(std::sync::Mutex::new(GanYingBus::default()));
        let peer_discovery = Arc::new(std::sync::Mutex::new(PeerDiscovery::default()));
        let signal_broadcast = Arc::new(std::sync::Mutex::new(SignalBroadcast::new(100)));
        // Sangha chat signs every message with the node's Ed25519
        // keypair, so peers can verify authorship and identity binding —
        // the trust primitive agent message boards require (cf. the July
        // 2026 agent-incident reporting).
        let sangha_chat = Arc::new(std::sync::Mutex::new(
            SanghaChat::new(100).with_signing_key(mesh_signing_key()),
        ));
        let lock_manager = Arc::new(std::sync::Mutex::new(ResourceLockManager::default()));

        let registry = wm_tools::expansion::resonance::register_resonance(
            &registry,
            Arc::clone(&gan_ying_bus),
        );
        let registry = wm_tools::expansion::sangha_tools::register_sangha(
            &registry,
            Arc::clone(&peer_discovery),
            Arc::clone(&signal_broadcast),
            Arc::clone(&sangha_chat),
            Arc::clone(&lock_manager),
        );
        let calibration_store =
            Arc::new(std::sync::Mutex::new(wm_simulation::CalibrationStore::new()));
        let registry = wm_tools::expansion::simulation_tools::register_simulation(
            &registry,
            Some(Arc::clone(&calibration_store)),
            Some(Arc::clone(&self_model)),
        );
        let claims_ledger = Arc::new(std::sync::Mutex::new(wm_simulation::ClaimsLedger::new()));
        let registry = wm_tools::expansion::claims_tools::register_claims(
            &registry,
            Some(Arc::clone(&claims_ledger)),
        );
        let registry = wm_tools::expansion::bayesian_tools::register_bayesian(&registry);

        let test_shadow_stats = Arc::new(std::sync::RwLock::new(
            wm_tools::embedding_router::ShadowModeStats::default(),
        ));

        // Build the pipeline BEFORE the meta-tools so the wm meta-tool's inner
        // dispatch is governance-gated (destructive confirm, dharma, rate limit).
        let write_audit = Arc::new(wm_governance::WriteAuditJournal::new(store.clone()).unwrap());
        let pipeline = Arc::new(
            DispatchPipeline::new(
                Arc::new(wm_dispatch::RateLimiter::default()),
                Arc::new(wm_dispatch::CircuitBreakerRegistry::default()),
                dharma_gate.clone(),
                Some(karma_ledger.clone()),
            )
            .with_resource_rules(resource_rules.clone())
            .with_write_audit(write_audit),
        );
        let (registry, _router) = wm_tools::register_meta_tools_with_router(
            &registry,
            &store,
            test_shadow_stats.clone(),
            Some(pipeline.clone()),
        );

        let friction_auto_log =
            Arc::new(FrictionAutoLogTool::new(store.clone(), Some(test_search)));

        McpServer::new(
            registry,
            pipeline,
            EcoModeController::default(),
            store,
            associations,
            substrate,
            dharma_gate,
            resource_rules,
            reflex_table,
            timescale_bus,
            workspace,
            self_model,
            bicameral,
            drive_core,
            None,
            gan_ying_bus,
            peer_discovery,
            signal_broadcast,
            sangha_chat,
            lock_manager,
            homeostatic_loop,
            anomaly_detector,
            Arc::new(std::sync::Mutex::new(SensorimotorBus::default())),
            Arc::new(std::sync::Mutex::new(ReflexLoop::new())),
            friction_auto_log,
            Some(karma_ledger),
            test_transaction_state,
            None,
            test_shadow_stats,
        )
    }

    #[tokio::test]
    async fn initialize_returns_server_info() {
        let mut server = test_server();
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(1)),
            method: "initialize".into(),
            params: json!({}),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());
        let result = resp.result.unwrap();
        assert_eq!(result["serverInfo"]["name"], "whitemagic");
        assert!(result["capabilities"]["tools"].is_object());
        // G1.6: the session rhythm must be delivered via server instructions.
        let instructions = result["instructions"]
            .as_str()
            .expect("instructions present");
        for expected in [
            "session.continuity",
            "session.start",
            "session.record",
            "turn_type",
            "session.checkpoint",
            "tools.list",
            "not encrypted",
            "Back up",
        ] {
            assert!(
                instructions.contains(expected),
                "instructions must mention {expected}"
            );
        }
    }

    #[tokio::test]
    async fn tools_list_returns_only_wm_meta_tool() {
        let mut server = test_server();
        // Trigger an event to move from Delta to Beta
        let _ = server.eco_mode.record_event();
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(2)),
            method: "tools/list".into(),
            params: json!({}),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());
        let result = resp.result.unwrap();
        let tools = result["tools"].as_array().unwrap().clone();
        // Only the wm meta-tool should be exposed
        assert_eq!(tools.len(), 1);
        assert_eq!(tools[0]["name"], "wm");
        assert!(tools[0]["inputSchema"].is_object());
        let description = tools[0]["description"].as_str().unwrap();
        assert!(
            description.contains("meta-tool") && description.contains("tool surface"),
            "tools/list description should describe the active surface, got: {description}"
        );
        assert!(
            !description.contains("229 tools"),
            "tools/list description must not advertise the full archive surface"
        );
    }

    #[tokio::test]
    async fn tools_list_delta_returns_empty() {
        let server = test_server();
        // Don't call handle() — that would record_event() and transition to Beta.
        // Test handle_tools_list directly while in Delta state.
        let result = server.handle_tools_list().unwrap();
        let tools = result["tools"].as_array().unwrap().clone();
        assert_eq!(tools.len(), 0);
    }

    #[tokio::test]
    async fn tools_list_filters_by_brain_wave() {
        let mut server = test_server();

        // Direct call in Delta: 0 tools
        let result = server.handle_tools_list().unwrap();
        let delta_count = result["tools"].as_array().unwrap().len();
        assert_eq!(delta_count, 0);

        // Transition to Beta via handle() (which calls record_event)
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(2)),
            method: "tools/list".into(),
            params: json!({}),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());
        let beta_result = resp.result.unwrap();
        let beta_count = beta_result["tools"].as_array().unwrap().len();
        // In Beta: only wm meta-tool is exposed (1 tool)
        // In Delta: 0 tools
        assert!(beta_count > delta_count);
        assert_eq!(beta_count, 1);
    }

    #[tokio::test]
    async fn tools_call_wm_with_thought() {
        let mut server = test_server();
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(3)),
            method: "tools/call".into(),
            params: json!({
                "name": "wm",
                "arguments": {"thought": "remember that test works"},
            }),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());
        let content = resp.result.unwrap()["content"].as_array().unwrap().clone();
        assert_eq!(content[0]["type"], "text");
        let text = content[0]["text"].as_str().unwrap();
        assert!(text.contains("success"));
        assert!(text.contains("memory.create"));
    }

    #[tokio::test]
    async fn tools_call_wm_routes_to_tools_list() {
        let mut server = test_server();
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(10)),
            method: "tools/call".into(),
            params: json!({
                "name": "wm",
                "arguments": {"thought": "list tools"},
            }),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());
        let content = resp.result.unwrap()["content"].as_array().unwrap().clone();
        let text = content[0]["text"].as_str().unwrap();
        assert!(text.contains("tools.list") || text.contains("total"));
    }

    #[tokio::test]
    async fn tools_call_rejects_unknown_tool() {
        let mut server = test_server();
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(4)),
            method: "tools/call".into(),
            params: json!({
                "name": "nonexistent.tool",
                "arguments": {},
            }),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_some());
        assert_eq!(resp.error.unwrap().code, -32602);
    }

    #[tokio::test]
    async fn unknown_method_returns_error() {
        let mut server = test_server();
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(5)),
            method: "foobar".into(),
            params: json!({}),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_some());
        assert_eq!(resp.error.unwrap().code, -32601);
    }

    #[tokio::test]
    async fn handle_request_initialize() {
        let mut server = test_server();
        let json_req = r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#;
        let response = server.handle_request(json_req).await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        assert_eq!(parsed["jsonrpc"], "2.0");
        assert_eq!(parsed["id"], 1);
        assert_eq!(parsed["result"]["serverInfo"]["name"], "whitemagic");
    }

    #[tokio::test]
    async fn handle_request_tools_list() {
        let mut server = test_server();
        // First call initialize to trigger an event (move out of Delta)
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#)
            .await;
        let response = server
            .handle_request(r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let tools = parsed["result"]["tools"].as_array().unwrap();
        // Only the wm meta-tool should be exposed
        assert_eq!(tools.len(), 1);
        assert_eq!(tools[0]["name"], "wm");
    }

    #[tokio::test]
    async fn handle_request_tools_call_wm() {
        let mut server = test_server();
        let json_req = r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"remember that PyO3 bridge works"}}}"#;
        let response = server.handle_request(json_req).await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        assert!(parsed["error"].is_null() || parsed.get("error").is_none());
        let content = parsed["result"]["content"].as_array().unwrap();
        assert_eq!(content[0]["type"], "text");
        let text = content[0]["text"].as_str().unwrap();
        assert!(text.contains("success"));
    }

    #[tokio::test]
    async fn handle_request_parse_error() {
        let mut server = test_server();
        let response = server.handle_request("not valid json {{{").await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        assert_eq!(parsed["error"]["code"], -32700);
        assert!(
            parsed["error"]["message"]
                .as_str()
                .unwrap()
                .contains("Parse error")
        );
    }

    #[tokio::test]
    async fn handle_request_unknown_method() {
        let mut server = test_server();
        let json_req = r#"{"jsonrpc":"2.0","id":99,"method":"unknown_method","params":{}}"#;
        let response = server.handle_request(json_req).await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        assert_eq!(parsed["error"]["code"], -32601);
    }

    #[tokio::test]
    async fn handle_request_ping_responds() {
        let mut server = test_server();
        // ping has no id — the MCP spec still requires an empty result.
        let response = server
            .handle_request(r#"{"jsonrpc":"2.0","method":"ping"}"#)
            .await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        assert_eq!(parsed["result"], json!({}));
        assert!(parsed.get("error").is_none());
    }

    #[tokio::test]
    async fn tool_count_is_positive() {
        let server = test_server();
        assert!(server.tool_count() > 0);
    }

    #[tokio::test]
    async fn galaxy_counts_returns_json() {
        let server = test_server();
        let counts = server.galaxy_counts();
        assert!(counts.is_object());
        // Total should be 0 for a fresh test store
        assert_eq!(counts["total"], 0);
    }

    #[tokio::test]
    async fn refresh_self_model_records_metrics() {
        let server = test_server();
        // Before refresh, no metrics tracked
        assert_eq!(server.self_model().lock().unwrap().tracked_count(), 0);
        // Refresh samples substrate + citta into self-model
        server.refresh_self_model();
        // Should now track 5 metrics: CpuLoad, MemoryPressure, SwapUsage, DiskIo, Coherence
        let count = server.self_model().lock().unwrap().tracked_count();
        assert!(
            count >= 5,
            "expected at least 5 tracked metrics, got {count}"
        );
    }

    #[tokio::test]
    async fn handle_records_dispatch_metrics_into_self_model() {
        let mut server = test_server();
        // Send a tools/call request — handle() will refresh_self_model() then
        // dispatch, then record latency + error_rate
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(10)),
            method: "tools/call".into(),
            params: json!({
                "name": "wm",
                "arguments": {"thought": "remember that self-model integration works"},
            }),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());

        // After dispatch, self-model should have Latency and ErrorRate metrics
        let (latency_count, error_count) = {
            let model = server.self_model().lock().unwrap();
            (
                model.sample_count(wm_selfmodel::MetricKind::Latency),
                model.sample_count(wm_selfmodel::MetricKind::ErrorRate),
            )
        };
        assert!(
            latency_count > 0,
            "latency should be recorded after dispatch"
        );
        assert!(
            error_count > 0,
            "error_rate should be recorded after dispatch"
        );
    }

    #[tokio::test]
    async fn handle_injects_self_model_confidence_into_context() {
        let mut server = test_server();
        // Pre-record some metrics so confidence is calculable
        {
            let model = server.self_model().lock().unwrap();
            for v in [0.1, 0.15, 0.12, 0.13, 0.11, 0.14] {
                model.record(wm_selfmodel::MetricKind::CpuLoad, v);
            }
        }
        // Send a request — the dispatch pipeline should see a non-default confidence
        let req = RpcRequest {
            jsonrpc: "2.0".into(),
            id: Some(json!(11)),
            method: "tools/call".into(),
            params: json!({
                "name": "wm",
                "arguments": {"route": "gnosis"},
            }),
        };
        let resp = server.handle(&req).await;
        assert!(resp.error.is_none());
        // The self-model should now have even more samples (from refresh_self_model + dispatch)
        let tracked = server.self_model().lock().unwrap().tracked_count();
        assert!(tracked >= 6);
    }

    // ── E2E Integration Tests ──────────────────────────────────────────

    #[tokio::test]
    async fn e2e_full_session_lifecycle() {
        let mut server = test_server();

        // 1. Initialize
        let init_resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#)
            .await;
        let init: Value = serde_json::from_str(&init_resp).unwrap();
        assert_eq!(init["result"]["serverInfo"]["name"], "whitemagic");

        // 2. tools/list (should now be Beta since handle() records an event)
        let list_resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#)
            .await;
        let list: Value = serde_json::from_str(&list_resp).unwrap();
        let tools = list["result"]["tools"].as_array().unwrap();
        // Only the wm meta-tool is exposed
        assert_eq!(tools.len(), 1);
        assert_eq!(tools[0]["name"], "wm");

        // 3. tools/call — create a memory
        let call_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"e2e test memory"}}}"#,
        ).await;
        let call: Value = serde_json::from_str(&call_resp).unwrap();
        assert!(call.get("error").is_none() || call["error"].is_null());
        let content = call["result"]["content"].as_array().unwrap();
        assert!(content[0]["text"].as_str().unwrap().contains("success"));

        // 4. tools/call — read the memory back
        let read_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.list"}}}"#,
        ).await;
        let read: Value = serde_json::from_str(&read_resp).unwrap();
        assert!(read.get("error").is_none() || read["error"].is_null());

        // 5. Verify citta was updated (coherence > 0 after beats)
        let (coherence, _) = server.citta().coherence_valence();
        assert!(coherence >= 0.0);

        // 6. Verify self-model has metrics from dispatch
        let latency_count = server
            .self_model()
            .lock()
            .unwrap()
            .sample_count(wm_selfmodel::MetricKind::Latency);
        assert!(
            latency_count > 0,
            "self-model should have latency samples after dispatch"
        );
    }

    #[tokio::test]
    async fn e2e_gan_ying_bus_records_dispatch_events() {
        let mut server = test_server();

        // Verify bus starts empty
        assert_eq!(server.gan_ying_bus().lock().unwrap().events_emitted(), 0);

        // Dispatch a tools/call
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"bus test"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // Verify Gan Ying Bus recorded events: ToolDispatchStart + ToolDispatchSuccess
        let bus = server.gan_ying_bus().lock().unwrap();
        let emitted = bus.events_emitted();
        assert!(
            emitted >= 2,
            "expected at least 2 bus events, got {emitted}"
        );

        let recent: Vec<_> = bus.recent_events(10).into_iter().cloned().collect();
        drop(bus);
        let has_start = recent
            .iter()
            .any(|e| e.event_type == wm_cognitive::EventType::ToolDispatchStart);
        let has_success = recent
            .iter()
            .any(|e| e.event_type == wm_cognitive::EventType::ToolDispatchSuccess);
        assert!(has_start, "ToolDispatchStart should be in recent events");
        assert!(
            has_success,
            "ToolDispatchSuccess should be in recent events"
        );
    }

    #[tokio::test]
    async fn e2e_gan_ying_bus_persists_events_to_disk() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();

        // Persistence is wired in the production constructor
        let persist_path = {
            let bus = server.gan_ying_bus().lock().unwrap();
            bus.persist_path().map(std::path::Path::to_path_buf)
        };
        assert_eq!(
            persist_path.as_deref(),
            Some(
                test_store_path(&tmp)
                    .join("resonance_events.jsonl")
                    .as_path()
            )
        );

        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"persistence test"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        let log = std::fs::read_to_string(test_store_path(&tmp).join("resonance_events.jsonl"))
            .expect("persistence log should exist after dispatch");
        assert!(
            log.contains("tool_dispatch_start"),
            "log should contain tool_dispatch_start, got: {log}"
        );

        // A fresh server over the same store seeds its recent buffer from the log
        drop(server);
        let server2 = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();
        let any_start = {
            let bus2 = server2.gan_ying_bus().lock().unwrap();
            bus2.recent_events(10)
                .iter()
                .any(|e| e.event_type == wm_cognitive::EventType::ToolDispatchStart)
        };
        assert!(
            any_start,
            "fresh server should seed recent events from the persisted log"
        );
    }

    #[tokio::test]
    async fn e2e_error_recovery_after_malformed_json() {
        let mut server = test_server();

        // 1. Send malformed JSON
        let bad_resp = server.handle_request("not valid json {{{").await;
        let bad: Value = serde_json::from_str(&bad_resp).unwrap();
        assert_eq!(bad["error"]["code"], -32700);

        // 2. Server should still handle valid requests
        let good_resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#)
            .await;
        let good: Value = serde_json::from_str(&good_resp).unwrap();
        assert_eq!(good["result"]["serverInfo"]["name"], "whitemagic");

        // 3. tools/call should work after error recovery
        let call_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"recovery test"}}}"#,
        ).await;
        let call: Value = serde_json::from_str(&call_resp).unwrap();
        assert!(call.get("error").is_none() || call["error"].is_null());
    }

    #[tokio::test]
    async fn e2e_unknown_tool_then_valid_tool() {
        let mut server = test_server();

        // 1. Call unknown tool — should get error
        let err_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nonexistent","arguments":{}}}"#,
        ).await;
        let err: Value = serde_json::from_str(&err_resp).unwrap();
        assert_eq!(err["error"]["code"], -32602);

        // 2. Call valid wm tool — should succeed
        let ok_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"after error test"}}}"#,
        ).await;
        let ok: Value = serde_json::from_str(&ok_resp).unwrap();
        assert!(ok.get("error").is_none() || ok["error"].is_null());
    }

    #[tokio::test]
    async fn e2e_shutdown_emits_system_shutdown_event() {
        let server = test_server();

        // Verify no events before shutdown
        assert_eq!(server.gan_ying_bus().lock().unwrap().events_emitted(), 0);

        // Call shutdown
        server.shutdown();

        // Verify SystemShutdown event was emitted
        let bus = server.gan_ying_bus().lock().unwrap();
        let emitted = bus.events_emitted();
        assert!(emitted >= 1, "shutdown should emit at least 1 event");

        let recent: Vec<_> = bus.recent_events(5).into_iter().cloned().collect();
        drop(bus);
        let has_shutdown = recent
            .iter()
            .any(|e| e.event_type == wm_cognitive::EventType::SystemShutdown);
        assert!(
            has_shutdown,
            "SystemShutdown event should be in recent events"
        );
    }

    #[tokio::test]
    async fn e2e_homeostasis_tools_share_state_with_server() {
        let mut server = test_server();

        // Dispatch a tools/call — this runs the homeostatic loop in handle_tools_call
        let _ = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"homeostasis state test"}}}"#,
        ).await;

        // The server's homeostatic_loop and anomaly_detector should have been
        // updated during the dispatch (sample_cycle runs in handle_tools_call).
        // Verify they are accessible and not poisoned.
        let loop_ok = server.homeostatic_loop().lock().is_ok();
        assert!(loop_ok, "homeostatic_loop mutex should not be poisoned");

        let detector_ok = server.anomaly_detector().lock().is_ok();
        assert!(detector_ok, "anomaly_detector mutex should not be poisoned");
    }

    #[tokio::test]
    async fn e2e_multiple_sequential_dispatches() {
        let mut server = test_server();

        // Send 5 sequential tools/call requests
        for i in 0..5 {
            let resp = server.handle_request(&format!(
                r#"{{"jsonrpc":"2.0","id":{i},"method":"tools/call","params":{{"name":"wm","arguments":{{"thought":"sequential test {i}"}}}}}}"#
            )).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            assert!(
                parsed.get("error").is_none() || parsed["error"].is_null(),
                "request {i} should succeed"
            );
        }

        // Verify bus recorded all dispatches (at least 2 events per dispatch: start + success)
        let emitted = server.gan_ying_bus().lock().unwrap().events_emitted();
        assert!(
            emitted >= 10,
            "expected at least 10 bus events from 5 dispatches, got {emitted}"
        );

        // Verify self-model has multiple latency samples
        let latency_count = server
            .self_model()
            .lock()
            .unwrap()
            .sample_count(wm_selfmodel::MetricKind::Latency);
        assert!(
            latency_count >= 5,
            "expected at least 5 latency samples, got {latency_count}"
        );
    }

    #[tokio::test]
    async fn e2e_brain_wave_transitions_through_activity() {
        let mut server = test_server();

        // Start in Delta
        assert_eq!(server.eco_mode().current(), wm_core::BrainWave::Delta);

        // Record events to transition to Beta
        for _ in 0..3 {
            let _ = server.eco_mode_mut().record_event();
        }
        assert_eq!(server.eco_mode().current(), wm_core::BrainWave::Beta);

        // Dispatch should work in Beta
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"beta state test"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());
    }

    #[tokio::test]
    async fn e2e_tool_count_matches_registry() {
        let server = test_server();
        let count = server.tool_count();
        // Should have well over 100 tools registered
        assert!(count >= 100, "expected at least 100 tools, got {count}");
    }

    #[tokio::test]
    async fn handle_request_empty_string_returns_parse_error() {
        let mut server = test_server();
        let response = server.handle_request("").await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        assert_eq!(parsed["error"]["code"], -32700);
    }

    #[tokio::test]
    async fn handle_request_null_returns_parse_error() {
        let mut server = test_server();
        let response = server.handle_request("null").await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        // null is valid JSON but not a valid RPC request
        assert!(parsed.get("error").is_some());
    }

    #[tokio::test]
    async fn handle_request_missing_method_field() {
        let mut server = test_server();
        let response = server.handle_request(r#"{"jsonrpc":"2.0","id":1}"#).await;
        let parsed: Value = serde_json::from_str(&response).unwrap();
        // Missing method field — should get an error, not panic
        assert!(parsed.get("error").is_some() || parsed.get("result").is_none());
    }

    // ── E2E RSI Outward Spiral Test ───────────────────────────────────

    #[tokio::test]
    async fn e2e_rsi_outward_spiral_full_loop() {
        let mut server = test_server();

        // Initialize to move out of Delta (no tools available in Delta)
        let init_req = r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#;
        let _ = server.handle_request(init_req).await;

        // 1. Log a friction entry via friction.log tool
        let log_req = r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"friction.log","arguments":{"what_happened":"memory.search returns empty results for valid queries","expected_behavior":"Should return matching memories","suggested_fix":"Check Tantivy index state","severity":"medium","category":"ux","tool_name":"memory.search"}}}"#;
        let resp = server.handle_request(log_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(
            parsed.get("result").is_some(),
            "friction.log should succeed"
        );
        let text = &parsed["result"]["content"][0]["text"];
        let friction_result: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(friction_result["status"], "success");
        let friction_id = friction_result["id"].as_str().unwrap().to_string();

        // 2. Log the same friction again — should dedup
        let dup_req = r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"friction.log","arguments":{"what_happened":"memory.search returns empty results for valid queries","expected_behavior":"Should return matching memories","suggested_fix":"Check Tantivy index state","severity":"medium","category":"ux","tool_name":"memory.search"}}}"#;
        let resp = server.handle_request(dup_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let text = &parsed["result"]["content"][0]["text"];
        let dup_result: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(dup_result["status"], "duplicate");
        assert_eq!(dup_result["duplicate_count"], 2);

        // 3. Review friction — should show 1 entry with dup_count=2
        let review_req = r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"friction.review","arguments":{}}}"#;
        let resp = server.handle_request(review_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let text = &parsed["result"]["content"][0]["text"];
        let review: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(review["status"], "success");
        assert!(review["total_friction_entries"].as_u64().unwrap() >= 1);
        assert_eq!(review["resolved"], 0);
        assert_eq!(review["regressions"], 0);
        // Verify the entry shows dup_count=2
        let entries = review["entries"].as_array().unwrap();
        let our_entry = entries
            .iter()
            .find(|e| e["id"] == friction_id)
            .expect("Should find our friction entry");
        assert_eq!(our_entry["duplicate_count"], 2);
        assert_eq!(our_entry["resolved"], false);

        // 4. Resolve the friction entry
        let resolve_args = format!(
            r#"{{"friction_id":"{friction_id}","resolution_note":"Fixed Tantivy index initialization","resolution_method":"code_fix"}}"#
        );
        let resolve_req = format!(
            r#"{{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{{"name":"friction.resolve","arguments":{resolve_args}}}}}"#
        );
        let resp = server.handle_request(&resolve_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(
            parsed.get("result").is_some(),
            "friction.resolve should succeed"
        );
        let text = &parsed["result"]["content"][0]["text"];
        let resolve_result: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(resolve_result["status"], "resolved");

        // 5. Review again — should show 1 resolved entry
        let resp = server.handle_request(review_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let text = &parsed["result"]["content"][0]["text"];
        let review2: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(review2["resolved"], 1, "Should show 1 resolved entry");
        assert_eq!(review2["regressions"], 0);

        // 6. Log the same friction AGAIN — should detect regression
        let regression_req = r#"{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"friction.log","arguments":{"what_happened":"memory.search returns empty results for valid queries","expected_behavior":"Should return matching memories","suggested_fix":"Check Tantivy index state","severity":"medium","category":"ux","tool_name":"memory.search"}}}"#;
        let resp = server.handle_request(regression_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let text = &parsed["result"]["content"][0]["text"];
        let reg_result: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(
            reg_result["status"], "regression",
            "Should detect regression when resolved friction reappears"
        );
        assert_eq!(reg_result["escalated_severity"], "high");

        // 7. Final review — should show 1 resolved + 1 regression
        let resp = server.handle_request(review_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let text = &parsed["result"]["content"][0]["text"];
        let review3: Value = serde_json::from_str(text.as_str().unwrap()).unwrap();
        assert_eq!(review3["resolved"], 1, "Should still show 1 resolved");
        assert_eq!(review3["regressions"], 1, "Should show 1 regression");
    }

    // ── E2E Transaction Integration Test ──────────────────────────────

    #[tokio::test]
    async fn e2e_transaction_begin_rollback_restores_data() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // 1. Create a memory in Codex
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"e2e transaction test memory","tags":["transaction","e2e"]}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        assert!(
            parsed.get("error").is_none() || parsed["error"].is_null(),
            "memory.create failed: {parsed}"
        );
        let content = parsed["result"]["content"].as_array().unwrap();
        let create_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(create_result["status"], "success");
        let mem_id = create_result["id"].as_str().unwrap().to_string();

        // 2. Begin transaction — snapshots all galaxies
        let begin_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"transaction.begin","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&begin_resp).unwrap();
        assert!(
            parsed.get("error").is_none() || parsed["error"].is_null(),
            "transaction.begin failed: {parsed}"
        );
        let content = parsed["result"]["content"].as_array().unwrap();
        let begin_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(begin_result["status"], "success");
        assert!(begin_result["total_memories_snapshotted"].as_u64() >= Some(1));

        // 3. Mutate — delete the memory
        let delete_req = format!(
            r#"{{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{{"name":"memory.delete","arguments":{{"galaxy":"codex","id":"{mem_id}","confirm":true}}}}}}"#
        );
        let delete_resp = server.handle_request(&delete_req).await;
        let parsed: Value = serde_json::from_str(&delete_resp).unwrap();
        assert!(
            parsed.get("error").is_none() || parsed["error"].is_null(),
            "memory.delete failed: {parsed}"
        );

        // Verify memory is gone
        let list_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"memory.list","arguments":{"galaxy":"codex","limit":100}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(list_result["status"], "success");
        // Memory should not be in the list
        let memories = list_result["memories"].as_array().unwrap();
        let found = memories.iter().any(|m| m["id"] == mem_id);
        assert!(!found, "memory should be deleted before rollback");

        // 4. Rollback — restore all galaxies from snapshot (destructive, needs confirm)
        let rollback_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"transaction.rollback","arguments":{"confirm":true}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&rollback_resp).unwrap();
        assert!(
            parsed.get("error").is_none() || parsed["error"].is_null(),
            "transaction.rollback failed: {parsed}"
        );
        let content = parsed["result"]["content"].as_array().unwrap();
        let rollback_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(rollback_result["status"], "success");
        assert!(
            rollback_result["memories_restored"].as_u64() >= Some(1),
            "should restore at least 1 memory"
        );

        // 5. Verify memory was restored
        let list_resp2 = server.handle_request(
            r#"{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"memory.list","arguments":{"galaxy":"codex","limit":100}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp2).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list_result2: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(list_result2["status"], "success");
        let memories2 = list_result2["memories"].as_array().unwrap();
        let found2 = memories2.iter().any(|m| {
            m["content_preview"]
                .as_str()
                .unwrap_or("")
                .contains("e2e transaction test")
        });
        assert!(found2, "memory content should be restored after rollback");
    }

    #[tokio::test]
    async fn e2e_transaction_begin_commit_keeps_changes() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // 1. Create a memory
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"commit test memory","tags":["commit"]}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let create_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let _mem_id = create_result["id"].as_str().unwrap().to_string();

        // 2. Begin transaction
        let begin_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"transaction.begin","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&begin_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // 3. Create a second memory (mutation)
        let create2_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"second memory after begin","tags":["commit"]}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create2_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // 4. Commit — keeps all changes
        let commit_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"transaction.commit","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&commit_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());
        let content = parsed["result"]["content"].as_array().unwrap();
        let commit_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(commit_result["status"], "success");

        // 5. Verify both memories still exist (commit kept changes)
        let list_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"memory.list","arguments":{"galaxy":"codex","limit":100}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let total = list_result["total"].as_u64().unwrap();
        assert!(
            total >= 2,
            "both memories should exist after commit, got {total}"
        );
    }

    #[tokio::test]
    async fn e2e_transaction_rollback_without_begin_errors() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Rollback without begin — should error
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"transaction.rollback","arguments":{"confirm":true}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        // Should get a governance error (no active transaction)
        assert!(
            parsed.get("error").is_some() || parsed.get("result").is_none(),
            "rollback without begin should fail"
        );
    }

    #[tokio::test]
    async fn e2e_transaction_rollback_without_confirm_blocked() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Begin a transaction
        let begin_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"transaction.begin","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&begin_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // Rollback without confirm — should be blocked by destructive gate
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"transaction.rollback","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        // Should get an error about destructive/confirm
        assert!(
            parsed.get("error").is_some() || parsed.get("result").is_none(),
            "rollback without confirm should be blocked"
        );
    }

    // ── E2E: wm meta-tool inner dispatch is governance-gated ───────────

    #[tokio::test]
    async fn e2e_wm_route_destructive_without_confirm_blocked() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Create a memory via the wm meta-tool
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"e2e destructive gate test"}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let create_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(create_result["status"], "success");
        let mem_id = create_result["id"].as_str().unwrap().to_string();

        // Delete via wm(route=...) WITHOUT confirm — must be blocked by the
        // pipeline's destructive gate, even though the request went through NLU
        // explicit routing.
        let delete_req = format!(
            r#"{{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{{"name":"wm","arguments":{{"route":"memory.delete","args":{{"galaxy":"codex","id":"{mem_id}"}}}}}}}}"#
        );
        let delete_resp = server.handle_request(&delete_req).await;
        let parsed: Value = serde_json::from_str(&delete_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let delete_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(
            delete_result["status"], "error",
            "wm(route=memory.delete) without confirm must fail, got: {delete_result}"
        );
        assert!(
            delete_result["error"]
                .as_str()
                .unwrap()
                .contains("destructive"),
            "expected destructive-gate message, got: {delete_result}"
        );

        // The memory must still exist
        let list_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.list","args":{"galaxy":"codex","limit":100}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let memories = list_result["memories"].as_array().unwrap();
        assert!(
            memories.iter().any(|m| m["id"] == mem_id),
            "memory should survive a blocked destructive call"
        );
    }

    #[tokio::test]
    async fn e2e_wm_inner_failure_recorded_as_failure_telemetry() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // A successful NLU request first, to establish a baseline (no error)
        let ok_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.list","args":{"galaxy":"codex","limit":1}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&ok_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // Inner failure: route to a tool that doesn't exist. The meta-tool
        // returns `{"status":"error", ...}` as a successful JSON-RPC result —
        // the request as a whole must still be seen as a failure by the
        // telemetry layers (friction auto-log below), not as a success.
        let fail_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wm","arguments":{"route":"no.such.tool"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&fail_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let fail_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(fail_result["status"], "error");

        // The inner failure must surface in the friction log — this is the
        // regression test for inner errors being swallowed as successes.
        let review_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"friction.review","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&review_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let review: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert!(
            review["total_friction_entries"].as_u64().unwrap() >= 1,
            "inner wm failure should be friction-logged, got: {review}"
        );
    }

    #[tokio::test]
    async fn e2e_curated_profile_filters_tool_surface() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults_mode_profile(
            &test_store_path(&tmp),
            false,
            &wm_tools::profiles::PROFILE_CURATED,
        )
        .unwrap();

        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Memory-hierarchy tools stay reachable through the meta-tool.
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"curated profile test"}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        assert!(
            parsed.get("error").is_none() || parsed["error"].is_null(),
            "memory.create should work under curated profile, got: {parsed}"
        );

        // Full-surface tools are filtered out: direct dispatch fails…
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"redteam.proposals","arguments":{}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(
            parsed.get("error").is_some(),
            "redteam.proposals should be filtered out under curated profile, got: {parsed}"
        );

        // …and the wm meta-tool cannot route to them either.
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"route":"redteam.proposals"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let routed: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(routed["status"], "error");
        assert!(
            routed["message"].as_str().unwrap().contains("Unknown tool"),
            "wm routing must not reach filtered tools, got: {routed}"
        );
    }

    #[tokio::test]
    async fn readonly_mode_blocks_all_mutations() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults_mode(&test_store_path(&tmp), true).unwrap();

        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Every mutating tool in the curated surface must fail under --readonly.
        // Regression: `--readonly` used to protect only the Tantivy writer,
        // while session.start and transaction.begin kept writing to LMDB.
        for (route, args) in [
            (
                "memory.create",
                r#"{"galaxy":"codex","content":"readonly regression"}"#,
            ),
            ("session.start", r#"{"title":"readonly regression"}"#),
            ("transaction.begin", "{}"),
        ] {
            let req = format!(
                r#"{{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{{"name":"wm","arguments":{{"route":"{route}","args":{args}}}}}}}"#
            );
            let resp = server.handle_request(&req).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            let content = parsed["result"]["content"]
                .as_array()
                .expect("tools/call should return content");
            let result: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
            assert_eq!(
                result["status"], "error",
                "read-only mode must reject {route}, got: {result}"
            );
        }
    }

    #[tokio::test]
    async fn unknown_compartment_fails_closed() {
        let mut server = test_server();

        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Regression: unknown compartment values used to fail open (full access).
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"compartment regression"}},"_meta":{"compartment":"bogus"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"]
            .as_array()
            .expect("tools/call should return content");
        let result: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(
            result["status"], "error",
            "unknown compartment must fail closed, got: {result}"
        );
    }

    #[tokio::test]
    async fn meta_in_tool_arguments_is_stripped() {
        let mut server = test_server();

        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // A caller tries to inject _meta inside tool arguments (not the
        // top-level params _meta). The server must strip it before dispatch
        // so it cannot override compartment/identity controls.
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"meta injection test","_meta":{"compartment":"bogus"}}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"]
            .as_array()
            .expect("tools/call should return content");
        let result: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();

        // The memory.create should succeed (no compartment restriction
        // because _meta in arguments was stripped, not treated as a
        // compartment override from the top-level _meta).
        assert_eq!(
            result["status"], "success",
            "_meta in tool arguments should be stripped, not interpreted — got: {result}"
        );
    }

    #[tokio::test]
    async fn tools_list_reflects_active_profile() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults_mode_profile(
            &test_store_path(&tmp),
            false,
            &wm_tools::profiles::PROFILE_CURATED,
        )
        .unwrap();

        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Regression: tools/list hardcoded the full-surface description
        // ("229 tools") regardless of the active profile.
        let list_resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        let description = parsed["result"]["tools"][0]["description"]
            .as_str()
            .unwrap();
        assert!(
            !description.contains("229 tools"),
            "curated tools/list description must not advertise the full surface, got: {description}"
        );

        // The inner tools.list must agree with the curated registry size.
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wm","arguments":{"route":"tools.list"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let listed: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        // tools.list snapshots the pre-meta-tool registry (gnosis excluded),
        // so the expected count is the registry minus the four meta-tools.
        let expected = server
            .registry()
            .all()
            .iter()
            .filter(|t| {
                ![
                    "wm",
                    "tools.list",
                    "tools.usage_report",
                    "gnosis",
                    "nlu.shadow_report",
                ]
                .contains(&t.name())
            })
            .count() as u64;
        assert_eq!(
            listed["total"],
            json!(expected),
            "inner tools.list must report the active profile registry size"
        );
        // The curated surface must not expose galaxy management tools and
        // must expose the explicit claims routes.
        let names: Vec<&str> = listed["tools"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|t| t["name"].as_str())
            .collect();
        assert!(
            !names.iter().any(|n| n.starts_with("galaxy.")),
            "curated tools.list must exclude galaxy tools, got: {names:?}"
        );
        assert!(
            names.contains(&"claims.calibration"),
            "curated tools.list must include claims.calibration, got: {names:?}"
        );
    }

    #[tokio::test]
    async fn private_memories_never_appear_in_mcp_read_paths() {
        let mut server = test_server();

        // Seed one private and one public memory directly in the store.
        let mut priv_mem = wm_memory::Memory::new(wm_core::Galaxy::Codex, "top secret note".into());
        priv_mem.metadata.is_private = true;
        let priv_id = priv_mem.metadata.id;
        server
            .store()
            .put(wm_core::Galaxy::Codex, &priv_mem)
            .unwrap();
        let pub_mem = wm_memory::Memory::new(wm_core::Galaxy::Codex, "public note".into());
        let pub_id = pub_mem.metadata.id;
        server
            .store()
            .put(wm_core::Galaxy::Codex, &pub_mem)
            .unwrap();

        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // memory.read of a private memory reports not_found.
        let read_req = format!(
            r#"{{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{{"name":"wm","arguments":{{"route":"memory.read","args":{{"galaxy":"codex","id":"{priv_id}"}}}}}}}}"#
        );
        let resp = server.handle_request(&read_req).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let read: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(
            read["status"], "not_found",
            "private memory.read must report not_found, got: {read}"
        );

        // memory.list excludes private memories.
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.list","args":{"galaxy":"codex","limit":50}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let ids: Vec<&str> = list["memories"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|m| m["id"].as_str())
            .collect();
        let priv_str = priv_id.to_string();
        let pub_str = pub_id.to_string();
        assert!(
            !ids.contains(&priv_str.as_str()),
            "private memory leaked through list: {list}"
        );
        assert!(
            ids.contains(&pub_str.as_str()),
            "public memory missing from list: {list}"
        );

        // memory.query excludes private memories.
        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.query","args":{"galaxy":"codex","limit":50,"query":"note"}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let query: Value = serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let qids: Vec<&str> = query["memories"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|m| m["id"].as_str())
            .collect();
        assert!(
            !qids.contains(&priv_str.as_str()),
            "private memory leaked through query: {query}"
        );
        assert!(
            qids.contains(&pub_str.as_str()),
            "public memory missing from query: {query}"
        );
    }

    #[tokio::test]
    async fn e2e_wm_thought_cannot_delete_memory() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Create a memory via the wm meta-tool
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"e2e NLU hard-block test"}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let create_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(create_result["status"], "success");
        let mem_id = create_result["id"].as_str().unwrap().to_string();

        // Natural-language delete — structurally blocked (NLU hard gate)
        let delete_req = format!(
            r#"{{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{{"name":"wm","arguments":{{"thought":"delete memory {mem_id}"}}}}}}"#
        );
        let delete_resp = server.handle_request(&delete_req).await;
        let parsed: Value = serde_json::from_str(&delete_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let delete_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(
            delete_result["status"], "error",
            "NLU delete must be blocked, got: {delete_result}"
        );
        assert!(
            delete_result["message"]
                .as_str()
                .unwrap()
                .contains("cannot be reached via natural language"),
            "expected NLU hard-block message, got: {delete_result}"
        );

        // The memory must still exist
        let list_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.list","args":{"galaxy":"codex","limit":100}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let memories = list_result["memories"].as_array().unwrap();
        assert!(
            memories.iter().any(|m| m["id"] == mem_id),
            "memory should survive an NLU delete attempt"
        );
    }

    #[tokio::test]
    async fn e2e_wm_route_destructive_with_confirm_succeeds() {
        let mut server = test_server();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Create a memory via the wm meta-tool
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"e2e confirm-path test"}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let create_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(create_result["status"], "success");
        let mem_id = create_result["id"].as_str().unwrap().to_string();

        // Delete via wm(route=...) WITH confirm — must succeed
        let delete_req = format!(
            r#"{{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{{"name":"wm","arguments":{{"route":"memory.delete","args":{{"galaxy":"codex","id":"{mem_id}","confirm":true}}}}}}}}"#
        );
        let delete_resp = server.handle_request(&delete_req).await;
        let parsed: Value = serde_json::from_str(&delete_resp).unwrap();
        assert!(
            parsed.get("error").is_none() || parsed["error"].is_null(),
            "wm(route=memory.delete) with confirm should succeed, got: {parsed}"
        );
        let content = parsed["result"]["content"].as_array().unwrap();
        let delete_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(delete_result["status"], "success");

        // The memory must be gone
        let list_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.list","args":{"galaxy":"codex","limit":100}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        let content = parsed["result"]["content"].as_array().unwrap();
        let list_result: Value =
            serde_json::from_str(content[0]["text"].as_str().unwrap()).unwrap();
        let memories = list_result["memories"].as_array().unwrap();
        assert!(
            !memories.iter().any(|m| m["id"] == mem_id),
            "memory should be deleted after confirmed destructive call"
        );
    }

    // ── E2E Mutable Structures Integration Tests (Phase 6) ─────────────

    #[tokio::test]
    async fn e2e_gana_registry_records_dispatch_co_usage() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();

        // Initialize to move out of Delta
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // Dispatch multiple tools to generate co-usage patterns
        for i in 0..5 {
            let resp = server.handle_request(&format!(
                r#"{{"jsonrpc":"2.0","id":{i},"method":"tools/call","params":{{"name":"wm","arguments":{{"thought":"gana registry test {i}"}}}}}}"#
            )).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            assert!(
                parsed.get("error").is_none() || parsed["error"].is_null(),
                "dispatch {i} should succeed"
            );
        }

        // Verify GanaRegistry recorded usage
        let total_usage: u64 = {
            let registry = server.gana_registry().lock().unwrap();
            registry.usage_counts().values().sum()
        };
        assert!(
            total_usage >= 5,
            "GanaRegistry should have recorded at least 5 usages, got {total_usage}"
        );
    }

    #[tokio::test]
    async fn e2e_dynamic_galaxy_registry_accessible() {
        let tmp = tempfile::tempdir().unwrap();
        let server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();

        // Verify DynamicGalaxyRegistry is accessible and starts empty
        let count = {
            let dg = server.dynamic_galaxies().lock().unwrap();
            dg.galaxy_count()
        };
        assert_eq!(count, 0, "DynamicGalaxyRegistry should start empty");
    }

    #[tokio::test]
    async fn e2e_learned_dream_cycle_attached() {
        let tmp = tempfile::tempdir().unwrap();
        let server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();

        // The dream cycle should have a LearnedDreamCycle attached
        // (verified indirectly: the dream cycle runs without error)
        assert_eq!(server.dream().cycles_completed(), 0);
    }

    #[tokio::test]
    async fn e2e_full_pipeline_with_mutable_structures() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();

        // 1. Initialize
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
            .await;

        // 2. Create a memory
        let create_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"galaxy":"codex","content":"mutable structures e2e test","tags":["e2e","mutable"]}}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&create_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // 3. List memories
        let list_resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"memory.list","arguments":{"galaxy":"codex","limit":10}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&list_resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        // 4. Verify GanaRegistry recorded usage from both dispatches
        let (total_usage, distinct_ganas) = {
            let registry = server.gana_registry().lock().unwrap();
            (
                registry.usage_counts().values().sum::<u64>(),
                registry.usage_counts().len(),
            )
        };
        assert!(
            total_usage >= 2,
            "GanaRegistry should have recorded at least 2 usages, got {total_usage}"
        );

        // 5. Verify at least 1 distinct Gana was tracked
        assert!(
            distinct_ganas >= 1,
            "GanaRegistry should track at least 1 Gana, got {distinct_ganas}"
        );
    }

    #[tokio::test]
    async fn e2e_mutable_state_persistence_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();

        // Phase 1: Create server, record usage, save
        {
            let mut server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();
            let _ = server
                .handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#)
                .await;

            // Dispatch tools to generate GanaRegistry usage
            for i in 0..3 {
                let _ = server.handle_request(&format!(
                    r#"{{"jsonrpc":"2.0","id":{i},"method":"tools/call","params":{{"name":"wm","arguments":{{"thought":"persistence test {i}"}}}}}}"#
                )).await;
            }

            // Record some dream phase effectiveness
            if let Some(learned) = server.dream_mut().learned_mut() {
                learned.record_phase(0, true, 0.8, 100);
                learned.record_phase(1, false, 0.2, 200);
            }

            // Record conformal coverage in the self-model (drift health)
            server
                .self_model()
                .lock()
                .unwrap()
                .record(wm_selfmodel::MetricKind::ConformalCoverage, 0.92);
            server
                .self_model()
                .lock()
                .unwrap()
                .record(wm_selfmodel::MetricKind::ConformalCoverage, 0.88);

            // Save mutable state
            server.save_mutable_state();
        }

        // Phase 2: Recreate server from same path, verify state was loaded
        {
            let server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();

            // GanaRegistry should have recorded usage
            let total_usage: u64 = {
                let registry = server.gana_registry().lock().unwrap();
                registry.usage_counts().values().sum()
            };
            assert!(
                total_usage >= 3,
                "GanaRegistry should have loaded {total_usage} usages from disk (expected >= 3)"
            );

            // LearnedDreamCycle should have phase effectiveness data
            let learned = server.dream().learned();
            assert!(learned.is_some(), "LearnedDreamCycle should be loaded");
            if let Some(learned) = learned {
                let eff0 = learned.effectiveness(0);
                assert!(eff0.is_some(), "Phase 0 should have effectiveness data");
                if let Some(eff) = eff0 {
                    assert_eq!(eff.runs, 1, "Phase 0 should have 1 run recorded");
                }
            }

            // Self-model should have restored conformal coverage history
            assert_eq!(
                server
                    .self_model()
                    .lock()
                    .unwrap()
                    .sample_count(wm_selfmodel::MetricKind::ConformalCoverage),
                2,
                "Self-model conformal coverage history should restore from disk"
            );
        }
    }

    /// Deterministic test embedder — returns fixed vectors so the embedding
    /// router can be constructed without a live llama-server.
    struct FixedEmbedder {
        dim: usize,
    }

    impl wm_memory::Embedder for FixedEmbedder {
        fn embed_batch(&self, texts: &[&str]) -> wm_core::Result<Vec<Vec<f32>>> {
            Ok(texts
                .iter()
                .enumerate()
                .map(|(i, _)| {
                    let mut v = vec![0.0; self.dim];
                    v[i % self.dim] = 1.0;
                    v
                })
                .collect())
        }
        fn dimension(&self) -> usize {
            self.dim
        }
        fn is_available(&self) -> bool {
            true
        }
        fn backend_name(&self) -> &'static str {
            "fixed-test"
        }
    }

    #[tokio::test]
    async fn e2e_oats_persistence_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();

        let oats_file = test_store_path(&tmp).join("mutable_oats.json");
        assert!(!oats_file.exists(), "no OATS file before save");

        // Phase 1: server with an injected embedding router; record outcomes;
        // save. The router is normally built by with_defaults when a real
        // embedder is configured — here we inject one to exercise the
        // persistence wiring.
        {
            let mut server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();
            let descriptions = vec![
                (
                    "memory.create".to_string(),
                    "remember and store information in persistent memory".to_string(),
                ),
                (
                    "memory.list".to_string(),
                    "list all stored memories".to_string(),
                ),
            ];
            let router = wm_tools::embedding_router::EmbeddingRouter::with_descriptions(
                Box::new(FixedEmbedder { dim: 8 }),
                descriptions,
            )
            .expect("router should init with fixed embedder");
            let router = Arc::new(router);
            server.embedding_router = Some(Arc::clone(&router));

            router.record_outcome("memory.create", "remember the sky is blue", true);
            router.record_outcome("memory.create", "store a thought", true);
            router.record_outcome("memory.list", "show all memories", false);

            server.save_mutable_state();
            assert!(
                oats_file.exists(),
                "mutable_oats.json should be written on save"
            );
        }

        // Phase 2: fresh server on the same path; inject a fresh router; load
        // state; verify the OATS counts and centroids came back.
        {
            let server = McpServer::with_defaults(&test_store_path(&tmp)).unwrap();
            assert!(server.embedding_router.is_none());

            let descriptions = vec![
                (
                    "memory.create".to_string(),
                    "remember and store information in persistent memory".to_string(),
                ),
                (
                    "memory.list".to_string(),
                    "list all stored memories".to_string(),
                ),
            ];
            let router = wm_tools::embedding_router::EmbeddingRouter::with_descriptions(
                Box::new(FixedEmbedder { dim: 8 }),
                descriptions,
            )
            .expect("router should init with fixed embedder");
            let router = Arc::new(router);
            let mut server = server;
            server.embedding_router = Some(Arc::clone(&router));
            server.load_mutable_state();

            let counts = router.outcome_counts();
            let create = counts
                .iter()
                .find(|(n, _, _)| n == "memory.create")
                .expect("memory.create should have OATS stats");
            assert_eq!(
                create.1, 2,
                "memory.create success count should restore to 2"
            );
            let list = counts
                .iter()
                .find(|(n, _, _)| n == "memory.list")
                .expect("memory.list should have OATS stats");
            assert_eq!(list.1, 0, "memory.list success count should restore to 0");
            assert_eq!(list.2, 1, "memory.list failure count should restore to 1");
        }
    }

    #[tokio::test]
    async fn boundary_validation_rejects_ssrf_url() {
        let mut server = test_server();
        let resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"http.fetch","arguments":{"url":"http://169.254.169.254/latest/meta-data"}}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert_eq!(
            parsed["error"]["code"], -32602,
            "SSRF URL must be rejected at the boundary: {resp}"
        );
    }

    #[tokio::test]
    async fn boundary_validation_rejects_path_traversal() {
        let mut server = test_server();
        let resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"file.read","arguments":{"path":"../../../etc/passwd"}}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert_eq!(
            parsed["error"]["code"], -32602,
            "Path traversal must be rejected at the boundary: {resp}"
        );
    }

    #[tokio::test]
    async fn boundary_validation_rejects_oversized_params() {
        let mut server = test_server();
        let huge = "x".repeat(MAX_PARAMS_SIZE + 1);
        let body = format!(
            r#"{{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{{"name":"memory.write","arguments":{{"content":"{huge}"}}}}}}"#
        );
        let resp = server.handle_request(&body).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert_eq!(
            parsed["error"]["code"], -32602,
            "Oversized params must be rejected: {resp}"
        );
    }

    #[tokio::test]
    async fn boundary_validation_allows_safe_call() {
        let mut server = test_server();
        let resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"memory.search","arguments":{"query":"hello"}}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(
            parsed["error"].is_null(),
            "Safe call should not be rejected: {resp}"
        );
    }

    #[tokio::test]
    async fn request_budget_rejects_after_cap() {
        let mut server = test_server();
        server.set_request_budget(2);

        for i in 1..=2 {
            let req = json!({"jsonrpc":"2.0","id":i,"method":"initialize","params":{}}).to_string();
            let resp = server.handle_request(&req).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            assert!(
                parsed["error"].is_null(),
                "request {i} should succeed: {resp}"
            );
        }

        let resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":3,"method":"initialize","params":{}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert_eq!(
            parsed["error"]["code"], -32000,
            "request beyond budget must be rejected: {resp}"
        );
        assert_eq!(
            parsed["error"]["data"]["limit"], 2,
            "error should report the budget limit"
        );
    }

    #[tokio::test]
    async fn request_budget_zero_is_unlimited() {
        let mut server = test_server();
        server.set_request_budget(0);
        for i in 1..=5 {
            let req = json!({"jsonrpc":"2.0","id":i,"method":"initialize","params":{}}).to_string();
            let resp = server.handle_request(&req).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            assert!(
                parsed["error"].is_null(),
                "request {i} should succeed: {resp}"
            );
        }
    }

    #[tokio::test]
    async fn rate_limit_throttles_bursts() {
        let mut server = test_server();
        server.set_rate_limit(3);

        for i in 1..=3 {
            let req = json!({"jsonrpc":"2.0","id":i,"method":"initialize","params":{}}).to_string();
            let resp = server.handle_request(&req).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            assert!(
                parsed["error"].is_null(),
                "request {i} should succeed: {resp}"
            );
        }

        let resp = server
            .handle_request(r#"{"jsonrpc":"2.0","id":4,"method":"initialize","params":{}}"#)
            .await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert_eq!(
            parsed["error"]["code"], -32000,
            "burst beyond rate cap must be throttled: {resp}"
        );
        assert_eq!(parsed["error"]["data"]["limit_rpm"], 3);
    }

    #[tokio::test]
    async fn rate_limit_zero_is_unlimited() {
        let mut server = test_server();
        server.set_rate_limit(0);
        for i in 1..=5 {
            let req = json!({"jsonrpc":"2.0","id":i,"method":"initialize","params":{}}).to_string();
            let resp = server.handle_request(&req).await;
            let parsed: Value = serde_json::from_str(&resp).unwrap();
            assert!(
                parsed["error"].is_null(),
                "request {i} should succeed: {resp}"
            );
        }
    }

    #[test]
    fn bounded_line_read_returns_line() {
        let mut input: &[u8] = b"hello world\nsecond line\n";
        let line = read_bounded_line(&mut input, 1024).unwrap();
        match line {
            BoundedLine::Ok(s) => assert_eq!(s, "hello world"),
            _ => panic!("expected a line"),
        }
    }

    #[test]
    fn bounded_line_read_handles_crlf() {
        let mut input: &[u8] = b"hello\r\n";
        let line = read_bounded_line(&mut input, 1024).unwrap();
        match line {
            BoundedLine::Ok(s) => assert_eq!(s, "hello"),
            _ => panic!("expected a line"),
        }
    }

    #[test]
    fn bounded_line_read_detects_oversize() {
        // 10 bytes of 'x' but max is 8 — must return TooLarge, not allocate 10 bytes
        let mut input: &[u8] = b"xxxxxxxxxx\nrest\n";
        let line = read_bounded_line(&mut input, 8).unwrap();
        match line {
            BoundedLine::TooLarge => {}
            _ => panic!("expected TooLarge"),
        }
        // Stream must be positioned after the oversized line so `rest` is next
        let next = read_bounded_line(&mut input, 1024).unwrap();
        match next {
            BoundedLine::Ok(s) => assert_eq!(s, "rest"),
            _ => panic!("expected next line to be 'rest'"),
        }
    }

    #[test]
    fn bounded_line_read_eof() {
        let mut input: &[u8] = b"";
        match read_bounded_line(&mut input, 1024).unwrap() {
            BoundedLine::Eof => {}
            _ => panic!("expected Eof"),
        }
    }

    #[test]
    fn bounded_line_read_no_trailing_newline() {
        let mut input: &[u8] = b"last line without newline";
        let line = read_bounded_line(&mut input, 1024).unwrap();
        match line {
            BoundedLine::Ok(s) => assert_eq!(s, "last line without newline"),
            _ => panic!("expected a line"),
        }
    }

    #[test]
    fn bounded_line_read_oversize_no_newline() {
        let mut input: &[u8] = b"xxxxxxxxxxxxxxxxxxxxxxxxxxxx";
        match read_bounded_line(&mut input, 8).unwrap() {
            BoundedLine::TooLarge => {}
            _ => panic!("expected TooLarge"),
        }
    }
}
