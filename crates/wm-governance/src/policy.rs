//! Dharma Policy — Runtime-configurable governance rules with OWASP Agentic
//! Top 10 mapping.
//!
//! Allows operators to tune DharmaGate thresholds, enable/disable sutras,
//! and define custom rules without recompiling. Each policy rule maps to
//! one or more OWASP Agentic Top 10 (2025) categories for auditability.

use std::sync::RwLock;

use wm_core::{BrainWave, EffectRow, Resource};

/// OWASP Agentic AI Threat & Vulnerability Taxonomy (2025).
///
/// See: https://genai.owasp.org/llm-top-10/
/// Extended for agentic systems with autonomous tool use.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OwaspAgentic {
    /// LLM01 — Prompt injection (direct or indirect)
    PromptInjection,
    /// LLM02 — Sensitive information disclosure
    SensitiveInfoDisclosure,
    /// LLM03 — Supply chain vulnerabilities
    SupplyChain,
    /// LLM04 — Data and model poisoning
    DataModelPoisoning,
    /// LLM05 — Improper output handling / SSRF
    ImproperOutputHandling,
    /// LLM06 — Excessive agency / autonomous action without guardrails
    ExcessiveAgency,
    /// LLM07 — System prompt leakage
    SystemPromptLeakage,
    /// LLM08 — Vector and embedding weaknesses
    VectorEmbeddingWeaknesses,
    /// LLM09 — Misinformation / hallucination
    Misinformation,
    /// LLM10 — Unbounded consumption (resource exhaustion)
    UnboundedConsumption,
}

impl OwaspAgentic {
    /// All variants in canonical order.
    #[must_use]
    pub const fn all() -> &'static [Self] {
        &[
            Self::PromptInjection,
            Self::SensitiveInfoDisclosure,
            Self::SupplyChain,
            Self::DataModelPoisoning,
            Self::ImproperOutputHandling,
            Self::ExcessiveAgency,
            Self::SystemPromptLeakage,
            Self::VectorEmbeddingWeaknesses,
            Self::Misinformation,
            Self::UnboundedConsumption,
        ]
    }

    /// Short code (e.g., "LLM01").
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::PromptInjection => "LLM01",
            Self::SensitiveInfoDisclosure => "LLM02",
            Self::SupplyChain => "LLM03",
            Self::DataModelPoisoning => "LLM04",
            Self::ImproperOutputHandling => "LLM05",
            Self::ExcessiveAgency => "LLM06",
            Self::SystemPromptLeakage => "LLM07",
            Self::VectorEmbeddingWeaknesses => "LLM08",
            Self::Misinformation => "LLM09",
            Self::UnboundedConsumption => "LLM10",
        }
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::PromptInjection => "Prompt Injection",
            Self::SensitiveInfoDisclosure => "Sensitive Information Disclosure",
            Self::SupplyChain => "Supply Chain Vulnerabilities",
            Self::DataModelPoisoning => "Data and Model Poisoning",
            Self::ImproperOutputHandling => "Improper Output Handling / SSRF",
            Self::ExcessiveAgency => "Excessive Agency",
            Self::SystemPromptLeakage => "System Prompt Leakage",
            Self::VectorEmbeddingWeaknesses => "Vector and Embedding Weaknesses",
            Self::Misinformation => "Misinformation / Hallucination",
            Self::UnboundedConsumption => "Unbounded Consumption",
        }
    }
}

/// A single policy rule with OWASP mapping.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PolicyRule {
    /// Unique rule identifier (e.g., "ahimsa_block_destructive").
    pub id: String,
    /// Human-readable description.
    pub description: String,
    /// Whether this rule is enabled.
    pub enabled: bool,
    /// OWASP categories this rule addresses.
    pub owasp_mappings: Vec<OwaspAgentic>,
    /// The sutra this rule implements (e.g., "Ahimsa", "Satya").
    pub sutra: String,
}

