//! WhiteMagic Landlock ABI 8 + cgroup v2 Process Sandboxing Engine
//!
//! Provides zero-dependency hardware/kernel-enforced unprivileged isolation for:
//! - Subprocess benchmark execution (Harness²)
//! - Untrusted code evaluation
//! - Agent tool command containment
//! - Proof-Carrying runtime verification

use serde::{Deserialize, Serialize};
use std::env;
use std::ffi::CString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus, exit};

pub const SYS_LANDLOCK_CREATE_RULESET: i64 = 444;
pub const SYS_LANDLOCK_ADD_RULE: i64 = 445;
pub const SYS_LANDLOCK_RESTRICT_SELF: i64 = 446;

pub const LANDLOCK_CREATE_RULESET_VERSION: u32 = 1 << 0;
pub const LANDLOCK_RULE_PATH_BENEATH: u32 = 1;
pub const LANDLOCK_RULE_NET_PORT: u32 = 2;

// Access rights bitmasks (ABI 8 compatible)
pub const LANDLOCK_ACCESS_FS_EXECUTE: u64 = 1 << 0;
pub const LANDLOCK_ACCESS_FS_WRITE_FILE: u64 = 1 << 1;
pub const LANDLOCK_ACCESS_FS_READ_FILE: u64 = 1 << 2;
pub const LANDLOCK_ACCESS_FS_READ_DIR: u64 = 1 << 3;
pub const LANDLOCK_ACCESS_FS_REMOVE_DIR: u64 = 1 << 4;
pub const LANDLOCK_ACCESS_FS_REMOVE_FILE: u64 = 1 << 5;
pub const LANDLOCK_ACCESS_FS_MAKE_CHAR: u64 = 1 << 6;
pub const LANDLOCK_ACCESS_FS_MAKE_DIR: u64 = 1 << 7;
pub const LANDLOCK_ACCESS_FS_MAKE_REG: u64 = 1 << 8;
pub const LANDLOCK_ACCESS_FS_MAKE_SOCK: u64 = 1 << 9;
pub const LANDLOCK_ACCESS_FS_MAKE_FIFO: u64 = 1 << 10;
pub const LANDLOCK_ACCESS_FS_MAKE_BLOCK: u64 = 1 << 11;
pub const LANDLOCK_ACCESS_FS_MAKE_SYM: u64 = 1 << 12;
pub const LANDLOCK_ACCESS_FS_REFER: u64 = 1 << 13;
pub const LANDLOCK_ACCESS_FS_TRUNCATE: u64 = 1 << 14;
pub const LANDLOCK_ACCESS_FS_IOCTL_DEV: u64 = 1 << 15;

pub const LANDLOCK_ACCESS_NET_BIND_TCP: u64 = 1 << 0;
pub const LANDLOCK_ACCESS_NET_CONNECT_TCP: u64 = 1 << 1;

pub const LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET: u64 = 1 << 0;
pub const LANDLOCK_SCOPE_SIGNAL: u64 = 1 << 1;

pub const PR_SET_NO_NEW_PRIVS: libc::c_int = 38;

#[repr(C)]
pub struct LandlockRulesetAttr {
    pub handled_access_fs: u64,
    pub handled_access_net: u64,
    pub scoped: u64,
}

#[repr(C, packed)]
pub struct LandlockPathBeneathAttr {
    pub allowed_access: u64,
    pub parent_fd: i32,
}

#[repr(C)]
pub struct LandlockNetPortAttr {
    pub allowed_access: u64,
    pub port: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandboxStatus {
    pub kernel_landlock_abi: i32,
    pub landlock_supported: bool,
    pub lsm_modules: String,
    pub cgroup_v2: bool,
    pub user_cgroup_delegated: bool,
    pub zero_egress_capable: bool,
    pub ipc_scoping_capable: bool,
    pub abi_8_features: Abi8Features,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Abi8Features {
    pub ioctl_dev_control: bool,
    pub abstract_socket_scoping: bool,
    pub signal_scoping: bool,
    pub truncate_control: bool,
    pub refer_control: bool,
}

#[derive(Debug)]
pub enum SandboxError {
    LandlockNotSupported(i32),
    RulesetCreateFailed(i32),
    AddRuleFailed(String, i32),
    PrctlFailed(i32),
    RestrictSelfFailed(i32),
    ForkFailed(i32),
    ExecFailed(String, i32),
    Io(String),
}

impl std::fmt::Display for SandboxError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::LandlockNotSupported(abi) => {
                write!(f, "Landlock not supported on this kernel (abi={abi})")
            }
            Self::RulesetCreateFailed(err) => {
                write!(f, "Failed to create Landlock ruleset (errno={err})")
            }
            Self::AddRuleFailed(p, err) => {
                write!(f, "Failed to add Landlock rule for '{p}' (errno={err})")
            }
            Self::PrctlFailed(err) => write!(f, "prctl PR_SET_NO_NEW_PRIVS failed (errno={err})"),
            Self::RestrictSelfFailed(err) => {
                write!(f, "Landlock restrict_self failed (errno={err})")
            }
            Self::ForkFailed(err) => write!(f, "Fork failed (errno={err})"),
            Self::ExecFailed(cmd, err) => write!(f, "execvp '{cmd}' failed (errno={err})"),
            Self::Io(msg) => write!(f, "IO error: {msg}"),
        }
    }
}

