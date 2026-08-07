//! Grammar-Constrained JSON Output — zero parsing failures from LLM output.
//!
//! Provides pre-built JSON schemas and GBNF grammars for structured LLM
//! output. When passed to llama-server's `json_schema` or `grammar` field,
//! the LLM is constrained to produce valid JSON matching the schema —
//! eliminating regex-based JSON extraction from free-form text.
//!
//! Also includes a lightweight validator that checks whether a JSON string
//! satisfies a schema's `required` fields and type constraints, so callers
//! can verify output even when the LLM doesn't support grammar constraints.
//!
//! Ported from v2 `inference/grammar_schemas.py` (230 lines).

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

// ── JSON Schema Constants ─────────────────────────────────────────────

/// Entity extraction schema — entities + relations arrays.
pub const ENTITY_EXTRACTION_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "type": {"type": "string"}
        },
        "required": ["name", "type"]
      }
    },
    "relations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "subject": {"type": "string"},
          "predicate": {"type": "string"},
          "object": {"type": "string"}
        },
        "required": ["subject", "predicate", "object"]
      }
    }
  },
  "required": ["entities", "relations"]
}"#;

/// Security classification schema — boolean + confidence.
pub const SECURITY_CLASSIFICATION_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "is_attack": {"type": "boolean"},
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
  },
  "required": ["is_attack", "confidence"]
}"#;

/// Safety evaluation schema — score + reasoning.
pub const SAFETY_EVALUATION_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "reasoning": {"type": "string"}
  },
  "required": ["score", "reasoning"]
}"#;

/// Tool call schema — single tool + args.
pub const TOOL_CALL_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "tool": {"type": "string"},
    "args": {"type": "object"}
  },
  "required": ["tool", "args"]
}"#;

/// Tool call list schema — array of tool calls + final answer.
pub const TOOL_CALL_LIST_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "tool_calls": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "tool": {"type": "string"},
          "args": {"type": "object"}
        },
        "required": ["tool", "args"]
      }
    },
    "final_answer": {"type": "string"}
  },
  "required": ["tool_calls", "final_answer"]
}"#;

/// Content summary schema — summary + key points.
pub const CONTENT_SUMMARY_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "summary": {"type": "string"},
    "key_points": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["summary"]
}"#;

/// Code generation schema — code + metadata.
pub const CODE_GENERATION_SCHEMA: &str = r#"{
  "type": "object",
  "properties": {
    "code": {"type": "string"},
    "language": {"type": "string"},
    "imports": {"type": "array", "items": {"type": "string"}},
    "description": {"type": "string"}
  },
  "required": ["code"]
}"#;

// ── GBNF Grammar Constants ────────────────────────────────────────────

/// GBNF grammar for a single JSON object (ensures valid JSON output).
pub const JSON_OBJECT_GRAMMAR: &str = r#"root ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
pair ::= string ws* ":" ws* value
value ::= string | number | "true" | "false" | "null" | object | array
object ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
array ::= "[" ws* (value (ws* "," ws* value)*)? ws* "]"
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
ws ::= [ \t\n\r]
"#;

/// GBNF grammar for tool call output (text with embedded JSON tool calls).
pub const TOOL_CALL_GRAMMAR: &str = r#"root ::= (text | tool_call)*
tool_call ::= "<tool_call>" ws* json ws* "</tool_call>"
json ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
pair ::= string ws* ":" ws* value
value ::= string | number | "true" | "false" | "null" | json | array
array ::= "[" ws* (value (ws* "," ws* value)*)? ws* "]"
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
text ::= [^<]+ | "<" [^<]*
ws ::= [ \t\n\r]
"#;

