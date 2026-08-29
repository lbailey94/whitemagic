//! Polyglot backend trait — defines the interface for all language backends.
//!
//! Each language backend (Julia, Haskell, Zig, Koka) implements this trait
//! to provide a unified interface for cross-language function calls.

use crate::value::{PolyglotError, PolyglotValue};

/// A polyglot function signature: takes a vector of arguments, returns a value.
pub type PolyglotFn =
    dyn Fn(&[PolyglotValue]) -> Result<PolyglotValue, PolyglotError> + Send + Sync;

/// The backend trait — each language runtime implements this.
pub trait PolyglotBackend: Send + Sync {
    /// Backend name (e.g., "julia", "haskell", "zig", "koka").
    fn name(&self) -> &str;

    /// Whether the backend is initialized and ready.
    fn is_initialized(&self) -> bool;

    /// Initialize the language runtime.
    ///
    /// # Errors
    /// Returns `PolyglotError::InitFailed` if initialization fails.
    fn init(&mut self) -> Result<(), PolyglotError>;

    /// Evaluate a code string in the target language.
    ///
    /// # Errors
    /// Returns `PolyglotError::CallFailed` if evaluation fails.
    fn eval(&self, code: &str) -> Result<PolyglotValue, PolyglotError>;

    /// Call a function by name with arguments.
    ///
    /// # Errors
    /// Returns `PolyglotError::FunctionNotFound` if the function doesn't exist,
    /// or `PolyglotError::CallFailed` if the call fails.
    fn call_function(
        &self,
        module: &str,
        function: &str,
        args: &[PolyglotValue],
    ) -> Result<PolyglotValue, PolyglotError>;

    /// Load a module/source file.
    ///
    /// # Errors
    /// Returns `PolyglotError::ModuleNotFound` if the module can't be loaded.
    fn load_module(&self, path: &str) -> Result<(), PolyglotError>;

    /// Shutdown the runtime cleanly.
    fn shutdown(&mut self);
}

/// Registry of available polyglot backends.
pub struct PolyglotRegistry {
    backends: Vec<Box<dyn PolyglotBackend>>,
}

impl PolyglotRegistry {
    /// Create a new empty registry.
    #[must_use]
    pub fn new() -> Self {
        Self {
            backends: Vec::new(),
        }
    }

    /// Register a backend.
    pub fn register(&mut self, backend: Box<dyn PolyglotBackend>) {
        self.backends.push(backend);
    }

    /// Get a backend by name.
    #[must_use]
    pub fn get(&self, name: &str) -> Option<&dyn PolyglotBackend> {
        self.backends
            .iter()
            .find(|b| b.name() == name)
            .map(|b| b.as_ref())
    }

    /// Get a mutable backend by name.
    pub fn get_mut(&mut self, name: &str) -> Option<&mut (dyn PolyglotBackend + 'static)> {
        self.backends
            .iter_mut()
            .find(|b| b.name() == name)
            .map(|b| b.as_mut())
    }

    /// List all registered backend names.
    #[must_use]
    pub fn backend_names(&self) -> Vec<&str> {
        self.backends.iter().map(|b| b.name()).collect()
    }

    /// Number of registered backends.
    #[must_use]
    pub fn len(&self) -> usize {
        self.backends.len()
    }

    /// Whether the registry is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.backends.is_empty()
    }

    /// Initialize all registered backends.
    ///
    /// # Errors
    /// Returns the first error encountered.
    pub fn init_all(&mut self) -> Result<(), PolyglotError> {
        for b in &mut self.backends {
            if !b.is_initialized() {
                b.init()?;
            }
        }
        Ok(())
    }

    /// Shutdown all backends.
    pub fn shutdown_all(&mut self) {
        for b in &mut self.backends {
            b.shutdown();
        }
    }

    /// Call a function on a specific backend.
    ///
    /// # Errors
    /// Returns `PolyglotError::BackendUnavailable` if the backend isn't found.
    pub fn call(
        &self,
        backend: &str,
        module: &str,
        function: &str,
        args: &[PolyglotValue],
    ) -> Result<PolyglotValue, PolyglotError> {
        let b = self
            .get(backend)
            .ok_or_else(|| PolyglotError::BackendUnavailable(backend.into()))?;
        b.call_function(module, function, args)
    }
}

impl Default for PolyglotRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Mock backend for testing the registry.
    struct MockBackend {
        name: String,
        initialized: bool,
    }

    impl MockBackend {
        fn new(name: &str) -> Self {
            Self {
                name: name.into(),
                initialized: false,
            }
        }
    }

    impl PolyglotBackend for MockBackend {
        fn name(&self) -> &str {
            &self.name
        }

        fn is_initialized(&self) -> bool {
            self.initialized
        }

        fn init(&mut self) -> Result<(), PolyglotError> {
            self.initialized = true;
            Ok(())
        }

        fn eval(&self, _code: &str) -> Result<PolyglotValue, PolyglotError> {
            Ok(PolyglotValue::null())
        }

        fn call_function(
            &self,
            _module: &str,
            function: &str,
            args: &[PolyglotValue],
        ) -> Result<PolyglotValue, PolyglotError> {
            if function == "echo" && !args.is_empty() {
                Ok(args[0].clone())
            } else {
                Ok(PolyglotValue::null())
            }
        }

        fn load_module(&self, _path: &str) -> Result<(), PolyglotError> {
            Ok(())
        }

        fn shutdown(&mut self) {
            self.initialized = false;
        }
    }

    #[test]
    fn registry_empty() {
        let reg = PolyglotRegistry::new();
        assert!(reg.is_empty());
        assert_eq!(reg.len(), 0);
    }

    #[test]
    fn registry_register_and_get() {
        let mut reg = PolyglotRegistry::new();
        reg.register(Box::new(MockBackend::new("mock")));
        assert_eq!(reg.len(), 1);
        assert!(reg.get("mock").is_some());
        assert!(reg.get("nonexistent").is_none());
    }

    #[test]
    fn registry_backend_names() {
        let mut reg = PolyglotRegistry::new();
        reg.register(Box::new(MockBackend::new("a")));
        reg.register(Box::new(MockBackend::new("b")));
        assert_eq!(reg.backend_names(), vec!["a", "b"]);
    }

    #[test]
    fn registry_init_all() {
        let mut reg = PolyglotRegistry::new();
        reg.register(Box::new(MockBackend::new("mock")));
        assert!(!reg.get("mock").unwrap().is_initialized());
        reg.init_all().unwrap();
        assert!(reg.get("mock").unwrap().is_initialized());
    }

    #[test]
    fn registry_shutdown_all() {
        let mut reg = PolyglotRegistry::new();
        reg.register(Box::new(MockBackend::new("mock")));
        reg.init_all().unwrap();
        reg.shutdown_all();
        assert!(!reg.get("mock").unwrap().is_initialized());
    }

    #[test]
    fn registry_call() {
        let mut reg = PolyglotRegistry::new();
        reg.register(Box::new(MockBackend::new("mock")));
        let result = reg
            .call("mock", "mod", "echo", &[PolyglotValue::int(42)])
            .unwrap();
        assert_eq!(result, PolyglotValue::int(42));
    }

    #[test]
    fn registry_call_missing_backend() {
        let reg = PolyglotRegistry::new();
        let result = reg.call("missing", "mod", "fn", &[]);
        assert!(result.is_err());
    }

    #[test]
    fn registry_get_mut() {
        let mut reg = PolyglotRegistry::new();
        reg.register(Box::new(MockBackend::new("mock")));
        let b = reg.get_mut("mock").unwrap();
        b.init().unwrap();
        assert!(b.is_initialized());
    }
}
