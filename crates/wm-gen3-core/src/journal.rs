//! Run journal — append-only JSONL evidence of decisions, refusals, relations,
//! selections, canaries and violations (`docs/PHASE2_RUN_JOURNAL.md`).
//!
//! Content is hash-only by default; the journal is the observable surface the
//! experiment wrapper reads. It never influences selection (journaling is a
//! side effect of operations, never an input).

use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use sha2::{Digest, Sha256};

#[must_use]
pub fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

#[must_use]
pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Hash a file's bytes (run-level journal hash; the host computes it after
/// `Substrate::finish` returns).
pub fn sha256_file(path: &Path) -> std::io::Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut file, &mut hasher)?;
    Ok(format!("{:x}", hasher.finalize()))
}

/// JSONL journal writer. One writer per run.
pub struct Journal {
    file: File,
    path: PathBuf,
    seq: u64,
}

impl Journal {
    pub fn open(path: &Path) -> std::io::Result<Self> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        // Recover the sequence and locate any truncated trailing record so a
        // crash mid-write cannot corrupt the next appended line.
        let (seq, valid_len, total_len) = match std::fs::read(path) {
            Ok(bytes) => {
                let (seq, valid_len) = recover_seq(&bytes);
                (seq, valid_len, bytes.len())
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (0, 0, 0),
            Err(e) => return Err(e),
        };
        let file = OpenOptions::new().create(true).append(true).open(path)?;
        if valid_len < total_len {
            file.set_len(valid_len as u64)?;
        }
        Ok(Self {
            file,
            path: path.to_path_buf(),
            seq,
        })
    }

    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Append one event. Field values are the caller's responsibility; content
    /// must be hashed by callers that carry it.
    pub fn event(
        &mut self,
        typ: &str,
        fields: serde_json::Map<String, serde_json::Value>,
    ) -> std::io::Result<()> {
        self.seq += 1;
        let mut obj = serde_json::Map::new();
        obj.insert("ts".into(), serde_json::Value::from(now_epoch()));
        obj.insert("seq".into(), serde_json::Value::from(self.seq));
        obj.insert("type".into(), serde_json::Value::from(typ));
        for (k, v) in fields {
            obj.insert(k, v);
        }
        writeln!(self.file, "{}", serde_json::Value::Object(obj))?;
        self.file.flush()
    }

    #[must_use]
    pub fn seq(&self) -> u64 {
        self.seq
    }
}

/// Returns `(last_seq, complete_len)` for existing journal bytes. `complete_len`
/// is the offset of the last newline (inclusive), so any truncated trailing
/// record is excluded from both the sequence scan and the repaired file.
fn recover_seq(bytes: &[u8]) -> (u64, usize) {
    let Some(last_newline) = bytes.iter().rposition(|b| *b == b'\n') else {
        return (0, 0);
    };
    let complete = &bytes[..=last_newline];
    let mut seq = 0u64;
    for line in complete.split(|b| *b == b'\n') {
        if line.is_empty() {
            continue;
        }
        if let Ok(value) = serde_json::from_slice::<serde_json::Value>(line)
            && let Some(found) = value.get("seq").and_then(serde_json::Value::as_u64)
        {
            seq = seq.max(found);
        }
    }
    (seq, complete.len())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_path(tag: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |d| d.as_nanos());
        std::env::temp_dir().join(format!("wm_journal_{tag}_{nanos}.jsonl"))
    }

    fn fields() -> serde_json::Map<String, serde_json::Value> {
        let mut f = serde_json::Map::new();
        f.insert("probe".into(), serde_json::Value::from(true));
        f
    }

    fn read_events(path: &Path) -> Vec<serde_json::Value> {
        std::fs::read_to_string(path)
            .unwrap()
            .lines()
            .filter(|l| !l.is_empty())
            .map(|l| serde_json::from_str(l).expect("every journal line must be valid JSON"))
            .collect()
    }

    #[test]
    fn test_reopen_seq_continuity() {
        let path = temp_path("reopen");
        {
            let mut journal = Journal::open(&path).unwrap();
            journal.event("a", fields()).unwrap();
            journal.event("b", fields()).unwrap();
            assert_eq!(journal.seq(), 2);
        }
        {
            let mut journal = Journal::open(&path).unwrap();
            assert_eq!(journal.seq(), 2, "seq must resume from the durable tail");
            journal.event("c", fields()).unwrap();
            assert_eq!(journal.seq(), 3);
        }
        let events = read_events(&path);
        let seqs: Vec<u64> = events
            .iter()
            .map(|e| e["seq"].as_u64().expect("seq field"))
            .collect();
        assert_eq!(seqs, vec![1, 2, 3]);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn test_flush_durability_write_read_back() {
        let path = temp_path("flush");
        let mut journal = Journal::open(&path).unwrap();
        journal.event("decision", fields()).unwrap();
        journal.event("refusal", fields()).unwrap();

        let events = read_events(&path);
        assert_eq!(events.len(), 2);
        assert_eq!(events[0]["type"], "decision");
        assert_eq!(events[1]["type"], "refusal");
        assert_eq!(events[1]["seq"], 2);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn test_partial_trailing_line_is_repaired_on_reopen() {
        let path = temp_path("partial");
        {
            let mut journal = Journal::open(&path).unwrap();
            journal.event("a", fields()).unwrap();
            journal.event("b", fields()).unwrap();
        }
        {
            let mut file = OpenOptions::new().append(true).open(&path).unwrap();
            file.write_all(b"{\"seq\":3,\"type\":\"trunc").unwrap();
            file.flush().unwrap();
        }
        {
            let mut journal = Journal::open(&path).unwrap();
            assert_eq!(journal.seq(), 2, "truncated tail must not advance seq");
            journal.event("c", fields()).unwrap();
        }
        let events = read_events(&path);
        assert_eq!(events.len(), 3);
        assert_eq!(events[2]["seq"], 3);
        assert_eq!(events[2]["type"], "c");
        let _ = std::fs::remove_file(&path);
    }
}
