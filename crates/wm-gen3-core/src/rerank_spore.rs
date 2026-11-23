//! `WM7D` Binary Reranker Spore — Quantized `ColBERT MaxSim` + Cross-Turn Context Scorer.
//!
//! Loads compact `<5 MB` `WM7D\x01` spores trained out-of-sample on Colab `L4` and executes
//! pure safe-Rust BERT WordPiece tokenization, residual depthwise-conv token mixing,
//! IDF-gated `ColBERT MaxSim` late interaction, and 24-feature query-conditioned bilinear
//! cross-turn reranking in sub-2ms on CPU.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::Arc;

use crate::ghrr_algebra;

pub const WM7D_MAGIC: &[u8; 8] = b"WM7D\x02\x00\x00\x00";
pub const WM7D_V3_MAGIC: &[u8; 8] = b"WM7D\x03\x00\x00\x00";
pub const WM7D_V4_MAGIC: &[u8; 8] = b"WM7D\x04\x00\x00\x00";

const STOPWORDS: &[&str] = &[
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "she",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
    "would",
    "could",
    "should",
    "can",
    "did",
    "do",
    "does",
    "me",
    "my",
    "you",
    "your",
    "i",
    "im",
    "ive",
    "id",
    "ill",
    "how",
    "many",
    "much",
    "what",
    "where",
    "when",
    "who",
    "which",
    "why",
    "please",
    "remind",
    "tell",
    "help",
    "looking",
    "thinking",
    "planning",
    "wondering",
    "just",
    "really",
    "very",
    "some",
    "any",
    "something",
    "anything",
    "recommend",
    "recommended",
    "suggest",
    "suggested",
    "suggestions",
    "ideas",
    "tips",
    "advice",
    "about",
    "going",
    "back",
];

const META_CLARIFY_PHRASES: &[&str] = &[
    "need a bit more information",
    "could you please tell me",
    "didn't mention which",
    "did not mention which",
    "could you clarify",
    "could you provide more",
    "what kind of",
    "let me know which",
    "as an ai language model",
    "do not have the ability to",
    "don't have access to",
    "happy to help! however",
    "be more specific",
];

const MONTH_WORDS: &[&str] = &[
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "yesterday",
    "today",
    "ago",
    "last week",
    "last month",
    "valentine",
    "christmas",
    "thanksgiving",
    "halloween",
    "easter",
];

const DURATION_UNITS: &[&str] = &[
    "hour", "hours", "hr", "hrs", "minute", "minutes", "min", "mins", "second", "seconds", "sec",
    "secs", "day", "days", "week", "weeks", "month", "months", "year", "years", "decade",
    "decades",
];

const NUM_WORDS: &[&str] = &[
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "fifteen", "dozen", "twenty", "thirty", "forty", "fifty", "half",
    "hundred",
];

#[inline]
fn fnv1a_64(bytes: &[u8]) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for &b in bytes {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0100_0000_01b3);
    }
    h
}

#[inline]
fn is_stopword(s: &str) -> bool {
    STOPWORDS.contains(&s)
}

#[inline]
fn sigmoid_f32(x: f32) -> f32 {
    if x >= 0.0 {
        1.0 / (1.0 + (-x).exp())
    } else {
        let ex = x.exp();
        ex / (1.0 + ex)
    }
}

#[inline]
fn silu_f32(x: f32) -> f32 {
    x * sigmoid_f32(x)
}

#[inline]
fn is_bert_punctuation(ch: char) -> bool {
    let cp = ch as u32;
    (33..=47).contains(&cp)
        || (58..=64).contains(&cp)
        || (91..=96).contains(&cp)
        || (123..=126).contains(&cp)
        || !ch.is_alphanumeric() && !ch.is_whitespace()
}

#[inline]
fn is_cjk(ch: char) -> bool {
    let cp = ch as u32;
    (0x4E00..=0x9FFF).contains(&cp)
        || (0x3400..=0x4DBF).contains(&cp)
        || (0x20000..=0x2A6DF).contains(&cp)
        || (0x2A700..=0x2B73F).contains(&cp)
        || (0x2B740..=0x2B81F).contains(&cp)
        || (0x2B820..=0x2CEAF).contains(&cp)
        || (0xF900..=0xFAFF).contains(&cp)
        || (0x2F800..=0x2FA1F).contains(&cp)
}

fn is_meta_clarification(text: &str) -> bool {
    let low = text.to_lowercase();
    META_CLARIFY_PHRASES.iter().any(|p| low.contains(p))
}

fn is_question_turn_score(text: &str) -> f32 {
    let s = text.trim();
    if s.is_empty() {
        return 0.0;
    }
    if s.ends_with('?') {
        return 1.0;
    }
    let tail_start = s.len().saturating_sub(100);
    let mut idx = tail_start;
    while idx < s.len() && !s.is_char_boundary(idx) {
        idx += 1;
    }
    if s[idx..].contains('?') { 0.5 } else { 0.0 }
}

#[derive(Debug, Clone, Copy, Default)]
pub struct FactProfile {
    pub density: f32,
    pub has_dollar: bool,
    pub has_digit: bool,
    pub has_num_word: bool,
    pub has_month_or_date: bool,
    pub proper_noun_count: u8,
    pub has_explicit_duration: bool,
    pub has_role_or_venue_prep: bool,
}

fn profile_facts(text: &str) -> FactProfile {
    if text.is_empty() {
        return FactProfile::default();
    }
    let low = text.to_lowercase();
    let words: Vec<&str> = low
        .split(|c: char| !c.is_ascii_alphanumeric())
        .filter(|w| !w.is_empty())
        .collect();
    let n = words.len().max(1);
    let dollar_cnt = text.bytes().filter(|&b| b == b'$').count();
    let digit_cnt = words
        .iter()
        .filter(|w| w.bytes().any(|b| b.is_ascii_digit()))
        .count();
    let num_word_cnt = words.iter().filter(|w| NUM_WORDS.contains(w)).count();
    let month_cnt = MONTH_WORDS
        .iter()
        .filter(|&&m| {
            if m == "may" {
                text.split_whitespace()
                    .any(|w| w.trim_matches(|c: char| !c.is_ascii_alphabetic()) == "May")
            } else if m.contains(' ') {
                low.contains(m)
            } else {
                words.contains(&m)
            }
        })
        .count();
    let has_explicit_duration = words.windows(2).any(|w| {
        let is_qty = w[0].bytes().all(|b| b.is_ascii_digit()) || NUM_WORDS.contains(&w[0]);
        is_qty && DURATION_UNITS.contains(&w[1])
    });
    let has_role_or_venue_prep = [
        "as a ",
        "as an ",
        "worked at ",
        "graduated from ",
        "at the ",
        "in the ",
        "went to ",
        "member of ",
        "enrolled at ",
        "from ",
        "bought at ",
        "staying at ",
        "stayed at ",
    ]
    .iter()
    .any(|p| low.contains(p));

    let mut proper_cnt = 0usize;
    let raw_toks: Vec<&str> = text.split_whitespace().collect();
    for (i, tok) in raw_toks.iter().enumerate() {
        let clean = tok.trim_matches(|c: char| ".,!?;:\"'()[]{}".contains(c));
        if matches!(
            clean,
            "I" | "I'm"
                | "I've"
                | "I'll"
                | "I'd"
                | "I’m"
                | "I’ve"
                | "I’ll"
                | "I’d"
                | "It's"
                | "That's"
                | "There's"
                | "Here's"
                | "What's"
                | "Let's"
        ) {
            continue;
        }
        let mut chars = clean.chars();
        let all_upper = clean.len() >= 2
            && clean.len() <= 6
            && clean.chars().all(|c| c.is_ascii_uppercase())
            && !matches!(
                clean,
                "AI" | "TV"
                    | "PC"
                    | "ID"
                    | "OK"
                    | "AM"
                    | "PM"
                    | "DIY"
                    | "FAQ"
                    | "PDF"
                    | "URL"
                    | "API"
                    | "RAM"
                    | "CPU"
                    | "GPU"
                    | "USB"
                    | "GPS"
            );
        if let Some(first) = chars.next()
            && i > 0
            && clean.len() >= 2
            && first.is_uppercase()
            && (all_upper || !clean.chars().all(|c| c.is_uppercase()))
            && (all_upper || !raw_toks[i - 1].ends_with(['.', '!', '?', ':']))
        {
            proper_cnt += 1;
        }
    }
    let hits = 2.0 * (dollar_cnt as f32)
        + 1.5 * (digit_cnt as f32)
        + 1.2 * (num_word_cnt as f32)
        + 1.3 * (month_cnt as f32)
        + 0.9 * (proper_cnt as f32);

    FactProfile {
        density: (hits / ((n as f32).sqrt() * 1.4).max(4.0)).clamp(0.0, 1.0),
        has_dollar: dollar_cnt > 0,
        has_digit: digit_cnt > 0,
        has_num_word: num_word_cnt > 0,
        has_month_or_date: month_cnt > 0,
        proper_noun_count: proper_cnt.min(255) as u8,
        has_explicit_duration,
        has_role_or_venue_prep,
    }
}

const PAST_FACT_PREFIX_CUES: &[&str] = &[
    "i graduated",
    "i bought",
    "i got",
    "i went",
    "i worked",
    "i lived",
    "i visited",
    "i attended",
    "i paid",
    "i spent",
    "i adopted",
    "i started",
    "i moved",
    "i completed",
    "i finished",
    "i received",
    "i loved",
    "i took",
    "i earned",
    "i won",
    "i built",
    "i painted",
    "i rescued",
];

