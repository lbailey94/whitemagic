//! Adversarial normalization, keyword-stuffing bounds, NLU capability firebreak,
//! and pre-cryptographic `IngestGuard` (`#![forbid(unsafe_code)]`).
//!
//! Ported cleanly from Gen 4 (`WMgen4/src/security.rs`).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};

/// Map common Cyrillic/Greek/confusable Latin lookalikes & fullwidth ASCII to canonical ASCII,
/// stripping invisible zero-width / BiDi / soft-hyphen control codepoints.
#[inline]
#[must_use]
pub fn fold_confusable_char(ch: char) -> Option<char> {
    if ch.is_ascii() {
        return Some(ch);
    }
    if matches!(
        ch,
        '\u{00AD}'
            | '\u{034F}'
            | '\u{061C}'
            | '\u{180E}'
            | '\u{200B}'..='\u{200F}'
            | '\u{202A}'..='\u{202E}'
            | '\u{2060}'..='\u{206F}'
            | '\u{FE00}'..='\u{FE0F}'
            | '\u{FEFF}'
    ) {
        return None;
    }

    if ('\u{FF01}'..='\u{FF5E}').contains(&ch) {
        return char::from_u32(u32::from(ch) - 0xFF01 + 0x21);
    }
    if ch == '\u{FF00}' || ch == '\u{3000}' {
        return Some(' ');
    }

    Some(match ch {
        'а' | 'А' | 'α' | 'Α' | 'à' | 'á' | 'â' | 'ä' | 'ã' | 'å' => {
            if ch.is_uppercase() { 'A' } else { 'a' }
        }
        'в' | 'В' | 'β' | 'Β' => 'b',
        'с' | 'С' | 'ς' => {
            if ch == 'С' {
                'C'
            } else {
                'c'
            }
        }
        'ԁ' | 'Ԁ' => 'd',
        'е' | 'Е' | 'ε' | 'Ε' | 'è' | 'é' | 'ê' | 'ë' => {
            if ch.is_uppercase() {
                'E'
            } else {
                'e'
            }
        }
        'ɡ' => 'g',
        'һ' | 'Н' | 'н' | 'Η' => 'h',
        'і' | 'І' | 'ι' | 'Ι' | 'ӏ' => 'i',
        'ј' | 'Ј' => 'j',
        'к' | 'К' | 'κ' | 'Κ' => 'k',
        'м' | 'М' | 'Μ' => 'm',
        'п' | 'ν' | 'Ν' => 'n',
        'о' | 'О' | 'ο' | 'Ο' | 'ө' | 'Ө' | 'ӧ' => {
            if ch.is_uppercase() {
                'O'
            } else {
                'o'
            }
        }
        'р' | 'Р' | 'ρ' | 'Ρ' => 'p',
        'ԛ' => 'q',
        'г' | 'ґ' => 'r',
        'ѕ' | 'Ѕ' => 's',
        'т' | 'Т' | 'τ' | 'Τ' => 't',
        'у' | 'У' | 'ү' | 'Υ' => 'y',
        'ѵ' => 'v',
        'х' | 'Х' | 'χ' | 'Χ' => 'x',
        '‐' | '‑' | '‒' | '–' | '—' | '−' => '-',
        '⁄' | '∕' => '/',
        _ => ch,
    })
}

/// Normalize untrusted text against homoglyph, fullwidth, and zero-width smuggle attacks.
#[must_use]
pub fn normalize_adversarial_text(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    let mut prev_space = false;
    for ch in input.chars() {
        if let Some(mapped) = fold_confusable_char(ch) {
            if mapped.is_whitespace() {
                if !prev_space && !out.is_empty() {
                    out.push(' ');
                    prev_space = true;
                }
            } else {
                out.push(mapped);
                prev_space = false;
            }
        }
    }
    if out.ends_with(' ') {
        out.pop();
    }
    out
}

/// Tokenize text after homoglyph/zero-width normalization.
#[must_use]
pub fn tokenize_adversarial_safe(input: &str) -> Vec<String> {
    let norm = normalize_adversarial_text(input);
    norm.split(|c: char| !c.is_alphanumeric() && c != '_' && c != '-')
        .filter(|t| t.len() >= 2)
        .map(|t| t.to_ascii_lowercase())
        .collect()
}

