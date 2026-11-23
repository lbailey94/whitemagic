//! Pure safe (`#![forbid(unsafe_code)]`) holographic & lexical-order algebra for Stage 4A:
//! - `Qfhrr64`: 64-D K=16 circular quantized Fourier HRR phase fingerprint (`64 B`).
//! - `GhrrBlockSo4x16`: non-commutative block-diagonal `SO(4)^16` group element for ordered
//!   phrase/causal binding (`A * B != B * A`) generated via exact planar Givens rotations.
//! - `content_terms_with_tf`: weighted BM25 term-frequency & adjacent-sequence extractor.
//! - `canonicalize_for_noise_check`: AGMI zero-width / confusable-homoglyph canonicalizer.

use std::collections::{HashMap, HashSet};

/// Common conversational function words down-weighted (0.10) vs content terms (1.00)
/// so noisy conversational frames ("what", "did", "when", "have", "that") never drown rare anchors.
pub const FUNCTION_STOPWORDS: &[&str] = &[
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can", "could", "d",
    "did", "do", "does", "doing", "done", "for", "from", "get", "got", "had", "has", "have",
    "having", "he", "her", "here", "hers", "him", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "just", "know", "like", "ll", "m", "me", "might", "more", "most", "my", "no",
    "not", "now", "of", "on", "one", "only", "or", "other", "our", "out", "over", "re", "really",
    "s", "said", "say", "she", "should", "so", "some", "such", "t", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "those", "to", "too", "up", "us", "ve",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "would", "you", "your", "yours",
];

#[inline]
pub fn is_function_stopword(tok: &str) -> bool {
    FUNCTION_STOPWORDS.binary_search(&tok).is_ok()
}

/// Sorted conversational query-frame / temporal scaffolding terms down-weighted (`0.24`)
/// inside `rank_stage4a_lexical_pool` so temporal/polite framing words never drown rare targets.
pub const CHASSIS_SCALING_WORDS: &[&str] = &[
    "advice",
    "after",
    "ago",
    "before",
    "chat",
    "combined",
    "conversation",
    "currently",
    "day",
    "days",
    "earlier",
    "help",
    "helping",
    "ideas",
    "last",
    "long",
    "looking",
    "many",
    "mentioned",
    "month",
    "months",
    "much",
    "often",
    "passed",
    "past",
    "planning",
    "previous",
    "previously",
    "recent",
    "recently",
    "recommend",
    "recommendations",
    "recommended",
    "remember",
    "remind",
    "since",
    "suggest",
    "suggested",
    "suggestions",
    "talked",
    "thinking",
    "tips",
    "total",
    "trying",
    "week",
    "weeks",
    "year",
    "years",
];

#[inline]
#[must_use]
pub fn is_chassis_word(tok: &str) -> bool {
    CHASSIS_SCALING_WORDS.binary_search(&tok).is_ok()
}

/// Deterministic light English inflection normalization for Stage 4A posting/BM25 matching
/// (`bikes -> bike`, `galleries -> gallery`, `doctors -> doctor`, `visited -> visit`).
#[must_use]
pub fn light_stem_english(tok: &str) -> String {
    if tok.len() <= 3 {
        return tok.to_string();
    }
    if tok.ends_with("ies") && tok.len() > 4 {
        return format!("{}y", &tok[..tok.len() - 3]);
    }
    if tok.ends_with("ing") && tok.len() > 5 {
        return tok[..tok.len() - 3].to_string();
    }
    if tok.ends_with("es") && tok.len() > 4 {
        let prev = tok.as_bytes()[tok.len() - 3];
        if matches!(prev, b's' | b'x' | b'z' | b'h') {
            return tok[..tok.len() - 2].to_string();
        }
    }
    if tok.ends_with("ed") && tok.len() > 4 {
        return tok[..tok.len() - 2].to_string();
    }
    if tok.ends_with('s') && !tok.ends_with("ss") {
        return tok[..tok.len() - 1].to_string();
    }
    tok.to_string()
}

/// FNV-1a 64-bit hash for deterministic cross-platform token seeding.
#[inline]
#[must_use]
pub fn fnv1a_64(bytes: &[u8]) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for &b in bytes {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x100000001b3);
    }
    h
}

#[inline]
#[must_use]
fn splitmix64(mut z: u64) -> u64 {
    z = z.wrapping_add(0x9e3779b97f4a7c15);
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
    z ^ (z >> 31)
}

/// Canonicalize zero-width / bidi characters and common Cyrillic/Greek confusable homoglyphs
/// into ASCII before adversarial noise/spoofing inspection.
#[must_use]
pub fn canonicalize_for_noise_check(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for ch in text.chars() {
        match ch {
            // Strip zero-width joiners / spaces / BOM / soft-hyphen
            '\u{200B}'..='\u{200F}' | '\u{202A}'..='\u{202E}' | '\u{FEFF}' | '\u{00AD}' => {}
            // Common Cyrillic homoglyphs
            'а' | 'ɑ' | 'α' => out.push('a'),
            'А' | 'Α' => out.push('A'),
            'В' | 'Β' => out.push('B'),
            'е' | 'є' | 'ε' => out.push('e'),
            'Е' | 'Ε' => out.push('E'),
            'і' | 'ї' | 'ι' => out.push('i'),
            'І' | 'Ι' => out.push('I'),
            'К' | 'Κ' => out.push('K'),
            'М' | 'Μ' => out.push('M'),
            'Н' | 'Η' => out.push('H'),
            'о' | 'ο' => out.push('o'),
            'О' | 'Ο' => out.push('O'),
            'р' | 'ρ' => out.push('p'),
            'Р' | 'Ρ' => out.push('P'),
            'с' | 'ϲ' => out.push('c'),
            'С' | 'Ϲ' => out.push('C'),
            'Т' | 'Τ' => out.push('T'),
            'х' | 'χ' => out.push('x'),
            'Х' | 'Χ' => out.push('X'),
            'у' => out.push('y'),
            _ => out.push(ch),
        }
    }
    out
}

