#!/usr/bin/env python3
"""
WhiteMagic LOC Counter - Safe analysis of codebase composition
"""

import os
from pathlib import Path
from collections import defaultdict

# Language extensions mapping
LANG_MAP = {
    '.py': 'Python',
    '.rs': 'Rust',
    '.go': 'Go',
    '.zig': 'Zig',
    '.ex': 'Elixir',
    '.exs': 'Elixir',
    '.hs': 'Haskell',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.mojo': 'Mojo',
    '.jl': 'Julia',
    '.koka': 'Koka',
}

# Directories to exclude
EXCLUDE_DIRS = {
    '_archives', 'monte_carlo_output', 'node_modules', 'target',
    'build', 'deps', '__pycache__', '.git', 'dist', '.venv',
    '.mypy_cache', '.pytest_cache', '.ruff_cache', '.claude',
    '.koka', '.devcontainer'
}

def count_loc(directory: Path) -> dict:
    """Count lines of code by language."""
    stats = defaultdict(lambda: {'files': 0, 'loc': 0})
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in LANG_MAP:
                lang = LANG_MAP[ext]
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                    stats[lang]['files'] += 1
                    stats[lang]['loc'] += lines
                except Exception:
                    pass
    
    return dict(stats)

def generate_report(stats: dict) -> str:
    """Generate ASCII bar chart report."""
    total_files = sum(s['files'] for s in stats.values())
    total_loc = sum(s['loc'] for s in stats.values())
    
    # Sort by LOC descending
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['loc'], reverse=True)
    
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append("║          WHITEMAGIC CODEBASE COMPOSITION (whitemagicdev)         ║")
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    lines.append(f"║  Total: {total_files:,} files | {total_loc:,} lines of code{'':>17}║")
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    lines.append("")
    
    # Bar chart
    max_loc = max(s['loc'] for s in stats.values()) if stats else 0
    bar_width = 40
    
    for lang, data in sorted_stats:
        pct = (data['loc'] / total_loc * 100) if total_loc else 0
        bar_len = int((data['loc'] / max_loc) * bar_width) if max_loc else 0
        bar = '█' * bar_len
        lines.append(f"{lang:12} │{bar:<{bar_width}}│ {pct:5.1f}% ({data['loc']:,} LOC, {data['files']} files)")
    
    lines.append("")
    lines.append("═" * 70)
    lines.append("PYTHON vs POLYGLOT BREAKDOWN")
    lines.append("═" * 70)
    
    python_loc = stats.get('Python', {}).get('loc', 0)
    python_files = stats.get('Python', {}).get('files', 0)
    polyglot_loc = total_loc - python_loc
    polyglot_files = total_files - python_files
    
    lines.append(f"  Python:     {python_loc:,} LOC ({python_loc/total_loc*100:5.1f}%) | {python_files:,} files")
    lines.append(f"  Polyglot:   {polyglot_loc:,} LOC ({polyglot_loc/total_loc*100:5.1f}%) | {polyglot_files:,} files")
    lines.append("")
    
    # Per-language breakdown
    lines.append("═" * 70)
    lines.append("LANGUAGE DETAILS")
    lines.append("═" * 70)
    
    for lang, data in sorted_stats:
        lines.append(f"  {lang:12}: {data['loc']:>8,} LOC  │  {data['files']:>4} files  │  {data['loc']/total_loc*100:5.1f}%")
    
    return '\n'.join(lines)

if __name__ == '__main__':
    root = Path('/home/lucas/Desktop/whitemagicdev')
    stats = count_loc(root)
    report = generate_report(stats)
    print(report)
    
    # Save to file
    output_path = root / 'reports' / 'loc_analysis.md'
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        f.write("# WhiteMagic LOC Analysis\n\n")
        f.write(f"```\n{report}\n```\n")
    print(f"\n\nReport saved to: {output_path}")
