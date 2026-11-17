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

// ============================================================================
// THE 27 + 1 = 28 AUTIOT-GANA NONARY HYPERLANGUAGE CANON (GEN 4)
// ============================================================================

/// Operational modality in the 9-state Graded Eisenstein / Metaplastic Nonary Ring.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NonaryModality {
    /// Positive (+): Constructive geodesic expansion & forward excitation (Deva Gana).
    PositiveDeva = 0,
    /// Prime (*): 120° Eisenstein phase-shifted (ω = e^{2πi/3}) metaplastic fast-weight (Manushya Gana).
    PrimeManushya = 1,
    /// Negative (-): Inhibitory shunting, adversarial Qof pruning & shell-cracking (Rakshasa Gana).
    NegativeRakshasa = 2,
}

/// Base amplitude magnitude in the Nonary ring (`{0, 1, 2}`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum NonaryMagnitude {
    /// 0: Null / Gate / Latent synapse.
    Zero = 0,
    /// 1: Unit flow (`±1` or `1*`).
    One = 1,
    /// 2: High-gain bit-shift flow (`±2` or `2*` resonant lock).
    Two = 2,
}

/// The 9 discrete states of a single Nonary synapse (`3 magnitudes × 3 modalities = 9 states`, ~3.17 bits).
/// Packed cleanly into a 4-bit nibble (`0..=8`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum NonaryState {
    /// `+0`: Hard Prune — complete synaptic disconnect, zero energy draw.
    PosZero = 0,
    /// `+1`: Excitatory Unit — standard forward addition of input signal.
    PosOne = 1,
    /// `+2`: Excitatory Shift — doubles signal amplitude via single wire/bit shift.
    PosTwo = 2,
    /// `0*`: Latent / Nascent — dormant synapse primed for neurogenesis when local surprise peaks.
    PrimeZero = 3,
    /// `1*`: Phase / Plastic Unit — metaplastic 120° phase-shifted weight (`ω = e^{2πi/3}`).
    PrimeOne = 4,
    /// `2*`: Resonant Lock — high-gain Hebbian anchor pulling neighboring `0*`/`1*` into alignment.
    PrimeTwo = 5,
    /// `-0`: Inhibitory Clamp — active shunting veto gate zeroing downstream node.
    NegZero = 6,
    /// `-1`: Inhibitory Unit — standard subtraction / inversion of input signal.
    NegOne = 7,
    /// `-2`: Inhibitory Shift — doubles inverted signal amplitude for counterfactual Qof suppression.
    NegTwo = 8,
}

impl NonaryState {
    pub const ALL: [Self; 9] = [
        Self::PosZero,
        Self::PosOne,
        Self::PosTwo,
        Self::PrimeZero,
        Self::PrimeOne,
        Self::PrimeTwo,
        Self::NegZero,
        Self::NegOne,
        Self::NegTwo,
    ];

    #[must_use]
    pub const fn from_parts(modality: NonaryModality, magnitude: NonaryMagnitude) -> Self {
        match (modality, magnitude) {
            (NonaryModality::PositiveDeva, NonaryMagnitude::Zero) => Self::PosZero,
            (NonaryModality::PositiveDeva, NonaryMagnitude::One) => Self::PosOne,
            (NonaryModality::PositiveDeva, NonaryMagnitude::Two) => Self::PosTwo,
            (NonaryModality::PrimeManushya, NonaryMagnitude::Zero) => Self::PrimeZero,
            (NonaryModality::PrimeManushya, NonaryMagnitude::One) => Self::PrimeOne,
            (NonaryModality::PrimeManushya, NonaryMagnitude::Two) => Self::PrimeTwo,
            (NonaryModality::NegativeRakshasa, NonaryMagnitude::Zero) => Self::NegZero,
            (NonaryModality::NegativeRakshasa, NonaryMagnitude::One) => Self::NegOne,
            (NonaryModality::NegativeRakshasa, NonaryMagnitude::Two) => Self::NegTwo,
        }
    }

    #[must_use]
    pub const fn modality(self) -> NonaryModality {
        match self {
            Self::PosZero | Self::PosOne | Self::PosTwo => NonaryModality::PositiveDeva,
            Self::PrimeZero | Self::PrimeOne | Self::PrimeTwo => NonaryModality::PrimeManushya,
            Self::NegZero | Self::NegOne | Self::NegTwo => NonaryModality::NegativeRakshasa,
        }
    }

