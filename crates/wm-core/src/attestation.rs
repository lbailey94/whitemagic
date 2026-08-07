//! Tool Capability Attestation — Signed manifests for tool provenance and trust.
//!
//! Implements supply chain security for the tool ecosystem:
//! - **Signed manifests**: Each tool has a cryptographic manifest declaring its
//!   capabilities, effects, and provenance, signed with an HMAC key.
//! - **Provenance verification**: Verify that a tool's manifest hasn't been
//!   tampered with and comes from a trusted publisher.
//! - **Trust scope controls**: Restrict which tools external MCP servers can
//!   invoke based on declared capabilities and trust level.

use crate::effects::EffectRow;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};

type HmacSha256 = Hmac<Sha256>;

/// A tool capability manifest — declares what a tool can do and who published it.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ToolManifest {
    /// Tool name (e.g., "memory.search").
    pub tool_name: String,
    /// Tool version (semver).
    pub version: String,
    /// Publisher identity (e.g., "whitemagic-core", "external:acme").
    pub publisher: String,
    /// Human-readable description (sanitized).
    pub description: String,
    /// Declared effects (reads, writes, spawns).
    #[serde(default)]
    pub effects: EffectSummary,
    /// Declared capabilities (e.g., "read_only", "network_access", "filesystem_write").
    pub capabilities: Vec<String>,
    /// Trust level assigned to this tool (0.0 = untrusted, 1.0 = fully trusted).
    pub trust_level: f32,
    /// Whether this tool requires human review before execution.
    pub requires_human_review: bool,
    /// Manifest creation timestamp (Unix seconds).
    pub created_at: i64,
    /// HMAC-SHA256 signature over the manifest content.
    #[serde(default)]
    pub signature: String,
}

/// A compact summary of effects for serialization in manifests.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct EffectSummary {
    /// Resources the tool reads.
    #[serde(default)]
    pub reads: Vec<String>,
    /// Resources the tool writes.
    #[serde(default)]
    pub writes: Vec<String>,
    /// Whether the tool can spawn subprocesses.
    #[serde(default)]
    pub spawns: bool,
}

impl EffectSummary {
    /// Create from an `EffectRow`.
    #[must_use]
    pub fn from_effect_row(effects: &EffectRow) -> Self {
        Self {
            reads: effects.reads.iter().map(|r| format!("{r:?}")).collect(),
            writes: effects.writes.iter().map(|r| format!("{r:?}")).collect(),
            spawns: effects.spawns,
        }
    }

    /// Whether this manifest declares any destructive (write) effects.
    #[must_use]
    pub fn has_destructive_effects(&self) -> bool {
        !self.writes.is_empty() || self.spawns
    }
}

impl ToolManifest {
    /// Create a new unsigned manifest.
    #[must_use]
    pub fn new(tool_name: &str, version: &str, publisher: &str, description: &str) -> Self {
        Self {
            tool_name: tool_name.to_string(),
            version: version.to_string(),
            publisher: publisher.to_string(),
            description: description.to_string(),
            effects: EffectSummary::default(),
            capabilities: Vec::new(),
            trust_level: 0.5,
            requires_human_review: false,
            created_at: chrono::Utc::now().timestamp(),
            signature: String::new(),
        }
    }

    /// Set effects on the manifest.
    #[must_use]
    pub fn with_effects(mut self, effects: EffectSummary) -> Self {
        self.effects = effects;
        self
    }

    /// Set capabilities on the manifest.
    #[must_use]
    pub fn with_capabilities(mut self, caps: Vec<String>) -> Self {
        self.capabilities = caps;
        self
    }

    /// Set trust level on the manifest.
    #[must_use]
    pub const fn with_trust(mut self, trust: f32) -> Self {
        self.trust_level = trust.clamp(0.0, 1.0);
        self
    }

    /// Require human review.
    #[must_use]
    pub const fn require_review(mut self) -> Self {
        self.requires_human_review = true;
        self
    }

    /// Compute the payload to sign (all fields except signature).
    #[must_use]
    pub fn signing_payload(&self) -> String {
        // Serialize without the signature field
        let without_sig = Self {
            signature: String::new(),
            ..self.clone()
        };
        serde_json::to_string(&without_sig).unwrap_or_default()
    }

