//! Code structure graph — `code.graph`, `code.query`, `code.affected_by`,
//! `fragment.search`.
//!
//! Port of the v26 `CodeStructureGraph` surface: scan a project, extract
//! symbols (functions, classes, methods, imports) and edges (calls,
//! imports, inheritance), then answer structural questions:
//!
//! - `code.graph` — build (or refresh) the graph for a project root
//! - `code.query` — natural-language queries: "what calls X", "what does X
//!   call", "path from A to B", "explain X", "god nodes", "search X"
//! - `code.affected_by` — everything transitively affected by changing a
//!   symbol (reverse call-graph BFS)
//! - `fragment.search` — locate the file/line fragments mentioning a query
//!
//! Extraction is regex-based per language (no parser dependency), bounded
//! by file count and file size, and the graph is shared across calls so a
//! single `code.graph` build serves many queries.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use std::sync::Mutex;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};

/// Maximum files scanned per build.
const DEFAULT_MAX_FILES: usize = 50_000;
/// Maximum size of a single source file read.
const MAX_FILE_BYTES: u64 = 1_000_000;
/// Directories always skipped.
const SKIP_DIRS: &[&str] = &[
    "target",
    "node_modules",
    ".git",
    "build",
    "dist",
    "vendor",
    ".venv",
    "__pycache__",
    "coverage",
];

/// A symbol in the code graph.
#[derive(Debug, Clone)]
pub struct CodeNode {
    /// Unique node id: `file:name:type`.
    pub id: String,
    /// Symbol name.
    pub name: String,
    /// function / class / method / import / module / struct / enum / const.
    pub node_type: String,
    /// Source file (relative to project root).
    pub file: String,
    /// 1-based line where the symbol appears.
    pub line: usize,
    /// Language inferred from the file extension.
    pub language: String,
}

/// A directed relationship between two nodes.
#[derive(Debug, Clone)]
pub struct CodeEdge {
    pub source_id: String,
    pub target_id: String,
    /// calls / imports / inherits
    pub edge_type: String,
}

/// The shared code structure graph.
#[derive(Debug, Default)]
pub struct CodeGraph {
    nodes: Vec<CodeNode>,
    edges: Vec<CodeEdge>,
    project_root: String,
    built: bool,
}

impl CodeGraph {
    /// Create an empty graph.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Whether a build has been performed.
    #[must_use]
    pub const fn is_built(&self) -> bool {
        self.built
    }

    /// The project root the graph was built from.
    #[must_use]
    pub fn root(&self) -> &str {
        &self.project_root
    }

