//! Dharma Resource Rules (Yama) — Resource budgets, novelty requirements,
//! purpose requirements, and human review gates for governed autonomy.
//!
//! This module directly addresses the v2 investigation findings:
//! - v2 ran 4-tier consciousness loop continuously with no resource awareness
//! - Produced 59,411 memories across 47 galaxies (11GB SQLite)
//! - Generated same 29 insights every 20-40 minutes (circular thinking)
//! - All 15+ feature flags defaulted to True (no opt-in)
//!
//! The Yama layer enforces discipline:
//! - **Resource budgets**: Rate-limit writes/spawns based on health score
//! - **Novelty requirement**: Block repetitive/circular actions
//! - **Purpose requirement**: Autonomous actions must declare a purpose
//! - **Human review**: Autonomous actions require explicit human approval

use std::collections::VecDeque;
use std::sync::RwLock;

use ahash::AHashMap;
use wm_core::BrainWave;

use crate::Homeostasis;

/// Configuration for resource rules.
#[derive(Debug, Clone)]
pub struct ResourceRulesConfig {
    /// Maximum writes per minute when healthy (health = 1.0).
    pub max_writes_per_minute: u32,
    /// Maximum process spawns per minute when healthy.
    pub max_spawns_per_minute: u32,
    /// Maximum network calls per minute when healthy.
    pub max_network_per_minute: u32,
    /// Number of recent action signatures to track for novelty.
    pub novelty_window: usize,
    /// How many times the same action can repeat within the window before blocking.
    pub max_repeats: u32,
    /// Whether autonomous actions require human review.
    pub require_human_review: bool,
}

impl Default for ResourceRulesConfig {
    fn default() -> Self {
        Self {
            max_writes_per_minute: 60,
            max_spawns_per_minute: 10,
            max_network_per_minute: 30,
            novelty_window: 50,
            max_repeats: 3,
            require_human_review: true,
        }
    }
}

impl ResourceRulesConfig {
    /// Strict configuration for Secure compartments — tighter budgets,
    /// lower repeat threshold, always require human review.
    #[must_use]
    pub const fn strict() -> Self {
        Self {
            max_writes_per_minute: 15,
            max_spawns_per_minute: 3,
            max_network_per_minute: 10,
            novelty_window: 100,
            max_repeats: 2,
            require_human_review: true,
        }
    }
}

/// Budget usage tracker for a resource type.
#[derive(Debug, Clone, Default)]
struct BudgetTracker {
    /// Timestamps (as seconds since epoch) of recent uses.
    recent: VecDeque<i64>,
}

impl BudgetTracker {
    fn record(&mut self, now: i64) {
        self.recent.push_back(now);
        // Prune entries older than 60 seconds
        while let Some(&front) = self.recent.front() {
            if now - front > 60 {
                self.recent.pop_front();
            } else {
                break;
            }
        }
    }

    fn count_last_minute(&self, now: i64) -> usize {
        self.recent.iter().filter(|&&t| now - t <= 60).count()
    }
}

/// Action signature for novelty tracking.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ActionSignature {
    tool_name: String,
    args_hash: u64,
}

/// The verdict from a resource rules evaluation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResourceVerdict {
    /// Action is within all budgets and novelty requirements.
    Allow,
    /// Action exceeds a resource budget — blocked.
    BudgetExceeded {
        resource: &'static str,
        used: u32,
        limit: u32,
    },
    /// Action is repetitive/circular — blocked.
    NotNovel {
        tool_name: String,
        repeats: u32,
        max: u32,
    },
    /// Autonomous action requires human review — blocked.
    RequiresHumanReview { tool_name: String },
    /// Autonomous action has no declared purpose — blocked.
    NoPurpose { tool_name: String },
}

impl ResourceVerdict {
    /// Whether this verdict blocks the action.
    #[must_use]
    pub const fn blocks(&self) -> bool {
        !matches!(self, Self::Allow)
    }

    /// Human-readable reason.
    #[must_use]
    pub fn reason(&self) -> String {
        match self {
            Self::Allow => "allowed".into(),
            Self::BudgetExceeded {
                resource,
                used,
                limit,
            } => {
                format!("Budget exceeded for {resource}: {used}/{limit} per minute")
            }
            Self::NotNovel {
                tool_name,
                repeats,
                max,
            } => {
                format!(
                    "Action '{tool_name}' is not novel (repeated {repeats}/{max} times recently)"
                )
            }
            Self::RequiresHumanReview { tool_name } => {
                format!("Action '{tool_name}' requires human review (autonomous mode)")
            }
            Self::NoPurpose { tool_name } => {
                format!(
                    "Action '{tool_name}' has no declared purpose (required for autonomous actions)"
                )
            }
        }
    }
}