fn has_declarative_fact_prefix(s: &str, facts: &FactProfile) -> bool {
    let Some(q_pos) = s.rfind('?') else {
        return false;
    };
    if q_pos == 0 {
        return false;
    }
    let head = &s[..q_pos];
    let sep_opt = [head.rfind(". "), head.rfind("! "), head.rfind('\n')]
        .into_iter()
        .flatten()
        .max();
    let Some(sep) = sep_opt else {
        return false;
    };
    if sep < 25 {
        return false;
    }
    let prefix = head[..=sep].trim();
    if prefix.len() < 30 {
        return false;
    }
    let plow = prefix.to_lowercase();
    if PAST_FACT_PREFIX_CUES.iter().any(|c| plow.contains(c)) {
        return true;
    }
    let is_planning_setup = plow.starts_with("i'm trying to ")
        || plow.starts_with("i'm thinking of ")
        || plow.starts_with("i'm considering ")
        || plow.starts_with("i'm looking for ")
        || plow.starts_with("i'm planning ")
        || plow.starts_with("i'm torn ")
        || plow.starts_with("i need to ")
        || plow.starts_with("i need some help");
    if is_planning_setup
        && !facts.has_dollar
        && !facts.has_digit
        && !facts.has_num_word
        && !facts.has_explicit_duration
    {
        return false;
    }
    ghrr_algebra::first_person_user_score(prefix) >= 0.25 && facts.proper_noun_count >= 1
}

fn has_inline_past_fact(s: &str, facts: &FactProfile) -> bool {
    let low = s.to_lowercase();
    (low.contains("considering i ")
        || low.contains("since i ")
        || low.contains("because i ")
        || low.contains("i used to "))
        && (facts.density >= 0.14 || facts.proper_noun_count >= 1 || low.contains("competitively"))
}

fn has_unanswered_q_trap(
    text: &str,
    facts: &FactProfile,
    is_asst_q: bool,
    is_open_pref: bool,
) -> f32 {
    if is_open_pref {
        return 0.0;
    }
    let s = text.trim();
    if s.is_empty() {
        return 0.0;
    }
    let tail_q = s.ends_with('?') || is_question_turn_score(s) >= 0.5;
    if !tail_q {
        return 0.0;
    }
    if is_asst_q {
        return if s.len() < 320 && !facts.has_digit && facts.proper_noun_count <= 1 {
            1.0
        } else {
            0.0
        };
    }
    if has_declarative_fact_prefix(s, facts) || has_inline_past_fact(s, facts) {
        return 0.0;
    }
    let has_concrete = facts.has_dollar
        || facts.has_digit
        || facts.has_num_word
        || facts.has_explicit_duration
        || facts.has_month_or_date;
    if s.ends_with('?') && !has_concrete {
        1.0
    } else if !has_concrete && facts.proper_noun_count == 0 {
        0.4
    } else {
        0.0
    }
}

fn compute_q_atype_match(
    query: &str,
    facts: &FactProfile,
    is_asst_q: bool,
    is_open_pref: bool,
    q_trap: f32,
) -> f32 {
    if is_asst_q || is_open_pref {
        return 0.0;
    }
    let ql = query.to_lowercase();
    let mut sc = 0.0_f32;
    if ql.contains("how much")
        || ql.contains("cost")
        || ql.contains("price")
        || ql.contains("spend")
        || ql.contains("spent")
        || ql.contains("paid")
        || ql.contains("pay ")
    {
        if facts.has_dollar {
            sc += 0.85;
        } else if facts.has_digit {
            sc += 0.35;
        } else if q_trap > 0.5 {
            sc -= 0.60;
        }
    } else if ql.contains("how long") || ql.contains("duration") || ql.contains("took") {
        if facts.has_explicit_duration {
            sc += 0.90;
        } else if facts.has_digit || facts.has_num_word {
            sc += 0.30;
        } else if q_trap > 0.5 {
            sc -= 0.60;
        }
    } else if ql.contains("how many")
        || ql.contains("times have")
        || ql.contains("number of")
        || ql.contains("how often")
        || ql.contains("total ")
    {
        if (facts.has_digit && !facts.has_dollar) || facts.has_num_word {
            sc += 0.55;
        } else if q_trap > 0.5 {
            sc -= 0.50;
        }
    } else if ql.starts_with("when ")
        || ql.contains(" when ")
        || ql.contains("what date")
        || ql.contains("which date")
        || ql.contains("months ago")
        || ql.contains("weeks ago")
        || ql.contains("days ago")
    {
        if facts.has_month_or_date {
            sc += 0.70;
        } else if facts.has_explicit_duration || facts.has_digit {
            sc += 0.35;
        } else if q_trap > 0.5 {
            sc -= 0.50;
        }
    } else if ql.starts_with("where ")
        || ql.contains(" where ")
        || ql.contains("which city")
        || ql.contains("which state")
        || ql.contains("which country")
        || ql.contains("which university")
        || ql.contains("which college")
        || ql.contains("occupation")
        || ql.contains("job")
        || ql.contains("role")
    {
        if facts.has_role_or_venue_prep && facts.proper_noun_count >= 1 {
            sc += 0.75;
        } else if facts.proper_noun_count >= 1 {
            sc += 0.40;
        }
    }
    sc.clamp(-1.0, 1.0)
}

/// Deterministic `head + tail` truncation used at bi-encoder doc ingest (`<= 680` chars)
/// matching `stage7d_rerank_v3_colab_l4.py` cleanly without query leakage.
#[must_use]
pub fn head_tail_snippet(text: &str, max_chars: usize) -> String {
    if text.len() <= max_chars {
        return text.to_string();
    }
    let mut head_len = (max_chars * 5) / 8;
    while head_len > 0 && !text.is_char_boundary(head_len) {
        head_len -= 1;
    }
    let target_tail = max_chars.saturating_sub(head_len + 5);
    let mut tail_start = text.len().saturating_sub(target_tail);
    while tail_start < text.len() && !text.is_char_boundary(tail_start) {
        tail_start += 1;
    }
    if tail_start <= head_len {
        return text.to_string();
    }
    format!("{} ... {}", &text[..head_len], &text[tail_start..])
}

/// Detailed `WM7D` ColBERT MaxSim + speaker/provenance features extracted for banded tie-breaking.
#[derive(Debug, Clone, Copy)]
pub struct RerankCandidateFeatures {
    pub raw_logit: f32,
    pub pref_logit: f32,
    pub topic_core_bi_cos: f32,
    pub maxsim_weighted: f32,
    pub maxsim_high_idf: f32,
    pub maxsim_min_c: f32,
    pub tag_asst: f32,
    pub tag_user: f32,
    pub is_asst_styled: bool,
    pub is_question_turn: f32,
    pub is_meta_clarify: bool,
    pub first_person_u: f32,
    pub recency_norm: f32,
    pub facts: FactProfile,
    pub unanswered_q_trap: f32,
    pub quotes_user_entity: bool,
}

/// Candidate metadata & raw fields supplied from `Substrate::recall` to `WM7D`.
pub struct RerankCandidateInput<'a> {
    pub record_id: u64,
    pub content: &'a str,
    pub source: &'a str,
    pub lex_support: f32,
    pub sem_support: f32,
    pub hybrid_support: f32,
    pub pre_rank: usize,
    pub recency_norm: f32,
    pub superseded: bool,
    pub temporal_hit: bool,
    pub prev_turn_lex: f32,
    pub prev_turn_is_user_question: bool,
    pub next_turn_lex: f32,
    pub next_turn_is_asst: bool,
    pub session_coref_lex: f32,
    pub fast_bi_cos: f32,
    pub sess_density_norm: f32,
}

/// Reusable scratch buffers for allocation-free batch WordPiece + bi-encoder doc embedding.
#[derive(Debug, Default)]
pub struct BiEncoderScratch {
    pre_buf: String,
    ranges: Vec<(usize, usize)>,
    wp_buf: String,
    byte_indices: Vec<usize>,
    sub_tokens: Vec<u32>,
    ids: Vec<u32>,
    x_buf: Vec<f32>,
    h_buf: Vec<f32>,
    conv_buf: Vec<f32>,
    mid_buf: Vec<f32>,
    v_pool: Vec<f32>,
}

/// Zero-heap-per-token open-addressed WordPiece lookup + quantized `WM7D\x02` / `WM7D\x03` inference engine.
#[derive(Debug, Clone)]
pub struct Wm7dRerankSpore {
    version: u8,
    vocab_size: usize,
    emb_dim: usize,
    bottleneck_dim: usize,
    _conv_kernel: usize,
    meta_dim: usize,
    mlp_hidden: usize,
    max_q_tokens: usize,
    max_d_tokens: usize,
    vocab_blob: Vec<u8>,
    tok_spans: Vec<(u32, u32)>,
    hash_table: Vec<u32>,
    unk_id: u32,
    emb_i8: Vec<i8>,
    emb_scales: Vec<f32>,
    q_dw_conv: Vec<f32>,
    q_u_down: Vec<f32>,
    q_u_up_t: Vec<f32>,
    d_dw_conv: Vec<f32>,
    d_u_down: Vec<f32>,
    d_u_up_t: Vec<f32>,
    q_gate_w: Vec<f32>,
    q_gate_b: f32,
    anchor_w: f32,
    meta_mean: Vec<f32>,
    meta_inv_std: Vec<f32>,
    w_linear: Vec<f32>,
    w_f: Vec<f32>,
    w_qf: Vec<f32>,
    b_f: Vec<f32>,
    w_out: Vec<f32>,
    b_out: f32,
    bi_q_gate_w: Vec<f32>,
    bi_d_gate_w: Vec<f32>,
    bi_proj_q: Vec<f32>,
    bi_proj_d: Vec<f32>,
    pref_hidden: usize,
    pref_w_linear: Vec<f32>,
    pref_w_f: Vec<f32>,
    pref_w_qf: Vec<f32>,
    pref_b_f: Vec<f32>,
    pref_w_out: Vec<f32>,
    pref_b_out: f32,
}

