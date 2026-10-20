//! Pure-Rust `TTTHead` (PCA-k + L2 Multinomial Logistic) & Conformal Singleton Gate.
//!
//! Implements System 0.5 calibrated non-autoregressive decision routing:
//! 1. Feature standardization: `Z = (X - mu) / sd`
//! 2. Principal subspace projection: `Zp = ((Z - c) @ P^T) / s` (`k <= 128` components)
//! 3. Multinomial logistic readout with temperature scaling:
//!    `probs = softmax((Zp @ W^T + b) / T)`
//! 4. Finite-sample conformal prediction sets (`PEB-12`):
//!    `q_hat = sorted(1 - p(y_i | x_i))[ceil((n + 1)(1 - alpha)) - 1]`
//!    Singleton sets (`|C(x)| == 1`) execute immediately at System 0.5;
//!    multi-label sets (`|C(x)| > 1`) escalate to System 1.5 (`Vega-U`) or System 2.

#![forbid(unsafe_code)]
#![allow(clippy::suboptimal_flops)]

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

/// Conformal gate outcome for a System 0.5 prediction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConformalGateStatus {
    /// Prediction set has size 1 (`|C(x)| == 1`): fast-path System 0.5 execution warranted.
    Singleton,
    /// Prediction set has size > 1 (`|C(x)| > 1`): escalate to System 1.5 (`Vega-U`) / System 2.
    EscalateMultiSet,
    /// Prediction set is empty (`|C(x)| == 0`): out-of-distribution / low confidence abstention.
    AbstainEmpty,
    /// Head is uncalibrated; returns top-1 without conformal coverage guarantee.
    Uncalibrated,
}

/// Calibrated prediction and conformal set emitted by [`TttHead`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConformalPrediction {
    pub top_label: String,
    pub top_index: usize,
    pub top_prob: f32,
    pub probabilities: Vec<f32>,
    pub prediction_set: Vec<String>,
    pub gate_status: ConformalGateStatus,
}

/// Pure-Rust Test-Time Training Head (`PCA-k` + L2 Multinomial Logistic + Conformal Gate).
///
/// Matrices `proj` (`[k * dim]`) and `weights` (`[num_classes * k]`) are stored row-major
/// so every inner loop is a contiguous slice dot product that auto-vectorizes cleanly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TttHead {
    pub labels: Vec<String>,
    pub dim: usize,
    pub k: usize,
    pub mu: Vec<f32>,
    pub sd: Vec<f32>,
    pub c: Vec<f32>,
    /// Row-major `[k * dim]`: row `j` is principal component axis `j` of length `dim`.
    pub proj: Vec<f32>,
    pub s: Vec<f32>,
    /// Row-major `[num_classes * k]`: row `cls` is logistic weight vector for class `cls`.
    pub weights: Vec<f32>,
    pub bias: Vec<f32>,
    /// Algebraically fused `[num_classes * dim]` operator: `W_fused = (W / s) * P / (sd * T)`.
    /// Reduces inference from `O(k * dim + C * k)` to `O(C * dim)` (32.3x fewer FLOPs for D=384, K=128, C=4)
    /// while remaining provably equivalent to the 3-stage PCA+Logistic pipeline.
    pub fused_weights: Vec<f32>,
    pub fused_bias: Vec<f32>,
    pub temperature: f32,
    pub conformal_alpha: Option<f32>,
    pub conformal_threshold: Option<f32>,
    pub calibration_n: usize,
}

