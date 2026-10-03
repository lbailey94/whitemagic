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
        let file = OpenOptions::new().create(true).append(true).open(path)?;
        Ok(Self {
            file,
            path: path.to_path_buf(),
            seq: 0,
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
