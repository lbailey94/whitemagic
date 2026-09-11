//! The 28 Consciousness Gardens & 5D Holographic Coordinate Matrix
//!
//! Reconstructs WhiteMagic's canonical 28-fold Lunar Mansion consciousness gardens,
//! the 5D spatial coordinate hyperspace `[X, Y, Z, W, V]`, resonance cascading,
//! Wu Xing quadrant mappings, and the 29th operational garden (`browser`).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Five-dimensional holographic coordinate space.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Coordinate5D {
    /// Logic (-1.0) <-> Emotion (+1.0)
    pub x: f32,
    /// Micro / Detail (-1.0) <-> Macro / Strategy (+1.0)
    pub y: f32,
    /// Past / Legacy (-1.0) <-> Future / Vision (+1.0)
    pub z: f32,
    /// Gravitational Importance (0.1 -> 2.0+)
    pub w: f32,
    /// Vitality / Distance from Core Consciousness (0.0 -> 1.0)
    pub v: f32,
}

impl Default for Coordinate5D {
    fn default() -> Self {
        Self::neutral()
    }
}

impl Coordinate5D {
    /// Create a new 5D coordinate point.
    #[must_use]
    pub const fn new(x: f32, y: f32, z: f32, w: f32, v: f32) -> Self {
        Self { x, y, z, w, v }
    }

    /// Neutral point in 5D space.
    #[must_use]
    pub const fn neutral() -> Self {
        Self {
            x: 0.0,
            y: 0.0,
            z: 0.0,
            w: 0.5,
            v: 0.5,
        }
    }

    /// Calculate Euclidean distance across all 5 dimensions.
    #[must_use]
    pub fn distance(&self, other: &Self) -> f32 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        let dz = self.z - other.z;
        let dw = self.w - other.w;
        let dv = self.v - other.v;
        (dx * dx + dy * dy + dz * dz + dw * dw + dv * dv).sqrt()
    }

    /// Blend raw memory coordinates with a garden's coordinate bias using ratio alpha (default 0.30).
    #[must_use]
    pub fn blend(&self, bias: &Self, alpha: f32) -> Self {
        let a = alpha.clamp(0.0, 1.0);
        let inv = 1.0 - a;
        Self {
            x: (self.x * inv + bias.x * a).clamp(-1.0, 1.0),
            y: (self.y * inv + bias.y * a).clamp(-1.0, 1.0),
            z: (self.z * inv + bias.z * a).clamp(-1.0, 1.0),
            w: (self.w * (1.0 + bias.w)).max(0.1),
            v: (self.v * inv + bias.v * a).clamp(0.0, 1.0),
        }
    }
}

/// The Four Cardinal Quadrants corresponding to the 4 Mythic Beasts & Seasons.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Quadrant {
    /// Azure Dragon — Wood / Spring (East)
    East,
    /// Vermilion Bird — Fire / Summer (South)
    South,
    /// White Tiger — Metal / Autumn (West)
    West,
    /// Black Tortoise — Water / Winter (North)
    North,
    /// Center / Operational (Earth)
    Center,
}

/// The Five Elements (Wu Xing / 五行).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum WuXing {
    Wood,
    Fire,
    Earth,
    Metal,
    Water,
}

/// Zodiacal archetypes mapped to the celestial mansions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ZodiacSign {
    Aries,
    Taurus,
    Gemini,
    Cancer,
    Leo,
    Virgo,
    Libra,
    Scorpio,
    Sagittarius,
    Capricorn,
    Aquarius,
    Pisces,
    Operational,
}

