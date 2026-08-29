//! Multi-agent coordination — file-based claim leases (`code.claim` v0).
//!
//! Phase 2 of the v7→v9 strategy: the coordination substrate from the
//! two-writer postmortem. One writer per checkout is the rule; these tools
//! make the rule *visible*. Leases live in the git common dir
//! (`$(git rev-parse --git-common-dir)/wm-leases.json`) so every worktree
//! of a checkout reads and writes the same ledger.
//!
//! Design (from `planning/STRATEGY_V7_V9.md` Phase 2):
//! - Advisory only — claims are coordination signals, not locks. No
//!   enforcement hooks, no merge radar; those are v1/v2.
//! - Entries carry a mandatory intent, an owner session, and a TTL.
//!   Expired leases prune lazily and the scope frees itself — a dead
//!   session cannot hold a scope forever.
//! - All mutations are lockfile-guarded read-modify-write with atomic
//!   rename, so two agents racing on one ledger cannot corrupt it.
//! - Claim/release/denied publish to the Gan Ying bus when one is wired.
//!
//! Research surface: registered on the full profile only (curated stays
//! the alpha contract surface).

#![forbid(unsafe_code)]

use async_trait::async_trait;

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use wm_cognitive::{EventType, GanYingBus};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};

/// Default lease TTL — one hour covers a focused work stretch; renewal is
/// a single re-claim with the same owner.
const DEFAULT_TTL_SECS: i64 = 3600;
/// Maximum TTL — a claim is coordination state, not a tombstone.
const MAX_TTL_SECS: i64 = 86_400;
/// Lockfile older than this is stale (a crashed writer) and gets stolen.
const STALE_LOCK_SECS: i64 = 30;
const LOCK_ATTEMPTS: usize = 150;
const LOCK_SLEEP_MS: u64 = 10;

/// One claim lease in the shared ledger.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Lease {
    /// What is claimed — a path, a subtree, or any resource label the
    /// agents agree on (`"src/expansion/"`, `"benchmarks/harness"`, …).
    pub scope: String,
    /// Why the scope is claimed. Mandatory — an intent-less claim is
    /// noise, and the conflict result must be able to explain the holder.
    pub intent: String,
    /// Claiming session (session id from `session.start`, or a stable
    /// agent label). Release requires a matching owner.
    pub owner_session: String,
    /// RFC 3339 claim time.
    pub claimed_at: String,
    /// RFC 3339 expiry — past this, the lease prunes lazily.
    pub expires_at: String,
    /// Requested TTL in seconds (recorded for diagnosis).
    pub ttl_secs: i64,
}

#[derive(Debug, Default, Serialize, Deserialize)]
struct LeaseFile {
    version: u8,
    leases: Vec<Lease>,
}

/// The shared ledger: `<git-common-dir>/wm-leases.json`.
#[derive(Debug, Clone)]
pub struct LeaseLedger {
    path: PathBuf,
}

impl LeaseLedger {
    /// Discover the ledger for a repository root. Requires a git checkout
    /// (worktree or bare-adjacent): the common dir is what makes leases
    /// visible across all worktrees.
    pub fn discover(root: &Path) -> wm_core::Result<Self> {
        let out = std::process::Command::new("git")
            .args(["rev-parse", "--git-common-dir"])
            .current_dir(root)
            .output()
            .map_err(|e| {
                CoreError::Tool(format!(
                    "code.claim could not run git ({e}) — pass root=<repo path> or set WM_PROJECT_ROOT to a git checkout"
                ))
            })?;
        if !out.status.success() {
            return Err(CoreError::Tool(
                "code.claim requires a git repository — pass root=<repo path> (or set WM_PROJECT_ROOT) pointing at a checkout; leases live in <git-common-dir>/wm-leases.json".into(),
            ));
        }
        let dir = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if dir.is_empty() {
            return Err(CoreError::Tool(
                "git rev-parse --git-common-dir returned nothing for this root".into(),
            ));
        }
        let common = PathBuf::from(&dir);
        let common = if common.is_absolute() {
            common
        } else {
            root.join(common)
        };
        Ok(Self {
            path: common.join("wm-leases.json"),
        })
    }

    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    fn lock_path(&self) -> PathBuf {
        let name = self.path.file_name().map_or_else(
            || "wm-leases.json.lock".to_string(),
            |n| format!("{}.lock", n.to_string_lossy()),
        );
        self.path.with_file_name(name)
    }

