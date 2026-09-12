//! Store writer-contention preflight for CLI write paths.
//!
//! `wm ingest` and `wm migrate` open the store's LMDB environment and the
//! Tantivy index for writing. When another process already holds the Tantivy
//! writer lock — a writable `wm serve` on the same store, as heritage runs —
//! the open blocks inside the lock acquisition with no output at all: it is
//! indistinguishable from a hang. Observed 2026-09-11: `wm migrate --dry-run`
//! silent for 18 minutes and `wm ingest` silent for 10+ minutes against a
//! served store, both completing in seconds once the serve was stopped.
//!
//! This module detects holders BEFORE the open so the CLI can fail fast with
//! process names and a remedy, or wait a bounded time (`--wait <secs>`).
//! Detection is advisory diagnostics, not a lock: the actual writer lock
//! remains Tantivy's.

#[cfg(not(unix))]
use std::path::Path;

/// A process holding the store (writer-lock holder or a live serve).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoreHolder {
    pub pid: u32,
    pub cmdline: String,
}

#[cfg(unix)]
mod imp {
    use super::StoreHolder;
    use std::os::unix::fs::MetadataExt;
    use std::path::Path;
    use std::time::{Duration, Instant};

    /// Fail-fast (or bounded-wait) guard for CLI write paths.
    ///
    /// Polls until the store is free, or `wait_secs` elapses, then returns an
    /// error naming every detected holder and the remedy.
    pub fn ensure_store_available(store_path: &Path, wait_secs: u64) -> anyhow::Result<()> {
        let start = Instant::now();
        loop {
            let holders = store_holders(store_path);
            if holders.is_empty() {
                return Ok(());
            }
            if start.elapsed().as_secs() < wait_secs {
                std::thread::sleep(Duration::from_secs(1));
                continue;
            }
            let list = holders
                .iter()
                .map(|h| {
                    let cmd: String = h.cmdline.chars().take(160).collect();
                    format!("  pid {} — {}", h.pid, cmd)
                })
                .collect::<Vec<_>>()
                .join("\n");
            anyhow::bail!(
                "store is busy: {} process(es) hold it:\n{}\n\
                 Stop the serving unit (`systemctl --user stop wm-serve@<name>`) \
                 or re-run with --wait <seconds>.",
                holders.len(),
                list
            );
        }
    }

    /// All detected holders for `store_path` (writer-lock holders plus live
    /// serves), deduplicated by pid.
    #[must_use]
    pub fn store_holders(store_path: &Path) -> Vec<StoreHolder> {
        store_holders_in(Path::new("/proc"), store_path)
    }

    pub(super) fn store_holders_in(proc_root: &Path, store_path: &Path) -> Vec<StoreHolder> {
        let mut holders: Vec<StoreHolder> = Vec::new();
        let mut push = |pid: u32| {
            if holders.iter().any(|h| h.pid == pid) {
                return;
            }
            holders.push(StoreHolder {
                pid,
                cmdline: read_cmdline(proc_root, pid),
            });
        };

        if let Some(inode) = writer_lock_inode(store_path) {
            for pid in locks_writers(&proc_root.join("locks"), inode) {
                push(pid);
            }
        }
        for pid in serving_pids(proc_root, store_path) {
            push(pid);
        }
        holders.sort_by_key(|h| h.pid);
        holders
    }

    /// Inode of `<store>/lmdb/tantivy/.tantivy-writer.lock`, if the index
    /// exists.
    fn writer_lock_inode(store_path: &Path) -> Option<u64> {
        let lock = store_path
            .join("lmdb")
            .join("tantivy")
            .join(".tantivy-writer.lock");
        std::fs::metadata(lock).ok().map(|m| m.ino())
    }

    /// PIDs with a WRITE lock on `inode`, parsed from `/proc/locks`:
    /// `131: FLOCK ADVISORY WRITE 1932 103:02:7077941 0 EOF`
    fn locks_writers(locks_path: &Path, inode: u64) -> Vec<u32> {
        let Ok(text) = std::fs::read_to_string(locks_path) else {
            return Vec::new();
        };
        parse_locks_writers(&text, inode)
    }

    pub(super) fn parse_locks_writers(text: &str, inode: u64) -> Vec<u32> {
        let mut pids = Vec::new();
        for line in text.lines() {
            let fields: Vec<&str> = line.split_whitespace().collect();
            // fields: index: type mode write pid dev:inode start end
            if fields.len() < 6 || fields[3] != "WRITE" {
                continue;
            }
            let Some(dev_inode) = fields.get(5) else {
                continue;
            };
            let Some(ino) = dev_inode.rsplit(':').next() else {
                continue;
            };
            if ino.parse::<u64>() == Ok(inode) {
                if let Ok(pid) = fields[4].parse::<u32>() {
                    pids.push(pid);
                }
            }
        }
        pids
    }

