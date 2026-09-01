//! Typology classes and write-path policy (V8 S5, `MEMORY_TYPOLOGY_V8.md`
//! §2–§3).
//!
//! Five classes. Class is stamped at creation, before importance is
//! assigned; importance is derived from class + content, **never
//! caller-chosen** where the class policy says so. The detector is
//! deliberately conservative: it stamps only what it *confidently*
//! recognizes (template shapes, tag families, session-JSON shape) —
//! unrecognized content stays `None` (unstamped) rather than being
//! guessed into a class whose floors it does not deserve. Template
//! mining (typology §4) widens this set with evidence; the census scripts
//! are the upstream evidence source.

use crate::memory::Tier;
use serde::{Deserialize, Serialize};

/// Typology class — what family a memory belongs to, decided at the
/// write path.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MemoryClass {
    /// User/agent turns, session decisions — the conversation record.
    Dialogue,
    /// Strategy docs, lessons, verified claims.
    Knowledge,
    /// Friction records, karma events, RSI auto-logs — the salience
    /// inversion's former winner; ceiling-capped.
    Telemetry,
    /// Heritage chunks, bulk transcripts — sealed, ceiling-capped.
    RawArchive,
    /// Dedup stubs, rollups, references — points at content.
    Pointer,
}

impl MemoryClass {
    /// String label for JSON / display.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Dialogue => "dialogue",
            Self::Knowledge => "knowledge",
            Self::Telemetry => "telemetry",
            Self::RawArchive => "raw_archive",
            Self::Pointer => "pointer",
        }
    }
}

/// Template prefixes that mark telemetry by construction — the
/// Template prefixes that mark telemetry by construction — every prefix
/// here is emitted by code in this repo (evidence-locked, no speculative
/// patterns): the RSI recorder's friction family (`rsi.rs`), the
/// friction.log tool's plain form, and the daemon's WS-4 improvement
/// proposals (`daemon.rs`, which also carries `rsi:proposal` tags).
const TELEMETRY_TEMPLATE_PREFIXES: [&str; 3] = [
    "## Auto-logged Friction:",
    "## Friction:",
    "## Improvement Proposal",
];

/// Class detection from content shape + tag families.
///
/// Returns `None` when nothing is confidently recognized — the honest
/// residue. Never guesses `Knowledge` (its floor would then be granted
/// to arbitrary prose, recreating the inversion this slice exists to
/// kill).
#[must_use]
pub fn detect_class(content: &str, tags: &[String]) -> Option<MemoryClass> {
    // Tag families first — they carry provenance the content shape lacks.
    for tag in tags {
        let t = tag.as_str();
        if t.starts_with("rsi:") || t == "friction" || t.starts_with("friction:") {
            return Some(MemoryClass::Telemetry);
        }
        if t.starts_with("ingest:") || t == "heritage" || t.starts_with("heritage:") {
            return Some(MemoryClass::RawArchive);
        }
        if t == "pointer" || t == "dedup-stub" || t == "rollup" {
            return Some(MemoryClass::Pointer);
        }
    }

    // Telemetry template shapes (the junk filter's recognizer).
    let trimmed = content.trim_start();
    if TELEMETRY_TEMPLATE_PREFIXES
        .iter()
        .any(|p| trimmed.starts_with(p))
    {
        return Some(MemoryClass::Telemetry);
    }

    // Session-record shape: the JSON envelope the session tools write
    // (role + session_id keys) — dialogue by construction. The session
    // start marker carries the `start` tag.
    if tags.iter().any(|t| t == "start") {
        return Some(MemoryClass::Dialogue);
    }
    if trimmed.starts_with('{') {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(trimmed) {
            let has_role = v.get("role").is_some();
            let has_session = v.get("session_id").is_some();
            if has_role && has_session {
                return Some(MemoryClass::Dialogue);
            }
        }
    }

    None
}

/// Class-based importance policy (typology §2) — the plausibility gate's
/// rule set, applied to the caller- or default-requested importance.
///
/// - `Dialogue`: floor 0.75 — a session decision can never rank below
///   friction telemetry's ceiling.
/// - `Telemetry`: **ceiling 0.40** — the salience inversion's fix.
/// - `RawArchive`: ceiling 0.30, sealed.
/// - `Knowledge` / `Pointer`: untouched in v0 — knowledge's 0.7 floor
///   waits for template mining (§4) to detect it confidently; flooring
///   the unrecognized residue would flood the ≥0.7 band with noise.
#[must_use]
pub const fn apply_class_policy(class: MemoryClass, importance: f32) -> f32 {
    match class {
        MemoryClass::Dialogue => importance.max(0.75),
        MemoryClass::Telemetry => importance.min(0.40),
        MemoryClass::RawArchive => importance.min(0.30),
        MemoryClass::Knowledge | MemoryClass::Pointer => importance,
    }
}

