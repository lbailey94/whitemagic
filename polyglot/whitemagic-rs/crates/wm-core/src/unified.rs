//! Unified HRR + 5D Spatial Model (Option 2)
//!
//! Maps HRR high-dimensional vectors into the 5D holographic coordinate space,
//! enabling joint symbolic-spatial queries:
//! - Symbolic similarity via HRR cosine similarity (what concepts are alike)
//! - Spatial proximity via 5D Euclidean distance (where memories are stored)
//!
//! The mapping is: project the HRR vector onto 5 orthogonal axes derived
//! from the HRR vector itself, producing (x, y, z, w, v).

use crate::holographic::Coordinate5D;
use crate::hrr::HRR;

/// Map an HRR vector to a 5D holographic coordinate.
///
/// The mapping extracts 5 features from the HRR vector:
/// - X: sum of first third (semantic content projection)
/// - Y: sum of second third (relational projection)
/// - Z: sum of final third (contextual projection)
/// - W: normalized vector entropy (temporal recency proxy)
/// - V: vector peak magnitude (importance/valence proxy)
pub fn hrr_to_coordinate(hrr: &HRR) -> Coordinate5D {
    let dim = hrr.dim();
    if dim == 0 {
        return Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0);
    }
    let third = dim / 3;
    let v = &hrr.vec;

    let x = v.iter().take(third).sum::<f64>() / third.max(1) as f64;
    let y = v.iter().skip(third).take(third).sum::<f64>() / third.max(1) as f64;
    let z = v.iter().skip(2 * third).sum::<f64>() / (dim - 2 * third).max(1) as f64;

    // W: entropy-based temporal proxy
    let sq_sum: f64 = v.iter().map(|&x| x * x).sum();
    let mean_sq = sq_sum / dim as f64;
    let variance = v.iter().map(|&x| (x * x - mean_sq).powi(2)).sum::<f64>() / dim as f64;
    let entropy = (1.0 + variance).ln();
    let w = (entropy / 5.0).clamp(0.0, 1.0);

    // V: peak magnitude as importance proxy
    let peak = v.iter().map(|&x| x.abs()).fold(0.0, f64::max);
    let v_val = (peak * 2.0).clamp(0.0, 1.0);

    Coordinate5D::new(x, y, z, w, v_val)
}

/// Joint query: find memories that are both symbolically similar (HRR cosine)
/// AND spatially close (5D distance).
pub fn joint_query(
    hrrs: &[HRR],
    coords: &[Coordinate5D],
    query_hrr: &HRR,
    query_coord: &Coordinate5D,
    k: usize,
    hrr_weight: f64,
    spatial_weight: f64,
) -> Vec<(usize, f64)> {
    assert_eq!(hrrs.len(), coords.len());

    let mut scored: Vec<(usize, f64)> = hrrs
        .iter()
        .zip(coords.iter())
        .enumerate()
        .map(|(i, (h, c))| {
            let hrr_sim = query_hrr.similarity(h);
            // Convert distance to similarity: 1 / (1 + dist)
            let spatial_sim = 1.0 / (1.0 + query_coord.distance(c));
            let score = hrr_weight * hrr_sim + spatial_weight * spatial_sim;
            (i, score)
        })
        .collect();

    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    scored.into_iter().take(k).collect()
}

/// Encode text into both HRR and 5D simultaneously.
pub fn dual_encode(text: &str, hrr_dim: usize) -> (HRR, Coordinate5D) {
    let hrr = HRR::encode(text, hrr_dim);
    let coord = hrr_to_coordinate(&hrr);
    (hrr, coord)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hrr_to_coord() {
        let h = HRR::encode("hello", 256);
        let c = hrr_to_coordinate(&h);
        assert!(c.v >= 0.0 && c.v <= 1.0);
        assert!(c.w >= 0.0 && c.w <= 1.0);
    }

    #[test]
    fn test_dual_encode_deterministic() {
        let (h1, c1) = dual_encode("test", 128);
        let (h2, c2) = dual_encode("test", 128);
        assert_eq!(h1.vec, h2.vec);
        assert_eq!(c1, c2);
    }

    #[test]
    fn test_joint_query() {
        let hrrs: Vec<HRR> = (0..5).map(|i| HRR::encode(&format!("item {}", i), 64)).collect();
        let coords: Vec<Coordinate5D> = hrrs.iter().map(|h| hrr_to_coordinate(h)).collect();
        let q_hrr = HRR::encode("item 2", 64);
        let q_coord = hrr_to_coordinate(&q_hrr);

        let results = joint_query(&hrrs, &coords, &q_hrr, &q_coord, 3, 0.5, 0.5);
        assert_eq!(results.len(), 3);
        // Item 2 should rank highly (exact match)
        assert!(results.iter().any(|(i, _)| *i == 2));
    }
}