    /// Acquire the ledger lock. create_new gives us an atomic test-and-set;
    /// a lockfile older than `STALE_LOCK_SECS` belongs to a crashed writer
    /// and is stolen.
    fn acquire_lock(&self) -> wm_core::Result<()> {
        let lock = self.lock_path();
        for _ in 0..LOCK_ATTEMPTS {
            match std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&lock)
            {
                Ok(_) => return Ok(()),
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
                    if let Ok(meta) = std::fs::metadata(&lock) {
                        if let Ok(modified) = meta.modified() {
                            let age = DateTime::<Utc>::from(modified);
                            if Utc::now() - age > Duration::seconds(STALE_LOCK_SECS) {
                                let _ = std::fs::remove_file(&lock);
                                continue;
                            }
                        }
                    }
                    std::thread::sleep(std::time::Duration::from_millis(LOCK_SLEEP_MS));
                }
                Err(e) => {
                    return Err(CoreError::Tool(format!(
                        "could not create lease lock {}: {e}",
                        lock.display()
                    )));
                }
            }
        }
        Err(CoreError::Tool(format!(
            "lease ledger is busy (lock held past {}s) — retry shortly: {}",
            (LOCK_ATTEMPTS as u64 * LOCK_SLEEP_MS) / 1000,
            lock.display()
        )))
    }

    fn release_lock(&self) {
        let _ = std::fs::remove_file(self.lock_path());
    }

    fn parse_file(&self) -> Vec<Lease> {
        let Ok(raw) = std::fs::read_to_string(&self.path) else {
            return Vec::new();
        };
        let Ok(parsed) = serde_json::from_str::<LeaseFile>(&raw) else {
            // A corrupt ledger must never wedge coordination: treat it as
            // empty (advisory system; the next successful write rebuilds).
            tracing::warn!(
                path = %self.path.display(),
                "wm-leases.json unreadable — treating ledger as empty"
            );
            return Vec::new();
        };
        parsed.leases
    }

    /// Run `f` against the active leases under the ledger lock, prune
    /// expired entries, and atomically persist the result. Expired leases
    /// are returned so callers can surface the transition.
    fn mutate<T>(
        &self,
        f: impl FnOnce(&mut Vec<Lease>, &[Lease]) -> wm_core::Result<T>,
    ) -> wm_core::Result<T> {
        if let Some(parent) = self.path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| {
                CoreError::Tool(format!("could not create {}: {e}", parent.display()))
            })?;
        }
        self.acquire_lock()?;
        let result = (|| {
            let now = Utc::now();
            let all = self.parse_file();
            let (mut active, expired): (Vec<Lease>, Vec<Lease>) =
                all.into_iter()
                    .partition(|l| match DateTime::parse_from_rfc3339(&l.expires_at) {
                        Ok(exp) => exp.with_timezone(&Utc) > now,
                        Err(_) => false, // unparseable expiry = expired
                    });
            let pre = active.clone();
            let out = f(&mut active, &expired)?;
            // Persist only on real change — pure reads (check/list on a
            // stable ledger) must not rewrite the file, and an expired
            // lease is reported once, at its discovery transition.
            if active == pre && expired.is_empty() {
                return Ok(out);
            }
            let file = LeaseFile {
                version: 1,
                leases: active,
            };
            let tmp = self
                .path
                .with_file_name(format!("wm-leases.json.tmp.{}", std::process::id()));
            let body = serde_json::to_string_pretty(&file)
                .map_err(|e| CoreError::Tool(format!("lease serialization failed: {e}")))?;
            std::fs::write(&tmp, body)
                .map_err(|e| CoreError::Tool(format!("lease write failed: {e}")))?;
            std::fs::rename(&tmp, &self.path)
                .map_err(|e| CoreError::Tool(format!("lease atomic rename failed: {e}")))?;
            Ok(out)
        })();
        self.release_lock();
        result
    }

    /// Active leases plus anything that expired since the last write.
    pub(crate) fn snapshot(&self) -> wm_core::Result<(Vec<Lease>, Vec<Lease>)> {
        self.mutate(|active, expired| Ok((active.clone(), expired.to_vec())))
    }

    // ── Bridge API (F-1): mesh-side scope coordination ────────────────
    //
    // `wm-leases.json` is the durable, cross-process substrate for scope
    // coordination; the sangha `ResourceLockManager` is the per-process
    // mesh-runtime view. These methods let mesh tools record their scope
    // claims in the durable ledger so agents coordinating through either
    // surface see the same truth (`code.list`, `code.check`, or plain bash
    // against the ledger file).

    /// Claim a scope on behalf of `owner`, atomically.
    ///
    /// Same-owner re-claim is a renewal; a live claim by another owner is a
    /// conflict naming the holder. Expired entries prune lazily as in every
    /// other mutate.
    pub fn try_claim(
        &self,
        scope: &str,
        intent: &str,
        owner: &str,
        ttl_secs: i64,
    ) -> wm_core::Result<Result<Lease, Lease>> {
        let claimed_at = now_rfc3339();
        let expires_at = (Utc::now() + Duration::seconds(ttl_secs))
            .to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        self.mutate(|leases, _expired| {
            if let Some(existing) = leases.iter_mut().find(|l| l.scope == scope) {
                if existing.owner_session == owner {
                    existing.intent = intent.to_string();
                    existing.claimed_at.clone_from(&claimed_at);
                    existing.expires_at.clone_from(&expires_at);
                    existing.ttl_secs = ttl_secs;
                    return Ok(Ok(existing.clone()));
                }
                return Ok(Err(existing.clone()));
            }
            let lease = Lease {
                scope: scope.to_string(),
                intent: intent.to_string(),
                owner_session: owner.to_string(),
                claimed_at: claimed_at.clone(),
                expires_at: expires_at.clone(),
                ttl_secs,
            };
            leases.push(lease.clone());
            Ok(Ok(lease))
        })
    }

    /// Release a scope owner-matched. `Ok(Ok(true))` = released;
    /// `Ok(Ok(false))` = scope was already free (idempotent);
    /// `Ok(Err(holder))` = live claim held by another owner.
    pub fn release_scope(&self, scope: &str, owner: &str) -> wm_core::Result<Result<bool, Lease>> {
        self.mutate(|leases, _expired| {
            let Some(pos) = leases.iter().position(|l| l.scope == scope) else {
                return Ok(Ok(false));
            };
            if leases[pos].owner_session != owner {
                return Ok(Err(leases[pos].clone()));
            }
            leases.remove(pos);
            Ok(Ok(true))
        })
    }

    /// Force-release every live claim held by `peer` whose scope starts with
    /// `prefix`. This is the community override behind the bad-apple rule:
    /// quarantine must not leave a cut-off peer holding shared scopes.
    /// Deliberately bypasses owner matching — the mesh revoked the peer.
    pub fn force_release_peer(&self, peer: &str, prefix: &str) -> wm_core::Result<Vec<String>> {
        self.mutate(|leases, _expired| {
            let mut freed = Vec::new();
            leases.retain(|l| {
                if l.owner_session == peer && l.scope.starts_with(prefix) {
                    freed.push(l.scope.clone());
                    return false;
                }
                true
            });
            Ok(freed)
        })
    }
}

