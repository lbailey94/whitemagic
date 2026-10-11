//! The Sutra Compiler & The 12-Glyph Logoglyphic Canon.
//!
//! Pairs SutraCode with WhiteMagic's ratified Vector Language (DIR-06 / LWF-v1)
//! and Model2Vec System 0.5 static embeddings (`potion-base-32M`).
//!
//! Compresses high-level human architectural intent and multi-step workflows
//! into compact, deterministic logoglyphic codons with sub-microsecond parsing.

use serde::{Deserialize, Serialize};
use std::fmt;

/// Embedded static vector table (12 glyphs * 512 f32, little-endian, with 16-byte header).
pub const EMBEDDED_SUTRA_VECTORS: &[u8] = include_bytes!("../../../catalogs/sutra_vectors.bin");

/// Dimension of the Model2Vec embedding space.
pub const SUTRA_VECTOR_DIM: usize = 512;

/// Number of canonical glyphs in the canon.
pub const CANONICAL_GLYPH_COUNT: usize = 12;

/// A bounded Kekkai sandbox capability specification for a glyph.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SutraKekkaiProfile {
    pub read_only_paths: Vec<String>,
    pub read_write_paths: Vec<String>,
    pub network_allowed: bool,
}

/// The 12 Canonical Logoglyphs of the WhiteMagic Canon.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SutraGlyph {
    /// 證 (Zhèng) — Verify / Test / Proof
    Zheng = 0,
    /// 行 (Xíng) — Execute / Commit / Dispatch
    Xing = 1,
    /// 觀 (Guān) — Survey / Telemetry / Inspect
    Guan = 2,
    /// 合 (Hé) — Synthesize / Unify into One
    He = 3,
    /// 遠 (Yuǎn) — Project / Horizon / N+ Order
    Yuan = 4,
    /// 鏡 (Jìng) — Mirror / Compare / Analogy
    Jing = 5,
    /// 息 (Xī) — Quiesce / Sleep / Dream
    Xi = 6,
    /// 清 (Qīng) — Clean / Prune / Compact
    Qing = 7,
    /// 應 (Yìng) — Resonate / Affirm / P2P Wire
    Ying = 8,
    /// 界 (Jiè) — Kekkai / Sandbox / Confine
    Jie = 9,
    /// 根 (Gēn) — Root / Lineage / Origins
    Gen = 10,
    /// 生 (Shēng) — Evolve / Mutate / Speciate
    Sheng = 11,
}

