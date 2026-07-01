#!/usr/bin/env python3
"""
🐍 The Great Python Census 🐍
=============================
Scans the entire WhiteMagic filesystem to categorize, date, and audit all Python files.

Outputs:
1. reports/python_census_v1.md (Human readable)
2. reports/python_census.json (Machine readable)
"""

import os
import json
import time
import ast
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import logging
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ROOT = Path(".").resolve()
IGNORE_DIRS = {
    # VCS / IDE
    ".git",
    ".idea",
    ".vscode",
    ".claude",

    # Python
    ".venv",
    "venv",
    "temp_venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # Runtime / local data (do not scan by default)
    "memory",
    "data",
    "logs",
    "reports",
    "tmp",
    ".whitemagic",
    ".whitemagic_audit",
    "windsurf_conversations",

    # Common build caches (polyglot)
    "node_modules",
    "target",
    "dist",
    "build",
    "_build",
    "deps",
    "dist-newstyle",
    "mojo-env",
    ".pixi",
    ".zig-cache",
    "zig-out",
}
REPORT_DIR = PROJECT_ROOT / "reports"

class FileCategory:
    CORE = "Core"
    GANA = "Gana"
    SCRIPT = "Script"
    TEST = "Test"
    LEGACY = "Legacy"
    CONFIG = "Config"
    UNKNOWN = "Unknown"

def get_category(path: Path) -> str:
    path_str = str(path)
    if "whitemagic/core" in path_str:
        if "ganas" in path_str: return FileCategory.GANA
        return FileCategory.CORE
    if "tests" in path_str or "test_" in path.name: return FileCategory.TEST
    if "scripts" in path_str: return FileCategory.SCRIPT
    if "legacy" in path_str or "archive" in path_str: return FileCategory.LEGACY
    if "config" in path_str: return FileCategory.CONFIG
    if path.parent == PROJECT_ROOT: return FileCategory.SCRIPT # Root scripts
    return FileCategory.UNKNOWN

def analyze_file(path: Path):
    try:
        stat = path.stat()
        mtime = stat.st_mtime
        size_bytes = stat.st_size
        
        # Read content for line count and AST check
        try:
            content = path.read_text(errors='ignore')
            lines = len(content.splitlines())
            
            # Basic AST check for class/function counts
            try:
                tree = ast.parse(content)
                classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            except SyntaxError:
                classes = 0
                functions = 0
                
        except Exception:
            lines = 0
            classes = 0
            functions = 0
            
        return {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "category": get_category(path),
            "mtime": mtime,
            "mtime_str": datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
            "age_days": (time.time() - mtime) / 86400,
            "size_bytes": size_bytes,
            "lines": lines,
            "classes": classes,
            "functions": functions
        }
    except Exception as e:
        logger.debug("Error analyzing %s: %s", path, e)
        return None

def generate_report(files_data):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Aggregation
    by_category = defaultdict(list)
    total_lines = 0
    total_files = len(files_data)
    
    for f in files_data:
        by_category[f["category"]].append(f)
        total_lines += f["lines"]

    # Generate Markdown
    lines = []
    lines.append(f"# 🐍 The Great Python Census (v1)")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total Files**: {total_files}")
    lines.append(f"**Total Lines of Code**: {total_lines}")
    lines.append("")
    
    # 1. Summary Table
    lines.append("## 1. Domain Breakdown")
    lines.append("| Category | Files | Lines | Avg Age (Days) |")
    lines.append("|----------|-------|-------|----------------|")
    
    for cat, items in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        cat_lines = sum(i["lines"] for i in items)
        avg_age = sum(i["age_days"] for i in items) / len(items) if items else 0
        lines.append(f"| {cat} | {len(items)} | {cat_lines} | {avg_age:.1f} |")
        
    # 2. Freshness Heatmap (Recent files)
    lines.append("\n## 2. Hotspots (Edited in last 7 days)")
    recent = sorted([f for f in files_data if f["age_days"] < 7], key=lambda x: x["mtime"], reverse=True)
    if recent:
        lines.append("| File | Modified | Category |")
        lines.append("|------|----------|----------|")
        for f in recent[:20]: # Top 20
            lines.append(f"| `{f['path']}` | {f['mtime_str']} | {f['category']} |")
    else:
        lines.append("*No files edited in the last 7 days.*")

    # 3. The Forgotten (Oldest files, excluding legacy/archive)
    lines.append("\n## 3. The Forgotten (Oldest Active Code)")
    active_files = [f for f in files_data if f["category"] not in (FileCategory.LEGACY, FileCategory.TEST)]
    oldest = sorted(active_files, key=lambda x: x["mtime"])
    
    if oldest:
        lines.append("| File | Modified | Age (Days) | Category |")
        lines.append("|------|----------|------------|----------|")
        for f in oldest[:20]:
            lines.append(f"| `{f['path']}` | {f['mtime_str']} | {f['age_days']:.1f} | {f['category']} |")

    # 4. Complexity Outliers (Largest files)
    lines.append("\n## 4. Behemoths (Largest Files)")
    largest = sorted(files_data, key=lambda x: x["lines"], reverse=True)
    lines.append("| File | Lines | Classes | Functions |")
    lines.append("|------|-------|---------|-----------|")
    for f in largest[:15]:
        lines.append(f"| `{f['path']}` | {f['lines']} | {f['classes']} | {f['functions']} |")

    # Write MD
    md_path = REPORT_DIR / "python_census_v1.md"
    md_path.write_text("\n".join(lines))
    logger.debug("✅ Report generated: %s", md_path)
    
    # Write JSON
    json_path = REPORT_DIR / "python_census.json"
    json_path.write_text(json.dumps(files_data, indent=2))
    logger.debug("✅ Data dumped: %s", json_path)

def main():
    logger.debug("🔍 Scanning codebase...")
    files_data = []
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.endswith(".egg-info")]
        
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                data = analyze_file(path)
                if data:
                    files_data.append(data)
    
    logger.debug(f"✅ Scanned {len(files_data)} Python files.")
    generate_report(files_data)

if __name__ == "__main__":
    main()
