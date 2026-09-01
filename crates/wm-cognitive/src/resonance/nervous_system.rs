//! Unified Nervous System — 7-subsystem architecture for the Gan Ying Bus.
//!
//! Maps the 233 event types to 7 biological nervous system analogs,
//! providing a structured way to route events through the appropriate
//! processing pipeline.
//!
//! The 7 subsystems:
//! 1. **Central Nervous System** — consciousness, cognition, decision
//! 2. **Autonomic Nervous System** — heartbeat, breathing, homeostasis
//! 3. **Sensory Nervous System** — input, perception, salience
//! 4. **Motor Nervous System** — output, action, actuation
//! 5. **Enteric Nervous System** — digestion, memory consolidation, dreaming
//! 6. **Endocrine System** — drives, hormones, neuromodulation
//! 7. **Immune System** — governance, dharma, karma, circuit breakers

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

use crate::resonance::event_type::{EventCategory, EventType};

// ── Nervous Subsystem ─────────────────────────────────────────────────

/// The 7 subsystems of the Unified Nervous System.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum NervousSubsystem {
    /// Central Nervous System — consciousness, cognition, decision-making.
    Central = 0,
    /// Autonomic Nervous System — heartbeat, breathing, homeostasis.
    Autonomic = 1,
    /// Sensory Nervous System — input, perception, salience filtering.
    Sensory = 2,
    /// Motor Nervous System — output, action, actuation.
    Motor = 3,
    /// Enteric Nervous System — digestion, memory consolidation, dreaming.
    Enteric = 4,
    /// Endocrine System — drives, hormones, neuromodulation.
    Endocrine = 5,
    /// Immune System — governance, dharma, karma, circuit breakers.
    Immune = 6,
}

