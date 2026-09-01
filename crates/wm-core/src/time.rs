//! Time — one generation point for every persisted timestamp.
//!
//! Three canonical forms exist in the wild (see
//! `docs/TIMESTAMP_CONVENTIONS.md` for the full per-surface registry):
//!
//! - **Epoch milliseconds** (`now_unix_millis`) — the default for new
//!   persisted event records (sessions, friction JSONL, the opencode
//!   corpus). Sub-second ordering matters for parallel sessions, and the
//!   opencode corpus we correlate against (Phase 4 archaeology) is millis.
//! - **Epoch seconds** (`now_unix_secs`) — legacy schemas already fixed to
//!   seconds (karma chain, write-audit journal, sangha locks). Do not
//!   migrate casually: readers exist.
//! - **RFC 3339** (`now_rfc3339`) — human-facing coordination surfaces
//!   (lease ledgers, drill reports) where an agent reads the value with a
//!   bare eye.
//!
//! Rules:
//! 1. Never hand-roll `SystemTime::now()` or `Utc::now().timestamp*()` at
//!    a write site — go through this module so the convention has one
//!    implementation.
//! 2. A persisted timestamp field's doc comment names its unit.
//! 3. Cross-surface correlation converts through typed `chrono::DateTime`,
//!    never by comparing raw integers (the 1000× ambiguity class).

#![forbid(unsafe_code)]

use std::time::{SystemTime, UNIX_EPOCH};

/// Current Unix time in **milliseconds** — the default for new persisted
/// event records.
#[must_use]
pub fn now_unix_millis() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_millis() as i64)
}

/// Current Unix time in **seconds** — legacy schemas fixed to seconds
/// (karma chain, write-audit journal, sangha locks).
#[must_use]
pub fn now_unix_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

/// Current time as **RFC 3339** with second precision and `Z` offset —
/// human-facing coordination surfaces (lease ledgers, drill reports).
#[must_use]
pub fn now_rfc3339() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn millis_and_secs_agree() {
        let secs = i64::try_from(now_unix_secs()).expect("unix seconds fit i64");
        let millis = now_unix_millis();
        // The two calls straddle the same wall-clock second in practice;
        // allow one second of drift between them.
        assert!(
            (millis - secs * 1000).abs() <= 1500,
            "millis {millis} vs secs {secs} disagree by more than a second"
        );
    }

    #[test]
    fn millis_is_thirteen_digits_this_era() {
        let millis = now_unix_millis();
        assert!(
            (1_000_000_000_000..=9_999_999_999_999).contains(&millis),
            "millis outside the 13-digit era: {millis}"
        );
    }

    #[test]
    fn rfc3339_shape_is_z_terminated() {
        let ts = now_rfc3339();
        assert!(ts.ends_with('Z'), "got: {ts}");
        assert_eq!(ts.len(), 20, "second-precision Z format, got: {ts}");
        assert!(chrono::DateTime::parse_from_rfc3339(&ts).is_ok());
    }
}