/// RFC 3339 at second precision — the human-facing lease ledger format
/// (convention: `wm_core::time`, unit registry in
/// `docs/TIMESTAMP_CONVENTIONS.md`).
fn now_rfc3339() -> String {
    wm_core::time::now_rfc3339()
}

pub(crate) fn clamp_ttl(ttl: i64) -> wm_core::Result<i64> {
    if !(1..=MAX_TTL_SECS).contains(&ttl) {
        return Err(CoreError::InvalidArgs(format!(
            "ttl_secs must be between 1 and {MAX_TTL_SECS} (a claim is coordination state, not a tombstone)"
        )));
    }
    Ok(ttl)
}

pub(crate) fn require_str(args: &Value, key: &str) -> wm_core::Result<String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .ok_or_else(|| {
            CoreError::InvalidArgs(format!(
                "'{key}' is required and must be a non-empty string"
            ))
        })
}

pub(crate) fn resolve_root(args: &Value) -> wm_core::Result<PathBuf> {
    args.get("root")
        .and_then(|v| v.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            std::env::var("WM_PROJECT_ROOT")
                .ok()
                .filter(|s| !s.trim().is_empty())
                .map(PathBuf::from)
        })
        .ok_or_else(|| {
            CoreError::InvalidArgs(
                "no repository root — pass root=<repo path> or set WM_PROJECT_ROOT".into(),
            )
        })
}

fn emit(gan_ying: Option<&Arc<Mutex<GanYingBus>>>, event_type: EventType, payload: Value) {
    if let Some(bus) = gan_ying {
        if let Ok(mut gy) = bus.lock() {
            gy.emit(event_type, "code.coordination", payload);
        }
    }
}

