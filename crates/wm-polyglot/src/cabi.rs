//! C ABI backend — loads shared libraries and calls functions via FFI.
//!
//! This backend implements the `PolyglotBackend` trait for any language
//! that compiles to a C ABI shared library (Zig, Koka, Haskell, C, etc.).
//!
//! ## Protocol
//!
//! Loaded libraries must export two functions:
//!
//! ```c
//! // Initialize the module (called once on load)
//! int32_t polyglot_init(void);
//!
//! // Call a function by name with JSON arguments
//! // Returns JSON string (caller must free via polyglot_free)
//! const char* polyglot_call(const char* function, const char* args_json);
//!
//! // Free a string returned by polyglot_call
//! void polyglot_free(const char* ptr);
//! ```

use crate::backend::PolyglotBackend;
use crate::value::{PolyglotError, PolyglotValue};
use libloading::{Library, Symbol};
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int};

/// Function pointer type for `polyglot_init`.
type InitFn = unsafe extern "C" fn() -> c_int;
/// Function pointer type for `polyglot_call`.
type CallFn = unsafe extern "C" fn(*const c_char, *const c_char) -> *const c_char;
/// Function pointer type for `polyglot_free`.
type FreeFn = unsafe extern "C" fn(*const c_char);

/// A loaded C ABI module.
pub struct CabiModule {
    /// Module name
    name: String,
    /// The loaded shared library
    library: Library,
    /// Whether init has been called
    initialized: bool,
}

/// C ABI backend — manages multiple loaded modules.
pub struct CabiBackend {
    /// Backend name (e.g., "zig", "koka", "haskell")
    backend_name: String,
    /// Loaded modules
    modules: Vec<CabiModule>,
}

impl CabiBackend {
    /// Create a new C ABI backend with the given name.
    #[must_use]
    pub fn new(name: &str) -> Self {
        Self {
            backend_name: name.into(),
            modules: Vec::new(),
        }
    }

    /// Load a shared library as a module.
    ///
    /// # Errors
    /// Returns `PolyglotError::LibraryLoad` if the library can't be loaded
    /// or doesn't export the required symbols.
    pub fn load(&mut self, module_name: &str, path: &str) -> Result<(), PolyglotError> {
        // Validate path for safety
        if !is_library_path_safe(path) {
            return Err(PolyglotError::LibraryLoad(format!(
                "library path rejected by safety validation: {path}"
            )));
        }

        let library =
            unsafe { Library::new(path).map_err(|e| PolyglotError::LibraryLoad(e.to_string()))? };

        // Verify required symbols exist
        unsafe {
            let _: Symbol<InitFn> = library
                .get(b"polyglot_init")
                .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;
            let _: Symbol<CallFn> = library
                .get(b"polyglot_call")
                .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;
            let _: Symbol<FreeFn> = library
                .get(b"polyglot_free")
                .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;
        }

        self.modules.push(CabiModule {
            name: module_name.into(),
            library,
            initialized: false,
        });

        tracing::info!("Loaded C ABI module '{module_name}' from {path}");
        Ok(())
    }

    /// Find a module by name.
    fn find_module(&self, name: &str) -> Option<&CabiModule> {
        self.modules.iter().find(|m| m.name == name)
    }

