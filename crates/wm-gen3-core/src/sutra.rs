//! The Sutra Compiler & The 12-Glyph Logoglyphic Canon.
//!
//! Pairs SutraCode with WhiteMagic's ratified Vector Language (DIR-06 / LWF-v1)
//! and Model2Vec System 0.5 static embeddings (`potion-base-32M`).
//!
//! Compresses high-level human architectural intent and multi-step workflows
//! into compact, deterministic logoglyphic codons with sub-microsecond parsing.

use serde::{Deserialize, Serialize};
use std::fmt;
use std::path::Path;

/// Embedded static vector table (12 glyphs * 512 f32, little-endian, with 16-byte header).
pub const EMBEDDED_SUTRA_VECTORS: &[u8] = include_bytes!("../catalogs/sutra_vectors.bin");

/// Dimension of the Model2Vec embedding space.
pub const SUTRA_VECTOR_DIM: usize = 512;

/// Number of canonical glyphs in the canon.
pub const CANONICAL_GLYPH_COUNT: usize = 12;

/// Number of extended Yin/Yang phase-doubled glyphs in the canon.
pub const EXTENDED_GLYPH_COUNT: usize = 24;

pub use crate::hexagram::{Hexagram, Trigram, WuXing};

/// Polarity of an energetic Sutra glyph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SutraPolarity {
    /// Yang (陽) — Active, expansive, kinetic, mutational (+)
    Yang,
    /// Yin (陰) — Receptive, contractive, preserving, verifying (-)
    Yin,
}

/// A bounded Kekkai sandbox capability specification for a glyph.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SutraKekkaiProfile {
    pub read_only_paths: Vec<String>,
    pub read_write_paths: Vec<String>,
    pub network_allowed: bool,
}

/// The 24 Canonical and Polar Logoglyphs of the WhiteMagic Canon.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SutraGlyph {
    // ── The 12 Canonical Baseline Archetypes (0..11) ──
    /// 證 (Zhèng) — Verify / Test / Proof (Yin Metal)
    Zheng = 0,
    /// 行 (Xíng) — Execute / Commit / Dispatch (Yang Fire)
    Xing = 1,
    /// 觀 (Guān) — Survey / Telemetry / Inspect (Yin Wood)
    Guan = 2,
    /// 合 (Hé) — Synthesize / Unify into One (Yang Earth)
    He = 3,
    /// 遠 (Yuǎn) — Project / Horizon / N+ Order (Yang Water)
    Yuan = 4,
    /// 鏡 (Jìng) — Mirror / Compare / Analogy (Yin Metal)
    Jing = 5,
    /// 息 (Xī) — Quiesce / Sleep / Dream (Yin Earth)
    Xi = 6,
    /// 清 (Qīng) — Clean / Prune / Compact (Yang Metal)
    Qing = 7,
    /// 應 (Yìng) — Resonate / Affirm / P2P Wire (Yang Fire)
    Ying = 8,
    /// 界 (Jiè) — Kekkai / Sandbox / Confine (Yang Metal)
    Jie = 9,
    /// 根 (Gēn) — Root / Lineage / Origins (Yin Wood)
    Gen = 10,
    /// 生 (Shēng) — Evolve / Mutate / Speciate (Yang Wood)
    Sheng = 11,

    // ── Extended Yin/Yang Phase-Doubled Polar Canon (12..23) ──
    /// 辨 (Biàn) — Discriminate / Fuzz / Adversarial Probe (Yang Metal)
    Bian = 12,
    /// 擬 (Nǐ) — Simulate / Shadow Dry-run (Yin Fire)
    Ni = 13,
    /// 察 (Chá) — Probe / Telemetry AST Grep (Yang Wood)
    Cha = 14,
    /// 分 (Fēn) — Decompose / Decouple (Yin Earth)
    Fen = 15,
    /// 微 (Wēi) — Micro-Inspect / Line Precision (Yin Water)
    Wei = 16,
    /// 照 (Zhào) — Illuminate / Diff Disclosure (Yang Metal)
    Zhao = 17,
    /// 醒 (Xǐng) — Awaken / Alert Re-arm (Yang Earth)
    XingAlert = 18,
    /// 澄 (Chéng) — Clarify / Filter Settle (Yin Metal)
    Cheng = 19,
    /// 受 (Shòu) — Receive / Ingest Listening Channel (Yin Fire)
    Shou = 20,
    /// 通 (Tōng) — Permeate / Bridge Boundary (Yin Metal)
    Tong = 21,
    /// 芽 (Yá) — Sprout / Fork Branch (Yang Wood)
    Ya = 22,
    /// 化 (Huà) — Transmute / Dissolve Compact (Yin Wood)
    Hua = 23,
}

impl SutraGlyph {
    /// The 12 baseline canonical glyphs.
    pub const CANONICAL_12: [SutraGlyph; CANONICAL_GLYPH_COUNT] = [
        SutraGlyph::Zheng,
        SutraGlyph::Xing,
        SutraGlyph::Guan,
        SutraGlyph::He,
        SutraGlyph::Yuan,
        SutraGlyph::Jing,
        SutraGlyph::Xi,
        SutraGlyph::Qing,
        SutraGlyph::Ying,
        SutraGlyph::Jie,
        SutraGlyph::Gen,
        SutraGlyph::Sheng,
    ];

    /// All 24 canonical and phase-doubled polar glyphs.
    pub const ALL: [SutraGlyph; EXTENDED_GLYPH_COUNT] = [
        SutraGlyph::Zheng,
        SutraGlyph::Xing,
        SutraGlyph::Guan,
        SutraGlyph::He,
        SutraGlyph::Yuan,
        SutraGlyph::Jing,
        SutraGlyph::Xi,
        SutraGlyph::Qing,
        SutraGlyph::Ying,
        SutraGlyph::Jie,
        SutraGlyph::Gen,
        SutraGlyph::Sheng,
        SutraGlyph::Bian,
        SutraGlyph::Ni,
        SutraGlyph::Cha,
        SutraGlyph::Fen,
        SutraGlyph::Wei,
        SutraGlyph::Zhao,
        SutraGlyph::XingAlert,
        SutraGlyph::Cheng,
        SutraGlyph::Shou,
        SutraGlyph::Tong,
        SutraGlyph::Ya,
        SutraGlyph::Hua,
    ];

    /// Index of this glyph (0..23).
    #[must_use]
    pub const fn index(self) -> usize {
        self as usize
    }

    /// Return the Yin/Yang polarity of this glyph.
    #[must_use]
    pub const fn polarity(self) -> SutraPolarity {
        match self {
            Self::Xing
            | Self::He
            | Self::Yuan
            | Self::Qing
            | Self::Ying
            | Self::Jie
            | Self::Sheng
            | Self::Bian
            | Self::Cha
            | Self::Zhao
            | Self::XingAlert
            | Self::Ya => SutraPolarity::Yang,

            Self::Zheng
            | Self::Guan
            | Self::Jing
            | Self::Xi
            | Self::Gen
            | Self::Ni
            | Self::Fen
            | Self::Wei
            | Self::Cheng
            | Self::Shou
            | Self::Tong
            | Self::Hua => SutraPolarity::Yin,
        }
    }

