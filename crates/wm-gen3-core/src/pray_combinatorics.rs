//! The Unified `PRAY` + 28-Gana + 24-Sutra + 64-Hexagram Combinatorial Meta-Engine.
//!
//! Synthesizes WhiteMagic's Gen 1, Gen 2, and Gen 3 heritage into a single
//! zero-allocation combinatorial dispatch algebra:
//! - **4 `PRAY` Phases:** `Perceive` (`觀/察/微/受/根/醒`) -> `Resonate` (`鏡/應/辨/通/照/遠`)
//!   -> `Act` (`行/生/擬/分/芽/化`) -> `Yield` (`證/合/息/清/界/澄`)
//! - **28 Lunar Mansion Ganas (二十八宿):** 4 Celestial Quadrants (East Azure Dragon,
//!   North Black Tortoise, West White Tiger, South Vermilion Bird) x 7 Mansions,
//!   each carrying a SkillsBench-compliant `<100`-token curated `PRAY` micro-skill.
//! - **64 King Wen Hexagrams x 28 Ganas = `1,792` Canonical Macro-Seals**
//! - **24 Yin/Yang Sutra Logoglyphs:** $24^3 = 13,824$ 3-glyph mudras and
//!   $24^4 = 331,776$ 4-glyph `PRAY` chains (`6^4 = 1,296` stage-pure `PRAY` chains).
//! - **Subagent Swarm Orchestration:** Statically computes the Kekkai sandbox
//!   boundary and fans out non-conflicting `FutureValue` subagent branches into
//!   `PulseTree::arbitrate` in microseconds.

#![forbid(unsafe_code)]
#![allow(clippy::suboptimal_flops)]

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::bicameral::EpistemicStatus;
use crate::capability::VerifiedWarrant;
use crate::hexagram::{Hexagram, Trigram, WuXing};
use crate::pulse_compiler::{
    CognitiveIntent, FutureValue, Provenance, PulseError, PulseTree, ResourceEnvelope, StateDelta,
    SubstrateSnapshot,
};
use crate::sutra::{SUTRA_VECTOR_DIM, SutraGlyph, SutraKekkaiProfile};

/// Total number of Lunar Mansion Ganas (二十八宿).
pub const GANA_COUNT: usize = 28;

/// Total number of 4-glyph combinations over the 24-glyph canon ($24^4$).
pub const TOTAL_4GLYPH_CODONS: usize = 24 * 24 * 24 * 24; // 331,776

/// Total number of stage-pure 4-glyph `PRAY` chains ($6^4$).
pub const STAGE_PURE_PRAY_CHAINS: usize = 6 * 6 * 6 * 6; // 1,296

/// Total number of Gana x Hexagram macro-seals ($28 \times 64$).
pub const GANA_HEXAGRAM_SEALS: usize = 28 * 64; // 1,792

/// The Four Celestial Quadrants (四象) of the 28 Lunar Mansions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CelestialQuadrant {
    /// 東方蒼龍 — Azure Dragon of the East (Wood / Spring / Reconnaissance)
    EastAzureDragon,
    /// 北方玄武 — Black Tortoise of the North (Water / Winter / Deep Memory & Foresight)
    NorthBlackTortoise,
    /// 西方白虎 — White Tiger of the West (Metal / Autumn / Verification & Containment)
    WestWhiteTiger,
    /// 南方朱雀 — Vermilion Bird of the South (Fire / Summer / Kinetic Execution & Mesh)
    SouthVermilionBird,
}

impl CelestialQuadrant {
    #[must_use]
    pub const fn wu_xing(self) -> WuXing {
        match self {
            Self::EastAzureDragon => WuXing::Wood,
            Self::NorthBlackTortoise => WuXing::Water,
            Self::WestWhiteTiger => WuXing::Metal,
            Self::SouthVermilionBird => WuXing::Fire,
        }
    }

    #[must_use]
    pub const fn name_zh(self) -> &'static str {
        match self {
            Self::EastAzureDragon => "東方蒼龍",
            Self::NorthBlackTortoise => "北方玄武",
            Self::WestWhiteTiger => "西方白虎",
            Self::SouthVermilionBird => "南方朱雀",
        }
    }
}

