//! Cyberbrain wiring — connects the bicameral reasoning stack to the MCP server.
//!
//! This module instantiates and wires together the advanced AI components:
//! - `TriModelManager` — tri-model lifecycle (autonomic/left/right)
//! - `SpeculativeDecoder` — draft+verify speculative decoding
//! - `MetaHarness` — multi-step enhancement (self-critique, debate, best-of-N)
//! - `DenseEncoder` — CJK-based context compression
//! - `EdgeRuleHandler` — Tier 0 rule-based inference (zero tokens)
//! - `MemoryProvider` adapter — grounds meta-harness in Tantivy search
//!
//! All components are env-gated and gracefully degrade to stubs when endpoints
//! are not configured.

use std::sync::Arc;

use wm_bicameral::{
    DenseEncoder, DenseEncodingConfig, EdgeRuleHandler, MemoryProvider, MetaHarness, NoMemory,
    SpeculativeConfig, SpeculativeDecoder, SpeculativeHandler, TierHandler, TierHandlerInference,
    TierHandlerRegistry, TriModelConfig, TriModelHandler, TriModelManager,
};
use wm_memory::SearchEngine;

/// Adapter that wraps `SearchEngine` as a `MemoryProvider` for the meta-harness.
///
/// This grounds the meta-harness's memory RAG step in Tantivy full-text search.
pub struct SearchMemoryProvider {
    search: Arc<SearchEngine>,
}

impl SearchMemoryProvider {
    pub const fn new(search: Arc<SearchEngine>) -> Self {
        Self { search }
    }
}

impl MemoryProvider for SearchMemoryProvider {
    fn search(&self, query: &str, limit: usize) -> Vec<(String, String)> {
        match self.search.search(query, limit) {
            Ok(results) => results
                .into_iter()
                .map(|r| (r.memory_id, r.content))
                .collect(),
            Err(e) => {
                tracing::warn!("meta-harness memory search failed: {e}");
                Vec::new()
            }
        }
    }
}

/// Bundle of wired cyberbrain components.
///
/// Created by `wire_cyberbrain()` and passed to `register_bicameral()`.
pub struct CyberbrainComponents {
    pub speculative: Option<Arc<SpeculativeDecoder>>,
    pub harness: Option<Arc<MetaHarness>>,
    pub encoder: Option<Arc<DenseEncoder>>,
    pub tri_model: Option<Arc<TriModelManager>>,
    pub tier_registry: Option<Arc<TierHandlerRegistry>>,
}

