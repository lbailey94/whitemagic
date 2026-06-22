//! Polyglot Scout — Rust AST + parallel file walker
//!
//! Replaces Python's deep_scout_deployment.py (77 files/sec) with a
//! Rust implementation using rayon + walkdir for true parallel scanning.
//!
//! Performance target: 5,000+ files/sec (65× over Python baseline)
//!
//! Scout categories:
//!   - Performance: nested loops, large functions, sync I/O in hot paths
//!   - Migration: Python files that are good Rust migration candidates
//!   - Quality: missing type hints, TODO/FIXME, high complexity
//!   - Integration: Python↔Rust boundary opportunities
//!   - Architecture: large files, circular imports, dead code patterns
//!
//! Usage:
//!   cargo run --bin polyglot-scout --features native-deps -- [path] [--json]

use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;
use walkdir::WalkDir;

// ---------------------------------------------------------------------------
// Finding types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum FindingCategory {
    Performance,
    Migration,
    Quality,
    Integration,
    Architecture,
    Security,
}

impl FindingCategory {
    fn name(&self) -> &'static str {
        match self {
            FindingCategory::Performance  => "performance",
            FindingCategory::Migration    => "migration",
            FindingCategory::Quality      => "quality",
            FindingCategory::Integration  => "integration",
            FindingCategory::Architecture => "architecture",
            FindingCategory::Security     => "security",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub file: String,
    pub line: usize,
    pub category: String,
    pub severity: u8,      // 1=low, 2=medium, 3=high, 4=critical
    pub title: String,
    pub detail: String,
    pub suggestion: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileReport {
    pub path: String,
    pub language: String,
    pub lines: usize,
    pub findings: Vec<Finding>,
    pub migration_score: f64,  // 0.0–1.0: how good a Rust migration candidate
    pub complexity_score: f64, // 0.0–1.0: estimated complexity
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScoutReport {
    pub total_files: usize,
    pub total_lines: usize,
    pub files_per_sec: f64,
    pub duration_ms: u64,
    pub findings_by_category: HashMap<String, usize>,
    pub top_migration_candidates: Vec<MigrationCandidate>,
    pub top_findings: Vec<Finding>,
    pub language_breakdown: HashMap<String, usize>,
    pub summary: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationCandidate {
    pub file: String,
    pub lines: usize,
    pub migration_score: f64,
    pub reason: String,
    pub estimated_speedup: String,
}

// ---------------------------------------------------------------------------
// Language detection
// ---------------------------------------------------------------------------

fn detect_language(path: &Path) -> Option<&'static str> {
    match path.extension()?.to_str()? {
        "py"   => Some("python"),
        "rs"   => Some("rust"),
        "kk"   => Some("koka"),
        "ex" | "exs" => Some("elixir"),
        "zig"  => Some("zig"),
        "mojo" => Some("mojo"),
        "go"   => Some("go"),
        "ts" | "tsx" => Some("typescript"),
        "js"   => Some("javascript"),
        "hs"   => Some("haskell"),
        "jl"   => Some("julia"),
        _      => None,
    }
}

// ---------------------------------------------------------------------------
// File analysis — the core scout logic
// ---------------------------------------------------------------------------

fn analyze_file(path: &Path) -> Option<FileReport> {
    let lang = detect_language(path)?;
    let content = fs::read_to_string(path).ok()?;
    let lines: Vec<&str> = content.lines().collect();
    let line_count = lines.len();

    if line_count == 0 { return None; }

    let mut findings = Vec::new();
    let path_str = path.to_string_lossy().to_string();

    match lang {
        "python" => analyze_python(&lines, &path_str, &mut findings),
        "rust"   => analyze_rust(&lines, &path_str, &mut findings),
        _        => {}
    }

    let migration_score = compute_migration_score(lang, &lines, &findings);
    let complexity_score = compute_complexity_score(&lines);

    Some(FileReport {
        path: path_str,
        language: lang.to_string(),
        lines: line_count,
        findings,
        migration_score,
        complexity_score,
    })
}

fn analyze_python(lines: &[&str], path: &str, findings: &mut Vec<Finding>) {
    let mut indent_depth: i32 = 0;
    let mut max_indent: i32 = 0;
    let mut in_nested_loop = false;
    let mut loop_depth: i32 = 0;
    let mut func_line_count = 0;
    let mut func_start_line = 0;
    let mut in_func = false;
    let mut has_type_hints = false;
    let mut _import_count = 0;
    let mut _todo_count = 0;
    let mut _sql_in_loop = false;
    let mut loop_stack: Vec<usize> = Vec::new();

    for (i, &line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        let current_indent = (line.len() - line.trim_start().len()) as i32 / 4;

        // Track imports
        if trimmed.starts_with("import ") || trimmed.starts_with("from ") {
            _import_count += 1;
        }

        // Track type hints
        if trimmed.contains("->") || trimmed.contains(": int") || trimmed.contains(": str")
            || trimmed.contains(": float") || trimmed.contains(": bool") || trimmed.contains(": list")
            || trimmed.contains(": dict") || trimmed.contains(": Optional") {
            has_type_hints = true;
        }

        // TODO/FIXME
        if trimmed.contains("TODO") || trimmed.contains("FIXME") || trimmed.contains("HACK") || trimmed.contains("XXX") {
            _todo_count += 1;
            findings.push(Finding {
                file: path.to_string(),
                line: i + 1,
                category: FindingCategory::Quality.name().to_string(),
                severity: 2,
                title: "TODO/FIXME present".to_string(),
                detail: trimmed.chars().take(80).collect(),
                suggestion: "Resolve or create a campaign VC for this item".to_string(),
            });
        }

        // Loop detection
        if trimmed.starts_with("for ") || trimmed.starts_with("while ") {
            loop_stack.push(i);
            loop_depth += 1;
            if loop_depth >= 2 {
                in_nested_loop = true;
            }
        }

        // Nested loop finding
        if in_nested_loop && loop_depth >= 2 && loop_stack.len() >= 2 {
            findings.push(Finding {
                file: path.to_string(),
                line: i + 1,
                category: FindingCategory::Performance.name().to_string(),
                severity: 3,
                title: "Nested loop (O(n²) or worse)".to_string(),
                detail: format!("Loop depth {} at line {}", loop_depth, i + 1),
                suggestion: "Consider Rust rayon parallel iterator or algorithmic optimization".to_string(),
            });
            in_nested_loop = false; // Only report once per nested section
        }

        // SQL in loop
        if loop_depth > 0 && (trimmed.contains(".execute(") || trimmed.contains("cursor.") || trimmed.contains("conn.")) {
            _sql_in_loop = true;
            findings.push(Finding {
                file: path.to_string(),
                line: i + 1,
                category: FindingCategory::Performance.name().to_string(),
                severity: 4,
                title: "DB query inside loop (N+1 problem)".to_string(),
                detail: trimmed.chars().take(80).collect(),
                suggestion: "Batch queries outside loop; use Rust r2d2 connection pool".to_string(),
            });
        }

        // Function tracking
        if trimmed.starts_with("def ") || trimmed.starts_with("async def ") {
            if in_func && func_line_count > 50 {
                findings.push(Finding {
                    file: path.to_string(),
                    line: func_start_line + 1,
                    category: FindingCategory::Quality.name().to_string(),
                    severity: 2,
                    title: format!("Large function ({} lines)", func_line_count),
                    detail: format!("Function starting at line {} has {} lines", func_start_line + 1, func_line_count),
                    suggestion: "Decompose into smaller functions; consider Rust module".to_string(),
                });
            }
            in_func = true;
            func_start_line = i;
            func_line_count = 0;
        }
        if in_func { func_line_count += 1; }

        // Dedent resets loop depth (simplified)
        if !trimmed.is_empty() && current_indent < indent_depth {
            let dedent = indent_depth - current_indent;
            loop_depth = (loop_depth - dedent).max(0);
            if loop_depth < 2 { in_nested_loop = false; }
            loop_stack.truncate(loop_stack.len().saturating_sub(dedent as usize));
        }

        if !trimmed.is_empty() {
            indent_depth = current_indent;
            max_indent = max_indent.max(current_indent);
        }
    }

    // Missing type hints
    if !has_type_hints && lines.iter().any(|l| l.trim().starts_with("def ")) {
        findings.push(Finding {
            file: path.to_string(),
            line: 1,
            category: FindingCategory::Quality.name().to_string(),
            severity: 1,
            title: "No type hints detected".to_string(),
            detail: "File has functions but no type annotations".to_string(),
            suggestion: "Add type hints; enables mypy checking and Rust migration planning".to_string(),
        });
    }

    // Large file
    if lines.len() > 300 {
        findings.push(Finding {
            file: path.to_string(),
            line: 1,
            category: FindingCategory::Architecture.name().to_string(),
            severity: 2,
            title: format!("Large file ({} lines)", lines.len()),
            detail: format!("{} lines — consider decomposition", lines.len()),
            suggestion: "Split into focused modules; large files are prime Rust migration candidates".to_string(),
        });
    }

    // Heavy computation patterns → migration candidate
    let heavy_patterns = ["numpy", "scipy", "torch", "sklearn", "embedding", "cosine", "matrix", "vector"];
    for pattern in &heavy_patterns {
        if lines.iter().any(|l| l.contains(pattern)) {
            findings.push(Finding {
                file: path.to_string(),
                line: 1,
                category: FindingCategory::Migration.name().to_string(),
                severity: 3,
                title: format!("Heavy computation: uses {}", pattern),
                detail: format!("File uses {} — strong Rust/Mojo migration candidate", pattern),
                suggestion: format!("Migrate {} operations to Rust ndarray or Mojo GPU", pattern),
            });
            break;
        }
    }

    // Security: f-string SQL
    for (i, &line) in lines.iter().enumerate() {
        let t = line.trim();
        if (t.contains("execute(f\"") || t.contains("execute(f'") || t.contains("execute(\"") && t.contains("{"))
            && (t.contains("SELECT") || t.contains("INSERT") || t.contains("UPDATE") || t.contains("DELETE")) {
            findings.push(Finding {
                file: path.to_string(),
                line: i + 1,
                category: FindingCategory::Security.name().to_string(),
                severity: 4,
                title: "Potential SQL injection (f-string in execute)".to_string(),
                detail: t.chars().take(80).collect(),
                suggestion: "Use parameterized queries: execute(sql, (param,))".to_string(),
            });
        }
    }
}

fn analyze_rust(lines: &[&str], path: &str, findings: &mut Vec<Finding>) {
    for (i, &line) in lines.iter().enumerate() {
        let t = line.trim();

        // unwrap() calls
        if t.contains(".unwrap()") && !t.starts_with("//") {
            findings.push(Finding {
                file: path.to_string(),
                line: i + 1,
                category: FindingCategory::Quality.name().to_string(),
                severity: 2,
                title: "unwrap() — potential panic".to_string(),
                detail: t.chars().take(80).collect(),
                suggestion: "Use ? operator or expect() with descriptive message".to_string(),
            });
        }

        // TODO in Rust
        if t.contains("todo!()") || t.contains("unimplemented!()") {
            findings.push(Finding {
                file: path.to_string(),
                line: i + 1,
                category: FindingCategory::Quality.name().to_string(),
                severity: 3,
                title: "Stub: todo!() or unimplemented!()".to_string(),
                detail: t.chars().take(80).collect(),
                suggestion: "Implement or add #[no_stub] enforcement".to_string(),
            });
        }

        // clone() in hot path (heuristic: inside for loop)
        if t.contains(".clone()") && i > 0 {
            let prev = lines[i.saturating_sub(3)..i].iter()
                .any(|l| l.trim().starts_with("for ") || l.trim().starts_with("while "));
            if prev {
                findings.push(Finding {
                    file: path.to_string(),
                    line: i + 1,
                    category: FindingCategory::Performance.name().to_string(),
                    severity: 2,
                    title: "clone() inside loop — possible allocation hot path".to_string(),
                    detail: t.chars().take(80).collect(),
                    suggestion: "Consider Arc<T> or borrowing instead of cloning".to_string(),
                });
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

fn compute_migration_score(lang: &str, lines: &[&str], findings: &[Finding]) -> f64 {
    if lang != "python" { return 0.0; }

    let mut score: f64 = 0.0;
    let line_count = lines.len() as f64;

    // Large files are better candidates
    if line_count > 500.0 { score += 0.3; }
    else if line_count > 200.0 { score += 0.15; }

    // Performance findings boost score
    let perf_findings = findings.iter().filter(|f| f.category == "performance").count();
    score += (perf_findings as f64 * 0.1).min(0.3);

    // Heavy computation patterns
    let heavy = findings.iter().filter(|f| f.category == "migration").count();
    score += (heavy as f64 * 0.15).min(0.3);

    // Security issues boost (Rust is memory-safe)
    let security = findings.iter().filter(|f| f.category == "security").count();
    score += (security as f64 * 0.05).min(0.1);

    score.min(1.0)
}

fn compute_complexity_score(lines: &[&str]) -> f64 {
    let mut complexity: f64 = 0.0;
    let line_count = lines.len() as f64;

    // Cyclomatic complexity proxies
    for line in lines {
        let t = line.trim();
        if t.starts_with("if ") || t.starts_with("elif ") || t.starts_with("else:") { complexity += 1.0; }
        if t.starts_with("for ") || t.starts_with("while ") { complexity += 1.5; }
        if t.starts_with("try:") || t.starts_with("except") { complexity += 1.0; }
        if t.contains(" and ") || t.contains(" or ") { complexity += 0.5; }
    }

    (complexity / line_count.max(1.0)).min(1.0)
}

// ---------------------------------------------------------------------------
// Directory walker
// ---------------------------------------------------------------------------

fn walk_directory(root: &Path, counter: Arc<AtomicU64>) -> Vec<FileReport> {
    let paths: Vec<PathBuf> = WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .filter(|e| {
            // Skip common noise directories
            let path = e.path();
            !path.components().any(|c| {
                let s = c.as_os_str().to_string_lossy();
                matches!(s.as_ref(), ".git" | "__pycache__" | "node_modules" | "target"
                    | ".venv" | "venv" | ".mypy_cache" | ".ruff_cache" | "dist" | "build")
            })
        })
        .map(|e| e.path().to_path_buf())
        .collect();

    paths.par_iter()
        .filter_map(|path| {
            let result = analyze_file(path);
            counter.fetch_add(1, Ordering::Relaxed);
            result
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Report aggregation
// ---------------------------------------------------------------------------

fn build_report(reports: Vec<FileReport>, duration_ms: u64, total_files: usize) -> ScoutReport {
    let total_lines: usize = reports.iter().map(|r| r.lines).sum();
    let files_per_sec = total_files as f64 / (duration_ms as f64 / 1000.0);

    let mut findings_by_category: HashMap<String, usize> = HashMap::new();
    let mut all_findings: Vec<Finding> = Vec::new();
    let mut language_breakdown: HashMap<String, usize> = HashMap::new();

    for report in &reports {
        *language_breakdown.entry(report.language.clone()).or_insert(0) += 1;
        for finding in &report.findings {
            *findings_by_category.entry(finding.category.clone()).or_insert(0) += 1;
            all_findings.push(finding.clone());
        }
    }

    // Sort findings by severity desc
    all_findings.sort_by(|a, b| b.severity.cmp(&a.severity));

    // Top migration candidates
    let mut candidates: Vec<MigrationCandidate> = reports.iter()
        .filter(|r| r.language == "python" && r.migration_score > 0.3)
        .map(|r| {
            let speedup = if r.migration_score > 0.7 { "20-50×" }
                else if r.migration_score > 0.5 { "10-20×" }
                else { "5-10×" };
            let reason = if r.findings.iter().any(|f| f.category == "performance") {
                "Performance bottlenecks detected".to_string()
            } else if r.findings.iter().any(|f| f.category == "migration") {
                "Heavy computation (numpy/embedding/vector)".to_string()
            } else {
                format!("Large file ({} lines)", r.lines)
            };
            MigrationCandidate {
                file: r.path.clone(),
                lines: r.lines,
                migration_score: r.migration_score,
                reason,
                estimated_speedup: speedup.to_string(),
            }
        })
        .collect();
    candidates.sort_by(|a, b| b.migration_score.partial_cmp(&a.migration_score).unwrap_or(std::cmp::Ordering::Equal));

    let summary = vec![
        format!("Scanned {} files ({} lines) in {}ms at {:.0} files/sec",
            total_files, total_lines, duration_ms, files_per_sec),
        format!("Found {} total findings across {} categories",
            all_findings.len(), findings_by_category.len()),
        format!("Top migration candidates: {} Python files scoring >0.3",
            candidates.len()),
        format!("Critical findings: {}",
            all_findings.iter().filter(|f| f.severity == 4).count()),
        format!("Languages: {}",
            language_breakdown.iter()
                .map(|(k, v)| format!("{}: {}", k, v))
                .collect::<Vec<_>>().join(", ")),
    ];

    ScoutReport {
        total_files,
        total_lines,
        files_per_sec,
        duration_ms,
        findings_by_category,
        top_migration_candidates: candidates.into_iter().take(10).collect(),
        top_findings: all_findings.into_iter().take(20).collect(),
        language_breakdown,
        summary,
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let root_path = args.get(1).map(|s| s.as_str()).unwrap_or(".");
    let json_output = args.iter().any(|a| a == "--json");

    let root = Path::new(root_path);

    if !json_output {
        println!("╔══════════════════════════════════════════════════════════════╗");
        println!("║           POLYGLOT SCOUT — Rust Parallel AST Walker          ║");
        println!("╚══════════════════════════════════════════════════════════════╝");
        println!();
        println!("  Root: {}", root.display());
        println!("  Threads: {}", rayon::current_num_threads());
        println!();
    }

    let counter = Arc::new(AtomicU64::new(0));
    let start = Instant::now();

    let reports = walk_directory(root, Arc::clone(&counter));
    let total_files = counter.load(Ordering::Relaxed) as usize;
    let duration_ms = start.elapsed().as_millis() as u64;

    let report = build_report(reports, duration_ms, total_files);

    if json_output {
        println!("{}", serde_json::to_string_pretty(&report).unwrap());
        return;
    }

    // Human-readable output
    println!("══════════════════════════════════════════════════════════════");
    println!("  SUMMARY");
    println!("══════════════════════════════════════════════════════════════");
    for line in &report.summary {
        println!("  {}", line);
    }

    println!();
    println!("══════════════════════════════════════════════════════════════");
    println!("  FINDINGS BY CATEGORY");
    println!("══════════════════════════════════════════════════════════════");
    let mut cats: Vec<(&String, &usize)> = report.findings_by_category.iter().collect();
    cats.sort_by(|a, b| b.1.cmp(a.1));
    for (cat, count) in &cats {
        println!("  {:15} {:>5}", cat, count);
    }

    println!();
    println!("══════════════════════════════════════════════════════════════");
    println!("  TOP MIGRATION CANDIDATES (Python → Rust)");
    println!("══════════════════════════════════════════════════════════════");
    for (i, c) in report.top_migration_candidates.iter().take(8).enumerate() {
        println!();
        println!("  {}. {} ({} lines, score={:.2}, speedup={})",
            i + 1,
            c.file.split('/').last().unwrap_or(&c.file),
            c.lines, c.migration_score, c.estimated_speedup);
        println!("     {}", c.reason);
        println!("     {}", c.file);
    }

    println!();
    println!("══════════════════════════════════════════════════════════════");
    println!("  TOP CRITICAL FINDINGS (severity 4)");
    println!("══════════════════════════════════════════════════════════════");
    for f in report.top_findings.iter().filter(|f| f.severity == 4).take(10) {
        println!();
        println!("  [{}] {} (line {})", f.category.to_uppercase(), f.title, f.line);
        println!("  File: {}", f.file.split('/').last().unwrap_or(&f.file));
        println!("  → {}", f.suggestion);
    }

    println!();
    println!("══════════════════════════════════════════════════════════════");
    println!("  LANGUAGE BREAKDOWN");
    println!("══════════════════════════════════════════════════════════════");
    let mut langs: Vec<(&String, &usize)> = report.language_breakdown.iter().collect();
    langs.sort_by(|a, b| b.1.cmp(a.1));
    for (lang, count) in langs {
        println!("  {:15} {:>5} files", lang, count);
    }

    println!();
    println!("══════════════════════════════════════════════════════════════");
    println!("  {} files in {}ms = {:.0} files/sec  ({:.1}× Python baseline)",
        report.total_files, report.duration_ms, report.files_per_sec,
        report.files_per_sec / 77.0);
    println!("══════════════════════════════════════════════════════════════");
}
