//! Trust stack — the one-call wiring for hosted/monetized deployments.
//!
//! Assembles the economic governance loop as a single object a server can
//! hold: a [`SecurityEventBus`], a [`PatternImmunity`] subscriber learning
//! from it (the Q2 loop), a [`NetworkStateProfile`] supplying real recipient
//! trust, and an [`EconomicFirewall`] gated by both and publishing its
//! denials back onto the bus. Every denial becomes a learnable event;
//! every learned pattern can harden future verdicts.
//!
//! This is the seam the MCP server wires into: construct once at startup
//! with the server's store, hold the [`TrustStack`], route economic tools
//! through `stack.firewall.validate(..)`.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use wm_core::Result;
use wm_memory::MemoryStore;

use crate::economic_firewall::{
    EconomicFirewall, NoDharmaSignOff, RecipientTrustSource, TransactionPolicy,
};
use crate::network_profile::NetworkStateProfile;
use crate::pattern_immunity::{PATTERN_THRESHOLD, PatternImmunity};
use crate::security_events::SecurityEventBus;

/// Shared, interior-mutable handle to the identity/reputation store.
///
/// The firewall only reads trust scores; registration and reputation
/// updates go through the same mutex so a server can mutate identity
/// data while serving.
pub struct SharedProfile(Mutex<NetworkStateProfile>);

impl SharedProfile {
    /// Wrap an owned profile for shared use.
    #[must_use]
    pub const fn new(profile: NetworkStateProfile) -> Self {
        Self(Mutex::new(profile))
    }

    /// Register an identity (idempotent on same key; error on collision).
    ///
    /// # Errors
    /// Propagates [`NetworkStateProfile::register`] errors.
    pub fn register(&self, agent_id: &str, public_key_hex: &str) -> Result<bool> {
        self.0
            .lock()
            .expect("profile lock poisoned")
            .register(agent_id, public_key_hex)
    }

    /// Update a reputation score (clamped, event logged).
    ///
    /// # Errors
    /// Propagates [`NetworkStateProfile::update_reputation`] errors.
    pub fn update_reputation(&self, agent_id: &str, delta: f64, reason: &str) -> Result<f64> {
        self.0
            .lock()
            .expect("profile lock poisoned")
            .update_reputation(agent_id, delta, reason)
    }

    /// Read a reputation score, if the identity is known.
    #[must_use]
    pub fn reputation(&self, agent_id: &str) -> Option<f64> {
        self.0
            .lock()
            .expect("profile lock poisoned")
            .reputation(agent_id)
    }
}

impl RecipientTrustSource for SharedProfile {
    fn trust(&self, recipient: &str) -> Option<f64> {
        self.0
            .lock()
            .expect("profile lock poisoned")
            .trust(recipient)
    }
}

/// The wired trust stack. All handles are shared; hold one per server.
#[derive(Clone)]
pub struct TrustStack {
    /// Denial-publishing economic firewall (the gate).
    pub firewall: Arc<EconomicFirewall>,
    /// Sovereign identity + reputation store (the trust source).
    pub profile: Arc<SharedProfile>,
    /// Typed security event bus (the nervous system).
    pub bus: Arc<SecurityEventBus>,
    /// Pattern immunity learning from the bus (the Q2 loop).
    pub immunity: Arc<PatternImmunity>,
}

impl TrustStack {
    /// Wire the full stack: immunity subscribes to the bus, the firewall
    /// uses the profile as its trust source and publishes denials to the
    /// bus. `bus_store_path` persists learned patterns across restarts
    /// (pass `None` for ephemeral learning).
    ///
    /// # Errors
    /// Propagates [`NetworkStateProfile`] construction errors (store open
    /// failures).
    pub fn build(
        store: Arc<MemoryStore>,
        log_dir: PathBuf,
        bus_store_path: Option<PathBuf>,
    ) -> Result<Self> {
        Self::build_with_policy(
            store,
            log_dir,
            bus_store_path,
            TransactionPolicy::default(),
            PATTERN_THRESHOLD,
        )
    }

