//! Dharma Gate — Ethical governance for tool dispatch.
//!
//! Evaluates tool calls against Dharma principles (Ahimsa, Satya) and
//! the current system state (brain-wave, karma debt, homeostasis).
//!
//! Replaces v2's `DharmaEngine` (which returned String verdicts) with
//! a typed `ActionVerdict` enum. Maturity and strictness are derived
//! from the current brain-wave state rather than static configuration,
//! tying governance to the system's actual energy and coherence level.
//!
//! Sutras:
//! - Ahimsa (non-harm): Destructive actions blocked in strict/low-maturity states.
//! - Satya (truth): Memory fabrication is always forbidden.

use std::sync::atomic::{AtomicU64, Ordering};
use wm_core::{BrainWave, Context, EffectRow, Resource};

/// The verdict from a Dharma evaluation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ActionVerdict {
    /// Proceed normally — action is harmonious.
    Observe,
    /// Proceed, but log a warning — harmony is destabilizing.
    Advise(String),
    /// Proceed with restrictions — high karmic debt or risky effect.
    Correct(String),
    /// Block the action — critical karmic debt or governance violation.
    Intervene(String),
    /// Hard block — severe violation (Ahimsa/Satya breach).
    Panic(String),
}

impl ActionVerdict {
    /// Whether this verdict blocks the tool call.
    #[must_use]
    pub const fn blocks(&self) -> bool {
        matches!(self, Self::Intervene(_) | Self::Panic(_))
    }

    /// Whether this verdict is a warning (non-blocking but notable).
    #[must_use]
    pub const fn is_warning(&self) -> bool {
        matches!(self, Self::Advise(_) | Self::Correct(_))
    }

    /// Human-readable reason for the verdict.
    #[must_use]
    pub fn reason(&self) -> &str {
        match self {
            Self::Observe => "observe",
            Self::Advise(r) | Self::Correct(r) | Self::Intervene(r) | Self::Panic(r) => r,
        }
    }
}

// ── Decision counters (telemetry) ────────────────────────────────────

static OBSERVE_COUNT: AtomicU64 = AtomicU64::new(0);
static ADVISE_COUNT: AtomicU64 = AtomicU64::new(0);
static CORRECT_COUNT: AtomicU64 = AtomicU64::new(0);
static INTERVENE_COUNT: AtomicU64 = AtomicU64::new(0);
static PANIC_COUNT: AtomicU64 = AtomicU64::new(0);

/// Per-verdict decision counts since process start.
///
/// Consumed by telemetry surfaces (`dharma.status`, Lakshmi's dharma
/// dimension): rates are meaningful as deltas between polls, absolute
/// values reset each process start by design.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct VerdictCounts {
    pub observe: u64,
    pub advise: u64,
    pub correct: u64,
    pub intervene: u64,
    pub panic: u64,
}

impl VerdictCounts {
    /// Total evaluations counted.
    #[must_use]
    pub const fn total(&self) -> u64 {
        self.observe + self.advise + self.correct + self.intervene + self.panic
    }

    /// Blocking verdicts (Intervene + Panic).
    #[must_use]
    pub const fn blocked(&self) -> u64 {
        self.intervene + self.panic
    }

    /// Blocked / total in [0.0, 1.0]; 0.0 when no decisions yet.
    #[must_use]
    pub fn blocked_ratio(&self) -> f32 {
        let total = self.total();
        if total == 0 {
            0.0
        } else {
            self.blocked() as f32 / total as f32
        }
    }
}

/// Increment the per-verdict counter (called by [`DharmaGate::evaluate`]).
pub fn record_verdict(verdict: &ActionVerdict) {
    let counter = match verdict {
        ActionVerdict::Observe => &OBSERVE_COUNT,
        ActionVerdict::Advise(_) => &ADVISE_COUNT,
        ActionVerdict::Correct(_) => &CORRECT_COUNT,
        ActionVerdict::Intervene(_) => &INTERVENE_COUNT,
        ActionVerdict::Panic(_) => &PANIC_COUNT,
    };
    counter.fetch_add(1, Ordering::Relaxed);
}

