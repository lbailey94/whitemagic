//! Nervous system - biological subsystems integration

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicU32, Ordering},
    Arc, RwLock,
};

use crate::conductor::{EventBus, EventType, OrchestrationEvent, ResonanceConductor};

/// The 7 biological subsystems + Apotheosis
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum BiologicalSubsystem {
    Immune,        // Security, DNA, antibodies
    Genetic,       // Evolution, phylogenetics
    Dream,         // 12-phase dream cycle
    Metabolism,    // Consolidation, forgetting
    Consciousness, // Coherence, embodiment
    Resonance,     // Harmony, gardens
    Emergence,     // Ecology, serendipity
    Apotheosis,    // Autonomous evolution
}

impl BiologicalSubsystem {
    /// Get display name
    pub fn name(&self) -> &'static str {
        match self {
            Self::Immune => "Immune System",
            Self::Genetic => "Genetic System",
            Self::Dream => "Dream System",
            Self::Metabolism => "Memory Metabolism",
            Self::Consciousness => "Consciousness",
            Self::Resonance => "Resonance",
            Self::Emergence => "Emergence",
            Self::Apotheosis => "Apotheosis",
        }
    }

    /// Get all variants
    pub fn all() -> Vec<Self> {
        vec![
            Self::Immune,
            Self::Genetic,
            Self::Dream,
            Self::Metabolism,
            Self::Consciousness,
            Self::Resonance,
            Self::Emergence,
            Self::Apotheosis,
        ]
    }
}

/// Nervous system configuration
#[derive(Debug, Clone)]
pub struct NervousSystemConfig {
    pub enable_dream_cycles: bool,
    pub enable_immune_monitoring: bool,
    pub enable_genetic_tracking: bool,
    pub coherence_threshold: f64,
}

impl Default for NervousSystemConfig {
    fn default() -> Self {
        Self {
            enable_dream_cycles: true,
            enable_immune_monitoring: true,
            enable_genetic_tracking: true,
            coherence_threshold: 0.6,
        }
    }
}

/// Nervous system state
pub struct NervousSystem {
    config: NervousSystemConfig,

    /// Subsystem handles
    subsystems: RwLock<HashMap<BiologicalSubsystem, SubsystemHandle>>,

    /// Coherence score
    coherence: RwLock<f64>,

    /// Event bus
    event_bus: Arc<EventBus>,

    /// Conductor reference
    conductor: Arc<ResonanceConductor>,
}

/// Subsystem handle
pub struct SubsystemHandle {
    pub id: BiologicalSubsystem,
    pub active: AtomicU32, // 0 = inactive, 1 = active
    pub last_heartbeat: RwLock<Instant>,
}

use std::time::Instant;

impl SubsystemHandle {
    /// Create new handle
    pub fn new(id: BiologicalSubsystem) -> Self {
        Self {
            id,
            active: AtomicU32::new(0),
            last_heartbeat: RwLock::new(Instant::now()),
        }
    }

    /// Check if active
    pub fn is_active(&self) -> bool {
        self.active.load(Ordering::SeqCst) == 1
    }

    /// Set active
    pub fn set_active(&self, active: bool) {
        self.active
            .store(if active { 1 } else { 0 }, Ordering::SeqCst);
    }

    /// Update heartbeat
    pub fn heartbeat(&self) {
        if let Ok(mut last) = self.last_heartbeat.write() {
            *last = Instant::now();
        }
    }
}

impl NervousSystem {
    /// Create new nervous system
    pub fn new(
        config: NervousSystemConfig,
        event_bus: Arc<EventBus>,
        conductor: Arc<ResonanceConductor>,
    ) -> Self {
        let subsystems = RwLock::new(HashMap::new());

        // Initialize all subsystems
        if let Ok(mut subs) = subsystems.write() {
            for subsystem in BiologicalSubsystem::all() {
                subs.insert(subsystem, SubsystemHandle::new(subsystem));
            }
        }

        Self {
            config,
            subsystems,
            coherence: RwLock::new(1.0),
            event_bus,
            conductor,
        }
    }

    /// Bootstrap all biological subsystems
    pub fn bootstrap(&self) -> Result<(), String> {
        // Activate each subsystem
        for subsystem in BiologicalSubsystem::all() {
            self.activate_subsystem(subsystem)?;
        }

        // Wire cross-subsystem events
        self.wire_cross_subsystem_events();

        Ok(())
    }

