//! Envelope v2 — one validator, three uses (V8 S4).
//!
//! Every bulk record stream this store produces carries an optional
//! single-line JSON envelope header as its first line:
//!
//! ```text
//! {"wm_envelope":{"count":5,"created_at":"2026-08-31T16:00:00+00:00","format_version":2,"generator":"wm 7.0.0-alpha.8","kind":"session_export"}}
//! ```
//!
//! Rules:
//! - **Writers always emit the header; readers accept streams with or
//!   without one.** Bare v1 payloads (plain record JSONL) stay importable
//!   forever — the header is additive, never a format break.
//! - The `wm_envelope` top-level key is the discriminator. Record types
//!   (`Memory` et al.) never serialize that key, so a header line can never
//!   collide with a record line.
//! - A header with `format_version` newer than [`ENVELOPE_FORMAT_VERSION`]
//!   is refused: a forward stream may carry records this build cannot
//!   parse honestly, and silently skipping records is the failure mode
//!   this module exists to prevent.
//! - `count` is advisory but checked: a mismatch is a warning, never a
//!   refusal (partial streams are still worth importing).
//!
//! Uses: `session.export` (header line in the JSONL stream),
//! `session.import` (validation), `wm backup`/`wm restore` (envelope.json
//! beside SHA256SUMS). All three go through this module — there is no
//! second implementation.

/// The envelope format this build writes. Readers accept this version and
/// any older header; newer headers are refused.
pub const ENVELOPE_FORMAT_VERSION: u32 = 2;

/// Top-level discriminator key on the header line.
pub const ENVELOPE_KEY: &str = "wm_envelope";

/// Header of an enveloped record stream.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct EnvelopeHeader {
    /// Stream format version. This build writes [`ENVELOPE_FORMAT_VERSION`].
    pub format_version: u32,
    /// What the stream carries: `"session_export"`, `"store_backup"`, ...
    pub kind: String,
    /// RFC 3339 creation timestamp of the stream.
    pub created_at: String,
    /// Declared record count (advisory; validated as a warning on mismatch).
    pub count: usize,
    /// Producing binary and version, e.g. `"wm 7.0.0-alpha.8"`.
    pub generator: String,
}

impl EnvelopeHeader {
    /// A header for a stream being written right now.
    #[must_use]
    pub fn new(kind: &str, count: usize) -> Self {
        Self {
            format_version: ENVELOPE_FORMAT_VERSION,
            kind: kind.to_string(),
            created_at: chrono::Utc::now().to_rfc3339(),
            count,
            generator: format!("wm {}", env!("CARGO_PKG_VERSION")),
        }
    }

    /// The header as a single JSON line for stream prefixes.
    #[must_use]
    pub fn header_line(&self) -> String {
        let mut v = serde_json::to_value(self).unwrap_or_else(|_| serde_json::json!({}));
        // Re-wrap under the discriminator key so the line is
        // distinguishable from any record line.
        let inner = v.take();
        serde_json::to_string(&serde_json::json!({ ENVELOPE_KEY: inner }))
            .unwrap_or_else(|_| format!("{{\"{ENVELOPE_KEY}\":null}}"))
    }

    /// Validate `format_version` against this build. Newer formats are
    /// refused with an actionable message; equal or older are accepted.
    ///
    /// # Errors
    /// When the header declares a format newer than this build supports.
    pub fn check_version(&self) -> Result<(), String> {
        if self.format_version > ENVELOPE_FORMAT_VERSION {
            return Err(format!(
                "envelope format_version {} is newer than this build supports ({}); \
                 upgrade `wm` to read this stream — refusing to import it partially",
                self.format_version, ENVELOPE_FORMAT_VERSION
            ));
        }
        Ok(())
    }
}

/// Result of reading a header line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HeaderRead {
    /// The line is not a header — the stream is bare (v1) JSONL.
    NotAHeader,
    /// Valid header.
    Header(EnvelopeHeader),
    /// Header-shaped but refused (newer format, malformed).
    Refused(String),
}

/// Read the first non-empty line of a stream as a potential header.
///
/// Returns [`HeaderRead::NotAHeader`] when the line parses as JSON but has
/// no `wm_envelope` key, or is not JSON at all (a bare v1 record).
#[must_use]
pub fn read_header_line(line: &str) -> HeaderRead {
    let trimmed = line.trim();
    let Ok(v) = serde_json::from_str::<serde_json::Value>(trimmed) else {
        return HeaderRead::NotAHeader;
    };
    let Some(inner) = v.get(ENVELOPE_KEY) else {
        return HeaderRead::NotAHeader;
    };
    if inner.is_null() {
        return HeaderRead::Refused(format!(
            "envelope header present but malformed (null {ENVELOPE_KEY})"
        ));
    }
    match serde_json::from_value::<EnvelopeHeader>(inner.clone()) {
        Ok(h) => match h.check_version() {
            Ok(()) => HeaderRead::Header(h),
            Err(msg) => HeaderRead::Refused(msg),
        },
        Err(e) => HeaderRead::Refused(format!(
            "envelope header failed to parse: {e} (required: format_version, kind, \
             created_at, count, generator)"
        )),
    }
}

/// Scan result for a whole stream.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct StreamScan {
    /// Header, when the stream carries one.
    pub header: Option<EnvelopeHeader>,
    /// Non-fatal findings (count mismatch, skipped lines).
    pub warnings: Vec<String>,
    /// JSON-parseable record lines seen (header excluded).
    pub records: usize,
    /// 1-based line numbers (in the original payload) whose JSON did not
    /// parse as an object.
    pub unparseable_lines: Vec<usize>,
}