/// Extract ordered lowercase terms with exact term-frequencies `(dl, tf_map, seq)`
/// plus a flag-aware sequence for ordered phrase/GHRR comparison.
#[must_use]
pub fn content_terms_with_tf(text: &str) -> (usize, HashMap<String, usize>, Vec<String>) {
    let mut seq = Vec::new();
    let mut tf = HashMap::new();
    let mut cur = String::new();
    let mut chars = text.chars().peekable();
    let flush = |tok: &mut String, seq: &mut Vec<String>, tf: &mut HashMap<String, usize>| {
        if tok.is_empty() {
            return;
        }
        let raw = std::mem::take(tok);
        let s = if raw.len() > 128 {
            let h1 = fnv1a_64(raw.as_bytes());
            let h2 = fnv1a_64(&raw.as_bytes()[raw.len() / 2..]);
            format!("tokh_{h1:016x}{h2:016x}")
        } else {
            raw
        };
        *tf.entry(s.clone()).or_insert(0) += 1;
        seq.push(s);
    };
    while let Some(ch) = chars.next() {
        if ch.is_alphanumeric() {
            cur.extend(ch.to_lowercase());
        } else if ch == '.'
            && !cur.is_empty()
            && cur.chars().all(|c| c.is_ascii_digit())
            && chars.peek().is_some_and(|n| n.is_ascii_digit())
        {
            cur.push('.');
        } else {
            flush(&mut cur, &mut seq, &mut tf);
        }
    }
    flush(&mut cur, &mut seq, &mut tf);
    let dl = seq.len();
    (dl, tf, seq)
}

/// Extract strictly content-bearing sequence (skipping `FUNCTION_STOPWORDS` when non-empty).
#[must_use]
pub fn content_sequence(seq: &[String]) -> Vec<String> {
    let filtered: Vec<String> = seq
        .iter()
        .filter(|t| !is_function_stopword(t.as_str()))
        .cloned()
        .collect();
    if filtered.is_empty() {
        seq.to_vec()
    } else {
        filtered
    }
}

/// Quantized `K=16` cyclic Fourier HRR 64-D phase fingerprint (`64 B`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Qfhrr64 {
    pub phases: [u8; 64],
}

impl Qfhrr64 {
    /// Bundle a token sequence (and adjacent pairs) onto 64 circular `K=16` phase bins.
    #[must_use]
    pub fn from_tokens(tokens: &[String]) -> Self {
        if tokens.is_empty() {
            return Self { phases: [0u8; 64] };
        }
        const TAU_OVER_16: f32 = std::f32::consts::TAU / 16.0;
        let mut cos_lut = [0.0f32; 16];
        let mut sin_lut = [0.0f32; 16];
        for k in 0..16 {
            let a = (k as f32) * TAU_OVER_16;
            cos_lut[k] = a.cos();
            sin_lut[k] = a.sin();
        }
        let mut re = [0.0f32; 64];
        let mut im = [0.0f32; 64];
        let mut accumulate = |seed: u64, w: f32| {
            let mut s = seed;
            for d in 0..16 {
                s = splitmix64(s);
                for sub in 0..4 {
                    let dim = d * 4 + sub;
                    let phase = ((s >> (sub * 16)) & 0x0F) as usize;
                    re[dim] += w * cos_lut[phase];
                    im[dim] += w * sin_lut[phase];
                }
            }
        };
        for tok in tokens.iter().take(128) {
            let w = if is_function_stopword(tok) { 0.15 } else { 1.0 };
            accumulate(fnv1a_64(tok.as_bytes()), w);
        }
        for pair in tokens.windows(2).take(128) {
            let h = fnv1a_64(pair[0].as_bytes()).rotate_left(13) ^ fnv1a_64(pair[1].as_bytes());
            accumulate(h, 0.85);
        }
        let mut phases = [0u8; 64];
        for d in 0..64 {
            let angle = im[d].atan2(re[d]).rem_euclid(std::f32::consts::TAU);
            phases[d] = (((angle / TAU_OVER_16).round() as usize) & 0x0F) as u8;
        }
        Self { phases }
    }

    /// Circular triangular similarity in `[0.0, 1.0]` (`1.0` identical, `~0.5` random).
    #[inline]
    #[must_use]
    pub fn triangular_sim(&self, other: &Self) -> f32 {
        let mut acc: i32 = 0;
        for d in 0..64 {
            let diff = other.phases[d].wrapping_sub(self.phases[d]) & 0x0F;
            let dist = if diff <= 8 { diff } else { 16 - diff };
            acc += i32::from(8 - dist);
        }
        (acc as f32) / 512.0
    }
}

/// Non-commutative block-diagonal Generalized Holographic Reduced Representation (`SO(4)^16`).
/// Uses 4 planar Givens rotations per `4x4` block so every generator is strictly `SO(4)` (`det = +1`).
#[derive(Debug, Clone)]
pub struct GhrrBlockSo4x16 {
    pub blocks: Box<[[f32; 16]; 16]>,
}

impl GhrrBlockSo4x16 {
    #[must_use]
    pub fn zeros() -> Self {
        Self {
            blocks: Box::new([[0.0f32; 16]; 16]),
        }
    }

    #[must_use]
    pub fn identity() -> Self {
        let mut blocks = Box::new([[0.0f32; 16]; 16]);
        for b in 0..16 {
            blocks[b][0] = 1.0;
            blocks[b][5] = 1.0;
            blocks[b][10] = 1.0;
            blocks[b][15] = 1.0;
        }
        Self { blocks }
    }