    /// Activate a subsystem
    fn activate_subsystem(&self, subsystem: BiologicalSubsystem) -> Result<(), String> {
        if let Ok(subs) = self.subsystems.read() {
            if let Some(handle) = subs.get(&subsystem) {
                handle.set_active(true);
                handle.heartbeat();

                // Emit activation event
                self.emit_event(
                    EventType::SubsystemRegistered,
                    HashMap::from([
                        ("subsystem".to_string(), serde_json::json!(subsystem.name())),
                        ("status".to_string(), serde_json::json!("activated")),
                    ]),
                );
            }
        }

        Ok(())
    }

    /// Wire cross-subsystem events
    fn wire_cross_subsystem_events(&self) {
        // Coherence critical → Dream cycle
        let conductor = self.conductor.clone();
        self.event_bus
            .subscribe(vec![EventType::CoherenceCritical], move |event| {
                if event.event_type == EventType::CoherenceCritical {
                    // Trigger dream cycle
                    conductor.emit_event(
                        EventType::DreamConsolidationComplete,
                        Some(0),
                        None,
                        HashMap::from([(
                            "trigger".to_string(),
                            serde_json::json!("coherence_critical"),
                        )]),
                    );
                }
            });
    }

    /// Emit event
    fn emit_event(&self, event_type: EventType, payload: HashMap<String, serde_json::Value>) {
        self.conductor
            .emit_event(event_type, Some(0), None, payload);
    }

    /// Get subsystem status
    pub fn get_subsystem_status(&self) -> HashMap<String, HashMap<String, serde_json::Value>> {
        let mut status = HashMap::new();

        if let Ok(subs) = self.subsystems.read() {
            for (subsystem, handle) in subs.iter() {
                let mut info = HashMap::new();
                info.insert("active".to_string(), serde_json::json!(handle.is_active()));

                if let Ok(last) = handle.last_heartbeat.read() {
                    info.insert(
                        "last_heartbeat_ms".to_string(),
                        serde_json::json!(last.elapsed().as_millis() as u64),
                    );
                }

                status.insert(subsystem.name().to_string(), info);
            }
        }

        status
    }

    /// Update coherence
    pub fn update_coherence(&self, coherence: f64) {
        if let Ok(mut c) = self.coherence.write() {
            let old_coherence = *c;
            *c = coherence;

            // Check for critical coherence drop
            if coherence < self.config.coherence_threshold
                && old_coherence >= self.config.coherence_threshold
            {
                self.emit_event(
                    EventType::CoherenceCritical,
                    HashMap::from([
                        ("coherence".to_string(), serde_json::json!(coherence)),
                        (
                            "threshold".to_string(),
                            serde_json::json!(self.config.coherence_threshold),
                        ),
                    ]),
                );
            }

            // Check for coherence restoration
            if coherence >= self.config.coherence_threshold
                && old_coherence < self.config.coherence_threshold
            {
                self.emit_event(
                    EventType::CoherenceRestore,
                    HashMap::from([("coherence".to_string(), serde_json::json!(coherence))]),
                );
            }
        }
    }

    /// Get current coherence
    pub fn get_coherence(&self) -> f64 {
        if let Ok(c) = self.coherence.read() {
            *c
        } else {
            0.0
        }
    }

    /// Health check all subsystems
    pub fn health_check(&self) -> bool {
        if let Ok(subs) = self.subsystems.read() {
            for (_, handle) in subs.iter() {
                if !handle.is_active() {
                    return false;
                }

                // Check heartbeat staleness
                if let Ok(last) = handle.last_heartbeat.read() {
                    if last.elapsed() > Duration::from_secs(60) {
                        return false;
                    }
                }
            }
        }

        true
    }

    /// Shutdown all subsystems
    pub fn shutdown(&self) {
        if let Ok(subs) = self.subsystems.read() {
            for (_, handle) in subs.iter() {
                handle.set_active(false);
            }
        }
    }
}

/// Zodiacal cycle state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ZodiacPhase {
    Yang, // Creative, outward
    Yin,  // Receptive, inward
}

impl ZodiacPhase {
    /// Get display name
    pub fn name(&self) -> &'static str {
        match self {
            Self::Yang => "Yang (Creative)",
            Self::Yin => "Yin (Receptive)",
        }
    }
}

/// Zodiacal cycle
pub struct ZodiacalCycle {
    current_phase: RwLock<ZodiacPhase>,
    cycle_count: AtomicU32,
    event_bus: Arc<EventBus>,
}

impl ZodiacalCycle {
    /// Create new cycle
    pub fn new(event_bus: Arc<EventBus>) -> Self {
        Self {
            current_phase: RwLock::new(ZodiacPhase::Yang),
            cycle_count: AtomicU32::new(0),
            event_bus,
        }
    }