impl NervousSubsystem {
    /// All 7 subsystems in canonical order.
    pub const ALL: [Self; 7] = [
        Self::Central,
        Self::Autonomic,
        Self::Sensory,
        Self::Motor,
        Self::Enteric,
        Self::Endocrine,
        Self::Immune,
    ];

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Central => "central",
            Self::Autonomic => "autonomic",
            Self::Sensory => "sensory",
            Self::Motor => "motor",
            Self::Enteric => "enteric",
            Self::Endocrine => "endocrine",
            Self::Immune => "immune",
        }
    }

    /// Biological analog description.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::Central => "Central Nervous System — consciousness, cognition, decision-making",
            Self::Autonomic => "Autonomic Nervous System — heartbeat, breathing, homeostasis",
            Self::Sensory => "Sensory Nervous System — input, perception, salience filtering",
            Self::Motor => "Motor Nervous System — output, action, actuation",
            Self::Enteric => "Enteric Nervous System — digestion, memory consolidation, dreaming",
            Self::Endocrine => "Endocrine System — drives, hormones, neuromodulation",
            Self::Immune => "Immune System — governance, dharma, karma, circuit breakers",
        }
    }

    /// Map an event type to its nervous subsystem.
    ///
    /// This mapping is based on the biological function each event type
    /// represents:
    /// - **Central**: consciousness events (citta, dream, spiral, brain-wave)
    /// - **Autonomic**: system events (heartbeat, health, state changes)
    /// - **Sensory**: memory read/search, sensor frames, harmony monitoring
    /// - **Motor**: memory write/delete, actuator commands, tool dispatch
    /// - **Enteric**: memory consolidation, dream consolidation, forgetting
    /// - **Endocrine**: drive events, limbic events, neuromodulation
    /// - **Immune**: governance events (dharma, karma, mandala, circuit breaker)
    #[must_use]
    pub const fn from_event_type(event_type: EventType) -> Self {
        match event_type {
            // Central — consciousness, cognition
            EventType::CittaAdvance
            | EventType::CittaDecay
            | EventType::CittaCoherenceMeasured
            | EventType::CittaValenceShift
            | EventType::CittaHeartbeat
            | EventType::SpiralUpdate
            | EventType::SpiralSuspension
            | EventType::SpiralRecovery
            | EventType::BrainWaveChange
            | EventType::BrainWaveGamma
            | EventType::BrainWaveBeta
            | EventType::BrainWaveAlpha
            | EventType::BrainWaveTheta
            | EventType::BrainWaveDelta
            | EventType::SmaranaRecall
            | EventType::SmaranaMiss
            | EventType::ApotheosisUpdate
            | EventType::PresenceDetected => Self::Central,

            // Autonomic — system lifecycle, heartbeat
            EventType::SystemStartup
            | EventType::SystemShutdown
            | EventType::SystemRestart
            | EventType::SystemHealthCheck
            | EventType::SystemHeartbeat
            | EventType::SystemStateChange
            | EventType::SystemConfigUpdate
            | EventType::SystemError
            | EventType::SystemWarning
            | EventType::SystemInfo
            | EventType::SystemReady
            | EventType::SystemPaused
            | EventType::SystemResumed
            | EventType::SystemCrash
            | EventType::SystemRecovery
            | EventType::SystemMemoryWarning
            | EventType::SystemCpuWarning
            | EventType::SystemDiskWarning
            | EventType::SystemThermalWarning
            | EventType::SystemBatteryLow
            | EventType::SystemUpdateAvailable
            | EventType::SystemMigrationStart
            | EventType::SystemMigrationComplete
            | EventType::SystemBackupStart
            | EventType::SystemBackupComplete => Self::Autonomic,

            // Sensory — input, perception, monitoring
            EventType::MemoryRead
            | EventType::MemoryListed
            | EventType::MemorySearched
            | EventType::MemoryRecalled
            | EventType::MemoryBatchRead
            | EventType::MemoryGalaxyStats
            | EventType::HarmonyAnomalyDetected
            | EventType::HarmonyAnomalyWarning
            | EventType::HarmonyAnomalyCritical
            | EventType::HarmonyHomeostaticObserve
            | EventType::HarmonyGunaShift
            | EventType::HarmonyGunaSattvic
            | EventType::HarmonyGunaRajasic
            | EventType::HarmonyGunaTamasic
            | EventType::HarmonyYinYangDrift
            | EventType::HarmonyYinYangBalanced
            | EventType::HarmonyYinYangYangExcess
            | EventType::HarmonyYinYangYinExcess
            | EventType::HarmonyHealthScoreUpdate
            | EventType::HarmonyHealthScoreLow
            | EventType::HarmonyHealthScoreCritical
            | EventType::HarmonyThermalAlert
            | EventType::HarmonyBatteryAlert
            | EventType::HarmonyCpuSpike
            | EventType::HarmonyMemorySpike
            | EventType::HarmonyDiskIoSpike
            | EventType::HarmonySwapSpike
            | EventType::HarmonyStressDetected
            | EventType::SensorFrameReceived
            | EventType::SensorFrameDropped
            | EventType::SensorCalibrationStart
            | EventType::SensorCalibrationComplete
            | EventType::SensorError
            | EventType::SensorTimeout
            | EventType::CerebellarPrediction
            | EventType::CerebellarErrorCorrection
            | EventType::CerebellarTimingCalibration
            | EventType::CerebellarMotorMemoryRecalled => Self::Sensory,

            // Motor — output, action
            EventType::MemoryCreated
            | EventType::MemoryUpdated
            | EventType::MemoryDeleted
            | EventType::MemoryTagged
            | EventType::MemoryUntagged
            | EventType::MemoryBatchWrite
            | EventType::MemoryGalaxyCreated
            | EventType::MemoryGalaxyDeleted
            | EventType::MemoryExported
            | EventType::MemoryImported
            | EventType::ActuatorCommandSent
            | EventType::ActuatorCommandAck
            | EventType::ActuatorCommandRejected
            | EventType::ActuatorError
            | EventType::ActuatorTimeout
            | EventType::ReflexFired
            | EventType::ReflexCooldown
            | EventType::ReflexSafeState
            | EventType::ReflexEmergencyStop
            | EventType::HardwareWatchdogTrigger
            | EventType::HardwareWatchdogRecovery
            | EventType::CerebellarMotorMemoryStored
            | EventType::ToolDispatchStart
            | EventType::ToolDispatchSuccess
            | EventType::ToolDispatchError
            | EventType::ToolDispatchTimeout
            | EventType::ToolDispatchRetry
            | EventType::ToolNluRoute
            | EventType::ToolNluFallback
            | EventType::ToolRegistered
            | EventType::ToolUnregistered
            | EventType::ToolRetired
            | EventType::ToolPromoted
            | EventType::ToolEffectivenessLow
            | EventType::ToolEffectivenessHigh
            | EventType::ToolRateLimited
            | EventType::ToolCircuitBroken
            | EventType::ToolStatsUpdated
            | EventType::ToolEffectChecked
            | EventType::ToolKarmaRecorded
            | EventType::ToolBatchDispatch
            | EventType::ToolBatchComplete
            | EventType::ToolCacheHit
            | EventType::ToolCacheMiss
            | EventType::ToolSpeculativeValidated
            | EventType::ToolSpeculativeRejected
            | EventType::ToolSpeculativeRepaired
            | EventType::SanghaMessageSent
            | EventType::SanghaLockAcquired
            | EventType::SanghaLockReleased
            | EventType::SanghaLockExpired
            | EventType::SanghaLockDenied
            | EventType::SanghaLockDeadlock
            | EventType::SanghaChatJoin
            | EventType::SanghaChatLeave
            | EventType::SanghaChatMessage
            | EventType::SanghaChatTopic
            | EventType::SanghaFederatedMemory
            | EventType::SanghaConstellationMerge
            | EventType::SanghaConflictResolved
            | EventType::SanghaHologramSync
            | EventType::HarmonyHomeostaticCorrect
            | EventType::HarmonyHomeostaticIntervene
            | EventType::HarmonyHomeostaticAdvise => Self::Motor,

            // Enteric — digestion, consolidation, dreaming
            EventType::MemoryConsolidated
            | EventType::MemoryForgotten
            | EventType::MemoryAssociated
            | EventType::MemoryDisassociated
            | EventType::MemoryDecayed
            | EventType::MemoryBoosted
            | EventType::MemoryEmbedded
            | EventType::MemoryReembedded
            | EventType::MemoryDeduplicated
            | EventType::DreamPhaseStart
            | EventType::DreamPhaseComplete
            | EventType::DreamCycleStart
            | EventType::DreamCycleComplete
            | EventType::DreamArtifactCreated
            | EventType::DreamConsolidationStart
            | EventType::DreamConsolidationComplete => Self::Enteric,

            // Endocrine — drives, hormones, neuromodulation
            EventType::DriveCuriositySpike
            | EventType::DriveCuriosityDrop
            | EventType::DriveSatisfactionRise
            | EventType::DriveSatisfactionDrop
            | EventType::DriveCautionAlert
            | EventType::DriveCautionRelease
            | EventType::DriveEnergyLow
            | EventType::DriveEnergyReplenished
            | EventType::DriveSocialInteraction
            | EventType::DriveSocialIsolation
            | EventType::DriveBiasUpdate
            | EventType::DriveDecayCycle
            | EventType::DriveEventProcessed
            | EventType::DriveNovelInput
            | EventType::DriveLowConfidence
            | EventType::DriveHighConfidence
            | EventType::DriveExplorationTrigger
            | EventType::DriveRestTrigger
            | EventType::DriveConsolidationTrigger
            | EventType::DriveSocialTrigger
            | EventType::DriveThresholdCrossed
            | EventType::DriveBaselineReset
            | EventType::DriveCrossPollination
            | EventType::DriveWuXingImbalance
            | EventType::DriveWuXingCorrection
            | EventType::LimbicValenceShift
            | EventType::LimbicAffectUpdate
            | EventType::LimbicNeuromodulation
            | EventType::LimbicEmotionalEvent
            | EventType::LimbicOpponentProcess
            | EventType::LimbicDecayCycle
            | EventType::LimbicCompositeAffect
            | EventType::AgentRegistered
            | EventType::AgentUnregistered
            | EventType::AgentHeartbeat
            | EventType::AgentStatusUpdate
            | EventType::AgentCapabilityAdvertised
            | EventType::PeerDiscovered
            | EventType::PeerLost
            | EventType::PeerHealthCheck
            | EventType::PeerHealthTimeout
            | EventType::SanghaMessageReceived
            | EventType::SanghaTrustUpdated
            | EventType::CoordinationClaimAcquired
            | EventType::CoordinationClaimReleased
            | EventType::CoordinationClaimDenied
            | EventType::CoordinationClaimExpired => Self::Endocrine,

            // Immune — governance, defense
            EventType::DharmaWarn
            | EventType::DharmaBlock
            | EventType::DharmaAllow
            | EventType::DharmaProfileChange
            | EventType::DharmaRuleEvaluated
            | EventType::DharmaRuleAdded
            | EventType::DharmaRuleRemoved
            | EventType::DharmaStrictModeEnabled
            | EventType::DharmaStrictModeDisabled
            | EventType::KarmaRecorded
            | EventType::KarmaDebtUpdated
            | EventType::KarmaDebtHigh
            | EventType::KarmaDebtCleared
            | EventType::KarmaChainValidated
            | EventType::KarmaChainBroken
            | EventType::KarmaSattvic
            | EventType::KarmaRajasic
            | EventType::KarmaTamasic
            | EventType::MandalaBreach
            | EventType::MandalaCompartmentSwitch
            | EventType::MandalaAccessGranted
            | EventType::MandalaAccessDenied
            | EventType::CircuitBreakerOpen
            | EventType::CircuitBreakerClose
            | EventType::CircuitBreakerHalfOpen => Self::Immune,
        }
    }

    /// Map an event category to its primary nervous subsystem.
    #[must_use]
    pub const fn from_category(category: EventCategory) -> Self {
        match category {
            EventCategory::System => Self::Autonomic,
            EventCategory::Memory => Self::Enteric,
            EventCategory::Consciousness => Self::Central,
            EventCategory::Drive => Self::Endocrine,
            EventCategory::Harmony => Self::Sensory,
            EventCategory::Governance => Self::Immune,
            EventCategory::Tool => Self::Motor,
            EventCategory::Agent => Self::Endocrine,
            EventCategory::Embodiment => Self::Sensory,
            EventCategory::Coordination => Self::Endocrine,
        }
    }
}

