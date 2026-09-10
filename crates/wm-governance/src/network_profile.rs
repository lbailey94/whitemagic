//! Network State Profile — sovereign agent identity + reputation store.
//!
//! Rust port of the Python `whitemagic/core/identity/network_state.py`
//! (`NetworkStateProfile`): agents hold persistent sovereign identities
//! (Ed25519 keypairs), carry a reputation score in [0, 1] with a bounded
//! update history, and can be looked up as trust sources for the
//! [`EconomicFirewall`](crate::economic_firewall) via the
//! [`RecipientTrustSource`](crate::economic_firewall::RecipientTrustSource)
//! trait.
//!
//! Semantics ported from the Python original:
//! - identity registration (idempotent per agent, keyed by agent id)
//! - reputation scoring in [0, 1], default 0.5, max ±0.1 per update
//! - reputation update history (bounded ring, oldest evicted)
//! - trust-score lookup by recipient id or public key; unknown → `None`
//!
//! Persistence follows the `karma_ledger` LMDB pattern: the whole state is
//! serialized as JSON into a single key in the Dharma (governance) galaxy of
//! an LMDB [`MemoryStore`]. The default store path resolves from
//! `$WM_ECONOMY_DIR` (or `$HOME/.local/share/whitemagic/economy`), matching
//! `EconomicFirewall::default_log_dir`.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::fmt;
use std::path::PathBuf;
use std::sync::Arc;

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use wm_core::{CoreError, Galaxy, Result};
use wm_memory::MemoryStore;

/// Default reputation for a newly registered agent (Python parity).
pub const DEFAULT_REPUTATION: f64 = 0.5;

/// Maximum absolute reputation delta per update (Python parity).
pub const MAX_REPUTATION_DELTA: f64 = 0.1;

/// Maximum number of reputation events retained per agent; the oldest is
/// evicted once the cap is exceeded.
pub const MAX_HISTORY_EVENTS: usize = 64;

/// LMDB key holding the serialized profile snapshot.
const STATE_KEY: &[u8] = b"__network_state__";

/// A single reputation change event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReputationEvent {
    /// Applied (clamped) delta.
    pub delta: f64,
    /// Why the reputation changed.
    pub reason: String,
    /// Unix epoch seconds when the change was applied.
    pub at: u64,
}

/// Per-agent reputation: score in [0, 1] plus a bounded update history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReputationRecord {
    /// Agent this record belongs to.
    pub agent_id: String,
    /// Current reputation score, clamped to [0, 1].
    pub score: f64,
    /// Unix epoch seconds of the last update.
    pub updated_at: u64,
    /// Bounded update history (oldest evicted beyond
    /// [`MAX_HISTORY_EVENTS`]).
    pub history: Vec<ReputationEvent>,
}

impl ReputationRecord {
    /// Append an event, evicting the oldest when over the cap.
    fn push_event(&mut self, event: ReputationEvent) {
        while self.history.len() >= MAX_HISTORY_EVENTS {
            self.history.remove(0);
        }
        self.history.push(event);
    }
}

/// A sovereign agent identity.
///
/// The public key is stored as lowercase hex of the 32-byte Ed25519
/// verifying key. Secret keys never enter persistence — identities hold
/// only the public half; the signing half lives in [`AgentKeypair`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentIdentity {
    /// Globally unique agent id.
    pub agent_id: String,
    /// Ed25519 public key (lowercase hex, 64 chars).
    pub public_key: String,
    /// Unix epoch seconds of registration.
    pub created_at: u64,
    /// Capability / role tags.
    pub capabilities: Vec<String>,
    /// Governance stake (participation weight).
    pub stake: f64,
}

/// An Ed25519 keypair for a sovereign agent identity.
///
/// The signing half is held in memory only (zeroized on drop by
/// ed25519-dalek); persistence stores just the public key hex.
pub struct AgentKeypair {
    signing: SigningKey,
}

impl fmt::Debug for AgentKeypair {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentKeypair")
            .field("public_key", &self.public_key_hex())
            .finish_non_exhaustive()
    }
}

