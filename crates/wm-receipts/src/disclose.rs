//! Selective disclosure over WM-emitted bundles (CR 0.2 semantics).
//!
//! Redaction is an **issuance-time act**: the modified receipts (and everything
//! after them) are re-signed, so it requires the issuer's signing key. WM keeps
//! the original stored bundle untouched and stores the redacted form as a
//! variant plus a separate disclosure map — evidence is never rewritten.

use serde_json::Value;

use crate::error::{ReceiptError, Result};
use crate::keys::ReceiptKey;

/// Replace optional fields with salted commitments; returns `(redacted, map)`.
///
/// Paths must be `receipts[i].body.<field>[...]`; required body fields are
/// refused by the CR implementation.
pub fn redact_bundle(key: &ReceiptKey, bundle: &Value, paths: &[String]) -> Result<(Value, Value)> {
    continuity_receipt::disclose::redact(bundle, paths, None, Some(key.signing_key()))
        .map_err(|error| ReceiptError::InvalidArgs(error.0))
}

/// Merge a disclosure map into a bundle (`disclosure_map`), preserving entries.
pub fn attach_map(bundle: &Value, disclosure: &Value) -> Result<Value> {
    continuity_receipt::disclose::attach(bundle, disclosure)
        .map_err(|error| ReceiptError::InvalidArgs(error.0))
}

/// Build a package disclosing only the requested paths from a full map.
pub fn reveal_paths(redacted: &Value, disclosure: &Value, paths: &[String]) -> Result<Value> {
    continuity_receipt::disclose::reveal(redacted, disclosure, paths)
        .map_err(|error| ReceiptError::InvalidArgs(error.0))
}
