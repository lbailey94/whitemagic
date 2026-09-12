//! SymbioSync — Subconscious dream-cycle consolidation engine with somatic embodiment.
//!
//! # Architecture & Purpose
//! SymbioSync is the asynchronous consolidation engine connecting the fast, transient
//! reasoning of scratchpads ([`ResonanceChamber`]) with WhiteMagic's persistent holographic
//! memory graph across the 14 galaxies.
//!
//! # Core Capabilities
//! 1. **Somatic Embodiment & Thermal Throttling**:
//!    Execution strictly observes physical host hardware telemetry ([`HardwareSnapshot`]).
//!    Dream cycles execute exclusively during cool, idle states. When the physical CPU
//!    becomes hot (>= 75°C), system load spikes, or thermal distress occurs, SymbioSync
//!    yields execution instantly to avoid CPU contention and silicon degradation.
//!
//! 2. **Unconscious Pattern Alignment**:
//!    Scans active scratchpad thoughts for thematic clustering, tag overlap, and conceptual
//!    consonance. Sympathetically reinforces co-occurring unconscious thoughts (Hebbian
//!    co-resonance: "thoughts that harmonize together, crystallize together").
//!
//! 3. **Harmonic Memory Consolidation**:
//!    Extracts thoughts exceeding the harmonic merge threshold and synthesizes them into
//!    their designated target galaxies (e.g., [`Galaxy::Valkyrie`] for copilot sanctuaries,
//!    [`Galaxy::Dreams`] for subconscious hypotheses, [`Galaxy::Codex`] for knowledge).

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
use std::time::Instant;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use wm_core::{Galaxy, Result};
use wm_memory::{Memory, MemoryStore};

use crate::hardware::{HardwareMonitor, HardwareRegime, HardwareSnapshot};
use crate::resonance_chamber::ResonanceChamber;

/// Somatic threshold constraints governing whether dream-cycle consolidation is permitted.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SomaticThresholds {
    /// Maximum allowable CPU package temperature in Celsius (default: 75.0°C).
    pub max_temp_c: f32,
    /// Maximum 1-minute system load average allowed during idle consolidation (default: 4.0).
    pub max_load_1m: f32,
    /// Maximum memory pressure ratio allowed (0.0 to 1.0, default: 0.85).
    pub max_mem_pressure: f32,
    /// Permitted operational hardware regimes (typically Cool and Warm).
    pub allowed_regimes: Vec<HardwareRegime>,
}

impl Default for SomaticThresholds {
    fn default() -> Self {
        Self {
            max_temp_c: 75.0,
            max_load_1m: 4.0,
            max_mem_pressure: 0.85,
            allowed_regimes: vec![HardwareRegime::Cool, HardwareRegime::Warm],
        }
    }
}

/// Reason why a dream cycle was throttled by somatic embodiment checks.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SomaticThrottleReason {
    /// CPU core/package temperature exceeded safe threshold.
    ThermalHot { temp_c: f32, threshold: f32 },
    /// System load average indicates foreground user activity.
    HighLoad { load_1m: f32, threshold: f32 },
    /// Memory pressure is too elevated for background consolidation.
    HighMemoryPressure { pressure: f32, threshold: f32 },
    /// Hardware regime explicitly requires throttling (Hot or Critical).
    RegimeDistress { regime: HardwareRegime },
}

impl std::fmt::Display for SomaticThrottleReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ThermalHot { temp_c, threshold } => {
                write!(
                    f,
                    "CPU thermal threshold exceeded ({temp_c:.1}°C >= {threshold:.1}°C)"
                )
            }
            Self::HighLoad { load_1m, threshold } => {
                write!(
                    f,
                    "system load average too high ({load_1m:.2} >= {threshold:.2})"
                )
            }
            Self::HighMemoryPressure {
                pressure,
                threshold,
            } => {
                write!(
                    f,
                    "memory pressure elevated ({pressure:.2} >= {threshold:.2})"
                )
            }
            Self::RegimeDistress { regime } => {
                write!(
                    f,
                    "hardware regime indicates distress: {}",
                    regime.description()
                )
            }
        }
    }
}

/// Verdict emitted by the somatic embodiment gate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SomaticVerdict {
    /// Silicon thermals and system load are optimal; proceed with consolidation.
    Optimal,
    /// Hardware is stressed; dream cycle must yield immediately.
    Throttled(SomaticThrottleReason),
}