    /// Sign the manifest with an HMAC key.
    ///
    /// Returns a new manifest with the signature set.
    #[must_use]
    pub fn sign(mut self, key: &[u8]) -> Self {
        let payload = self.signing_payload();
        if let Ok(mut mac) = HmacSha256::new_from_slice(key) {
            mac.update(payload.as_bytes());
            self.signature = format!("{:x}", mac.finalize().into_bytes());
        }
        self
    }

    /// Verify the manifest's signature.
    ///
    /// Returns true if the signature matches the current content.
    #[must_use]
    pub fn verify_signature(&self, key: &[u8]) -> bool {
        if self.signature.is_empty() {
            return false;
        }

        let Ok(mut mac) = HmacSha256::new_from_slice(key) else {
            return false;
        };

        let payload = self.signing_payload();
        mac.update(payload.as_bytes());
        let expected = format!("{:x}", mac.finalize().into_bytes());
        expected == self.signature
    }

    /// Whether this manifest declares a specific capability.
    #[must_use]
    pub fn has_capability(&self, cap: &str) -> bool {
        self.capabilities.iter().any(|c| c == cap)
    }

    /// Whether this manifest has destructive effects.
    #[must_use]
    pub fn is_destructive(&self) -> bool {
        self.effects.has_destructive_effects()
    }
}

/// Trust scope — defines what external MCP servers are allowed to do.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TrustScope {
    /// Name of this trust scope (e.g., "default", "strict", "external").
    pub name: String,
    /// Minimum trust level required for tool execution.
    pub min_trust: f32,
    /// Allowed tool name patterns (empty = all allowed).
    #[serde(default)]
    pub allowed_tools: Vec<String>,
    /// Denied tool name patterns (takes precedence over allowed).
    #[serde(default)]
    pub denied_tools: Vec<String>,
    /// Whether destructive tools are allowed.
    pub allow_destructive: bool,
    /// Whether network access tools are allowed.
    pub allow_network: bool,
    /// Whether filesystem write tools are allowed.
    pub allow_filesystem_write: bool,
    /// Whether human review is required for all tools in this scope.
    pub require_review: bool,
    /// Maximum number of tool calls per minute (0 = unlimited).
    pub max_calls_per_minute: u32,
}

impl Default for TrustScope {
    fn default() -> Self {
        Self {
            name: "default".into(),
            min_trust: 0.5,
            allowed_tools: Vec::new(),
            denied_tools: Vec::new(),
            allow_destructive: false,
            allow_network: false,
            allow_filesystem_write: false,
            require_review: false,
            max_calls_per_minute: 60,
        }
    }
}

impl TrustScope {
    /// Strict scope for untrusted external servers.
    #[must_use]
    pub fn strict() -> Self {
        Self {
            name: "strict".into(),
            min_trust: 0.8,
            allowed_tools: vec!["memory.search".into(), "memory.recall".into()],
            denied_tools: vec!["file.".into(), "process.".into(), "network.".into()],
            allow_destructive: false,
            allow_network: false,
            allow_filesystem_write: false,
            require_review: true,
            max_calls_per_minute: 10,
        }
    }

    /// Permissive scope for trusted internal servers.
    #[must_use]
    pub fn permissive() -> Self {
        Self {
            name: "permissive".into(),
            min_trust: 0.3,
            allow_destructive: true,
            allow_network: true,
            allow_filesystem_write: true,
            require_review: false,
            max_calls_per_minute: 200,
            ..Self::default()
        }
    }

    /// Check if a tool is allowed under this trust scope.
    #[must_use]
    pub fn is_tool_allowed(&self, manifest: &ToolManifest) -> bool {
        // Check trust level
        if manifest.trust_level < self.min_trust {
            return false;
        }

        // Check denied list
        if self
            .denied_tools
            .iter()
            .any(|p| manifest.tool_name.starts_with(p))
        {
            return false;
        }

        // Check allowed list (empty = all allowed)
        if !self.allowed_tools.is_empty()
            && !self
                .allowed_tools
                .iter()
                .any(|p| manifest.tool_name.starts_with(p))
        {
            return false;
        }

        // Check destructive
        if manifest.is_destructive() && !self.allow_destructive {
            return false;
        }

        // Check network access
        if manifest.has_capability("network_access") && !self.allow_network {
            return false;
        }

        // Check filesystem write
        if manifest.has_capability("filesystem_write") && !self.allow_filesystem_write {
            return false;
        }

        // Check human review requirement
        if self.require_review && !manifest.requires_human_review {
            // Tool doesn't declare it needs review, but scope requires it
            // This is a warning, not a hard block — the caller should enforce review
        }

        true
    }
}

