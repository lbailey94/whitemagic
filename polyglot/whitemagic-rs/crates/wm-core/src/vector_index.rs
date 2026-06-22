//! Vector index operations: cosine similarity, brute-force top-k, batch search.

/// Cosine similarity between two f64 vectors.
pub fn cosine_similarity(a: &[f64], b: &[f64]) -> f64 {
    assert_eq!(a.len(), b.len(), "Vectors must have same dimension");
    let mut dot = 0.0;
    let mut mag_a = 0.0;
    let mut mag_b = 0.0;
    for i in 0..a.len() {
        dot += a[i] * b[i];
        mag_a += a[i] * a[i];
        mag_b += b[i] * b[i];
    }
    let denom = (mag_a * mag_b).sqrt();
    if denom > 0.0 {
        dot / denom
    } else {
        0.0
    }
}

/// Brute-force top-k search by cosine similarity.
/// Returns (index, score) pairs, sorted descending by score.
pub fn topk_search(vectors: &[Vec<f64>], query: &[f64], k: usize) -> Vec<(usize, f64)> {
    let mut scores: Vec<(usize, f64)> = vectors
        .iter()
        .enumerate()
        .map(|(i, v)| (i, cosine_similarity(v, query)))
        .collect();
    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    scores.into_iter().take(k).collect()
}

/// Batch cosine similarity between query and all vectors.
pub fn batch_cosine(vectors: &[Vec<f64>], query: &[f64]) -> Vec<f64> {
    vectors.iter().map(|v| cosine_similarity(v, query)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_identical() {
        let a = vec![1.0, 0.0, 0.0];
        assert!((cosine_similarity(&a, &a) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_cosine_orthogonal() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        assert!(cosine_similarity(&a, &b).abs() < 1e-9);
    }

    #[test]
    fn test_topk() {
        let vecs = vec![
            vec![1.0, 0.0, 0.0],
            vec![0.9, 0.1, 0.0],
            vec![0.0, 1.0, 0.0],
            vec![0.1, 0.9, 0.0],
        ];
        let q = vec![1.0, 0.0, 0.0];
        let top = topk_search(&vecs, &q, 2);
        assert_eq!(top.len(), 2);
        assert_eq!(top[0].0, 0);
        assert_eq!(top[1].0, 1);
    }

    #[test]
    fn test_batch() {
        let vecs = vec![vec![1.0, 0.0], vec![0.0, 1.0], vec![0.5, 0.5]];
        let q = vec![1.0, 0.0];
        let scores = batch_cosine(&vecs, &q);
        assert_eq!(scores.len(), 3);
        assert!((scores[0] - 1.0).abs() < 1e-9);
        assert!(scores[1].abs() < 1e-9);
    }
}