    /// Scan `project_root` and rebuild the graph.
    pub fn build(&mut self, project_root: &str, max_files: usize) -> Result<usize, String> {
        let root = std::path::Path::new(project_root);
        if !root.is_dir() {
            return Err(format!("project_root is not a directory: {project_root}"));
        }
        let mut files: Vec<std::path::PathBuf> = Vec::new();
        let mut walked = 0usize;
        collect_files(root, root, max_files, &mut files, &mut walked)?;

        let mut nodes: Vec<CodeNode> = Vec::new();
        let mut edges: Vec<CodeEdge> = Vec::new();
        // Pass 1: extract all symbols from every file. Per-file symbol sets
        // are kept (with file contents) so pass 2 can build edges with
        // cross-file name resolution.
        struct FileInfo {
            rel: String,
            language: String,
            contents: String,
        }
        let mut files_info: Vec<FileInfo> = Vec::new();

        for file in &files {
            let rel = file
                .strip_prefix(root)
                .unwrap_or(file)
                .to_string_lossy()
                .replace('\\', "/");
            let language = language_for(&rel);
            if language.is_empty() {
                continue;
            }
            let contents = read_bounded(file);
            let Some(contents) = contents else { continue };

            // Extract symbols per language.
            let (patterns, inline) = symbol_patterns(&language);
            for (line_no, line) in contents.lines().enumerate() {
                let line_no = line_no + 1;
                for (pat, ty) in &patterns {
                    for cap in regex_captures(pat, line) {
                        let name = cap.clone();
                        let id = format!("{rel}:{name}:{ty}");
                        nodes.push(CodeNode {
                            id: id.clone(),
                            name: name.clone(),
                            node_type: (*ty).to_string(),
                            file: rel.clone(),
                            line: line_no,
                            language: language.clone(),
                        });
                        // Inheritance edges: class A(B) — resolved in pass 2.
                        if *ty == "class" {
                            for parent in inherit_targets(line) {
                                if !parent.is_empty() {
                                    edges.push(CodeEdge {
                                        source_id: id.clone(),
                                        target_id: format!("{rel}:{parent}:class"),
                                        edge_type: "inherits".into(),
                                    });
                                }
                            }
                        }
                    }
                }
                for (pat, ty) in &inline {
                    for cap in regex_captures(pat, line) {
                        let name = cap.clone();
                        nodes.push(CodeNode {
                            id: format!("{rel}:{name}:{ty}"),
                            name,
                            node_type: (*ty).to_string(),
                            file: rel.clone(),
                            line: line_no,
                            language: language.clone(),
                        });
                    }
                }
            }
            files_info.push(FileInfo {
                rel: rel.clone(),
                language,
                contents,
            });
        }

        // Pass 2: call edges with cross-file resolution. Every call site
        // `name(` on a line connects its enclosing function to every node
        // named `name` (any file), same-file candidates first.
        let name_index: HashMap<&str, Vec<usize>> = {
            let mut index: HashMap<&str, Vec<usize>> = HashMap::new();
            for (i, node) in nodes.iter().enumerate() {
                index.entry(node.name.as_str()).or_default().push(i);
            }
            index
        };
        for info in &files_info {
            for (line_no, line) in info.contents.lines().enumerate() {
                let Some(caller) = enclosing_function(&info.contents, line_no) else {
                    continue;
                };
                let source_id = format!("{}:{caller}:function", info.rel);
                for name in call_sites(line) {
                    let Some(mut candidates) = name_index.get(name.as_str()).cloned() else {
                        continue;
                    };
                    // same-file candidates first
                    candidates.sort_by_key(|&i| usize::from(nodes[i].file != info.rel));
                    for i in candidates.into_iter().take(3) {
                        edges.push(CodeEdge {
                            source_id: source_id.clone(),
                            target_id: nodes[i].id.clone(),
                            edge_type: "calls".into(),
                        });
                    }
                }
            }
            // Import edges.
            for line in info.contents.lines() {
                for target in import_targets(&info.language, line) {
                    edges.push(CodeEdge {
                        source_id: format!("{}:*:import", info.rel),
                        target_id: target,
                        edge_type: "imports".into(),
                    });
                }
            }
        }

        // Deduplicate (a symbol may match several patterns).
        let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
        nodes.retain(|n| seen.insert(n.id.clone()));
        let mut edge_seen: std::collections::HashSet<String> = std::collections::HashSet::new();
        edges.retain(|e| {
            edge_seen.insert(format!("{}|{}|{}", e.source_id, e.target_id, e.edge_type))
        });

        self.nodes = nodes;
        self.edges = edges;
        self.project_root = project_root.to_string();
        self.built = true;
        Ok(files.len())
    }

    /// Search nodes by name substring.
    #[must_use]
    pub fn search(&self, query: &str, limit: usize) -> Vec<Value> {
        let q = query.to_ascii_lowercase();
        self.nodes
            .iter()
            .filter(|n| n.name.to_ascii_lowercase().contains(&q))
            .take(limit)
            .map(node_json)
            .collect()
    }

    /// Find callers of a symbol (direct in-edges).
    #[must_use]
    pub fn callers(&self, symbol: &str, limit: usize) -> Vec<Value> {
        let targets: Vec<&CodeNode> = self.nodes.iter().filter(|n| n.name == symbol).collect();
        let mut out = Vec::new();
        for target in targets {
            for edge in &self.edges {
                if edge.edge_type == "calls" && edge.target_id == target.id {
                    if let Some(src) = self.node(&edge.source_id) {
                        out.push(node_json(src));
                        if out.len() >= limit {
                            return out;
                        }
                    }
                }
            }
        }
        out
    }

    /// Find callees of a symbol (direct out-edges).
    #[must_use]
    pub fn callees(&self, symbol: &str, limit: usize) -> Vec<Value> {
        let sources: Vec<&CodeNode> = self.nodes.iter().filter(|n| n.name == symbol).collect();
        let mut out = Vec::new();
        for source in sources {
            for edge in &self.edges {
                if edge.edge_type == "calls" && edge.source_id == source.id {
                    if let Some(tgt) = self.node(&edge.target_id) {
                        out.push(node_json(tgt));
                        if out.len() >= limit {
                            return out;
                        }
                    }
                }
            }
        }
        out
    }

