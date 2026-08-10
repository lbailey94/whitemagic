//! Web research tools — `web.fetch`, `web.search`, `web.search_and_read`,
//! `web.deep_fetch`.
//!
//! Port of the v26 `web_research` handlers (web_fetch / web_search /
//! web_search_and_read / deep_fetch) onto the v5 substrate:
//!
//! - `web.fetch` — fetch a URL, return clean text (no browser needed)
//! - `web.deep_fetch` — full-content retrieval (up to 200K chars)
//! - `web.search` — DuckDuckGo HTML search, no API key required
//! - `web.search_and_read` — search + fetch top results in one call
//!
//! Safety (Gana::Chariot, Resource::Network):
//! - Every URL (including each redirect hop) passes `is_url_safe` — SSRF
//!   defense-in-depth on top of the MCP boundary check
//! - Response bodies are bounded (`max_chars`), timeouts are bounded
//! - No HTML parser dependency: a compact tag/entity stripper is used

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use std::time::{Duration, Instant};
use wm_core::security::is_url_safe;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};

const USER_AGENT: &str = "WhiteMagic/5.6 (local research agent)";
const MAX_REDIRECTS: u32 = 5;

/// Result of a bounded fetch.
struct Fetched {
    url: String,
    title: String,
    /// Plain-text content (tags stripped, entities decoded).
    content: String,
    /// Raw body bytes (UTF-8 lossy) — used by search parsers.
    raw: String,
    status_code: u16,
    duration_ms: f64,
    pages: u32,
}

/// Validate a URL for SSRF safety.
fn safe_url(url: &str) -> Result<String, wm_core::CoreError> {
    if !is_url_safe(url) {
        return Err(wm_core::CoreError::InvalidArgs(format!(
            "unsafe URL (SSRF guard): {url}"
        )));
    }
    Ok(url.to_string())
}

/// GET with manual redirect following — every hop re-validated for SSRF,
/// body bounded, per-hop timeout.
fn fetch_bounded(
    start_url: &str,
    max_chars: usize,
    timeout: Duration,
) -> Result<Fetched, wm_core::CoreError> {
    let started = Instant::now();
    let mut current = start_url.to_string();
    let mut pages = 1u32;

    for _hop in 0..=MAX_REDIRECTS {
        let agent = ureq::Agent::config_builder()
            .timeout_global(Some(timeout))
            .build()
            .new_agent();
        let response = agent
            .get(&current)
            .header("User-Agent", USER_AGENT)
            .call()
            .map_err(|e| wm_core::CoreError::Tool(format!("fetch {current}: {e}")))?;

        let status = response.status().as_u16();
        if (300..400).contains(&status) {
            let location = response
                .headers()
                .get("location")
                .and_then(|v| v.to_str().ok())
                .ok_or_else(|| {
                    wm_core::CoreError::Tool(format!(
                        "redirect {status} without Location at {current}"
                    ))
                })?
                .to_string();
            let next = resolve_url(&current, &location);
            safe_url(&next)?;
            current = next;
            pages += 1;
            continue;
        }
        if !(200..300).contains(&status) {
            return Err(wm_core::CoreError::Tool(format!(
                "HTTP {status} from {current}"
            )));
        }

        // Bounded read: Read::take truncates silently (ureq's .limit() errors
        // on oversized bodies, which would surface as a fetch failure). Read a
        // generous raw window (head markup can dwarf the actual content) and
        // truncate the stripped text to max_chars below.
        let raw_budget = (max_chars as u64)
            .saturating_mul(8)
            .clamp(64_000, 1_000_000);
        let mut reader = response.into_body().into_reader();
        let mut bytes = Vec::new();
        std::io::Read::read_to_end(
            &mut std::io::Read::take(&mut reader, raw_budget),
            &mut bytes,
        )
        .map_err(|e| wm_core::CoreError::Tool(format!("read {current}: {e}")))?;
        let html = String::from_utf8_lossy(&bytes).into_owned();
        let title = extract_title(&html).unwrap_or_default();
        let content = strip_html(&html);
        let content: String = content.chars().take(max_chars).collect();
        return Ok(Fetched {
            url: current,
            title,
            content,
            raw: html,
            status_code: status,
            duration_ms: started.elapsed().as_secs_f64() * 1000.0,
            pages,
        });
    }

    Err(wm_core::CoreError::Tool(format!(
        "too many redirects ({MAX_REDIRECTS})"
    )))
}

