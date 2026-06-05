//! 5D Holographic Memory Coordinates
//!
//! Spatial indexing with X, Y, Z, W (recency), V (valence/importance).
//! Galactic zones based on V coordinate.

use std::f64;

/// 5D holographic coordinate (X, Y, Z, W, V).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Coordinate5D {
    pub x: f64, // spatial X
    pub y: f64, // spatial Y
    pub z: f64, // spatial Z
    pub w: f64, // temporal recency (0-1)
    pub v: f64, // valence / importance (0-1)
}

/// Galactic zone based on V coordinate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Zone {
    Core,
    InnerRing,
    MidRing,
    OuterRing,
    FarEdge,
}

impl Zone {
    pub fn from_valence(v: f64) -> Self {
        match v {
            v if v < 0.2 => Zone::Core,
            v if v < 0.4 => Zone::InnerRing,
            v if v < 0.6 => Zone::MidRing,
            v if v < 0.8 => Zone::OuterRing,
            _ => Zone::FarEdge,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Zone::Core => "CORE",
            Zone::InnerRing => "INNER_RING",
            Zone::MidRing => "MID_RING",
            Zone::OuterRing => "OUTER_RING",
            Zone::FarEdge => "FAR_EDGE",
        }
    }
}

impl Coordinate5D {
    pub fn new(x: f64, y: f64, z: f64, w: f64, v: f64) -> Self {
        Self { x, y, z, w, v: v.clamp(0.0, 1.0) }
    }

    pub fn zone(&self) -> Zone {
        Zone::from_valence(self.v)
    }

    /// Encode a text string into a 5D holographic coordinate.
    /// Uses the string's hash as a deterministic seed for reproducibility.
    pub fn encode(text: &str) -> Self {
        let s = hash_djb2(text).abs() as i64;
        let vals = lcg_sequence(s, 768);
        let norm = vals.iter().map(|v| v * v).sum::<f64>().sqrt();
        let nvec: Vec<f64> = if norm > 0.0 {
            vals.iter().map(|v| v / norm).collect()
        } else {
            vals
        };

        let x = nvec.iter().take(256).sum::<f64>() / 16.0;
        let y = nvec.iter().skip(256).take(256).sum::<f64>() / 16.0;
        let z = nvec.iter().skip(512).sum::<f64>() / 16.0;

        let w = (text.len() as f64 / 1000.0).clamp(0.0, 1.0);

        let caps = text.chars().filter(|c| c.is_ascii_uppercase()).count() as f64;
        let punct = text.chars().filter(|c| "!?.;:".contains(*c)).count() as f64;
        let v = ((caps + 2.0 * punct) / text.len().max(1) as f64).clamp(0.0, 1.0);

        Self { x, y, z, w, v }
    }

    /// Euclidean distance in 5D holographic space.
    /// V (valence) gets 2× weight because zone transitions matter more.
    pub fn distance(&self, other: &Self) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        let dz = self.z - other.z;
        let dw = self.w - other.w;
        let dv = 2.0 * (self.v - other.v);
        (dx * dx + dy * dy + dz * dz + dw * dw + dv * dv).sqrt()
    }

    /// Locality-sensitive hash: map coordinate to a discrete hash bucket.
    pub fn lsh_hash(&self, bins: usize) -> u64 {
        let bx = ((self.x + 1.0) / 2.0 * bins as f64).clamp(0.0, bins as f64 - 1.0) as u64;
        let by = ((self.y + 1.0) / 2.0 * bins as f64).clamp(0.0, bins as f64 - 1.0) as u64;
        let bz = ((self.z + 1.0) / 2.0 * bins as f64).clamp(0.0, bins as f64 - 1.0) as u64;
        let bw = ((self.w + 1.0) / 2.0 * bins as f64).clamp(0.0, bins as f64 - 1.0) as u64;
        let bv = ((self.v + 1.0) / 2.0 * bins as f64).clamp(0.0, bins as f64 - 1.0) as u64;

        // 5D Morton-like encoding
        bx + by * bins as u64
            + bz * (bins as u64).pow(2)
            + bw * (bins as u64).pow(3)
            + bv * (bins as u64).pow(4)
    }
}

/// Merge multiple coordinates into a weighted centroid.
pub fn merge_coords(coords: &[Coordinate5D], weights: &[f64]) -> Coordinate5D {
    let n = coords.len();
    if n == 0 {
        return Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0);
    }
    let w: Vec<f64> = if weights.is_empty() {
        vec![1.0 / n as f64; n]
    } else {
        let total: f64 = weights.iter().sum();
        weights.iter().map(|w| w / total).collect()
    };

    let wx = coords.iter().zip(w.iter()).map(|(c, w)| c.x * w).sum::<f64>();
    let wy = coords.iter().zip(w.iter()).map(|(c, w)| c.y * w).sum::<f64>();
    let wz = coords.iter().zip(w.iter()).map(|(c, w)| c.z * w).sum::<f64>();
    let ww = coords.iter().zip(w.iter()).map(|(c, w)| c.w * w).sum::<f64>();
    let wv = coords.iter().zip(w.iter()).map(|(c, w)| c.v * w).sum::<f64>();

    Coordinate5D::new(wx, wy, wz, ww, wv)
}

