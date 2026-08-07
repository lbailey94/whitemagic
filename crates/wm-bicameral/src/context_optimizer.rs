//! Context Window Optimizer — salience-based context packing for LLM calls.
//!
//! Ported from v2's ai/context_optimizer.py.
//! Scores context items by salience (importance, recency, relevance), then
//! greedily fits the highest-value items into a token budget. Prevents the
//! "lost in the middle" problem by placing the most salient items at the
//! start and end of the context window (primacy/recency effect).

use serde::{Deserialize, Serialize};

/// A single item to consider for context packing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextItem {
    /// Unique identifier
    pub id: String,
    /// Text content
    pub content: String,
    /// Source type (e.g. "memory", "session", "tool_result")
    pub source: String,
    /// Importance score (0.0–1.0)
    pub importance: f32,
    /// Recency score (0.0 = old, 1.0 = fresh)
    pub recency: f32,
    /// Relevance to current query (0.0–1.0)
    pub relevance: f32,
    /// Estimated token count (auto-calculated if 0)
    pub tokens: usize,
}

impl ContextItem {
    /// Create a new context item with default scores.
    #[must_use]
    pub fn new(id: impl Into<String>, content: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            content: content.into(),
            source: String::new(),
            importance: 0.5,
            recency: 0.5,
            relevance: 0.5,
            tokens: 0,
        }
    }

    /// Combined salience: weighted blend of importance, recency, relevance.
    #[must_use]
    pub fn salience_score(&self) -> f32 {
        self.importance
            .mul_add(0.3, self.recency.mul_add(0.2, self.relevance * 0.5))
    }

    /// Builder: set source.
    #[must_use]
    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = source.into();
        self
    }

    /// Builder: set importance.
    #[must_use]
    pub const fn with_importance(mut self, importance: f32) -> Self {
        self.importance = importance.clamp(0.0, 1.0);
        self
    }

    /// Builder: set recency.
    #[must_use]
    pub const fn with_recency(mut self, recency: f32) -> Self {
        self.recency = recency.clamp(0.0, 1.0);
        self
    }

    /// Builder: set relevance.
    #[must_use]
    pub const fn with_relevance(mut self, relevance: f32) -> Self {
        self.relevance = relevance.clamp(0.0, 1.0);
        self
    }

    /// Builder: set token count.
    #[must_use]
    pub const fn with_tokens(mut self, tokens: usize) -> Self {
        self.tokens = tokens;
        self
    }
}

/// Result of context packing.
#[derive(Debug, Clone)]
pub struct PackedContext {
    /// Items selected for the context window, ordered for primacy/recency
    pub items: Vec<ContextItem>,
    /// Total tokens used
    pub total_tokens: usize,
    /// Token budget
    pub budget: usize,
    /// Budget utilization (0.0–1.0)
    pub utilization: f32,
    /// Number of items dropped due to budget
    pub dropped_count: usize,
    /// Packing strategy name
    pub strategy: &'static str,
}

/// Rough token estimate: ~4 chars per token for English text.
#[must_use]
pub fn estimate_tokens(text: &str) -> usize {
    std::cmp::max(1, text.len() / 4)
}

/// Context optimizer — packs context items into a token budget.
///
/// Strategy:
/// 1. Score all items by salience (importance × recency × relevance)
/// 2. Sort by salience descending
/// 3. Greedily fit into budget
/// 4. Reorder: highest-salience at START and END (primacy/recency effect)
pub struct ContextOptimizer {
    default_budget: usize,
}

impl Default for ContextOptimizer {
    fn default() -> Self {
        Self {
            default_budget: 8000,
        }
    }
}

impl ContextOptimizer {
    /// Create a new optimizer with a custom default budget.
    #[must_use]
    pub const fn new(default_budget: usize) -> Self {
        Self { default_budget }
    }