    /// Deterministically project `token` onto an exact `SO(4)^16` group element.
    #[must_use]
    pub fn from_seed(token: &str) -> Self {
        let mut out = Self::identity();
        let mut state = fnv1a_64(token.as_bytes());
        const PAIRS: [(usize, usize); 6] = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)];
        for b in 0..16 {
            let m = &mut out.blocks[b];
            for &(p, q) in &PAIRS {
                state = splitmix64(state);
                let u = ((state >> 32) as u32 as f32) / (u32::MAX as f32);
                let theta = (u * 2.0 - 1.0) * std::f32::consts::PI;
                let (s, c) = theta.sin_cos();
                for r in 0..4 {
                    let mp = m[r * 4 + p];
                    let mq = m[r * 4 + q];
                    m[r * 4 + p] = c * mp - s * mq;
                    m[r * 4 + q] = s * mp + c * mq;
                }
            }
        }
        out
    }

    /// Non-commutative blockwise `4x4` matrix product `self * rhs`.
    #[must_use]
    pub fn bind(&self, rhs: &Self) -> Self {
        let mut out = Self::zeros();
        for b in 0..16 {
            let a = &self.blocks[b];
            let r = &rhs.blocks[b];
            let o = &mut out.blocks[b];
            for i in 0..4 {
                for j in 0..4 {
                    o[i * 4 + j] = a[i * 4] * r[j]
                        + a[i * 4 + 1] * r[4 + j]
                        + a[i * 4 + 2] * r[8 + j]
                        + a[i * 4 + 3] * r[12 + j];
                }
            }
        }
        out
    }

    pub fn add_scaled(&mut self, rhs: &Self, weight: f32) {
        if !weight.is_finite() {
            return;
        }
        for b in 0..16 {
            for k in 0..16 {
                self.blocks[b][k] += weight * rhs.blocks[b][k];
            }
        }
    }

    /// Normalized Frobenius inner product in `[-1.0, 1.0]`.
    #[must_use]
    pub fn cosine_sim(&self, other: &Self) -> f32 {
        let mut dot = 0.0f32;
        let mut n1 = 0.0f32;
        let mut n2 = 0.0f32;
        for b in 0..16 {
            let a = &self.blocks[b];
            let c = &other.blocks[b];
            for k in 0..16 {
                dot += a[k] * c[k];
                n1 += a[k] * a[k];
                n2 += c[k] * c[k];
            }
        }
        let denom = (n1 * n2).sqrt();
        if denom > 1e-12 && dot.is_finite() {
            (dot / denom).clamp(-1.0, 1.0)
        } else {
            0.0
        }
    }

    /// Encode ordered bigrams `A * B` superposed over `tokens`.
    #[must_use]
    pub fn from_ordered_bigrams(tokens: &[String]) -> Option<Self> {
        if tokens.len() < 2 {
            return None;
        }
        let elems: Vec<Self> = tokens.iter().take(48).map(|t| Self::from_seed(t)).collect();
        let mut acc = Self::zeros();
        let norm = 1.0 / ((elems.len() - 1) as f32).sqrt();
        for i in 0..(elems.len() - 1) {
            let bound = elems[i].bind(&elems[i + 1]);
            acc.add_scaled(&bound, norm);
        }
        Some(acc)
    }

    /// Windowed non-commutative ordered similarity + exact ordered content-bigram overlap.
    /// Evaluates ordered chains ONLY around candidate token hits inside `doc_tokens` so long
    /// documents cannot dilute genuine short contiguous phrases.
    #[must_use]
    pub fn windowed_ordered_score(
        q_content: &[String],
        q_ghrr: Option<&Self>,
        doc_content: &[String],
    ) -> f32 {
        if q_content.len() < 2 || doc_content.len() < 2 {
            return 0.0;
        }
        let mut q_bigrams: HashSet<(&str, &str)> = HashSet::new();
        for w in q_content.windows(2) {
            q_bigrams.insert((w[0].as_str(), w[1].as_str()));
        }
        if q_bigrams.is_empty() {
            return 0.0;
        }
        let mut matched_bigrams = HashSet::new();
        for w in doc_content.windows(2) {
            let pair = (w[0].as_str(), w[1].as_str());
            if q_bigrams.contains(&pair) {
                matched_bigrams.insert(pair);
            }
        }
        let exact_bigram = (matched_bigrams.len() as f32) / (q_bigrams.len() as f32);

        let ghrr_sim = if let Some(qg) = q_ghrr {
            let q_set: HashSet<&str> = q_content.iter().map(String::as_str).collect();
            let mut relevant_indices = Vec::new();
            for (idx, tok) in doc_content.iter().enumerate() {
                if q_set.contains(tok.as_str()) {
                    relevant_indices.push(idx);
                }
            }
            if relevant_indices.is_empty() {
                0.0
            } else {
                let mut best = 0.0f32;
                let mut evaluated = 0usize;
                for idx in relevant_indices {
                    if idx + 1 < doc_content.len() {
                        let start = idx.saturating_sub(1);
                        let end = (idx + 3).min(doc_content.len());
                        if let Some(win_ghrr) = Self::from_ordered_bigrams(&doc_content[start..end])
                        {
                            let s = qg.cosine_sim(&win_ghrr).max(0.0);
                            if s > best {
                                best = s;
                            }
                        }
                        evaluated += 1;
                        if evaluated >= 16 {
                            break;
                        }
                    }
                }
                best
            }
        } else {
            0.0
        };

        (0.60 * exact_bigram + 0.40 * ghrr_sim).clamp(0.0, 1.0)
    }
}

/// Detect structured assistant-style responses (markdown lists, numbered sections,
/// polite helper preambles) purely from text structure.
#[must_use]
pub fn is_assistant_styled(text: &str) -> bool {
    let has_struct_header = text.contains("\n**1.")
        || text.contains("\n### ")
        || (text.contains("\n**")
            && (text.contains("\n* ") || text.contains("\n- ") || text.contains("\n\t+ ")));
    if text.len() >= 160
        && (text.contains("I'd be happy to")
            || text.contains("Here are some")
            || text.contains("Here's the updated")
            || has_struct_header)
    {
        return true;
    }
    if text.len() < 480 {
        return false;
    }
    text.contains("\n1. ")
        || text.contains("\n* ")
        || text.contains("\n- ")
        || text.contains("Certainly!")
}

#[inline]
fn normalize_quotes_lower(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        let mapped = match ch {
            '\u{2018}' | '\u{2019}' | '\u{02BC}' => '\'',
            _ => ch,
        };
        for lc in mapped.to_lowercase() {
            out.push(lc);
        }
    }
    out
}