impl AgentKeypair {
    /// Generate a fresh keypair from OS entropy.
    #[must_use]
    pub fn generate() -> Self {
        use getrandom::SysRng;
        use getrandom::rand_core::UnwrapErr;
        Self {
            signing: SigningKey::generate(&mut UnwrapErr(SysRng)),
        }
    }

    /// Derive a keypair from a 32-byte seed (deterministic, for tests).
    #[must_use]
    pub fn from_seed(seed: [u8; 32]) -> Self {
        Self {
            signing: SigningKey::from_bytes(&seed),
        }
    }

    /// The public key as lowercase hex (the agent's sovereign address).
    #[must_use]
    pub fn public_key_hex(&self) -> String {
        hex_encode(&self.signing.verifying_key().to_bytes())
    }

    /// Sign a message, returning the signature as lowercase hex.
    #[must_use]
    pub fn sign_hex(&self, message: &[u8]) -> String {
        let sig: Signature = self.signing.sign(message);
        hex_encode(&sig.to_bytes())
    }
}

/// Verify an Ed25519 signature against a hex public key.
///
/// Returns `false` on any malformed input (bad hex, wrong lengths,
/// invalid signature) — verification is a boolean gate, never an error
/// surface.
#[must_use]
pub fn verify_signature(public_key_hex: &str, message: &[u8], signature_hex: &str) -> bool {
    let Some(pk_bytes) = hex_decode_32(public_key_hex) else {
        return false;
    };
    let Some(sig_bytes) = hex_decode_64(signature_hex) else {
        return false;
    };
    let Ok(vk) = VerifyingKey::from_bytes(&pk_bytes) else {
        return false;
    };
    vk.verify(message, &Signature::from_bytes(&sig_bytes))
        .is_ok()
}

fn hex_encode(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        let _ = write!(out, "{b:02x}");
    }
    out
}

fn hex_decode_into<const N: usize>(hex: &str) -> Option<[u8; N]> {
    let hex = hex.trim();
    if hex.len() != N * 2 || !hex.bytes().all(|b| b.is_ascii_hexdigit()) {
        return None;
    }
    let mut out = [0u8; N];
    for (i, chunk) in hex.as_bytes().chunks_exact(2).enumerate() {
        let hi = (chunk[0] as char).to_digit(16)?;
        let lo = (chunk[1] as char).to_digit(16)?;
        out[i] = u8::try_from(hi * 16 + lo).ok()?;
    }
    Some(out)
}

fn hex_decode_32(hex: &str) -> Option<[u8; 32]> {
    hex_decode_into(hex)
}

fn hex_decode_64(hex: &str) -> Option<[u8; 64]> {
    hex_decode_into(hex)
}

/// Outcome of a reputation-weighted vote.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WeightedVote {
    /// Winning agent id.
    pub winner: String,
    /// Weight (reputation) of the winning vote.
    pub weight: f64,
}

/// Serialized snapshot of the whole profile (identities + reputations).
#[derive(Debug, Default, Serialize, Deserialize)]
struct PersistedState {
    identities: BTreeMap<String, AgentIdentity>,
    reputations: BTreeMap<String, ReputationRecord>,
}

/// Sovereign agent identity + reputation store, persisted to LMDB.
///
/// Ported from the Python `NetworkStateProfile` singleton; in Rust the
/// profile is an owned value (wrap in `Arc<Mutex<_>>` at the caller for
/// shared mutable access, or clone the `Arc<MemoryStore>` to open
/// additional read-loads).
pub struct NetworkStateProfile {
    store: Arc<MemoryStore>,
    identities: BTreeMap<String, AgentIdentity>,
    reputations: BTreeMap<String, ReputationRecord>,
}

impl NetworkStateProfile {
    /// Open (or create) a profile backed by the given LMDB store, loading
    /// any previously persisted snapshot.
    pub fn new(store: Arc<MemoryStore>) -> Result<Self> {
        let mut profile = Self {
            store,
            identities: BTreeMap::new(),
            reputations: BTreeMap::new(),
        };
        profile.load()?;
        Ok(profile)
    }