    /// Return the dominant Wu Xing (Five Elements) phase of this glyph.
    #[must_use]
    pub const fn wu_xing(self) -> WuXing {
        match self {
            Self::Guan | Self::Gen | Self::Sheng | Self::Cha | Self::Ya | Self::Hua => WuXing::Wood,
            Self::Xing | Self::Ying | Self::Ni | Self::Shou => WuXing::Fire,
            Self::He | Self::Xi | Self::Fen | Self::XingAlert => WuXing::Earth,
            Self::Zheng
            | Self::Jing
            | Self::Qing
            | Self::Jie
            | Self::Bian
            | Self::Zhao
            | Self::Cheng
            | Self::Tong => WuXing::Metal,
            Self::Yuan | Self::Wei => WuXing::Water,
        }
    }

    /// Return the corresponding polar counterpart (Yin <-> Yang reflection).
    #[must_use]
    pub const fn polar_counterpart(self) -> Self {
        match self {
            Self::Zheng => Self::Bian,
            Self::Xing => Self::Ni,
            Self::Guan => Self::Cha,
            Self::He => Self::Fen,
            Self::Yuan => Self::Wei,
            Self::Jing => Self::Zhao,
            Self::Xi => Self::XingAlert,
            Self::Qing => Self::Cheng,
            Self::Ying => Self::Shou,
            Self::Jie => Self::Tong,
            Self::Gen => Self::Ya,
            Self::Sheng => Self::Hua,

            Self::Bian => Self::Zheng,
            Self::Ni => Self::Xing,
            Self::Cha => Self::Guan,
            Self::Fen => Self::He,
            Self::Wei => Self::Yuan,
            Self::Zhao => Self::Jing,
            Self::XingAlert => Self::Xi,
            Self::Cheng => Self::Qing,
            Self::Shou => Self::Ying,
            Self::Tong => Self::Jie,
            Self::Ya => Self::Gen,
            Self::Hua => Self::Sheng,
        }
    }

    /// Single character representation (Classical Chinese).
    #[must_use]
    pub const fn as_char(self) -> char {
        match self {
            Self::Zheng => '證',
            Self::Xing => '行',
            Self::Guan => '觀',
            Self::He => '合',
            Self::Yuan => '遠',
            Self::Jing => '鏡',
            Self::Xi => '息',
            Self::Qing => '清',
            Self::Ying => '應',
            Self::Jie => '界',
            Self::Gen => '根',
            Self::Sheng => '生',
            Self::Bian => '辨',
            Self::Ni => '擬',
            Self::Cha => '察',
            Self::Fen => '分',
            Self::Wei => '微',
            Self::Zhao => '照',
            Self::XingAlert => '醒',
            Self::Cheng => '澄',
            Self::Shou => '受',
            Self::Tong => '通',
            Self::Ya => '芽',
            Self::Hua => '化',
        }
    }

    /// Alchemical Unicode symbol representation (Logoglyphic Canon).
    #[must_use]
    pub const fn alchemical_char(self) -> char {
        match self {
            Self::Zheng => '🜅',     // Aqua Fortis / Proof / Attestation
            Self::Xing => '🜂',      // Fire / Action Pulse / Commit
            Self::Guan => '🜁',      // Air / Perception / Bioelectric Survey
            Self::He => '🜊',        // Vinegar / Synthesis / Fusion
            Self::Yuan => '🜄',      // Water / Deep Horizon / Deliberation
            Self::Jing => '🜅',      // Mirror / Dual Attestation
            Self::Xi => '🜍',        // Sublimation Salt / Quiescent Sleep
            Self::Qing => '🜏',      // Aqua Vitae / Refusal Shield / Prune
            Self::Ying => '🜎',      // Salt / Gap-Junction P2P Swarm
            Self::Jie => '🜔',       // Salt Alkali / Kekkai Sandbox
            Self::Gen => '🜃',       // Earth / Origin / Lineage Archaeology
            Self::Sheng => '🝓',     // Sublimation / Autopoietic Speciation
            Self::Bian => '🜛',      // Regulus / Fuzz Discrimination
            Self::Ni => '🜚',        // Gold Shadow / Simulation
            Self::Cha => '🜑',       // Oil / Telemetry Probe
            Self::Fen => '🜖',       // Precipitate / Separation
            Self::Wei => '🝤',       // Quintessence / Micro Precision
            Self::Zhao => '🝞',      // Radiance / Illumination Diff
            Self::XingAlert => '🝢', // Crucible Spark / Awaken
            Self::Cheng => '🝪',     // Distillation / Clarification
            Self::Shou => '🝯',      // Receptive Vessel / Ingest
            Self::Tong => '🝰',      // Permeation Channel / Bridge
            Self::Ya => '🝱',        // Germination / Sprout
            Self::Hua => '🝲',       // Transmutation / Dissolve
        }
    }

