//! Glyph wire tools — Q34 sub-experiment 2 (2026-09-09, session 7f56e966).
//!
//! `glyph.encode` translates {route, args} into the compact {r, a} wire
//! form (see the codebook in crate root: GLYPH_ROUTES / GLYPH_ARGS).
//! Pure function, read-only effects, registered unconditionally — the
//! trust-boundary gate lives on the DECODE seam (`WM_GLYPH=1` in the
//! meta-tool), not here: emitting codes is harmless, parsing them is
//! what Q09 reviews. Unknown names pass through unchanged (both sides),
//! so partial books never corrupt.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};

/// `glyph.encode` — {route, args} → {r, a} compact form.
/// Args: route (required), args (object, default {}).
pub struct GlyphEncodeTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl GlyphEncodeTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for GlyphEncodeTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for GlyphEncodeTool {
    fn name(&self) -> &str {
        "glyph.encode"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Encode a {route, args} dispatch into the compact glyph wire form {r, a}. Args: route (required), args (object, default {}). Pure translation — unknown names pass through; decode side (WM_GLYPH=1) reverses it."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let route = args
            .get("route")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("route is required".into()))?;
        let inner = args.get("args").cloned().unwrap_or_else(|| json!({}));
        let encoded = crate::encode_glyph(route, &inner);
        let raw_len =
            serde_json::to_string(&json!({"route": route, "args": inner})).map_or(0, |s| s.len());
        let enc_len = serde_json::to_string(&encoded).map_or(0, |s| s.len());
        Ok(json!({
            "status": "success",
            "encoded": encoded,
            "raw_length": raw_len,
            "encoded_length": enc_len,
            "saved_ratio": if raw_len > 0 {
                1.0 - enc_len as f64 / raw_len as f64
            } else {
                0.0
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `glyph.decode` — {r, a} compact form → {route, args}. Debug/bench
/// surface for the wire format; the live decode seam sits in the
/// meta-tool (WM_GLYPH=1). Unknown route codes refuse (None → error).
pub struct GlyphDecodeTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl GlyphDecodeTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for GlyphDecodeTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for GlyphDecodeTool {
    fn name(&self) -> &str {
        "glyph.decode"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Decode a glyph wire object {r, a} back into {route, args}. Args: r (required route code), a (object of coded args, default {}). Unknown route codes are refused; unknown arg codes pass through."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let decoded = crate::decode_glyph(&args).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(
                "not a glyph object: need {r: <known route code>, a: {...}}".into(),
            )
        })?;
        Ok(json!({ "status": "success", "decoded": decoded }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the glyph tools (2) — pure translators, no gating: the
/// trust gate lives on the meta-tool's decode seam (WM_GLYPH=1).
#[must_use]
pub fn register_glyph(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    registry
        .register(std::sync::Arc::new(GlyphEncodeTool::new()))
        .register(std::sync::Arc::new(GlyphDecodeTool::new()))
}

#[cfg(test)]
mod glyph_tests {
    use super::*;

    #[test]
    fn book_tables_cover_measured_routes() {
        for route in [
            "memory.search",
            "memory.create",
            "session.record",
            "session.continuity",
            "dharma.escalate",
            "graph.walk",
            "tools.list",
            "citta.status",
        ] {
            assert!(
                crate::glyph_lookup(crate::GLYPH_ROUTES, route).is_some(),
                "missing {route}"
            );
        }
    }
}