    /// Open (or create) a profile at the default economy data dir:
    /// `$WM_ECONOMY_DIR/network_state` or
    /// `$HOME/.local/share/whitemagic/economy/network_state` (same
    /// resolution as `EconomicFirewall::default_log_dir`).
    pub fn open_default() -> Result<Self> {
        Self::new(Arc::new(MemoryStore::open_default(Self::default_dir())?))
    }

    /// Default persistence directory root.
    #[must_use]
    pub fn default_dir() -> PathBuf {
        if let Ok(dir) = std::env::var("WM_ECONOMY_DIR") {
            return PathBuf::from(dir).join("network_state");
        }
        std::env::var("HOME").map_or_else(
            |_| PathBuf::from(".whitemagic-economy/network_state"),
            |home| PathBuf::from(home).join(".local/share/whitemagic/economy/network_state"),
        )
    }

    /// The backing LMDB store.
    #[must_use]
    pub const fn store(&self) -> &Arc<MemoryStore> {
        &self.store
    }

    fn load(&mut self) -> Result<()> {
        if let Some(data) = self.store.get_raw(Galaxy::Dharma, STATE_KEY)? {
            let state: PersistedState = serde_json::from_slice(&data)?;
            self.identities = state.identities;
            self.reputations = state.reputations;
        }
        Ok(())
    }

    /// Persist the full state snapshot to LMDB.
    pub fn persist(&self) -> Result<()> {
        let state = PersistedState {
            identities: self.identities.clone(),
            reputations: self.reputations.clone(),
        };
        let data = serde_json::to_vec(&state)?;
        self.store.put_raw(Galaxy::Dharma, STATE_KEY, &data)
    }

    /// Register a sovereign identity for `agent_id` bound to the Ed25519
    /// public key `public_key_hex`.
    ///
    /// - Idempotent: re-registering the same id with the same key returns
    ///   `Ok(false)` and preserves the existing identity.
    /// - Key collision: re-registering the same id with a *different* key
    ///   is refused (`Err`) — identity binding is immutable.
    /// - Malformed keys (bad hex, wrong length) are refused.
    ///
    /// Returns `Ok(true)` when a new identity was created. A fresh
    /// identity starts at [`DEFAULT_REPUTATION`] with zero stake.
    pub fn register(&mut self, agent_id: &str, public_key_hex: &str) -> Result<bool> {
        let key = normalize_key_hex(public_key_hex)
            .ok_or_else(|| CoreError::InvalidArgs("public_key_hex must be 64 hex chars".into()))?;
        if let Some(existing) = self.identities.get(agent_id) {
            if existing.public_key == key {
                return Ok(false);
            }
            return Err(CoreError::Governance(format!(
                "agent {agent_id} already registered with a different public key"
            )));
        }
        let identity = AgentIdentity {
            agent_id: agent_id.to_owned(),
            public_key: key,
            created_at: wm_core::time::now_unix_secs(),
            capabilities: Vec::new(),
            stake: 0.0,
        };
        self.identities.insert(agent_id.to_owned(), identity);
        self.reputations.insert(
            agent_id.to_owned(),
            ReputationRecord {
                agent_id: agent_id.to_owned(),
                score: DEFAULT_REPUTATION,
                updated_at: wm_core::time::now_unix_secs(),
                history: Vec::new(),
            },
        );
        self.persist()?;
        Ok(true)
    }

    /// Replace an agent's capability / role tags.
    pub fn set_capabilities(&mut self, agent_id: &str, capabilities: Vec<String>) -> Result<()> {
        let identity = self
            .identities
            .get_mut(agent_id)
            .ok_or_else(|| CoreError::NotFound(format!("unknown agent {agent_id}")))?;
        identity.capabilities = capabilities;
        self.persist()
    }

    /// Update governance stake by `delta` (Python `update_stake` parity).
    /// Returns the new stake.
    pub fn update_stake(&mut self, agent_id: &str, delta: f64) -> Result<f64> {
        let identity = self
            .identities
            .get_mut(agent_id)
            .ok_or_else(|| CoreError::NotFound(format!("unknown agent {agent_id}")))?;
        identity.stake += delta;
        let stake = identity.stake;
        self.persist()?;
        Ok(stake)
    }

    /// Look up an identity by agent id.
    #[must_use]
    pub fn identity(&self, agent_id: &str) -> Option<&AgentIdentity> {
        self.identities.get(agent_id)
    }