/// Resolve a possibly-relative redirect target against the current URL
/// (RFC 3986 §5.3: relative references resolve against the current path's
/// directory).
fn resolve_url(base: &str, location: &str) -> String {
    if location.starts_with("http://") || location.starts_with("https://") {
        return location.to_string();
    }
    let (scheme, rest) = base
        .split_once("://")
        .map_or(("https", base), |(s, r)| (s, r));
    if location.starts_with("//") {
        return format!("{scheme}:{location}");
    }
    let slash = rest.find('/').unwrap_or(rest.len());
    let (host, path) = rest.split_at(slash);
    if location.starts_with('/') {
        return format!("{scheme}://{host}{location}");
    }
    // relative: resolve against the directory of the current path
    let dir: String = if path.is_empty() {
        "/".to_string()
    } else {
        format!("{}/", path.rsplit_once('/').map_or("/", |(d, _)| d))
    };
    format!("{scheme}://{host}{dir}{location}")
}

/// Extract the first `<title>…</title>`.
fn extract_title(html: &str) -> Option<String> {
    let lower = html.to_ascii_lowercase();
    let start = lower.find("<title")?;
    let gt = lower[start..].find('>')? + start + 1;
    let end = lower[gt..].find("</title")? + gt;
    let raw = &html[gt.min(html.len())..end.min(html.len())];
    let title = strip_html(raw);
    let title = title.trim();
    if title.is_empty() {
        None
    } else {
        Some(title.to_string())
    }
}

/// Strip HTML to plain text: drop script/style content, tags, and decode
/// common entities. Compact and dependency-free.
fn strip_html(html: &str) -> String {
    let mut out = String::with_capacity(html.len() / 2);
    let mut in_script = false;
    let mut chars = html.chars();
    while let Some(c) = chars.next() {
        match c {
            '<' => {
                let mut tag = String::new();
                for pc in chars.by_ref() {
                    tag.push(pc);
                    if pc == '>' {
                        break;
                    }
                }
                let lower = tag.to_ascii_lowercase();
                let trimmed = lower.trim_matches(['<', '>', '/']);
                let name = trimmed.split_whitespace().next().unwrap_or("");
                if name == "script" || name == "style" {
                    // The leading '<' was consumed by the outer match, so a
                    // leading '/' marks the closing tag.
                    in_script = !lower.starts_with('/');
                } else if !in_script
                    && !lower.starts_with("</")
                    && matches!(
                        name,
                        "p" | "br" | "div" | "li" | "h1" | "h2" | "h3" | "h4" | "tr"
                    )
                    && !out.ends_with('\n')
                {
                    out.push('\n');
                }
            }
            '&' => {
                // decode entity
                let mut entity = String::new();
                for pc in chars.by_ref() {
                    entity.push(pc);
                    if pc == ';' || entity.len() > 12 {
                        break;
                    }
                }
                out.push_str(&decode_entity(&entity));
            }
            c if in_script => {} // inside <script>/<style>: drop content
            c => out.push(c),
        }
    }
    // Collapse whitespace runs to single spaces (keep newlines).
    let mut result = String::with_capacity(out.len());
    let mut pending_newline = false;
    let mut pending_space = false;
    for c in out.chars() {
        if c == '\n' {
            pending_newline = true;
            pending_space = false;
        } else if c.is_whitespace() {
            pending_space = true;
        } else {
            if pending_newline {
                if !result.ends_with('\n') && !result.is_empty() {
                    result.push('\n');
                }
                pending_newline = false;
            } else if pending_space {
                if !result.ends_with(' ') && !result.ends_with('\n') && !result.is_empty() {
                    result.push(' ');
                }
                pending_space = false;
            }
            result.push(c);
        }
    }
    result.trim().to_string()
}

/// Decode a single HTML entity (`amp;`, `#123;`, …).
fn decode_entity(entity: &str) -> String {
    let e = entity.trim_end_matches(';');
    let out = match e {
        "amp" => "&",
        "lt" => "<",
        "gt" => ">",
        "quot" => "\"",
        "apos" | "#39" => "'",
        "nbsp" => " ",
        _ => {
            if let Some(num) = e.strip_prefix('#') {
                let code = num.parse::<u32>().ok().or_else(|| {
                    num.strip_prefix('x')
                        .and_then(|h| u32::from_str_radix(h, 16).ok())
                });
                if let Some(code) = code {
                    if let Some(ch) = char::from_u32(code) {
                        return ch.to_string();
                    }
                }
            }
            return format!("&{e};");
        }
    };
    out.to_string()
}

