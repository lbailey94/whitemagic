//! Predictive Coding — prediction error computation for memory writes.
//!
//! Based on PAM (arXiv, Feb 2026): JEPA-style predictor trained on temporal
//! co-occurrence. When a new memory arrives, the system predicts what it
//! should contain based on recent context. The prediction error (surprise)
//! determines whether the memory is worth storing and how much consolidation
//! priority it receives.

use std::collections::HashMap;

pub struct PredictiveCoder {
    /// Context window: recent memory embeddings (simple bag-of-words vectors)
    context_window: Vec<Vec<f64>>,
    /// Prediction model: simple linear weights
    weights: HashMap<String, f64>,
    /// Window size for context
    window_size: usize,
    /// Vector dimensionality
    dim: usize,
    /// Statistics
    pub total_predictions: u64,
    total_surprise: f64,
}

impl PredictiveCoder {
    pub fn new(window_size: usize, dim: usize) -> Self {
        Self {
            context_window: Vec::with_capacity(window_size),
            weights: HashMap::new(),
            window_size,
            dim,
            total_predictions: 0,
            total_surprise: 0.0,
        }
    }

    /// Add a memory embedding to the context window
    pub fn observe(&mut self, embedding: Vec<f64>) {
        if self.context_window.len() >= self.window_size {
            self.context_window.remove(0);
        }
        self.context_window.push(embedding);
    }

    /// Predict the next embedding from context (simple moving average)
    pub fn predict(&self) -> Vec<f64> {
        if self.context_window.is_empty() {
            return vec![0.0; self.dim];
        }
        let n = self.context_window.len() as f64;
        let mut predicted = vec![0.0; self.dim];
        for emb in &self.context_window {
            for (i, &v) in emb.iter().enumerate() {
                if i < self.dim {
                    predicted[i] += v / n;
                }
            }
        }
        predicted
    }

    /// Compute prediction error (surprise) between prediction and actual
    pub fn prediction_error(&mut self, actual: &[f64]) -> f64 {
        self.total_predictions += 1;
        let predicted = self.predict();
        let mut error = 0.0;
        for i in 0..actual.len().min(predicted.len()) {
            let diff = actual[i] - predicted[i];
            error += diff * diff;
        }
        let rmse = error.sqrt();
        self.total_surprise += rmse;
        rmse
    }

    /// Process a new memory: observe + compute surprise
    pub fn process(&mut self, embedding: Vec<f64>) -> f64 {
        let surprise = self.prediction_error(&embedding);
        self.observe(embedding);
        surprise
    }

    /// Get novelty score (normalized surprise)
    pub fn novelty_score(&self, surprise: f64) -> f64 {
        if self.total_predictions == 0 {
            return 0.5;
        }
        let avg_surprise = self.total_surprise / self.total_predictions as f64;
        if avg_surprise < 1e-10 {
            return 0.5;
        }
        // Normalize: surprise relative to average
        let ratio = surprise / avg_surprise;
        // Sigmoid: 0.5 + 0.5 * (ratio - 1) / (1 + |ratio - 1|)
        let adjusted = (ratio - 1.0) / (1.0 + (ratio - 1.0).abs());
        0.5 + 0.5 * adjusted
    }

    pub fn stats(&self) -> HashMap<String, f64> {
        let mut s = HashMap::new();
        s.insert("total_predictions".to_string(), self.total_predictions as f64);
        s.insert("avg_surprise".to_string(), 
            if self.total_predictions > 0 { self.total_surprise / self.total_predictions as f64 } else { 0.0 });
        s.insert("window_size".to_string(), self.window_size as f64);
        s.insert("context_length".to_string(), self.context_window.len() as f64);
        s
    }

    pub fn reset(&mut self) {
        self.context_window.clear();
        self.total_predictions = 0;
        self.total_surprise = 0.0;
    }
}

impl Default for PredictiveCoder {
    fn default() -> Self {
        Self::new(5, 128)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_predict() {
        let coder = PredictiveCoder::new(5, 4);
        let pred = coder.predict();
        assert_eq!(pred, vec![0.0; 4]);
    }

    #[test]
    fn test_observe_and_predict() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        coder.observe(vec![0.0, 1.0, 0.0]);
        let pred = coder.predict();
        assert!((pred[0] - 0.5).abs() < 0.01);
        assert!((pred[1] - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_prediction_error_zero_for_matching() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 1.0, 1.0]);
        let error = coder.prediction_error(&[1.0, 1.0, 1.0]);
        assert!(error < 0.01);
    }

    #[test]
    fn test_prediction_error_nonzero_for_different() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        let error = coder.prediction_error(&[0.0, 1.0, 0.0]);
        assert!(error > 0.5);
    }

    #[test]
    fn test_window_eviction() {
        let mut coder = PredictiveCoder::new(2, 2);
        coder.observe(vec![1.0, 0.0]);
        coder.observe(vec![0.0, 1.0]);
        coder.observe(vec![1.0, 1.0]);
        // Window should only have last 2
        let pred = coder.predict();
        assert!((pred[0] - 0.5).abs() < 0.01);
        assert!((pred[1] - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_novelty_score() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        let e1 = coder.prediction_error(&[1.0, 0.0, 0.0]);
        let n1 = coder.novelty_score(e1);
        assert!(n1 >= 0.0 && n1 <= 1.0);
    }
}