fn transpose_2d(src: &[f32], rows: usize, cols: usize) -> Vec<f32> {
    let mut out = vec![0.0_f32; rows * cols];
    for r in 0..rows {
        for c in 0..cols {
            out[c * rows + r] = src[r * cols + c];
        }
    }
    out
}

#[inline]
fn dot_fast(a: &[f32], b: &[f32]) -> f32 {
    let mut s0 = 0.0_f32;
    let mut s1 = 0.0_f32;
    let mut s2 = 0.0_f32;
    let mut s3 = 0.0_f32;
    for (ca, cb) in a.chunks_exact(4).zip(b.chunks_exact(4)) {
        s0 += ca[0] * cb[0];
        s1 += ca[1] * cb[1];
        s2 += ca[2] * cb[2];
        s3 += ca[3] * cb[3];
    }
    let rem = a.len() & !3;
    let mut tail = 0.0_f32;
    for (&x, &y) in a[rem..].iter().zip(b[rem..].iter()) {
        tail += x * y;
    }
    (s0 + s1) + (s2 + s3) + tail
}

impl Wm7dRerankSpore {
    /// Load a binary `WM7D\x02` spore from disk in ~1-2ms using flat open-addressed hashing.
    pub fn load_from_path(path: &Path) -> Result<Self, String> {
        let bytes = fs::read(path)
            .map_err(|e| format!("failed to read WM7D spore {}: {e}", path.display()))?;
        Self::from_bytes(&bytes)
    }

    pub fn from_bytes(bytes: &[u8]) -> Result<Self, String> {
        if bytes.len() < 44 {
            return Err("truncated WM7D spore".into());
        }
        let version: u8 = if &bytes[0..8] == WM7D_MAGIC {
            2
        } else if &bytes[0..8] == WM7D_V3_MAGIC {
            3
        } else if &bytes[0..8] == WM7D_V4_MAGIC {
            4
        } else {
            return Err("invalid WM7D v2/v3/v4 magic header".into());
        };
        let read_u32 = |off: usize| -> Result<usize, String> {
            let s: [u8; 4] = bytes
                .get(off..off + 4)
                .ok_or_else(|| "truncated WM7D header".to_string())?
                .try_into()
                .map_err(|_| "slice mismatch".to_string())?;
            Ok(u32::from_le_bytes(s) as usize)
        };
        let vocab_size = read_u32(8)?;
        let emb_dim = read_u32(12)?;
        let bottleneck_dim = read_u32(16)?;
        let conv_kernel = read_u32(20)?;
        let meta_dim = read_u32(24)?;
        let mlp_hidden = read_u32(28)?;
        let max_q_tokens = read_u32(32)?;
        let max_d_tokens = read_u32(36)?;
        let vocab_bytes_len = read_u32(40)?;

        if vocab_size == 0
            || emb_dim == 0
            || emb_dim % 8 != 0
            || bottleneck_dim == 0
            || conv_kernel != 3
            || (meta_dim != 24 && meta_dim != 32 && meta_dim != 40)
        {
            return Err("invalid WM7D hyperparameter dimensions".into());
        }
        let mut cursor = 44;
        let vocab_blob = bytes
            .get(cursor..cursor + vocab_bytes_len)
            .ok_or_else(|| "truncated WM7D vocab blob".to_string())?
            .to_vec();
        cursor += vocab_bytes_len;

        // Parse spans + populate power-of-two linear-probing hash table cleanly
        let mut tok_spans = Vec::with_capacity(vocab_size);
        let mut start = 0usize;
        for (idx, &b) in vocab_blob.iter().enumerate() {
            if b == b'\n' {
                tok_spans.push((start as u32, idx as u32));
                start = idx + 1;
            }
        }
        if start <= vocab_blob.len() && tok_spans.len() < vocab_size {
            tok_spans.push((start as u32, vocab_blob.len() as u32));
        }
        if tok_spans.len() != vocab_size {
            return Err(format!(
                "vocab count mismatch: parsed {} expected {}",
                tok_spans.len(),
                vocab_size
            ));
        }

        let table_len = (vocab_size * 2).next_power_of_two();
        let mask = table_len - 1;
        let mut hash_table = vec![u32::MAX; table_len];
        let mut unk_id = 100u32.min((vocab_size - 1) as u32);
        for (tid, &(s, e)) in tok_spans.iter().enumerate() {
            let slice = &vocab_blob[s as usize..e as usize];
            if slice == b"[UNK]" {
                unk_id = tid as u32;
            }
            let mut slot = (fnv1a_64(slice) as usize) & mask;
            while hash_table[slot] != u32::MAX {
                slot = (slot + 1) & mask;
            }
            hash_table[slot] = tid as u32;
        }

        let emb_bytes = vocab_size * emb_dim;
        let emb_raw = bytes
            .get(cursor..cursor + emb_bytes)
            .ok_or_else(|| "truncated WM7D emb_i8".to_string())?;
        let emb_i8: Vec<i8> = emb_raw.iter().map(|&u| u as i8).collect();
        cursor += emb_bytes;

        let read_f32_vec = |cur: &mut usize, count: usize| -> Result<Vec<f32>, String> {
            let byte_len = count * 4;
            let slice = bytes
                .get(*cur..*cur + byte_len)
                .ok_or_else(|| "truncated WM7D f32 tensor".to_string())?;
            *cur += byte_len;
            let mut out = Vec::with_capacity(count);
            for c in slice.chunks_exact(4) {
                out.push(f32::from_le_bytes([c[0], c[1], c[2], c[3]]));
            }
            Ok(out)
        };

        let emb_scales = read_f32_vec(&mut cursor, vocab_size)?;
        let q_dw_conv = read_f32_vec(&mut cursor, emb_dim * conv_kernel)?;
        let q_u_down = read_f32_vec(&mut cursor, bottleneck_dim * emb_dim)?;
        let q_u_up = read_f32_vec(&mut cursor, emb_dim * bottleneck_dim)?;
        let d_dw_conv = read_f32_vec(&mut cursor, emb_dim * conv_kernel)?;
        let d_u_down = read_f32_vec(&mut cursor, bottleneck_dim * emb_dim)?;
        let d_u_up = read_f32_vec(&mut cursor, emb_dim * bottleneck_dim)?;
        let q_gate_w = read_f32_vec(&mut cursor, emb_dim + 2)?;
        let q_gate_b = read_f32_vec(&mut cursor, 1)?[0];
        let anchor_w = read_f32_vec(&mut cursor, 1)?[0];
        let meta_mean = read_f32_vec(&mut cursor, meta_dim)?;
        let meta_inv_std = read_f32_vec(&mut cursor, meta_dim)?;
        let w_linear = read_f32_vec(&mut cursor, meta_dim)?;
        let w_f = read_f32_vec(&mut cursor, mlp_hidden * meta_dim)?;
        let w_qf = read_f32_vec(&mut cursor, mlp_hidden * emb_dim)?;
        let b_f = read_f32_vec(&mut cursor, mlp_hidden)?;
        let w_out = read_f32_vec(&mut cursor, mlp_hidden)?;
        let b_out = read_f32_vec(&mut cursor, 1)?[0];
        let (bi_q_gate_w, bi_d_gate_w, bi_proj_q, bi_proj_d) = if version >= 3 {
            let bq = read_f32_vec(&mut cursor, emb_dim + 1)?;
            let bd = read_f32_vec(&mut cursor, emb_dim + 1)?;
            let pq = read_f32_vec(&mut cursor, emb_dim * emb_dim)?;
            let pd = read_f32_vec(&mut cursor, emb_dim * emb_dim)?;
            (bq, bd, pq, pd)
        } else {
            (Vec::new(), Vec::new(), Vec::new(), Vec::new())
        };
        let (pref_hidden, pref_w_linear, pref_w_f, pref_w_qf, pref_b_f, pref_w_out, pref_b_out) =
            if version >= 4 {
                let ph = read_u32(cursor)?;
                cursor += 4;
                if ph == 0 || ph > 512 {
                    return Err("invalid WM7D v4 pref_hidden".into());
                }
                let pwl = read_f32_vec(&mut cursor, meta_dim)?;
                let pwf = read_f32_vec(&mut cursor, ph * meta_dim)?;
                let pwqf = read_f32_vec(&mut cursor, ph * emb_dim)?;
                let pbf = read_f32_vec(&mut cursor, ph)?;
                let pwo = read_f32_vec(&mut cursor, ph)?;
                let pbo = read_f32_vec(&mut cursor, 1)?[0];
                (ph, pwl, pwf, pwqf, pbf, pwo, pbo)
            } else {
                (
                    0,
                    Vec::new(),
                    Vec::new(),
                    Vec::new(),
                    Vec::new(),
                    Vec::new(),
                    0.0,
                )
            };
        let q_u_up_t = transpose_2d(&q_u_up, emb_dim, bottleneck_dim);
        let d_u_up_t = transpose_2d(&d_u_up, emb_dim, bottleneck_dim);

        Ok(Self {
            version,
            vocab_size,
            emb_dim,
            bottleneck_dim,
            _conv_kernel: conv_kernel,
            meta_dim,
            mlp_hidden,
            max_q_tokens,
            max_d_tokens,
            vocab_blob,
            tok_spans,
            hash_table,
            unk_id,
            emb_i8,
            emb_scales,
            q_dw_conv,
            q_u_down,
            q_u_up_t,
            d_dw_conv,
            d_u_down,
            d_u_up_t,
            q_gate_w,
            q_gate_b,
            anchor_w,
            meta_mean,
            meta_inv_std,
            w_linear,
            w_f,
            w_qf,
            b_f,
            w_out,
            b_out,
            bi_q_gate_w,
            bi_d_gate_w,
            bi_proj_q,
            bi_proj_d,
            pref_hidden,
            pref_w_linear,
            pref_w_f,
            pref_w_qf,
            pref_b_f,
            pref_w_out,
            pref_b_out,
        })
    }