/// Extract the real target from a DuckDuckGo redirect href
/// (`//duckduckgo.com/l/?uddg=<url-encoded>`).
fn ddg_target(href: &str) -> Option<String> {
    let idx = href.find("uddg=")?;
    let encoded = &href[idx + 5..];
    let end = encoded.find('&').unwrap_or(encoded.len());
    let mut out = Vec::new();
    let bytes = &encoded.as_bytes()[..end];
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(b) = u8::from_str_radix(&encoded[i + 1..i + 3], 16) {
                out.push(b);
                i += 3;
                continue;
            }
        }
        out.push(bytes[i]);
        i += 1;
    }
    String::from_utf8(out).ok()
}

/// Decode a Bing click-tracking link (`https://www.bing.com/ck/a?...`).
///
/// The real target is carried in the `u=a1<base64url>` parameter. The href
/// arrives HTML-escaped (`&amp;`), so unescape first, then extract and
/// decode the base64url payload.
fn bing_decode(href: &str) -> Option<String> {
    let unescaped = href.replace("&amp;", "&");
    let idx = unescaped.find("u=a1")?;
    let rest = &unescaped[idx + 4..];
    let end = rest.find('&').unwrap_or(rest.len());
    let b64 = rest[..end].replace('-', "+").replace('_', "/");
    let mut bytes = Vec::with_capacity(b64.len() * 3 / 4);
    let table: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut acc = 0u32;
    let mut bits = 0u8;
    for c in b64.bytes().filter(|c| *c != b'=') {
        let v = table.iter().position(|t| *t == c)?;
        acc = (acc << 6) | v as u32;
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            bytes.push((acc >> bits) as u8);
            acc &= (1 << bits) - 1;
        }
    }
    String::from_utf8(bytes).ok()
}

/// Percent-encode a query for a search URL.
fn percent_encode_query(query: &str) -> String {
    query
        .chars()
        .flat_map(|c| match c {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' | '.' | '~' => vec![c],
            ' ' => vec!['+'],
            _ => {
                let mut bytes = [0u8; 4];
                let s = c.encode_utf8(&mut bytes);
                s.bytes()
                    .flat_map(|b| format!("%{b:02X}").chars().collect::<Vec<_>>())
                    .collect()
            }
        })
        .collect()
}

/// One parsed search result.
#[derive(Debug)]
struct SearchResult {
    url: String,
    title: String,
    snippet: String,
}