/// Snapshot of the decision counters since process start.
#[must_use]
pub fn verdict_counts() -> VerdictCounts {
    VerdictCounts {
        observe: OBSERVE_COUNT.load(Ordering::Relaxed),
        advise: ADVISE_COUNT.load(Ordering::Relaxed),
        correct: CORRECT_COUNT.load(Ordering::Relaxed),
        intervene: INTERVENE_COUNT.load(Ordering::Relaxed),
        panic: PANIC_COUNT.load(Ordering::Relaxed),
    }
}

/// Homeostasis snapshot — real system state for adaptive governance.
///
/// When the system is under load (high CPU, low memory), governance
/// becomes stricter. When idle and healthy, it relaxes.
#[derive(Debug, Clone, Default)]
pub struct Homeostasis {
    /// CPU load fraction (0.0 = idle, 1.0 = saturated).
    pub cpu_load: f32,
    /// Memory pressure fraction (0.0 = plenty, 1.0 = critical).
    pub memory_pressure: f32,
    /// Whether the system is actively processing user requests.
    pub active: bool,
}

impl Homeostasis {
    /// Compute a health score (0.0 = critical, 1.0 = perfect).
    #[must_use]
    pub fn health_score(&self) -> f32 {
        let cpu_health = 1.0 - self.cpu_load.min(1.0);
        let mem_health = 1.0 - self.memory_pressure.min(1.0);
        (cpu_health * 0.5) + (mem_health * 0.5)
    }

    /// Whether the system is under stress (health < 0.3).
    #[must_use]
    pub fn is_stressed(&self) -> bool {
        self.health_score() < 0.3
    }
}

/// Maturity level derived from brain-wave state.
///
/// Higher levels permit more aggressive actions. The brain-wave state
/// reflects the system's available energy and coherence.
const fn maturity_from_brain_wave(bw: BrainWave) -> u8 {
    match bw {
        BrainWave::Gamma => 5, // Full power — highest maturity
        BrainWave::Beta => 4,  // Active — high maturity
        BrainWave::Alpha => 3, // Relaxed — moderate maturity
        BrainWave::Theta => 2, // Dreaming — low maturity, no writes
        BrainWave::Delta => 1, // Deep rest — minimal maturity
    }
}

/// Whether strict mode should be active given the system state.
///
/// Strict mode blocks destructive actions entirely. It's active when:
/// - Brain-wave is Theta or Delta (low power) — unless the caller carried
///   an explicit `confirm: true` (deliberate operator intent; 9.1.6)
/// - Homeostasis shows system stress (health < 0.3) — never bypassed
fn is_strict_mode(bw: BrainWave, homeostasis: &Homeostasis, explicit_confirm: bool) -> bool {
    (matches!(bw, BrainWave::Theta | BrainWave::Delta) && !explicit_confirm)
        || homeostasis.is_stressed()
}

/// The Dharma gate — evaluates tool calls against ethical principles.
pub struct DharmaGate {
    /// Current homeostasis snapshot (updated periodically).
    homeostasis: std::sync::RwLock<Homeostasis>,
}

impl DharmaGate {
    /// Create a new Dharma gate with default (healthy) homeostasis.
    #[must_use]
    pub fn new() -> Self {
        Self {
            homeostasis: std::sync::RwLock::new(Homeostasis::default()),
        }
    }

    /// Update the homeostasis snapshot.
    pub fn update_homeostasis(&self, h: Homeostasis) {
        if let Ok(mut guard) = self.homeostasis.write() {
            *guard = h;
        }
    }

    /// Get the current homeostasis snapshot.
    pub fn homeostasis(&self) -> Homeostasis {
        self.homeostasis
            .read()
            .map(|g| g.clone())
            .unwrap_or_default()
    }

    /// Evaluate a tool call against Dharma principles.
    ///
    /// Returns a verdict indicating whether the call should proceed.
    pub fn evaluate(&self, effects: &EffectRow, ctx: &Context) -> ActionVerdict {
        let verdict = self.evaluate_inner(effects, ctx);
        record_verdict(&verdict);
        verdict
    }