    #[inline]
    #[must_use]
    pub fn version(&self) -> u8 {
        self.version
    }

    #[inline]
    #[must_use]
    pub fn has_biencoder(&self) -> bool {
        self.version >= 3 && !self.bi_proj_q.is_empty() && !self.bi_proj_d.is_empty()
    }

    #[inline]
    #[must_use]
    pub fn biencoder_dim(&self) -> usize {
        self.emb_dim
    }

    fn bi_pool_tokens_into(
        &self,
        h: &[f32],
        len: usize,
        gate_wb: &[f32],
        proj: &[f32],
        v_pool: &mut Vec<f32>,
    ) -> Vec<f32> {
        let d = self.emb_dim;
        if len == 0 || gate_wb.len() <= d || proj.len() < d * d {
            return vec![0.0_f32; d];
        }
        v_pool.resize(d, 0.0);
        v_pool.fill(0.0);
        let mut w_sum = 0.0_f32;
        for t in 0..len {
            let ht = &h[t * d..(t + 1) * d];
            let w = sigmoid_f32(dot_fast(ht, &gate_wb[..d]) + gate_wb[d]);
            w_sum += w;
            for (dst, &hv) in v_pool.iter_mut().zip(ht.iter()) {
                *dst += w * hv;
            }
        }
        let inv_w = 1.0 / w_sum.max(1e-6);
        for v in v_pool.iter_mut() {
            *v *= inv_w;
        }
        let mut v_out = vec![0.0_f32; d];
        let mut norm_sq = 0.0_f32;
        for i in 0..d {
            let val = v_pool[i] + 0.35 * dot_fast(&proj[i * d..(i + 1) * d], v_pool);
            v_out[i] = val;
            norm_sq += val * val;
        }
        let inv_n = 1.0 / norm_sq.sqrt().max(1e-6);
        for v in &mut v_out {
            *v *= inv_n;
        }
        v_out
    }

    fn bi_pool_tokens(&self, h: &[f32], len: usize, gate_wb: &[f32], proj: &[f32]) -> Vec<f32> {
        let mut v_pool = Vec::with_capacity(self.emb_dim);
        self.bi_pool_tokens_into(h, len, gate_wb, proj, &mut v_pool)
    }

    /// Encode a query into an L2-normalized dense bi-encoder vector (`WM7D\x03`).
    #[must_use]
    pub fn encode_biencoder_query(&self, query: &str) -> Vec<f32> {
        let d = self.emb_dim;
        let ids = self.tokenize_wordpiece(query, self.max_q_tokens);
        let mut x = Vec::with_capacity(ids.len() * d);
        let mut h = Vec::with_capacity(ids.len() * d);
        let mut conv = vec![0.0_f32; d];
        let mut mid = vec![0.0_f32; self.bottleneck_dim];
        self.encode_tokens_into_transposed(
            &ids,
            &self.q_dw_conv,
            &self.q_u_down,
            &self.q_u_up_t,
            &mut x,
            &mut h,
            &mut conv,
            &mut mid,
        );
        self.bi_pool_tokens(&h, ids.len(), &self.bi_q_gate_w, &self.bi_proj_q)
    }

    /// Encode a document using reusable scratch buffers (`WM7D\x03`, `head_tail <= 680`).
    #[must_use]
    pub fn encode_biencoder_doc_into(&self, text: &str, s: &mut BiEncoderScratch) -> Vec<f32> {
        if text.len() <= 680 {
            self.tokenize_wordpiece_with_scratch(
                text,
                self.max_d_tokens,
                &mut s.ids,
                &mut s.pre_buf,
                &mut s.ranges,
                &mut s.wp_buf,
                &mut s.byte_indices,
                &mut s.sub_tokens,
            );
        } else {
            let snip = head_tail_snippet(text, 680);
            self.tokenize_wordpiece_with_scratch(
                &snip,
                self.max_d_tokens,
                &mut s.ids,
                &mut s.pre_buf,
                &mut s.ranges,
                &mut s.wp_buf,
                &mut s.byte_indices,
                &mut s.sub_tokens,
            );
        }
        self.encode_tokens_into_transposed(
            &s.ids,
            &self.d_dw_conv,
            &self.d_u_down,
            &self.d_u_up_t,
            &mut s.x_buf,
            &mut s.h_buf,
            &mut s.conv_buf,
            &mut s.mid_buf,
        );
        self.bi_pool_tokens_into(
            &s.h_buf,
            s.ids.len(),
            &self.bi_d_gate_w,
            &self.bi_proj_d,
            &mut s.v_pool,
        )
    }

    /// Encode a document into an L2-normalized dense bi-encoder vector (`WM7D\x03`, `head_tail <= 680`).
    #[must_use]
    pub fn encode_biencoder_doc(&self, text: &str) -> Vec<f32> {
        let mut scratch = BiEncoderScratch::default();
        self.encode_biencoder_doc_into(text, &mut scratch)
    }

    #[inline]
    fn lookup_vocab_id(&self, token_bytes: &[u8]) -> Option<u32> {
        let mask = self.hash_table.len() - 1;
        let mut slot = (fnv1a_64(token_bytes) as usize) & mask;
        loop {
            let tid = self.hash_table[slot];
            if tid == u32::MAX {
                return None;
            }
            let (s, e) = self.tok_spans[tid as usize];
            if &self.vocab_blob[s as usize..e as usize] == token_bytes {
                return Some(tid);
            }
            slot = (slot + 1) & mask;
        }
    }

    #[inline]
    pub fn token_str(&self, tid: u32) -> &str {
        let (s, e) = self.tok_spans[tid as usize];
        std::str::from_utf8(&self.vocab_blob[s as usize..e as usize]).unwrap_or("")
    }

    /// BERT-compatible basic + greedy `##` WordPiece tokenizer with zero per-word heap churn.
    pub fn tokenize_wordpiece(&self, text: &str, max_len: usize) -> Vec<u32> {
        let mut ids = Vec::with_capacity(max_len);
        self.tokenize_wordpiece_into(text, max_len, &mut ids);
        ids
    }

    fn tokenize_wordpiece_into(&self, text: &str, max_len: usize, ids: &mut Vec<u32>) {
        let mut pre_buf = String::with_capacity(text.len().min(768));
        let mut ranges: Vec<(usize, usize)> = Vec::with_capacity(128);
        let mut buf = String::with_capacity(64);
        let mut byte_indices: Vec<usize> = Vec::with_capacity(32);
        let mut sub_tokens: Vec<u32> = Vec::with_capacity(8);
        self.tokenize_wordpiece_with_scratch(
            text,
            max_len,
            ids,
            &mut pre_buf,
            &mut ranges,
            &mut buf,
            &mut byte_indices,
            &mut sub_tokens,
        );
    }

