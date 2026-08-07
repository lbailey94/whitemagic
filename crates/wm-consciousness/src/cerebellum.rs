//! Cerebellar Forward Model — predictive motor control and error correction.
//!
//! Implements a computational framework inspired by the cerebellum's role
//! in motor learning and predictive control. The cerebellum learns forward
//! models that predict the sensory consequences of motor commands, enabling:
//!
//! - **Prediction**: Given a motor command, predict the sensory outcome
//! - **Error detection**: Compare predicted vs actual sensory feedback
//! - **Adaptive learning**: Update the forward model based on prediction errors
//! - **Reflex suppression**: Dampen reflexes when self-generated sensory
//!   consequences match predictions (sensory attenuation)
//!
//! Architecture (based on Wolpert & Miall 1996, Nguyen et al. 2025):
//!   Motor Command → Efference Copy → Forward Model → Predicted State
//!                                                         ↓
//!   Actual State ← Sensor Feedback ← [Environment]
//!         ↓
//!   Comparator → Sensory Prediction Error → Learning Update
//!
//! The forward model is implemented as a simple linear model with
//! adaptable weights, suitable for framework extension to neural networks
//! or other function approximators.

#![forbid(unsafe_code)]

use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

// ── Forward Model ──────────────────────────────────────────────────────

/// A forward model that predicts the next state given the current state
/// and a motor command.
///
/// Implemented as a simple linear model:
///   predicted_next = A * current_state + B * motor_command + bias
///
/// This is intentionally simple — the framework is designed to be extended
/// with more complex models (neural networks, etc.) via the `ForwardModel`
/// trait.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinearForwardModel {
    /// State transition matrix (A), shape [state_dim x state_dim].
    /// Stored row-major.
    pub matrix_a: Vec<Vec<f64>>,
    /// Input matrix (B), shape [state_dim x command_dim].
    pub matrix_b: Vec<Vec<f64>>,
    /// Bias vector, shape [state_dim].
    pub bias: Vec<f64>,
    /// Learning rate for weight updates.
    pub learning_rate: f64,
}

impl LinearForwardModel {
    /// Create a new linear forward model with given dimensions.
    /// Weights are initialized to identity (A) and zero (B, bias).
    #[must_use]
    pub fn new(state_dim: usize, command_dim: usize) -> Self {
        let matrix_a = (0..state_dim)
            .map(|i| {
                (0..state_dim)
                    .map(|j| if i == j { 1.0 } else { 0.0 })
                    .collect()
            })
            .collect();
        let matrix_b = (0..state_dim)
            .map(|_| (0..command_dim).map(|_| 0.0).collect())
            .collect();
        let bias = vec![0.0; state_dim];

        Self {
            matrix_a,
            matrix_b,
            bias,
            learning_rate: 0.01,
        }
    }

    /// Predict the next state given current state and motor command.
    #[must_use]
    pub fn predict(&self, state: &[f64], command: &[f64]) -> Vec<f64> {
        let state_dim = self.bias.len();
        let mut result = vec![0.0; state_dim];

        // A * state + B * command + bias
        for (i, result_i) in result.iter_mut().enumerate() {
            for (j, &s) in state.iter().enumerate().take(state_dim) {
                *result_i += self.matrix_a[i][j] * s;
            }
            for (j, &c) in command.iter().enumerate().take(self.matrix_b[i].len()) {
                *result_i += self.matrix_b[i][j] * c;
            }
            *result_i += self.bias[i];
        }

        result
    }

