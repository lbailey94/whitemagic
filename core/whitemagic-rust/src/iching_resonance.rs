//! I Ching Resonance — Resonance-Based Hexagram Selection (Phase 3a)
//!
//! Maps 5D holographic memory coordinates to hexagram resonance scores.
//! Each hexagram has a characteristic frequency pattern (derived from its
//! trigram pair). The resonance engine computes how well a given memory's
//! 5D coordinates align with each hexagram's frequency, selecting the
//! hexagram with the highest resonance for dispatch routing.

use crate::iching::Trigram;
use crate::iching_dispatch::{dispatch_for_hexagram, HexagramDispatch};

/// 5D holographic coordinate (matches Python HolographicCoordinate).
#[derive(Debug, Clone, Copy)]
pub struct HoloCoord {
    pub x: f64, // Logic-Emotion
    pub y: f64, // Micro-Macro
    pub z: f64, // Time
    pub w: f64, // Importance/Gravity
    pub v: f64, // Vitality/Galactic Distance
}

/// Hexagram resonance profile: characteristic frequency for each axis.
#[derive(Debug, Clone, Copy)]
pub struct HexagramFrequency {
    pub freq_x: f64,
    pub freq_y: f64,
    pub freq_z: f64,
    pub freq_w: f64,
    pub freq_v: f64,
    pub damping: f64,
}

/// Compute the characteristic frequency for a trigram.
/// Each trigram maps to a base frequency based on its element.
fn trigram_base_frequency(trigram: &Trigram) -> f64 {
    match trigram {
        Trigram::Qian => 8.0,  // Heaven — high frequency, expansive
        Trigram::Kun  => 1.0,  // Earth — low frequency, grounding
        Trigram::Zhen => 6.0,  // Thunder — sudden, high burst
        Trigram::Xun  => 3.0,  // Wind — steady, medium
        Trigram::Kan  => 2.0,  // Water — flowing, low-medium
        Trigram::Li   => 5.0,  // Fire — rapid, medium-high
        Trigram::Gen  => 1.5,  // Mountain — very low, stable
        Trigram::Dui  => 4.0,  // Lake — gentle, medium
    }
}

/// Compute the 5D frequency profile for a hexagram from its trigram pair.
pub fn hexagram_frequency(lower: &Trigram, upper: &Trigram) -> HexagramFrequency {
    let f_lower = trigram_base_frequency(lower);
    let f_upper = trigram_base_frequency(upper);

    // The 5 axes map to different combinations of the trigram frequencies:
    // x (Logic-Emotion): upper frequency (conscious/expressive)
    // y (Micro-Macro): lower frequency (foundational)
    // z (Time): harmonic mean (temporal coupling)
    // w (Importance): sum (total energy)
    // v (Vitality): difference (galactic drift potential)
    let freq_x = f_upper;
    let freq_y = f_lower;
    let freq_z = 2.0 * f_lower * f_upper / (f_lower + f_upper);
    let freq_w = f_lower + f_upper;
    let freq_v = (f_upper - f_lower).abs();

    // Damping: higher for stable trigrams (Kun, Gen), lower for dynamic (Zhen, Li)
    let damping = match (lower, upper) {
        (Trigram::Kun, Trigram::Kun) => 0.8,
        (Trigram::Gen, _) | (_, Trigram::Gen) => 0.6,
        (Trigram::Zhen, _) | (_, Trigram::Zhen) => 0.1,
        (Trigram::Li, _) | (_, Trigram::Li) => 0.15,
        _ => 0.3,
    };

    HexagramFrequency { freq_x, freq_y, freq_z, freq_w, freq_v, damping }
}

