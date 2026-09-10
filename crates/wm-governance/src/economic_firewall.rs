//! Transaction Firewall — economic safety layer.
//!
//! Rust port of the Python-era `whitemagic/security/transaction_firewall.py`
//! (DEFERRED_OBJECTIVES_2026 Q3/Q4): intercepts, validates, and rate-limits
//! outbound economic actions (tips, x402 payments, escrow, transfers) before
//! they reach any payment rail.
//!
//! Checks, in order (parity with the Python original):
//!   0. malformed input
//!   1. per-transaction amount limit
//!   2. daily cumulative spend limit (midnight rollover, persisted)
//!   3. rate limit (transactions per rolling 60s)
//!   4. recipient blocklist
//!   5. recipient allowlist (if non-empty)
//!   6. recipient trust score (injectable; unknown = pass-through)
//!   7. Dharma ethical sign-off (injectable; unavailable → fail-closed or
//!      permissive per `WM_FIREWALL_FAIL_CLOSED`)
//!
//! Env knobs (read per call, parity with the original):
//!   - `WM_FIREWALL_FAIL_CLOSED`  — deny when Dharma sign-off is unavailable
//!   - `WM_FIREWALL_MAINTENANCE`  — operator bypass, logged as such
//!   - `WM_MIN_RECIPIENT_TRUST`   — minimum known recipient trust (default 0.3)

use std::collections::{BTreeSet, HashMap};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use sha2::{Digest, Sha256};

/// Economic tool surfaces that must pass through the firewall.
pub const ECONOMIC_TOOLS: &[&str] = &[
    "bounty.create",
    "bounty.link_escrow",
    "bounty.complete",
    "wallet.transfer",
    "wallet.send",
    "wallet.balance",
    "tip.send",
    "gratitude.tip",
    "mesh.payment",
    "payment.channel",
    "engagement.issue",
    "engagement.revoke",
];

/// Whether a tool call is an economic action requiring firewall review.
#[must_use]
pub fn is_economic_tool(tool_name: &str) -> bool {
    ECONOMIC_TOOLS.contains(&tool_name)
}

/// Per-agent spending policy.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TransactionPolicy {
    /// Maximum amount for a single transaction.
    pub max_single_transaction: f64,
    /// Maximum cumulative spend per calendar day (UTC).
    pub daily_limit: f64,
    /// Recipients permitted (empty set = allowlist not enforced).
    pub allowed_recipients: BTreeSet<String>,
    /// Recipients always denied.
    pub blocked_recipients: BTreeSet<String>,
    /// Maximum transactions per rolling 60-second window.
    pub rate_limit_per_minute: u32,
    /// Whether Dharma ethical sign-off is required.
    pub dharma_check_required: bool,
    /// Minimum Dharma score for sign-off to pass.
    pub dharma_threshold: f64,
}

impl Default for TransactionPolicy {
    fn default() -> Self {
        Self {
            max_single_transaction: 100.0,
            daily_limit: 1000.0,
            allowed_recipients: BTreeSet::new(),
            blocked_recipients: BTreeSet::new(),
            rate_limit_per_minute: 10,
            dharma_check_required: true,
            dharma_threshold: 0.5,
        }
    }
}

impl TransactionPolicy {
    /// Profile for hosted-lane agent traffic: sub-cent tips and micropayments
    /// only, generous rate room, Dharma sign-off on. Encodes the spirit of
    /// the Dharma `economic` profile from DEFERRED_OBJECTIVES Q3 and the
    /// tip ladder of `docs/PRICING_ETHICS.md`.
    #[must_use]
    pub fn economic() -> Self {
        Self {
            max_single_transaction: 5.0,
            daily_limit: 50.0,
            rate_limit_per_minute: 30,
            ..Self::default()
        }
    }
}

