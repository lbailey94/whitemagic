use serde::{Deserialize, Deserializer};
use std::env;
use std::path::PathBuf;
use wm_sandbox::{SandboxBuilder, probe_sandbox_status, run_self_test};

const ENVELOPE_SCHEMA: &str = "wm-sandbox-exec-v1";

fn default_schema() -> String {
    ENVELOPE_SCHEMA.to_string()
}

fn present_string<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Option<String>, D::Error> {
    String::deserialize(deserializer).map(Some)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ExecutionEnvelope {
    #[serde(default = "default_schema")]
    schema: String,
    program: String,
    #[serde(default)]
    args: Vec<String>,
    #[serde(default)]
    net: bool,
    #[serde(default, deserialize_with = "present_string")]
    workspace: Option<String>,
    #[serde(default)]
    rw: bool,
    #[serde(default)]
    egress: Vec<String>,
}

impl ExecutionEnvelope {
    fn parse(json: &str) -> Result<Self, String> {
        let envelope: Self = serde_json::from_str(json).map_err(|error| error.to_string())?;
        if envelope.schema != ENVELOPE_SCHEMA {
            return Err("unsupported envelope schema".to_string());
        }
        if envelope.program.is_empty() || envelope.program.contains('\0') {
            return Err("program must be nonempty and contain no NUL".to_string());
        }
        if envelope.args.iter().any(|arg| arg.contains('\0')) {
            return Err("args must contain no NUL".to_string());
        }
        if let Some(workspace) = &envelope.workspace {
            if workspace.is_empty() || workspace.contains('\0') {
                return Err("workspace must be nonempty and contain no NUL".to_string());
            }
        } else if envelope.rw {
            return Err("rw requires a workspace".to_string());
        }
        if !envelope.egress.is_empty() {
            return Err("destination egress allowlists are unsupported by this runner".to_string());
        }
        Ok(envelope)
    }

    fn configure(self, builder: &mut SandboxBuilder) -> (String, Vec<String>) {
        builder.allow_net = self.net;
        if let Some(workspace) = self.workspace {
            if self.rw {
                builder.rw_paths.push(workspace.into());
            } else {
                builder.ro_paths.push(workspace.into());
            }
        }
        (self.program, self.args)
    }
}

fn print_help() {
    println!(
        r#"wm-sandbox — WhiteMagic Landlock ABI 8 + cgroup v2 Process Sandboxing Engine

USAGE:
    wm-sandbox [OPTIONS] -- <cmd> [args...]
    wm-sandbox --exec '<json envelope>'
    wm-sandbox --probe
    wm-sandbox --test

OPTIONS:
    --exec '<json>'     Execute a strict wm-sandbox-exec-v1 JSON envelope
                        Nonempty destination egress allowlists are unsupported
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
            "--exec" => {
                if i + 1 < args.len() {
                    let envelope_str = &args[i + 1];
                    let envelope = ExecutionEnvelope::parse(envelope_str).unwrap_or_else(|e| {
                        eprintln!("[wm-sandbox] ERROR: invalid JSON envelope: {e}");
                        std::process::exit(64);
                    });
                    let (program, exec_args) = envelope.configure(&mut builder);
                    builder.execute_sandboxed(&program, &exec_args);
                } else {
                    eprintln!("[wm-sandbox] ERROR: --exec requires a JSON envelope argument");
                    std::process::exit(64);
                }
            }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn envelope_preserves_literal_arguments_and_applies_explicit_builder_flags() {
        for net in [false, true] {
            for rw in [false, true] {
                let json = serde_json::json!({
                    "schema": ENVELOPE_SCHEMA,
                    "program": "/usr/bin/printf",
                    "args": ["", "a b", "--net", "雪", "$HOME"],
                    "workspace": "/tmp/workspace with spaces",
                    "rw": rw,
                    "net": net,
                    "egress": [],
                });
                let mut builder = SandboxBuilder::new();
                let (program, args) = ExecutionEnvelope::parse(&json.to_string())
                    .unwrap()
                    .configure(&mut builder);
                assert_eq!(program, "/usr/bin/printf");
                assert_eq!(args, ["", "a b", "--net", "雪", "$HOME"]);
                assert_eq!(builder.allow_net, net);
                let workspace = PathBuf::from("/tmp/workspace with spaces");
                assert_eq!(builder.rw_paths.contains(&workspace), rw);
                assert_eq!(builder.ro_paths.contains(&workspace), !rw);
                // Envelope workspace access adds to the runner's default paths.
                assert!(builder.rw_paths.contains(&PathBuf::from("/tmp")));
            }
        }
    }

    #[test]
    fn omitted_optional_fields_keep_existing_defaults() {
        let mut builder = SandboxBuilder::new().allow_net(true);
        let (program, args) = ExecutionEnvelope::parse(r#"{"program":"echo"}"#)
            .unwrap()
            .configure(&mut builder);
        assert_eq!(program, "echo");
        assert!(args.is_empty());
        assert!(!builder.allow_net);
    }
}
