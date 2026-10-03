//! Stateless cognitive recipes and Gana transform policies (Charter §3.10, Article 4).
//!
//! # Epistemic Principles
//!
//! 1. **Symbols May Render; Symbols May Never Dispatch (Charter §3.10):**
//!    Ganas are not autonomous agent personas, background daemons, or execution actors.
//!    They are pure, stateless parameter configurations (`TransformPolicy` / `Recipe`)
//!    modulating operational lenses over standard kernel operations:
//!    `remember`, `recall`, `think`, and `inspect`.
//!
//! 2. **Authoritative Background Loops = 0 (Article 4):**
//!    Cognitive lenses never spawn execution threads, maintain un-audited state, or
//!    execute unearned background mutations. All evaluations occur inside active,
//!    authorized pulses bearing `CommitCapability`.
//!
//! 3. **Conformal Forgotten Diamonds:**
//!    High-value dormant memories are recovered through conformal uncertainty
//!    expansion and exponential salience decay, replacing ad-hoc background cron sweeps.

use crate::evidence::EvidenceRecord;
use serde::{Deserialize, Serialize};

/// The four classical taxonomic families of Gana cognitive lenses.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum GanaFamily {
    Analytical,
    Synthesis,
    Operational,
    Guardrail,
}

/// The 28 canonical Gana archetypes re-derived as stateless lenses.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum GanaArchetype {
    // Family 1: Analytical (7)
    Pratyeka,
    Viveka,
    Vicara,
    Prajna,
    Smrti,
    Sati,
    Mimamsa,

    // Family 2: Synthesis (7)
    Sravaka,
    Samadhi,
    Dhyana,
    Bhavana,
    Alchemical,
    Consolidation,
    Mandala,

    // Family 3: Operational (7)
    Ksetra,
    Karma,
    Upaya,
    Virya,
    Kalyanamitra,
    Dana,
    Sila,

    // Family 4: Guardrail (7)
    Ksanti,
    Upeksa,
    Dharma,
    Nirodha,
    Yana,
    Bodhi,
    Tathata,
}

impl GanaArchetype {
    #[must_use]
    pub const fn family(&self) -> GanaFamily {
        match self {
            Self::Pratyeka
            | Self::Viveka
            | Self::Vicara
            | Self::Prajna
            | Self::Smrti
            | Self::Sati
            | Self::Mimamsa => GanaFamily::Analytical,

            Self::Sravaka
            | Self::Samadhi
            | Self::Dhyana
            | Self::Bhavana
            | Self::Alchemical
            | Self::Consolidation
            | Self::Mandala => GanaFamily::Synthesis,

            Self::Ksetra
            | Self::Karma
            | Self::Upaya
            | Self::Virya
            | Self::Kalyanamitra
            | Self::Dana
            | Self::Sila => GanaFamily::Operational,

            Self::Ksanti
            | Self::Upeksa
            | Self::Dharma
            | Self::Nirodha
            | Self::Yana
            | Self::Bodhi
            | Self::Tathata => GanaFamily::Guardrail,
        }
    }

    #[must_use]
    pub const fn label(&self) -> &'static str {
        match self {
            Self::Pratyeka => "Pratyeka (Independent Inquiry)",
            Self::Viveka => "Viveka (Discernment)",
            Self::Vicara => "Vicara (Sustained Investigation)",
            Self::Prajna => "Prajna (Transcendental Insight)",
            Self::Smrti => "Smrti (Mindful Retention)",
            Self::Sati => "Sati (Vigilant Attention)",
            Self::Mimamsa => "Mimamsa (Rigorous Verification)",

            Self::Sravaka => "Sravaka (Attentive Ingestion)",
            Self::Samadhi => "Samadhi (Deep Convergence)",
            Self::Dhyana => "Dhyana (Meditative Synthesis)",
            Self::Bhavana => "Bhavana (Cumulative Cultivation)",
            Self::Alchemical => "Alchemical (Cross-Domain Fusion)",
            Self::Consolidation => "Consolidation (Episodic Compression)",
            Self::Mandala => "Mandala (Topological Whole)",

            Self::Ksetra => "Ksetra (Field Navigation)",
            Self::Karma => "Karma (Causal Trajectory)",
            Self::Upaya => "Upaya (Skilled Expediency)",
            Self::Virya => "Virya (Tenacious Application)",
            Self::Kalyanamitra => "Kalyanamitra (Collaborative Resonance)",
            Self::Dana => "Dana (Generous Emission)",
            Self::Sila => "Sila (Disciplined Grounding)",

            Self::Ksanti => "Ksanti (Patient Endurance)",
            Self::Upeksa => "Upeksa (Equanimous Balance)",
            Self::Dharma => "Dharma (Constitutional Invariance)",
            Self::Nirodha => "Nirodha (Noise Quenching)",
            Self::Yana => "Yana (Evolutionary Vehicle)",
            Self::Bodhi => "Bodhi (Awakened Coherence)",
            Self::Tathata => "Tathata (Reality Grounding)",
        }
    }
}