impl TttHead {
    /// Construct a `TttHead` from pre-computed weights (e.g. exported from `vegaml.TTTHead` or fitted in Rust).
    #[allow(clippy::too_many_arguments)]
    pub fn from_weights(
        labels: Vec<String>,
        dim: usize,
        k: usize,
        mu: Vec<f32>,
        sd: Vec<f32>,
        c: Vec<f32>,
        proj: Vec<f32>,
        s: Vec<f32>,
        weights: Vec<f32>,
        bias: Vec<f32>,
    ) -> Result<Self, String> {
        let num_classes = labels.len();
        if num_classes < 2 {
            return Err("TttHead requires at least 2 labels".to_string());
        }
        if dim == 0 || k == 0 || k > dim {
            return Err(format!("invalid dimensions: dim={dim}, k={k}"));
        }
        if mu.len() != dim || sd.len() != dim || c.len() != dim {
            return Err("mu, sd, and c must have length == dim".to_string());
        }
        if proj.len() != k * dim {
            return Err(format!("proj length {} != k*dim ({})", proj.len(), k * dim));
        }
        if s.len() != k {
            return Err(format!("s length {} != k ({k})", s.len()));
        }
        if weights.len() != num_classes * k || bias.len() != num_classes {
            return Err("weights/bias dimensions do not match num_classes * k".to_string());
        }
        let mut head = Self {
            labels,
            dim,
            k,
            mu,
            sd,
            c,
            proj,
            s,
            weights,
            bias,
            fused_weights: Vec::new(),
            fused_bias: Vec::new(),
            temperature: 1.0,
            conformal_alpha: None,
            conformal_threshold: None,
            calibration_n: 0,
        };
        head.recompute_fused_operator();
        Ok(head)
    }

    /// Algebraically fuse standardization `(mu, sd, c)`, PCA projection `(proj, s)`,
    /// and logistic readout `(weights, bias, temperature)` into a single `[C * dim]`
    /// affine map `logits = W_fused * x + b_fused`.
    pub fn recompute_fused_operator(&mut self) {
        let num_classes = self.labels.len();
        let inv_temp = 1.0 / self.temperature.max(1e-4);
        let mut fw = vec![0.0f32; num_classes * self.dim];
        let mut fb = vec![0.0f32; num_classes];

        for cls in 0..num_classes {
            let w_row = &self.weights[cls * self.k..(cls + 1) * self.k];
            let fw_row = &mut fw[cls * self.dim..(cls + 1) * self.dim];
            for (comp, &w_val) in w_row.iter().enumerate() {
                let scale = (w_val / self.s[comp]) * inv_temp;
                let p_row = &self.proj[comp * self.dim..(comp + 1) * self.dim];
                for (d, fw_val) in fw_row.iter_mut().enumerate() {
                    *fw_val += scale * (p_row[d] / self.sd[d]);
                }
            }
            let mut shift = 0.0f32;
            for (d, &fw_val) in fw_row.iter().enumerate() {
                shift += fw_val * (self.mu[d] + self.sd[d] * self.c[d]);
            }
            fb[cls] = self.bias[cls] * inv_temp - shift;
        }
        self.fused_weights = fw;
        self.fused_bias = fb;
    }

