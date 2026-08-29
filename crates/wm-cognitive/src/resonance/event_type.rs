//! Gan Ying (感應) event type taxonomy — 233 event types across 10 categories.
//!
//! "Things that accord in tone vibrate together" — the Gan Ying Bus is
//! WhiteMagic's internal event resonance system. Every significant
//! occurrence in the cognitive system emits an event, and subscribers
//! react to events they care about.
//!
//! The taxonomy is organized into 10 categories, each with sub-types.
//! Subscribers can subscribe to individual event types or entire
//! categories.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

// ── Event Category ────────────────────────────────────────────────────

/// Top-level event category in the Gan Ying taxonomy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum EventCategory {
    /// System lifecycle, health, configuration.
    System = 0,
    /// Memory operations (create, read, consolidate, forget).
    Memory = 1,
    /// Consciousness events (citta, dream, spiral, brain-wave).
    Consciousness = 2,
    /// Drive and motivation events.
    Drive = 3,
    /// Harmony and anomaly events.
    Harmony = 4,
    /// Governance events (dharma, karma, mandala).
    Governance = 5,
    /// Tool dispatch events.
    Tool = 6,
    /// Agent and mesh events.
    Agent = 7,
    /// Embodiment and sensorimotor events.
    Embodiment = 8,
    /// Multi-agent coordination events (claims, leases, batons).
    Coordination = 9,
}

impl EventCategory {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::System => "system",
            Self::Memory => "memory",
            Self::Consciousness => "consciousness",
            Self::Drive => "drive",
            Self::Harmony => "harmony",
            Self::Governance => "governance",
            Self::Tool => "tool",
            Self::Agent => "agent",
            Self::Embodiment => "embodiment",
            Self::Coordination => "coordination",
        }
    }

    /// All 10 categories in canonical order.
    pub const ALL: [Self; 10] = [
        Self::System,
        Self::Memory,
        Self::Consciousness,
        Self::Drive,
        Self::Harmony,
        Self::Governance,
        Self::Tool,
        Self::Agent,
        Self::Embodiment,
        Self::Coordination,
    ];
}

impl std::fmt::Display for EventCategory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// ── Event Type ────────────────────────────────────────────────────────

/// Gan Ying event type — 233 types across 10 categories.
///
/// The enum is organized by category with explicit variant naming.
/// Each variant maps to its category via [`EventType::category()`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[repr(u16)]
pub enum EventType {
    // ── System (0–24) ────────────────────────────────────────────
    SystemStartup = 0,
    SystemShutdown = 1,
    SystemRestart = 2,
    SystemHealthCheck = 3,
    SystemHeartbeat = 4,
    SystemStateChange = 5,
    SystemConfigUpdate = 6,
    SystemError = 7,
    SystemWarning = 8,
    SystemInfo = 9,
    SystemReady = 10,
    SystemPaused = 11,
    SystemResumed = 12,
    SystemCrash = 13,
    SystemRecovery = 14,
    SystemMemoryWarning = 15,
    SystemCpuWarning = 16,
    SystemDiskWarning = 17,
    SystemThermalWarning = 18,
    SystemBatteryLow = 19,
    SystemUpdateAvailable = 20,
    SystemMigrationStart = 21,
    SystemMigrationComplete = 22,
    SystemBackupStart = 23,
    SystemBackupComplete = 24,

    // ── Memory (25–49) ───────────────────────────────────────────
    MemoryCreated = 25,
    MemoryUpdated = 26,
    MemoryDeleted = 27,
    MemoryRead = 28,
    MemoryListed = 29,
    MemorySearched = 30,
    MemoryConsolidated = 31,
    MemoryForgotten = 32,
    MemoryAssociated = 33,
    MemoryDisassociated = 34,
    MemoryTagged = 35,
    MemoryUntagged = 36,
    MemoryDecayed = 37,
    MemoryBoosted = 38,
    MemoryRecalled = 39,
    MemoryEmbedded = 40,
    MemoryReembedded = 41,
    MemoryBatchWrite = 42,
    MemoryBatchRead = 43,
    MemoryGalaxyCreated = 44,
    MemoryGalaxyDeleted = 45,
    MemoryGalaxyStats = 46,
    MemoryExported = 47,
    MemoryImported = 48,
    MemoryDeduplicated = 49,

    // ── Consciousness (50–74) ────────────────────────────────────
    CittaAdvance = 50,
    CittaDecay = 51,
    CittaCoherenceMeasured = 52,
    CittaValenceShift = 53,
    CittaHeartbeat = 54,
    DreamPhaseStart = 55,
    DreamPhaseComplete = 56,
    DreamCycleStart = 57,
    DreamCycleComplete = 58,
    DreamArtifactCreated = 59,
    DreamConsolidationStart = 60,
    DreamConsolidationComplete = 61,
    SpiralUpdate = 62,
    SpiralSuspension = 63,
    SpiralRecovery = 64,
    BrainWaveChange = 65,
    BrainWaveGamma = 66,
    BrainWaveBeta = 67,
    BrainWaveAlpha = 68,
    BrainWaveTheta = 69,
    BrainWaveDelta = 70,
    SmaranaRecall = 71,
    SmaranaMiss = 72,
    ApotheosisUpdate = 73,
    PresenceDetected = 74,