/// Score first-person user ownership, habit, and preference declarations `[0.0, 1.0]`
/// on non-assistant-styled conversational turns.
#[must_use]
pub fn first_person_user_score(text: &str) -> f32 {
    if is_assistant_styled(text) {
        return 0.0;
    }
    let lower = normalize_quotes_lower(text);
    const CUES: &[(&str, f32)] = &[
        ("i'm ", 0.25),
        ("i am ", 0.25),
        ("i've ", 0.28),
        ("i have ", 0.22),
        ("my ", 0.25),
        ("i like", 0.38),
        ("i also like", 0.45),
        ("i love", 0.42),
        ("i'd love", 0.42),
        ("i enjoy", 0.45),
        ("i prefer", 0.48),
        ("i usually", 0.38),
        ("i always", 0.35),
        ("i want", 0.30),
        ("i'd like", 0.35),
        ("i bought", 0.32),
        ("i got", 0.28),
        ("i started", 0.30),
        ("i switched", 0.38),
        ("working in", 0.32),
        ("i'm looking", 0.38),
        ("i'm considering", 0.38),
        ("i'm thinking", 0.36),
        ("i'm trying", 0.36),
        ("i'm planning", 0.36),
        ("i've been", 0.38),
        ("i recently", 0.38),
        ("i replaced", 0.38),
        ("i like the idea", 0.45),
        ("i still remember", 0.40),
        ("as a ", 0.35),
        ("as an ", 0.35),
        ("i'm allergic", 0.50),
        ("allergic to", 0.42),
        ("intolerant", 0.42),
        ("i avoid ", 0.45),
        ("i don't eat", 0.48),
        ("i can't eat", 0.48),
        ("i hate ", 0.40),
        ("i dislike", 0.40),
        ("my favorite", 0.48),
    ];
    let mut score = 0.0_f32;
    for &(pat, w) in CUES {
        if lower.contains(pat) {
            score += w;
        }
    }
    score.clamp(0.0, 1.0)
}

/// True when a non-assistant conversational turn expresses a durable preference,
/// dietary/health constraint, ownership fact, or recurring personal habit.
/// Evaluates **declarative clauses** so multi-sentence user turns that declare a
/// preference before asking a follow-up question (`"I'm vegan. Any dinner ideas?"`)
/// are preserved while pure question-only turns remain excluded.
#[must_use]
pub fn has_preference_or_habit_declaration(text: &str) -> bool {
    if is_assistant_styled(text) {
        return false;
    }
    let pol = evaluate_preference_polarity(text);
    if !pol.has_decl_clause {
        return false;
    }
    if pol.e_pos >= 0.30 || pol.e_neg >= 0.30 || pol.implicit_pref_count > 0 {
        return true;
    }
    first_person_user_score(&pol.declarative_text) >= 0.42
}

/// Extract non-question declarative clauses from a conversational turn.
/// Splits on sentence boundaries (`.`, `!`, `?`, `\n`) and keeps clauses that do not
/// end with `?` and are not pure recommendation/request solicitations.
#[must_use]
pub fn extract_declarative_clauses(text: &str) -> String {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return String::new();
    }
    let mut clauses: Vec<&str> = Vec::new();
    let bytes = trimmed.as_bytes();
    let mut start = 0usize;
    let mut i = 0usize;
    while i < bytes.len() {
        let b = bytes[i];
        let is_break = b == b'\n'
            || ((b == b'.' || b == b'!' || b == b'?')
                && (i + 1 == bytes.len() || bytes[i + 1].is_ascii_whitespace()));
        if is_break {
            let end = if b == b'\n' { i } else { i + 1 };
            let seg = trimmed[start..end].trim();
            if !seg.is_empty() {
                clauses.push(seg);
            }
            start = i + 1;
        }
        i += 1;
    }
    if start < trimmed.len() {
        let tail = trimmed[start..].trim();
        if !tail.is_empty() {
            clauses.push(tail);
        }
    }

    const PURE_SOLICIT_PREFIXES: &[&str] = &[
        "can you ",
        "could you ",
        "would you ",
        "do you have ",
        "do you know ",
        "do you think ",
        "what are some ",
        "what should i ",
        "any tips",
        "any suggestions",
        "any recommendations",
        "any advice",
        "any ideas",
        "is there any ",
        "are there any ",
    ];

    let mut out = String::new();
    for seg in clauses {
        if seg.ends_with('?') {
            continue;
        }
        let low = normalize_quotes_lower(seg);
        if PURE_SOLICIT_PREFIXES.iter().any(|p| low.starts_with(p)) {
            continue;
        }
        if !out.is_empty() {
            out.push(' ');
        }
        out.push_str(seg);
    }
    out
}

/// `Catuṣkoṭi` `(E+, E-)` declarative preference polarity and `wave3_braid` implicit
/// facet profile for a single conversational turn.
#[derive(Debug, Clone, PartialEq)]
pub struct PreferencePolarity {
    /// Positive affinity / adoption / ownership / habit evidence `E+ in [0.0, 1.0]`.
    pub e_pos: f32,
    /// Negative aversion / allergy / avoidance / constraint evidence `E- in [0.0, 1.0]`.
    pub e_neg: f32,
    /// True when the turn contains at least one non-question declarative clause (`>= 12` chars).
    pub has_decl_clause: bool,
    /// True when the turn has no meaningful declarative clause (pure question/solicitation).
    pub pure_question: bool,
    /// Number of implicit preferences extracted by `wave3_braid::enrich_document_facets_at_index_time`.
    pub implicit_pref_count: usize,
    /// Extracted declarative clauses used for polarity and `qFHRR` topic-phase binding.
    pub declarative_text: String,
}

