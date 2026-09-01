//! Speculative Execution Validator — pre-validates outputs before dispatch.
//!
//! Ported from v2's optimization/speculative_exec.py.
//! Validates AI-generated code or text using a hierarchy of cheap checks:
//! 1. Bracket/brace balance check (< 1ms)
//! 2. Security heuristics — regex scan for SQLi, hardcoded secrets, dangerous calls
//! 3. (Future) Local LLM sanity check
//!
//! Prevents invalid or unsafe outputs from reaching expensive downstream
//! processes or the user.

use regex::Regex;
use std::sync::OnceLock;

static SQL_INJECTION_RE: OnceLock<Regex> = OnceLock::new();
static HARDCODED_SECRET_RE: OnceLock<Regex> = OnceLock::new();
static DANGEROUS_EXEC_RE: OnceLock<Regex> = OnceLock::new();

fn sql_injection_re() -> &'static Regex {
    SQL_INJECTION_RE.get_or_init(|| Regex::new(r#"(?i)execute\(\s*f["']"#).unwrap())
}

fn hardcoded_secret_re() -> &'static Regex {
    HARDCODED_SECRET_RE.get_or_init(|| {
        Regex::new(r#"(?i)(api_key|secret|password|token)\s*=\s*["'][A-Za-z0-9\-_]{20,}["']"#)
            .unwrap()
    })
}

fn dangerous_exec_re() -> &'static Regex {
    DANGEROUS_EXEC_RE.get_or_init(|| Regex::new(r"\b(exec|eval|system|popen)\s*\(").unwrap())
}

/// Result of a single validation check.
#[derive(Debug, Clone)]
pub struct CheckResult {
    /// Check name
    pub name: &'static str,
    /// Whether the check passed
    pub passed: bool,
    /// Error message if failed
    pub error: Option<String>,
    /// Issues found (for security checks)
    pub issues: Vec<String>,
}

/// Full validation result.
#[derive(Debug, Clone)]
pub struct ValidationResult {
    /// Overall validity — true only if all checks passed
    pub valid: bool,
    /// Individual check results
    pub checks: Vec<CheckResult>,
    /// All error messages
    pub errors: Vec<String>,
}

impl ValidationResult {
    /// Create a new passing result.
    #[must_use]
    pub const fn passing() -> Self {
        Self {
            valid: true,
            checks: Vec::new(),
            errors: Vec::new(),
        }
    }
}

/// Speculative executor — validates code/text candidates.
///
/// Uses a hierarchy of cheap-to-expensive checks. Fails fast: if a cheap
/// check fails, more expensive checks are skipped.
pub struct SpeculativeExecutor {
    /// Whether to run security heuristics
    pub check_security: bool,
    /// Whether to run bracket balance check
    pub check_brackets: bool,
}

impl Default for SpeculativeExecutor {
    fn default() -> Self {
        Self {
            check_security: true,
            check_brackets: true,
        }
    }
}

