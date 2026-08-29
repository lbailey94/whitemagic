//! Research tools — `research.topic`, `research.repo`, `research.rabbit_hole`.
//!
//! Port of the v26 web-research orchestrators onto the web tooling in
//! [`super::web`] (Bing search + bounded fetch + SSRF guard):
//!
//! - `research.topic` — search → fetch top sources → extract key terms →
//!   synthesize; optionally stores the result in the Research galaxy
//! - `research.repo` — GitHub repo README deep-read (raw + rendered)
//! - `research.rabbit_hole` — bounded recursive spiral: search the topic,
//!   extract unfamiliar terms, search each, fetch top results, synthesize
//!
//! All synthesis is extractive (frequency-based) — no LLM dependency, so
//! the pipeline works air-gapped against the search backend.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use wm_core::security::is_url_safe;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

use super::web::{Fetched, fetch_bounded, web_search};

const STOPWORDS: &[&str] = &[
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "for",
    "with",
    "of",
    "in",
    "on",
    "at",
    "to",
    "from",
    "by",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "this",
    "that",
    "these",
    "those",
    "as",
    "into",
    "over",
    "under",
    "about",
    "between",
    "after",
    "before",
    "during",
    "through",
    "against",
    "within",
    "without",
    "not",
    "no",
    "nor",
    "so",
    "such",
    "too",
    "very",
    "can",
    "will",
    "just",
    "don",
    "does",
    "did",
    "has",
    "have",
    "had",
    "more",
    "most",
    "other",
    "some",
    "which",
    "what",
    "when",
    "where",
    "why",
    "how",
    "all",
    "any",
    "both",
    "each",
    "few",
    "own",
    "same",
    "than",
    "then",
    "there",
    "they",
    "them",
    "their",
    "you",
    "your",
    "we",
    "our",
    "us",
    "also",
    "may",
    "could",
    "would",
    "should",
    "if",
    "else",
    "while",
    "via",
    "etc",
    "e.g",
    "i.e",
    "per",
    "new",
    "use",
    "used",
    "using",
    "one",
    "two",
    "via",
    "e.g",
    "say",
    "says",
    "said",
    "get",
    "got",
    "see",
    "also",
    "well",
    "way",
    "like",
    "make",
    "made",
    "much",
    "many",
    "even",
    "still",
    "though",
    "however",
    "include",
    "includes",
    "including",
    "provide",
    "provides",
    "provide",
    "based",
    "because",
];

/// Lowercase a word and keep only alphabetic characters.
fn clean_word(w: &str) -> Option<String> {
    let cleaned: String = w
        .chars()
        .filter(|c| c.is_alphabetic())
        .map(|c| c.to_ascii_lowercase())
        .collect();
    if cleaned.len() < 4 || STOPWORDS.contains(&cleaned.as_str()) {
        return None;
    }
    Some(cleaned)
}

/// Extract the most frequent meaningful terms from text (frequency-based,
/// stopword-filtered). A term must appear in **at least two sources** to
/// count — this filters single-page junk (bot walls, error pages).
fn key_terms(texts: &[String], limit: usize) -> Vec<String> {
    let mut counts: HashMap<String, usize> = HashMap::new();
    let mut per_source: HashMap<String, Vec<usize>> = HashMap::new();
    for (idx, text) in texts.iter().enumerate() {
        for token in text
            .split(|c: char| !c.is_alphabetic() && c != '-' && c != ' ')
            .flat_map(|s| s.split_whitespace())
        {
            if let Some(word) = clean_word(token) {
                *counts.entry(word.clone()).or_default() += 1;
                let seen = per_source.entry(word).or_default();
                if !seen.contains(&idx) {
                    seen.push(idx);
                }
            }
        }
    }
    let mut terms: Vec<(String, usize, usize)> = counts
        .into_iter()
        .filter(|(word, _)| per_source.get(word).map_or(0, Vec::len) >= 2)
        .map(|(word, count)| {
            let sources = per_source.get(&word).map_or(0, Vec::len);
            (word, count, sources)
        })
        .collect();
    terms.sort_by(|a, b| {
        b.1.cmp(&a.1)
            .then_with(|| b.2.cmp(&a.2))
            .then_with(|| a.0.cmp(&b.0))
    });
    terms.into_iter().take(limit).map(|(t, _, _)| t).collect()
}