fn lease_json(lease: &Lease) -> Value {
    json!({
        "lease_id": lease.scope,
        "scope": lease.scope,
        "intent": lease.intent,
        "owner_session": lease.owner_session,
        "claimed_at": lease.claimed_at,
        "expires_at": lease.expires_at,
        "ttl_secs": lease.ttl_secs,
    })
}

const CONFLICT_NEXT_ACTION: &str =
    "wait for expiry, ask the holder to code.release the scope, or claim a different scope";

// ── code.claim ────────────────────────────────────────────────────────

/// `code.claim` — claim a scope before shared-tree edits.
pub struct CodeClaimTool {
    stats: ToolStats,
    effects: EffectRow,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
}

impl CodeClaimTool {
    #[must_use]
    pub fn new(gan_ying: Option<Arc<Mutex<GanYingBus>>>) -> Self {
        Self {
            stats: ToolStats::default(),
            // EffectRow declares data-plane effects (the ledger file), per
            // the session-tools precedent: the fixed-argv `git rev-parse`
            // lookup is the same trust class as checkpoint's git capture,
            // and declaring spawns would push every coordination call
            // against the Yama spawn budget (found live: a two-agent
            // negotiation burst exceeds 6 spawns/min).
            effects: EffectRow {
                reads: vec![Resource::Filesystem],
                writes: vec![Resource::Filesystem],
                ..Default::default()
            },
            gan_ying,
        }
    }
}

#[async_trait]
impl Tool for CodeClaimTool {
    fn name(&self) -> &str {
        "code.claim"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "scope": super::common::str_prop("Scope to claim — path, subtree, or resource label (e.g. 'src/expansion/')"),
                "intent": super::common::str_prop("Why this scope is claimed (mandatory — surfaced to conflicting agents)"),
                "owner_session": super::common::str_prop("Claiming session id (session.start result) or stable agent label"),
                "ttl_secs": super::common::int_prop("Lease TTL in seconds (default 3600, max 86400; expired claims free themselves)"),
                "root": super::common::str_prop("Repository root (default: WM_PROJECT_ROOT env)"),
            }),
            &["scope", "intent", "owner_session"],
        )
    }
    fn description(&self) -> &str {
        "Claim a scope before shared-tree edits (advisory file-based lease with TTL in the git common dir; visible to every worktree). Conflict results name the holder and their intent."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let scope = require_str(&args, "scope")?;
        let intent = require_str(&args, "intent")?;
        let owner = require_str(&args, "owner_session")?;
        let ttl = match args.get("ttl_secs").and_then(serde_json::Value::as_i64) {
            Some(t) => clamp_ttl(t)?,
            None => DEFAULT_TTL_SECS,
        };
        let root = resolve_root(&args)?;
        let ledger = LeaseLedger::discover(&root)?;
        let claimed_at = now_rfc3339();
        let expires_at = (Utc::now() + Duration::seconds(ttl))
            .to_rfc3339_opts(chrono::SecondsFormat::Secs, true);

        let mut newly_expired: Vec<Lease> = Vec::new();
        let result = ledger.mutate(|leases, expired| {
            newly_expired = expired.to_vec();
            if let Some(existing) = leases.iter_mut().find(|l| l.scope == scope) {
                if existing.owner_session == owner {
                    // Renewal: refresh intent and TTL, keep the claim.
                    existing.intent.clone_from(&intent);
                    existing.claimed_at.clone_from(&claimed_at);
                    existing.expires_at.clone_from(&expires_at);
                    existing.ttl_secs = ttl;
                    return Ok(json!({
                        "status": "success",
                        "renewed": true,
                        "lease_id": scope,
                        "scope": scope,
                        "intent": intent,
                        "owner_session": owner,
                        "claimed_at": claimed_at,
                        "expires_at": expires_at,
                        "ttl_secs": ttl,
                        "note": "advisory lease renewed — release with code.release when done"
                    }));
                }
                let holder = existing.clone();
                return Ok(json!({
                    "status": "conflict",
                    "scope": scope,
                    "requested_by": owner,
                    "holder": holder.owner_session,
                    "holder_intent": holder.intent,
                    "claimed_at": holder.claimed_at,
                    "expires_at": holder.expires_at,
                    "next_action": CONFLICT_NEXT_ACTION,
                    "advisory": true,
                }));
            }
            leases.push(Lease {
                scope: scope.clone(),
                intent: intent.clone(),
                owner_session: owner.clone(),
                claimed_at: claimed_at.clone(),
                expires_at: expires_at.clone(),
                ttl_secs: ttl,
            });
            Ok(json!({
                "status": "success",
                "lease_id": scope,
                "scope": scope,
                "intent": intent,
                "owner_session": owner,
                "claimed_at": claimed_at,
                "expires_at": expires_at,
                "ttl_secs": ttl,
                "note": "advisory lease — release with code.release when done"
            }))
        });

        for lease in &newly_expired {
            emit(
                self.gan_ying.as_ref(),
                EventType::CoordinationClaimExpired,
                json!({"scope": lease.scope, "owner_session": lease.owner_session}),
            );
        }

        let result = result?;
        if result["status"] == "success" {
            emit(
                self.gan_ying.as_ref(),
                EventType::CoordinationClaimAcquired,
                json!({"scope": scope, "owner_session": owner, "intent": intent}),
            );
        } else if result["status"] == "conflict" {
            emit(
                self.gan_ying.as_ref(),
                EventType::CoordinationClaimDenied,
                json!({"scope": scope, "requested_by": owner, "holder": result["holder"]}),
            );
        }
        Ok(result)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── code.check ────────────────────────────────────────────────────────

/// `code.check` — is a scope claimed?
pub struct CodeCheckTool {
    stats: ToolStats,
    effects: EffectRow,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
}

impl CodeCheckTool {
    #[must_use]
    pub fn new(gan_ying: Option<Arc<Mutex<GanYingBus>>>) -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Filesystem],
                ..Default::default()
            },
            gan_ying,
        }
    }
}