    /// Fit a `TttHead` directly in pure Rust from frozen embedding vectors and string labels.
    ///
    /// Performs standardization, top-`k` orthogonal power-iteration PCA with Gram-Schmidt
    /// deflation, and L2-regularized multinomial logistic regression.
    pub fn fit(
        samples: &[Vec<f32>],
        sample_labels: &[String],
        class_labels: Vec<String>,
        requested_k: usize,
        l2: f32,
        iters: usize,
        lr: f32,
    ) -> Result<Self, String> {
        let n = samples.len();
        if n < 4 || n != sample_labels.len() {
            return Err("need at least 4 samples with matching label count".to_string());
        }
        let dim = samples[0].len();
        if dim == 0 || samples.iter().any(|v| v.len() != dim) {
            return Err("all samples must have non-zero equal dimension".to_string());
        }
        let num_classes = class_labels.len();
        if num_classes < 2 {
            return Err("need at least 2 classes".to_string());
        }

        let mut y_idx = Vec::with_capacity(n);
        for lbl in sample_labels {
            match class_labels.iter().position(|c| c == lbl) {
                Some(idx) => y_idx.push(idx),
                None => return Err(format!("unknown sample label '{lbl}'")),
            }
        }

        let inv_n = 1.0 / (n as f32);
        let mut mu = vec![0.0f32; dim];
        for row in samples {
            for (d, &val) in row.iter().enumerate() {
                mu[d] += val * inv_n;
            }
        }

        let mut sd = vec![0.0f32; dim];
        for row in samples {
            for (d, &val) in row.iter().enumerate() {
                let diff = val - mu[d];
                sd[d] += diff * diff * inv_n;
            }
        }
        for val in &mut sd {
            *val = val.sqrt() + 1e-6;
        }

        let mut z = vec![0.0f32; n * dim];
        let mut c = vec![0.0f32; dim];
        for (i, row) in samples.iter().enumerate() {
            let base = i * dim;
            for d in 0..dim {
                let val = (row[d] - mu[d]) / sd[d];
                z[base + d] = val;
                c[d] += val * inv_n;
            }
        }
        for i in 0..n {
            let base = i * dim;
            for d in 0..dim {
                z[base + d] -= c[d];
            }
        }

        let k = requested_k.min(dim).min(n.saturating_sub(1)).max(1);
        let mut proj = vec![0.0f32; k * dim];

        // Extract top-k orthogonal principal directions via deflated power iteration
        let mut tmp_n = vec![0.0f32; n];
        for comp in 0..k {
            let mut v = vec![0.0f32; dim];
            for (d, item) in v.iter_mut().enumerate() {
                // Deterministic initialization orthogonal-friendly across component index
                let seed = ((comp + 1) * 131 + (d + 1) * 17) as f32;
                *item = seed.sin();
            }
            normalize_in_place(&mut v);

            for _ in 0..18 {
                // tmp_n = Z * v
                for i in 0..n {
                    let row = &z[i * dim..(i + 1) * dim];
                    tmp_n[i] = dot_slice(row, &v);
                }
                // v_next = Z^T * tmp_n
                v.fill(0.0);
                for (i, &t) in tmp_n.iter().enumerate() {
                    let row = &z[i * dim..(i + 1) * dim];
                    for (d, &r) in row.iter().enumerate() {
                        v[d] += t * r;
                    }
                }
                // Gram-Schmidt orthogonalization against previous components
                for prev in 0..comp {
                    let prev_axis = &proj[prev * dim..(prev + 1) * dim];
                    let overlap = dot_slice(&v, prev_axis);
                    for (d, &p) in prev_axis.iter().enumerate() {
                        v[d] -= overlap * p;
                    }
                }
                normalize_in_place(&mut v);
            }
            proj[comp * dim..(comp + 1) * dim].copy_from_slice(&v);
        }

        // Project Z onto proj -> Zp [n * k] and standardize by s
        let mut zp = vec![0.0f32; n * k];
        let mut s = vec![0.0f32; k];
        for i in 0..n {
            let z_row = &z[i * dim..(i + 1) * dim];
            let zp_row = &mut zp[i * k..(i + 1) * k];
            for (comp, out) in zp_row.iter_mut().enumerate() {
                let axis = &proj[comp * dim..(comp + 1) * dim];
                let val = dot_slice(z_row, axis);
                *out = val;
                s[comp] += val * val * inv_n;
            }
        }
        for val in &mut s {
            *val = val.sqrt() + 1e-6;
        }
        for i in 0..n {
            let zp_row = &mut zp[i * k..(i + 1) * k];
            for (comp, val) in zp_row.iter_mut().enumerate() {
                *val /= s[comp];
            }
        }

        // L2-regularized multinomial logistic regression
        let mut weights = vec![0.0f32; num_classes * k];
        let mut bias = vec![0.0f32; num_classes];
        let mut grad_w = vec![0.0f32; num_classes * k];
        let mut grad_b = vec![0.0f32; num_classes];
        let mut logits = vec![0.0f32; num_classes];

        for _ in 0..iters {
            grad_w.fill(0.0);
            grad_b.fill(0.0);

            for (i, &target_cls) in y_idx.iter().enumerate() {
                let zp_row = &zp[i * k..(i + 1) * k];
                let mut max_logit = f32::NEG_INFINITY;
                for cls in 0..num_classes {
                    let w_row = &weights[cls * k..(cls + 1) * k];
                    let l = dot_slice(zp_row, w_row) + bias[cls];
                    logits[cls] = l;
                    if l > max_logit {
                        max_logit = l;
                    }
                }
                let mut sum_exp = 0.0f32;
                for l in &mut logits {
                    *l = (*l - max_logit).exp();
                    sum_exp += *l;
                }
                let inv_sum = 1.0 / sum_exp.max(1e-12);
                for cls in 0..num_classes {
                    let prob = logits[cls] * inv_sum;
                    let diff = (prob - if cls == target_cls { 1.0 } else { 0.0 }) * inv_n;
                    grad_b[cls] += diff;
                    let gw_row = &mut grad_w[cls * k..(cls + 1) * k];
                    for (comp, &zp_val) in zp_row.iter().enumerate() {
                        gw_row[comp] += diff * zp_val;
                    }
                }
            }

            for cls in 0..num_classes {
                bias[cls] -= lr * grad_b[cls];
                let w_row = &mut weights[cls * k..(cls + 1) * k];
                let gw_row = &grad_w[cls * k..(cls + 1) * k];
                for comp in 0..k {
                    w_row[comp] -= lr * (gw_row[comp] + l2 * w_row[comp]);
                }
            }
        }

        Self::from_weights(class_labels, dim, k, mu, sd, c, proj, s, weights, bias)
    }