/// Scan a whole stream: header, per-line JSON validity, record count.
///
/// Line-shape checks beyond JSON-object are the caller's business (the
/// import tool deserializes `Memory`; backup validates files differently).
/// The header line, when present, must be the first non-empty line.
#[must_use]
pub fn scan_stream(payload: &str) -> StreamScan {
    let mut scan = StreamScan::default();
    let mut header_checked = false;
    for (idx, line) in payload.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        if !header_checked {
            header_checked = true;
            match read_header_line(line) {
                HeaderRead::NotAHeader => { /* bare v1 stream; this line is a record */ }
                HeaderRead::Header(h) => {
                    scan.header = Some(h);
                    continue;
                }
                HeaderRead::Refused(msg) => {
                    scan.warnings.push(msg);
                    continue;
                }
            }
        }
        match serde_json::from_str::<serde_json::Value>(line.trim()) {
            Ok(v) if v.is_object() => scan.records += 1,
            _ => scan.unparseable_lines.push(idx + 1),
        }
    }
    if let Some(h) = &scan.header {
        if h.count != scan.records {
            scan.warnings.push(format!(
                "envelope declares count {} but stream carries {} records",
                h.count, scan.records
            ));
        }
    }
    if !scan.unparseable_lines.is_empty() {
        scan.warnings.push(format!(
            "{} line(s) skipped as unparseable JSON at lines {:?}",
            scan.unparseable_lines.len(),
            scan.unparseable_lines
        ));
    }
    scan
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn header_line_roundtrips_through_read() {
        let h = EnvelopeHeader::new("session_export", 5);
        let line = h.header_line();
        assert!(line.contains(ENVELOPE_KEY));
        match read_header_line(&line) {
            HeaderRead::Header(parsed) => {
                assert_eq!(parsed, h);
                assert_eq!(parsed.format_version, ENVELOPE_FORMAT_VERSION);
                assert_eq!(parsed.kind, "session_export");
                assert_eq!(parsed.count, 5);
            }
            other => panic!("expected header, got {other:?}"),
        }
    }

    #[test]
    fn bare_record_line_is_not_a_header() {
        let mem = serde_json::json!({
            "metadata": {"id": "00000000-0000-0000-0000-000000000000"},
            "content": "old memory",
            "embedding": null
        });
        let line = serde_json::to_string(&mem).unwrap();
        assert_eq!(read_header_line(&line), HeaderRead::NotAHeader);
    }

    #[test]
    fn non_json_line_is_not_a_header() {
        assert_eq!(read_header_line("not json at all"), HeaderRead::NotAHeader);
    }

    #[test]
    fn newer_format_version_is_refused() {
        let h = EnvelopeHeader {
            format_version: ENVELOPE_FORMAT_VERSION + 1,
            kind: "session_export".into(),
            created_at: chrono::Utc::now().to_rfc3339(),
            count: 1,
            generator: "wm 99.0.0".into(),
        };
        match read_header_line(&h.header_line()) {
            HeaderRead::Refused(msg) => {
                assert!(msg.contains("newer than this build supports"), "{msg}");
            }
            other => panic!("expected refusal, got {other:?}"),
        }
    }

    #[test]
    fn malformed_header_is_refused_with_field_names() {
        let line = serde_json::to_string(&serde_json::json!({
            ENVELOPE_KEY: {"format_version": 2}
        }))
        .unwrap();
        match read_header_line(&line) {
            HeaderRead::Refused(msg) => assert!(msg.contains("required"), "{msg}"),
            other => panic!("expected refusal, got {other:?}"),
        }
    }

    #[test]
    fn scan_stream_v2_payload() {
        let rec1 = serde_json::json!({"metadata": {}, "content": "a"}).to_string();
        let rec2 = serde_json::json!({"metadata": {}, "content": "b"}).to_string();
        let payload = format!(
            "{}\n{rec1}\n{rec2}\n",
            EnvelopeHeader::new("session_export", 2).header_line()
        );
        let scan = scan_stream(&payload);
        assert!(scan.header.is_some());
        assert_eq!(scan.records, 2);
        assert!(scan.warnings.is_empty(), "{:?}", scan.warnings);
        assert!(scan.unparseable_lines.is_empty());
    }

    #[test]
    fn scan_stream_bare_v1_payload_has_no_header() {
        let rec1 = serde_json::json!({"metadata": {}, "content": "a"}).to_string();
        let payload = format!("{rec1}\n");
        let scan = scan_stream(&payload);
        assert!(scan.header.is_none());
        assert_eq!(scan.records, 1);
        assert!(scan.warnings.is_empty());
    }

    #[test]
    fn scan_stream_flags_count_mismatch_and_bad_lines() {
        let good = serde_json::json!({"metadata": {}, "content": "a"}).to_string();
        let payload = format!(
            "{}\n{good}\n{{\"broken\":\nnot json\n",
            EnvelopeHeader::new("session_export", 3).header_line()
        );
        let scan = scan_stream(&payload);
        assert_eq!(scan.records, 1);
        assert!(
            scan.warnings
                .iter()
                .any(|w| w.contains("declares count 3 but stream carries 1"))
        );
        assert!(scan.warnings.iter().any(|w| w.contains("unparseable JSON")));
        assert_eq!(scan.unparseable_lines, vec![3, 4]);
    }

    #[test]
    fn header_survives_backup_json_roundtrip() {
        // `wm backup` writes the header as a JSON object (envelope.json);
        // the same struct must deserialize back identically.
        let h = EnvelopeHeader::new("store_backup", 42);
        let json = serde_json::to_string_pretty(&h).unwrap();
        let parsed: EnvelopeHeader = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed, h);
    }
}