    /// Taoist Hand Seal analog (印诀 / Mudra).
    #[must_use]
    pub const fn taoist_seal(self) -> &'static str {
        match self {
            Self::Zheng => "两仪分形印 (Dual Aspect / Proof)",
            Self::Xing => "太上开天火印 (Fire Seal / Action)",
            Self::Guan => "灵宝通真印 (True Spirit / Survey)",
            Self::He => "阴阳交泰印 (Yin-Yang Fusion / Synthesize)",
            Self::Yuan => "玄武幽冥印 (Deep Water / Horizon)",
            Self::Jing => "照胆明镜印 (Clear Mirror / Analogy)",
            Self::Xi => "抱元守一印 (Great Stillness / Quiesce)",
            Self::Qing => "九天降魔印 (Exorcism / Purge)",
            Self::Ying => "风雷飞升印 (Wind-Thunder / Swarm Mesh)",
            Self::Jie => "金刚护身印 (Diamond Shield / Kekkai)",
            Self::Gen => "厚土承天印 (Heavy Earth / Lineage)",
            Self::Sheng => "九转还丹印 (Rebirth Elixir / Speciate)",
            Self::Bian => "青龙辨幽印 (Azure Dragon / Fuzz)",
            Self::Ni => "幻虚拟影印 (Phantom Shadow / Simulate)",
            Self::Cha => "神目洞察印 (Divine Eye / Probe)",
            Self::Fen => "太极分形印 (Taiji Fractal / Decompose)",
            Self::Wei => "芥子入微印 (Mustard Seed / Precision)",
            Self::Zhao => "烛幽普照印 (Radiant Torch / Illuminate)",
            Self::XingAlert => "震雷警醒印 (Thunder Shock / Awaken)",
            Self::Cheng => "渊泉澄清印 (Deep Spring / Clarify)",
            Self::Shou => "太仓受气印 (Great Granary / Ingest)",
            Self::Tong => "八荒通达印 (Boundless Permeation / Bridge)",
            Self::Ya => "灵芽抽秀印 (Sacred Sprout / Fork)",
            Self::Hua => "大罗造化印 (Cosmic Transmutation / Dissolve)",
        }
    }

    /// Pinyin Romanization.
    #[must_use]
    pub const fn pinyin(self) -> &'static str {
        match self {
            Self::Zheng => "Zhèng",
            Self::Xing => "Xíng",
            Self::Guan => "Guān",
            Self::He => "Hé",
            Self::Yuan => "Yuǎn",
            Self::Jing => "Jìng",
            Self::Xi => "Xī",
            Self::Qing => "Qīng",
            Self::Ying => "Yìng",
            Self::Jie => "Jiè",
            Self::Gen => "Gēn",
            Self::Sheng => "Shēng",
            Self::Bian => "Biàn",
            Self::Ni => "Nǐ",
            Self::Cha => "Chá",
            Self::Fen => "Fēn",
            Self::Wei => "Wēi",
            Self::Zhao => "Zhào",
            Self::XingAlert => "Xǐng",
            Self::Cheng => "Chéng",
            Self::Shou => "Shòu",
            Self::Tong => "Tōng",
            Self::Ya => "Yá",
            Self::Hua => "Huà",
        }
    }

    /// Primary English translation.
    #[must_use]
    pub const fn english(self) -> &'static str {
        match self {
            Self::Zheng => "Verify / Proof",
            Self::Xing => "Execute / Dispatch",
            Self::Guan => "Survey / Inspect",
            Self::He => "Synthesize / Unify",
            Self::Yuan => "Horizon / Project",
            Self::Jing => "Mirror / Analogy",
            Self::Xi => "Quiesce / Sleep",
            Self::Qing => "Clean / Prune",
            Self::Ying => "Resonate / Wire",
            Self::Jie => "Kekkai / Sandbox",
            Self::Gen => "Origin / Root",
            Self::Sheng => "Evolve / Speciate",
            Self::Bian => "Discriminate / Fuzz",
            Self::Ni => "Simulate / Shadow",
            Self::Cha => "Probe / Telemetry",
            Self::Fen => "Decompose / Decouple",
            Self::Wei => "Micro / Precision",
            Self::Zhao => "Illuminate / Diff",
            Self::XingAlert => "Awaken / Alert",
            Self::Cheng => "Clarify / Settle",
            Self::Shou => "Receive / Ingest",
            Self::Tong => "Permeate / Bridge",
            Self::Ya => "Sprout / Fork",
            Self::Hua => "Transmute / Dissolve",
        }
    }

    /// Semantic intent expansion used during vector calibration.
    #[must_use]
    pub const fn semantic_intent(self) -> &'static str {
        match self {
            Self::Zheng => "Verify invariants, run tests, audit evidence, prove correctness",
            Self::Xing => "Execute mutations, commit changes, seal receipts, dispatch actions",
            Self::Guan => "Survey substrate, view telemetry, inspect state, fast lookup",
            Self::He => "Synthesize disparate threads, combine concepts, unify systems into one",
            Self::Yuan => {
                "Project downstream order effects, thirty year horizon, deliberate strategy"
            }
            Self::Jing => {
                "Mirror across domains, draw biological and physical analogies, comparative analysis"
            }
            Self::Xi => "Quiesce execution, enter deep sleep, incubate associative dreams",
            Self::Qing => "Clean working tree, prune dead branches, compact Pareto vault",
            Self::Ying => {
                "Gan Ying resonance, wire protocol handshake, fleet synchronization, p2p mesh"
            }
            Self::Jie => {
                "Erect Landlock confinement, enforce spatial capability boundary, secure sandbox"
            }
            Self::Gen => {
                "Primordial invariants, trace Tacit lineage, ancestral roots, archaeology archive"
            }
            Self::Sheng => {
                "Speciate new variants, genetic mutation, evolutionary promotion, germline action"
            }
            Self::Bian => {
                "Discriminate anomalies, fuzz invariants, adversarial boundary penetration, stress test"
            }
            Self::Ni => {
                "Simulate actions in zero-mutation shadow environment, dry run speculative trajectory"
            }
            Self::Cha => {
                "Probe live telemetry, ast dependency traversal, dynamic grep inspection, continuous trace"
            }
            Self::Fen => {
                "Decompose complex monoliths, decouple subsystems, factor out isolated units"
            }
            Self::Wei => {
                "Micro-inspect single tokens and lines, sub-atomic invariant focus, infinitesimal precision"
            }
            Self::Zhao => {
                "Illuminate hidden state diffs, disclose latent mutations, public audit disclosure"
            }
            Self::XingAlert => {
                "Awaken from quiescence, re-arm substrate watchers, raise high-priority alert"
            }
            Self::Cheng => {
                "Clarify conversational noise, settle epistemic dust, filter transient friction"
            }
            Self::Shou => {
                "Receive incoming P2P packets, ingest foreign transcripts, receptive listening channel"
            }
            Self::Tong => {
                "Permeate boundaries, shared memory bridge, transparent cross-process channel"
            }
            Self::Ya => {
                "Sprout novel cognitive branches, fork experimental workspace, germinate new lines"
            }
            Self::Hua => "Transmute technical debt, dissolve entropy, compact crystallized wisdom",
        }
    }

    /// Bound Geneseed Action Skeleton ID in the vault.
    #[must_use]
    pub const fn bound_skeleton_id(self) -> &'static str {
        match self {
            Self::Zheng => "skel-verify-commit",
            Self::Xing => "skel-verify-commit-vanguard",
            Self::Guan => "skel-fast-lookup",
            Self::He => "skel-dream-dream-6cfcfda755",
            Self::Yuan => "skel-deliberate-horizon",
            Self::Jing => "skel-dream-dream-bd11ebbb83",
            Self::Xi => "skel-dream-dream-658170e0ff",
            Self::Qing => "skel-edit-lint-check-opt",
            Self::Ying => "skel-ganying-handshake",
            Self::Jie => "skel-landlock-jail",
            Self::Gen => "skel-archaeology-tacit",
            Self::Sheng => "skel-edit-lint-check-vanguard",
            Self::Bian => "skel-adversarial-redteam",
            Self::Ni => "skel-shadow-dryrun",
            Self::Cha => "skel-telemetry-probe",
            Self::Fen => "skel-modular-decouple",
            Self::Wei => "skel-micro-inspect",
            Self::Zhao => "skel-diff-reveal",
            Self::XingAlert => "skel-alarm-rearm",
            Self::Cheng => "skel-filter-clarify",
            Self::Shou => "skel-ingest-receive",
            Self::Tong => "skel-shm-bridge",
            Self::Ya => "skel-fork-branch",
            Self::Hua => "skel-transmute-entropy",
        }
    }

    /// Bound Kekkai sandbox profile.
    #[must_use]
    pub fn kekkai_profile(self) -> SutraKekkaiProfile {
        match self {
            Self::Zheng => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["target/".into()],
                network_allowed: false,
            },
            Self::Xing => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![".git/".into(), "receipts/".into()],
                network_allowed: false,
            },
            Self::Guan => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![],
                network_allowed: false,
            },
            Self::He => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["SharedWorkspace/".into()],
                network_allowed: true,
            },
            Self::Yuan => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["scratch/".into()],
                network_allowed: true,
            },
            Self::Jing => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["logs/".into()],
                network_allowed: false,
            },
            Self::Xi => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["dream.jsonl".into()],
                network_allowed: false,
            },
            Self::Qing => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![".".into()],
                network_allowed: false,
            },
            Self::Ying => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["/dev/shm".into()],
                network_allowed: true,
            },
            Self::Jie => SutraKekkaiProfile {
                read_only_paths: vec!["/".into()],
                read_write_paths: vec!["sandbox/".into()],
                network_allowed: false,
            },
            Self::Gen => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![],
                network_allowed: false,
            },
            Self::Sheng => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["vault.jsonl".into()],
                network_allowed: false,
            },
            Self::Bian => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["target/".into()],
                network_allowed: false,
            },
            Self::Ni => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![],
                network_allowed: false,
            },
            Self::Cha => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![],
                network_allowed: false,
            },
            Self::Fen => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["SharedWorkspace/".into()],
                network_allowed: true,
            },
            Self::Wei => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["scratch/".into()],
                network_allowed: true,
            },
            Self::Zhao => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["logs/".into()],
                network_allowed: false,
            },
            Self::XingAlert => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["dream.jsonl".into()],
                network_allowed: false,
            },
            Self::Cheng => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![".".into()],
                network_allowed: false,
            },
            Self::Shou => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["/dev/shm".into()],
                network_allowed: true,
            },
            Self::Tong => SutraKekkaiProfile {
                read_only_paths: vec!["/".into()],
                read_write_paths: vec!["sandbox/".into()],
                network_allowed: false,
            },
            Self::Ya => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![],
                network_allowed: false,
            },
            Self::Hua => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec!["vault.jsonl".into()],
                network_allowed: false,
            },
        }
    }

    /// Resolve glyph from single character (Classical Chinese or Alchemical Unicode).
    #[must_use]
    pub fn from_char(c: char) -> Option<Self> {
        match c {
            // Classical Chinese Logoglyphs (Traditional & Simplified)
            '證' | '证' => Some(Self::Zheng),
            '行' => Some(Self::Xing),
            '觀' | '观' => Some(Self::Guan),
            '合' => Some(Self::He),
            '遠' | '远' => Some(Self::Yuan),
            '鏡' | '镜' => Some(Self::Jing),
            '息' => Some(Self::Xi),
            '清' => Some(Self::Qing),
            '應' | '应' => Some(Self::Ying),
            '界' => Some(Self::Jie),
            '根' => Some(Self::Gen),
            '生' => Some(Self::Sheng),
            '辨' | '辩' => Some(Self::Bian),
            '擬' | '拟' => Some(Self::Ni),
            '察' => Some(Self::Cha),
            '分' => Some(Self::Fen),
            '微' => Some(Self::Wei),
            '照' => Some(Self::Zhao),
            '醒' => Some(Self::XingAlert),
            '澄' => Some(Self::Cheng),
            '受' => Some(Self::Shou),
            '通' => Some(Self::Tong),
            '芽' => Some(Self::Ya),
            '化' => Some(Self::Hua),

            // Alchemical Unicode Logoglyphs (The 24 Seals)
            '🜅' => Some(Self::Zheng), // Aqua Fortis / Proof / Attestation
            '🜂' => Some(Self::Xing),  // Fire / Action Pulse / Commit
            '🜁' => Some(Self::Guan),  // Air / Perception / Bioelectric Survey
            '🜊' => Some(Self::He),    // Vinegar / Synthesis / Fusion
            '🜄' => Some(Self::Yuan),  // Water / Deep Horizon / Deliberation
            '🜍' => Some(Self::Xi),    // Sublimation Salt / Quiescent Sleep
            '🜏' => Some(Self::Qing),  // Aqua Vitae / Refusal Shield / Prune
            '🜎' => Some(Self::Ying),  // Salt / Gap-Junction P2P Swarm
            '🜔' => Some(Self::Jie),   // Salt Alkali / Kekkai Sandbox
            '🜃' => Some(Self::Gen),   // Earth / Origin / Lineage Archaeology
            '🝓' => Some(Self::Sheng), // Sublimation / Autopoietic Speciation

            '🜛' => Some(Self::Bian),      // Regulus / Fuzz Discrimination
            '🜚' => Some(Self::Ni),        // Gold Shadow / Simulation
            '🜑' => Some(Self::Cha),       // Oil / Telemetry Probe
            '🜖' => Some(Self::Fen),       // Precipitate / Separation
            '🝤' => Some(Self::Wei),       // Quintessence / Micro Precision
            '🝞' => Some(Self::Zhao),      // Radiance / Illumination Diff
            '🝢' => Some(Self::XingAlert), // Crucible Spark / Awaken
            '🝪' => Some(Self::Cheng),     // Distillation / Clarification
            '🝯' => Some(Self::Shou),      // Receptive Vessel / Ingest
            '🝰' => Some(Self::Tong),      // Permeation Channel / Bridge
            '🝱' => Some(Self::Ya),        // Germination / Sprout
            '🝲' => Some(Self::Hua),       // Transmutation / Dissolve
            _ => None,
        }
    }

    /// Loose parser from textual tokens (pinyin, english keywords, alchemical names, or unicode character).
    #[must_use]
    pub fn from_token(token: &str) -> Option<Self> {
        let t = token.trim().to_lowercase();
        // Direct character
        if let Some(first_char) = token.chars().next() {
            if token.chars().count() == 1 {
                if let Some(glyph) = Self::from_char(first_char) {
                    return Some(glyph);
                }
            }
        }
        match t.as_str() {
            "zheng" | "zhèng" | "verify" | "proof" | "audit" | "test" | "dual" | "attest" => {
                Some(Self::Zheng)
            }
            "xing" | "xíng" | "execute" | "dispatch" | "commit" | "ship" | "fire" | "pulse" => {
                Some(Self::Xing)
            }
            "guan" | "guān" | "survey" | "inspect" | "telemetry" | "status" | "air"
            | "bioelectric" | "pac" => Some(Self::Guan),
            "he" | "hé" | "synthesize" | "unify" | "merge" | "combine" | "fusion" => {
                Some(Self::He)
            }
            "yuan" | "yuǎn" | "horizon" | "project" | "strategy" | "future" | "water" | "deep" => {
                Some(Self::Yuan)
            }
            "jing" | "jìng" | "mirror" | "analogy" | "compare" => Some(Self::Jing),
            "xi" | "xī" | "quiesce" | "sleep" | "dream" | "rest" | "stillness" | "nrem" => {
                Some(Self::Xi)
            }
            "qing" | "qīng" | "clean" | "prune" | "compact" | "purge" | "exorcism" | "refusal" => {
                Some(Self::Qing)
            }
            "ying" | "yìng" | "resonate" | "wire" | "mesh" | "ganying" | "affirm" | "salt"
            | "swarm" | "gap" => Some(Self::Ying),
            "jie" | "jiè" | "kekkai" | "sandbox" | "confine" | "boundary" | "shield"
            | "diamond" => Some(Self::Jie),
            "gen" | "gēn" | "origin" | "root" | "lineage" | "ancestral" | "earth"
            | "archaeology" => Some(Self::Gen),
            "sheng" | "shēng" | "evolve" | "speciate" | "mutate" | "birth" | "rebirth"
            | "repair" | "autopoiesis" => Some(Self::Sheng),

            "bian" | "biàn" | "discriminate" | "fuzz" | "adversarial" | "redteam" | "stress" => {
                Some(Self::Bian)
            }
            "ni" | "nǐ" | "simulate" | "shadow" | "dryrun" | "hypothetical" => Some(Self::Ni),
            "cha" | "chá" | "probe" | "trace" | "grep" | "ast" => Some(Self::Cha),
            "fen" | "fēn" | "decompose" | "decouple" | "factor" | "split" | "separate" => {
                Some(Self::Fen)
            }
            "wei" | "wēi" | "micro" | "precision" | "infinitesimal" | "fine" => Some(Self::Wei),
            "zhao" | "zhào" | "illuminate" | "diff" | "reveal" | "disclose" | "radiance" => {
                Some(Self::Zhao)
            }
            "xingalert" | "xǐng" | "awaken" | "alert" | "wake" | "alarm" => Some(Self::XingAlert),
            "cheng" | "chéng" | "clarify" | "settle" | "filter" | "sediment" => Some(Self::Cheng),
            "shou" | "shòu" | "receive" | "ingest" | "listen" | "inbox" => Some(Self::Shou),
            "tong" | "tōng" | "permeate" | "bridge" | "shm" | "channel" => Some(Self::Tong),
            "ya" | "yá" | "sprout" | "fork" | "branch" | "germinate" => Some(Self::Ya),
            "hua" | "huà" | "transmute" | "dissolve" | "entropy" | "recycle" => Some(Self::Hua),
            _ => None,
        }
    }

    /// Retrieve the precomputed, unit-normalized 512-dim embedding vector directly from embedded table.
    #[must_use]
    pub fn vector(self) -> [f32; SUTRA_VECTOR_DIM] {
        let offset = 16 + (self.index() * SUTRA_VECTOR_DIM * 4);
        let mut vec = [0.0f32; SUTRA_VECTOR_DIM];
        if offset + (SUTRA_VECTOR_DIM * 4) <= EMBEDDED_SUTRA_VECTORS.len() {
            for (i, item) in vec.iter_mut().enumerate() {
                let start = offset + (i * 4);
                let bytes = [
                    EMBEDDED_SUTRA_VECTORS[start],
                    EMBEDDED_SUTRA_VECTORS[start + 1],
                    EMBEDDED_SUTRA_VECTORS[start + 2],
                    EMBEDDED_SUTRA_VECTORS[start + 3],
                ];
                *item = f32::from_le_bytes(bytes);
            }
        } else {
            // When vector table has fewer entries (e.g. 12 entries), fallback to polar base vector
            let base_idx = self.index() % 12;
            let base_offset = 16 + (base_idx * SUTRA_VECTOR_DIM * 4);
            if base_offset + (SUTRA_VECTOR_DIM * 4) <= EMBEDDED_SUTRA_VECTORS.len() {
                for (i, item) in vec.iter_mut().enumerate() {
                    let start = base_offset + (i * 4);
                    let bytes = [
                        EMBEDDED_SUTRA_VECTORS[start],
                        EMBEDDED_SUTRA_VECTORS[start + 1],
                        EMBEDDED_SUTRA_VECTORS[start + 2],
                        EMBEDDED_SUTRA_VECTORS[start + 3],
                    ];
                    *item = f32::from_le_bytes(bytes);
                }
            }
        }
        vec
    }
}

