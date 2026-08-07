//! Holographic Coordinates — 6D spatial-temporal memory addressing
//!
//! Each memory has 6D holographic coordinates enabling spatial queries
//! via LMDB cursor range scans. Preserved from v2.
//!
//! Also provides `Coordinate5D` — a 5D holographic coordinate system
//! (x, y, z, w, v) ported from v2 for spatial memory indexing and
//! constellation clustering.

use serde::{Deserialize, Serialize};

/// 6D holographic coordinate for a memory.
///
/// Stored as a composite LMDB key enabling spatial range queries.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HolographicCoords {
    /// Which of 14 galaxies (0-13)
    pub galaxy: u8,
    /// Spatial sector within galaxy (0-65535)
    pub sector: u16,
    /// Radial distance from center (0.0 = center, 1.0 = edge)
    pub radial: f32,
    /// Angular position in radians (0 to 2π)
    pub angular: f32,
    /// Temporal coordinate (Unix timestamp in microseconds)
    pub temporal: u64,
    /// Consciousness resonance frequency (0.0 to 1.0)
    pub consciousness: f32,
}

impl HolographicCoords {
    /// Create new coordinates for a memory in the given galaxy.
    #[must_use]
    pub fn new(galaxy: crate::Galaxy, temporal: u64) -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros() as u64;
        Self {
            galaxy: galaxy as u8,
            sector: 0,
            radial: 0.5,
            angular: 0.0,
            temporal: temporal.max(now),
            consciousness: 0.5,
        }
    }

    /// Encode as a sortable composite key for LMDB.
    ///
    /// Format: galaxy(1) + sector(2) + temporal(8) + radial(4) + angular(4) + consciousness(4)
    /// = 23 bytes total
    #[must_use]
    pub fn encode_key(&self) -> Vec<u8> {
        let mut key = Vec::with_capacity(23);
        key.push(self.galaxy);
        key.extend_from_slice(&self.sector.to_be_bytes());
        key.extend_from_slice(&self.temporal.to_be_bytes());
        key.extend_from_slice(&self.radial.to_be_bytes());
        key.extend_from_slice(&self.angular.to_be_bytes());
        key.extend_from_slice(&self.consciousness.to_be_bytes());
        key
    }

    /// Decode from a composite key.
    #[must_use]
    pub fn decode_key(key: &[u8]) -> Option<Self> {
        if key.len() < 23 {
            return None;
        }
        Some(Self {
            galaxy: key[0],
            sector: u16::from_be_bytes([key[1], key[2]]),
            temporal: u64::from_be_bytes([
                key[3], key[4], key[5], key[6], key[7], key[8], key[9], key[10],
            ]),
            radial: f32::from_be_bytes([key[11], key[12], key[13], key[14]]),
            angular: f32::from_be_bytes([key[15], key[16], key[17], key[18]]),
            consciousness: f32::from_be_bytes([key[19], key[20], key[21], key[22]]),
        })
    }

    /// Compute the galactic distance between two coordinates.
    ///
    /// This is a weighted distance metric combining radial, angular,
    /// temporal, and consciousness dimensions.
    #[must_use]
    pub fn distance_to(&self, other: &Self) -> f32 {
        let radial_diff = (self.radial - other.radial).abs();
        let angular_diff = {
            let d = (self.angular - other.angular).abs();
            let pi2 = std::f32::consts::TAU;
            d.min(pi2 - d) / pi2 // normalized to [0, 0.5]
        };
        let temporal_diff = {
            let max_ts = self.temporal.max(other.temporal);
            let min_ts = self.temporal.min(other.temporal);
            if max_ts == 0 {
                0.0
            } else {
                (max_ts - min_ts) as f32 / max_ts as f32
            }
        };
        let consciousness_diff = (self.consciousness - other.consciousness).abs();

        // Weighted additive distance (v2 used multiplicative which was buggy)
        consciousness_diff.mul_add(
            0.2,
            radial_diff.mul_add(0.3, angular_diff * 0.2) + temporal_diff * 0.3,
        )
    }
}

// ── 5D Holographic Coordinate System ─────────────────────────────────

/// Spatial zone within the holographic memory space.
///
/// Determines the radial region a coordinate falls into, used by
/// constellation detection for clustering nearby memories.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Zone {
    /// Innermost zone (radial < 0.2) — core memories
    Core,
    /// Inner ring (0.2 ≤ radial < 0.4) — frequently accessed
    InnerRing,
    /// Middle ring (0.4 ≤ radial < 0.6) — standard memories
    MidRing,
    /// Outer ring (0.6 ≤ radial < 0.8) — peripheral memories
    OuterRing,
    /// Far edge (radial ≥ 0.8) — fading/archival memories
    FarEdge,
}