    /// Update the model based on prediction error.
    /// `state` = actual previous state, `command` = command sent,
    /// `actual_next` = actual next state observed.
    pub fn learn(&mut self, state: &[f64], command: &[f64], actual_next: &[f64]) -> f64 {
        let predicted = self.predict(state, command);
        let state_dim = self.bias.len();

        // Compute error
        let mut error_vec = vec![0.0; state_dim];
        let mut total_error = 0.0;
        for (i, err) in error_vec
            .iter_mut()
            .enumerate()
            .take(state_dim.min(actual_next.len()))
        {
            *err = actual_next[i] - predicted[i];
            total_error += *err * *err;
        }
        let mse = total_error / f64::from(u32::try_from(state_dim).unwrap_or(1));

        // Gradient descent update
        // dA[i][j] = lr * error[i] * state[j]
        for (i, row_a) in self.matrix_a.iter_mut().enumerate().take(state_dim) {
            for (j, &s) in state.iter().enumerate().take(state_dim) {
                row_a[j] += self.learning_rate * error_vec[i] * s;
            }
        }

        // dB[i][j] = lr * error[i] * command[j]
        for (i, row_b) in self.matrix_b.iter_mut().enumerate().take(state_dim) {
            for (j, &c) in command.iter().enumerate().take(row_b.len()) {
                row_b[j] += self.learning_rate * error_vec[i] * c;
            }
        }

        // dbias[i] = lr * error[i]
        for (i, b) in self.bias.iter_mut().enumerate().take(state_dim) {
            *b += self.learning_rate * error_vec[i];
        }

        mse
    }

    /// Set the learning rate.
    #[must_use]
    pub const fn with_learning_rate(mut self, lr: f64) -> Self {
        self.learning_rate = lr;
        self
    }

    /// State dimension.
    #[must_use]
    pub fn state_dim(&self) -> usize {
        self.bias.len()
    }

    /// Command dimension.
    #[must_use]
    pub fn command_dim(&self) -> usize {
        self.matrix_b.first().map_or(0, Vec::len)
    }
}

// ── Prediction Error ───────────────────────────────────────────────────

/// Result of comparing a prediction to actual sensory feedback.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionError {
    /// Predicted state.
    pub predicted: Vec<f64>,
    /// Actual state from sensors.
    pub actual: Vec<f64>,
    /// Element-wise error (actual - predicted).
    pub error: Vec<f64>,
    /// Mean squared error.
    pub mse: f64,
    /// Whether the error exceeds the surprise threshold.
    pub is_surprising: bool,
}

impl PredictionError {
    /// Compute prediction error between predicted and actual states.
    #[must_use]
    pub fn compute(predicted: &[f64], actual: &[f64], surprise_threshold: f64) -> Self {
        let error: Vec<f64> = (0..predicted.len().min(actual.len()))
            .map(|i| actual[i] - predicted[i])
            .collect();

        let mse = if error.is_empty() {
            0.0
        } else {
            error.iter().map(|e| e * e).sum::<f64>()
                / f64::from(u32::try_from(error.len()).unwrap_or(1))
        };

        Self {
            predicted: predicted.to_vec(),
            actual: actual.to_vec(),
            error,
            mse,
            is_surprising: mse > surprise_threshold,
        }
    }

    /// Magnitude of the error vector (L2 norm).
    #[must_use]
    pub fn magnitude(&self) -> f64 {
        self.error.iter().map(|e| e * e).sum::<f64>().sqrt()
    }
}

// ── Cerebellar Controller ──────────────────────────────────────────────

/// The cerebellar controller integrates a forward model with error
/// detection and adaptive learning.
///
/// It maintains:
/// - A forward model for prediction
/// - A history of recent predictions and errors
/// - A surprise threshold for detecting unexpected outcomes
/// - Sensory attenuation (dampening reflexes for self-generated actions)
pub struct CerebellarController {
    /// The forward model.
    pub model: LinearForwardModel,
    /// Threshold for flagging prediction errors as surprising.
    pub surprise_threshold: f64,
    /// Recent prediction errors (ring buffer).
    error_history: VecDeque<PredictionError>,
    /// Max error history size.
    max_history: usize,
    /// Total predictions made.
    predictions: u64,
    /// Total learning updates.
    learning_updates: u64,
    /// Running average MSE.
    avg_mse: f64,
    /// Sensory attenuation factor (0.0 = full reflex, 1.0 = full attenuation).
    attenuation: f64,
}

impl CerebellarController {
    /// Create a new cerebellar controller.
    #[must_use]
    pub fn new(state_dim: usize, command_dim: usize) -> Self {
        Self {
            model: LinearForwardModel::new(state_dim, command_dim),
            surprise_threshold: 0.1,
            error_history: VecDeque::with_capacity(64),
            max_history: 64,
            predictions: 0,
            learning_updates: 0,
            avg_mse: 0.0,
            attenuation: 0.0,
        }
    }

    /// Set the surprise threshold.
    #[must_use]
    pub const fn with_surprise_threshold(mut self, threshold: f64) -> Self {
        self.surprise_threshold = threshold;
        self
    }