/// Runtime-configurable Dharma policy.
///
/// Controls which governance rules are active and their thresholds.
/// Can be loaded from JSON config at startup or updated at runtime.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DharmaPolicy {
    /// Whether the Ahimsa sutra (non-harm) is enabled.
    pub ahimsa_enabled: bool,
    /// Whether the Satya sutra (truth) is enabled.
    pub satya_enabled: bool,
    /// Minimum maturity level for destructive actions (1-5).
    pub min_maturity_destructive: u8,
    /// Karma debt threshold for blocking (Intervene).
    pub karma_block_threshold: f32,
    /// Karma debt threshold for warning (Correct).
    pub karma_warn_threshold: f32,
    /// Intent score threshold for blocking.
    pub intent_block_threshold: f32,
    /// Health score threshold for strict mode.
    pub strict_mode_health_threshold: f32,
    /// Whether to block network access to private IPs (SSRF defense).
    pub block_private_network: bool,
    /// Whether to require provenance signatures on memory writes.
    pub require_provenance: bool,
    /// Maximum allowed tool calls per minute (unbounded consumption defense).
    pub max_tool_calls_per_minute: u32,
    /// Whether autonomous actions require human review.
    pub require_human_review: bool,
    /// ACS Output checkpoint (L2): deny egress to hosts not on the
    /// allowlist. Unknown hosts are blocked; allowlisted hosts pass.
    #[serde(default)]
    pub tier2_deny_unknown_egress: bool,
    /// Hosts permitted for network egress when
    /// `tier2_deny_unknown_egress` is enabled (e.g. "api.example.com").
    #[serde(default)]
    pub egress_allowlist: Vec<String>,
    /// ACS Output checkpoint (L3): validate output size/content before it
    /// leaves the agent.
    #[serde(default)]
    pub tier3_output_validation: bool,
    /// Maximum output size (bytes) enforced when `tier3_output_validation`
    /// is enabled.
    #[serde(default = "default_output_max_bytes")]
    pub output_max_bytes: u32,
    /// Custom policy rules.
    pub custom_rules: Vec<PolicyRule>,
}

/// Default output size cap: 1 MiB.
const fn default_output_max_bytes() -> u32 {
    1_048_576
}

impl Default for DharmaPolicy {
    fn default() -> Self {
        Self {
            ahimsa_enabled: true,
            satya_enabled: true,
            min_maturity_destructive: 4,
            karma_block_threshold: 0.3,
            karma_warn_threshold: 0.5,
            intent_block_threshold: 0.3,
            strict_mode_health_threshold: 0.3,
            block_private_network: true,
            require_provenance: false,
            max_tool_calls_per_minute: 60,
            require_human_review: true,
            tier2_deny_unknown_egress: false,
            egress_allowlist: Vec::new(),
            tier3_output_validation: false,
            output_max_bytes: default_output_max_bytes(),
            custom_rules: vec![
                PolicyRule {
                    id: "ahimsa_block_destructive".into(),
                    description:
                        "Block destructive actions (Filesystem, Process, Network) in strict mode"
                            .into(),
                    enabled: true,
                    owasp_mappings: vec![
                        OwaspAgentic::ExcessiveAgency,
                        OwaspAgentic::ImproperOutputHandling,
                    ],
                    sutra: "Ahimsa".into(),
                },
                PolicyRule {
                    id: "satya_block_fabrication".into(),
                    description: "Block memory fabrication (writing to citta without reading)"
                        .into(),
                    enabled: true,
                    owasp_mappings: vec![
                        OwaspAgentic::Misinformation,
                        OwaspAgentic::DataModelPoisoning,
                    ],
                    sutra: "Satya".into(),
                },
                PolicyRule {
                    id: "karma_debt_block".into(),
                    description: "Block actions when cumulative karma debt exceeds threshold"
                        .into(),
                    enabled: true,
                    owasp_mappings: vec![OwaspAgentic::ExcessiveAgency],
                    sutra: "Karma".into(),
                },
                PolicyRule {
                    id: "ssrf_block_private".into(),
                    description: "Block network access to private/internal IP ranges".into(),
                    enabled: true,
                    owasp_mappings: vec![OwaspAgentic::ImproperOutputHandling],
                    sutra: "Ahimsa".into(),
                },
                PolicyRule {
                    id: "unbounded_consumption_limit".into(),
                    description: "Rate-limit tool calls to prevent unbounded resource consumption"
                        .into(),
                    enabled: true,
                    owasp_mappings: vec![OwaspAgentic::UnboundedConsumption],
                    sutra: "Brahmacharya".into(),
                },
            ],
        }
    }
}