/// Normalized representation of an economic action.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TransactionRequest {
    /// Initiating agent identity.
    pub agent_id: String,
    /// Amount in currency units.
    pub amount: f64,
    /// Currency / asset code (e.g. "XRP", "USDC").
    pub currency: String,
    /// Destination address or identity.
    pub recipient: String,
    /// Human/agent-readable purpose.
    pub purpose: String,
    /// The tool call that produced this request.
    pub tool_name: String,
    /// Unix epoch seconds (defaults to now).
    pub timestamp: Option<i64>,
}

impl TransactionRequest {
    /// Request timestamp, defaulting to wall-clock now.
    #[must_use]
    pub fn timestamp_or_now(&self) -> i64 {
        self.timestamp.unwrap_or_else(now_secs)
    }
}

fn now_secs() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

/// Typed reason for a firewall verdict.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VerdictReason {
    Approved,
    PolicyDenied,
    PolicyUnavailable,
    PolicyMalformed,
    PolicyStorageError,
    MaintenanceBypass,
}

/// Result of firewall validation.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TransactionVerdict {
    /// Whether the action may proceed.
    pub approved: bool,
    /// Human-readable reason.
    pub reason: String,
    /// Typed reason.
    pub verdict_reason: VerdictReason,
    /// Cumulative spend for the agent today (after this decision).
    pub daily_spent: f64,
    /// Remaining transactions in the current 60s window.
    pub rate_remaining: u32,
}

/// Append-only security event for the audit trail.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SecurityEvent {
    /// Unix epoch seconds.
    pub timestamp: i64,
    /// Producing tool call.
    pub tool_name: String,
    /// Initiating agent.
    pub agent_id: String,
    /// Typed verdict reason.
    pub verdict_reason: VerdictReason,
    /// Whether the action was approved.
    pub approved: bool,
    /// Amount (0.0 for non-monetary events).
    pub amount: f64,
    /// Recipient (empty when not applicable).
    pub recipient: String,
    /// Extra detail.
    pub detail: String,
}

/// Source of recipient trust scores (0.0–1.0).
///
/// Rust analogue of the Python `NetworkStateProfile.get_reputation` lookup.
/// `None` means "recipient is not a known registered identity" — allowlist /
/// blocklist checks remain the sole gate for unknown recipients.
pub trait RecipientTrustSource: Send + Sync {
    /// Reputation of a recipient, or `None` when unknown.
    fn trust(&self, recipient: &str) -> Option<f64>;
}

/// No-op trust source: every recipient is unknown (firewall relies on
/// allowlist/blocklist only). Matches the Python behaviour when the
/// NetworkStateProfile is unavailable.
#[derive(Debug, Default, Clone, Copy)]
pub struct NoRecipientTrust;

impl RecipientTrustSource for NoRecipientTrust {
    fn trust(&self, _recipient: &str) -> Option<f64> {
        None
    }
}

/// Dharma ethical sign-off for economic actions.
///
/// `Some(true)` = approved, `Some(false)` = denied, `None` = engine
/// unavailable (then `WM_FIREWALL_FAIL_CLOSED` decides).
pub trait DharmaSignOff: Send + Sync {
    /// Evaluate a transaction request for ethical sign-off.
    fn evaluate(&self, request: &TransactionRequest) -> Option<bool>;
}

/// Static sign-off used when no rules engine is wired: always unavailable
/// (permissive or fail-closed depending on env, exactly as the original).
#[derive(Debug, Default, Clone, Copy)]
pub struct NoDharmaSignOff;

impl DharmaSignOff for NoDharmaSignOff {
    fn evaluate(&self, _request: &TransactionRequest) -> Option<bool> {
        None
    }
}

#[derive(Debug, Default)]
struct DailySpend {
    amount: f64,
    day: String,
}

#[derive(Debug, Default)]
struct Inner {
    policies: HashMap<String, TransactionPolicy>,
    daily_spent: HashMap<String, DailySpend>,
    rate_log: HashMap<String, Vec<i64>>,
}