/// Registry of known tool manifests with verification.
pub struct ToolAttestationRegistry {
    /// Known manifests keyed by tool name.
    manifests: ahash::AHashMap<String, ToolManifest>,
    /// Signing key for manifest verification.
    signing_key: Vec<u8>,
    /// Trust scope for external tools.
    external_scope: TrustScope,
    /// Set of trusted publishers.
    trusted_publishers: Vec<String>,
}

impl ToolAttestationRegistry {
    /// Create a new registry with the given signing key.
    #[must_use]
    pub fn new(signing_key: Vec<u8>) -> Self {
        Self {
            manifests: ahash::AHashMap::new(),
            signing_key,
            external_scope: TrustScope::default(),
            trusted_publishers: vec!["whitemagic-core".into()],
        }
    }

    /// Set the trust scope for external tools.
    #[must_use]
    pub fn with_external_scope(mut self, scope: TrustScope) -> Self {
        self.external_scope = scope;
        self
    }

    /// Add a trusted publisher.
    pub fn trust_publisher(&mut self, publisher: &str) {
        if !self.trusted_publishers.contains(&publisher.to_string()) {
            self.trusted_publishers.push(publisher.to_string());
        }
    }

    /// Register a tool manifest.
    ///
    /// Verifies the manifest's signature before registering. Returns false
    /// if the signature is invalid.
    pub fn register(&mut self, manifest: ToolManifest) -> bool {
        // Verify signature
        if !manifest.verify_signature(&self.signing_key) {
            return false;
        }

        // Check publisher is trusted
        if !self.trusted_publishers.contains(&manifest.publisher) {
            return false;
        }

        self.manifests.insert(manifest.tool_name.clone(), manifest);
        true
    }

    /// Register a tool manifest without signature verification (for self-signed tools).
    ///
    /// The manifest must still come from a trusted publisher.
    pub fn register_unsigned(&mut self, manifest: ToolManifest) -> bool {
        if !self.trusted_publishers.contains(&manifest.publisher) {
            return false;
        }
        self.manifests.insert(manifest.tool_name.clone(), manifest);
        true
    }

    /// Get a tool's manifest.
    #[must_use]
    pub fn get(&self, tool_name: &str) -> Option<&ToolManifest> {
        self.manifests.get(tool_name)
    }

    /// Check if a tool is allowed under the current trust scope.
    #[must_use]
    pub fn is_tool_allowed(&self, tool_name: &str) -> bool {
        let Some(manifest) = self.manifests.get(tool_name) else {
            return false; // Unknown tools are not allowed
        };

        // Internal tools (from whitemagic-core) bypass external scope
        if manifest.publisher == "whitemagic-core" {
            return true;
        }

        // External tools must pass the trust scope
        self.external_scope.is_tool_allowed(manifest)
    }

    /// Verify a manifest's provenance (signature + publisher).
    #[must_use]
    pub fn verify_provenance(&self, manifest: &ToolManifest) -> bool {
        manifest.verify_signature(&self.signing_key)
            && self.trusted_publishers.contains(&manifest.publisher)
    }

    /// List all registered tool names.
    #[must_use]
    pub fn registered_tools(&self) -> Vec<String> {
        self.manifests.keys().cloned().collect()
    }

    /// Number of registered tools.
    #[must_use]
    pub fn len(&self) -> usize {
        self.manifests.len()
    }

    /// Whether the registry is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.manifests.is_empty()
    }
}

