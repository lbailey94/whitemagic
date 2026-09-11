//! Logographic Kernel Execution Pipeline (LKEP) — Proposal 3
//!
//! Ultra-low-latency logographic expression parsing and kernel dispatch for local LLMs.
//! Bridges single-token Sanskrit-Chinese ideograms (`忆`, `索`, `录`, `存`, `读`, `回`,
//! `续`, `契`, `记`, `心`, `律`, `业`, `具`) and arguments (`问`, `数`, `文`, `标`, `界`, `号`)
//! directly into WhiteMagic dispatch and memory kernels without JSON framing overhead.

#![forbid(unsafe_code)]

use async_trait::async_trait;
use serde_json::{Map, Value, json};
use thiserror::Error;
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};

/// Errors encountered during Logographic Kernel parsing or execution.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum LkepError {
    #[error("Empty logographic expression")]
    EmptyExpression,

    #[error("Unknown route or glyph ideogram: {0}")]
    UnknownRoute(String),

    #[error("Syntax error in logographic expression: {0}")]
    SyntaxError(String),
}

/// Fast route resolver: maps ASCII glyphs ("Ms"), single-character ideograms ("忆"),
/// or canonical route strings ("memory.search") to the canonical route string.
#[must_use]
pub fn resolve_route(code: &str) -> Option<&'static str> {
    let trimmed = code.trim();
    // 1. Check if it's a known code or ideogram in GLYPH_ROUTES
    for &(canonical, route_code) in crate::GLYPH_ROUTES {
        if route_code == trimmed {
            return Some(canonical);
        }
    }
    // 2. Check if it's already a canonical route name
    for &(canonical, _) in crate::GLYPH_ROUTES {
        if canonical == trimmed {
            return Some(canonical);
        }
    }
    None
}

/// Fast arg key resolver: maps ASCII arg codes ("q"), single-character ideograms ("问"),
/// or canonical arg names ("query") to the canonical arg name.
#[must_use]
pub fn resolve_arg(code: &str) -> Option<&'static str> {
    let trimmed = code.trim();
    // 1. Check if it's a known code or ideogram in GLYPH_ARGS
    for &(canonical, arg_code) in crate::GLYPH_ARGS {
        if arg_code == trimmed {
            return Some(canonical);
        }
    }
    // 2. Check if it's already a canonical arg name
    for &(canonical, _) in crate::GLYPH_ARGS {
        if canonical == trimmed {
            return Some(canonical);
        }
    }
    None
}

/// Returns the primary default argument for a canonical route, used for positional shorthand.
#[must_use]
pub fn primary_arg_for_route(canonical_route: &str) -> &'static str {
    match canonical_route {
        "memory.search" | "memory.hybrid_recall" | "session.continuity" => "query",
        "memory.create" | "session.record" => "content",
        "memory.read" => "id",
        "session.checkpoint" => "title",
        _ => "query",
    }
}

/// Parse a raw scalar or JSON literal string into a `serde_json::Value`.
fn parse_scalar_or_json(raw: &str) -> Value {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Value::Null;
    }

    // Try standard JSON parsing first for numbers, booleans, arrays, objects, and quoted strings
    if let Ok(v) = serde_json::from_str::<Value>(trimmed) {
        return v;
    }

    // Handle single-quoted strings: 'foo' -> "foo"
    if trimmed.len() >= 2
        && trimmed.starts_with('\'')
        && trimmed.ends_with('\'')
    {
        return Value::String(trimmed[1..trimmed.len() - 1].to_string());
    }

    // Bare word fallback as a string
    Value::String(trimmed.to_string())
}

