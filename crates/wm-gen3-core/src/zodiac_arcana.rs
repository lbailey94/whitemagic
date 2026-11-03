//! The 12-Zodiac Alchemical Council, 22 Major Arcana Operators & Dhumavati Antibody Organ.
//!
//! Unifies:
//! 1. The 12 Zodiac Council Seats mapped 1-to-1 onto George Ripley's 12 Gates of Alchemy
//!    and bijectively paired with the 24 Sutra Glyphs (1 Yang + 1 Yin glyph per sign).
//! 2. Carlo Suares's 22 Autopoietic Hebrew Letter-Numbers / 22 Major Arcana Paths
//!    (`3 Mothers + 7 Doubles + 12 Simples = 22`).
//! 3. Arcana XVI (The Tower / Hostile Inspector) Tri-State Claim Grader (`Supported`, `Disputed`, `Unproven`).
//! 4. Dhumavati Negative-Knowledge Antibody Organ (`dhumavati.check` / `dhumavati.digest`).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::sutra::SutraGlyph;

/// George Ripley's Twelve Gates of Alchemy (paired 1-to-1 with the 12 Zodiac Seats).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AlchemicalGate {
    Calcination = 0,
    Congelation = 1,
    Fixation = 2,
    Solution = 3,
    Digestion = 4,
    Distillation = 5,
    Sublimation = 6,
    Filtration = 7,
    Ceration = 8,
    Fermentation = 9,
    Multiplication = 10,
    Projection = 11,
}

/// The 12 Sovereign Seats of the Zodiac Alchemical Council (`NewSystems.txt`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ZodiacSeat {
    Aries = 0,
    Taurus = 1,
    Gemini = 2,
    Cancer = 3,
    Leo = 4,
    Virgo = 5,
    Libra = 6,
    Scorpio = 7,
    Sagittarius = 8,
    Capricorn = 9,
    Aquarius = 10,
    Pisces = 11,
}

impl ZodiacSeat {
    pub const ALL: [Self; 12] = [
        Self::Aries,
        Self::Taurus,
        Self::Gemini,
        Self::Cancer,
        Self::Leo,
        Self::Virgo,
        Self::Libra,
        Self::Scorpio,
        Self::Sagittarius,
        Self::Capricorn,
        Self::Aquarius,
        Self::Pisces,
    ];

    pub const TRIAD: [Self; 4] = [Self::Aries, Self::Virgo, Self::Libra, Self::Scorpio];