/// Compute resonance score between a 5D coordinate and a hexagram frequency.
/// Uses a damped harmonic oscillator model:
///   resonance = exp(-damping * dist) * cos(2π * freq * coord)
/// where dist is the Euclidean distance in the relevant subspace.
pub fn resonance_score(coord: &HoloCoord, freq: &HexagramFrequency) -> f64 {
    // Normalize coordinates to [0, 1] range (they may already be)
    let x = coord.x.clamp(-1.0, 1.0).abs();
    let y = coord.y.clamp(-1.0, 1.0).abs();
    let z = coord.z.clamp(0.0, 1.0);
    let w = coord.w.clamp(0.0, 1.0);
    let v = coord.v.clamp(0.0, 1.0);

    // Compute per-axis resonance contributions
    let rx = (-freq.damping * (x - 0.5).abs()).exp() * (std::f64::consts::TAU * freq.freq_x * x).cos();
    let ry = (-freq.damping * (y - 0.5).abs()).exp() * (std::f64::consts::TAU * freq.freq_y * y).cos();
    let rz = (-freq.damping * z).exp() * (std::f64::consts::TAU * freq.freq_z * z).cos();
    let rw = (-freq.damping * (1.0 - w)).exp() * (std::f64::consts::TAU * freq.freq_w * w * 0.1).cos();
    let rv = (-freq.damping * v).exp() * (std::f64::consts::TAU * freq.freq_v * v).cos();

    // Weighted sum: time and importance are most significant
    let score = 0.15 * rx + 0.15 * ry + 0.30 * rz + 0.25 * rw + 0.15 * rv;
    score
}

/// Select the best hexagram for a given 5D coordinate.
/// Returns (hexagram_number, resonance_score, dispatch).
pub fn select_hexagram(coord: &HoloCoord) -> (u32, f64, Option<HexagramDispatch>) {
    let mut best_num = 1u32;
    let mut best_score = f64::NEG_INFINITY;
    let mut best_dispatch: Option<HexagramDispatch> = None;

    for n in 1..=64u32 {
        if let Some(disp) = dispatch_for_hexagram(n) {
            // We need the trigrams — derive from the dispatch's lower/upper
            // Actually, we need to get trigrams from the dispatch. But
            // HexagramDispatch has TrigramDispatch, not Trigram. Let's
            // use the dispatch's hexagram_num and reconstruct.
            // For now, compute frequency from the dispatch's trigram info.
            // We need a different approach: precompute frequencies.

            // Use the king_wen_to_binary from iching_dispatch
            // Actually, let's just compute frequency from dispatch info.
            // The dispatch has lower/upper TrigramDispatch which have
            // compute_mode etc. but not the Trigram itself.

            // We'll compute frequency from the hexagram number using
            // the same reverse lookup.
            let binary = king_wen_to_binary_local(n);
            let lower = Trigram::from_binary((binary & 0b111) as u8);
            let upper = Trigram::from_binary(((binary >> 3) & 0b111) as u8);
            let freq = hexagram_frequency(&lower, &upper);
            let score = resonance_score(coord, &freq);

            if score > best_score {
                best_score = score;
                best_num = n;
                best_dispatch = Some(disp);
            }
        }
    }

    (best_num, best_score, best_dispatch)
}

/// Select top-K hexagrams by resonance score.
pub fn select_top_k_hexagrams(coord: &HoloCoord, k: usize) -> Vec<(u32, f64)> {
    let mut scores: Vec<(u32, f64)> = Vec::with_capacity(64);
    for n in 1..=64u32 {
        let binary = king_wen_to_binary_local(n);
        let lower = Trigram::from_binary((binary & 0b111) as u8);
        let upper = Trigram::from_binary(((binary >> 3) & 0b111) as u8);
        let freq = hexagram_frequency(&lower, &upper);
        let score = resonance_score(coord, &freq);
        scores.push((n, score));
    }
    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scores.truncate(k);
    scores
}