impl DharmaPolicy {
    /// Strict policy for Secure compartments.
    #[must_use]
    pub fn strict() -> Self {
        Self {
            min_maturity_destructive: 5,
            karma_block_threshold: 0.5,
            karma_warn_threshold: 0.7,
            intent_block_threshold: 0.5,
            strict_mode_health_threshold: 0.5,
            block_private_network: true,
            require_provenance: true,
            max_tool_calls_per_minute: 15,
            require_human_review: true,
            tier2_deny_unknown_egress: true,
            tier3_output_validation: true,
            output_max_bytes: 512_000,
            ..Self::default()
        }
    }

    /// Permissive policy for Research compartments.
    #[must_use]
    pub fn permissive() -> Self {
        Self {
            min_maturity_destructive: 3,
            karma_block_threshold: 0.1,
            karma_warn_threshold: 0.3,
            intent_block_threshold: 0.1,
            strict_mode_health_threshold: 0.1,
            require_human_review: false,
            max_tool_calls_per_minute: 200,
            ..Self::default()
        }
    }

    /// Load policy from JSON.
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    /// Serialize policy to JSON.
    #[must_use]
    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_else(|_| "{}".into())
    }

    /// Get all enabled rules with their OWASP mappings.
    #[must_use]
    pub fn enabled_rules(&self) -> Vec<&PolicyRule> {
        self.custom_rules.iter().filter(|r| r.enabled).collect()
    }

    /// Get all OWASP categories covered by enabled rules.
    #[must_use]
    pub fn owasp_coverage(&self) -> Vec<OwaspAgentic> {
        let mut seen = std::collections::HashSet::new();
        let mut result = Vec::new();
        for rule in self.enabled_rules() {
            for &owasp in &rule.owasp_mappings {
                if seen.insert(owasp) {
                    result.push(owasp);
                }
            }
        }
        result
    }

    /// Check if a specific OWASP category is covered by any enabled rule.
    #[must_use]
    pub fn covers(&self, owasp: OwaspAgentic) -> bool {
        self.enabled_rules()
            .iter()
            .any(|r| r.owasp_mappings.contains(&owasp))
    }

    /// Whether the given host is permitted for network egress.
    ///
    /// When `tier2_deny_unknown_egress` is enabled, only allowlisted hosts
    /// (exact match, or subdomain of an allowlisted domain) may be reached.
    #[must_use]
    pub fn egress_allowed(&self, host: &str) -> bool {
        if !self.tier2_deny_unknown_egress {
            return true;
        }
        if host.is_empty() {
            return false;
        }
        let host = host.to_ascii_lowercase();
        self.egress_allowlist.iter().any(|allowed| {
            let allowed = allowed.to_ascii_lowercase();
            allowed == host || host.ends_with(&format!(".{allowed}"))
        })
    }

    /// Check a network egress target against the ACS Output checkpoint.
    /// Returns an error message when the target is denied.
    #[must_use]
    pub fn check_egress(&self, host: &str) -> Option<String> {
        if self.tier2_deny_unknown_egress && !self.egress_allowed(host) {
            return Some(format!(
                "egress denied by tier2_deny_unknown_egress: host '{host}' is not allowlisted"
            ));
        }
        None
    }

    /// Generate an OWASP compliance report.
    #[must_use]
    pub fn owasp_report(&self) -> OwaspComplianceReport {
        let all = OwaspAgentic::all();
        let covered = self.owasp_coverage();
        let missing: Vec<OwaspAgentic> = all
            .iter()
            .copied()
            .filter(|o| !covered.contains(o))
            .collect();
        OwaspComplianceReport {
            total_categories: all.len(),
            covered_count: covered.len(),
            covered,
            missing,
            policy_version: "4.0.0".to_string(),
        }
    }
}