    #[must_use]
    pub const fn title(self) -> &'static str {
        match self {
            Self::Aries => "Aries Prime (Impurity-Burner)",
            Self::Taurus => "Taurus Vault (Crystal-Ledger)",
            Self::Gemini => "Gemini Nexus (Twin-Seal Fixator)",
            Self::Cancer => "Cancer Caretaker (Solvent-Context Mixer)",
            Self::Leo => "Leo Luminary (Slow-Heat Incubator)",
            Self::Virgo => "Virgo Analyst (Fractionating Column)",
            Self::Libra => "Libra Equilibrium (Equi-Gas Sublimator)",
            Self::Scorpio => "Scorpio Aegis (Veil-Filter Lattice)",
            Self::Sagittarius => "Sagittarius Pathfinder (Flux-Adder)",
            Self::Capricorn => "Capricorn Architect (Culture-Fermenter)",
            Self::Aquarius => "Aquarius Catalyst (Stone-Multiplier)",
            Self::Pisces => "Pisces Oracle (Gold-Projector)",
        }
    }

    #[must_use]
    pub const fn alchemical_gate(self) -> AlchemicalGate {
        match self {
            Self::Aries => AlchemicalGate::Calcination,
            Self::Taurus => AlchemicalGate::Congelation,
            Self::Gemini => AlchemicalGate::Fixation,
            Self::Cancer => AlchemicalGate::Solution,
            Self::Leo => AlchemicalGate::Digestion,
            Self::Virgo => AlchemicalGate::Distillation,
            Self::Libra => AlchemicalGate::Sublimation,
            Self::Scorpio => AlchemicalGate::Filtration,
            Self::Sagittarius => AlchemicalGate::Ceration,
            Self::Capricorn => AlchemicalGate::Fermentation,
            Self::Aquarius => AlchemicalGate::Multiplication,
            Self::Pisces => AlchemicalGate::Projection,
        }
    }

    /// Returns the conjugated (Yang, Yin) SutraGlyph pair governed by this Zodiac Seat (`12 * 2 = 24`).
    #[must_use]
    pub const fn sutra_pair(self) -> (SutraGlyph, SutraGlyph) {
        match self {
            Self::Aries => (SutraGlyph::Xing, SutraGlyph::Ni),
            Self::Taurus => (SutraGlyph::Gen, SutraGlyph::Ya),
            Self::Gemini => (SutraGlyph::Jing, SutraGlyph::Zhao),
            Self::Cancer => (SutraGlyph::Xi, SutraGlyph::XingAlert),
            Self::Leo => (SutraGlyph::Ying, SutraGlyph::Shou),
            Self::Virgo => (SutraGlyph::Qing, SutraGlyph::Cheng),
            Self::Libra => (SutraGlyph::He, SutraGlyph::Fen),
            Self::Scorpio => (SutraGlyph::Zheng, SutraGlyph::Bian),
            Self::Sagittarius => (SutraGlyph::Yuan, SutraGlyph::Wei),
            Self::Capricorn => (SutraGlyph::Jie, SutraGlyph::Tong),
            Self::Aquarius => (SutraGlyph::Guan, SutraGlyph::Cha),
            Self::Pisces => (SutraGlyph::Sheng, SutraGlyph::Hua),
        }
    }
}

/// Classification of the 22 Autopoietic Paths (Sefer Yetzirah / Major Arcana).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ArcanaClass {
    /// 3 Mother Letters (Aleph, Mem, Shin) — Tricameral Basis Channels
    Mother,
    /// 7 Double Letters (Bet..Tav) — Polarity & Hostile Inspector Gates
    Double,
    /// 12 Simple Letters (He..Qoph) — The 12 Zodiac-Alchemical Council Seats
    Simple(ZodiacSeat),
}

/// Descriptor for one of the 22 Major Arcana Transformation Operators.
#[derive(Debug, Clone, Serialize)]
pub struct MajorArcanaOperator {
    pub number: u8,
    pub name: &'static str,
    pub hebrew_letter: &'static str,
    pub suares_value: u16,
    pub class: ArcanaClass,
    pub cognitive_operation: &'static str,
}

