#!/usr/bin/env python3
"""
Fast File Audit Tool - Powered by Rust

Uses parallel Rust processing for 10-100x faster file comprehension.
Perfect for auditing large directories with minimal token usage.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict
import json

try:
    import whitemagic_rs
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("⚠️  Rust module not available. Install with: cd whitemagic-rs && maturin develop --release")


def fast_audit(directory: str, pattern: str = "*.md", max_files: int = 1000) -> List:
    """
    Perform fast audit of directory using Rust parallel processing.
    
    Args:
        directory: Directory to audit
        pattern: File pattern (e.g., "*.md", "*.py")
        max_files: Maximum files to process
        
    Returns:
        List of FileInfo objects with metadata
    """
    if not RUST_AVAILABLE:
        raise RuntimeError("Rust module required for fast audit")
    
    start = time.perf_counter()
    results = whitemagic_rs.audit_directory(directory, pattern, max_files)
    duration = time.perf_counter() - start
    
    print(f"⚡ Audited {len(results)} files in {duration:.3f}s")
    print(f"   Speed: {len(results)/duration:.0f} files/second")
    
    return results


def generate_audit_report(results: List, output_file: str = None) -> str:
    """
    Generate comprehensive audit report from Rust results.
    
    Token-efficient: Summarizes large amounts of data concisely.
    """
    total_files = len(results)
    total_lines = sum(f.lines for f in results)
    total_words = sum(f.words for f in results)
    total_size = sum(f.size for f in results)
    
    report = f"""# Fast Audit Report
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Powered by: Rust (parallel processing)

## Summary Statistics
- **Total Files**: {total_files}
- **Total Lines**: {total_lines:,}
- **Total Words**: {total_words:,}
- **Total Size**: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)
- **Avg Lines/File**: {total_lines/total_files:.0f}
- **Avg Words/File**: {total_words/total_files:.0f}

## File Breakdown
| File | Lines | Words | Size |
|------|-------|-------|------|
"""
    
    # Sort by lines (descending)
    sorted_results = sorted(results, key=lambda f: f.lines, reverse=True)
    
    for file_info in sorted_results[:20]:  # Top 20
        name = Path(file_info.path).name
        report += f"| {name[:40]:40} | {file_info.lines:5} | {file_info.words:6} | {file_info.size:7} |\n"
    
    if total_files > 20:
        report += f"\n... and {total_files - 20} more files\n"
    
    report += f"""
## Content Previews

"""
    
    # Add previews of largest files
    for i, file_info in enumerate(sorted_results[:5]):
        report += f"### {i+1}. {Path(file_info.path).name}\n"
        report += f"**Summary**: {file_info.summary}\n\n"
    
    if output_file:
        Path(output_file).write_text(report)
        print(f"📄 Report saved to {output_file}")
    
    return report


def compare_with_python(directory: str, pattern: str = "*.md") -> Dict:
    """
    Compare Rust vs Python performance for file auditing.
    
    Demonstrates the 10-100x speedup.
    """
    print("\n🏁 Performance Comparison: Rust vs Python")
    print("=" * 60)
    
    # Rust timing
    rust_start = time.perf_counter()
    rust_results = whitemagic_rs.audit_directory(directory, pattern, 1000)
    rust_time = time.perf_counter() - rust_start
    
    print(f"\n⚡ Rust (parallel):")
    print(f"   Time: {rust_time:.3f}s")
    print(f"   Files: {len(rust_results)}")
    print(f"   Speed: {len(rust_results)/rust_time:.0f} files/sec")
    
    # Python timing (sequential)
    python_start = time.perf_counter()
    python_count = 0
    total_lines = 0
    
    for file_path in Path(directory).rglob(pattern):
        if python_count >= 1000:
            break
        try:
            content = file_path.read_text()
            lines = len(content.splitlines())
            total_lines += lines
            python_count += 1
        except:
            pass
    
    python_time = time.perf_counter() - python_start
    
    print(f"\n🐍 Python (sequential):")
    print(f"   Time: {python_time:.3f}s")
    print(f"   Files: {python_count}")
    print(f"   Speed: {python_count/python_time:.0f} files/sec")
    
    speedup = python_time / rust_time if rust_time > 0 else 0
    
    print(f"\n🚀 Speedup: {speedup:.1f}x faster with Rust!")
    
    return {
        'rust_time': rust_time,
        'python_time': python_time,
        'speedup': speedup,
        'files_processed': len(rust_results)
    }


def main():
    """CLI interface for fast audit tool."""
    if len(sys.argv) < 2:
        print("Usage: python fast_audit.py <directory> [pattern] [output_file]")
        print("\nExample:")
        print("  python fast_audit.py docs/plans '*.md' audit_report.md")
        sys.exit(1)
    
    directory = sys.argv[1]
    pattern = sys.argv[2] if len(sys.argv) > 2 else "*.md"
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not RUST_AVAILABLE:
        print("❌ Rust module required. Install with:")
        print("   cd whitemagic-rs && maturin develop --release")
        sys.exit(1)
    
    print(f"📂 Auditing directory: {directory}")
    print(f"🔍 Pattern: {pattern}")
    
    # Perform fast audit
    results = fast_audit(directory, pattern)
    
    # Generate report
    report = generate_audit_report(results, output_file)
    
    if not output_file:
        print("\n" + report)
    
    # Performance comparison
    print("\n" + "=" * 60)
    compare_with_python(directory, pattern)


if __name__ == "__main__":
    main()