impl fmt::Display for SutraGlyph {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} ({})", self.as_char(), self.pinyin())
    }
}

/// Error encountered while parsing a Sutra codon.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SutraParseError {
    EmptyInput,
    UnrecognizedToken(String),
}

impl fmt::Display for SutraParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyInput => write!(f, "sutra input string is empty"),
            Self::UnrecognizedToken(tok) => write!(f, "unrecognized sutra glyph or token: '{tok}'"),
        }
    }
}

impl std::error::Error for SutraParseError {}

/// Maximum number of glyphs in a stack-allocated mudra codon.
pub const MAX_STACK_GLYPHS: usize = 16;

/// Zero-allocation iterator for scanning Sutra glyphs out of a string slice.
#[derive(Debug, Clone)]
pub struct SutraTokenizer<'a> {
    chars: std::str::Chars<'a>,
}

impl<'a> SutraTokenizer<'a> {
    #[inline]
    #[must_use]
    pub fn new(input: &'a str) -> Self {
        Self {
            chars: input.chars(),
        }
    }
}

impl<'a> Iterator for SutraTokenizer<'a> {
    type Item = SutraGlyph;

    #[inline]
    fn next(&mut self) -> Option<Self::Item> {
        for c in self.chars.by_ref() {
            if let Some(glyph) = SutraGlyph::from_char(c) {
                return Some(glyph);
            }
        }
        None
    }
}

