//! Credential-shape detection for memory content.
//!
//! Phase 3 secrets hygiene: `wm ingest` refuses credential-shaped
//! *filenames* (`.env`, keys, certs); this module extends the same
//! discipline to *content*. A store that silently swallows an API key
//! becomes a liability the moment it is backed up, mesh-synced, or fed
//! into a model context — so writes that look credential-bearing are
//! flagged at the tool layer (warn + advise a keyring, not refuse:
//! false-positive-proof refusal would train agents to hide secrets
//! worse).
//!
//! High-precision heuristics only — the goal is to warn on real
//! credentials without crying wolf on ordinary prose.

#![forbid(unsafe_code)]

/// Kinds of credential shapes the detector recognizes.
pub const ADVICE: &str = "keep the secret in a keyring (OS keychain, pass, systemd-credentials) and store a reference in memory instead; memory privacy flags are not encryption";

/// Detect credential-shaped content. Returns the matched kinds
/// (e.g. `["private_key_pem", "github_token"]`); empty means clean.
#[must_use]
pub fn credential_shaped_content(content: &str) -> Vec<&'static str> {
    let mut kinds: Vec<&'static str> = Vec::new();
    let push = |k: &'static str, kinds: &mut Vec<&'static str>| {
        if !kinds.contains(&k) {
            kinds.push(k);
        }
    };

    // 1. PEM private keys (RSA/OpenSSH/EC/PKCS8/PGP/encrypted).
    if content.contains("-----BEGIN") && content.contains("PRIVATE KEY") {
        push("private_key_pem", &mut kinds);
    }

    // 2. AWS access key ids: AKIA + 16 uppercase/digits.
    if token_after(content, "AKIA", 16, |c| {
        c.is_ascii_uppercase() || c.is_ascii_digit()
    }) {
        push("aws_access_key_id", &mut kinds);
    }

    // 3. GitHub tokens.
    let alnum = |c: char| c.is_ascii_alphanumeric() || c == '_';
    if token_after(content, "ghp_", 30, alnum)
        || token_after(content, "gho_", 30, alnum)
        || token_after(content, "github_pat_", 20, alnum)
    {
        push("github_token", &mut kinds);
    }

    // 4. OpenAI-style keys: sk- + 20 token chars.
    if token_after(content, "sk-", 20, |c| {
        c.is_ascii_alphanumeric() || c == '_' || c == '-'
    }) {
        push("openai_style_key", &mut kinds);
    }

    // 5. Slack tokens: xox{b,p,a,r,s}-.
    if ["xoxb-", "xoxp-", "xoxa-", "xoxr-", "xoxs-"]
        .iter()
        .any(|p| token_after(content, p, 10, |c| c.is_ascii_alphanumeric() || c == '-'))
    {
        push("slack_token", &mut kinds);
    }

    // 6. JWTs: two base64url segments separated by dots.
    if content.match_indices("eyJ").count() >= 2 {
        push("jwt", &mut kinds);
    }

    // 7. Assignment shapes: password/secret/api_key/token followed by a
    //    delimiter and a 16+ char value.
    if assignment_shaped(content) {
        push("credential_assignment", &mut kinds);
    }

    kinds
}

/// Scan for `prefix` followed by at least `min_len` charset characters.
fn token_after(
    haystack: &str,
    prefix: &str,
    min_len: usize,
    charset: impl Fn(char) -> bool,
) -> bool {
    let mut from = 0usize;
    while let Some(pos) = haystack[from..].find(prefix) {
        let abs = from + pos + prefix.len();
        let run = haystack[abs..].chars().take_while(|c| charset(*c)).count();
        if run >= min_len {
            return true;
        }
        from = abs;
    }
    false
}

/// Case-insensitive `password = "..."` / `api_key: ...` detection with a
/// 16+ character non-space value.
fn assignment_shaped(content: &str) -> bool {
    const KEYS: &[&str] = &[
        "password",
        "passwd",
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "access_token",
    ];
    let lower = content.to_lowercase();
    for key in KEYS {
        let mut from = 0usize;
        while let Some(pos) = lower[from..].find(key) {
            let abs = from + pos + key.len();
            let rest = lower[abs..].trim_start();
            let Some(delim) = rest.chars().next() else {
                break;
            };
            if delim == ':' || delim == '=' {
                let value = rest[1..].trim_start();
                let value = value.strip_prefix(['"', '\'']).unwrap_or(value);
                // Redaction markers must never re-trigger detection, or the
                // scrubber loops on its own output.
                if !value.starts_with("[REDACTED:") {
                    let run: usize = value
                        .chars()
                        .take_while(|c| !c.is_whitespace() && *c != '"' && *c != '\'')
                        .map(char::len_utf8)
                        .sum();
                    if run >= 16 {
                        return true;
                    }
                }
            }
            from = abs;
        }
    }
    false
}

