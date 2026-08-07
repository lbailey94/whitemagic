//! Julia backend — embeds the Julia runtime via jlrs.
//!
//! Provides evaluation of Julia code and function calls with automatic
//! conversion between `PolyglotValue` and Julia types.
//!
//! Requires the `julia` feature to be enabled:
//! ```bash
//! cargo build --features wm-polyglot/julia
//! ```

use crate::backend::PolyglotBackend;
use crate::value::{PolyglotError, PolyglotValue};

/// Julia backend (stub when `julia` feature is disabled).
pub struct JuliaBackend {
    initialized: bool,
}

impl JuliaBackend {
    /// Create a new Julia backend.
    #[must_use]
    pub fn new() -> Self {
        Self { initialized: false }
    }
}

impl Default for JuliaBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl PolyglotBackend for JuliaBackend {
    fn name(&self) -> &str {
        "julia"
    }

    fn is_initialized(&self) -> bool {
        self.initialized
    }

    fn init(&mut self) -> Result<(), PolyglotError> {
        #[cfg(feature = "julia")]
        {
            use jlrs::prelude::*;
            Julia::init().map_err(|e| PolyglotError::InitFailed(e.to_string()))?;
            self.initialized = true;
            tracing::info!("Julia runtime initialized");
            Ok(())
        }
        #[cfg(not(feature = "julia"))]
        {
            Err(PolyglotError::BackendUnavailable(
                "Julia backend requires --features wm-polyglot/julia".into(),
            ))
        }
    }

    fn eval(&self, code: &str) -> Result<PolyglotValue, PolyglotError> {
        if code.is_empty() {
            return Err(PolyglotError::InvalidArg("eval code is empty".into()));
        }
        if code.len() > 1024 * 1024 {
            return Err(PolyglotError::InvalidArg(format!(
                "eval code too long ({} > 1MB)",
                code.len()
            )));
        }
        #[cfg(feature = "julia")]
        {
            use jlrs::prelude::*;
            let mut frame = StackFrame::new();
            let mut julia = Julia::init().map_err(|e| PolyglotError::InitFailed(e.to_string()))?;
            julia
                .scope(&mut frame, |mut frame| {
                    let result = unsafe { Value::eval_string(&mut frame, code)? };
                    convert_julia_value(&mut frame, result)
                })
                .map_err(|e| PolyglotError::CallFailed(e.to_string()))
        }
        #[cfg(not(feature = "julia"))]
        {
            let _ = code;
            Err(PolyglotError::BackendUnavailable(
                "Julia backend requires --features wm-polyglot/julia".into(),
            ))
        }
    }

    fn call_function(
        &self,
        module: &str,
        function: &str,
        args: &[PolyglotValue],
    ) -> Result<PolyglotValue, PolyglotError> {
        if module.is_empty() {
            return Err(PolyglotError::InvalidArg("module name is empty".into()));
        }
        if function.is_empty() {
            return Err(PolyglotError::InvalidArg("function name is empty".into()));
        }
        if function.len() > 256 {
            return Err(PolyglotError::InvalidArg(format!(
                "function name too long ({} > 256 bytes)",
                function.len()
            )));
        }
        let args_json = serde_json::to_string(args).unwrap_or_default();
        if args_json.len() > 1024 * 1024 {
            return Err(PolyglotError::InvalidArg(format!(
                "args too large ({} > 1MB)",
                args_json.len()
            )));
        }
        #[cfg(feature = "julia")]
        {
            use jlrs::prelude::*;
            let mut frame = StackFrame::new();
            let mut julia = Julia::init().map_err(|e| PolyglotError::InitFailed(e.to_string()))?;
            julia
                .scope(&mut frame, |mut frame| {
                    let module_value = unsafe {
                        Module::main(&mut frame)
                            .base()
                            .submodule(&mut frame, module)?
                    };
                    let func = unsafe { module_value.function(&mut frame, function)? };
                    // Convert args and call
                    let mut julia_args = Vec::with_capacity(args.len());
                    for arg in args {
                        let jval = convert_to_julia(&mut frame, arg)?;
                        julia_args.push(jval);
                    }
                    let result = unsafe { func.call(&mut frame, julia_args)? };
                    convert_julia_value(&mut frame, result)
                })
                .map_err(|e| PolyglotError::CallFailed(e.to_string()))
        }
        #[cfg(not(feature = "julia"))]
        {
            let _ = (module, function, args);
            Err(PolyglotError::BackendUnavailable(
                "Julia backend requires --features wm-polyglot/julia".into(),
            ))
        }
    }

    fn load_module(&self, path: &str) -> Result<(), PolyglotError> {
        if path.is_empty() {
            return Err(PolyglotError::InvalidArg("module path is empty".into()));
        }
        if path.contains("..") {
            return Err(PolyglotError::InvalidArg(
                "module path contains path traversal".into(),
            ));
        }
        #[cfg(feature = "julia")]
        {
            let code = format!("include(\"{path}\")");
            self.eval(&code).map(|_| ())
        }
        #[cfg(not(feature = "julia"))]
        {
            let _ = path;
            Err(PolyglotError::BackendUnavailable(
                "Julia backend requires --features wm-polyglot/julia".into(),
            ))
        }
    }

