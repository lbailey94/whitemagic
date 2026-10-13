//! The 64-Hexagram Combinatorial Matrix & Ba Gua Trigram Engine.
//!
//! Grounded in WhiteMagic's heritage (DIR-09 / Gem 19 & Gem 24), this module
//! implements the 64 King Wen Hexagrams as zero-allocation macro-action seals.
//!
//! Each hexagram maps an Inner Agent Posture (Lower Trigram) and an Outer System
//! Context (Upper Trigram) into a deterministic systemic operator with bound
//! logoglyphic sutra codons and strict Kekkai sandboxing.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::fmt;

use crate::sutra::{CompoundSutra, SutraGlyph, SutraKekkaiProfile, SutraParseError};

/// The Five Elements of Chinese Philosophy (五行).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum WuXing {
    /// Wood (木) — Generation, Sprouting, Exploration, Citrinitas
    Wood,
    /// Fire (火) — Kinetic Action, Combustion, Solar Radiance, Rubedo
    Fire,
    /// Earth (土) — Equilibrium, Foundation, Consolidation, Transmutation
    Earth,
    /// Metal (金) — Verification, Discrimination, Boundary, Albedo
    Metal,
    /// Water (水) — Deep Abyss, Deliberation, Horizon Foresight, Nigredo
    Water,
}

impl WuXing {
    #[must_use]
    pub const fn name_zh(self) -> &'static str {
        match self {
            Self::Wood => "木",
            Self::Fire => "火",
            Self::Earth => "土",
            Self::Metal => "金",
            Self::Water => "水",
        }
    }

    #[must_use]
    pub const fn name_en(self) -> &'static str {
        match self {
            Self::Wood => "Wood",
            Self::Fire => "Fire",
            Self::Earth => "Earth",
            Self::Metal => "Metal",
            Self::Water => "Water",
        }
    }
}

/// Polarity of an energetic or structural operator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Polarity {
    /// Yang (陽) — Active, expansive, kinetic, mutational (+)
    Yang,
    /// Yin (陰) — Receptive, contractive, preserving, verifying (-)
    Yin,
}

/// The Eight Fundamental Trigrams of the I Ching (八卦 / Ba Gua).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Trigram {
    /// ☰ 乾 (Qián) — Heaven / Creative Force (Lines: 111)
    Qian = 0,
    /// ☱ 兌 (Duì) — Lake / Joyous Reflection (Lines: 011)
    Dui = 1,
    /// ☲ 離 (Lí) — Fire / Clinging Clarity (Lines: 101)
    Li = 2,
    /// ☳ 震 (Zhèn) — Thunder / Arousing Shock (Lines: 100)
    Zhen = 3,
    /// ☴ 巽 (Xùn) — Wind / Gentle Penetration (Lines: 011 / 110)
    Xun = 4,
    /// ☵ 坎 (Kǎn) — Water / Abysmal Depth (Lines: 010)
    Kan = 5,
    /// ☶ 艮 (Gèn) — Mountain / Stillness Boundary (Lines: 001)
    Gen = 6,
    /// ☷ 坤 (Kūn) — Earth / Receptive Ground (Lines: 000)
    Kun = 7,
}

impl Trigram {
    /// All 8 Trigrams in canonical sequence.
    pub const ALL: [Trigram; 8] = [
        Trigram::Qian,
        Trigram::Dui,
        Trigram::Li,
        Trigram::Zhen,
        Trigram::Xun,
        Trigram::Kan,
        Trigram::Gen,
        Trigram::Kun,
    ];

    #[must_use]
    pub const fn index(self) -> usize {
        self as usize
    }

    #[must_use]
    pub const fn as_char(self) -> char {
        match self {
            Self::Qian => '☰',
            Self::Dui => '☱',
            Self::Li => '☲',
            Self::Zhen => '☳',
            Self::Xun => '☴',
            Self::Kan => '☵',
            Self::Gen => '☶',
            Self::Kun => '☷',
        }
    }