/// Validates economic actions before execution, with JSONL audit trails.
pub struct EconomicFirewall {
    inner: Mutex<Inner>,
    default_policy: TransactionPolicy,
    trust_source: Arc<dyn RecipientTrustSource>,
    dharma: Arc<dyn DharmaSignOff>,
    log_dir: PathBuf,
    min_recipient_trust: f64,
    fail_closed: bool,
    maintenance: bool,
}

impl Default for EconomicFirewall {
    fn default() -> Self {
        Self::new(
            Self::default_log_dir(),
            Arc::new(NoRecipientTrust),
            Arc::new(NoDharmaSignOff),
        )
    }
}

impl EconomicFirewall {
    /// Firewall with explicit log directory and injected trust/Dharma sources.
    #[must_use]
    pub fn new(
        log_dir: PathBuf,
        trust_source: Arc<dyn RecipientTrustSource>,
        dharma: Arc<dyn DharmaSignOff>,
    ) -> Self {
        let min_recipient_trust = std::env::var("WM_MIN_RECIPIENT_TRUST")
            .ok()
            .and_then(|v| v.parse::<f64>().ok())
            .unwrap_or(0.3);
        Self {
            inner: Mutex::new(Inner::default()),
            default_policy: TransactionPolicy::default(),
            trust_source,
            dharma,
            log_dir,
            min_recipient_trust,
            fail_closed: env_flag("WM_FIREWALL_FAIL_CLOSED"),
            maintenance: env_flag("WM_FIREWALL_MAINTENANCE"),
        }
    }

    /// Operator maintenance bypass: approve everything, log as bypass.
    #[must_use]
    pub const fn with_maintenance(mut self, maintenance: bool) -> Self {
        self.maintenance = maintenance;
        self
    }

    /// Deny when the Dharma sign-off engine is unavailable.
    #[must_use]
    pub const fn with_fail_closed(mut self, fail_closed: bool) -> Self {
        self.fail_closed = fail_closed;
        self
    }

    /// Minimum known-recipient trust score.
    #[must_use]
    pub const fn with_min_recipient_trust(mut self, min: f64) -> Self {
        self.min_recipient_trust = min;
        self
    }

    /// Set the policy for a specific agent.
    pub fn set_policy(&self, agent_id: &str, policy: TransactionPolicy) {
        self.inner
            .lock()
            .expect("firewall lock poisoned")
            .policies
            .insert(agent_id.to_owned(), policy);
    }

    /// Replace the default policy for agents without an explicit one.
    pub fn set_default_policy(&mut self, policy: TransactionPolicy) {
        self.default_policy = policy;
    }

    /// Default log directory: `$WM_ECONOMY_DIR` or
    /// `$HOME/.local/share/whitemagic/economy`.
    #[must_use]
    pub fn default_log_dir() -> PathBuf {
        if let Ok(dir) = std::env::var("WM_ECONOMY_DIR") {
            return PathBuf::from(dir);
        }
        std::env::var("HOME").map_or_else(
            |_| PathBuf::from(".whitemagic-economy"),
            |home| PathBuf::from(home).join(".local/share/whitemagic/economy"),
        )
    }

    fn policy_for(&self, inner: &Inner, agent_id: &str) -> TransactionPolicy {
        inner
            .policies
            .get(agent_id)
            .cloned()
            .unwrap_or_else(|| self.default_policy.clone())
    }

    fn day_key(ts: i64) -> String {
        chrono::DateTime::from_timestamp(ts, 0)
            .map(|dt| dt.format("%Y-%m-%d").to_string())
            .unwrap_or_default()
    }