    /// Calibrate finite-sample split-conformal threshold (`PEB-12`) at miscoverage rate `alpha`.
    ///
    /// Computes nonconformity scores `s_i = 1 - p(y_i | x_i)` and sets `conformal_threshold`
    /// to the `ceil((n + 1)(1 - alpha)) / n` empirical quantile.
    pub fn calibrate_conformal(
        &mut self,
        cal_samples: &[Vec<f32>],
        cal_labels: &[String],
        alpha: f32,
    ) -> Result<f32, String> {
        if !(0.001..0.999).contains(&alpha) {
            return Err(format!("alpha {alpha} must be in (0.001, 0.999)"));
        }
        let n = cal_samples.len();
        if n == 0 || n != cal_labels.len() {
            return Err(
                "calibration samples and labels must be non-empty and equal length".to_string(),
            );
        }

        let mut scores = Vec::with_capacity(n);
        let mut z_buf = vec![0.0f32; self.dim];
        let mut zp_buf = vec![0.0f32; self.k];
        let mut probs = vec![0.0f32; self.labels.len()];

        for (x, lbl) in cal_samples.iter().zip(cal_labels.iter()) {
            let cls_idx = self
                .labels
                .iter()
                .position(|c| c == lbl)
                .ok_or_else(|| format!("unknown calibration label '{lbl}'"))?;
            self.predict_into(x, &mut z_buf, &mut zp_buf, &mut probs);
            scores.push(1.0 - probs[cls_idx]);
        }

        scores.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
        let rank = (((n + 1) as f32) * (1.0 - alpha)).ceil() as usize;
        let idx = rank.saturating_sub(1).min(n - 1);
        let q_hat = scores[idx];

        self.conformal_alpha = Some(alpha);
        self.conformal_threshold = Some(q_hat);
        self.calibration_n = n;
        Ok(q_hat)
    }

    /// Zero-allocation hot-path probability computation using the algebraically fused
    /// `[C * dim]` affine operator (`O(C * dim)` instead of `O(k * dim + C * k)`).
    #[inline]
    pub fn predict_into(
        &self,
        x: &[f32],
        _z_buf: &mut [f32],
        _zp_buf: &mut [f32],
        probs_out: &mut [f32],
    ) {
        debug_assert_eq!(x.len(), self.dim);
        debug_assert_eq!(probs_out.len(), self.labels.len());

        let mut max_logit = f32::NEG_INFINITY;
        for (cls, out) in probs_out.iter_mut().enumerate() {
            let fw_row = &self.fused_weights[cls * self.dim..(cls + 1) * self.dim];
            let logit = dot_slice(x, fw_row) + self.fused_bias[cls];
            *out = logit;
            if logit > max_logit {
                max_logit = logit;
            }
        }

        let mut sum_exp = 0.0f32;
        for out in probs_out.iter_mut() {
            *out = (*out - max_logit).exp();
            sum_exp += *out;
        }
        let inv_sum = 1.0 / sum_exp.max(1e-12);
        for out in probs_out.iter_mut() {
            *out *= inv_sum;
        }
    }