    /// Set the learning rate.
    #[must_use]
    pub const fn with_learning_rate(mut self, lr: f64) -> Self {
        self.model.learning_rate = lr;
        self
    }

    /// Set the history capacity.
    #[must_use]
    pub fn with_history_size(mut self, size: usize) -> Self {
        self.max_history = size;
        self.error_history = VecDeque::with_capacity(size);
        self
    }

    /// Predict the next state given current state and motor command.
    pub fn predict(&mut self, state: &[f64], command: &[f64]) -> Vec<f64> {
        self.predictions += 1;
        self.model.predict(state, command)
    }

    /// Process actual sensory feedback: compute error, learn, and update.
    pub fn process_feedback(
        &mut self,
        state: &[f64],
        command: &[f64],
        actual_next: &[f64],
    ) -> PredictionError {
        let predicted = self.model.predict(state, command);
        let error = PredictionError::compute(&predicted, actual_next, self.surprise_threshold);

        // Learn from the error
        let mse = self.model.learn(state, command, actual_next);
        self.learning_updates += 1;

        // Update running average MSE
        let n = f64::from(u32::try_from(self.learning_updates).unwrap_or(1));
        self.avg_mse = self.avg_mse * (n - 1.0) / n + mse / n;

        // Update sensory attenuation: if prediction was good, increase attenuation
        if error.is_surprising {
            self.attenuation = (self.attenuation - 0.1).max(0.0);
        } else {
            self.attenuation = (self.attenuation + 0.01).min(1.0);
        }

        // Store in history
        self.error_history.push_back(error.clone());
        if self.error_history.len() > self.max_history {
            self.error_history.pop_front();
        }

        error
    }

    /// Current sensory attenuation factor.
    /// 0.0 = full reflex sensitivity, 1.0 = full attenuation (self-generated).
    #[must_use]
    pub const fn attenuation(&self) -> f64 {
        self.attenuation
    }

    /// Running average MSE.
    #[must_use]
    pub const fn avg_mse(&self) -> f64 {
        self.avg_mse
    }

    /// Total predictions made.
    #[must_use]
    pub const fn predictions(&self) -> u64 {
        self.predictions
    }

    /// Total learning updates.
    #[must_use]
    pub const fn learning_updates(&self) -> u64 {
        self.learning_updates
    }

    /// Recent error history.
    #[must_use]
    pub fn error_history(&self) -> Vec<&PredictionError> {
        self.error_history.iter().collect()
    }

    /// Whether the system is well-calibrated (low average error).
    #[must_use]
    pub fn is_calibrated(&self) -> bool {
        self.learning_updates > 10 && self.avg_mse < self.surprise_threshold
    }
}

impl Default for CerebellarController {
    fn default() -> Self {
        Self::new(3, 2)
    }
}

// ── Motor Timing ───────────────────────────────────────────────────────

/// Motor timing profile for a planned action.
///
/// The cerebellum is critical for precise motor timing — coordinating
/// sequences of motor commands with correct temporal relationships.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MotorTiming {
    /// Sequence of motor commands.
    pub commands: Vec<Vec<f64>>,
    /// Time offsets for each command (seconds from start).
    pub time_offsets: Vec<f64>,
    /// Total duration of the motor sequence (seconds).
    pub total_duration: f64,
}

impl MotorTiming {
    /// Create a new motor timing plan.
    #[must_use]
    pub const fn new(commands: Vec<Vec<f64>>, time_offsets: Vec<f64>, total_duration: f64) -> Self {
        Self {
            commands,
            time_offsets,
            total_duration,
        }
    }

    /// Get the command that should be executed at time `t` (seconds from start).
    /// Returns `None` if `t` is outside the sequence duration.
    #[must_use]
    pub fn command_at_time(&self, t: f64) -> Option<&Vec<f64>> {
        if t < 0.0 || t > self.total_duration {
            return None;
        }
        // Find the latest time_offset <= t
        let mut best_idx: Option<usize> = None;
        for (i, &offset) in self.time_offsets.iter().enumerate() {
            if offset <= t {
                best_idx = Some(i);
            } else {
                break;
            }
        }
        best_idx.and_then(|i| self.commands.get(i))
    }

