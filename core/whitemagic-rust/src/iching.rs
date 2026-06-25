//! I Ching Engine — Expanded (Phase 2a)
//!
//! Features:
//! - Stochastic casting: 3-coin method and yarrow stalk method
//! - Deterministic hash casting (for testing/replay)
//! - Trigram decomposition (upper/lower)
//! - Second hexagram from moving lines
//! - King Wen sequence lookup
//! - Hexagram metadata (names, trigrams)
//! - PyO3 wrapper (`iching_cast`) matching Python expectations

use rand::Rng;
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

// ---------------------------------------------------------------------------
// King Wen sequence: maps binary pattern (0-63) → King Wen number (1-64)
// Binary: bit 0 = bottom line, bit 5 = top line. 1=yang, 0=yin.
// ---------------------------------------------------------------------------

const KING_WEN: [u8; 64] = [
     2, 24,  7, 19, 15, 36, 46, 11,
    16, 51, 40, 54, 62, 55, 32, 34,
     8,  3, 29, 60, 39, 63, 48,  5,
    45, 17, 47, 58, 31, 49, 28, 43,
    23, 27,  4, 41, 52, 22, 18, 26,
    35, 21, 64, 38, 56, 30, 50, 14,
    20, 42, 59, 61, 53, 37, 57,  9,
    12, 25,  6, 10, 33, 13, 44,  1,
];

/// Convert binary pattern (0-63) to King Wen hexagram number (1-64).
fn binary_to_king_wen(binary: u32) -> u32 {
    let idx = (binary & 63) as usize;
    // Use the canonical table; fallback to binary+1 if 0 (shouldn't happen)
    let kw = KING_WEN[idx];
    if kw == 0 { binary + 1 } else { kw as u32 }
}

// ---------------------------------------------------------------------------
// Trigram enum
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Trigram {
    Qian, // ☰ Heaven, Creative
    Kun,  // ☷ Earth, Receptive
    Zhen, // ☳ Thunder, Shock
    Xun,  // ☴ Wind, Penetrating
    Kan,  // ☵ Water, Abysmal
    Li,   // ☲ Fire, Clinging
    Gen,  // ☶ Mountain, Still
    Dui,  // ☱ Lake, Joyous
}

impl Trigram {
    /// Binary value (3-bit): bit 0 = bottom line, bit 2 = top line. 1=yang, 0=yin.
    pub fn binary(&self) -> u8 {
        match self {
            Trigram::Qian => 0b111,
            Trigram::Kun  => 0b000,
            Trigram::Zhen => 0b001,
            Trigram::Xun  => 0b110,
            Trigram::Kan  => 0b010,
            Trigram::Li   => 0b101,
            Trigram::Gen  => 0b100,
            Trigram::Dui  => 0b011,
        }
    }

    pub fn from_binary(bits: u8) -> Self {
        match bits & 0b111 {
            0b111 => Trigram::Qian,
            0b000 => Trigram::Kun,
            0b001 => Trigram::Zhen,
            0b110 => Trigram::Xun,
            0b010 => Trigram::Kan,
            0b101 => Trigram::Li,
            0b100 => Trigram::Gen,
            0b011 => Trigram::Dui,
            _ => Trigram::Kun,
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            Trigram::Qian => "Qian", Trigram::Kun => "Kun",
            Trigram::Zhen => "Zhen", Trigram::Xun => "Xun",
            Trigram::Kan => "Kan", Trigram::Li => "Li",
            Trigram::Gen => "Gen", Trigram::Dui => "Dui",
        }
    }

    pub fn element(&self) -> &'static str {
        match self {
            Trigram::Qian => "Heaven", Trigram::Kun => "Earth",
            Trigram::Zhen => "Thunder", Trigram::Xun => "Wind",
            Trigram::Kan => "Water", Trigram::Li => "Fire",
            Trigram::Gen => "Mountain", Trigram::Dui => "Lake",
        }
    }
}

// ---------------------------------------------------------------------------
// Cast method + result
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CastMethod { Coin, Yarrow, Hash }

#[derive(Debug, Clone)]
pub struct HexagramCast {
    pub primary: u32,
    pub relating: u32,
    pub lines: Vec<u32>,
    pub moving_lines: Vec<usize>,
    pub lower_trigram: Trigram,
    pub upper_trigram: Trigram,
    pub cast_method: CastMethod,
}