/// Resource rules engine — enforces budgets, novelty, purpose, and human review.
///
/// The Yama (discipline) layer of the Mandala OS. It prevents the system
/// from running amok — a direct response to v2's uncontrolled resource
/// consumption and circular thinking patterns.
pub struct ResourceRules {
    config: RwLock<ResourceRulesConfig>,
    write_budget: RwLock<BudgetTracker>,
    spawn_budget: RwLock<BudgetTracker>,
    network_budget: RwLock<BudgetTracker>,
    novelty: RwLock<VecDeque<ActionSignature>>,
    /// Whether the current session has human approval for autonomous actions.
    human_approved: RwLock<bool>,
    /// Whether the current action is user-initiated (vs autonomous).
    user_initiated: RwLock<bool>,
}

impl ResourceRules {
    /// Create new resource rules with the given config.
    #[must_use]
    pub fn new(config: ResourceRulesConfig) -> Self {
        Self {
            config: RwLock::new(config),
            write_budget: RwLock::new(BudgetTracker::default()),
            spawn_budget: RwLock::new(BudgetTracker::default()),
            network_budget: RwLock::new(BudgetTracker::default()),
            novelty: RwLock::new(VecDeque::new()),
            human_approved: RwLock::new(false),
            user_initiated: RwLock::new(true),
        }
    }

    /// Replace the resource limits configuration at runtime
    /// (sandbox.set_limits).
    pub fn set_config(&self, config: ResourceRulesConfig) {
        if let Ok(mut c) = self.config.write() {
            *c = config;
        }
    }

    /// Current resource limits configuration.
    #[must_use]
    pub fn config(&self) -> ResourceRulesConfig {
        self.config.read().map(|c| c.clone()).unwrap_or_default()
    }

    /// Create with default config.
    #[must_use]
    #[allow(clippy::should_implement_trait)]
    pub fn default() -> Self {
        Self::new(ResourceRulesConfig::default())
    }

    /// Set whether the human has approved autonomous actions.
    pub fn set_human_approved(&self, approved: bool) {
        if let Ok(mut g) = self.human_approved.write() {
            *g = approved;
        }
    }

    /// Set whether the next action is user-initiated (vs autonomous).
    pub fn set_user_initiated(&self, user: bool) {
        if let Ok(mut g) = self.user_initiated.write() {
            *g = user;
        }
    }

    /// Check if human has approved autonomous actions.
    #[must_use]
    pub fn human_approved(&self) -> bool {
        self.human_approved.read().map(|g| *g).unwrap_or(false)
    }