impl Zone {
    /// Classify a radial value into a zone.
    #[must_use]
    pub fn from_radial(radial: f32) -> Self {
        match radial {
            r if r < 0.2 => Self::Core,
            r if r < 0.4 => Self::InnerRing,
            r if r < 0.6 => Self::MidRing,
            r if r < 0.8 => Self::OuterRing,
            _ => Self::FarEdge,
        }
    }

    /// Numeric zone index (0 = Core, 4 = `FarEdge`).
    #[must_use]
    pub const fn index(self) -> u8 {
        self as u8
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Core => "core",
            Self::InnerRing => "inner_ring",
            Self::MidRing => "mid_ring",
            Self::OuterRing => "outer_ring",
            Self::FarEdge => "far_edge",
        }
    }
}

/// 5D holographic coordinate for spatial memory indexing.
///
/// Ported from v2's Rust implementation. Each dimension is normalized
/// to [0.0, 1.0] and derived deterministically from content via
/// `Coordinate5D::encode(text)`.
///
/// - **x**: semantic axis (content hash byte 0-3)
/// - **y**: semantic axis (content hash byte 4-7)
/// - **z**: semantic axis (content hash byte 8-11)
/// - **w**: temporal weight (recency-based)
/// - **v**: consciousness resonance (importance-based)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Coordinate5D {
    /// Semantic axis X (content-derived)
    pub x: f32,
    /// Semantic axis Y (content-derived)
    pub y: f32,
    /// Semantic axis Z (content-derived)
    pub z: f32,
    /// Temporal weight (0 = old, 1 = recent)
    pub w: f32,
    /// Consciousness resonance (0 = low importance, 1 = high)
    pub v: f32,
}

impl Coordinate5D {
    /// Create a coordinate from explicit values.
    #[must_use]
    pub const fn new(x: f32, y: f32, z: f32, w: f32, v: f32) -> Self {
        Self {
            x: x.clamp(0.0, 1.0),
            y: y.clamp(0.0, 1.0),
            z: z.clamp(0.0, 1.0),
            w: w.clamp(0.0, 1.0),
            v: v.clamp(0.0, 1.0),
        }
    }

    /// Deterministically encode text content into a 5D coordinate.
    ///
    /// Uses SHA-256 of the text to derive x, y, z dimensions.
    /// The w (temporal) and v (consciousness) dimensions default to
    /// 0.5 and should be updated when the memory is created with
    /// actual temporal and importance data.
    #[must_use]
    pub fn encode(text: &str) -> Self {
        use sha2::{Digest, Sha256};
        let hash = Sha256::digest(text.as_bytes());
        let x = u32::from_be_bytes([hash[0], hash[1], hash[2], hash[3]]) as f32 / u32::MAX as f32;
        let y = u32::from_be_bytes([hash[4], hash[5], hash[6], hash[7]]) as f32 / u32::MAX as f32;
        let z = u32::from_be_bytes([hash[8], hash[9], hash[10], hash[11]]) as f32 / u32::MAX as f32;
        Self {
            x,
            y,
            z,
            w: 0.5,
            v: 0.5,
        }
    }

    /// Create a coordinate from pre-computed semantic scores.
    ///
    /// Unlike `encode()` which uses SHA-256 hash bytes (semantically meaningless),
    /// this constructor accepts x/y/z values derived from semantic analysis of
    /// the content (e.g., TF-IDF anchor projection). This enables similar content
    /// to produce similar coordinates.
    #[must_use]
    pub const fn from_semantic(
        x: f32,
        y: f32,
        z: f32,
        temporal_weight: f32,
        importance: f32,
    ) -> Self {
        Self {
            x: x.clamp(0.0, 1.0),
            y: y.clamp(0.0, 1.0),
            z: z.clamp(0.0, 1.0),
            w: temporal_weight.clamp(0.0, 1.0),
            v: importance.clamp(0.0, 1.0),
        }
    }

    /// Encode text with temporal and importance context.
    #[must_use]
    pub fn encode_with_context(text: &str, temporal_weight: f32, importance: f32) -> Self {
        let mut coord = Self::encode(text);
        coord.w = temporal_weight.clamp(0.0, 1.0);
        coord.v = importance.clamp(0.0, 1.0);
        coord
    }