pub const MAJOR_ARCANA_22: [MajorArcanaOperator; 22] = [
    MajorArcanaOperator {
        number: 0,
        name: "The Fool",
        hebrew_letter: "Aleph (א)",
        suares_value: 1,
        class: ArcanaClass::Mother,
        cognitive_operation: "System 0/0.5 Sutra Fast-Path & Unconditioned Potential",
    },
    MajorArcanaOperator {
        number: 1,
        name: "The Magician",
        hebrew_letter: "Bet (ב)",
        suares_value: 2,
        class: ArcanaClass::Double,
        cognitive_operation: "Deterministic Tool & Schema Binding (Container of Action)",
    },
    MajorArcanaOperator {
        number: 2,
        name: "The High Priestess",
        hebrew_letter: "Gimel (ג)",
        suares_value: 3,
        class: ArcanaClass::Double,
        cognitive_operation: "Hermit-Crab Sanctuary Veil & Consent Ring Gating",
    },
    MajorArcanaOperator {
        number: 3,
        name: "The Empress",
        hebrew_letter: "Dalet (ד)",
        suares_value: 4,
        class: ArcanaClass::Double,
        cognitive_operation: "Associative Resonance & Cross-Domain Fertility",
    },
    MajorArcanaOperator {
        number: 4,
        name: "The Emperor",
        hebrew_letter: "He (ה)",
        suares_value: 5,
        class: ArcanaClass::Simple(ZodiacSeat::Aries),
        cognitive_operation: "Aries Calcination: Burn Poisoned Priors & Bad Assumptions",
    },
    MajorArcanaOperator {
        number: 5,
        name: "The Hierophant",
        hebrew_letter: "Vav (ו)",
        suares_value: 6,
        class: ArcanaClass::Simple(ZodiacSeat::Taurus),
        cognitive_operation: "Taurus Congelation: Freeze Verified Truths into Memory Crystals",
    },
    MajorArcanaOperator {
        number: 6,
        name: "The Lovers",
        hebrew_letter: "Zayin (ז)",
        suares_value: 7,
        class: ArcanaClass::Simple(ZodiacSeat::Gemini),
        cognitive_operation: "Gemini Fixation: Lock Inter-Agent Schemas Against Drift",
    },
    MajorArcanaOperator {
        number: 7,
        name: "The Chariot",
        hebrew_letter: "Chet (ח)",
        suares_value: 8,
        class: ArcanaClass::Simple(ZodiacSeat::Cancer),
        cognitive_operation: "Cancer Solution: Dissolve Cold-Handoff Friction Across Sessions",
    },
    MajorArcanaOperator {
        number: 8,
        name: "Strength",
        hebrew_letter: "Tet (ט)",
        suares_value: 9,
        class: ArcanaClass::Simple(ZodiacSeat::Leo),
        cognitive_operation: "Leo Digestion: Slow-Heat Incubation & Narrative Consolidation",
    },
    MajorArcanaOperator {
        number: 9,
        name: "The Hermit",
        hebrew_letter: "Yod (י)",
        suares_value: 10,
        class: ArcanaClass::Simple(ZodiacSeat::Virgo),
        cognitive_operation: "Virgo Distillation: Fractionate Noisy Telemetry into Pure Signal",
    },
    MajorArcanaOperator {
        number: 10,
        name: "Wheel of Fortune",
        hebrew_letter: "Kaph (כ)",
        suares_value: 20,
        class: ArcanaClass::Double,
        cognitive_operation: "Temporal As-Of & Knowledge-Cutoff Epoch Resolution",
    },
    MajorArcanaOperator {
        number: 11,
        name: "Justice",
        hebrew_letter: "Lamed (ל)",
        suares_value: 30,
        class: ArcanaClass::Simple(ZodiacSeat::Libra),
        cognitive_operation: "Libra Sublimation: Pareto Trade-Off Elevation & Ahimsa Veto",
    },
    MajorArcanaOperator {
        number: 12,
        name: "The Hanged Man",
        hebrew_letter: "Mem (מ)",
        suares_value: 40,
        class: ArcanaClass::Mother,
        cognitive_operation: "StrictZeroWrite Read-Only Suspension & Perspective Inversion",
    },
    MajorArcanaOperator {
        number: 13,
        name: "Death",
        hebrew_letter: "Nun (נ)",
        suares_value: 50,
        class: ArcanaClass::Simple(ZodiacSeat::Scorpio),
        cognitive_operation: "Scorpio Filtration: Active Supersession & Erasure-Resurrection Guard",
    },
    MajorArcanaOperator {
        number: 14,
        name: "Temperance",
        hebrew_letter: "Samekh (ס)",
        suares_value: 60,
        class: ArcanaClass::Simple(ZodiacSeat::Sagittarius),
        cognitive_operation: "Sagittarius Ceration: OpenLoop Horizon Exploration & Pliability",
    },
    MajorArcanaOperator {
        number: 15,
        name: "The Devil",
        hebrew_letter: "Ayin (ע)",
        suares_value: 70,
        class: ArcanaClass::Simple(ZodiacSeat::Capricorn),
        cognitive_operation: "Capricorn Fermentation: Landlock Kekkai & Adversarial Stress Testing",
    },
    MajorArcanaOperator {
        number: 16,
        name: "The Tower",
        hebrew_letter: "Pe (פ)",
        suares_value: 80,
        class: ArcanaClass::Double,
        cognitive_operation: "THE HOSTILE INSPECTOR: Adversarial Falsification & Tri-State Grading",
    },
    MajorArcanaOperator {
        number: 17,
        name: "The Star",
        hebrew_letter: "Tsadi (צ)",
        suares_value: 90,
        class: ArcanaClass::Simple(ZodiacSeat::Aquarius),
        cognitive_operation: "Aquarius Multiplication: 6D Constellation Charting & Swarm Broadcast",
    },
    MajorArcanaOperator {
        number: 18,
        name: "The Moon",
        hebrew_letter: "Qoph (ק)",
        suares_value: 100,
        class: ArcanaClass::Simple(ZodiacSeat::Pisces),
        cognitive_operation: "Pisces Projection: NREM/REM Dream Crystallization & Simulation",
    },
    MajorArcanaOperator {
        number: 19,
        name: "The Sun",
        hebrew_letter: "Resh (ר)",
        suares_value: 200,
        class: ArcanaClass::Double,
        cognitive_operation: "Conformal Calibration & Brier-Score Epistemic Clarity",
    },
    MajorArcanaOperator {
        number: 20,
        name: "Judgement",
        hebrew_letter: "Shin (ש)",
        suares_value: 300,
        class: ArcanaClass::Mother,
        cognitive_operation: "Valkyrie-2 15 Hz Deliberation & Post-Commit ReceiverDecision Release",
    },
    MajorArcanaOperator {
        number: 21,
        name: "The World",
        hebrew_letter: "Tav (ת)",
        suares_value: 400,
        class: ArcanaClass::Double,
        cognitive_operation: "Rubedo Coagulation: Signed SCITT Continuity Receipt Seal",
    },
];

