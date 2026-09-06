//! Predictive LRU Cache with Markov Chain Pre-warming.
//!
//! Ported from v2's optimization/predictive_cache.py.
//! Tracks access patterns to predict future accesses, maintaining a
//! rolling window of transitions. When a key is accessed, likely-next
//! keys are pre-warmed for faster retrieval.
//!
//! Target: 60–70% faster access for frequently used memories.

use std::collections::{HashMap, VecDeque};

/// Cache performance statistics.
#[derive(Debug, Clone, Default)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub predictions: u64,
    pub prediction_hits: u64,
    pub evictions: u64,
}

impl CacheStats {
    /// Hit rate (0.0–1.0).
    #[must_use]
    pub fn hit_rate(&self) -> f64 {
        let total = self.hits + self.misses;
        if total == 0 {
            0.0
        } else {
            self.hits as f64 / total as f64
        }
    }

    /// Prediction accuracy (0.0–1.0).
    #[must_use]
    pub fn prediction_accuracy(&self) -> f64 {
        if self.predictions == 0 {
            0.0
        } else {
            self.prediction_hits as f64 / self.predictions as f64
        }
    }
}

/// LRU cache entry.
struct Entry<V> {
    value: V,
    /// Position in the LRU order (higher = more recently used)
    order: u64,
}

/// Predictive LRU cache with Markov chain pre-warming.
///
/// Generic over the value type `V`. Keys are strings.
pub struct PredictiveCache<V> {
    max_size: usize,
    prediction_depth: usize,
    max_history: usize,

    cache: HashMap<String, Entry<V>>,
    lru_counter: u64,

    access_history: VecDeque<String>,
    /// Markov transition counts: access_patterns[a][b] = count of a→b transitions
    access_patterns: HashMap<String, HashMap<String, u64>>,

    /// Keys predicted to be accessed soon
    prewarmed: HashMap<String, bool>,

    pub stats: CacheStats,
}

impl<V: Clone> PredictiveCache<V> {
    /// Create a new predictive cache.
    ///
    /// # Arguments
    /// * `max_size` - Maximum number of cached entries
    /// * `prediction_depth` - How many likely-next keys to pre-warm
    #[must_use]
    pub fn new(max_size: usize, prediction_depth: usize) -> Self {
        Self {
            max_size,
            prediction_depth,
            max_history: 100,
            cache: HashMap::new(),
            lru_counter: 0,
            access_history: VecDeque::with_capacity(100),
            access_patterns: HashMap::new(),
            prewarmed: HashMap::new(),
            stats: CacheStats::default(),
        }
    }

    /// Get a value from the cache.
    ///
    /// Returns `Some(value)` on hit, `None` on miss.
    /// On hit, records the access and predicts likely-next accesses.
    pub fn get(&mut self, key: &str) -> Option<V> {
        // Check if this was a predicted access
        if self.prewarmed.remove(key).is_some() {
            self.stats.prediction_hits += 1;
        }

        let found = self.cache.get(key).map(|e| e.value.clone());

        if let Some(value) = found {
            self.stats.hits += 1;
            self.lru_counter += 1;
            if let Some(entry) = self.cache.get_mut(key) {
                entry.order = self.lru_counter;
            }

            self.record_access(key);
            self.predict_next(key);

            Some(value)
        } else {
            self.stats.misses += 1;
            self.record_access(key);
            None
        }
    }

    /// Set a value in the cache.
    ///
    /// Evicts the least-recently-used entry if over capacity.
    pub fn set(&mut self, key: &str, value: V) {
        self.lru_counter += 1;

        if let Some(entry) = self.cache.get_mut(key) {
            entry.value = value;
            entry.order = self.lru_counter;
            return;
        }

        self.cache.insert(
            key.to_string(),
            Entry {
                value,
                order: self.lru_counter,
            },
        );

        // Evict if over capacity
        if self.cache.len() > self.max_size {
            self.evict_lru();
        }
    }

