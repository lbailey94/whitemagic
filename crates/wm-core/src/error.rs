//! Core error types for `WhiteMagic` v4.

use thiserror::Error;

/// Result type alias for `WhiteMagic` core operations.
pub type Result<T> = std::result::Result<T, CoreError>;

/// Core error type covering all `WhiteMagic` failure modes.
#[derive(Debug, Error)]
pub enum CoreError {
    /// Tool execution failed
    #[error("tool error: {0}")]
    Tool(String),

    /// Memory operation failed
    #[error("memory error: {0}")]
    Memory(String),

    /// Governance rule violation
    #[error("governance violation: {0}")]
    Governance(String),

    /// Rate limit exceeded
    #[error("rate limited: {0}")]
    RateLimited(String),

    /// Circuit breaker open
    #[error("circuit breaker open for: {0}")]
    CircuitBreaker(String),

    /// Invalid arguments
    #[error("invalid args: {0}")]
    InvalidArgs(String),

    /// Resource not found
    #[error("not found: {0}")]
    NotFound(String),

    /// Polyglot bridge error
    #[error("polyglot error: {0}")]
    Polyglot(String),

    /// I/O error
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    /// Serialization error
    #[error("serialization error: {0}")]
    Serde(#[from] serde_json::Error),

    /// Internal error (should not happen in normal operation)
    #[error("internal error: {0}")]
    Internal(String),
}

impl CoreError {
    /// Whether this error is retryable.
    #[must_use]
    pub const fn is_retryable(&self) -> bool {
        matches!(self, Self::RateLimited(_) | Self::CircuitBreaker(_))
    }

    /// Whether this error indicates a governance violation.
    #[must_use]
    pub const fn is_governance(&self) -> bool {
        matches!(self, Self::Governance(_))
    }
}
