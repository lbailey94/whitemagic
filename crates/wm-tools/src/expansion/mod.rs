//! Expansion tools — 77 tool implementations organized by category.
//!
//! Modules:
//! - `memory_ops`: consolidate, decay, batch_read, update, tag, stats, hybrid_recall, sort, filter, deduplicate, export
//! - `session`: start, checkpoint, recall, end
//! - `consciousness`: citta.status, citta.reflect, dream.status, dream.trigger
//! - `tools_mgmt`: effectiveness_report, retire
//! - `patterns`: pattern.search, salience.spotlight, serendipity.surface
//! - `constellation`: detect, list
//! - `galaxy`: stats, export, import, transfer, merge, snapshot, restore, dashboard, backup, taxonomy, purge, health
//! - `karma`: history, clear
//! - `dharma`: rules, audit
//! - `agents`: register, list, heartbeat, trust, descriptions, capabilities, heartbeat.history, deregister
//! - `tasks`: distribute, status
//! - `system`: health, config, flush
//! - `association`: associate_mine
//! - `network`: association.mine, pattern.detect, emergence.report, network.stats, network.centrality, network.clusters
//! - `additional`: count, tags, session_list, citta_coherence, dharma_profiles, nearby
//! - `autonomous`: spiral.report, consolidation.connect/compress, emergence.scan, retention.prune
//! - `knowledge_graph`: kg.extract, kg.query, kg.top
//! - `graph`: graph.walk, graph.community, graph.propagate
//! - `archaeology`: archaeology.search, learning.pattern, learning.suggest
//! - `reasoning`: reasoning.bicameral, think, explain
//! - `pipeline`: pipeline.create/list/status, skill.invoke/list
//! - `anomaly`: anomaly.detect, state.snapshot, state.revert
//! - `correlation`: correlation.analyze, god.nodes
//! - `boundary`: anti_loop.check, boundary.enforce
//! - `homeostasis`: homeostasis.check, homeostasis.adjust, homeostasis.history, homeostasis.alerts
//! - `transaction`: transaction.begin, transaction.commit, transaction.rollback

#![forbid(unsafe_code)]

pub mod additional;
pub mod agents;
pub mod anomaly;
pub mod archaeology;
pub mod association;
pub mod autonomous;
pub mod bayesian_tools;
pub mod bicameral;
pub mod boundary;
pub mod claims_tools;
pub mod common;
pub mod conformal;
pub mod consciousness;
pub mod constellation;
pub mod correlation;
pub mod dharma;
pub mod drive;
pub mod galaxy;
pub mod graph;
pub mod homeostasis;
pub mod imagination;
pub mod karma;
pub mod knowledge_graph;
pub mod memory_ops;
pub mod network;
pub mod nlu_tools;
pub mod patterns;
pub mod pipeline;
pub mod reasoning;
pub mod research;
pub mod resonance;
pub mod rsi;
pub mod sangha_tools;
pub mod self_play;
pub mod selfmodel;
pub mod sensorimotor_tools;
pub mod session;
pub mod simulation_tools;
pub mod system;
pub mod tasks;
pub mod tools_mgmt;
pub mod transaction;
pub mod v4;
pub mod web;