    /// Manually pre-warm the cache with specific keys using a loader function.
    pub fn prewarm<F>(&mut self, loader: F, keys: &[String])
    where
        F: Fn(&str) -> Option<V>,
    {
        for key in keys {
            if !self.cache.contains_key(key) {
                if let Some(value) = loader(key) {
                    self.set(key, value);
                }
            }
        }
    }

    /// Remove a key from the cache.
    pub fn invalidate(&mut self, key: &str) {
        self.cache.remove(key);
        self.prewarmed.remove(key);
    }

    /// Clear the entire cache and all state.
    pub fn clear(&mut self) {
        self.cache.clear();
        self.prewarmed.clear();
        self.access_history.clear();
        self.access_patterns.clear();
        self.stats = CacheStats::default();
    }

    /// Current number of cached entries.
    #[must_use]
    pub fn len(&self) -> usize {
        self.cache.len()
    }

    /// Whether the cache is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.cache.is_empty()
    }

    /// Get the most likely next accesses given a current key.
    #[must_use]
    pub fn likely_next(&self, current_key: &str, top_n: usize) -> Vec<(String, f64)> {
        match self.access_patterns.get(current_key) {
            None => Vec::new(),
            Some(transitions) => {
                let total: u64 = transitions.values().sum();
                if total == 0 {
                    return Vec::new();
                }
                let mut result: Vec<(String, f64)> = transitions
                    .iter()
                    .map(|(k, &count)| (k.clone(), count as f64 / total as f64))
                    .collect();
                result.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                result.truncate(top_n);
                result
            }
        }
    }

    /// Get the most frequently accessed keys.
    #[must_use]
    pub fn hot_keys(&self, top_n: usize) -> Vec<(String, u64)> {
        let mut counts: HashMap<String, u64> = HashMap::new();
        for key in &self.access_history {
            *counts.entry(key.clone()).or_insert(0) += 1;
        }
        let mut result: Vec<(String, u64)> = counts.into_iter().collect();
        result.sort_by_key(|x| std::cmp::Reverse(x.1));
        result.truncate(top_n);
        result
    }

    fn evict_lru(&mut self) {
        if self.cache.is_empty() {
            return;
        }
        // Find the entry with the lowest order
        let min_key = self
            .cache
            .iter()
            .min_by_key(|(_, e)| e.order)
            .map(|(k, _)| k.clone());

        if let Some(key) = min_key {
            self.cache.remove(&key);
            self.stats.evictions += 1;
        }
    }

    fn record_access(&mut self, key: &str) {
        self.access_history.push_back(key.to_string());
        if self.access_history.len() > self.max_history {
            self.access_history.pop_front();
        }

        // Update Markov transition counts
        if self.access_history.len() >= 2 {
            let prev_key = self
                .access_history
                .get(self.access_history.len() - 2)
                .cloned();
            if let Some(prev) = prev_key {
                *self
                    .access_patterns
                    .entry(prev)
                    .or_default()
                    .entry(key.to_string())
                    .or_insert(0) += 1;
            }
        }
    }

    fn predict_next(&mut self, current_key: &str) {
        let transitions = match self.access_patterns.get(current_key) {
            None => return,
            Some(t) => t.clone(),
        };

        let total: u64 = transitions.values().sum();
        if total == 0 {
            return;
        }

        let mut likely: Vec<(String, f64)> = transitions
            .iter()
            .map(|(k, &count)| (k.clone(), count as f64 / total as f64))
            .collect();
        likely.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        likely.truncate(self.prediction_depth);

        for (next_key, probability) in likely {
            if probability > 0.3 {
                self.prewarmed.insert(next_key, true);
                self.stats.predictions += 1;
            }
        }
    }
}