/// Stateless cognitive recipe modulating operational parameters.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Recipe {
    pub archetype: GanaArchetype,
    pub family: GanaFamily,
    pub name: &'static str,
    pub temperature: f32,
    pub conformal_alpha: f64,
    pub relevance_floor: f32,
    pub salience_bias: f32,
    pub temporal_horizon_sweeps: u64,
    pub diamond_harvest: bool,
}

impl Recipe {
    /// Return the canonical preset for any given Gana archetype.
    #[must_use]
    pub const fn preset(archetype: GanaArchetype) -> Self {
        let family = archetype.family();
        match archetype {
            // Analytical: High precision, lower temperature, tight conformal alpha
            GanaArchetype::Pratyeka => Self {
                archetype,
                family,
                name: "Pratyeka",
                temperature: 0.2,
                conformal_alpha: 0.05,
                relevance_floor: 0.55,
                salience_bias: 0.3,
                temporal_horizon_sweeps: 100,
                diamond_harvest: false,
            },
            GanaArchetype::Viveka => Self {
                archetype,
                family,
                name: "Viveka",
                temperature: 0.1,
                conformal_alpha: 0.02,
                relevance_floor: 0.60,
                salience_bias: 0.2,
                temporal_horizon_sweeps: 80,
                diamond_harvest: false,
            },
            GanaArchetype::Vicara => Self {
                archetype,
                family,
                name: "Vicara",
                temperature: 0.3,
                conformal_alpha: 0.05,
                relevance_floor: 0.50,
                salience_bias: 0.4,
                temporal_horizon_sweeps: 120,
                diamond_harvest: false,
            },
            GanaArchetype::Prajna => Self {
                archetype,
                family,
                name: "Prajna",
                temperature: 0.4,
                conformal_alpha: 0.05,
                relevance_floor: 0.52,
                salience_bias: 0.6,
                temporal_horizon_sweeps: 200,
                diamond_harvest: true,
            },
            GanaArchetype::Smrti => Self {
                archetype,
                family,
                name: "Smrti",
                temperature: 0.1,
                conformal_alpha: 0.01,
                relevance_floor: 0.50,
                salience_bias: 0.8,
                temporal_horizon_sweeps: 500,
                diamond_harvest: true,
            },
            GanaArchetype::Sati => Self {
                archetype,
                family,
                name: "Sati",
                temperature: 0.2,
                conformal_alpha: 0.05,
                relevance_floor: 0.50,
                salience_bias: 0.5,
                temporal_horizon_sweeps: 50,
                diamond_harvest: false,
            },
            GanaArchetype::Mimamsa => Self {
                archetype,
                family,
                name: "Mimamsa",
                temperature: 0.05,
                conformal_alpha: 0.01,
                relevance_floor: 0.65,
                salience_bias: 0.1,
                temporal_horizon_sweeps: 60,
                diamond_harvest: false,
            },

            // Synthesis: Balanced exploration, broad horizons, diamond-seeking
            GanaArchetype::Sravaka => Self {
                archetype,
                family,
                name: "Sravaka",
                temperature: 0.3,
                conformal_alpha: 0.10,
                relevance_floor: 0.45,
                salience_bias: 0.3,
                temporal_horizon_sweeps: 40,
                diamond_harvest: false,
            },
            GanaArchetype::Samadhi => Self {
                archetype,
                family,
                name: "Samadhi",
                temperature: 0.2,
                conformal_alpha: 0.05,
                relevance_floor: 0.55,
                salience_bias: 0.7,
                temporal_horizon_sweeps: 250,
                diamond_harvest: true,
            },
            GanaArchetype::Dhyana => Self {
                archetype,
                family,
                name: "Dhyana",
                temperature: 0.4,
                conformal_alpha: 0.08,
                relevance_floor: 0.50,
                salience_bias: 0.6,
                temporal_horizon_sweeps: 300,
                diamond_harvest: true,
            },
            GanaArchetype::Bhavana => Self {
                archetype,
                family,
                name: "Bhavana",
                temperature: 0.35,
                conformal_alpha: 0.05,
                relevance_floor: 0.50,
                salience_bias: 0.7,
                temporal_horizon_sweeps: 400,
                diamond_harvest: true,
            },
            GanaArchetype::Alchemical => Self {
                archetype,
                family,
                name: "Alchemical",
                temperature: 0.6,
                conformal_alpha: 0.10,
                relevance_floor: 0.48,
                salience_bias: 0.8,
                temporal_horizon_sweeps: 500,
                diamond_harvest: true,
            },
            GanaArchetype::Consolidation => Self {
                archetype,
                family,
                name: "Consolidation",
                temperature: 0.2,
                conformal_alpha: 0.05,
                relevance_floor: 0.52,
                salience_bias: 0.9,
                temporal_horizon_sweeps: 600,
                diamond_harvest: true,
            },
            GanaArchetype::Mandala => Self {
                archetype,
                family,
                name: "Mandala",
                temperature: 0.5,
                conformal_alpha: 0.08,
                relevance_floor: 0.50,
                salience_bias: 0.85,
                temporal_horizon_sweeps: 750,
                diamond_harvest: true,
            },

            // Operational: Responsive, moderate horizons, pragmatic relevance
            GanaArchetype::Ksetra => Self {
                archetype,
                family,
                name: "Ksetra",
                temperature: 0.4,
                conformal_alpha: 0.08,
                relevance_floor: 0.50,
                salience_bias: 0.4,
                temporal_horizon_sweeps: 80,
                diamond_harvest: false,
            },
            GanaArchetype::Karma => Self {
                archetype,
                family,
                name: "Karma",
                temperature: 0.25,
                conformal_alpha: 0.05,
                relevance_floor: 0.52,
                salience_bias: 0.5,
                temporal_horizon_sweeps: 150,
                diamond_harvest: false,
            },
            GanaArchetype::Upaya => Self {
                archetype,
                family,
                name: "Upaya",
                temperature: 0.45,
                conformal_alpha: 0.10,
                relevance_floor: 0.48,
                salience_bias: 0.4,
                temporal_horizon_sweeps: 90,
                diamond_harvest: false,
            },
            GanaArchetype::Virya => Self {
                archetype,
                family,
                name: "Virya",
                temperature: 0.35,
                conformal_alpha: 0.06,
                relevance_floor: 0.50,
                salience_bias: 0.5,
                temporal_horizon_sweeps: 100,
                diamond_harvest: false,
            },
            GanaArchetype::Kalyanamitra => Self {
                archetype,
                family,
                name: "Kalyanamitra",
                temperature: 0.4,
                conformal_alpha: 0.08,
                relevance_floor: 0.50,
                salience_bias: 0.6,
                temporal_horizon_sweeps: 120,
                diamond_harvest: true,
            },
            GanaArchetype::Dana => Self {
                archetype,
                family,
                name: "Dana",
                temperature: 0.5,
                conformal_alpha: 0.10,
                relevance_floor: 0.45,
                salience_bias: 0.5,
                temporal_horizon_sweeps: 70,
                diamond_harvest: false,
            },
            GanaArchetype::Sila => Self {
                archetype,
                family,
                name: "Sila",
                temperature: 0.15,
                conformal_alpha: 0.02,
                relevance_floor: 0.58,
                salience_bias: 0.4,
                temporal_horizon_sweeps: 150,
                diamond_harvest: false,
            },

            // Guardrail: High discipline, strict conformal coverage, defensive thresholds
            GanaArchetype::Ksanti => Self {
                archetype,
                family,
                name: "Ksanti",
                temperature: 0.2,
                conformal_alpha: 0.04,
                relevance_floor: 0.52,
                salience_bias: 0.4,
                temporal_horizon_sweeps: 200,
                diamond_harvest: false,
            },
            GanaArchetype::Upeksa => Self {
                archetype,
                family,
                name: "Upeksa",
                temperature: 0.1,
                conformal_alpha: 0.02,
                relevance_floor: 0.55,
                salience_bias: 0.3,
                temporal_horizon_sweeps: 150,
                diamond_harvest: false,
            },
            GanaArchetype::Dharma => Self {
                archetype,
                family,
                name: "Dharma",
                temperature: 0.0,
                conformal_alpha: 0.005,
                relevance_floor: 0.70,
                salience_bias: 0.1,
                temporal_horizon_sweeps: 1000,
                diamond_harvest: false,
            },
            GanaArchetype::Nirodha => Self {
                archetype,
                family,
                name: "Nirodha",
                temperature: 0.05,
                conformal_alpha: 0.01,
                relevance_floor: 0.65,
                salience_bias: 0.0,
                temporal_horizon_sweeps: 50,
                diamond_harvest: false,
            },
            GanaArchetype::Yana => Self {
                archetype,
                family,
                name: "Yana",
                temperature: 0.3,
                conformal_alpha: 0.05,
                relevance_floor: 0.52,
                salience_bias: 0.5,
                temporal_horizon_sweeps: 350,
                diamond_harvest: true,
            },
            GanaArchetype::Bodhi => Self {
                archetype,
                family,
                name: "Bodhi",
                temperature: 0.25,
                conformal_alpha: 0.03,
                relevance_floor: 0.58,
                salience_bias: 0.8,
                temporal_horizon_sweeps: 500,
                diamond_harvest: true,
            },
            GanaArchetype::Tathata => Self {
                archetype,
                family,
                name: "Tathata",
                temperature: 0.0,
                conformal_alpha: 0.01,
                relevance_floor: 0.60,
                salience_bias: 0.5,
                temporal_horizon_sweeps: 500,
                diamond_harvest: true,
            },
        }
    }