    #[allow(clippy::too_many_arguments)]
    fn tokenize_wordpiece_with_scratch(
        &self,
        text: &str,
        max_len: usize,
        ids: &mut Vec<u32>,
        pre_buf: &mut String,
        ranges: &mut Vec<(usize, usize)>,
        buf: &mut String,
        byte_indices: &mut Vec<usize>,
        sub_tokens: &mut Vec<u32>,
    ) {
        ids.clear();
        pre_buf.clear();
        ranges.clear();
        let mut tok_start: Option<usize> = None;

        for ch in text.chars() {
            if ch == '\0' || ch == '\u{fffd}' {
                continue;
            }
            if ch.is_whitespace() || ch.is_control() {
                if let Some(s) = tok_start.take() {
                    ranges.push((s, pre_buf.len()));
                }
                continue;
            }
            if is_cjk(ch) || is_bert_punctuation(ch) {
                if let Some(s) = tok_start.take() {
                    ranges.push((s, pre_buf.len()));
                }
                let p_s = pre_buf.len();
                for lc in ch.to_lowercase() {
                    pre_buf.push(lc);
                }
                ranges.push((p_s, pre_buf.len()));
            } else {
                if tok_start.is_none() {
                    tok_start = Some(pre_buf.len());
                }
                for lc in ch.to_lowercase() {
                    pre_buf.push(lc);
                }
            }
        }
        if let Some(s) = tok_start {
            ranges.push((s, pre_buf.len()));
        }

        for &(ws, we) in ranges.iter() {
            if ids.len() >= max_len {
                break;
            }
            let word = &pre_buf[ws..we];
            if word.len() > 100 {
                ids.push(self.unk_id);
                continue;
            }
            if word.is_ascii()
                && let Some(tid) = self.lookup_vocab_id(word.as_bytes())
            {
                ids.push(tid);
                continue;
            }
            byte_indices.clear();
            byte_indices.extend(word.char_indices().map(|(i, _)| i));
            byte_indices.push(word.len());
            let mut start_ci = 0usize;
            let n_ci = byte_indices.len() - 1;
            sub_tokens.clear();
            let mut is_bad = false;
            while start_ci < n_ci {
                let mut end_ci = n_ci;
                let mut found: Option<u32> = None;
                let sb = byte_indices[start_ci];
                while end_ci > start_ci {
                    let eb = byte_indices[end_ci];
                    buf.clear();
                    if start_ci > 0 {
                        buf.push_str("##");
                    }
                    buf.push_str(&word[sb..eb]);
                    if let Some(tid) = self.lookup_vocab_id(buf.as_bytes()) {
                        found = Some(tid);
                        break;
                    }
                    end_ci -= 1;
                }
                if let Some(tid) = found {
                    sub_tokens.push(tid);
                    start_ci = end_ci;
                } else {
                    is_bad = true;
                    break;
                }
            }
            if is_bad {
                ids.push(self.unk_id);
            } else {
                for &tid in sub_tokens.iter() {
                    if ids.len() >= max_len {
                        break;
                    }
                    ids.push(tid);
                }
            }
        }
        if ids.is_empty() {
            ids.push(self.unk_id);
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn encode_tokens_into_transposed(
        &self,
        ids: &[u32],
        dw_conv: &[f32],
        u_down: &[f32],
        u_up_t: &[f32],
        x_buf: &mut Vec<f32>,
        out_buf: &mut Vec<f32>,
        conv_buf: &mut Vec<f32>,
        mid_buf: &mut Vec<f32>,
    ) {
        let len = ids.len();
        let d = self.emb_dim;
        let r_bn = self.bottleneck_dim;
        x_buf.resize(len * d, 0.0);
        for (t, &tid) in ids.iter().enumerate() {
            let row = (tid as usize).min(self.vocab_size - 1);
            let scale = self.emb_scales[row];
            let src = &self.emb_i8[row * d..(row + 1) * d];
            let dst = &mut x_buf[t * d..(t + 1) * d];
            for k in 0..d {
                dst[k] = f32::from(src[k]) * scale;
            }
        }

        out_buf.resize(len * d, 0.0);
        conv_buf.resize(d, 0.0);
        mid_buf.resize(r_bn, 0.0);
        for t in 0..len {
            let x_cur = &x_buf[t * d..(t + 1) * d];
            if t > 0 && t + 1 < len {
                let x_prev = &x_buf[(t - 1) * d..t * d];
                let x_next = &x_buf[(t + 1) * d..(t + 2) * d];
                for k in 0..d {
                    let c = dw_conv[k * 3] * x_prev[k]
                        + dw_conv[k * 3 + 1] * x_cur[k]
                        + dw_conv[k * 3 + 2] * x_next[k];
                    conv_buf[k] = silu_f32(c);
                }
            } else {
                for k in 0..d {
                    let left = if t > 0 { x_buf[(t - 1) * d + k] } else { 0.0 };
                    let right = if t + 1 < len {
                        x_buf[(t + 1) * d + k]
                    } else {
                        0.0
                    };
                    let c = dw_conv[k * 3] * left
                        + dw_conv[k * 3 + 1] * x_cur[k]
                        + dw_conv[k * 3 + 2] * right;
                    conv_buf[k] = silu_f32(c);
                }
            }
            for r in 0..r_bn {
                mid_buf[r] = dot_fast(conv_buf, &u_down[r * d..(r + 1) * d]);
            }
            let h_dst = &mut out_buf[t * d..(t + 1) * d];
            h_dst.copy_from_slice(x_cur);
            for r in 0..r_bn {
                let m = mid_buf[r];
                let row = &u_up_t[r * d..(r + 1) * d];
                for (dst, &w) in h_dst.iter_mut().zip(row.iter()) {
                    *dst += m * w;
                }
            }
            let mut norm_sq = 0.0_f32;
            for &v in h_dst.iter() {
                norm_sq += v * v;
            }
            let inv = 1.0 / norm_sq.sqrt().max(1e-6);
            for v in h_dst.iter_mut() {
                *v *= inv;
            }
        }
    }

    /// Score all candidates in a pool jointly with `ColBERT MaxSim` + 24 metadata & adjacency features.
    #[must_use]
    pub fn score_pool(&self, query: &str, candidates: &[RerankCandidateInput<'_>]) -> Vec<f32> {
        self.score_pool_detailed(query, candidates)
            .into_iter()
            .map(|f| f.raw_logit)
            .collect()
    }

    /// Score all candidates and return full ColBERT MaxSim + speaker + fact features in one pass.
    #[must_use]
    pub fn score_pool_detailed(
        &self,
        query: &str,
        candidates: &[RerankCandidateInput<'_>],
    ) -> Vec<RerankCandidateFeatures> {
        if candidates.is_empty() {
            return Vec::new();
        }
        let d = self.emb_dim;
        let q_ids = self.tokenize_wordpiece(query, self.max_q_tokens);
        let lq = q_ids.len();
        let mut x_scratch = Vec::with_capacity(self.max_d_tokens * d);
        let mut conv_scratch = vec![0.0_f32; d];
        let mut mid_scratch = vec![0.0_f32; self.bottleneck_dim];
        let mut q_h = Vec::with_capacity(lq * d);
        self.encode_tokens_into_transposed(
            &q_ids,
            &self.q_dw_conv,
            &self.q_u_down,
            &self.q_u_up_t,
            &mut x_scratch,
            &mut q_h,
            &mut conv_scratch,
            &mut mid_scratch,
        );

        // Local DF over the pool matching Python `df_local` cleanly
        let mut df_local: HashMap<String, usize> = HashMap::new();
        for c in candidates {
            let low = c.content.to_lowercase();
            let mut seen_words: HashSet<&str> = HashSet::new();
            for w in low
                .split(|ch: char| !ch.is_ascii_alphanumeric())
                .filter(|w| !w.is_empty())
            {
                if seen_words.insert(w) {
                    *df_local.entry(w.to_string()).or_insert(0) += 1;
                }
            }
        }
        let k_pool = (candidates.len().max(10)) as f32;
        let max_idf = (1.0 + k_pool).ln().max(1e-6);

        let mut q_idf = vec![0.0_f32; lq];
        let mut q_is_content = vec![0.0_f32; lq];
        let mut alpha = vec![0.0_f32; lq];
        let mut alpha_sum = 0.0_f32;

        let is_open_pref = ghrr_algebra::is_open_preference_query(query);
        for (i, &tid) in q_ids.iter().enumerate() {
            let ts = self.token_str(tid);
            let clean = ts.strip_prefix("##").unwrap_or(ts);
            let df = df_local.get(clean).copied().unwrap_or(0) as f32;
            let idf = ((1.0 + k_pool / (1.0 + df)).ln() / max_idf).clamp(0.0, 1.0);
            let is_c = if is_stopword(clean)
                || (self.version >= 3 && ghrr_algebra::is_chassis_word(clean))
            {
                0.0
            } else {
                1.0
            };
            q_idf[i] = idf;
            q_is_content[i] = is_c;

            let q_vec = &q_h[i * d..(i + 1) * d];
            let mut dot = self.q_gate_b + self.q_gate_w[d] * idf + self.q_gate_w[d + 1] * is_c;
            for (k, &qv) in q_vec.iter().enumerate().take(d) {
                dot += qv * self.q_gate_w[k];
            }
            let a = sigmoid_f32(dot);
            alpha[i] = a;
            alpha_sum += a;
        }
        let eff_alpha_sum = alpha_sum.max(1e-6);

        // Softmax over `q_idf * 6.0` for top-entity MaxSim focus
        let max_q_scaled = q_idf
            .iter()
            .map(|&v| v * 6.0)
            .fold(f32::NEG_INFINITY, f32::max);
        let mut idf_w: Vec<f32> = q_idf
            .iter()
            .map(|&v| (v * 6.0 - max_q_scaled).exp())
            .collect();
        let idf_sum: f32 = idf_w.iter().sum::<f32>().max(1e-6);
        for w in idf_w.iter_mut() {
            *w /= idf_sum;
        }
        let has_content_tok = q_is_content.iter().any(|&v| v > 0.5);

        // Weighted mean query embedding `v_q` + Query-conditioned MLP bias vector
        let mut vq = vec![0.0_f32; d];
        for i in 0..lq {
            let w = alpha[i] / eff_alpha_sum;
            let qv = &q_h[i * d..(i + 1) * d];
            for k in 0..d {
                vq[k] += w * qv[k];
            }
        }
        let mut qf_bias = vec![0.0_f32; self.mlp_hidden];
        for (h, bias_slot) in qf_bias.iter_mut().enumerate().take(self.mlp_hidden) {
            let row = &self.w_qf[h * d..(h + 1) * d];
            let mut acc = 0.0_f32;
            for (a, b) in vq.chunks_exact(8).zip(row.chunks_exact(8)) {
                acc += a[0] * b[0]
                    + a[1] * b[1]
                    + a[2] * b[2]
                    + a[3] * b[3]
                    + a[4] * b[4]
                    + a[5] * b[5]
                    + a[6] * b[6]
                    + a[7] * b[7];
            }
            *bias_slot = acc + self.b_f[h];
        }

        let mut out = Vec::with_capacity(candidates.len());
        let md = self.meta_dim.clamp(24, 40);
        let mut meta = [0.0_f32; 40];
        let mut meta_norm = [0.0_f32; 40];
        let mut d_scratch = BiEncoderScratch::default();
        let mut decl_bi_scratch = BiEncoderScratch::default();
        let mut d_h = Vec::with_capacity(self.max_d_tokens * d);
        let is_asst_q = ghrr_algebra::is_assistant_recall_query(query);
        let snip_chars = if self.version >= 3 { 1024 } else { 560 };

        let q_core = if self.version >= 4 {
            ghrr_algebra::extract_open_preference_topic_core(query)
        } else {
            String::new()
        };
        let q_core_sig = (self.version >= 4 && is_open_pref)
            .then(|| ghrr_algebra::pref_role_bound_qfhrr_signature(&q_core));
        let qv_core_bi = if self.version >= 4 && self.has_biencoder() {
            self.encode_biencoder_query(&q_core)
        } else {
            Vec::new()
        };
        let mut pqf_bias = if self.version >= 4 && is_open_pref && self.pref_hidden > 0 {
            let mut pb = vec![0.0_f32; self.pref_hidden];
            for (h, slot) in pb.iter_mut().enumerate().take(self.pref_hidden) {
                let row = &self.pref_w_qf[h * d..(h + 1) * d];
                *slot = dot_fast(&vq, row) + self.pref_b_f[h];
            }
            pb
        } else {
            Vec::new()
        };
        let _ = &mut pqf_bias;

        for c in candidates {
            let snip = ghrr_algebra::extract_query_focused_snippet(query, c.content, snip_chars);
            self.tokenize_wordpiece_with_scratch(
                &snip,
                self.max_d_tokens,
                &mut d_scratch.ids,
                &mut d_scratch.pre_buf,
                &mut d_scratch.ranges,
                &mut d_scratch.wp_buf,
                &mut d_scratch.byte_indices,
                &mut d_scratch.sub_tokens,
            );
            let ld = d_scratch.ids.len();
            self.encode_tokens_into_transposed(
                &d_scratch.ids,
                &self.d_dw_conv,
                &self.d_u_down,
                &self.d_u_up_t,
                &mut x_scratch,
                &mut d_h,
                &mut conv_scratch,
                &mut mid_scratch,
            );

            let mut maxsim_weighted = 0.0_f32;
            let mut maxsim_mean = 0.0_f32;
            let mut maxsim_cov = 0.0_f32;
            let mut maxsim_high_idf = 0.0_f32;
            let mut maxsim_min_c = 2.0_f32;

            for i in 0..lq {
                let qv = &q_h[i * d..(i + 1) * d];
                let mut r_max = -1e4_f32;
                for j in 0..ld {
                    let dv = &d_h[j * d..(j + 1) * d];
                    let dot = dot_fast(qv, dv);
                    if dot > r_max {
                        r_max = dot;
                    }
                }
                maxsim_weighted += alpha[i] * r_max;
                maxsim_mean += r_max;
                maxsim_cov += alpha[i] * sigmoid_f32((r_max - 0.40) * 10.0);
                maxsim_high_idf += idf_w[i] * r_max;
                if (!has_content_tok || q_is_content[i] > 0.5) && r_max < maxsim_min_c {
                    maxsim_min_c = r_max;
                }
            }
            maxsim_weighted /= eff_alpha_sum;
            maxsim_mean /= lq as f32;
            maxsim_cov /= eff_alpha_sum;
            maxsim_min_c = maxsim_min_c.clamp(-1.0, 1.0);

            let tag_asst = if c.source.contains(":assistant,") || c.source.ends_with(":assistant") {
                1.0
            } else {
                0.0
            };
            let tag_user = if c.source.contains(":user,") || c.source.ends_with(":user") {
                1.0
            } else {
                0.0
            };

            let fp_u = ghrr_algebra::first_person_user_score(c.content);
            let role_q_align = if is_asst_q {
                if tag_asst > 0.5 {
                    1.0
                } else if c.next_turn_is_asst {
                    -0.8
                } else {
                    -0.3
                }
            } else if tag_asst < 0.5 {
                0.5 * fp_u
            } else {
                0.0
            };

            let is_asst_styled = ghrr_algebra::is_assistant_styled(c.content);
            let is_question_turn = is_question_turn_score(c.content);
            let is_meta_clarify = is_meta_clarification(c.content);
            let facts = profile_facts(c.content);
            let unanswered_q_trap =
                has_unanswered_q_trap(c.content, &facts, is_asst_q, is_open_pref);
            let low_c = c.content.to_lowercase();
            let quotes_user_entity = (tag_asst > 0.5 || is_asst_styled)
                && (low_c.contains("your ") || low_c.contains("you "))
                && facts.proper_noun_count >= 1;

            meta[0] = c.lex_support;
            meta[1] = c.sem_support;
            meta[2] = c.hybrid_support;
            meta[3] = 1.0 / (1.0 + c.pre_rank as f32);
            meta[4] = maxsim_weighted;
            meta[5] = maxsim_mean;
            meta[6] = maxsim_cov;
            meta[7] = maxsim_high_idf;
            meta[8] = maxsim_min_c;
            meta[9] = tag_asst;
            meta[10] = tag_user;
            meta[11] = if is_asst_styled { 1.0 } else { 0.0 };
            meta[12] = is_question_turn;
            meta[13] = if is_meta_clarify { 1.0 } else { 0.0 };
            meta[14] = fp_u;
            meta[15] = c.recency_norm;
            meta[16] = if c.superseded { 1.0 } else { 0.0 };
            meta[17] = if c.temporal_hit { 1.0 } else { 0.0 };
            meta[18] = role_q_align;
            meta[19] = facts.density;
            meta[20] = c.prev_turn_lex;
            meta[21] = if c.prev_turn_is_user_question {
                1.0
            } else {
                0.0
            };
            meta[22] = c.next_turn_lex;
            meta[23] = if c.next_turn_is_asst { 1.0 } else { 0.0 };
            if md >= 32 {
                meta[24] = c.session_coref_lex;
                meta[25] = unanswered_q_trap;
                meta[26] = if facts.has_explicit_duration {
                    1.0
                } else {
                    0.0
                };
                meta[27] = if facts.has_role_or_venue_prep {
                    1.0
                } else {
                    0.0
                };
                meta[28] = if quotes_user_entity { 1.0 } else { 0.0 };
                meta[29] = c.fast_bi_cos;
                meta[30] = c.sess_density_norm;
                meta[31] = compute_q_atype_match(
                    query,
                    &facts,
                    is_asst_q,
                    is_open_pref,
                    unanswered_q_trap,
                );
            }
            let mut topic_core_bi_cos = 0.0_f32;
            if md >= 40 && self.version >= 4 {
                let pol = ghrr_algebra::evaluate_preference_polarity(c.content);
                if !qv_core_bi.is_empty() {
                    let decl_src = if pol.has_decl_clause {
                        pol.declarative_text.as_str()
                    } else {
                        c.content
                    };
                    if !decl_src.is_empty() {
                        let dv_decl =
                            self.encode_biencoder_doc_into(decl_src, &mut decl_bi_scratch);
                        let raw_c = dot_fast(&qv_core_bi, &dv_decl);
                        if raw_c.is_finite() {
                            topic_core_bi_cos = raw_c.clamp(0.0, 1.0);
                        }
                    }
                }
                let decl_qfhrr = if is_open_pref && pol.has_decl_clause {
                    q_core_sig.map_or(0.0_f32, |qs| {
                        qs.similarity(&ghrr_algebra::pref_role_bound_qfhrr_signature(
                            &pol.declarative_text,
                        ))
                    })
                } else {
                    0.0
                };
                let pure_decl = pol.has_decl_clause && !c.content.trim().ends_with('?');
                meta[32] = if is_open_pref { 1.0 } else { 0.0 };
                meta[33] = pol.e_pos;
                meta[34] = pol.e_neg;
                meta[35] = if pol.has_decl_clause { 1.0 } else { 0.0 };
                meta[36] = if pol.pure_question { 1.0 } else { 0.0 };
                meta[37] = decl_qfhrr;
                meta[38] = if pure_decl { 1.0 } else { 0.0 };
                meta[39] = topic_core_bi_cos;
                if is_open_pref {
                    let stance = (pol.e_pos + pol.e_neg).min(1.0);
                    meta[31] = (stance * (0.40 + 0.60 * topic_core_bi_cos)
                        - 0.65 * meta[36]
                        - 0.35 * (1.0 - meta[35]))
                        .clamp(-1.0, 1.0);
                }
            }

            let mut lin = self.b_out;
            for k in 0..md {
                let mn = ((meta[k] - self.meta_mean[k]) * self.meta_inv_std[k]).clamp(-4.0, 4.0);
                meta_norm[k] = mn;
                lin += self.w_linear[k] * mn;
            }
            let mut hidden_acc = 0.0_f32;
            for (h, &qb) in qf_bias.iter().enumerate().take(self.mlp_hidden) {
                let row = &self.w_f[h * md..(h + 1) * md];
                let dot = qb + dot_fast(row, &meta_norm[..md]);
                hidden_acc += self.w_out[h] * silu_f32(dot);
            }
            let res_raw = lin + hidden_acc;
            let raw_logit = if self.version >= 3 {
                0.24 * res_raw.tanh()
            } else {
                self.anchor_w * meta[2] + 0.95 * (res_raw / 2.0).tanh()
            };
            let pref_logit = if self.version >= 4 && is_open_pref && !pqf_bias.is_empty() {
                let plin = self.pref_b_out + dot_fast(&self.pref_w_linear[..md], &meta_norm[..md]);
                let mut phid = 0.0_f32;
                for (h, &pb) in pqf_bias.iter().enumerate().take(self.pref_hidden) {
                    let row = &self.pref_w_f[h * md..(h + 1) * md];
                    let dot = pb + dot_fast(row, &meta_norm[..md]);
                    phid += self.pref_w_out[h] * silu_f32(dot);
                }
                0.48 * ((plin + phid) / 2.5).tanh()
            } else {
                0.0
            };
            out.push(RerankCandidateFeatures {
                raw_logit,
                pref_logit,
                topic_core_bi_cos,
                maxsim_weighted,
                maxsim_high_idf,
                maxsim_min_c,
                tag_asst,
                tag_user,
                is_asst_styled,
                is_question_turn,
                is_meta_clarify,
                first_person_u: fp_u,
                recency_norm: c.recency_norm,
                facts,
                unanswered_q_trap,
                quotes_user_entity,
            });
        }

        out
    }
}

/// Optional Arc wrapper for cheap Substrate cloning / process sharing.
pub fn try_load_default_wm7d_spore() -> Option<Arc<Wm7dRerankSpore>> {
    if let Ok(p) = std::env::var("WM_GEN3_RERANK_SPORE") {
        let path = Path::new(&p);
        if path.exists()
            && let Ok(sp) = Wm7dRerankSpore::load_from_path(path)
        {
            return Some(Arc::new(sp));
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn build_synthetic_wm7d_bytes() -> Vec<u8> {
        let vocab = [
            "[PAD]", "[UNK]", "[CLS]", "[SEP]", "bike", "money", "$", "smoker",
        ];
        let vocab_blob = vocab.join("\n").into_bytes();
        let vs = vocab.len();
        let d = 64usize;
        let bn = 16usize;
        let hidden = 48usize;
        let mut out = Vec::new();
        out.extend_from_slice(WM7D_MAGIC);
        for &v in &[
            vs as u32,
            d as u32,
            bn as u32,
            3u32,
            24u32,
            hidden as u32,
            28u32,
            80u32,
            vocab_blob.len() as u32,
        ] {
            out.extend_from_slice(&v.to_le_bytes());
        }
        out.extend_from_slice(&vocab_blob);
        // emb_i8: orthogonal rows for test tokens
        let mut emb_i8 = vec![0i8; vs * d];
        emb_i8[4 * d] = 100; // bike
        emb_i8[5 * d + 1] = 100; // money
        emb_i8[6 * d + 1] = 100; // $ aligns with money!
        emb_i8[7 * d + 2] = 100; // smoker
        for b in emb_i8 {
            out.push(b as u8);
        }
        let push_f32s = |buf: &mut Vec<u8>, vals: &[f32]| {
            for &x in vals {
                buf.extend_from_slice(&x.to_le_bytes());
            }
        };
        push_f32s(&mut out, &vec![0.01f32; vs]); // scales
        let dw = vec![0.0f32; d * 3];
        push_f32s(&mut out, &dw); // q_dw
        push_f32s(&mut out, &vec![0.0f32; bn * d]); // q_u_down
        push_f32s(&mut out, &vec![0.0f32; d * bn]); // q_u_up
        push_f32s(&mut out, &dw); // d_dw
        push_f32s(&mut out, &vec![0.0f32; bn * d]); // d_u_down
        push_f32s(&mut out, &vec![0.0f32; d * bn]); // d_u_up
        push_f32s(&mut out, &vec![0.0f32; d + 2]); // q_gate_w
        push_f32s(&mut out, &[0.0f32]); // q_gate_b
        push_f32s(&mut out, &[1.2f32]); // anchor_w
        push_f32s(&mut out, &[0.0f32; 24]); // meta_mean
        push_f32s(&mut out, &[1.0f32; 24]); // meta_inv_std
        let mut w_lin = vec![0.0f32; 24];
        w_lin[4] = 2.0; // score driven by MaxSim_weighted
        push_f32s(&mut out, &w_lin);
        push_f32s(&mut out, &vec![0.0f32; hidden * 24]);
        push_f32s(&mut out, &vec![0.0f32; hidden * d]);
        push_f32s(&mut out, &vec![0.0f32; hidden]);
        push_f32s(&mut out, &vec![0.0f32; hidden]);
        push_f32s(&mut out, &[0.0f32]);
        out
    }

    #[test]
    fn wm7d_roundtrip_and_maxsim_ordering() {
        let bytes = build_synthetic_wm7d_bytes();
        let spore = Wm7dRerankSpore::from_bytes(&bytes).expect("valid synthetic WM7D v2 spore");
        assert!(is_stopword("my"));
        assert!(!is_stopword("smoker"));
        let ids = spore.tokenize_wordpiece("Bike money? $!", 28);
        assert_eq!(ids, vec![4, 5, 1, 6, 1]);

        let cands = vec![
            RerankCandidateInput {
                record_id: 1,
                content: "bike mileage 347",
                source: "corpus:codex:user,s1",
                lex_support: 0.7,
                sem_support: 0.0,
                hybrid_support: 0.7,
                pre_rank: 0,
                recency_norm: 0.5,
                superseded: false,
                temporal_hit: false,
                prev_turn_lex: 0.0,
                prev_turn_is_user_question: false,
                next_turn_lex: 0.0,
                next_turn_is_asst: false,
                session_coref_lex: 0.0,
                fast_bi_cos: 0.0,
                sess_density_norm: 0.5,
            },
            RerankCandidateInput {
                record_id: 2,
                content: "bike $ smoker",
                source: "corpus:codex:user,s1",
                lex_support: 0.4,
                sem_support: 0.0,
                hybrid_support: 0.4,
                pre_rank: 1,
                recency_norm: 0.6,
                superseded: false,
                temporal_hit: false,
                prev_turn_lex: 0.0,
                prev_turn_is_user_question: false,
                next_turn_lex: 0.0,
                next_turn_is_asst: false,
                session_coref_lex: 0.0,
                fast_bi_cos: 0.0,
                sess_density_norm: 0.5,
            },
        ];
        let sc = spore.score_pool("bike money smoker", &cands);
        assert!(
            sc[1] > sc[0],
            "money/$ + smoker match must outscore mileage distractor: {sc:?}"
        );
    }

    #[test]
    fn wm7d_v3_roundtrip_biencoder_and_32_meta() {
        let vocab = [
            "[PAD]",
            "[UNK]",
            "[CLS]",
            "[SEP]",
            "kitchen",
            "appliance",
            "smoker",
            "hours",
        ];
        let vocab_blob = vocab.join("\n").into_bytes();
        let vs = vocab.len();
        let d = 64usize;
        let bn = 16usize;
        let md = 32usize;
        let hidden = 48usize;
        let mut out = Vec::new();
        out.extend_from_slice(WM7D_V3_MAGIC);
        for &v in &[
            vs as u32,
            d as u32,
            bn as u32,
            3u32,
            md as u32,
            hidden as u32,
            28u32,
            128u32,
            vocab_blob.len() as u32,
        ] {
            out.extend_from_slice(&v.to_le_bytes());
        }
        out.extend_from_slice(&vocab_blob);
        let mut emb_i8 = vec![0i8; vs * d];
        emb_i8[4 * d] = 80; // kitchen
        emb_i8[5 * d] = 80; // appliance
        emb_i8[6 * d] = 100; // smoker aligns with kitchen appliance!
        emb_i8[7 * d + 1] = 100; // hours
        for b in emb_i8 {
            out.push(b as u8);
        }
        let push_f32s = |buf: &mut Vec<u8>, vals: &[f32]| {
            for &x in vals {
                buf.extend_from_slice(&x.to_le_bytes());
            }
        };
        push_f32s(&mut out, &vec![0.01f32; vs]);
        let dw = vec![0.0f32; d * 3];
        push_f32s(&mut out, &dw);
        push_f32s(&mut out, &vec![0.0f32; bn * d]);
        push_f32s(&mut out, &vec![0.0f32; d * bn]);
        push_f32s(&mut out, &dw);
        push_f32s(&mut out, &vec![0.0f32; bn * d]);
        push_f32s(&mut out, &vec![0.0f32; d * bn]);
        push_f32s(&mut out, &vec![0.0f32; d + 2]);
        push_f32s(&mut out, &[0.0f32]);
        push_f32s(&mut out, &[1.0f32]);
        push_f32s(&mut out, &vec![0.0f32; md]);
        push_f32s(&mut out, &vec![1.0f32; md]);
        let mut w_lin = vec![0.0f32; md];
        w_lin[25] = -2.0; // punish unanswered_q_trap
        w_lin[26] = 1.5; // reward explicit duration
        push_f32s(&mut out, &w_lin);
        push_f32s(&mut out, &vec![0.0f32; hidden * md]);
        push_f32s(&mut out, &vec![0.0f32; hidden * d]);
        push_f32s(&mut out, &vec![0.0f32; hidden]);
        push_f32s(&mut out, &vec![0.0f32; hidden]);
        push_f32s(&mut out, &[0.0f32]);
        push_f32s(&mut out, &vec![0.0f32; d + 1]); // bi_q_gate_w
        push_f32s(&mut out, &vec![0.0f32; d + 1]); // bi_d_gate_w
        push_f32s(&mut out, &vec![0.0f32; d * d]); // bi_proj_q
        push_f32s(&mut out, &vec![0.0f32; d * d]); // bi_proj_d

        let spore = Wm7dRerankSpore::from_bytes(&out).expect("valid synthetic WM7D v3 spore");
        assert_eq!(spore.version(), 3);
        assert!(spore.has_biencoder());
        let qv = spore.encode_biencoder_query("kitchen appliance");
        let dv_hit = spore.encode_biencoder_doc("I bought a new smoker today.");
        let dv_miss = spore.encode_biencoder_doc("I waited 4 hours.");
        let sim_hit: f32 = qv.iter().zip(dv_hit.iter()).map(|(a, b)| a * b).sum();
        let sim_miss: f32 = qv.iter().zip(dv_miss.iter()).map(|(a, b)| a * b).sum();
        assert!(
            sim_hit > 0.9 && sim_hit > sim_miss,
            "hit={sim_hit} miss={sim_miss}"
        );

        let cands = vec![
            RerankCandidateInput {
                record_id: 1,
                content: "Can you remind me how long it took?",
                source: "corpus:codex:user,s1",
                lex_support: 0.6,
                sem_support: 0.0,
                hybrid_support: 0.6,
                pre_rank: 0,
                recency_norm: 0.5,
                superseded: false,
                temporal_hit: false,
                prev_turn_lex: 0.0,
                prev_turn_is_user_question: false,
                next_turn_lex: 0.0,
                next_turn_is_asst: false,
                session_coref_lex: 0.0,
                fast_bi_cos: sim_miss,
                sess_density_norm: 0.5,
            },
            RerankCandidateInput {
                record_id: 2,
                content: "Putting the shelf together took 4 hours yesterday.",
                source: "corpus:codex:user,s1",
                lex_support: 0.5,
                sem_support: 0.0,
                hybrid_support: 0.5,
                pre_rank: 1,
                recency_norm: 0.6,
                superseded: false,
                temporal_hit: false,
                prev_turn_lex: 0.0,
                prev_turn_is_user_question: false,
                next_turn_lex: 0.0,
                next_turn_is_asst: false,
                session_coref_lex: 0.0,
                fast_bi_cos: sim_miss,
                sess_density_norm: 0.5,
            },
        ];
        let feats = spore.score_pool_detailed("How long did it take?", &cands);
        assert!(feats[0].unanswered_q_trap > 0.5);
        assert!(feats[1].facts.has_explicit_duration);
        assert!(feats[1].raw_logit > feats[0].raw_logit);

        let fact_with_followup = "I graduated with a degree in Business Administration, which helped my new role. Do you have any advice on paperwork?";
        let f_profile = profile_facts(fact_with_followup);
        assert_eq!(
            has_unanswered_q_trap(fact_with_followup, &f_profile, false, false),
            0.0,
            "fact declaration followed by polite question must not trigger unanswered_q_trap"
        );
        let mut scratch = BiEncoderScratch::default();
        let dv_hit_scratch =
            spore.encode_biencoder_doc_into("I bought a new smoker today.", &mut scratch);
        let max_diff = dv_hit
            .iter()
            .zip(dv_hit_scratch.iter())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0_f32, f32::max);
        assert!(
            max_diff < 1e-5,
            "scratch bi-encoder must match cleanly: {max_diff}"
        );
    }

    #[test]
    fn wm7d_v4_preference_gated_head_separates_pref_from_question_trap() {
        let vocab = [
            "[PAD]", "[UNK]", "[CLS]", "[SEP]", "coffee", "espresso", "oat", "dairy",
        ];
        let vocab_blob = vocab.join("\n").into_bytes();
        let vs = vocab.len();
        let d = 96usize;
        let bn = 24usize;
        let md = 40usize;
        let hidden = 64usize;
        let pref_hidden = 48usize;
        let mut out = Vec::new();
        out.extend_from_slice(WM7D_V4_MAGIC);
        for &v in &[
            vs as u32,
            d as u32,
            bn as u32,
            3u32,
            md as u32,
            hidden as u32,
            28u32,
            128u32,
            vocab_blob.len() as u32,
        ] {
            out.extend_from_slice(&v.to_le_bytes());
        }
        out.extend_from_slice(&vocab_blob);
        let mut emb_i8 = vec![0i8; vs * d];
        emb_i8[4 * d] = 100; // coffee
        emb_i8[5 * d] = 100; // espresso
        emb_i8[6 * d] = 100; // oat aligns with coffee!
        emb_i8[7 * d] = 100; // dairy aligns with coffee!
        for b in emb_i8 {
            out.push(b as u8);
        }
        let push_f32s = |buf: &mut Vec<u8>, vals: &[f32]| {
            for &x in vals {
                buf.extend_from_slice(&x.to_le_bytes());
            }
        };
        push_f32s(&mut out, &vec![0.01f32; vs]);
        push_f32s(&mut out, &vec![0.0f32; d * 3]);
        push_f32s(&mut out, &vec![0.0f32; bn * d]);
        push_f32s(&mut out, &vec![0.0f32; d * bn]);
        push_f32s(&mut out, &vec![0.0f32; d * 3]);
        push_f32s(&mut out, &vec![0.0f32; bn * d]);
        push_f32s(&mut out, &vec![0.0f32; d * bn]);
        push_f32s(&mut out, &vec![0.0f32; d + 2]);
        push_f32s(&mut out, &[0.0f32]);
        push_f32s(&mut out, &[1.0f32]);
        push_f32s(&mut out, &vec![0.0f32; md]);
        push_f32s(&mut out, &vec![1.0f32; md]);
        push_f32s(&mut out, &vec![0.0f32; md]);
        push_f32s(&mut out, &vec![0.0f32; hidden * md]);
        push_f32s(&mut out, &vec![0.0f32; hidden * d]);
        push_f32s(&mut out, &vec![0.0f32; hidden]);
        push_f32s(&mut out, &vec![0.0f32; hidden]);
        push_f32s(&mut out, &[0.0f32]);
        push_f32s(&mut out, &vec![0.0f32; d + 1]);
        push_f32s(&mut out, &vec![0.0f32; d + 1]);
        push_f32s(&mut out, &vec![0.0f32; d * d]);
        push_f32s(&mut out, &vec![0.0f32; d * d]);
        // v4 pref head
        out.extend_from_slice(&(pref_hidden as u32).to_le_bytes());
        let mut pwl = vec![0.0f32; md];
        pwl[33] = 1.0; // e_pos
        pwl[34] = 1.2; // e_neg
        pwl[36] = -1.5; // pure_question penalty
        pwl[39] = 1.0; // topic_core_bi_cos
        push_f32s(&mut out, &pwl);
        push_f32s(&mut out, &vec![0.0f32; pref_hidden * md]);
        push_f32s(&mut out, &vec![0.0f32; pref_hidden * d]);
        push_f32s(&mut out, &vec![0.0f32; pref_hidden]);
        push_f32s(&mut out, &vec![0.0f32; pref_hidden]);
        push_f32s(&mut out, &[0.0f32]);

        let spore = Wm7dRerankSpore::from_bytes(&out).expect("valid synthetic WM7D v4 spore");
        assert_eq!(spore.version(), 4);
        let cands = vec![
            RerankCandidateInput {
                record_id: 1,
                content: "Can you suggest a good coffee creamer?",
                source: "corpus:codex:user,s1",
                lex_support: 0.7,
                sem_support: 0.5,
                hybrid_support: 0.6,
                pre_rank: 0,
                recency_norm: 0.5,
                superseded: false,
                temporal_hit: false,
                prev_turn_lex: 0.0,
                prev_turn_is_user_question: false,
                next_turn_lex: 0.0,
                next_turn_is_asst: false,
                session_coref_lex: 0.0,
                fast_bi_cos: 0.6,
                sess_density_norm: 0.5,
            },
            RerankCandidateInput {
                record_id: 2,
                content: "I'm allergic to cow dairy so I always use oat milk for espresso.",
                source: "corpus:codex:user,s2",
                lex_support: 0.2,
                sem_support: 0.4,
                hybrid_support: 0.3,
                pre_rank: 1,
                recency_norm: 0.6,
                superseded: false,
                temporal_hit: false,
                prev_turn_lex: 0.0,
                prev_turn_is_user_question: false,
                next_turn_lex: 0.0,
                next_turn_is_asst: false,
                session_coref_lex: 0.0,
                fast_bi_cos: 0.5,
                sess_density_norm: 0.5,
            },
        ];
        // On non-preference query, pref_logit must be strictly 0.0 (zero regression guarantee!)
        let feats_fact = spore.score_pool_detailed("What did I buy yesterday?", &cands);
        assert_eq!(feats_fact[0].pref_logit, 0.0);
        assert_eq!(feats_fact[1].pref_logit, 0.0);
        // On open-preference query, preference declaration must decisively outscore pure question
        let feats_pref =
            spore.score_pool_detailed("Can you recommend a coffee creamer recipe?", &cands);
        assert!(
            feats_pref[1].pref_logit > feats_pref[0].pref_logit + 0.30,
            "v4 pref head must separate preference ({:.3}) from pure question ({:.3})",
            feats_pref[1].pref_logit,
            feats_pref[0].pref_logit
        );

        let smoke_path = Path::new("/tmp/stage7d_v4_smoke/wm7d_reranker_v4.tm7d");
        if smoke_path.exists() {
            let py_spore = Wm7dRerankSpore::load_from_path(smoke_path)
                .expect("Rust must cleanly parse Python-exported WM7D v4 binary");
            assert_eq!(py_spore.version(), 4);
            let py_feats =
                py_spore.score_pool_detailed("Can you recommend a coffee creamer recipe?", &cands);
            assert!(
                py_feats
                    .iter()
                    .all(|f| f.raw_logit.is_finite() && f.pref_logit.is_finite())
            );
        }
    }
}