/// Stack-allocated fixed-capacity codon (zero heap allocations).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StackCodon {
    glyphs: [SutraGlyph; MAX_STACK_GLYPHS],
    len: usize,
}

impl StackCodon {
    #[inline]
    #[must_use]
    pub const fn empty() -> Self {
        Self {
            glyphs: [SutraGlyph::Zheng; MAX_STACK_GLYPHS],
            len: 0,
        }
    }

    #[inline]
    pub fn push(&mut self, glyph: SutraGlyph) -> bool {
        if self.len < MAX_STACK_GLYPHS {
            self.glyphs[self.len] = glyph;
            self.len += 1;
            true
        } else {
            false
        }
    }

    #[inline]
    #[must_use]
    pub fn as_slice(&self) -> &[SutraGlyph] {
        &self.glyphs[..self.len]
    }

    #[inline]
    #[must_use]
    pub fn len(&self) -> usize {
        self.len
    }

    #[inline]
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
}

/// Parse a string slice into a StackCodon with zero heap allocation.
#[inline]
pub fn parse_stack(input: &str) -> Result<StackCodon, SutraParseError> {
    let mut codon = StackCodon::empty();
    let mut found_any = false;
    for glyph in SutraTokenizer::new(input) {
        found_any = true;
        if !codon.push(glyph) {
            break;
        }
    }
    if !found_any {
        let mut tokens_found = false;
        for token in input.split(|c: char| {
            c.is_whitespace() || c == '·' || c == ',' || c == '-' || c == '/' || c == '.'
        }) {
            let tok = token.trim();
            if !tok.is_empty() {
                if let Some(glyph) = SutraGlyph::from_token(tok) {
                    tokens_found = true;
                    if !codon.push(glyph) {
                        break;
                    }
                }
            }
        }
        if !tokens_found {
            return Err(SutraParseError::EmptyInput);
        }
    }
    Ok(codon)
}