    /// Evaluate a tool call against resource rules.
    ///
    /// - `tool_name`: Name of the tool being called
    /// - `args_hash`: Hash of the arguments (for novelty detection)
    /// - `is_write`: Whether the tool writes to resources
    /// - `is_spawn`: Whether the tool spawns processes
    /// - `is_network`: Whether the tool makes network calls
    /// - `has_purpose`: Whether a purpose was declared for this action
    /// - `homeostasis`: Current system state
    /// - `brain_wave`: Current brain-wave state
    #[allow(clippy::too_many_arguments, clippy::fn_params_excessive_bools)]
    pub fn evaluate(
        &self,
        tool_name: &str,
        args_hash: u64,
        is_write: bool,
        is_spawn: bool,
        is_network: bool,
        has_purpose: bool,
        homeostasis: &Homeostasis,
        brain_wave: BrainWave,
    ) -> ResourceVerdict {
        let now = chrono::Utc::now().timestamp();
        let health = homeostasis.health_score();

        // Budgets scale with health — when stressed, budgets shrink
        let health_scale = health.clamp(0.1, 1.0);
        let cfg = self.config();
        let write_limit = ((cfg.max_writes_per_minute as f32) * health_scale) as u32;
        let spawn_limit = ((cfg.max_spawns_per_minute as f32) * health_scale) as u32;
        let network_limit = ((cfg.max_network_per_minute as f32) * health_scale) as u32;

        // In low-power states, budgets are further reduced
        let (write_limit, spawn_limit, network_limit) = match brain_wave {
            BrainWave::Delta => (0, 0, 0),
            BrainWave::Theta => (write_limit / 4, 0, 0),
            BrainWave::Alpha => (write_limit / 2, spawn_limit / 4, network_limit / 4),
            _ => (write_limit, spawn_limit, network_limit),
        };

        // Check write budget
        if is_write {
            if let Ok(mut tracker) = self.write_budget.write() {
                let used = tracker.count_last_minute(now) as u32;
                if used >= write_limit {
                    return ResourceVerdict::BudgetExceeded {
                        resource: "writes",
                        used,
                        limit: write_limit,
                    };
                }
                tracker.record(now);
            }
        }

        // Check spawn budget
        if is_spawn {
            if let Ok(mut tracker) = self.spawn_budget.write() {
                let used = tracker.count_last_minute(now) as u32;
                if used >= spawn_limit {
                    return ResourceVerdict::BudgetExceeded {
                        resource: "spawns",
                        used,
                        limit: spawn_limit,
                    };
                }
                tracker.record(now);
            }
        }

        // Check network budget
        if is_network {
            if let Ok(mut tracker) = self.network_budget.write() {
                let used = tracker.count_last_minute(now) as u32;
                if used >= network_limit {
                    return ResourceVerdict::BudgetExceeded {
                        resource: "network",
                        used,
                        limit: network_limit,
                    };
                }
                tracker.record(now);
            }
        }

        // Check novelty — prevent circular thinking
        let sig = ActionSignature {
            tool_name: tool_name.to_string(),
            args_hash,
        };
        if let Ok(mut novelty) = self.novelty.write() {
            let repeats = novelty.iter().filter(|s| **s == sig).count() as u32;
            if repeats >= cfg.max_repeats {
                return ResourceVerdict::NotNovel {
                    tool_name: tool_name.to_string(),
                    repeats,
                    max: cfg.max_repeats,
                };
            }
            novelty.push_back(sig);
            if novelty.len() > cfg.novelty_window {
                novelty.pop_front();
            }
        }

        // Check if autonomous action requires human review
        let user_initiated = self.user_initiated.read().map(|g| *g).unwrap_or(true);
        if !user_initiated && cfg.require_human_review {
            let approved = self.human_approved.read().map(|g| *g).unwrap_or(false);
            if !approved {
                return ResourceVerdict::RequiresHumanReview {
                    tool_name: tool_name.to_string(),
                };
            }
        }

        // Check purpose requirement for autonomous actions
        if !user_initiated && !has_purpose {
            return ResourceVerdict::NoPurpose {
                tool_name: tool_name.to_string(),
            };
        }

        ResourceVerdict::Allow
    }

    /// Clear novelty history (e.g., when entering a new session).
    pub fn clear_novelty(&self) {
        if let Ok(mut n) = self.novelty.write() {
            n.clear();
        }
    }

    /// Get current budget usage counts (for monitoring/transparency).
    #[must_use]
    pub fn budget_usage(&self) -> BudgetUsage {
        let now = chrono::Utc::now().timestamp();
        BudgetUsage {
            writes_last_minute: self
                .write_budget
                .read()
                .map(|t| t.count_last_minute(now) as u32)
                .unwrap_or(0),
            spawns_last_minute: self
                .spawn_budget
                .read()
                .map(|t| t.count_last_minute(now) as u32)
                .unwrap_or(0),
            network_last_minute: self
                .network_budget
                .read()
                .map(|t| t.count_last_minute(now) as u32)
                .unwrap_or(0),
            novelty_entries: self.novelty.read().map(|n| n.len() as u32).unwrap_or(0),
        }
    }
}

/// Snapshot of current budget usage for monitoring.
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct BudgetUsage {
    /// Writes in the last minute.
    pub writes_last_minute: u32,
    /// Spawns in the last minute.
    pub spawns_last_minute: u32,
    /// Network calls in the last minute.
    pub network_last_minute: u32,
    /// Entries in the novelty tracking window.
    pub novelty_entries: u32,
}