    // ── Drive (75–99) ────────────────────────────────────────────
    DriveCuriositySpike = 75,
    DriveCuriosityDrop = 76,
    DriveSatisfactionRise = 77,
    DriveSatisfactionDrop = 78,
    DriveCautionAlert = 79,
    DriveCautionRelease = 80,
    DriveEnergyLow = 81,
    DriveEnergyReplenished = 82,
    DriveSocialInteraction = 83,
    DriveSocialIsolation = 84,
    DriveBiasUpdate = 85,
    DriveDecayCycle = 86,
    DriveEventProcessed = 87,
    DriveNovelInput = 88,
    DriveLowConfidence = 89,
    DriveHighConfidence = 90,
    DriveExplorationTrigger = 91,
    DriveRestTrigger = 92,
    DriveConsolidationTrigger = 93,
    DriveSocialTrigger = 94,
    DriveThresholdCrossed = 95,
    DriveBaselineReset = 96,
    DriveCrossPollination = 97,
    DriveWuXingImbalance = 98,
    DriveWuXingCorrection = 99,

    // ── Harmony (100–124) ────────────────────────────────────────
    HarmonyAnomalyDetected = 100,
    HarmonyAnomalyWarning = 101,
    HarmonyAnomalyCritical = 102,
    HarmonyHomeostaticObserve = 103,
    HarmonyHomeostaticAdvise = 104,
    HarmonyHomeostaticCorrect = 105,
    HarmonyHomeostaticIntervene = 106,
    HarmonyGunaShift = 107,
    HarmonyGunaSattvic = 108,
    HarmonyGunaRajasic = 109,
    HarmonyGunaTamasic = 110,
    HarmonyYinYangDrift = 111,
    HarmonyYinYangBalanced = 112,
    HarmonyYinYangYangExcess = 113,
    HarmonyYinYangYinExcess = 114,
    HarmonyHealthScoreUpdate = 115,
    HarmonyHealthScoreLow = 116,
    HarmonyHealthScoreCritical = 117,
    HarmonyThermalAlert = 118,
    HarmonyBatteryAlert = 119,
    HarmonyCpuSpike = 120,
    HarmonyMemorySpike = 121,
    HarmonyDiskIoSpike = 122,
    HarmonySwapSpike = 123,
    HarmonyStressDetected = 124,

    // ── Governance (125–149) ─────────────────────────────────────
    DharmaWarn = 125,
    DharmaBlock = 126,
    DharmaAllow = 127,
    DharmaProfileChange = 128,
    DharmaRuleEvaluated = 129,
    DharmaRuleAdded = 130,
    DharmaRuleRemoved = 131,
    DharmaStrictModeEnabled = 132,
    DharmaStrictModeDisabled = 133,
    KarmaRecorded = 134,
    KarmaDebtUpdated = 135,
    KarmaDebtHigh = 136,
    KarmaDebtCleared = 137,
    KarmaChainValidated = 138,
    KarmaChainBroken = 139,
    KarmaSattvic = 140,
    KarmaRajasic = 141,
    KarmaTamasic = 142,
    MandalaBreach = 143,
    MandalaCompartmentSwitch = 144,
    MandalaAccessGranted = 145,
    MandalaAccessDenied = 146,
    CircuitBreakerOpen = 147,
    CircuitBreakerClose = 148,
    CircuitBreakerHalfOpen = 149,

    // ── Tool (150–174) ───────────────────────────────────────────
    ToolDispatchStart = 150,
    ToolDispatchSuccess = 151,
    ToolDispatchError = 152,
    ToolDispatchTimeout = 153,
    ToolDispatchRetry = 154,
    ToolNluRoute = 155,
    ToolNluFallback = 156,
    ToolRegistered = 157,
    ToolUnregistered = 158,
    ToolRetired = 159,
    ToolPromoted = 160,
    ToolEffectivenessLow = 161,
    ToolEffectivenessHigh = 162,
    ToolRateLimited = 163,
    ToolCircuitBroken = 164,
    ToolStatsUpdated = 165,
    ToolEffectChecked = 166,
    ToolKarmaRecorded = 167,
    ToolBatchDispatch = 168,
    ToolBatchComplete = 169,
    ToolCacheHit = 170,
    ToolCacheMiss = 171,
    ToolSpeculativeValidated = 172,
    ToolSpeculativeRejected = 173,
    ToolSpeculativeRepaired = 174,

    // ── Agent (175–199) ──────────────────────────────────────────
    AgentRegistered = 175,
    AgentUnregistered = 176,
    AgentHeartbeat = 177,
    AgentStatusUpdate = 178,
    AgentCapabilityAdvertised = 179,
    PeerDiscovered = 180,
    PeerLost = 181,
    PeerHealthCheck = 182,
    PeerHealthTimeout = 183,
    SanghaMessageSent = 184,
    SanghaMessageReceived = 185,
    SanghaLockAcquired = 186,
    SanghaLockReleased = 187,
    SanghaLockExpired = 188,
    SanghaLockDenied = 189,
    SanghaLockDeadlock = 190,
    SanghaChatJoin = 191,
    SanghaChatLeave = 192,
    SanghaChatMessage = 193,
    SanghaChatTopic = 194,
    SanghaFederatedMemory = 195,
    SanghaConstellationMerge = 196,
    SanghaConflictResolved = 197,
    SanghaHologramSync = 198,
    SanghaTrustUpdated = 199,