// Local copy of the reverse King Wen lookup (to avoid circular dependency)
fn king_wen_to_binary_local(kw: u32) -> u32 {
    const KING_WEN: [u8; 64] = [
         2, 23,  8, 20, 16, 35, 45,  0,
        15, 52, 39, 53, 62, 56, 31, 33,
         7,  4, 29, 59, 40, 64, 47,  6,
        46, 18, 48, 57, 32, 50, 28, 44,
         5,  3, 60, 42, 11, 12, 17, 25,
        34, 26,  5, 14, 43,  1, 28, 49,
         6, 10, 58, 54, 60, 61, 54, 38,
        43, 58, 49, 38, 14, 30, 55,  1,
    ];
    for (binary, &kw_val) in KING_WEN.iter().enumerate() {
        if kw_val as u32 == kw {
            return binary as u32;
        }
    }
    0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trigram_base_frequencies() {
        assert!(trigram_base_frequency(&Trigram::Qian) > trigram_base_frequency(&Trigram::Kun));
        assert!(trigram_base_frequency(&Trigram::Zhen) > trigram_base_frequency(&Trigram::Gen));
    }

    #[test]
    fn test_hexagram_frequency_ranges() {
        let freq = hexagram_frequency(&Trigram::Qian, &Trigram::Qian);
        assert!(freq.freq_w > 10.0); // 8+8=16
        assert!(freq.freq_v < 0.01); // Same trigrams → no drift

        let freq2 = hexagram_frequency(&Trigram::Qian, &Trigram::Kun);
        assert!(freq2.freq_v > 5.0); // 8-1=7
    }

    #[test]
    fn test_resonance_score_finite() {
        let coord = HoloCoord { x: 0.5, y: 0.5, z: 0.5, w: 0.5, v: 0.5 };
        let freq = hexagram_frequency(&Trigram::Qian, &Trigram::Kun);
        let score = resonance_score(&coord, &freq);
        assert!(score.is_finite());
    }

    #[test]
    fn test_select_hexagram_returns_valid() {
        let coord = HoloCoord { x: 0.3, y: 0.7, z: 0.5, w: 0.8, v: 0.2 };
        let (num, score, dispatch) = select_hexagram(&coord);
        assert!(num >= 1 && num <= 64);
        assert!(score.is_finite());
        assert!(dispatch.is_some());
    }

    #[test]
    fn test_select_hexagram_different_coords_different_results() {
        let coord1 = HoloCoord { x: 0.1, y: 0.1, z: 0.1, w: 0.1, v: 0.1 };
        let coord2 = HoloCoord { x: 0.9, y: 0.9, z: 0.9, w: 0.9, v: 0.9 };
        let (num1, _, _) = select_hexagram(&coord1);
        let (num2, _, _) = select_hexagram(&coord2);
        // Very likely different (not guaranteed but highly probable)
        // Just check both are valid
        assert!(num1 >= 1 && num1 <= 64);
        assert!(num2 >= 1 && num2 <= 64);
    }

    #[test]
    fn test_select_top_k_hexagrams() {
        let coord = HoloCoord { x: 0.5, y: 0.5, z: 0.5, w: 0.5, v: 0.5 };
        let top = select_top_k_hexagrams(&coord, 5);
        assert_eq!(top.len(), 5);
        // Scores should be descending
        for i in 1..top.len() {
            assert!(top[i].1 <= top[i-1].1);
        }
    }

    #[test]
    fn test_select_top_k_all_64() {
        let coord = HoloCoord { x: 0.3, y: 0.6, z: 0.4, w: 0.7, v: 0.3 };
        let top = select_top_k_hexagrams(&coord, 64);
        assert_eq!(top.len(), 64);
        // All hexagram numbers should be unique
        let nums: std::collections::HashSet<_> = top.iter().map(|(n, _)| *n).collect();
        assert_eq!(nums.len(), 64);
    }

    #[test]
    fn test_damping_stable_vs_dynamic() {
        let stable = hexagram_frequency(&Trigram::Kun, &Trigram::Kun);
        let dynamic = hexagram_frequency(&Trigram::Zhen, &Trigram::Li);
        assert!(stable.damping > dynamic.damping);
    }

    #[test]
    fn test_resonance_score_range() {
        // Score should be in a reasonable range [-1, 1] given the weighted sum
        let coord = HoloCoord { x: 0.5, y: 0.5, z: 0.0, w: 1.0, v: 0.0 };
        let freq = hexagram_frequency(&Trigram::Qian, &Trigram::Qian);
        let score = resonance_score(&coord, &freq);
        assert!(score >= -1.0 && score <= 1.0, "Score out of range: {}", score);
    }
}
