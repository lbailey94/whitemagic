//! Error type for receipt emission and verification.

use thiserror::Error;

/// Receipt operation failure.
#[derive(Debug, Error)]
pub enum ReceiptError {
    /// Canonicalization rejected the value (e.g. a float).
    #[error("receipt canon error: {0}")]
    Canon(String),
    /// Signing failed or key material is unusable.
    #[error("receipt key error: {0}")]
    Key(String),
    /// Caller-supplied arguments are invalid.
    #[error("invalid receipt args: {0}")]
    InvalidArgs(String),
    /// The requested receipt does not exist.
    #[error("receipt not found: {0}")]
    NotFound(String),
    /// Emission was refused (e.g. attesting an invalid chain).
    #[error("receipt refused: {0}")]
    Refused(String),
    /// Store interaction failed.
    #[error("receipt store error: {0}")]
    Store(String),
    /// I/O failure.
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    /// JSON (de)serialization failure.
    #[error("serde error: {0}")]
    Serde(#[from] serde_json::Error),
}

/// Result alias for receipt operations.
pub type Result<T> = std::result::Result<T, ReceiptError>;

impl ReceiptError {
    /// Map into the workspace core error so tool handlers can propagate with `?`.
    #[must_use]
    pub fn into_core_error(self) -> wm_core::CoreError {
        match self {
            Self::Canon(message) | Self::Key(message) | Self::Store(message) => {
                wm_core::CoreError::Tool(message)
            }
            Self::InvalidArgs(message) => wm_core::CoreError::InvalidArgs(message),
            Self::NotFound(message) => wm_core::CoreError::NotFound(message),
            Self::Refused(message) => wm_core::CoreError::Governance(message),
            Self::Io(error) => wm_core::CoreError::Io(error),
            Self::Serde(error) => wm_core::CoreError::Serde(error),
        }
    }
}
