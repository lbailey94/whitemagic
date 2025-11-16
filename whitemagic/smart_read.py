"""
Smart file reading utilities for token optimization.

Implements hybrid reading strategy:
- Small files (< 300 lines): Full read
- Large files: Context-targeted reading around specific lines
"""

from pathlib import Path
from typing import Optional, Tuple, List
import time


class SessionContext:
    """
    Track what we've already read this session.
    
    Prevents duplicate file reads and enables smart caching.
    """
    
    def __init__(self, max_age_seconds: int = 300):
        """
        Initialize session context.
        
        Args:
            max_age_seconds: Maximum age for cached content (default: 5 minutes)
        """
        self.max_age = max_age_seconds
        self.read_files = {}  # {path: (content, timestamp, line_count)}
        self.grep_results = {}  # {(query, path): (results, timestamp)}
        self.summaries = {}  # {key: (summary, timestamp)}
    
    def has_file(self, path: str) -> bool:
        """Check if we've read this file recently."""
        if path not in self.read_files:
            return False
        
        _, timestamp, _ = self.read_files[path]
        age = time.time() - timestamp
        return age < self.max_age
    
    def get_file(self, path: str) -> Optional[Tuple[str, int]]:
        """
        Get cached file content.
        
        Returns:
            Tuple of (content, line_count) or None if not cached/expired
        """
        if self.has_file(path):
            content, _, line_count = self.read_files[path]
            return (content, line_count)
        return None
    
    def cache_file(self, path: str, content: str, line_count: int):
        """Cache file content with timestamp."""
        self.read_files[path] = (content, time.time(), line_count)
    
    def cache_summary(self, key: str, summary: str):
        """Cache a summary with timestamp."""
        self.summaries[key] = (summary, time.time())
    
    def get_summary(self, key: str) -> Optional[str]:
        """Get cached summary if it exists and is fresh."""
        if key not in self.summaries:
            return None
        
        summary, timestamp = self.summaries[key]
        age = time.time() - timestamp
        
        if age < self.max_age:
            return summary
        
        # Expired, remove it
        del self.summaries[key]
        return None
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "files_cached": len(self.read_files),
            "summaries_cached": len(self.summaries),
            "total_entries": len(self.read_files) + len(self.summaries),
        }