/// Redact credential-shaped spans, replacing them with `[REDACTED:<kind>]`.
///
/// Detection is [`credential_shaped_content`]; when nothing fires the text is
/// returned unchanged. Redaction is span-oriented (PEM blocks, prefixed
/// tokens, assignment values) and deliberately over-redacts rather than
/// under-redacts. Returns the redacted text and the kinds that fired, using
/// the same labels as detection.
#[must_use]
pub fn redact_credential_content(content: &str) -> (String, Vec<&'static str>) {
    let kinds = credential_shaped_content(content);
    if kinds.is_empty() {
        return (content.to_string(), kinds);
    }

    let mut out = content.to_string();

    if kinds.contains(&"private_key_pem") {
        while let Some((start, end)) = pem_block_span(&out) {
            out.replace_range(start..end, "[REDACTED:private_key_pem]");
        }
    }

    if kinds.contains(&"credential_assignment") {
        while let Some((start, end)) = assignment_value_span(&out) {
            out.replace_range(start..end, "[REDACTED:credential_assignment]");
        }
    }

    type TokenSpec = (&'static str, &'static str, usize, fn(char) -> bool);
    let token_specs: &[TokenSpec] = &[
        ("aws_access_key_id", "AKIA", 16, |c: char| {
            c.is_ascii_uppercase() || c.is_ascii_digit()
        }),
        ("github_token", "ghp_", 30, |c: char| {
            c.is_ascii_alphanumeric() || c == '_'
        }),
        ("github_token", "gho_", 30, |c: char| {
            c.is_ascii_alphanumeric() || c == '_'
        }),
        ("github_token", "github_pat_", 20, |c: char| {
            c.is_ascii_alphanumeric() || c == '_'
        }),
        ("openai_style_key", "sk-", 20, |c: char| {
            c.is_ascii_alphanumeric() || c == '_' || c == '-'
        }),
        ("slack_token", "xoxb-", 10, |c: char| {
            c.is_ascii_alphanumeric() || c == '-'
        }),
        ("slack_token", "xoxp-", 10, |c: char| {
            c.is_ascii_alphanumeric() || c == '-'
        }),
        ("slack_token", "xoxa-", 10, |c: char| {
            c.is_ascii_alphanumeric() || c == '-'
        }),
        ("slack_token", "xoxr-", 10, |c: char| {
            c.is_ascii_alphanumeric() || c == '-'
        }),
        ("slack_token", "xoxs-", 10, |c: char| {
            c.is_ascii_alphanumeric() || c == '-'
        }),
        ("jwt", "eyJ", 8, |c: char| {
            c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '.'
        }),
    ];
    for (kind, prefix, min_len, charset) in token_specs {
        while let Some((start, end)) = prefixed_token_span(&out, prefix, *min_len, *charset) {
            out.replace_range(start..end, &format!("[REDACTED:{kind}]"));
        }
    }

    (out, kinds)
}

/// Span of the first PEM private-key block (including its BEGIN/END markers).
fn pem_block_span(text: &str) -> Option<(usize, usize)> {
    let begin = text.find("-----BEGIN")?;
    let key_at = text[begin..].find("PRIVATE KEY-----")? + begin;
    let end_at = text[key_at..].find("-----END")? + key_at;
    let marker_at = text[end_at..].find("PRIVATE KEY-----")? + end_at;
    Some((begin, marker_at + "PRIVATE KEY-----".len()))
}

/// Span of the first assignment *value* (the 16+ char secret, not the key).
fn assignment_value_span(text: &str) -> Option<(usize, usize)> {
    const KEYS: &[&str] = &[
        "password",
        "passwd",
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "access_token",
    ];
    for key in KEYS {
        let mut from = 0usize;
        while let Some(pos) = find_ascii_case_insensitive(text, key, from) {
            let after = pos + key.len();
            let rest = &text[after..];
            let ws = rest.len() - rest.trim_start().len();
            let delim_pos = after + ws;
            let delim = text[delim_pos..].chars().next();
            if matches!(delim, Some(':' | '=')) {
                let tail = &text[delim_pos + 1..];
                let vws = tail.len() - tail.trim_start().len();
                let mut vstart = delim_pos + 1 + vws;
                if let Some(quote) = text[vstart..].chars().next() {
                    if quote == '"' || quote == '\'' {
                        vstart += quote.len_utf8();
                    }
                }
                let mut bytes = 0usize;
                for c in text[vstart..].chars() {
                    if c.is_whitespace() || c == '"' || c == '\'' {
                        break;
                    }
                    bytes += c.len_utf8();
                }
                if bytes >= 16 && !text[vstart..].starts_with("[REDACTED:") {
                    return Some((vstart, vstart + bytes));
                }
            }
            from = after;
        }
    }
    None
}

/// Span of the first `prefix` + charset run of at least `min_len` characters.
fn prefixed_token_span(
    text: &str,
    prefix: &str,
    min_len: usize,
    charset: fn(char) -> bool,
) -> Option<(usize, usize)> {
    let mut from = 0usize;
    while let Some(pos) = text[from..].find(prefix) {
        let start = from + pos;
        let value_start = start + prefix.len();
        let mut bytes = 0usize;
        let mut count = 0usize;
        for c in text[value_start..].chars() {
            if !charset(c) {
                break;
            }
            bytes += c.len_utf8();
            count += 1;
        }
        if count >= min_len {
            return Some((start, value_start + bytes));
        }
        from = value_start;
    }
    None
}