impl SpeculativeExecutor {
    /// Create a new executor with all checks enabled.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            check_security: true,
            check_brackets: true,
        }
    }

    /// Check bracket/brace/paren balance in code.
    ///
    /// Returns `(balanced, error_message)`.
    #[must_use]
    pub fn check_bracket_balance(code: &str) -> (bool, Option<String>) {
        let mut paren = 0i32;
        let mut bracket = 0i32;
        let mut brace = 0i32;
        let mut in_string = false;
        let mut string_char = '\0';
        let mut escaped = false;

        for ch in code.chars() {
            if escaped {
                escaped = false;
                continue;
            }
            if ch == '\\' && in_string {
                escaped = true;
                continue;
            }
            if in_string {
                if ch == string_char {
                    in_string = false;
                }
                continue;
            }
            match ch {
                '"' | '\'' => {
                    in_string = true;
                    string_char = ch;
                }
                '(' => paren += 1,
                ')' => paren -= 1,
                '[' => bracket += 1,
                ']' => bracket -= 1,
                '{' => brace += 1,
                '}' => brace -= 1,
                _ => {}
            }
            if paren < 0 || bracket < 0 || brace < 0 {
                return (false, Some(format!("Unmatched closing delimiter at: {ch}")));
            }
        }

        if paren != 0 {
            return (
                false,
                Some(format!("Unbalanced parentheses: offset {paren}")),
            );
        }
        if bracket != 0 {
            return (
                false,
                Some(format!("Unbalanced brackets: offset {bracket}")),
            );
        }
        if brace != 0 {
            return (false, Some(format!("Unbalanced braces: offset {brace}")));
        }

        (true, None)
    }

    /// Fast regex scan for obvious security issues.
    ///
    /// Returns `(clean, issues)`.
    #[must_use]
    pub fn check_security_heuristics(code: &str) -> (bool, Vec<String>) {
        let mut issues = Vec::new();

        if sql_injection_re().is_match(code) {
            issues.push("Potential SQL Injection (f-string in execute)".to_string());
        }

        if hardcoded_secret_re().is_match(code) {
            issues.push("Potential hardcoded secret".to_string());
        }

        if dangerous_exec_re().is_match(code) {
            issues.push("Dangerous usage of exec/eval/system/popen".to_string());
        }

        (issues.is_empty(), issues)
    }

    /// Run full validation pipeline.
    #[must_use]
    pub fn validate(&self, content: &str) -> ValidationResult {
        let mut result = ValidationResult::passing();

        if self.check_brackets {
            let (balanced, err) = Self::check_bracket_balance(content);
            let check = CheckResult {
                name: "bracket_balance",
                passed: balanced,
                error: err.clone(),
                issues: Vec::new(),
            };
            result.checks.push(check);
            if !balanced {
                result.valid = false;
                if let Some(e) = err {
                    result.errors.push(e);
                }
                return result; // Fail fast
            }
        }

        if self.check_security {
            let (clean, issues) = Self::check_security_heuristics(content);
            let check = CheckResult {
                name: "security",
                passed: clean,
                error: None,
                issues: issues.clone(),
            };
            result.checks.push(check);
            if !clean {
                result.valid = false;
                result.errors.extend(issues);
            }
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bracket_balance_ok() {
        let (ok, err) = SpeculativeExecutor::check_bracket_balance("fn main() { let x = [1, 2]; }");
        assert!(ok);
        assert!(err.is_none());
    }

    #[test]
    fn bracket_balance_unmatched() {
        let (ok, err) = SpeculativeExecutor::check_bracket_balance("fn main() {");
        assert!(!ok);
        assert!(err.is_some());
    }

    #[test]
    fn bracket_balance_ignores_strings() {
        let (ok, _) =
            SpeculativeExecutor::check_bracket_balance("let s = \"(unmatched in string\";");
        assert!(ok);
    }

    #[test]
    fn bracket_balance_ignores_escapes() {
        let (ok, _) = SpeculativeExecutor::check_bracket_balance("let s = \"\\\"escaped\\\"\";");
        assert!(ok);
    }

    #[test]
    fn security_clean_code() {
        let (clean, issues) = SpeculativeExecutor::check_security_heuristics("let x = 1 + 2;");
        assert!(clean);
        assert!(issues.is_empty());
    }

    #[test]
    fn security_detects_sql_injection() {
        let (clean, issues) = SpeculativeExecutor::check_security_heuristics(
            "cursor.execute(f\"SELECT * FROM {table}\")",
        );
        assert!(!clean);
        assert!(issues.iter().any(|i| i.contains("SQL Injection")));
    }

    #[test]
    fn security_detects_hardcoded_secret() {
        let (clean, issues) = SpeculativeExecutor::check_security_heuristics(
            "api_key = \"abcdefghijklmnopqrstuvwxyz123456\"",
        );
        assert!(!clean);
        assert!(issues.iter().any(|i| i.contains("secret")));
    }

    #[test]
    fn security_detects_dangerous_exec() {
        let (clean, issues) = SpeculativeExecutor::check_security_heuristics("eval(user_input)");
        assert!(!clean);
        assert!(issues.iter().any(|i| i.contains("exec/eval")));
    }

    #[test]
    fn validate_passes_clean_code() {
        let executor = SpeculativeExecutor::default();
        let result = executor.validate("fn add(a: i32, b: i32) -> i32 { a + b }");
        assert!(result.valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn validate_fails_on_unbalanced() {
        let executor = SpeculativeExecutor::default();
        let result = executor.validate("fn add(a: i32 {");
        assert!(!result.valid);
        assert!(!result.errors.is_empty());
    }

    #[test]
    fn validate_fails_on_security() {
        let executor = SpeculativeExecutor::default();
        let result = executor.validate("eval(\"dangerous code\")");
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| e.contains("exec/eval")));
    }

    #[test]
    fn validate_fail_fast_on_brackets() {
        let executor = SpeculativeExecutor::default();
        let result = executor.validate("fn { eval(\"bad\")");
        // Should fail on brackets before security
        assert!(!result.valid);
        // Only bracket check should have run
        assert_eq!(result.checks.len(), 1);
        assert_eq!(result.checks[0].name, "bracket_balance");
    }

    #[test]
    fn validate_passes_with_security_disabled() {
        let mut executor = SpeculativeExecutor::new();
        executor.check_security = false;
        let result = executor.validate("let x = 1;");
        assert!(result.valid);
        // Only bracket check should run
        assert_eq!(result.checks.len(), 1);
    }
}
