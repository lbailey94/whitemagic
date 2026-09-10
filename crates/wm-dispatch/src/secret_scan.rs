//! Output credential-shape sampling — warn-only secret-exposure tripwire.
//!
//! P-PROV-5/B(c) (2026-09-10, Glama secret-exposure thread): tool outputs
//! can carry credential-shaped strings into logs, journals, and model
//! context. The sampler scans a deterministic 1-in-N fraction of
//! *successful* dispatch outputs with the ingest path's high-precision
//! detector ([`wm_memory::credential_shaped_content`]) and warns — never
//! blocks, never logs content (matched kind names + byte sizes only).
//! Counters feed the false-positive-rate report that gates any future
//! enforcement, which is an explicit non-goal of this module.
//!
//! Sampling is counter-deterministic (`seen % every == 0`), so tests and
//! audits reproduce exactly which dispatches were scanned. `every == 0`
//! disables scanning entirely (zero per-dispatch cost beyond one branch).

use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};

/// Default sampling cadence: scan every 100th successful output (~1%).
pub const DEFAULT_SAMPLE_EVERY: u64 = 100;

/// Environment knob: `WM_SECRET_SCAN_EVERY` (`0` = off, unset/invalid =
/// [`DEFAULT_SAMPLE_EVERY`]).
pub const SAMPLE_EVERY_ENV: &str = "WM_SECRET_SCAN_EVERY";

/// Warn-only sampler over successful dispatch outputs.
pub struct SecretSampler {
    every: u64,
    seen: AtomicU64,
    sampled: AtomicU64,
    hits: AtomicU64,
}

impl SecretSampler {
    /// Build with an explicit cadence (`0` disables).
    #[must_use]
    pub const fn new(every: u64) -> Self {
        Self {
            every,
            seen: AtomicU64::new(0),
            sampled: AtomicU64::new(0),
            hits: AtomicU64::new(0),
        }
    }

    /// Build from [`SAMPLE_EVERY_ENV`] (default [`DEFAULT_SAMPLE_EVERY`]).
    #[must_use]
    pub fn from_env() -> Self {
        Self::new(parse_every(std::env::var(SAMPLE_EVERY_ENV).ok().as_deref()))
    }

    /// Sampling cadence (`0` = disabled).
    #[must_use]
    pub const fn every(&self) -> u64 {
        self.every
    }

    /// (outputs seen, outputs scanned, outputs with credential-shaped hits).
    #[must_use]
    pub fn stats(&self) -> (u64, u64, u64) {
        (
            self.seen.load(Ordering::Relaxed),
            self.sampled.load(Ordering::Relaxed),
            self.hits.load(Ordering::Relaxed),
        )
    }

    /// Maybe scan one successful output. Returns the matched kinds (empty
    /// when skipped, disabled, clean, or unserializable). Hits emit a
    /// `WARN` carrying kind names and sizes only — content is never logged.
    pub fn scan(&self, tool: &str, output: &serde_json::Value) -> Vec<&'static str> {
        if self.every == 0 {
            return Vec::new();
        }
        let n = self.seen.fetch_add(1, Ordering::Relaxed);
        if n % self.every != 0 {
            return Vec::new();
        }
        self.sampled.fetch_add(1, Ordering::Relaxed);
        let Ok(text) = serde_json::to_string(output) else {
            return Vec::new();
        };
        let kinds = wm_memory::credential_shaped_content(&text);
        if !kinds.is_empty() {
            self.hits.fetch_add(1, Ordering::Relaxed);
            tracing::warn!(
                tool,
                kinds = ?kinds,
                output_bytes = text.len(),
                "secret-scan: successful output looks credential-bearing (warn-only; content withheld)"
            );
        }
        kinds
    }
}

/// Parse a cadence value.
///
/// Explicit numbers honored (`0` disables), missing/garbage falls back to
/// [`DEFAULT_SAMPLE_EVERY`]. Split out so tests never mutate process-global
/// env (Rust 2024 `set_var` is unsafe and the crates forbid it).
#[must_use]
pub fn parse_every(value: Option<&str>) -> u64 {
    value
        .and_then(|v| v.trim().parse::<u64>().ok())
        .unwrap_or(DEFAULT_SAMPLE_EVERY)
}

/// Shared sampler handle for the dispatch pipeline.
pub type SharedSampler = Arc<SecretSampler>;

#[cfg(test)]
mod tests {
    use super::*;

    // AWS-documentation example key shape (non-live, publisheddocs only).
    const EXAMPLE_AKIA: &str = "AKIAIOSFODNN7EXAMPLE";

    fn key_output() -> serde_json::Value {
        serde_json::json!({"data": format!("key={EXAMPLE_AKIA}")})
    }

    #[test]
    fn disabled_sampler_scans_nothing() {
        let s = SecretSampler::new(0);
        assert!(s.scan("memory.read", &key_output()).is_empty());
        assert_eq!(s.stats(), (0, 0, 0));
    }

    #[test]
    fn cadence_is_counter_deterministic() {
        let s = SecretSampler::new(3);
        for _ in 0..9 {
            s.scan("t", &serde_json::json!({"ok": true}));
        }
        // Dispatches 0, 3, 6 (0-indexed) sampled.
        assert_eq!(s.stats(), (9, 3, 0));
    }

    #[test]
    fn hit_kinds_returned_and_counted() {
        let s = SecretSampler::new(1);
        let kinds = s.scan("memory.read", &key_output());
        assert!(kinds.contains(&"aws_access_key_id"));
        assert_eq!(s.stats(), (1, 1, 1));
    }

    #[test]
    fn clean_output_sampled_without_hit() {
        let s = SecretSampler::new(1);
        let kinds = s.scan("memory.search", &serde_json::json!({"results": []}));
        assert!(kinds.is_empty());
        assert_eq!(s.stats(), (1, 1, 0));
    }

    #[test]
    fn parse_every_defaults_and_parses() {
        // Pure parse function — no process-global env mutation (Rust 2024
        // `set_var` is unsafe; the crates forbid it).
        assert_eq!(parse_every(None), DEFAULT_SAMPLE_EVERY);
        assert_eq!(parse_every(Some("7")), 7);
        assert_eq!(parse_every(Some("0")), 0);
        assert_eq!(parse_every(Some("  25  ")), 25);
        assert_eq!(parse_every(Some("garbage")), DEFAULT_SAMPLE_EVERY);
        assert_eq!(parse_every(Some("")), DEFAULT_SAMPLE_EVERY);
    }
}