    #[must_use]
    pub const fn name_zh(self) -> &'static str {
        match self {
            Self::Qian => "乾",
            Self::Dui => "兑",
            Self::Li => "离",
            Self::Zhen => "震",
            Self::Xun => "巽",
            Self::Kan => "坎",
            Self::Gen => "艮",
            Self::Kun => "坤",
        }
    }

    #[must_use]
    pub const fn name_pinyin(self) -> &'static str {
        match self {
            Self::Qian => "Qián",
            Self::Dui => "Duì",
            Self::Li => "Lí",
            Self::Zhen => "Zhèn",
            Self::Xun => "Xùn",
            Self::Kan => "Kǎn",
            Self::Gen => "Gèn",
            Self::Kun => "Kūn",
        }
    }

    #[must_use]
    pub const fn name_en(self) -> &'static str {
        match self {
            Self::Qian => "Heaven / The Creative",
            Self::Dui => "Lake / The Joyous",
            Self::Li => "Fire / The Clinging",
            Self::Zhen => "Thunder / The Arousing",
            Self::Xun => "Wind / The Gentle",
            Self::Kan => "Water / The Abysmal",
            Self::Gen => "Mountain / Keeping Still",
            Self::Kun => "Earth / The Receptive",
        }
    }

    #[must_use]
    pub const fn wu_xing(self) -> WuXing {
        match self {
            Self::Qian | Self::Dui => WuXing::Metal,
            Self::Li => WuXing::Fire,
            Self::Zhen | Self::Xun => WuXing::Wood,
            Self::Kan => WuXing::Water,
            Self::Gen | Self::Kun => WuXing::Earth,
        }
    }

    #[must_use]
    pub const fn polarity(self) -> Polarity {
        match self {
            Self::Qian | Self::Li | Self::Zhen | Self::Kan => Polarity::Yang,
            Self::Dui | Self::Xun | Self::Gen | Self::Kun => Polarity::Yin,
        }
    }

    /// Three boolean lines from bottom to top (true = Yang, false = Yin).
    #[must_use]
    pub const fn lines(self) -> [bool; 3] {
        match self {
            Self::Qian => [true, true, true],
            Self::Dui => [true, true, false],
            Self::Li => [true, false, true],
            Self::Zhen => [true, false, false],
            Self::Xun => [false, true, true],
            Self::Kan => [false, true, false],
            Self::Gen => [false, false, true],
            Self::Kun => [false, false, false],
        }
    }

    /// 3-bit binary value (0..=7).
    #[must_use]
    pub const fn lines_u8(self) -> u8 {
        let [l1, l2, l3] = self.lines();
        (l1 as u8) | ((l2 as u8) << 1) | ((l3 as u8) << 2)
    }

    /// Decode from 3 boolean lines (bottom to top).
    #[must_use]
    pub const fn from_lines(lines: [bool; 3]) -> Self {
        match lines {
            [true, true, true] => Self::Qian,
            [true, true, false] => Self::Dui,
            [true, false, true] => Self::Li,
            [true, false, false] => Self::Zhen,
            [false, true, true] => Self::Xun,
            [false, true, false] => Self::Kan,
            [false, false, true] => Self::Gen,
            [false, false, false] => Self::Kun,
        }
    }

    /// Decode from 3-bit integer.
    #[must_use]
    pub const fn from_lines_u8(bits: u8) -> Self {
        Self::from_lines([(bits & 1) != 0, (bits & 2) != 0, (bits & 4) != 0])
    }

    /// Primary bound Sutra glyph representing this trigram.
    #[must_use]
    pub const fn bound_sutra_glyph(self) -> SutraGlyph {
        match self {
            Self::Qian => SutraGlyph::Xing,
            Self::Dui => SutraGlyph::Jing,
            Self::Li => SutraGlyph::Zheng,
            Self::Zhen => SutraGlyph::Ying,
            Self::Xun => SutraGlyph::Gen,
            Self::Kan => SutraGlyph::Yuan,
            Self::Gen => SutraGlyph::Jie,
            Self::Kun => SutraGlyph::Xi,
        }
    }
}

/// The 64 King Wen Hexagrams (六十四卦).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Hexagram {
    Qian = 1,
    Kun = 2,
    Zhun = 3,
    Meng = 4,
    Xu = 5,
    Song = 6,
    Shi = 7,
    Bi = 8,
    XiaoXu = 9,
    Lv = 10,
    Tai = 11,
    Pi = 12,
    TongRen = 13,
    DaYou = 14,
    Qian15 = 15,
    Yu = 16,
    Sui = 17,
    Gu = 18,
    Lin = 19,
    Guan = 20,
    ShiKe = 21,
    Bi22 = 22,
    Bo = 23,
    Fu = 24,
    WuWang = 25,
    DaXu = 26,
    Yi = 27,
    DaGuo = 28,
    Kan = 29,
    Li = 30,
    Xian = 31,
    Heng = 32,
    Dun = 33,
    DaZhuang = 34,
    Jin = 35,
    MingYi = 36,
    JiaRen = 37,
    Kui = 38,
    Jian = 39,
    Xie = 40,
    Sun = 41,
    Yi42 = 42,
    Guai = 43,
    Gou = 44,
    Cui = 45,
    Sheng = 46,
    Kun47 = 47,
    Jing = 48,
    Ge = 49,
    Ding = 50,
    Zhen = 51,
    Gen = 52,
    Jian53 = 53,
    GuiMei = 54,
    Feng = 55,
    Lv56 = 56,
    Xun = 57,
    Dui = 58,
    Huan = 59,
    Jie60 = 60,
    ZhongFu = 61,
    XiaoGuo = 62,
    JiJi = 63,
    WeiJi = 64,
}

/// Hexagram Metadata Definition.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct HexagramMeta {
    pub king_wen_id: u8,
    pub unicode: char,
    pub name_zh: &'static str,
    pub name_pinyin: &'static str,
    pub name_en: &'static str,
    pub upper_trigram: Trigram,
    pub lower_trigram: Trigram,
    pub macro_role: &'static str,
    pub default_codon: &'static str,
    pub dominant_element: WuXing,
}