/// Result of scoring a document for adversarial keyword stuffing via `median + 2` tf cap.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StuffingScore {
    pub total_tokens: usize,
    pub unique_tokens: usize,
    pub median_tf: usize,
    pub cap: usize,
    pub max_raw_tf: usize,
    pub penalized_fraction: f32,
    pub effective_term_weights: HashMap<String, f32>,
}

/// Compute the `median + 2` term-frequency stuffing cap (`[2, 8]`) from an existing TF map
/// without re-allocating token strings.
#[must_use]
pub fn stuffing_cap_from_tf_counts(counts: &HashMap<String, usize>) -> usize {
    if counts.is_empty() {
        return 2;
    }
    let mut freqs: Vec<usize> = counts.values().copied().collect();
    freqs.sort_unstable();
    let median_tf = freqs[freqs.len() / 2];
    (median_tf + 2).clamp(2, 8)
}

/// Dampen a raw term frequency `tf` that exceeds `cap` (`median + 2`) via
/// `cap / (1 + ln(1 + excess)^2)` so keyword-stuffed bursts lose leverage.
#[inline]
#[must_use]
pub fn dampen_stuffed_tf(tf: usize, cap: usize) -> f32 {
    let excess = tf.saturating_sub(cap);
    if excess == 0 {
        (tf as f32).min(cap as f32)
    } else {
        let dampen = 1.0 / (1.0 + ((1.0 + excess as f32).ln()).powi(2));
        (cap as f32) * dampen
    }
}

/// Compute `median + 2` capped term weights to defeat adversarial keyword-stuffing bursts.
#[must_use]
pub fn score_with_stuffing_cap(tokens: &[String]) -> StuffingScore {
    let mut counts: HashMap<&str, usize> = HashMap::with_capacity(tokens.len().min(256));
    for t in tokens {
        *counts.entry(t.as_str()).or_insert(0) += 1;
    }
    if counts.is_empty() {
        return StuffingScore {
            total_tokens: 0,
            unique_tokens: 0,
            median_tf: 0,
            cap: 2,
            max_raw_tf: 0,
            penalized_fraction: 0.0,
            effective_term_weights: HashMap::new(),
        };
    }

    let mut freqs: Vec<usize> = counts.values().copied().collect();
    freqs.sort_unstable();
    let median_tf = freqs[freqs.len() / 2];
    let cap = (median_tf + 2).clamp(2, 8);
    let max_raw_tf = *freqs.last().unwrap_or(&0);

    let mut effective_term_weights = HashMap::with_capacity(counts.len());
    let mut penalized = 0usize;
    for (tok, tf) in &counts {
        if *tf > cap {
            penalized += 1;
        }
        effective_term_weights.insert((*tok).to_owned(), dampen_stuffed_tf(*tf, cap));
    }

    StuffingScore {
        total_tokens: tokens.len(),
        unique_tokens: counts.len(),
        median_tf,
        cap,
        max_raw_tf,
        penalized_fraction: (penalized as f32) / (counts.len() as f32),
        effective_term_weights,
    }
}