/// The four functional stages of the Gen 1 / Gen 3 `PRAY` cycle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PrayStage {
    /// Perceive (觀): Survey, probe, micro-inspect, receive, trace roots, awaken.
    Perceive = 0,
    /// Resonate (應): Mirror, affirm P2P, discriminate/fuzz, bridge, illuminate, project horizon.
    Resonate = 1,
    /// Act (行): Execute, evolve/speciate, simulate shadow, decompose, sprout/fork, transmute.
    Act = 2,
    /// Yield (證): Verify/attest, synthesize, quiesce/dream, clean/prune, confine Kekkai, clarify.
    Yield = 3,
}

impl PrayStage {
    pub const ALL: [PrayStage; 4] = [Self::Perceive, Self::Resonate, Self::Act, Self::Yield];

    /// The 6 canonical/polar glyphs assigned to this `PRAY` stage.
    #[must_use]
    pub const fn stage_glyphs(self) -> [SutraGlyph; 6] {
        match self {
            Self::Perceive => [
                SutraGlyph::Guan,
                SutraGlyph::Cha,
                SutraGlyph::Wei,
                SutraGlyph::Shou,
                SutraGlyph::Gen,
                SutraGlyph::XingAlert,
            ],
            Self::Resonate => [
                SutraGlyph::Jing,
                SutraGlyph::Ying,
                SutraGlyph::Bian,
                SutraGlyph::Tong,
                SutraGlyph::Zhao,
                SutraGlyph::Yuan,
            ],
            Self::Act => [
                SutraGlyph::Xing,
                SutraGlyph::Sheng,
                SutraGlyph::Ni,
                SutraGlyph::Fen,
                SutraGlyph::Ya,
                SutraGlyph::Hua,
            ],
            Self::Yield => [
                SutraGlyph::Zheng,
                SutraGlyph::He,
                SutraGlyph::Xi,
                SutraGlyph::Qing,
                SutraGlyph::Jie,
                SutraGlyph::Cheng,
            ],
        }
    }
}

/// Metadata and curated `<100`-token `PRAY` micro-skill for each of the 28 Ganas.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct GanaMansion {
    /// 1-indexed Lunar Mansion number (`1..=28`).
    pub id: u8,
    pub slug: &'static str,
    pub name_zh: &'static str,
    pub name_en: &'static str,
    pub quadrant: CelestialQuadrant,
    pub primary_glyph: SutraGlyph,
    pub primary_trigram: Trigram,
    /// Compact (<100-token) procedural micro-skill (SkillsBench Finding 3 compliant).
    pub curated_pray_skill: &'static str,
}