macro_rules! hex_def {
    (
        $id:expr, $uni:expr, $zh:expr, $py:expr, $en:expr,
        $up:ident, $lo:ident, $role:expr, $codon:expr, $elem:ident
    ) => {
        HexagramMeta {
            king_wen_id: $id,
            unicode: $uni,
            name_zh: $zh,
            name_pinyin: $py,
            name_en: $en,
            upper_trigram: Trigram::$up,
            lower_trigram: Trigram::$lo,
            macro_role: $role,
            default_codon: $codon,
            dominant_element: WuXing::$elem,
        }
    };
}

/// Comprehensive Static Catalog of the 64 King Wen Hexagrams.
pub const HEXAGRAM_CATALOG: [HexagramMeta; 64] = [
    // 1..8
    hex_def!(
        1,
        '䷀',
        "乾",
        "Qián",
        "The Creative",
        Qian,
        Qian,
        "Master Sovereign Commit",
        "⟪ 行 · 證 · 應 ⟫",
        Metal
    ),
    hex_def!(
        2,
        '䷁',
        "坤",
        "Kūn",
        "The Receptive",
        Kun,
        Kun,
        "Quiescent Foundation Storage",
        "⟪ 息 · 根 · 界 ⟫",
        Earth
    ),
    hex_def!(
        3,
        '䷂',
        "屯",
        "Zhūn",
        "Difficulty at the Beginning",
        Kan,
        Zhen,
        "Embryonic Fork & Sprout",
        "⟪ 根 · 生 · 擬 ⟫",
        Water
    ),
    hex_def!(
        4,
        '䷃',
        "蒙",
        "Méng",
        "Youthful Folly",
        Gen,
        Kan,
        "Sandbox Exploratory Probing",
        "⟪ 界 · 觀 · 察 ⟫",
        Earth
    ),
    hex_def!(
        5,
        '䷄',
        "需",
        "Xū",
        "Calculated Waiting",
        Kan,
        Qian,
        "Strategic Deliberation Hold",
        "⟪ 遠 · 息 · 證 ⟫",
        Water
    ),
    hex_def!(
        6,
        '䷅',
        "讼",
        "Sòng",
        "Conflict / Arbitration",
        Qian,
        Kan,
        "Adversarial Red-Team Gate",
        "⟪ 辨 · 證 · 照 ⟫",
        Metal
    ),
    hex_def!(
        7,
        '䷆',
        "师",
        "Shī",
        "The Army",
        Kun,
        Kan,
        "Swarm Fleet Mobilization",
        "⟪ 應 · 行 · 界 ⟫",
        Earth
    ),
    hex_def!(
        8,
        '䷇',
        "比",
        "Bǐ",
        "Holding Together",
        Kan,
        Kun,
        "P2P Mesh Consensus",
        "⟪ 應 · 合 · 遠 ⟫",
        Water
    ),
    // 9..16
    hex_def!(
        9,
        '䷈',
        "小畜",
        "Xiǎo Xù",
        "Taming Power of Small",
        Xun,
        Qian,
        "Incremental Atomic Mutation",
        "⟪ 微 · 行 · 證 ⟫",
        Wood
    ),
    hex_def!(
        10,
        '䷉',
        "履",
        "Lǚ",
        "Treading with Caution",
        Qian,
        Dui,
        "Verified Invariant March",
        "⟪ 證 · 鏡 · 行 ⟫",
        Metal
    ),
    hex_def!(
        11,
        '䷊',
        "泰",
        "Tài",
        "Peace / Flourishing",
        Kun,
        Qian,
        "Systemic Equilibrium State",
        "⟪ 合 · 息 · 生 ⟫",
        Earth
    ),
    hex_def!(
        12,
        '䷋',
        "否",
        "Pǐ",
        "Standstill / Stagnation",
        Qian,
        Kun,
        "Firebreak Safety Lockdown",
        "⟪ 界 · 息 · 澄 ⟫",
        Metal
    ),
    hex_def!(
        13,
        '䷌',
        "同人",
        "Tóng Rén",
        "Fellowship with Men",
        Qian,
        Li,
        "Consilience Knowledge Fusion",
        "⟪ 合 · 照 · 應 ⟫",
        Metal
    ),
    hex_def!(
        14,
        '䷍',
        "大有",
        "Dà Yǒu",
        "Great Possession",
        Li,
        Qian,
        "Holographic Memory Store",
        "⟪ 照 · 根 · 鏡 ⟫",
        Fire
    ),
    hex_def!(
        15,
        '䷎',
        "谦",
        "Qiān",
        "Modesty",
        Kun,
        Gen,
        "Parsimonious Pruning",
        "⟪ 清 · 息 · 根 ⟫",
        Earth
    ),
    hex_def!(
        16,
        '䷏',
        "豫",
        "Yù",
        "Enthusiasm",
        Zhen,
        Kun,
        "Rapid Task Ingestion",
        "⟪ 應 · 醒 · 行 ⟫",
        Wood
    ),
    // 17..24
    hex_def!(
        17,
        '䷐',
        "随",
        "Suí",
        "Following",
        Dui,
        Zhen,
        "Adaptive Reflex Routing",
        "⟪ 鏡 · 應 · 行 ⟫",
        Metal
    ),
    hex_def!(
        18,
        '䷑',
        "蛊",
        "Gǔ",
        "Work on What Has Been Spoiled",
        Gen,
        Xun,
        "Technical Debt Exorcism",
        "⟪ 清 · 化 · 證 ⟫",
        Earth
    ),
    hex_def!(
        19,
        '䷒',
        "临",
        "Lín",
        "Approach",
        Kun,
        Dui,
        "Active Invariant Supervision",
        "⟪ 察 · 觀 · 證 ⟫",
        Earth
    ),
    hex_def!(
        20,
        '䷓',
        "观",
        "Guān",
        "Contemplation",
        Xun,
        Kun,
        "Deep Telemetry Survey",
        "⟪ 觀 · 遠 · 鏡 ⟫",
        Wood
    ),
    hex_def!(
        21,
        '䷔',
        "噬嗑",
        "Shì Kè",
        "Biting Through",
        Li,
        Zhen,
        "Decisive Bug Resolution",
        "⟪ 照 · 辨 · 行 ⟫",
        Fire
    ),
    hex_def!(
        22,
        '䷕',
        "贲",
        "Bì",
        "Grace / Form",
        Gen,
        Li,
        "Code Beautification & Format",
        "⟪ 清 · 澄 · 鏡 ⟫",
        Earth
    ),
    hex_def!(
        23,
        '䷖',
        "剥",
        "Bō",
        "Splitting Apart",
        Gen,
        Kun,
        "Deprecation & Dead Code Strip",
        "⟪ 清 · 分 · 界 ⟫",
        Earth
    ),
    hex_def!(
        24,
        '䷗',
        "复",
        "Fù",
        "Return",
        Kun,
        Zhen,
        "Substrate Reversion & Rollback",
        "⟪ 根 · 醒 · 證 ⟫",
        Earth
    ),
    // 25..32
    hex_def!(
        25,
        '䷘',
        "无妄",
        "Wú Wàng",
        "Innocence / Truth",
        Qian,
        Zhen,
        "Zero Hallucination Verification",
        "⟪ 證 · 辨 · 根 ⟫",
        Metal
    ),
    hex_def!(
        26,
        '䷙',
        "大畜",
        "Dà Xù",
        "Taming Power of Great",
        Gen,
        Qian,
        "Tacit Memory Consolidation",
        "⟪ 界 · 根 · 息 ⟫",
        Earth
    ),
    hex_def!(
        27,
        '䷚',
        "颐",
        "Yí",
        "Nourishment",
        Gen,
        Zhen,
        "Corpus Ingestion & Feeding",
        "⟪ 受 · 根 · 化 ⟫",
        Earth
    ),
    hex_def!(
        28,
        '䷛',
        "大过",
        "Dà Guò",
        "Preponderance of Great",
        Dui,
        Xun,
        "Stress & High-Load Endurance",
        "⟪ 辨 · 界 · 行 ⟫",
        Metal
    ),
    hex_def!(
        29,
        '䷜',
        "坎",
        "Kǎn",
        "The Abysmal",
        Kan,
        Kan,
        "Uncertainty Exploration",
        "⟪ 遠 · 觀 · 擬 ⟫",
        Water
    ),
    hex_def!(
        30,
        '䷝',
        "离",
        "Lí",
        "The Clinging / Radiance",
        Li,
        Li,
        "Full Telemetry Illumination",
        "⟪ 照 · 察 · 證 ⟫",
        Fire
    ),
    hex_def!(
        31,
        '䷞',
        "咸",
        "Xián",
        "Mutual Influence",
        Dui,
        Gen,
        "Gan Ying P2P Induction",
        "⟪ 應 · 鏡 · 受 ⟫",
        Metal
    ),
    hex_def!(
        32,
        '䷟',
        "恒",
        "Héng",
        "Duration / Continuity",
        Zhen,
        Xun,
        "Permanent Lineage Attestation",
        "⟪ 根 · 行 · 通 ⟫",
        Wood
    ),
    // 33..40
    hex_def!(
        33,
        '䷠',
        "遁",
        "Dùn",
        "Retreat",
        Qian,
        Gen,
        "Graceful Self-Suspension",
        "⟪ 界 · 息 · 通 ⟫",
        Metal
    ),
    hex_def!(
        34,
        '䷡',
        "大壮",
        "Dà Zhuàng",
        "Great Power",
        Zhen,
        Qian,
        "High-Throughput Burst Dispatch",
        "⟪ 行 · 醒 · 應 ⟫",
        Wood
    ),
    hex_def!(
        35,
        '䷢',
        "晋",
        "Jìn",
        "Progress",
        Li,
        Kun,
        "Rapid Sequential Advancement",
        "⟪ 照 · 行 · 生 ⟫",
        Fire
    ),
    hex_def!(
        36,
        '䷣',
        "明夷",
        "Míng Yí",
        "Darkening of Light",
        Kun,
        Li,
        "Silent Headless Operation",
        "⟪ 息 · 擬 · 界 ⟫",
        Earth
    ),
    hex_def!(
        37,
        '䷤',
        "家人",
        "Jiā Rén",
        "The Family / Workspace",
        Xun,
        Li,
        "Internal Substrate Harmony",
        "⟪ 合 · 照 · 根 ⟫",
        Wood
    ),
    hex_def!(
        38,
        '䷥',
        "睽",
        "Kuí",
        "Opposition",
        Li,
        Dui,
        "Dialectic Thesis/Antithesis",
        "⟪ 辨 · 照 · 鏡 ⟫",
        Fire
    ),
    hex_def!(
        39,
        '䷦',
        "蹇",
        "Jiǎn",
        "Obstruction",
        Kan,
        Gen,
        "Deadlock Detection & Reflect",
        "⟪ 界 · 遠 · 息 ⟫",
        Water
    ),
    hex_def!(
        40,
        '䷧',
        "解",
        "Xiè",
        "Deliverance",
        Zhen,
        Kan,
        "Knot Untying & Unblock",
        "⟪ 醒 · 分 · 行 ⟫",
        Wood
    ),
    // 41..48
    hex_def!(
        41,
        '䷨',
        "损",
        "Sǔn",
        "Decrease",
        Gen,
        Dui,
        "Lossless Memory Distillation",
        "⟪ 清 · 澄 · 息 ⟫",
        Earth
    ),
    hex_def!(
        42,
        '䷩',
        "益",
        "Yì",
        "Increase",
        Xun,
        Zhen,
        "Capability Speciation Augment",
        "⟪ 芽 · 生 · 行 ⟫",
        Wood
    ),
    hex_def!(
        43,
        '䷪',
        "夬",
        "Guài",
        "Breakthrough",
        Dui,
        Qian,
        "Decisive Branch Merge & Release",
        "⟪ 證 · 行 · 照 ⟫",
        Metal
    ),
    hex_def!(
        44,
        '䷫',
        "姤",
        "Gòu",
        "Coming to Meet",
        Qian,
        Xun,
        "First Contact Peer Handshake",
        "⟪ 應 · 受 · 通 ⟫",
        Metal
    ),
    hex_def!(
        45,
        '䷬',
        "萃",
        "Cuì",
        "Gathering Together",
        Dui,
        Kun,
        "Cluster & Galaxy Aggregation",
        "⟪ 合 · 根 · 鏡 ⟫",
        Metal
    ),
    hex_def!(
        46,
        '䷭',
        "升",
        "Shēng",
        "Pushing Upward",
        Kun,
        Xun,
        "Vertical Capability Promotion",
        "⟪ 芽 · 生 · 醒 ⟫",
        Earth
    ),
    hex_def!(
        47,
        '䷮',
        "困",
        "Kùn",
        "Oppression / Exhaustion",
        Dui,
        Kan,
        "Resource Exhaustion Recovery",
        "⟪ 息 · 界 · 澄 ⟫",
        Metal
    ),
    hex_def!(
        48,
        '䷯',
        "井",
        "Jǐng",
        "The Inexhaustible Well",
        Kan,
        Xun,
        "Deep Tacit Wisdom Retrieval",
        "⟪ 根 · 遠 · 受 ⟫",
        Water
    ),
    // 49..56
    hex_def!(
        49,
        '䷰',
        "革",
        "Gé",
        "Revolution",
        Dui,
        Li,
        "Radical Architecture Refactor",
        "⟪ 清 · 化 · 生 ⟫",
        Metal
    ),
    hex_def!(
        50,
        '䷱',
        "鼎",
        "Dǐng",
        "The Caldron",
        Li,
        Xun,
        "Alchemical Transmutation Crucible",
        "⟪ 化 · 照 · 合 ⟫",
        Fire
    ),
    hex_def!(
        51,
        '䷲',
        "震",
        "Zhèn",
        "The Arousing",
        Zhen,
        Zhen,
        "Swarm Event Wakeup Pulse",
        "⟪ 醒 · 應 · 行 ⟫",
        Wood
    ),
    hex_def!(
        52,
        '䷳',
        "艮",
        "Gèn",
        "Keeping Still",
        Gen,
        Gen,
        "Immutable Quarantine Barrier",
        "⟪ 界 · 界 · 息 ⟫",
        Earth
    ),
    hex_def!(
        53,
        '䷴',
        "渐",
        "Jiàn",
        "Gradual Progress",
        Xun,
        Gen,
        "Stepwise Verification Cycle",
        "⟪ 觀 · 證 · 生 ⟫",
        Wood
    ),
    hex_def!(
        54,
        '䷵',
        "归妹",
        "Guī Mèi",
        "The Marrying Maiden",
        Zhen,
        Dui,
        "Foreign Interface Integration",
        "⟪ 通 · 應 · 擬 ⟫",
        Wood
    ),
    hex_def!(
        55,
        '䷶',
        "丰",
        "Fēng",
        "Abundance",
        Zhen,
        Li,
        "Peak Computational Activity",
        "⟪ 照 · 行 · 應 ⟫",
        Wood
    ),
    hex_def!(
        56,
        '䷷',
        "旅",
        "Lǚ",
        "The Wanderer",
        Li,
        Gen,
        "Ephemeral Isolated Process",
        "⟪ 界 · 照 · 擬 ⟫",
        Fire
    ),
    // 57..64
    hex_def!(
        57,
        '䷸',
        "巽",
        "Xùn",
        "The Gentle",
        Xun,
        Xun,
        "Pervasive Code Inspection",
        "⟪ 察 · 微 · 觀 ⟫",
        Wood
    ),
    hex_def!(
        58,
        '䷹',
        "兑",
        "Duì",
        "The Joyous",
        Dui,
        Dui,
        "Dual Attestation Mirroring",
        "⟪ 鏡 · 鏡 · 證 ⟫",
        Metal
    ),
    hex_def!(
        59,
        '䷺',
        "涣",
        "Huàn",
        "Dispersion",
        Xun,
        Kan,
        "Friction & Entropy Dissolution",
        "⟪ 分 · 澄 · 通 ⟫",
        Wood
    ),
    hex_def!(
        60,
        '䷻',
        "节",
        "Jié",
        "Limitation",
        Kan,
        Dui,
        "Rate Limiting & Token Budget",
        "⟪ 界 · 微 · 澄 ⟫",
        Water
    ),
    hex_def!(
        61,
        '䷼',
        "中孚",
        "Zhōng Fú",
        "Inner Truth",
        Xun,
        Dui,
        "Core Invariant Verification",
        "⟪ 證 · 根 · 照 ⟫",
        Wood
    ),
    hex_def!(
        62,
        '䷽',
        "小过",
        "Xiǎo Guò",
        "Small Exceeding",
        Zhen,
        Gen,
        "Micro Fault Recovery Loop",
        "⟪ 辨 · 微 · 醒 ⟫",
        Wood
    ),
    hex_def!(
        63,
        '䷾',
        "既济",
        "Jì Jì",
        "After Completion",
        Kan,
        Li,
        "The Shipwright's Final Audit",
        "⟪ 證 · 行 · 鏡 ⟫",
        Water
    ),
    hex_def!(
        64,
        '䷿',
        "未济",
        "Wèi Jì",
        "Before Completion",
        Li,
        Kan,
        "Exploratory Horizon Probing",
        "⟪ 察 · 遠 · 擬 ⟫",
        Fire
    ),
];

