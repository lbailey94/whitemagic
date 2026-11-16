//! Pure-Rust `#![forbid(unsafe_code)]` 32-byte packed `qFHRR` (`K=16` cyclic phase)
//! holographic similarity and zero-DLL prefilter.
//!
//! Ported cleanly from Gen 4 (`wm-gen4-lut`), providing deterministic sub-microsecond
//! 32-byte L1-cache-resident similarity scoring on every platform without `unsafe` or
//! ONNX Runtime dependencies.

#![forbid(unsafe_code)]

/// Triangular similarity LUT for `K = 16` cyclic integer phases: `lut[d] = 8 - min(d, 16 - d)`.
pub const QFHRR_K16_TRI_LUT: [u8; 16] = [8, 7, 6, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7];

/// Maximum raw similarity score across 64 4-bit phases (`64 * 8 = 512`).
pub const QFHRR_MAX_SCORE: i32 = 512;

/// Compact 32-byte packed 64D `qFHRR` (`K=16`) vector (half an L1 cacheline).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct QfhrrPacked32(pub [u8; 32]);

impl QfhrrPacked32 {
    #[must_use]
    pub const fn zero() -> Self {
        Self([0u8; 32])
    }

    #[must_use]
    pub fn from_nibbles(nibbles: &[u8; 64]) -> Self {
        Self(pack_64_nibbles_to_32(nibbles))
    }

    #[must_use]
    pub fn from_text(text: &str) -> Self {
        qfhrr_text_signature_packed32(text)
    }

    #[must_use]
    pub fn raw_similarity(&self, other: &Self) -> i32 {
        qfhrr_packed32_triangular_sim(&self.0, &other.0)
    }

    /// Normalized triangular similarity in `[0.0, 1.0]`.
    #[must_use]
    pub fn similarity(&self, other: &Self) -> f32 {
        (self.raw_similarity(other) as f32) / (QFHRR_MAX_SCORE as f32)
    }
}

/// Pack 64 4-bit nibbles (`0..15`) into 32 bytes (low nibble even index, high nibble odd index).
#[inline]
#[must_use]
pub fn pack_64_nibbles_to_32(nibbles: &[u8; 64]) -> [u8; 32] {
    let mut out = [0u8; 32];
    for i in 0..32 {
        out[i] = (nibbles[2 * i] & 0x0F) | ((nibbles[2 * i + 1] & 0x0F) << 4);
    }
    out
}

/// Cyclic phase binding `(a + b) & 0x0F` across 64 `K=16` phase coordinates.
#[inline]
pub fn qfhrr_bind_64d(a: &[u8; 64], b: &[u8; 64], out: &mut [u8; 64]) {
    for i in 0..64 {
        out[i] = a[i].wrapping_add(b[i]) & 0x0F;
    }
}

/// 64D `qFHRR` `K=16` triangular similarity in `[0, 512]`.
#[inline]
#[must_use]
pub fn qfhrr_triangular_sim_64d(a: &[u8; 64], b: &[u8; 64]) -> i32 {
    let mut acc = 0i32;
    for i in 0..64 {
        let diff = b[i].wrapping_sub(a[i]) & 0x0F;
        acc += i32::from(QFHRR_K16_TRI_LUT[usize::from(diff)]);
    }
    acc
}

/// Packed 32-byte (64-nibble) `qFHRR` `K=16` triangular similarity in `[0, 512]`.
#[inline]
#[must_use]
pub fn qfhrr_packed32_triangular_sim(a_p: &[u8; 32], b_p: &[u8; 32]) -> i32 {
    let mut acc = 0i32;
    for i in 0..32 {
        let da_lo = (b_p[i] & 0x0F).wrapping_sub(a_p[i] & 0x0F) & 0x0F;
        let da_hi = ((b_p[i] >> 4).wrapping_sub(a_p[i] >> 4)) & 0x0F;
        acc += i32::from(QFHRR_K16_TRI_LUT[usize::from(da_lo)])
            + i32::from(QFHRR_K16_TRI_LUT[usize::from(da_hi)]);
    }
    acc
}

