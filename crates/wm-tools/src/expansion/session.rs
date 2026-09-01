//! Session tools — start, checkpoint, recall, end, verify.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use wm_core::{
    Context, EffectRow, EpisodicKind, Galaxy, Gana, ProvenanceSource, Resource, Tool, ToolStats,
};
use wm_memory::{Memory, MemoryStore};

/// Capture verifiable git state from a repository root.
///
/// Returns `None` when the path is not a git repository or `git` is
/// unavailable — callers degrade gracefully to manual payloads.
fn capture_git_state(root: &Path) -> Option<Value> {
    let run = |git_args: &[&str]| -> Option<String> {
        let out = std::process::Command::new("git")
            .args(git_args)
            .current_dir(root)
            // Index refresh is a write to .git/ — under Landlock confinement
            // (writes confined to the store root) it would fail, and it is
            // needless wear for a read-only capture. GIT_OPTIONAL_LOCKS=0
            // disables the refresh so `status --porcelain` stays truthful.
            .env("GIT_OPTIONAL_LOCKS", "0")
            .output()
            .ok()?;
        if out.status.success() {
            Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
        } else {
            None
        }
    };
    // A bare directory passes `rev-parse` only if it is inside a work tree;
    // `--is-inside-work-tree` is the cheap sanity gate.
    run(&["rev-parse", "--is-inside-work-tree"])?;
    let commit = run(&["rev-parse", "HEAD"]).unwrap_or_default();
    let branch = run(&["rev-parse", "--abbrev-ref", "HEAD"]).unwrap_or_default();
    let dirty_count = run(&["status", "--porcelain"]).map_or(0, |s| s.lines().count());
    Some(json!({
        "commit": commit,
        "branch": branch,
        "dirty_count": dirty_count,
    }))
}

/// Resolve the project root for git capture: explicit arg wins over the
/// `WM_PROJECT_ROOT` environment variable; empty values are treated unset.
fn resolve_project_root(args: &Value) -> Option<PathBuf> {
    args.get("root")
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            std::env::var("WM_PROJECT_ROOT")
                .ok()
                .filter(|s| !s.is_empty())
                .map(PathBuf::from)
        })
}

/// Latest session-start id by creation time (`created_at`, not LMDB key
/// order — see session_ops resolution fix).
fn latest_session_start(store: &MemoryStore) -> Option<String> {
    store
        .scan_all(Galaxy::Sessions)
        .ok()?
        .iter()
        .filter(|m| m.metadata.tags.contains(&"start".to_string()))
        .max_by_key(|m| m.metadata.created_at)
        .map(|m| m.metadata.id.to_string())
}

