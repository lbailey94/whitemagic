//! Transaction firewall — `tx_firewall.set_policy`, `tx_firewall.status`,
//! `tx_firewall.check`.
//!
//! A policy gate for multi-tool transactional sequences. The firewall
//! declares which tools may participate in a transaction, how many
//! operations a transaction may contain, and whether rollback requires
//! explicit confirmation. Ports the v26 `tx_firewall.set_policy` surface.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::sync::RwLock;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};

/// Firewall policy for transactional tool use.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TxFirewallPolicy {
    /// Whether the firewall is active. Disabled = all tools allowed.
    pub enabled: bool,
    /// Tool name prefixes allowed inside a transaction (e.g. "memory.",
    /// "galaxy."). Empty = deny all when enabled.
    pub allowed_tool_prefixes: Vec<String>,
    /// Deny tools that do not match any allowed prefix.
    pub deny_unknown_tools: bool,
    /// Maximum operations per transaction.
    pub max_ops_per_transaction: u32,
    /// Whether rollback requires an explicit confirm flag.
    pub require_rollback_confirmation: bool,
}

impl Default for TxFirewallPolicy {
    fn default() -> Self {
        Self {
            enabled: false,
            allowed_tool_prefixes: vec!["memory.".into(), "galaxy.".into()],
            deny_unknown_tools: true,
            max_ops_per_transaction: 50,
            require_rollback_confirmation: true,
        }
    }
}

impl TxFirewallPolicy {
    /// Strict policy: only declarative memory ops, small transactions,
    /// rollback always confirmed.
    #[must_use]
    pub fn strict() -> Self {
        Self {
            enabled: true,
            allowed_tool_prefixes: vec!["memory.".into()],
            deny_unknown_tools: true,
            max_ops_per_transaction: 20,
            require_rollback_confirmation: true,
        }
    }
}

/// The transaction firewall — shared, persistable policy.
#[derive(Debug, Default)]
pub struct TxFirewall {
    policy: RwLock<TxFirewallPolicy>,
}

impl TxFirewall {
    /// Create a firewall with the default policy.
    #[must_use]
    pub fn new() -> Self {
        Self {
            policy: RwLock::new(TxFirewallPolicy::default()),
        }
    }

    /// Replace the policy (tx_firewall.set_policy).
    pub fn set_policy(&self, policy: TxFirewallPolicy) {
        if let Ok(mut p) = self.policy.write() {
            *p = policy;
        }
    }

    /// Current policy.
    #[must_use]
    pub fn policy(&self) -> TxFirewallPolicy {
        self.policy.read().map(|p| p.clone()).unwrap_or_default()
    }

    /// Check whether a tool may participate in a transaction.
    /// Returns `Ok(())` when allowed, or the denial reason.
    pub fn check(&self, tool: &str) -> Result<(), String> {
        let policy = self.policy();
        if !policy.enabled {
            return Ok(());
        }
        let allowed = policy
            .allowed_tool_prefixes
            .iter()
            .any(|prefix| tool.starts_with(prefix.as_str()));
        if allowed {
            Ok(())
        } else if policy.deny_unknown_tools {
            Err(format!(
                "tx firewall: tool '{tool}' is not allowed in transactions"
            ))
        } else {
            Ok(())
        }
    }

    /// Serialize for persistence.
    #[must_use]
    pub fn to_json(&self) -> Value {
        serde_json::to_value(self.policy()).unwrap_or_else(|_| json!({}))
    }

    /// Restore from persisted JSON.
    pub fn from_json(&self, value: &Value) -> Result<(), String> {
        let policy: TxFirewallPolicy =
            serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
        self.set_policy(policy);
        Ok(())
    }
}

