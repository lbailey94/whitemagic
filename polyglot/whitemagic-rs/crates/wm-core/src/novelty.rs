//! Novelty detection via KL-divergence surprise gate.

/// Compute KL divergence from expected to actual distribution.
/// Both must be non-negative and sum to > 0.
pub fn kl_divergence(expected: &[f64], actual: &[f64]) -> f64 {
    assert_eq!(expected.len(), actual.len());
    let mut kl = 0.0;
    for i in 0..expected.len() {
        if expected[i] > 0.0 && actual[i] > 0.0 {
            kl += actual[i] * (actual[i] / expected[i]).ln();
        }
    }
    kl
}

/// Check if surprise exceeds threshold.
pub fn gate_trigger(surprise: f64, threshold: f64) -> bool {
    surprise > threshold
}

/// Compute expected distribution as a smoothed moving average.
pub fn moving_average(history: &[Vec<f64>], window: usize) -> Vec<f64> {
    if history.is_empty() {
        return vec![];
    }
    let dim = history[0].len();
    let start = history.len().saturating_sub(window);
    let recent = &history[start..];
    let n = recent.len() as f64;
    let mut avg = vec![0.0; dim];
    for v in recent {
        for (i, &x) in v.iter().enumerate() {
            avg[i] += x;
        }
    }
    for a in &mut avg {
        *a /= n;
    }
    avg
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kl_same_dist() {
        let p = vec![0.5, 0.5];
        assert!(kl_divergence(&p, &p).abs() < 1e-9);
    }

    #[test]
    fn test_gate() {
        assert!(gate_trigger(1.5, 1.0));
        assert!(!gate_trigger(0.5, 1.0));
    }

    #[test]
    fn test_moving_average() {
        let hist = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
        ];
        let avg = moving_average(&hist, 2);
        assert!((avg[0] - 0.5).abs() < 1e-9);
        assert!((avg[1] - 0.5).abs() < 1e-9);
    }
}