/// Flip a line value: 6→9, 9→6, 7→8, 8→7 (for moving line transformation)
fn flip_line(line: u32) -> u32 {
    match line { 6 => 9, 9 => 6, 7 => 8, 8 => 7, _ => line }
}

/// Lines to binary pattern (0-63). Yang lines (7,9) = 1, Yin lines (6,8) = 0.
fn lines_to_binary(lines: &[u32]) -> u32 {
    let mut val = 0u32;
    for (i, &l) in lines.iter().enumerate() {
        if l == 7 || l == 9 { val |= 1 << i; }
    }
    val
}

/// Build a HexagramCast from 6 line values.
fn build_cast(lines: Vec<u32>, method: CastMethod) -> HexagramCast {
    let binary = lines_to_binary(&lines);
    let primary = binary_to_king_wen(binary);

    // Moving lines: 6 (old yin) and 9 (old yang)
    let moving_lines: Vec<usize> = lines.iter().enumerate()
        .filter(|(_, &l)| l == 6 || l == 9)
        .map(|(i, _)| i)
        .collect();

    // Relating hexagram: flip moving lines
    let relating = if moving_lines.is_empty() {
        primary
    } else {
        let transformed: Vec<u32> = lines.iter().enumerate().map(|(i, &l)| {
            if moving_lines.contains(&i) { flip_line(l) } else { l }
        }).collect();
        binary_to_king_wen(lines_to_binary(&transformed))
    };

    // Trigram decomposition: lower = lines 0-2, upper = lines 3-5
    let lower_bits = (binary & 0b111) as u8;
    let upper_bits = ((binary >> 3) & 0b111) as u8;
    let lower_trigram = Trigram::from_binary(lower_bits);
    let upper_trigram = Trigram::from_binary(upper_bits);

    HexagramCast { primary, relating, lines, moving_lines, lower_trigram, upper_trigram, cast_method: method }
}

// ---------------------------------------------------------------------------
// Casting methods
// ---------------------------------------------------------------------------

/// 3-coin method: each line = sum of 3 coins (2=yang, 3=yin).
/// 6=old yin (all tails), 7=young yang (2 heads 1 tail), 8=young yin (1 head 2 tails), 9=old yang (all heads).
pub fn cast_coin(rng: &mut impl Rng) -> HexagramCast {
    let mut lines = Vec::with_capacity(6);
    for _ in 0..6 {
        let mut sum = 0u32;
        for _ in 0..3 {
            sum += if rng.gen_bool(0.5) { 3 } else { 2 };
        }
        lines.push(sum);
    }
    build_cast(lines, CastMethod::Coin)
}

/// Yarrow stalk method: probabilities 1/16, 5/16, 7/16, 3/16 for 6,7,8,9.
pub fn cast_yarrow(rng: &mut impl Rng) -> HexagramCast {
    let mut lines = Vec::with_capacity(6);
    for _ in 0..6 {
        let r: u32 = rng.gen_range(0..16);
        let line = match r {
            0 => 6,         // 1/16 old yin
            1..=5 => 7,     // 5/16 young yang
            6..=12 => 8,    // 7/16 young yin
            _ => 9,         // 3/16 old yang
        };
        lines.push(line);
    }
    build_cast(lines, CastMethod::Yarrow)
}

/// Deterministic hash-based casting (for testing/replay).
/// Same query → same result.
pub fn cast_hash(query: &str) -> HexagramCast {
    let mut hasher = DefaultHasher::new();
    query.hash(&mut hasher);
    let hash = hasher.finish();
    let mut lines = Vec::with_capacity(6);
    for i in 0..6 {
        let part = ((hash >> (i * 4)) & 0xF) as u32;
        let line = match part {
            0 => 6, 1..=5 => 7, 6..=12 => 8, _ => 9,
        };
        lines.push(line);
    }
    build_cast(lines, CastMethod::Hash)
}

// ---------------------------------------------------------------------------
// Hexagram metadata (names for all 64)
// ---------------------------------------------------------------------------