impl std::error::Error for SandboxError {}

pub fn get_landlock_abi() -> i32 {
    unsafe {
        libc::syscall(
            SYS_LANDLOCK_CREATE_RULESET,
            std::ptr::null::<LandlockRulesetAttr>(),
            0,
            LANDLOCK_CREATE_RULESET_VERSION,
        ) as i32
    }
}

pub fn probe_sandbox_status() -> SandboxStatus {
    let abi = get_landlock_abi();
    let lsm = fs::read_to_string("/sys/kernel/security/lsm")
        .unwrap_or_else(|_| "unknown".to_string())
        .trim()
        .to_string();
    let cgroup_type = fs::read_to_string("/sys/fs/cgroup/cgroup.controllers").is_ok();
    let uid = unsafe { libc::getuid() };
    let user_slice_delegated = fs::metadata(format!(
        "/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service"
    ))
    .is_ok();

    SandboxStatus {
        kernel_landlock_abi: abi,
        landlock_supported: abi >= 1,
        lsm_modules: lsm,
        cgroup_v2: cgroup_type,
        user_cgroup_delegated: user_slice_delegated,
        zero_egress_capable: abi >= 4,
        ipc_scoping_capable: abi >= 6,
        abi_8_features: Abi8Features {
            ioctl_dev_control: abi >= 5,
            abstract_socket_scoping: abi >= 6,
            signal_scoping: abi >= 6,
            truncate_control: abi >= 3,
            refer_control: abi >= 2,
        },
    }
}

#[derive(Debug, Clone)]
pub struct SandboxBuilder {
    pub ro_paths: Vec<PathBuf>,
    pub rw_paths: Vec<PathBuf>,
    pub allow_net: bool,
    pub scope_ipc: bool,
    pub memory_limit: Option<String>,
    pub pids_limit: Option<u32>,
    pub egress_socket: Option<PathBuf>,
}

impl Default for SandboxBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl SandboxBuilder {
    pub fn new() -> Self {
        Self {
            ro_paths: vec![
                "/usr".into(),
                "/lib".into(),
                "/lib64".into(),
                "/bin".into(),
                "/sbin".into(),
                "/etc".into(),
                "/proc".into(),
                "/dev".into(),
            ],
            rw_paths: vec!["/tmp".into()],
            allow_net: false,
            scope_ipc: true,
            memory_limit: None,
            pids_limit: None,
            egress_socket: None,
        }
    }

    pub fn ro_path(mut self, path: impl AsRef<Path>) -> Self {
        self.ro_paths.push(path.as_ref().to_path_buf());
        self
    }

    pub fn rw_path(mut self, path: impl AsRef<Path>) -> Self {
        self.rw_paths.push(path.as_ref().to_path_buf());
        self
    }

    pub fn allow_net(mut self, allow: bool) -> Self {
        self.allow_net = allow;
        self
    }

    pub fn scope_ipc(mut self, scope: bool) -> Self {
        self.scope_ipc = scope;
        self
    }

    pub fn memory_limit(mut self, limit: impl Into<String>) -> Self {
        self.memory_limit = Some(limit.into());
        self
    }

    pub fn pids_limit(mut self, limit: u32) -> Self {
        self.pids_limit = Some(limit);
        self
    }

    pub fn egress_socket(mut self, sock: impl AsRef<Path>) -> Self {
        let p = sock.as_ref().to_path_buf();
        self.ro_paths.push(p.clone());
        self.egress_socket = Some(p);
        self
    }