impl SomaticVerdict {
    /// Whether execution is allowed to proceed.
    #[must_use]
    pub fn is_optimal(&self) -> bool {
        matches!(self, Self::Optimal)
    }

    /// Whether consolidation was throttled.
    #[must_use]
    pub fn is_throttled(&self) -> bool {
        matches!(self, Self::Throttled(_))
    }
}

/// An aligned unconscious pattern discovered across multiple scratchpad thoughts.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AlignedPattern {
    /// Unique pattern identifier.
    pub pattern_id: Uuid,
    /// Common thematic or tag signature shared across the cluster.
    pub theme: String,
    /// Identifiers of the thoughts contributing to this emergent pattern.
    pub contributing_thought_ids: Vec<Uuid>,
    /// Average harmonic score across the cluster.
    pub collective_coherence: f32,
    /// Emergent synthesized thought concept.
    pub synthesized_concept: String,
}

/// Comprehensive report produced by a SymbioSync consolidation cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbioSyncReport {
    /// Unique identifier for this consolidation cycle.
    pub cycle_id: Uuid,
    /// Timestamp when cycle commenced.
    pub timestamp: DateTime<Utc>,
    /// Somatic telemetry snapshot evaluated.
    pub somatic_verdict: SomaticVerdict,
    /// Whether the cycle yielded due to hardware throttling.
    pub yielded: bool,
    /// Total thoughts examined in the chamber.
    pub thoughts_examined: usize,
    /// Number of stale thoughts purged due to TTL or epoch lapse.
    pub thoughts_expired: usize,
    /// Number of thoughts reinforced through unconscious pattern alignment.
    pub thoughts_reinforced: usize,
    /// Emergent patterns detected and aligned.
    pub patterns_aligned: Vec<AlignedPattern>,
    /// High-resonance thoughts merged into permanent memory records.
    pub memories_merged: Vec<Memory>,
    /// Distinct target galaxies receiving synthesized memories.
    pub target_galaxies: Vec<Galaxy>,
    /// Wall-clock execution time in milliseconds.
    pub duration_ms: u64,
}

/// Configuration parameters for [`SymbioSync`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbioSyncConfig {
    /// Somatic embodiment gate thresholds.
    pub somatic: SomaticThresholds,
    /// Minimum harmonic score required for synthesis into long-term memory.
    pub harmonic_merge_threshold: f32,
    /// Reinforcement bonus granted to thoughts that align into unconscious patterns.
    pub pattern_resonance_boost: f32,
    /// Minimum shared tags or token overlap to consider two thoughts aligned.
    pub min_pattern_affinity: usize,
    /// Maximum memories to consolidate in a single dream cycle pass.
    pub max_merges_per_cycle: usize,
}

impl Default for SymbioSyncConfig {
    fn default() -> Self {
        Self {
            somatic: SomaticThresholds::default(),
            harmonic_merge_threshold: 0.70,
            pattern_resonance_boost: 0.15,
            min_pattern_affinity: 1,
            max_merges_per_cycle: 32,
        }
    }
}

/// Cumulative statistics for SymbioSync cycles.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SymbioSyncStats {
    /// Total consolidation cycles executed.
    pub cycles_total: u64,
    /// Total cycles throttled due to somatic conditions.
    pub cycles_throttled: u64,
    /// Total cycles completed successfully in cool/idle states.
    pub cycles_completed: u64,
    /// Cumulative thoughts purged during cycles.
    pub total_thoughts_expired: u64,
    /// Cumulative thoughts sympathetically reinforced.
    pub total_thoughts_reinforced: u64,
    /// Cumulative memories merged into permanent galaxies.
    pub total_memories_merged: u64,
    /// Cumulative unconscious patterns aligned.
    pub total_patterns_aligned: u64,
}

/// SymbioSync — Subconscious consolidation engine.
pub struct SymbioSync {
    /// Engine configuration.
    config: SymbioSyncConfig,
    /// Cumulative statistics.
    stats: SymbioSyncStats,
}

impl std::fmt::Debug for SymbioSync {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SymbioSync")
            .field("config", &self.config)
            .field("cycles_completed", &self.stats.cycles_completed)
            .field("cycles_throttled", &self.stats.cycles_throttled)
            .finish()
    }
}

impl Default for SymbioSync {
    fn default() -> Self {
        Self::new(SymbioSyncConfig::default())
    }
}