pub static HEXAGRAM_NAMES: [&str; 64] = [
    "The Creative", "The Receptive", "Difficulty at the Beginning", "Youthful Folly",
    "Waiting", "Conflict", "The Army", "Holding Together",
    "Small Taming", "Treading", "Peace", "Standstill",
    "Fellowship with Others", "Great Possession", "Modesty", "Enthusiasm",
    "Following", "Work on the Decayed", "Approach", "Contemplation",
    "Biting Through", "Grace", "Splitting Apart", "Return",
    "Innocence", "Great Taming", "Mouth Corners", "Great Preponderance",
    "The Abysmal", "The Clinging Fire", "Influence", "Duration",
    "Retreat", "Great Power", "Progress", "Darkening of the Light",
    "Opposition", "The Family", "Obstruction", "Deliverance",
    "Decrease", "Increase", "Breakthrough", "Coming to Meet",
    "Gathering Together", "Pushing Upward", "Oppression", "The Well",
    "Revolution", "The Cauldron", "The Arousing", "Keeping Still",
    "Development", "The Marrying Maiden", "Abundance", "The Wanderer",
    "The Gentle", "The Joyous", "Dispersion", "Limitation",
    "Inner Truth", "Small Preponderance", "After Completion", "Before Completion",
];

pub fn hexagram_name(num: u32) -> &'static str {
    if num == 0 || num > 64 { return "Unknown"; }
    HEXAGRAM_NAMES[(num - 1) as usize]
}

// ---------------------------------------------------------------------------
// Phase 4a: Beta-Calibrated Line Probabilities
// ---------------------------------------------------------------------------

/// Standard I Ching line probabilities:
/// - 3-coin: P(6)=1/8, P(7)=3/8, P(8)=3/8, P(9)=1/8
/// - Yarrow stalk: P(6)=1/16, P(7)=5/16, P(8)=7/16, P(9)=3/16
///
/// Beta calibration adjusts these based on a system "temperature" parameter:
/// - temperature → 0.5: conservative (favors stable lines 7/8, fewer moving)
/// - temperature → 1.0: standard probabilities
/// - temperature → 2.0: volatile (favors moving lines 6/9)

/// Compute beta-calibrated probabilities for each line value.
/// Returns (p6, p7, p8, p9) that sum to 1.0.
pub fn beta_line_probabilities(temperature: f64) -> (f64, f64, f64, f64) {
    let t = temperature.clamp(0.1, 10.0);

    // Base probabilities (yarrow stalk — more traditional)
    let base_p6 = 1.0 / 16.0;
    let base_p7 = 5.0 / 16.0;
    let base_p8 = 7.0 / 16.0;
    let base_p9 = 3.0 / 16.0;

    // Moving line probability scales with temperature
    // At t=1.0: standard. At t=2.0: moving lines doubled. At t=0.5: halved.
    let moving_scale = t;
    let stable_scale = 2.0 - t; // inverse: when moving increases, stable decreases

    let p6 = base_p6 * moving_scale;
    let p9 = base_p9 * moving_scale;
    let p7 = base_p7 * stable_scale;
    let p8 = base_p8 * stable_scale;

    // Normalize
    let total = p6 + p7 + p8 + p9;
    (p6 / total, p7 / total, p8 / total, p9 / total)
}

/// Sample a line value from beta-calibrated probabilities.
pub fn sample_beta_line(rng: &mut impl Rng, temperature: f64) -> u32 {
    let (p6, p7, p8, p9) = beta_line_probabilities(temperature);
    let r: f64 = rng.gen();
    if r < p6 { 6 }
    else if r < p6 + p7 { 7 }
    else if r < p6 + p7 + p8 { 8 }
    else { 9 }
}

/// Cast a hexagram using beta-calibrated line probabilities.
pub fn cast_beta(rng: &mut impl Rng, temperature: f64) -> HexagramCast {
    let lines: Vec<u32> = (0..6).map(|_| sample_beta_line(rng, temperature)).collect();
    build_cast(lines, CastMethod::Coin) // reuse Coin method label
}

/// Compute the entropy of a line probability distribution.
/// Higher entropy = more uncertainty = more moving lines likely.
pub fn line_entropy(temperature: f64) -> f64 {
    let (p6, p7, p8, p9) = beta_line_probabilities(temperature);
    let mut h = 0.0;
    for p in [p6, p7, p8, p9] {
        if p > 0.0 {
            h -= p * p.ln();
        }
    }
    h
}

