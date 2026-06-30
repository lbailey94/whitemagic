//! 64-Lane Hexagram SIMD Execution (Phase 6a)
//!
//! Maps each of the 64 hexagrams to a SIMD execution lane. Processes
//! multiple hexagram dispatches in parallel using batch operations.
//! Each lane corresponds to a King Wen hexagram number (1-64).

use crate::iching_dispatch::{dispatch_for_hexagram, HexagramDispatch, DispatchStrategy};

/// A single execution lane for one hexagram.
#[derive(Debug, Clone)]
pub struct SimdLane {
    pub hexagram_num: u32,
    pub dispatch: Option<HexagramDispatch>,
    /// Input data vector (f64 values to process)
    pub input: Vec<f64>,
    /// Output result vector
    pub output: Vec<f64>,
    /// Whether this lane is active
    pub active: bool,
}

/// 64-lane SIMD execution engine.
#[derive(Debug)]
pub struct HexagramSimdEngine {
    pub lanes: Vec<SimdLane>,
    /// Total number of active lanes
    pub active_count: usize,
}

impl HexagramSimdEngine {
    /// Create a new 64-lane engine with all lanes initialized.
    pub fn new() -> Self {
        let lanes: Vec<SimdLane> = (1..=64u32)
            .map(|n| {
                let dispatch = dispatch_for_hexagram(n);
                SimdLane {
                    hexagram_num: n,
                    dispatch,
                    input: Vec::new(),
                    output: Vec::new(),
                    active: false,
                }
            })
            .collect();
        Self { lanes, active_count: 0 }
    }

    /// Load data into a specific lane (by hexagram number).
    pub fn load(&mut self, hexagram_num: u32, data: Vec<f64>) {
        if hexagram_num >= 1 && hexagram_num <= 64 {
            let idx = (hexagram_num - 1) as usize;
            if !self.lanes[idx].active {
                self.active_count += 1;
            }
            self.lanes[idx].input = data;
            self.lanes[idx].active = true;
        }
    }

    /// Load data into multiple lanes at once.
    pub fn load_batch(&mut self, loads: &[(u32, Vec<f64>)]) {
        for &(num, ref data) in loads {
            self.load(num, data.clone());
        }
    }

    /// Execute all active lanes in parallel.
    /// Each lane applies its dispatch strategy to its input data.
    pub fn execute(&mut self) {
        for lane in &mut self.lanes {
            if !lane.active || lane.input.is_empty() {
                continue;
            }

            let strategy = lane.dispatch.as_ref()
                .map(|d| d.strategy)
                .unwrap_or(DispatchStrategy::Sequential);

            lane.output = match strategy {
                DispatchStrategy::ParallelSimd => Self::execute_parallel(&lane.input),
                DispatchStrategy::Batch => Self::execute_batch(&lane.input),
                DispatchStrategy::Stream => Self::execute_stream(&lane.input),
                DispatchStrategy::Pipelined => Self::execute_pipelined(&lane.input),
                DispatchStrategy::AsyncOverlap => Self::execute_async(&lane.input),
                DispatchStrategy::Sequential => Self::execute_sequential(&lane.input),
                DispatchStrategy::SingleThread => Self::execute_single(&lane.input),
                DispatchStrategy::GpuOffload => Self::execute_gpu(&lane.input),
            };
        }
    }

    /// Collect results from all active lanes.
    pub fn collect(&self) -> Vec<(u32, Vec<f64>)> {
        self.lanes.iter()
            .filter(|l| l.active && !l.output.is_empty())
            .map(|l| (l.hexagram_num, l.output.clone()))
            .collect()
    }

    /// Get result from a specific lane.
    pub fn result(&self, hexagram_num: u32) -> Option<&[f64]> {
        if hexagram_num >= 1 && hexagram_num <= 64 {
            let idx = (hexagram_num - 1) as usize;
            if !self.lanes[idx].output.is_empty() {
                return Some(&self.lanes[idx].output);
            }
        }
        None
    }