    /// Explain a symbol: type, file, degree, incoming/outgoing.
    #[must_use]
    pub fn explain(&self, symbol: &str) -> Option<Value> {
        let node = self.nodes.iter().find(|n| n.name == symbol).or_else(|| {
            self.nodes
                .iter()
                .find(|n| n.name == symbol && n.node_type == "class")
        })?;
        let in_deg = self.edges.iter().filter(|e| e.target_id == node.id).count();
        let out_deg = self.edges.iter().filter(|e| e.source_id == node.id).count();
        let incoming: Vec<Value> = self
            .edges
            .iter()
            .filter(|e| e.target_id == node.id && e.edge_type == "calls")
            .take(20)
            .filter_map(|e| self.node(&e.source_id))
            .map(node_json)
            .collect();
        let outgoing: Vec<Value> = self
            .edges
            .iter()
            .filter(|e| e.source_id == node.id && e.edge_type == "calls")
            .take(20)
            .filter_map(|e| self.node(&e.target_id))
            .map(node_json)
            .collect();
        Some(json!({
            "symbol": node.name,
            "node_type": node.node_type,
            "file": node.file,
            "line": node.line,
            "language": node.language,
            "degree": in_deg + out_deg,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "incoming": incoming,
            "outgoing": outgoing,
        }))
    }

    /// Shortest call path from A to B (BFS), max_hops bound.
    #[must_use]
    pub fn path(&self, symbol_a: &str, symbol_b: &str, max_hops: usize) -> Value {
        let node_a = self.nodes.iter().find(|n| n.name == symbol_a);
        let node_b = self.nodes.iter().find(|n| n.name == symbol_b);
        let (Some(node_a), Some(node_b)) = (node_a, node_b) else {
            let missing = if node_a.is_none() { symbol_a } else { symbol_b };
            return json!({
                "status": "error",
                "error": format!("symbol not found: {missing}"),
            });
        };
        if node_a.id == node_b.id {
            return json!({
                "status": "success",
                "path": [symbol_a],
                "hops": 0,
            });
        }
        let mut adj: HashMap<String, Vec<String>> = HashMap::new();
        for e in &self.edges {
            if e.edge_type == "calls" {
                adj.entry(e.source_id.clone())
                    .or_default()
                    .push(e.target_id.clone());
            }
        }
        let mut visited = std::collections::HashSet::new();
        let mut queue: VecDeque<(String, Vec<String>)> = VecDeque::new();
        visited.insert(node_a.id.clone());
        queue.push_back((node_a.id.clone(), vec![node_a.id.clone()]));
        while let Some((current, path)) = queue.pop_front() {
            if current == node_b.id {
                let names: Vec<String> = path
                    .iter()
                    .map(|id| self.node(id).map_or_else(|| id.clone(), |n| n.name.clone()))
                    .collect();
                return json!({
                    "status": "success",
                    "path": names,
                    "hops": path.len() - 1,
                });
            }
            if path.len() > max_hops {
                continue;
            }
            if let Some(neighbors) = adj.get(&current) {
                for neighbor in neighbors {
                    if !visited.contains(neighbor) {
                        visited.insert(neighbor.clone());
                        let mut next = path.clone();
                        next.push(neighbor.clone());
                        queue.push_back((neighbor.clone(), next));
                    }
                }
            }
        }
        json!({
            "status": "no_path",
            "message": format!("no call path between {symbol_a} and {symbol_b} in {max_hops} hops"),
        })
    }

    /// All symbols transitively affected by a change to `symbol` —
    /// reverse BFS over the call graph (who calls it, who calls them…).
    #[must_use]
    pub fn affected_by(&self, symbol: &str, max_depth: usize) -> Value {
        let roots: Vec<&CodeNode> = self.nodes.iter().filter(|n| n.name == symbol).collect();
        if roots.is_empty() {
            return json!({
                "status": "error",
                "error": format!("symbol not found: {symbol}"),
            });
        }
        // reverse adjacency over calls edges
        let mut rev: HashMap<String, Vec<String>> = HashMap::new();
        for e in &self.edges {
            if e.edge_type == "calls" {
                rev.entry(e.target_id.clone())
                    .or_default()
                    .push(e.source_id.clone());
            }
        }
        let mut affected: Vec<Value> = Vec::new();
        let mut visited = std::collections::HashSet::new();
        let mut queue: VecDeque<(String, usize)> = VecDeque::new();
        for root in roots {
            queue.push_back((root.id.clone(), 0));
            visited.insert(root.id.clone());
        }
        while let Some((current, depth)) = queue.pop_front() {
            if depth > 0 {
                if let Some(node) = self.node(&current) {
                    affected.push(json!({
                        "symbol": node.name,
                        "node_type": node.node_type,
                        "file": node.file,
                        "line": node.line,
                        "depth": depth,
                    }));
                }
            }
            if depth >= max_depth {
                continue;
            }
            if let Some(callers) = rev.get(&current) {
                for caller in callers {
                    if !visited.contains(caller) {
                        visited.insert(caller.clone());
                        queue.push_back((caller.clone(), depth + 1));
                    }
                }
            }
        }
        json!({
            "status": "success",
            "symbol": symbol,
            "affected_count": affected.len(),
            "max_depth": max_depth,
            "affected": affected,
        })
    }