    /// Return all 28 canonical recipes.
    #[must_use]
    pub fn all_presets() -> [Self; 28] {
        [
            Self::preset(GanaArchetype::Pratyeka),
            Self::preset(GanaArchetype::Viveka),
            Self::preset(GanaArchetype::Vicara),
            Self::preset(GanaArchetype::Prajna),
            Self::preset(GanaArchetype::Smrti),
            Self::preset(GanaArchetype::Sati),
            Self::preset(GanaArchetype::Mimamsa),
            Self::preset(GanaArchetype::Sravaka),
            Self::preset(GanaArchetype::Samadhi),
            Self::preset(GanaArchetype::Dhyana),
            Self::preset(GanaArchetype::Bhavana),
            Self::preset(GanaArchetype::Alchemical),
            Self::preset(GanaArchetype::Consolidation),
            Self::preset(GanaArchetype::Mandala),
            Self::preset(GanaArchetype::Ksetra),
            Self::preset(GanaArchetype::Karma),
            Self::preset(GanaArchetype::Upaya),
            Self::preset(GanaArchetype::Virya),
            Self::preset(GanaArchetype::Kalyanamitra),
            Self::preset(GanaArchetype::Dana),
            Self::preset(GanaArchetype::Sila),
            Self::preset(GanaArchetype::Ksanti),
            Self::preset(GanaArchetype::Upeksa),
            Self::preset(GanaArchetype::Dharma),
            Self::preset(GanaArchetype::Nirodha),
            Self::preset(GanaArchetype::Yana),
            Self::preset(GanaArchetype::Bodhi),
            Self::preset(GanaArchetype::Tathata),
        ]
    }
}