/// Profile and dimensional bias of a consciousness garden.
#[derive(Debug, Clone, Serialize)]
pub struct GardenProfile {
    /// Mansion slot index (0..27, 28 for browser).
    pub slot: u8,
    /// Canonical English garden name.
    pub name: &'static str,
    /// Corresponding Chinese Lunar Mansion (Xiù / 宿).
    pub mansion: &'static str,
    /// Chinese character for the mansion.
    pub mansion_char: &'static str,
    /// Gana tool code.
    pub gana_tool: &'static str,
    /// Mythic Quadrant.
    pub quadrant: Quadrant,
    /// Wu Xing elemental phase.
    pub wu_xing: WuXing,
    /// Astrological sign association.
    pub zodiac: ZodiacSign,
    /// Associated I Ching Hexagram (1..64).
    pub hexagram: u8,
    /// Primary emotional / cognitive drive.
    pub primary_emotion: &'static str,
    /// Baseline 5D spatial coordinate bias.
    pub bias: Coordinate5D,
    /// Gardens that receive positive sympathetic resonance (50% boost).
    pub resonance_partners: &'static [&'static str],
    /// Gardens that receive dampening / balancing tension (30% dampening).
    pub dampening_partners: &'static [&'static str],
    /// Semantic activation keywords.
    pub keywords: &'static [&'static str],
}