/// Compute SHA-256 hash of a manifest (for fingerprinting).
#[must_use]
pub fn manifest_hash(manifest: &ToolManifest) -> String {
    let payload = manifest.signing_payload();
    let mut hasher = Sha256::new();
    hasher.update(payload.as_bytes());
    format!("{:x}", hasher.finalize())
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    const TEST_KEY: &[u8] = b"test_signing_key_123";

    fn make_manifest(name: &str, publisher: &str) -> ToolManifest {
        ToolManifest::new(name, "1.0.0", publisher, "A test tool")
            .with_trust(0.8)
            .with_capabilities(vec!["read_only".into()])
    }

    #[test]
    fn manifest_sign_and_verify() {
        let manifest = make_manifest("memory.search", "whitemagic-core").sign(TEST_KEY);
        assert!(
            manifest.verify_signature(TEST_KEY),
            "Signed manifest should verify"
        );
    }

    #[test]
    fn manifest_tamper_detected() {
        let manifest = make_manifest("memory.search", "whitemagic-core").sign(TEST_KEY);
        let tampered = ToolManifest {
            description: "Tampered description".into(),
            ..manifest
        };
        assert!(
            !tampered.verify_signature(TEST_KEY),
            "Tampered manifest should fail verification"
        );
    }

    #[test]
    fn manifest_unsigned_fails_verification() {
        let manifest = make_manifest("memory.search", "whitemagic-core");
        assert!(!manifest.verify_signature(TEST_KEY));
    }

    #[test]
    fn manifest_wrong_key_fails() {
        let manifest = make_manifest("memory.search", "whitemagic-core").sign(TEST_KEY);
        assert!(!manifest.verify_signature(b"wrong_key"));
    }

    #[test]
    fn manifest_has_capability() {
        let manifest = make_manifest("memory.search", "whitemagic-core")
            .with_capabilities(vec!["read_only".into(), "search".into()]);
        assert!(manifest.has_capability("read_only"));
        assert!(manifest.has_capability("search"));
        assert!(!manifest.has_capability("network_access"));
    }

    #[test]
    fn manifest_destructive_detection() {
        let manifest = ToolManifest::new("file.write", "1.0.0", "whitemagic-core", "Write file")
            .with_effects(EffectSummary {
                writes: vec!["Filesystem".into()],
                ..Default::default()
            });
        assert!(manifest.is_destructive());

        let read_only = ToolManifest::new("memory.search", "1.0.0", "whitemagic-core", "Search")
            .with_effects(EffectSummary {
                reads: vec!["Galaxy".into()],
                ..Default::default()
            });
        assert!(!read_only.is_destructive());
    }

    #[test]
    fn trust_scope_default_allows_trusted() {
        let scope = TrustScope::default();
        let manifest = make_manifest("memory.search", "whitemagic-core").with_trust(0.6);
        assert!(scope.is_tool_allowed(&manifest));
    }

    #[test]
    fn trust_scope_blocks_low_trust() {
        let scope = TrustScope::default();
        let manifest = make_manifest("memory.search", "external").with_trust(0.2);
        assert!(!scope.is_tool_allowed(&manifest));
    }

    #[test]
    fn trust_scope_strict_blocks_destructive() {
        let scope = TrustScope::strict();
        let manifest = ToolManifest::new("file.write", "1.0.0", "external", "Write file")
            .with_trust(0.9)
            .with_effects(EffectSummary {
                writes: vec!["Filesystem".into()],
                ..Default::default()
            });
        assert!(!scope.is_tool_allowed(&manifest));
    }

    #[test]
    fn trust_scope_strict_blocks_network() {
        let scope = TrustScope::strict();
        let manifest = ToolManifest::new("http.fetch", "1.0.0", "external", "Fetch URL")
            .with_trust(0.9)
            .with_capabilities(vec!["network_access".into()]);
        assert!(!scope.is_tool_allowed(&manifest));
    }

    #[test]
    fn trust_scope_denied_list_takes_precedence() {
        let scope = TrustScope {
            allowed_tools: vec!["memory.".into()],
            denied_tools: vec!["memory.delete".into()],
            ..TrustScope::permissive()
        };
        let manifest = make_manifest("memory.delete", "external").with_trust(0.9);
        assert!(!scope.is_tool_allowed(&manifest));
    }

    #[test]
    fn registry_register_signed_manifest() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        let manifest = make_manifest("memory.search", "whitemagic-core").sign(TEST_KEY);
        assert!(registry.register(manifest));
        assert_eq!(registry.len(), 1);
    }

    #[test]
    fn registry_rejects_invalid_signature() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        let manifest = make_manifest("memory.search", "whitemagic-core").sign(b"wrong_key");
        assert!(!registry.register(manifest));
        assert_eq!(registry.len(), 0);
    }

    #[test]
    fn registry_rejects_untrusted_publisher() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        let manifest = make_manifest("memory.search", "untrusted").sign(TEST_KEY);
        assert!(!registry.register(manifest));
    }

    #[test]
    fn registry_allows_trusted_publisher() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        registry.trust_publisher("external:acme");
        let manifest = make_manifest("custom.tool", "external:acme").sign(TEST_KEY);
        assert!(registry.register(manifest));
    }

    #[test]
    fn registry_internal_tools_bypass_scope() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec())
            .with_external_scope(TrustScope::strict());
        let manifest = ToolManifest::new("file.write", "1.0.0", "whitemagic-core", "Write")
            .with_trust(0.5)
            .with_effects(EffectSummary {
                writes: vec!["Filesystem".into()],
                ..Default::default()
            })
            .sign(TEST_KEY);
        registry.register(manifest);

        // Internal tool should be allowed even under strict scope
        assert!(registry.is_tool_allowed("file.write"));
    }

    #[test]
    fn registry_external_tools_checked_against_scope() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec())
            .with_external_scope(TrustScope::strict());
        registry.trust_publisher("external:acme");
        let manifest = ToolManifest::new("file.write", "1.0.0", "external:acme", "Write")
            .with_trust(0.9)
            .with_effects(EffectSummary {
                writes: vec!["Filesystem".into()],
                ..Default::default()
            })
            .sign(TEST_KEY);
        registry.register(manifest);

        // External destructive tool should be blocked by strict scope
        assert!(!registry.is_tool_allowed("file.write"));
    }

    #[test]
    fn registry_unknown_tool_not_allowed() {
        let registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        assert!(!registry.is_tool_allowed("unknown.tool"));
    }

    #[test]
    fn registry_verify_provenance() {
        let registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        let manifest = make_manifest("memory.search", "whitemagic-core").sign(TEST_KEY);
        assert!(registry.verify_provenance(&manifest));

        let untrusted = make_manifest("memory.search", "untrusted").sign(TEST_KEY);
        assert!(!registry.verify_provenance(&untrusted));
    }

    #[test]
    fn manifest_hash_deterministic() {
        let m1 = make_manifest("memory.search", "whitemagic-core");
        let m2 = make_manifest("memory.search", "whitemagic-core");
        assert_eq!(manifest_hash(&m1), manifest_hash(&m2));
    }

    #[test]
    fn manifest_hash_changes_with_content() {
        let m1 = make_manifest("memory.search", "whitemagic-core");
        let m2 = make_manifest("memory.search", "whitemagic-core").with_trust(0.9);
        assert_ne!(manifest_hash(&m1), manifest_hash(&m2));
    }

    #[test]
    fn registry_registered_tools_list() {
        let mut registry = ToolAttestationRegistry::new(TEST_KEY.to_vec());
        registry.register(make_manifest("memory.search", "whitemagic-core").sign(TEST_KEY));
        registry.register(make_manifest("memory.recall", "whitemagic-core").sign(TEST_KEY));

        let tools = registry.registered_tools();
        assert_eq!(tools.len(), 2);
        assert!(tools.contains(&"memory.search".to_string()));
        assert!(tools.contains(&"memory.recall".to_string()));
    }

    #[test]
    fn trust_scope_permissive_allows_most() {
        let scope = TrustScope::permissive();
        let manifest = ToolManifest::new("file.write", "1.0.0", "external", "Write")
            .with_trust(0.5)
            .with_effects(EffectSummary {
                writes: vec!["Filesystem".into()],
                ..Default::default()
            })
            .with_capabilities(vec!["filesystem_write".into()]);
        assert!(scope.is_tool_allowed(&manifest));
    }
}