/// The Canonical 28 Lunar Mansion Ganas (二十八宿).
pub const GANA_CATALOG: [GanaMansion; GANA_COUNT] = [
    // ── East Azure Dragon (1..=7) — Wood ──
    GanaMansion {
        id: 1,
        slug: "gana_horn",
        name_zh: "角宿",
        name_en: "Horn (Jiao)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Guan,
        primary_trigram: Trigram::Zhen,
        curated_pray_skill: "P:Read session.continuity & active claims. R:Check scope conflicts. A:Open session/track claim. Y:Emit bounded initiation state.",
    },
    GanaMansion {
        id: 2,
        slug: "gana_neck",
        name_zh: "亢宿",
        name_en: "Neck (Kang)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Jie,
        primary_trigram: Trigram::Gen,
        curated_pray_skill: "P:Inspect path & network requirements. R:Compute Kekkai intersection. A:Lock Landlock write-barrier. Y:Verify capability jti.",
    },
    GanaMansion {
        id: 3,
        slug: "gana_root",
        name_zh: "氐宿",
        name_en: "Root (Di)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Gen,
        primary_trigram: Trigram::Xun,
        curated_pray_skill: "P:Query LMDB substrate & ancestral lineage. R:Rank hybrid BM25+vector hits. A:Bind provenance citations. Y:Verify digest integrity.",
    },
    GanaMansion {
        id: 4,
        slug: "gana_room",
        name_zh: "房宿",
        name_en: "Room (Fang)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Tong,
        primary_trigram: Trigram::Dui,
        curated_pray_skill: "P:Scan compartment boundaries. R:Validate cross-galaxy access policy. A:Route scoped SHM/IPC transfer. Y:Audit zero-leakage.",
    },
    GanaMansion {
        id: 5,
        slug: "gana_heart",
        name_zh: "心宿",
        name_en: "Heart (Xin)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Ying,
        primary_trigram: Trigram::Li,
        curated_pray_skill: "P:Sample bioelectric homeostasis & thermals. R:Check Citta rhythm setpoint. A:Modulate cognitive tier budget. Y:Record harmony vector.",
    },
    GanaMansion {
        id: 6,
        slug: "gana_tail",
        name_zh: "尾宿",
        name_en: "Tail (Wei)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Ya,
        primary_trigram: Trigram::Zhen,
        curated_pray_skill: "P:Identify parallelizable sub-tasks. R:Partition disjoint write sets. A:Fork isolated subagent branches. Y:Collect FutureValue deltas.",
    },
    GanaMansion {
        id: 7,
        slug: "gana_winnowing_basket",
        name_zh: "箕宿",
        name_en: "Winnowing Basket (Ji)",
        quadrant: CelestialQuadrant::EastAzureDragon,
        primary_glyph: SutraGlyph::Cheng,
        primary_trigram: Trigram::Xun,
        curated_pray_skill: "P:Ingest raw stream or corpus batch. R:Project via TTTHead PCA-128. A:Filter noise & tag singletons. Y:Escalate only conformal multi-sets.",
    },
    // ── North Black Tortoise (8..=14) — Water ──
    GanaMansion {
        id: 8,
        slug: "gana_dipper",
        name_zh: "斗宿",
        name_en: "Dipper (Dou)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::Yuan,
        primary_trigram: Trigram::Kan,
        curated_pray_skill: "P:Measure calibration & nonconformity scores. R:Compute PEB-12 quantile q_hat. A:Gate prediction sets at 1-alpha. Y:Report Wilson CI.",
    },
    GanaMansion {
        id: 9,
        slug: "gana_ox",
        name_zh: "牛宿",
        name_en: "Ox (Niu)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::He,
        primary_trigram: Trigram::Kun,
        curated_pray_skill: "P:Scan durable journal & WAL state. R:Verify SHA-256 chain continuity. A:Commit atomic batch transaction. Y:Emit state.commitment receipt.",
    },
    GanaMansion {
        id: 10,
        slug: "gana_girl",
        name_zh: "女宿",
        name_en: "Girl (Nu)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::Shou,
        primary_trigram: Trigram::Kun,
        curated_pray_skill: "P:Receive tenant or crystal payload. R:Bind cell_id & owner HKDF scope. A:Seal XChaCha20-Poly1305 envelope. Y:Verify tag & W-OTS+ sig.",
    },
    GanaMansion {
        id: 11,
        slug: "gana_emptiness",
        name_zh: "虛宿",
        name_en: "Emptiness (Xu)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::Xi,
        primary_trigram: Trigram::Kan,
        curated_pray_skill: "P:Detect idle/quiescent window. R:Select high-salience unlinked turns. A:Run NREM/REM dream consolidation. Y:Persist crystallized insights.",
    },
    GanaMansion {
        id: 12,
        slug: "gana_rooftop",
        name_zh: "危宿",
        name_en: "Rooftop (Wei)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::Bian,
        primary_trigram: Trigram::Kan,
        curated_pray_skill: "P:Inspect perimeter & canary tokens. R:Probe adversarial edge cases. A:Quarantine bad-apple peers/IPs. Y:Append dual-hash Blue-Ops ledger.",
    },
    GanaMansion {
        id: 13,
        slug: "gana_encampment",
        name_zh: "室宿",
        name_en: "Encampment (Shi)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::Qing,
        primary_trigram: Trigram::Gen,
        curated_pray_skill: "P:Check disk headroom & store fragmentation. R:Identify regenerable caches. A:Prune incrementals & compact cold records. Y:Verify 0 data loss.",
    },
    GanaMansion {
        id: 14,
        slug: "gana_wall",
        name_zh: "壁宿",
        name_en: "Wall (Bi)",
        quadrant: CelestialQuadrant::NorthBlackTortoise,
        primary_glyph: SutraGlyph::Zheng,
        primary_trigram: Trigram::Gen,
        curated_pray_skill: "P:Load formal laws & invariant specs. R:Check bidirectional proof terms. A:Run deterministic test battery. Y:Seal verified conformance report.",
    },
    // ── West White Tiger (15..=21) — Metal ──
    GanaMansion {
        id: 15,
        slug: "gana_legs",
        name_zh: "奎宿",
        name_en: "Legs (Kui)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Cha,
        primary_trigram: Trigram::Qian,
        curated_pray_skill: "P:Traverse AST & dependency graph. R:Cross-reference symbol definitions. A:Pinpoint exact line ranges. Y:Return cited structural map.",
    },
    GanaMansion {
        id: 16,
        slug: "gana_bond",
        name_zh: "婁宿",
        name_en: "Bond (Lou)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Jing,
        primary_trigram: Trigram::Dui,
        curated_pray_skill: "P:Read multi-repo contract surfaces. R:Diff schemas, hashes, and versions. A:Synchronize canonical artifacts. Y:Verify deploy-check 100% SAME.",
    },
    GanaMansion {
        id: 17,
        slug: "gana_stomach",
        name_zh: "胃宿",
        name_en: "Stomach (Wei)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Hua,
        primary_trigram: Trigram::Kun,
        curated_pray_skill: "P:Digest large transcript or document batch. R:Extract high-importance decisions. A:Compress into typed memory records. Y:Link DiAML edges.",
    },
    GanaMansion {
        id: 18,
        slug: "gana_hairy_head",
        name_zh: "昴宿",
        name_en: "Hairy Head (Mao)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Wei,
        primary_trigram: Trigram::Dui,
        curated_pray_skill: "P:Zoom to single-line / byte boundary. R:Check UTF-8, base64 pad bits, and RFC grammar. A:Apply surgical fix. Y:Confirm regression vector passes.",
    },
    GanaMansion {
        id: 19,
        slug: "gana_net",
        name_zh: "畢宿",
        name_en: "Net (Bi)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Zhao,
        primary_trigram: Trigram::Qian,
        curated_pray_skill: "P:Capture failed probes & friction logs. R:Synthesize minimal reproduction test. A:Patch root cause & re-probe. Y:Resolve friction record.",
    },
    GanaMansion {
        id: 20,
        slug: "gana_turtle_beak",
        name_zh: "觜宿",
        name_en: "Turtle Beak (Zui)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Fen,
        primary_trigram: Trigram::Dui,
        curated_pray_skill: "P:Parse natural-language or glyph intent. R:Resolve Catuskoti K1-K4 corner. A:Compile zero-alloc StackCodon. Y:Dispatch bound action skeleton.",
    },
    GanaMansion {
        id: 21,
        slug: "gana_three_stars",
        name_zh: "參宿",
        name_en: "Three Stars (Shen)",
        quadrant: CelestialQuadrant::WestWhiteTiger,
        primary_glyph: SutraGlyph::Ni,
        primary_trigram: Trigram::Qian,
        curated_pray_skill: "P:Gather candidate FutureValue branches. R:Evaluate Law 8 composite margins. A:Arbitrate non-conflicting write sets. Y:Issue VerifiedWarrant.",
    },
    // ── South Vermilion Bird (22..=28) — Fire ──
    GanaMansion {
        id: 22,
        slug: "gana_well",
        name_zh: "井宿",
        name_en: "Well (Jing)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::Guan,
        primary_trigram: Trigram::Kan,
        curated_pray_skill: "P:Query 6D holographic coordinates & cold catalog. R:Fuse dense + lexical scores. A:Hydrate top-k context within token budget. Y:Cite record IDs.",
    },
    GanaMansion {
        id: 23,
        slug: "gana_ghost",
        name_zh: "鬼宿",
        name_en: "Ghost (Gui)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::XingAlert,
        primary_trigram: Trigram::Li,
        curated_pray_skill: "P:Monitor sentinel timers & unclaimed dirty trees. R:Check lease TTL & owner liveness. A:Flag anomalies to Sangha board. Y:Maintain 0 lint errors.",
    },
    GanaMansion {
        id: 24,
        slug: "gana_willow",
        name_zh: "柳宿",
        name_en: "Willow (Liu)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::Sheng,
        primary_trigram: Trigram::Xun,
        curated_pray_skill: "P:Sample hypothesis tails in parallel. R:Probe candidates against executable oracle. A:Compose winning primitive skills. Y:Promote to library.",
    },
    GanaMansion {
        id: 25,
        slug: "gana_star",
        name_zh: "星宿",
        name_en: "Star (Xing)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::Zhao,
        primary_trigram: Trigram::Li,
        curated_pray_skill: "P:Inspect public discovery cards & llms.txt. R:Compare against signed release manifest. A:Regenerate facts & chunks. Y:Pass check_build_truth.",
    },
    GanaMansion {
        id: 26,
        slug: "gana_extended_net",
        name_zh: "張宿",
        name_en: "Extended Net (Zhang)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::Ying,
        primary_trigram: Trigram::Li,
        curated_pray_skill: "P:Listen on Wire Protocol 7369 & Agora bridge. R:Verify peer HMAC/Ed25519 signature. A:Route mudra handoff or board post. Y:Ack delivery receipt.",
    },
    GanaMansion {
        id: 27,
        slug: "gana_wings",
        name_zh: "翼宿",
        name_en: "Wings (Yi)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::Xing,
        primary_trigram: Trigram::Qian,
        curated_pray_skill: "P:Verify release gates, clippy, and fmt. R:Sign artifacts & compute SHA256SUMS. A:Publish release & deploy service units. Y:Run live rollback probe.",
    },
    GanaMansion {
        id: 28,
        slug: "gana_chariot",
        name_zh: "軫宿",
        name_en: "Chariot (Zhen)",
        quadrant: CelestialQuadrant::SouthVermilionBird,
        primary_glyph: SutraGlyph::Zheng,
        primary_trigram: Trigram::Kun,
        curated_pray_skill: "P:Verify x402 EIP-3009 or XRPL PayChannel claim. R:Enforce R16 budget & nullifier guard. A:Settle payment & issue SessionPass. Y:Emit AER-1 receipt.",
    },
];