def count_lines(file_path: Path) -> int:
    """Quickly count lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def read_file_smart(
    file_path: Path,
    session_ctx: Optional[SessionContext] = None,
    small_file_threshold: int = 300
) -> Tuple[str, dict]:
    """
    Smart file reading with session caching.
    
    Args:
        file_path: Path to file
        session_ctx: Optional session context for caching
        small_file_threshold: Files smaller than this read in full
        
    Returns:
        Tuple of (content, metadata dict)
    """
    file_path = Path(file_path)
    path_str = str(file_path)
    
    # Check session cache first
    if session_ctx and session_ctx.has_file(path_str):
        content, line_count = session_ctx.get_file(path_str)
        return content, {
            "source": "session_cache",
            "line_count": line_count,
            "full_read": True
        }
    
    # Read from disk
    try:
        content = file_path.read_text(encoding='utf-8')
        line_count = content.count('\n') + 1
        
        # Cache if session context provided
        if session_ctx:
            session_ctx.cache_file(path_str, content, line_count)
        
        return content, {
            "source": "disk",
            "line_count": line_count,
            "full_read": True,
            "is_small_file": line_count < small_file_threshold
        }
    
    except Exception as e:
        return "", {
            "source": "error",
            "error": str(e),
            "line_count": 0,
            "full_read": False
        }


def read_file_context(
    file_path: Path,
    target_line: int,
    before: int = 50,
    after: int = 50,
    small_file_threshold: int = 300,
    session_ctx: Optional[SessionContext] = None
) -> Tuple[str, dict]:
    """
    Read file with context around specific line.
    
    If file is small (< threshold), reads entire file.
    Otherwise reads [target_line - before : target_line + after].
    
    Args:
        file_path: Path to file
        target_line: Line number to center on (1-indexed)
        before: Lines before target
        after: Lines after target
        small_file_threshold: Threshold for full read
        session_ctx: Optional session context for caching
        
    Returns:
        Tuple of (content_with_line_numbers, metadata dict)
    """
    file_path = Path(file_path)
    path_str = str(file_path)
    
    # First, check total line count
    total_lines = count_lines(file_path)
    
    # Small file? Read everything
    if total_lines < small_file_threshold:
        content, meta = read_file_smart(file_path, session_ctx, small_file_threshold)
        
        # Add line numbers
        lines = content.split('\n')
        numbered = '\n'.join(f"{i+1:4d}→{line}" for i, line in enumerate(lines))
        
        meta["read_strategy"] = "full_small_file"
        meta["window_start"] = 1
        meta["window_end"] = total_lines
        
        return numbered, meta
    
    # Large file: context window reading
    start_line = max(1, target_line - before)
    end_line = min(total_lines, target_line + after)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []
            for i, line in enumerate(f, start=1):
                if start_line <= i <= end_line:
                    lines.append(f"{i:4d}→{line.rstrip()}")
                elif i > end_line:
                    break
        
        content = '\n'.join(lines)
        
        return content, {
            "source": "disk_context",
            "read_strategy": "context_window",
            "line_count": total_lines,
            "window_start": start_line,
            "window_end": end_line,
            "lines_read": len(lines),
            "target_line": target_line,
            "full_read": False
        }
    
    except Exception as e:
        return "", {
            "source": "error",
            "error": str(e),
            "read_strategy": "failed"
        }


def read_multiple_contexts(
    file_path: Path,
    target_lines: List[int],
    before: int = 50,
    after: int = 50,
    small_file_threshold: int = 300,
    session_ctx: Optional[SessionContext] = None
) -> Tuple[str, dict]:
    """
    Read multiple context windows from same file (optimized).
    
    If windows overlap or file is small, reads once and extracts ranges.
    
    Args:
        file_path: Path to file
        target_lines: List of line numbers to get context for
        before: Lines before each target
        after: Lines after each target
        small_file_threshold: Threshold for full read
        session_ctx: Optional session context
        
    Returns:
        Tuple of (combined_content, metadata dict)
    """
    if not target_lines:
        return "", {"error": "No target lines provided"}
    
    total_lines = count_lines(file_path)
    
    # Small file or many targets? Just read full file once
    if total_lines < small_file_threshold or len(target_lines) > 5:
        return read_file_smart(file_path, session_ctx, small_file_threshold)
    
    # Calculate merged ranges (avoid overlapping reads)
    ranges = []
    for target in sorted(target_lines):
        start = max(1, target - before)
        end = min(total_lines, target + after)
        ranges.append((start, end, target))
    
    # Merge overlapping ranges
    merged_ranges = []
    current_start, current_end, targets = ranges[0][0], ranges[0][1], [ranges[0][2]]
    
    for start, end, target in ranges[1:]:
        if start <= current_end + 1:  # Overlapping or adjacent
            current_end = max(current_end, end)
            targets.append(target)
        else:
            merged_ranges.append((current_start, current_end, targets))
            current_start, current_end, targets = start, end, [target]
    
    merged_ranges.append((current_start, current_end, targets))
    
    # Read merged ranges
    all_content = []
    total_lines_read = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_range_idx = 0
            if current_range_idx >= len(merged_ranges):
                return "", {"error": "No ranges to read"}
            
            start, end, targets = merged_ranges[current_range_idx]
            
            for i, line in enumerate(f, start=1):
                if i < start:
                    continue
                
                if start <= i <= end:
                    # Mark target lines
                    marker = " ← TARGET" if i in targets else ""
                    all_content.append(f"{i:4d}→{line.rstrip()}{marker}")
                    total_lines_read += 1
                
                if i >= end:
                    # Move to next range
                    current_range_idx += 1
                    if current_range_idx >= len(merged_ranges):
                        break
                    
                    # Add separator between ranges
                    if current_range_idx < len(merged_ranges):
                        all_content.append("\n... (lines omitted) ...\n")
                        start, end, targets = merged_ranges[current_range_idx]
        
        content = '\n'.join(all_content)
        
        return content, {
            "source": "disk_multi_context",
            "read_strategy": "merged_windows",
            "line_count": total_lines,
            "target_count": len(target_lines),
            "merged_ranges": len(merged_ranges),
            "lines_read": total_lines_read,
            "full_read": False
        }
    
    except Exception as e:
        return "", {
            "source": "error",
            "error": str(e),
            "read_strategy": "failed"
        }