    /// Most-connected symbols (call-graph degree).
    #[must_use]
    pub fn god_nodes(&self, limit: usize) -> Vec<Value> {
        let mut degrees: HashMap<String, usize> = HashMap::new();
        for e in &self.edges {
            if e.edge_type == "calls" {
                *degrees.entry(e.source_id.clone()).or_default() += 1;
                *degrees.entry(e.target_id.clone()).or_default() += 1;
            }
        }
        let mut ranked: Vec<(&CodeNode, usize)> = degrees
            .iter()
            .filter_map(|(id, d)| self.node(id).map(|n| (n, *d)))
            .collect();
        ranked.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.name.cmp(&b.0.name)));
        ranked
            .into_iter()
            .take(limit)
            .map(|(n, d)| {
                let mut v = node_json(n);
                v["degree"] = json!(d);
                v
            })
            .collect()
    }

    /// Locate file/line fragments mentioning `query` (bounded grep over
    /// the scanned source files).
    #[must_use]
    pub fn fragment_search(&self, query: &str, max_results: usize) -> Vec<Value> {
        let mut out = Vec::new();
        let root = std::path::Path::new(&self.project_root);
        let mut files: Vec<std::path::PathBuf> = Vec::new();
        let mut walked = 0usize;
        if collect_files(root, root, 20_000, &mut files, &mut walked).is_err() {
            return out;
        }
        for file in files {
            let rel = file
                .strip_prefix(root)
                .unwrap_or(&file)
                .to_string_lossy()
                .replace('\\', "/");
            if language_for(&rel).is_empty() {
                continue;
            }
            let Some(contents) = read_bounded(&file) else {
                continue;
            };
            for (line_no, line) in contents.lines().enumerate() {
                if line
                    .to_ascii_lowercase()
                    .contains(&query.to_ascii_lowercase())
                {
                    out.push(json!({
                        "file": rel,
                        "line": line_no + 1,
                        "content": line.trim().to_string(),
                    }));
                    if out.len() >= max_results {
                        return out;
                    }
                }
            }
        }
        out
    }

    /// Graph statistics.
    #[must_use]
    pub fn stats(&self) -> Value {
        let mut languages: HashMap<String, (usize, usize)> = HashMap::new();
        for node in &self.nodes {
            let e = languages.entry(node.language.clone()).or_default();
            e.0 += 1;
        }
        for edge in &self.edges {
            if edge.edge_type == "calls" {
                if let Some(n) = self.node(&edge.source_id) {
                    let e = languages.entry(n.language.clone()).or_default();
                    e.1 += 1;
                }
            }
        }
        let languages: Vec<Value> = languages
            .into_iter()
            .map(|(lang, (nodes, calls))| json!({"language": lang, "nodes": nodes, "call_edges": calls}))
            .collect();
        json!({
            "built": self.built,
            "project_root": self.project_root,
            "nodes": self.nodes.len(),
            "edges": self.edges.len(),
            "languages": languages,
        })
    }

    fn node(&self, id: &str) -> Option<&CodeNode> {
        self.nodes.iter().find(|n| n.id == id)
    }
}

fn node_json(node: &CodeNode) -> Value {
    json!({
        "name": node.name,
        "node_type": node.node_type,
        "file": node.file,
        "line": node.line,
        "language": node.language,
    })
}

/// Recursively collect source files, bounded.
#[allow(clippy::only_used_in_recursion)]
fn collect_files(
    root: &std::path::Path,
    dir: &std::path::Path,
    max_files: usize,
    out: &mut Vec<std::path::PathBuf>,
    walked: &mut usize,
) -> Result<(), String> {
    if out.len() >= max_files {
        return Ok(());
    }
    let entries =
        std::fs::read_dir(dir).map_err(|e| format!("cannot read dir {}: {e}", dir.display()))?;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let name = entry.file_name().to_string_lossy().to_string();
            if SKIP_DIRS.contains(&name.as_str()) {
                continue;
            }
            collect_files(root, &path, max_files, out, walked)?;
            if out.len() >= max_files {
                return Ok(());
            }
        } else if path.is_file() {
            *walked += 1;
            if language_for(&path.to_string_lossy()).is_empty() {
                continue;
            }
            if entry.metadata().map_or(true, |m| m.len() > MAX_FILE_BYTES) {
                continue;
            }
            out.push(path);
        }
    }
    Ok(())
}