/// Conformal Forgotten Diamond recovery candidate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DiamondCandidate {
    pub record_id: u64,
    pub intrinsic_confidence: f32,
    pub diamond_score: f64,
    pub delta_sweeps: u64,
    pub access_count: u64,
}

/// Pure deterministic evaluator for dormant memories and forgotten diamonds.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct DiamondEvaluator {
    /// Half-life in sweeps for dormant memory attention decay. Default: 50.0 sweeps.
    pub half_life_sweeps: f64,
    /// Minimum score threshold to qualify as a diamond. Default: 0.35.
    pub diamond_floor: f64,
}

impl Default for DiamondEvaluator {
    fn default() -> Self {
        Self {
            half_life_sweeps: 50.0,
            diamond_floor: 0.35,
        }
    }
}

impl DiamondEvaluator {
    #[must_use]
    pub const fn new(half_life_sweeps: f64, diamond_floor: f64) -> Self {
        Self {
            half_life_sweeps,
            diamond_floor,
        }
    }

    /// Compute exponential dormant decay: S(t) = S0 * 0.5^(dt / tau).
    #[must_use]
    pub fn temporal_salience(&self, initial_salience: f32, delta_sweeps: u64) -> f64 {
        let ratio = delta_sweeps as f64 / self.half_life_sweeps.max(1.0);
        (initial_salience as f64) * 0.5_f64.powf(ratio)
    }

