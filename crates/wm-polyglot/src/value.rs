//! Polyglot value — cross-language data representation.
//!
//! All language backends convert between their native types and `PolyglotValue`.
//! This ensures type-safe data passing across FFI boundaries.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// A cross-language value type for polyglot function calls.
///
/// Maps naturally to JSON, making it easy to serialize across FFI boundaries.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub enum PolyglotValue {
    /// Null / nil / nothing
    #[default]
    Null,
    /// Boolean
    Bool(bool),
    /// 64-bit signed integer
    Int(i64),
    /// 64-bit floating point
    Float(f64),
    /// UTF-8 string
    String(String),
    /// Array of values
    Array(Vec<PolyglotValue>),
    /// Key-value map (sorted for deterministic serialization)
    Map(BTreeMap<String, PolyglotValue>),
}

impl PolyglotValue {
    /// Create a null value.
    #[must_use]
    pub fn null() -> Self {
        Self::Null
    }

    /// Create a boolean value.
    #[must_use]
    pub fn bool(b: bool) -> Self {
        Self::Bool(b)
    }

    /// Create an integer value.
    #[must_use]
    pub fn int(i: i64) -> Self {
        Self::Int(i)
    }

    /// Create a float value.
    #[must_use]
    pub fn float(f: f64) -> Self {
        Self::Float(f)
    }

    /// Create a string value.
    #[must_use]
    pub fn string(s: impl Into<String>) -> Self {
        Self::String(s.into())
    }

    /// Create an array value.
    #[must_use]
    pub fn array(items: Vec<PolyglotValue>) -> Self {
        Self::Array(items)
    }

    /// Create a map value.
    #[must_use]
    pub fn map(entries: impl IntoIterator<Item = (String, PolyglotValue)>) -> Self {
        Self::Map(entries.into_iter().collect())
    }

    /// Check if this value is null.
    #[must_use]
    pub fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }

    /// Try to get a boolean.
    #[must_use]
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Self::Bool(b) => Some(*b),
            _ => None,
        }
    }

    /// Try to get an integer.
    #[must_use]
    pub fn as_int(&self) -> Option<i64> {
        match self {
            Self::Int(i) => Some(*i),
            Self::Float(f) if f.fract() == 0.0 => Some(*f as i64),
            _ => None,
        }
    }

    /// Try to get a float.
    #[must_use]
    pub fn as_float(&self) -> Option<f64> {
        match self {
            Self::Float(f) => Some(*f),
            Self::Int(i) => Some(*i as f64),
            _ => None,
        }
    }

    /// Try to get a string reference.
    #[must_use]
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Self::String(s) => Some(s),
            _ => None,
        }
    }

    /// Try to get an array reference.
    #[must_use]
    pub fn as_array(&self) -> Option<&[PolyglotValue]> {
        match self {
            Self::Array(a) => Some(a),
            _ => None,
        }
    }

    /// Try to get a map reference.
    #[must_use]
    pub fn as_map(&self) -> Option<&BTreeMap<String, PolyglotValue>> {
        match self {
            Self::Map(m) => Some(m),
            _ => None,
        }
    }

    /// Serialize to JSON string.
    #[must_use]
    pub fn to_json(&self) -> String {
        serde_json::to_string(self).unwrap_or_else(|_| "null".into())
    }

    /// Deserialize from JSON string.
    ///
    /// # Errors
    /// Returns `PolyglotError::Serialization` if the JSON is invalid.
    pub fn from_json(s: &str) -> Result<Self, PolyglotError> {
        serde_json::from_str(s).map_err(|e| PolyglotError::Serialization(e.to_string()))
    }
}

impl From<bool> for PolyglotValue {
    fn from(b: bool) -> Self {
        Self::Bool(b)
    }
}

impl From<i64> for PolyglotValue {
    fn from(i: i64) -> Self {
        Self::Int(i)
    }
}

impl From<i32> for PolyglotValue {
    fn from(i: i32) -> Self {
        Self::Int(i as i64)
    }
}

impl From<f64> for PolyglotValue {
    fn from(f: f64) -> Self {
        Self::Float(f)
    }
}

impl From<&str> for PolyglotValue {
    fn from(s: &str) -> Self {
        Self::String(s.into())
    }
}

impl From<String> for PolyglotValue {
    fn from(s: String) -> Self {
        Self::String(s)
    }
}

impl From<Vec<PolyglotValue>> for PolyglotValue {
    fn from(v: Vec<PolyglotValue>) -> Self {
        Self::Array(v)
    }
}