/// OWASP compliance report — shows which categories are covered by policy.
#[derive(Debug, Clone, serde::Serialize)]
pub struct OwaspComplianceReport {
    /// Total OWASP categories (10).
    pub total_categories: usize,
    /// Number of categories covered by enabled rules.
    pub covered_count: usize,
    /// Categories covered.
    pub covered: Vec<OwaspAgentic>,
    /// Categories not covered.
    pub missing: Vec<OwaspAgentic>,
    /// Policy version.
    pub policy_version: String,
}

impl OwaspComplianceReport {
    /// Coverage percentage (0-100).
    #[must_use]
    pub fn coverage_percent(&self) -> f32 {
        if self.total_categories == 0 {
            return 100.0;
        }
        (self.covered_count as f32 / self.total_categories as f32) * 100.0
    }

    /// Whether all categories are covered.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.missing.is_empty()
    }
}

/// Thread-safe wrapper for runtime-updatable Dharma policy.
pub struct PolicyEngine {
    policy: RwLock<DharmaPolicy>,
}

impl PolicyEngine {
    /// Create a new policy engine with the given policy.
    #[must_use]
    pub const fn new(policy: DharmaPolicy) -> Self {
        Self {
            policy: RwLock::new(policy),
        }
    }

    /// Create with default policy.
    #[must_use]
    #[allow(clippy::should_implement_trait)]
    pub fn default() -> Self {
        Self::new(DharmaPolicy::default())
    }

    /// Get a snapshot of the current policy.
    pub fn policy(&self) -> DharmaPolicy {
        self.policy.read().map(|p| p.clone()).unwrap_or_default()
    }

    /// Update the policy at runtime.
    ///
    /// Returns an error if the new policy would weaken Ahimsa (non-harm)
    /// protections that are currently enabled. This prevents runtime
    /// policy updates from bypassing Dharma constraints.
    pub fn update(&self, policy: DharmaPolicy) -> Result<(), PolicyUpdateError> {
        let current = self.policy();
        validate_ahimsa_preservation(&current, &policy)?;
        if let Ok(mut guard) = self.policy.write() {
            *guard = policy;
        }
        Ok(())
    }

    /// Update policy from JSON.
    pub fn update_from_json(&self, json: &str) -> Result<(), PolicyUpdateError> {
        let policy = DharmaPolicy::from_json(json)?;
        self.update(policy)
    }

    /// Add a single custom rule at runtime.
    ///
    /// Returns an error if the rule contradicts Ahimsa (e.g., a rule
    /// that would allow destructive actions at low maturity).
    pub fn add_rule(&self, rule: PolicyRule) -> Result<(), PolicyUpdateError> {
        let mut policy = self.policy();
        validate_rule_against_ahimsa(&policy, &rule)?;
        policy.custom_rules.push(rule);
        self.update(policy)
    }

    /// Check if a rule is enabled by ID.
    #[must_use]
    pub fn is_rule_enabled(&self, rule_id: &str) -> bool {
        self.policy()
            .custom_rules
            .iter()
            .any(|r| r.id == rule_id && r.enabled)
    }

    /// Generate an OWASP compliance report.
    #[must_use]
    pub fn owasp_report(&self) -> OwaspComplianceReport {
        self.policy().owasp_report()
    }