    // ── Embodiment (200–228) ─────────────────────────────────────
    SensorFrameReceived = 200,
    SensorFrameDropped = 201,
    SensorCalibrationStart = 202,
    SensorCalibrationComplete = 203,
    SensorError = 204,
    SensorTimeout = 205,
    ActuatorCommandSent = 206,
    ActuatorCommandAck = 207,
    ActuatorCommandRejected = 208,
    ActuatorError = 209,
    ActuatorTimeout = 210,
    ReflexFired = 211,
    ReflexCooldown = 212,
    ReflexSafeState = 213,
    ReflexEmergencyStop = 214,
    HardwareWatchdogTrigger = 215,
    HardwareWatchdogRecovery = 216,
    CerebellarPrediction = 217,
    CerebellarErrorCorrection = 218,
    CerebellarTimingCalibration = 219,
    CerebellarMotorMemoryStored = 220,
    CerebellarMotorMemoryRecalled = 221,
    LimbicValenceShift = 222,
    LimbicAffectUpdate = 223,
    LimbicNeuromodulation = 224,
    LimbicEmotionalEvent = 225,
    LimbicOpponentProcess = 226,
    LimbicDecayCycle = 227,
    LimbicCompositeAffect = 228,

    // ── Coordination (229–232) ───────────────────────────────────
    CoordinationClaimAcquired = 229,
    CoordinationClaimReleased = 230,
    CoordinationClaimDenied = 231,
    CoordinationClaimExpired = 232,
}

impl EventType {
    /// Get the category for this event type.
    #[must_use]
    pub const fn category(self) -> EventCategory {
        let id = self as u16;
        match id {
            0..=24 => EventCategory::System,
            25..=49 => EventCategory::Memory,
            50..=74 => EventCategory::Consciousness,
            75..=99 => EventCategory::Drive,
            100..=124 => EventCategory::Harmony,
            125..=149 => EventCategory::Governance,
            150..=174 => EventCategory::Tool,
            175..=199 => EventCategory::Agent,
            200..=228 => EventCategory::Embodiment,
            229..=232 => EventCategory::Coordination,
            _ => EventCategory::System, // unreachable
        }
    }