fn read_bounded(path: &std::path::Path) -> Option<String> {
    use std::io::Read;
    let file = std::fs::File::open(path).ok()?;
    let mut buf = Vec::new();
    std::io::Read::take(file, MAX_FILE_BYTES)
        .read_to_end(&mut buf)
        .ok()?;
    Some(String::from_utf8_lossy(&buf).into_owned())
}

fn language_for(path: &str) -> String {
    let ext = path.rsplit('.').next().unwrap_or("").to_ascii_lowercase();
    match ext.as_str() {
        "rs" => "rust".to_string(),
        "py" => "python".to_string(),
        "js" | "jsx" | "mjs" | "cjs" => "javascript".to_string(),
        "ts" | "tsx" => "typescript".to_string(),
        "go" => "go".to_string(),
        "java" => "java".to_string(),
        "c" | "h" => "c".to_string(),
        "cpp" | "cc" | "hpp" => "cpp".to_string(),
        "rb" => "ruby".to_string(),
        "sh" => "shell".to_string(),
        "zig" => "zig".to_string(),
        "jl" => "julia".to_string(),
        _ => String::new(),
    }
}

/// (pattern, node_type) pairs for top-level symbols; (pattern, node_type)
/// pairs for inline symbols.
type PatternList = Vec<(&'static str, &'static str)>;
fn symbol_patterns(language: &str) -> (PatternList, PatternList) {
    match language {
        "rust" => (
            vec![
                (r"fn\s+([a-zA-Z_][a-zA-Z0-9_]*)", "function"),
                (r"struct\s+([a-zA-Z_][a-zA-Z0-9_]*)", "struct"),
                (r"enum\s+([a-zA-Z_][a-zA-Z0-9_]*)", "enum"),
                (r"impl\s+([a-zA-Z_][a-zA-Z0-9_]*)", "impl"),
                (r"trait\s+([a-zA-Z_][a-zA-Z0-9_]*)", "trait"),
                (r"mod\s+([a-zA-Z_][a-zA-Z0-9_]*)", "module"),
            ],
            vec![(r"pub\s+fn\s+([a-zA-Z_][a-zA-Z0-9_]*)", "function")],
        ),
        "python" => (
            vec![
                (r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", "function"),
                (r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)", "class"),
            ],
            vec![],
        ),
        "javascript" | "typescript" => (
            vec![
                (r"function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", "function"),
                (r"class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", "class"),
            ],
            vec![(
                r"(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=",
                "const",
            )],
        ),
        "go" => (
            vec![
                (r"func\s+([a-zA-Z_][a-zA-Z0-9_]*)", "function"),
                (r"type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+struct", "struct"),
            ],
            vec![],
        ),
        "java" => (
            vec![
                (
                    r"(?:public|private|protected)\s+(?:static\s+)?[a-zA-Z0-9_<>\[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                    "method",
                ),
                (r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)", "class"),
            ],
            vec![],
        ),
        _ => (
            vec![(
                r"(?:fn|def|function)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                "function",
            )],
            vec![],
        ),
    }
}

/// Regex capture helper without the regex crate: find `(name)` after the
/// first occurrence of the pattern's literal prefix. Supports the simple
/// `\s+` and capture-group patterns used above.
fn regex_captures(pattern: &str, line: &str) -> Vec<String> {
    let mut captures = Vec::new();
    let line_lower = line;
    // crude matcher for our pattern subset:
    // pattern = "literal\s+([class])" where literal contains no regex
    let open = pattern.find('(').unwrap_or(pattern.len());
    let literal = &pattern[..open];
    let trimmed = literal.trim_end_matches("\\s+");
    let mut rest = line_lower;
    while let Some(idx) = rest.find(trimmed) {
        let after = &rest[idx + trimmed.len()..];
        // skip \s+ if present
        let after = after.trim_start_matches([' ', '\t']);
        // capture group is a class like [a-zA-Z_][a-zA-Z0-9_]* — match a name
        if let Some(name) = leading_identifier(after) {
            captures.push(name);
        }
        rest = after;
    }
    captures
}

/// Match a leading identifier `[A-Za-z_][A-Za-z0-9_$]*`.
fn leading_identifier(s: &str) -> Option<String> {
    let mut name = String::new();
    for c in s.chars() {
        if name.is_empty() {
            if c.is_ascii_alphabetic() || c == '_' || c == '$' {
                name.push(c);
            } else {
                return None;
            }
        } else if c.is_ascii_alphanumeric() || c == '_' || c == '$' {
            name.push(c);
        } else {
            break;
        }
    }
    if name.is_empty() { None } else { Some(name) }
}

/// Class inheritance targets: `class A(B, C)` → `["B", "C"]`.
fn inherit_targets(line: &str) -> Vec<String> {
    let Some(open) = line.find('(') else {
        return Vec::new();
    };
    let Some(close) = line[open..].find(')') else {
        return Vec::new();
    };
    line[open + 1..open + close]
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

/// Identifiers immediately followed by '(' on a line — potential call
/// sites. Skips function definitions (`fn name(`, `def name(`,
/// `function name(`) and qualified/attribute accesses are included
/// (module::name(, obj.name() are real call sites).
fn call_sites(line: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut rest = line;
    while !rest.is_empty() {
        // skip leading non-identifier characters
        let skipped = rest
            .chars()
            .take_while(|c| !(c.is_ascii_alphabetic() || *c == '_' || *c == '$'))
            .count();
        rest = &rest[skipped..];
        let Some(name) = leading_identifier(rest) else {
            break;
        };
        let consumed = line.len() - rest.len();
        let before = line[..consumed].chars().last();
        // valid boundary: not part of a larger identifier
        let boundary_ok = !before.is_some_and(|c| c.is_ascii_alphanumeric() || c == '_');
        if boundary_ok {
            let after = &rest[name.len()..];
            if after.starts_with('(') {
                // skip definition lines: "fn name(" / "def name(" / "function name("
                let def_marker = line[..consumed].rsplit([' ', '\t']).next().unwrap_or("");
                if !(def_marker == "fn"
                    || def_marker == "def"
                    || def_marker == "function"
                    || out.contains(&name))
                {
                    out.push(name.clone());
                }
            }
        }
        // advance past the identifier
        let skip = name.len().max(1);
        rest = &rest[skip..];
    }
    out
}

/// The function that encloses a given line index — the **last**
/// `fn/def/function` declaration at or before it (a definition line
/// encloses itself).
fn enclosing_function(contents: &str, line_idx: usize) -> Option<String> {
    let mut found: Option<String> = None;
    for (i, line) in contents.lines().enumerate() {
        if i > line_idx {
            break;
        }
        for pat in ["fn ", "def ", "function "] {
            if let Some(idx) = line.find(pat) {
                if let Some(name) = leading_identifier(&line[idx + pat.len()..]) {
                    found = Some(name);
                }
            }
        }
    }
    found
}

/// Import edge targets from a line, by language.
fn import_targets(language: &str, line: &str) -> Vec<String> {
    let mut out = Vec::new();
    match language {
        "rust" => {
            if let Some(rest) = line.trim().strip_prefix("use ") {
                let target = rest.trim_end_matches(';').trim();
                if !target.starts_with("crate::") {
                    out.push(format!("import:{target}"));
                }
            }
        }
        "python" => {
            if let Some(rest) = line.trim().strip_prefix("import ") {
                for part in rest.split(',') {
                    let module = part.trim().split('.').next().unwrap_or("").to_string();
                    if !module.is_empty() {
                        out.push(format!("import:{module}"));
                    }
                }
            } else if let Some(rest) = line.trim().strip_prefix("from ") {
                let module = rest.split(" import ").next().unwrap_or("").trim();
                if !module.is_empty() {
                    out.push(format!("import:{module}"));
                }
            }
        }
        "javascript" | "typescript" => {
            if let Some(rest) = line.trim().strip_prefix("import ") {
                if let Some(from) = rest.split(" from ").nth(1) {
                    let module = from.trim().trim_matches(['\'', '"']).to_string();
                    out.push(format!("import:{module}"));
                }
            }
        }
        "go" => {
            if let Some(rest) = line.trim().strip_prefix("import \"") {
                let module = rest.trim_end_matches('"').to_string();
                out.push(format!("import:{module}"));
            }
        }
        _ => {}
    }
    out
}

// ── code.graph ───────────────────────────────────────────────────────

/// `code.graph` — build (or refresh) the code structure graph.
pub struct CodeGraphTool {
    graph: Arc<Mutex<CodeGraph>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CodeGraphTool {
    #[must_use]
    pub fn new(graph: Arc<Mutex<CodeGraph>>) -> Self {
        Self {
            graph,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Filesystem]),
        }
    }
}

#[async_trait]
impl Tool for CodeGraphTool {
    fn name(&self) -> &str {
        "code.graph"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Build (or refresh) the code structure graph for a project. Args: project_root (required), max_files (default 50000)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let project_root = args
            .get("project_root")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("project_root is required".into()))?;
        let max_files = args
            .get("max_files")
            .and_then(Value::as_u64)
            .unwrap_or(DEFAULT_MAX_FILES as u64) as usize;
        let project_root = project_root.to_string();
        let mut graph = self
            .graph
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("code graph lock: {e}")))?;
        let files = graph
            .build(&project_root, max_files)
            .map_err(wm_core::CoreError::Tool)?;
        let stats = graph.stats();
        let mut result = json!({
            "status": "success",
            "files_scanned": files,
        });
        for (k, v) in stats.as_object().unwrap() {
            result[k.clone()] = v.clone();
        }
        Ok(result)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── code.query ───────────────────────────────────────────────────────