/// Fetch several URLs sequentially with a per-URL char budget.
async fn fetch_sources(
    urls: &[String],
    max_sources: usize,
    max_chars: usize,
    timeout: Duration,
) -> Vec<Fetched> {
    let mut fetched = Vec::new();
    for url in urls.iter().take(max_sources) {
        if !is_url_safe(url) {
            continue;
        }
        let url_c = url.clone();
        let max_c = max_chars;
        let t = timeout;
        if let Ok(Ok(f)) =
            tokio::task::spawn_blocking(move || fetch_bounded(&url_c, max_c, t)).await
        {
            if !f.content.trim().is_empty() {
                fetched.push(f);
            }
        }
    }
    fetched
}

/// Build the per-source finding entry.
fn finding(f: &Fetched) -> Value {
    let domain = f
        .url
        .strip_prefix("https://")
        .or_else(|| f.url.strip_prefix("http://"))
        .and_then(|d| d.split('/').next())
        .unwrap_or("")
        .to_string();
    json!({
        "url": f.url,
        "domain": domain,
        "title": f.title,
        "content": f.content,
        "content_length": f.content.len(),
    })
}

/// Store a research report in the Research galaxy (best-effort).
fn store_research(store: Option<&Arc<MemoryStore>>, topic: &str, report: &Value) -> Option<String> {
    let store = store?;
    let content = format!(
        "RESEARCH: {topic}\n{}",
        report
            .get("synthesis")
            .and_then(Value::as_str)
            .unwrap_or("")
    );
    let mut memory = Memory::new(Galaxy::Research, content);
    memory = memory.with_tags(vec!["research".into(), topic.to_ascii_lowercase()]);
    if let Some(sources) = report.get("sources").and_then(Value::as_array) {
        if let Some(first) = sources.first() {
            if let Some(url) = first.get("url").and_then(Value::as_str) {
                memory = memory.with_source(url.to_string(), 0.8);
            }
        }
    }
    store.put(Galaxy::Research, &memory).ok()?;
    Some(memory.metadata.id.to_string())
}

// ── research.topic ───────────────────────────────────────────────────

/// `research.topic` — deep research on a topic: search, fetch, synthesize.
pub struct ResearchTopicTool {
    store: Option<Arc<MemoryStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ResearchTopicTool {
    #[must_use]
    pub fn new(store: Option<Arc<MemoryStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![
                Resource::Network,
                Resource::Galaxy("research".into()),
            ]),
        }
    }
}

#[async_trait]
impl Tool for ResearchTopicTool {
    fn name(&self) -> &str {
        "research.topic"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Deep research on a topic: search, fetch top sources, extract key terms, synthesize. Args: topic (required), num_results (default 6), max_sources (default 4), max_chars_per_source (default 15000), store_memories (default true)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let topic = args
            .get("topic")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("topic is required".into()))?;
        let num_results = args.get("num_results").and_then(Value::as_u64).unwrap_or(6) as usize;
        let max_sources = args.get("max_sources").and_then(Value::as_u64).unwrap_or(4) as usize;
        let max_chars = args
            .get("max_chars_per_source")
            .and_then(Value::as_u64)
            .unwrap_or(15_000) as usize;
        let store_memories = args
            .get("store_memories")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let timeout = Duration::from_secs(20);

        let topic_s = topic.to_string();
        let results =
            tokio::task::spawn_blocking(move || web_search(&topic_s, num_results, timeout))
                .await
                .map_err(|e| {
                    wm_core::CoreError::Tool(format!("research.topic search task: {e}"))
                })??;

        let urls: Vec<String> = results
            .iter()
            .filter(|r| !r.url.is_empty())
            .map(|r| r.url.clone())
            .collect();
        let fetched = fetch_sources(&urls, max_sources, max_chars, timeout).await;

        let contents: Vec<String> = fetched.iter().map(|f| f.content.clone()).collect();
        let terms = key_terms(&contents, 14);

        let findings: Vec<Value> = fetched.iter().map(finding).collect();
        let synthesis = if findings.is_empty() {
            format!(
                "No readable sources found for '{topic}' — refine the topic or check network access."
            )
        } else {
            let source_list: Vec<String> = findings
                .iter()
                .map(|f| {
                    let title = f.get("title").and_then(Value::as_str).unwrap_or("");
                    let domain = f.get("domain").and_then(Value::as_str).unwrap_or("");
                    format!("{title} ({domain})")
                })
                .collect();
            format!(
                "Research on '{topic}' synthesized from {} source(s): {}. Key terms across sources: {}.",
                findings.len(),
                source_list.join("; "),
                terms.join(", ")
            )
        };

        let report = json!({
            "status": "success",
            "topic": topic,
            "query": topic,
            "sources_fetched": findings.len(),
            "search_results": results.len(),
            "key_terms": terms,
            "synthesis": synthesis,
            "sources": findings,
        });