    /// Number of commands in the sequence.
    #[must_use]
    pub fn command_count(&self) -> usize {
        self.commands.len()
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn forward_model_new() {
        let m = LinearForwardModel::new(3, 2);
        assert_eq!(m.state_dim(), 3);
        assert_eq!(m.command_dim(), 2);
        // A should be identity
        assert!((m.matrix_a[0][0] - 1.0).abs() < f64::EPSILON);
        assert!((m.matrix_a[0][1] - 0.0).abs() < f64::EPSILON);
        // B should be zero
        assert!((m.matrix_b[0][0] - 0.0).abs() < f64::EPSILON);
    }

    #[test]
    fn forward_model_predict_identity() {
        let m = LinearForwardModel::new(3, 1);
        let state = vec![1.0, 2.0, 3.0];
        let command = vec![0.5];
        let predicted = m.predict(&state, &command);
        // With identity A and zero B, predicted = state
        assert!((predicted[0] - 1.0).abs() < 1e-10);
        assert!((predicted[1] - 2.0).abs() < 1e-10);
        assert!((predicted[2] - 3.0).abs() < 1e-10);
    }

    #[test]
    fn forward_model_learn_reduces_error() {
        let mut m = LinearForwardModel::new(2, 1).with_learning_rate(0.1);
        let state = vec![1.0, 0.0];
        let command = vec![1.0];
        let actual = vec![1.0, 1.0]; // B should learn to map command→[0, 1]

        // Before learning, prediction is [1, 0] (identity)
        let pred0 = m.predict(&state, &command);
        assert!((pred0[1] - 0.0).abs() < 1e-10);

        // Learn
        let _mse1 = m.learn(&state, &command, &actual);

        // After learning, prediction should be closer to [1, 1]
        let pred1 = m.predict(&state, &command);
        assert!(pred1[1] > 0.0);

        // Learn more
        for _ in 0..100 {
            m.learn(&state, &command, &actual);
        }
        let pred_final = m.predict(&state, &command);
        assert!((pred_final[1] - 1.0).abs() < 0.1);
    }

    #[test]
    fn prediction_error_compute() {
        let predicted = vec![1.0, 2.0, 3.0];
        let actual = vec![1.1, 2.0, 2.9];
        let err = PredictionError::compute(&predicted, &actual, 0.1);
        assert!((err.error[0] - 0.1).abs() < 1e-10);
        assert!((err.error[1] - 0.0).abs() < 1e-10);
        assert!((err.error[2] + 0.1).abs() < 1e-10);
        assert!(!err.is_surprising); // MSE should be small
    }

    #[test]
    fn prediction_error_surprising() {
        let predicted = vec![0.0, 0.0];
        let actual = vec![5.0, 5.0];
        let err = PredictionError::compute(&predicted, &actual, 0.1);
        assert!(err.is_surprising);
        assert!(err.mse > 0.1);
    }

    #[test]
    fn prediction_error_magnitude() {
        let err = PredictionError::compute(&[0.0, 0.0], &[3.0, 4.0], 0.0);
        assert!((err.magnitude() - 5.0).abs() < 1e-10); // 3-4-5 triangle
    }

    #[test]
    fn cerebellar_controller_new() {
        let c = CerebellarController::new(3, 2);
        assert_eq!(c.model.state_dim(), 3);
        assert_eq!(c.model.command_dim(), 2);
        assert!((c.attenuation() - 0.0).abs() < f64::EPSILON);
    }

    #[test]
    fn cerebellar_controller_predict() {
        let mut c = CerebellarController::new(2, 1);
        let state = vec![1.0, 2.0];
        let command = vec![0.5];
        let predicted = c.predict(&state, &command);
        assert_eq!(predicted.len(), 2);
        assert_eq!(c.predictions(), 1);
    }

    #[test]
    fn cerebellar_controller_process_feedback() {
        let mut c = CerebellarController::new(2, 1).with_learning_rate(0.1);
        let state = vec![1.0, 0.0];
        let command = vec![1.0];
        let actual = vec![1.0, 1.0];

        let err = c.process_feedback(&state, &command, &actual);
        assert_eq!(c.learning_updates(), 1);
        assert!(!err.error.is_empty());
    }

    #[test]
    fn cerebellar_controller_attenuation_increases() {
        let mut c = CerebellarController::new(2, 1).with_surprise_threshold(10.0);
        let state = vec![0.0, 0.0];
        let command = vec![0.0];
        let actual = vec![0.0, 0.0]; // Perfect prediction

        let a0 = c.attenuation();
        c.process_feedback(&state, &command, &actual);
        let a1 = c.attenuation();
        assert!(a1 > a0);
    }

    #[test]
    fn cerebellar_controller_attenuation_decreases_on_surprise() {
        let mut c = CerebellarController::new(2, 1).with_surprise_threshold(0.001);
        // First, build up some attenuation
        for _ in 0..50 {
            c.process_feedback(&[0.0, 0.0], &[0.0], &[0.0, 0.0]);
        }
        let a0 = c.attenuation();
        assert!(a0 > 0.0);

        // Now introduce a surprise
        c.process_feedback(&[0.0, 0.0], &[0.0], &[5.0, 5.0]);
        let a1 = c.attenuation();
        assert!(a1 < a0);
    }

    #[test]
    fn cerebellar_controller_avg_mse() {
        let mut c = CerebellarController::new(2, 1).with_learning_rate(0.1);
        c.process_feedback(&[1.0, 0.0], &[1.0], &[1.0, 1.0]);
        c.process_feedback(&[1.0, 0.0], &[1.0], &[1.0, 1.0]);
        assert!(c.avg_mse() >= 0.0);
    }

    #[test]
    fn cerebellar_controller_error_history() {
        let mut c = CerebellarController::new(2, 1).with_history_size(5);
        for _ in 0..10 {
            c.process_feedback(&[0.0, 0.0], &[0.0], &[0.0, 0.0]);
        }
        let history = c.error_history();
        assert_eq!(history.len(), 5);
    }

    #[test]
    fn cerebellar_controller_is_calibrated() {
        let mut c = CerebellarController::new(2, 1)
            .with_learning_rate(0.1)
            .with_surprise_threshold(0.5);

        // Not calibrated with few updates
        assert!(!c.is_calibrated());

        // Train with consistent data
        for _ in 0..100 {
            c.process_feedback(&[0.0, 0.0], &[0.0], &[0.0, 0.0]);
        }
        assert!(c.is_calibrated());
    }

    #[test]
    fn cerebellar_controller_default() {
        let c = CerebellarController::default();
        assert_eq!(c.model.state_dim(), 3);
        assert_eq!(c.model.command_dim(), 2);
    }

    #[test]
    fn motor_timing_new() {
        let mt = MotorTiming::new(
            vec![vec![1.0], vec![0.5], vec![0.0]],
            vec![0.0, 0.5, 1.0],
            1.5,
        );
        assert_eq!(mt.command_count(), 3);
        assert!((mt.total_duration - 1.5).abs() < f64::EPSILON);
    }

    #[test]
    fn motor_timing_command_at_time() {
        let mt = MotorTiming::new(
            vec![vec![1.0], vec![0.5], vec![0.0]],
            vec![0.0, 0.5, 1.0],
            1.5,
        );

        assert_eq!(mt.command_at_time(0.0), Some(&vec![1.0]));
        assert_eq!(mt.command_at_time(0.3), Some(&vec![1.0])); // Before 0.5
        assert_eq!(mt.command_at_time(0.5), Some(&vec![0.5]));
        assert_eq!(mt.command_at_time(0.7), Some(&vec![0.5])); // Before 1.0
        assert_eq!(mt.command_at_time(1.0), Some(&vec![0.0]));
        assert_eq!(mt.command_at_time(1.2), Some(&vec![0.0]));
        assert_eq!(mt.command_at_time(-0.1), None);
        assert_eq!(mt.command_at_time(2.0), None);
    }

    #[test]
    fn forward_model_with_learning_rate() {
        let m = LinearForwardModel::new(2, 1).with_learning_rate(0.5);
        assert!((m.learning_rate - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn controller_with_surprise_threshold() {
        let c = CerebellarController::new(2, 1).with_surprise_threshold(0.5);
        assert!((c.surprise_threshold - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn controller_with_history_size() {
        let c = CerebellarController::new(2, 1).with_history_size(128);
        assert_eq!(c.max_history, 128);
    }
}