    /// Pack items into the token budget.
    ///
    /// If `query` is provided, relevance scores are updated via keyword overlap.
    #[must_use]
    pub fn pack(
        &self,
        mut items: Vec<ContextItem>,
        token_budget: Option<usize>,
        query: Option<&str>,
    ) -> PackedContext {
        let budget = token_budget.unwrap_or(self.default_budget);

        // Auto-estimate tokens if needed
        for item in &mut items {
            if item.tokens == 0 {
                item.tokens = estimate_tokens(&item.content);
            }
        }

        // Score relevance against query if provided
        if let Some(q) = query {
            let q_lower = q.to_lowercase();
            let query_words: std::collections::HashSet<&str> = q_lower.split_whitespace().collect();
            if !query_words.is_empty() {
                for item in &mut items {
                    let c_lower = item.content.to_lowercase();
                    let content_words: std::collections::HashSet<&str> =
                        c_lower.split_whitespace().collect();
                    let overlap = query_words.intersection(&content_words).count();
                    item.relevance = (overlap as f32 / query_words.len().max(1) as f32).min(1.0);
                }
            }
        }

        // Sort by salience descending
        items.sort_by(|a, b| {
            b.salience_score()
                .partial_cmp(&a.salience_score())
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Greedy packing
        let mut selected: Vec<ContextItem> = Vec::new();
        let mut total_tokens = 0usize;
        let mut dropped = 0usize;

        for item in items {
            if total_tokens + item.tokens <= budget {
                total_tokens += item.tokens;
                selected.push(item);
            } else {
                dropped += 1;
            }
        }

        // Primacy-recency reorder: best at start and end
        if selected.len() >= 4 {
            selected = primacy_recency_reorder(selected);
        }

        let utilization = if budget > 0 {
            total_tokens as f32 / budget as f32
        } else {
            0.0
        };

        PackedContext {
            items: selected,
            total_tokens,
            budget,
            utilization,
            dropped_count: dropped,
            strategy: "salience_primacy_recency",
        }
    }

    /// Render packed context into a single string.
    #[must_use]
    pub fn render(packed: &PackedContext, separator: &str) -> String {
        packed
            .items
            .iter()
            .map(|item| item.content.as_str())
            .collect::<Vec<_>>()
            .join(separator)
    }
}

/// Place highest-salience items at start and end of the list.
///
/// Exploits the primacy and recency effects in LLM attention:
/// - Top 25% go to front (primacy)
/// - Next 25% go to back, reversed (recency)
/// - Remaining 50% in middle
fn primacy_recency_reorder(mut items: Vec<ContextItem>) -> Vec<ContextItem> {
    if items.len() <= 2 {
        return items;
    }

    // Re-sort by salience
    items.sort_by(|a, b| {
        b.salience_score()
            .partial_cmp(&a.salience_score())
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    let quarter = std::cmp::max(1, items.len() / 4);
    let mut result = Vec::with_capacity(items.len());

    // Front: top 25%
    let front: Vec<ContextItem> = items.drain(..quarter).collect();
    result.extend(front);

    // Back: next 25% (reversed for recency effect)
    #[allow(clippy::needless_collect)]
    let back: Vec<ContextItem> = items.drain(..quarter).collect();
    result.extend(items);
    result.extend(back.into_iter().rev());

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn estimate_tokens_basic() {
        assert!(estimate_tokens("hello world") > 0);
        assert_eq!(estimate_tokens(""), 1); // min 1
        // ~20 chars → ~5 tokens
        assert_eq!(estimate_tokens("abcdefghijklmnopqrst"), 5);
    }

    #[test]
    fn context_item_salience() {
        let item = ContextItem::new("1", "test")
            .with_importance(1.0)
            .with_recency(1.0)
            .with_relevance(1.0);
        assert!((item.salience_score() - 1.0).abs() < f32::EPSILON);

        let item_low = ContextItem::new("2", "test")
            .with_importance(0.0)
            .with_recency(0.0)
            .with_relevance(0.0);
        assert!((item_low.salience_score() - 0.0).abs() < f32::EPSILON);
    }

    #[test]
    fn pack_fits_all() {
        let opt = ContextOptimizer::default();
        let items = vec![
            ContextItem::new("a", "short").with_tokens(100),
            ContextItem::new("b", "also short").with_tokens(200),
        ];
        let packed = opt.pack(items, Some(1000), None);
        assert_eq!(packed.items.len(), 2);
        assert_eq!(packed.dropped_count, 0);
        assert_eq!(packed.total_tokens, 300);
        assert!((packed.utilization - 0.3).abs() < 0.01);
    }

    #[test]
    fn pack_drops_low_salience() {
        let opt = ContextOptimizer::default();
        let items = vec![
            ContextItem::new("high", "important")
                .with_tokens(800)
                .with_importance(1.0),
            ContextItem::new("low", "trivial")
                .with_tokens(800)
                .with_importance(0.0),
        ];
        let packed = opt.pack(items, Some(1000), None);
        assert_eq!(packed.items.len(), 1);
        assert_eq!(packed.dropped_count, 1);
        assert_eq!(packed.items[0].id, "high");
    }

    #[test]
    fn pack_query_updates_relevance() {
        let opt = ContextOptimizer::default();
        let items = vec![
            ContextItem::new("a", "rust programming code").with_tokens(100),
            ContextItem::new("b", "cooking recipe pasta").with_tokens(100),
        ];
        let packed = opt.pack(items, Some(1000), Some("rust code"));
        // Both fit, but "a" should be first (higher relevance)
        assert_eq!(packed.items[0].id, "a");
    }

    #[test]
    fn pack_auto_estimates_tokens() {
        let opt = ContextOptimizer::default();
        let items = vec![ContextItem::new(
            "a",
            "This is a moderately long piece of text content",
        )];
        let packed = opt.pack(items, Some(10000), None);
        assert!(packed.items[0].tokens > 0);
        assert_eq!(packed.total_tokens, packed.items[0].tokens);
    }

    #[test]
    fn pack_primacy_recency_reorder() {
        let opt = ContextOptimizer::default();
        let mut items: Vec<ContextItem> = Vec::new();
        for i in 0..8 {
            items.push(
                ContextItem::new(format!("item{i}"), format!("content {i}"))
                    .with_tokens(100)
                    .with_importance((i as f32).mul_add(-0.1, 1.0))
                    .with_relevance((i as f32).mul_add(-0.1, 1.0)),
            );
        }
        let packed = opt.pack(items, Some(10000), None);
        assert_eq!(packed.items.len(), 8);
        // First item should be highest salience (item0)
        assert_eq!(packed.items[0].id, "item0");
        // Last item should be from the back section (reversed): item2
        assert_eq!(packed.items[7].id, "item2");
    }

    #[test]
    fn render_produces_string() {
        let opt = ContextOptimizer::default();
        let items = vec![
            ContextItem::new("a", "first").with_tokens(10),
            ContextItem::new("b", "second").with_tokens(10),
        ];
        let packed = opt.pack(items, Some(1000), None);
        let rendered = ContextOptimizer::render(&packed, "\n---\n");
        assert!(rendered.contains("first"));
        assert!(rendered.contains("second"));
    }

    #[test]
    fn pack_empty_items() {
        let opt = ContextOptimizer::default();
        let packed = opt.pack(vec![], Some(1000), None);
        assert_eq!(packed.items.len(), 0);
        assert_eq!(packed.total_tokens, 0);
        assert_eq!(packed.dropped_count, 0);
    }

    #[test]
    fn pack_zero_budget_drops_all() {
        let opt = ContextOptimizer::default();
        let items = vec![ContextItem::new("a", "test").with_tokens(100)];
        let packed = opt.pack(items, Some(0), None);
        assert_eq!(packed.items.len(), 0);
        assert_eq!(packed.dropped_count, 1);
    }
}