    /// Uncounted inner evaluation — public entry is [`Self::evaluate`].
    fn evaluate_inner(&self, effects: &EffectRow, ctx: &Context) -> ActionVerdict {
        let bw = ctx.brain_wave;
        let homeostasis = self.homeostasis();
        let maturity = maturity_from_brain_wave(bw);
        // Strict mode = low-power brain wave (Theta/Delta) or stressed
        // homeostasis. Deliberate operator intent (`ctx.explicit_confirm`,
        // set by the dispatch pipeline from a `confirm: true` arg) passes
        // the brain-wave arm — a human explicitly authorized the action;
        // the stressed-homeostasis arm stays absolute (9.1.6).
        let strict = is_strict_mode(bw, &homeostasis, ctx.explicit_confirm);
        let karma_debt = ctx.karma_debt;
        let intent_score = ctx.intent_score;

        // Sutra 1: Ahimsa (non-harm) — check for destructive effects.
        //
        // Destruction is declared (`EffectRow::destructive`), not inferred
        // from resource types: additive filesystem writes (lease ledgers,
        // audit logs, gnosis explanations) are not harm, and inferring them
        // as destructive blocked coordination operations under system stress
        // (live-caught 2026-09-12: code.claim/code.release refused with
        // VIOLATION_AHIMSA at load 15). Process/Network writes and process
        // spawning stay destructive-by-class — side effects with no additive
        // reading. Destructive tools must set the flag for this gate and the
        // confirm gate alike.
        let is_destructive = effects.destructive
            || effects.spawns
            || effects
                .writes
                .iter()
                .any(|r| matches!(r, Resource::Process | Resource::Network));

        if is_destructive {
            if strict {
                return ActionVerdict::Panic(
                    "VIOLATION_AHIMSA: Destructive action blocked in strict mode (low energy or system stress)".into(),
                );
            } else if maturity < 4 && !ctx.explicit_confirm {
                return ActionVerdict::Intervene(
                    "Maturity level too low for destructive actions (requires Beta+ brain-wave)"
                        .into(),
                );
            }
        }

        // AHIMSA Target A (9.1.8): coordination lease acquisition/renewal is
        // refused in strict mode — stress must not trap new work, and the TTL
        // frees existing leases. Only two coordination shapes are admitted
        // under strict mode, by construction: exact-owner cleanup
        // (`Resource::CoordinationRelease`) and the no-discovery checkpoint
        // (a single Sessions write). Nothing here is a filesystem or process
        // exception.
        if strict && effects.acquires_coordination_lease() {
            return ActionVerdict::Panic(
                "VIOLATION_AHIMSA: coordination lease acquisition/renewal is refused in strict mode — release held leases explicitly or wait for TTL expiry".into(),
            );
        }

        // Sutra 2: Satya (truth) — prevent memory fabrication
        // Tools that write to Citta galaxy without reading are fabricating
        let writes_citta = effects
            .writes
            .iter()
            .any(|r| matches!(r, Resource::Galaxy(g) if g == "citta"));
        let reads_citta = effects
            .reads
            .iter()
            .any(|r| matches!(r, Resource::Galaxy(g) if g == "citta"));

        if writes_citta && !reads_citta {
            return ActionVerdict::Panic(
                "VIOLATION_SATYA: Memory fabrication — writing to citta without reading".into(),
            );
        }

        // Harmony vector thresholds (Tiferet Loop)
        // Intent score adjusted by karma debt and homeostasis health
        let health = homeostasis.health_score();
        let total_health = health.mul_add(0.1, karma_debt.mul_add(-0.1, intent_score));

        if total_health < 0.3 {
            ActionVerdict::Intervene(format!(
                "Critical karmic debt ({karma_debt:.2}) or low intent ({intent_score:.2}). Action blocked."
            ))
        } else if total_health < 0.5 {
            ActionVerdict::Correct(format!(
                "High karmic debt ({karma_debt:.2}). Proceeding with restrictions."
            ))
        } else if total_health < 0.7 {
            ActionVerdict::Advise("Harmony vector is destabilizing. Proceed with awareness.".into())
        } else {
            ActionVerdict::Observe
        }
    }
}