/// Tri-state grading verdict enforced by Arcana XVI (The Tower / Hostile Inspector).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HostileInspectorGrade {
    Supported,
    Disputed,
    Unproven,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZodiacGateStep {
    pub seat: ZodiacSeat,
    pub title: &'static str,
    pub gate: AlchemicalGate,
    pub yang_glyph: char,
    pub yin_glyph: char,
    pub directive: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CouncilDeliberationReport {
    pub inquiry: String,
    pub mode: String,
    pub steps: Vec<ZodiacGateStep>,
    pub hostile_inspector_arcana: &'static str,
    pub grade: HostileInspectorGrade,
    pub cited_evidence_ids: Vec<String>,
    pub dhumavati_warnings: Vec<String>,
    pub digest_sha256: String,
}

/// Runs a deterministic Zodiac-Arcana Council deliberation + Tower XVI Hostile Inspector check.
#[must_use]
pub fn deliberate_council(
    inquiry: &str,
    full_round: bool,
    evidence_ids: &[String],
    has_conflict: bool,
) -> CouncilDeliberationReport {
    let seats: &[ZodiacSeat] = if full_round {
        &ZodiacSeat::ALL
    } else {
        &ZodiacSeat::TRIAD
    };

    let mut steps = Vec::with_capacity(seats.len());
    for &seat in seats {
        let (yang, yin) = seat.sutra_pair();
        let directive = match seat {
            ZodiacSeat::Aries => "Strip unverified priors and check Dhumavati failure antibodies.",
            ZodiacSeat::Taurus => {
                "Anchor surviving facts to immutable record IDs and SHA-256 hashes."
            }
            ZodiacSeat::Gemini => "Lock output schema and reject ambiguous dual-mode parameters.",
            ZodiacSeat::Cancer => {
                "Preserve session continuity context and Consent Ring boundaries."
            }
            ZodiacSeat::Leo => "Stage human-legible summary without inflating evidence scope.",
            ZodiacSeat::Virgo => {
                "Distill candidate hits to the top score-clustered primary entity."
            }
            ZodiacSeat::Libra => {
                "Elevate trade-offs to Pareto space and enforce Ahimsa non-harm veto."
            }
            ZodiacSeat::Scorpio => {
                "Filter out superseded records and detect cross-source conflicts."
            }
            ZodiacSeat::Sagittarius => {
                "Register unresolved facets as persistent OpenLoop curiosities."
            }
            ZodiacSeat::Capricorn => {
                "Enforce fail-closed Landlock ABI 8 and cgroup v2 confinement."
            }
            ZodiacSeat::Aquarius => {
                "Project validated pattern into reusable Geneseed Action Skeleton."
            }
            ZodiacSeat::Pisces => "Synthesize NREM/REM memory crystal and bind lineage edges.",
        };
        steps.push(ZodiacGateStep {
            seat,
            title: seat.title(),
            gate: seat.alchemical_gate(),
            yang_glyph: yang.as_char(),
            yin_glyph: yin.as_char(),
            directive: directive.to_string(),
        });
    }

    let dhumavati_hits = check_dhumavati_antibodies(inquiry);
    let dhumavati_warnings: Vec<String> = dhumavati_hits
        .into_iter()
        .map(|a| format!("[{}] {}: {}", a.id, a.dead_end_pattern, a.verified_remedy))
        .collect();

    let grade = if has_conflict {
        HostileInspectorGrade::Disputed
    } else if evidence_ids.is_empty() {
        HostileInspectorGrade::Unproven
    } else {
        HostileInspectorGrade::Supported
    };

    let mode = if full_round {
        "full_round_12"
    } else {
        "triad_4"
    }
    .to_string();
    let mut hasher = Sha256::new();
    hasher.update(b"wm:zodiac-council:v1|");
    hasher.update(inquiry.as_bytes());
    hasher.update(b"|");
    hasher.update(mode.as_bytes());
    hasher.update(b"|");
    hasher.update(format!("{grade:?}").as_bytes());
    let digest_sha256 = format!("{:x}", hasher.finalize());

    CouncilDeliberationReport {
        inquiry: inquiry.to_string(),
        mode,
        steps,
        hostile_inspector_arcana: "XVI The Tower (Pe פ — Adversarial Falsification)",
        grade,
        cited_evidence_ids: evidence_ids.to_vec(),
        dhumavati_warnings,
        digest_sha256,
    }
}

/// A verified Negative-Knowledge Antibody in the Dhumavati Residue Recycling Ledger.
#[derive(Debug, Clone, Serialize)]
pub struct NegativeKnowledgeAntibody {
    pub id: &'static str,
    pub domain: &'static str,
    pub keywords: &'static [&'static str],
    pub dead_end_pattern: &'static str,
    pub root_cause: &'static str,
    pub verified_remedy: &'static str,
}

