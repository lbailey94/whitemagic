//! Q35b flight recorder — opt-in dispatch payload capture (JSONL sidecar).
//!
//! Design: `planning/Q35B_FLIGHT_RECORDER_DESIGN.md`. The write-audit
//! journal stays digest-only (always-on, security-clean); the flight
//! sidecar holds the replay payloads, OFF by default, captured at the
//! same point the `args_digest` is computed so sidecar args always hash
//! to the journal digest (the replay identity gate).

use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// One captured dispatch — the replay payload unit.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FlightEntry {
    /// Monotonic capture sequence (capture order).
    pub seq: u64,
    /// Unix timestamp (seconds) at capture.
    pub ts: u64,
    /// Tool that was dispatched.
    pub tool: String,
    /// The dispatch arguments as captured (post-gate, digest-aligned).
    pub args: Value,
}

/// Append-only JSONL sidecar. Single-writer per file (matches the
/// journal's best-effort window note for concurrent dispatches).
pub struct FlightRecorder {
    path: PathBuf,
    next_seq: AtomicU64,
}

impl FlightRecorder {
    /// Create (or append to) a flight log at `path`.
    pub fn new(path: impl Into<PathBuf>) -> io::Result<Self> {
        let path = path.into();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let next = Self::scan_last_seq(&path)?.map_or(0, |s| s + 1);
        Ok(Self {
            path,
            next_seq: AtomicU64::new(next),
        })
    }

    /// Capture one dispatch. Returns the assigned seq.
    pub fn record(&self, tool: &str, args: &Value) -> io::Result<u64> {
        let seq = self.next_seq.fetch_add(1, Ordering::Relaxed);
        let entry = FlightEntry {
            seq,
            ts: wm_core::time::now_unix_secs(),
            tool: tool.to_string(),
            args: args.clone(),
        };
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)?;
        writeln!(
            file,
            "{}",
            serde_json::to_string(&entry).map_err(|e| {
                io::Error::new(io::ErrorKind::InvalidData, format!("serialize: {e}"))
            })?
        )?;
        file.flush()?;
        Ok(seq)
    }

    /// Last seq in an existing log (`None` = new/empty file).
    fn scan_last_seq(path: &Path) -> io::Result<Option<u64>> {
        if !path.exists() {
            return Ok(None);
        }
        let last = BufReader::new(File::open(path)?)
            .lines()
            .map_while(Result::ok)
            .filter_map(|l| serde_json::from_str::<FlightEntry>(&l).ok())
            .map(|e| e.seq)
            .max();
        Ok(last)
    }

    /// Read all entries from a flight log (skips malformed tail lines
    /// loudly via count — a torn last line after a crash must not
    /// silently truncate the replay set).
    pub fn read_entries(path: impl AsRef<Path>) -> io::Result<(Vec<FlightEntry>, usize)> {
        let file = File::open(path.as_ref())?;
        let mut entries = Vec::new();
        let mut malformed = 0usize;
        for line in BufReader::new(file).lines() {
            let line = line?;
            match serde_json::from_str::<FlightEntry>(&line) {
                Ok(e) => entries.push(e),
                Err(_) => malformed += 1,
            }
        }
        Ok((entries, malformed))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn tmp_path(tag: &str) -> PathBuf {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join(format!("{tag}.jsonl"));
        // Leak the tempdir for the test lifetime via Box::leak pattern:
        // simpler — write into std::env::temp_dir with a unique suffix.
        drop(dir);
        std::env::temp_dir().join(format!("wm-flight-test-{tag}-{}", std::process::id()))
    }

    #[test]
    fn record_then_read_roundtrip_and_append_seq() {
        let path = tmp_path("roundtrip");
        let rec = FlightRecorder::new(&path).unwrap();
        let s0 = rec
            .record("test.writer", &json!({"key": "a", "n": 1}))
            .unwrap();
        let s1 = rec.record("test.reader", &json!({"id": "x"})).unwrap();
        assert_eq!((s0, s1), (0, 1));

        // Reopen: append must continue from the last seq, not restart.
        let rec2 = FlightRecorder::new(&path).unwrap();
        let s2 = rec2
            .record("test.writer", &json!({"key": "b", "n": 2}))
            .unwrap();
        assert_eq!(s2, 2, "reopen continues the sequence");

        let (entries, malformed) = FlightRecorder::read_entries(&path).unwrap();
        assert_eq!(malformed, 0);
        assert_eq!(entries.len(), 3);
        assert_eq!(entries[0].tool, "test.writer");
        assert_eq!(entries[1].args["id"], "x");
        let _ = fs::remove_file(&path);
    }

    #[test]
    fn malformed_tail_is_counted_not_silent() {
        let path = tmp_path("torn");
        let rec = FlightRecorder::new(&path).unwrap();
        rec.record("test.writer", &json!({"key": "a"})).unwrap();
        // Simulate a torn write (crash mid-line).
        let mut f = OpenOptions::new().append(true).open(&path).unwrap();
        f.write_all(b"{\"seq\":1,\"tool\":\"te").unwrap();
        drop(f);
        let (entries, malformed) = FlightRecorder::read_entries(&path).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(malformed, 1, "torn line must be loud");
        let _ = fs::remove_file(&path);
    }
}
