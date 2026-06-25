//! Counterfactual estimation via synthetic control (Objective C)
//!
//! Implements:
//! - Exponential smoothing projection of pre-improvement trajectory
//! - Bootstrap confidence intervals for synthetic control
//! - Causal impact estimation: actual_post - synthetic_control

use std::f64;

/// Project a pre-improvement trajectory forward using exponential smoothing.
///
/// Uses alpha-weighted smoothing + linear trend from last two points.
/// Returns projected values for n_steps.
pub fn project_forward(
    pre_values: &[f64],
    smoothing_alpha: f64,
    n_steps: i32,
) -> Vec<f64> {
    if pre_values.is_empty() || n_steps <= 0 {
        return vec![];
    }

    // Exponential smoothing
    let mut smoothed = pre_values[0];
    for &v in &pre_values[1..] {
        smoothed = smoothing_alpha * v + (1.0 - smoothing_alpha) * smoothed;
    }

    // Linear trend from last two points
    let trend = if pre_values.len() >= 2 {
        pre_values[pre_values.len() - 1] - pre_values[pre_values.len() - 2]
    } else {
        0.0
    };

    let mut projections = Vec::with_capacity(n_steps as usize);
    let mut current = smoothed;
    for _ in 0..n_steps {
        current = current + trend * smoothing_alpha;
        projections.push(current);
    }
    projections
}

/// Bootstrap confidence interval for the synthetic control.
///
/// Resamples pre_values with replacement, projects forward, collects
/// the final projection, and returns percentile-based CI.
pub fn bootstrap_ci(
    pre_values: &[f64],
    smoothing_alpha: f64,
    n_steps: i32,
    n_bootstrap: i32,
    confidence: f64,
    seed: u64,
) -> (f64, f64) {
    if pre_values.is_empty() || n_bootstrap < 10 || n_steps <= 0 {
        return (0.0, 0.0);
    }

    let mut s = seed;
    let mut samples = Vec::with_capacity(n_bootstrap as usize);

    for _ in 0..n_bootstrap {
        // Resample with replacement
        let mut boot = Vec::with_capacity(pre_values.len());
        for _ in 0..pre_values.len() {
            let idx = (lcg_next_f64(&mut s) * pre_values.len() as f64) as usize;
            let idx = idx.min(pre_values.len() - 1);
            boot.push(pre_values[idx]);
        }
        let projection = project_forward(&boot, smoothing_alpha, n_steps);
        if let Some(&last) = projection.last() {
            samples.push(last);
        }
    }

    if samples.is_empty() {
        return (0.0, 0.0);
    }

    samples.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let alpha = (1.0 - confidence) / 2.0;
    let lower_idx = (alpha * samples.len() as f64) as usize;
    let upper_idx = ((1.0 - alpha) * samples.len() as f64) as usize;
    let upper_idx = upper_idx.min(samples.len() - 1);

    (samples[lower_idx], samples[upper_idx])
}

/// Estimate causal impact of an improvement.
///
/// Returns (actual_post, synthetic_control, causal_impact, ci_lower, ci_upper).
pub fn estimate_impact(
    pre_values: &[f64],
    post_values: &[f64],
    smoothing_alpha: f64,
    n_bootstrap: i32,
    confidence: f64,
    seed: u64,
) -> (f64, f64, f64, f64, f64) {
    let n_post = post_values.len() as i32;

    // Project pre-improvement trajectory forward
    let projections = project_forward(pre_values, smoothing_alpha, n_post);
    let synthetic_control: f64 = if projections.is_empty() {
        0.0
    } else {
        projections.iter().sum::<f64>() / projections.len() as f64
    };

    // Actual post-improvement average
    let actual_post: f64 = if post_values.is_empty() {
        0.0
    } else {
        post_values.iter().sum::<f64>() / post_values.len() as f64
    };

    let causal_impact = actual_post - synthetic_control;

    // Bootstrap CI
    let (ci_lower, ci_upper) = bootstrap_ci(
        pre_values,
        smoothing_alpha,
        n_post,
        n_bootstrap,
        confidence,
        seed,
    );

    (actual_post, synthetic_control, causal_impact, ci_lower, ci_upper)
}

/// Check if a confidence interval indicates statistical significance
/// (CI doesn't contain 0).
pub fn is_significant(ci_lower: f64, ci_upper: f64) -> bool {
    (ci_lower > 0.0 && ci_upper > 0.0) || (ci_lower < 0.0 && ci_upper < 0.0)
}

// ---- Internal ----

fn lcg_next_f64(seed: &mut u64) -> f64 {
    *seed = seed.wrapping_mul(1103515245).wrapping_add(12345);
    (*seed % 2147483647) as f64 / 2147483647.0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_project_forward_basic() {
        let pre = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let proj = project_forward(&pre, 0.3, 3);
        assert_eq!(proj.len(), 3);
        // Should project upward (positive trend)
        assert!(proj[0] > 3.0, "projection should continue trend, got {}", proj[0]);
    }

    #[test]
    fn test_project_forward_empty() {
        let proj = project_forward(&[], 0.3, 5);
        assert!(proj.is_empty());
    }

    #[test]
    fn test_project_forward_zero_steps() {
        let proj = project_forward(&[1.0, 2.0], 0.3, 0);
        assert!(proj.is_empty());
    }

    #[test]
    fn test_project_forward_single_point() {
        let proj = project_forward(&[5.0], 0.3, 3);
        assert_eq!(proj.len(), 3);
        // No trend from single point
        assert!((proj[0] - 5.0).abs() < 0.001);
    }

    #[test]
    fn test_bootstrap_ci() {
        let pre = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
        let (lower, upper) = bootstrap_ci(&pre, 0.3, 3, 100, 0.95, 42);
        assert!(lower <= upper, "lower should be <= upper: {} vs {}", lower, upper);
    }

    #[test]
    fn test_bootstrap_ci_empty() {
        let (lower, upper) = bootstrap_ci(&[], 0.3, 3, 100, 0.95, 42);
        assert_eq!(lower, 0.0);
        assert_eq!(upper, 0.0);
    }

    #[test]
    fn test_estimate_impact() {
        let pre = vec![1.0, 1.1, 1.0, 1.1, 1.0];
        let post = vec![2.0, 2.1, 2.0, 2.1, 2.0];
        let (actual, control, impact, ci_lo, ci_hi) = estimate_impact(
            &pre, &post, 0.3, 100, 0.95, 42,
        );
        assert!(actual > 1.5, "actual post should be ~2.0, got {}", actual);
        assert!(control < 1.5, "synthetic control should be ~1.0, got {}", control);
        assert!(impact > 0.5, "causal impact should be positive, got {}", impact);
        assert!(ci_lo <= ci_hi);
    }

    #[test]
    fn test_is_significant() {
        assert!(is_significant(0.5, 1.0));
        assert!(is_significant(-1.0, -0.5));
        assert!(!is_significant(-0.5, 0.5));
        assert!(!is_significant(0.0, 1.0));
    }
}