    /// Call a function in a specific module.
    fn call_in_module(
        &self,
        module: &CabiModule,
        function: &str,
        args: &[PolyglotValue],
    ) -> Result<PolyglotValue, PolyglotError> {
        // Validate function name (prevent empty or oversized names)
        if function.is_empty() {
            return Err(PolyglotError::InvalidArg("function name is empty".into()));
        }
        if function.len() > 256 {
            return Err(PolyglotError::InvalidArg(format!(
                "function name too long ({} > 256 bytes)",
                function.len()
            )));
        }

        let args_json =
            serde_json::to_string(args).map_err(|e| PolyglotError::Serialization(e.to_string()))?;

        // Validate args size (prevent oversized payloads to FFI)
        const MAX_ARGS_SIZE: usize = 1024 * 1024; // 1 MB
        if args_json.len() > MAX_ARGS_SIZE {
            return Err(PolyglotError::InvalidArg(format!(
                "args JSON too large ({} > {MAX_ARGS_SIZE} bytes)",
                args_json.len()
            )));
        }

        let func_c =
            CString::new(function).map_err(|e| PolyglotError::InvalidArg(e.to_string()))?;
        let args_c = CString::new(args_json.as_str())
            .map_err(|e| PolyglotError::InvalidArg(e.to_string()))?;

        unsafe {
            let call_fn: Symbol<CallFn> = module
                .library
                .get(b"polyglot_call")
                .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;

            let result_ptr = call_fn(func_c.as_ptr(), args_c.as_ptr());
            if result_ptr.is_null() {
                return Err(PolyglotError::CallFailed(
                    "null result from FFI call".into(),
                ));
            }

            let result_str = CStr::from_ptr(result_ptr)
                .to_str()
                .map_err(|e| PolyglotError::CallFailed(e.to_string()))?;

            // Validate result size (prevent oversized results from FFI)
            const MAX_RESULT_SIZE: usize = 10 * 1024 * 1024; // 10 MB
            if result_str.len() > MAX_RESULT_SIZE {
                // Free the result string before returning error
                let free_fn: Symbol<FreeFn> = module
                    .library
                    .get(b"polyglot_free")
                    .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;
                free_fn(result_ptr);
                return Err(PolyglotError::CallFailed(format!(
                    "FFI result too large ({} > {MAX_RESULT_SIZE} bytes)",
                    result_str.len()
                )));
            }

            let result_json = result_str.to_string();

            // Free the result string
            let free_fn: Symbol<FreeFn> = module
                .library
                .get(b"polyglot_free")
                .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;
            free_fn(result_ptr);

            PolyglotValue::from_json(&result_json)
        }
    }
}

impl PolyglotBackend for CabiBackend {
    fn name(&self) -> &str {
        &self.backend_name
    }

    fn is_initialized(&self) -> bool {
        !self.modules.is_empty() && self.modules.iter().all(|m| m.initialized)
    }

    fn init(&mut self) -> Result<(), PolyglotError> {
        for module in &mut self.modules {
            if module.initialized {
                continue;
            }
            unsafe {
                let init_fn: Symbol<InitFn> = module
                    .library
                    .get(b"polyglot_init")
                    .map_err(|e| PolyglotError::SymbolLookup(e.to_string()))?;
                let result = init_fn();
                if result != 0 {
                    return Err(PolyglotError::InitFailed(format!(
                        "module '{}' init returned {result}",
                        module.name
                    )));
                }
            }
            module.initialized = true;
        }
        Ok(())
    }

    fn eval(&self, _code: &str) -> Result<PolyglotValue, PolyglotError> {
        // C ABI doesn't support eval — only function calls
        Err(PolyglotError::InvalidArg(
            "C ABI backend does not support eval — use call_function instead".into(),
        ))
    }

    fn call_function(
        &self,
        module: &str,
        function: &str,
        args: &[PolyglotValue],
    ) -> Result<PolyglotValue, PolyglotError> {
        // Validate function name before module lookup
        if function.is_empty() {
            return Err(PolyglotError::InvalidArg("function name is empty".into()));
        }
        if function.len() > 256 {
            return Err(PolyglotError::InvalidArg(format!(
                "function name too long ({} > 256 bytes)",
                function.len()
            )));
        }

        let mod_ref = self
            .find_module(module)
            .ok_or_else(|| PolyglotError::ModuleNotFound(module.into()))?;
        self.call_in_module(mod_ref, function, args)
    }

    fn load_module(&self, _path: &str) -> Result<(), PolyglotError> {
        // Module loading is done via `load()` which requires &mut self
        Err(PolyglotError::InvalidArg(
            "Use CabiBackend::load() to load C ABI modules".into(),
        ))
    }

    fn shutdown(&mut self) {
        for module in &mut self.modules {
            module.initialized = false;
        }
    }
}

/// Create a Zig backend.
#[must_use]
pub fn zig_backend() -> CabiBackend {
    CabiBackend::new("zig")
}