    /// Reference 3-stage unfused evaluation (`Standardize -> PCA-k -> Logistic`) used to
    /// verify algebraic equivalence with [`Self::predict_into`].
    #[inline]
    pub fn predict_unfused_into(
        &self,
        x: &[f32],
        z_buf: &mut [f32],
        zp_buf: &mut [f32],
        probs_out: &mut [f32],
    ) {
        debug_assert_eq!(x.len(), self.dim);
        debug_assert_eq!(z_buf.len(), self.dim);
        debug_assert_eq!(zp_buf.len(), self.k);
        debug_assert_eq!(probs_out.len(), self.labels.len());

        // 1. Standardize and center: z_buf[d] = (x[d] - mu[d]) / sd[d] - c[d]
        for d in 0..self.dim {
            z_buf[d] = ((x[d] - self.mu[d]) / self.sd[d]) - self.c[d];
        }

        // 2. Project onto k principal axes and scale by s
        for (comp, zp_val) in zp_buf.iter_mut().enumerate() {
            let axis = &self.proj[comp * self.dim..(comp + 1) * self.dim];
            *zp_val = dot_slice(z_buf, axis) / self.s[comp];
        }

        // 3. Multinomial logistic readout + temperature softmax
        let inv_temp = 1.0 / self.temperature.max(1e-4);
        let mut max_logit = f32::NEG_INFINITY;
        for (cls, out) in probs_out.iter_mut().enumerate() {
            let w_row = &self.weights[cls * self.k..(cls + 1) * self.k];
            let logit = (dot_slice(zp_buf, w_row) + self.bias[cls]) * inv_temp;
            *out = logit;
            if logit > max_logit {
                max_logit = logit;
            }
        }

        let mut sum_exp = 0.0f32;
        for out in probs_out.iter_mut() {
            *out = (*out - max_logit).exp();
            sum_exp += *out;
        }
        let inv_sum = 1.0 / sum_exp.max(1e-12);
        for out in probs_out.iter_mut() {
            *out *= inv_sum;
        }
    }

    /// Predict calibrated probabilities and conformal prediction set for a single vector.
    #[must_use]
    pub fn predict_conformal(&self, x: &[f32]) -> ConformalPrediction {
        let mut z_buf = vec![0.0f32; self.dim];
        let mut zp_buf = vec![0.0f32; self.k];
        let mut probs = vec![0.0f32; self.labels.len()];
        self.predict_into(x, &mut z_buf, &mut zp_buf, &mut probs);
        self.build_conformal_prediction(probs)
    }

    /// Predict a batch of vectors using reusable thread-local scratch buffers (`micro_batch_size` chunking).
    #[must_use]
    pub fn predict_batch_conformal(
        &self,
        batch: &[Vec<f32>],
        micro_batch_size: usize,
    ) -> Vec<ConformalPrediction> {
        let chunk_sz = micro_batch_size.max(1);
        let mut results = Vec::with_capacity(batch.len());
        let mut z_buf = vec![0.0f32; self.dim];
        let mut zp_buf = vec![0.0f32; self.k];

        for chunk in batch.chunks(chunk_sz) {
            for x in chunk {
                let mut probs = vec![0.0f32; self.labels.len()];
                self.predict_into(x, &mut z_buf, &mut zp_buf, &mut probs);
                results.push(self.build_conformal_prediction(probs));
            }
        }
        results
    }

