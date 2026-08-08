//! Bicameral reasoning tools — uses wm-bicameral engine for dual-hemisphere debate.
//!
//! Gana::ThreeStars — "Bicameral reasoning, dual-hemisphere debate"
//!
//! Tools:
//! - `bicameral.reason` — Run bicameral reasoning on a topic with evidence
//! - `bicameral.status` — Show engine configuration and hemisphere availability

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::{Arc, Mutex};
use wm_bicameral::{
    BicameralEngine, DenseEncoder, HemisphereInput, MetaHarness, SpeculativeDecoder,
};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::common::parse_galaxy;

// ── bicameral.reason ──────────────────────────────────────────────────

/// Bicameral reasoning tool — dual-hemisphere debate on a topic.
///
/// Gathers evidence from memories, then runs the bicameral engine
/// (left + right hemisphere) to produce a consensus conclusion.
pub struct BicameralReasonTool {
    store: Arc<MemoryStore>,
    engine: Arc<Mutex<BicameralEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BicameralReasonTool {
    /// Create a new bicameral reasoning tool.
    pub fn new(store: Arc<MemoryStore>, engine: Arc<Mutex<BicameralEngine>>) -> Self {
        Self {
            store,
            engine,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for BicameralReasonTool {
    fn name(&self) -> &str {
        "bicameral.reason"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Dual-hemisphere bicameral reasoning: left (deterministic) + right (heuristic) debate with consensus gate"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let topic = args
            .get("topic")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("topic (string) required".into()))?;

        let galaxy_str = args.get("galaxy").and_then(Value::as_str);
        let scan_limit = args
            .get("scan_limit")
            .and_then(Value::as_u64)
            .unwrap_or(500) as usize;

        // Gather evidence from memories
        let galaxies: Vec<wm_core::Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => wm_core::Galaxy::memory_galaxies().to_vec(),
        };

        let topic_lower = topic.to_lowercase();
        let topic_words: Vec<&str> = topic_lower.split_whitespace().collect();

        let mut evidence: Vec<String> = Vec::new();
        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, scan_limit)?;
            for mem in mems {
                let content_lower = mem.content.to_lowercase();
                if topic_words.iter().any(|tw| content_lower.contains(tw)) {
                    evidence.push(mem.content.chars().take(200).collect());
                }
            }
        }

        let input = HemisphereInput::new(topic).with_evidence(evidence);

        let result = {
            let engine = self.engine.lock().map_err(|e| {
                wm_core::CoreError::Tool(format!("bicameral engine lock error: {e}"))
            })?;
            engine.reason(&input)
        };

        let messages_json: Vec<Value> = result
            .messages
            .iter()
            .map(|m| {
                json!({
                    "direction": format!("{:?}", m.direction),
                    "kind": format!("{:?}", m.kind),
                    "payload": m.payload,
                    "round": m.round,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "topic": topic,
            "verdict": format!("{:?}", result.verdict),
            "conclusion": result.conclusion,
            "confidence": result.confidence,
            "rounds": result.rounds,
            "left_hemisphere": {
                "conclusion": result.left_output.conclusion,
                "confidence": result.left_output.confidence,
                "stance": format!("{:?}", result.left_output.stance),
                "key_points": result.left_output.key_points,
            },
            "right_hemisphere": match result.right_output.as_ref() {
                Some(ro) => json!({
                    "conclusion": ro.conclusion,
                    "confidence": ro.confidence,
                    "stance": format!("{:?}", ro.stance),
                    "key_points": ro.key_points,
                }),
                None => Value::Null,
            },
            "messages": messages_json,
            "evidence_count": input.evidence.len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── bicameral.status ──────────────────────────────────────────────────

/// Show bicameral engine configuration and hemisphere availability.
pub struct BicameralStatusTool {
    engine: Arc<Mutex<BicameralEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BicameralStatusTool {
    /// Create a new bicameral status tool.
    pub fn new(engine: Arc<Mutex<BicameralEngine>>) -> Self {
        Self {
            engine,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for BicameralStatusTool {
    fn name(&self) -> &str {
        "bicameral.status"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Show bicameral engine configuration and hemisphere availability"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let (config, has_right, left_name) = {
            let engine = self.engine.lock().map_err(|e| {
                wm_core::CoreError::Tool(format!("bicameral engine lock error: {e}"))
            })?;
            (
                engine.config().clone(),
                engine.has_right_hemisphere(),
                engine.left_hemisphere_name(),
            )
        };

        Ok(json!({
            "status": "success",
            "config": {
                "max_rounds": config.max_rounds,
                "timeout_ms": config.timeout.as_millis(),
                "callosum_bandwidth": config.callosum_bandwidth,
                "right_enabled": config.right_enabled,
            },
            "left_hemisphere": left_name,
            "right_hemisphere": if has_right { "available" } else { "unavailable" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register bicameral tools into a registry.
///
/// `speculative` is the optional N4 speculative decoder. When provided,
/// `speculative.decode` and `speculative.stats` tools are registered.
/// `harness` is the optional N6 meta-harness. When provided,
/// `meta.enhance` and `meta.stats` tools are registered.
/// `encoder` is the optional N7 dense encoder. When provided,
/// `dense.encode` and `dense.decode` tools are registered.
pub fn register_bicameral(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    engine: Arc<Mutex<BicameralEngine>>,
    speculative: Option<Arc<SpeculativeDecoder>>,
    harness: Option<Arc<MetaHarness>>,
    encoder: Option<Arc<DenseEncoder>>,
) -> wm_dispatch::ToolRegistry {
    let mut reg = registry
        .register(Arc::new(BicameralReasonTool::new(
            store.clone(),
            engine.clone(),
        )))
        .register(Arc::new(BicameralStatusTool::new(engine)));

    if let Some(decoder) = speculative {
        reg = reg
            .register(Arc::new(SpeculativeDecodeTool::new(decoder.clone())))
            .register(Arc::new(SpeculativeStatsTool::new(decoder)));
    }

    if let Some(h) = harness {
        reg = reg
            .register(Arc::new(MetaEnhanceTool::new(h.clone())))
            .register(Arc::new(MetaStatsTool::new(h)));
    }

    if let Some(enc) = encoder {
        reg = reg
            .register(Arc::new(DenseEncodeTool::new(enc.clone())))
            .register(Arc::new(DenseDecodeTool::new(enc)));
    }

    reg
}

// ── speculative.decode ───────────────────────────────────────────────

/// Speculative decoding tool — accelerated inference using draft + verify.
///
/// Runs a prompt through the speculative decoder, which uses a small draft
/// model to generate a candidate response, then a larger verify model to
/// check or regenerate it. Can provide 1.5-2.1x speedup over verify-only.
pub struct SpeculativeDecodeTool {
    decoder: Arc<SpeculativeDecoder>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SpeculativeDecodeTool {
    /// Create a new speculative decode tool.
    pub fn new(decoder: Arc<SpeculativeDecoder>) -> Self {
        Self {
            decoder,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SpeculativeDecodeTool {
    fn name(&self) -> &str {
        "speculative.decode"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Speculative decoding: draft model generates, verify model checks. 1.5-2.1x speedup for local LLM inference"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let prompt = args
            .get("prompt")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("prompt (string) required".into()))?;

        let max_tokens = args
            .get("max_tokens")
            .and_then(Value::as_u64)
            .unwrap_or(256) as usize;

        let result = self.decoder.generate(prompt, max_tokens);

        Ok(json!({
            "status": "success",
            "output": result.output,
            "confidence": result.confidence,
            "method": result.method,
            "draft_accepted": result.draft_accepted,
            "verified": result.verified,
            "draft_latency_ms": result.draft_latency_ms,
            "verify_latency_ms": result.verify_latency_ms,
            "total_latency_ms": result.total_latency_ms,
            "token_count": result.token_count,
            "draft_tokens_accepted": result.draft_tokens_accepted,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── speculative.stats ─────────────────────────────────────────────────

/// Show speculative decoder statistics.
pub struct SpeculativeStatsTool {
    decoder: Arc<SpeculativeDecoder>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SpeculativeStatsTool {
    /// Create a new speculative stats tool.
    pub fn new(decoder: Arc<SpeculativeDecoder>) -> Self {
        Self {
            decoder,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SpeculativeStatsTool {
    fn name(&self) -> &str {
        "speculative.stats"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Show speculative decoder statistics: acceptance rate, latency, estimated speedup"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let stats = self.decoder.stats();
        let config = self.decoder.config();

        Ok(json!({
            "status": "success",
            "enabled": config.enabled,
            "draft_k": config.draft_k,
            "draft_handler": self.decoder.draft_name(),
            "verify_handler": self.decoder.verify_name(),
            "total_calls": stats.total_calls,
            "draft_accepted": stats.draft_accepted,
            "verify_accepted": stats.verify_accepted,
            "draft_rejected": stats.draft_rejected,
            "acceptance_rate": stats.acceptance_rate(),
            "draft_only_rate": stats.draft_only_rate(),
            "avg_draft_latency_ms": stats.avg_draft_latency_ms(),
            "avg_verify_latency_ms": stats.avg_verify_latency_ms(),
            "token_acceptance_rate": stats.token_acceptance_rate(),
            "estimated_speedup": stats.estimated_speedup(config.draft_k),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── meta.enhance ──────────────────────────────────────────────────────

/// Meta-harness enhance tool — wraps inference with cognitive enhancement.
///
/// Applies enhancement strategies (memory grounding, self-correction,
/// ensemble voting) to improve LLM output quality.
pub struct MetaEnhanceTool {
    harness: Arc<MetaHarness>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MetaEnhanceTool {
    /// Create a new meta-enhance tool.
    pub fn new(harness: Arc<MetaHarness>) -> Self {
        Self {
            harness,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![wm_core::Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MetaEnhanceTool {
    fn name(&self) -> &str {
        "meta.enhance"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Enhance a prompt with cognitive strategies (memory grounding, self-correction, ensemble voting)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let prompt = args
            .get("prompt")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::Tool("missing 'prompt' argument".into()))?;

        let max_tokens = args
            .get("max_tokens")
            .and_then(Value::as_u64)
            .map_or(512, |v| v as usize);

        let mode_str = args.get("mode").and_then(Value::as_str).unwrap_or("");

        let mode = match mode_str {
            "direct" => wm_bicameral::EnhancementMode::Direct,
            "memory_grounded" => wm_bicameral::EnhancementMode::MemoryGrounded,
            "self_correcting" => wm_bicameral::EnhancementMode::SelfCorrecting,
            "ensemble" => wm_bicameral::EnhancementMode::Ensemble,
            "full_stack" => wm_bicameral::EnhancementMode::FullStack,
            _ => self.harness.config().default_mode,
        };

        let resp = self.harness.enhance_with_mode(prompt, max_tokens, mode);

        Ok(json!({
            "output": resp.output,
            "confidence": resp.confidence,
            "mode": resp.mode.label(),
            "grounded_memories": resp.grounded_memories,
            "correction_rounds": resp.correction_rounds,
            "ensemble_attempts": resp.ensemble_attempts,
            "validated": resp.validated,
            "latency_us": resp.latency_us,
            "improvement_score": resp.improvement_score,
            "steps": resp.steps.iter().map(|s| json!({
                "name": s.name,
                "latency_us": s.latency_us,
                "modified": s.modified,
                "detail": s.detail,
            })).collect::<Vec<_>>(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── meta.stats ────────────────────────────────────────────────────────

/// Meta-harness stats tool — shows enhancement statistics by mode.
pub struct MetaStatsTool {
    harness: Arc<MetaHarness>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MetaStatsTool {
    /// Create a new meta-stats tool.
    pub fn new(harness: Arc<MetaHarness>) -> Self {
        Self {
            harness,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MetaStatsTool {
    fn name(&self) -> &str {
        "meta.stats"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Show meta-harness enhancement statistics (calls, latency, improvement by mode)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let stats = self.harness.stats();

        let modes = [
            wm_bicameral::EnhancementMode::Direct,
            wm_bicameral::EnhancementMode::MemoryGrounded,
            wm_bicameral::EnhancementMode::SelfCorrecting,
            wm_bicameral::EnhancementMode::Ensemble,
            wm_bicameral::EnhancementMode::FullStack,
        ];

        let by_mode: Vec<Value> = modes
            .iter()
            .filter_map(|&m| {
                stats.mode(m).map(|ms| {
                    json!({
                        "mode": m.label(),
                        "calls": ms.calls,
                        "avg_latency_us": ms.avg_latency_us(),
                        "avg_improvement": ms.avg_improvement(),
                        "grounded_count": ms.grounded_count,
                        "corrected_count": ms.corrected_count,
                        "ensemble_count": ms.ensemble_count,
                    })
                })
            })
            .collect();

        Ok(json!({
            "total_calls": stats.total_calls,
            "avg_latency_us": stats.avg_latency_us(),
            "validation_failures": stats.validation_failures,
            "by_mode": by_mode,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── dense.encode ──────────────────────────────────────────────────────

/// Dense encoding tool — compresses text using CJK character mapping.
///
/// Replaces common English words with single CJK characters to reduce
/// token count for internal LLM context (2-3x compression).
pub struct DenseEncodeTool {
    encoder: Arc<DenseEncoder>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DenseEncodeTool {
    /// Create a new dense-encode tool.
    #[must_use]
    pub fn new(encoder: Arc<DenseEncoder>) -> Self {
        Self {
            encoder,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for DenseEncodeTool {
    fn name(&self) -> &str {
        "dense.encode"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Compress text using CJK character mapping for token-efficient internal context"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let text = args
            .get("text")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::Tool("missing 'text' argument".into()))?;

        let encoded = self.encoder.encode(text);
        let ratio = self.encoder.compression_ratio(text);

        Ok(json!({
            "encoded": encoded,
            "original_length": text.len(),
            "encoded_length": encoded.len(),
            "compression_ratio": ratio,
            "phrase_count": self.encoder.phrase_count(),
            "enabled": self.encoder.is_enabled(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── dense.decode ──────────────────────────────────────────────────────

/// Dense decoding tool — restores compressed text to approximate original.
pub struct DenseDecodeTool {
    encoder: Arc<DenseEncoder>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DenseDecodeTool {
    /// Create a new dense-decode tool.
    #[must_use]
    pub fn new(encoder: Arc<DenseEncoder>) -> Self {
        Self {
            encoder,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for DenseDecodeTool {
    fn name(&self) -> &str {
        "dense.decode"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Decode CJK-compressed text back to approximate English original"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let text = args
            .get("text")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::Tool("missing 'text' argument".into()))?;

        let decoded = self.encoder.decode(text);

        Ok(json!({
            "decoded": decoded,
            "input_length": text.len(),
            "decoded_length": decoded.len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_bicameral::{BicameralConfig, RightHemisphereStub};

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    fn seed_memories(store: &Arc<MemoryStore>) {
        let entries = [
            (
                wm_core::Galaxy::Codex,
                "Rust is great for systems programming",
            ),
            (
                wm_core::Galaxy::Codex,
                "However Rust has a steep learning curve",
            ),
            (
                wm_core::Galaxy::Research,
                "Rust ownership prevents memory leaks",
            ),
            (
                wm_core::Galaxy::Tutorial,
                "Rust is excellent for safe concurrency",
            ),
        ];
        for (galaxy, content) in entries {
            let mem = wm_memory::Memory::new(galaxy, content.into());
            store.put(galaxy, &mem).unwrap();
        }
    }

    fn make_engine() -> Arc<Mutex<BicameralEngine>> {
        let right = Arc::new(RightHemisphereStub::new()) as Arc<dyn wm_bicameral::RightHemisphere>;
        Arc::new(Mutex::new(BicameralEngine::new(
            BicameralConfig::default(),
            Some(right),
        )))
    }

    #[tokio::test]
    async fn bicameral_reason_with_evidence() {
        let (_tmp, store) = open_store();
        seed_memories(&store);
        let engine = make_engine();
        let tool = BicameralReasonTool::new(store, engine);

        let result = tool
            .call(&mut Context::default(), json!({"topic": "rust"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["evidence_count"].as_u64().unwrap() > 0);
        assert!(!obj["conclusion"].as_str().unwrap().is_empty());
        assert!(obj["left_hemisphere"].is_object());
        assert!(obj["right_hemisphere"].is_object());
    }

    #[tokio::test]
    async fn bicameral_reason_no_evidence() {
        let (_tmp, store) = open_store();
        let engine = make_engine();
        let tool = BicameralReasonTool::new(store, engine);

        let result = tool
            .call(&mut Context::default(), json!({"topic": "nonexistent"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["evidence_count"], 0);
        assert!(!obj["conclusion"].as_str().unwrap().is_empty());
    }

    #[tokio::test]
    async fn bicameral_reason_missing_topic() {
        let (_tmp, store) = open_store();
        let engine = make_engine();
        let tool = BicameralReasonTool::new(store, engine);

        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn bicameral_status_shows_config() {
        let engine = make_engine();
        let tool = BicameralStatusTool::new(engine);

        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["left_hemisphere"], "left");
        assert_eq!(obj["right_hemisphere"], "available");
        assert!(obj["config"]["max_rounds"].as_u64().unwrap() > 0);
    }

    #[tokio::test]
    async fn bicameral_status_left_only() {
        let engine = Arc::new(Mutex::new(BicameralEngine::left_only(
            BicameralConfig::default(),
        )));
        let tool = BicameralStatusTool::new(engine);

        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["right_hemisphere"], "unavailable");
    }
}