// ---------------------------------------------------------------------------
// PyO3 wrapper — matches what Python i_ching.py expects: `iching_cast(query)`
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pyfunction]
pub fn iching_cast(query: &str) -> (u32, Vec<u32>) {
    let cast = cast_hash(query);
    (cast.primary, cast.lines)
}

#[cfg(feature = "python")]
#[pyfunction]
pub fn iching_cast_stochastic(method: &str) -> PyResult<(u32, u32, Vec<u32>, Vec<usize>, String, String, String)> {
    use rand::SeedableRng;
    use rand::rngs::SmallRng;
    let mut rng = SmallRng::from_entropy();
    let cast = match method {
        "coin" => cast_coin(&mut rng),
        "yarrow" => cast_yarrow(&mut rng),
        _ => cast_yarrow(&mut rng),
    };
    Ok((
        cast.primary,
        cast.relating,
        cast.lines.clone(),
        cast.moving_lines.clone(),
        cast.lower_trigram.name().to_string(),
        cast.upper_trigram.name().to_string(),
        format!("{:?}", cast.cast_method),
    ))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trigram_binary_roundtrip() {
        for t in [Trigram::Qian, Trigram::Kun, Trigram::Zhen, Trigram::Xun,
                  Trigram::Kan, Trigram::Li, Trigram::Gen, Trigram::Dui] {
            assert_eq!(Trigram::from_binary(t.binary()), t);
        }
    }

    #[test]
    fn test_coin_cast_valid_lines() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(42);
        let cast = cast_coin(&mut rng);
        assert_eq!(cast.lines.len(), 6);
        for &l in &cast.lines {
            assert!(l == 6 || l == 7 || l == 8 || l == 9, "Invalid line: {}", l);
        }
        assert!(cast.primary >= 1 && cast.primary <= 64);
        assert_eq!(cast.cast_method, CastMethod::Coin);
    }

    #[test]
    fn test_yarrow_cast_valid_lines() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(99);
        let cast = cast_yarrow(&mut rng);
        assert_eq!(cast.lines.len(), 6);
        for &l in &cast.lines {
            assert!(l == 6 || l == 7 || l == 8 || l == 9);
        }
        assert!(cast.primary >= 1 && cast.primary <= 64);
        assert_eq!(cast.cast_method, CastMethod::Yarrow);
    }

    #[test]
    fn test_hash_cast_deterministic() {
        let c1 = cast_hash("will I succeed?");
        let c2 = cast_hash("will I succeed?");
        assert_eq!(c1.primary, c2.primary);
        assert_eq!(c1.lines, c2.lines);
        assert_eq!(c1.cast_method, CastMethod::Hash);
    }

    #[test]
    fn test_hash_cast_different_queries() {
        let c1 = cast_hash("question one");
        let c2 = cast_hash("question two");
        // Very likely different (could theoretically be same but extremely unlikely)
        assert_ne!(c1.lines, c2.lines);
    }

    #[test]
    fn test_trigram_decomposition() {
        // Hexagram 1 (all yang): both trigrams Qian
        let cast = cast_hash("test_trigram_111111");
        // Check trigram decomposition is consistent
        let lower = cast.lower_trigram;
        let upper = cast.upper_trigram;
        // Reconstruct binary from trigrams
        let reconstructed = (upper.binary() as u32) << 3 | (lower.binary() as u32);
        let expected = lines_to_binary(&cast.lines);
        assert_eq!(reconstructed, expected);
    }

    #[test]
    fn test_moving_line_transformation() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(7);
        // Cast until we get moving lines
        for _ in 0..100 {
            let cast = cast_yarrow(&mut rng);
            if !cast.moving_lines.is_empty() {
                assert_ne!(cast.primary, cast.relating,
                    "With moving lines, relating should differ from primary");
                return;
            }
        }
        panic!("No moving lines in 100 casts — check yarrow probabilities");
    }

    #[test]
    fn test_no_moving_lines_same_hexagram() {
        // Build a cast with no moving lines (all 7s and 8s)
        let lines = vec![7, 8, 7, 8, 7, 8];
        let cast = build_cast(lines, CastMethod::Hash);
        assert!(cast.moving_lines.is_empty());
        assert_eq!(cast.primary, cast.relating);
    }

    #[test]
    fn test_flip_line() {
        assert_eq!(flip_line(6), 9);
        assert_eq!(flip_line(9), 6);
        assert_eq!(flip_line(7), 8);
        assert_eq!(flip_line(8), 7);
    }

    #[test]
    fn test_hexagram_name() {
        assert_eq!(hexagram_name(1), "The Creative");
        assert_eq!(hexagram_name(2), "The Receptive");
        assert_eq!(hexagram_name(64), "Before Completion");
        assert_eq!(hexagram_name(0), "Unknown");
        assert_eq!(hexagram_name(65), "Unknown");
    }

    #[test]
    fn test_king_wen_all_valid() {
        // Every binary 0-63 should map to a valid King Wen number 1-64
        for b in 0..64u32 {
            let kw = binary_to_king_wen(b);
            assert!(kw >= 1 && kw <= 64, "binary {} → King Wen {} out of range", b, kw);
        }
    }

    #[test]
    fn test_king_wen_canonical_reference() {
        // Cross-referenced with Wikibooks "I Ching/The 64 Hexagrams"
        // and Wikipedia "King Wen sequence" article.
        // Binary: bit 0 = bottom line, bit 5 = top line. 1=yang, 0=yin.

        // Key reference points:
        assert_eq!(binary_to_king_wen(0b000000), 2,  "Kun (all yin) → KW 2");
        assert_eq!(binary_to_king_wen(0b111111), 1,  "Qian (all yang) → KW 1");
        assert_eq!(binary_to_king_wen(0b000001), 24, "Fu (Return, bottom yang) → KW 24");
        assert_eq!(binary_to_king_wen(0b000010), 7,  "Shi (Army) → KW 7");
        assert_eq!(binary_to_king_wen(0b000111), 11, "Tai (Peace) → KW 11");
        assert_eq!(binary_to_king_wen(0b111000), 12, "Pi (Standstill) → KW 12");
        assert_eq!(binary_to_king_wen(0b010001), 3,  "Zhun (Difficulty) → KW 3");
        assert_eq!(binary_to_king_wen(0b100010), 4,  "Meng (Youthful Folly) → KW 4");
        assert_eq!(binary_to_king_wen(0b010010), 29, "Kan (Water/Abysmal) → KW 29");
        assert_eq!(binary_to_king_wen(0b101101), 30, "Li (Fire/Clinging) → KW 30");
        assert_eq!(binary_to_king_wen(0b010101), 63, "Ji Ji (After Completion) → KW 63");
        assert_eq!(binary_to_king_wen(0b101010), 64, "Wei Ji (Before Completion) → KW 64");
        assert_eq!(binary_to_king_wen(0b011100), 31, "Xian (Influence) → KW 31");
        assert_eq!(binary_to_king_wen(0b001110), 32, "Heng (Duration) → KW 32");
        assert_eq!(binary_to_king_wen(0b001001), 51, "Zhen (Thunder) → KW 51");
        assert_eq!(binary_to_king_wen(0b100100), 52, "Gen (Mountain) → KW 52");
        assert_eq!(binary_to_king_wen(0b110110), 57, "Xun (Wind) → KW 57");
        assert_eq!(binary_to_king_wen(0b011011), 58, "Dui (Lake) → KW 58");
    }

    #[test]
    fn test_king_wen_no_duplicates() {
        // Every King Wen number 1-64 should appear exactly once
        let mut counts = [0u8; 65];
        for b in 0..64u32 {
            let kw = binary_to_king_wen(b) as usize;
            assert!(kw >= 1 && kw <= 64);
            counts[kw] += 1;
        }
        for n in 1..=64 {
            assert_eq!(counts[n], 1, "King Wen {} appears {} times (should be 1)", n, counts[n]);
        }
    }

    #[test]
    fn test_king_wen_inversion_pairs() {
        // In the King Wen sequence, consecutive pairs are typically inversions.
        // Hexagrams 1&2 are complementary (all yang vs all yin).
        // Hexagrams 3&4 are inversions (upside-down of each other).
        // Verify: binary of KW 3 inverted (upside-down) should give binary of KW 4.
        let bin_3 = 0b010001u32; // KW 3: Thunder over Water
        let bin_4 = 0b100010u32; // KW 4: Water over Mountain (upside-down of 3)
        // Upside-down: reverse the 6 bits
        fn reverse_bits(b: u32) -> u32 {
            let mut r = 0u32;
            for i in 0..6 {
                if b & (1 << i) != 0 { r |= 1 << (5 - i); }
            }
            r
        }
        assert_eq!(reverse_bits(bin_3), bin_4, "KW 3 and 4 should be inversions");
        assert_eq!(binary_to_king_wen(bin_3), 3);
        assert_eq!(binary_to_king_wen(bin_4), 4);
    }

    #[test]
    fn test_all_64_hexagrams_castable() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(12345);
        let mut seen = std::collections::HashSet::new();
        for _ in 0..500 {
            let cast = cast_coin(&mut rng);
            seen.insert(cast.primary);
        }
        // Should have seen a good fraction of 64 hexagrams
        assert!(seen.len() > 30, "Only saw {} unique hexagrams in 500 casts", seen.len());
    }

    #[test]
    fn test_beta_probabilities_sum_to_one() {
        for t in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0] {
            let (p6, p7, p8, p9) = beta_line_probabilities(t);
            let sum = p6 + p7 + p8 + p9;
            assert!((sum - 1.0).abs() < 1e-10, "t={}: probs sum to {} not 1.0", t, sum);
        }
    }

    #[test]
    fn test_beta_standard_temperature_matches_yarrow() {
        let (p6, p7, p8, p9) = beta_line_probabilities(1.0);
        assert!((p6 - 1.0/16.0).abs() < 1e-10, "p6 should be 1/16");
        assert!((p7 - 5.0/16.0).abs() < 1e-10, "p7 should be 5/16");
        assert!((p8 - 7.0/16.0).abs() < 1e-10, "p8 should be 7/16");
        assert!((p9 - 3.0/16.0).abs() < 1e-10, "p9 should be 3/16");
    }

    #[test]
    fn test_beta_low_temp_favors_stable() {
        let (p6_low, p7_low, p8_low, p9_low) = beta_line_probabilities(0.5);
        let (p6_std, p7_std, p8_std, p9_std) = beta_line_probabilities(1.0);
        // Moving lines (6,9) should have lower probability at low temp
        assert!(p6_low < p6_std, "p6 should decrease at low temp");
        assert!(p9_low < p9_std, "p9 should decrease at low temp");
        // Stable lines (7,8) should have higher probability at low temp
        assert!(p7_low > p7_std, "p7 should increase at low temp");
        assert!(p8_low > p8_std, "p8 should increase at low temp");
    }

    #[test]
    fn test_beta_high_temp_favors_moving() {
        let (p6_hi, _, _, p9_hi) = beta_line_probabilities(2.0);
        let (p6_std, _, _, p9_std) = beta_line_probabilities(1.0);
        assert!(p6_hi > p6_std, "p6 should increase at high temp");
        assert!(p9_hi > p9_std, "p9 should increase at high temp");
    }

    #[test]
    fn test_sample_beta_line_valid() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(42);
        for _ in 0..100 {
            let line = sample_beta_line(&mut rng, 1.0);
            assert!(line == 6 || line == 7 || line == 8 || line == 9);
        }
    }

    #[test]
    fn test_cast_beta_valid() {
        use rand::SeedableRng;
        use rand::rngs::SmallRng;
        let mut rng = SmallRng::seed_from_u64(7);
        let cast = cast_beta(&mut rng, 1.5);
        assert_eq!(cast.lines.len(), 6);
        assert!(cast.primary >= 1 && cast.primary <= 64);
    }

    #[test]
    fn test_line_entropy_positive() {
        for t in [0.5, 1.0, 2.0] {
            let h = line_entropy(t);
            assert!(h > 0.0, "Entropy should be positive at t={}", t);
        }
    }

    #[test]
    fn test_line_entropy_varies_with_temp() {
        let h_low = line_entropy(0.5);
        let h_std = line_entropy(1.0);
        let h_hi = line_entropy(2.0);
        // Entropy should differ across temperatures
        assert!(h_low != h_std, "Entropy should differ: {} vs {}", h_low, h_std);
        assert!(h_std != h_hi, "Entropy should differ: {} vs {}", h_std, h_hi);
        // Standard temperature should have highest entropy (most balanced)
        assert!(h_std > h_low, "Standard temp should have higher entropy than low: {} > {}", h_std, h_low);
    }
}