    /// Run all checks and return a verdict.
    ///
    /// The lock guard intentionally spans the full check chain: the checks
    /// plus the spend record are one atomic decision (dropping between checks
    /// would let concurrent requests race past a just-satisfied limit).
    #[allow(clippy::significant_drop_tightening)]
    ///
    /// # Panics
    /// Panics only if the internal mutex is poisoned by another thread
    /// panicking while holding it.
    pub fn validate(&self, request: &TransactionRequest) -> TransactionVerdict {
        if self.maintenance {
            let verdict = TransactionVerdict {
                approved: true,
                reason: "Maintenance mode bypass active".into(),
                verdict_reason: VerdictReason::MaintenanceBypass,
                daily_spent: 0.0,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "maintenance bypass");
            return verdict;
        }

        if let Some(bad) = Self::malformed_reason(request) {
            let verdict = TransactionVerdict {
                approved: false,
                reason: bad,
                verdict_reason: VerdictReason::PolicyMalformed,
                daily_spent: 0.0,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "malformed request");
            return verdict;
        }

        let mut inner = self.inner.lock().expect("firewall lock poisoned");
        let policy = self.policy_for(&inner, &request.agent_id);
        let now = request.timestamp_or_now();
        let Inner {
            daily_spent,
            rate_log,
            ..
        } = &mut *inner;

        // Check 1: single-transaction limit.
        if request.amount > policy.max_single_transaction {
            let verdict = TransactionVerdict {
                approved: false,
                reason: format!(
                    "Single transaction {} {} exceeds limit {}",
                    request.amount, request.currency, policy.max_single_transaction
                ),
                verdict_reason: VerdictReason::PolicyDenied,
                daily_spent: 0.0,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "single-tx limit");
            return verdict;
        }

        // Check 2: daily cumulative limit (with midnight rollover).
        let today = Self::day_key(now);
        let spent_entry = daily_spent.entry(request.agent_id.clone()).or_default();
        if spent_entry.day != today {
            spent_entry.day.clone_from(&today);
            spent_entry.amount = 0.0;
        }
        let spent = spent_entry.amount;
        if spent + request.amount > policy.daily_limit {
            let verdict = TransactionVerdict {
                approved: false,
                reason: format!(
                    "Daily limit exceeded: {:.2} would exceed {}",
                    spent + request.amount,
                    policy.daily_limit
                ),
                verdict_reason: VerdictReason::PolicyDenied,
                daily_spent: spent,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "daily limit");
            return verdict;
        }

        // Check 3: rate limit over a rolling 60s window.
        let rate_log = rate_log.entry(request.agent_id.clone()).or_default();
        rate_log.retain(|t| now - *t < 60);
        if rate_log.len() >= policy.rate_limit_per_minute as usize {
            let verdict = TransactionVerdict {
                approved: false,
                reason: format!(
                    "Rate limit: {} transactions in last 60s, limit is {}",
                    rate_log.len(),
                    policy.rate_limit_per_minute
                ),
                verdict_reason: VerdictReason::PolicyDenied,
                daily_spent: spent,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "rate limit");
            return verdict;
        }

        // Check 4: recipient blocklist.
        if policy.blocked_recipients.contains(&request.recipient) {
            let verdict = TransactionVerdict {
                approved: false,
                reason: format!("Recipient {} is blocked", request.recipient),
                verdict_reason: VerdictReason::PolicyDenied,
                daily_spent: spent,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "blocklist");
            return verdict;
        }

        // Check 5: recipient allowlist (if non-empty).
        if !policy.allowed_recipients.is_empty()
            && !policy.allowed_recipients.contains(&request.recipient)
        {
            let verdict = TransactionVerdict {
                approved: false,
                reason: format!("Recipient {} not in allowlist", request.recipient),
                verdict_reason: VerdictReason::PolicyDenied,
                daily_spent: spent,
                rate_remaining: 0,
            };
            self.emit_event(request, &verdict, "allowlist");
            return verdict;
        }

        // Check 5.5: recipient trust (only known identities are scored).
        if let Some(score) = self.trust_source.trust(&request.recipient) {
            if score < self.min_recipient_trust {
                let verdict = TransactionVerdict {
                    approved: false,
                    reason: format!(
                        "Recipient {} has insufficient trust score ({score:.2} < {:.2})",
                        request.recipient, self.min_recipient_trust
                    ),
                    verdict_reason: VerdictReason::PolicyDenied,
                    daily_spent: spent,
                    rate_remaining: 0,
                };
                self.emit_event(request, &verdict, "recipient trust");
                return verdict;
            }
        }

        // Check 6: Dharma ethical sign-off.
        if policy.dharma_check_required {
            match self.dharma.evaluate(request) {
                Some(false) => {
                    let verdict = TransactionVerdict {
                        approved: false,
                        reason: format!(
                            "Dharma check failed (threshold={})",
                            policy.dharma_threshold
                        ),
                        verdict_reason: VerdictReason::PolicyDenied,
                        daily_spent: spent,
                        rate_remaining: 0,
                    };
                    self.emit_event(request, &verdict, "dharma denied");
                    return verdict;
                }
                None => {
                    if self.fail_closed {
                        let verdict = TransactionVerdict {
                            approved: false,
                            reason: "Dharma engine unavailable (fail-closed)".into(),
                            verdict_reason: VerdictReason::PolicyUnavailable,
                            daily_spent: spent,
                            rate_remaining: 0,
                        };
                        self.emit_event(request, &verdict, "fail-closed");
                        return verdict;
                    }
                    tracing::warn!("Dharma unavailable (permissive mode) — allowing transaction");
                }
                Some(true) => {}
            }
        }

        // All checks passed — record spend.
        spent_entry.amount += request.amount;
        rate_log.push(now);
        self.persist_spend(request);
        let verdict = TransactionVerdict {
            approved: true,
            reason: "approved".into(),
            verdict_reason: VerdictReason::Approved,
            daily_spent: spent_entry.amount,
            rate_remaining: policy.rate_limit_per_minute - rate_log.len() as u32,
        };
        self.emit_event(request, &verdict, "approved");
        verdict
    }