    /// Euclidean distance in 5D space.
    #[must_use]
    pub fn distance_to(&self, other: &Self) -> f32 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        let dz = self.z - other.z;
        let dw = self.w - other.w;
        let dv = self.v - other.v;
        dv.mul_add(dv, dw.mul_add(dw, dz.mul_add(dz, dx.mul_add(dx, dy * dy))))
            .sqrt()
    }

    /// Weighted distance — emphasizes semantic dimensions (x, y, z)
    /// over temporal (w) and consciousness (v).
    #[must_use]
    pub fn semantic_distance_to(&self, other: &Self) -> f32 {
        let dx = (self.x - other.x) * 0.35;
        let dy = (self.y - other.y) * 0.35;
        let dz = (self.z - other.z) * 0.20;
        let dw = (self.w - other.w) * 0.05;
        let dv = (self.v - other.v) * 0.05;
        (dx * dx + dy * dy + dz * dz + dw * dw + dv * dv).sqrt()
    }

    /// Which zone this coordinate falls into, based on radial distance
    /// from the center (0.5, 0.5, 0.5, 0.5, 0.5).
    #[must_use]
    pub fn zone(&self) -> Zone {
        let center = Self::new(0.5, 0.5, 0.5, 0.5, 0.5);
        let radial = self.distance_to(&center) / 1.118; // sqrt(5 * 0.25) = max distance
        Zone::from_radial(radial)
    }

    /// Encode as a sortable composite key for LMDB (20 bytes).
    #[must_use]
    pub fn encode_key(&self) -> Vec<u8> {
        let mut key = Vec::with_capacity(20);
        key.extend_from_slice(&self.x.to_be_bytes());
        key.extend_from_slice(&self.y.to_be_bytes());
        key.extend_from_slice(&self.z.to_be_bytes());
        key.extend_from_slice(&self.w.to_be_bytes());
        key.extend_from_slice(&self.v.to_be_bytes());
        key
    }

    /// Decode from a composite key.
    #[must_use]
    pub fn decode_key(key: &[u8]) -> Option<Self> {
        if key.len() < 20 {
            return None;
        }
        Some(Self {
            x: f32::from_be_bytes([key[0], key[1], key[2], key[3]]),
            y: f32::from_be_bytes([key[4], key[5], key[6], key[7]]),
            z: f32::from_be_bytes([key[8], key[9], key[10], key[11]]),
            w: f32::from_be_bytes([key[12], key[13], key[14], key[15]]),
            v: f32::from_be_bytes([key[16], key[17], key[18], key[19]]),
        })
    }
}