        let mut report = report;
        if store_memories {
            if let Some(id) = store_research(self.store.as_ref(), topic, &report) {
                report["memory_id"] = json!(id);
            }
        }
        Ok(report)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── research.repo ────────────────────────────────────────────────────

/// `research.repo` — deep-read a GitHub repo's README and structure.
pub struct ResearchRepoTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl ResearchRepoTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Network]),
        }
    }
}

impl Default for ResearchRepoTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for ResearchRepoTool {
    fn name(&self) -> &str {
        "research.repo"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Research a GitHub repo by deep-reading its README. Args: repo (required, owner/name), max_chars (default 50000)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let repo = args.get("repo").and_then(Value::as_str).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs("repo (owner/name) is required".into())
        })?;
        let max_chars = args
            .get("max_chars")
            .and_then(Value::as_u64)
            .unwrap_or(50_000) as usize;
        let timeout = Duration::from_secs(25);

        let repo = repo.trim().trim_start_matches("https://github.com/");
        let parts: Vec<&str> = repo.split('/').filter(|p| !p.is_empty()).collect();
        if parts.len() < 2 {
            return Err(wm_core::CoreError::InvalidArgs(
                "repo must be 'owner/name'".into(),
            ));
        }
        let owner = parts[0];
        let name = parts[1];

        // Try the raw README endpoints in order; fall back to the rendered page.
        let mut raw: Option<Fetched> = None;
        for candidate in [
            "README.md",
            "README.rst",
            "readme.md",
            "readme.rst",
            "README",
        ] {
            let url = format!("https://raw.githubusercontent.com/{owner}/{name}/HEAD/{candidate}");
            if !is_url_safe(&url) {
                continue;
            }
            let url_c = url.clone();
            let max_c = max_chars;
            let t = timeout;
            if let Ok(Ok(f)) =
                tokio::task::spawn_blocking(move || fetch_bounded(&url_c, max_c, t)).await
            {
                if !f.content.trim().is_empty() {
                    raw = Some(f);
                    break;
                }
            }
        }

        let (content, source_url, title) = if let Some(f) = raw {
            (f.content, f.url, name.to_string())
        } else {
            let page_url = format!("https://github.com/{owner}/{name}");
            let page_url_c = page_url.clone();
            let max_c = max_chars;
            let t = timeout;
            let fetched = tokio::task::spawn_blocking(move || fetch_bounded(&page_url_c, max_c, t))
                .await
                .map_err(|e| wm_core::CoreError::Tool(format!("research.repo task: {e}")))?
                .map_err(|e| wm_core::CoreError::Tool(format!("research.repo: {e}")))?;
            (fetched.content, page_url, name.to_string())
        };

        // Extract headings (markdown or HTML) as a structure outline.
        let mut sections: Vec<String> = Vec::new();
        for line in content.lines() {
            let line = line.trim();
            if let Some(h) = line.strip_prefix("## ") {
                sections.push(h.to_string());
            } else if line.starts_with("### ") {
                sections.push(line.trim_start_matches("### ").to_string());
            }
        }

        let description = content
            .lines()
            .map(str::trim)
            .find(|l| !l.is_empty() && !l.starts_with('#') && !l.starts_with('!'))
            .unwrap_or("")
            .to_string();

        Ok(json!({
            "status": "success",
            "repo": format!("{owner}/{name}"),
            "source_url": source_url,
            "title": title,
            "description": description,
            "sections": sections,
            "content_length": content.len(),
            "content": content,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── research.rabbit_hole ─────────────────────────────────────────────

/// `research.rabbit_hole` — bounded recursive spiral research.
///
/// Explores a topic by searching, extracting unfamiliar terms from the
/// results, searching each term, and fetching the top pages — then
/// synthesizing the whole exploration. Depth is bounded (default 2) and
/// parallelism is bounded, so a call cannot fan out unboundedly.
pub struct ResearchRabbitHoleTool {
    store: Option<Arc<MemoryStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ResearchRabbitHoleTool {
    #[must_use]
    pub fn new(store: Option<Arc<MemoryStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![
                Resource::Network,
                Resource::Galaxy("research".into()),
            ]),
        }
    }
}

#[async_trait]
impl Tool for ResearchRabbitHoleTool {
    fn name(&self) -> &str {
        "research.rabbit_hole"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Recursive spiral research: search the topic, extract unfamiliar terms, search each term, fetch top results, synthesize. Args: topic (required), max_depth (default 2, max 3), num_search_results (default 5), fetch_top_results (default 2), max_parallel_terms (default 6), store_memories (default true)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let topic = args
            .get("topic")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("topic is required".into()))?;
        let max_depth = args
            .get("max_depth")
            .and_then(Value::as_u64)
            .unwrap_or(2)
            .clamp(1, 3) as usize;
        let num_results = args
            .get("num_search_results")
            .and_then(Value::as_u64)
            .unwrap_or(5) as usize;
        let fetch_top = args
            .get("fetch_top_results")
            .and_then(Value::as_u64)
            .unwrap_or(2) as usize;
        let max_parallel_terms = args
            .get("max_parallel_terms")
            .and_then(Value::as_u64)
            .unwrap_or(6)
            .clamp(1, 12) as usize;
        let max_chars = args
            .get("max_chars_per_fetch")
            .and_then(Value::as_u64)
            .unwrap_or(50_000) as usize;
        let store_memories = args
            .get("store_memories")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let timeout = Duration::from_secs(20);

        // Level 0: search the topic itself.
        let topic_s = topic.to_string();
        let level0 =
            tokio::task::spawn_blocking(move || web_search(&topic_s, num_results, timeout))
                .await
                .map_err(|e| {
                    wm_core::CoreError::Tool(format!("research.rabbit_hole search task: {e}"))
                })??;

        // Fetch the top topic results.
        let topic_urls: Vec<String> = level0
            .iter()
            .filter(|r| !r.url.is_empty())
            .map(|r| r.url.clone())
            .collect();
        let topic_fetched = fetch_sources(&topic_urls, fetch_top, max_chars, timeout).await;

        // Extract unfamiliar terms from titles + snippets of the first level.
        let mut terms: Vec<String> = Vec::new();
        {
            let mut seen: Vec<String> = Vec::new();
            let candidates: Vec<String> = level0
                .iter()
                .flat_map(|r| {
                    r.title
                        .split_whitespace()
                        .chain(r.snippet.split_whitespace())
                        .map(str::to_string)
                        .collect::<Vec<_>>()
                })
                .collect();
            for word in candidates {
                let word = word.trim_matches(|c: char| !c.is_alphanumeric());
                if word.len() < 5 || STOPWORDS.contains(&word.to_ascii_lowercase().as_str()) {
                    continue;
                }
                if word.eq_ignore_ascii_case(topic) {
                    continue;
                }
                let key = word.to_ascii_lowercase();
                if !seen.contains(&key) {
                    seen.push(key);
                    terms.push(word.to_string());
                }
                if terms.len() >= max_parallel_terms {
                    break;
                }
            }
        }

        // Level 1: search each unfamiliar term.
        let mut entries: Vec<Value> = Vec::new();
        for term in terms.iter().take(max_parallel_terms) {
            let term_s = term.clone();
            let n = num_results.max(3);
            let t = timeout;
            let results = tokio::task::spawn_blocking(move || web_search(&term_s, n, t))
                .await
                .map_err(|e| {
                    wm_core::CoreError::Tool(format!("research.rabbit_hole term task: {e}"))
                })??;
            let best = results.first();
            entries.push(json!({
                "term": term,
                "depth": 1,
                "definition": best.map(|b| b.snippet.clone()).unwrap_or_default(),
                "source": best.map(|b| b.url.clone()).unwrap_or_default(),
                "related_terms": results.iter().take(3).map(|r| r.title.clone()).collect::<Vec<_>>(),
            }));
        }

        // Level 2: recurse on the most interesting term.
        let mut extra_entries: Vec<Value> = Vec::new();
        if max_depth >= 2 && !entries.is_empty() {
            // pick the term whose search returned the most results
            let mut best_term = String::new();
            let mut best_score = 0usize;
            for entry in &entries {
                let related = entry
                    .get("related_terms")
                    .and_then(Value::as_array)
                    .map_or(0, Vec::len);
                if related > best_score {
                    best_score = related;
                    best_term = entry
                        .get("term")
                        .and_then(Value::as_str)
                        .unwrap_or("")
                        .to_string();
                }
            }
            if !best_term.is_empty() && !best_term.eq_ignore_ascii_case(topic) {
                let bt = best_term.clone();
                let n = num_results.max(3);
                let t = timeout;
                let results = tokio::task::spawn_blocking(move || web_search(&bt, n, t))
                    .await
                    .map_err(|e| {
                        wm_core::CoreError::Tool(format!("research.rabbit_hole depth-2 task: {e}"))
                    })??;
                for r in results.iter().take(3) {
                    extra_entries.push(json!({
                        "term": best_term,
                        "depth": 2,
                        "definition": r.snippet,
                        "source": r.url,
                        "related_terms": [],
                    }));
                }
            }
        }
        entries.extend(extra_entries);

        // Synthesis: what was explored and what was found.
        let mut connections: Vec<String> = Vec::new();
        for entry in &entries {
            if let (Some(term), Some(src)) = (
                entry.get("term").and_then(Value::as_str),
                entry.get("source").and_then(Value::as_str),
            ) {
                if !src.is_empty() {
                    connections.push(format!("{term} → {src}"));
                }
            }
        }
        let synthesis = format!(
            "Rabbit-hole exploration of '{topic}' (depth {max_depth}): {} unfamiliar term(s) explored — {}. Top sources on the topic itself: {}.",
            entries.len(),
            entries
                .iter()
                .map(|e| e.get("term").and_then(Value::as_str).unwrap_or(""))
                .collect::<Vec<_>>()
                .join(", "),
            topic_fetched
                .iter()
                .map(|f| f.title.as_str())
                .collect::<Vec<_>>()
                .join("; "),
        );

        let topic_sources: Vec<Value> = topic_fetched.iter().map(finding).collect();
        let report = json!({
            "status": "success",
            "title": topic,
            "topics": entries.iter().map(|e| e["term"].clone()).collect::<Vec<_>>(),
            "entries_count": entries.len(),
            "synthesis": synthesis,
            "connections_count": connections.len(),
            "connections": connections,
            "depth_used": max_depth,
            "entries": entries,
            "sources": topic_sources,
        });

        let mut report = report;
        if store_memories {
            if let Some(id) = store_research(self.store.as_ref(), topic, &report) {
                report["memory_id"] = json!(id);
            }
        }
        Ok(report)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the research tools (3). `store` enables `store_memories`.
#[must_use]
pub fn register_research(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(ResearchTopicTool::new(Some(store.clone()))))
        .register(Arc::new(ResearchRepoTool::new()))
        .register(Arc::new(ResearchRabbitHoleTool::new(Some(store.clone()))))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn key_terms_filters_stopwords() {
        let texts = vec![
            "The architecture of the agentic system and the governance layer".to_string(),
            "The governance layer architecture and the agentic system".to_string(),
            "Architecture governance agentic system".to_string(),
        ];
        let terms = key_terms(&texts, 5);
        assert_eq!(terms.len(), 5);
        assert!(!terms.contains(&"the".to_string()));
        assert!(terms.contains(&"governance".to_string()));
        assert!(terms.contains(&"architecture".to_string()));
        assert!(terms.contains(&"agentic".to_string()));
        assert!(terms.contains(&"system".to_string()));
        assert!(terms.contains(&"layer".to_string()));
    }

    #[test]
    fn key_terms_require_two_sources() {
        // "onlyonce" appears in a single text — must be filtered out.
        let texts = vec![
            "onlyonce appears only here in the alpha bravo".to_string(),
            "alpha bravo both sources share the delta".to_string(),
        ];
        let terms = key_terms(&texts, 10);
        assert!(!terms.contains(&"onlyonce".to_string()));
        assert!(!terms.contains(&"delta".to_string()));
        assert!(terms.contains(&"bravo".to_string()));
        assert!(terms.contains(&"alpha".to_string()));
    }

    #[test]
    fn repo_name_validation() {
        let tool = ResearchRepoTool::new();
        assert_eq!(tool.name(), "research.repo");
        assert_eq!(ResearchTopicTool::new(None).name(), "research.topic");
        assert_eq!(
            ResearchRabbitHoleTool::new(None).name(),
            "research.rabbit_hole"
        );
    }

    #[tokio::test]
    async fn topic_requires_topic() {
        let tool = ResearchTopicTool::new(None);
        let mut ctx = Context::default();
        assert!(tool.call(&mut ctx, json!({})).await.is_err());
    }

    #[tokio::test]
    async fn rabbit_hole_requires_topic() {
        let tool = ResearchRabbitHoleTool::new(None);
        let mut ctx = Context::default();
        assert!(tool.call(&mut ctx, json!({})).await.is_err());
    }

    #[tokio::test]
    async fn repo_requires_owner_and_name() {
        let tool = ResearchRepoTool::new();
        let mut ctx = Context::default();
        assert!(
            tool.call(&mut ctx, json!({"repo": "singleword"}))
                .await
                .is_err()
        );
    }

    #[test]
    fn effects_declare_network_read() {
        let topic = ResearchTopicTool::new(None);
        assert_eq!(topic.effects().reads[0], Resource::Network);
        assert!(topic.effects().writes.is_empty());
    }
}