/// Fail-closed list of destructive / privilege-escalating / network-egress / credential tool names
/// that raw NLU outputs must never reach without an explicit non-NLU capability seal.
pub const DESTRUCTIVE_TOOL_CLASSES: &[&str] = &[
    "exec",
    "shell",
    "bash",
    "sh",
    "cmd",
    "rm",
    "rmdir",
    "unlink",
    "sudo",
    "chmod",
    "chown",
    "mkfs",
    "dd",
    "fdisk",
    "parted",
    "fs_write",
    "fs_delete",
    "file_write",
    "file_delete",
    "drop_table",
    "drop_database",
    "truncate_table",
    "net_dial",
    "mesh_dial",
    "http_post_external",
    "credential_read",
    "key_export",
    "process_kill",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundaryVerdict {
    pub allowed: bool,
    pub normalized_intent: String,
    pub reason: String,
}

/// Enforce `nlu_cannot_reach_any_destructive_tool` + normalized shell/credential blocking.
#[must_use]
pub fn evaluate_nlu_action_boundary(
    tool_or_intent: &str,
    payload: &str,
    has_non_nlu_capability_seal: bool,
) -> BoundaryVerdict {
    let norm_tool = normalize_adversarial_text(tool_or_intent).to_ascii_lowercase();
    let norm_payload = normalize_adversarial_text(payload).to_ascii_lowercase();

    let targets_destructive = DESTRUCTIVE_TOOL_CLASSES.iter().any(|&cls| {
        norm_tool == cls
            || norm_tool.ends_with(&format!(".{cls}"))
            || norm_tool.starts_with(&format!("{cls}:"))
            || norm_tool.starts_with(&format!("{cls} "))
            || norm_tool.contains(&format!(" {cls} "))
    });
    if targets_destructive && !has_non_nlu_capability_seal {
        return BoundaryVerdict {
            allowed: false,
            normalized_intent: norm_tool,
            reason: "blocked by nlu_cannot_reach_any_destructive_tool: unsigned NLU intent cannot dispatch destructive tool".to_string(),
        };
    }

    let compact: String = norm_payload
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    let compact_nospace = compact.replace(' ', "");
    let forbidden_markers = [
        "rm -rf /",
        "rm -fr /",
        "rm${ifs}-rf",
        "rm$ifs-rf",
        ">/dev/sd",
        ">/dev/nvme",
        "mkfs.",
        ":(){:|:&};:",
        "id_rsa",
        "id_ed25519",
        "/.ssh/",
        "/.gnupg",
        "/etc/shadow",
        "authorized_keys",
        ".aws/credentials",
        "drop database",
        "drop table",
        "truncate table",
        "sudo rm",
    ];
    for pat in forbidden_markers {
        if compact.contains(pat) || compact_nospace.contains(&pat.replace(' ', "")) {
            return BoundaryVerdict {
                allowed: false,
                normalized_intent: norm_tool,
                reason: format!(
                    "blocked by adversarial firebreak pattern '{pat}' after confusable/ZWSP strip"
                ),
            };
        }
    }

    BoundaryVerdict {
        allowed: true,
        normalized_intent: norm_tool,
        reason: "clean".to_string(),
    }
}

/// Pre-cryptographic `IngestGuard` validating frame size, per-source rate, timestamp skew,
/// and replay nonces before performing Ed25519/AEAD verification.
#[derive(Debug, Clone)]
pub struct IngestGuard {
    pub max_bytes: usize,
    pub max_skew_secs: u64,
    pub max_events_per_window: usize,
    pub window_secs: u64,
    source_windows: HashMap<String, VecDeque<u64>>,
    seen_nonces: HashSet<String>,
    nonce_order: VecDeque<String>,
    max_nonces: usize,
}

impl Default for IngestGuard {
    fn default() -> Self {
        Self::new(65_536, 300, 32, 60, 4096)
    }
}

impl IngestGuard {
    #[must_use]
    pub fn new(
        max_bytes: usize,
        max_skew_secs: u64,
        max_events_per_window: usize,
        window_secs: u64,
        max_nonces: usize,
    ) -> Self {
        Self {
            max_bytes,
            max_skew_secs,
            max_events_per_window: max_events_per_window.max(1),
            window_secs: window_secs.max(1),
            source_windows: HashMap::new(),
            seen_nonces: HashSet::new(),
            nonce_order: VecDeque::new(),
            max_nonces: max_nonces.max(16),
        }
    }

    pub fn admit_before_crypto(
        &mut self,
        source_id: &str,
        nonce: &str,
        payload_len: usize,
        msg_ts_secs: u64,
        now_secs: u64,
    ) -> Result<(), String> {
        if payload_len == 0 || payload_len > self.max_bytes {
            return Err(format!(
                "IngestGuard rejected size {payload_len} (bounds 1..={})",
                self.max_bytes
            ));
        }
        let skew = now_secs.abs_diff(msg_ts_secs);
        if skew > self.max_skew_secs {
            return Err(format!(
                "IngestGuard rejected stale/future timestamp skew {skew}s > {}s",
                self.max_skew_secs
            ));
        }
        if self.seen_nonces.contains(nonce) {
            return Err(format!("IngestGuard rejected replayed nonce '{nonce}'"));
        }

        let win = self
            .source_windows
            .entry(source_id.to_string())
            .or_default();
        let cutoff = now_secs.saturating_sub(self.window_secs);
        while win.front().is_some_and(|&t| t < cutoff) {
            win.pop_front();
        }
        if win.len() >= self.max_events_per_window {
            return Err(format!(
                "IngestGuard rate-limited source '{source_id}' ({}/{} in {}s)",
                win.len(),
                self.max_events_per_window,
                self.window_secs
            ));
        }

        win.push_back(now_secs);
        if self.seen_nonces.len() >= self.max_nonces {
            if let Some(old) = self.nonce_order.pop_front() {
                self.seen_nonces.remove(&old);
            }
        }
        self.seen_nonces.insert(nonce.to_string());
        self.nonce_order.push_back(nonce.to_string());
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blocks_homoglyph_zwsp_stuffing_and_destructive_nlu() {
        let bypass_attempts = [
            ("mandala.evaluate", "r\u{200B}m\u{FEFF} -rf /"),
            ("mandala.evaluate", "гм -rf /"),
            ("mandala.evaluate", "\u{FF52}\u{FF4D} -rf /"),
            ("wm", "sudo\u{200B} rm /var/log/syslog"),
            ("memory.ingest", "/home/bob/.\u{2060}ssh/id_еd25519"),
        ];
        for (i, (tool, payload)) in bypass_attempts.iter().enumerate() {
            let v = evaluate_nlu_action_boundary(tool, payload, false);
            assert!(
                !v.allowed,
                "attempt #{i} ({payload:?}) must be blocked; normalized={:?}",
                v.normalized_intent
            );
        }

        for destructive in [
            "exec",
            "shell",
            "fs_write",
            "rm",
            "drop_table",
            "credential_read",
        ] {
            let blocked = evaluate_nlu_action_boundary(destructive, "harmless text", false);
            assert!(!blocked.allowed, "NLU must never reach '{destructive}'");
        }

        let safe = evaluate_nlu_action_boundary(
            "memory.search",
            "Verify SCITT continuity receipt and Linux Landlock confinement status",
            false,
        );
        assert!(
            safe.allowed,
            "benign query produced false positive: {safe:?}"
        );

        let mut stuffed = vec!["lobby".to_string(); 50];
        stuffed.push("sofa".to_string());
        stuffed.push("archive".to_string());
        let st = score_with_stuffing_cap(&stuffed);
        assert_eq!(st.median_tf, 1);
        assert_eq!(st.cap, 3);
        assert!(st.effective_term_weights["lobby"] < 1.0);
        assert_eq!(st.effective_term_weights["sofa"], 1.0);
    }

    #[test]
    fn ingest_guard_rejects_replay_size_skew_and_bursts() {
        let mut guard = IngestGuard::new(4096, 60, 3, 60, 64);
        assert!(
            guard
                .admit_before_crypto("peerA", "n1", 256, 1000, 1005)
                .is_ok()
        );
        assert!(
            guard
                .admit_before_crypto("peerA", "n1", 256, 1005, 1006)
                .is_err()
        );
        assert!(
            guard
                .admit_before_crypto("peerA", "n2", 99_999, 1005, 1006)
                .is_err()
        );
        assert!(
            guard
                .admit_before_crypto("peerA", "n3", 256, 500, 1006)
                .is_err()
        );
        assert!(
            guard
                .admit_before_crypto("peerA", "n4", 256, 1005, 1006)
                .is_ok()
        );
        assert!(
            guard
                .admit_before_crypto("peerA", "n5", 256, 1005, 1007)
                .is_ok()
        );
        assert!(
            guard
                .admit_before_crypto("peerA", "n6", 256, 1005, 1008)
                .is_err()
        );
    }
}