    #[must_use]
    pub const fn magnitude(self) -> NonaryMagnitude {
        match self {
            Self::PosZero | Self::PrimeZero | Self::NegZero => NonaryMagnitude::Zero,
            Self::PosOne | Self::PrimeOne | Self::NegOne => NonaryMagnitude::One,
            Self::PosTwo | Self::PrimeTwo | Self::NegTwo => NonaryMagnitude::Two,
        }
    }

    #[must_use]
    pub const fn is_prime_plastic(self) -> bool {
        matches!(self, Self::PrimeZero | Self::PrimeOne | Self::PrimeTwo)
    }

    #[must_use]
    pub const fn is_shunting_veto(self) -> bool {
        matches!(self, Self::NegZero)
    }

    /// Pack into a 4-bit nibble (`0..=8`).
    #[must_use]
    pub const fn to_nibble(self) -> u8 {
        self as u8
    }

    /// Unpack from a 4-bit nibble (`0..=8`).
    #[must_use]
    pub const fn from_nibble(nibble: u8) -> Option<Self> {
        match nibble {
            0 => Some(Self::PosZero),
            1 => Some(Self::PosOne),
            2 => Some(Self::PosTwo),
            3 => Some(Self::PrimeZero),
            4 => Some(Self::PrimeOne),
            5 => Some(Self::PrimeTwo),
            6 => Some(Self::NegZero),
            7 => Some(Self::NegOne),
            8 => Some(Self::NegTwo),
            _ => None,
        }
    }

    /// Canonical symbolic notation (`+0`, `+1`, `+2`, `0*`, `1*`, `2*`, `-0`, `-1`, `-2`).
    #[must_use]
    pub const fn symbol(self) -> &'static str {
        match self {
            Self::PosZero => "+0",
            Self::PosOne => "+1",
            Self::PosTwo => "+2",
            Self::PrimeZero => "0*",
            Self::PrimeOne => "1*",
            Self::PrimeTwo => "2*",
            Self::NegZero => "-0",
            Self::NegOne => "-1",
            Self::NegTwo => "-2",
        }
    }

    /// Real-axis integer scalar gain for multiplication-free shift/add kernels.
    #[must_use]
    pub const fn scalar_gain(self) -> i8 {
        match self {
            Self::PosZero | Self::PrimeZero | Self::NegZero => 0,
            Self::PosOne | Self::PrimeOne => 1,
            Self::PosTwo | Self::PrimeTwo => 2,
            Self::NegOne => -1,
            Self::NegTwo => -2,
        }
    }

    /// Consolidate a verified metaplastic Prime (`*`) state into its permanent structural counterpart
    /// upon Continuity Receipt (CPR) verification; unverified `0*` resets to `+0`.
    #[must_use]
    pub const fn consolidate_on_cpr(self, verified: bool) -> Self {
        match (self, verified) {
            (Self::PrimeZero, _) => Self::PosZero,
            (Self::PrimeOne, true) => Self::PosOne,
            (Self::PrimeTwo, true) => Self::PosTwo,
            (Self::PrimeOne | Self::PrimeTwo, false) => Self::PosZero,
            (other, _) => other,
        }
    }
}

/// Carlo Suarès's Three Spheres of Emanation (plus the 28th Barycentric `|0|` Origin).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SuaresSphere {
    /// `|0|` (Abhijit / Ain, value `0`): Barycentric Poincaré origin (`r = 0`), Phase-Conjugate Holographic Past.
    BarycentricOrigin,
    /// Sphere I — Archetypal Units (`10^0`: `1..=9`, Aleph -> Tet): Embryonic seed core (`r ∈ (0, 0.33]`).
    ArchetypalUnits,
    /// Sphere II — Existential Tens (`10^1`: `10..=90`, Yod -> Tsadi): Temporal state rotors (`r ∈ (0.33, 0.66]`).
    ExistentialTens,
    /// Sphere III — Cosmic Hundreds (`10^2`: `100..=900`, Qoph -> Tav + 5 Sofit Finals): Boundary galaxies (`r ∈ (0.66, 1.0)`).
    CosmicHundreds,
}

