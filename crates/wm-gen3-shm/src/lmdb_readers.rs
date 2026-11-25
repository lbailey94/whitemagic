//! Safe wrapper around `liblmdb` reader-table diagnostics and stale-PID reclamation.
//!
//! `lmdb` 0.8 omits wrappers for `mdb_reader_check`, `mdb_reader_list`, and
//! `mdb_env_get_maxreaders`. Isolating those FFI calls in `wm-gen3-shm` keeps
//! `#![forbid(unsafe_code)]` intact across `wm-gen3-core` and `wm-gen3-harness`.

use std::ffi::CStr;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// Snapshot of a single occupied slot in LMDB's `lock.mdb` reader table.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReaderSlotInfo {
    pub pid: i32,
    pub thread: String,
    pub active_txnid: Option<u64>,
    pub alive: Option<bool>,
}

/// Summary of an LMDB environment's `lock.mdb` reader-lock table.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReaderTableSnapshot {
    pub max_readers: u32,
    pub occupied: usize,
    pub live: usize,
    pub dead: usize,
    pub free: usize,
    pub slots: Vec<ReaderSlotInfo>,
}

extern "C" fn collect_reader_line(msg: *const libc::c_char, ctx: *mut libc::c_void) -> libc::c_int {
    if msg.is_null() || ctx.is_null() {
        return 0;
    }
    // SAFETY: `liblmdb` passes a NUL-terminated static/stack line buffer and the
    // `&mut Vec<String>` pointer supplied to `mdb_reader_list` in `inspect_readers`.
    let line = unsafe { CStr::from_ptr(msg) }
        .to_string_lossy()
        .into_owned();
    let lines = unsafe { &mut *(ctx.cast::<Vec<String>>()) };
    lines.push(line);
    0
}

#[cfg(unix)]
fn is_pid_alive(pid: i32) -> Option<bool> {
    if pid <= 0 {
        return Some(false);
    }
    // SAFETY: `kill(pid, 0)` probes process existence without delivering a signal.
    let rc = unsafe { libc::kill(pid, 0) };
    if rc == 0 {
        return Some(true);
    }
    match std::io::Error::last_os_error().raw_os_error() {
        Some(libc::EPERM) => Some(true),
        Some(libc::ESRCH) => Some(false),
        _ => None,
    }
}

#[cfg(not(unix))]
fn is_pid_alive(_pid: i32) -> Option<bool> {
    None
}

fn parse_reader_line(line: &str) -> Option<ReaderSlotInfo> {
    let trimmed = line.trim();
    if trimmed.is_empty() || trimmed.starts_with('(') {
        return None;
    }
    let mut parts = trimmed.split_whitespace();
    let pid = parts.next()?.parse::<i32>().ok()?;
    let thread = parts.next()?.to_string();
    let txnid_token = parts.next()?;
    let active_txnid = if txnid_token == "-" {
        None
    } else {
        txnid_token.parse::<u64>().ok()
    };
    Some(ReaderSlotInfo {
        pid,
        thread,
        active_txnid,
        alive: is_pid_alive(pid),
    })
}

/// Reclaim stale reader-table slots left behind by crashed or SIGKILL'd processes.
pub fn clear_stale_readers(env: &lmdb::Environment) -> Result<usize, lmdb::Error> {
    let mut dead: libc::c_int = 0;
    // SAFETY: `env.env()` returns a live `MDB_env *` valid for `&lmdb::Environment`.
    let rc = unsafe { lmdb_sys::mdb_reader_check(env.env(), &mut dead) };
    if rc == 0 {
        Ok(usize::try_from(dead.max(0)).unwrap_or(0))
    } else {
        Err(lmdb::Error::from_err_code(rc))
    }
}

/// Return the environment's effective `max_readers` slot capacity.
pub fn max_readers(env: &lmdb::Environment) -> Result<u32, lmdb::Error> {
    let mut max: libc::c_uint = 0;
    // SAFETY: `env.env()` returns a live `MDB_env *` valid for `&lmdb::Environment`.
    let rc = unsafe { lmdb_sys::mdb_env_get_maxreaders(env.env(), &mut max) };
    if rc == 0 {
        Ok(max)
    } else {
        Err(lmdb::Error::from_err_code(rc))
    }
}

/// Inspect live and stale entries currently registered in `env`'s `lock.mdb` reader table.
pub fn inspect_readers(env: &lmdb::Environment) -> Result<ReaderTableSnapshot, lmdb::Error> {
    let cap = max_readers(env)?;
    let mut lines: Vec<String> = Vec::new();
    let cb: lmdb_sys::MDB_msg_func = collect_reader_line;
    // `lmdb-sys` typed `func` as `*mut MDB_msg_func` even though `MDB_msg_func` is already a
    // C function pointer (`typedef int (MDB_msg_func)(...)`), so `liblmdb` invokes the address.
    let cb_ptr = (cb as *const ())
        .cast_mut()
        .cast::<lmdb_sys::MDB_msg_func>();
    // SAFETY: `env.env()` is valid, `cb_ptr` points to `collect_reader_line`, and `ctx`
    // exclusively borrows `lines` for the synchronous duration of `mdb_reader_list`.
    let rc = unsafe {
        lmdb_sys::mdb_reader_list(env.env(), cb_ptr, (&raw mut lines).cast::<libc::c_void>())
    };
    if rc < 0 {
        return Err(lmdb::Error::from_err_code(rc));
    }
    let slots: Vec<ReaderSlotInfo> = lines
        .iter()
        .filter_map(|line| parse_reader_line(line))
        .collect();
    let occupied = slots.len();
    let dead = slots.iter().filter(|s| s.alive == Some(false)).count();
    let live = occupied.saturating_sub(dead);
    let free = (cap as usize).saturating_sub(occupied);
    Ok(ReaderTableSnapshot {
        max_readers: cap,
        occupied,
        live,
        dead,
        free,
        slots,
    })
}