/// Brute-force k-nearest neighbors.
pub fn nearest_neighbors(query: &Coordinate5D, coords: &[Coordinate5D], k: usize) -> Vec<(usize, f64)> {
    let mut indexed: Vec<(usize, f64)> = coords
        .iter()
        .enumerate()
        .map(|(i, c)| (i, query.distance(c)))
        .collect();
    indexed.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
    indexed.into_iter().take(k).collect()
}

/// Union-Find (disjoint set) for constellation detection.
struct UnionFind {
    parent: Vec<usize>,
    rank: Vec<usize>,
}

impl UnionFind {
    fn new(n: usize) -> Self {
        Self {
            parent: (0..n).collect(),
            rank: vec![0; n],
        }
    }

    fn find(&mut self, x: usize) -> usize {
        if self.parent[x] != x {
            self.parent[x] = self.find(self.parent[x]);
        }
        self.parent[x]
    }

    fn union(&mut self, x: usize, y: usize) {
        let px = self.find(x);
        let py = self.find(y);
        if px == py {
            return;
        }
        match self.rank[px].cmp(&self.rank[py]) {
            std::cmp::Ordering::Less => self.parent[px] = py,
            std::cmp::Ordering::Greater => self.parent[py] = px,
            std::cmp::Ordering::Equal => {
                self.parent[py] = px;
                self.rank[px] += 1;
            }
        }
    }
}

/// Detect constellations (clusters) using Union-Find.
/// Returns a list of cluster member indices.
pub fn detect_constellations(coords: &[Coordinate5D], threshold: f64, min_size: usize) -> Vec<Vec<usize>> {
    let n = coords.len();
    if n < 2 {
        return vec![];
    }
    let mut uf = UnionFind::new(n);

    for i in 0..n.saturating_sub(1) {
        for j in (i + 1)..n {
            if coords[i].distance(&coords[j]) <= threshold {
                uf.union(i, j);
            }
        }
    }

    use std::collections::HashMap;
    let mut groups: HashMap<usize, Vec<usize>> = HashMap::new();
    for i in 0..n {
        let root = uf.find(i);
        groups.entry(root).or_default().push(i);
    }

    groups
        .into_values()
        .filter(|g| g.len() >= min_size)
        .collect()
}

/// Deterministic pseudo-random sequence from a seed.
fn lcg_sequence(seed: i64, count: usize) -> Vec<f64> {
    let mut s = seed.abs() % 2147483647;
    (0..count)
        .map(|_| {
            s = (1103515245i64.wrapping_mul(s).wrapping_add(12345)) % 2147483647;
            s as f64 / 2147483647.0
        })
        .collect()
}

/// Compute string hash for seeding (djb2-like).
fn hash_djb2(text: &str) -> i32 {
    let mut h: i32 = 5381;
    for c in text.chars() {
        h = h.wrapping_shl(5).wrapping_add(h).wrapping_add(c as i32);
    }
    h
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_deterministic() {
        let c1 = Coordinate5D::encode("hello world");
        let c2 = Coordinate5D::encode("hello world");
        assert_eq!(c1, c2);
    }

    #[test]
    fn test_zone_mapping() {
        assert_eq!(Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.1).zone(), Zone::Core);
        assert_eq!(Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.3).zone(), Zone::InnerRing);
        assert_eq!(Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.5).zone(), Zone::MidRing);
        assert_eq!(Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.7).zone(), Zone::OuterRing);
        assert_eq!(Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.9).zone(), Zone::FarEdge);
    }

    #[test]
    fn test_distance() {
        let a = Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0);
        let b = Coordinate5D::new(3.0, 4.0, 0.0, 0.0, 0.0);
        assert!((a.distance(&b) - 5.0).abs() < 1e-9);
    }

    #[test]
    fn test_merge() {
        let a = Coordinate5D::new(1.0, 2.0, 3.0, 0.5, 0.5);
        let b = Coordinate5D::new(3.0, 4.0, 5.0, 0.5, 0.5);
        let m = merge_coords(&[a, b], &[0.5, 0.5]);
        assert!((m.x - 2.0).abs() < 1e-9);
        assert!((m.y - 3.0).abs() < 1e-9);
    }

    #[test]
    fn test_nearest_neighbors() {
        let pts: Vec<Coordinate5D> = (0..10)
            .map(|i| Coordinate5D::new(i as f64, 0.0, 0.0, 0.0, 0.0))
            .collect();
        let q = Coordinate5D::new(4.5, 0.0, 0.0, 0.0, 0.0);
        let nn = nearest_neighbors(&q, &pts, 3);
        assert_eq!(nn.len(), 3);
        assert_eq!(nn[0].0, 4);
        assert_eq!(nn[1].0, 5);
        assert_eq!(nn[2].0, 3);
    }

    #[test]
    fn test_constellations() {
        let pts: Vec<Coordinate5D> = vec![
            Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0),
            Coordinate5D::new(0.1, 0.0, 0.0, 0.0, 0.0),
            Coordinate5D::new(0.2, 0.0, 0.0, 0.0, 0.0),
            Coordinate5D::new(10.0, 0.0, 0.0, 0.0, 0.0),
            Coordinate5D::new(10.1, 0.0, 0.0, 0.0, 0.0),
        ];
        let clusters = detect_constellations(&pts, 0.8, 2);
        assert_eq!(clusters.len(), 2);
    }

    #[test]
    fn test_lsh_hash() {
        let c = Coordinate5D::encode("test");
        let h = c.lsh_hash(8);
        assert!(h < 8u64.pow(5));
    }
}
