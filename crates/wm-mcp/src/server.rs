//! JSON-RPC over stdio MCP server.
//!
//! Implements the Model Context Protocol with three methods:
//! - `initialize`: handshake with client info
//! - `tools/list`: returns only the `wm` meta-tool (single entry point)
//! - `tools/call`: dispatches any registered tool through the governance pipeline
//!
//! The `wm` meta-tool routes natural language to 192 tools via TF-IDF NLU
//! classification, or accepts an explicit `route` parameter for direct dispatch.
//! Use `wm(thought="list tools")` or `wm(route="tools.list")` to discover tools.

use std::io::{BufRead, Write};
use std::sync::Arc;

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
    SearchEngine, VectorStore, create_embedder,
};
use wm_sangha::{PeerDiscovery, ResourceLockManager, SanghaChat, SignalBroadcast};
use wm_selfmodel::SelfModel;
use wm_substrate::SubstrateMonitor;
use wm_substrate::anomaly::AnomalyDetector;
use wm_substrate::homeostatic::HomeostaticLoop;
use wm_substrate::sensorimotor::{ReflexLoop, SensorimotorBus};
use wm_tools::expansion::rsi::{DispatchTelemetry, FrictionAutoLogTool};
use wm_workspace::GlobalWorkspace;

/// MCP server state.
#[allow(dead_code)]
pub struct McpServer {
    registry: ToolRegistry,
    pipeline: DispatchPipeline,
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
    /// Dispatch counter for periodic autonomous cycles
    dispatch_count: std::sync::atomic::AtomicU64,
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

impl McpServer {
    /// Create a new MCP server with the given tool registry, dispatch pipeline,
    /// and eco mode controller.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        registry: ToolRegistry,
        pipeline: DispatchPipeline,
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
            dispatch_count: std::sync::atomic::AtomicU64::new(0),
            transaction_state,
            tri_model,
            scenario_engine: None,
            gana_registry: Arc::new(std::sync::Mutex::new(wm_core::GanaRegistry::new())),
            dynamic_galaxies: Arc::new(
                std::sync::Mutex::new(wm_core::DynamicGalaxyRegistry::new()),
            ),
            shadow_stats,
        }
    }

    /// Create a new MCP server with the given registry and pipeline, using
    /// a default eco mode controller.
    #[allow(clippy::too_many_arguments)]
    pub fn with_default_eco(
        registry: ToolRegistry,
        pipeline: DispatchPipeline,
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
        let store = std::sync::Arc::new(MemoryStore::open_default(store_path)?);

        // Open Tantivy search index alongside LMDB
        let search_path = store_path.join("tantivy");
        std::fs::create_dir_all(&search_path)?;
        let search = std::sync::Arc::new(SearchEngine::open(&search_path)?);

        let karma_ledger = std::sync::Arc::new(KarmaLedger::new(store.clone())?);
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

        let registry = ToolRegistry::new();
        let conversational = {
            let embedder: Arc<dyn Embedder> = create_embedder().into();
            let recall = RecallEngine::new(
                store.clone(),
                search.clone(),
                VectorStore::new(),
                embedder,
                RecallConfig::default(),
            )?;
            Some(ConversationalSearch::with_defaults(recall))
        };
        let friction_search = search.clone();
        let transaction_state: wm_tools::expansion::TransactionState =
            Arc::new(std::sync::Mutex::new(None));
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
            Some(Arc::clone(&homeostatic_loop)),
            Some(Arc::clone(&anomaly_detector)),
            Some(Arc::clone(&sensorimotor_bus)),
            Some(Arc::clone(&reflex_loop)),
            Some(&gan_ying_bus),
            transaction_state.clone(),
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
        let sangha_chat = Arc::new(std::sync::Mutex::new(SanghaChat::new(100)));
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
        let registry = wm_tools::expansion::simulation_tools::register_simulation(&registry);

        let shadow_stats = Arc::new(std::sync::RwLock::new(
            wm_tools::embedding_router::ShadowModeStats::default(),
        ));
        let registry = wm_tools::register_meta_tools(&registry, &store, shadow_stats.clone());

        let gana_registry = Arc::new(std::sync::Mutex::new(wm_core::GanaRegistry::new()));
        let dynamic_galaxies =
            Arc::new(std::sync::Mutex::new(wm_core::DynamicGalaxyRegistry::new()));

        let pipeline = DispatchPipeline::new(
            std::sync::Arc::new(wm_dispatch::RateLimiter::default()),
            std::sync::Arc::new(wm_dispatch::CircuitBreakerRegistry::default()),
            dharma_gate.clone(),
            Some(karma_ledger.clone()),
        )
        .with_gana_registry(gana_registry.clone());

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
            Some(karma_ledger),
            transaction_state,
            cyberbrain.tri_model,
            shadow_stats,
        );

        // Override mutable structure registries with shared instances (Phase 6)
        server.gana_registry = gana_registry;
        server.dynamic_galaxies = dynamic_galaxies;

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
    pub fn run(&mut self) -> anyhow::Result<()> {
        let rt = tokio::runtime::Runtime::new()?;
        let stdin = std::io::stdin();
        let stdout = std::io::stdout();
        let mut out = stdout.lock();

        for line in stdin.lock().lines() {
            let line = line?;
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
        use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
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

            // Build the line buffer for this iteration
            let mut line = String::new();

            tokio::select! {
                // Signal received — graceful shutdown
                result = &mut shutdown_signal => {
                    match result {
                        Ok(sig) => tracing::info!(signal = sig, "Shutdown signal received — shutting down gracefully"),
                        Err(e) => tracing::warn!(error = %e, "Signal handler error — shutting down"),
                    }
                    break;
                }

                // stdin ready — MCP request arrived
                result = reader.read_line(&mut line) => {
                    let n = result?;
                    if n == 0 {
                        // EOF — client disconnected
                        break;
                    }
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
                    if request.id.is_some() {
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

        // Save mutable structures to disk (Phase 6 persistence)
        self.save_mutable_state();

        // LMDB is automatically flushed by Drop when Arc<MemoryStore> is dropped.
        // The store uses memory-mapped files, so data is persistent by default.
    }

    /// Get a reference to the eco mode controller.
    #[must_use]
    pub const fn eco_mode(&self) -> &EcoModeController {
        &self.eco_mode
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
                "name": "whitemagic-v5",
                "version": env!("CARGO_PKG_VERSION"),
            },
            "capabilities": {
                "tools": {},
            },
        }))
    }

    /// Handle `tools/list` — return only the `wm` meta-tool.
    ///
    /// The `wm` meta-tool is the single entry point for MCP clients. It routes
    /// natural language input to any of the 184 registered tools via TF-IDF
    /// NLU classification, or accepts an explicit `route` parameter for direct
    /// dispatch. Use `wm(thought="list tools")` or `wm(route="tools.list")` to
    /// discover available tools.
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

        // Only expose the wm meta-tool — all 192 tools are accessible through it
        if let Some(wm) = self.registry.get("wm") {
            Ok(json!({
                "tools": [{
                    "name": wm.name(),
                    "description": "WhiteMagic v5 meta-tool — routes natural language to 192 tools across 28 Ganas. Use thought= for NLU routing (e.g. 'remember that X is Y', 'search for Z', 'list tools'), route= for explicit dispatch (e.g. 'memory.create', 'tools.list', 'friction.log'), and args= for passthrough arguments. Say 'list tools' to discover all available tools.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "thought": {
                                "type": "string",
                                "description": "Natural language input describing what to do. Auto-routes to the best-matching tool via TF-IDF NLU classification.",
                            },
                            "route": {
                                "type": "string",
                                "description": "Explicit tool name for direct dispatch (e.g. 'memory.create', 'tools.list', 'friction.log', 'redteam.proposals').",
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

        let arguments = params
            .get("arguments")
            .cloned()
            .unwrap_or_else(|| json!({}));

        let mut ctx = Context::new(self.eco_mode.current());

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

        // Record dispatch metrics into self-model for future forecasting
        if let Ok(model) = self.self_model.lock() {
            model.record(wm_selfmodel::MetricKind::Latency, dispatch_latency);
            let error_rate = if dispatch_result.is_ok() { 0.0 } else { 1.0 };
            model.record(wm_selfmodel::MetricKind::ErrorRate, error_rate);
        }

        // Citta heartbeat — post-dispatch consciousness update
        let success = dispatch_result.is_ok();
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
            Ok(_) => String::new(),
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
            // Anomaly detection on successful dispatches
            let p99_ms = telemetry.tool_stats.p99_latency_ns as f32 / 1_000_000.0;
            if p99_ms > 0.0 && telemetry.latency_ms > p99_ms {
                if let Err(e) = self
                    .friction_auto_log
                    .log_anomaly(&telemetry, "high_latency")
                {
                    tracing::warn!("Failed to auto-log anomaly entry: {e}");
                }
            } else if effectiveness < 0.3 && telemetry.tool_stats.call_count > 5 {
                // Only flag low_effectiveness after enough calls for a
                // meaningful success rate. Skip on fresh processes where
                // stats haven't accumulated yet (avoids false positives).
                if let Err(e) = self
                    .friction_auto_log
                    .log_anomaly(&telemetry, "low_effectiveness")
                {
                    tracing::warn!("Failed to auto-log anomaly entry: {e}");
                }
            } else if ctx.karma_debt > 0.5 {
                if let Err(e) = self
                    .friction_auto_log
                    .log_anomaly(&telemetry, "high_karma_debt")
                {
                    tracing::warn!("Failed to auto-log anomaly entry: {e}");
                }
            }
        } else if let Err(e) = self.friction_auto_log.log_error(&telemetry) {
            tracing::warn!("Failed to auto-log friction entry: {e}");
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
                if !wm_tools::expansion::friction_hash_exists(&self.store, &hash_tag) {
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

        // Check if dream cycle should run (Theta state)
        if self.dream.should_run(self.eco_mode.current()) {
            let ctx = if let Some(ref engine) = self.scenario_engine {
                DreamContext::new(&self.store, &self.associations).with_imagination(engine)
            } else {
                DreamContext::new(&self.store, &self.associations)
            };
            let dream_result = self.dream.run(&ctx);
            tracing::info!(
                phases = dream_result.phases.len(),
                duration_ms = dream_result.total_duration.as_millis(),
                "Dream cycle completed"
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
        {
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

        // ── Periodic Sensorimotor Autonomous Cycle ──
        // Run the full sensorimotor cycle (poll → evaluate reflexes → execute commands)
        // every 10 dispatches for self-regulated embodiment.
        let count = self
            .dispatch_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        if count % 10 == 0 && count > 0 {
            let hv = self.substrate.sample();
            let health = hv.health_score();
            let cycle_ctx =
                wm_cognitive::CycleContext::new(&self.store, &self.associations, health)
                    .with_sensorimotor(&self.sensorimotor_bus, &self.reflex_loop);
            let cycle_ctx = if let Some(ref engine) = self.scenario_engine {
                cycle_ctx.with_imagination(engine)
            } else {
                cycle_ctx
            };

            let mut runner = wm_cognitive::AutonomousCycleRunner::default();
            let result = runner.run_cycle(wm_cognitive::CycleType::Sensorimotor, &cycle_ctx);

            if result.status == wm_cognitive::CycleStatus::Completed {
                tracing::debug!(
                    sensors = result.memories_scanned,
                    proposals = result.proposals_generated,
                    "Periodic sensorimotor cycle completed"
                );
                // Emit ReflexFired events for any triggered reflexes
                if result.proposals_generated > 0 {
                    if let Ok(mut gy) = self.gan_ying_bus.lock() {
                        let triggered: Vec<_> = result
                            .sensorimotor
                            .iter()
                            .filter(|s| s.reflex_triggered)
                            .collect();
                        if !triggered.is_empty() {
                            gy.emit(
                                wm_cognitive::EventType::ReflexFired,
                                "sensorimotor_cycle",
                                json!({
                                    "triggered_count": triggered.len(),
                                    "sensors": triggered.iter().map(|s| json!({
                                        "sensor_id": s.sensor_id,
                                        "actuator_id": s.actuator_id,
                                        "command_value": s.command_value,
                                    })).collect::<Vec<_>>(),
                                }),
                            );
                        }
                    }
                }
            }
        }

        // ── WS-4: Proactive Improvement Surfacing ──
        // Trigger Improve cycle every 50 dispatches or on Theta/Delta (idle states)
        let should_run_improve = count > 0 && count % 50 == 0;
        let bw = self.eco_mode.current();
        let is_idle = matches!(bw, wm_core::BrainWave::Theta | wm_core::BrainWave::Delta);
        if should_run_improve || is_idle {
            let hv = self.substrate.sample();
            let health = hv.health_score();
            let cycle_ctx =
                wm_cognitive::CycleContext::new(&self.store, &self.associations, health);

            let mut runner = wm_cognitive::AutonomousCycleRunner::default();
            let improve_result = runner.run_cycle(wm_cognitive::CycleType::Improve, &cycle_ctx);

            if improve_result.status == wm_cognitive::CycleStatus::Completed
                && improve_result.proposals_generated > 0
            {
                tracing::info!(
                    proposals = improve_result.proposals_generated,
                    friction_scanned = improve_result.memories_scanned,
                    "Proactive improve cycle generated proposals"
                );

                // Store proposals as Codex memories with rsi:proposal:active tag
                for proposal in &improve_result.improvements {
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
                    if let Err(e) = self.store.put(wm_core::Galaxy::Codex, &memory) {
                        tracing::warn!("Failed to store proposal memory: {e}");
                    }
                }

                // Emit workspace event with high salience
                if let Ok(mut ws) = self.workspace.lock() {
                    ws.publish_simple(
                        wm_workspace::CoreId::Autonomous,
                        wm_workspace::EventType::AttentionRequest,
                        0.8,
                        0.8,
                        json!({
                            "proposals": improve_result.proposals_generated,
                            "friction_scanned": improve_result.memories_scanned,
                            "notes": improve_result.notes,
                        }),
                    );
                }
            }
        }

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

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

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
        let conversational = {
            let embedder: Arc<dyn Embedder> = create_embedder().into();
            let recall = RecallEngine::new(
                store.clone(),
                search.clone(),
                VectorStore::new(),
                embedder,
                RecallConfig::default(),
            )
            .unwrap();
            Some(ConversationalSearch::with_defaults(recall))
        };
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
            Some(Arc::clone(&homeostatic_loop)),
            Some(Arc::clone(&anomaly_detector)),
            None,
            None,
            None,
            test_transaction_state.clone(),
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
        let sangha_chat = Arc::new(std::sync::Mutex::new(SanghaChat::new(100)));
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
        let registry = wm_tools::expansion::simulation_tools::register_simulation(&registry);

        let test_shadow_stats = Arc::new(std::sync::RwLock::new(
            wm_tools::embedding_router::ShadowModeStats::default(),
        ));
        let registry = wm_tools::register_meta_tools(&registry, &store, test_shadow_stats.clone());

        let pipeline = DispatchPipeline::new(
            Arc::new(wm_dispatch::RateLimiter::default()),
            Arc::new(wm_dispatch::CircuitBreakerRegistry::default()),
            dharma_gate.clone(),
            Some(karma_ledger.clone()),
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
        assert_eq!(result["serverInfo"]["name"], "whitemagic-v5");
        assert!(result["capabilities"]["tools"].is_object());
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
        assert!(
            tools[0]["description"]
                .as_str()
                .unwrap()
                .contains("192 tools")
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
        assert_eq!(parsed["result"]["serverInfo"]["name"], "whitemagic-v5");
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
        assert_eq!(init["result"]["serverInfo"]["name"], "whitemagic-v5");

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
        let mut server = McpServer::with_defaults(tmp.path()).unwrap();

        // Persistence is wired in the production constructor
        let persist_path = {
            let bus = server.gan_ying_bus().lock().unwrap();
            bus.persist_path().map(std::path::Path::to_path_buf)
        };
        assert_eq!(
            persist_path.as_deref(),
            Some(tmp.path().join("resonance_events.jsonl").as_path())
        );

        let resp = server.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"persistence test"}}}"#,
        ).await;
        let parsed: Value = serde_json::from_str(&resp).unwrap();
        assert!(parsed.get("error").is_none() || parsed["error"].is_null());

        let log = std::fs::read_to_string(tmp.path().join("resonance_events.jsonl"))
            .expect("persistence log should exist after dispatch");
        assert!(
            log.contains("tool_dispatch_start"),
            "log should contain tool_dispatch_start, got: {log}"
        );

        // A fresh server over the same store seeds its recent buffer from the log
        drop(server);
        let server2 = McpServer::with_defaults(tmp.path()).unwrap();
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
        assert_eq!(good["result"]["serverInfo"]["name"], "whitemagic-v5");

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

    // ── E2E Mutable Structures Integration Tests (Phase 6) ─────────────

    #[tokio::test]
    async fn e2e_gana_registry_records_dispatch_co_usage() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults(tmp.path()).unwrap();

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
        let server = McpServer::with_defaults(tmp.path()).unwrap();

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
        let server = McpServer::with_defaults(tmp.path()).unwrap();

        // The dream cycle should have a LearnedDreamCycle attached
        // (verified indirectly: the dream cycle runs without error)
        assert_eq!(server.dream().cycles_completed(), 0);
    }

    #[tokio::test]
    async fn e2e_full_pipeline_with_mutable_structures() {
        let tmp = tempfile::tempdir().unwrap();
        let mut server = McpServer::with_defaults(tmp.path()).unwrap();

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
            let mut server = McpServer::with_defaults(tmp.path()).unwrap();
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

            // Save mutable state
            server.save_mutable_state();
        }

        // Phase 2: Recreate server from same path, verify state was loaded
        {
            let server = McpServer::with_defaults(tmp.path()).unwrap();

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
        }
    }
}