impl Hexagram {
    /// Return all 64 hexagrams in King Wen sequence.
    pub const ALL: [Hexagram; 64] = [
        Hexagram::Qian,
        Hexagram::Kun,
        Hexagram::Zhun,
        Hexagram::Meng,
        Hexagram::Xu,
        Hexagram::Song,
        Hexagram::Shi,
        Hexagram::Bi,
        Hexagram::XiaoXu,
        Hexagram::Lv,
        Hexagram::Tai,
        Hexagram::Pi,
        Hexagram::TongRen,
        Hexagram::DaYou,
        Hexagram::Qian15,
        Hexagram::Yu,
        Hexagram::Sui,
        Hexagram::Gu,
        Hexagram::Lin,
        Hexagram::Guan,
        Hexagram::ShiKe,
        Hexagram::Bi22,
        Hexagram::Bo,
        Hexagram::Fu,
        Hexagram::WuWang,
        Hexagram::DaXu,
        Hexagram::Yi,
        Hexagram::DaGuo,
        Hexagram::Kan,
        Hexagram::Li,
        Hexagram::Xian,
        Hexagram::Heng,
        Hexagram::Dun,
        Hexagram::DaZhuang,
        Hexagram::Jin,
        Hexagram::MingYi,
        Hexagram::JiaRen,
        Hexagram::Kui,
        Hexagram::Jian,
        Hexagram::Xie,
        Hexagram::Sun,
        Hexagram::Yi42,
        Hexagram::Guai,
        Hexagram::Gou,
        Hexagram::Cui,
        Hexagram::Sheng,
        Hexagram::Kun47,
        Hexagram::Jing,
        Hexagram::Ge,
        Hexagram::Ding,
        Hexagram::Zhen,
        Hexagram::Gen,
        Hexagram::Jian53,
        Hexagram::GuiMei,
        Hexagram::Feng,
        Hexagram::Lv56,
        Hexagram::Xun,
        Hexagram::Dui,
        Hexagram::Huan,
        Hexagram::Jie60,
        Hexagram::ZhongFu,
        Hexagram::XiaoGuo,
        Hexagram::JiJi,
        Hexagram::WeiJi,
    ];