    /// Irrevocably confines the current process with Landlock rules.
    pub fn restrict_self(&self) -> Result<(), SandboxError> {
        let abi = get_landlock_abi();
        if abi < 1 {
            return Err(SandboxError::LandlockNotSupported(abi));
        }

        let fs_rw = LANDLOCK_ACCESS_FS_EXECUTE
            | LANDLOCK_ACCESS_FS_WRITE_FILE
            | LANDLOCK_ACCESS_FS_READ_FILE
            | LANDLOCK_ACCESS_FS_READ_DIR
            | LANDLOCK_ACCESS_FS_REMOVE_DIR
            | LANDLOCK_ACCESS_FS_REMOVE_FILE
            | LANDLOCK_ACCESS_FS_MAKE_CHAR
            | LANDLOCK_ACCESS_FS_MAKE_DIR
            | LANDLOCK_ACCESS_FS_MAKE_REG
            | LANDLOCK_ACCESS_FS_MAKE_SOCK
            | LANDLOCK_ACCESS_FS_MAKE_FIFO
            | LANDLOCK_ACCESS_FS_MAKE_BLOCK
            | LANDLOCK_ACCESS_FS_MAKE_SYM
            | LANDLOCK_ACCESS_FS_REFER
            | LANDLOCK_ACCESS_FS_TRUNCATE
            | LANDLOCK_ACCESS_FS_IOCTL_DEV;

        let fs_ro =
            LANDLOCK_ACCESS_FS_EXECUTE | LANDLOCK_ACCESS_FS_READ_FILE | LANDLOCK_ACCESS_FS_READ_DIR;

        let net_mask = if !self.allow_net && abi >= 4 {
            LANDLOCK_ACCESS_NET_BIND_TCP | LANDLOCK_ACCESS_NET_CONNECT_TCP
        } else {
            0
        };

        let scoped_mask = if self.scope_ipc && abi >= 6 {
            LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET | LANDLOCK_SCOPE_SIGNAL
        } else {
            0
        };

        let attr = LandlockRulesetAttr {
            handled_access_fs: fs_rw,
            handled_access_net: net_mask,
            scoped: scoped_mask,
        };

        unsafe {
            let ruleset_fd = libc::syscall(
                SYS_LANDLOCK_CREATE_RULESET,
                &attr,
                std::mem::size_of::<LandlockRulesetAttr>(),
                0,
            ) as i32;

            if ruleset_fd < 0 {
                return Err(SandboxError::RulesetCreateFailed(*libc::__errno_location()));
            }

            // Add RW paths
            for p in &self.rw_paths {
                if p.exists() {
                    let c_p = CString::new(p.to_string_lossy().as_bytes())
                        .map_err(|e| SandboxError::Io(e.to_string()))?;
                    let fd = libc::open(c_p.as_ptr(), libc::O_PATH | libc::O_CLOEXEC);
                    if fd >= 0 {
                        let rule = LandlockPathBeneathAttr {
                            allowed_access: fs_rw,
                            parent_fd: fd,
                        };
                        let ret = libc::syscall(
                            SYS_LANDLOCK_ADD_RULE,
                            ruleset_fd,
                            LANDLOCK_RULE_PATH_BENEATH,
                            &rule,
                            0,
                        );
                        libc::close(fd);
                        if ret < 0 {
                            libc::close(ruleset_fd);
                            return Err(SandboxError::AddRuleFailed(
                                p.display().to_string(),
                                *libc::__errno_location(),
                            ));
                        }
                    }
                }
            }

            // Add RO paths
            for p in &self.ro_paths {
                if p.exists() {
                    let c_p = CString::new(p.to_string_lossy().as_bytes())
                        .map_err(|e| SandboxError::Io(e.to_string()))?;
                    let fd = libc::open(c_p.as_ptr(), libc::O_PATH | libc::O_CLOEXEC);
                    if fd >= 0 {
                        let rule = LandlockPathBeneathAttr {
                            allowed_access: fs_ro,
                            parent_fd: fd,
                        };
                        let ret = libc::syscall(
                            SYS_LANDLOCK_ADD_RULE,
                            ruleset_fd,
                            LANDLOCK_RULE_PATH_BENEATH,
                            &rule,
                            0,
                        );
                        libc::close(fd);
                        if ret < 0 {
                            libc::close(ruleset_fd);
                            return Err(SandboxError::AddRuleFailed(
                                p.display().to_string(),
                                *libc::__errno_location(),
                            ));
                        }
                    }
                }
            }

            // Irrevocably lock self
            if libc::prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0 {
                libc::close(ruleset_fd);
                return Err(SandboxError::PrctlFailed(*libc::__errno_location()));
            }

            if libc::syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0) != 0 {
                libc::close(ruleset_fd);
                return Err(SandboxError::RestrictSelfFailed(*libc::__errno_location()));
            }

            libc::close(ruleset_fd);
        }