#[async_trait]
impl Tool for CodeCheckTool {
    fn name(&self) -> &str {
        "code.check"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "scope": super::common::str_prop("Scope to check"),
                "root": super::common::str_prop("Repository root (default: WM_PROJECT_ROOT env)"),
            }),
            &["scope"],
        )
    }
    fn description(&self) -> &str {
        "Check whether a scope is claimed — reports the holder, their intent, and expiry when claimed; 'free' means no active lease."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let scope = require_str(&args, "scope")?;
        let root = resolve_root(&args)?;
        let ledger = LeaseLedger::discover(&root)?;

        let mut newly_expired: Vec<Lease> = Vec::new();
        let holder = ledger.mutate(|leases, expired| {
            newly_expired = expired.to_vec();
            Ok(leases.iter().find(|l| l.scope == scope).map(lease_json))
        })?;

        for lease in &newly_expired {
            emit(
                self.gan_ying.as_ref(),
                EventType::CoordinationClaimExpired,
                json!({"scope": lease.scope, "owner_session": lease.owner_session}),
            );
        }

        match holder {
            Some(h) => Ok(json!({
                "status": "success",
                "scope": scope,
                "state": "claimed",
                "holder": h["owner_session"],
                "intent": h["intent"],
                "expires_at": h["expires_at"],
                "next_action": CONFLICT_NEXT_ACTION,
            })),
            None => Ok(json!({
                "status": "success",
                "scope": scope,
                "state": "free",
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── code.release ──────────────────────────────────────────────────────

/// `code.release` — release a claimed scope (owner must match).
pub struct CodeReleaseTool {
    stats: ToolStats,
    effects: EffectRow,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
}

impl CodeReleaseTool {
    #[must_use]
    pub fn new(gan_ying: Option<Arc<Mutex<GanYingBus>>>) -> Self {
        Self {
            stats: ToolStats::default(),
            // EffectRow declares data-plane effects (the ledger file), per
            // the session-tools precedent: the fixed-argv `git rev-parse`
            // lookup is the same trust class as checkpoint's git capture,
            // and declaring spawns would push every coordination call
            // against the Yama spawn budget (found live: a two-agent
            // negotiation burst exceeds 6 spawns/min).
            effects: EffectRow {
                reads: vec![Resource::Filesystem],
                writes: vec![Resource::Filesystem],
                ..Default::default()
            },
            gan_ying,
        }
    }
}

#[async_trait]
impl Tool for CodeReleaseTool {
    fn name(&self) -> &str {
        "code.release"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "scope": super::common::str_prop("Scope to release (the claim's lease_id)"),
                "owner_session": super::common::str_prop("Releasing session id — must match the claim's owner"),
                "root": super::common::str_prop("Repository root (default: WM_PROJECT_ROOT env)"),
            }),
            &["scope", "owner_session"],
        )
    }
    fn description(&self) -> &str {
        "Release a claimed scope when work is done — only the owning session can release; releasing a free scope is an idempotent no-op."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let scope = require_str(&args, "scope")?;
        let owner = require_str(&args, "owner_session")?;
        let root = resolve_root(&args)?;
        let ledger = LeaseLedger::discover(&root)?;

        let outcome = ledger.mutate(|leases, _expired| {
            let Some(pos) = leases.iter().position(|l| l.scope == scope) else {
                return Ok(json!({
                    "status": "success",
                    "scope": scope,
                    "state": "free",
                    "note": "no active claim on this scope (already released or expired)"
                }));
            };
            let lease = &leases[pos];
            if lease.owner_session != owner {
                return Ok(json!({
                    "status": "not_owner",
                    "scope": scope,
                    "holder": lease.owner_session,
                    "holder_intent": lease.intent,
                    "expires_at": lease.expires_at,
                    "note": "only the owning session can release a claim",
                }));
            }
            leases.remove(pos);
            Ok(json!({
                "status": "success",
                "scope": scope,
                "state": "released",
                "owner_session": owner,
            }))
        })?;

        if outcome["status"] == "success" && outcome["state"] == "released" {
            emit(
                self.gan_ying.as_ref(),
                EventType::CoordinationClaimReleased,
                json!({"scope": scope, "owner_session": owner}),
            );
        }
        Ok(outcome)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── code.list ─────────────────────────────────────────────────────────

/// `code.list` — list claims in the shared ledger.
pub struct CodeListTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl CodeListTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Filesystem],
                ..Default::default()
            },
        }
    }
}