/// ASCII-case-insensitive substring search starting at `from`.
fn find_ascii_case_insensitive(haystack: &str, needle: &str, from: usize) -> Option<usize> {
    let h = haystack.as_bytes();
    let n = needle.as_bytes();
    if n.is_empty() || from >= h.len() || n.len() > h.len() - from {
        return None;
    }
    (from..=h.len() - n.len()).find(|&i| h[i..i + n.len()].eq_ignore_ascii_case(n))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_private_keys_aws_and_github() {
        let pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n-----END RSA PRIVATE KEY-----";
        assert_eq!(credential_shaped_content(pem), vec!["private_key_pem"]);

        let aws = "access id AKIAIOSFODNN7EXAMPLE found in logs";
        assert_eq!(credential_shaped_content(aws), vec!["aws_access_key_id"]);

        let gh = "token ghp_0123456789abcdefghijklmnopqrstuvwxyzABC pasted";
        assert_eq!(credential_shaped_content(gh), vec!["github_token"]);
    }

    #[test]
    fn detects_sk_slack_jwt_and_assignments() {
        let sk = "key: sk-proj0123456789abcdefghijklmnopqrstuv";
        assert_eq!(credential_shaped_content(sk), vec!["openai_style_key"]);

        // Assembled at runtime: the raw Slack token shape must never appear
        // in source (GitHub push protection blocks it), while the detector
        // must still match the real shape at runtime.
        let slack = format!(
            "xoxb-{}-{}-{}",
            "123456789012", "1234567890123", "abcdefghijklmnop"
        );
        assert_eq!(credential_shaped_content(&slack), vec!["slack_token"]);

        let jwt = "header eyJhbGciOiJIUzI1NiJ9.payload eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig";
        assert_eq!(credential_shaped_content(jwt), vec!["jwt"]);

        let assign = "connect with DATABASE_PASSWORD=correct-horse-battery-staple-1 tomorrow";
        assert_eq!(
            credential_shaped_content(assign),
            vec!["credential_assignment"]
        );
    }

    #[test]
    fn ordinary_prose_stays_clean() {
        assert!(
            credential_shaped_content("remember that the password policy requires rotation")
                .is_empty()
        );
        assert!(credential_shaped_content("api_key rotation happens quarterly").is_empty());
        assert!(credential_shaped_content("short token: abc123").is_empty());
        assert!(
            credential_shaped_content("the sk- prefix marks OpenAI keys in general").is_empty()
        );
        assert!(credential_shaped_content("AKIA is the AWS key prefix").is_empty());
        assert!(credential_shaped_content("we discussed jwt sessions at length").is_empty());
    }

    #[test]
    fn dedupes_kinds() {
        let both = "AKIAIOSFODNN7EXAMPLE and AKIAIOSFODNN7EXAMPLE again";
        assert_eq!(credential_shaped_content(both), vec!["aws_access_key_id"]);
    }

    #[test]
    fn redacts_private_key_blocks() {
        let pem = "before\n-----BEGIN RSA PRIVATE KEY-----\nMIIEowSECRET\n-----END RSA PRIVATE KEY-----\nafter";
        let (redacted, kinds) = redact_credential_content(pem);
        assert!(kinds.contains(&"private_key_pem"));
        assert!(!redacted.contains("MIIEowSECRET"), "key body must be gone");
        assert!(!redacted.contains("BEGIN RSA PRIVATE KEY"));
        assert_eq!(redacted, "before\n[REDACTED:private_key_pem]\nafter");
    }

    #[test]
    fn redacts_assignment_values_and_tokens() {
        let text = "db password=correct-horse-battery-staple and key sk-proj0123456789abcdefghijklmnopqrstuv";
        let (redacted, _) = redact_credential_content(text);
        assert!(redacted.contains("password=[REDACTED:credential_assignment]"));
        assert!(!redacted.contains("correct-horse-battery-staple"));
        assert!(!redacted.contains("sk-proj0123456789abcdefghijklmnopqrstuv"));
        assert!(redacted.contains("[REDACTED:openai_style_key]"));

        let aws = "id AKIAIOSFODNN7EXAMPLE here";
        let (redacted, _) = redact_credential_content(aws);
        assert_eq!(redacted, "id [REDACTED:aws_access_key_id] here");
    }

    #[test]
    fn clean_content_passes_through_unchanged() {
        let text = "remember that the password policy requires rotation";
        let (redacted, kinds) = redact_credential_content(text);
        assert!(kinds.is_empty());
        assert_eq!(redacted, text);
    }

    #[test]
    fn redaction_is_idempotent() {
        let text = "key sk-proj0123456789abcdefghijklmnopqrstuv end";
        let (once, _) = redact_credential_content(text);
        let (twice, kinds) = redact_credential_content(&once);
        assert_eq!(once, twice);
        assert!(
            kinds.is_empty(),
            "redacted marker must read clean: {kinds:?}"
        );
    }
}
