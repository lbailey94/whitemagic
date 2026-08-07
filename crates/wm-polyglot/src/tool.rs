//! Polyglot tool — wraps the polyglot registry as a WhiteMagic `Tool`.
//!
//! This allows the dispatch pipeline to route calls to any registered
//! language backend. The tool name is `polyglot.call`.

use crate::backend::PolyglotRegistry;
use crate::value::PolyglotValue;
use std::sync::{Arc, Mutex};
use wm_core::{
    Args, Capability, Context, CostEstimate, EffectRow, Gana, Output, Resource, Tool, ToolStats,
};

/// A WhiteMagic tool that dispatches to polyglot backends.
pub struct PolyglotTool {
    stats: ToolStats,
    effects: EffectRow,
    registry: Arc<Mutex<PolyglotRegistry>>,
}

impl PolyglotTool {
    /// Create a new polyglot tool wrapping the given registry.
    #[must_use]
    pub fn new(registry: Arc<Mutex<PolyglotRegistry>>) -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![],
                writes: vec![Resource::Galaxy("polyglot".into())],
                invokes: vec![Capability::Execute],
                spawns: true,
                destructive: false,
                cost: CostEstimate {
                    cpu_ns: 10_000_000,
                    expensive: true,
                    ..Default::default()
                },
            },
            registry,
        }
    }
}

impl Tool for PolyglotTool {
    fn name(&self) -> &str {
        "polyglot.call"
    }

    fn gana(&self) -> Gana {
        Gana::Horn
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        let backend = args
            .get("backend")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("missing 'backend' field".into()))?;
        let module = args
            .get("module")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("missing 'module' field".into()))?;
        let function = args
            .get("function")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("missing 'function' field".into()))?;

        // Convert JSON args to PolyglotValue
        let poly_args: Vec<PolyglotValue> = args
            .get("args")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().map(json_to_polyglot).collect())
            .unwrap_or_default();

        let reg = self
            .registry
            .lock()
            .map_err(|e| wm_core::CoreError::Polyglot(format!("registry lock failed: {e}")))?;

        let result = reg
            .call(backend, module, function, &poly_args)
            .map_err(|e| wm_core::CoreError::Polyglot(format!("polyglot call failed: {e}")))?;

        Ok(polyglot_to_json(&result))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Convert a JSON value to a PolyglotValue.
fn json_to_polyglot(v: &serde_json::Value) -> PolyglotValue {
    match v {
        serde_json::Value::Null => PolyglotValue::Null,
        serde_json::Value::Bool(b) => PolyglotValue::Bool(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                PolyglotValue::Int(i)
            } else if let Some(f) = n.as_f64() {
                PolyglotValue::Float(f)
            } else {
                PolyglotValue::Null
            }
        }
        serde_json::Value::String(s) => PolyglotValue::String(s.clone()),
        serde_json::Value::Array(arr) => {
            PolyglotValue::Array(arr.iter().map(json_to_polyglot).collect())
        }
        serde_json::Value::Object(obj) => PolyglotValue::Map(
            obj.iter()
                .map(|(k, v)| (k.clone(), json_to_polyglot(v)))
                .collect(),
        ),
    }
}