/// `code.query` — natural-language queries against the code graph.
pub struct CodeQueryTool {
    graph: Arc<Mutex<CodeGraph>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CodeQueryTool {
    #[must_use]
    pub fn new(graph: Arc<Mutex<CodeGraph>>) -> Self {
        Self {
            graph,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Filesystem]),
        }
    }
}

#[async_trait]
impl Tool for CodeQueryTool {
    fn name(&self) -> &str {
        "code.query"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Query the code graph with natural language: 'what calls X', 'what does X call', 'path from A to B', 'explain X', 'god nodes', or a symbol search. Args: query (required), limit (default 20). Build the graph first with code.graph."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query is required".into()))?;
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(20) as usize;
        let graph = self
            .graph
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("code graph lock: {e}")))?;
        if !graph.is_built() {
            return Ok(json!({
                "status": "error",
                "error": "code graph not built — run code.graph first",
            }));
        }
        let q = query.to_ascii_lowercase();
        let result = if let Some(rest) = q.strip_prefix("what calls ") {
            json!({"status": "success", "query": query, "callers": graph.callers(rest.trim(), limit)})
        } else if q.contains("what does") && q.contains("call") {
            let symbol = q
                .split("what does")
                .nth(1)
                .and_then(|s| s.split("call").next())
                .unwrap_or("")
                .trim();
            json!({"status": "success", "query": query, "callees": graph.callees(symbol, limit)})
        } else if q.contains("path from") && q.contains(" to ") {
            let parts: Vec<&str> = q.split(" to ").collect();
            let a = parts[0].strip_prefix("path from").unwrap_or("").trim();
            let b = parts[1].trim();
            graph.path(a, b, 5)
        } else if let Some(rest) = q.strip_prefix("explain ") {
            match graph.explain(rest.trim()) {
                Some(expl) => json!({"status": "success", "query": query, "explanation": expl}),
                None => {
                    json!({"status": "error", "error": format!("symbol not found: {}", rest.trim())})
                }
            }
        } else if q.contains("god") || q.contains("most connected") {
            json!({"status": "success", "query": query, "god_nodes": graph.god_nodes(limit)})
        } else if q == "stats" || q.contains("stats") {
            graph.stats()
        } else {
            json!({"status": "success", "query": query, "matches": graph.search(query, limit)})
        };
        Ok(result)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── code.affected_by ─────────────────────────────────────────────────