    fn serving_pids(proc_root: &Path, store_path: &Path) -> Vec<u32> {
        let Ok(entries) = std::fs::read_dir(proc_root) else {
            return Vec::new();
        };
        let self_pid = std::process::id();
        let mut pids = Vec::new();
        for entry in entries.flatten() {
            let Some(name) = entry.file_name().to_str().map(str::to_string) else {
                continue;
            };
            let Ok(pid) = name.parse::<u32>() else {
                continue;
            };
            if pid == self_pid {
                continue;
            }
            let cmdline = read_cmdline(proc_root, pid);
            if is_serving_cmdline(&cmdline, store_path) {
                pids.push(pid);
            }
        }
        pids
    }

    pub(super) fn is_serving_cmdline(cmdline: &str, store_path: &Path) -> bool {
        let args: Vec<&str> = cmdline.split(' ').filter(|a| !a.is_empty()).collect();
        let serves = args.contains(&"serve");
        if !serves {
            return false;
        }
        // A `--readonly` serve takes no writer lock and no write transactions
        // (LMDB MVCC + Tantivy read-only open), so it cannot block a writer —
        // it must not be reported as a holder.
        if args.contains(&"--readonly") {
            return false;
        }
        let store = store_path.to_string_lossy();
        args.iter()
            .any(|a| *a == store || a.contains(store.as_ref()))
    }

    fn read_cmdline(proc_root: &Path, pid: u32) -> String {
        let path = proc_root.join(pid.to_string()).join("cmdline");
        let Ok(bytes) = std::fs::read(&path) else {
            return "(unknown)".to_string();
        };
        let joined = bytes
            .split(|b| *b == 0)
            .filter(|s| !s.is_empty())
            .map(|s| String::from_utf8_lossy(s).to_string())
            .collect::<Vec<_>>()
            .join(" ");
        let trimmed = joined.trim();
        if trimmed.is_empty() {
            "(empty)".to_string()
        } else {
            // Full command line: holder detection reads flags that can sit
            // past any truncation (--readonly). Display truncation happens
            // at the error-message seam only.
            trimmed.to_string()
        }
    }
}

#[cfg(unix)]
pub use imp::{ensure_store_available, store_holders};

#[cfg(not(unix))]
#[must_use]
pub fn store_holders(_store_path: &Path) -> Vec<StoreHolder> {
    Vec::new()
}

#[cfg(not(unix))]
pub fn ensure_store_available(_store_path: &Path, _wait_secs: u64) -> anyhow::Result<()> {
    Ok(())
}

#[cfg(all(test, unix))]
mod tests {
    use super::imp::{is_serving_cmdline, parse_locks_writers, store_holders_in};
    use std::path::Path;

    #[test]
    fn locks_writers_finds_write_holder_by_inode() {
        let text = "\
1: POSIX  ADVISORY  READ  100 103:02:5 0 0
131: FLOCK  ADVISORY  WRITE 1932 103:02:7077941 0 EOF
132: FLOCK  ADVISORY  READ  200 103:02:7077941 0 EOF
";
        assert_eq!(parse_locks_writers(text, 7_077_941), vec![1932]);
        assert!(parse_locks_writers(text, 999).is_empty());
    }

    #[test]
    fn serving_cmdline_requires_writable_serve_and_store() {
        let store = Path::new("/data/vault");
        assert!(is_serving_cmdline(
            "/home/u/.local/bin/wm serve --profile curated --store /data/vault",
            store
        ));
        assert!(
            !is_serving_cmdline(
                "/home/u/.local/bin/wm serve --store /data/vault --readonly",
                store
            ),
            "readonly serves hold no writer resources and must not block"
        );
        assert!(!is_serving_cmdline(
            "/home/u/.local/bin/wm serve --store /data/other",
            store
        ));
        assert!(!is_serving_cmdline(
            "/usr/bin/editor /data/vault/notes.md",
            store
        ));
    }

    #[test]
    fn store_holders_in_detects_fake_serve_process() {
        let tmp = tempfile::tempdir().unwrap();
        let store = tmp.path().join("store");
        std::fs::create_dir_all(store.join("lmdb/tantivy")).unwrap();
        // no writer lock file: only the cmdline scan should fire
        let pid_dir = tmp.path().join("4242");
        std::fs::create_dir_all(&pid_dir).unwrap();
        let cmdline = format!("wm\0serve\0--store\0{}\0", store.display());
        std::fs::write(pid_dir.join("cmdline"), cmdline).unwrap();

        let holders = store_holders_in(tmp.path(), &store);
        assert_eq!(holders.len(), 1, "exactly the fake serve must be detected");
        assert_eq!(holders[0].pid, 4242);
        assert!(holders[0].cmdline.contains("serve"));
    }
}