    /// Reset all lanes (clear input/output, deactivate).
    pub fn reset(&mut self) {
        for lane in &mut self.lanes {
            lane.input.clear();
            lane.output.clear();
            lane.active = false;
        }
        self.active_count = 0;
    }

    /// Get the number of active lanes.
    pub fn active_lanes(&self) -> usize {
        self.active_count
    }

    // Lane execution strategies (simulated SIMD operations)

    /// Parallel SIMD: element-wise square (simulates parallel compute)
    fn execute_parallel(input: &[f64]) -> Vec<f64> {
        input.iter().map(|x| x * x).collect()
    }

    /// Batch: cumulative sum (simulates batch processing)
    fn execute_batch(input: &[f64]) -> Vec<f64> {
        let mut result = Vec::with_capacity(input.len());
        let mut acc = 0.0;
        for &x in input {
            acc += x;
            result.push(acc);
        }
        result
    }

    /// Stream: moving average (simulates streaming computation)
    fn execute_stream(input: &[f64]) -> Vec<f64> {
        let window = 3.min(input.len());
        if window == 0 {
            return Vec::new();
        }
        let mut result = Vec::with_capacity(input.len());
        for i in 0..input.len() {
            let start = i.saturating_sub(window - 1);
            let sum: f64 = input[start..=i].iter().sum();
            result.push(sum / (i - start + 1) as f64);
        }
        result
    }

    /// Pipelined: FFT-like magnitude (simulates compute→memory→I/O stages)
    fn execute_pipelined(input: &[f64]) -> Vec<f64> {
        input.iter().map(|x| x.abs() + 0.001).collect()
    }

    /// Async overlap: interleaved processing
    fn execute_async(input: &[f64]) -> Vec<f64> {
        let mut result = vec![0.0; input.len()];
        // Process even indices first, then odd (simulates async overlap)
        for i in (0..input.len()).step_by(2) {
            result[i] = input[i] * 2.0;
        }
        for i in (1..input.len()).step_by(2) {
            result[i] = input[i] * 0.5;
        }
        result
    }

    /// Sequential: identity with delay simulation
    fn execute_sequential(input: &[f64]) -> Vec<f64> {
        input.to_vec()
    }

    /// Single thread: minimal processing
    fn execute_single(input: &[f64]) -> Vec<f64> {
        if input.is_empty() {
            return Vec::new();
        }
        vec![input.iter().sum::<f64>()]
    }

    /// GPU offload: matrix-like operation (simulates GPU compute)
    fn execute_gpu(input: &[f64]) -> Vec<f64> {
        // Simulate GPU matrix multiply: output[i] = sum(input[j] * input[(i+j)%n])
        let n = input.len();
        if n == 0 {
            return Vec::new();
        }
        let mut result = vec![0.0; n];
        for i in 0..n {
            for j in 0..n {
                result[i] += input[j] * input[(i + j) % n];
            }
            result[i] /= n as f64;
        }
        result
    }
}