/// `code.affected_by` — find symbols affected by a change.
pub struct CodeAffectedByTool {
    graph: Arc<Mutex<CodeGraph>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CodeAffectedByTool {
    #[must_use]
    pub fn new(graph: Arc<Mutex<CodeGraph>>) -> Self {
        Self {
            graph,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Filesystem]),
        }
    }
}

#[async_trait]
impl Tool for CodeAffectedByTool {
    fn name(&self) -> &str {
        "code.affected_by"
    }
    fn gana(&self) -> Gana {
        Gana::Chariot
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Find all symbols transitively affected by a change to the given symbol (reverse call-graph BFS). Args: symbol (required), max_depth (default 3)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let symbol = args
            .get("symbol")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("symbol is required".into()))?;
        let max_depth = args
            .get("max_depth")
            .and_then(Value::as_u64)
            .unwrap_or(3)
            .clamp(1, 10) as usize;
        let graph = self
            .graph
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("code graph lock: {e}")))?;
        if !graph.is_built() {
            return Ok(json!({
                "status": "error",
                "error": "code graph not built — run code.graph first",
            }));
        }
        Ok(graph.affected_by(symbol, max_depth))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── fragment.search ──────────────────────────────────────────────────

/// `fragment.search` — locate code fragments mentioning a query.
pub struct FragmentSearchTool {
    graph: Arc<Mutex<CodeGraph>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl FragmentSearchTool {
    #[must_use]
    pub fn new(graph: Arc<Mutex<CodeGraph>>) -> Self {
        Self {
            graph,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Filesystem]),
        }
    }
}