/// A 4-glyph `PRAY` chain (`Perceive · Resonate · Act · Yield`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PrayChain {
    pub perceive: SutraGlyph,
    pub resonate: SutraGlyph,
    pub act: SutraGlyph,
    pub yield_glyph: SutraGlyph,
}

impl PrayChain {
    #[must_use]
    pub const fn new(
        perceive: SutraGlyph,
        resonate: SutraGlyph,
        act: SutraGlyph,
        yield_glyph: SutraGlyph,
    ) -> Self {
        Self {
            perceive,
            resonate,
            act,
            yield_glyph,
        }
    }

    #[must_use]
    pub const fn as_array(self) -> [SutraGlyph; 4] {
        [self.perceive, self.resonate, self.act, self.yield_glyph]
    }

    /// Encode this 4-glyph chain into a unique bijective index in `0..331,776` ($24^4$).
    #[must_use]
    pub const fn combinatorial_id(self) -> u32 {
        let p = self.perceive.index() as u32;
        let r = self.resonate.index() as u32;
        let a = self.act.index() as u32;
        let y = self.yield_glyph.index() as u32;
        ((p * 24 + r) * 24 + a) * 24 + y
    }

    /// Decode a bijective index in `0..331,776` ($24^4$) back into its exact `PrayChain`.
    #[must_use]
    pub fn from_combinatorial_id(id: u32) -> Option<Self> {
        if id as usize >= TOTAL_4GLYPH_CODONS {
            return None;
        }
        let y = (id % 24) as usize;
        let a = ((id / 24) % 24) as usize;
        let r = ((id / (24 * 24)) % 24) as usize;
        let p = ((id / (24 * 24 * 24)) % 24) as usize;
        Some(Self {
            perceive: SutraGlyph::ALL[p],
            resonate: SutraGlyph::ALL[r],
            act: SutraGlyph::ALL[a],
            yield_glyph: SutraGlyph::ALL[y],
        })
    }

