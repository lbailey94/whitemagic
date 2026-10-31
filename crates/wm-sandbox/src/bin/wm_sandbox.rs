use std::env;
use std::path::PathBuf;
use wm_sandbox::{SandboxBuilder, probe_sandbox_status, run_self_test};

fn print_help() {
    println!(
        r#"wm-sandbox — WhiteMagic Landlock ABI 8 + cgroup v2 Process Sandboxing Engine

USAGE:
    wm-sandbox [OPTIONS] -- <cmd> [args...]
    wm-sandbox --probe
    wm-sandbox --test

OPTIONS:
    --ro <paths>        Colon-delimited paths granted Read-Only access
                        Default: /usr:/lib:/lib64:/bin:/sbin:/etc:/proc:/dev/urandom:/dev/null:/dev/zero
    --rw <paths>        Colon-delimited paths granted Read-Write access
                        Default: /tmp:.
    --net               Allow outbound/inbound TCP networking (default: Zero Egress)
    --no-ipc-scope      Disable abstract unix socket and signal isolation
    --mem <MB>          Memory limit via cgroup v2 (e.g. 512M)
    --pids <max>        Tasks limit via cgroup v2 (e.g. 64)
    --probe             Output JSON status of host kernel sandboxing capabilities
    --test              Execute self-test battery verifying Landlock ABI 8 confinement
    -h, --help          Print this help message
"#
    );
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_help();
        std::process::exit(1);
    }

    if args.contains(&"--help".to_string()) || args.contains(&"-h".to_string()) {
        print_help();
        return;
    }

    if args.contains(&"--probe".to_string()) {
        let status = probe_sandbox_status();
        println!("{}", serde_json::to_string_pretty(&status).unwrap());
        return;
    }

    if args.contains(&"--test".to_string()) {
        if run_self_test() {
            std::process::exit(0);
        } else {
            std::process::exit(1);
        }
    }

    let mut builder = SandboxBuilder::new();
    let mut cmd_start_idx = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--" => {
                cmd_start_idx = Some(i + 1);
                break;
            }
            "--ro" => {
                if i + 1 < args.len() {
                    let paths: Vec<PathBuf> = args[i + 1].split(':').map(PathBuf::from).collect();
                    builder.ro_paths.extend(paths);
                    i += 1;
                }
            }
            "--rw" => {
                if i + 1 < args.len() {
                    let paths: Vec<PathBuf> = args[i + 1].split(':').map(PathBuf::from).collect();
                    builder.rw_paths.extend(paths);
                    i += 1;
                }
            }
            "--net" => {
                builder.allow_net = true;
            }
            "--no-ipc-scope" => {
                builder.scope_ipc = false;
            }
            "--mem" => {
                if i + 1 < args.len() {
                    builder.memory_limit = Some(args[i + 1].clone());
                    i += 1;
                }
            }
            "--pids" => {
                if i + 1 < args.len() {
                    if let Ok(limit) = args[i + 1].parse::<u32>() {
                        builder.pids_limit = Some(limit);
                    }
                    i += 1;
                }
            }
            _ => {
                // If not an option and we haven't seen '--', treat first non-flag as cmd
                if !args[i].starts_with('-') {
                    cmd_start_idx = Some(i);
                    break;
                }
            }
        }
        i += 1;
    }

    let Some(cmd_idx) = cmd_start_idx else {
        eprintln!("[wm-sandbox] ERROR: No command specified to run.");
        print_help();
        std::process::exit(1);
    };

    if cmd_idx >= args.len() {
        eprintln!("[wm-sandbox] ERROR: Empty command after '--'");
        std::process::exit(1);
    }

    let target_cmd = &args[cmd_idx];
    let target_args = &args[cmd_idx + 1..];

    builder.execute_sandboxed(target_cmd, target_args);
}