/// Search Bing's HTML results (no API key) and parse `li.b_algo` blocks.
///
/// Bing currently serves parseable HTML to plain HTTP clients where
/// DuckDuckGo serves a bot-detection challenge (HTTP 202). If the markup
/// changes such that no results parse, an empty result list is returned —
/// callers surface that gracefully.
fn web_search(
    query: &str,
    num_results: usize,
    timeout: Duration,
) -> Result<Vec<SearchResult>, wm_core::CoreError> {
    let url = format!(
        "https://www.bing.com/search?q={}&count={}",
        percent_encode_query(query),
        num_results
    );
    safe_url(&url)?;
    let fetched = fetch_bounded(&url, 300_000, timeout)?;
    if fetched.status_code == 202 {
        return Ok(Vec::new());
    }
    let html = fetched.raw;
    let lower = html.to_ascii_lowercase();

    let mut results: Vec<SearchResult> = Vec::new();
    let mut pos = 0usize;
    while results.len() < num_results {
        let block = lower[pos..].find("<li class=\"b_algo\"");
        let Some(block) = block else { break };
        let block = pos + block;
        let block_end = lower[block..]
            .find("</li>")
            .map_or(lower.len(), |e| block + e);
        let chunk = &html[block..block_end];
        let chunk_lower = &lower[block..block_end];

        // First non-javascript anchor href
        let mut anchor_at = 0usize;
        let mut href = None;
        while anchor_at < chunk.len() {
            let Some(rel) = chunk_lower[anchor_at..].find("<a ") else {
                break;
            };
            let a_start = anchor_at + rel;
            let Some(href_start) = chunk_lower[a_start..].find("href=\"") else {
                break;
            };
            let href_start = a_start + href_start + 6;
            let Some(href_end) = chunk_lower[href_start..].find('"') else {
                break;
            };
            let href_end = href_start + href_end;
            let candidate = &chunk[href_start..href_end];
            anchor_at = href_end + 1;
            if candidate.starts_with("javascript:") || candidate.starts_with('#') {
                continue;
            }
            href = Some(candidate.to_string());
            break;
        }
        let Some(href) = href else {
            pos = block + 7;
            continue;
        };

        // Title: text inside the <h2>…</h2> heading (the result title)
        let title = {
            let h2 = chunk_lower.find("<h2").unwrap_or(0);
            let gt = chunk_lower[h2..].find('>').map_or(0, |e| h2 + e + 1);
            let close = chunk_lower[gt..]
                .find("</a>")
                .map_or(chunk.len(), |e| gt + e);
            strip_html(&chunk[gt..close.min(chunk.len())])
        };

        // Snippet: first <p …>…</p> paragraph
        let snippet = {
            let p_start = chunk_lower.find("<p ");
            match p_start {
                Some(ps) => {
                    let gt = chunk_lower[ps..].find('>').map(|e| ps + e + 1);
                    match gt {
                        Some(gt) => {
                            let p_close = chunk_lower[gt..].find("</p>").map(|e| gt + e);
                            match p_close {
                                Some(pc) => strip_html(&chunk[gt..pc]),
                                None => String::new(),
                            }
                        }
                        None => String::new(),
                    }
                }
                None => String::new(),
            }
        };

        let target = if href.contains("/ck/a") {
            bing_decode(&href)
                .filter(|t| is_url_safe(t))
                .unwrap_or_default()
        } else if href.starts_with("http") && is_url_safe(&href) {
            href
        } else {
            ddg_target(&href)
                .filter(|t| is_url_safe(t))
                .unwrap_or_default()
        };

        if !target.is_empty() {
            results.push(SearchResult {
                url: target,
                title: title.trim().to_string(),
                snippet: snippet.trim().to_string(),
            });
        }
        pos = block + 7;
    }
    Ok(results)
}

/// Build the common response envelope.
fn fetch_response(fetched: &Fetched, truncated: bool) -> Value {
    json!({
        "status": "success",
        "url": fetched.url,
        "title": fetched.title,
        "content": fetched.content,
        "content_length": fetched.content.len(),
        "status_code": fetched.status_code,
        "duration_ms": fetched.duration_ms,
        "pages_fetched": fetched.pages,
        "truncated": truncated,
    })
}

// ── web.fetch ────────────────────────────────────────────────────────

/// `web.fetch` — fetch a URL and return clean text content.
pub struct WebFetchTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl WebFetchTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Network]),
        }
    }
}

impl Default for WebFetchTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for WebFetchTool {
    fn name(&self) -> &str {
        "web.fetch"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Fetch a URL and return clean text content (no browser needed). Args: url (required), max_chars (default 30000), timeout_secs (default 15)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let url = args
            .get("url")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("url is required".into()))?;
        let max_chars = args
            .get("max_chars")
            .and_then(Value::as_u64)
            .unwrap_or(30_000) as usize;
        let timeout = args
            .get("timeout_secs")
            .and_then(Value::as_f64)
            .unwrap_or(15.0);
        let url = safe_url(url)?;
        let fetched = tokio::task::spawn_blocking(move || {
            fetch_bounded(&url, max_chars, Duration::from_secs_f64(timeout))
        })
        .await
        .map_err(|e| wm_core::CoreError::Tool(format!("web.fetch task: {e}")))??;
        Ok(fetch_response(&fetched, fetched.content.len() >= max_chars))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── web.deep_fetch ───────────────────────────────────────────────────

/// `web.deep_fetch` — full-content retrieval (up to 200K chars).
pub struct WebDeepFetchTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl WebDeepFetchTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Network]),
        }
    }
}