/// Error type for polyglot operations.
#[derive(Debug, Clone, thiserror::Error)]
pub enum PolyglotError {
    /// Library loading failed
    #[error("FFI library load failed: {0}")]
    LibraryLoad(String),
    /// Symbol lookup failed
    #[error("FFI symbol lookup failed: {0}")]
    SymbolLookup(String),
    /// Function call failed
    #[error("Polyglot function call failed: {0}")]
    CallFailed(String),
    /// Serialization/deserialization error
    #[error("Serialization error: {0}")]
    Serialization(String),
    /// Backend not available
    #[error("Polyglot backend not available: {0}")]
    BackendUnavailable(String),
    /// Module not found
    #[error("Module not found: {0}")]
    ModuleNotFound(String),
    /// Function not found
    #[error("Function not found: {0}")]
    FunctionNotFound(String),
    /// Runtime initialization failed
    #[error("Runtime initialization failed: {0}")]
    InitFailed(String),
    /// Invalid argument
    #[error("Invalid argument: {0}")]
    InvalidArg(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn polyglot_value_null() {
        let v = PolyglotValue::null();
        assert!(v.is_null());
        assert!(v.as_bool().is_none());
        assert!(v.as_int().is_none());
    }

    #[test]
    fn polyglot_value_bool() {
        let v = PolyglotValue::bool(true);
        assert_eq!(v.as_bool(), Some(true));
        assert!(v.as_int().is_none());
    }

    #[test]
    fn polyglot_value_int() {
        let v = PolyglotValue::int(42);
        assert_eq!(v.as_int(), Some(42));
        assert_eq!(v.as_float(), Some(42.0));
    }

    #[test]
    fn polyglot_value_float() {
        let v = PolyglotValue::float(3.15);
        assert_eq!(v.as_float(), Some(3.15));
        assert!(v.as_int().is_none()); // 3.15 is not integer-valued
    }

    #[test]
    fn polyglot_value_float_to_int() {
        let v = PolyglotValue::float(42.0);
        assert_eq!(v.as_int(), Some(42)); // exact integer float converts
    }

    #[test]
    fn polyglot_value_string() {
        let v = PolyglotValue::string("hello");
        assert_eq!(v.as_str(), Some("hello"));
    }

    #[test]
    fn polyglot_value_array() {
        let v = PolyglotValue::array(vec![PolyglotValue::int(1), PolyglotValue::int(2)]);
        assert_eq!(v.as_array().map(|a| a.len()), Some(2));
    }

    #[test]
    fn polyglot_value_map() {
        let v = PolyglotValue::map([
            ("key".into(), PolyglotValue::int(1)),
            ("key2".into(), PolyglotValue::string("val")),
        ]);
        let m = v.as_map().unwrap();
        assert_eq!(m.len(), 2);
        assert_eq!(m.get("key").unwrap().as_int(), Some(1));
    }

    #[test]
    fn polyglot_value_json_roundtrip() {
        let v = PolyglotValue::map([
            ("name".into(), PolyglotValue::string("test")),
            ("value".into(), PolyglotValue::int(42)),
            (
                "items".into(),
                PolyglotValue::array(vec![PolyglotValue::bool(true), PolyglotValue::float(3.15)]),
            ),
        ]);
        let json = v.to_json();
        let restored = PolyglotValue::from_json(&json).unwrap();
        assert_eq!(v, restored);
    }

    #[test]
    fn polyglot_value_from_conversions() {
        let b: PolyglotValue = true.into();
        assert_eq!(b, PolyglotValue::Bool(true));

        let i: PolyglotValue = 42i64.into();
        assert_eq!(i, PolyglotValue::Int(42));

        let i32v: PolyglotValue = 7i32.into();
        assert_eq!(i32v, PolyglotValue::Int(7));

        let f: PolyglotValue = 3.15f64.into();
        assert_eq!(f, PolyglotValue::Float(3.15));

        let s: PolyglotValue = "hello".into();
        assert_eq!(s, PolyglotValue::String("hello".into()));
    }

    #[test]
    fn polyglot_value_from_json_invalid() {
        let result = PolyglotValue::from_json("not valid json");
        assert!(result.is_err());
    }

    #[test]
    fn polyglot_value_default_is_null() {
        assert_eq!(PolyglotValue::default(), PolyglotValue::Null);
    }

    #[test]
    fn polyglot_error_display() {
        let e = PolyglotError::LibraryLoad("test.so not found".into());
        assert!(e.to_string().contains("test.so"));
    }
}