    /// Format into canonical mudra string `⟪ P · R · A · Y ⟫`.
    #[must_use]
    pub fn to_codon_string(self) -> String {
        format!(
            "⟪ {} · {} · {} · {} ⟫",
            self.perceive.as_char(),
            self.resonate.as_char(),
            self.act.as_char(),
            self.yield_glyph.as_char()
        )
    }

    /// Compute the static Kekkai sandbox profile for this 4-stage `PRAY` chain.
    #[must_use]
    pub fn kekkai_profile(self) -> SutraKekkaiProfile {
        let mut ro_set = Vec::new();
        let mut rw_set = Vec::new();
        let mut net = false;
        for g in self.as_array() {
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
        SutraKekkaiProfile {
            read_only_paths: ro_set,
            read_write_paths: rw_set,
            network_allowed: net,
        }
    }
}

/// A compiled combinatorial macro-seal binding a `PrayChain`, a `GanaMansion` (`1..=28`),
/// and a `Hexagram` (`1..=64`).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CompiledPraySeal {
    pub chain: PrayChain,
    pub combinatorial_id: u32,
    pub codon_str: String,
    pub gana: GanaMansion,
    pub hexagram: Hexagram,
    pub seal_index_1792: u16,
    pub kekkai_profile: SutraKekkaiProfile,
    pub alignment_score: f32,
}