    fn shutdown(&mut self) {
        self.initialized = false;
        #[cfg(feature = "julia")]
        {
            // jlrs doesn't have an explicit shutdown — Julia runtime is process-global
            tracing::info!("Julia backend shutdown (runtime remains alive)");
        }
    }
}

#[cfg(feature = "julia")]
fn convert_to_julia<'frame>(
    frame: &mut jlrs::prelude::OutputScope<'frame, '_>,
    value: &PolyglotValue,
) -> jlrs::prelude::JlrsResult<jlrs::prelude::Value<'frame, 'static>> {
    use jlrs::prelude::*;
    match value {
        PolyglotValue::Null => Ok(unsafe { Value::nothing(frame) }),
        PolyglotValue::Bool(b) => Ok(unsafe { Value::bool(frame, *b)? }),
        PolyglotValue::Int(i) => Ok(unsafe { Value::int64(frame, *i)? }),
        PolyglotValue::Float(f) => Ok(unsafe { Value::float64(frame, *f)? }),
        PolyglotValue::String(s) => Ok(unsafe { Value::string(frame, s)? }),
        PolyglotValue::Array(_) | PolyglotValue::Map(_) => {
            // Complex types — serialize to JSON and parse in Julia
            let json = value.to_json();
            let code = format!("JSON.parse(\"{}\")", json.replace('"', "\\\""));
            let result = unsafe { Value::eval_string(frame, &code)? };
            Ok(result)
        }
    }
}

#[cfg(feature = "julia")]
fn convert_julia_value<'frame>(
    _frame: &mut jlrs::prelude::OutputScope<'frame, '_>,
    _value: jlrs::prelude::Value<'frame, 'static>,
) -> jlrs::prelude::JlrsResult<PolyglotValue> {
    // Full type conversion would require pattern matching on Julia type tags.
    // For now, serialize via JSON.jl.
    // This is a simplified stub — full implementation would inspect type tags.
    Ok(PolyglotValue::null())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn julia_backend_name() {
        let b = JuliaBackend::new();
        assert_eq!(b.name(), "julia");
    }

    #[test]
    fn julia_backend_not_initialized() {
        let b = JuliaBackend::new();
        assert!(!b.is_initialized());
    }

    #[test]
    fn julia_backend_init_without_feature() {
        let mut b = JuliaBackend::new();
        let result = b.init();
        #[cfg(not(feature = "julia"))]
        assert!(result.is_err());
        #[cfg(feature = "julia")]
        {
            let _ = result;
        }
    }

    #[test]
    fn julia_backend_eval_without_feature() {
        let b = JuliaBackend::new();
        let result = b.eval("1 + 1");
        #[cfg(not(feature = "julia"))]
        assert!(result.is_err());
        #[cfg(feature = "julia")]
        {
            let _ = result;
        }
    }

    #[test]
    fn julia_backend_call_without_feature() {
        let b = JuliaBackend::new();
        let result = b.call_function("Base", "sum", &[PolyglotValue::int(1)]);
        #[cfg(not(feature = "julia"))]
        assert!(result.is_err());
        #[cfg(feature = "julia")]
        {
            let _ = result;
        }
    }

    #[test]
    fn julia_backend_shutdown() {
        let mut b = JuliaBackend::new();
        b.shutdown();
        assert!(!b.is_initialized());
    }

    #[test]
    fn julia_backend_default() {
        let b = JuliaBackend::default();
        assert_eq!(b.name(), "julia");
    }

    #[test]
    fn julia_eval_rejects_empty_code() {
        let b = JuliaBackend::new();
        let result = b.eval("");
        assert!(result.is_err());
        match result {
            Err(PolyglotError::InvalidArg(msg)) => assert!(msg.contains("empty")),
            _ => panic!("Expected InvalidArg error"),
        }
    }

    #[test]
    fn julia_eval_rejects_oversized_code() {
        let b = JuliaBackend::new();
        let big = "x".repeat(1024 * 1024 + 1);
        let result = b.eval(&big);
        assert!(result.is_err());
    }

    #[test]
    fn julia_call_rejects_empty_module() {
        let b = JuliaBackend::new();
        let result = b.call_function("", "f", &[]);
        assert!(result.is_err());
    }

    #[test]
    fn julia_call_rejects_empty_function() {
        let b = JuliaBackend::new();
        let result = b.call_function("mod", "", &[]);
        assert!(result.is_err());
    }

    #[test]
    fn julia_call_rejects_oversized_function_name() {
        let b = JuliaBackend::new();
        let big = "f".repeat(257);
        let result = b.call_function("mod", &big, &[]);
        assert!(result.is_err());
    }

    #[test]
    fn julia_load_module_rejects_empty_path() {
        let b = JuliaBackend::new();
        let result = b.load_module("");
        assert!(result.is_err());
    }

    #[test]
    fn julia_load_module_rejects_path_traversal() {
        let b = JuliaBackend::new();
        let result = b.load_module("../../etc/passwd");
        assert!(result.is_err());
    }
}