#[async_trait]
impl Tool for FragmentSearchTool {
    fn name(&self) -> &str {
        "fragment.search"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Locate file/line fragments mentioning a query in the built code graph's project. Args: query (required), max_results (default 20)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query is required".into()))?;
        let max_results = args
            .get("max_results")
            .and_then(Value::as_u64)
            .unwrap_or(20) as usize;
        let graph = self
            .graph
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("code graph lock: {e}")))?;
        if !graph.is_built() {
            return Ok(json!({
                "status": "error",
                "error": "code graph not built — run code.graph first",
            }));
        }
        let symbols = graph.search(query, max_results);
        let fragments = graph.fragment_search(query, max_results);
        Ok(json!({
            "status": "success",
            "query": query,
            "symbol_matches": symbols.len(),
            "fragment_matches": fragments.len(),
            "symbols": symbols,
            "fragments": fragments,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the code tools (4) against a shared graph.
#[must_use]
pub fn register_code(
    registry: &wm_dispatch::ToolRegistry,
    graph: Arc<Mutex<CodeGraph>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(CodeGraphTool::new(graph.clone())))
        .register(Arc::new(CodeQueryTool::new(graph.clone())))
        .register(Arc::new(CodeAffectedByTool::new(graph.clone())))
        .register(Arc::new(FragmentSearchTool::new(graph)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_project(dir: &std::path::Path) {
        std::fs::create_dir_all(dir.join("src")).unwrap();
        std::fs::write(
            dir.join("src/main.rs"),
            "mod utils;\nfn main() {\n    let x = utils::double(21);\n    println!(\"{x}\");\n}\n",
        )
        .unwrap();
        std::fs::write(
            dir.join("src/utils.rs"),
            "pub fn double(x: i32) -> i32 {\n    x * 2\n}\n",
        )
        .unwrap();
    }

    #[test]
    fn build_extracts_symbols_and_calls() {
        let dir = tempfile::tempdir().unwrap();
        write_project(dir.path());
        let mut graph = CodeGraph::new();
        let files = graph.build(dir.path().to_str().unwrap(), 100).unwrap();
        assert!(files >= 2);
        assert!(
            graph
                .nodes
                .iter()
                .any(|n| n.name == "main" && n.node_type == "function")
        );
        assert!(
            graph
                .nodes
                .iter()
                .any(|n| n.name == "double" && n.node_type == "function")
        );
        // main calls double
        assert!(!graph.callers("double", 10).is_empty());
        assert!(!graph.callees("main", 10).is_empty());
    }

    #[test]
    fn affected_by_traces_reverse_bfs() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        std::fs::write(
            dir.path().join("src/a.rs"),
            "fn top() { mid(); }\nfn mid() { leaf(); }\nfn leaf() {}\n",
        )
        .unwrap();
        let mut graph = CodeGraph::new();
        graph.build(dir.path().to_str().unwrap(), 100).unwrap();
        let result = graph.affected_by("leaf", 3);
        assert_eq!(result["status"], "success");
        let affected = result["affected"].as_array().unwrap();
        let names: Vec<&str> = affected
            .iter()
            .filter_map(|a| a.get("symbol").and_then(Value::as_str))
            .collect();
        assert!(names.contains(&"mid"));
        assert!(names.contains(&"top"));
    }

    #[test]
    fn path_finds_connection() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        std::fs::write(dir.path().join("src/a.rs"), "fn a() { b(); }\nfn b() {}\n").unwrap();
        let mut graph = CodeGraph::new();
        graph.build(dir.path().to_str().unwrap(), 100).unwrap();
        let result = graph.path("a", "b", 3);
        assert_eq!(result["status"], "success");
        assert_eq!(result["hops"], 1);
    }

    #[test]
    fn fragment_search_finds_lines() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        std::fs::write(
            dir.path().join("src/a.rs"),
            "fn a() {}\n// the unique marker word\nfn b() {}\n",
        )
        .unwrap();
        let mut graph = CodeGraph::new();
        graph.build(dir.path().to_str().unwrap(), 100).unwrap();
        let fragments = graph.fragment_search("unique marker", 10);
        assert_eq!(fragments.len(), 1);
        assert_eq!(fragments[0]["line"], 2);
    }

    #[test]
    fn skip_dirs_are_not_scanned() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("target")).unwrap();
        std::fs::write(dir.path().join("target/bad.rs"), "fn bad() {}\n").unwrap();
        std::fs::write(dir.path().join("good.rs"), "fn good() {}\n").unwrap();
        let mut graph = CodeGraph::new();
        graph.build(dir.path().to_str().unwrap(), 100).unwrap();
        assert!(!graph.nodes.iter().any(|n| n.name == "bad"));
        assert!(graph.nodes.iter().any(|n| n.name == "good"));
    }

    #[tokio::test]
    async fn tools_require_built_graph() {
        let graph = Arc::new(Mutex::new(CodeGraph::new()));
        let tool = CodeQueryTool::new(graph);
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"query": "what calls main"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "error");
        assert_eq!(
            result["error"],
            "code graph not built — run code.graph first"
        );
    }
}