/// `tx_firewall.set_policy` — update the transaction firewall policy.
pub struct TxFirewallSetPolicyTool {
    firewall: std::sync::Arc<TxFirewall>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TxFirewallSetPolicyTool {
    #[must_use]
    pub fn new(firewall: std::sync::Arc<TxFirewall>) -> Self {
        Self {
            firewall,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for TxFirewallSetPolicyTool {
    fn name(&self) -> &str {
        "tx_firewall.set_policy"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Set the transaction firewall policy. Args: enabled (bool), allowed_tool_prefixes (list), deny_unknown_tools (bool), max_ops_per_transaction (int), require_rollback_confirmation (bool), or profile: \"default\" | \"strict\"."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let profile = args.get("profile").and_then(Value::as_str);
        let mut policy = self.firewall.policy();
        match profile {
            Some("strict") => policy = TxFirewallPolicy::strict(),
            Some("default") => policy = TxFirewallPolicy::default(),
            Some(other) => {
                return Err(wm_core::CoreError::InvalidArgs(format!(
                    "unknown profile '{other}' (expected 'default' or 'strict')"
                )));
            }
            None => {}
        }
        if let Some(v) = args.get("enabled").and_then(Value::as_bool) {
            policy.enabled = v;
        }
        if let Some(v) = args.get("allowed_tool_prefixes").and_then(Value::as_array) {
            policy.allowed_tool_prefixes = v
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect();
        }
        if let Some(v) = args.get("deny_unknown_tools").and_then(Value::as_bool) {
            policy.deny_unknown_tools = v;
        }
        if let Some(v) = args.get("max_ops_per_transaction").and_then(Value::as_u64) {
            policy.max_ops_per_transaction = v as u32;
        }
        if let Some(v) = args
            .get("require_rollback_confirmation")
            .and_then(Value::as_bool)
        {
            policy.require_rollback_confirmation = v;
        }
        self.firewall.set_policy(policy.clone());
        Ok(json!({
            "status": "success",
            "policy": policy,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `tx_firewall.status` — show the current firewall policy and check a tool.
pub struct TxFirewallStatusTool {
    firewall: std::sync::Arc<TxFirewall>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TxFirewallStatusTool {
    #[must_use]
    pub fn new(firewall: std::sync::Arc<TxFirewall>) -> Self {
        Self {
            firewall,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::DharmaRules]),
        }
    }
}

#[async_trait]
impl Tool for TxFirewallStatusTool {
    fn name(&self) -> &str {
        "tx_firewall.status"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Show the transaction firewall policy, optionally checking a tool against it (check_tool arg)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let policy = self.firewall.policy();
        let mut result = json!({
            "status": "success",
            "policy": policy,
        });
        if let Some(tool) = args.get("check_tool").and_then(Value::as_str) {
            match self.firewall.check(tool) {
                Ok(()) => {
                    result["check"] = json!({"tool": tool, "allowed": true});
                }
                Err(reason) => {
                    result["check"] = json!({"tool": tool, "allowed": false, "reason": reason});
                }
            }
        }
        Ok(result)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the firewall tools (2).
#[must_use]
pub fn register_firewall(
    registry: &wm_dispatch::ToolRegistry,
    firewall: std::sync::Arc<TxFirewall>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(std::sync::Arc::new(TxFirewallSetPolicyTool::new(
            firewall.clone(),
        )))
        .register(std::sync::Arc::new(TxFirewallStatusTool::new(firewall)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_policy_allows_memory_prefix() {
        let firewall = TxFirewall::new();
        assert!(firewall.check("memory.create").is_ok());
        assert!(firewall.check("galaxy.stats").is_ok());
        assert!(firewall.check("web.fetch").is_ok()); // disabled by default
    }

    #[test]
    fn strict_policy_denies_unknown_tools() {
        let firewall = TxFirewall::new();
        firewall.set_policy(TxFirewallPolicy::strict());
        assert!(firewall.check("memory.create").is_ok());
        assert!(firewall.check("web.fetch").is_err());
        assert!(firewall.check("galaxy.stats").is_err());
    }

    #[test]
    fn disabled_firewall_allows_everything() {
        let firewall = TxFirewall::new();
        firewall.set_policy(TxFirewallPolicy {
            enabled: false,
            ..TxFirewallPolicy::default()
        });
        assert!(firewall.check("anything.else").is_ok());
    }

    #[test]
    fn json_roundtrip() {
        let firewall = TxFirewall::new();
        firewall.set_policy(TxFirewallPolicy::strict());
        let json = firewall.to_json();
        let restored = TxFirewall::new();
        restored.from_json(&json).unwrap();
        assert!(restored.check("web.fetch").is_err());
        assert!(restored.check("memory.read").is_ok());
        assert_eq!(restored.policy().max_ops_per_transaction, 20);
    }
}