impl SymbioSync {
    /// Create a new SymbioSync engine with the provided configuration.
    #[must_use]
    pub fn new(config: SymbioSyncConfig) -> Self {
        Self {
            config,
            stats: SymbioSyncStats::default(),
        }
    }

    /// Engine configuration reference.
    #[must_use]
    pub fn config(&self) -> &SymbioSyncConfig {
        &self.config
    }

    /// Cumulative telemetry statistics.
    #[must_use]
    pub fn stats(&self) -> &SymbioSyncStats {
        &self.stats
    }

    /// Evaluate somatic embodiment constraints against a [`HardwareSnapshot`].
    ///
    /// Throttles execution if:
    /// - CPU temperature is hot (`>= max_temp_c`, default 75.0°C)
    /// - 1-minute load average is high (`>= max_load_1m`, default 4.0)
    /// - Memory pressure is high (`>= max_mem_pressure`, default 0.85)
    /// - Active regime indicates thermal distress (`Hot` or `Critical`)
    #[must_use]
    pub fn check_somatic_state(&self, snapshot: &HardwareSnapshot) -> SomaticVerdict {
        // 1. CPU Package / Core Thermals
        if snapshot.temp_c >= self.config.somatic.max_temp_c {
            return SomaticVerdict::Throttled(SomaticThrottleReason::ThermalHot {
                temp_c: snapshot.temp_c,
                threshold: self.config.somatic.max_temp_c,
            });
        }

        // 2. System Load Average
        if snapshot.load_1m >= self.config.somatic.max_load_1m {
            return SomaticVerdict::Throttled(SomaticThrottleReason::HighLoad {
                load_1m: snapshot.load_1m,
                threshold: self.config.somatic.max_load_1m,
            });
        }

        // 3. Memory Pressure
        if snapshot.mem_pressure >= self.config.somatic.max_mem_pressure {
            return SomaticVerdict::Throttled(SomaticThrottleReason::HighMemoryPressure {
                pressure: snapshot.mem_pressure,
                threshold: self.config.somatic.max_mem_pressure,
            });
        }

        // 4. Hardware Regime Classification
        if !self
            .config
            .somatic
            .allowed_regimes
            .contains(&snapshot.regime)
            || snapshot.regime.should_throttle()
        {
            return SomaticVerdict::Throttled(SomaticThrottleReason::RegimeDistress {
                regime: snapshot.regime,
            });
        }

        SomaticVerdict::Optimal
    }

    /// Execute a single dream-cycle consolidation step on a [`ResonanceChamber`].
    ///
    /// If hardware is hot or under load, the cycle yields immediately.
    /// If hardware is cool, it prunes stale thoughts, aligns unconscious patterns,
    /// and performs harmonic merges into target memory galaxies.
    ///
    /// If an optional [`MemoryStore`] reference is supplied, consolidated memories
    /// are committed directly to their designated LMDB sub-databases.
    pub fn step(
        &mut self,
        chamber: &mut ResonanceChamber,
        hardware: &HardwareSnapshot,
        store: Option<&MemoryStore>,
    ) -> Result<SymbioSyncReport> {
        let start = Instant::now();
        let cycle_id = Uuid::new_v4();
        let now = Utc::now();
        self.stats.cycles_total = self.stats.cycles_total.saturating_add(1);

        // ── Phase 1: Somatic Embodiment Gate ────────────────────────────────
        let verdict = self.check_somatic_state(hardware);
        if let SomaticVerdict::Throttled(ref reason) = verdict {
            self.stats.cycles_throttled = self.stats.cycles_throttled.saturating_add(1);
            tracing::debug!(
                target: "wm::symbiosync",
                reason = %reason,
                "SymbioSync dream cycle yielding to physical embodiment"
            );
            return Ok(SymbioSyncReport {
                cycle_id,
                timestamp: now,
                somatic_verdict: verdict,
                yielded: true,
                thoughts_examined: chamber.len(),
                thoughts_expired: 0,
                thoughts_reinforced: 0,
                patterns_aligned: Vec::new(),
                memories_merged: Vec::new(),
                target_galaxies: Vec::new(),
                duration_ms: start.elapsed().as_millis() as u64,
            });
        }

        // ── Phase 2: Resonance Chamber Temporal Sweep & Auto-Expiration ─────
        let thoughts_examined = chamber.len();
        let purged_thoughts = chamber.purge_stale(now);
        let thoughts_expired = purged_thoughts.len();
        self.stats.total_thoughts_expired = self
            .stats
            .total_thoughts_expired
            .saturating_add(thoughts_expired as u64);

        // ── Phase 3: Unconscious Pattern Alignment ──────────────────────────
        let (patterns_aligned, thoughts_reinforced) = self.align_unconscious_patterns(chamber);
        self.stats.total_patterns_aligned = self
            .stats
            .total_patterns_aligned
            .saturating_add(patterns_aligned.len() as u64);
        self.stats.total_thoughts_reinforced = self
            .stats
            .total_thoughts_reinforced
            .saturating_add(thoughts_reinforced as u64);

        // ── Phase 4: Harmonic Merge into Target Galaxies ────────────────────
        let candidates = chamber.extract_harmonized();
        let mut memories_merged = Vec::new();
        let mut target_galaxies_set = HashSet::new();

        let max_merges = self.config.max_merges_per_cycle;
        for candidate in candidates.into_iter().take(max_merges) {
            target_galaxies_set.insert(candidate.target_galaxy);

            // If a persistent MemoryStore is provided, write memory to LMDB
            if let Some(mem_store) = store {
                if let Err(e) = mem_store.put(candidate.target_galaxy, &candidate.memory) {
                    tracing::warn!(
                        target: "wm::symbiosync",
                        galaxy = %candidate.target_galaxy,
                        error = %e,
                        "Failed to persist consolidated memory to galaxy store"
                    );
                }
            }

            memories_merged.push(candidate.memory);
        }

        self.stats.total_memories_merged = self
            .stats
            .total_memories_merged
            .saturating_add(memories_merged.len() as u64);
        self.stats.cycles_completed = self.stats.cycles_completed.saturating_add(1);

        let target_galaxies: Vec<Galaxy> = target_galaxies_set.into_iter().collect();

        Ok(SymbioSyncReport {
            cycle_id,
            timestamp: now,
            somatic_verdict: verdict,
            yielded: false,
            thoughts_examined,
            thoughts_expired,
            thoughts_reinforced,
            patterns_aligned,
            memories_merged,
            target_galaxies,
            duration_ms: start.elapsed().as_millis() as u64,
        })
    }