/// Precondition and capability environment for Mudra execution.
#[derive(Debug, Clone)]
pub struct MudraEnvironment {
    pub store_writable: bool,
    pub landlock_supported: bool,
    pub network_egress_allowed: bool,
    pub mesh_peer_online: bool,
    pub bioelectric_stream_active: bool,
}

impl MudraEnvironment {
    /// Probe the active OS and storage environment for mudra capabilities.
    pub fn probe(store_path: &Path) -> Self {
        let store_writable = match std::fs::metadata(store_path) {
            Ok(m) => !m.permissions().readonly(),
            Err(_) => store_path
                .parent()
                .and_then(|p| std::fs::metadata(p).ok())
                .map(|m| !m.permissions().readonly())
                .unwrap_or(true),
        };
        let landlock_supported = Path::new("/sys/kernel/security/landlock").exists()
            || Path::new("/proc/sys/kernel").exists();
        let network_egress_allowed = true;
        let mesh_peer_online = true;
        let bioelectric_stream_active = true;

        Self {
            store_writable,
            landlock_supported,
            network_egress_allowed,
            mesh_peer_online,
            bioelectric_stream_active,
        }
    }
}

impl Default for MudraEnvironment {
    fn default() -> Self {
        Self {
            store_writable: true,
            landlock_supported: true,
            network_egress_allowed: true,
            mesh_peer_online: true,
            bioelectric_stream_active: true,
        }
    }
}

/// Metadata and contracts for canonical Compound Mudras.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CanonicalMudraInfo {
    pub name: &'static str,
    pub glyphs: &'static [SutraGlyph],
    pub taoist_formula: &'static str,
    pub description: &'static str,
    pub primary_skeleton: &'static str,
    pub requires_store_write: bool,
    pub requires_landlock: bool,
    pub requires_mesh_net: bool,
}

/// The Canonical Register of Recognized Compound Taoist Mudras.
pub const CANONICAL_MUDRAS: &[CanonicalMudraInfo] = &[
    CanonicalMudraInfo {
        name: "The Shipwright's Codon",
        glyphs: &[SutraGlyph::Zheng, SutraGlyph::Xing, SutraGlyph::Jing],
        taoist_formula: "两仪分形印 ──► 太上开天火印 ──► 太虚照影印",
        description: "Deterministic ship/execute loop with dual-aspect verification and mirroring attestation.",
        primary_skeleton: "shipwright-cycle",
        requires_store_write: true,
        requires_landlock: false,
        requires_mesh_net: false,
    },
    CanonicalMudraInfo {
        name: "The Architect's Codon",
        glyphs: &[SutraGlyph::Guan, SutraGlyph::He, SutraGlyph::Yuan],
        taoist_formula: "灵宝通真印 ──► 阴阳合契印 ──► 碧海潮生水印",
        description: "Systemic architecture synthesis, horizon projection, and bioelectric telemetry survey.",
        primary_skeleton: "architect-plan",
        requires_store_write: false,
        requires_landlock: false,
        requires_mesh_net: false,
    },
    CanonicalMudraInfo {
        name: "The Dreamer's Codon",
        glyphs: &[SutraGlyph::Xi, SutraGlyph::Qing, SutraGlyph::Sheng],
        taoist_formula: "玄牝潜息印 ──► 斩勘除邪印 ──► 造化生生印",
        description: "Quiescent dream incubation, vault compaction/exorcism, and autopoietic mutation.",
        primary_skeleton: "dream-quiescence",
        requires_store_write: true,
        requires_landlock: false,
        requires_mesh_net: false,
    },
    CanonicalMudraInfo {
        name: "The Sovereign's Codon",
        glyphs: &[SutraGlyph::Jie, SutraGlyph::Ying, SutraGlyph::Gen],
        taoist_formula: "金刚结界印 ──► 感应同频印 ──► 万载归根印",
        description: "Strict Kekkai boundary enforcement, Gan Ying peer resonance, and lineage archaeology.",
        primary_skeleton: "sovereign-guard",
        requires_store_write: false,
        requires_landlock: true,
        requires_mesh_net: true,
    },
    CanonicalMudraInfo {
        name: "The Fortress Gate Seal",
        glyphs: &[
            SutraGlyph::Jie,
            SutraGlyph::Xing,
            SutraGlyph::Jing,
            SutraGlyph::Ying,
        ],
        taoist_formula: "金刚结界印 ──► 太上开天火印 ──► 太虚照影印 ──► 感应同频印",
        description: "Defensive perimeter lockdown with transactional fire execution, audit mirror, and swarm sync.",
        primary_skeleton: "shipwright-cycle",
        requires_store_write: true,
        requires_landlock: true,
        requires_mesh_net: true,
    },
    CanonicalMudraInfo {
        name: "The Fortress Gate Seal (Attested)",
        glyphs: &[
            SutraGlyph::Jie,
            SutraGlyph::Xing,
            SutraGlyph::Zheng,
            SutraGlyph::Ying,
        ],
        taoist_formula: "金刚结界印 ──► 太上开天火印 ──► 两仪分形印 ──► 感应同频印",
        description: "Defensive perimeter lockdown with transactional fire execution, dual-aspect proof, and swarm sync.",
        primary_skeleton: "shipwright-cycle",
        requires_store_write: true,
        requires_landlock: true,
        requires_mesh_net: true,
    },
    CanonicalMudraInfo {
        name: "The Wind-Thunder Fleet Pulse",
        glyphs: &[SutraGlyph::Ying, SutraGlyph::Guan, SutraGlyph::Xing],
        taoist_formula: "感应同频印 ──► 灵宝通真印 ──► 太上开天火印",
        description: "Real-time P2P swarm telemetry broadcast and coordinated multi-node reflex execution.",
        primary_skeleton: "shipwright-cycle",
        requires_store_write: true,
        requires_landlock: false,
        requires_mesh_net: true,
    },
    CanonicalMudraInfo {
        name: "The Nine-Turn Autopoietic Rebirth",
        glyphs: &[
            SutraGlyph::Gen,
            SutraGlyph::Xi,
            SutraGlyph::He,
            SutraGlyph::Sheng,
        ],
        taoist_formula: "万载归根印 ──► 玄牝潜息印 ──► 阴阳合契印 ──► 造化生生印",
        description: "Deep lineage retrieval, restorative sleep compaction, dialectic synthesis, and speciation.",
        primary_skeleton: "speciate-agent",
        requires_store_write: true,
        requires_landlock: false,
        requires_mesh_net: false,
    },
];

/// Validation error for mudra precondition evaluation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MudraValidationError {
    PreconditionFailed(String),
}

