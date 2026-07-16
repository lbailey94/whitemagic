/// Streaming Inference Engine - Phase 2
/// 
/// High-performance local LLM inference with:
/// - Layer streaming (92x RAM reduction)
/// - Quantized KV cache (2-4x memory savings)
/// - AVX2 SIMD acceleration
/// - io_uring async I/O
/// 
/// Target: 50-100x faster than Python baseline

pub mod streaming;
pub mod quantization;
pub mod simd;
pub mod simd_ops;
pub mod ternary_kernel;
pub mod ring_buffer;
pub mod trigram_pool;

pub use streaming::StreamingEngine;
pub use quantization::{QuantizedKVCache, Quantizer};
pub use ternary_kernel::{ternary_gemv, ternary_dot, pack_ternary_matrix, Ternary};
pub use ring_buffer::RingBuffer;
pub use trigram_pool::{Trigram, TrigramPool, TrigramStatus};