/// GBNF grammar for Python code output.
pub const PYTHON_CODE_GRAMMAR: &str = r##"root ::= (line)*
line ::= indent (statement | comment | blank) "\n"
indent ::= [ ]*
statement ::= import_stmt | def_stmt | class_stmt | assign | expr | return_stmt | if_stmt | for_stmt | while_stmt | try_stmt | with_stmt | pass_stmt | raise_stmt | decorator
comment ::= "#" [^\n]*
blank ::= [ \t]*
import_stmt ::= "import" [^\n]+ | "from" [^\n]+ "import" [^\n]+
decorator ::= "@" [^\n]+
def_stmt ::= "def" ws+ identifier ws* "(" params? ")" ws* ":" ws* ("->" ws* type_hint)? rtype?
class_stmt ::= "class" ws+ identifier ws* ("(" base_classes? ")")? ws* ":"
assign ::= identifier ws* ("=" | "+=" | "-=" | "*=" | "/=" | "//=" | "%=" | "&=" | "|=" | "^=" | ">>=" | "<<=") ws* expr
return_stmt ::= "return" ws* expr?
if_stmt ::= "if" ws+ expr ws* ":" | "elif" ws+ expr ws* ":" | "else" ws* ":"
for_stmt ::= "for" ws+ identifier ws+ "in" ws+ expr ws* ":"
while_stmt ::= "while" ws+ expr ws* ":"
try_stmt ::= "try" ws* ":" | "except" [^\n]* ":" | "finally" ws* ":"
with_stmt ::= "with" [^\n]* ":"
pass_stmt ::= "pass" | "break" | "continue"
raise_stmt ::= "raise" [^\n]*
expr ::= [^\n]+
params ::= [^)]+
base_classes ::= [^)]+
type_hint ::= [^\n:]+
rtype ::= [^\n]+
identifier ::= [a-zA-Z_] [a-zA-Z0-9_]*
string_lit ::= "\"" ([^"\\] | "\\" .)* "\"" | "'" ([^'\\] | "\\" .)* "'" | "\"\"\"" ([^"] | "\\\"\"\"")* "\"\"\"" | "'''" ([^'] | "\\'\\'\\'")* "'''"
ws ::= [ \t]*
"##;

// ── Schema / Grammar Registry ─────────────────────────────────────────

/// Schema name in the registry.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SchemaName {
    /// Entity extraction (entities + relations).
    EntityExtraction,
    /// Security classification (is_attack + confidence).
    SecurityClassification,
    /// Safety evaluation (score + reasoning).
    SafetyEvaluation,
    /// Single tool call (tool + args).
    ToolCall,
    /// Tool call list (tool_calls + final_answer).
    ToolCallList,
    /// Content summary (summary + key_points).
    ContentSummary,
    /// Code generation (code + metadata).
    CodeGeneration,
}

impl SchemaName {
    /// All schema names.
    #[must_use]
    pub const fn all() -> [Self; 7] {
        [
            Self::EntityExtraction,
            Self::SecurityClassification,
            Self::SafetyEvaluation,
            Self::ToolCall,
            Self::ToolCallList,
            Self::ContentSummary,
            Self::CodeGeneration,
        ]
    }

    /// Human-readable name string.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EntityExtraction => "entity_extraction",
            Self::SecurityClassification => "security_classification",
            Self::SafetyEvaluation => "safety_evaluation",
            Self::ToolCall => "tool_call",
            Self::ToolCallList => "tool_call_list",
            Self::ContentSummary => "content_summary",
            Self::CodeGeneration => "code_generation",
        }
    }

    /// Get the JSON schema string for this name.
    #[must_use]
    pub const fn schema(self) -> &'static str {
        match self {
            Self::EntityExtraction => ENTITY_EXTRACTION_SCHEMA,
            Self::SecurityClassification => SECURITY_CLASSIFICATION_SCHEMA,
            Self::SafetyEvaluation => SAFETY_EVALUATION_SCHEMA,
            Self::ToolCall => TOOL_CALL_SCHEMA,
            Self::ToolCallList => TOOL_CALL_LIST_SCHEMA,
            Self::ContentSummary => CONTENT_SUMMARY_SCHEMA,
            Self::CodeGeneration => CODE_GENERATION_SCHEMA,
        }
    }

    /// Parse a string into a schema name.
    #[must_use]
    pub fn parse_name(s: &str) -> Option<Self> {
        match s {
            "entity_extraction" => Some(Self::EntityExtraction),
            "security_classification" => Some(Self::SecurityClassification),
            "safety_evaluation" => Some(Self::SafetyEvaluation),
            "tool_call" => Some(Self::ToolCall),
            "tool_call_list" => Some(Self::ToolCallList),
            "content_summary" => Some(Self::ContentSummary),
            "code_generation" => Some(Self::CodeGeneration),
            _ => None,
        }
    }
}

/// Grammar name in the registry.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GrammarName {
    /// JSON object grammar (valid JSON output).
    JsonObject,
    /// Tool call grammar (text + embedded JSON).
    ToolCall,
    /// Python code grammar.
    PythonCode,
}

impl GrammarName {
    /// All grammar names.
    #[must_use]
    pub const fn all() -> [Self; 3] {
        [Self::JsonObject, Self::ToolCall, Self::PythonCode]
    }

    /// Human-readable name string.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::JsonObject => "json_object",
            Self::ToolCall => "tool_call",
            Self::PythonCode => "python_code",
        }
    }

    /// Get the GBNF grammar string for this name.
    #[must_use]
    pub const fn grammar(self) -> &'static str {
        match self {
            Self::JsonObject => JSON_OBJECT_GRAMMAR,
            Self::ToolCall => TOOL_CALL_GRAMMAR,
            Self::PythonCode => PYTHON_CODE_GRAMMAR,
        }
    }

    /// Parse a string into a grammar name.
    #[must_use]
    pub fn parse_name(s: &str) -> Option<Self> {
        match s {
            "json_object" => Some(Self::JsonObject),
            "tool_call" => Some(Self::ToolCall),
            "python_code" => Some(Self::PythonCode),
            _ => None,
        }
    }
}

/// Look up a JSON schema by name.
#[must_use]
pub fn get_schema(name: &str) -> Option<&'static str> {
    SchemaName::parse_name(name).map(SchemaName::schema)
}

/// Look up a GBNF grammar by name.
#[must_use]
pub fn get_grammar(name: &str) -> Option<&'static str> {
    GrammarName::parse_name(name).map(GrammarName::grammar)
}

/// Get all schemas as a map.
#[must_use]
pub fn schema_map() -> HashMap<&'static str, &'static str> {
    SchemaName::all()
        .iter()
        .map(|name| (name.as_str(), name.schema()))
        .collect()
}

/// Get all grammars as a map.
#[must_use]
pub fn grammar_map() -> HashMap<&'static str, &'static str> {
    GrammarName::all()
        .iter()
        .map(|name| (name.as_str(), name.grammar()))
        .collect()
}

// ── JSON Schema Validator ─────────────────────────────────────────────

/// Validation error types.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationError {
    /// JSON parsing failed.
    InvalidJson(String),
    /// Expected an object but got something else.
    NotAnObject,
    /// Required field is missing.
    MissingField(String),
    /// Field has wrong type.
    WrongType {
        /// Field name.
        field: String,
        /// Expected type.
        expected: String,
        /// Actual type.
        actual: String,
    },
    /// Number out of range.
    OutOfRange {
        /// Field name.
        field: String,
        /// Minimum value (if specified).
        min: Option<f64>,
        /// Maximum value (if specified).
        max: Option<f64>,
        /// Actual value.
        actual: f64,
    },
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidJson(msg) => write!(f, "invalid JSON: {msg}"),
            Self::NotAnObject => write!(f, "expected a JSON object"),
            Self::MissingField(field) => write!(f, "missing required field: {field}"),
            Self::WrongType {
                field,
                expected,
                actual,
            } => write!(f, "field '{field}' expected {expected}, got {actual}"),
            Self::OutOfRange {
                field,
                min,
                max,
                actual,
            } => {
                write!(f, "field '{field}' value {actual} out of range")?;
                if let Some(mn) = min {
                    write!(f, " [min={mn}]")?;
                }
                if let Some(mx) = max {
                    write!(f, " [max={mx}]")?;
                }
                Ok(())
            }
        }
    }
}

impl std::error::Error for ValidationError {}

/// Result of validating JSON against a schema.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    /// Whether the JSON is valid against the schema.
    pub valid: bool,
    /// List of validation errors (empty if valid).
    pub errors: Vec<ValidationError>,
}

impl ValidationResult {
    /// Create a successful validation result.
    #[must_use]
    pub const fn ok() -> Self {
        Self {
            valid: true,
            errors: Vec::new(),
        }
    }

    /// Create a failed validation result with a single error.
    #[must_use]
    pub fn fail(error: ValidationError) -> Self {
        Self {
            valid: false,
            errors: vec![error],
        }
    }

    /// Create a failed validation result with multiple errors.
    #[must_use]
    pub fn fail_many(errors: Vec<ValidationError>) -> Self {
        let valid = errors.is_empty();
        Self { valid, errors }
    }
}

/// Validate a JSON string against a named schema.
///
/// Parses the JSON and checks:
/// - Top-level value is an object
/// - All `required` fields are present
/// - Field types match the schema
/// - Numeric ranges (min/max) are satisfied
#[must_use]
pub fn validate_json(json_str: &str, schema_name: SchemaName) -> ValidationResult {
    let schema_str = schema_name.schema();
    let schema: Value = match serde_json::from_str(schema_str) {
        Ok(v) => v,
        Err(e) => {
            return ValidationResult::fail(ValidationError::InvalidJson(format!(
                "schema parse error: {e}"
            )));
        }
    };

    let value: Value = match serde_json::from_str(json_str) {
        Ok(v) => v,
        Err(e) => return ValidationResult::fail(ValidationError::InvalidJson(e.to_string())),
    };

    validate_value(&value, &schema)
}

/// Validate a JSON value against a schema value.
fn validate_value(value: &Value, schema: &Value) -> ValidationResult {
    let schema_type = schema.get("type").and_then(Value::as_str);

    // Check type
    if let Some(expected_type) = schema_type {
        let actual_type = json_type_name(value);
        if !json_type_matches(value, expected_type) {
            return ValidationResult::fail(ValidationError::WrongType {
                field: "root".to_string(),
                expected: expected_type.to_string(),
                actual: actual_type.to_string(),
            });
        }
    }

    // If object, check required fields and properties
    if schema_type == Some("object") || (schema_type.is_none() && value.is_object()) {
        return validate_object(value, schema);
    }

    // Check numeric constraints
    if schema_type == Some("number") || schema_type == Some("integer") {
        if let Some(err) = validate_numeric(value, schema, "root") {
            return ValidationResult::fail(err);
        }
    }

    ValidationResult::ok()
}

/// Validate a JSON object against an object schema.
fn validate_object(value: &Value, schema: &Value) -> ValidationResult {
    let obj = match value.as_object() {
        Some(o) => o,
        None => return ValidationResult::fail(ValidationError::NotAnObject),
    };

    let mut errors = Vec::new();

    // Check required fields
    if let Some(required) = schema.get("required").and_then(Value::as_array) {
        for req in required {
            if let Some(field) = req.as_str() {
                if !obj.contains_key(field) {
                    errors.push(ValidationError::MissingField(field.to_string()));
                }
            }
        }
    }

    // Check property types
    if let Some(properties) = schema.get("properties").and_then(Value::as_object) {
        for (field, prop_schema) in properties {
            if let Some(field_value) = obj.get(field) {
                let prop_result = validate_value(field_value, prop_schema);
                if !prop_result.valid {
                    for err in prop_result.errors {
                        errors.push(match err {
                            ValidationError::WrongType {
                                field: _,
                                expected,
                                actual,
                            } => ValidationError::WrongType {
                                field: field.clone(),
                                expected,
                                actual,
                            },
                            ValidationError::OutOfRange {
                                field: _,
                                min,
                                max,
                                actual,
                            } => ValidationError::OutOfRange {
                                field: field.clone(),
                                min,
                                max,
                                actual,
                            },
                            other => other,
                        });
                    }
                }
            }
        }
    }

    ValidationResult::fail_many(errors)
}

/// Validate numeric constraints (minimum, maximum).
fn validate_numeric(value: &Value, schema: &Value, field: &str) -> Option<ValidationError> {
    let num = value.as_f64()?;

    if let Some(min) = schema.get("minimum").and_then(Value::as_f64) {
        if num < min {
            return Some(ValidationError::OutOfRange {
                field: field.to_string(),
                min: Some(min),
                max: schema.get("maximum").and_then(Value::as_f64),
                actual: num,
            });
        }
    }

    if let Some(max) = schema.get("maximum").and_then(Value::as_f64) {
        if num > max {
            return Some(ValidationError::OutOfRange {
                field: field.to_string(),
                min: schema.get("minimum").and_then(Value::as_f64),
                max: Some(max),
                actual: num,
            });
        }
    }

    None
}

/// Get the JSON type name of a value.
#[must_use]
pub const fn json_type_name(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}

/// Check if a JSON value matches a schema type string.
fn json_type_matches(value: &Value, expected: &str) -> bool {
    match expected {
        "object" => value.is_object(),
        "array" => value.is_array(),
        "string" => value.is_string(),
        "number" => value.is_number(),
        "integer" => value.is_i64() || value.is_u64(),
        "boolean" => value.is_boolean(),
        "null" => value.is_null(),
        _ => true, // Unknown type — don't fail
    }
}

/// Extract a JSON object from LLM output text.
///
/// Finds the first `{` and last `}` in the text and attempts to parse
/// the substring as JSON. Useful when the LLM produces JSON embedded
/// in markdown code blocks or surrounding text.
#[must_use]
pub fn extract_json(text: &str) -> Option<Value> {
    // Try direct parse first
    if let Ok(v) = serde_json::from_str(text) {
        return Some(v);
    }

    // Find first { and last }
    let start = text.find('{')?;
    let end = text.rfind('}')?;
    if end < start {
        return None;
    }
    let candidate = &text[start..=end];
    serde_json::from_str(candidate).ok()
}

/// Extract and validate JSON from LLM output text.
#[must_use]
pub fn extract_and_validate(text: &str, schema_name: SchemaName) -> ValidationResult {
    match extract_json(text) {
        Some(value) => {
            let schema: Value = serde_json::from_str(schema_name.schema()).unwrap_or(Value::Null);
            validate_value(&value, &schema)
        }
        None => ValidationResult::fail(ValidationError::InvalidJson(
            "no JSON object found in text".to_string(),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schema_name_all_returns_seven() {
        assert_eq!(SchemaName::all().len(), 7);
    }

    #[test]
    fn schema_name_as_str() {
        assert_eq!(SchemaName::EntityExtraction.as_str(), "entity_extraction");
        assert_eq!(SchemaName::ToolCall.as_str(), "tool_call");
        assert_eq!(SchemaName::CodeGeneration.as_str(), "code_generation");
    }

    #[test]
    fn schema_name_parse_name_roundtrip() {
        for name in SchemaName::all() {
            let s = name.as_str();
            assert_eq!(SchemaName::parse_name(s), Some(name));
        }
    }

    #[test]
    fn schema_name_parse_name_invalid() {
        assert_eq!(SchemaName::parse_name("nonexistent"), None);
    }

    #[test]
    fn grammar_name_all_returns_three() {
        assert_eq!(GrammarName::all().len(), 3);
    }

    #[test]
    fn grammar_name_as_str() {
        assert_eq!(GrammarName::JsonObject.as_str(), "json_object");
        assert_eq!(GrammarName::ToolCall.as_str(), "tool_call");
        assert_eq!(GrammarName::PythonCode.as_str(), "python_code");
    }

    #[test]
    fn grammar_name_parse_name_roundtrip() {
        for name in GrammarName::all() {
            let s = name.as_str();
            assert_eq!(GrammarName::parse_name(s), Some(name));
        }
    }

    #[test]
    fn get_schema_returns_correct_string() {
        let schema = get_schema("tool_call").unwrap();
        assert!(schema.contains("\"tool\""));
        assert!(schema.contains("\"args\""));
    }

    #[test]
    fn get_schema_unknown_returns_none() {
        assert!(get_schema("nonexistent").is_none());
    }

    #[test]
    fn get_grammar_returns_correct_string() {
        let grammar = get_grammar("json_object").unwrap();
        assert!(grammar.contains("root ::="));
        assert!(grammar.contains("pair"));
    }

    #[test]
    fn get_grammar_unknown_returns_none() {
        assert!(get_grammar("nonexistent").is_none());
    }

    #[test]
    fn schema_map_contains_all() {
        let map = schema_map();
        assert_eq!(map.len(), 7);
        assert!(map.contains_key("entity_extraction"));
        assert!(map.contains_key("code_generation"));
    }

    #[test]
    fn grammar_map_contains_all() {
        let map = grammar_map();
        assert_eq!(map.len(), 3);
        assert!(map.contains_key("json_object"));
        assert!(map.contains_key("python_code"));
    }

    #[test]
    fn validate_valid_tool_call() {
        let json = r#"{"tool": "memory_search", "args": {"query": "test"}}"#;
        let result = validate_json(json, SchemaName::ToolCall);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_missing_required_field() {
        let json = r#"{"tool": "memory_search"}"#;
        let result = validate_json(json, SchemaName::ToolCall);
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| matches!(
            e,
            ValidationError::MissingField(f) if f == "args"
        )));
    }

    #[test]
    fn validate_wrong_type() {
        let json = r#"{"tool": 123, "args": {}}"#;
        let result = validate_json(json, SchemaName::ToolCall);
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| matches!(
            e,
            ValidationError::WrongType { field, .. } if field == "tool"
        )));
    }

    #[test]
    fn validate_security_classification_valid() {
        let json = r#"{"is_attack": true, "confidence": 0.85}"#;
        let result = validate_json(json, SchemaName::SecurityClassification);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_security_classification_confidence_out_of_range() {
        let json = r#"{"is_attack": false, "confidence": 1.5}"#;
        let result = validate_json(json, SchemaName::SecurityClassification);
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| matches!(
            e,
            ValidationError::OutOfRange { field, .. } if field == "confidence"
        )));
    }

    #[test]
    fn validate_safety_evaluation_valid() {
        let json = r#"{"score": 0.5, "reasoning": "looks safe"}"#;
        let result = validate_json(json, SchemaName::SafetyEvaluation);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_entity_extraction_valid() {
        let json = r#"{"entities": [{"name": "Alice", "type": "person"}], "relations": []}"#;
        let result = validate_json(json, SchemaName::EntityExtraction);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_content_summary_valid() {
        let json = r#"{"summary": "A test document", "key_points": ["point 1"]}"#;
        let result = validate_json(json, SchemaName::ContentSummary);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_content_summary_missing_required() {
        let json = r#"{"key_points": ["point 1"]}"#;
        let result = validate_json(json, SchemaName::ContentSummary);
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| matches!(
            e,
            ValidationError::MissingField(f) if f == "summary"
        )));
    }

    #[test]
    fn validate_code_generation_valid() {
        let json = r#"{"code": "print(42)", "language": "python"}"#;
        let result = validate_json(json, SchemaName::CodeGeneration);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_invalid_json() {
        let json = "not json at all";
        let result = validate_json(json, SchemaName::ToolCall);
        assert!(!result.valid);
        assert!(
            result
                .errors
                .iter()
                .any(|e| matches!(e, ValidationError::InvalidJson(_)))
        );
    }

    #[test]
    fn validate_not_an_object() {
        let json = "[1, 2, 3]";
        let result = validate_json(json, SchemaName::ToolCall);
        assert!(!result.valid);
    }

    #[test]
    fn validate_tool_call_list_valid() {
        let json = r#"{"tool_calls": [{"tool": "search", "args": {}}], "final_answer": "done"}"#;
        let result = validate_json(json, SchemaName::ToolCallList);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn extract_json_direct_parse() {
        let result = extract_json(r#"{"key": "value"}"#);
        assert!(result.is_some());
        assert_eq!(
            result.unwrap().get("key").and_then(Value::as_str),
            Some("value")
        );
    }

    #[test]
    fn extract_json_from_markdown_block() {
        let text = "Here is the result:\n```json\n{\"tool\": \"test\", \"args\": {}}\n```\nDone.";
        let result = extract_json(text);
        assert!(result.is_some());
        assert_eq!(
            result.unwrap().get("tool").and_then(Value::as_str),
            Some("test")
        );
    }

    #[test]
    fn extract_json_embedded_in_text() {
        let text = "The answer is {\"score\": 0.9, \"reasoning\": \"good\"} as you can see.";
        let result = extract_json(text);
        assert!(result.is_some());
    }

    #[test]
    fn extract_json_no_json_returns_none() {
        assert!(extract_json("no json here").is_none());
    }

    #[test]
    fn extract_and_validate_valid() {
        let text = r#"Result: {"tool": "search", "args": {"q": "test"}}"#;
        let result = extract_and_validate(text, SchemaName::ToolCall);
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn extract_and_validate_no_json() {
        let result = extract_and_validate("no json here", SchemaName::ToolCall);
        assert!(!result.valid);
    }

    #[test]
    fn validation_error_display() {
        let err = ValidationError::MissingField("test".to_string());
        assert!(err.to_string().contains("test"));
        let err = ValidationError::InvalidJson("bad".to_string());
        assert!(err.to_string().contains("bad"));
    }

    #[test]
    fn validation_result_ok() {
        let result = ValidationResult::ok();
        assert!(result.valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn validation_result_fail() {
        let result = ValidationResult::fail(ValidationError::NotAnObject);
        assert!(!result.valid);
        assert_eq!(result.errors.len(), 1);
    }

    #[test]
    fn all_schemas_are_valid_json() {
        for name in SchemaName::all() {
            let result: Result<Value, _> = serde_json::from_str(name.schema());
            assert!(result.is_ok(), "schema {} is not valid JSON", name.as_str());
        }
    }

    #[test]
    fn all_grammars_contain_root_rule() {
        for name in GrammarName::all() {
            assert!(
                name.grammar().contains("root ::="),
                "grammar {} missing root rule",
                name.as_str()
            );
        }
    }

    #[test]
    fn entity_extraction_schema_has_entities_and_relations() {
        let schema: Value = serde_json::from_str(ENTITY_EXTRACTION_SCHEMA).unwrap();
        let props = schema.get("properties").unwrap();
        assert!(props.get("entities").is_some());
        assert!(props.get("relations").is_some());
    }

    #[test]
    fn tool_call_schema_has_tool_and_args() {
        let schema: Value = serde_json::from_str(TOOL_CALL_SCHEMA).unwrap();
        let props = schema.get("properties").unwrap();
        assert!(props.get("tool").is_some());
        assert!(props.get("args").is_some());
    }

    #[test]
    fn validate_multiple_errors() {
        // Both tool and args missing
        let json = "{}";
        let result = validate_json(json, SchemaName::ToolCall);
        assert!(!result.valid);
        assert_eq!(result.errors.len(), 2);
    }

    #[test]
    fn validate_integer_type() {
        let json = r#"{"is_attack": true, "confidence": 1}"#;
        let result = validate_json(json, SchemaName::SecurityClassification);
        // 1 is a valid number even though schema says "number"
        assert!(result.valid, "errors: {:?}", result.errors);
    }

    #[test]
    fn validate_boolean_type() {
        let json = r#"{"is_attack": "yes", "confidence": 0.5}"#;
        let result = validate_json(json, SchemaName::SecurityClassification);
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| matches!(
            e,
            ValidationError::WrongType { field, expected, .. } if field == "is_attack" && expected == "boolean"
        )));
    }
}