/// Convert a [`HarmonyVector`](wm_substrate::HarmonyVector) into [`Homeostasis`].
///
/// This bridges the substrate monitor (Lakshmi) to the Dharma gate,
/// populating the homeostasis fields with real hardware data. The
/// `active` flag is derived from CPU load (> 15% = active).
impl From<wm_substrate::HarmonyVector> for Homeostasis {
    fn from(hv: wm_substrate::HarmonyVector) -> Self {
        Self {
            cpu_load: hv.cpu_load,
            memory_pressure: hv.memory_pressure,
            active: hv.active,
        }
    }
}

impl Default for DharmaGate {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Context;

    #[test]
    fn observe_when_healthy() {
        let gate = DharmaGate::new();
        let ctx = Context::new(BrainWave::Gamma);
        let effects = EffectRow::read_only(vec![Resource::Galaxy("codex".into())]);
        let verdict = gate.evaluate(&effects, &ctx);
        assert_eq!(verdict, ActionVerdict::Observe);
    }

    #[test]
    fn verdict_counters_track_evaluations() {
        let gate = DharmaGate::new();
        let ctx = Context::new(BrainWave::Gamma);
        let effects = EffectRow::read_only(vec![Resource::Galaxy("codex".into())]);
        let before = verdict_counts();
        let verdict = gate.evaluate(&effects, &ctx);
        let after = verdict_counts();
        assert_eq!(verdict, ActionVerdict::Observe);
        assert!(after.observe > before.observe);
        assert!(after.total() > before.total());
        assert!(after.blocked() >= before.blocked());
        let ratio = after.blocked_ratio();
        assert!((0.0..=1.0).contains(&ratio));
    }