/// Wire all cyberbrain components from environment configuration.
///
/// This instantiates the tri-model manager, speculative decoder, meta-harness,
/// and dense encoder based on environment variables. Components that are not
/// configured (missing env vars) are returned as `None`.
#[allow(clippy::too_many_lines)]
pub fn wire_cyberbrain(search: &Option<Arc<SearchEngine>>) -> CyberbrainComponents {
    // 1. TriModelManager — manages autonomic/left/right model lifecycle
    let tri_config = TriModelConfig::from_env();
    let has_tri_model = tri_config.left_endpoint.is_some()
        || tri_config.right_endpoint.is_some()
        || tri_config.autonomic_bin.is_some();

    let tri_manager = if has_tri_model {
        let manager = Arc::new(TriModelManager::new(tri_config));
        tracing::info!("TriModelManager configured");
        Some(manager)
    } else {
        None
    };

    // 2. Edge rule handler — Tier 0 (always available, zero-token inference)
    let edge_handler = Arc::new(EdgeRuleHandler::new());

    // 3. Speculative decoder — needs draft + verify handlers
    //
    // Draft = autonomic (BitMamba via tri-model) or edge rules
    // Verify = left/right (llama.cpp via tri-model) or edge rules
    let speculative = if let Some(ref tm) = tri_manager {
        let draft = Arc::new(TriModelHandler::production(
            Arc::clone(tm),
            wm_bicameral::InferenceTier::LocalSmall,
        )) as Arc<dyn TierHandler>;
        let verify = Arc::new(TriModelHandler::production(
            Arc::clone(tm),
            wm_bicameral::InferenceTier::LocalLarge,
        )) as Arc<dyn TierHandler>;
        let decoder = Arc::new(SpeculativeDecoder::from_env(draft, verify));
        tracing::info!("SpeculativeDecoder configured (tri-model draft+verify)");
        Some(decoder)
    } else {
        // Without tri-model, use edge rules as draft and a speculative handler
        // that wraps edge rules for both draft and verify (degraded mode)
        let draft = edge_handler.clone() as Arc<dyn TierHandler>;
        let verify = edge_handler as Arc<dyn TierHandler>;
        let config = SpeculativeConfig::from_env();
        if config.enabled {
            let decoder = Arc::new(SpeculativeDecoder::new(draft, verify, config));
            tracing::info!("SpeculativeDecoder configured (edge-rules fallback)");
            Some(decoder)
        } else {
            None
        }
    };

    // 4. Meta-harness — wraps inference with cognitive enhancement
    //
    // InferenceProvider = TierHandlerInference wrapping the verify handler
    // MemoryProvider = SearchMemoryProvider wrapping Tantivy (if available)
    // CritiqueProvider = HeuristicCritique (default)
    let harness = if let Some(ref spec) = speculative {
        let inference_handler =
            Arc::new(SpeculativeHandler::new(Arc::clone(spec))) as Arc<dyn TierHandler>;
        let inference = Arc::new(TierHandlerInference::new(inference_handler));

        let memory: Arc<dyn MemoryProvider> = if let Some(s) = search {
            Arc::new(SearchMemoryProvider::new(Arc::clone(s)))
        } else {
            Arc::new(NoMemory)
        };

        let h = Arc::new(MetaHarness::with_defaults(inference, memory));
        tracing::info!("MetaHarness configured (speculative+memory grounded)");
        Some(h)
    } else if let Some(ref tm) = tri_manager {
        // No speculative, but tri-model is available — use tri-model handler directly
        let handler = Arc::new(TriModelHandler::production(
            Arc::clone(tm),
            wm_bicameral::InferenceTier::LocalLarge,
        )) as Arc<dyn TierHandler>;
        let inference = Arc::new(TierHandlerInference::new(handler));

        let memory: Arc<dyn MemoryProvider> = if let Some(s) = search {
            Arc::new(SearchMemoryProvider::new(Arc::clone(s)))
        } else {
            Arc::new(NoMemory)
        };

        let h = Arc::new(MetaHarness::with_defaults(inference, memory));
        tracing::info!("MetaHarness configured (tri-model+memory grounded)");
        Some(h)
    } else {
        None
    };

    // 5. Dense encoder — CJK-based context compression
    let dense_config = DenseEncodingConfig::from_env();
    let encoder = if dense_config.enabled {
        let enc = Arc::new(DenseEncoder::new(dense_config));
        tracing::info!("DenseEncoder configured (CJK compression)");
        Some(enc)
    } else {
        None
    };

    // 6. Tier handler registry — maps inference tiers to handlers
    //
    // EdgeRules → EdgeRuleHandler (zero-token, always available)
    // LocalLlamaCpp → TriModelHandler (autonomic/draft)
    // LocalSmall → TriModelHandler (left/verify)
    // LocalLarge → TriModelHandler (right/verify)
    let tier_registry = if let Some(ref tm) = tri_manager {
        let registry = Arc::new(TierHandlerRegistry::from_components(Arc::clone(tm)));
        tracing::info!("TierHandlerRegistry configured (edge + tri-model handlers)");
        Some(registry)
    } else {
        // Edge-rules-only registry (Tier 0 always available)
        let mut registry = TierHandlerRegistry::new();
        registry.register(
            wm_bicameral::InferenceTier::EdgeRules,
            Box::new(EdgeRuleHandler::new()),
        );
        tracing::info!("TierHandlerRegistry configured (edge-rules only)");
        Some(Arc::new(registry))
    };

    CyberbrainComponents {
        speculative,
        harness,
        encoder,
        tri_model: tri_manager,
        tier_registry,
    }
}