    /// All registered identities, ordered by agent id.
    pub fn identities(&self) -> impl Iterator<Item = &AgentIdentity> + '_ {
        self.identities.values()
    }

    /// Number of registered citizens.
    #[must_use]
    pub fn citizen_count(&self) -> usize {
        self.identities.len()
    }

    /// Update an agent's reputation by `delta` (clamped to
    /// ±[`MAX_REPUTATION_DELTA`]), clamped to a score in [0, 1], logging a
    /// [`ReputationEvent`]. Returns the new score.
    ///
    /// Unknown agents are refused (the Python original silently returned
    /// 0.0; failing loud is the Rust-side choice for a store API).
    pub fn update_reputation(&mut self, agent_id: &str, delta: f64, reason: &str) -> Result<f64> {
        let record = self
            .reputations
            .get_mut(agent_id)
            .ok_or_else(|| CoreError::NotFound(format!("unknown agent {agent_id}")))?;
        let clamped = delta.clamp(-MAX_REPUTATION_DELTA, MAX_REPUTATION_DELTA);
        record.score = (record.score + clamped).clamp(0.0, 1.0);
        record.updated_at = wm_core::time::now_unix_secs();
        let event = ReputationEvent {
            delta: clamped,
            reason: reason.to_owned(),
            at: record.updated_at,
        };
        record.push_event(event);
        let score = record.score;
        self.persist()?;
        Ok(score)
    }

    /// Current reputation score, if the agent is known.
    #[must_use]
    pub fn reputation(&self, agent_id: &str) -> Option<f64> {
        self.reputations.get(agent_id).map(|r| r.score)
    }

    /// The full reputation record (score + history), if known.
    #[must_use]
    pub fn reputation_record(&self, agent_id: &str) -> Option<&ReputationRecord> {
        self.reputations.get(agent_id)
    }

    /// Average reputation across all citizens (0.5 on an empty network,
    /// matching the Python status default).
    #[must_use]
    pub fn average_reputation(&self) -> f64 {
        if self.reputations.is_empty() {
            return DEFAULT_REPUTATION;
        }
        let total: f64 = self.reputations.values().map(|r| r.score).sum();
        total / (self.reputations.len() as f64)
    }

    /// Deterministic reputation-weighted vote over
    /// `(agent_id, proposal_hash)` candidates.
    ///
    /// Each candidate's weight is its agent's reputation (unknown agents
    /// weigh [`DEFAULT_REPUTATION`], Python vote parity). The highest
    /// weight wins; ties break to the lexicographically lowest proposal
    /// hash — fully deterministic for governance replays. Empty input
    /// yields `None`.
    #[must_use]
    pub fn reputation_weighted_vote(
        &self,
        candidates: &[(String, String)],
    ) -> Option<WeightedVote> {
        let mut best: Option<(WeightedVote, String)> = None;
        for (agent_id, proposal_hash) in candidates {
            let weight = self
                .reputations
                .get(agent_id)
                .map_or(DEFAULT_REPUTATION, |r| r.score);
            let better = match &best {
                None => true,
                Some((b, b_hash)) => {
                    weight > b.weight || (weight == b.weight && proposal_hash < b_hash)
                }
            };
            if better {
                best = Some((
                    WeightedVote {
                        winner: agent_id.clone(),
                        weight,
                    },
                    proposal_hash.clone(),
                ));
            }
        }
        best.map(|(vote, _)| vote)
    }
}

impl crate::economic_firewall::RecipientTrustSource for NetworkStateProfile {
    /// Reputation of a recipient: looked up by agent id first, then by
    /// public-key hex. Unknown recipients → `None` (the firewall then
    /// relies on its allowlist/blocklist alone, Python parity).
    fn trust(&self, recipient: &str) -> Option<f64> {
        if self.reputations.contains_key(recipient) {
            return self.reputation(recipient);
        }
        self.identities
            .values()
            .find(|id| id.public_key.eq_ignore_ascii_case(recipient))
            .and_then(|id| self.reputation(&id.agent_id))
    }
}

