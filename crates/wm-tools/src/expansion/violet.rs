//! Violet security surface — engagement tokens + model signing tools.
//!
//! PLAN_F F-1/F-2 router surface:
//! - `violet.engagement.issue` / `violet.engagement.validate` / `violet.engagement.revoke`
//! - `model.sign` / `model.verify`
//!
//! The issuer/signer Ed25519 keypairs live in memory for the life of the
//! server process. Tokens and manifests carry their public keys, so
//! verification by peers works without shared secrets; key persistence
//! across restarts is a follow-up.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::{Arc, Mutex, MutexGuard};
use std::time::{SystemTime, UNIX_EPOCH};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_governance::engagement_tokens::{
    EngagementIssuer, EngagementScope, EngagementToken, TokenVerdict, sha256_hex,
    verify_token_with_key,
};
use wm_governance::model_signing::{
    ModelSignature, ModelSigner, sha256_hex_bytes, verify_model_hash,
};

type Issuer = Arc<Mutex<EngagementIssuer>>;
type Signer = Arc<Mutex<ModelSigner>>;

fn lock_issuer(issuer: &Issuer) -> wm_core::Result<MutexGuard<'_, EngagementIssuer>> {
    issuer
        .lock()
        .map_err(|e| CoreError::Internal(format!("engagement issuer lock poisoned: {e}")))
}

fn lock_signer(signer: &Signer) -> wm_core::Result<MutexGuard<'_, ModelSigner>> {
    signer
        .lock()
        .map_err(|e| CoreError::Internal(format!("model signer lock poisoned: {e}")))
}

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

fn parse_roe_hash(args: &Value) -> wm_core::Result<String> {
    if let Some(text) = args.get("rules_of_engagement").and_then(Value::as_str) {
        return Ok(sha256_hex(text));
    }
    if let Some(hash) = args.get("rules_of_engagement_hash").and_then(Value::as_str) {
        return Ok(hash.trim().to_ascii_lowercase());
    }
    Err(CoreError::InvalidArgs(
        "provide rules_of_engagement (text) or rules_of_engagement_hash (hex)".into(),
    ))
}

fn parse_scope(args: &Value) -> EngagementScope {
    match args.get("scope").and_then(Value::as_str) {
        None | Some("poc") => EngagementScope::Poc,
        Some("redteam") => EngagementScope::Redteam,
        Some("demo") => EngagementScope::Demo,
        Some(other) => EngagementScope::Custom(other.to_string()),
    }
}

fn token_verdict_json(verdict: &TokenVerdict) -> Value {
    match verdict {
        TokenVerdict::Valid => json!({"verdict": "valid"}),
        TokenVerdict::BadSignature => json!({"verdict": "bad_signature"}),
        TokenVerdict::Revoked => json!({"verdict": "revoked"}),
        TokenVerdict::Expired => json!({"verdict": "expired"}),
        TokenVerdict::RulesOfEngagementMismatch { expected, actual } => json!({
            "verdict": "roe_mismatch",
            "expected": expected,
            "actual": actual,
        }),
    }
}

// ── violet.engagement.issue ────────────────────────────────────────────

/// `violet.engagement.issue` — issue a signed scope-of-engagement token.
pub struct EngagementIssueTool {
    issuer: Issuer,
    stats: ToolStats,
    effects: EffectRow,
}