    /// Evaluate whether a resource access is allowed under the current policy.
    ///
    /// This is a lightweight check that complements DharmaGate's ethical
    /// evaluation with policy-based access control.
    #[must_use]
    pub fn check_resource_access(&self, effects: &EffectRow, bw: BrainWave) -> PolicyCheckResult {
        let policy = self.policy();

        // Check Ahimsa: destructive resources
        if policy.ahimsa_enabled {
            let is_destructive = effects.writes.iter().any(|r| {
                matches!(
                    r,
                    Resource::Filesystem | Resource::Process | Resource::Network
                )
            }) || effects.spawns;

            if is_destructive {
                let maturity = match bw {
                    BrainWave::Gamma => 5,
                    BrainWave::Beta => 4,
                    BrainWave::Alpha => 3,
                    BrainWave::Theta => 2,
                    BrainWave::Delta => 1,
                };
                if maturity < policy.min_maturity_destructive {
                    return PolicyCheckResult::Deny {
                        rule_id: "ahimsa_block_destructive".into(),
                        reason: format!(
                            "Maturity {maturity} below required {} for destructive actions",
                            policy.min_maturity_destructive
                        ),
                        owasp: vec![OwaspAgentic::ExcessiveAgency],
                    };
                }
            }
        }

        // Check Satya: memory fabrication
        if policy.satya_enabled {
            let writes_citta = effects
                .writes
                .iter()
                .any(|r| matches!(r, Resource::Galaxy(g) if g == "citta"));
            let reads_citta = effects
                .reads
                .iter()
                .any(|r| matches!(r, Resource::Galaxy(g) if g == "citta"));

            if writes_citta && !reads_citta {
                return PolicyCheckResult::Deny {
                    rule_id: "satya_block_fabrication".into(),
                    reason: "Memory fabrication: writing to citta without reading".into(),
                    owasp: vec![
                        OwaspAgentic::Misinformation,
                        OwaspAgentic::DataModelPoisoning,
                    ],
                };
            }
        }

        PolicyCheckResult::Allow
    }
}

/// Result of a policy check.
#[derive(Debug, Clone)]
pub enum PolicyCheckResult {
    /// Access allowed.
    Allow,
    /// Access denied.
    Deny {
        /// Rule ID that triggered the denial.
        rule_id: String,
        /// Human-readable reason.
        reason: String,
        /// OWASP categories relevant to this denial.
        owasp: Vec<OwaspAgentic>,
    },
}

impl PolicyCheckResult {
    /// Whether access is allowed.
    #[must_use]
    pub const fn is_allowed(&self) -> bool {
        matches!(self, Self::Allow)
    }

    /// Whether access is denied.
    #[must_use]
    pub const fn is_denied(&self) -> bool {
        !self.is_allowed()
    }
}

// ── Policy Update Validation ──────────────────────────────────────────

/// Error returned when a policy update would violate Dharma constraints.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PolicyUpdateError {
    /// Attempted to disable Ahimsa while it is currently enabled.
    AhimsaDisabled,
    /// Attempted to lower the minimum maturity for destructive actions.
    MaturityLowered { old: u8, new: u8 },
    /// Attempted to disable the Ahimsa block-destructive rule.
    AhimsaRuleDisabled,
    /// Attempted to add a rule that contradicts Ahimsa.
    RuleContradictsAhimsa,
    /// JSON parse error during policy update.
    JsonParse,
}

impl std::fmt::Display for PolicyUpdateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::AhimsaDisabled => {
                f.write_str("Cannot disable Ahimsa (non-harm) while it is currently enabled")
            }
            Self::MaturityLowered { old, new } => {
                write!(
                    f,
                    "Cannot lower min_maturity_destructive from {old} to {new}"
                )
            }
            Self::AhimsaRuleDisabled => {
                f.write_str("Cannot disable the ahimsa_block_destructive rule")
            }
            Self::RuleContradictsAhimsa => {
                f.write_str("New rule contradicts Ahimsa (non-harm) constraints")
            }
            Self::JsonParse => f.write_str("Failed to parse policy JSON"),
        }
    }
}

impl std::error::Error for PolicyUpdateError {}

impl From<serde_json::Error> for PolicyUpdateError {
    fn from(_e: serde_json::Error) -> Self {
        Self::JsonParse
    }
}