    #[inline]
    fn build_conformal_prediction(&self, probs: Vec<f32>) -> ConformalPrediction {
        let mut top_index = 0;
        let mut top_prob = f32::NEG_INFINITY;
        for (idx, &p) in probs.iter().enumerate() {
            if p > top_prob {
                top_prob = p;
                top_index = idx;
            }
        }

        let (prediction_set, gate_status) = match self.conformal_threshold {
            Some(q_hat) => {
                let min_prob = 1.0 - q_hat;
                let mut set = Vec::new();
                for (idx, &p) in probs.iter().enumerate() {
                    if p >= min_prob {
                        set.push(self.labels[idx].clone());
                    }
                }
                let status = match set.len() {
                    0 => ConformalGateStatus::AbstainEmpty,
                    1 => ConformalGateStatus::Singleton,
                    _ => ConformalGateStatus::EscalateMultiSet,
                };
                (set, status)
            }
            None => (
                vec![self.labels[top_index].clone()],
                ConformalGateStatus::Uncalibrated,
            ),
        };

        ConformalPrediction {
            top_label: self.labels[top_index].clone(),
            top_index,
            top_prob,
            probabilities: probs,
            prediction_set,
            gate_status,
        }
    }
}

#[inline]
fn dot_slice(a: &[f32], b: &[f32]) -> f32 {
    let mut s0 = 0.0f32;
    let mut s1 = 0.0f32;
    let mut s2 = 0.0f32;
    let mut s3 = 0.0f32;
    let mut a_chunks = a.chunks_exact(4);
    let mut b_chunks = b.chunks_exact(4);
    for (ac, bc) in a_chunks.by_ref().zip(b_chunks.by_ref()) {
        s0 += ac[0] * bc[0];
        s1 += ac[1] * bc[1];
        s2 += ac[2] * bc[2];
        s3 += ac[3] * bc[3];
    }
    let rem: f32 = a_chunks
        .remainder()
        .iter()
        .zip(b_chunks.remainder().iter())
        .map(|(&x, &y)| x * y)
        .sum();
    (s0 + s1) + (s2 + s3) + rem
}