/// Parse a logographic expression string into a `(canonical_route, args)` tuple.
///
/// Supported formats:
/// 1. Function call syntax: `忆(问="auth failure", 数=5)` or `忆(问: "auth failure")`
/// 2. Positional shorthand: `忆("auth failure")` or `忆(auth failure)`
/// 3. Colon syntax: `忆: "auth failure"` or `忆: auth failure`
/// 4. Bare route: `心()` or `心`
pub fn parse_lkep_expression(expr: &str) -> Result<(String, Value), LkepError> {
    let trimmed = expr.trim();
    if trimmed.is_empty() {
        return Err(LkepError::EmptyExpression);
    }

    // Case 1 & 2: Paren syntax — Route(...)
    if let Some(open_paren) = trimmed.find('(') {
        if !trimmed.ends_with(')') {
            return Err(LkepError::SyntaxError("Missing closing parenthesis ')'".into()));
        }

        let route_part = trimmed[..open_paren].trim();
        let canonical_route = resolve_route(route_part)
            .ok_or_else(|| LkepError::UnknownRoute(route_part.to_string()))?;

        let inner = trimmed[open_paren + 1..trimmed.len() - 1].trim();
        if inner.is_empty() {
            return Ok((canonical_route.to_string(), json!({})));
        }

        // Check if there are key-value separators (= or :)
        if !inner.contains('=') && !inner.contains(':') {
            // Positional shorthand: single primary argument
            let primary = primary_arg_for_route(canonical_route);
            let val = parse_scalar_or_json(inner);
            let mut map = Map::new();
            map.insert(primary.to_string(), val);
            return Ok((canonical_route.to_string(), Value::Object(map)));
        }

        // Parse key-value arguments separated by commas (respecting quotes and brackets)
        let mut map = Map::new();
        let mut in_quotes = false;
        let mut quote_char = '"';
        let mut bracket_depth = 0;
        let mut current_segment = String::new();

        for ch in inner.chars() {
            match ch {
                '"' | '\'' if !in_quotes => {
                    in_quotes = true;
                    quote_char = ch;
                    current_segment.push(ch);
                }
                c if in_quotes && c == quote_char => {
                    in_quotes = false;
                    current_segment.push(ch);
                }
                '[' | '{' if !in_quotes => {
                    bracket_depth += 1;
                    current_segment.push(ch);
                }
                ']' | '}' if !in_quotes && bracket_depth > 0 => {
                    bracket_depth -= 1;
                    current_segment.push(ch);
                }
                ',' if !in_quotes && bracket_depth == 0 => {
                    parse_arg_pair(&current_segment, &mut map)?;
                    current_segment.clear();
                }
                _ => {
                    current_segment.push(ch);
                }
            }
        }

        if !current_segment.trim().is_empty() {
            parse_arg_pair(&current_segment, &mut map)?;
        }

        return Ok((canonical_route.to_string(), Value::Object(map)));
    }

    // Case 3: Colon syntax — Route: Argument
    if let Some(colon_pos) = trimmed.find(':') {
        let route_part = trimmed[..colon_pos].trim();
        if let Some(canonical_route) = resolve_route(route_part) {
            let inner = trimmed[colon_pos + 1..].trim();
            let primary = primary_arg_for_route(canonical_route);
            let val = parse_scalar_or_json(inner);
            let mut map = Map::new();
            map.insert(primary.to_string(), val);
            return Ok((canonical_route.to_string(), Value::Object(map)));
        }
    }

    // Case 4: Bare route — Route
    if let Some(canonical_route) = resolve_route(trimmed) {
        return Ok((canonical_route.to_string(), json!({})));
    }

    Err(LkepError::UnknownRoute(trimmed.to_string()))
}

/// Helper to parse a single `key=val` or `key:val` argument pair.
fn parse_arg_pair(segment: &str, map: &mut Map<String, Value>) -> Result<(), LkepError> {
    let seg = segment.trim();
    if seg.is_empty() {
        return Ok(());
    }

    let (k_part, v_part) = if let Some(eq_pos) = seg.find('=') {
        (&seg[..eq_pos], &seg[eq_pos + 1..])
    } else if let Some(col_pos) = seg.find(':') {
        (&seg[..col_pos], &seg[col_pos + 1..])
    } else {
        return Err(LkepError::SyntaxError(format!(
            "Expected 'key=value' or 'key:value' in '{seg}'"
        )));
    };

    let k_trimmed = k_part.trim();
    let canonical_key = resolve_arg(k_trimmed).unwrap_or(k_trimmed);
    let val = parse_scalar_or_json(v_part);
    map.insert(canonical_key.to_string(), val);
    Ok(())
}

/// Universal decoder: decodes ANY representation (string expression, glyph JSON,
/// route object, root ideogram map) into `(canonical_route, canonical_args)`.
#[must_use]
pub fn decode_lkep(input: &Value) -> Option<(String, Value)> {
    // 1. String representation: parse as LKEP expression
    if let Some(s) = input.as_str() {
        return parse_lkep_expression(s).ok();
    }

    let obj = input.as_object()?;

    // 2. Standard glyph object: {"r": "忆", "a": {"问": "..."}}
    if let Some(rcode) = obj.get("r").and_then(Value::as_str) {
        let canonical_route = resolve_route(rcode)?;
        let mut decoded_args = Map::new();
        if let Some(aobj) = obj.get("a").and_then(Value::as_object) {
            for (k, v) in aobj {
                let canonical_key = resolve_arg(k).unwrap_or(k);
                decoded_args.insert(canonical_key.to_string(), v.clone());
            }
        }
        return Some((canonical_route.to_string(), Value::Object(decoded_args)));
    }

    // 3. Object with "route" key: {"route": "忆", "args": {...}}
    if let Some(route_str) = obj.get("route").and_then(Value::as_str) {
        let canonical_route = resolve_route(route_str)?;
        let mut decoded_args = Map::new();
        if let Some(aobj) = obj.get("args").and_then(Value::as_object) {
            for (k, v) in aobj {
                let canonical_key = resolve_arg(k).unwrap_or(k);
                decoded_args.insert(canonical_key.to_string(), v.clone());
            }
        }
        return Some((canonical_route.to_string(), Value::Object(decoded_args)));
    }

    // 4. Single-key root ideogram object: {"忆": {"问": "..."}} or {"忆": "query string"}
    if obj.len() == 1 {
        let (k, v) = obj.iter().next()?;
        if let Some(canonical_route) = resolve_route(k) {
            if let Some(inner_obj) = v.as_object() {
                let mut decoded_args = Map::new();
                for (ik, iv) in inner_obj {
                    let canonical_key = resolve_arg(ik).unwrap_or(ik);
                    decoded_args.insert(canonical_key.to_string(), iv.clone());
                }
                return Some((canonical_route.to_string(), Value::Object(decoded_args)));
            }
            // Positional shorthand for single-key root object: {"忆": "auth failure"}
            let primary = primary_arg_for_route(canonical_route);
            let mut map = Map::new();
            map.insert(primary.to_string(), v.clone());
            return Some((canonical_route.to_string(), Value::Object(map)));
        }
    }

    None
}