/// Validate that a policy update does not weaken Ahimsa protections.
fn validate_ahimsa_preservation(
    current: &DharmaPolicy,
    new: &DharmaPolicy,
) -> Result<(), PolicyUpdateError> {
    // Cannot disable Ahimsa if it's currently enabled
    if current.ahimsa_enabled && !new.ahimsa_enabled {
        return Err(PolicyUpdateError::AhimsaDisabled);
    }

    // Cannot lower min_maturity_destructive (would weaken destructive action guard)
    if current.ahimsa_enabled && new.min_maturity_destructive < current.min_maturity_destructive {
        return Err(PolicyUpdateError::MaturityLowered {
            old: current.min_maturity_destructive,
            new: new.min_maturity_destructive,
        });
    }

    // Cannot disable the ahimsa_block_destructive rule if it's currently enabled
    if current.ahimsa_enabled {
        let current_ahimsa_rule = current
            .custom_rules
            .iter()
            .find(|r| r.id == "ahimsa_block_destructive");
        if let Some(current_rule) = current_ahimsa_rule {
            if current_rule.enabled {
                let new_ahimsa_rule = new
                    .custom_rules
                    .iter()
                    .find(|r| r.id == "ahimsa_block_destructive");
                match new_ahimsa_rule {
                    None => {
                        return Err(PolicyUpdateError::AhimsaRuleDisabled);
                    }
                    Some(new_rule) if !new_rule.enabled => {
                        return Err(PolicyUpdateError::AhimsaRuleDisabled);
                    }
                    _ => {}
                }
            }
        }
    }

    Ok(())
}