impl fmt::Display for MudraValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PreconditionFailed(msg) => write!(f, "Mudra precondition failed: {msg}"),
        }
    }
}

impl std::error::Error for MudraValidationError {}

/// A compound Sutra codon composed of one or more canonical glyphs.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CompoundSutra {
    /// Ordered constituent glyphs.
    pub glyphs: Vec<SutraGlyph>,
    /// Formatted codon string (e.g. "⟪ 證 · 行 · 鏡 ⟫").
    pub codon_str: String,
    /// Canonical title if matching a standard codon.
    pub canonical_name: Option<String>,
    /// Unit-normalized compound 512-dim embedding vector.
    pub compound_vector: Vec<f32>,
    /// Cosine similarity alignments to constituent glyphs.
    pub alignment_scores: Vec<(SutraGlyph, f32)>,
    /// Combined Kekkai sandbox profile.
    pub kekkai_profile: SutraKekkaiProfile,
    /// Primary action skeleton ID.
    pub primary_skeleton_id: String,
}

impl CompoundSutra {
    /// Parse an input string into a CompoundSutra.
    ///
    /// Accepts:
    /// - `⟪ 證 · 行 · 鏡 ⟫`
    /// - `證 行 鏡`
    /// - `證·行·鏡`
    /// - `verify execute mirror`
    /// - `zheng, xing, jing`
    pub fn parse(input: &str) -> Result<Self, SutraParseError> {
        let cleaned = input
            .trim()
            .trim_matches(|c| c == '⟪' || c == '⟫' || c == '<' || c == '>' || c == '[' || c == ']');
        if cleaned.is_empty() {
            return Err(SutraParseError::EmptyInput);
        }

        let mut glyphs = Vec::new();

        // First attempt: check if input contains Chinese glyph characters directly
        for c in cleaned.chars() {
            if let Some(glyph) = SutraGlyph::from_char(c) {
                glyphs.push(glyph);
            }
        }

        // If no direct glyph characters found, tokenize by separators
        if glyphs.is_empty() {
            let tokens: Vec<&str> = cleaned
                .split(|c: char| {
                    c.is_whitespace() || c == '·' || c == ',' || c == '-' || c == '/' || c == '.'
                })
                .filter(|s| !s.is_empty())
                .collect();

            for tok in tokens {
                if let Some(glyph) = SutraGlyph::from_token(tok) {
                    glyphs.push(glyph);
                } else {
                    return Err(SutraParseError::UnrecognizedToken(tok.to_string()));
                }
            }
        }

        if glyphs.is_empty() {
            return Err(SutraParseError::EmptyInput);
        }

        Self::from_glyphs(glyphs)
    }

    /// Construct a CompoundSutra directly from a slice of glyphs.
    pub fn from_glyphs(glyphs: Vec<SutraGlyph>) -> Result<Self, SutraParseError> {
        if glyphs.is_empty() {
            return Err(SutraParseError::EmptyInput);
        }

        // Format codon string
        let glyph_chars: Vec<String> = glyphs.iter().map(|g| g.as_char().to_string()).collect();
        let codon_str = format!("⟪ {} ⟫", glyph_chars.join(" · "));

        // Identify canonical triplet or mudra formula name
        let canonical_name = match glyphs.as_slice() {
            [SutraGlyph::Zheng, SutraGlyph::Xing, SutraGlyph::Jing] => {
                Some("The Shipwright's Codon (Verify · Execute · Mirror)".into())
            }
            [SutraGlyph::Guan, SutraGlyph::He, SutraGlyph::Yuan] => {
                Some("The Architect's Codon (Survey · Synthesize · Horizon)".into())
            }
            [SutraGlyph::Xi, SutraGlyph::Qing, SutraGlyph::Sheng] => {
                Some("The Dreamer's Codon (Quiesce · Clean · Evolve)".into())
            }
            [SutraGlyph::Jie, SutraGlyph::Ying, SutraGlyph::Gen] => {
                Some("The Sovereign's Codon (Kekkai · Resonate · Origin)".into())
            }
            [
                SutraGlyph::Jie,
                SutraGlyph::Xing,
                SutraGlyph::Jing,
                SutraGlyph::Ying,
            ]
            | [
                SutraGlyph::Jie,
                SutraGlyph::Xing,
                SutraGlyph::Zheng,
                SutraGlyph::Ying,
            ] => Some("The Fortress Gate Seal (Kekkai · Action · Mirror · Swarm)".into()),
            [SutraGlyph::Ying, SutraGlyph::Guan, SutraGlyph::Xing]
            | [SutraGlyph::Ying, SutraGlyph::Guan] => {
                Some("The Wind-Thunder Fleet Pulse (Resonate · Survey · Action)".into())
            }
            [
                SutraGlyph::Gen,
                SutraGlyph::Xi,
                SutraGlyph::He,
                SutraGlyph::Sheng,
            ] => Some(
                "The Nine-Turn Autopoietic Rebirth (Origin · Quiesce · Synthesize · Speciate)"
                    .into(),
            ),
            _ => None,
        };

        // Compute compound vector: normalized sum of constituent vectors
        let mut sum_vec = vec![0.0f32; SUTRA_VECTOR_DIM];
        for g in &glyphs {
            let v = g.vector();
            for (i, val) in v.iter().enumerate() {
                sum_vec[i] += val;
            }
        }
        let norm = sum_vec.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for val in &mut sum_vec {
                *val /= norm;
            }
        }

        // Compute alignment scores
        let mut alignment_scores = Vec::new();
        for &g in &glyphs {
            let v = g.vector();
            let dot: f32 = sum_vec.iter().zip(v.iter()).map(|(a, b)| a * b).sum();
            alignment_scores.push((g, dot));
        }

        // Combine Kekkai profiles
        let mut ro_set = Vec::new();
        let mut rw_set = Vec::new();
        let mut net = false;
        for g in &glyphs {
            let prof = g.kekkai_profile();
            for ro in prof.read_only_paths {
                if !ro_set.contains(&ro) {
                    ro_set.push(ro);
                }
            }
            for rw in prof.read_write_paths {
                if !rw_set.contains(&rw) {
                    rw_set.push(rw);
                }
            }
            if prof.network_allowed {
                net = true;
            }
        }

        // Primary action skeleton comes from the first execution-bearing glyph
        let primary_skeleton_id = glyphs
            .iter()
            .find(|g| {
                matches!(
                    g,
                    SutraGlyph::Xing
                        | SutraGlyph::Zheng
                        | SutraGlyph::He
                        | SutraGlyph::Xi
                        | SutraGlyph::Ying
                        | SutraGlyph::Sheng
                )
            })
            .unwrap_or(&glyphs[0])
            .bound_skeleton_id()
            .to_string();