impl Default for CodeListTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for CodeListTool {
    fn name(&self) -> &str {
        "code.list"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "include_expired": super::common::bool_prop("Include expired leases in the listing (default false)"),
                "root": super::common::str_prop("Repository root (default: WM_PROJECT_ROOT env)"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "List active claims in the shared lease ledger — what each agent is holding and until when."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let include_expired = args
            .get("include_expired")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(false);
        let root = resolve_root(&args)?;
        let ledger = LeaseLedger::discover(&root)?;
        let (active, expired) = ledger.snapshot()?;
        let mut leases: Vec<Value> = active.iter().map(lease_json).collect();
        if include_expired {
            let mut expired_json: Vec<Value> = expired
                .iter()
                .map(|l| {
                    let mut v = lease_json(l);
                    v["expired"] = json!(true);
                    v
                })
                .collect();
            leases.append(&mut expired_json);
        }
        let count = leases.len();
        Ok(json!({
            "status": "success",
            "count": count,
            "leases": leases,
            "file": ledger.path().display().to_string(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the coordination tools (full-profile surface).
#[must_use]
pub fn register_coordination(
    registry: &wm_dispatch::ToolRegistry,
    gan_ying_bus: Option<&Arc<Mutex<GanYingBus>>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(CodeClaimTool::new(gan_ying_bus.cloned())))
        .register(Arc::new(CodeCheckTool::new(gan_ying_bus.cloned())))
        .register(Arc::new(CodeReleaseTool::new(gan_ying_bus.cloned())))
        .register(Arc::new(CodeListTool::new()))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Fresh local git repository with one empty initial commit.
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

    fn root_str(root: &Path) -> Value {
        json!(root.display().to_string())
    }

    #[tokio::test]
    async fn claim_then_conflict_names_holder_and_intent() {
        let (_guard, root) = git_repo();
        let a = CodeClaimTool::new(None);
        let b = CodeClaimTool::new(None);
        let mut ctx = Context::default();

        let first = a
            .call(
                &mut ctx,
                json!({
                    "scope": "src/expansion/",
                    "intent": "refactoring session tools",
                    "owner_session": "session-aaa",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();
        assert_eq!(first["status"], "success", "got: {first}");
        assert_eq!(first["lease_id"], "src/expansion/");
        assert_eq!(first["owner_session"], "session-aaa");

        let second = b
            .call(
                &mut ctx,
                json!({
                    "scope": "src/expansion/",
                    "intent": "unrelated edits",
                    "owner_session": "session-bbb",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();
        assert_eq!(second["status"], "conflict", "got: {second}");
        assert_eq!(second["holder"], "session-aaa");
        assert_eq!(second["holder_intent"], "refactoring session tools");
        assert!(
            second["next_action"]
                .as_str()
                .unwrap()
                .contains("code.release")
        );
    }

    #[tokio::test]
    async fn check_reports_claimed_then_free_zero_false_free() {
        let (_guard, root) = git_repo();
        let claim = CodeClaimTool::new(None);
        let check = CodeCheckTool::new(None);
        let mut ctx = Context::default();

        let free = check
            .call(&mut ctx, json!({"scope": "docs/", "root": root_str(&root)}))
            .await
            .unwrap();
        assert_eq!(free["state"], "free");

        claim
            .call(
                &mut ctx,
                json!({
                    "scope": "docs/",
                    "intent": "doc rewrite",
                    "owner_session": "session-aaa",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();

        let claimed = check
            .call(&mut ctx, json!({"scope": "docs/", "root": root_str(&root)}))
            .await
            .unwrap();
        assert_eq!(claimed["state"], "claimed", "got: {claimed}");
        assert_eq!(claimed["holder"], "session-aaa");
        assert_eq!(claimed["intent"], "doc rewrite");
    }

    #[tokio::test]
    async fn release_requires_owner_then_scope_frees() {
        let (_guard, root) = git_repo();
        let claim = CodeClaimTool::new(None);
        let release = CodeReleaseTool::new(None);
        let check = CodeCheckTool::new(None);
        let mut ctx = Context::default();

        claim
            .call(
                &mut ctx,
                json!({
                    "scope": "src/foo.rs",
                    "intent": "bugfix",
                    "owner_session": "session-aaa",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();

        let wrong = release
            .call(
                &mut ctx,
                json!({
                    "scope": "src/foo.rs",
                    "owner_session": "session-bbb",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();
        assert_eq!(wrong["status"], "not_owner", "got: {wrong}");
        assert_eq!(wrong["holder"], "session-aaa");

        let still = check
            .call(
                &mut ctx,
                json!({"scope": "src/foo.rs", "root": root_str(&root)}),
            )
            .await
            .unwrap();
        assert_eq!(
            still["state"], "claimed",
            "release must not free others' claims"
        );

        let right = release
            .call(
                &mut ctx,
                json!({
                    "scope": "src/foo.rs",
                    "owner_session": "session-aaa",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();
        assert_eq!(right["status"], "success");
        assert_eq!(right["state"], "released");

        let freed = check
            .call(
                &mut ctx,
                json!({"scope": "src/foo.rs", "root": root_str(&root)}),
            )
            .await
            .unwrap();
        assert_eq!(
            freed["state"], "free",
            "zero false free: freed after owner release"
        );

        // Release again — idempotent no-op.
        let again = release
            .call(
                &mut ctx,
                json!({
                    "scope": "src/foo.rs",
                    "owner_session": "session-aaa",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();
        assert_eq!(again["status"], "success");
        assert_eq!(again["state"], "free");
    }

    #[tokio::test]
    async fn expired_lease_frees_scope() {
        let (_guard, root) = git_repo();
        let claim = CodeClaimTool::new(None);
        let check = CodeCheckTool::new(None);
        let mut ctx = Context::default();

        claim
            .call(
                &mut ctx,
                json!({
                    "scope": "src/stale.rs",
                    "intent": "dead session's claim",
                    "owner_session": "session-dead",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();

        // Backdate the expiry in the ledger directly — simulates the passage
        // of time without a sleep.
        let path = LeaseLedger::discover(&root).unwrap().path().to_path_buf();
        let raw = std::fs::read_to_string(&path).unwrap();
        let mut file: LeaseFile = serde_json::from_str(&raw).unwrap();
        file.leases[0].expires_at = "2020-01-01T00:00:00Z".into();
        std::fs::write(&path, serde_json::to_string(&file).unwrap()).unwrap();

        let freed = check
            .call(
                &mut ctx,
                json!({"scope": "src/stale.rs", "root": root_str(&root)}),
            )
            .await
            .unwrap();
        assert_eq!(freed["state"], "free", "expired claims free the scope");

        // A different owner can claim the freed scope immediately.
        let other = CodeClaimTool::new(None);
        let taken = other
            .call(
                &mut ctx,
                json!({
                    "scope": "src/stale.rs",
                    "intent": "rescued work",
                    "owner_session": "session-live",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();
        assert_eq!(taken["status"], "success", "got: {taken}");
    }

    #[tokio::test]
    async fn ledger_visible_across_independent_tool_instances() {
        // Two "agents" = two tool instances with no shared state except the
        // file in the git common dir (the deployment shape: separate server
        // processes over one checkout).
        let (_guard, root) = git_repo();
        let claim_a = CodeClaimTool::new(None);
        let list_b = CodeListTool::new();
        let check_b = CodeCheckTool::new(None);
        let mut ctx = Context::default();

        claim_a
            .call(
                &mut ctx,
                json!({
                    "scope": "worktree-A",
                    "intent": "agent A rewriting the harness",
                    "owner_session": "session-aaa",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();

        let listed = list_b
            .call(&mut ctx, json!({"root": root_str(&root)}))
            .await
            .unwrap();
        assert_eq!(listed["status"], "success");
        assert_eq!(listed["count"], 1, "got: {listed}");
        assert_eq!(listed["leases"][0]["scope"], "worktree-A");
        assert_eq!(
            listed["leases"][0]["intent"],
            "agent A rewriting the harness"
        );
        assert!(listed["file"].as_str().unwrap().contains("wm-leases.json"));

        let seen = check_b
            .call(
                &mut ctx,
                json!({"scope": "worktree-A", "root": root_str(&root)}),
            )
            .await
            .unwrap();
        assert_eq!(seen["state"], "claimed");
        assert_eq!(seen["holder"], "session-aaa");
    }

    #[tokio::test]
    async fn renew_own_claim_keeps_single_entry() {
        let (_guard, root) = git_repo();
        let claim = CodeClaimTool::new(None);
        let list = CodeListTool::new();
        let mut ctx = Context::default();

        for ttl in [7200i64, 60i64] {
            let r = claim
                .call(
                    &mut ctx,
                    json!({
                        "scope": "src/renewed.rs",
                        "intent": "long-running refactor",
                        "owner_session": "session-aaa",
                        "ttl_secs": ttl,
                        "root": root_str(&root),
                    }),
                )
                .await
                .unwrap();
            assert_eq!(r["status"], "success", "got: {r}");
        }
        let listed = list
            .call(&mut ctx, json!({"root": root_str(&root)}))
            .await
            .unwrap();
        assert_eq!(listed["count"], 1, "renewal must not duplicate entries");
        assert_eq!(listed["leases"][0]["ttl_secs"], 60);
    }

    #[tokio::test]
    async fn claim_rejects_missing_intent_and_bad_ttl() {
        let (_guard, root) = git_repo();
        let claim = CodeClaimTool::new(None);
        let mut ctx = Context::default();

        let no_intent = claim
            .call(
                &mut ctx,
                json!({
                    "scope": "src/x.rs",
                    "owner_session": "s",
                    "root": root_str(&root),
                }),
            )
            .await;
        assert!(no_intent.is_err(), "intent is mandatory");

        let bad_ttl = claim
            .call(
                &mut ctx,
                json!({
                    "scope": "src/x.rs",
                    "intent": "y",
                    "owner_session": "s",
                    "ttl_secs": 0,
                    "root": root_str(&root),
                }),
            )
            .await;
        assert!(bad_ttl.is_err(), "ttl_secs must be >= 1");
    }

    #[tokio::test]
    async fn non_git_root_is_a_clear_error() {
        let dir = tempfile::tempdir().unwrap();
        let claim = CodeClaimTool::new(None);
        let mut ctx = Context::default();
        let err = claim
            .call(
                &mut ctx,
                json!({
                    "scope": "src/x.rs",
                    "intent": "y",
                    "owner_session": "s",
                    "root": dir.path().display().to_string(),
                }),
            )
            .await
            .unwrap_err();
        assert!(err.to_string().contains("git repository"), "got: {err}");
    }

    #[tokio::test]
    async fn list_hides_expired_by_default_but_can_include_them() {
        let (_guard, root) = git_repo();
        let claim = CodeClaimTool::new(None);
        let list = CodeListTool::new();
        let mut ctx = Context::default();

        claim
            .call(
                &mut ctx,
                json!({
                    "scope": "src/old.rs",
                    "intent": "long gone",
                    "owner_session": "session-old",
                    "root": root_str(&root),
                }),
            )
            .await
            .unwrap();

        let path = LeaseLedger::discover(&root).unwrap().path().to_path_buf();
        let raw = std::fs::read_to_string(&path).unwrap();
        let mut file: LeaseFile = serde_json::from_str(&raw).unwrap();
        file.leases[0].expires_at = "2020-01-01T00:00:00Z".into();
        std::fs::write(&path, serde_json::to_string(&file).unwrap()).unwrap();

        // First observation discovers the expiry (and prunes it), so the
        // inclusive listing must come first.
        let with_expired = list
            .call(
                &mut ctx,
                json!({"root": root_str(&root), "include_expired": true}),
            )
            .await
            .unwrap();
        assert_eq!(with_expired["count"], 1);
        assert_eq!(with_expired["leases"][0]["expired"], true);

        let default_list = list
            .call(&mut ctx, json!({"root": root_str(&root)}))
            .await
            .unwrap();
        assert_eq!(default_list["count"], 0, "expired leases hidden by default");
    }
}
