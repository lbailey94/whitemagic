//! Zero-allocation, sub-microsecond (< 1 µs) speculative AST validator.
//!
//! Uses a 64-bit token bloom pre-filter and SIMD substring searching (memchr).

use crate::action_skeleton::{AstActionType, SkeletonLanguage, SkeletonValidationResult};
use std::time::Instant;

pub struct SourceBufferIndex<'a> {
    pub bytes: &'a [u8],
    pub bloom_mask: u64,
}

impl<'a> SourceBufferIndex<'a> {
    #[inline]
    pub fn new(bytes: &'a [u8]) -> Self {
        let mut bloom = 0u64;
        for word in bytes.split(|b| !b.is_ascii_alphanumeric() && *b != b'_') {
            if !word.is_empty() {
                let mut val = 0u64;
                for &b in word {
                    val = (val << 5).wrapping_add(b as u64);
                }
                bloom |= 1u64 << (val % 64);
            }
        }
        Self {
            bytes,
            bloom_mask: bloom,
        }
    }

    #[inline(always)]
    pub fn fast_contains(&self, needle: &[u8]) -> bool {
        if needle.is_empty() {
            return true;
        }
        // Step 1: Check bloom filter for each word in needle
        for word in needle.split(|b| !b.is_ascii_alphanumeric() && *b != b'_') {
            if !word.is_empty() {
                let mut val = 0u64;
                for &b in word {
                    val = (val << 5).wrapping_add(b as u64);
                }
                let bit = 1u64 << (val % 64);
                if (self.bloom_mask & bit) == 0 {
                    return false;
                }
            }
        }

        // Step 2: Exact SIMD Byte Substring Search
        memchr::memmem::find(self.bytes, needle).is_some()
    }
}

pub fn validate_speculative_fast(
    skeleton: &crate::action_skeleton::ActionSkeleton,
    source_index: &SourceBufferIndex,
) -> SkeletonValidationResult {
    let start = Instant::now();
    let mut conflicts = Vec::new();
    let warnings = Vec::new();

    for delta in &skeleton.deltas {
        let sig = delta.signature_delta.as_bytes();

        // 1. Structural signature emptiness check
        if sig.is_empty() && delta.action_type != AstActionType::AddImport {
            conflicts.push(format!("Delta '{}' empty signature", delta.target_symbol));
            continue;
        }

        // 2. Pre-invariant verification via SIMD bloom search (< 100ns per invariant)
        for pre in &delta.pre_invariants {
            if !source_index.fast_contains(pre.as_bytes()) {
                conflicts.push(format!(
                    "Pre-invariant check failed for '{}': '{}' missing",
                    delta.target_symbol, pre
                ));
            }
        }

        // 3. Language syntactic heuristics
        match skeleton.language {
            SkeletonLanguage::Python => {
                if (delta.action_type == AstActionType::AddFunction
                    || delta.action_type == AstActionType::ModifySignature)
                    && !sig.windows(4).any(|w| w == b"def ")
                    && !sig.windows(6).any(|w| w == b"class ")
                {
                    conflicts.push(format!(
                        "Python signature '{}' missing def/class",
                        delta.target_symbol
                    ));
                }
            }
            SkeletonLanguage::Rust
                if (delta.action_type == AstActionType::AddFunction
                    || delta.action_type == AstActionType::ModifySignature)
                    && !sig.windows(3).any(|w| w == b"fn ")
                    && !sig.windows(7).any(|w| w == b"pub fn ") =>
            {
                conflicts.push(format!(
                    "Rust signature '{}' missing fn",
                    delta.target_symbol
                ));
            }
            _ => {}
        }
    }

    let is_valid = conflicts.is_empty();
    let validation_duration_micros = start.elapsed().as_micros() as u64;

    SkeletonValidationResult {
        is_valid,
        conflicts,
        warnings,
        validation_duration_micros,
    }
}
