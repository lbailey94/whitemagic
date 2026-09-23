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

    // 8. Credential-bearing URI userinfo (`scheme://user:pass@host`),
    //    independent of any surrounding variable name — a bare URL in prose
    //    and `DATABASE_URL=...` are the same shape (2026-09-21 review:
    //    connection strings survived `--redact` because only keyed
    //    assignments were scanned).
    if uri_userinfo_span(content).is_some() {
        push("credential_uri", &mut kinds);
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

/// Assignment-key names (case-insensitive) whose `=`/`:` value is treated as
/// a secret. Compound keys are listed explicitly because the delimiter must
/// immediately follow the key name: `secret` alone never matches
/// `AWS_SECRET_ACCESS_KEY=...` (the `_` blocks the delimiter check).
///
/// 2026-09-21 review: `token` was missing although the detection comment
/// claimed it, so `TOKEN=...` and every `*_token=...` compound (the
/// delimiter follows the `token` substring) survived `--redact`. Compounds
/// ending in a listed key are covered by that key; only compounds where the
/// suffix blocks the delimiter (`secret_access_key`) need their own entry.
const ASSIGNMENT_KEYS: &[&str] = &[
    "password",
    "passwd",
    "passphrase",
    "api_key",
    "api-key",
    "apikey",
    "secret",
    "token",
    "access_token",
    "secret_access_key",
    "aws_secret_access_key",
    "secret_key",
    "client_secret",
    "private_key",
    "auth_token",
    "refresh_token",
];

/// Case-insensitive `password = "..."` / `api_key: ...` detection with a
/// 16+ character non-space value.
fn assignment_shaped(content: &str) -> bool {
    let lower = content.to_lowercase();
    for key in ASSIGNMENT_KEYS {
        let mut from = 0usize;
        while let Some(pos) = lower[from..].find(key) {
            let abs = from + pos + key.len();
            let rest = lower[abs..].trim_start();
            // JSON-style keys close the quote first: `"api_key": "..."`.
            let rest = rest.strip_prefix('"').unwrap_or(rest).trim_start();
            let Some(delim) = rest.chars().next() else {
                break;
            };
            if delim == ':' || delim == '=' {
                let value = rest[1..].trim_start();
                let value = value.strip_prefix(['"', '\'']).unwrap_or(value);
                // Redaction markers must never re-trigger detection, or the
                // scrubber loops on its own output. `value` comes from the
                // lowercased text, so the marker check is case-insensitive.
                let is_marker = value
                    .get(..10)
                    .is_some_and(|p| p.eq_ignore_ascii_case("[REDACTED:"));
                if !is_marker {
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
        // Detection fires on any content holding both "-----BEGIN" and
        // "PRIVATE KEY" — including truncated/example fragments with no
        // complete END block, which the span loop above cannot match.
        // Neutralize the marker strings so the pass is idempotent.
        out = out.replace("PRIVATE KEY-----", "[REDACTED:pem-key]");
        out = out.replace("-----BEGIN", "[REDACTED:pem-begin]");
        out = out.replace("-----END", "[REDACTED:pem-end]");
    }

    if kinds.contains(&"credential_assignment") {
        while let Some((start, end)) = assignment_value_span(&out) {
            out.replace_range(start..end, "[REDACTED:credential_assignment]");
        }
    }

    if kinds.contains(&"credential_uri") {
        while let Some((start, end)) = uri_userinfo_span(&out) {
            out.replace_range(start..end, "[REDACTED:credential_uri]");
        }
    }

    // JWT detection fires on any two `eyJ` occurrences (fragments included),
    // so redaction must remove every occurrence — a min-run scan left short
    // fragments detectable and the apply pass non-idempotent.
    if kinds.contains(&"jwt") {
        while let Some(pos) = out.find("eyJ") {
            out.replace_range(pos..pos + "eyJ".len(), "[REDACTED:jwt]");
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
    for key in ASSIGNMENT_KEYS {
        let mut from = 0usize;
        while let Some(pos) = find_ascii_case_insensitive(text, key, from) {
            let after = pos + key.len();
            let rest_raw = &text[after..];
            // JSON-style keys close their quote first: `"api_key": "..."`.
            let quoted = rest_raw.strip_prefix('"').is_some();
            let rest = rest_raw.strip_prefix('"').unwrap_or(rest_raw);
            let ws = rest.len() - rest.trim_start().len();
            let delim_pos = after + usize::from(quoted) + ws;
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
                let is_marker = text[vstart..]
                    .get(..10)
                    .is_some_and(|p| p.eq_ignore_ascii_case("[REDACTED:"));
                if bytes >= 16 && !is_marker {
                    return Some((vstart, vstart + bytes));
                }
            }
            from = after;
        }
    }
    None
}

/// Span of the first credential-bearing URI userinfo
/// (`scheme://user:pass@host`).
///
/// Structural, not key-based: the authority (between `://` and the first
/// `/`, `?`, `#`, or whitespace) must contain `@`, and the userinfo before
/// the last `@` must contain a colon with a non-empty password. URLs without
/// userinfo (`https://example.com/x`), bare usernames
/// (`ssh://git@github.com:22/repo`), and `host:port` pairs stay clean.
/// Redaction replaces the whole userinfo — user and password — deliberately
/// over- rather than under-redacting.
fn uri_userinfo_span(text: &str) -> Option<(usize, usize)> {
    let mut from = 0usize;
    while let Some(rel) = text[from..].find("://") {
        let sep = from + rel;
        let authority_start = sep + 3;
        let scheme_start = text[..sep]
            .rfind(|c: char| !(c.is_ascii_alphanumeric() || c == '+' || c == '.' || c == '-'))
            .map_or(0, |i| {
                // `rfind` returns the byte index of the char start; advance by
                // its UTF-8 width so a multibyte neighbor (e.g. '†' before
                // "://") cannot land the slice mid-character (2026-09-23
                // ingest panic: "start byte index ... is not a char boundary").
                i + text[i..].chars().next().map_or(1, char::len_utf8)
            });
        let scheme = &text[scheme_start..sep];
        let scheme_ok = scheme.starts_with(|c: char| c.is_ascii_alphabetic());
        if scheme_ok {
            let authority_end = text[authority_start..]
                .find(|c: char| c == '/' || c == '?' || c == '#' || c.is_whitespace())
                .map_or(text.len(), |i| authority_start + i);
            if let Some(at_rel) = text[authority_start..authority_end].rfind('@') {
                let at = authority_start + at_rel;
                let userinfo = &text[authority_start..at];
                if let Some(colon_rel) = userinfo.rfind(':') {
                    let password = &userinfo[colon_rel + 1..];
                    // The redaction marker must never re-trigger detection,
                    // or the apply pass is not idempotent.
                    let is_marker = userinfo
                        .get(..10)
                        .is_some_and(|p| p.eq_ignore_ascii_case("[REDACTED:"));
                    if !password.is_empty() && !is_marker {
                        return Some((authority_start, at));
                    }
                }
            }
        }
        from = authority_start;
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
    fn detects_aws_secret_and_compound_assignment_keys() {
        // Regression (P0, 2026-09-14): in AWS_SECRET_ACCESS_KEY the `secret`
        // key name is followed by `_`, so the delimiter check never fired and
        // the secret survived `wm ingest --redact`. Compound keys now need
        // no special-casing at the call sites — they are listed explicitly.
        let aws = "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY";
        assert_eq!(
            credential_shaped_content(aws),
            vec!["credential_assignment"]
        );
        let (redacted, kinds) = redact_credential_content(aws);
        assert!(kinds.contains(&"credential_assignment"));
        assert_eq!(
            redacted,
            "AWS_SECRET_ACCESS_KEY=[REDACTED:credential_assignment]"
        );
        assert!(
            credential_shaped_content(&redacted).is_empty(),
            "redacted AWS secret must read clean: {redacted}"
        );
        let (twice, _) = redact_credential_content(&redacted);
        assert_eq!(redacted, twice);

        // Compound keys with identifier suffixes need explicit listing.
        for text in [
            "secret_access_key=0123456789abcdef",
            "secret_key: 0123456789abcdef",
            "refresh_token=0123456789abcdef",
            "auth_token=0123456789abcdef",
        ] {
            assert_eq!(
                credential_shaped_content(text),
                vec!["credential_assignment"],
                "{text}"
            );
        }

        // Prose naming the key without an assignment stays clean.
        assert!(
            credential_shaped_content("the aws secret access key rotation policy was updated")
                .is_empty()
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

    /// 2026-09-15 review: JSON-style keys close their quote before the
    /// delimiter (`"api_key": "..."`), so the assignment detector missed
    /// them — exactly the shape a `.jsonl` credential file uses.
    #[test]
    fn redacts_json_style_assignment_values() {
        let json = r#"{"api_key": "supersecretvalue12345", "note": "plain"}"#;
        let (redacted, kinds) = redact_credential_content(json);
        assert!(
            kinds.contains(&"credential_assignment"),
            "JSON assignment must be detected: {kinds:?}"
        );
        assert!(
            !redacted.contains("supersecretvalue12345"),
            "JSON assignment value must be scrubbed: {redacted}"
        );
        assert!(
            redacted.contains("plain"),
            "non-secret values stay: {redacted}"
        );
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

    #[test]
    fn assignment_marker_does_not_retrigger_detection() {
        // Regression: detection lowercases before scanning, so the marker
        // guard must compare case-insensitively or apply-pass runs are never
        // idempotent (found by the wm redact-content store pass, 2026-09-11).
        let text = "db password=correct-horse-battery-staple";
        let (once, _) = redact_credential_content(text);
        assert!(
            credential_shaped_content(&once).is_empty(),
            "redacted assignment must read clean: {once}"
        );
        let (twice, kinds) = redact_credential_content(&once);
        assert_eq!(once, twice);
        assert!(kinds.is_empty());
    }

    #[test]
    fn short_jwt_fragments_are_redacted_too() {
        // Regression: detection counts any two `eyJ` occurrences, but the
        // redactor used to demand an 8-char run — short fragments stayed
        // detectable and the store pass kept re-finding them (2026-09-11).
        let text = "tokens eyJab and eyJcd appeared in logs";
        let (once, kinds) = redact_credential_content(text);
        assert!(kinds.contains(&"jwt"));
        assert!(
            credential_shaped_content(&once).is_empty(),
            "short fragments must read clean after redaction: {once}"
        );
        let (twice, _) = redact_credential_content(&once);
        assert_eq!(once, twice);
    }

    #[test]
    fn pem_fragments_are_redacted_too() {
        // Regression: a truncated/example PEM with no END block fires
        // detection but has no complete span; the marker strings themselves
        // must be neutralized so the store pass is idempotent (2026-09-11).
        let text = "docs explain -----BEGIN PRIVATE KEY----- when truncated";
        let (once, kinds) = redact_credential_content(text);
        assert!(kinds.contains(&"private_key_pem"));
        assert!(
            credential_shaped_content(&once).is_empty(),
            "PEM fragments must read clean after redaction: {once}"
        );
        let (twice, _) = redact_credential_content(&once);
        assert_eq!(once, twice);
    }

    /// 2026-09-21 reviewer P0: `TOKEN=...` survived `--redact` because
    /// `ASSIGNMENT_KEYS` omitted `token`, and connection strings survived
    /// because only keyed assignments were scanned.
    #[test]
    fn reviewer_fixtures_are_detected_and_redacted() {
        let token = "TOKEN=generic_token_value_0123456789abcdef";
        assert!(
            credential_shaped_content(token).contains(&"credential_assignment"),
            "plain token assignments must fire"
        );
        let (red, kinds) = redact_credential_content(token);
        assert!(kinds.contains(&"credential_assignment"));
        assert!(!red.contains("generic_token_value_0123456789abcdef"));
        assert!(
            credential_shaped_content(&red).is_empty(),
            "redacted token must read clean: {red}"
        );

        let uri = "DATABASE_URL=postgres://alice:fakepassword123456@db.example.com/prod";
        assert!(
            credential_shaped_content(uri).contains(&"credential_uri"),
            "URI userinfo must be detected independently of the key name"
        );
        let (red, kinds) = redact_credential_content(uri);
        assert!(kinds.contains(&"credential_uri"));
        assert!(!red.contains("fakepassword123456"), "password must be gone");
        assert!(
            !red.contains("alice"),
            "userinfo over-redaction is deliberate"
        );
        assert!(red.contains("db.example.com"), "host stays: {red}");
        assert!(
            credential_shaped_content(&red).is_empty(),
            "redacted URI must read clean: {red}"
        );
        let (twice, _) = redact_credential_content(&red);
        assert_eq!(red, twice, "URI redaction must be idempotent");

        // Empty user, non-empty password (`redis://:pass@host`).
        let redis = "REDIS_URL=redis://:hunter2hunter2@cache.internal:6379/0";
        let (red, kinds) = redact_credential_content(redis);
        assert!(kinds.contains(&"credential_uri"));
        assert!(!red.contains("hunter2hunter2"));
        assert!(credential_shaped_content(&red).is_empty());

        // JSON form, mixed case, quotes, and surrounding whitespace.
        let json = r#"{"Database_Url": "Postgres://Alice:Passw0rd123456@Db.Example.com/prod"}"#;
        let (red, kinds) = redact_credential_content(json);
        assert!(
            kinds.contains(&"credential_uri"),
            "JSON URI must fire: {kinds:?}"
        );
        assert!(!red.contains("Passw0rd123456"));
        assert!(credential_shaped_content(&red).is_empty());

        // Compound token names are covered by the `token` key: the delimiter
        // immediately follows the substring.
        for text in [
            "BOT_TOKEN=0123456789abcdef",
            "SESSION_TOKEN: 0123456789abcdef",
            "bearer_token=0123456789abcdef",
            "PASSPHRASE=correct-horse-battery-staple",
        ] {
            assert!(
                credential_shaped_content(text).contains(&"credential_assignment"),
                "{text}"
            );
        }
    }

    #[test]
    fn uri_lookalikes_stay_clean() {
        for text in [
            "see https://example.com/path for details",
            "ssh://git@github.com:22/repo",
            "connect to http://127.0.0.1:8080/status",
            "https://user@example.com/profile",
            "the scheme: separator is not a URL",
            "note:// just a label",
        ] {
            assert!(
                credential_shaped_content(text).is_empty(),
                "lookalike must stay clean: {text}"
            );
        }
    }

    /// Regression (2026-09-23 fleet report): a multibyte character directly
    /// before the scheme separator made the backward scheme scan slice at
    /// `char_start + 1`, panicking mid-character during `wm ingest` on Codex
    /// session logs ("start byte index ... is not a char boundary").
    #[test]
    fn uri_scan_is_char_boundary_safe_next_to_multibyte_text() {
        // '†' is 3 bytes; the old code produced a mid-char slice here.
        let text = "†††https://alice:fakepassword123456@db.example.com/prod";
        assert_eq!(
            credential_shaped_content(text),
            vec!["credential_uri".to_string()],
            "multibyte neighbors must not break URI detection"
        );
        let (redacted, _) = redact_credential_content(text);
        assert!(redacted.contains("[REDACTED:"), "{redacted}");
        assert!(!redacted.contains("fakepassword123456"), "{redacted}");

        // And a long multibyte run before a lookalike stays clean, no panic.
        let lookalike = "†".repeat(64) + "https://example.com/path";
        assert!(credential_shaped_content(&lookalike).is_empty());
    }
}