/// Initial lifecycle tier for a freshly stamped class (typology §6):
/// fresh writes land hot (Working) and age out via the dream cycle;
/// heritage/raw-archive content is born cold.
#[must_use]
pub const fn initial_tier(class: MemoryClass) -> Tier {
    match class {
        MemoryClass::RawArchive => Tier::Archival,
        _ => Tier::Working,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn friction_templates_detect_telemetry() {
        for template in [
            "## Auto-logged Friction: Tool dispatch error (REGRESSION)\n\nbody",
            "## Friction: what happened\n\n**Expected:** x",
            "## Improvement Proposal\n\n**Category:** hygiene\n\n**Severity:** low",
        ] {
            assert_eq!(
                detect_class(template, &[]),
                Some(MemoryClass::Telemetry),
                "{template}"
            );
        }
    }

    #[test]
    fn tag_families_detect_classes() {
        let tags = |t: &[&str]| -> Vec<String> { t.iter().map(|s| (*s).to_string()).collect() };
        assert_eq!(
            detect_class("anything", &tags(&["rsi:hash:abcdef0123456789"])),
            Some(MemoryClass::Telemetry)
        );
        assert_eq!(
            detect_class("chunk text", &tags(&["source:heritage", "ingest:v5"])),
            Some(MemoryClass::RawArchive)
        );
        assert_eq!(
            detect_class("stub", &tags(&["pointer"])),
            Some(MemoryClass::Pointer)
        );
    }

    #[test]
    fn session_json_shape_detects_dialogue() {
        let turn = r#"{"role":"ai","content":"decision text","session_id":"abc"}"#;
        assert_eq!(detect_class(turn, &[]), Some(MemoryClass::Dialogue));
        let start = "plain marker content";
        assert_eq!(
            detect_class(start, &["start".to_string()]),
            Some(MemoryClass::Dialogue)
        );
    }

    #[test]
    fn unrecognized_content_stays_unstamped() {
        assert_eq!(detect_class("a normal thought about kumquats", &[]), None);
        // JSON that lacks the session-record shape is not dialogue.
        assert_eq!(detect_class(r#"{"foo": 1}"#, &[]), None);
    }

    #[test]
    fn class_policy_floors_dialogue_and_caps_telemetry() {
        assert_eq!(apply_class_policy(MemoryClass::Dialogue, 0.5), 0.75);
        assert_eq!(apply_class_policy(MemoryClass::Dialogue, 0.9), 0.9);
        assert_eq!(apply_class_policy(MemoryClass::Telemetry, 0.9), 0.40);
        assert_eq!(apply_class_policy(MemoryClass::Telemetry, 0.2), 0.2);
        assert_eq!(apply_class_policy(MemoryClass::RawArchive, 0.8), 0.30);
        assert_eq!(apply_class_policy(MemoryClass::Knowledge, 0.5), 0.5);
        assert_eq!(apply_class_policy(MemoryClass::Pointer, 0.5), 0.5);
    }

    #[test]
    fn dialogue_floor_dominate_telemetry_ceiling_by_construction() {
        // The acceptance invariant: a dialogue record at its floor still
        // outranks a telemetry record at its ceiling.
        assert!(
            apply_class_policy(MemoryClass::Dialogue, 0.0)
                > apply_class_policy(MemoryClass::Telemetry, 1.0)
        );
    }

    #[test]
    fn initial_tier_born_hot_except_archival() {
        assert_eq!(initial_tier(MemoryClass::Dialogue), Tier::Working);
        assert_eq!(initial_tier(MemoryClass::Telemetry), Tier::Working);
        assert_eq!(initial_tier(MemoryClass::RawArchive), Tier::Archival);
    }

    #[test]
    fn class_serde_roundtrip_snake_case() {
        let json = serde_json::to_string(&MemoryClass::RawArchive).unwrap();
        assert_eq!(json, "\"raw_archive\"");
        let back: MemoryClass = serde_json::from_str(&json).unwrap();
        assert_eq!(back, MemoryClass::RawArchive);
    }
}