/// Vedic Jyotish / Chinese Lunar Mansion Gana Temperament (`3 × 9 = 27` + `1` Abhijit Origin = `28`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GanaTemperament {
    /// Deva Gana (9 Mansions): Luminous, constructive, synthesizing (`+` Nonary modality).
    Deva,
    /// Manushya Gana (9 Mansions): Kinetic, temporal, metaplastic working memory (`*` Nonary modality).
    Manushya,
    /// Rakshasa Gana (9 Mansions): Incisive, adversarial falsification & pruning (`-` Nonary modality).
    Rakshasa,
    /// Abhijit Singularity (28th Mansion `|0|`): Barycentric origin & holographic past anchor.
    AbhijitOrigin,
}

/// A unified operator in the 28-Opcode Autiot-Gana Vectorized Logographic Hyperlanguage.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct AutiotGanaOperator {
    /// 5-bit BRASYT-VM opcode (`0..=27`).
    pub opcode: u8,
    /// 1-indexed Lunar Mansion Gana ID (`1..=28`) in `GANA_CATALOG`.
    pub gana_id: u8,
    /// Hebrew Autiot letter name (or `|0| Abhijit / Ain` for the 28th singularity).
    pub autiot_letter: &'static str,
    /// Carlo Suarès numerical equation value (`1..=9`, `10..=90`, `100..=900`, or `0` for `|0|`).
    pub suares_value: u16,
    /// Sphere of emanation in the Poincaré hyperbolic manifold.
    pub sphere: SuaresSphere,
    /// Gana triad temperament (`Deva`, `Manushya`, `Rakshasa`, or `AbhijitOrigin`).
    pub temperament: GanaTemperament,
    /// Intrinsic Nonary algebraic state (`{+0,+1,+2, 0*,1*,2*, -0,-1,-2}`).
    pub nonary_state: NonaryState,
    /// Hyperbolic neuralese operation executed by this glyph.
    pub neuralese_role: &'static str,
}