    #[must_use]
    pub const fn king_wen_id(self) -> u8 {
        self as u8
    }

    #[must_use]
    pub const fn meta(self) -> &'static HexagramMeta {
        &HEXAGRAM_CATALOG[(self as usize) - 1]
    }

    #[must_use]
    pub const fn as_char(self) -> char {
        self.meta().unicode
    }

    #[must_use]
    pub const fn name_zh(self) -> &'static str {
        self.meta().name_zh
    }

    #[must_use]
    pub const fn name_pinyin(self) -> &'static str {
        self.meta().name_pinyin
    }

    #[must_use]
    pub const fn name_en(self) -> &'static str {
        self.meta().name_en
    }

    #[must_use]
    pub const fn upper_trigram(self) -> Trigram {
        self.meta().upper_trigram
    }

    #[must_use]
    pub const fn lower_trigram(self) -> Trigram {
        self.meta().lower_trigram
    }

    #[must_use]
    pub const fn macro_role(self) -> &'static str {
        self.meta().macro_role
    }

    #[must_use]
    pub const fn default_codon(self) -> &'static str {
        self.meta().default_codon
    }

    #[must_use]
    pub const fn dominant_element(self) -> WuXing {
        self.meta().dominant_element
    }

    /// Six boolean lines from line 1 (bottom) to line 6 (top).
    #[must_use]
    pub const fn lines(self) -> [bool; 6] {
        let lo = self.lower_trigram().lines();
        let up = self.upper_trigram().lines();
        [lo[0], lo[1], lo[2], up[0], up[1], up[2]]
    }

    /// 6-bit integer representation (bits 0..2 = lower, bits 3..5 = upper).
    #[must_use]
    pub const fn lines_u8(self) -> u8 {
        let lo = self.lower_trigram().lines_u8();
        let up = self.upper_trigram().lines_u8();
        lo | (up << 3)
    }

    /// Construct Hexagram directly from Upper and Lower Trigram pair.
    #[must_use]
    pub fn from_trigrams(upper: Trigram, lower: Trigram) -> Self {
        Self::ALL
            .iter()
            .find(|&&h| h.upper_trigram() == upper && h.lower_trigram() == lower)
            .copied()
            .unwrap_or(Self::Qian)
    }

    /// Construct Hexagram from 6 boolean lines (bottom to top).
    #[must_use]
    pub fn from_lines(lines: [bool; 6]) -> Self {
        let lo = Trigram::from_lines([lines[0], lines[1], lines[2]]);
        let up = Trigram::from_lines([lines[3], lines[4], lines[5]]);
        Self::from_trigrams(up, lo)
    }

    /// Construct Hexagram from 6-bit integer (bits 0..2 = lower, 3..5 = upper).
    #[must_use]
    pub fn from_lines_u8(bits: u8) -> Self {
        let lo = Trigram::from_lines_u8(bits & 0b111);
        let up = Trigram::from_lines_u8((bits >> 3) & 0b111);
        Self::from_trigrams(up, lo)
    }

    /// Retrieve hexagram by its 1-indexed King Wen sequence number (1..=64).
    #[must_use]
    pub fn from_king_wen(id: u8) -> Option<Self> {
        if (1..=64).contains(&id) {
            Some(Self::ALL[(id as usize) - 1])
        } else {
            None
        }
    }

    /// Resolve hexagram from Unicode symbol (U+4DC0..=U+4DFF).
    #[must_use]
    pub fn from_char(c: char) -> Option<Self> {
        Self::ALL.iter().find(|&&h| h.as_char() == c).copied()
    }

    /// Mutate a specific changing line (1-indexed: 1..=6) to yield transformed hexagram (Bian Gua 变卦).
    #[must_use]
    pub fn mutate_line(self, line_1_to_6: usize) -> Self {
        let mut l = self.lines();
        if (1..=6).contains(&line_1_to_6) {
            l[line_1_to_6 - 1] = !l[line_1_to_6 - 1];
        }
        Self::from_lines(l)
    }

    /// Complement Hexagram (Pang Tong 旁通卦): Invert all 6 lines simultaneously.
    #[must_use]
    pub fn complement(self) -> Self {
        let mut l = self.lines();
        for item in &mut l {
            *item = !*item;
        }
        Self::from_lines(l)
    }

    /// Reverse Hexagram (Zong Gua 综卦): Invert the hexagram upside down (line 1 <-> line 6).
    #[must_use]
    pub fn reverse(self) -> Self {
        let l = self.lines();
        Self::from_lines([l[5], l[4], l[3], l[2], l[1], l[0]])
    }

    /// Nuclear Hexagram (Hu Gua 互卦):
    /// Lines 2, 3, 4 become Lower Trigram; Lines 3, 4, 5 become Upper Trigram.
    #[must_use]
    pub fn nuclear(self) -> Self {
        let l = self.lines();
        let lo = Trigram::from_lines([l[1], l[2], l[3]]);
        let up = Trigram::from_lines([l[2], l[3], l[4]]);
        Self::from_trigrams(up, lo)
    }

    /// Parse Hexagram by name, number, or character.
    #[must_use]
    pub fn parse(input: &str) -> Option<Self> {
        let t = input.trim();
        if let Ok(id) = t.parse::<u8>() {
            return Self::from_king_wen(id);
        }
        if t.chars().count() == 1 {
            if let Some(c) = t.chars().next() {
                if let Some(h) = Self::from_char(c) {
                    return Some(h);
                }
            }
        }
        let lower = t.to_lowercase().replace([' ', '-', '_'], "");
        for &h in &Self::ALL {
            let enum_name = format!("{:?}", h).to_lowercase();
            let pinyin_clean = h
                .name_pinyin()
                .to_lowercase()
                .replace([' ', '-', '_'], "")
                .replace(['ā', 'á', 'ǎ', 'à'], "a")
                .replace(['ē', 'é', 'ě', 'è'], "e")
                .replace(['ī', 'í', 'ǐ', 'ì'], "i")
                .replace(['ō', 'ó', 'ǒ', 'ò'], "o")
                .replace(['ū', 'ú', 'ǔ', 'ù', 'ü'], "u");
            let en_clean = h.name_en().to_lowercase().replace([' ', '-', '_', '/'], "");

            if h.name_zh() == t
                || enum_name == lower
                || pinyin_clean == lower
                || en_clean.contains(&lower)
            {
                return Some(h);
            }
        }
        None
    }

    /// Parse and compile this hexagram's bound default codon into an executable CompoundSutra.
    pub fn to_compound_sutra(self) -> Result<CompoundSutra, SutraParseError> {
        CompoundSutra::parse(self.default_codon())
    }

    /// Derive constitutional Kekkai sandbox profile for this hexagram.
    pub fn kekkai_profile(self) -> SutraKekkaiProfile {
        match self.to_compound_sutra() {
            Ok(cs) => cs.kekkai_profile,
            Err(_) => SutraKekkaiProfile {
                read_only_paths: vec![".".into()],
                read_write_paths: vec![],
                network_allowed: false,
            },
        }
    }
}