impl<V: Clone> Default for PredictiveCache<V> {
    fn default() -> Self {
        Self::new(1000, 3)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cache_miss_then_hit() {
        let mut cache: PredictiveCache<String> = PredictiveCache::new(10, 3);
        assert!(cache.get("missing").is_none());
        assert_eq!(cache.stats.misses, 1);

        cache.set("key", "value".to_string());
        assert_eq!(cache.get("key"), Some("value".to_string()));
        assert_eq!(cache.stats.hits, 1);
    }

    #[test]
    fn cache_eviction() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(3, 1);
        cache.set("a", 1);
        cache.set("b", 2);
        cache.set("c", 3);
        cache.set("d", 4); // should evict "a" (least recently used)

        assert_eq!(cache.len(), 3);
        assert!(cache.get("a").is_none());
        assert!(cache.get("d").is_some());
        assert_eq!(cache.stats.evictions, 1);
    }

    #[test]
    fn cache_lru_order_updates_on_get() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(3, 1);
        cache.set("a", 1);
        cache.set("b", 2);
        cache.set("c", 3);

        // Access "a" to make it recently used
        let _ = cache.get("a");
        cache.set("d", 4); // should evict "b" now, not "a"

        assert!(cache.get("a").is_some());
        assert!(cache.get("b").is_none());
    }

    #[test]
    fn cache_markov_prediction() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 3);

        // Build a pattern: a → b → c → a → b → c
        for key in &["a", "b", "c", "a", "b", "c"] {
            cache.set(key, 1);
            let _ = cache.get(key);
        }

        // After accessing "a", "b" should be predicted
        let likely = cache.likely_next("a", 5);
        assert!(!likely.is_empty());
        assert_eq!(likely[0].0, "b");
    }

    #[test]
    fn cache_prediction_hit_tracking() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 3);

        // Build pattern: a → b
        cache.set("a", 1);
        let _ = cache.get("a");
        cache.set("b", 2);
        let _ = cache.get("b");

        // Access "a" again — should predict "b"
        let _ = cache.get("a");
        assert!(cache.stats.predictions > 0);

        // Now access "b" — should count as prediction hit
        let _ = cache.get("b");
        assert!(cache.stats.prediction_hits > 0);
    }

    #[test]
    fn cache_hot_keys() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 1);
        for _ in 0..5 {
            let _ = cache.get("hot");
        }
        for _ in 0..2 {
            let _ = cache.get("warm");
        }

        let hot = cache.hot_keys(10);
        assert_eq!(hot[0].0, "hot");
        assert!(hot[0].1 > hot[1].1);
    }

    #[test]
    fn cache_invalidate() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 1);
        cache.set("a", 1);
        cache.invalidate("a");
        assert!(cache.get("a").is_none());
    }

    #[test]
    fn cache_clear() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 1);
        cache.set("a", 1);
        cache.set("b", 2);
        let _ = cache.get("a");
        cache.clear();
        assert!(cache.is_empty());
        assert_eq!(cache.stats.hits, 0);
    }

    #[test]
    fn cache_prewarm() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 1);
        let loader = |key: &str| -> Option<i32> { i32::try_from(key.len()).ok() };
        cache.prewarm(loader, &["alpha".to_string(), "beta".to_string()]);
        assert_eq!(cache.get("alpha"), Some(5));
        assert_eq!(cache.get("beta"), Some(4));
    }

    #[test]
    fn cache_stats_hit_rate() {
        let mut cache: PredictiveCache<i32> = PredictiveCache::new(10, 1);
        cache.set("a", 1);
        let _ = cache.get("a"); // hit
        let _ = cache.get("a"); // hit
        let _ = cache.get("b"); // miss

        assert!((cache.stats.hit_rate() - 2.0 / 3.0).abs() < 0.01);
    }

    #[test]
    fn cache_likely_next_empty_for_unknown() {
        let cache: PredictiveCache<i32> = PredictiveCache::new(10, 3);
        assert!(cache.likely_next("unknown", 5).is_empty());
    }
}