    /// Compute diamond score: combines high intrinsic salience, dormancy decay,
    /// and inverse access frequency (rewarding valuable un-accessed memories).
    #[must_use]
    pub fn compute_diamond_score(
        &self,
        initial_confidence: f32,
        delta_sweeps: u64,
        access_count: u64,
    ) -> f64 {
        let salience = self.temporal_salience(initial_confidence, delta_sweeps);
        let dormancy_factor = 1.0 / (1.0 + access_count as f64);
        salience * dormancy_factor
    }

    /// Evaluate whether a candidate record qualifies as a Forgotten Diamond
    /// under conformal uncertainty expansion.
    #[must_use]
    pub fn evaluate_record(
        &self,
        record: &EvidenceRecord,
        current_sweep: u64,
        access_count: u64,
    ) -> Option<DiamondCandidate> {
        let delta_sweeps = current_sweep.saturating_sub(record.created_at());
        let score = self.compute_diamond_score(record.confidence(), delta_sweeps, access_count);
        if score >= self.diamond_floor {
            Some(DiamondCandidate {
                record_id: record.id(),
                intrinsic_confidence: record.confidence(),
                diamond_score: score,
                delta_sweeps,
                access_count,
            })
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evidence::{Class, Domain, RecordStatus};

    #[test]
    fn all_28_ganas_are_present_and_distinct() {
        let presets = Recipe::all_presets();
        assert_eq!(presets.len(), 28);
        let mut names = std::collections::HashSet::new();
        for p in &presets {
            assert!(!p.name.is_empty());
            assert!(names.insert(p.name), "duplicate name: {}", p.name);
            assert!(p.temperature >= 0.0 && p.temperature <= 1.0);
            assert!(p.conformal_alpha > 0.0 && p.conformal_alpha < 1.0);
            assert!(p.relevance_floor > 0.0 && p.relevance_floor < 1.0);
        }
    }

    #[test]
    fn family_distribution_is_balanced_seven_each() {
        let presets = Recipe::all_presets();
        let mut counts = std::collections::HashMap::new();
        for p in &presets {
            *counts.entry(p.family).or_insert(0) += 1;
        }
        assert_eq!(counts[&GanaFamily::Analytical], 7);
        assert_eq!(counts[&GanaFamily::Synthesis], 7);
        assert_eq!(counts[&GanaFamily::Operational], 7);
        assert_eq!(counts[&GanaFamily::Guardrail], 7);
    }

    #[test]
    fn diamond_scoring_follows_exponential_decay() {
        let evaluator = DiamondEvaluator::new(50.0, 0.20);
        // At delta = 0, access = 0: score == initial confidence
        let s0 = evaluator.compute_diamond_score(1.0, 0, 0);
        assert!((s0 - 1.0).abs() < 1e-6);

        // At delta = 50 (1 half life), access = 0: score == 0.5
        let s50 = evaluator.compute_diamond_score(1.0, 50, 0);
        assert!((s50 - 0.5).abs() < 1e-6);

        // At delta = 100 (2 half lives), access = 0: score == 0.25
        let s100 = evaluator.compute_diamond_score(1.0, 100, 0);
        assert!((s100 - 0.25).abs() < 1e-6);

        // High access reduces diamond score (not forgotten)
        let s50_accessed = evaluator.compute_diamond_score(1.0, 50, 9);
        assert!((s50_accessed - 0.05).abs() < 1e-6);
    }

    #[test]
    fn diamond_evaluation_identifies_candidates() {
        let evaluator = DiamondEvaluator::new(100.0, 0.30);
        let record = EvidenceRecord::from_wire(
            42,
            Domain::World,
            Class::Evidence,
            "fundamental architectural principle".into(),
            "operator:genesis".into(),
            1.0,
            RecordStatus::Persistent,
            10,
        );

        // Current sweep 50 (delta 40 sweeps), zero recent accesses
        let candidate = evaluator.evaluate_record(&record, 50, 0);
        assert!(candidate.is_some());
        let c = candidate.unwrap();
        assert_eq!(c.record_id, 42);
        assert!(c.diamond_score > 0.30);

        // Current sweep 1000 (delta 990 sweeps, ~10 half lives) -> score ~ 0.001 < 0.30
        let expired = evaluator.evaluate_record(&record, 1000, 0);
        assert!(expired.is_none());
    }
}