// Re-export all tool structs for registration
pub use additional::{
    CittaCoherenceTool, DharmaProfilesTool, MemoryCountTool, MemoryNearbyTool, MemoryTagsTool,
    SessionListTool,
};
pub use agents::{
    AgentCapabilitiesTool, AgentDeregisterTool, AgentDescriptionsTool, AgentHeartbeatHistoryTool,
    AgentHeartbeatTool, AgentListTool, AgentRegisterTool, AgentTrustTool,
};
pub use anomaly::{AnomalyDetectTool, StateRevertTool, StateSnapshotTool};
pub use archaeology::{ArchaeologySearchTool, LearningPatternTool, LearningSuggestTool};
pub use association::MemoryAssociateMineTool;
pub use autonomous::{
    ConsolidationCompressTool, ConsolidationConnectTool, EmergenceScanTool, RetentionPruneTool,
    SensorimotorScanTool, SpiralReportTool,
};
pub use bayesian_tools::{McOptimizeTool, McSurrogateTool};
pub use bicameral::{BicameralReasonTool, BicameralStatusTool};
pub use boundary::{AntiLoopCheckTool, BoundaryEnforceTool};
pub use claims_tools::{ClaimsTool, register_claims};
pub use consciousness::{
    ApotheosisCheckTool, CittaHistoryTool, CittaReflectTool, CittaStatusTool,
    ConsciousnessDepthTool, DreamAnalyzeTool, DreamStatusTool, DreamTriggerTool, SmaranaStatusTool,
    SmaranaTraceTool,
};
pub use constellation::{ConstellationDetectTool, ConstellationListTool};
pub use correlation::{CorrelationAnalyzeTool, GodNodesTool};
pub use dharma::{DharmaAcsTool, DharmaAuditTool, DharmaRulesTool};
pub use drive::{DriveEventTool, DriveSnapshotTool};
pub use galaxy::{
    GalaxyBackupTool, GalaxyDashboardTool, GalaxyExportTool, GalaxyHealthTool, GalaxyImportTool,
    GalaxyMergeTool, GalaxyPurgeTool, GalaxyRestoreTool, GalaxySnapshotTool, GalaxyStatsTool,
    GalaxyTaxonomyTool, GalaxyTransferTool,
};
pub use graph::{GraphCommunityTool, GraphPropagateTool, GraphWalkTool};
pub use homeostasis::{
    HomeostasisAdjustTool, HomeostasisAlertsTool, HomeostasisCheckTool, HomeostasisHistoryTool,
};
pub use imagination::{
    ImaginePredictTool, ImagineReflectTool, ImagineScenarioTool, register_imagination,
};
pub use karma::{KarmaClearTool, KarmaHistoryTool};
pub use knowledge_graph::{KgExtractTool, KgQueryTool, KgTopTool};
pub use memory_ops::{
    MemoryBatchReadTool, MemoryConsolidateTool, MemoryDecayTool, MemoryDeduplicateTool,
    MemoryExportTool, MemoryFilterTool, MemoryHybridRecallTool, MemorySortTool, MemoryStatsTool,
    MemoryTagTool, MemoryUpdateTool,
};
pub use network::{
    AssociationMineTool, EmergenceReportTool, NetworkCentralityTool, NetworkClustersTool,
    NetworkStatsTool, PatternDetectTool,
};
pub use nlu_tools::NluShadowReportTool;
pub use patterns::{PatternSearchTool, SalienceSpotlightTool, SerendipitySurfaceTool};
pub use pipeline::{
    PipelineCreateTool, PipelineListTool, PipelineStatusTool, SkillInvokeTool, SkillListTool,
};
pub use reasoning::{ExplainTool, ReasoningBicameralTool, ThinkTool};
pub use research::{
    ResearchRabbitHoleTool, ResearchRepoTool, ResearchTopicTool, register_research,
};
pub use resonance::{BusEmitTool, BusRecentTool, BusStatsTool};
pub use rsi::{
    ActiveProposalsTool, DispatchTelemetry, FrictionAutoLogTool, FrictionLogTool,
    FrictionResolveTool, FrictionReviewTool, ImproveProposalsTool, RedteamCoverageReportTool,
    RedteamFromFrictionTool, RedteamProposalsTool, friction_hash, friction_hash_exists,
};
pub use sangha_tools::{
    SanghaChatTool, SanghaDiscoverTool, SanghaLocksTool, SanghaPeersTool, SanghaSignalTool,
};
pub use self_play::{
    SelfPlayExportTool, SelfPlayRunTool, SelfPlayStatusTool, SharedSelfPlayLoop,
    build_self_play_loop, new_shared_loop, register_self_play,
};
pub use sensorimotor_tools::{
    ActuatorCommandTool, ActuatorEStopTool, ActuatorListTool, ReflexAddTool, ReflexEvaluateTool,
    ReflexListTool, SensorHistoryTool, SensorListTool, SensorPollTool, SensorReadTool,
};
pub use session::{SessionCheckpointTool, SessionEndTool, SessionRecallTool, SessionStartTool};
pub use simulation_tools::{SimCounterfactualTool, SimForecastTool, SimMcTool};
pub use system::{SystemConfigTool, SystemFlushTool, SystemHealthTool};
pub use tasks::{TaskDistributeTool, TaskStatusTool};
pub use tools_mgmt::{ToolsEffectivenessReportTool, ToolsRetireTool};
pub use transaction::{
    TransactionBeginTool, TransactionCommitTool, TransactionRollbackTool, TransactionState,
};
pub use v4::{
    ReflexDispatchTool, ReflexStatusTool, TimescaleHooksTool, TimescaleStatusTool,
    WorkspaceEventsTool, WorkspacePublishTool, WorkspaceSpotlightTool, WorkspaceStatsTool,
};
pub use web::{WebDeepFetchTool, WebFetchTool, WebSearchAndReadTool, WebSearchTool, register_web};