impl Default for HexagramSimdEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = HexagramSimdEngine::new();
        assert_eq!(engine.lanes.len(), 64);
        assert_eq!(engine.active_count, 0);
    }

    #[test]
    fn test_all_lanes_have_dispatch() {
        let engine = HexagramSimdEngine::new();
        for lane in &engine.lanes {
            assert!(lane.dispatch.is_some(), "Lane {} has no dispatch", lane.hexagram_num);
        }
    }

    #[test]
    fn test_load_activates_lane() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(5, vec![1.0, 2.0, 3.0]);
        assert_eq!(engine.active_count, 1);
        assert!(engine.lanes[4].active);
        assert_eq!(engine.lanes[4].input, vec![1.0, 2.0, 3.0]);
    }

    #[test]
    fn test_load_batch() {
        let mut engine = HexagramSimdEngine::new();
        engine.load_batch(&[(1, vec![1.0]), (10, vec![2.0]), (64, vec![3.0])]);
        assert_eq!(engine.active_count, 3);
        assert!(engine.lanes[0].active);
        assert!(engine.lanes[9].active);
        assert!(engine.lanes[63].active);
    }

    #[test]
    fn test_execute_produces_output() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(1, vec![1.0, 2.0, 3.0, 4.0]);
        engine.execute();
        let result = engine.result(1);
        assert!(result.is_some());
        assert!(!result.unwrap().is_empty());
    }

    #[test]
    fn test_execute_parallel_squares() {
        let mut engine = HexagramSimdEngine::new();
        // Find a lane with ParallelSimd strategy
        let simd_lane = engine.lanes.iter()
            .find(|l| l.dispatch.as_ref().map(|d| d.strategy) == Some(DispatchStrategy::ParallelSimd))
            .map(|l| l.hexagram_num)
            .expect("Should have at least one ParallelSimd lane");
        engine.load(simd_lane, vec![2.0, 3.0, 4.0]);
        engine.execute();
        let result = engine.result(simd_lane).unwrap();
        assert_eq!(result, &[4.0, 9.0, 16.0]);
    }

    #[test]
    fn test_execute_sequential_identity() {
        let mut engine = HexagramSimdEngine::new();
        // Find a lane with Sequential strategy
        let seq_lane = engine.lanes.iter()
            .find(|l| l.dispatch.as_ref().map(|d| d.strategy) == Some(DispatchStrategy::Sequential))
            .map(|l| l.hexagram_num)
            .expect("Should have at least one Sequential lane");
        let data = vec![1.0, 2.0, 3.0];
        engine.load(seq_lane, data.clone());
        engine.execute();
        let result = engine.result(seq_lane).unwrap();
        assert_eq!(result, &data);
    }

    #[test]
    fn test_collect_all_active() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(1, vec![1.0]);
        engine.load(2, vec![2.0]);
        engine.load(3, vec![3.0]);
        engine.execute();
        let results = engine.collect();
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn test_reset_clears_all() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(1, vec![1.0]);
        engine.load(2, vec![2.0]);
        engine.execute();
        engine.reset();
        assert_eq!(engine.active_count, 0);
        assert!(engine.lanes[0].input.is_empty());
        assert!(engine.lanes[0].output.is_empty());
        assert!(!engine.lanes[0].active);
    }

    #[test]
    fn test_invalid_hexagram_ignored() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(0, vec![1.0]);
        engine.load(65, vec![1.0]);
        assert_eq!(engine.active_count, 0);
    }

    #[test]
    fn test_active_lanes_count() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(10, vec![1.0]);
        engine.load(20, vec![2.0]);
        assert_eq!(engine.active_lanes(), 2);
    }

    #[test]
    fn test_execute_empty_input_no_output() {
        let mut engine = HexagramSimdEngine::new();
        engine.load(1, vec![]);
        engine.execute();
        assert!(engine.result(1).is_none());
    }

    #[test]
    fn test_single_thread_strategy() {
        let mut engine = HexagramSimdEngine::new();
        // Find a lane with SingleThread strategy
        let st_lane = engine.lanes.iter()
            .find(|l| l.dispatch.as_ref().map(|d| d.strategy) == Some(DispatchStrategy::SingleThread))
            .map(|l| l.hexagram_num);
        if let Some(lane_num) = st_lane {
            engine.load(lane_num, vec![1.0, 2.0, 3.0]);
            engine.execute();
            let result = engine.result(lane_num).unwrap();
            assert_eq!(result.len(), 1); // SingleThread returns single value
            assert_eq!(result[0], 6.0); // sum
        }
    }

    #[test]
    fn test_all_64_lanes_executable() {
        let mut engine = HexagramSimdEngine::new();
        for n in 1..=64u32 {
            engine.load(n, vec![1.0, 2.0, 3.0]);
        }
        assert_eq!(engine.active_count, 64);
        engine.execute();
        let results = engine.collect();
        // All lanes should produce output (some strategies may produce empty for empty input,
        // but we loaded non-empty data)
        assert_eq!(results.len(), 64);
    }
}