    /// Get current phase
    pub fn get_phase(&self) -> ZodiacPhase {
        if let Ok(phase) = self.current_phase.read() {
            *phase
        } else {
            ZodiacPhase::Yang
        }
    }

    /// Transition phase
    pub fn transition(&self) {
        if let Ok(mut phase) = self.current_phase.write() {
            let old_phase = *phase;
            *phase = match *phase {
                ZodiacPhase::Yang => ZodiacPhase::Yin,
                ZodiacPhase::Yin => {
                    self.cycle_count.fetch_add(1, Ordering::SeqCst);
                    ZodiacPhase::Yang
                }
            };

            // Emit phase transition event
            self.event_bus.publish(OrchestrationEvent {
                sequence: 0, // Will be set by conductor
                event_type: EventType::PhaseTransition,
                source: 0,
                target: None,
                priority: crate::conductor::Priority::High,
                timestamp: Instant::now(),
                payload: HashMap::from([
                    ("from".to_string(), serde_json::json!(old_phase.name())),
                    ("to".to_string(), serde_json::json!(phase.name())),
                    (
                        "cycle_count".to_string(),
                        serde_json::json!(self.cycle_count.load(Ordering::SeqCst)),
                    ),
                ]),
            });
        }
    }

    /// Get cycle count
    pub fn get_cycle_count(&self) -> u32 {
        self.cycle_count.load(Ordering::SeqCst)
    }
}

/// Garden registry
pub struct GardenRegistry {
    gardens: RwLock<HashMap<String, GardenHandle>>,
}

/// Garden handle
pub struct GardenHandle {
    pub name: String,
    pub quadrant: GardenQuadrant,
    pub active: AtomicU32,
}

/// Garden quadrants
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GardenQuadrant {
    Eastern,
    Southern,
    Western,
    Northern,
}

impl GardenRegistry {
    /// Create new registry
    pub fn new() -> Self {
        let gardens = RwLock::new(HashMap::new());

        // Initialize all 28 gardens
        if let Ok(mut g) = gardens.write() {
            // Eastern quadrant (7 gardens)
            for name in [
                "Horn",
                "Neck",
                "Root",
                "Room",
                "Heart",
                "Tail",
                "WinnowingBasket",
            ] {
                g.insert(
                    name.to_string(),
                    GardenHandle {
                        name: name.to_string(),
                        quadrant: GardenQuadrant::Eastern,
                        active: AtomicU32::new(0),
                    },
                );
            }

            // Southern quadrant (7 gardens)
            for name in [
                "Ghost",
                "Willow",
                "Star",
                "ExtendedNet",
                "Wings",
                "Chariot",
                "Abundance",
            ] {
                g.insert(
                    name.to_string(),
                    GardenHandle {
                        name: name.to_string(),
                        quadrant: GardenQuadrant::Southern,
                        active: AtomicU32::new(0),
                    },
                );
            }

            // Western quadrant (7 gardens)
            for name in [
                "Straddling",
                "Mound",
                "Stomach",
                "HairyHead",
                "TurtleBeak",
                "ThreeStars",
                "Net",
            ] {
                g.insert(
                    name.to_string(),
                    GardenHandle {
                        name: name.to_string(),
                        quadrant: GardenQuadrant::Western,
                        active: AtomicU32::new(0),
                    },
                );
            }

            // Northern quadrant (7 gardens)
            for name in [
                "Dipper",
                "Ox",
                "Girl",
                "Emptiness",
                "Roof",
                "Encampment",
                "Wall",
            ] {
                g.insert(
                    name.to_string(),
                    GardenHandle {
                        name: name.to_string(),
                        quadrant: GardenQuadrant::Northern,
                        active: AtomicU32::new(0),
                    },
                );
            }
        }

        Self { gardens }
    }

    /// Activate a garden
    pub fn activate(&self, name: &str) -> bool {
        if let Ok(gardens) = self.gardens.read() {
            if let Some(garden) = gardens.get(name) {
                garden.active.store(1, Ordering::SeqCst);
                return true;
            }
        }
        false
    }

    /// Get active gardens
    pub fn get_active_gardens(&self) -> Vec<String> {
        if let Ok(gardens) = self.gardens.read() {
            gardens
                .iter()
                .filter(|(_, g)| g.active.load(Ordering::SeqCst) == 1)
                .map(|(name, _)| name.clone())
                .collect()
        } else {
            Vec::new()
        }
    }