    /// Wire the stack with an explicit firewall policy and immunity
    /// threshold (e.g. [`TransactionPolicy::economic`] for hosted lanes).
    ///
    /// # Errors
    /// Propagates [`NetworkStateProfile`] construction errors.
    pub fn build_with_policy(
        store: Arc<MemoryStore>,
        log_dir: PathBuf,
        bus_store_path: Option<PathBuf>,
        policy: TransactionPolicy,
        immunity_threshold: u64,
    ) -> Result<Self> {
        let bus = Arc::new(SecurityEventBus::new());
        let immunity = PatternImmunity::subscribe_to_bus(&bus, immunity_threshold, bus_store_path);
        let profile_data = NetworkStateProfile::new(store)?;
        let shared = Arc::new(SharedProfile::new(profile_data));
        let shared_for_firewall: Arc<SharedProfile> = Arc::clone(&shared);
        let trust: Arc<dyn RecipientTrustSource> = shared_for_firewall;
        let mut firewall = EconomicFirewall::new(log_dir, trust, Arc::new(NoDharmaSignOff));
        firewall.set_default_policy(policy);
        firewall.set_event_bus(Arc::clone(&bus));
        Ok(Self {
            firewall: Arc::new(firewall),
            profile: shared,
            bus,
            immunity,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::economic_firewall::{TransactionRequest, VerdictReason};
    use crate::network_profile::AgentKeypair;
    use crate::security_events::SecurityEventType;

    fn make_stack() -> (tempfile::TempDir, TrustStack) {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let store = Arc::new(MemoryStore::open_default(tmp.path()).expect("store"));
        let stack =
            TrustStack::build(Arc::clone(&store), tmp.path().join("economy"), None).expect("stack");
        (tmp, stack)
    }

    fn request(agent: &str, amount: f64, recipient: &str) -> TransactionRequest {
        TransactionRequest {
            agent_id: agent.into(),
            amount,
            currency: "USDC".into(),
            recipient: recipient.into(),
            purpose: "test".into(),
            tool_name: "gratitude.tip".into(),
            timestamp: Some(1_789_000_000),
        }
    }

    #[test]
    fn denials_publish_onto_the_bus() {
        let (_tmp, stack) = make_stack();
        stack
            .firewall
            .validate(&request("agent_1", 10_000.0, "raddr"));
        let history = stack.bus.history();
        assert!(
            history
                .iter()
                .any(|e| e.event_type == SecurityEventType::EconomicDenied
                    && e.agent_id == "agent_1")
        );
    }

    #[test]
    fn rate_denials_publish_rate_limited_events() {
        let (_tmp, stack) = make_stack();
        for _ in 0..12 {
            stack.firewall.validate(&request("agent_2", 0.01, "raddr"));
        }
        let history = stack.bus.history();
        assert!(
            history
                .iter()
                .any(|e| e.event_type == SecurityEventType::RateLimited)
        );
    }

    #[test]
    fn immunity_learns_from_repeated_denials() {
        let (_tmp, stack) = make_stack();
        for _ in 0..PATTERN_THRESHOLD {
            let v = stack.firewall.validate(&request("rogue", 9_999.0, "raddr"));
            assert_eq!(v.verdict_reason, VerdictReason::PolicyDenied);
        }
        assert!(
            stack
                .immunity
                .is_immune("economic_denied|gratitude.tip|rogue")
        );
    }

    #[test]
    fn profile_backed_trust_gate_deny_and_pass() {
        let (_tmp, stack) = make_stack();
        let key = AgentKeypair::from_seed([7u8; 32]).public_key_hex();
        stack.profile.register("low_trust", &key).expect("register");
        for i in 0..6 {
            stack
                .profile
                .update_reputation("low_trust", -0.1, "abuse")
                .unwrap_or_else(|e| panic!("rep {i}: {e}"));
        }

        let v = stack.firewall.validate(&request("agent_9", 1.0, &key));
        assert!(!v.approved);
        assert!(v.reason.contains("insufficient trust"));

        // Unknown recipients still pass (blocklist/allowlist remain the
        // gate for unregistered identities).
        assert!(
            stack
                .firewall
                .validate(&request("agent_9", 1.0, "stranger"))
                .approved
        );
    }

    #[test]
    fn economic_policy_stack_caps_sub_cent_lanes() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let store = Arc::new(MemoryStore::open_default(tmp.path()).expect("store"));
        let stack = TrustStack::build_with_policy(
            store,
            tmp.path().join("econ"),
            None,
            TransactionPolicy::economic(),
            3,
        )
        .expect("stack");
        let v = stack.firewall.validate(&request("tipper", 0.03, "raddr"));
        assert!(v.approved);
        let v = stack.firewall.validate(&request("tipper", 50.0, "raddr"));
        assert!(!v.approved);
    }
}