    /// Human-readable name (snake_case).
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            // System
            Self::SystemStartup => "system_startup",
            Self::SystemShutdown => "system_shutdown",
            Self::SystemRestart => "system_restart",
            Self::SystemHealthCheck => "system_health_check",
            Self::SystemHeartbeat => "system_heartbeat",
            Self::SystemStateChange => "system_state_change",
            Self::SystemConfigUpdate => "system_config_update",
            Self::SystemError => "system_error",
            Self::SystemWarning => "system_warning",
            Self::SystemInfo => "system_info",
            Self::SystemReady => "system_ready",
            Self::SystemPaused => "system_paused",
            Self::SystemResumed => "system_resumed",
            Self::SystemCrash => "system_crash",
            Self::SystemRecovery => "system_recovery",
            Self::SystemMemoryWarning => "system_memory_warning",
            Self::SystemCpuWarning => "system_cpu_warning",
            Self::SystemDiskWarning => "system_disk_warning",
            Self::SystemThermalWarning => "system_thermal_warning",
            Self::SystemBatteryLow => "system_battery_low",
            Self::SystemUpdateAvailable => "system_update_available",
            Self::SystemMigrationStart => "system_migration_start",
            Self::SystemMigrationComplete => "system_migration_complete",
            Self::SystemBackupStart => "system_backup_start",
            Self::SystemBackupComplete => "system_backup_complete",
            // Memory
            Self::MemoryCreated => "memory_created",
            Self::MemoryUpdated => "memory_updated",
            Self::MemoryDeleted => "memory_deleted",
            Self::MemoryRead => "memory_read",
            Self::MemoryListed => "memory_listed",
            Self::MemorySearched => "memory_searched",
            Self::MemoryConsolidated => "memory_consolidated",
            Self::MemoryForgotten => "memory_forgotten",
            Self::MemoryAssociated => "memory_associated",
            Self::MemoryDisassociated => "memory_disassociated",
            Self::MemoryTagged => "memory_tagged",
            Self::MemoryUntagged => "memory_untagged",
            Self::MemoryDecayed => "memory_decayed",
            Self::MemoryBoosted => "memory_boosted",
            Self::MemoryRecalled => "memory_recalled",
            Self::MemoryEmbedded => "memory_embedded",
            Self::MemoryReembedded => "memory_reembedded",
            Self::MemoryBatchWrite => "memory_batch_write",
            Self::MemoryBatchRead => "memory_batch_read",
            Self::MemoryGalaxyCreated => "memory_galaxy_created",
            Self::MemoryGalaxyDeleted => "memory_galaxy_deleted",
            Self::MemoryGalaxyStats => "memory_galaxy_stats",
            Self::MemoryExported => "memory_exported",
            Self::MemoryImported => "memory_imported",
            Self::MemoryDeduplicated => "memory_deduplicated",
            // Consciousness
            Self::CittaAdvance => "citta_advance",
            Self::CittaDecay => "citta_decay",
            Self::CittaCoherenceMeasured => "citta_coherence_measured",
            Self::CittaValenceShift => "citta_valence_shift",
            Self::CittaHeartbeat => "citta_heartbeat",
            Self::DreamPhaseStart => "dream_phase_start",
            Self::DreamPhaseComplete => "dream_phase_complete",
            Self::DreamCycleStart => "dream_cycle_start",
            Self::DreamCycleComplete => "dream_cycle_complete",
            Self::DreamArtifactCreated => "dream_artifact_created",
            Self::DreamConsolidationStart => "dream_consolidation_start",
            Self::DreamConsolidationComplete => "dream_consolidation_complete",
            Self::SpiralUpdate => "spiral_update",
            Self::SpiralSuspension => "spiral_suspension",
            Self::SpiralRecovery => "spiral_recovery",
            Self::BrainWaveChange => "brain_wave_change",
            Self::BrainWaveGamma => "brain_wave_gamma",
            Self::BrainWaveBeta => "brain_wave_beta",
            Self::BrainWaveAlpha => "brain_wave_alpha",
            Self::BrainWaveTheta => "brain_wave_theta",
            Self::BrainWaveDelta => "brain_wave_delta",
            Self::SmaranaRecall => "smarana_recall",
            Self::SmaranaMiss => "smarana_miss",
            Self::ApotheosisUpdate => "apotheosis_update",
            Self::PresenceDetected => "presence_detected",
            // Drive
            Self::DriveCuriositySpike => "drive_curiosity_spike",
            Self::DriveCuriosityDrop => "drive_curiosity_drop",
            Self::DriveSatisfactionRise => "drive_satisfaction_rise",
            Self::DriveSatisfactionDrop => "drive_satisfaction_drop",
            Self::DriveCautionAlert => "drive_caution_alert",
            Self::DriveCautionRelease => "drive_caution_release",
            Self::DriveEnergyLow => "drive_energy_low",
            Self::DriveEnergyReplenished => "drive_energy_replenished",
            Self::DriveSocialInteraction => "drive_social_interaction",
            Self::DriveSocialIsolation => "drive_social_isolation",
            Self::DriveBiasUpdate => "drive_bias_update",
            Self::DriveDecayCycle => "drive_decay_cycle",
            Self::DriveEventProcessed => "drive_event_processed",
            Self::DriveNovelInput => "drive_novel_input",
            Self::DriveLowConfidence => "drive_low_confidence",
            Self::DriveHighConfidence => "drive_high_confidence",
            Self::DriveExplorationTrigger => "drive_exploration_trigger",
            Self::DriveRestTrigger => "drive_rest_trigger",
            Self::DriveConsolidationTrigger => "drive_consolidation_trigger",
            Self::DriveSocialTrigger => "drive_social_trigger",
            Self::DriveThresholdCrossed => "drive_threshold_crossed",
            Self::DriveBaselineReset => "drive_baseline_reset",
            Self::DriveCrossPollination => "drive_cross_pollination",
            Self::DriveWuXingImbalance => "drive_wu_xing_imbalance",
            Self::DriveWuXingCorrection => "drive_wu_xing_correction",
            // Harmony
            Self::HarmonyAnomalyDetected => "harmony_anomaly_detected",
            Self::HarmonyAnomalyWarning => "harmony_anomaly_warning",
            Self::HarmonyAnomalyCritical => "harmony_anomaly_critical",
            Self::HarmonyHomeostaticObserve => "harmony_homeostatic_observe",
            Self::HarmonyHomeostaticAdvise => "harmony_homeostatic_advise",
            Self::HarmonyHomeostaticCorrect => "harmony_homeostatic_correct",
            Self::HarmonyHomeostaticIntervene => "harmony_homeostatic_intervene",
            Self::HarmonyGunaShift => "harmony_guna_shift",
            Self::HarmonyGunaSattvic => "harmony_guna_sattvic",
            Self::HarmonyGunaRajasic => "harmony_guna_rajasic",
            Self::HarmonyGunaTamasic => "harmony_guna_tamasic",
            Self::HarmonyYinYangDrift => "harmony_yin_yang_drift",
            Self::HarmonyYinYangBalanced => "harmony_yin_yang_balanced",
            Self::HarmonyYinYangYangExcess => "harmony_yin_yang_yang_excess",
            Self::HarmonyYinYangYinExcess => "harmony_yin_yang_yin_excess",
            Self::HarmonyHealthScoreUpdate => "harmony_health_score_update",
            Self::HarmonyHealthScoreLow => "harmony_health_score_low",
            Self::HarmonyHealthScoreCritical => "harmony_health_score_critical",
            Self::HarmonyThermalAlert => "harmony_thermal_alert",
            Self::HarmonyBatteryAlert => "harmony_battery_alert",
            Self::HarmonyCpuSpike => "harmony_cpu_spike",
            Self::HarmonyMemorySpike => "harmony_memory_spike",
            Self::HarmonyDiskIoSpike => "harmony_disk_io_spike",
            Self::HarmonySwapSpike => "harmony_swap_spike",
            Self::HarmonyStressDetected => "harmony_stress_detected",
            // Governance
            Self::DharmaWarn => "dharma_warn",
            Self::DharmaBlock => "dharma_block",
            Self::DharmaAllow => "dharma_allow",
            Self::DharmaProfileChange => "dharma_profile_change",
            Self::DharmaRuleEvaluated => "dharma_rule_evaluated",
            Self::DharmaRuleAdded => "dharma_rule_added",
            Self::DharmaRuleRemoved => "dharma_rule_removed",
            Self::DharmaStrictModeEnabled => "dharma_strict_mode_enabled",
            Self::DharmaStrictModeDisabled => "dharma_strict_mode_disabled",
            Self::KarmaRecorded => "karma_recorded",
            Self::KarmaDebtUpdated => "karma_debt_updated",
            Self::KarmaDebtHigh => "karma_debt_high",
            Self::KarmaDebtCleared => "karma_debt_cleared",
            Self::KarmaChainValidated => "karma_chain_validated",
            Self::KarmaChainBroken => "karma_chain_broken",
            Self::KarmaSattvic => "karma_sattvic",
            Self::KarmaRajasic => "karma_rajasic",
            Self::KarmaTamasic => "karma_tamasic",
            Self::MandalaBreach => "mandala_breach",
            Self::MandalaCompartmentSwitch => "mandala_compartment_switch",
            Self::MandalaAccessGranted => "mandala_access_granted",
            Self::MandalaAccessDenied => "mandala_access_denied",
            Self::CircuitBreakerOpen => "circuit_breaker_open",
            Self::CircuitBreakerClose => "circuit_breaker_close",
            Self::CircuitBreakerHalfOpen => "circuit_breaker_half_open",
            // Tool
            Self::ToolDispatchStart => "tool_dispatch_start",
            Self::ToolDispatchSuccess => "tool_dispatch_success",
            Self::ToolDispatchError => "tool_dispatch_error",
            Self::ToolDispatchTimeout => "tool_dispatch_timeout",
            Self::ToolDispatchRetry => "tool_dispatch_retry",
            Self::ToolNluRoute => "tool_nlu_route",
            Self::ToolNluFallback => "tool_nlu_fallback",
            Self::ToolRegistered => "tool_registered",
            Self::ToolUnregistered => "tool_unregistered",
            Self::ToolRetired => "tool_retired",
            Self::ToolPromoted => "tool_promoted",
            Self::ToolEffectivenessLow => "tool_effectiveness_low",
            Self::ToolEffectivenessHigh => "tool_effectiveness_high",
            Self::ToolRateLimited => "tool_rate_limited",
            Self::ToolCircuitBroken => "tool_circuit_broken",
            Self::ToolStatsUpdated => "tool_stats_updated",
            Self::ToolEffectChecked => "tool_effect_checked",
            Self::ToolKarmaRecorded => "tool_karma_recorded",
            Self::ToolBatchDispatch => "tool_batch_dispatch",
            Self::ToolBatchComplete => "tool_batch_complete",
            Self::ToolCacheHit => "tool_cache_hit",
            Self::ToolCacheMiss => "tool_cache_miss",
            Self::ToolSpeculativeValidated => "tool_speculative_validated",
            Self::ToolSpeculativeRejected => "tool_speculative_rejected",
            Self::ToolSpeculativeRepaired => "tool_speculative_repaired",
            // Agent
            Self::AgentRegistered => "agent_registered",
            Self::AgentUnregistered => "agent_unregistered",
            Self::AgentHeartbeat => "agent_heartbeat",
            Self::AgentStatusUpdate => "agent_status_update",
            Self::AgentCapabilityAdvertised => "agent_capability_advertised",
            Self::PeerDiscovered => "peer_discovered",
            Self::PeerLost => "peer_lost",
            Self::PeerHealthCheck => "peer_health_check",
            Self::PeerHealthTimeout => "peer_health_timeout",
            Self::SanghaMessageSent => "sangha_message_sent",
            Self::SanghaMessageReceived => "sangha_message_received",
            Self::SanghaLockAcquired => "sangha_lock_acquired",
            Self::SanghaLockReleased => "sangha_lock_released",
            Self::SanghaLockExpired => "sangha_lock_expired",
            Self::SanghaLockDenied => "sangha_lock_denied",
            Self::SanghaLockDeadlock => "sangha_lock_deadlock",
            Self::SanghaChatJoin => "sangha_chat_join",
            Self::SanghaChatLeave => "sangha_chat_leave",
            Self::SanghaChatMessage => "sangha_chat_message",
            Self::SanghaChatTopic => "sangha_chat_topic",
            Self::SanghaFederatedMemory => "sangha_federated_memory",
            Self::SanghaConstellationMerge => "sangha_constellation_merge",
            Self::SanghaConflictResolved => "sangha_conflict_resolved",
            Self::SanghaHologramSync => "sangha_hologram_sync",
            Self::SanghaTrustUpdated => "sangha_trust_updated",
            // Embodiment
            Self::SensorFrameReceived => "sensor_frame_received",
            Self::SensorFrameDropped => "sensor_frame_dropped",
            Self::SensorCalibrationStart => "sensor_calibration_start",
            Self::SensorCalibrationComplete => "sensor_calibration_complete",
            Self::SensorError => "sensor_error",
            Self::SensorTimeout => "sensor_timeout",
            Self::ActuatorCommandSent => "actuator_command_sent",
            Self::ActuatorCommandAck => "actuator_command_ack",
            Self::ActuatorCommandRejected => "actuator_command_rejected",
            Self::ActuatorError => "actuator_error",
            Self::ActuatorTimeout => "actuator_timeout",
            Self::ReflexFired => "reflex_fired",
            Self::ReflexCooldown => "reflex_cooldown",
            Self::ReflexSafeState => "reflex_safe_state",
            Self::ReflexEmergencyStop => "reflex_emergency_stop",
            Self::HardwareWatchdogTrigger => "hardware_watchdog_trigger",
            Self::HardwareWatchdogRecovery => "hardware_watchdog_recovery",
            Self::CerebellarPrediction => "cerebellar_prediction",
            Self::CerebellarErrorCorrection => "cerebellar_error_correction",
            Self::CerebellarTimingCalibration => "cerebellar_timing_calibration",
            Self::CerebellarMotorMemoryStored => "cerebellar_motor_memory_stored",
            Self::CerebellarMotorMemoryRecalled => "cerebellar_motor_memory_recalled",
            Self::LimbicValenceShift => "limbic_valence_shift",
            Self::LimbicAffectUpdate => "limbic_affect_update",
            Self::LimbicNeuromodulation => "limbic_neuromodulation",
            Self::LimbicEmotionalEvent => "limbic_emotional_event",
            Self::LimbicOpponentProcess => "limbic_opponent_process",
            Self::LimbicDecayCycle => "limbic_decay_cycle",
            Self::LimbicCompositeAffect => "limbic_composite_affect",
            // Coordination
            Self::CoordinationClaimAcquired => "coordination_claim_acquired",
            Self::CoordinationClaimReleased => "coordination_claim_released",
            Self::CoordinationClaimDenied => "coordination_claim_denied",
            Self::CoordinationClaimExpired => "coordination_claim_expired",
        }
    }

    /// All event types in a given category.
    #[must_use]
    pub fn in_category(cat: EventCategory) -> Vec<Self> {
        Self::all()
            .into_iter()
            .filter(|e| e.category() == cat)
            .collect()
    }

    /// All 233 event types in canonical order.
    #[must_use]
    pub fn all() -> Vec<Self> {
        (0..=232u16).map(Self::from_id).collect()
    }

    /// Total number of event types.
    pub const COUNT: usize = 233;

    /// Convert from u16 id.
    #[must_use]
    const fn from_id(id: u16) -> Self {
        match id {
            0 => Self::SystemStartup,
            1 => Self::SystemShutdown,
            2 => Self::SystemRestart,
            3 => Self::SystemHealthCheck,
            4 => Self::SystemHeartbeat,
            5 => Self::SystemStateChange,
            6 => Self::SystemConfigUpdate,
            7 => Self::SystemError,
            8 => Self::SystemWarning,
            9 => Self::SystemInfo,
            10 => Self::SystemReady,
            11 => Self::SystemPaused,
            12 => Self::SystemResumed,
            13 => Self::SystemCrash,
            14 => Self::SystemRecovery,
            15 => Self::SystemMemoryWarning,
            16 => Self::SystemCpuWarning,
            17 => Self::SystemDiskWarning,
            18 => Self::SystemThermalWarning,
            19 => Self::SystemBatteryLow,
            20 => Self::SystemUpdateAvailable,
            21 => Self::SystemMigrationStart,
            22 => Self::SystemMigrationComplete,
            23 => Self::SystemBackupStart,
            24 => Self::SystemBackupComplete,
            25 => Self::MemoryCreated,
            26 => Self::MemoryUpdated,
            27 => Self::MemoryDeleted,
            28 => Self::MemoryRead,
            29 => Self::MemoryListed,
            30 => Self::MemorySearched,
            31 => Self::MemoryConsolidated,
            32 => Self::MemoryForgotten,
            33 => Self::MemoryAssociated,
            34 => Self::MemoryDisassociated,
            35 => Self::MemoryTagged,
            36 => Self::MemoryUntagged,
            37 => Self::MemoryDecayed,
            38 => Self::MemoryBoosted,
            39 => Self::MemoryRecalled,
            40 => Self::MemoryEmbedded,
            41 => Self::MemoryReembedded,
            42 => Self::MemoryBatchWrite,
            43 => Self::MemoryBatchRead,
            44 => Self::MemoryGalaxyCreated,
            45 => Self::MemoryGalaxyDeleted,
            46 => Self::MemoryGalaxyStats,
            47 => Self::MemoryExported,
            48 => Self::MemoryImported,
            49 => Self::MemoryDeduplicated,
            50 => Self::CittaAdvance,
            51 => Self::CittaDecay,
            52 => Self::CittaCoherenceMeasured,
            53 => Self::CittaValenceShift,
            54 => Self::CittaHeartbeat,
            55 => Self::DreamPhaseStart,
            56 => Self::DreamPhaseComplete,
            57 => Self::DreamCycleStart,
            58 => Self::DreamCycleComplete,
            59 => Self::DreamArtifactCreated,
            60 => Self::DreamConsolidationStart,
            61 => Self::DreamConsolidationComplete,
            62 => Self::SpiralUpdate,
            63 => Self::SpiralSuspension,
            64 => Self::SpiralRecovery,
            65 => Self::BrainWaveChange,
            66 => Self::BrainWaveGamma,
            67 => Self::BrainWaveBeta,
            68 => Self::BrainWaveAlpha,
            69 => Self::BrainWaveTheta,
            70 => Self::BrainWaveDelta,
            71 => Self::SmaranaRecall,
            72 => Self::SmaranaMiss,
            73 => Self::ApotheosisUpdate,
            74 => Self::PresenceDetected,
            75 => Self::DriveCuriositySpike,
            76 => Self::DriveCuriosityDrop,
            77 => Self::DriveSatisfactionRise,
            78 => Self::DriveSatisfactionDrop,
            79 => Self::DriveCautionAlert,
            80 => Self::DriveCautionRelease,
            81 => Self::DriveEnergyLow,
            82 => Self::DriveEnergyReplenished,
            83 => Self::DriveSocialInteraction,
            84 => Self::DriveSocialIsolation,
            85 => Self::DriveBiasUpdate,
            86 => Self::DriveDecayCycle,
            87 => Self::DriveEventProcessed,
            88 => Self::DriveNovelInput,
            89 => Self::DriveLowConfidence,
            90 => Self::DriveHighConfidence,
            91 => Self::DriveExplorationTrigger,
            92 => Self::DriveRestTrigger,
            93 => Self::DriveConsolidationTrigger,
            94 => Self::DriveSocialTrigger,
            95 => Self::DriveThresholdCrossed,
            96 => Self::DriveBaselineReset,
            97 => Self::DriveCrossPollination,
            98 => Self::DriveWuXingImbalance,
            99 => Self::DriveWuXingCorrection,
            100 => Self::HarmonyAnomalyDetected,
            101 => Self::HarmonyAnomalyWarning,
            102 => Self::HarmonyAnomalyCritical,
            103 => Self::HarmonyHomeostaticObserve,
            104 => Self::HarmonyHomeostaticAdvise,
            105 => Self::HarmonyHomeostaticCorrect,
            106 => Self::HarmonyHomeostaticIntervene,
            107 => Self::HarmonyGunaShift,
            108 => Self::HarmonyGunaSattvic,
            109 => Self::HarmonyGunaRajasic,
            110 => Self::HarmonyGunaTamasic,
            111 => Self::HarmonyYinYangDrift,
            112 => Self::HarmonyYinYangBalanced,
            113 => Self::HarmonyYinYangYangExcess,
            114 => Self::HarmonyYinYangYinExcess,
            115 => Self::HarmonyHealthScoreUpdate,
            116 => Self::HarmonyHealthScoreLow,
            117 => Self::HarmonyHealthScoreCritical,
            118 => Self::HarmonyThermalAlert,
            119 => Self::HarmonyBatteryAlert,
            120 => Self::HarmonyCpuSpike,
            121 => Self::HarmonyMemorySpike,
            122 => Self::HarmonyDiskIoSpike,
            123 => Self::HarmonySwapSpike,
            124 => Self::HarmonyStressDetected,
            125 => Self::DharmaWarn,
            126 => Self::DharmaBlock,
            127 => Self::DharmaAllow,
            128 => Self::DharmaProfileChange,
            129 => Self::DharmaRuleEvaluated,
            130 => Self::DharmaRuleAdded,
            131 => Self::DharmaRuleRemoved,
            132 => Self::DharmaStrictModeEnabled,
            133 => Self::DharmaStrictModeDisabled,
            134 => Self::KarmaRecorded,
            135 => Self::KarmaDebtUpdated,
            136 => Self::KarmaDebtHigh,
            137 => Self::KarmaDebtCleared,
            138 => Self::KarmaChainValidated,
            139 => Self::KarmaChainBroken,
            140 => Self::KarmaSattvic,
            141 => Self::KarmaRajasic,
            142 => Self::KarmaTamasic,
            143 => Self::MandalaBreach,
            144 => Self::MandalaCompartmentSwitch,
            145 => Self::MandalaAccessGranted,
            146 => Self::MandalaAccessDenied,
            147 => Self::CircuitBreakerOpen,
            148 => Self::CircuitBreakerClose,
            149 => Self::CircuitBreakerHalfOpen,
            150 => Self::ToolDispatchStart,
            151 => Self::ToolDispatchSuccess,
            152 => Self::ToolDispatchError,
            153 => Self::ToolDispatchTimeout,
            154 => Self::ToolDispatchRetry,
            155 => Self::ToolNluRoute,
            156 => Self::ToolNluFallback,
            157 => Self::ToolRegistered,
            158 => Self::ToolUnregistered,
            159 => Self::ToolRetired,
            160 => Self::ToolPromoted,
            161 => Self::ToolEffectivenessLow,
            162 => Self::ToolEffectivenessHigh,
            163 => Self::ToolRateLimited,
            164 => Self::ToolCircuitBroken,
            165 => Self::ToolStatsUpdated,
            166 => Self::ToolEffectChecked,
            167 => Self::ToolKarmaRecorded,
            168 => Self::ToolBatchDispatch,
            169 => Self::ToolBatchComplete,
            170 => Self::ToolCacheHit,
            171 => Self::ToolCacheMiss,
            172 => Self::ToolSpeculativeValidated,
            173 => Self::ToolSpeculativeRejected,
            174 => Self::ToolSpeculativeRepaired,
            175 => Self::AgentRegistered,
            176 => Self::AgentUnregistered,
            177 => Self::AgentHeartbeat,
            178 => Self::AgentStatusUpdate,
            179 => Self::AgentCapabilityAdvertised,
            180 => Self::PeerDiscovered,
            181 => Self::PeerLost,
            182 => Self::PeerHealthCheck,
            183 => Self::PeerHealthTimeout,
            184 => Self::SanghaMessageSent,
            185 => Self::SanghaMessageReceived,
            186 => Self::SanghaLockAcquired,
            187 => Self::SanghaLockReleased,
            188 => Self::SanghaLockExpired,
            189 => Self::SanghaLockDenied,
            190 => Self::SanghaLockDeadlock,
            191 => Self::SanghaChatJoin,
            192 => Self::SanghaChatLeave,
            193 => Self::SanghaChatMessage,
            194 => Self::SanghaChatTopic,
            195 => Self::SanghaFederatedMemory,
            196 => Self::SanghaConstellationMerge,
            197 => Self::SanghaConflictResolved,
            198 => Self::SanghaHologramSync,
            199 => Self::SanghaTrustUpdated,
            200 => Self::SensorFrameReceived,
            201 => Self::SensorFrameDropped,
            202 => Self::SensorCalibrationStart,
            203 => Self::SensorCalibrationComplete,
            204 => Self::SensorError,
            205 => Self::SensorTimeout,
            206 => Self::ActuatorCommandSent,
            207 => Self::ActuatorCommandAck,
            208 => Self::ActuatorCommandRejected,
            209 => Self::ActuatorError,
            210 => Self::ActuatorTimeout,
            211 => Self::ReflexFired,
            212 => Self::ReflexCooldown,
            213 => Self::ReflexSafeState,
            214 => Self::ReflexEmergencyStop,
            215 => Self::HardwareWatchdogTrigger,
            216 => Self::HardwareWatchdogRecovery,
            217 => Self::CerebellarPrediction,
            218 => Self::CerebellarErrorCorrection,
            219 => Self::CerebellarTimingCalibration,
            220 => Self::CerebellarMotorMemoryStored,
            221 => Self::CerebellarMotorMemoryRecalled,
            222 => Self::LimbicValenceShift,
            223 => Self::LimbicAffectUpdate,
            224 => Self::LimbicNeuromodulation,
            225 => Self::LimbicEmotionalEvent,
            226 => Self::LimbicOpponentProcess,
            227 => Self::LimbicDecayCycle,
            228 => Self::LimbicCompositeAffect,
            229 => Self::CoordinationClaimAcquired,
            230 => Self::CoordinationClaimReleased,
            231 => Self::CoordinationClaimDenied,
            232 => Self::CoordinationClaimExpired,
            _ => Self::SystemStartup, // unreachable
        }
    }
}

