//! `WhiteMagic` v4 Consciousness — Citta, Dream, Brain-Wave
//!
//! Implements the consciousness subsystems: citta cycle (16D vector),
//! coherence measurement, dream cycle (12 phases), and the brain-wave
//! eco mode state machine.

#![forbid(unsafe_code)]

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