    fn malformed_reason(request: &TransactionRequest) -> Option<String> {
        if request.agent_id.is_empty() {
            return Some("agent_id must not be empty".into());
        }
        if request.currency.is_empty() {
            return Some("currency must not be empty".into());
        }
        if request.recipient.is_empty() {
            return Some("recipient must not be empty".into());
        }
        if !request.amount.is_finite() || request.amount < 0.0 {
            return Some(format!(
                "amount must be a non-negative finite number, got {}",
                request.amount
            ));
        }
        None
    }

    fn persist_spend(&self, request: &TransactionRequest) {
        let entry = serde_json::json!({
            "timestamp": request.timestamp_or_now(),
            "agent_id": request.agent_id,
            "amount": request.amount,
            "currency": request.currency,
            "recipient": request.recipient,
            "purpose": request.purpose,
            "tool_name": request.tool_name,
        });
        self.append_jsonl("transaction_log.jsonl", &entry);
    }

    fn emit_event(&self, request: &TransactionRequest, verdict: &TransactionVerdict, detail: &str) {
        let event = SecurityEvent {
            timestamp: request.timestamp_or_now(),
            tool_name: request.tool_name.clone(),
            agent_id: request.agent_id.clone(),
            verdict_reason: verdict.verdict_reason,
            approved: verdict.approved,
            amount: request.amount,
            recipient: request.recipient.clone(),
            detail: detail.to_owned(),
        };
        self.append_jsonl("security_events.jsonl", &event);
    }

    fn append_jsonl(&self, file: &str, value: &impl serde::Serialize) {
        if self.write_jsonl(file, value).is_err() {
            tracing::warn!("economic firewall: could not append to {file}");
        }
    }