/// Evaluate `Catuṣkoṭi` (`EpistemicQuadruple (E+, E-)`) affinity/aversion polarity over
/// a turn's declarative clauses, augmented by `wave3_braid::enrich_document_facets_at_index_time`.
#[must_use]
pub fn evaluate_preference_polarity(text: &str) -> PreferencePolarity {
    if is_assistant_styled(text) {
        return PreferencePolarity {
            e_pos: 0.0,
            e_neg: 0.0,
            has_decl_clause: false,
            pure_question: false,
            implicit_pref_count: 0,
            declarative_text: String::new(),
        };
    }
    let decl = extract_declarative_clauses(text);
    let has_decl_clause = decl.len() >= 12;
    let trimmed = text.trim();
    let eval_slice = if has_decl_clause {
        decl.as_str()
    } else {
        trimmed
    };

    let lower = normalize_quotes_lower(eval_slice);
    let mut quad =
        crate::catuskoti::EpistemicQuadruple::new(crate::catuskoti::Context::new("episodic_pref"));

    const POS_CUES: &[(&str, f32)] = &[
        ("i prefer", 0.55),
        ("i love", 0.50),
        ("i enjoy", 0.50),
        ("i really like", 0.50),
        ("i like ", 0.40),
        ("i also like", 0.45),
        ("my favorite", 0.55),
        ("my favourite", 0.55),
        ("big fan of", 0.45),
        ("i usually", 0.38),
        ("i always", 0.36),
        ("i switched to", 0.45),
        ("i started ", 0.36),
        ("i've been into", 0.45),
        ("i've been using", 0.42),
        ("i'm using ", 0.38),
        ("i use ", 0.34),
        ("i own ", 0.36),
        ("i bought ", 0.36),
        ("i got a ", 0.32),
        ("i'm learning ", 0.38),
        ("trying to learn", 0.38),
        ("i'm working on", 0.36),
        ("i've been working on", 0.38),
        ("i'm vegan", 0.55),
        ("i'm vegetarian", 0.55),
        ("plant-based", 0.45),
        ("passionate about", 0.45),
        ("i'm into ", 0.40),
        ("i commute", 0.38),
        ("i live in", 0.34),
        ("my go-to", 0.48),
        ("i tend to", 0.36),
    ];
    const NEG_CUES: &[(&str, f32)] = &[
        ("i hate ", 0.50),
        ("i dislike", 0.48),
        ("i avoid ", 0.52),
        ("i don't like", 0.50),
        ("i don't eat", 0.55),
        ("i can't eat", 0.55),
        ("i don't drink", 0.50),
        ("i can't stand", 0.50),
        ("not a fan", 0.45),
        ("i'm allergic", 0.60),
        ("allergic to", 0.55),
        ("intolerant", 0.55),
        ("dairy-free", 0.52),
        ("gluten-free", 0.52),
        ("lactose", 0.45),
        ("i gave up ", 0.48),
        ("i cut out ", 0.48),
        ("i stopped ", 0.42),
        ("no longer ", 0.38),
        ("rather not", 0.40),
        ("not into ", 0.42),
        ("stay away from", 0.48),
        ("sensitive to", 0.45),
        ("struggle with", 0.38),
        ("too spicy", 0.42),
        ("too sweet", 0.42),
    ];

    for &(pat, w) in POS_CUES {
        if lower.contains(pat) {
            quad.add_positive(if has_decl_clause { w } else { w * 0.75 });
        }
    }
    for &(pat, w) in NEG_CUES {
        if lower.contains(pat) {
            quad.add_negative(if has_decl_clause { w } else { w * 0.75 });
        }
    }

    let enriched = crate::wave3_braid::enrich_document_facets_at_index_time(0, "", eval_slice, &[]);
    let implicit_pref_count = enriched.implicit_preferences.len();
    if implicit_pref_count > 0 {
        quad.add_positive(if has_decl_clause { 0.32 } else { 0.24 });
    }

    // A single-sentence question is only a contentless `pure_question` when it carries
    // neither explicit/implicit preference polarity nor concrete personal ownership context.
    let has_embedded_pref_in_q = !has_decl_clause
        && (quad.positive_evidence > 0.0
            || quad.negative_evidence > 0.0
            || implicit_pref_count > 0);
    let pure_question = !has_decl_clause && !has_embedded_pref_in_q && trimmed.ends_with('?');

    PreferencePolarity {
        e_pos: quad.positive_evidence,
        e_neg: quad.negative_evidence,
        has_decl_clause: has_decl_clause || has_embedded_pref_in_q,
        pure_question,
        implicit_pref_count,
        declarative_text: if has_decl_clause {
            decl
        } else if has_embedded_pref_in_q {
            trimmed.to_string()
        } else {
            String::new()
        },
    }
}

/// Extract the topical subject core of an open-ended preference/recommendation query by
/// stripping polite recommendation framing (`"can you recommend some tips for..."`) so
/// dense/static/holographic encoders match the *subject* rather than boilerplate framing.
#[must_use]
pub fn extract_open_preference_topic_core(query: &str) -> String {
    const PREF_FRAME_NOISE: &[&str] = &[
        "anything",
        "best",
        "complement",
        "find",
        "good",
        "great",
        "helpful",
        "interesting",
        "learn",
        "new",
        "resource",
        "resources",
        "something",
        "thing",
        "things",
        "way",
        "ways",
    ];
    let (_, _, seq) = content_terms_with_tf(query);
    let kept: Vec<&str> = seq
        .iter()
        .map(String::as_str)
        .filter(|tok| {
            tok.len() >= 3
                && !is_function_stopword(tok)
                && !is_chassis_word(tok)
                && PREF_FRAME_NOISE.binary_search(tok).is_err()
        })
        .collect();
    if kept.is_empty() {
        query.trim().to_string()
    } else {
        kept.join(" ")
    }
}

/// Deterministic 64-nibble `K=16` `qFHRR` role key representing `USER_PREF_ROLE`.
const USER_PREF_ROLE_NIBBLES: [u8; 64] = [
    3, 11, 7, 14, 1, 9, 5, 12, 15, 2, 10, 6, 13, 4, 8, 0, 6, 13, 2, 9, 14, 7, 11, 4, 1, 15, 8, 3,
    12, 5, 0, 10, 9, 4, 13, 1, 6, 15, 3, 10, 12, 7, 2, 14, 5, 11, 0, 8, 11, 6, 0, 12, 8, 3, 14, 5,
    10, 1, 15, 7, 4, 13, 9, 2,
];