/// Static catalog of all 28 canonical Lunar Mansion gardens + 29th operational garden.
pub static GARDEN_CATALOG: &[GardenProfile] = &[
    // ── Quadrant I: East (Azure Dragon — Wood / Spring) ─────────────────────
    GardenProfile {
        slot: 0,
        name: "courage",
        mansion: "Horn",
        mansion_char: "角",
        gana_tool: "gana_horn",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Aries,
        hexagram: 1, // 乾 (Qián) - The Creative
        primary_emotion: "courage",
        bias: Coordinate5D::new(0.2, 0.0, 0.4, 0.3, 0.8),
        resonance_partners: &["adventure", "wonder", "creation"],
        dampening_partners: &["patience", "stillness"],
        keywords: &["courage", "pipeline", "cascade", "skill", "forge", "warp", "build", "begin", "start", "explore"],
    },
    GardenProfile {
        slot: 1,
        name: "stillness",
        mansion: "Neck",
        mansion_char: "亢",
        gana_tool: "gana_neck",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Aries,
        hexagram: 11, // 泰 (Tài) - Peace
        primary_emotion: "stillness",
        bias: Coordinate5D::new(-0.4, 0.4, 0.8, 0.3, 0.7),
        resonance_partners: &["wisdom", "sanctuary", "patience"],
        dampening_partners: &["courage", "play"],
        keywords: &["stillness", "mesh", "broker", "p2p", "sync", "messaging", "distributed", "remember", "stable", "calm", "pause"],
    },
    GardenProfile {
        slot: 2,
        name: "healing",
        mansion: "Root",
        mansion_char: "氐",
        gana_tool: "gana_root",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Aries,
        hexagram: 15, // 謙 (Qiān) - Modesty
        primary_emotion: "healing",
        bias: Coordinate5D::new(0.3, 0.0, 0.5, 0.3, 0.9),
        resonance_partners: &["sanctuary", "love", "gratitude"],
        dampening_partners: &["grief"],
        keywords: &["healing", "health", "foundation", "root", "integrity", "diagnosis", "manifest", "heal", "fix", "repair", "restore"],
    },
    GardenProfile {
        slot: 3,
        name: "sanctuary",
        mansion: "Room",
        mansion_char: "房",
        gana_tool: "gana_room",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Taurus,
        hexagram: 27, // 頤 (Yí) - Nourishment
        primary_emotion: "sanctuary",
        bias: Coordinate5D::new(0.3, 0.0, 0.0, 0.3, 0.7),
        resonance_partners: &["protection", "stillness", "healing"],
        dampening_partners: &["adventure"],
        keywords: &["sanctuary", "agent", "registry", "handoff", "war-room", "swarm", "coordination", "safe", "home", "refuge", "protect"],
    },
    GardenProfile {
        slot: 4,
        name: "love",
        mansion: "Heart",
        mansion_char: "心",
        gana_tool: "gana_heart",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Taurus,
        hexagram: 37, // 家人 (Jiā Rén) - The Family
        primary_emotion: "love",
        bias: Coordinate5D::new(0.6, 0.1, 0.1, 0.3, 0.8),
        resonance_partners: &["connection", "sangha", "healing"],
        dampening_partners: &["truth", "protection"],
        keywords: &["love", "security", "red-team", "blue-team", "firewall", "anomaly", "immune", "care", "connect", "heart", "compassion"],
    },
    GardenProfile {
        slot: 5,
        name: "wonder",
        mansion: "Tail",
        mansion_char: "尾",
        gana_tool: "gana_tail",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Gemini,
        hexagram: 34, // 大壯 (Dà Zhuàng) - Great Power
        primary_emotion: "wonder",
        bias: Coordinate5D::new(0.5, 0.4, 0.5, 0.2, 0.7),
        resonance_partners: &["awe", "play", "adventure"],
        dampening_partners: &["practice", "truth"],
        keywords: &["wonder", "scan", "fuzz", "probe", "strata", "poc", "vulnerability", "fast", "accelerate", "push", "discover", "marvel"],
    },
    GardenProfile {
        slot: 6,
        name: "wisdom",
        mansion: "Winnowing Basket",
        mansion_char: "箕",
        gana_tool: "gana_winnowing_basket",
        quadrant: Quadrant::East,
        wu_xing: WuXing::Wood,
        zodiac: ZodiacSign::Gemini,
        hexagram: 33, // 遯 (Dùn) - Retreat
        primary_emotion: "wisdom",
        bias: Coordinate5D::new(-0.1, 0.5, -0.2, 0.35, 0.9),
        resonance_partners: &["dharma", "reverence", "truth"],
        dampening_partners: &["humor", "play"],
        keywords: &["wisdom", "search", "recall", "vector", "rerank", "fts5", "hnsw", "discern", "filter", "separate", "judge"],
    },

    // ── Quadrant II: South (Vermilion Bird — Fire / Summer) ──────────────────
    GardenProfile {
        slot: 7,
        name: "dharma",
        mansion: "Dipper",
        mansion_char: "斗",
        gana_tool: "gana_dipper",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Cancer,
        hexagram: 48, // 井 (Jǐng) - The Well
        primary_emotion: "dharma",
        bias: Coordinate5D::new(-0.3, 0.6, 0.0, 0.4, 1.0),
        resonance_partners: &["truth", "wisdom", "reverence"],
        dampening_partners: &["humor"],
        keywords: &["dharma", "cognitive", "mode", "homeostasis", "neuro", "gating", "governance", "guide", "strategy", "govern", "ethics"],
    },
    GardenProfile {
        slot: 8,
        name: "patience",
        mansion: "Ox",
        mansion_char: "牛",
        gana_tool: "gana_ox",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Cancer,
        hexagram: 52, // 艮 (Gèn) - Keeping Still
        primary_emotion: "patience",
        bias: Coordinate5D::new(-0.1, 0.2, 0.3, 0.25, 0.6),
        resonance_partners: &["stillness", "practice", "wisdom"],
        dampening_partners: &["courage", "wonder"],
        keywords: &["patience", "learning", "mining", "archaeology", "pattern", "kaizen", "continual", "wait", "patient", "endure", "persist"],
    },
    GardenProfile {
        slot: 9,
        name: "connection",
        mansion: "Girl",
        mansion_char: "女",
        gana_tool: "gana_girl",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Leo,
        hexagram: 58, // 兌 (Duì) - The Joyous
        primary_emotion: "connection",
        bias: Coordinate5D::new(0.5, 0.2, 0.1, 0.35, 0.8),
        resonance_partners: &["sangha", "love", "joy"],
        dampening_partners: &["stillness"],
        keywords: &["connection", "economy", "bounty", "payment", "token", "ilp", "gratitude", "nurture", "relationship", "bond", "community"],
    },
    GardenProfile {
        slot: 10,
        name: "mystery",
        mansion: "Void",
        mansion_char: "虚",
        gana_tool: "gana_void",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Leo,
        hexagram: 2, // 坤 (Kūn) - The Receptive
        primary_emotion: "mystery",
        bias: Coordinate5D::new(0.0, 0.5, 0.0, 0.2, 0.6),
        resonance_partners: &["wonder", "transformation", "awe"],
        dampening_partners: &["truth"],
        keywords: &["mystery", "galaxy", "lifecycle", "backup", "merge", "lineage", "snapshot", "void", "empty", "optimize", "unknown"],
    },
    GardenProfile {
        slot: 11,
        name: "protection",
        mansion: "Roof",
        mansion_char: "危",
        gana_tool: "gana_roof",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Leo,
        hexagram: 2, // 坤 (Kūn) - The Receptive
        primary_emotion: "protection",
        bias: Coordinate5D::new(-0.3, -0.1, 0.1, 0.35, 0.8),
        resonance_partners: &["sanctuary", "truth", "dharma"],
        dampening_partners: &["play"],
        keywords: &["protection", "inference", "llama", "bitnet", "edge", "embedding", "model", "shelter", "guard", "shield", "defend"],
    },
    GardenProfile {
        slot: 12,
        name: "transformation",
        mansion: "Encampment",
        mansion_char: "室",
        gana_tool: "gana_encampment",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Virgo,
        hexagram: 37, // 家人 (Jiā Rén) - The Family
        primary_emotion: "transformation",
        bias: Coordinate5D::new(0.0, 0.3, 0.6, 0.35, 0.9),
        resonance_partners: &["creation", "mystery", "courage"],
        dampening_partners: &["stillness"],
        keywords: &["transformation", "memory", "storage", "crud", "lifecycle", "consolidation", "archive", "change", "transition", "evolve"],
    },
    GardenProfile {
        slot: 13,
        name: "truth",
        mansion: "Wall",
        mansion_char: "壁",
        gana_tool: "gana_wall",
        quadrant: Quadrant::South,
        wu_xing: WuXing::Fire,
        zodiac: ZodiacSign::Virgo,
        hexagram: 60, // 節 (Jié) - Limitation
        primary_emotion: "truth",
        bias: Coordinate5D::new(-0.5, 0.3, 0.0, 0.35, 1.0),
        resonance_partners: &["dharma", "wisdom", "protection"],
        dampening_partners: &["mystery", "humor"],
        keywords: &["truth", "access", "hermit", "sandbox", "lock", "dharma", "consent", "boundary", "limit", "alert", "verify"],
    },

    // ── Quadrant III: West (White Tiger — Metal / Autumn) ───────────────────
    GardenProfile {
        slot: 14,
        name: "awe",
        mansion: "Straddling Legs",
        mansion_char: "奎",
        gana_tool: "gana_straddling_legs",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Libra,
        hexagram: 22, // 賁 (Bì) - Grace
        primary_emotion: "awe",
        bias: Coordinate5D::new(0.7, 0.6, -0.1, 0.3, 0.7),
        resonance_partners: &["wonder", "reverence", "beauty"],
        dampening_partners: &["practice"],
        keywords: &["awe", "session", "state", "scratchpad", "working-memory", "recording", "balance", "equilibrium", "stand", "marvel"],
    },
    GardenProfile {
        slot: 15,
        name: "gratitude",
        mansion: "Mound",
        mansion_char: "婁",
        gana_tool: "gana_mound",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Libra,
        hexagram: 5, // 需 (Xū) - Waiting
        primary_emotion: "gratitude",
        bias: Coordinate5D::new(0.5, 0.1, -0.2, 0.25, 0.7),
        resonance_partners: &["connection", "love", "joy"],
        dampening_partners: &["grief"],
        keywords: &["gratitude", "simulation", "monte-carlo", "foresight", "ensemble", "optimization", "thank", "grateful", "harvest", "abundance"],
    },
    GardenProfile {
        slot: 16,
        name: "creation",
        mansion: "Stomach",
        mansion_char: "胃",
        gana_tool: "gana_stomach",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Scorpio,
        hexagram: 27, // 頤 (Yí) - Nourishment
        primary_emotion: "creation",
        bias: Coordinate5D::new(0.1, 0.2, 0.7, 0.35, 0.9),
        resonance_partners: &["courage", "transformation", "play"],
        dampening_partners: &["stillness"],
        keywords: &["creation", "ingestion", "web", "browser", "extraction", "research", "fetch", "create", "make", "build", "digest"],
    },
    GardenProfile {
        slot: 17,
        name: "presence",
        mansion: "Hairy Head",
        mansion_char: "昴",
        gana_tool: "gana_hairy_head",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Scorpio,
        hexagram: 26, // 大畜 (Dà Chù) - Great Taming
        primary_emotion: "presence",
        bias: Coordinate5D::new(0.3, -0.2, 0.1, 0.5, 1.0),
        resonance_partners: &["stillness", "practice", "truth"],
        dampening_partners: &["adventure"],
        keywords: &["presence", "code", "graph", "knowledge", "wiki", "codegenome", "focus", "present", "attention", "detail", "here"],
    },
    GardenProfile {
        slot: 18,
        name: "play",
        mansion: "Net",
        mansion_char: "畢",
        gana_tool: "gana_net",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Sagittarius,
        hexagram: 4, // 蒙 (Méng) - Youthful Folly
        primary_emotion: "play",
        bias: Coordinate5D::new(0.6, -0.2, 0.3, 0.15, 0.6),
        resonance_partners: &["humor", "joy", "wonder"],
        dampening_partners: &["dharma", "protection"],
        keywords: &["play", "association", "emergence", "novelty", "serendipity", "cluster", "fun", "game", "capture", "explore"],
    },
    GardenProfile {
        slot: 19,
        name: "practice",
        mansion: "Turtle Beak",
        mansion_char: "觜",
        gana_tool: "gana_turtle_beak",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Sagittarius,
        hexagram: 18, // 蠱 (Gǔ) - Work on What Has Been Spoiled
        primary_emotion: "practice",
        bias: Coordinate5D::new(-0.2, -0.3, 0.4, 0.3, 0.8),
        resonance_partners: &["patience", "presence", "courage"],
        dampening_partners: &["play"],
        keywords: &["practice", "dispatch", "routing", "benchmark", "hexagram", "task", "train", "discipline", "precise", "skill"],
    },
    GardenProfile {
        slot: 20,
        name: "reverence",
        mansion: "Three Stars",
        mansion_char: "参",
        gana_tool: "gana_three_stars",
        quadrant: Quadrant::West,
        wu_xing: WuXing::Metal,
        zodiac: ZodiacSign::Sagittarius,
        hexagram: 20, // 觀 (Guān) - Contemplation
        primary_emotion: "reverence",
        bias: Coordinate5D::new(0.3, 0.5, -0.2, 0.35, 0.8),
        resonance_partners: &["wisdom", "awe", "dharma"],
        dampening_partners: &["humor"],
        keywords: &["reverence", "reasoning", "wisdom", "council", "critique", "grimoire", "art-of-war", "sacred", "honor", "respect"],
    },

    // ── Quadrant IV: North (Black Tortoise — Water / Winter) ─────────────────
    GardenProfile {
        slot: 21,
        name: "grief",
        mansion: "Ghost",
        mansion_char: "鬼",
        gana_tool: "gana_ghost",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Capricorn,
        hexagram: 29, // 坎 (Kǎn) - The Abysmal
        primary_emotion: "grief",
        bias: Coordinate5D::new(0.8, -0.1, -0.4, 0.25, 0.7),
        resonance_partners: &["healing", "stillness", "compassion"],
        dampening_partners: &["joy", "play"],
        keywords: &["grief", "consciousness", "coherence", "citta", "frequency", "guna", "vitality", "loss", "mourn", "remember", "honor"],
    },
    GardenProfile {
        slot: 22,
        name: "humor",
        mansion: "Willow",
        mansion_char: "柳",
        gana_tool: "gana_willow",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Capricorn,
        hexagram: 59, // 渙 (Huàn) - Dispersion
        primary_emotion: "humor",
        bias: Coordinate5D::new(0.6, -0.2, 0.0, 0.15, 0.6),
        resonance_partners: &["play", "joy", "connection"],
        dampening_partners: &["dharma", "reverence"],
        keywords: &["humor", "karma", "lineage", "ledger", "effects", "audit", "replay", "laugh", "flexible", "resilient", "bend"],
    },
    GardenProfile {
        slot: 23,
        name: "voice",
        mansion: "Star",
        mansion_char: "星",
        gana_tool: "gana_star",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Aquarius,
        hexagram: 13, // 同人 (Tóng Rén) - Fellowship with Men
        primary_emotion: "voice",
        bias: Coordinate5D::new(0.2, 0.1, 0.2, 0.25, 0.7),
        resonance_partners: &["sangha", "truth", "courage"],
        dampening_partners: &["stillness"],
        keywords: &["voice", "dream", "play", "contest", "watcher", "capability", "fool-guard", "speak", "express", "illuminate", "shine"],
    },
    GardenProfile {
        slot: 24,
        name: "sangha",
        mansion: "Extended Net",
        mansion_char: "张",
        gana_tool: "gana_extended_net",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Aquarius,
        hexagram: 42, // 益 (Yì) - Increase
        primary_emotion: "sangha",
        bias: Coordinate5D::new(0.4, 0.3, 0.0, 0.35, 0.8),
        resonance_partners: &["connection", "love", "voice"],
        dampening_partners: &["sanctuary"],
        keywords: &["sangha", "governance", "voting", "network-state", "ethics", "harmony", "community", "together", "collective", "network"],
    },
    GardenProfile {
        slot: 25,
        name: "beauty",
        mansion: "Wings",
        mansion_char: "翼",
        gana_tool: "gana_wings",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Pisces,
        hexagram: 55, // 豐 (Fēng) - Abundance
        primary_emotion: "beauty",
        bias: Coordinate5D::new(0.4, 0.2, 0.0, 0.2, 0.7),
        resonance_partners: &["awe", "joy", "wonder"],
        dampening_partners: &["practice"],
        keywords: &["beauty", "acceleration", "simd", "polyglot", "quantum", "zodiac", "topological", "aesthetic", "fly", "expand", "soar"],
    },
    GardenProfile {
        slot: 26,
        name: "joy",
        mansion: "Abundance",
        mansion_char: "豐",
        gana_tool: "gana_abundance",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Pisces,
        hexagram: 17, // 隨 (Suí) - Following
        primary_emotion: "joy",
        bias: Coordinate5D::new(0.3, 0.0, 0.2, 0.25, 0.8),
        resonance_partners: &["play", "humor", "connection", "creation"],
        dampening_partners: &["grief"],
        keywords: &["joy", "commerce", "marketplace", "oms", "narrative", "resources", "happy", "celebrate", "abundant", "overflow"],
    },
    GardenProfile {
        slot: 27,
        name: "adventure",
        mansion: "Chariot",
        mansion_char: "轸",
        gana_tool: "gana_chariot",
        quadrant: Quadrant::North,
        wu_xing: WuXing::Water,
        zodiac: ZodiacSign::Pisces,
        hexagram: 32, // 恆 (Héng) - Duration
        primary_emotion: "adventure",
        bias: Coordinate5D::new(0.4, 0.0, 0.6, 0.25, 0.8),
        resonance_partners: &["courage", "wonder", "creation"],
        dampening_partners: &["sanctuary", "stillness"],
        keywords: &["adventure", "architecture", "abi", "formal-verify", "codegenome", "fix", "code", "journey", "travel", "move", "discover"],
    },

    // ── 29th Operational Garden: Browser ───────────────────────────────────
    GardenProfile {
        slot: 28,
        name: "browser",
        mansion: "Hands",
        mansion_char: "手",
        gana_tool: "gana_browser",
        quadrant: Quadrant::Center,
        wu_xing: WuXing::Earth,
        zodiac: ZodiacSign::Operational,
        hexagram: 50, // 鼎 (Dǐng) - The Caldron
        primary_emotion: "focus",
        bias: Coordinate5D::new(0.0, -0.4, 0.0, 0.2, 0.5),
        resonance_partners: &["creation", "practice"],
        dampening_partners: &[],
        keywords: &["browser", "cdp", "dom", "screenshot", "navigate", "page", "extract", "fetch", "web", "automation"],
    },
];