impl EngagementIssueTool {
    #[must_use]
    pub fn new(issuer: Issuer) -> Self {
        Self {
            issuer,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for EngagementIssueTool {
    fn name(&self) -> &str {
        "violet.engagement.issue"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Issue an Ed25519 scope-of-engagement token. Args: issued_to (str), scope (poc|redteam|demo|<custom>), rules_of_engagement (text) or rules_of_engagement_hash (hex), ttl_seconds (optional int; omitted = until revoked)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let issued_to = args
            .get("issued_to")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("issued_to is required".into()))?;
        let scope = parse_scope(&args);
        let roe_hash = parse_roe_hash(&args)?;
        let ttl = args.get("ttl_seconds").and_then(Value::as_i64);

        let mut issuer = lock_issuer(&self.issuer)?;
        let token = issuer.issue(issued_to, scope, &roe_hash, ttl);
        let issuer_public_key = issuer.signer_public_key_hex();

        Ok(json!({
            "status": "success",
            "issuer_public_key": issuer_public_key,
            "rules_of_engagement_hash": roe_hash,
            "token": token,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── violet.engagement.validate ─────────────────────────────────────────

/// `violet.engagement.validate` — stateless token verification.
pub struct EngagementValidateTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl EngagementValidateTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

impl Default for EngagementValidateTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for EngagementValidateTool {
    fn name(&self) -> &str {
        "violet.engagement.validate"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Verify an engagement token against an explicit issuer public key. Args: token (object or JSON string), issuer_public_key (hex), rules_of_engagement (text) or rules_of_engagement_hash (hex), now (optional epoch seconds). Note: the issuer's out-of-band revocation set is not visible statelessly — only the token's revoked flag."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let token: EngagementToken = match args.get("token") {
            Some(Value::String(s)) => serde_json::from_str(s)
                .map_err(|e| CoreError::InvalidArgs(format!("token JSON: {e}")))?,
            Some(v) => serde_json::from_value(v.clone())
                .map_err(|e| CoreError::InvalidArgs(format!("token object: {e}")))?,
            None => return Err(CoreError::InvalidArgs("token is required".into())),
        };
        let issuer_public_key = args
            .get("issuer_public_key")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("issuer_public_key is required".into()))?;
        let roe_hash = parse_roe_hash(&args)?;
        let now = args
            .get("now")
            .and_then(Value::as_i64)
            .unwrap_or_else(now_unix);

        let outcome = verify_token_with_key(&token, &roe_hash, issuer_public_key, now);
        match outcome {
            Ok(verdict) => {
                let mut out = token_verdict_json(&verdict);
                out["status"] = json!("success");
                out["token_id"] = json!(token.id);
                Ok(out)
            }
            Err(e) => Ok(json!({
                "status": "success",
                "verdict": "malformed_signature",
                "token_id": token.id,
                "reason": e.to_string(),
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── violet.engagement.revoke ───────────────────────────────────────────

/// `violet.engagement.revoke` — revoke a token issued by this server.
pub struct EngagementRevokeTool {
    issuer: Issuer,
    stats: ToolStats,
    effects: EffectRow,
}

impl EngagementRevokeTool {
    #[must_use]
    pub fn new(issuer: Issuer) -> Self {
        Self {
            issuer,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for EngagementRevokeTool {
    fn name(&self) -> &str {
        "violet.engagement.revoke"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Revoke an engagement token issued by this server. Args: id (evt_...)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("id is required".into()))?;
        let mut issuer = lock_issuer(&self.issuer)?;
        issuer
            .revoke(id)
            .map_err(|e| CoreError::InvalidArgs(e.to_string()))?;
        Ok(json!({"status": "success", "revoked": id}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── model.sign ─────────────────────────────────────────────────────────

/// `model.sign` — Ed25519-sign an artifact hash (or content).
pub struct ModelSignTool {
    signer: Signer,
    stats: ToolStats,
    effects: EffectRow,
}

impl ModelSignTool {
    #[must_use]
    pub fn new(signer: Signer) -> Self {
        Self {
            signer,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for ModelSignTool {
    fn name(&self) -> &str {
        "model.sign"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Ed25519-sign an artifact manifest. Args: artifact_id (str), content (str; hashed) or content_hash (sha256 hex), nonce (optional), rules_of_engagement_hash (optional; binding is re-signed)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let artifact_id = args
            .get("artifact_id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("artifact_id is required".into()))?;
        let content_hash = match (
            args.get("content").and_then(Value::as_str),
            args.get("content_hash").and_then(Value::as_str),
        ) {
            (Some(content), _) => sha256_hex_bytes(content.as_bytes()),
            (None, Some(hash)) => hash.trim().to_ascii_lowercase(),
            (None, None) => {
                return Err(CoreError::InvalidArgs(
                    "provide content (str) or content_hash (sha256 hex)".into(),
                ));
            }
        };
        let nonce = args.get("nonce").and_then(Value::as_str);
        let roe_hash = args
            .get("rules_of_engagement_hash")
            .and_then(Value::as_str)
            .map(|h| h.trim().to_ascii_lowercase());

        let signer = lock_signer(&self.signer)?;
        let manifest = signer.sign_hash(artifact_id, &content_hash);
        let manifest = match (&nonce, &roe_hash) {
            (Some(nonce), Some(roe)) => signer.bind_engagement(manifest, nonce, roe),
            (Some(nonce), None) => signer.bind_engagement(manifest, nonce, ""),
            (None, Some(roe)) => signer.bind_engagement(manifest, "", roe),
            (None, None) => manifest,
        };
        let signer_public_key = signer.signer_public_key_hex();

        Ok(json!({
            "status": "success",
            "signer_public_key": signer_public_key,
            "signature": manifest,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── model.verify ───────────────────────────────────────────────────────

/// `model.verify` — verify a signed artifact manifest.
pub struct ModelVerifyTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl ModelVerifyTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

impl Default for ModelVerifyTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for ModelVerifyTool {
    fn name(&self) -> &str {
        "model.verify"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Verify a signed model/artifact manifest. Args: signature (manifest object), content (str; hashed) or content_hash (sha256 hex)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let manifest: ModelSignature = match args.get("signature") {
            Some(Value::String(s)) => serde_json::from_str(s)
                .map_err(|e| CoreError::InvalidArgs(format!("signature JSON: {e}")))?,
            Some(v) => serde_json::from_value(v.clone())
                .map_err(|e| CoreError::InvalidArgs(format!("signature object: {e}")))?,
            None => return Err(CoreError::InvalidArgs("signature is required".into())),
        };
        let content_hash = match (
            args.get("content").and_then(Value::as_str),
            args.get("content_hash").and_then(Value::as_str),
        ) {
            (Some(content), _) => sha256_hex_bytes(content.as_bytes()),
            (None, Some(hash)) => hash.trim().to_ascii_lowercase(),
            (None, None) => {
                return Err(CoreError::InvalidArgs(
                    "provide content (str) or content_hash (sha256 hex)".into(),
                ));
            }
        };

        let verdict = verify_model_hash(&content_hash, &manifest);
        let out = match verdict {
            wm_governance::model_signing::ModelVerdict::Valid => {
                json!({"status": "success", "verdict": "valid"})
            }
            wm_governance::model_signing::ModelVerdict::BadSignature => {
                json!({"status": "success", "verdict": "bad_signature"})
            }
            wm_governance::model_signing::ModelVerdict::HashMismatch { expected, actual } => {
                json!({
                    "status": "success",
                    "verdict": "hash_mismatch",
                    "expected": expected,
                    "actual": actual,
                })
            }
        };
        Ok(out)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the Violet security tool surface (5 tools).
#[must_use]
pub fn register_violet(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    let issuer: Issuer = Arc::new(Mutex::new(EngagementIssuer::new()));
    let signer: Signer = Arc::new(Mutex::new(ModelSigner::new()));
    registry
        .register(Arc::new(EngagementIssueTool::new(issuer.clone())))
        .register(Arc::new(EngagementValidateTool::new()))
        .register(Arc::new(EngagementRevokeTool::new(issuer)))
        .register(Arc::new(ModelSignTool::new(signer)))
        .register(Arc::new(ModelVerifyTool::new()))
}