#[inline]
fn normalize_in_place(v: &mut [f32]) {
    let norm = v.iter().map(|&x| x * x).sum::<f32>().sqrt();
    if norm > 1e-12 {
        for x in v.iter_mut() {
            *x /= norm;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ttt_head_fits_calibrates_and_gates_singletons() {
        let classes = vec![
            "tech".to_string(),
            "study".to_string(),
            "science".to_string(),
        ];
        let dim = 16;
        let mut train_x = Vec::new();
        let mut train_y = Vec::new();

        // Construct 60 separable synthetic embeddings across 3 classes
        for i in 0..60 {
            let cls = i % 3;
            let mut vec = vec![0.0f32; dim];
            for (d, val) in vec.iter_mut().enumerate() {
                let base = if d / 5 == cls { 2.5 } else { -0.4 };
                let jitter = (((i * 31 + d * 7) % 19) as f32 - 9.0) * 0.03;
                *val = base + jitter;
            }
            train_x.push(vec);
            train_y.push(classes[cls].clone());
        }

        let mut head = TttHead::fit(&train_x, &train_y, classes.clone(), 8, 1e-2, 250, 0.8)
            .expect("TTTHead fits cleanly");
        let q_hat = head
            .calibrate_conformal(&train_x, &train_y, 0.10)
            .expect("conformal calibration succeeds");
        assert!(
            (0.0..0.5).contains(&q_hat),
            "expected sharp q_hat, got {q_hat}"
        );

        // Clear prototype -> Singleton fast path
        let pred = head.predict_conformal(&train_x[0]);
        assert_eq!(pred.top_label, "tech");
        assert_eq!(pred.gate_status, ConformalGateStatus::Singleton);
        assert_eq!(pred.prediction_set, vec!["tech".to_string()]);

        // Batch conformal prediction matches single-item
        let batch_preds = head.predict_batch_conformal(&train_x[0..6], 16);
        assert_eq!(batch_preds.len(), 6);
        for (i, bp) in batch_preds.iter().enumerate() {
            assert_eq!(bp.top_label, classes[i % 3]);
            assert_eq!(bp.gate_status, ConformalGateStatus::Singleton);
        }
    }

    #[test]
    fn benchmark_ttt_head_384d_pca128_throughput() {
        use std::time::Instant;

        let classes = vec![
            "tech".to_string(),
            "study".to_string(),
            "science".to_string(),
            "self".to_string(),
        ];
        let dim = 384;
        let k = 128;
        let c_len = classes.len();

        let mu = vec![0.01f32; dim];
        let sd = vec![1.0f32; dim];
        let c = vec![0.0f32; dim];
        let mut proj = vec![0.0f32; k * dim];
        for (i, val) in proj.iter_mut().enumerate() {
            *val = ((i as f32) * 0.013).sin() * 0.05;
        }
        let s = vec![1.0f32; k];
        let mut weights = vec![0.0f32; c_len * k];
        for (i, val) in weights.iter_mut().enumerate() {
            *val = ((i as f32) * 0.029).cos() * 0.2;
        }
        let bias = vec![0.1f32, -0.05, 0.02, -0.07];

        let mut head =
            TttHead::from_weights(classes, dim, k, mu, sd, c, proj, s, weights, bias).unwrap();
        head.conformal_alpha = Some(0.10);
        head.conformal_threshold = Some(0.75);
        head.calibration_n = 1220;

        let n_items = 2000;
        let mut queries = Vec::with_capacity(n_items);
        for i in 0..n_items {
            let mut q = vec![0.0f32; dim];
            for (d, val) in q.iter_mut().enumerate() {
                *val = (((i * 17 + d * 13) % 97) as f32 - 48.0) * 0.02;
            }
            queries.push(q);
        }

        // 1. Zero-allocation fused hot path (predict_into) vs unfused 3-stage path
        let mut z_buf = vec![0.0f32; dim];
        let mut zp_buf = vec![0.0f32; k];
        let mut probs = vec![0.0f32; c_len];
        let mut probs_unfused = vec![0.0f32; c_len];

        // Verify algebraic equivalence between unfused 3-stage and fused 1-stage across all queries
        for q in &queries[..50] {
            head.predict_into(q, &mut z_buf, &mut zp_buf, &mut probs);
            head.predict_unfused_into(q, &mut z_buf, &mut zp_buf, &mut probs_unfused);
            for c_i in 0..c_len {
                assert!(
                    (probs[c_i] - probs_unfused[c_i]).abs() < 1e-5,
                    "fused vs unfused mismatch: {} vs {}",
                    probs[c_i],
                    probs_unfused[c_i]
                );
            }
        }

        let t_unfused = Instant::now();
        let mut checksum_u = 0.0f32;
        for q in &queries {
            head.predict_unfused_into(q, &mut z_buf, &mut zp_buf, &mut probs_unfused);
            checksum_u += probs_unfused[0];
        }
        let us_unfused = t_unfused.elapsed().as_secs_f64() * 1e6 / (n_items as f64);

        let t0 = Instant::now();
        let mut checksum = 0.0f32;
        for q in &queries {
            head.predict_into(q, &mut z_buf, &mut zp_buf, &mut probs);
            checksum += probs[0];
        }
        let elapsed_into = t0.elapsed();
        let us_per_item_into = elapsed_into.as_secs_f64() * 1e6 / (n_items as f64);

        // 2. Full ConformalPrediction struct path (B=16 micro-batch)
        let t1 = Instant::now();
        let preds = head.predict_batch_conformal(&queries, 16);
        let elapsed_batch = t1.elapsed();
        let us_per_item_batch = elapsed_batch.as_secs_f64() * 1e6 / (n_items as f64);

        assert_eq!(preds.len(), n_items);
        assert!((checksum - checksum_u).abs() < 1e-2);
        println!(
            "TTTHead Rust Benchmark (dim=384, k=128, C=4, N={n_items}): unfused = {us_unfused:.3} us/item, fused predict_into = {us_per_item_into:.3} us/item ({:.0} items/s, {:.1}x speedup vs unfused), predict_batch_conformal(B=16) = {us_per_item_batch:.3} us/item ({:.0} items/s)",
            1e6 / us_per_item_into,
            us_unfused / us_per_item_into,
            1e6 / us_per_item_batch
        );
    }
}
