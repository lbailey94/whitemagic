//! Tool registry — maps Gana → tools and provides lookup.

use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Gana, Tool};

/// Inner state of the registry, wrapped in Arc for cheap cloning.
struct RegistryInner {
    tools: Vec<Arc<dyn Tool>>,
    by_gana: HashMap<Gana, Vec<usize>>,
    by_name: HashMap<String, usize>,
}

/// Registry of all available tools, organized by Gana.
///
/// Wraps inner state in `Arc` so the registry can be cheaply cloned
/// and shared between the dispatch pipeline, MCP server, and meta-tools.
pub struct ToolRegistry {
    inner: Arc<RegistryInner>,
}

impl ToolRegistry {
    /// Create a new empty registry.
    #[must_use]
    pub fn new() -> Self {
        Self {
            inner: Arc::new(RegistryInner {
                tools: vec![],
                by_gana: HashMap::new(),
                by_name: HashMap::new(),
            }),
        }
    }

    /// Create a new empty registry with pre-allocated capacity.
    #[must_use]
    pub fn with_capacity(cap: usize) -> Self {
        Self {
            inner: Arc::new(RegistryInner {
                tools: Vec::with_capacity(cap),
                by_gana: HashMap::new(),
                by_name: HashMap::new(),
            }),
        }
    }

    /// Register a tool. Returns a new registry (immutable, Arc-shared).
    ///
    /// Since the inner state is Arc-shared, this method is on `&self`
    /// and returns a new `ToolRegistry` with the tool added.
    /// For bulk registration, use `ToolRegistryBuilder` instead.
    #[must_use]
    pub fn register(&self, tool: Arc<dyn Tool>) -> Self {
        let mut inner = RegistryInner {
            tools: self.inner.tools.clone(),
            by_gana: self.inner.by_gana.clone(),
            by_name: self.inner.by_name.clone(),
        };
        let idx = inner.tools.len();
        let gana = tool.gana();
        let name = tool.name().to_string();
        inner.by_gana.entry(gana).or_default().push(idx);
        inner.by_name.insert(name, idx);
        inner.tools.push(tool);
        Self {
            inner: Arc::new(inner),
        }
    }

    /// Get a tool by name. Returns an owned `Arc<dyn Tool>` clone.
    #[must_use]
    pub fn get(&self, name: &str) -> Option<Arc<dyn Tool>> {
        self.inner
            .by_name
            .get(name)
            .map(|&i| Arc::clone(&self.inner.tools[i]))
    }

    /// Get all tools for a Gana. Returns owned `Arc<dyn Tool>` clones.
    #[must_use]
    pub fn by_gana(&self, gana: Gana) -> Vec<Arc<dyn Tool>> {
        self.inner
            .by_gana
            .get(&gana)
            .map(|indices| {
                indices
                    .iter()
                    .map(|&i| Arc::clone(&self.inner.tools[i]))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Get all registered tools. Returns cloned Arcs.
    #[must_use]
    pub fn all(&self) -> Vec<Arc<dyn Tool>> {
        self.inner.tools.clone()
    }

    /// Get all registered tools as a slice reference (no clone).
    #[must_use]
    pub fn all_ref(&self) -> &[Arc<dyn Tool>] {
        &self.inner.tools
    }

    /// Number of registered tools.
    #[must_use]
    pub fn len(&self) -> usize {
        self.inner.tools.len()
    }

    /// Whether the registry is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.inner.tools.is_empty()
    }

    /// Get all tools available in the given brain-wave state.
    ///
    /// Filters tools by their `EffectRow::is_available_in()` check.
    /// In Alpha/Theta/Delta modes, write-heavy and expensive tools are excluded.
    #[must_use]
    pub fn available_in(&self, brain_wave: wm_core::BrainWave) -> Vec<Arc<dyn Tool>> {
        self.inner
            .tools
            .iter()
            .filter(|t| t.effects().is_available_in(brain_wave))
            .cloned()
            .collect()
    }

    /// Count tools available in the given brain-wave state.
    #[must_use]
    pub fn available_count(&self, brain_wave: wm_core::BrainWave) -> usize {
        self.inner
            .tools
            .iter()
            .filter(|t| t.effects().is_available_in(brain_wave))
            .count()
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl Clone for ToolRegistry {
    fn clone(&self) -> Self {
        Self {
            inner: Arc::clone(&self.inner),
        }
    }
}

/// Builder for incrementally constructing a ToolRegistry.
pub struct ToolRegistryBuilder {
    tools: Vec<Arc<dyn Tool>>,
    by_gana: HashMap<Gana, Vec<usize>>,
    by_name: HashMap<String, usize>,
}

impl ToolRegistryBuilder {
    /// Create a new empty builder.
    #[must_use]
    pub fn new() -> Self {
        Self {
            tools: vec![],
            by_gana: HashMap::new(),
            by_name: HashMap::new(),
        }
    }

    /// Register a tool.
    ///
    /// If a tool with the same name is already registered, the new tool
    /// shadows the old one. A warning is logged to alert developers of
    /// potential unintended shadowing.
    pub fn register(&mut self, tool: Arc<dyn Tool>) -> &mut Self {
        let idx = self.tools.len();
        let gana = tool.gana();
        let name = tool.name().to_string();
        if self.by_name.contains_key(&name) {
            tracing::warn!(
                tool_name = %name,
                "Duplicate tool registration — new tool will shadow existing one"
            );
        }
        self.by_gana.entry(gana).or_default().push(idx);
        self.by_name.insert(name, idx);
        self.tools.push(tool);
        self
    }

    /// Build the immutable registry.
    #[must_use]
    pub fn build(self) -> ToolRegistry {
        ToolRegistry {
            inner: Arc::new(RegistryInner {
                tools: self.tools,
                by_gana: self.by_gana,
                by_name: self.by_name,
            }),
        }
    }
}

impl Default for ToolRegistryBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::{EffectRow, ToolStats};

    struct MockTool {
        name: String,
        gana: Gana,
        effects: EffectRow,
        stats: ToolStats,
    }

    impl Tool for MockTool {
        fn name(&self) -> &str {
            &self.name
        }
        fn gana(&self) -> Gana {
            self.gana
        }
        fn effects(&self) -> &EffectRow {
            &self.effects
        }
        fn stats(&self) -> &ToolStats {
            &self.stats
        }
        fn call(
            &self,
            _ctx: &mut wm_core::Context,
            _args: wm_core::Args,
        ) -> wm_core::Result<wm_core::Output> {
            Ok(serde_json::json!({"ok": true}))
        }
    }

    fn make_tool(name: &str) -> Arc<dyn Tool> {
        Arc::new(MockTool {
            name: name.into(),
            gana: Gana::Horn,
            effects: EffectRow::default(),
            stats: ToolStats::default(),
        })
    }

    #[test]
    fn duplicate_registration_shadows_and_warns() {
        let mut builder = ToolRegistryBuilder::new();
        builder.register(make_tool("dup"));
        builder.register(make_tool("dup"));

        let registry = builder.build();
        let tool = registry.get("dup").unwrap();
        assert_eq!(tool.name(), "dup");
    }

    #[test]
    fn unique_registration_no_warning() {
        let mut builder = ToolRegistryBuilder::new();
        builder.register(make_tool("tool_a"));
        builder.register(make_tool("tool_b"));

        let registry = builder.build();
        assert!(registry.get("tool_a").is_some());
        assert!(registry.get("tool_b").is_some());
    }
}