impl std::fmt::Display for NervousSubsystem {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// ── Subsystem Health ──────────────────────────────────────────────────

/// Health status of a nervous subsystem.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubsystemHealth {
    /// The subsystem.
    pub subsystem: NervousSubsystem,
    /// Number of events processed.
    pub events_processed: u64,
    /// Number of errors encountered.
    pub errors: u64,
    /// Last activity timestamp (Unix seconds).
    pub last_activity: i64,
    /// Whether the subsystem is active.
    pub active: bool,
}

impl SubsystemHealth {
    /// Create a new health tracker for a subsystem.
    #[must_use]
    pub const fn new(subsystem: NervousSubsystem) -> Self {
        Self {
            subsystem,
            events_processed: 0,
            errors: 0,
            last_activity: 0,
            active: false,
        }
    }

    /// Record an event processed by this subsystem.
    pub fn record_event(&mut self, is_error: bool) {
        self.events_processed += 1;
        if is_error {
            self.errors += 1;
        }
        self.last_activity = chrono::Utc::now().timestamp();
        self.active = true;
    }

    /// Error rate (0.0–1.0).
    #[must_use]
    pub fn error_rate(&self) -> f32 {
        if self.events_processed == 0 {
            0.0
        } else {
            self.errors as f32 / self.events_processed as f32
        }
    }