/// Find nearby coordinates within a radius.
///
/// Returns indices of memories whose 5D coordinate is within `radius`
/// of the `center` coordinate, sorted by distance (nearest first).
#[must_use]
pub fn find_nearby(
    center: &Coordinate5D,
    candidates: &[(usize, Coordinate5D)],
    radius: f32,
) -> Vec<(usize, f32)> {
    let mut results: Vec<(usize, f32)> = candidates
        .iter()
        .map(|(idx, coord)| (*idx, center.distance_to(coord)))
        .filter(|(_, dist)| *dist <= radius)
        .collect();
    results.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
    results
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn coords_encode_decode_roundtrip() {
        let coords = HolographicCoords {
            galaxy: 3,
            sector: 42,
            radial: 0.75,
            angular: 1.5,
            temporal: 1700000000,
            consciousness: 0.8,
        };
        let key = coords.encode_key();
        let decoded = HolographicCoords::decode_key(&key).unwrap();
        assert_eq!(coords.galaxy, decoded.galaxy);
        assert_eq!(coords.sector, decoded.sector);
        assert_eq!(coords.temporal, decoded.temporal);
        assert!((coords.radial - decoded.radial).abs() < f32::EPSILON);
    }

    #[test]
    fn coords_distance_identical() {
        let coords = HolographicCoords {
            galaxy: 0,
            sector: 0,
            radial: 0.5,
            angular: 0.0,
            temporal: 1000,
            consciousness: 0.5,
        };
        assert_eq!(coords.distance_to(&coords), 0.0);
    }

    #[test]
    fn coords_distance_different_galaxies() {
        let a = HolographicCoords {
            galaxy: 0,
            sector: 0,
            radial: 0.5,
            angular: 0.0,
            temporal: 1000,
            consciousness: 0.5,
        };
        let b = HolographicCoords {
            galaxy: 1,
            sector: 0,
            radial: 0.5,
            angular: 0.0,
            temporal: 1000,
            consciousness: 0.5,
        };
        // Same coordinates except galaxy — distance should be 0
        // (galaxy is used for routing, not distance)
        assert_eq!(a.distance_to(&b), 0.0);
    }

    // ── Coordinate5D Tests ────────────────────────────────────────────

    #[test]
    fn coord5d_encode_deterministic() {
        let a = Coordinate5D::encode("hello world");
        let b = Coordinate5D::encode("hello world");
        assert_eq!(a, b);
    }

    #[test]
    fn coord5d_encode_different_text() {
        let a = Coordinate5D::encode("hello world");
        let b = Coordinate5D::encode("goodbye world");
        assert_ne!(a, b);
    }

    #[test]
    fn coord5d_encode_in_range() {
        let coord = Coordinate5D::encode("test content");
        assert!(coord.x >= 0.0 && coord.x <= 1.0);
        assert!(coord.y >= 0.0 && coord.y <= 1.0);
        assert!(coord.z >= 0.0 && coord.z <= 1.0);
    }

    #[test]
    fn coord5d_encode_with_context() {
        let coord = Coordinate5D::encode_with_context("test", 0.8, 0.9);
        assert!((coord.w - 0.8).abs() < f32::EPSILON);
        assert!((coord.v - 0.9).abs() < f32::EPSILON);
    }

    #[test]
    fn coord5d_distance_identical() {
        let coord = Coordinate5D::encode("test");
        assert!((coord.distance_to(&coord)).abs() < f32::EPSILON);
    }

    #[test]
    fn coord5d_distance_positive() {
        let a = Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0);
        let b = Coordinate5D::new(1.0, 1.0, 1.0, 1.0, 1.0);
        let dist = a.distance_to(&b);
        assert!(dist > 0.0);
        // sqrt(5) ≈ 2.236
        assert!((dist - 2.236068).abs() < 0.001);
    }

    #[test]
    fn coord5d_semantic_distance_weighted() {
        let a = Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0);
        let b = Coordinate5D::new(1.0, 0.0, 0.0, 0.0, 0.0);
        let c = Coordinate5D::new(0.0, 0.0, 0.0, 1.0, 0.0);
        let dist_x = a.semantic_distance_to(&b);
        let dist_w = a.semantic_distance_to(&c);
        // x-axis should have more weight than w-axis
        assert!(dist_x > dist_w);
    }

    #[test]
    fn coord5d_key_roundtrip() {
        let coord = Coordinate5D::new(0.1, 0.2, 0.3, 0.4, 0.5);
        let key = coord.encode_key();
        let decoded = Coordinate5D::decode_key(&key).unwrap();
        assert!((coord.x - decoded.x).abs() < f32::EPSILON);
        assert!((coord.y - decoded.y).abs() < f32::EPSILON);
        assert!((coord.z - decoded.z).abs() < f32::EPSILON);
        assert!((coord.w - decoded.w).abs() < f32::EPSILON);
        assert!((coord.v - decoded.v).abs() < f32::EPSILON);
    }

    #[test]
    fn zone_from_radial() {
        assert_eq!(Zone::from_radial(0.1), Zone::Core);
        assert_eq!(Zone::from_radial(0.3), Zone::InnerRing);
        assert_eq!(Zone::from_radial(0.5), Zone::MidRing);
        assert_eq!(Zone::from_radial(0.7), Zone::OuterRing);
        assert_eq!(Zone::from_radial(0.9), Zone::FarEdge);
    }

    #[test]
    fn zone_name_and_index() {
        assert_eq!(Zone::Core.name(), "core");
        assert_eq!(Zone::Core.index(), 0);
        assert_eq!(Zone::FarEdge.name(), "far_edge");
        assert_eq!(Zone::FarEdge.index(), 4);
    }

    #[test]
    fn coord5d_zone_classification() {
        let center = Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5);
        assert_eq!(center.zone(), Zone::Core);
        let edge = Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0);
        assert_eq!(edge.zone(), Zone::FarEdge);
    }

    #[test]
    fn find_nearby_returns_sorted() {
        let center = Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5);
        let candidates = vec![
            (0, Coordinate5D::new(0.9, 0.5, 0.5, 0.5, 0.5)), // far
            (1, Coordinate5D::new(0.51, 0.5, 0.5, 0.5, 0.5)), // near
            (2, Coordinate5D::new(0.0, 0.0, 0.0, 0.0, 0.0)), // very far
            (3, Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5)), // identical
        ];
        let results = find_nearby(&center, &candidates, 1.0);
        assert_eq!(results.len(), 3); // excludes the very far one
        assert_eq!(results[0].0, 3); // nearest is identical
        assert_eq!(results[1].0, 1); // next is near
        assert_eq!(results[2].0, 0); // farthest within radius
    }

    #[test]
    fn find_nearby_empty_for_tiny_radius() {
        let center = Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5);
        let candidates = vec![(0, Coordinate5D::new(0.9, 0.5, 0.5, 0.5, 0.5))];
        let results = find_nearby(&center, &candidates, 0.01);
        assert!(results.is_empty());
    }
}