impl Default for WebDeepFetchTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for WebDeepFetchTool {
    fn name(&self) -> &str {
        "web.deep_fetch"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Fetch a URL with full-content retrieval (up to 200K chars, no chunk skimming). Args: url (required), max_chars (default 200000), timeout_secs (default 30)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let url = args
            .get("url")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("url is required".into()))?;
        let max_chars = args
            .get("max_chars")
            .and_then(Value::as_u64)
            .unwrap_or(200_000) as usize;
        let timeout = args
            .get("timeout_secs")
            .and_then(Value::as_f64)
            .unwrap_or(30.0);
        let url = safe_url(url)?;
        let fetched = tokio::task::spawn_blocking(move || {
            fetch_bounded(&url, max_chars, Duration::from_secs_f64(timeout))
        })
        .await
        .map_err(|e| wm_core::CoreError::Tool(format!("web.deep_fetch task: {e}")))??;
        Ok(fetch_response(&fetched, fetched.content.len() >= max_chars))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── web.search ───────────────────────────────────────────────────────

/// `web.search` — DuckDuckGo web search (no API key needed).
pub struct WebSearchTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl WebSearchTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Network]),
        }
    }
}

impl Default for WebSearchTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for WebSearchTool {
    fn name(&self) -> &str {
        "web.search"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Search the web (Bing HTML, no API key needed). Args: query (required), num_results (default 8), timeout_secs (default 10)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query is required".into()))?;
        let num_results = args.get("num_results").and_then(Value::as_u64).unwrap_or(8) as usize;
        let timeout = args
            .get("timeout_secs")
            .and_then(Value::as_f64)
            .unwrap_or(10.0);
        let query = query.to_string();
        let query_for_task = query.clone();
        let results = tokio::task::spawn_blocking(move || {
            web_search(
                &query_for_task,
                num_results,
                Duration::from_secs_f64(timeout),
            )
        })
        .await
        .map_err(|e| wm_core::CoreError::Tool(format!("web.search task: {e}")))??;
        let results: Vec<Value> = results
            .into_iter()
            .map(|r| json!({"url": r.url, "title": r.title, "snippet": r.snippet}))
            .collect();
        Ok(json!({
            "status": "success",
            "query": query,
            "total_results": results.len(),
            "results": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── web.search_and_read ──────────────────────────────────────────────

/// `web.search_and_read` — search AND fetch content from top results.
pub struct WebSearchAndReadTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl WebSearchAndReadTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Network]),
        }
    }
}