fn normalize_key_hex(key: &str) -> Option<String> {
    let bytes = hex_decode_into::<32>(key)?;
    // Reject keys that don't decode to a valid curve point.
    VerifyingKey::from_bytes(&bytes)
        .ok()
        .map(|_| hex_encode(&bytes))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::economic_firewall::{
        DharmaSignOff, EconomicFirewall, RecipientTrustSource, TransactionRequest, VerdictReason,
    };
    use ed25519_dalek::Signature;

    fn make_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let store = Arc::new(MemoryStore::open_default(tmp.path()).expect("store"));
        (tmp, store)
    }

    fn make_profile() -> (tempfile::TempDir, NetworkStateProfile) {
        let (tmp, store) = make_store();
        let profile = NetworkStateProfile::new(store).expect("profile");
        (tmp, profile)
    }

    fn seed_key(seed: u8) -> (AgentKeypair, String) {
        let mut bytes = [0u8; 32];
        bytes[0] = seed;
        let kp = AgentKeypair::from_seed(bytes);
        let hex = kp.public_key_hex();
        (kp, hex)
    }

    #[test]
    fn register_is_idempotent_and_collisions_refused() {
        let (_tmp, mut profile) = make_profile();
        let (_kp, key) = seed_key(1);

        assert!(profile.register("agent_1", &key).expect("register"));
        assert!(
            !profile
                .register("agent_1", &key)
                .expect("idempotent re-register")
        );

        let created_at = profile.identity("agent_1").expect("identity").created_at;
        assert!(!profile.register("agent_1", &key).expect("still idempotent"));
        assert_eq!(profile.identity("agent_1").unwrap().created_at, created_at);

        let (_kp2, key2) = seed_key(2);
        assert!(profile.register("agent_1", &key2).is_err());

        assert!(profile.register("agent_2", "nothex").is_err());
        assert!(profile.register("agent_2", "aabb").is_err());
    }

    #[test]
    fn reputation_clamps_and_history_bounds() {
        let (_tmp, mut profile) = make_profile();
        let (_kp, key) = seed_key(3);
        profile.register("agent_r", &key).expect("register");

        assert_eq!(
            profile
                .update_reputation("agent_r", 5.0, "huge bonus")
                .unwrap(),
            DEFAULT_REPUTATION + MAX_REPUTATION_DELTA
        );
        assert_eq!(
            profile
                .update_reputation("agent_r", -5.0, "huge penalty")
                .unwrap(),
            DEFAULT_REPUTATION
        );

        // Push to the ceiling then past it — score clamps at 1.0.
        for i in 0..10 {
            profile
                .update_reputation("agent_r", MAX_REPUTATION_DELTA, &format!("up {i}"))
                .unwrap();
        }
        assert_eq!(profile.reputation("agent_r"), Some(1.0));
        profile
            .update_reputation("agent_r", 0.1, "over the top")
            .unwrap();
        assert_eq!(profile.reputation("agent_r"), Some(1.0));

        // Down to the floor.
        for i in 0..12 {
            profile
                .update_reputation("agent_r", -MAX_REPUTATION_DELTA, &format!("down {i}"))
                .unwrap();
        }
        assert_eq!(profile.reputation("agent_r"), Some(0.0));

        // History is bounded at MAX_HISTORY_EVENTS with oldest evicted:
        // apply enough no-op updates to exceed the cap.
        for i in 0..70 {
            profile
                .update_reputation("agent_r", 0.0, &format!("noop {i}"))
                .unwrap();
        }
        let record = profile.reputation_record("agent_r").expect("record");
        assert_eq!(record.history.len(), MAX_HISTORY_EVENTS);
        assert_eq!(record.history.first().expect("first").reason, "noop 6");
    }

    #[test]
    fn unknown_agent_updates_are_refused() {
        let (_tmp, mut profile) = make_profile();
        assert!(profile.update_reputation("ghost", 0.1, "no").is_err());
        assert!(profile.reputation("ghost").is_none());
        assert!(profile.reputation_record("ghost").is_none());
    }

    #[test]
    fn trust_lookup_by_id_and_public_key() {
        let (_tmp, mut profile) = make_profile();
        let (_kp, key) = seed_key(4);
        profile.register("agent_t", &key).expect("register");
        profile
            .update_reputation("agent_t", MAX_REPUTATION_DELTA, "good")
            .unwrap();

        assert_eq!(profile.trust("agent_t"), Some(0.6));
        assert_eq!(profile.trust(&key), Some(0.6));
        assert_eq!(profile.trust(&key.to_uppercase()), Some(0.6));
        assert_eq!(profile.trust("unknown_agent"), None);
    }

    #[test]
    fn firewall_integration_low_rep_denied_unknown_and_high_pass() {
        let (_tmp, mut profile) = make_profile();
        let (_kp_low, low_key) = seed_key(5);
        let (_kp_high, high_key) = seed_key(6);
        profile.register("shady", &low_key).expect("register shady");
        profile
            .register("solid", &high_key)
            .expect("register solid");
        // Three negative updates: 0.5 → 0.2 (below the 0.3 firewall floor).
        for i in 0..3 {
            profile
                .update_reputation("shady", -MAX_REPUTATION_DELTA, &format!("bad act {i}"))
                .unwrap();
        }
        profile
            .update_reputation("solid", MAX_REPUTATION_DELTA, "good act")
            .unwrap();

        struct AllowDharma;
        impl DharmaSignOff for AllowDharma {
            fn evaluate(&self, _request: &TransactionRequest) -> Option<bool> {
                Some(true)
            }
        }

        let dir = tempfile::tempdir().expect("firewall tmpdir");
        let fw = EconomicFirewall::new(
            dir.path().to_path_buf(),
            Arc::new(profile),
            Arc::new(AllowDharma),
        )
        .with_min_recipient_trust(0.3);

        let req = |recipient: &str| TransactionRequest {
            agent_id: "payer".into(),
            amount: 1.0,
            currency: "XRP".into(),
            recipient: recipient.into(),
            purpose: "test".into(),
            tool_name: "tip.send".into(),
            timestamp: Some(1_789_000_000),
        };

        let low = fw.validate(&req("shady"));
        assert!(!low.approved);
        assert_eq!(low.verdict_reason, VerdictReason::PolicyDenied);
        assert!(low.reason.contains("insufficient trust"));

        let unknown = fw.validate(&req("nobody"));
        assert!(unknown.approved);

        let high = fw.validate(&req("solid"));
        assert!(high.approved);

        // Public-key-as-recipient also resolves through the profile.
        let by_key = fw.validate(&req(&high_key));
        assert!(by_key.approved);
    }

    #[test]
    fn persistence_roundtrip_across_instances() {
        let (tmp, store) = make_store();
        {
            let mut profile = NetworkStateProfile::new(Arc::clone(&store)).expect("profile");
            let (_kp, key) = seed_key(7);
            profile.register("agent_p", &key).expect("register");
            profile
                .set_capabilities("agent_p", vec!["analysis".into()])
                .expect("caps");
            profile.update_stake("agent_p", 0.25).expect("stake");
            profile
                .update_reputation("agent_p", MAX_REPUTATION_DELTA, "merit")
                .expect("rep");
        }

        let profile2 = NetworkStateProfile::new(store).expect("reloaded profile");
        let id = profile2.identity("agent_p").expect("identity persisted");
        assert_eq!(id.public_key, seed_key(7).1);
        assert_eq!(id.capabilities, vec!["analysis".to_string()]);
        assert!((id.stake - 0.25).abs() < f64::EPSILON);
        assert_eq!(profile2.reputation("agent_p"), Some(0.6));
        assert_eq!(
            profile2.reputation_record("agent_p").unwrap().history.len(),
            1
        );

        // The store outlives the tempdir guard in this test's scope.
        drop(profile2);
        drop(tmp);
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        let kp = AgentKeypair::from_seed([9u8; 32]);
        let message = b"sovereign vote: proposal-42";

        let sig = kp.sign_hex(message);
        assert!(verify_signature(&kp.public_key_hex(), message, &sig));

        // Tampered message fails.
        assert!(!verify_signature(
            &kp.public_key_hex(),
            b"sovereign vote: proposal-43",
            &sig
        ));

        // Wrong key fails.
        let other = AgentKeypair::from_seed([10u8; 32]);
        assert!(!verify_signature(&other.public_key_hex(), message, &sig));

        // Malformed inputs fail closed.
        assert!(!verify_signature("zz", message, &sig));
        assert!(!verify_signature(&kp.public_key_hex(), message, "short"));

        // Generated keypairs are random and valid.
        let a = AgentKeypair::generate();
        let b = AgentKeypair::generate();
        assert_ne!(a.public_key_hex(), b.public_key_hex());
        assert_eq!(a.public_key_hex().len(), 64);
        let sig = a.sign_hex(message);
        assert!(verify_signature(&a.public_key_hex(), message, &sig));

        // Debug output must never contain the secret key.
        assert!(!format!("{a:?}").contains("signing"));
    }

    #[test]
    fn weighted_vote_is_deterministic() {
        let (_tmp, mut profile) = make_profile();
        let (_kp_a, key_a) = seed_key(11);
        let (_kp_b, key_b) = seed_key(12);
        let (_kp_c, key_c) = seed_key(13);
        profile.register("low", &key_a).unwrap();
        profile.register("high", &key_b).unwrap();
        profile.register("mid", &key_c).unwrap();
        profile
            .update_reputation("low", -MAX_REPUTATION_DELTA, "penalty")
            .unwrap();
        profile
            .update_reputation("high", MAX_REPUTATION_DELTA, "bonus")
            .unwrap();

        let candidates = vec![
            ("low".to_string(), "hash_c".to_string()),
            ("high".to_string(), "hash_b".to_string()),
            ("mid".to_string(), "hash_a".to_string()),
        ];
        let vote = profile.reputation_weighted_vote(&candidates).expect("vote");
        assert_eq!(vote.winner, "high");
        assert!((vote.weight - 0.6).abs() < f64::EPSILON);

        // Tie (all default weight) breaks to the lowest proposal hash.
        let tied = vec![
            ("zeta".to_string(), "bbb".to_string()),
            ("alpha".to_string(), "ccc".to_string()),
            ("mike".to_string(), "aaa".to_string()),
        ];
        let vote = profile.reputation_weighted_vote(&tied).expect("vote");
        assert_eq!(vote.winner, "mike");
        assert!((vote.weight - DEFAULT_REPUTATION).abs() < f64::EPSILON);

        // Same input → same output.
        assert_eq!(
            profile.reputation_weighted_vote(&candidates),
            profile.reputation_weighted_vote(&candidates)
        );

        assert!(profile.reputation_weighted_vote(&[]).is_none());
    }

    #[test]
    fn average_reputation_tracks_citizens() {
        let (_tmp, mut profile) = make_profile();
        assert_eq!(profile.citizen_count(), 0);
        assert!((profile.average_reputation() - DEFAULT_REPUTATION).abs() < f64::EPSILON);

        let (_kp_a, key_a) = seed_key(21);
        let (_kp_b, key_b) = seed_key(22);
        profile.register("a", &key_a).unwrap();
        profile.register("b", &key_b).unwrap();
        profile
            .update_reputation("a", MAX_REPUTATION_DELTA, "up")
            .unwrap();
        profile
            .update_reputation("b", -MAX_REPUTATION_DELTA, "down")
            .unwrap();
        assert_eq!(profile.citizen_count(), 2);
        assert!((profile.average_reputation() - DEFAULT_REPUTATION).abs() < f64::EPSILON);
    }

    #[test]
    fn signature_bytes_reject_malleable_forms() {
        // Signature::from_bytes round-trips exactly; a mutated high bit
        // flips verification.
        let kp = AgentKeypair::from_seed([30u8; 32]);
        let msg = b"malleability probe";
        let sig_hex = kp.sign_hex(msg);
        let mut sig_bytes = hex_decode_64(&sig_hex).expect("sig bytes");
        assert!(verify_signature(&kp.public_key_hex(), msg, &sig_hex));
        sig_bytes[0] ^= 0x01;
        let mutated = hex_encode(&sig_bytes);
        assert!(!verify_signature(&kp.public_key_hex(), msg, &mutated));

        // Sanity: Signature::from_bytes is total for 64 bytes.
        let _ = Signature::from_bytes(&sig_bytes);
    }
}
