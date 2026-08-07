//! Context — Per-request execution environment
//!
//! The Context is passed to every tool call. It provides access to the
//! memory store, current brain-wave state, session information, and
//! a scratchpad for intermediate results.

use crate::brain_wave::BrainWave;
use crate::galaxy::Galaxy;
use std::collections::HashMap;

/// Per-request execution context.
pub struct Context {
    /// Current brain-wave state
    pub brain_wave: BrainWave,
    /// Session ID (if in a session)
    pub session_id: Option<uuid::Uuid>,
    /// User ID (for multi-user isolation)
    pub user_id: Option<String>,
    /// Request metadata (from MCP client)
    pub meta: HashMap<String, serde_json::Value>,
    /// Scratchpad for intermediate results within a single dispatch
    pub scratchpad: HashMap<String, serde_json::Value>,
    /// Whether this request is running under a Dharma governance profile
    pub dharma_profile: Option<String>,
    /// Mandala compartment (research/sandbox/production/secure)
    pub compartment: Option<String>,
    /// Cached karma debt (updated post-dispatch, synced periodically)
    pub karma_debt: f32,
    /// Intent score for this request (0.0 = low intent, 1.0 = high intent)
    pub intent_score: f32,
    /// Citta coherence at dispatch time (0.0–1.0). Low coherence blocks writes.
    pub citta_coherence: f32,
    /// Citta valence at dispatch time (−1.0 to 1.0). Negative = displeasure.
    pub citta_valence: f32,
    /// Self-model confidence at dispatch time (0.0–1.0).
    /// Below 0.5 triggers conservative dispatch (prefer cached results).
    pub self_model_confidence: f32,
    /// Drive curiosity level (0.0–1.0). High curiosity → exploration bias.
    pub drive_curiosity: f32,
    /// Drive caution level (0.0–1.0). High caution → conservative bias.
    pub drive_caution: f32,
    /// Drive energy level (0.0–1.0). Low energy → lightweight tool bias.
    pub drive_energy: f32,
    /// Drive exploration weight (0.0–1.0). Derived from curiosity.
    pub drive_exploration_weight: f32,
    /// Drive conservative weight (0.0–1.0). Derived from caution.
    pub drive_conservative_weight: f32,
}

impl Context {
    /// Create a new context with the given brain-wave state.
    #[must_use]
    pub fn new(brain_wave: BrainWave) -> Self {
        Self {
            brain_wave,
            session_id: None,
            user_id: None,
            meta: HashMap::new(),
            scratchpad: HashMap::new(),
            dharma_profile: None,
            compartment: None,
            karma_debt: 0.0,
            intent_score: 1.0,
            citta_coherence: 1.0,
            citta_valence: 0.0,
            self_model_confidence: 0.5,
            drive_curiosity: 0.5,
            drive_caution: 0.3,
            drive_energy: 0.8,
            drive_exploration_weight: 0.5,
            drive_conservative_weight: 0.3,
        }
    }

    /// Get the current brain-wave state.
    #[must_use]
    pub const fn brain_wave(&self) -> BrainWave {
        self.brain_wave
    }

    /// Set a scratchpad value.
    pub fn set(&mut self, key: impl Into<String>, value: serde_json::Value) {
        self.scratchpad.insert(key.into(), value);
    }

    /// Get a scratchpad value.
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&serde_json::Value> {
        self.scratchpad.get(key)
    }

    /// Check if this context has access to the given galaxy.
    ///
    /// Compartment-based access control:
    /// - `None` (default): full access to all galaxies (backward compatible)
    /// - `sandbox`: only Tutorial and Research (no production data)
    /// - `production`: all memory galaxies except system (Karma, Dharma, Substrate)
    /// - `secure`: all memory galaxies
    #[must_use]
    pub fn can_access_galaxy(&self, galaxy: Galaxy) -> bool {
        match self.compartment.as_deref() {
            None => true,
            Some("sandbox") => matches!(galaxy, Galaxy::Tutorial | Galaxy::Research),
            Some("production") => !matches!(
                galaxy,
                Galaxy::Karma
                    | Galaxy::Dharma
                    | Galaxy::Substrate
                    | Galaxy::Associations
                    | Galaxy::Embeddings
            ),
            Some("secure") => matches!(
                galaxy,
                Galaxy::Aria
                    | Galaxy::Citta
                    | Galaxy::Codex
                    | Galaxy::Journals
                    | Galaxy::Dreams
                    | Galaxy::Research
                    | Galaxy::Sessions
                    | Galaxy::Substrate
                    | Galaxy::Tutorial
                    | Galaxy::Universal
            ),
            Some(_) => true,
        }
    }

    /// Check if this context allows write operations to the given galaxy.
    ///
    /// Sandbox is read-only for Research (can write to Tutorial only).
    #[must_use]
    pub fn can_write_galaxy(&self, galaxy: Galaxy) -> bool {
        match self.compartment.as_deref() {
            None => true,
            Some("sandbox") => matches!(galaxy, Galaxy::Tutorial),
            Some("production" | "secure") => self.can_access_galaxy(galaxy),
            Some(_) => true,
        }
    }
}

impl Default for Context {
    fn default() -> Self {
        Self::new(BrainWave::Gamma)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::galaxy::Galaxy;

    #[test]
    fn no_compartment_has_full_access() {
        let ctx = Context::default();
        for g in Galaxy::all() {
            assert!(
                ctx.can_access_galaxy(g),
                "No compartment should access {g:?}"
            );
            assert!(ctx.can_write_galaxy(g), "No compartment should write {g:?}");
        }
    }

    fn make_ctx(compartment: &str) -> Context {
        Context {
            compartment: Some(compartment.into()),
            ..Context::default()
        }
    }

    #[test]
    fn sandbox_can_only_read_tutorial_and_research() {
        let ctx = make_ctx("sandbox");
        assert!(ctx.can_access_galaxy(Galaxy::Tutorial));
        assert!(ctx.can_access_galaxy(Galaxy::Research));
        assert!(!ctx.can_access_galaxy(Galaxy::Codex));
        assert!(!ctx.can_access_galaxy(Galaxy::Karma));
        // Sandbox can only write to Tutorial
        assert!(ctx.can_write_galaxy(Galaxy::Tutorial));
        assert!(!ctx.can_write_galaxy(Galaxy::Research));
    }

    #[test]
    fn production_cannot_access_system_galaxies() {
        let ctx = make_ctx("production");
        assert!(ctx.can_access_galaxy(Galaxy::Codex));
        assert!(ctx.can_access_galaxy(Galaxy::Research));
        assert!(!ctx.can_access_galaxy(Galaxy::Karma));
        assert!(!ctx.can_access_galaxy(Galaxy::Dharma));
        assert!(!ctx.can_access_galaxy(Galaxy::Substrate));
        assert!(ctx.can_write_galaxy(Galaxy::Codex));
    }

    #[test]
    fn secure_can_access_all_memory_galaxies() {
        let ctx = make_ctx("secure");
        assert!(ctx.can_access_galaxy(Galaxy::Codex));
        assert!(ctx.can_access_galaxy(Galaxy::Substrate));
        assert!(ctx.can_write_galaxy(Galaxy::Codex));
        // Secure still can't access non-memory galaxies
        assert!(!ctx.can_access_galaxy(Galaxy::Karma));
    }
}