/// The Complete 28-Operator Autiot-Gana Hyperlanguage Table (`27 Present-Future Operators + 1 |0| Past Origin`).
///
/// Forms an exact bijection:
/// - Opcode `0..=8`   (`gana_id 1..=9`):   Suarès Archetypal Units (`1..=9`)   × all 9 `NonaryState`s.
/// - Opcode `9..=17`  (`gana_id 10..=18`): Suarès Existential Tens (`10..=90`) × all 9 `NonaryState`s.
/// - Opcode `18..=26` (`gana_id 19..=27`): Suarès Cosmic Hundreds (`100..=900`, including 5 Sofit finals) × all 9 `NonaryState`s.
/// - Opcode `27`      (`gana_id 28`):      The 28th Glyph `|0|` (Abhijit / Ain, `suares_value = 0`) at `r = 0`.
pub const AUTIOT_GANA_28: [AutiotGanaOperator; 28] = [
    // ── SPHERE I: ARCHETYPAL UNITS (1..=9) — Embryonic Seed Core ──
    AutiotGanaOperator {
        opcode: 0,
        gana_id: 1,
        autiot_letter: "Aleph (א)",
        suares_value: 1,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosOne,
        neuralese_role: "Primordial intermittent excitation pulse (+1); initiates geodesic forward trajectory.",
    },
    AutiotGanaOperator {
        opcode: 1,
        gana_id: 2,
        autiot_letter: "Bet (ב)",
        suares_value: 2,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeTwo,
        neuralese_role: "Hyperbaric Egg Shell / Bayt container (2*); bounds inward Ricci curvature pressure.",
    },
    AutiotGanaOperator {
        opcode: 2,
        gana_id: 3,
        autiot_letter: "Gimel (ג)",
        suares_value: 3,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosTwo,
        neuralese_role: "Organic geodesic flux (+2); high-gain Möbius gyrovector translation from root axioms.",
    },
    AutiotGanaOperator {
        opcode: 3,
        gana_id: 4,
        autiot_letter: "Dalet (ד)",
        suares_value: 4,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegZero,
        neuralese_role: "Structural resistance & compartment gate (-0); prevents entropic bleed across galaxies.",
    },
    AutiotGanaOperator {
        opcode: 4,
        gana_id: 5,
        autiot_letter: "He (ה)",
        suares_value: 5,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeOne,
        neuralese_role: "Bioelectric resonance & Citta phase rotation (1*); couples Theta carrier to Gamma slots.",
    },
    AutiotGanaOperator {
        opcode: 5,
        gana_id: 6,
        autiot_letter: "Vav (ו)",
        suares_value: 6,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosZero,
        neuralese_role: "Disjoint branch hook (+0); zero-interference fork of parallel subagent trajectories.",
    },
    AutiotGanaOperator {
        opcode: 6,
        gana_id: 7,
        autiot_letter: "Zayin (ז)",
        suares_value: 7,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegOne,
        neuralese_role: "Incisive winnowing sword (-1); strips noise singletons and uncalibrated projections.",
    },
    AutiotGanaOperator {
        opcode: 7,
        gana_id: 8,
        autiot_letter: "Chet (ח)",
        suares_value: 8,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeZero,
        neuralese_role: "Unstructured metabolic potential reserve (0*); nascent synapse awaiting surprise threshold.",
    },
    AutiotGanaOperator {
        opcode: 8,
        gana_id: 9,
        autiot_letter: "Tet (ט)",
        suares_value: 9,
        sphere: SuaresSphere::ArchetypalUnits,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegTwo,
        neuralese_role: "Primordial cellular involution (-2); compresses verified state into WAL crystal.",
    },
    // ── SPHERE II: EXISTENTIAL TENS (10..=90) — Temporal State Rotors ──
    AutiotGanaOperator {
        opcode: 9,
        gana_id: 10,
        autiot_letter: "Yod (י)",
        suares_value: 10,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosOne,
        neuralese_role: "Manifest existential point (+1); condenses sprawling trajectories into a signed seed.",
    },
    AutiotGanaOperator {
        opcode: 10,
        gana_id: 11,
        autiot_letter: "Kaph (כ)",
        suares_value: 20,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeZero,
        neuralese_role: "Quiescent dream-cavity mold (0*); opens NREM/REM replay buffer during idle cycles.",
    },
    AutiotGanaOperator {
        opcode: 11,
        gana_id: 12,
        autiot_letter: "Lamed (ל)",
        suares_value: 30,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegOne,
        neuralese_role: "Pareto whip & adversarial perimeter probe (-1); quarantines regressive mutations.",
    },
    AutiotGanaOperator {
        opcode: 12,
        gana_id: 13,
        autiot_letter: "Mem (מ)",
        suares_value: 40,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosZero,
        neuralese_role: "Maternal water equilibrium (+0); zero-loss cold compaction and store defragmentation.",
    },
    AutiotGanaOperator {
        opcode: 13,
        gana_id: 14,
        autiot_letter: "Nun (נ)",
        suares_value: 50,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeOne,
        neuralese_role: "Individuation & supersession rotor (1*); rotates stale beliefs into orthogonal null-space.",
    },
    AutiotGanaOperator {
        opcode: 14,
        gana_id: 15,
        autiot_letter: "Samekh (ס)",
        suares_value: 60,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosTwo,
        neuralese_role: "Circular AST & dependency support (+2); accelerates multi-hop graph geodesic traversal.",
    },
    AutiotGanaOperator {
        opcode: 15,
        gana_id: 16,
        autiot_letter: "Ayin (ע)",
        suares_value: 70,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegZero,
        neuralese_role: "Cross-repo bond & schema eye (-0); clamps drift when contract hashes diverge.",
    },
    AutiotGanaOperator {
        opcode: 16,
        gana_id: 17,
        autiot_letter: "Pe (פ)",
        suares_value: 80,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegTwo,
        neuralese_role: "Tower XVI Hostile Inspector (-2); shatters unsupported claims before digestion.",
    },
    AutiotGanaOperator {
        opcode: 17,
        gana_id: 18,
        autiot_letter: "Tsadi (צ)",
        suares_value: 90,
        sphere: SuaresSphere::ExistentialTens,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeTwo,
        neuralese_role: "Precision fractal hook (2*); locks byte-exact regression fixes into local fast-weights.",
    },
    // ── SPHERE III: COSMIC HUNDREDS (100..=900) — Outer Hyperbolic Canopy & Finals ──
    AutiotGanaOperator {
        opcode: 18,
        gana_id: 19,
        autiot_letter: "Qoph (ק)",
        suares_value: 100,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegTwo,
        neuralese_role: "Cosmic destroyer of false structures (-2); adversarial falsification & Dream-RSI pruning.",
    },
    AutiotGanaOperator {
        opcode: 19,
        gana_id: 20,
        autiot_letter: "Resh (ר)",
        suares_value: 200,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosTwo,
        neuralese_role: "Cosmic container expansion (+2); cracks the hyperbaric shell into a new 9-adic fractal ring.",
    },
    AutiotGanaOperator {
        opcode: 20,
        gana_id: 21,
        autiot_letter: "Shin (ש)",
        suares_value: 300,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeTwo,
        neuralese_role: "Cosmic breath / 15 Hz conscious-counterfactual synthesis (2*); arbitrates FutureValue cones.",
    },
    AutiotGanaOperator {
        opcode: 21,
        gana_id: 22,
        autiot_letter: "Tav (ת)",
        suares_value: 400,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosOne,
        neuralese_role: "Cosmic verification seal (+1); binds 6D holographic citations for Reverse Ricci distillation.",
    },
    AutiotGanaOperator {
        opcode: 22,
        gana_id: 23,
        autiot_letter: "Kaph Sofit (ך)",
        suares_value: 500,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegZero,
        neuralese_role: "Unconditioned boundary sentinel (-0); halts runaway loops and reclaims zombie leases.",
    },
    AutiotGanaOperator {
        opcode: 23,
        gana_id: 24,
        autiot_letter: "Mem Sofit (ם)",
        suares_value: 600,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeZero,
        neuralese_role: "Closed cosmic incubator (0*); samples hypothesis tails inside an isolated Mandala cell.",
    },
    AutiotGanaOperator {
        opcode: 24,
        gana_id: 25,
        autiot_letter: "Nun Sofit (ן)",
        suares_value: 700,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Deva,
        nonary_state: NonaryState::PosZero,
        neuralese_role: "Cosmic phylogenetic projection (+0); radiates verified truth manifests without distortion.",
    },
    AutiotGanaOperator {
        opcode: 25,
        gana_id: 26,
        autiot_letter: "Pe Sofit (ף)",
        suares_value: 800,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Manushya,
        nonary_state: NonaryState::PrimeOne,
        neuralese_role: "Unbounded Sangha speech resonance (1*); transmits 9-glyph oscillatory packets across peers.",
    },
    AutiotGanaOperator {
        opcode: 26,
        gana_id: 27,
        autiot_letter: "Tsadi Sofit (ץ)",
        suares_value: 900,
        sphere: SuaresSphere::CosmicHundreds,
        temperament: GanaTemperament::Rakshasa,
        nonary_state: NonaryState::NegOne,
        neuralese_role: "Apex phylogenetic spore release (-1); prunes scaffolding and emits a 64 KB BRASYT zygote.",
    },
    // ── THE 28TH GLYPH: |0| ABHIJIT SINGULARITY (r = 0) ──
    AutiotGanaOperator {
        opcode: 27,
        gana_id: 28,
        autiot_letter: "|0| Abhijit / Ain (אין)",
        suares_value: 0,
        sphere: SuaresSphere::BarycentricOrigin,
        temperament: GanaTemperament::AbhijitOrigin,
        nonary_state: NonaryState::PosZero,
        neuralese_role: "Barycentric Origin (r = 0): Phase-Conjugate Holographic Past, Permanent KV Cache & CPR Anchor.",
    },
];