    /// Whether this subsystem is healthy (error rate < 0.1).
    #[must_use]
    pub fn is_healthy(&self) -> bool {
        self.error_rate() < 0.1
    }
}

// ── Unified Nervous System ────────────────────────────────────────────

/// The Unified Nervous System — routes events through 7 biological subsystems.
///
/// Each event type maps to exactly one subsystem. The system tracks
/// per-subsystem health and provides routing metadata.
pub struct UnifiedNervousSystem {
    health: [SubsystemHealth; 7],
}

impl Default for UnifiedNervousSystem {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for UnifiedNervousSystem {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("UnifiedNervousSystem")
            .field(
                "subsystems",
                &self
                    .health
                    .iter()
                    .map(|h| (h.subsystem.as_str(), h.events_processed))
                    .collect::<Vec<_>>(),
            )
            .finish()
    }
}

impl UnifiedNervousSystem {
    /// Create a new Unified Nervous System with all 7 subsystems initialized.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            health: [
                SubsystemHealth::new(NervousSubsystem::Central),
                SubsystemHealth::new(NervousSubsystem::Autonomic),
                SubsystemHealth::new(NervousSubsystem::Sensory),
                SubsystemHealth::new(NervousSubsystem::Motor),
                SubsystemHealth::new(NervousSubsystem::Enteric),
                SubsystemHealth::new(NervousSubsystem::Endocrine),
                SubsystemHealth::new(NervousSubsystem::Immune),
            ],
        }
    }

    /// Route an event to its subsystem and record the activity.
    pub fn route(&mut self, event_type: EventType, is_error: bool) -> NervousSubsystem {
        let subsystem = NervousSubsystem::from_event_type(event_type);
        let idx = subsystem as usize;
        self.health[idx].record_event(is_error);
        subsystem
    }

    /// Get the health status for a subsystem.
    #[must_use]
    pub const fn health(&self, subsystem: NervousSubsystem) -> &SubsystemHealth {
        &self.health[subsystem as usize]
    }

    /// Get health for all subsystems.
    #[must_use]
    pub const fn all_health(&self) -> &[SubsystemHealth; 7] {
        &self.health
    }

    /// Get a JSON summary of the nervous system state.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        let subsystems: Vec<serde_json::Value> = self
            .health
            .iter()
            .map(|h| {
                serde_json::json!({
                    "subsystem": h.subsystem.as_str(),
                    "description": h.subsystem.description(),
                    "events_processed": h.events_processed,
                    "errors": h.errors,
                    "error_rate": h.error_rate(),
                    "healthy": h.is_healthy(),
                    "active": h.active,
                    "last_activity": h.last_activity,
                })
            })
            .collect();

        serde_json::json!({
            "subsystems": subsystems,
            "total_events": self.health.iter().map(|h| h.events_processed).sum::<u64>(),
            "total_errors": self.health.iter().map(|h| h.errors).sum::<u64>(),
        })
    }

    /// Get the subsystem for an event type without recording.
    #[must_use]
    pub const fn subsystem_for(event_type: EventType) -> NervousSubsystem {
        NervousSubsystem::from_event_type(event_type)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seven_subsystems() {
        assert_eq!(NervousSubsystem::ALL.len(), 7);
    }

    #[test]
    fn subsystem_names() {
        assert_eq!(NervousSubsystem::Central.as_str(), "central");
        assert_eq!(NervousSubsystem::Autonomic.as_str(), "autonomic");
        assert_eq!(NervousSubsystem::Sensory.as_str(), "sensory");
        assert_eq!(NervousSubsystem::Motor.as_str(), "motor");
        assert_eq!(NervousSubsystem::Enteric.as_str(), "enteric");
        assert_eq!(NervousSubsystem::Endocrine.as_str(), "endocrine");
        assert_eq!(NervousSubsystem::Immune.as_str(), "immune");
    }

    #[test]
    fn consciousness_events_map_to_central() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::CittaAdvance),
            NervousSubsystem::Central
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::BrainWaveTheta),
            NervousSubsystem::Central
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::SpiralUpdate),
            NervousSubsystem::Central
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::PresenceDetected),
            NervousSubsystem::Central
        );
    }

    #[test]
    fn system_events_map_to_autonomic() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::SystemStartup),
            NervousSubsystem::Autonomic
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::SystemHeartbeat),
            NervousSubsystem::Autonomic
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::SystemCrash),
            NervousSubsystem::Autonomic
        );
    }

    #[test]
    fn sensor_harmony_events_map_to_sensory() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::SensorFrameReceived),
            NervousSubsystem::Sensory
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::HarmonyAnomalyDetected),
            NervousSubsystem::Sensory
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::HarmonyCpuSpike),
            NervousSubsystem::Sensory
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::MemoryRead),
            NervousSubsystem::Sensory
        );
    }

    #[test]
    fn tool_actuator_events_map_to_motor() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::ToolDispatchStart),
            NervousSubsystem::Motor
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::ActuatorCommandSent),
            NervousSubsystem::Motor
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::ReflexFired),
            NervousSubsystem::Motor
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::MemoryCreated),
            NervousSubsystem::Motor
        );
    }

    #[test]
    fn consolidation_dream_events_map_to_enteric() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::MemoryConsolidated),
            NervousSubsystem::Enteric
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::DreamCycleStart),
            NervousSubsystem::Enteric
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::MemoryForgotten),
            NervousSubsystem::Enteric
        );
    }

    #[test]
    fn drive_limbic_events_map_to_endocrine() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::DriveCuriositySpike),
            NervousSubsystem::Endocrine
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::LimbicValenceShift),
            NervousSubsystem::Endocrine
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::DriveEnergyLow),
            NervousSubsystem::Endocrine
        );
    }

    #[test]
    fn governance_events_map_to_immune() {
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::DharmaWarn),
            NervousSubsystem::Immune
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::KarmaRecorded),
            NervousSubsystem::Immune
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::CircuitBreakerOpen),
            NervousSubsystem::Immune
        );
        assert_eq!(
            NervousSubsystem::from_event_type(EventType::MandalaBreach),
            NervousSubsystem::Immune
        );
    }

    #[test]
    fn category_to_subsystem_mapping() {
        assert_eq!(
            NervousSubsystem::from_category(EventCategory::System),
            NervousSubsystem::Autonomic
        );
        assert_eq!(
            NervousSubsystem::from_category(EventCategory::Consciousness),
            NervousSubsystem::Central
        );
        assert_eq!(
            NervousSubsystem::from_category(EventCategory::Harmony),
            NervousSubsystem::Sensory
        );
        assert_eq!(
            NervousSubsystem::from_category(EventCategory::Governance),
            NervousSubsystem::Immune
        );
        assert_eq!(
            NervousSubsystem::from_category(EventCategory::Drive),
            NervousSubsystem::Endocrine
        );
    }

    #[test]
    fn all_233_events_map_to_a_subsystem() {
        for event_type in EventType::all() {
            let subsystem = NervousSubsystem::from_event_type(event_type);
            // Just ensure it doesn't panic — all events must be covered
            assert!(NervousSubsystem::ALL.contains(&subsystem));
        }
    }

    #[test]
    fn uns_routes_events() {
        let mut uns = UnifiedNervousSystem::new();

        let s1 = uns.route(EventType::CittaAdvance, false);
        assert_eq!(s1, NervousSubsystem::Central);

        let s2 = uns.route(EventType::ToolDispatchError, true);
        assert_eq!(s2, NervousSubsystem::Motor);

        assert_eq!(uns.health(NervousSubsystem::Central).events_processed, 1);
        assert_eq!(uns.health(NervousSubsystem::Motor).events_processed, 1);
        assert_eq!(uns.health(NervousSubsystem::Motor).errors, 1);
    }

    #[test]
    fn uns_health_error_rate() {
        let mut health = SubsystemHealth::new(NervousSubsystem::Central);
        health.record_event(false);
        health.record_event(false);
        health.record_event(true);
        assert_eq!(health.error_rate(), 1.0 / 3.0);
        // 33% error rate is above 10% threshold, so NOT healthy
        assert!(!health.is_healthy());
    }

    #[test]
    fn uns_health_unhealthy() {
        let mut health = SubsystemHealth::new(NervousSubsystem::Motor);
        for _ in 0..8 {
            health.record_event(true);
        }
        for _ in 0..2 {
            health.record_event(false);
        }
        assert!(!health.is_healthy());
    }

    #[test]
    fn uns_summary() {
        let mut uns = UnifiedNervousSystem::new();
        uns.route(EventType::SystemStartup, false);
        uns.route(EventType::MemoryCreated, false);
        uns.route(EventType::DharmaWarn, true);

        let summary = uns.summary();
        assert_eq!(summary["total_events"], 3);
        assert_eq!(summary["total_errors"], 1);
        assert!(summary["subsystems"].is_array());
    }

    #[test]
    fn subsystem_display() {
        assert_eq!(format!("{}", NervousSubsystem::Central), "central");
        assert_eq!(format!("{}", NervousSubsystem::Immune), "immune");
    }

    #[test]
    fn subsystem_description() {
        assert!(!NervousSubsystem::Central.description().is_empty());
        assert!(!NervousSubsystem::Immune.description().is_empty());
    }
}