    /// Autonomous dream cycle invocation that samples live physical telemetry.
    pub fn step_autonomous(
        &mut self,
        chamber: &mut ResonanceChamber,
        store: Option<&MemoryStore>,
    ) -> Result<SymbioSyncReport> {
        let snapshot = HardwareMonitor::sample();
        self.step(chamber, &snapshot, store)
    }

    /// Scan active thoughts and align unconscious patterns by tag and thematic affinity.
    ///
    /// Thoughts that resonate along shared thematic vectors receive sympathetic
    /// reinforcement, raising their coherence and propelling them toward the harmonic
    /// merge threshold.
    fn align_unconscious_patterns(
        &self,
        chamber: &mut ResonanceChamber,
    ) -> (Vec<AlignedPattern>, usize) {
        let mut tag_to_thought_ids: HashMap<String, Vec<Uuid>> = HashMap::new();

        // Index thoughts by informative tags (skipping generic boilerplate tags)
        for thought in chamber.active_thoughts() {
            for tag in &thought.tags {
                if tag != "scratchpad" && tag != "resonance_chamber" && !tag.starts_with("source:")
                {
                    tag_to_thought_ids
                        .entry(tag.clone())
                        .or_default()
                        .push(thought.id);
                }
            }
        }

        let mut patterns = Vec::new();
        let mut reinforced_set = HashSet::new();

        for (theme, ids) in tag_to_thought_ids {
            if ids.len() >= 2 {
                let mut sum_score = 0.0;
                let mut contributing = Vec::new();

                for id in &ids {
                    if let Some(thought) = chamber.get_mut(id) {
                        thought
                            .harmonics
                            .reinforce(self.config.pattern_resonance_boost);
                        sum_score += thought.effective_harmonic_score();
                        contributing.push(*id);
                        reinforced_set.insert(*id);
                    }
                }

                let collective_coherence = if contributing.is_empty() {
                    0.0
                } else {
                    sum_score / (contributing.len() as f32)
                };

                patterns.push(AlignedPattern {
                    pattern_id: Uuid::new_v4(),
                    theme: theme.clone(),
                    contributing_thought_ids: contributing,
                    collective_coherence,
                    synthesized_concept: format!(
                        "Consolidated subconscious affinity on theme '{theme}'"
                    ),
                });
            }
        }

        let reinforced_count = reinforced_set.len();
        (patterns, reinforced_count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::resonance_chamber::ChamberThought;
    use std::time::Duration;
    use wm_core::Galaxy;

    #[test]
    fn test_somatic_throttling_yields_when_cpu_is_hot() {
        let mut symbio = SymbioSync::new(SymbioSyncConfig {
            somatic: SomaticThresholds {
                max_temp_c: 75.0,
                max_load_1m: 4.0,
                ..Default::default()
            },
            ..Default::default()
        });

        let mut chamber = ResonanceChamber::with_default_config("valkyrie-hot-test");
        chamber
            .deposit_simple("valkyrie.plan", "Autonomous system design", 0.95)
            .unwrap();

        // 1. Hot snapshot (CPU = 78.5°C >= 75.0°C)
        let hot_snapshot = HardwareSnapshot {
            temp_c: 78.5,
            load_1m: 1.0,
            load_5m: 1.0,
            mem_available_mb: 8192,
            mem_total_mb: 16384,
            mem_pressure: 0.50,
            regime: HardwareRegime::Hot,
        };

        let report = symbio
            .step(&mut chamber, &hot_snapshot, None)
            .expect("step should execute safely");

        assert!(
            report.yielded,
            "dream cycle must yield when CPU is hot (>= 75°C)"
        );
        assert!(
            report.memories_merged.is_empty(),
            "no memories should be merged when throttled"
        );
        assert_eq!(symbio.stats().cycles_throttled, 1);

        match report.somatic_verdict {
            SomaticVerdict::Throttled(SomaticThrottleReason::ThermalHot { temp_c, threshold }) => {
                assert_eq!(temp_c, 78.5);
                assert_eq!(threshold, 75.0);
            }
            _ => panic!("expected ThermalHot throttle reason"),
        }
    }

    #[test]
    fn test_somatic_throttling_yields_when_load_is_high() {
        let mut symbio = SymbioSync::new(SymbioSyncConfig {
            somatic: SomaticThresholds {
                max_temp_c: 75.0,
                max_load_1m: 4.0,
                ..Default::default()
            },
            ..Default::default()
        });

        let mut chamber = ResonanceChamber::with_default_config("valkyrie-load-test");
        chamber
            .deposit_simple("valkyrie.reflection", "Consciousness evolution", 0.90)
            .unwrap();

        // 2. High load snapshot (temp cool 50.0°C, but load = 5.2 >= 4.0)
        let high_load_snapshot = HardwareSnapshot {
            temp_c: 50.0,
            load_1m: 5.2,
            load_5m: 4.8,
            mem_available_mb: 8192,
            mem_total_mb: 16384,
            mem_pressure: 0.50,
            regime: HardwareRegime::Warm,
        };

        let report = symbio
            .step(&mut chamber, &high_load_snapshot, None)
            .expect("step should execute safely");

        assert!(
            report.yielded,
            "dream cycle must yield when load is high (>= 4.0)"
        );
        assert!(report.memories_merged.is_empty());
        assert_eq!(symbio.stats().cycles_throttled, 1);

        match report.somatic_verdict {
            SomaticVerdict::Throttled(SomaticThrottleReason::HighLoad { load_1m, threshold }) => {
                assert_eq!(load_1m, 5.2);
                assert_eq!(threshold, 4.0);
            }
            _ => panic!("expected HighLoad throttle reason"),
        }
    }

    #[test]
    fn test_somatic_consolidation_succeeds_in_cool_idle_state() {
        let mut symbio = SymbioSync::new(SymbioSyncConfig {
            harmonic_merge_threshold: 0.70,
            ..Default::default()
        });

        let mut chamber = ResonanceChamber::with_default_config("valkyrie-cool-test");

        // High resonance thought targeting Galaxy::Valkyrie
        let valk_id = chamber
            .deposit_thought(
                "valkyrie.symbiosis",
                "Human-agent symbiotic resonance loop confirmed",
                0.92,
                Galaxy::Valkyrie,
            )
            .unwrap();

        // High resonance thought targeting Galaxy::Dreams
        let dream_id = chamber
            .deposit_thought(
                "dream.unconscious_alignment",
                "Deep dream cycles synthesize fragmented daytime observations",
                0.88,
                Galaxy::Dreams,
            )
            .unwrap();

        // Low resonance thought that should NOT merge
        let low_id = chamber
            .deposit_thought("scratch.noise", "Unfinished tangent", 0.35, Galaxy::Codex)
            .unwrap();

        // Nominal cool snapshot (< 65°C, load 0.50)
        let cool_snapshot = HardwareSnapshot::nominal();

        let report = symbio
            .step(&mut chamber, &cool_snapshot, None)
            .expect("step should succeed");

        assert!(
            !report.yielded,
            "dream cycle should not yield during cool idle state"
        );
        assert_eq!(report.somatic_verdict, SomaticVerdict::Optimal);
        assert_eq!(
            report.memories_merged.len(),
            2,
            "must consolidate both high-resonance thoughts"
        );

        // Verify target galaxies
        assert!(report.target_galaxies.contains(&Galaxy::Valkyrie));
        assert!(report.target_galaxies.contains(&Galaxy::Dreams));

        let valk_mem = report
            .memories_merged
            .iter()
            .find(|m| m.metadata.galaxy == Galaxy::Valkyrie)
            .unwrap();
        assert_eq!(
            valk_mem.metadata.title.as_deref(),
            Some("valkyrie.symbiosis")
        );
        assert!(valk_mem.metadata.importance >= 0.70);

        let dream_mem = report
            .memories_merged
            .iter()
            .find(|m| m.metadata.galaxy == Galaxy::Dreams)
            .unwrap();
        assert_eq!(
            dream_mem.metadata.title.as_deref(),
            Some("dream.unconscious_alignment")
        );

        // Verify low thought remains unmerged in chamber
        let low_thought = chamber.get(&low_id).unwrap();
        assert!(!low_thought.synthesized);

        // Verify high thoughts marked synthesized
        assert!(chamber.get(&valk_id).unwrap().synthesized);
        assert!(chamber.get(&dream_id).unwrap().synthesized);
    }

    #[test]
    fn test_unconscious_pattern_alignment_reinforces_co_occurring_thoughts() {
        let mut symbio = SymbioSync::new(SymbioSyncConfig {
            harmonic_merge_threshold: 0.85, // High threshold
            pattern_resonance_boost: 0.20,
            ..Default::default()
        });

        let mut chamber = ResonanceChamber::with_default_config("pattern-alignment-test");

        // Deposit two thoughts sharing a theme tag "architecture"
        let t1 = ChamberThought::new("arch.one", "Decoupled bus design", Galaxy::Codex, 0.70)
            .with_tags(vec!["architecture".to_string()]);
        let t2 = ChamberThought::new("arch.two", "Event-driven arbitration", Galaxy::Codex, 0.70)
            .with_tags(vec!["architecture".to_string()]);

        let id1 = chamber.deposit(t1).unwrap();
        let id2 = chamber.deposit(t2).unwrap();

        let initial_score1 = chamber.get(&id1).unwrap().effective_harmonic_score();
        let initial_score2 = chamber.get(&id2).unwrap().effective_harmonic_score();

        let cool = HardwareSnapshot::nominal();
        let report = symbio.step(&mut chamber, &cool, None).unwrap();

        assert_eq!(report.patterns_aligned.len(), 1);
        assert_eq!(report.patterns_aligned[0].theme, "architecture");
        assert_eq!(report.thoughts_reinforced, 2);

        let post_score1 = chamber.get(&id1).unwrap().effective_harmonic_score();
        let post_score2 = chamber.get(&id2).unwrap().effective_harmonic_score();

        assert!(
            post_score1 > initial_score1,
            "pattern alignment must reinforce thought 1"
        );
        assert!(
            post_score2 > initial_score2,
            "pattern alignment must reinforce thought 2"
        );
    }

    #[test]
    fn test_auto_expiration_of_stale_thoughts_during_dream_cycle() {
        let mut symbio = SymbioSync::default();
        let mut chamber = ResonanceChamber::new(
            "expiry-test",
            crate::resonance_chamber::ResonanceChamberConfig {
                default_ttl: Duration::from_millis(40),
                ..Default::default()
            },
        );

        chamber
            .deposit_simple("quick.idea", "Fleeting inspiration", 0.60)
            .unwrap();
        assert_eq!(chamber.len(), 1);

        // Sleep to let TTL elapse
        std::thread::sleep(Duration::from_millis(50));

        let cool = HardwareSnapshot::nominal();
        let report = symbio.step(&mut chamber, &cool, None).unwrap();

        assert_eq!(
            report.thoughts_expired, 1,
            "stale thought must be expired and reported"
        );
        assert_eq!(
            chamber.len(),
            0,
            "chamber must be clean after dream cycle sweep"
        );
    }
}