/// Bind `text` with `USER_PREF_ROLE` using pure-Rust 32-byte `qfhrr_lut::qfhrr_bind_64d`
/// (`K=16` cyclic phase convolution) for zero-ONNX preference-topic alignment.
#[must_use]
pub fn pref_role_bound_qfhrr_signature(text: &str) -> crate::qfhrr_lut::QfhrrPacked32 {
    let base = crate::qfhrr_lut::qfhrr_text_signature_packed32(text);
    let mut unpacked = [0u8; 64];
    for i in 0..32 {
        unpacked[2 * i] = base.0[i] & 0x0F;
        unpacked[2 * i + 1] = (base.0[i] >> 4) & 0x0F;
    }
    let mut bound = [0u8; 64];
    crate::qfhrr_lut::qfhrr_bind_64d(&USER_PREF_ROLE_NIBBLES, &unpacked, &mut bound);
    crate::qfhrr_lut::QfhrrPacked32::from_nibbles(&bound)
}

/// True when the query explicitly asks what the assistant previously said/recommended/shared.
#[must_use]
pub fn is_assistant_recall_query(query: &str) -> bool {
    let q = normalize_quotes_lower(query);
    q.contains("you gave")
        || q.contains("you shared")
        || q.contains("you recommended")
        || q.contains("you mentioned")
        || q.contains("you suggested")
        || q.contains("you provided")
        || q.contains("you listed")
        || q.contains("you told")
        || q.contains("you advised")
        || q.contains("did you ")
        || q.contains("have you ")
        || q.contains("remind me of the")
        || q.contains("remind me what you")
        || q.contains("previous chat")
        || q.contains("previous conversation")
        || q.contains("our chat about")
        || q.contains("our last conversation")
        || q.contains("remind me of that")
        || q.contains("we talked about")
        || q.contains("you created")
        || q.contains("you wrote")
}

/// True when the query asks for a fresh open-ended recommendation, tip, or advice tailored
/// to the user's implicit preferences (and is not asking what the assistant previously said).
#[must_use]
pub fn is_open_preference_query(query: &str) -> bool {
    if is_assistant_recall_query(query) {
        return false;
    }
    let q = normalize_quotes_lower(query);
    q.contains("can you recommend")
        || q.contains("can you suggest")
        || q.contains("could you recommend")
        || q.contains("could you suggest")
        || q.contains("any recommendations")
        || q.contains("any suggestions")
        || q.contains("any tips")
        || q.contains("helpful tips")
        || q.contains("any advice")
        || q.contains("any ideas")
        || q.contains("what should i ")
        || q.contains("might find interesting")
        || q.contains("would complement")
        || q.contains("suggest a ")
        || q.contains("suggest some ")
        || q.contains("recommend a ")
        || q.contains("recommend some ")
        || q.contains("do you think it might be")
        || q.contains("do you think it would be")
        || q.contains("what do you think?")
}

pub(crate) fn floor_char_boundary_safe(s: &str, mut idx: usize) -> usize {
    idx = idx.min(s.len());
    while idx > 0 && !s.is_char_boundary(idx) {
        idx -= 1;
    }
    idx
}

fn ceil_char_boundary_safe(s: &str, mut idx: usize) -> usize {
    idx = idx.min(s.len());
    while idx < s.len() && !s.is_char_boundary(idx) {
        idx += 1;
    }
    idx
}

/// Extract a query-focused multi-window passage (`<= max_chars` bytes) so transformers
/// and ColBERT late-interaction spans neither waste CPU nor clip mid/tail evidence.
#[must_use]
pub fn extract_query_focused_snippet(query: &str, text: &str, max_chars: usize) -> String {
    if text.len() <= max_chars {
        return text.to_string();
    }
    let (_, _, q_raw) = content_terms_with_tf(query);
    let q_terms = content_sequence(&q_raw);
    let lower = text.to_lowercase();
    let max_win = if max_chars >= 768 { 4 } else { 3 };
    let head_len = floor_char_boundary_safe(text, max_chars / max_win);
    let win_len = max_chars / max_win;
    let mut out = String::with_capacity(max_chars + 32);
    out.push_str(&text[..head_len]);

    let mut windows: Vec<(usize, usize)> = vec![(0, head_len)];
    for term in q_terms.iter().filter(|t| t.len() >= 3) {
        if windows.len() >= max_win {
            break;
        }
        let pos_opt = if max_chars >= 768 {
            let stem = light_stem_english(term);
            lower.find(term.as_str()).or_else(|| {
                (stem.len() >= 3 && stem != *term)
                    .then(|| lower.find(stem.as_str()))
                    .flatten()
            })
        } else {
            lower.find(term.as_str())
        };
        if let Some(pos) = pos_opt {
            let start = floor_char_boundary_safe(text, pos.saturating_sub(win_len / 3));
            let end = ceil_char_boundary_safe(text, (start + win_len).min(text.len()));
            let overlaps = windows
                .iter()
                .any(|&(s, e)| start < e && end > s && (end.min(e) - start.max(s)) > win_len / 2);
            if !overlaps && end > start {
                windows.push((start, end));
                out.push_str(" ... ");
                out.push_str(&text[start..end]);
            }
        }
    }
    if windows.len() < (max_win - 1) {
        let tail_start = floor_char_boundary_safe(text, text.len().saturating_sub(win_len));
        if tail_start > head_len {
            out.push_str(" ... ");
            out.push_str(&text[tail_start..]);
        }
    }
    out
}