/// Tool `lkep.exec` — Executes or translates logographic expressions directly.
pub struct LkepExecTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl LkepExecTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for LkepExecTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for LkepExecTool {
    fn name(&self) -> &str {
        "lkep.exec"
    }

    fn gana(&self) -> Gana {
        Gana::Horn
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Execute or parse a Sanskrit-Chinese logographic expression (e.g. 忆(问=\"auth failure\", 数=5)) directly through the WhiteMagic logographic kernel execution pipeline."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let (route, resolved_args) = if let Some((r, a)) = decode_lkep(&args) {
            (r, a)
        } else if let Some(expr) = args.get("expr").and_then(Value::as_str) {
            parse_lkep_expression(expr).map_err(|e| wm_core::CoreError::InvalidArgs(e.to_string()))?
        } else {
            return Err(wm_core::CoreError::InvalidArgs(
                "Expected logographic expression in string format, {expr: \"...\"}, or glyph object".into(),
            ));
        };

        Ok(json!({
            "status": "success",
            "pipeline": "LKEP-v1",
            "route": route,
            "args": resolved_args,
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_routes_and_args() {
        assert_eq!(resolve_route("忆"), Some("memory.search"));
        assert_eq!(resolve_route("索"), Some("memory.search"));
        assert_eq!(resolve_route("Ms"), Some("memory.search"));
        assert_eq!(resolve_route("memory.search"), Some("memory.search"));
        assert_eq!(resolve_route("录"), Some("memory.create"));
        assert_eq!(resolve_route("心"), Some("citta.status"));
        assert_eq!(resolve_route("nonexistent"), None);

        assert_eq!(resolve_arg("问"), Some("query"));
        assert_eq!(resolve_arg("数"), Some("limit"));
        assert_eq!(resolve_arg("文"), Some("content"));
        assert_eq!(resolve_arg("标"), Some("tags"));
        assert_eq!(resolve_arg("query"), Some("query"));
    }

    #[test]
    fn test_parse_lkep_function_call_named_args() {
        let (route, args) = parse_lkep_expression("忆(问=\"auth failure\", 数=5)").unwrap();
        assert_eq!(route, "memory.search");
        assert_eq!(args["query"], "auth failure");
        assert_eq!(args["limit"], 5);

        let (route2, args2) =
            parse_lkep_expression("录(文=\"daemon restart\", 标=[\"crash\", \"vulkan\"])").unwrap();
        assert_eq!(route2, "memory.create");
        assert_eq!(args2["content"], "daemon restart");
        assert_eq!(args2["tags"][0], "crash");
        assert_eq!(args2["tags"][1], "vulkan");
    }

    #[test]
    fn test_parse_lkep_positional_shorthand() {
        let (route, args) = parse_lkep_expression("忆(\"system deadlock\")").unwrap();
        assert_eq!(route, "memory.search");
        assert_eq!(args["query"], "system deadlock");

        let (route2, args2) = parse_lkep_expression("忆: system deadlock").unwrap();
        assert_eq!(route2, "memory.search");
        assert_eq!(args2["query"], "system deadlock");
    }

    #[test]
    fn test_parse_lkep_bare_route() {
        let (route, args) = parse_lkep_expression("心()").unwrap();
        assert_eq!(route, "citta.status");
        assert_eq!(args, json!({}));

        let (route2, args2) = parse_lkep_expression("律").unwrap();
        assert_eq!(route2, "dharma.rules");
        assert_eq!(args2, json!({}));
    }

    #[test]
    fn test_decode_lkep_all_shapes() {
        // Shape 1: String
        let res1 = decode_lkep(&json!("忆(问=\"disk full\", 数=10)")).unwrap();
        assert_eq!(res1.0, "memory.search");
        assert_eq!(res1.1["query"], "disk full");
        assert_eq!(res1.1["limit"], 10);

        // Shape 2: Glyph JSON
        let res2 = decode_lkep(&json!({ "r": "忆", "a": { "问": "timeout" } })).unwrap();
        assert_eq!(res2.0, "memory.search");
        assert_eq!(res2.1["query"], "timeout");

        // Shape 3: Route object
        let res3 = decode_lkep(&json!({ "route": "录", "args": { "文": "snapshot", "标": ["auto"] } })).unwrap();
        assert_eq!(res3.0, "memory.create");
        assert_eq!(res3.1["content"], "snapshot");

        // Shape 4: Root ideogram object
        let res4 = decode_lkep(&json!({ "忆": "uncommitted writes" })).unwrap();
        assert_eq!(res4.0, "memory.search");
        assert_eq!(res4.1["query"], "uncommitted writes");
    }
}