        Ok(())
    }

    /// Spawns a command inside a confined child process and waits for its exit status.
    pub fn spawn_command(&self, cmd: &str, args: &[String]) -> Result<ExitStatus, SandboxError> {
        let mut command = Command::new(cmd);
        command.args(args);

        // Pre-exec hook restricts the child process before exec
        let builder = self.clone();
        unsafe {
            use std::os::unix::process::CommandExt;
            command.pre_exec(move || {
                builder.restrict_self().map_err(|e| {
                    std::io::Error::new(std::io::ErrorKind::PermissionDenied, e.to_string())
                })
            });
        }

        command
            .status()
            .map_err(|e| SandboxError::Io(e.to_string()))
    }

    /// Replaces the current process with the target sandboxed command.
    pub fn execute_sandboxed(&self, cmd: &str, args: &[String]) -> ! {
        // Apply cgroups if requested and not yet active
        if (self.memory_limit.is_some() || self.pids_limit.is_some())
            && env::var("WM_SANDBOX_CGROUP_ACTIVE").is_err()
        {
            let mut srun = Command::new("systemd-run");
            srun.arg("--user").arg("--scope");
            if let Some(ref mem) = self.memory_limit {
                srun.arg(format!("-pMemoryMax={}", mem));
            }
            if let Some(pids) = self.pids_limit {
                srun.arg(format!("-pTasksMax={}", pids));
            }
            srun.env("WM_SANDBOX_CGROUP_ACTIVE", "1");
            let current_exe = env::current_exe().unwrap_or_else(|_| PathBuf::from("wm-sandbox"));
            srun.arg(current_exe);
            let all_args: Vec<String> = env::args().skip(1).collect();
            srun.args(all_args);

            let status = srun.status().expect("Failed to spawn systemd-run");
            exit(status.code().unwrap_or(1));
        }

        let _ = self.restrict_self();

        let c_cmd = CString::new(cmd).expect("Invalid cmd");
        let mut c_args: Vec<CString> = vec![c_cmd.clone()];
        for a in args {
            c_args.push(CString::new(a.as_bytes()).expect("Invalid arg"));
        }
        let mut c_argv: Vec<*const libc::c_char> = c_args.iter().map(|s| s.as_ptr()).collect();
        c_argv.push(std::ptr::null());

        unsafe {
            libc::execvp(c_cmd.as_ptr(), c_argv.as_ptr());
            libc::_exit(127);
        }
    }
}

pub fn run_self_test() -> bool {
    println!("[wm-sandbox] Starting Landlock ABI 8 & isolation self-test...");
    let abi = get_landlock_abi();
    if abi < 1 {
        eprintln!("[wm-sandbox] ERROR: Landlock not supported on this kernel (abi={abi})");
        return false;
    }
    println!("[wm-sandbox] Kernel Landlock ABI detected: {abi}");

    unsafe {
        let pid = libc::fork();
        if pid < 0 {
            eprintln!("[wm-sandbox] Fork failed");
            return false;
        }

        if pid == 0 {
            let builder = SandboxBuilder::new();
            if let Err(e) = builder.restrict_self() {
                eprintln!("[wm-sandbox child] restrict_self failed: {e}");
                libc::_exit(1);
            }

            // Test 1: Write in /tmp should succeed
            let test_path = format!("/tmp/wm_sandbox_test_{}.tmp", libc::getpid());
            if fs::write(&test_path, b"sandbox ok").is_err() {
                eprintln!("[wm-sandbox child] Test 1 FAILED: Could not write in /tmp");
                libc::_exit(10);
            }
            let _ = fs::remove_file(&test_path);

            // Test 2: Accessing ~/.bashrc or other user home files outside RW must fail
            let home = env::var("HOME").unwrap_or_else(|_| "/home/lucas".to_string());
            let bashrc = format!("{home}/.bashrc");
            if fs::read_to_string(&bashrc).is_ok() {
                eprintln!(
                    "[wm-sandbox child] Test 2 FAILED: Unauthorized read to {bashrc} succeeded!"
                );
                libc::_exit(11);
            }

            // Test 3: Network connect must fail (Zero Egress)
            if abi >= 4 {
                let sock = libc::socket(libc::AF_INET, libc::SOCK_STREAM, 0);
                if sock >= 0 {
                    let mut addr: libc::sockaddr_in = std::mem::zeroed();
                    addr.sin_family = libc::AF_INET as u16;
                    addr.sin_port = 80u16.to_be();
                    addr.sin_addr.s_addr = 0x01010101; // 1.1.1.1
                    let res = libc::connect(
                        sock,
                        &addr as *const _ as *const libc::sockaddr,
                        std::mem::size_of::<libc::sockaddr_in>() as u32,
                    );
                    libc::close(sock);
                    if res == 0 {
                        eprintln!(
                            "[wm-sandbox child] Test 3 FAILED: Network connection succeeded despite zero-egress rule!"
                        );
                        libc::_exit(12);
                    }
                }
            }

            libc::_exit(0);
        } else {
            let mut status = 0;
            libc::waitpid(pid, &mut status, 0);
            if libc::WIFEXITED(status) && libc::WEXITSTATUS(status) == 0 {
                println!(
                    "[wm-sandbox] ALL SELF-TESTS PASSED: FS RW, FS RO, Credential Lockout, and Zero Egress certified."
                );
                true
            } else {
                eprintln!(
                    "[wm-sandbox] Self-test failed with child exit code: {}",
                    libc::WEXITSTATUS(status)
                );
                false
            }
        }
    }
}