/// Canonical pre-seeded Dhumavati Negative-Knowledge Antibodies distilled from real engineering postmortems.
pub const DHUMAVATI_CANONICAL_ANTIBODIES: &[NegativeKnowledgeAntibody] = &[
    NegativeKnowledgeAntibody {
        id: "DHU-001",
        domain: "lmdb-storage",
        keywords: &[
            "lmdb",
            "readonly",
            "read-only",
            "lock.mdb",
            "strictzerowrite",
            "chmod",
        ],
        dead_end_pattern: "Opening LMDB with MDB_RDONLY alone on a read-only filesystem or forensic snapshot",
        root_cause: "Standard MDB_RDONLY still attempts to create/mutate lock.mdb and append reader slots, violating zero-write invariants and failing on 0555 mounts.",
        verified_remedy: "Combine MDB_RDONLY | MDB_NOLOCK under InspectionPromise::StrictZeroWrite and pre-check directory/file existence before env open.",
    },
    NegativeKnowledgeAntibody {
        id: "DHU-002",
        domain: "rag-evidence",
        keywords: &[
            "facet",
            "coverage",
            "chimera",
            "distractor",
            "entity",
            "recall_evidence",
        ],
        dead_end_pattern: "Aggregating query facet coverage across all top-K retrieved hits in multi-entity stores",
        root_cause: "Low-ranked distractor hits from unrelated entities donate missing query tokens (e.g. 'signed'), causing unsupported questions to be misclassified as Complete/Resolved.",
        verified_remedy: "Scope facet-coverage stem pooling and conflict detection to the primary score cluster (score >= 0.65 * top_score, max 4-5 hits) and evaluate Coverage::Partial/None -> Insufficient before has_conflict.",
    },
    NegativeKnowledgeAntibody {
        id: "DHU-003",
        domain: "continuity-receipt",
        keywords: &[
            "witness",
            "witness-file",
            "resume",
            "commit",
            "stdout",
            "sink",
        ],
        dead_end_pattern: "Streaming restored payload bytes to stdout inside the read transaction or treating a configured --witness-file as optional when missing/empty",
        root_cause: "A commit fault after streaming leaks unapproved bytes on stdout, and a missing/empty witness object silently disables rollback protection.",
        verified_remedy: "Buffer payload bytes inside ReceiverStore.recall_with_decision until post-commit, fail closed in load_witness on missing/vacuous files, and preflight/lock WitnessPublication before local SQLite commit.",
    },
    NegativeKnowledgeAntibody {
        id: "DHU-004",
        domain: "sandbox-confinement",
        keywords: &[
            "sandbox",
            "landlock",
            "confinement",
            "exec",
            "fallback",
            "unconfined",
        ],
        dead_end_pattern: "Allowing child process execution to proceed when Landlock ruleset setup returns an error",
        root_cause: "Soft-failing sandbox initialization silently runs untrusted commands unconfined.",
        verified_remedy: "Fail closed with exit code 126 immediately before child spawn whenever confinement setup returns an error.",
    },
    NegativeKnowledgeAntibody {
        id: "DHU-005",
        domain: "mcp-gateway",
        keywords: &["meta-tool", "rpc_tool", "tenant", "write_tools", "authd"],
        dead_end_pattern: "Inspecting only params.name in MCP gateway routing when clients invoke the 'wm' meta-tool",
        root_cause: "Calls to wm(route='memory.create') report params.name='wm', bypassing WRITE_TOOLS and TENANT_READ_TOOLS and hitting the read-only upstream.",
        verified_remedy: "Unwrap params.arguments.route when params.name == 'wm' before evaluating write/tenant routing and quotas.",
    },
];