#[inline]
fn fnv1a_64(bytes: &[u8]) -> u64 {
    let mut h = 0xcbf2_9ce4_8422_2325_u64;
    for &b in bytes {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0100_0000_01b3);
    }
    h
}

/// Deterministic zero-DLL 32-byte `qFHRR` text projection over lowercase byte trigrams & words.
#[must_use]
pub fn qfhrr_text_signature_packed32(text: &str) -> QfhrrPacked32 {
    let norm: Vec<u8> = text
        .bytes()
        .map(|b| b.to_ascii_lowercase())
        .filter(|b| b.is_ascii_alphanumeric() || *b == b' ' || *b == b'_' || *b == b'-')
        .collect();
    if norm.is_empty() {
        return QfhrrPacked32::zero();
    }

    let mut re = [0.0_f32; 64];
    let mut im = [0.0_f32; 64];

    // Accumulate word + trigram cyclic phase votes using unit roots on Z/16Z
    let mut add_feature = |seed: u64, weight: f32| {
        let mut s = seed;
        for j in 0..64 {
            s ^= s >> 12;
            s ^= s << 25;
            s ^= s >> 27;
            let k = (s.wrapping_mul(0x2545_f491_4f6c_dd1d) >> 60) as usize;
            let angle = (k as f32) * (std::f32::consts::TAU / 16.0);
            re[j] += weight * angle.cos();
            im[j] += weight * angle.sin();
        }
    };

    for tok in norm.split(|&b| b == b' ') {
        if tok.len() >= 2 {
            add_feature(fnv1a_64(tok), 1.5);
        }
    }
    if norm.len() >= 3 {
        for w in norm.windows(3) {
            add_feature(fnv1a_64(w) ^ 0x9e37_79b9_7f4a_7c15, 0.75);
        }
    } else {
        add_feature(fnv1a_64(&norm), 1.0);
    }

    let mut nibbles = [0u8; 64];
    for j in 0..64 {
        let mut theta = im[j].atan2(re[j]);
        if theta < 0.0 {
            theta += std::f32::consts::TAU;
        }
        let bin = ((theta / std::f32::consts::TAU) * 16.0).round() as usize;
        nibbles[j] = (bin & 0x0F) as u8;
    }

    QfhrrPacked32::from_nibbles(&nibbles)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn packed32_matches_unpacked_64d_and_self_similarity_is_exact() {
        let mut a = [0u8; 64];
        let mut b = [0u8; 64];
        for i in 0..64 {
            a[i] = ((i * 5 + 1) & 0x0F) as u8;
            b[i] = ((i * 3 + 7) & 0x0F) as u8;
        }
        let ap = pack_64_nibbles_to_32(&a);
        let bp = pack_64_nibbles_to_32(&b);

        assert_eq!(qfhrr_triangular_sim_64d(&a, &a), QFHRR_MAX_SCORE);
        assert_eq!(qfhrr_packed32_triangular_sim(&ap, &ap), QFHRR_MAX_SCORE);
        assert_eq!(
            qfhrr_triangular_sim_64d(&a, &b),
            qfhrr_packed32_triangular_sim(&ap, &bp)
        );

        let mut bound = [0u8; 64];
        qfhrr_bind_64d(&a, &b, &mut bound);
        assert_eq!(bound[0], (a[0] + b[0]) & 0x0F);
    }

    #[test]
    fn text_signature_ranks_related_text_above_unrelated() {
        let q = QfhrrPacked32::from_text("rust local memory landlock confinement");
        let close = QfhrrPacked32::from_text("local memory store with linux landlock confinement");
        let far = QfhrrPacked32::from_text("chocolate cake baking recipe butter sugar");
        assert!(
            q.raw_similarity(&close) > q.raw_similarity(&far),
            "close={} far={}",
            q.raw_similarity(&close),
            q.raw_similarity(&far)
        );
    }
}