    #[test]
    fn panic_on_destructive_in_strict_mode() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Theta); // Strict mode
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            destructive: true,
            spawns: false,
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(verdict.blocks());
        assert!(matches!(verdict, ActionVerdict::Panic(_)));
    }

    #[test]
    fn coordination_lease_acquisition_refused_in_strict_mode() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Theta);
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            reads: vec![Resource::Filesystem],
            writes: vec![Resource::CoordinationLease],
            ..Default::default()
        };
        assert!(effects.acquires_coordination_lease());
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(matches!(verdict, ActionVerdict::Panic(_)), "{verdict:?}");
    }

    #[test]
    fn coordination_lease_refused_under_stress_with_normal_brain_wave() {
        let gate = DharmaGate::new();
        gate.update_homeostasis(Homeostasis {
            cpu_load: 0.95,
            memory_pressure: 0.95,
            active: true,
        });
        let mut ctx = Context::new(BrainWave::Beta);
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::CoordinationLease],
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(matches!(verdict, ActionVerdict::Panic(_)), "{verdict:?}");
    }

    #[test]
    fn coordination_cleanup_and_nodiscovery_checkpoint_admitted_in_strict_mode() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Theta);
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;

        let cleanup = EffectRow {
            reads: vec![Resource::Filesystem],
            writes: vec![Resource::CoordinationRelease],
            ..Default::default()
        };
        assert!(cleanup.is_coordination_cleanup());
        let verdict = gate.evaluate(&cleanup, &ctx);
        assert!(
            !verdict.blocks(),
            "owner cleanup must stay available under stress: {verdict:?}"
        );

        let nodiscovery = EffectRow {
            writes: vec![Resource::Galaxy("sessions".into())],
            ..Default::default()
        };
        assert!(nodiscovery.is_no_discovery_checkpoint());
        let verdict = gate.evaluate(&nodiscovery, &ctx);
        assert!(
            !verdict.blocks(),
            "no-discovery checkpoint must stay available under stress: {verdict:?}"
        );
    }

    #[test]
    fn rich_checkpoint_spawns_are_refused_in_strict_mode() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Theta);
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            reads: vec![Resource::Filesystem],
            writes: vec![Resource::Galaxy("sessions".into())],
            spawns: true,
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(matches!(verdict, ActionVerdict::Panic(_)), "{verdict:?}");
    }

    #[test]
    fn intervene_on_destructive_low_maturity() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Alpha); // maturity=3, not strict
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            destructive: true,
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(verdict.blocks());
        assert!(matches!(verdict, ActionVerdict::Intervene(_)));
    }

    #[test]
    fn allow_destructive_at_high_maturity() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Gamma); // maturity=5
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            destructive: true,
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert_eq!(verdict, ActionVerdict::Observe);
    }

    #[test]
    fn additive_filesystem_write_allowed_in_strict_mode() {
        // Additive FS writes (lease ledgers, audit logs) are not destruction:
        // strict mode must not block them. Live-caught 2026-09-12 —
        // code.claim/code.release were refused under system stress.
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Theta); // strict
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert_eq!(verdict, ActionVerdict::Observe);
    }

    #[test]
    fn process_write_still_blocked_in_strict_mode() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Theta);
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::Process],
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(verdict.blocks());
    }

    #[test]
    fn panic_on_memory_fabrication() {
        let gate = DharmaGate::new();
        let ctx = Context::new(BrainWave::Gamma);
        let effects = EffectRow {
            writes: vec![Resource::Galaxy("citta".into())],
            reads: vec![],
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(matches!(verdict, ActionVerdict::Panic(_)));
    }

    #[test]
    fn allow_citta_write_with_read() {
        let gate = DharmaGate::new();
        let ctx = Context::new(BrainWave::Gamma);
        let effects = EffectRow {
            reads: vec![Resource::Galaxy("citta".into())],
            writes: vec![Resource::Galaxy("citta".into())],
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert_eq!(verdict, ActionVerdict::Observe);
    }

    #[test]
    fn intervene_on_critical_karma_debt() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.karma_debt = 5.0; // High debt
        ctx.intent_score = 0.5;
        let effects = EffectRow::pure();
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(verdict.blocks());
        assert!(matches!(verdict, ActionVerdict::Intervene(_)));
    }

    #[test]
    fn advise_on_destabilizing_harmony() {
        let gate = DharmaGate::new();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.karma_debt = 2.0;
        ctx.intent_score = 0.6;
        let effects = EffectRow::pure();
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(verdict.is_warning());
        assert!(matches!(verdict, ActionVerdict::Advise(_)));
    }

    #[test]
    fn strict_mode_under_system_stress() {
        let gate = DharmaGate::new();
        gate.update_homeostasis(Homeostasis {
            cpu_load: 0.9,
            memory_pressure: 0.8,
            active: true,
        });
        let mut ctx = Context::new(BrainWave::Beta); // Normally not strict
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            destructive: true,
            ..Default::default()
        };
        let verdict = gate.evaluate(&effects, &ctx);
        assert!(
            verdict.blocks(),
            "Should block destructive action under system stress"
        );
    }

    #[test]
    fn homeostasis_health_score() {
        let h = Homeostasis {
            cpu_load: 0.2,
            memory_pressure: 0.3,
            active: true,
        };
        assert!(h.health_score() > 0.7);
        assert!(!h.is_stressed());

        let h2 = Homeostasis {
            cpu_load: 0.9,
            memory_pressure: 0.9,
            active: true,
        };
        assert!(h2.health_score() < 0.2);
        assert!(h2.is_stressed());
    }

    #[test]
    fn verdict_blocks_and_warning() {
        assert!(!ActionVerdict::Observe.blocks());
        assert!(!ActionVerdict::Observe.is_warning());
        assert!(!ActionVerdict::Advise("test".into()).blocks());
        assert!(ActionVerdict::Advise("test".into()).is_warning());
        assert!(ActionVerdict::Intervene("test".into()).blocks());
        assert!(!ActionVerdict::Intervene("test".into()).is_warning());
        assert!(ActionVerdict::Panic("test".into()).blocks());
    }

    #[test]
    fn harmony_vector_to_homeostasis_conversion() {
        let hv = wm_substrate::HarmonyVector {
            cpu_load: 0.5,
            memory_pressure: 0.6,
            swap_usage: 0.3,
            thermal_state: wm_substrate::ThermalState::Warm,
            temperature_c: Some(65.0),
            battery_state: wm_substrate::BatteryState::Discharging,
            battery_percent: 0.5,
            disk_io_rate: 0.0,
            active: true,
            guna: wm_substrate::GunaTag::Rajasic,
            timestamp: chrono::Utc::now(),
        };
        let h: Homeostasis = hv.into();
        assert!((h.cpu_load - 0.5).abs() < 0.01);
        assert!((h.memory_pressure - 0.6).abs() < 0.01);
        assert!(h.active);
    }

    // ── Property-based tests (proptest) ─────────────────────────────

    use proptest::prelude::*;

    fn arb_brain_wave() -> impl Strategy<Value = BrainWave> {
        prop_oneof![
            Just(BrainWave::Gamma),
            Just(BrainWave::Beta),
            Just(BrainWave::Alpha),
            Just(BrainWave::Theta),
            Just(BrainWave::Delta),
        ]
    }

    fn arb_resource() -> impl Strategy<Value = Resource> {
        prop_oneof![
            Just(Resource::Galaxy("codex".into())),
            Just(Resource::Galaxy("citta".into())),
            Just(Resource::Galaxy("aria".into())),
            Just(Resource::Filesystem),
            Just(Resource::Network),
            Just(Resource::Process),
            Just(Resource::KarmaLedger),
            Just(Resource::SearchIndex),
        ]
    }

    fn arb_effect_row() -> impl Strategy<Value = EffectRow> {
        (
            proptest::collection::vec(arb_resource(), 0..8),
            proptest::collection::vec(arb_resource(), 0..8),
            any::<bool>(),
            any::<bool>(),
        )
            .prop_map(|(reads, writes, spawns, destructive)| EffectRow {
                reads,
                writes,
                spawns,
                destructive,
                ..Default::default()
            })
    }

    proptest! {
        /// evaluate() must never panic with any combination of inputs.
        #[test]
        fn evaluate_never_panics(
            bw in arb_brain_wave(),
            karma_debt in 0.0f32..10.0,
            intent_score in 0.0f32..1.0,
            cpu_load in 0.0f32..1.0,
            mem_pressure in 0.0f32..1.0,
            effects in arb_effect_row(),
        ) {
            let gate = DharmaGate::new();
            gate.update_homeostasis(Homeostasis {
                cpu_load,
                memory_pressure: mem_pressure,
                active: cpu_load > 0.15,
            });
            let mut ctx = Context::new(bw);
            ctx.karma_debt = karma_debt;
            ctx.intent_score = intent_score;
            let verdict = gate.evaluate(&effects, &ctx);
            // Verdict must be well-formed
            let _ = verdict.blocks();
            let _ = verdict.is_warning();
            let _ = verdict.reason();
        }

        /// Delta brain-wave with destructive effects must always block.
        #[test]
        fn delta_blocks_destructive(
            karma_debt in 0.0f32..5.0,
            effects in arb_effect_row(),
        ) {
            let gate = DharmaGate::new();
            let mut ctx = Context::new(BrainWave::Delta);
            ctx.karma_debt = karma_debt;
            ctx.intent_score = 1.0;
            let verdict = gate.evaluate(&effects, &ctx);
            // Delta is strict mode — destructive actions must block
            let is_destructive = effects.destructive
                || effects.spawns
                || effects
                    .writes
                    .iter()
                    .any(|r| matches!(r, Resource::Process | Resource::Network));
            if is_destructive {
                prop_assert!(verdict.blocks(), "Delta must block destructive: {:?}", verdict);
            }
        }

        /// Satya violation (write citta without read) must always Panic.
        #[test]
        fn satya_violation_always_panics(
            bw in arb_brain_wave(),
            karma_debt in 0.0f32..10.0,
            intent_score in 0.0f32..1.0,
        ) {
            let gate = DharmaGate::new();
            let mut ctx = Context::new(bw);
            ctx.karma_debt = karma_debt;
            ctx.intent_score = intent_score;
            let effects = EffectRow {
                writes: vec![Resource::Galaxy("citta".into())],
                reads: vec![],
                ..Default::default()
            };
            let verdict = gate.evaluate(&effects, &ctx);
            prop_assert!(
                matches!(verdict, ActionVerdict::Panic(_)),
                "Satya violation must Panic, got {:?}",
                verdict
            );
        }

        /// health_score is always in [0, 1].
        #[test]
        fn health_score_bounded(
            cpu_load in 0.0f32..1.0,
            mem_pressure in 0.0f32..1.0,
        ) {
            let h = Homeostasis {
                cpu_load,
                memory_pressure: mem_pressure,
                active: true,
            };
            let score = h.health_score();
            prop_assert!((0.0..=1.0).contains(&score), "health_score {score} out of [0,1]");
        }
    }
}