fn open_locked_readonly(store_path: &Path) -> Result<lmdb::Environment, lmdb::Error> {
    let mut builder = lmdb::Environment::new();
    builder
        .set_max_dbs(16)
        .set_flags(lmdb::EnvironmentFlags::READ_ONLY | lmdb::EnvironmentFlags::NO_TLS);
    builder.open_with_permissions(store_path, 0o600)
}

/// Inspect `lock.mdb` reader slots at `store_path` without creating missing files.
pub fn inspect_readers_at_path(
    store_path: &Path,
) -> Result<Option<ReaderTableSnapshot>, lmdb::Error> {
    if !store_path.join("lock.mdb").is_file() || !store_path.join("data.mdb").is_file() {
        return Ok(None);
    }
    let env = open_locked_readonly(store_path)?;
    Ok(Some(inspect_readers(&env)?))
}

/// Reclaim stale reader slots in `store_path/lock.mdb` without disturbing live servers.
pub fn reclaim_stale_readers_at_path(store_path: &Path) -> Result<usize, lmdb::Error> {
    if !store_path.join("lock.mdb").is_file() || !store_path.join("data.mdb").is_file() {
        return Ok(0);
    }
    let env = open_locked_readonly(store_path)?;
    clear_stale_readers(&env)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    struct TempDir(PathBuf);

    impl TempDir {
        fn new(label: &str) -> Self {
            let path =
                std::env::temp_dir().join(format!("wm-shm-{label}-{}", uuid::Uuid::new_v4()));
            std::fs::create_dir_all(&path).expect("create temp dir");
            Self(path)
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn missing_store_returns_none_and_zero_without_creating_dir() {
        let missing = std::env::temp_dir().join(format!("wm-shm-missing-{}", uuid::Uuid::new_v4()));
        assert!(!missing.exists());
        assert_eq!(inspect_readers_at_path(&missing).unwrap(), None);
        assert_eq!(reclaim_stale_readers_at_path(&missing).unwrap(), 0);
        assert!(
            !missing.exists(),
            "reader inspection must never create dirs"
        );
    }

    #[test]
    fn no_tls_releases_reader_slot_immediately_and_honors_max_readers() {
        let tmp = TempDir::new("no-tls");
        let mut builder = lmdb::Environment::new();
        builder
            .set_max_dbs(16)
            .set_max_readers(512)
            .set_flags(lmdb::EnvironmentFlags::NO_TLS);
        let env = builder.open_with_permissions(&tmp.0, 0o600).unwrap();
        assert_eq!(max_readers(&env).unwrap(), 512);

        let txn = env.begin_ro_txn().unwrap();
        let active = inspect_readers(&env).unwrap();
        assert_eq!(active.occupied, 1);
        assert_eq!(active.live, 1);
        assert_eq!(active.dead, 0);
        assert_eq!(active.free, 511);
        drop(txn);

        let after = inspect_readers(&env).unwrap();
        assert_eq!(after.occupied, 0);
        assert_eq!(after.free, 512);
    }

    #[cfg(unix)]
    #[test]
    fn helper_pin_stale_reader_slot() {
        let Ok(dir) = std::env::var("WM_TEST_PIN_STALE_READER_DIR") else {
            return;
        };
        let mut builder = lmdb::Environment::new();
        builder.set_max_dbs(16).set_max_readers(2);
        let env = builder
            .open_with_permissions(Path::new(&dir), 0o600)
            .unwrap();
        let txn = env.begin_ro_txn().unwrap();
        // Leak txn + env and exit via `_exit(0)` so pthread TLS destructors do not
        // clear the reader slot, faithfully simulating a SIGKILL'd reader process.
        std::mem::forget(txn);
        std::mem::forget(env);
        unsafe { libc::_exit(0) };
    }

    #[cfg(unix)]
    #[test]
    fn reclaim_recovers_from_real_stale_readers_full() {
        let tmp = TempDir::new("stale-full");
        let mut builder = lmdb::Environment::new();
        builder
            .set_max_dbs(16)
            .set_max_readers(2)
            .set_flags(lmdb::EnvironmentFlags::NO_TLS);
        let env = builder.open_with_permissions(&tmp.0, 0o600).unwrap();
        let exe = std::env::current_exe().expect("current_exe");

        for _ in 0..2 {
            let status = std::process::Command::new(&exe)
                .arg("--exact")
                .arg("lmdb_readers::tests::helper_pin_stale_reader_slot")
                .env("WM_TEST_PIN_STALE_READER_DIR", &tmp.0)
                .status()
                .expect("spawn stale reader child");
            assert!(status.success(), "child helper failed: {status}");
        }

        assert_eq!(env.begin_ro_txn().unwrap_err(), lmdb::Error::ReadersFull);

        let wedged = inspect_readers(&env).unwrap();
        assert_eq!(wedged.max_readers, 2);
        assert_eq!(wedged.occupied, 2);
        assert_eq!(wedged.dead, 2);
        assert_eq!(wedged.free, 0);

        let reclaimed = clear_stale_readers(&env).unwrap();
        assert_eq!(reclaimed, 2);

        let txn = env
            .begin_ro_txn()
            .expect("ro txn succeeds after clearing stale slots");
        drop(txn);

        let healed = inspect_readers(&env).unwrap();
        assert_eq!(healed.occupied, 0);
        assert_eq!(healed.dead, 0);
        assert_eq!(healed.free, 2);
    }
}
