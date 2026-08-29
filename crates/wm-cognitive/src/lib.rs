//! WhiteMagic v5 Cognitive — unified consciousness, reflex, timescale, drive, resonance, autonomic.
//!
//! Merges v4's wm-consciousness + wm-reflex + wm-timescale + wm-drive + wm-resonance + wm-autonomic
//! into a single crate to reduce cross-crate dependency friction for cognitive changes.

#![forbid(unsafe_code)]

// ── Consciousness modules (from wm-consciousness) ───────────────────
pub mod autonomous;
pub mod cerebellum;
pub mod citta;
pub mod codegen;
pub mod constellation;
pub mod depth_gauge;
pub mod dream;
pub mod eco_mode;
pub mod limbic;
pub mod miner;
pub mod neural;
pub mod pattern_bridge;
pub mod pattern_dream_bridge;
pub mod redteam_manifest;
pub mod retention;
pub mod spiral;
pub mod strategy;
pub mod wu_xing;

// ── Merged modules ──────────────────────────────────────────────────
pub mod autonomic;
pub mod drive;
pub mod reflex;
pub mod resonance;
pub mod timescale;

// ── Consciousness re-exports ────────────────────────────────────────
pub use autonomous::{
    AutonomousCycleRunner, CompressionProposal, ConnectionProposal, CycleConfig, CycleContext,
    CycleResult, CycleStatus, CycleType, EmergencePattern, ImprovementProposal, PruneCandidate,
    RedteamProposal, ResearchProposal, SensorimotorProposal,
};
pub use citta::{
    Apotheosis, CittaDimension, CittaHeartbeat, CittaVector, CoherenceConfig, CoherenceReading,
    Presence, Smarana,
};
pub use codegen::{CodeGenConfig, CodeGenResult, CodePatch, PatchTestResult, run_code_gen_cycle};
pub use constellation::{
    Constellation, ConstellationConfig, ConstellationDetector, ConstellationDrift,
    ConstellationReport, is_in_constellation,
};
pub use depth_gauge::{
    ConsciousnessLayer, CurrentMetrics, DepthGauge, DepthReading, HistorySummary,
};
pub use dream::{
    DreamContext, DreamCycle, DreamPhase, DreamResult, PhaseResult, SleepConsolidation,
};
pub use eco_mode::{EcoModeController, EcoModeMetrics, SubsystemFlags};
pub use miner::{AssociationMiner, MinerConfig, MiningReport, ProposedLink};
pub use neural::{
    ActivationResult, CognitiveContext, GateDecision, Metaplasticity, MomentumDynamics,
    Neuromodulator, PredictiveCoder, RippleReport, RippleTagger, SpreadingActivation, SurpriseGate,
    ThalamicGate,
};
pub use pattern_bridge::{
    ConstellationNovelty, GateDecisionKind, PatternBridge, PatternBridgeConfig,
    PatternEnrichedScenario, StrategyPrior, SurpriseAssessment,
};
pub use pattern_dream_bridge::{BridgeSummary, DreamSynthesis, PatternDreamBridge, QueuedPattern};
pub use retention::{
    RetentionConfig, RetentionEngine, RetentionSignal, RetentionVerdict, SweepReport,
};
pub use spiral::{
    CycleSpiralData, EscalationCallback, SemanticConfig, SpiralDirection, SpiralReport,
    SpiralTracker, jaccard_similarity, novelty_score,
};
pub use strategy::{MemoryCluster, StrategyConfig, StrategySynthesizer, SynthesisReport};
pub use wu_xing::{
    BalanceAssessment, CycleEntry, Element, ElementalState, SituationAnalysis, WuXingEngine,
};

// ── Reflex re-exports (from wm-reflex) ──────────────────────────────
pub use reflex::{
    ReflexArgs, ReflexCommand, ReflexDispatchTable, ReflexError, ReflexHandler, ReflexId,
    ReflexOutput, SAFETY_ALLOW_ALL, SAFETY_DENY_ALL, SafetyBit, SafetyMask,
};

// ── Timescale re-exports (from wm-timescale) ────────────────────────
pub use timescale::{
    Hook, HookId, HookResult, HookStats, TIER_COUNT, Tier, TierConfig, TimescaleBus, TimescaleError,
};

// ── Drive re-exports (from wm-drive) ────────────────────────────────
pub use drive::{
    BASELINE, Baseline, BiasConfig, DriveBias, DriveConfig, DriveCore, DriveEvent, DriveEventKind,
    DriveEventSource, DriveState, ToolBias,
};

// ── Resonance re-exports (from wm-resonance) ────────────────────────
pub use resonance::{
    BusStats, EventCallback, EventCategory, EventType, GanYingBus, MAX_CASCADE_DEPTH,
    NervousSubsystem, ResonanceEvent, SubscriptionFilter, SubscriptionId, SubsystemHealth,
    Synchronicity, SynchronicityConfig, SynchronicityDetector, UnifiedNervousSystem,
    default_cascade_rules,
};

// ── Autonomic re-exports (from wm-autonomic) ────────────────────────
pub use autonomic::{
    AutonomicConfig, AutonomicLayer, BitMambaDaemon, SalienceProcessor, SalienceSignal,
    SignalMetadata, SignalType,
};