impl fmt::Display for Hexagram {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{} #{:02} {} ({}) — {}",
            self.as_char(),
            self.king_wen_id(),
            self.name_zh(),
            self.name_pinyin(),
            self.macro_role()
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_64_hexagrams_unique() {
        assert_eq!(Hexagram::ALL.len(), 64);
        let mut seen_ids = std::collections::HashSet::new();
        let mut seen_chars = std::collections::HashSet::new();

        for &h in &Hexagram::ALL {
            assert!(
                seen_ids.insert(h.king_wen_id()),
                "duplicate king wen id {}",
                h.king_wen_id()
            );
            assert!(
                seen_chars.insert(h.as_char()),
                "duplicate unicode char {}",
                h.as_char()
            );
        }
    }

    #[test]
    fn test_trigram_composition_bijective() {
        for &up in &Trigram::ALL {
            for &lo in &Trigram::ALL {
                let h = Hexagram::from_trigrams(up, lo);
                assert_eq!(h.upper_trigram(), up);
                assert_eq!(h.lower_trigram(), lo);
            }
        }
    }

    #[test]
    fn test_line_mutations_and_complements() {
        // Hexagram 1 (乾 Qián, all Yang) mutated at line 1 becomes Hexagram 44 (姤 Gòu)
        let qian = Hexagram::Qian;
        let gou = qian.mutate_line(1);
        assert_eq!(gou, Hexagram::Gou);

        // Qian complement is Kun (Earth, all Yin)
        assert_eq!(qian.complement(), Hexagram::Kun);

        // Hexagram 63 (既济 Jì Jì) reverse is Hexagram 64 (未济 Wèi Jì)
        assert_eq!(Hexagram::JiJi.reverse(), Hexagram::WeiJi);
    }

    #[test]
    fn test_hexagram_sutra_codon_binding() {
        // Hexagram 63 is the Shipwright's Codon
        let jiji = Hexagram::JiJi;
        assert_eq!(jiji.default_codon(), "⟪ 證 · 行 · 鏡 ⟫");
        let sutra = jiji.to_compound_sutra().expect("parses codon");
        assert_eq!(sutra.glyphs.len(), 3);
        assert_eq!(sutra.glyphs[0], SutraGlyph::Zheng);
        assert_eq!(sutra.glyphs[1], SutraGlyph::Xing);
        assert_eq!(sutra.glyphs[2], SutraGlyph::Jing);
    }

    #[test]
    fn test_parse_by_name_and_unicode() {
        assert_eq!(Hexagram::parse("乾"), Some(Hexagram::Qian));
        assert_eq!(Hexagram::parse("1"), Some(Hexagram::Qian));
        assert_eq!(Hexagram::parse("䷀"), Some(Hexagram::Qian));
        assert_eq!(Hexagram::parse("JiJi"), Some(Hexagram::JiJi));
        assert_eq!(Hexagram::parse("革"), Some(Hexagram::Ge));
        assert_eq!(Hexagram::parse("䷰"), Some(Hexagram::Ge));
    }
}
