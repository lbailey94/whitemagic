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
];

const NUM_WORDS: &[&str] = &[
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "dozen", "twenty", "thirty", "hundred",
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

    let mut proper_cnt = 0usize;
    let raw_toks: Vec<&str> = text.split_whitespace().collect();
    for (i, tok) in raw_toks.iter().enumerate() {
        let clean = tok.trim_matches(|c: char| ".,!?;:\"'()[]{}".contains(c));
        let mut chars = clean.chars();
        if let Some(first) = chars.next()
            && i > 0
            && clean.len() >= 2
            && first.is_uppercase()
            && !clean.chars().all(|c| c.is_uppercase())
            && !raw_toks[i - 1].ends_with(['.', '!', '?', ':'])
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
    }
}

/// Detailed `WM7D` ColBERT MaxSim + speaker/provenance features extracted for banded tie-breaking.
#[derive(Debug, Clone, Copy)]
pub struct RerankCandidateFeatures {
    pub raw_logit: f32,
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
}

/// Zero-heap-per-token open-addressed WordPiece lookup + quantized `WM7D\x01` inference engine.
#[derive(Debug, Clone)]
pub struct Wm7dRerankSpore {
    vocab_size: usize,
    emb_dim: usize,
    bottleneck_dim: usize,
    _conv_kernel: usize,
    _meta_dim: usize,
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
    q_u_up: Vec<f32>,
    d_dw_conv: Vec<f32>,
    d_u_down: Vec<f32>,
    d_u_up: Vec<f32>,
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
        if bytes.len() < 44 || &bytes[0..8] != WM7D_MAGIC {
            return Err("invalid WM7D v2 magic header".into());
        }
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
        {
            return Err("invalid WM7D v2 hyperparameter dimensions".into());
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

        Ok(Self {
            vocab_size,
            emb_dim,
            bottleneck_dim,
            _conv_kernel: conv_kernel,
            _meta_dim: meta_dim,
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
            q_u_up,
            d_dw_conv,
            d_u_down,
            d_u_up,
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
        })
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
        ids.clear();
        let mut pre_buf = String::with_capacity(text.len().min(768));
        let mut ranges: Vec<(usize, usize)> = Vec::with_capacity(128);
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

        let mut buf = String::with_capacity(64);
        let mut byte_indices: Vec<usize> = Vec::with_capacity(32);
        let mut sub_tokens: Vec<u32> = Vec::with_capacity(8);

        for (ws, we) in ranges {
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
                for &tid in &sub_tokens {
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
    fn encode_tokens_into(
        &self,
        ids: &[u32],
        dw_conv: &[f32],
        u_down: &[f32],
        u_up: &[f32],
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
            for k in 0..d {
                let left = if t > 0 { x_buf[(t - 1) * d + k] } else { 0.0 };
                let mid = x_cur[k];
                let right = if t + 1 < len {
                    x_buf[(t + 1) * d + k]
                } else {
                    0.0
                };
                let c =
                    dw_conv[k * 3] * left + dw_conv[k * 3 + 1] * mid + dw_conv[k * 3 + 2] * right;
                conv_buf[k] = silu_f32(c);
            }
            for r in 0..r_bn {
                mid_buf[r] = dot_fast(conv_buf, &u_down[r * d..(r + 1) * d]);
            }
            let h_dst = &mut out_buf[t * d..(t + 1) * d];
            let mut norm_sq = 0.0_f32;
            for k in 0..d {
                let acc = dot_fast(&mid_buf[..r_bn], &u_up[k * r_bn..(k + 1) * r_bn]);
                let val = x_cur[k] + acc;
                h_dst[k] = val;
                norm_sq += val * val;
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
        self.encode_tokens_into(
            &q_ids,
            &self.q_dw_conv,
            &self.q_u_down,
            &self.q_u_up,
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

        for (i, &tid) in q_ids.iter().enumerate() {
            let ts = self.token_str(tid);
            let clean = ts.strip_prefix("##").unwrap_or(ts);
            let df = df_local.get(clean).copied().unwrap_or(0) as f32;
            let idf = ((1.0 + k_pool / (1.0 + df)).ln() / max_idf).clamp(0.0, 1.0);
            let is_c = if is_stopword(clean) { 0.0 } else { 1.0 };
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
        let mut meta = [0.0_f32; 24];
        let mut meta_norm = [0.0_f32; 24];
        let mut d_ids = Vec::with_capacity(self.max_d_tokens);
        let mut d_h = Vec::with_capacity(self.max_d_tokens * d);
        let is_asst_q = ghrr_algebra::is_assistant_recall_query(query);

        for c in candidates {
            let snip = ghrr_algebra::extract_query_focused_snippet(query, c.content, 560);
            self.tokenize_wordpiece_into(&snip, self.max_d_tokens, &mut d_ids);
            let ld = d_ids.len();
            self.encode_tokens_into(
                &d_ids,
                &self.d_dw_conv,
                &self.d_u_down,
                &self.d_u_up,
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

            let mut lin = self.b_out;
            for k in 0..24 {
                let mn = ((meta[k] - self.meta_mean[k]) * self.meta_inv_std[k]).clamp(-4.0, 4.0);
                meta_norm[k] = mn;
                lin += self.w_linear[k] * mn;
            }
            let mut hidden_acc = 0.0_f32;
            for (h, &qb) in qf_bias.iter().enumerate().take(self.mlp_hidden) {
                let row = &self.w_f[h * 24..(h + 1) * 24];
                let dot = qb + dot_fast(row, &meta_norm);
                hidden_acc += self.w_out[h] * silu_f32(dot);
            }
            let res_raw = lin + hidden_acc;
            let raw_logit = self.anchor_w * meta[2] + 0.95 * (res_raw / 2.0).tanh();
            out.push(RerankCandidateFeatures {
                raw_logit,
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
            },
        ];
        let sc = spore.score_pool("bike money smoker", &cands);
        assert!(
            sc[1] > sc[0],
            "money/$ + smoker match must outscore mileage distractor: {sc:?}"
        );
    }
}