/// Count action signatures by tool name for novelty reporting.
#[must_use]
pub fn novelty_report(novelty: &VecDeque<ActionSignature>) -> AHashMap<String, u32> {
    let mut counts = AHashMap::new();
    for sig in novelty {
        *counts.entry(sig.tool_name.clone()).or_insert(0) += 1;
    }
    counts
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn healthy() -> Homeostasis {
        Homeostasis {
            cpu_load: 0.1,
            memory_pressure: 0.1,
            active: true,
        }
    }

    fn perfect_health() -> Homeostasis {
        Homeostasis {
            cpu_load: 0.0,
            memory_pressure: 0.0,
            active: true,
        }
    }

    fn stressed() -> Homeostasis {
        Homeostasis {
            cpu_load: 0.9,
            memory_pressure: 0.9,
            active: true,
        }
    }

    #[test]
    fn allow_healthy_user_initiated() {
        let rules = ResourceRules::default();
        let h = healthy();
        let verdict = rules.evaluate(
            "memory.create",
            12345,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert_eq!(verdict, ResourceVerdict::Allow);
    }

    #[test]
    fn budget_exceeded_writes() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 3,
            max_spawns_per_minute: 10,
            max_network_per_minute: 30,
            novelty_window: 50,
            max_repeats: 100, // High to avoid triggering novelty first
            require_human_review: false,
        };
        let rules = ResourceRules::new(config);
        let h = perfect_health();

        // Use different args_hash each time to avoid novelty trigger
        for i in 0..3 {
            let v = rules.evaluate(
                "memory.create",
                i as u64,
                true,
                false,
                false,
                true,
                &h,
                BrainWave::Gamma,
            );
            assert_eq!(v, ResourceVerdict::Allow, "Call {i} should be allowed");
        }

        // 4th write should be blocked
        let v = rules.evaluate(
            "memory.create",
            99,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert!(
            matches!(v, ResourceVerdict::BudgetExceeded { resource, .. } if resource == "writes")
        );
    }

    #[test]
    fn budget_scales_with_health() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 100,
            max_spawns_per_minute: 10,
            max_network_per_minute: 30,
            novelty_window: 50,
            max_repeats: 100,
            require_human_review: false,
        };
        let rules = ResourceRules::new(config);
        let h = stressed();
        // Health ~0.1, so write_limit = 100 * 0.1 = 10
        // Should allow a few writes but not many
        for i in 0..10 {
            let v = rules.evaluate(
                "memory.create",
                i as u64,
                true,
                false,
                false,
                true,
                &h,
                BrainWave::Gamma,
            );
            assert_eq!(v, ResourceVerdict::Allow, "Call {i} should be allowed");
        }
        // 11th should be blocked
        let v = rules.evaluate(
            "memory.create",
            99,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert!(v.blocks());
    }

    #[test]
    fn delta_blocks_all_writes() {
        let rules = ResourceRules::default();
        let h = healthy();
        let v = rules.evaluate(
            "memory.create",
            1,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Delta,
        );
        assert!(
            matches!(v, ResourceVerdict::BudgetExceeded { resource, .. } if resource == "writes")
        );
    }

    #[test]
    fn theta_reduces_writes() {
        let rules = ResourceRules::default();
        let h = perfect_health();
        for i in 0..15 {
            let v = rules.evaluate(
                "memory.create",
                i as u64,
                true,
                false,
                false,
                true,
                &h,
                BrainWave::Theta,
            );
            assert_eq!(
                v,
                ResourceVerdict::Allow,
                "Call {i} should be allowed in Theta"
            );
        }
        let v = rules.evaluate(
            "memory.create",
            99,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Theta,
        );
        assert!(v.blocks());
    }

    #[test]
    fn novelty_blocks_repeats() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 1000,
            max_spawns_per_minute: 100,
            max_network_per_minute: 100,
            novelty_window: 50,
            max_repeats: 3,
            require_human_review: false,
        };
        let rules = ResourceRules::new(config);
        let h = healthy();

        // Same action 3 times — should be allowed
        for _ in 0..3 {
            let v = rules.evaluate(
                "dream.trigger",
                42, // Same args_hash
                false,
                false,
                false,
                true,
                &h,
                BrainWave::Gamma,
            );
            assert_eq!(v, ResourceVerdict::Allow);
        }

        // 4th time with same signature — blocked as not novel
        let v = rules.evaluate(
            "dream.trigger",
            42,
            false,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert!(
            matches!(v, ResourceVerdict::NotNovel { tool_name, .. } if tool_name == "dream.trigger")
        );
    }

    #[test]
    fn novelty_allows_different_args() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 1000,
            max_spawns_per_minute: 100,
            max_network_per_minute: 100,
            novelty_window: 50,
            max_repeats: 2,
            require_human_review: false,
        };
        let rules = ResourceRules::new(config);
        let h = healthy();

        // Same tool, different args — should be allowed
        for i in 0..10 {
            let v = rules.evaluate(
                "memory.create",
                i as u64, // Different args_hash each time
                true,
                false,
                false,
                true,
                &h,
                BrainWave::Gamma,
            );
            assert_eq!(
                v,
                ResourceVerdict::Allow,
                "Call {i} with different args should be allowed"
            );
        }
    }

    #[test]
    fn human_review_blocks_autonomous() {
        let rules = ResourceRules::default();
        let h = healthy();

        rules.set_user_initiated(false);
        // Not approved
        let v = rules.evaluate(
            "memory.consolidate",
            1,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert!(matches!(v, ResourceVerdict::RequiresHumanReview { .. }));
    }

    #[test]
    fn human_review_allows_when_approved() {
        let rules = ResourceRules::default();
        let h = healthy();

        rules.set_user_initiated(false);
        rules.set_human_approved(true);
        let v = rules.evaluate(
            "memory.consolidate",
            1,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert_eq!(v, ResourceVerdict::Allow);
    }

    #[test]
    fn human_review_not_required_for_user_initiated() {
        let rules = ResourceRules::default();
        let h = healthy();

        rules.set_user_initiated(true);
        let v = rules.evaluate(
            "memory.create",
            1,
            true,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert_eq!(v, ResourceVerdict::Allow);
    }

    #[test]
    fn purpose_required_for_autonomous() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 1000,
            max_spawns_per_minute: 100,
            max_network_per_minute: 100,
            novelty_window: 50,
            max_repeats: 100,
            require_human_review: false, // Disable to test purpose separately
        };
        let rules = ResourceRules::new(config);
        let h = healthy();

        rules.set_user_initiated(false);
        // No purpose
        let v = rules.evaluate(
            "memory.consolidate",
            1,
            true,
            false,
            false,
            false, // no purpose
            &h,
            BrainWave::Gamma,
        );
        assert!(matches!(v, ResourceVerdict::NoPurpose { .. }));

        // With purpose
        let v = rules.evaluate(
            "memory.consolidate",
            2,
            true,
            false,
            false,
            true, // has purpose
            &h,
            BrainWave::Gamma,
        );
        assert_eq!(v, ResourceVerdict::Allow);
    }

    #[test]
    fn budget_usage_tracking() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 1000,
            max_spawns_per_minute: 100,
            max_network_per_minute: 100,
            novelty_window: 50,
            max_repeats: 100,
            require_human_review: false,
        };
        let rules = ResourceRules::new(config);
        let h = healthy();

        for i in 0..5 {
            let _ = rules.evaluate(
                "memory.create",
                i as u64,
                true,
                false,
                false,
                true,
                &h,
                BrainWave::Gamma,
            );
        }

        let usage = rules.budget_usage();
        assert_eq!(usage.writes_last_minute, 5);
        assert_eq!(usage.spawns_last_minute, 0);
    }

    #[test]
    fn clear_novelty_resets() {
        let config = ResourceRulesConfig {
            max_writes_per_minute: 1000,
            max_spawns_per_minute: 100,
            max_network_per_minute: 100,
            novelty_window: 50,
            max_repeats: 2,
            require_human_review: false,
        };
        let rules = ResourceRules::new(config);
        let h = healthy();

        // Fill novelty
        for _ in 0..2 {
            let _ = rules.evaluate(
                "dream.trigger",
                42,
                false,
                false,
                false,
                true,
                &h,
                BrainWave::Gamma,
            );
        }
        // 3rd would be blocked
        let v = rules.evaluate(
            "dream.trigger",
            42,
            false,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert!(v.blocks());

        // Clear and try again
        rules.clear_novelty();
        let v = rules.evaluate(
            "dream.trigger",
            42,
            false,
            false,
            false,
            true,
            &h,
            BrainWave::Gamma,
        );
        assert_eq!(v, ResourceVerdict::Allow);
    }

    #[test]
    fn resource_verdict_reason() {
        let v = ResourceVerdict::Allow;
        assert_eq!(v.reason(), "allowed");
        assert!(!v.blocks());

        let v = ResourceVerdict::BudgetExceeded {
            resource: "writes",
            used: 10,
            limit: 5,
        };
        assert!(v.blocks());
        assert!(v.reason().contains("writes"));

        let v = ResourceVerdict::NotNovel {
            tool_name: "dream.trigger".into(),
            repeats: 3,
            max: 3,
        };
        assert!(v.blocks());
        assert!(v.reason().contains("dream.trigger"));

        let v = ResourceVerdict::RequiresHumanReview {
            tool_name: "memory.consolidate".into(),
        };
        assert!(v.blocks());
        assert!(v.reason().contains("human review"));

        let v = ResourceVerdict::NoPurpose {
            tool_name: "memory.consolidate".into(),
        };
        assert!(v.blocks());
        assert!(v.reason().contains("purpose"));
    }
}