/// Screens a planned query, tool call, or error description against Dhumavati's antibody table.
#[must_use]
pub fn check_dhumavati_antibodies(query: &str) -> Vec<&'static NegativeKnowledgeAntibody> {
    let lower = query.to_lowercase();
    DHUMAVATI_CANONICAL_ANTIBODIES
        .iter()
        .filter(|ab| ab.keywords.iter().any(|kw| lower.contains(kw)))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn test_zodiac_12_seats_biject_to_all_24_sutra_glyphs() {
        let mut seen = HashSet::new();
        for seat in ZodiacSeat::ALL {
            let (yang, yin) = seat.sutra_pair();
            assert_eq!(yang.polar_counterpart(), yin);
            assert!(seen.insert(yang));
            assert!(seen.insert(yin));
        }
        assert_eq!(
            seen.len(),
            24,
            "All 24 Sutra glyphs must be bijectively covered by the 12 Zodiac seats"
        );
    }

    #[test]
    fn test_major_arcana_3_7_12_partition() {
        assert_eq!(MAJOR_ARCANA_22.len(), 22);
        let mothers = MAJOR_ARCANA_22
            .iter()
            .filter(|a| matches!(a.class, ArcanaClass::Mother))
            .count();
        let doubles = MAJOR_ARCANA_22
            .iter()
            .filter(|a| matches!(a.class, ArcanaClass::Double))
            .count();
        let simples = MAJOR_ARCANA_22
            .iter()
            .filter(|a| matches!(a.class, ArcanaClass::Simple(_)))
            .count();
        assert_eq!((mothers, doubles, simples), (3, 7, 12));
    }

    #[test]
    fn test_council_deliberate_and_dhumavati_antibodies() {
        let report = deliberate_council(
            "Opening LMDB in readonly mode on chmod 0555 mount",
            false,
            &["rec-1".to_string()],
            false,
        );
        assert_eq!(report.steps.len(), 4);
        assert_eq!(report.grade, HostileInspectorGrade::Supported);
        assert!(!report.dhumavati_warnings.is_empty());
        assert!(report.dhumavati_warnings[0].contains("DHU-001"));
    }
}