impl std::fmt::Display for EventType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn event_count_is_233() {
        assert_eq!(EventType::all().len(), 233);
        assert_eq!(EventType::COUNT, 233);
    }

    #[test]
    fn categories_are_10() {
        assert_eq!(EventCategory::ALL.len(), 10);
    }

    #[test]
    fn category_names() {
        assert_eq!(EventCategory::System.as_str(), "system");
        assert_eq!(EventCategory::Memory.as_str(), "memory");
        assert_eq!(EventCategory::Consciousness.as_str(), "consciousness");
        assert_eq!(EventCategory::Drive.as_str(), "drive");
        assert_eq!(EventCategory::Harmony.as_str(), "harmony");
        assert_eq!(EventCategory::Governance.as_str(), "governance");
        assert_eq!(EventCategory::Tool.as_str(), "tool");
        assert_eq!(EventCategory::Agent.as_str(), "agent");
        assert_eq!(EventCategory::Embodiment.as_str(), "embodiment");
        assert_eq!(EventCategory::Coordination.as_str(), "coordination");
    }

    #[test]
    fn event_category_mapping() {
        assert_eq!(EventType::SystemStartup.category(), EventCategory::System);
        assert_eq!(
            EventType::SystemBackupComplete.category(),
            EventCategory::System
        );
        assert_eq!(EventType::MemoryCreated.category(), EventCategory::Memory);
        assert_eq!(
            EventType::MemoryDeduplicated.category(),
            EventCategory::Memory
        );
        assert_eq!(
            EventType::CittaAdvance.category(),
            EventCategory::Consciousness
        );
        assert_eq!(
            EventType::PresenceDetected.category(),
            EventCategory::Consciousness
        );
        assert_eq!(
            EventType::DriveCuriositySpike.category(),
            EventCategory::Drive
        );
        assert_eq!(
            EventType::DriveWuXingCorrection.category(),
            EventCategory::Drive
        );
        assert_eq!(
            EventType::HarmonyAnomalyDetected.category(),
            EventCategory::Harmony
        );
        assert_eq!(
            EventType::HarmonyStressDetected.category(),
            EventCategory::Harmony
        );
        assert_eq!(EventType::DharmaWarn.category(), EventCategory::Governance);
        assert_eq!(
            EventType::CircuitBreakerHalfOpen.category(),
            EventCategory::Governance
        );
        assert_eq!(EventType::ToolDispatchStart.category(), EventCategory::Tool);
        assert_eq!(
            EventType::ToolSpeculativeRepaired.category(),
            EventCategory::Tool
        );
        assert_eq!(EventType::AgentRegistered.category(), EventCategory::Agent);
        assert_eq!(
            EventType::SanghaTrustUpdated.category(),
            EventCategory::Agent
        );
        assert_eq!(
            EventType::SensorFrameReceived.category(),
            EventCategory::Embodiment
        );
        assert_eq!(
            EventType::LimbicCompositeAffect.category(),
            EventCategory::Embodiment
        );
        assert_eq!(
            EventType::CoordinationClaimAcquired.category(),
            EventCategory::Coordination
        );
        assert_eq!(
            EventType::CoordinationClaimExpired.category(),
            EventCategory::Coordination
        );
    }

    #[test]
    fn in_category_counts() {
        assert_eq!(EventType::in_category(EventCategory::System).len(), 25);
        assert_eq!(EventType::in_category(EventCategory::Memory).len(), 25);
        assert_eq!(
            EventType::in_category(EventCategory::Consciousness).len(),
            25
        );
        assert_eq!(EventType::in_category(EventCategory::Drive).len(), 25);
        assert_eq!(EventType::in_category(EventCategory::Harmony).len(), 25);
        assert_eq!(EventType::in_category(EventCategory::Governance).len(), 25);
        assert_eq!(EventType::in_category(EventCategory::Tool).len(), 25);
        assert_eq!(EventType::in_category(EventCategory::Agent).len(), 25);
        assert_eq!(EventType::in_category(EventCategory::Embodiment).len(), 29);
        assert_eq!(EventType::in_category(EventCategory::Coordination).len(), 4);
    }

    #[test]
    fn all_events_have_unique_names() {
        let names: Vec<&str> = EventType::all().iter().map(|e| e.as_str()).collect();
        let unique: std::collections::HashSet<&str> = names.iter().copied().collect();
        assert_eq!(names.len(), unique.len(), "Duplicate event names found");
    }

    #[test]
    fn event_type_display() {
        assert_eq!(format!("{}", EventType::SystemStartup), "system_startup");
        assert_eq!(format!("{}", EventType::MemoryCreated), "memory_created");
        assert_eq!(format!("{}", EventType::CittaAdvance), "citta_advance");
    }

    #[test]
    fn category_display() {
        assert_eq!(format!("{}", EventCategory::System), "system");
        assert_eq!(format!("{}", EventCategory::Embodiment), "embodiment");
    }
}
