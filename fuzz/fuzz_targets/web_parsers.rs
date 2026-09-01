//! Fuzz target: web parsers — feed arbitrary bytes to the dependency-free
//! HTML/URL parsing pipeline used by web.fetch / web.search.
//!
//! Invariants:
//! - `strip_html` must never panic and must never emit tags or entities
//! - `bing_decode` / `ddg_target` must never panic and decoded targets must
//!   be valid UTF-8
//! - `resolve_url` must never panic and must always produce an absolute
//!   http(s) URL
//! - `percent_encode_query` must never panic and must round-trip through
//!   a percent-decode
//! - `parse_bing_results` must never panic and must be bounded by
//!   `num_results`

#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_tools::expansion::web::{
    bing_decode, ddg_target, parse_bing_results, percent_encode_query, resolve_url, strip_html,
};

fuzz_target!(|data: &[u8]| {
    let text = String::from_utf8_lossy(data);

    // strip_html: no panics, no tag leaks. Every '<' in the output must
    // come from a '<'-producing entity in the input (`&lt;`, `&#60;`,
    // `&#x3c;` in any case) — raw markup is stripped, never passed through.
    let stripped = strip_html(&text);
    let input_lts = count_lt_entities(&text);
    let output_lts = stripped.matches('<').count();
    assert!(
        output_lts <= input_lts,
        "strip_html leaked {output_lts} '<' from {input_lts} entities: {stripped}"
    );

    // bing_decode: never panics; if it decodes, it is valid UTF-8 (by
    // construction) and non-empty
    if let Some(target) = bing_decode(&text) {
        assert!(!target.is_empty(), "bing_decode returned an empty target");
        assert!(
            target.starts_with("http://") || target.starts_with("https://"),
            "bing_decode returned a non-http target: {target}"
        );
    }

    // ddg_target: never panics
    let _ = ddg_target(&text);

    // resolve_url: never panics; always produces an absolute http(s) URL
    let resolved = resolve_url("https://example.com/a/b", &text);
    assert!(
        resolved.starts_with("http://") || resolved.starts_with("https://"),
        "resolve_url returned a non-absolute URL: {resolved}"
    );

    // percent_encode_query: never panics; encode+decode round-trips
    let encoded = percent_encode_query(&text);
    let decoded = percent_decode(&encoded);
    assert_eq!(
        decoded, text,
        "percent round-trip mismatch: {text:?} != {decoded:?}"
    );

    // parse_bing_results: never panics; bounded by num_results
    let results = parse_bing_results(&text, 3);
    assert!(results.len() <= 3, "parse_bing_results exceeded the bound");
    for result in results {
        assert!(result.url.is_empty() || result.url.starts_with("http"),
            "unexpected result URL: {}", result.url);
    }
});

/// Count `<`-producing entities (`&lt;`, `&#60;`, `&#x3c;`, any case) in
/// the input — the maximum number of `<` chars that may legitimately
/// appear in stripped output.
fn count_lt_entities(s: &str) -> usize {
    let lower = s.to_ascii_lowercase();
    ["&lt;", "&#60;", "&#x3c;"]
        .iter()
        .map(|e| lower.matches(e).count())
        .sum()
}

/// Percent-decode a string produced by [`percent_encode_query`] (query
/// style: `+` decodes back to a space).
fn percent_decode(s: &str) -> String {    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'+' {
            out.push(b' ');
            i += 1;
        } else if bytes[i] == b'%' && i + 2 < bytes.len() {
            match u8::from_str_radix(&s[i + 1..i + 3], 16) {
                Ok(b) => {
                    out.push(b);
                    i += 3;
                }
                Err(_) => {
                    out.push(bytes[i]);
                    i += 1;
                }
            }
        } else {
            out.push(bytes[i]);
            i += 1;
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}