    /// Get all gardens
    pub fn get_all_gardens(&self) -> Vec<String> {
        if let Ok(gardens) = self.gardens.read() {
            gardens.keys().cloned().collect()
        } else {
            Vec::new()
        }
    }

    /// Activate all gardens
    pub fn activate_all(&self) -> usize {
        let mut activated = 0;

        if let Ok(gardens) = self.gardens.read() {
            for (_name, garden) in gardens.iter() {
                garden.active.store(1, Ordering::SeqCst);
                activated += 1;
            }
        }

        activated
    }
}

impl Default for GardenRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Harmony vector (7-dimensional health tracking)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HarmonyVector {
    pub coherence: f64,
    pub resonance: f64,
    pub emergence: f64,
    pub metabolism: f64,
    pub consciousness: f64,
    pub immune: f64,
    pub genetic: f64,
}

impl Default for HarmonyVector {
    fn default() -> Self {
        Self {
            coherence: 1.0,
            resonance: 1.0,
            emergence: 1.0,
            metabolism: 1.0,
            consciousness: 1.0,
            immune: 1.0,
            genetic: 1.0,
        }
    }
}

impl HarmonyVector {
    /// Calculate composite score
    pub fn composite(&self) -> f64 {
        (self.coherence
            + self.resonance
            + self.emergence
            + self.metabolism
            + self.consciousness
            + self.immune
            + self.genetic)
            / 7.0
    }

    /// Check if all dimensions are healthy
    pub fn is_healthy(&self, threshold: f64) -> bool {
        self.coherence >= threshold
            && self.resonance >= threshold
            && self.emergence >= threshold
            && self.metabolism >= threshold
            && self.consciousness >= threshold
            && self.immune >= threshold
            && self.genetic >= threshold
    }
}

/// Coherence monitor
pub struct CoherenceMonitor {
    harmony_vector: RwLock<HarmonyVector>,
    history: RwLock<Vec<(Instant, f64)>>,
}

impl CoherenceMonitor {
    /// Create new monitor
    pub fn new() -> Self {
        Self {
            harmony_vector: RwLock::new(HarmonyVector::default()),
            history: RwLock::new(Vec::with_capacity(1000)),
        }
    }

    /// Update harmony vector
    pub fn update(&self, vector: HarmonyVector) {
        let composite = vector.composite();

        if let Ok(mut hv) = self.harmony_vector.write() {
            *hv = vector;
        }

        if let Ok(mut history) = self.history.write() {
            history.push((Instant::now(), composite));
            if history.len() > 1000 {
                history.remove(0);
            }
        }
    }

    /// Get current harmony vector
    pub fn get_vector(&self) -> HarmonyVector {
        if let Ok(hv) = self.harmony_vector.read() {
            hv.clone()
        } else {
            HarmonyVector::default()
        }
    }

    /// Get coherence history
    pub fn get_history(&self, limit: usize) -> Vec<(Instant, f64)> {
        if let Ok(history) = self.history.read() {
            history.iter().rev().take(limit).cloned().collect()
        } else {
            Vec::new()
        }
    }
}

impl Default for CoherenceMonitor {
    fn default() -> Self {
        Self::new()
    }
}

use std::time::Duration;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_biological_subsystem_names() {
        assert_eq!(BiologicalSubsystem::Immune.name(), "Immune System");
        assert_eq!(BiologicalSubsystem::Dream.name(), "Dream System");
    }

    #[test]
    fn test_harmony_vector() {
        let hv = HarmonyVector::default();
        assert_eq!(hv.composite(), 1.0);
        assert!(hv.is_healthy(0.9));

        let low_hv = HarmonyVector {
            coherence: 0.5,
            ..Default::default()
        };
        assert!(!low_hv.is_healthy(0.9));
    }

    #[test]
    fn test_garden_registry() {
        let registry = GardenRegistry::new();

        assert_eq!(registry.get_all_gardens().len(), 28);

        let activated = registry.activate_all();
        assert_eq!(activated, 28);

        let active = registry.get_active_gardens();
        assert_eq!(active.len(), 28);
    }

    #[test]
    fn test_zodiacal_cycle() {
        let event_bus = Arc::new(EventBus::new());
        let cycle = ZodiacalCycle::new(event_bus);

        assert_eq!(cycle.get_phase(), ZodiacPhase::Yang);
        assert_eq!(cycle.get_cycle_count(), 0);

        cycle.transition();
        assert_eq!(cycle.get_phase(), ZodiacPhase::Yin);

        cycle.transition();
        assert_eq!(cycle.get_phase(), ZodiacPhase::Yang);
        assert_eq!(cycle.get_cycle_count(), 1);
    }
}
