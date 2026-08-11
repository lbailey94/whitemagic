//! WhiteMagic v5 Dispatch — Tool routing pipeline
//!
//! Replaces the v2 Python 22-stage middleware chain (~200µs/call)
//! with a Rust trait-based pipeline (~2µs/call).

#![forbid(unsafe_code)]

pub mod circuit_breaker;
pub mod composition;
pub mod pipeline;
pub mod rate_limiter;
pub mod registry;
pub mod speculative;

pub use circuit_breaker::{BreakerConfig, BreakerState, CircuitBreaker, CircuitBreakerRegistry};
pub use composition::{CompositionConfig, CompositionPattern, CompositionTracker};
pub use pipeline::DispatchPipeline;
pub use rate_limiter::{RateLimiter, RateLimiterConfig, SlidingWindow};
pub use registry::{ToolRegistry, ToolRegistryBuilder};
pub use speculative::{CheckResult, SpeculativeExecutor, ValidationResult};