/// Convert a PolyglotValue to a JSON value.
fn polyglot_to_json(v: &PolyglotValue) -> serde_json::Value {
    match v {
        PolyglotValue::Null => serde_json::Value::Null,
        PolyglotValue::Bool(b) => serde_json::Value::Bool(*b),
        PolyglotValue::Int(i) => serde_json::Value::Number((*i).into()),
        PolyglotValue::Float(f) => serde_json::Number::from_f64(*f)
            .map(serde_json::Value::Number)
            .unwrap_or(serde_json::Value::Null),
        PolyglotValue::String(s) => serde_json::Value::String(s.clone()),
        PolyglotValue::Array(arr) => {
            serde_json::Value::Array(arr.iter().map(polyglot_to_json).collect())
        }
        PolyglotValue::Map(m) => serde_json::Value::Object(
            m.iter()
                .map(|(k, v)| (k.clone(), polyglot_to_json(v)))
                .collect(),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn polyglot_tool_name() {
        let reg = Arc::new(Mutex::new(PolyglotRegistry::new()));
        let tool = PolyglotTool::new(reg);
        assert_eq!(tool.name(), "polyglot.call");
    }

    #[test]
    fn polyglot_tool_gana() {
        let reg = Arc::new(Mutex::new(PolyglotRegistry::new()));
        let tool = PolyglotTool::new(reg);
        assert_eq!(tool.gana(), Gana::Horn);
    }

    #[test]
    fn polyglot_tool_call_missing_backend() {
        let reg = Arc::new(Mutex::new(PolyglotRegistry::new()));
        let tool = PolyglotTool::new(reg);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, serde_json::json!({}));
        assert!(result.is_err());
    }

    #[test]
    fn polyglot_tool_call_missing_module() {
        let reg = Arc::new(Mutex::new(PolyglotRegistry::new()));
        let tool = PolyglotTool::new(reg);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, serde_json::json!({"backend": "zig"}));
        assert!(result.is_err());
    }

    #[test]
    fn polyglot_tool_call_missing_function() {
        let reg = Arc::new(Mutex::new(PolyglotRegistry::new()));
        let tool = PolyglotTool::new(reg);
        let mut ctx = Context::default();
        let result = tool.call(
            &mut ctx,
            serde_json::json!({"backend": "zig", "module": "mymod"}),
        );
        assert!(result.is_err());
    }

    #[test]
    fn polyglot_tool_call_no_backend_registered() {
        let reg = Arc::new(Mutex::new(PolyglotRegistry::new()));
        let tool = PolyglotTool::new(reg);
        let mut ctx = Context::default();
        let result = tool.call(
            &mut ctx,
            serde_json::json!({
                "backend": "zig",
                "module": "mymod",
                "function": "add",
                "args": [1, 2]
            }),
        );
        assert!(result.is_err());
    }

    #[test]
    fn json_to_polyglot_roundtrip() {
        let json = serde_json::json!({
            "name": "test",
            "value": 42,
            "items": [true, 3.15, "hello"]
        });
        let poly = json_to_polyglot(&json);
        let back = polyglot_to_json(&poly);
        assert_eq!(json, back);
    }

    #[test]
    fn json_to_polyglot_null() {
        let json = serde_json::Value::Null;
        let poly = json_to_polyglot(&json);
        assert_eq!(poly, PolyglotValue::Null);
    }

    #[test]
    fn json_to_polyglot_bool() {
        let json = serde_json::Value::Bool(true);
        let poly = json_to_polyglot(&json);
        assert_eq!(poly, PolyglotValue::Bool(true));
    }

    #[test]
    fn json_to_polyglot_int() {
        let json = serde_json::json!(42);
        let poly = json_to_polyglot(&json);
        assert_eq!(poly, PolyglotValue::Int(42));
    }

    #[test]
    fn json_to_polyglot_float() {
        let json = serde_json::json!(3.15);
        let poly = json_to_polyglot(&json);
        assert_eq!(poly, PolyglotValue::Float(3.15));
    }

    #[test]
    fn json_to_polyglot_array() {
        let json = serde_json::json!([1, 2, 3]);
        let poly = json_to_polyglot(&json);
        assert!(poly.as_array().is_some());
        assert_eq!(poly.as_array().unwrap().len(), 3);
    }

    #[test]
    fn polyglot_to_json_map() {
        let poly = PolyglotValue::map([("key".into(), PolyglotValue::int(1))]);
        let json = polyglot_to_json(&poly);
        assert!(json.is_object());
        assert_eq!(json.get("key").unwrap(), &serde_json::json!(1));
    }
}