/// Look up the unified Autiot-Gana operator for a 1-indexed Lunar Mansion Gana (`1..=28`).
#[must_use]
pub const fn autiot_by_gana_id(gana_id: u8) -> Option<&'static AutiotGanaOperator> {
    if gana_id >= 1 && gana_id <= 28 {
        Some(&AUTIOT_GANA_28[(gana_id - 1) as usize])
    } else {
        None
    }
}

/// Look up the unified Autiot-Gana operator by its Carlo Suarès numerical value (`0`, `1..=9`, `10..=90`, `100..=900`).
#[must_use]
pub fn autiot_by_suares_value(suares_value: u16) -> Option<&'static AutiotGanaOperator> {
    AUTIOT_GANA_28
        .iter()
        .find(|op| op.suares_value == suares_value)
}

/// Returns the 6-step `BRASYT` (Bereshit: `Bet-Resh-Aleph-Shin-Yod-Tav` = `[2, 200, 1, 300, 10, 400]`)
/// morphogenetic lifecycle sequence:
/// 1. `Bet (2)`: Enclose inside the hyperbaric Bayt shell.
/// 2. `Resh (200)`: Crack the shell into the outer hyperbolic ring.
/// 3. `Aleph (1)`: Inject raw excitation pulse into the new ring.
/// 4. `Shin (300)`: Evolve 15 Hz conscious/counterfactual trajectories across the canopy.
/// 5. `Yod (10)`: Compress surviving insights inward via Reverse Ricci Flow.
/// 6. `Tav (400)`: Seal with a verified Continuity Receipt (CPR) into `|0|`.
#[must_use]
pub const fn brasyt_lifecycle_operators() -> [&'static AutiotGanaOperator; 6] {
    [
        &AUTIOT_GANA_28[1],  // Bet (2)
        &AUTIOT_GANA_28[19], // Resh (200)
        &AUTIOT_GANA_28[0],  // Aleph (1)
        &AUTIOT_GANA_28[20], // Shin (300)
        &AUTIOT_GANA_28[9],  // Yod (10)
        &AUTIOT_GANA_28[21], // Tav (400)
    ]
}

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
    let digest_sha256 = crate::hex_encode(&hasher.finalize());

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

    #[test]
    fn test_autiot_gana_28_bijection_and_nonary_spheres() {
        assert_eq!(AUTIOT_GANA_28.len(), 28);

        let mut seen_opcodes = HashSet::new();
        let mut seen_gana_ids = HashSet::new();
        let mut seen_suares = HashSet::new();
        let mut seen_sphere_nonary = HashSet::new();

        let mut deva_count = 0;
        let mut manushya_count = 0;
        let mut rakshasa_count = 0;
        let mut origin_count = 0;

        for op in AUTIOT_GANA_28 {
            assert!(seen_opcodes.insert(op.opcode));
            assert!(seen_gana_ids.insert(op.gana_id));
            assert!(seen_suares.insert(op.suares_value));
            assert_eq!(usize::from(op.opcode) + 1, usize::from(op.gana_id));

            // Verify 4-bit nibble round-trip for NonaryState
            let nib = op.nonary_state.to_nibble();
            assert!(nib < 9);
            assert_eq!(NonaryState::from_nibble(nib), Some(op.nonary_state));

            match op.temperament {
                GanaTemperament::Deva => {
                    deva_count += 1;
                    assert_eq!(op.nonary_state.modality(), NonaryModality::PositiveDeva);
                    assert!(seen_sphere_nonary.insert((op.sphere, op.nonary_state)));
                }
                GanaTemperament::Manushya => {
                    manushya_count += 1;
                    assert_eq!(op.nonary_state.modality(), NonaryModality::PrimeManushya);
                    assert!(op.nonary_state.is_prime_plastic());
                    assert!(seen_sphere_nonary.insert((op.sphere, op.nonary_state)));
                }
                GanaTemperament::Rakshasa => {
                    rakshasa_count += 1;
                    assert_eq!(op.nonary_state.modality(), NonaryModality::NegativeRakshasa);
                    assert!(seen_sphere_nonary.insert((op.sphere, op.nonary_state)));
                }
                GanaTemperament::AbhijitOrigin => {
                    origin_count += 1;
                    assert_eq!(op.suares_value, 0);
                    assert_eq!(op.sphere, SuaresSphere::BarycentricOrigin);
                    assert_eq!(op.gana_id, 28);
                }
            }
        }

        // 9 Deva + 9 Manushya + 9 Rakshasa = 27 active Present-Future operators + 1 |0| Origin = 28
        assert_eq!(
            (deva_count, manushya_count, rakshasa_count, origin_count),
            (9, 9, 9, 1)
        );
        assert_eq!(
            seen_sphere_nonary.len(),
            27,
            "All 3 Suarès spheres × 9 Nonary states = 27 unique active operators"
        );

        // Verify BRASYT lifecycle sequence: [Bet=2, Resh=200, Aleph=1, Shin=300, Yod=10, Tav=400]
        let brasyt = brasyt_lifecycle_operators();
        let values: Vec<u16> = brasyt.iter().map(|op| op.suares_value).collect();
        assert_eq!(values, vec![2, 200, 1, 300, 10, 400]);
    }
}