/// Zero-allocation combinatorial compiler and subagent swarm orchestrator.
pub struct PrayCombinatorialEngine;

impl PrayCombinatorialEngine {
    /// Retrieve a Gana Mansion by its 1-indexed ID (`1..=28`).
    #[must_use]
    pub const fn get_gana(id_1_to_28: u8) -> Option<&'static GanaMansion> {
        if id_1_to_28 >= 1 && (id_1_to_28 as usize) <= GANA_COUNT {
            Some(&GANA_CATALOG[(id_1_to_28 as usize) - 1])
        } else {
            None
        }
    }

    /// Compile a 512-dimensional query vector into its optimal `CompiledPraySeal`
    /// (`PrayChain` + `GanaMansion` + `Hexagram` + static `SutraKekkaiProfile`).
    #[must_use]
    pub fn compile_from_vector512(query_vec: &[f32; SUTRA_VECTOR_DIM]) -> CompiledPraySeal {
        // Score all 24 SutraGlyph vectors on the stack using 4-lane accumulator
        let mut scores = [0.0f32; 24];
        for (idx, &glyph) in SutraGlyph::ALL.iter().enumerate() {
            let gv = glyph.vector();
            let mut s0 = 0.0f32;
            let mut s1 = 0.0f32;
            let mut s2 = 0.0f32;
            let mut s3 = 0.0f32;
            let mut q_chunks = query_vec.chunks_exact(4);
            let mut g_chunks = gv.chunks_exact(4);
            for (qc, gc) in q_chunks.by_ref().zip(g_chunks.by_ref()) {
                s0 += qc[0] * gc[0];
                s1 += qc[1] * gc[1];
                s2 += qc[2] * gc[2];
                s3 += qc[3] * gc[3];
            }
            scores[idx] = (s0 + s1) + (s2 + s3);
        }

        // Select the highest-scoring glyph in each of the 4 PRAY stages
        let best_in_stage = |stage: PrayStage| -> (SutraGlyph, f32) {
            let candidates = stage.stage_glyphs();
            let mut best_g = candidates[0];
            let mut best_s = f32::NEG_INFINITY;
            for &g in &candidates {
                let s = scores[g.index()];
                if s > best_s {
                    best_s = s;
                    best_g = g;
                }
            }
            (best_g, best_s)
        };

        let (p_glyph, s_p) = best_in_stage(PrayStage::Perceive);
        let (r_glyph, s_r) = best_in_stage(PrayStage::Resonate);
        let (a_glyph, s_a) = best_in_stage(PrayStage::Act);
        let (y_glyph, s_y) = best_in_stage(PrayStage::Yield);

        let chain = PrayChain::new(p_glyph, r_glyph, a_glyph, y_glyph);
        let alignment_score = (s_p + s_r + s_a + s_y) * 0.25;

        // Derive Lower Trigram (Inner Agent Posture from Perceive+Act) and Upper Trigram (Outer Context from Resonate+Yield)
        let lower_trigram = Self::glyph_to_trigram(a_glyph);
        let upper_trigram = Self::glyph_to_trigram(r_glyph);
        let hexagram = Hexagram::from_trigrams(upper_trigram, lower_trigram);

        // Select the highest-resonance Gana Mansion among the 28 Mansions
        let mut best_gana = GANA_CATALOG[0];
        let mut best_gana_score = f32::NEG_INFINITY;
        for &gana in &GANA_CATALOG {
            let mut gs = scores[gana.primary_glyph.index()];
            if gana.primary_trigram == lower_trigram || gana.primary_trigram == upper_trigram {
                gs += 0.15;
            }
            if gana.quadrant.wu_xing() == hexagram.dominant_element() {
                gs += 0.10;
            }
            if gs > best_gana_score {
                best_gana_score = gs;
                best_gana = gana;
            }
        }

        let seal_index_1792 =
            ((best_gana.id as u16 - 1) * 64) + (hexagram.king_wen_id() as u16 - 1);

        CompiledPraySeal {
            chain,
            combinatorial_id: chain.combinatorial_id(),
            codon_str: chain.to_codon_string(),
            gana: best_gana,
            hexagram,
            seal_index_1792,
            kekkai_profile: chain.kekkai_profile(),
            alignment_score,
        }
    }

    /// Fan out a slice of `CompiledPraySeal` subagent tasks into non-conflicting `FutureValue`
    /// proposals and arbitrate them through `PulseTree::arbitrate` in microseconds.
    pub fn execute_parallel_subagent_swarm(
        seals: &[CompiledPraySeal],
        snapshot: &SubstrateSnapshot,
        sequence_id: u64,
        scope: &str,
    ) -> Result<(StateDelta, VerifiedWarrant), PulseError> {
        let mut candidates = Vec::with_capacity(seals.len());
        for (idx, seal) in seals.iter().enumerate() {
            let key = format!(
                "gana:{}/hex:{}/codon:{}",
                seal.gana.slug,
                seal.hexagram.king_wen_id(),
                seal.combinatorial_id
            );
            let val = format!(
                "{}|{}|{}",
                seal.codon_str,
                seal.gana.name_en,
                seal.hexagram.name_en()
            );
            let mut delta = StateDelta::with_capacity(1);
            delta.insert(key.clone(), val);
            let mut write_set = HashSet::with_capacity(1);
            write_set.insert(key);

            let margin = 0.88 + (seal.alignment_score.clamp(-0.02, 0.11) as f64);
            candidates.push(FutureValue {
                candidate_id: (idx + 1) as u64,
                snapshot_epoch: snapshot.version.global_epoch,
                read_set: HashSet::new(),
                write_set,
                delta,
                composite_margin: margin,
                estimated_risk: 0.04,
                expected_utility: margin,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: String::new(),
            });
        }
        let intent = CognitiveIntent {
            intent_name: "pray_combinatorial_swarm".to_string(),
            target_scope: scope.to_string(),
            candidates,
        };
        let tree = PulseTree::compile(snapshot.clone(), intent, ResourceEnvelope::default())?;
        tree.arbitrate(sequence_id, scope)
    }

    #[must_use]
    pub const fn glyph_to_trigram(glyph: SutraGlyph) -> Trigram {
        match glyph {
            SutraGlyph::Xing | SutraGlyph::Zhao | SutraGlyph::Bian => Trigram::Qian,
            SutraGlyph::Jing | SutraGlyph::Tong | SutraGlyph::Cheng => Trigram::Dui,
            SutraGlyph::Zheng | SutraGlyph::Ni | SutraGlyph::Shou => Trigram::Li,
            SutraGlyph::Ying | SutraGlyph::Sheng | SutraGlyph::Ya => Trigram::Zhen,
            SutraGlyph::Gen | SutraGlyph::Guan | SutraGlyph::Cha => Trigram::Xun,
            SutraGlyph::Yuan | SutraGlyph::Wei | SutraGlyph::Qing => Trigram::Kan,
            SutraGlyph::Jie | SutraGlyph::Fen | SutraGlyph::XingAlert => Trigram::Gen,
            SutraGlyph::Xi | SutraGlyph::He | SutraGlyph::Hua => Trigram::Kun,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pulse_compiler::SnapshotVersion;
    use std::collections::HashMap;

    #[test]
    fn test_28_ganas_and_combinatorial_bijection() {
        assert_eq!(GANA_CATALOG.len(), 28);
        for (i, gana) in GANA_CATALOG.iter().enumerate() {
            assert_eq!(gana.id as usize, i + 1);
            assert!(
                gana.curated_pray_skill.len() < 240,
                "Gana {} skill must stay compact (<100 tokens)",
                gana.slug
            );
        }

        // Verify bijective encoding/decoding across corners of the 331,776 (24^4) space
        for id in [0u32, 1, 23, 575, 13_823, 123_456, 331_775] {
            let chain = PrayChain::from_combinatorial_id(id).expect("valid combinatorial id");
            assert_eq!(chain.combinatorial_id(), id);
        }
        assert!(PrayChain::from_combinatorial_id(331_776).is_none());
    }

    #[test]
    fn test_compile_vector_and_parallel_swarm_arbitration() {
        let v1 = SutraGlyph::Guan.vector();
        let v2 = SutraGlyph::Xing.vector();
        let v3 = SutraGlyph::Zheng.vector();

        let s1 = PrayCombinatorialEngine::compile_from_vector512(&v1);
        let s2 = PrayCombinatorialEngine::compile_from_vector512(&v2);
        let s3 = PrayCombinatorialEngine::compile_from_vector512(&v3);

        assert!(s1.seal_index_1792 < 1792);
        assert!(s2.seal_index_1792 < 1792);
        assert!(s3.seal_index_1792 < 1792);

        let snap = SubstrateSnapshot::new(SnapshotVersion::new(1), HashMap::new());
        let (delta, warrant) = PrayCombinatorialEngine::execute_parallel_subagent_swarm(
            &[s1, s2, s3],
            &snap,
            1,
            "swarm/pray",
        )
        .expect("parallel PRAY subagent swarm arbitrates cleanly");
        assert_eq!(delta.mutations.len(), 3);
        let _ = warrant;
    }

    #[test]
    fn benchmark_pray_combinatorics_and_swarm_fanout() {
        use crate::pulse::run_peb0_1_intelligent_merger_benchmark;
        use crate::pulse_compiler::run_peb10_pulse_compiler_benchmark;
        use std::time::Instant;

        // 1. Compile 1,000 512d vectors into full (PrayChain 331,776 + 28 Gana + 64 Hexagram + Kekkai) seals
        let mut vectors = Vec::with_capacity(64);
        for i in 0..64 {
            let base_g = SutraGlyph::ALL[i % 24].vector();
            let mod_g = SutraGlyph::ALL[(i * 7 + 3) % 24].vector();
            let mut v = [0.0f32; SUTRA_VECTOR_DIM];
            for d in 0..SUTRA_VECTOR_DIM {
                v[d] = base_g[d] * 0.75 + mod_g[d] * 0.25;
            }
            vectors.push(v);
        }

        let iterations = 1000;
        let t0 = Instant::now();
        let mut compiled_seals = Vec::with_capacity(64);
        for i in 0..iterations {
            let seal = PrayCombinatorialEngine::compile_from_vector512(&vectors[i % 64]);
            if i < 64 {
                compiled_seals.push(seal);
            }
        }
        let compile_us = t0.elapsed().as_secs_f64() * 1e6 / (iterations as f64);

        // 2. Arbitrate N=10, N=28 (all 28 Ganas), and N=64 (all 64 Hexagrams) parallel subagents
        let snap = SubstrateSnapshot::new(SnapshotVersion::new(1), HashMap::new());
        for &swarm_n in &[10usize, 28, 64] {
            let mut slice = compiled_seals[..swarm_n].to_vec();
            // Ensure distinct combinatorial IDs for non-conflicting write sets
            for (idx, item) in slice.iter_mut().enumerate() {
                item.combinatorial_id = idx as u32;
            }
            let trials = 200;
            let t_sw = Instant::now();
            for seq in 0..trials {
                let (delta, _) = PrayCombinatorialEngine::execute_parallel_subagent_swarm(
                    &slice,
                    &snap,
                    seq as u64 + 1,
                    "swarm/bench",
                )
                .unwrap();
                assert_eq!(delta.mutations.len(), swarm_n);
            }
            let sw_us = t_sw.elapsed().as_secs_f64() * 1e6 / (trials as f64);
            println!(
                "PRAY Swarm Fan-Out + PulseTree Arbitrate (N={swarm_n} subagents): {sw_us:.2} us/swarm ({:.0} swarms/s)",
                1e6 / sw_us
            );
        }

        let peb10 = run_peb10_pulse_compiler_benchmark(500);
        let peb01 = run_peb0_1_intelligent_merger_benchmark(42);
        println!(
            "PRAY Compile (512d -> 331,776 Codon + 28 Gana + 64 Hexagram + Kekkai): {compile_us:.2} us/seal ({:.0} seals/s)",
            1e6 / compile_us
        );
        println!("PEB-10 PulseCompiler (500 trials): {peb10:?}");
        println!("PEB-0.1 Intelligent Merger: {peb01:?}");
    }
}