/// Score a bounded candidate pool with BM25 (TF saturation `k1=1.2`, doc-length normalization
/// `b=0.65`) + content-term query coverage + non-commutative `SO(4)^16` ordered phrase/bigram
/// score + `Qfhrr64` circular fingerprint + Stage 5A conversational role-intent alignment.
/// Returns `(record_id, score)` sorted descending.
pub fn rank_stage4a_lexical_pool<F>(
    query: &str,
    idf_lookup: F,
    docs: &[(u64, &str)],
) -> Vec<(u64, f32)>
where
    F: Fn(&str) -> f32,
{
    if docs.is_empty() {
        return Vec::new();
    }
    let (_, _, q_raw_seq) = content_terms_with_tf(query);
    let q_content_seq = content_sequence(&q_raw_seq);
    if q_content_seq.is_empty() {
        return docs.iter().map(|&(id, _)| (id, 0.0)).collect();
    }
    let open_pref_q = is_open_preference_query(query);
    let asst_recall_q = is_assistant_recall_query(query);

    // Deduplicate query terms while down-weighting stopwords (0.12) & chassis words (0.24).
    const PREF_FRAME_WORDS: &[&str] = &[
        "anything",
        "best",
        "complement",
        "find",
        "good",
        "great",
        "helpful",
        "interesting",
        "learn",
        "new",
        "resource",
        "resources",
        "something",
        "thing",
        "things",
        "way",
        "ways",
    ];
    let mut q_terms: Vec<(String, String, f32)> = Vec::new();
    let mut seen = HashSet::new();
    for tok in &q_raw_seq {
        if seen.insert(tok.clone()) {
            let base_idf = idf_lookup(tok).max(0.1);
            let w = if is_function_stopword(tok) {
                base_idf * 0.12
            } else if is_chassis_word(tok) {
                base_idf * 0.24
            } else if open_pref_q && PREF_FRAME_WORDS.binary_search(&tok.as_str()).is_ok() {
                base_idf * 0.18
            } else {
                base_idf
            };
            q_terms.push((tok.clone(), light_stem_english(tok), w));
        }
    }
    let total_w: f32 = q_terms.iter().map(|(_, _, w)| *w).sum::<f32>().max(1e-6);

    let q_ghrr = GhrrBlockSo4x16::from_ordered_bigrams(&q_content_seq);
    let q_qfhrr = Qfhrr64::from_tokens(&q_content_seq);

    type ParsedDoc = (
        u64,
        usize,
        HashMap<String, usize>,
        HashSet<String>,
        Vec<String>,
    );
    let parsed: Vec<ParsedDoc> = docs
        .iter()
        .map(|&(id, text)| {
            let (dl, tf, seq) = content_terms_with_tf(text);
            let stems: HashSet<String> = tf.keys().map(|t| light_stem_english(t)).collect();
            (id, dl.max(1), tf, stems, seq)
        })
        .collect();
    let mean_dl = parsed
        .iter()
        .map(|(_, dl, _, _, _)| *dl as f32)
        .sum::<f32>()
        / (parsed.len() as f32);
    let mut sorted_dls: Vec<f32> = parsed.iter().map(|(_, dl, _, _, _)| *dl as f32).collect();
    sorted_dls.sort_by(f32::total_cmp);
    let median_dl = sorted_dls[sorted_dls.len() / 2];
    let avgdl = (0.5 * mean_dl + 0.5 * median_dl).clamp(32.0, 72.0);

    const K1: f32 = 0.50;
    const B: f32 = 0.85;

    struct RawEntry {
        id: u64,
        bm25_raw: f32,
        cov: f32,
        ghrr_ordered: f32,
        qfhrr_sim: f32,
        role_mult: f32,
    }
    let mut raw_entries: Vec<RawEntry> = Vec::with_capacity(parsed.len());
    let mut max_bm25 = 1e-6_f32;
    for (idx, (id, dl, tf, d_stems, d_seq)) in parsed.iter().enumerate() {
        let doc_text = docs[idx].1;
        let asst = is_assistant_styled(doc_text);
        let fp_user = first_person_user_score(doc_text);
        let role_mult = if open_pref_q {
            if asst {
                0.82
            } else {
                let pol = evaluate_preference_polarity(doc_text);
                if pol.pure_question {
                    0.88
                } else {
                    let stance = (pol.e_pos + pol.e_neg).min(1.0);
                    1.0 + 0.16 * fp_user + 0.12 * stance
                }
            }
        } else if asst_recall_q {
            if asst { 1.10 } else { 1.0 }
        } else if !asst && fp_user >= 0.35 {
            1.05
        } else if asst && doc_text.len() > 1400 {
            0.94
        } else {
            1.0
        };
        let dl_ratio = ((*dl as f32) / avgdl).max(1.0);
        let len_norm = 1.0 - B + B * dl_ratio;
        let stuff_cap = crate::adversarial_guard::stuffing_cap_from_tf_counts(tf);
        let mut bm25_raw = 0.0f32;
        let mut matched_w = 0.0f32;
        for (term, stem, qw) in &q_terms {
            let raw_tf = tf.get(term).copied().unwrap_or(0);
            let mut c = if raw_tf > 0 {
                crate::adversarial_guard::dampen_stuffed_tf(raw_tf, stuff_cap)
            } else {
                0.0
            };
            let mut eff_qw = *qw;
            if c == 0.0 && stem != term && d_stems.contains(stem.as_str()) {
                c = 1.0;
                eff_qw *= 0.58;
            }
            if c > 0.0 {
                matched_w += eff_qw;
                bm25_raw += eff_qw * (c * (K1 + 1.0)) / (c + K1 * len_norm);
            }
        }
        if bm25_raw > max_bm25 {
            max_bm25 = bm25_raw;
        }
        let cov = (matched_w / total_w).clamp(0.0, 1.0);
        let d_content_seq = content_sequence(d_seq);
        let ghrr_ordered = GhrrBlockSo4x16::windowed_ordered_score(
            &q_content_seq,
            q_ghrr.as_ref(),
            &d_content_seq,
        );
        let qfhrr_sim = ((q_qfhrr.triangular_sim(&Qfhrr64::from_tokens(&d_content_seq)) - 0.50)
            * 2.0)
            .clamp(0.0, 1.0);
        raw_entries.push(RawEntry {
            id: *id,
            bm25_raw,
            cov,
            ghrr_ordered,
            qfhrr_sim,
            role_mult,
        });
    }

    let sat_k = (total_w * 0.5).max(1.5);
    let mut out: Vec<(u64, f32)> = raw_entries
        .into_iter()
        .map(|e| {
            let bm25_rel = (e.bm25_raw / max_bm25).clamp(0.0, 1.0);
            let bm25_sat = (e.bm25_raw / (e.bm25_raw + sat_k)).clamp(0.0, 1.0);
            let bm25_norm = 0.65 * bm25_rel + 0.35 * bm25_sat;
            let combined =
                ((0.50 * bm25_norm + 0.22 * e.cov + 0.20 * e.ghrr_ordered + 0.08 * e.qfhrr_sim)
                    * e.role_mult)
                    .clamp(0.0, 1.0);
            (e.id, combined)
        })
        .collect();
    out.sort_by(|a, b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ghrr_so4x16_is_non_commutative_and_qfhrr_tracks_overlap() {
        let a = GhrrBlockSo4x16::from_seed("daily");
        let b = GhrrBlockSo4x16::from_seed("commute");
        let ab = a.bind(&b);
        let ba = b.bind(&a);
        assert!(
            ab.cosine_sim(&ba) < 0.35,
            "SO(4)^16 binding must distinguish A*B from B*A (sim={})",
            ab.cosine_sim(&ba)
        );
        assert!((ab.cosine_sim(&ab) - 1.0).abs() < 1e-4);

        let q = vec!["daily".into(), "commute".into(), "work".into()];
        let qg = GhrrBlockSo4x16::from_ordered_bigrams(&q);
        let good = vec![
            "listening".into(),
            "audiobooks".into(),
            "daily".into(),
            "commute".into(),
            "minutes".into(),
        ];
        let scrambled = vec![
            "commute".into(),
            "eisenhower".into(),
            "matrix".into(),
            "daily".into(),
            "tasks".into(),
        ];
        let s_good = GhrrBlockSo4x16::windowed_ordered_score(&q, qg.as_ref(), &good);
        let s_bad = GhrrBlockSo4x16::windowed_ordered_score(&q, qg.as_ref(), &scrambled);
        assert!(
            s_good > s_bad * 2.0,
            "ordered phrase should decisively beat scrambled words ({s_good} vs {s_bad})"
        );

        let qf = Qfhrr64::from_tokens(&q);
        let gf = Qfhrr64::from_tokens(&good);
        assert!(qf.triangular_sim(&gf) > 0.55);

        let zwsp = "hi\u{200B}\u{FEFF}!".to_string();
        assert_eq!(canonicalize_for_noise_check(&zwsp), "hi!");
        assert_eq!(canonicalize_for_noise_check("Еrror: spoof"), "Error: spoof");

        // Verify Stage 4A pool ranking breaks verbose distractor inversion on "daily commute"
        let query = "How long is my daily commute to work?";
        let needle = "I've been listening to audiobooks during my daily commute to work, which takes 45 minutes each way.";
        let verbose_distractor = "I like the Eisenhower Matrix, it's a helpful tool for managing daily tasks and weekly meetings. Planning my project roadmap carefully helps balance office work, long deliverables, and commute logistics across the whole quarter without burning out.";
        let assistant_echo = "Congratulations on your daily commute routine and audiobooks! Let me share 10 detailed long productivity templates, time-blocking worksheets, morning checklists, evening reflection prompts, habit trackers, priority matrices, meeting agendas, and weekly planning guides so your daily commute feels organized and calm throughout the entire year.";
        let docs = [
            (886, verbose_distractor),
            (637, assistant_echo),
            (636, needle),
        ];
        let ranked = rank_stage4a_lexical_pool(
            query,
            |tok| match tok {
                "commute" => 4.2,
                "daily" => 3.5,
                "work" | "long" => 1.5,
                _ => 0.4,
            },
            &docs,
        );
        assert_eq!(
            ranked[0].0, 636,
            "concise needle with ordered bigram must rank #1, got {ranked:?}"
        );
    }

    #[test]
    fn preference_habit_and_curly_quote_detection() {
        assert!(has_preference_or_habit_declaration(
            "I\u{2019}m allergic to cow dairy so I always use roasted oat milk."
        ));
        assert!(
            has_preference_or_habit_declaration(
                "I\u{2019}ve been learning Adobe Premiere Pro and prefer advanced settings. Can you suggest tutorials?"
            ),
            "multi-sentence preference declaration followed by a question must preserve has_decl"
        );
        assert!(!has_preference_or_habit_declaration(
            "Can anyone recommend a cozy coffee shop near downtown?"
        ));
        assert!(first_person_user_score("I\u{2019}ve been into film photography lately.") >= 0.35);
        assert!(is_open_preference_query(
            "I\u{2019}m a bit anxious about transit. Do you have any helpful tips?"
        ));
        assert!(!is_open_preference_query(
            "What recipes did you recommend last Tuesday?"
        ));

        let pol_neg = evaluate_preference_polarity(
            "I\u{2019}m allergic to shellfish and avoid spicy sauces. Any dinner ideas?",
        );
        assert!(pol_neg.has_decl_clause && !pol_neg.pure_question);
        assert!(pol_neg.e_neg >= 0.50);

        let pol_q = evaluate_preference_polarity("Can you recommend some dinner restaurants?");
        assert!(pol_q.pure_question && !pol_q.has_decl_clause);

        let core = extract_open_preference_topic_core(
            "Can you recommend some good resources where I can learn more about video editing?",
        );
        assert!(core.contains("video") && core.contains("editing"));
        assert!(!core.contains("recommend"));

        let q_sig = pref_role_bound_qfhrr_signature(&core);
        let d_match = pref_role_bound_qfhrr_signature(
            "I've been using Adobe Premiere Pro for video editing lately.",
        );
        let d_other = pref_role_bound_qfhrr_signature(
            "I prefer hiking mountain trails with lightweight boots.",
        );
        assert!(
            q_sig.similarity(&d_match) > q_sig.similarity(&d_other),
            "role-bound qFHRR signature must align topic-matched preference above unrelated turn"
        );
    }
}