impl Default for WebSearchAndReadTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for WebSearchAndReadTool {
    fn name(&self) -> &str {
        "web.search_and_read"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Search the web AND fetch content from top results in one call. Args: query (required), num_results (default 5), max_fetch (default 3), max_chars_per_page (default 15000)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query is required".into()))?;
        let num_results = args.get("num_results").and_then(Value::as_u64).unwrap_or(5) as usize;
        let max_fetch = args.get("max_fetch").and_then(Value::as_u64).unwrap_or(3) as usize;
        let max_chars = args
            .get("max_chars_per_page")
            .and_then(Value::as_u64)
            .unwrap_or(15_000) as usize;
        let timeout = args
            .get("timeout_secs")
            .and_then(Value::as_f64)
            .unwrap_or(15.0);
        let query = query.to_string();
        let query_for_task = query.clone();
        let results = tokio::task::spawn_blocking(move || {
            web_search(
                &query_for_task,
                num_results,
                Duration::from_secs_f64(timeout),
            )
        })
        .await
        .map_err(|e| wm_core::CoreError::Tool(format!("web.search_and_read task: {e}")))??;

        let mut entries: Vec<Value> = results
            .into_iter()
            .map(|r| json!({"url": r.url, "title": r.title, "snippet": r.snippet, "content": null}))
            .collect();

        let mut fetched_count = 0usize;
        for entry in &mut entries.iter_mut().take(max_fetch) {
            let url = entry
                .get("url")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_string();
            if url.is_empty() || !is_url_safe(&url) {
                continue;
            }
            let url_c = url.clone();
            let max_c = max_chars;
            let t = timeout;
            if let Ok(Ok(fetched)) = tokio::task::spawn_blocking(move || {
                fetch_bounded(&url_c, max_c, Duration::from_secs_f64(t))
            })
            .await
            {
                entry["content"] = json!(fetched.content);
                entry["content_length"] = json!(fetched.content.len());
                if entry["title"].as_str().unwrap_or_default().is_empty() {
                    entry["title"] = json!(fetched.title);
                }
                fetched_count += 1;
            }
        }

        Ok(json!({
            "status": "success",
            "query": query,
            "results": entries,
            "total_results": entries.len(),
            "fetched_count": fetched_count,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the web tools (4).
#[must_use]
pub fn register_web(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(WebFetchTool::new()))
        .register(Arc::new(WebDeepFetchTool::new()))
        .register(Arc::new(WebSearchTool::new()))
        .register(Arc::new(WebSearchAndReadTool::new()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn html_stripping_removes_tags_and_scripts() {
        let html = "<html><head><title>Test Page</title><script>var x=1;</script></head><body><h1>Hello</h1><p>World&nbsp;wide</p><div>One</div><div>Two</div></body></html>";
        let text = strip_html(html);
        assert!(text.contains("Hello"));
        assert!(text.contains("World wide"));
        assert!(text.contains("One"));
        assert!(!text.contains("var x"));
        assert!(!text.contains("<p>"));
    }

    #[test]
    fn html_stripping_decodes_entities() {
        assert_eq!(
            strip_html("&amp; &lt;tag&gt; &quot;q&quot; &#65; &#x42;"),
            "& <tag> \"q\" A B"
        );
        assert_eq!(strip_html("&unknown;"), "&unknown;");
    }

    #[test]
    fn title_extraction() {
        assert_eq!(
            extract_title("<html><title>  My Page  </title></html>"),
            Some("My Page".to_string())
        );
        assert!(extract_title("<html><body>no title</body></html>").is_none());
    }

    #[test]
    fn ddg_redirect_decodes_target() {
        let href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage%3Fa%3D1&rut=abc";
        assert_eq!(
            ddg_target(href),
            Some("https://example.com/page?a=1".to_string())
        );
    }

    #[test]
    fn bing_ck_a_decodes_target() {
        // u=a1 + base64url of "https://rust-lang.org/"
        let href = "https://www.bing.com/ck/a?!&amp;&amp;p=abc&amp;u=a1aHR0cHM6Ly9ydXN0LWxhbmcub3JnLw&amp;ntb=1";
        assert_eq!(
            bing_decode(href),
            Some("https://rust-lang.org/".to_string())
        );
        // UTF-8 payload (base64url alphabet, padding omitted)
        let href2 = "https://www.bing.com/ck/a?u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS8_YS1iX3M";
        assert_eq!(
            bing_decode(href2),
            Some("https://example.com/?a-b_s".to_string())
        );
        assert_eq!(bing_decode("https://www.bing.com/ck/a?p=1"), None);
    }

    #[test]
    fn resolve_url_handles_relative_and_protocol() {
        assert_eq!(
            resolve_url("https://example.com/a/b", "/c"),
            "https://example.com/c"
        );
        assert_eq!(
            resolve_url("https://example.com/a/b", "c.html"),
            "https://example.com/a/c.html"
        );
        assert_eq!(
            resolve_url("http://example.com/x", "//other.com/y"),
            "http://other.com/y"
        );
        assert_eq!(
            resolve_url("https://example.com/x", "https://other.com/y"),
            "https://other.com/y"
        );
    }

    #[test]
    fn ssrf_guard_rejects_private_and_non_http() {
        assert!(safe_url("http://169.254.169.254/latest/meta-data").is_err());
        assert!(safe_url("file:///etc/passwd").is_err());
        assert!(safe_url("https://example.com").is_ok());
    }

    #[test]
    fn tool_declarations() {
        assert_eq!(WebFetchTool::new().name(), "web.fetch");
        assert_eq!(WebSearchTool::new().name(), "web.search");
        assert_eq!(WebDeepFetchTool::new().name(), "web.deep_fetch");
        assert_eq!(WebSearchAndReadTool::new().name(), "web.search_and_read");
        let tools: Vec<Box<dyn Tool>> = vec![
            Box::new(WebFetchTool::new()),
            Box::new(WebSearchTool::new()),
            Box::new(WebDeepFetchTool::new()),
            Box::new(WebSearchAndReadTool::new()),
        ];
        for tool in tools {
            assert_eq!(tool.gana(), Gana::Chariot);
            assert!(tool.effects().writes.is_empty());
            assert!(!tool.effects().destructive);
            assert_eq!(tool.effects().reads.len(), 1);
            assert_eq!(tool.effects().reads[0], Resource::Network);
        }
    }

    #[tokio::test]
    async fn fetch_requires_url() {
        let tool = WebFetchTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn search_requires_query() {
        let tool = WebSearchTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_err());
    }
}