use std::sync::Arc;
use wm_cognitive::GanYingBus;
use wm_governance::KarmaLedger;
use wm_memory::{AssociationStore, MemoryStore, SearchEngine};
use wm_substrate::SubstrateMonitor;
use wm_substrate::anomaly::AnomalyDetector;
use wm_substrate::homeostatic::HomeostaticLoop;
use wm_substrate::sensorimotor::{ReflexLoop, SensorimotorBus};

/// Register all expansion tools into a registry.
#[allow(clippy::too_many_arguments)]
pub fn register_expansion(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    karma: Option<Arc<KarmaLedger>>,
    substrate: Option<Arc<SubstrateMonitor>>,
    homeostatic_loop: Option<Arc<std::sync::Mutex<HomeostaticLoop>>>,
    anomaly_detector: Option<Arc<std::sync::Mutex<AnomalyDetector>>>,
    sensorimotor_bus: Option<Arc<std::sync::Mutex<SensorimotorBus>>>,
    reflex_loop: Option<Arc<std::sync::Mutex<ReflexLoop>>>,
    gan_ying_bus: Option<&Arc<std::sync::Mutex<GanYingBus>>>,
    transaction_state: TransactionState,
) -> wm_dispatch::ToolRegistry {
    let mut reg = registry
        // Memory ops (7)
        .register(Arc::new(MemoryConsolidateTool::new(store.clone())))
        .register(Arc::new(MemoryDecayTool::new(store.clone())))
        .register(Arc::new(MemoryBatchReadTool::new(store.clone())))
        .register(Arc::new(MemoryUpdateTool::new(store.clone(), search.clone())))
        .register(Arc::new(MemoryTagTool::new(store.clone())))
        .register(Arc::new(MemoryStatsTool::new(store.clone())))
        .register(Arc::new(MemoryHybridRecallTool::new(store.clone(), search)))
        // Memory ops Tier 7 (4) — WinnowingBasket
        .register(Arc::new(MemorySortTool::new(store.clone())))
        .register(Arc::new(MemoryFilterTool::new(store.clone())))
        .register(Arc::new(MemoryDeduplicateTool::new(store.clone())))
        .register(Arc::new(MemoryExportTool::new(store.clone())))
        // Session (4)
        .register(Arc::new(SessionStartTool::new(store.clone())))
        .register(Arc::new(SessionCheckpointTool::new(store.clone())))
        .register(Arc::new(SessionRecallTool::new(store.clone())))
        .register(Arc::new(SessionEndTool::new(store.clone())))
        // Consciousness (4)
        .register(Arc::new(CittaStatusTool::new()))
        .register(Arc::new(CittaReflectTool::new(store.clone())))
        .register(Arc::new(DreamStatusTool::new(store.clone())))
        .register(Arc::new(DreamTriggerTool::new(store.clone())))
        // Tools management (2)
        .register(Arc::new(ToolsEffectivenessReportTool::new()))
        .register(Arc::new(ToolsRetireTool::new()))
        // Patterns (3)
        .register(Arc::new(PatternSearchTool::new(store.clone())))
        .register(Arc::new(SalienceSpotlightTool::new(store.clone())))
        .register(Arc::new(SerendipitySurfaceTool::new(store.clone())))
        // Constellation (2)
        .register(Arc::new(ConstellationDetectTool::new(store.clone())))
        .register(Arc::new(ConstellationListTool::new(store.clone())))
        // Galaxy (12)
        .register(Arc::new(GalaxyStatsTool::new(store.clone())))
        .register(Arc::new(GalaxyExportTool::new(store.clone())))
        .register(Arc::new(GalaxyImportTool::new(store.clone())))
        .register(Arc::new(GalaxyTransferTool::new(store.clone())))
        .register(Arc::new(GalaxyMergeTool::new(store.clone())))
        .register(Arc::new(GalaxySnapshotTool::new(store.clone())))
        .register(Arc::new(GalaxyRestoreTool::new(store.clone())))
        .register(Arc::new(GalaxyDashboardTool::new(store.clone())))
        .register(Arc::new(GalaxyBackupTool::new(store.clone())))
        .register(Arc::new(GalaxyTaxonomyTool::new(store.clone())))
        .register(Arc::new(GalaxyPurgeTool::new(store.clone())))
        .register(Arc::new(GalaxyHealthTool::new(store.clone())))
        // Knowledge graph (3)
        .register(Arc::new(KgExtractTool::new(store.clone())))
        .register(Arc::new(KgQueryTool::new(store.clone())))
        .register(Arc::new(KgTopTool::new(store.clone())))
        // Graph traversal (3)
        .register(Arc::new(GraphWalkTool::new(store.clone())))
        .register(Arc::new(GraphCommunityTool::new(store.clone())))
        .register(Arc::new(GraphPropagateTool::new(store.clone())))
        // Archaeology & learning (3)
        .register(Arc::new(ArchaeologySearchTool::new(store.clone())))
        .register(Arc::new(LearningPatternTool::new(store.clone())))
        .register(Arc::new(LearningSuggestTool::new(store.clone())))
        // Reasoning (3)
        .register(Arc::new(ReasoningBicameralTool::new(store.clone())))
        .register(Arc::new(ThinkTool::new(store.clone())))
        .register(Arc::new(ExplainTool::new(store.clone())))
        // Pipeline & skills (5)
        .register(Arc::new(PipelineCreateTool::new(store.clone())))
        .register(Arc::new(PipelineListTool::new(store.clone())))
        .register(Arc::new(PipelineStatusTool::new(store.clone())))
        .register(Arc::new(SkillInvokeTool::new(store.clone())))
        .register(Arc::new(SkillListTool::new(store.clone())))
        // Anomaly & state (3)
        .register(Arc::new(AnomalyDetectTool::new(store.clone())))
        .register(Arc::new(StateSnapshotTool::new(store.clone())))
        .register(Arc::new(StateRevertTool::new(store.clone())))
        // Correlation & god nodes (2)
        .register(Arc::new(CorrelationAnalyzeTool::new(store.clone())))
        .register(Arc::new(GodNodesTool::new(store.clone())))
        // Anti-loop & boundary (2)
        .register(Arc::new(AntiLoopCheckTool::new(store.clone())))
        .register(Arc::new(BoundaryEnforceTool::new(store.clone())))
        // Karma (2) — only if karma ledger is available
        ;
    if let Some(k) = karma {
        reg = reg
            .register(Arc::new(KarmaHistoryTool::new(k.clone())))
            .register(Arc::new(KarmaClearTool::new(k)));
    }
    let mut reg = reg
        // Dharma (3)
        .register(Arc::new(DharmaRulesTool::new()))
        .register(Arc::new(DharmaAuditTool::new(store.clone())))
        .register(Arc::new(DharmaAcsTool::new()))
        // Agents (8)
        .register(Arc::new(AgentRegisterTool::new(store.clone())))
        .register(Arc::new(AgentListTool::new(store.clone())))
        .register(Arc::new(AgentHeartbeatTool::new(store.clone())))
        .register(Arc::new(AgentTrustTool::new(store.clone())))
        .register(Arc::new(AgentDescriptionsTool::new(store.clone())))
        .register(Arc::new(AgentCapabilitiesTool::new(store.clone())))
        .register(Arc::new(AgentHeartbeatHistoryTool::new(store.clone())))
        .register(Arc::new(AgentDeregisterTool::new(store.clone())))
        // Tasks (2)
        .register(Arc::new(TaskDistributeTool::new(store.clone())))
        .register(Arc::new(TaskStatusTool::new(store.clone())))
        // System (3)
        .register(Arc::new(SystemHealthTool::new(store.clone())))
        .register(Arc::new(SystemConfigTool::new()))
        .register(Arc::new(SystemFlushTool::new(store.clone())))
        // Association mining (1)
        .register(Arc::new(MemoryAssociateMineTool::new(store.clone())))
        // Additional (5)
        .register(Arc::new(MemoryCountTool::new(store.clone())))
        .register(Arc::new(MemoryTagsTool::new(store.clone())))
        .register(Arc::new(SessionListTool::new(store.clone())))
        .register(Arc::new(CittaCoherenceTool::new()))
        .register(Arc::new(DharmaProfilesTool::new()))
        // Spatial queries (1)
        .register(Arc::new(MemoryNearbyTool::new(store.clone())))
        // Autonomous cycles (4) — Phase E
        .register(Arc::new(ConsolidationConnectTool::new(
            store.clone(),
            associations.clone(),
            spiral_tracker.clone(),
        )))
        .register(Arc::new(ConsolidationCompressTool::new(
            store.clone(),
            associations.clone(),
            spiral_tracker.clone(),
        )))
        .register(Arc::new(EmergenceScanTool::new(
            store.clone(),
            associations.clone(),
            spiral_tracker.clone(),
        )))
        .register(Arc::new(RetentionPruneTool::new(
            store.clone(),
            associations.clone(),
            spiral_tracker.clone(),
        )))
        // Spiral tracker (1) — Phase F
        .register(Arc::new(SpiralReportTool::new(spiral_tracker.clone())))
        // Tier 5: Net tools (6)
        .register(Arc::new(AssociationMineTool::new(store.clone())))
        .register(Arc::new(PatternDetectTool::new(store.clone())))
        .register(Arc::new(EmergenceReportTool::new(store.clone())))
        .register(Arc::new(NetworkStatsTool::new(store.clone())))
        .register(Arc::new(NetworkCentralityTool::new(store.clone())))
        .register(Arc::new(NetworkClustersTool::new(store.clone())))
        // Tier 5: Ghost tools (6)
        .register(Arc::new(SmaranaStatusTool::new(store.clone())))
        .register(Arc::new(SmaranaTraceTool::new(store.clone())))
        .register(Arc::new(ApotheosisCheckTool::new(store.clone())))
        .register(Arc::new(CittaHistoryTool::new(store.clone())))
        .register(Arc::new(DreamAnalyzeTool::new(store.clone())))
        .register(Arc::new(ConsciousnessDepthTool::new(store.clone())));

    // Homeostasis (4) — Tier 7 Dipper — only if substrate monitor is available
    if let Some(sm) = substrate {
        let loop_ = homeostatic_loop
            .unwrap_or_else(|| Arc::new(std::sync::Mutex::new(HomeostaticLoop::default())));
        let detector = anomaly_detector
            .unwrap_or_else(|| Arc::new(std::sync::Mutex::new(AnomalyDetector::default())));
        reg = reg
            .register(Arc::new(HomeostasisCheckTool::new(
                sm.clone(),
                loop_,
                detector.clone(),
            )))
            .register(Arc::new(HomeostasisAdjustTool::new(sm.clone())))
            .register(Arc::new(HomeostasisHistoryTool::new(sm.clone())))
            .register(Arc::new(HomeostasisAlertsTool::new(sm, detector)));
    }

    let _ = &mut reg; // suppress unused_mut warning

    // RSI: Friction logging + improvement + redteam + resolve (7) — Phase 1-3
    reg = rsi::register_rsi(&reg, store, None, &associations, None, None);

    // Sensorimotor tools (10) — Embodiment I/O
    let bus = sensorimotor_bus.unwrap_or_else(|| {
        Arc::new(std::sync::Mutex::new(
            wm_substrate::sensorimotor::linux_hardware_bus(),
        ))
    });
    let reflex = reflex_loop.unwrap_or_else(|| Arc::new(std::sync::Mutex::new(ReflexLoop::new())));
    reg =
        sensorimotor_tools::register_sensorimotor(&reg, bus.clone(), reflex.clone(), gan_ying_bus);

    // Sensorimotor autonomous cycle (1) — Embodiment
    reg = reg.register(Arc::new(SensorimotorScanTool::new(
        store.clone(),
        associations,
        spiral_tracker,
        bus,
        reflex,
    )));

    // Transaction tools (3) — snapshot/rollback for multi-tool sequences
    reg = reg
        .register(Arc::new(TransactionBeginTool::new(
            store.clone(),
            transaction_state.clone(),
        )))
        .register(Arc::new(TransactionCommitTool::new(
            transaction_state.clone(),
        )))
        .register(Arc::new(TransactionRollbackTool::new(
            store.clone(),
            transaction_state,
        )));

    // Imagination tools (3) — scenario generation, prediction, reflection
    reg = register_imagination(&reg, store);

    // Self-play tools (3) — training loop, status, export
    reg = register_self_play(&reg, store, new_shared_loop());

    // Web research tools (4) — fetch, deep_fetch, search, search_and_read
    reg = register_web(&reg);

    // Research tools (3) — topic, repo, rabbit_hole
    reg = register_research(&reg, store);

    reg
}