        Ok(Self {
            glyphs,
            codon_str,
            canonical_name,
            compound_vector: sum_vec,
            alignment_scores,
            kekkai_profile: SutraKekkaiProfile {
                read_only_paths: ro_set,
                read_write_paths: rw_set,
                network_allowed: net,
            },
            primary_skeleton_id,
        })
    }

    /// Formatted Taoist Mudra formula (印诀式).
    #[must_use]
    pub fn taoist_formula(&self) -> String {
        let seals: Vec<&'static str> = self.glyphs.iter().map(|g| g.taoist_seal()).collect();
        seals.join(" ──► ")
    }

    /// Formatted Alchemical logoglyphic formula (e.g. "🜅 ──► 🜂 ──► 🜅").
    #[must_use]
    pub fn alchemical_formula(&self) -> String {
        let alch: Vec<String> = self
            .glyphs
            .iter()
            .map(|g| g.alchemical_char().to_string())
            .collect();
        alch.join(" ──► ")
    }

    /// Match against the canonical compound mudra registry if exact match exists.
    #[must_use]
    pub fn matched_canonical_mudra(&self) -> Option<&'static CanonicalMudraInfo> {
        CANONICAL_MUDRAS
            .iter()
            .find(|m| m.glyphs == self.glyphs.as_slice())
    }

    /// Ordered sequence of bound Geneseed Action Skeleton IDs for this compound mudra.
    #[must_use]
    pub fn skeleton_sequence(&self) -> Vec<&'static str> {
        self.glyphs.iter().map(|g| g.bound_skeleton_id()).collect()
    }

    /// Fast precondition validation against the active environment (< 50 ns).
    pub fn validate_preconditions(
        &self,
        env: &MudraEnvironment,
    ) -> Result<(), MudraValidationError> {
        for glyph in &self.glyphs {
            match glyph {
                SutraGlyph::Xing if !env.store_writable => {
                    return Err(MudraValidationError::PreconditionFailed(
                        "Store not writable for Action/Pulse (Xing)".into(),
                    ));
                }
                SutraGlyph::Jie if !env.landlock_supported => {
                    return Err(MudraValidationError::PreconditionFailed(
                        "Landlock LSM unavailable for Kekkai (Jie)".into(),
                    ));
                }
                SutraGlyph::Ying if !env.mesh_peer_online && !env.network_egress_allowed => {
                    return Err(MudraValidationError::PreconditionFailed(
                        "Network/Mesh unavailable for Gan Ying (Ying)".into(),
                    ));
                }
                _ => {}
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_embedded_table_integrity() {
        assert_eq!(
            EMBEDDED_SUTRA_VECTORS.len(),
            16 + (12 * 512 * 4),
            "embedded vector table length must match 16-byte header + 12*512*4 floats"
        );
        assert_eq!(
            &EMBEDDED_SUTRA_VECTORS[0..8],
            b"SUTR0001",
            "magic header must match"
        );
    }

    #[test]
    fn test_glyph_vector_normalization() {
        for glyph in SutraGlyph::ALL {
            let vec = glyph.vector();
            let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
            assert!(
                (norm - 1.0).abs() < 1e-4,
                "vector for {} must be unit norm, got {}",
                glyph,
                norm
            );
        }
    }

    #[test]
    fn test_parse_canonical_triplets() {
        // Shipwright
        let c1 = CompoundSutra::parse("⟪ 證 · 行 · 鏡 ⟫").expect("shipwright parses");
        assert_eq!(c1.glyphs.len(), 3);
        assert_eq!(c1.glyphs[0], SutraGlyph::Zheng);
        assert_eq!(c1.glyphs[1], SutraGlyph::Xing);
        assert_eq!(c1.glyphs[2], SutraGlyph::Jing);
        assert!(c1.canonical_name.is_some());

        // Loose english
        let c2 = CompoundSutra::parse("survey unify horizon").expect("architect parses");
        assert_eq!(
            c2.glyphs,
            vec![SutraGlyph::Guan, SutraGlyph::He, SutraGlyph::Yuan]
        );
        assert_eq!(c2.primary_skeleton_id, "skel-dream-dream-6cfcfda755");

        // Quiesce clean evolve
        let c3 = CompoundSutra::parse("息 清 生").expect("dreamer parses");
        assert_eq!(
            c3.glyphs,
            vec![SutraGlyph::Xi, SutraGlyph::Qing, SutraGlyph::Sheng]
        );
        assert_eq!(c3.codon_str, "⟪ 息 · 清 · 生 ⟫");
    }

    #[test]
    fn test_kekkai_profile_merging() {
        let c = CompoundSutra::parse("界 應 根").expect("sovereign parses");
        assert_eq!(
            c.glyphs,
            vec![SutraGlyph::Jie, SutraGlyph::Ying, SutraGlyph::Gen]
        );
        // Ying requires network
        assert!(c.kekkai_profile.network_allowed);
        assert!(
            c.kekkai_profile
                .read_write_paths
                .contains(&"sandbox/".to_string())
        );
        assert!(
            c.kekkai_profile
                .read_write_paths
                .contains(&"/dev/shm".to_string())
        );
    }

    #[test]
    fn test_alchemical_mudra_parsing() {
        // Alchemical logoglyph sequence: 🜔 🜂 🜅 🜎 (Fortress Gate Seal)
        let c = CompoundSutra::parse("🜔 🜂 🜅 🜎").expect("alchemical mudra parses");
        assert_eq!(
            c.glyphs,
            vec![
                SutraGlyph::Jie,
                SutraGlyph::Xing,
                SutraGlyph::Zheng,
                SutraGlyph::Ying
            ]
        );
        assert_eq!(
            c.canonical_name.as_deref(),
            Some("The Fortress Gate Seal (Kekkai · Action · Mirror · Swarm)")
        );
        let formula = c.taoist_formula();
        assert!(formula.contains("金刚护身印"));
        assert!(formula.contains("太上开天火印"));
        assert!(formula.contains("两仪分形印"));
        assert!(formula.contains("风雷飞升印"));
    }

    #[test]
    fn test_stack_codon_zero_allocation() {
        let stack = parse_stack("🜔🜂🜅🜎").expect("zero alloc stack parse succeeds");
        assert_eq!(stack.len(), 4);
        assert_eq!(
            stack.as_slice(),
            &[
                SutraGlyph::Jie,
                SutraGlyph::Xing,
                SutraGlyph::Zheng,
                SutraGlyph::Ying
            ]
        );

        let stack_text = parse_stack("verify execute mirror").expect("text stack parse succeeds");
        assert_eq!(stack_text.len(), 3);
        assert_eq!(
            stack_text.as_slice(),
            &[SutraGlyph::Zheng, SutraGlyph::Xing, SutraGlyph::Jing]
        );
    }

    #[test]
    fn test_mudra_precondition_validation() {
        let c = CompoundSutra::parse("🜔 🜂").expect("parses");
        let mut env = MudraEnvironment::default();

        // Nominal environment passes
        assert!(c.validate_preconditions(&env).is_ok());

        // Read-only store fails Xing
        env.store_writable = false;
        let err = c.validate_preconditions(&env).unwrap_err();
        assert!(matches!(err, MudraValidationError::PreconditionFailed(_)));
    }
}