/// Validate that a new rule doesn't contradict Ahimsa constraints.
fn validate_rule_against_ahimsa(
    policy: &DharmaPolicy,
    rule: &PolicyRule,
) -> Result<(), PolicyUpdateError> {
    // A rule that tries to override the Ahimsa block-destructive rule is rejected
    if rule.id == "ahimsa_block_destructive" && !rule.enabled && policy.ahimsa_enabled {
        return Err(PolicyUpdateError::RuleContradictsAhimsa);
    }

    // A rule with "allow" in its description that references destructive actions is suspicious
    let desc_lower = rule.description.to_lowercase();
    if policy.ahimsa_enabled
        && desc_lower.contains("allow")
        && (desc_lower.contains("destructive") || desc_lower.contains("harm"))
        && rule.sutra == "Ahimsa"
    {
        return Err(PolicyUpdateError::RuleContradictsAhimsa);
    }

    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_policy_has_rules() {
        let policy = DharmaPolicy::default();
        assert!(!policy.custom_rules.is_empty());
        assert!(policy.ahimsa_enabled);
        assert!(policy.satya_enabled);
    }

    #[test]
    fn strict_policy_tighter_thresholds() {
        let strict = DharmaPolicy::strict();
        let default = DharmaPolicy::default();
        assert!(strict.min_maturity_destructive >= default.min_maturity_destructive);
        assert!(strict.karma_block_threshold >= default.karma_block_threshold);
        assert!(strict.max_tool_calls_per_minute <= default.max_tool_calls_per_minute);
    }

    #[test]
    fn permissive_policy_relaxed() {
        let perm = DharmaPolicy::permissive();
        let default = DharmaPolicy::default();
        assert!(perm.min_maturity_destructive <= default.min_maturity_destructive);
        assert!(perm.karma_block_threshold <= default.karma_block_threshold);
    }

    #[test]
    fn owasp_coverage_includes_key_categories() {
        let policy = DharmaPolicy::default();
        let report = policy.owasp_report();
        assert!(
            report.covered_count >= 4,
            "Should cover at least 4 OWASP categories"
        );
        assert!(policy.covers(OwaspAgentic::ExcessiveAgency));
        assert!(policy.covers(OwaspAgentic::ImproperOutputHandling));
        assert!(policy.covers(OwaspAgentic::UnboundedConsumption));
    }

    #[test]
    fn owasp_report_coverage_percent() {
        let policy = DharmaPolicy::default();
        let report = policy.owasp_report();
        let pct = report.coverage_percent();
        assert!(pct > 0.0 && pct <= 100.0);
    }

    #[test]
    fn policy_json_roundtrip() {
        let policy = DharmaPolicy::default();
        let json = policy.to_json();
        let restored = DharmaPolicy::from_json(&json).unwrap();
        assert_eq!(restored.ahimsa_enabled, policy.ahimsa_enabled);
        assert_eq!(restored.satya_enabled, policy.satya_enabled);
        assert_eq!(restored.custom_rules.len(), policy.custom_rules.len());
    }

    #[test]
    fn policy_engine_update() {
        let engine = PolicyEngine::default();
        // Valid update: tightening thresholds (Ahimsa stays enabled)
        let new_policy = DharmaPolicy {
            karma_block_threshold: 0.2,
            ..DharmaPolicy::default()
        };
        assert!(engine.update(new_policy).is_ok());
        assert!((engine.policy().karma_block_threshold - 0.2).abs() < f32::EPSILON);
    }

    #[test]
    fn policy_engine_update_rejects_ahimsa_disable() {
        let engine = PolicyEngine::default();
        let new_policy = DharmaPolicy {
            ahimsa_enabled: false,
            ..DharmaPolicy::default()
        };
        let result = engine.update(new_policy);
        assert!(result.is_err());
        // Original policy should be unchanged
        assert!(engine.policy().ahimsa_enabled);
    }

    #[test]
    fn policy_engine_update_rejects_lowered_maturity() {
        let engine = PolicyEngine::default();
        // Default min_maturity_destructive is 4; try to lower to 1
        let new_policy = DharmaPolicy {
            min_maturity_destructive: 1,
            ..DharmaPolicy::default()
        };
        let result = engine.update(new_policy);
        assert!(result.is_err());
        assert_eq!(engine.policy().min_maturity_destructive, 4);
    }

    #[test]
    fn policy_engine_update_from_json() {
        let engine = PolicyEngine::default();
        // Valid JSON update: keeps Ahimsa enabled, changes other fields
        // Must include custom_rules that preserve ahimsa_block_destructive
        let default = DharmaPolicy::default();
        let rules_json: String = default
            .custom_rules
            .iter()
            .map(|r| serde_json::to_string(r).unwrap())
            .collect::<Vec<_>>()
            .join(",");
        let json = format!(
            r#"{{"ahimsa_enabled": true, "satya_enabled": true, "min_maturity_destructive": 5, "karma_block_threshold": 0.1, "karma_warn_threshold": 0.3, "intent_block_threshold": 0.2, "strict_mode_health_threshold": 0.2, "block_private_network": true, "require_provenance": false, "max_tool_calls_per_minute": 100, "require_human_review": false, "custom_rules": [{rules_json}]}}"#
        );
        engine.update_from_json(&json).unwrap();
        assert!(engine.policy().ahimsa_enabled);
        assert!(!engine.policy().require_human_review);
    }

    #[test]
    fn policy_engine_update_from_json_rejects_ahimsa_disable() {
        let engine = PolicyEngine::default();
        let json = r#"{"ahimsa_enabled": false, "satya_enabled": true, "min_maturity_destructive": 3, "karma_block_threshold": 0.1, "karma_warn_threshold": 0.3, "intent_block_threshold": 0.2, "strict_mode_health_threshold": 0.2, "block_private_network": true, "require_provenance": false, "max_tool_calls_per_minute": 100, "require_human_review": false, "custom_rules": []}"#;
        let result = engine.update_from_json(json);
        assert!(result.is_err());
        assert!(engine.policy().ahimsa_enabled);
    }

    #[test]
    fn policy_engine_add_rule_rejects_ahimsa_contradiction() {
        let engine = PolicyEngine::default();
        // Try to add a rule that claims destructive actions are always safe
        let rule = PolicyRule {
            id: "allow_all_destructive".into(),
            description: "Allow all destructive actions regardless of maturity".into(),
            enabled: true,
            owasp_mappings: vec![],
            sutra: "Ahimsa".into(),
        };
        // Should be rejected: description contains "allow" + "destructive" with sutra "Ahimsa"
        let result = engine.add_rule(rule);
        assert!(result.is_err());
        assert_eq!(
            result.unwrap_err(),
            PolicyUpdateError::RuleContradictsAhimsa
        );
    }

    #[test]
    fn policy_engine_add_rule_allows_benign_rule() {
        let engine = PolicyEngine::default();
        let rule = PolicyRule {
            id: "log_all_access".into(),
            description: "Log all resource access for audit".into(),
            enabled: true,
            owasp_mappings: vec![OwaspAgentic::SensitiveInfoDisclosure],
            sutra: "Satya".into(),
        };
        assert!(engine.add_rule(rule).is_ok());
        assert!(engine.is_rule_enabled("log_all_access"));
    }

    #[test]
    fn check_resource_access_allows_read() {
        let engine = PolicyEngine::default();
        let effects = EffectRow::read_only(vec![Resource::Galaxy("codex".into())]);
        let result = engine.check_resource_access(&effects, BrainWave::Gamma);
        assert!(result.is_allowed());
    }

    #[test]
    fn check_resource_access_denies_destructive_low_maturity() {
        let engine = PolicyEngine::default();
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            ..Default::default()
        };
        let result = engine.check_resource_access(&effects, BrainWave::Alpha);
        assert!(result.is_denied());
    }

    #[test]
    fn check_resource_access_allows_destructive_high_maturity() {
        let engine = PolicyEngine::default();
        let effects = EffectRow {
            writes: vec![Resource::Filesystem],
            ..Default::default()
        };
        let result = engine.check_resource_access(&effects, BrainWave::Gamma);
        assert!(result.is_allowed());
    }

    #[test]
    fn check_resource_access_denies_fabrication() {
        let engine = PolicyEngine::default();
        let effects = EffectRow {
            writes: vec![Resource::Galaxy("citta".into())],
            reads: vec![],
            ..Default::default()
        };
        let result = engine.check_resource_access(&effects, BrainWave::Gamma);
        assert!(result.is_denied());
    }

    #[test]
    fn owasp_codes_and_names() {
        assert_eq!(OwaspAgentic::PromptInjection.code(), "LLM01");
        assert_eq!(OwaspAgentic::ExcessiveAgency.code(), "LLM06");
        assert_eq!(OwaspAgentic::UnboundedConsumption.code(), "LLM10");
        assert!(!OwaspAgentic::PromptInjection.name().is_empty());
    }

    #[test]
    fn owasp_all_has_10() {
        assert_eq!(OwaspAgentic::all().len(), 10);
    }

    #[test]
    fn enabled_rules_filters_disabled() {
        let mut policy = DharmaPolicy::default();
        policy.custom_rules[0].enabled = false;
        let enabled = policy.enabled_rules();
        assert!(enabled.iter().all(|r| r.enabled));
    }

    #[test]
    fn policy_engine_update_allows_ahimsa_already_disabled() {
        // If Ahimsa is already disabled, updating to another disabled state is fine
        let engine = PolicyEngine::new(DharmaPolicy {
            ahimsa_enabled: false,
            ..DharmaPolicy::default()
        });
        let new_policy = DharmaPolicy {
            ahimsa_enabled: false,
            karma_block_threshold: 0.1,
            ..DharmaPolicy::default()
        };
        assert!(engine.update(new_policy).is_ok());
    }

    #[test]
    fn policy_engine_update_rejects_disabling_ahimsa_rule() {
        let engine = PolicyEngine::default();
        // Try to update with the ahimsa_block_destructive rule disabled
        let mut new_policy = DharmaPolicy::default();
        if let Some(rule) = new_policy
            .custom_rules
            .iter_mut()
            .find(|r| r.id == "ahimsa_block_destructive")
        {
            rule.enabled = false;
        }
        let result = engine.update(new_policy);
        assert!(result.is_err());
    }

    #[test]
    fn owasp_report_is_complete_with_all_rules() {
        let mut policy = DharmaPolicy::default();
        // Add rules to cover all 10 categories
        let covered: std::collections::HashSet<_> = policy.owasp_coverage().into_iter().collect();
        for &owasp in OwaspAgentic::all() {
            if !covered.contains(&owasp) {
                policy.custom_rules.push(PolicyRule {
                    id: format!("rule_{owasp:?}"),
                    description: format!("Cover {owasp:?}"),
                    enabled: true,
                    owasp_mappings: vec![owasp],
                    sutra: "Custom".into(),
                });
            }
        }
        let report = policy.owasp_report();
        assert!(
            report.is_complete(),
            "All OWASP categories should be covered"
        );
        assert_eq!(report.coverage_percent(), 100.0);
    }
}