/// Create a Koka backend.
#[must_use]
pub fn koka_backend() -> CabiBackend {
    CabiBackend::new("koka")
}

/// Create a Haskell backend.
#[must_use]
pub fn haskell_backend() -> CabiBackend {
    CabiBackend::new("haskell")
}

/// Validate a library path for FFI safety.
///
/// Checks:
/// - Path must be absolute (no relative paths)
/// - No path traversal components (..)
/// - Must not be empty
#[must_use]
pub fn is_library_path_safe(path: &str) -> bool {
    if path.is_empty() {
        return false;
    }

    let p = std::path::Path::new(path);

    // Must be absolute
    if !p.is_absolute() {
        return false;
    }

    // Block path traversal
    for component in p.components() {
        if component == std::path::Component::ParentDir {
            return false;
        }
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cabi_backend_name() {
        let b = zig_backend();
        assert_eq!(b.name(), "zig");
    }

    #[test]
    fn cabi_backend_koka_name() {
        let b = koka_backend();
        assert_eq!(b.name(), "koka");
    }

    #[test]
    fn cabi_backend_haskell_name() {
        let b = haskell_backend();
        assert_eq!(b.name(), "haskell");
    }

    #[test]
    fn cabi_backend_not_initialized() {
        let b = zig_backend();
        assert!(!b.is_initialized());
    }

    #[test]
    fn cabi_backend_eval_unsupported() {
        let b = zig_backend();
        let result = b.eval("1 + 1");
        assert!(result.is_err());
    }

    #[test]
    fn cabi_backend_load_nonexistent() {
        let mut b = zig_backend();
        let result = b.load("test", "/nonexistent/path/libtest.so");
        assert!(result.is_err());
    }

    #[test]
    fn cabi_backend_call_no_modules() {
        let b = zig_backend();
        let result = b.call_function("mod", "fn", &[]);
        assert!(result.is_err());
    }

    #[test]
    fn cabi_backend_shutdown() {
        let mut b = zig_backend();
        b.shutdown();
        assert!(!b.is_initialized());
    }

    #[test]
    fn cabi_backend_load_module_unsupported() {
        let b = zig_backend();
        let result = b.load_module("path");
        assert!(result.is_err());
    }

    // ── FFI boundary validation tests ───────────────────────────────

    #[test]
    fn library_path_rejects_empty() {
        assert!(!is_library_path_safe(""));
    }

    #[test]
    fn library_path_rejects_relative() {
        assert!(!is_library_path_safe("libtest.so"));
        assert!(!is_library_path_safe("./libtest.so"));
    }

    #[test]
    fn library_path_rejects_traversal() {
        assert!(!is_library_path_safe("/usr/../etc/passwd"));
        assert!(!is_library_path_safe("/usr/local/../../lib/evil.so"));
    }

    #[test]
    fn library_path_accepts_absolute() {
        assert!(is_library_path_safe("/usr/lib/libtest.so"));
        assert!(is_library_path_safe("/home/user/modules/libzig.so"));
    }

    #[test]
    fn load_rejects_unsafe_path() {
        let mut b = zig_backend();
        // Relative path should be rejected
        let result = b.load("test", "libevil.so");
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(
            err.contains("safety validation"),
            "error should mention safety validation: {err}"
        );
    }

    #[test]
    fn load_rejects_traversal_path() {
        let mut b = zig_backend();
        let result = b.load("test", "/usr/../etc/passwd");
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(
            err.contains("safety validation"),
            "error should mention safety validation: {err}"
        );
    }

    #[test]
    fn call_function_empty_name_rejected() {
        let b = zig_backend();
        let result = b.call_function("mod", "", &[]);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(
            err.contains("function name is empty"),
            "error should mention empty function name: {err}"
        );
    }

    #[test]
    fn call_function_oversized_name_rejected() {
        let b = zig_backend();
        let long_name = "a".repeat(300);
        let result = b.call_function("mod", &long_name, &[]);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(
            err.contains("function name too long"),
            "error should mention oversized function name: {err}"
        );
    }
}