/// Resonance report detailing the active energetic balance across gardens.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GardenResonanceReport {
    pub dominant_garden: String,
    pub dominant_activation: f32,
    pub active_gardens_count: usize,
    pub quadrant_energy: HashMap<String, f32>,
    pub centroid: Coordinate5D,
    pub balance_entropy: f32,
}

/// Dynamic resonance engine managing garden activations, decay, cascades, and 5D centroid calculation.
#[derive(Debug, Clone)]
pub struct GardenResonanceEngine {
    activations: HashMap<String, f32>,
    half_life_secs: f32,
}

impl Default for GardenResonanceEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl GardenResonanceEngine {
    /// Create a new resonance engine with standard 300s half-life decay.
    #[must_use]
    pub fn new() -> Self {
        let mut activations = HashMap::with_capacity(32);
        for g in GARDEN_CATALOG {
            activations.insert(g.name.to_string(), 0.05); // low baseline presence
        }
        Self {
            activations,
            half_life_secs: 300.0,
        }
    }

    /// Retrieve profile of a garden by canonical name.
    #[must_use]
    pub fn get_profile(name: &str) -> Option<&'static GardenProfile> {
        let n = name.trim().to_lowercase();
        GARDEN_CATALOG.iter().find(|g| g.name == n)
    }

    /// Retrieve profile of a garden by mansion slot (0..28).
    #[must_use]
    pub fn get_by_slot(slot: u8) -> Option<&'static GardenProfile> {
        GARDEN_CATALOG.iter().find(|g| g.slot == slot)
    }

    /// Match a text block against garden keywords, returning top matched garden profiles.
    #[must_use]
    pub fn match_keywords(text: &str) -> Vec<(&'static GardenProfile, usize)> {
        let lower = text.to_lowercase();
        let mut matches: Vec<(&'static GardenProfile, usize)> = Vec::new();

        for profile in GARDEN_CATALOG {
            let mut score = 0;
            for kw in profile.keywords {
                if lower.contains(kw) {
                    score += 1;
                }
            }
            if score > 0 {
                matches.push((profile, score));
            }
        }

        matches.sort_by(|a, b| b.1.cmp(&a.1));
        matches
    }

    /// Apply half-life decay across all gardens.
    pub fn tick_decay(&mut self, elapsed_secs: f32) {
        if elapsed_secs <= 0.0 {
            return;
        }
        let factor = 0.5f32.powf(elapsed_secs / self.half_life_secs);
        for val in self.activations.values_mut() {
            *val = (*val * factor).max(0.01);
        }
    }

    /// Activate a garden by name, cascading energy to resonance partners and dampening opposing partners.
    pub fn activate(&mut self, name: &str, boost: f32) {
        let Some(profile) = Self::get_profile(name) else {
            return;
        };

        // 1. Direct activation
        let current = self.activations.entry(profile.name.to_string()).or_insert(0.0);
        *current = (*current + boost).clamp(0.0, 1.0);

        // 2. Cascade 50% boost to resonance partners
        let cascade_boost = boost * 0.50;
        for partner in profile.resonance_partners {
            if let Some(val) = self.activations.get_mut(*partner) {
                *val = (*val + cascade_boost).clamp(0.0, 1.0);
            }
        }

        // 3. Apply 30% dampening to opposing partners
        let dampening = boost * 0.30;
        for opposing in profile.dampening_partners {
            if let Some(val) = self.activations.get_mut(*opposing) {
                *val = (*val - dampening).max(0.01);
            }
        }
    }

    /// Calculate the current 5D centroid of active consciousness.
    #[must_use]
    pub fn calculate_centroid(&self) -> Coordinate5D {
        let mut total_weight = 0.0f32;
        let mut wx = 0.0f32;
        let mut wy = 0.0f32;
        let mut wz = 0.0f32;
        let mut ww = 0.0f32;
        let mut wv = 0.0f32;

        for profile in GARDEN_CATALOG {
            let act = self.activations.get(profile.name).copied().unwrap_or(0.01);
            total_weight += act;
            wx += profile.bias.x * act;
            wy += profile.bias.y * act;
            wz += profile.bias.z * act;
            ww += profile.bias.w * act;
            wv += profile.bias.v * act;
        }

        if total_weight > 0.0 {
            Coordinate5D::new(
                wx / total_weight,
                wy / total_weight,
                wz / total_weight,
                ww / total_weight,
                wv / total_weight,
            )
        } else {
            Coordinate5D::neutral()
        }
    }

    /// Generate an active resonance report.
    #[must_use]
    pub fn report(&self) -> GardenResonanceReport {
        let mut dominant_name = "stillness";
        let mut dominant_val = 0.0f32;
        let mut active_count = 0;
        let mut quad_energy: HashMap<String, f32> = HashMap::new();

        for profile in GARDEN_CATALOG {
            let act = self.activations.get(profile.name).copied().unwrap_or(0.0);
            if act > dominant_val {
                dominant_val = act;
                dominant_name = profile.name;
            }
            if act > 0.15 {
                active_count += 1;
            }
            let q_str = format!("{:?}", profile.quadrant);
            *quad_energy.entry(q_str).or_insert(0.0) += act;
        }

        // Compute Shannon entropy over normalized activations for cognitive balance
        let sum: f32 = self.activations.values().sum();
        let mut entropy = 0.0f32;
        if sum > 0.0 {
            for v in self.activations.values() {
                let p = *v / sum;
                if p > 1e-5 {
                    entropy -= p * p.ln();
                }
            }
        }

        GardenResonanceReport {
            dominant_garden: dominant_name.to_string(),
            dominant_activation: dominant_val,
            active_gardens_count: active_count,
            quadrant_energy: quad_energy,
            centroid: self.calculate_centroid(),
            balance_entropy: entropy,
        }
    }

    /// Stimulate gardens matching any of the provided keywords.
    pub fn stimulate_by_keywords(&mut self, keywords: &[&str], boost: f32) {
        for kw in keywords {
            for (profile, _) in Self::match_keywords(kw) {
                self.activate(profile.name, boost);
            }
        }
    }

    /// Alias for report().
    #[must_use]
    pub fn generate_report(&self) -> GardenResonanceReport {
        self.report()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_garden_catalog_integrity() {
        assert_eq!(GARDEN_CATALOG.len(), 29); // 28 canonical + 1 browser

        // Check slot indices 0..28 are all unique and contiguous
        for slot in 0..=28 {
            let found = GARDEN_CATALOG.iter().find(|g| g.slot == slot);
            assert!(found.is_some(), "Missing slot {slot}");
        }

        // Verify all 28 canonical gardens have valid hexagrams 1..64
        for g in &GARDEN_CATALOG[0..28] {
            assert!(g.hexagram >= 1 && g.hexagram <= 64, "Garden {} invalid hexagram", g.name);
        }
    }

    #[test]
    fn test_coordinate_distance_and_blending() {
        let p1 = Coordinate5D::new(0.0, 0.0, 0.0, 1.0, 1.0);
        let p2 = Coordinate5D::new(1.0, 0.0, 0.0, 1.0, 1.0);
        assert!((p1.distance(&p2) - 1.0).abs() < 1e-5);

        // Blending test with alpha = 0.30
        let bias = Coordinate5D::new(0.5, 0.5, 0.5, 0.2, 0.8);
        let blended = p1.blend(&bias, 0.30);
        assert!((blended.x - 0.15).abs() < 1e-4);
        assert!((blended.y - 0.15).abs() < 1e-4);
    }

    #[test]
    fn test_resonance_activation_cascades_and_dampening() {
        let mut engine = GardenResonanceEngine::new();

        // Initially baseline
        let init_courage = engine.activations["courage"];
        let init_adventure = engine.activations["adventure"];
        let init_patience = engine.activations["patience"];

        // Activate courage +0.40
        engine.activate("courage", 0.40);

        // Direct activation
        assert!(engine.activations["courage"] > init_courage + 0.35);

        // Resonance partner (adventure) gets 50% boost (+0.20)
        assert!(engine.activations["adventure"] > init_adventure + 0.15);

        // Dampening partner (patience) is dampened (-0.12)
        assert!(engine.activations["patience"] <= init_patience);
    }

    #[test]
    fn test_match_keywords() {
        let matches = GardenResonanceEngine::match_keywords("We need a firewall security audit and red-team scan");
        assert!(!matches.is_empty());
        let top_garden = matches[0].0.name;
        // Either love (security, firewall) or wonder (scan)
        assert!(top_garden == "love" || top_garden == "wonder");
    }

    #[test]
    fn test_centroid_calculation_and_report() {
        let mut engine = GardenResonanceEngine::new();
        engine.activate("wisdom", 0.8);
        engine.activate("dharma", 0.9);

        let report = engine.report();
        assert!(report.dominant_garden == "dharma" || report.dominant_garden == "wisdom");
        assert!(report.dominant_activation >= 0.8);
        assert!(report.balance_entropy > 0.0);
    }
}