    fn write_jsonl(&self, file: &str, value: &impl serde::Serialize) -> std::io::Result<()> {
        let path = self.log_dir.join(file);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        use std::io::Write;
        let mut f = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)?;
        let line = serde_json::to_string(value).map_err(std::io::Error::other)?;
        f.write_all(line.as_bytes())?;
        f.write_all(b"\n")
    }

    /// Content hash of the combined log state, for anchor/ledger surfaces.
    #[must_use]
    pub fn log_digest(&self) -> Option<String> {
        let mut hasher = Sha256::new();
        for file in ["transaction_log.jsonl", "security_events.jsonl"] {
            let data = std::fs::read(self.log_dir.join(file)).ok()?;
            hasher.update(&data);
        }
        Some(format!("{:x}", hasher.finalize()))
    }
}

fn env_flag(name: &str) -> bool {
    std::env::var(name).is_ok_and(|v| matches!(v.as_str(), "1" | "true" | "yes"))
}

/// Ensure a path exists for tests and thin callers.
///
/// # Panics
/// Panics if the directory cannot be created.
#[must_use]
pub fn ensure_log_dir(dir: &Path) -> PathBuf {
    std::fs::create_dir_all(dir).expect("create economy log dir");
    dir.to_path_buf()
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FixedTrust(f64);

    impl RecipientTrustSource for FixedTrust {
        fn trust(&self, _recipient: &str) -> Option<f64> {
            Some(self.0)
        }
    }

    struct FixedDharma(bool);

    impl DharmaSignOff for FixedDharma {
        fn evaluate(&self, _request: &TransactionRequest) -> Option<bool> {
            Some(self.0)
        }
    }

    struct UnknownDharma;

    impl DharmaSignOff for UnknownDharma {
        fn evaluate(&self, _request: &TransactionRequest) -> Option<bool> {
            None
        }
    }

    fn request(amount: f64, recipient: &str) -> TransactionRequest {
        TransactionRequest {
            agent_id: "agent_1".into(),
            amount,
            currency: "XRP".into(),
            recipient: recipient.into(),
            purpose: "test".into(),
            tool_name: "tip.send".into(),
            timestamp: Some(1_789_000_000),
        }
    }

    fn firewall(dir: &Path) -> EconomicFirewall {
        EconomicFirewall::new(
            dir.to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(FixedDharma(true)),
        )
    }

    #[test]
    fn approves_within_limits_and_persists_logs() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = firewall(dir.path());
        let v = fw.validate(&request(1.0, "raddr"));
        assert!(v.approved);
        assert_eq!(v.verdict_reason, VerdictReason::Approved);
        assert!((v.daily_spent - 1.0).abs() < f64::EPSILON);
        let spend =
            std::fs::read_to_string(dir.path().join("transaction_log.jsonl")).expect("spend log");
        assert!(spend.contains("tip.send"));
        let events =
            std::fs::read_to_string(dir.path().join("security_events.jsonl")).expect("event log");
        assert!(events.contains("approved"));
        assert!(fw.log_digest().is_some());
    }

    #[test]
    fn denies_over_single_transaction_limit() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = firewall(dir.path());
        let v = fw.validate(&request(101.0, "raddr"));
        assert!(!v.approved);
        assert_eq!(v.verdict_reason, VerdictReason::PolicyDenied);
        assert!(v.reason.contains("exceeds limit"));
    }

    #[test]
    fn daily_limit_rolls_over_and_enforces() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let mut fw = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(FixedDharma(true)),
        );
        fw.set_default_policy(TransactionPolicy {
            daily_limit: 10.0,
            ..TransactionPolicy::default()
        });
        let v = fw.validate(&request(6.0, "raddr"));
        assert!(v.approved);
        let v = fw.validate(&request(6.0, "raddr"));
        assert!(!v.approved);
        assert!(v.reason.contains("Daily limit exceeded"));
    }

    #[test]
    fn rate_limit_caps_rolling_window() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let mut fw = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(FixedDharma(true)),
        );
        fw.set_default_policy(TransactionPolicy {
            rate_limit_per_minute: 2,
            ..TransactionPolicy::default()
        });
        assert!(fw.validate(&request(1.0, "r")).approved);
        assert!(fw.validate(&request(1.0, "r")).approved);
        let v = fw.validate(&request(1.0, "r"));
        assert!(!v.approved);
        assert!(v.reason.contains("Rate limit"));
    }

    #[test]
    fn blocklist_and_allowlist_gates() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = firewall(dir.path());
        let mut policy = TransactionPolicy {
            allowed_recipients: BTreeSet::from(["good".into()]),
            blocked_recipients: BTreeSet::from(["bad".into()]),
            ..TransactionPolicy::default()
        };
        fw.set_policy("a_block", policy.clone());
        let v = fw.validate(&TransactionRequest {
            agent_id: "a_block".into(),
            recipient: "bad".into(),
            ..request(1.0, "unused")
        });
        assert!(!v.approved && v.reason.contains("blocked"));

        policy.blocked_recipients.clear();
        fw.set_policy("a_allow", policy);
        let v = fw.validate(&TransactionRequest {
            agent_id: "a_allow".into(),
            recipient: "unknown".into(),
            ..request(1.0, "unused")
        });
        assert!(!v.approved && v.reason.contains("not in allowlist"));
        let v = fw.validate(&TransactionRequest {
            agent_id: "a_allow".into(),
            recipient: "good".into(),
            ..request(1.0, "unused")
        });
        assert!(v.approved);
    }

    #[test]
    fn recipient_trust_blocks_low_scores_passes_unknown() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(FixedTrust(0.1)),
            Arc::new(FixedDharma(true)),
        );
        let v = fw.validate(&request(1.0, "shady"));
        assert!(!v.approved);
        assert!(v.reason.contains("insufficient trust"));

        let fw_unknown = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(FixedDharma(true)),
        );
        assert!(fw_unknown.validate(&request(1.0, "nobody")).approved);
    }

    #[test]
    fn dharma_denial_and_fail_closed() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(FixedDharma(false)),
        );
        let v = fw.validate(&request(1.0, "r"));
        assert!(!v.approved);
        assert!(v.reason.contains("Dharma check failed"));

        // Permissive mode: unavailable engine allows.
        let fw_permissive = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(UnknownDharma),
        );
        assert!(fw_permissive.validate(&request(1.0, "r")).approved);

        // Fail-closed mode: unavailable engine denies.
        let fw_closed = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(NoRecipientTrust),
            Arc::new(UnknownDharma),
        )
        .with_fail_closed(true);
        let v = fw_closed.validate(&request(1.0, "r"));
        assert!(!v.approved);
        assert_eq!(v.verdict_reason, VerdictReason::PolicyUnavailable);
    }

    #[test]
    fn maintenance_bypass_allows_but_logs() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(FixedTrust(0.0)),
            Arc::new(FixedDharma(false)),
        )
        .with_maintenance(true);
        let v = fw.validate(&request(9_999.0, "anything"));
        assert!(v.approved);
        assert_eq!(v.verdict_reason, VerdictReason::MaintenanceBypass);
    }

    #[test]
    fn malformed_requests_rejected() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let fw = firewall(dir.path());
        for bad in [
            request(-1.0, "r"),
            request(f64::NAN, "r"),
            TransactionRequest {
                agent_id: String::new(),
                ..request(1.0, "r")
            },
            TransactionRequest {
                recipient: String::new(),
                ..request(1.0, "r")
            },
        ] {
            let v = fw.validate(&bad);
            assert!(!v.approved);
            assert_eq!(v.verdict_reason, VerdictReason::PolicyMalformed);
        }
    }

    #[test]
    fn economic_tool_list_matches_lineage() {
        assert!(is_economic_tool("gratitude.tip"));
        assert!(is_economic_tool("mesh.payment"));
        assert!(!is_economic_tool("memory.recall"));
        assert_eq!(TransactionPolicy::economic().max_single_transaction, 5.0);
    }
}