/// `session.start` — create a new session memory.
pub struct SessionStartTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionStartTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sessions".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SessionStartTool {
    fn name(&self) -> &str {
        "session.start"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "title": super::common::str_prop("Session title"),
                "user": super::common::str_prop("User identifier (default 'default')"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Start a new session — creates a session memory in Sessions galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let title = args
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("Untitled Session");
        let user = args
            .get("user")
            .and_then(|v| v.as_str())
            .unwrap_or("default");
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_start",
                "title": title,
                "user": user,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "start".into()];
        mem.metadata.importance = 0.7;
        // Machine-captured event — claims system provenance, never user.
        mem.metadata.source = "system".to_string();
        mem.metadata.source_trust = 0.7;
        self.store.put(Galaxy::Sessions, &mem)?;
        crate::capture_explicit_memory(
            &self.store,
            &mem,
            EpisodicKind::SystemEvent,
            ProvenanceSource::System,
            Some(mem.metadata.id),
            0,
        );
        Ok(json!({
            "status": "success",
            "session_id": mem.metadata.id,
            "title": title,
            "user": user,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.checkpoint` — save a checkpoint in a session.
pub struct SessionCheckpointTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionCheckpointTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sessions".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SessionCheckpointTool {
    fn name(&self) -> &str {
        "session.checkpoint"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "session_id": super::common::str_prop("Target session (default: most recent session)"),
                "label": super::common::str_prop("Checkpoint label (default 'checkpoint')"),
                "data": {
                    "type": "object",
                    "description": "Legacy free-form passthrough stored beside the handoff."
                },
                "commit": super::common::str_prop("Manual commit hash (auto-captured from git when root/WM_PROJECT_ROOT is set)"),
                "branch": super::common::str_prop("Manual branch name (auto-captured when git is available)"),
                "tests_green": {
                    "type": "boolean",
                    "description": "Whether the test suite was green at checkpoint time."
                },
                "next_queue": {
                    "type": "array",
                    "description": "Ordered next-step strings for the next session."
                },
                "open_flags": {
                    "type": "array",
                    "description": "Open concerns/flags worth surfacing on resume."
                },
                "lease_id": super::common::str_prop("Claimed scope (code.claim lease_id) that remains held at this handoff"),
                "root": super::common::str_prop("Repository root for auto git-capture (default: WM_PROJECT_ROOT env)"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Save a session checkpoint with a verifiable structured handoff: commit, branch, dirty count (auto-captured from git via WM_PROJECT_ROOT), tests_green, next_queue, open_flags, lease_id (a code.claim scope that stays held)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = match args.get("session_id").and_then(|v| v.as_str()) {
            Some(sid) if !sid.is_empty() => sid.to_string(),
            _ => latest_session_start(&self.store).ok_or_else(|| {
                wm_core::CoreError::Tool("no session found — run session.start first".into())
            })?,
        };
        let label = args
            .get("label")
            .and_then(|v| v.as_str())
            .unwrap_or("checkpoint");
        let data = args.get("data").cloned().unwrap_or_else(|| json!({}));

        // Structured handoff (P0): explicit arguments win; git state is
        // auto-captured so the common case records truth without effort.
        let git_state = resolve_project_root(&args).and_then(|root| capture_git_state(&root));
        let mut handoff = json!({});
        {
            let h = handoff.as_object_mut().expect("just created");
            for (key, value) in [
                ("commit", args.get("commit")),
                ("branch", args.get("branch")),
                ("tests_green", args.get("tests_green")),
                ("next_queue", args.get("next_queue")),
                ("open_flags", args.get("open_flags")),
                ("lease_id", args.get("lease_id")),
            ] {
                if value.is_some() {
                    h.insert(key.to_string(), value.cloned().expect("checked above"));
                }
            }
            if let Some(git) = git_state {
                h.insert("git".to_string(), git);
            }
        }

        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "checkpoint",
                "session_id": session_id,
                "label": label,
                "data": data,
                "handoff": handoff,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "checkpoint".into()];
        mem.metadata.importance = 0.5;
        // Machine-captured event — claims system provenance, never user.
        mem.metadata.source = "system".to_string();
        mem.metadata.source_trust = 0.7;
        self.store.put(Galaxy::Sessions, &mem)?;
        crate::capture_explicit_memory(
            &self.store,
            &mem,
            EpisodicKind::SystemEvent,
            ProvenanceSource::System,
            uuid::Uuid::parse_str(&session_id).ok(),
            0,
        );
        Ok(json!({
            "status": "success",
            "checkpoint_id": mem.metadata.id,
            "session_id": session_id,
            "label": label,
            "handoff": handoff,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.verify` — grade stored checkpoint state against live git reality.
///
/// Self-correcting memory: the checkpoint asserted "HEAD was X, N files
/// dirty"; this compares that assertion to the repository now and reports
/// drift (commits ahead, dirty-count delta) so a future session knows how
/// much it can trust the handoff before acting on it.
pub struct SessionVerifyTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionVerifyTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
impl Tool for SessionVerifyTool {
    fn name(&self) -> &str {
        "session.verify"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "session_id": super::common::str_prop("Session whose latest checkpoint to verify (default: most recent session)"),
                "root": super::common::str_prop("Repository root to verify against (default: WM_PROJECT_ROOT env)"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Verify a session's stored checkpoint against live git state — reports commit drift and dirty-count delta ('your memory says HEAD was X; git says Y')."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = match args.get("session_id").and_then(|v| v.as_str()) {
            Some(sid) if !sid.is_empty() => sid.to_string(),
            _ => latest_session_start(&self.store).ok_or_else(|| {
                wm_core::CoreError::Tool("no session found — run session.start first".into())
            })?,
        };

        // Latest verifiable checkpoint for this session: handoff.git.commit
        // present. Checkpoints from before structured handoffs are skipped.
        let memories = self.store.scan_all(Galaxy::Sessions)?;
        let stored = memories
            .iter()
            .filter(|m| {
                m.metadata.tags.contains(&"checkpoint".to_string())
                    && m.content.contains(&session_id)
            })
            .filter_map(|m| {
                let parsed: Value = serde_json::from_str(&m.content).ok()?;
                let git = parsed.get("handoff")?.get("git")?.clone();
                if git.get("commit").and_then(Value::as_str).is_some() {
                    Some((m.metadata.id.to_string(), m.metadata.created_at, git))
                } else {
                    None
                }
            })
            .max_by_key(|(_, created_at, _)| *created_at);

        let Some((checkpoint_id, _, stored_git)) = stored else {
            return Ok(json!({
                "status": "success",
                "verifiable": false,
                "message": "no checkpoint with captured git state found for this session — checkpoint with WM_PROJECT_ROOT set (or an explicit root) to enable verification"
            }));
        };

        let Some(root) = resolve_project_root(&args) else {
            return Ok(json!({
                "status": "error",
                "checkpoint_id": checkpoint_id,
                "stored_git": stored_git,
                "message": "no repository root available — pass 'root' or set WM_PROJECT_ROOT to verify against live git"
            }));
        };
        let Some(current_git) = capture_git_state(&root) else {
            return Ok(json!({
                "status": "error",
                "checkpoint_id": checkpoint_id,
                "stored_git": stored_git,
                "message": format!("'{}' is not a usable git work tree", root.display())
            }));
        };

        let stored_commit = stored_git["commit"].as_str().unwrap_or_default();
        let current_commit = current_git["commit"].as_str().unwrap_or_default();
        let commits_ahead = if stored_commit == current_commit {
            Some(0)
        } else {
            std::process::Command::new("git")
                .args(["rev-list", "--count", &format!("{stored_commit}..HEAD")])
                .current_dir(&root)
                .output()
                .ok()
                .filter(|o| o.status.success())
                .and_then(|o| {
                    String::from_utf8_lossy(&o.stdout)
                        .trim()
                        .parse::<u64>()
                        .ok()
                })
        };
        let dirty_delta = current_git["dirty_count"].as_i64().unwrap_or(0)
            - stored_git["dirty_count"].as_i64().unwrap_or(0);

        let verdict = if stored_commit == current_commit && dirty_delta == 0 {
            "clean"
        } else if stored_commit == current_commit {
            "dirty-drift"
        } else {
            "drifted"
        };

        Ok(json!({
            "status": "success",
            "verifiable": true,
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
            "stored_git": stored_git,
            "current_git": current_git,
            "commits_ahead": commits_ahead,
            "dirty_delta": dirty_delta,
            "verdict": verdict,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.recall` — retrieve session memories.
pub struct SessionRecallTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionRecallTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SessionRecallTool {
    fn name(&self) -> &str {
        "session.recall"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Recall session memories by session_id"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = args
            .get("session_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let memories = self.store.scan_all(Galaxy::Sessions)?;
        let filtered: Vec<Value> = memories
            .iter()
            .filter(|m| m.content.contains(session_id))
            .take(limit)
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "tags": m.metadata.tags,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "session_id": session_id,
            "count": filtered.len(),
            "memories": filtered,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.end` — end a session.
pub struct SessionEndTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionEndTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sessions".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SessionEndTool {
    fn name(&self) -> &str {
        "session.end"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "End a session — writes a session_end marker"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = args
            .get("session_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let summary = args.get("summary").and_then(|v| v.as_str()).unwrap_or("");
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_end",
                "session_id": session_id,
                "summary": summary,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "end".into()];
        mem.metadata.importance = 0.6;
        // Machine-captured event — claims system provenance, never user.
        mem.metadata.source = "system".to_string();
        mem.metadata.source_trust = 0.7;
        self.store.put(Galaxy::Sessions, &mem)?;
        crate::capture_explicit_memory(
            &self.store,
            &mem,
            EpisodicKind::SystemEvent,
            ProvenanceSource::System,
            uuid::Uuid::parse_str(session_id).ok(),
            0,
        );
        Ok(json!({
            "status": "success",
            "session_id": session_id,
            "end_id": mem.metadata.id,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("lmdb");
        std::fs::create_dir_all(&path).unwrap();
        Arc::new(MemoryStore::open_default(path).unwrap())
    }

    fn start_session(store: &MemoryStore) -> String {
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({"type": "session_start"}).to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "start".into()];
        store.put(Galaxy::Sessions, &mem).unwrap();
        mem.metadata.id.to_string()
    }

    /// Fresh local git repository with one empty initial commit — returns
    /// its path.
    fn git_repo() -> (tempfile::TempDir, PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().to_path_buf();
        let run = |args: &[&str]| {
            std::process::Command::new("git")
                .args(args)
                .current_dir(&root)
                .output()
                .expect("git must be available")
        };
        assert!(run(&["init", "-q"]).status.success());
        assert!(run(&["config", "user.email", "t@t"]).status.success());
        assert!(run(&["config", "user.name", "t"]).status.success());
        assert!(
            run(&["commit", "--allow-empty", "-m", "c1"])
                .status
                .success()
        );
        (dir, root)
    }

    /// Machine events claim system provenance (never user) — the
    /// sessions-galaxy attribution fix (2026-08-29).
    #[tokio::test]
    async fn start_marker_stamps_system_provenance() {
        let store = test_store();
        let tool = SessionStartTool::new(store.clone());
        let mut ctx = Context::default();
        let out = tool
            .call(&mut ctx, json!({"title": "prov test"}))
            .await
            .unwrap();
        let sid = uuid::Uuid::parse_str(out["session_id"].as_str().unwrap()).unwrap();
        let mem = store
            .get(Galaxy::Sessions, sid)
            .expect("start stored")
            .expect("start present");
        assert_eq!(mem.metadata.source, "system");
        assert!((mem.metadata.source_trust - 0.7).abs() < 1e-5);
    }

    #[tokio::test]
    async fn checkpoint_auto_captures_git_state() {
        let store = test_store();
        let sid = start_session(&store);
        let (_guard, root) = git_repo();

        let tool = SessionCheckpointTool::new(store.clone());
        let mut ctx = Context::default();
        let r = tool
            .call(
                &mut ctx,
                json!({"session_id": sid, "root": root.display().to_string(), "tests_green": true}),
            )
            .await
            .unwrap();

        assert_eq!(r["status"], "success");
        let git = &r["handoff"]["git"];
        let expected = String::from_utf8(
            std::process::Command::new("git")
                .args(["rev-parse", "HEAD"])
                .current_dir(&root)
                .output()
                .unwrap()
                .stdout,
        )
        .unwrap();
        assert_eq!(
            git["commit"].as_str().unwrap().trim(),
            expected.trim(),
            "checkpoint must auto-capture the live HEAD"
        );
        assert_eq!(git["dirty_count"], 0);
        assert_eq!(r["handoff"]["tests_green"], true);
    }

    #[tokio::test]
    async fn checkpoint_resolves_latest_session_when_absent() {
        let store = test_store();
        let _old = start_session(&store);
        let newest = start_session(&store);

        let tool = SessionCheckpointTool::new(store);
        let mut ctx = Context::default();
        let r = tool.call(&mut ctx, json!({"label": "wrap"})).await.unwrap();

        assert_eq!(r["status"], "success");
        assert_eq!(r["session_id"], newest, "must target the newest session");
    }

    #[tokio::test]
    async fn verify_reports_clean_then_drifted() {
        let store = test_store();
        let sid = start_session(&store);
        let (dir_guard, root) = git_repo();
        let root_str = root.display().to_string();

        let cp = SessionCheckpointTool::new(store.clone());
        let mut ctx = Context::default();
        cp.call(&mut ctx, json!({"session_id": sid, "root": root_str}))
            .await
            .unwrap();

        let verify = SessionVerifyTool::new(store.clone());
        let clean = verify
            .call(&mut ctx, json!({"session_id": sid, "root": root_str}))
            .await
            .unwrap();
        assert_eq!(clean["verifiable"], true);
        assert_eq!(clean["verdict"], "clean", "got: {clean}");
        assert_eq!(clean["commits_ahead"], 0);

        // Land a second commit behind the checkpoint's back.
        assert!(
            std::process::Command::new("git")
                .args(["commit", "--allow-empty", "-m", "c2"])
                .current_dir(&root)
                .output()
                .unwrap()
                .status
                .success()
        );

        let drifted = verify
            .call(&mut ctx, json!({"session_id": sid, "root": root_str}))
            .await
            .unwrap();
        assert_eq!(drifted["verdict"], "drifted", "got: {drifted}");
        assert_eq!(drifted["commits_ahead"], 1);
        assert_ne!(
            drifted["stored_git"]["commit"],
            drifted["current_git"]["commit"]
        );

        drop(dir_guard);
    }

    #[tokio::test]
    async fn checkpoint_carries_lease_id_in_handoff() {
        let store = test_store();
        let sid = start_session(&store);

        let tool = SessionCheckpointTool::new(store);
        let mut ctx = Context::default();
        let r = tool
            .call(
                &mut ctx,
                json!({"session_id": sid, "lease_id": "src/expansion/"}),
            )
            .await
            .unwrap();

        assert_eq!(r["status"], "success");
        assert_eq!(r["handoff"]["lease_id"], "src/expansion/");
    }

    #[tokio::test]
    async fn verify_reports_unverifiable_without_git_checkpoint() {
        let store = test_store();
        let sid = start_session(&store);

        // Legacy-style checkpoint: data passthrough only, no handoff.git.
        let cp = SessionCheckpointTool::new(store.clone());
        let mut ctx = Context::default();
        // NOTE: no `root` arg and WM_PROJECT_ROOT unset in the test env.
        let r = cp.call(&mut ctx, json!({"session_id": sid})).await.unwrap();
        assert!(r["handoff"]["git"].is_null());

        let verify = SessionVerifyTool::new(store);
        let v = verify
            .call(&mut ctx, json!({"session_id": sid}))
            .await
            .unwrap();
        assert_eq!(v["verifiable"], false, "got: {v}");
        assert!(v["message"].as_str().unwrap().contains("no checkpoint"));
    }
}