impl SutraGlyph {
    /// All 12 canonical glyphs in standard index order.
    pub const ALL: [SutraGlyph; CANONICAL_GLYPH_COUNT] = [
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

    /// Index of this glyph (0..11).
    #[must_use]
    pub const fn index(self) -> usize {
        self as usize
    }

    /// Single character representation.
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
            Self::Yuan => "Project downstream order effects, thirty year horizon, deliberate strategy",
            Self::Jing => "Mirror across domains, draw biological and physical analogies, comparative analysis",
            Self::Xi => "Quiesce execution, enter deep sleep, incubate associative dreams",
            Self::Qing => "Clean working tree, prune dead branches, compact Pareto vault",
            Self::Ying => "Gan Ying resonance, wire protocol handshake, fleet synchronization, p2p mesh",
            Self::Jie => "Erect Landlock confinement, enforce spatial capability boundary, secure sandbox",
            Self::Gen => "Primordial invariants, trace Tacit lineage, ancestral roots, archaeology archive",
            Self::Sheng => "Speciate new variants, genetic mutation, evolutionary promotion, germline action",
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
        }
    }

    /// Resolve glyph from single character.
    #[must_use]
    pub fn from_char(c: char) -> Option<Self> {
        match c {
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
            _ => None,
        }
    }

    /// Loose parser from textual tokens (pinyin, english keywords, or unicode character).
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
            "zheng" | "zhèng" | "verify" | "proof" | "audit" | "test" => Some(Self::Zheng),
            "xing" | "xíng" | "execute" | "dispatch" | "commit" | "ship" => Some(Self::Xing),
            "guan" | "guān" | "survey" | "inspect" | "telemetry" | "status" => Some(Self::Guan),
            "he" | "hé" | "synthesize" | "unify" | "merge" | "combine" => Some(Self::He),
            "yuan" | "yuǎn" | "horizon" | "project" | "strategy" | "future" => Some(Self::Yuan),
            "jing" | "jìng" | "mirror" | "analogy" | "compare" => Some(Self::Jing),
            "xi" | "xī" | "quiesce" | "sleep" | "dream" | "rest" => Some(Self::Xi),
            "qing" | "qīng" | "clean" | "prune" | "compact" | "purge" => Some(Self::Qing),
            "ying" | "yìng" | "resonate" | "wire" | "mesh" | "ganying" | "affirm" => Some(Self::Ying),
            "jie" | "jiè" | "kekkai" | "sandbox" | "confine" | "boundary" => Some(Self::Jie),
            "gen" | "gēn" | "origin" | "root" | "lineage" | "ancestral" => Some(Self::Gen),
            "sheng" | "shēng" | "evolve" | "speciate" | "mutate" | "birth" => Some(Self::Sheng),
            _ => None,
        }
    }

    /// Retrieve the precomputed, unit-normalized 512-dim embedding vector directly from embedded table.
    #[must_use]
    pub fn vector(self) -> [f32; SUTRA_VECTOR_DIM] {
        let offset = 16 + (self.index() * SUTRA_VECTOR_DIM * 4);
        let mut vec = [0.0f32; SUTRA_VECTOR_DIM];
        for i in 0..SUTRA_VECTOR_DIM {
            let start = offset + (i * 4);
            let bytes = [
                EMBEDDED_SUTRA_VECTORS[start],
                EMBEDDED_SUTRA_VECTORS[start + 1],
                EMBEDDED_SUTRA_VECTORS[start + 2],
                EMBEDDED_SUTRA_VECTORS[start + 3],
            ];
            vec[i] = f32::from_le_bytes(bytes);
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
                .split(|c: char| c.is_whitespace() || c == '·' || c == ',' || c == '-' || c == '/' || c == '.')
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

        // Identify canonical triplet name
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
            .find(|g| matches!(g, SutraGlyph::Xing | SutraGlyph::Zheng | SutraGlyph::He | SutraGlyph::Xi | SutraGlyph::Ying | SutraGlyph::Sheng))
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
        assert_eq!(&EMBEDDED_SUTRA_VECTORS[0..8], b"SUTR0001", "magic header must match");
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
        assert_eq!(c2.glyphs, vec![SutraGlyph::Guan, SutraGlyph::He, SutraGlyph::Yuan]);
        assert_eq!(c2.primary_skeleton_id, "skel-dream-dream-6cfcfda755");

        // Quiesce clean evolve
        let c3 = CompoundSutra::parse("息 清 生").expect("dreamer parses");
        assert_eq!(c3.glyphs, vec![SutraGlyph::Xi, SutraGlyph::Qing, SutraGlyph::Sheng]);
        assert_eq!(c3.codon_str, "⟪ 息 · 清 · 生 ⟫");
    }

    #[test]
    fn test_kekkai_profile_merging() {
        let c = CompoundSutra::parse("界 應 根").expect("sovereign parses");
        assert_eq!(c.glyphs, vec![SutraGlyph::Jie, SutraGlyph::Ying, SutraGlyph::Gen]);
        // Ying requires network
        assert!(c.kekkai_profile.network_allowed);
        assert!(c.kekkai_profile.read_write_paths.contains(&"sandbox/".to_string()));
        assert!(c.kekkai_profile.read_write_paths.contains(&"/dev/shm".to_string()));
    }
}
