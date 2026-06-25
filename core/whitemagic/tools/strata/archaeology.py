"""
Code Archaeology Kit — geological analysis of git history.

Subcommands:
  excavate   — Show code that existed in a specific time layer
  fossil     — Timeline of a file's evolution
  extinction — Find deleted code still referenced
  composition — Analyze who contributed what
  temper     — Measure how "heated" a file's history is
"""

import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def _git(args: List[str], cwd: Path, timeout: int = 30) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def _git_json(args: List[str], cwd: Path, timeout: int = 30) -> List[dict]:
    """Run git log with JSON format."""
    result = subprocess.run(
        ["git", "log", "--format=%H|%an|%ae|%at|%s"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git log failed: {result.stderr}")
    entries = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            entries.append({
                "hash": parts[0],
                "author": parts[1],
                "email": parts[2],
                "timestamp": int(parts[3]),
                "subject": parts[4],
            })
    return entries


# ------------------------------------------------------------------
# excavate — show code that existed in a time layer
# ------------------------------------------------------------------

def excavate(project_path: Path, layer: str, file_filter: Optional[str] = None) -> str:
    """Show files and their content as they existed in a given time layer.

    Layer formats:
      YYYY        — entire year
      YYYY-QN     — quarter (Q1-Q4)
      YYYY-MM     — month
      YYYY-WNN    — ISO week
    """
    since, until = _parse_layer(layer)
    # Find the last commit before 'until' that touched each file
    files = _git(["ls-files"], project_path).strip().splitlines()
    if file_filter:
        files = [f for f in files if file_filter in f]

    lines = [
        f"⛏️  STRATA Excavation — Layer: {layer}",
        f"   Period: {since.isoformat()} → {until.isoformat()}",
        f"   Files:  {len(files)}",
        "",
    ]

    found = 0
    for f in files[:50]:  # Limit to avoid terminal flood
        try:
            # Get the last commit in this layer that touched the file
            blame = _git(
                ["log", f"--since={since.isoformat()}", f"--until={until.isoformat()}",
                 "--format=%H", "-n1", "--", f],
                project_path, timeout=10
            ).strip()
            if blame:
                found += 1
                lines.append(f"📄 {f}")
                # Show author of that version
                author = _git(["show", "-s", "--format=%an (%ar)", blame], project_path, timeout=5).strip()
                lines.append(f"   Last touched: {author}")
        except RuntimeError:
            continue

    lines.append("")
    lines.append(f"Found {found} files with activity in layer {layer}")
    return "\n".join(lines)


def _parse_layer(layer: str) -> Tuple[datetime, datetime]:
    """Parse a layer string into (since, until) datetimes."""
    import re as _re
    if _re.match(r'^\d{4}$', layer):
        year = int(layer)
        return (datetime(year, 1, 1, tzinfo=timezone.utc),
                datetime(year + 1, 1, 1, tzinfo=timezone.utc))
    if _re.match(r'^\d{4}-Q[1-4]$', layer):
        year, q = int(layer[:4]), int(layer[3])
        start_month = (q - 1) * 3 + 1
        end_month = q * 3 + 1
        end_year = year
        if end_month > 12:
            end_month = 1
            end_year += 1
        return (datetime(year, start_month, 1, tzinfo=timezone.utc),
                datetime(end_year, end_month, 1, tzinfo=timezone.utc))
    if _re.match(r'^\d{4}-\d{2}$', layer):
        year, month = int(layer[:4]), int(layer[5:7])
        if month == 12:
            return (datetime(year, 12, 1, tzinfo=timezone.utc),
                    datetime(year + 1, 1, 1, tzinfo=timezone.utc))
        return (datetime(year, month, 1, tzinfo=timezone.utc),
                datetime(year, month + 1, 1, tzinfo=timezone.utc))
    raise ValueError(f"Unknown layer format: {layer}. Use YYYY, YYYY-QN, YYYY-MM")


# ------------------------------------------------------------------
# fossil — timeline of a file's evolution
# ------------------------------------------------------------------

def fossil(project_path: Path, file_path: str, max_commits: int = 20) -> str:
    """Show the evolution timeline of a single file."""
    entries = _git_json(
        [f"-n{max_commits}", "--follow", "--", file_path],
        project_path, timeout=15
    )

    if not entries:
        return f"No history found for {file_path}"

    lines = [
        f"🦴 STRATA Fossil — {file_path}",
        f"   Commits: {len(entries)}",
        "",
    ]

    for entry in entries:
        dt = datetime.fromtimestamp(entry["timestamp"], tz=timezone.utc)
        lines.append(f"[{entry['hash'][:7]}] {dt.strftime('%Y-%m-%d')}")
        lines.append(f"   {entry['author']}: {entry['subject']}")
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------
# extinction — find deleted code still referenced
# ------------------------------------------------------------------

def extinction(project_path: Path) -> str:
    """Find symbols (functions, classes) that were deleted but are still referenced."""
    # Get recently deleted files
    deleted_raw = _git(
        ["log", "--diff-filter=D", "--summary", "--name-only", "-n50"],
        project_path, timeout=15
    )
    deleted_files = set()
    for line in deleted_raw.splitlines():
        line = line.strip()
        if line.startswith("delete mode "):
            continue
        if line and " => " not in line:
            deleted_files.add(line)

    lines = [
        "💀 STRATA Extinction Report",
        f"   Recently deleted files: {len(deleted_files)}",
        "",
    ]

    # Extract function/class names from deleted files (via git show)
    extinct_symbols: Set[str] = set()
    for f in list(deleted_files)[:20]:
        try:
            content = _git(["show", f"HEAD:{f}"], project_path, timeout=5)
            # Naive extraction: def/class lines
            for match in re.finditer(r'^(?:def|class|function|fn|pub fn)\s+([A-Za-z_]\w*)', content, re.MULTILINE):
                extinct_symbols.add(match.group(1))
        except RuntimeError:
            continue

    if not extinct_symbols:
        lines.append("No extinct symbols found in recently deleted files.")
        return "\n".join(lines)

    # Search current codebase for references to extinct symbols
    alive_files = _git(["ls-files"], project_path).strip().splitlines()
    references: Dict[str, List[str]] = defaultdict(list)

    for f in alive_files:
        if not any(f.endswith(ext) for ext in ['.py', '.js', '.ts', '.rs', '.go', '.java', '.c', '.cpp', '.zig']):
            continue
        try:
            content = (project_path / f).read_text(encoding="utf-8", errors="ignore")
            for symbol in extinct_symbols:
                if symbol in content and symbol not in f:
                    # Count occurrences
                    count = content.count(symbol)
                    if count > 0:
                        references[symbol].append(f"{f} ({count}x)")
        except (OSError, UnicodeDecodeError):
            continue

    if not references:
        lines.append("No references to extinct symbols found. Good riddance.")
        return "\n".join(lines)

    for symbol, refs in sorted(references.items(), key=lambda x: -len(x[1]))[:15]:
        lines.append(f"🪦 {symbol} (extinct, but referenced in {len(refs)} files)")
        for ref in refs[:5]:
            lines.append(f"   → {ref}")
        if len(refs) > 5:
            lines.append(f"   ... and {len(refs) - 5} more")
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------
# composition — contributor analysis
# ------------------------------------------------------------------

def composition(project_path: Path, top_n: int = 10) -> str:
    """Analyze codebase composition by contributor."""
    log = _git_json(["--no-merges"], project_path, timeout=30)

    if not log:
        return "No git history found."

    author_commits = Counter()
    author_lines = Counter()
    author_files: Dict[str, Set[str]] = defaultdict(set)
    monthly_commits: Dict[str, int] = defaultdict(int)

    for entry in log:
        author_commits[entry["author"]] += 1
        dt = datetime.fromtimestamp(entry["timestamp"], tz=timezone.utc)
        monthly_commits[dt.strftime("%Y-%m")] += 1

    # For line counts, use git blame on a sample of files
    files = _git(["ls-files"], project_path).strip().splitlines()
    sample_files = files[:30]  # Sample for speed
    for f in sample_files:
        try:
            blame = _git(["blame", "--porcelain", f], project_path, timeout=5)
            for line in blame.splitlines():
                if line.startswith("author "):
                    author_lines[line[7:]] += 1
                if line.startswith("filename "):
                    fname = line[9:]
                    # Find the author from previous line... this is approximate
                    # A simpler approach: just count files touched
                    pass
        except RuntimeError:
            continue

    lines = [
        "🧬 STRATA Composition Report",
        f"   Total commits: {len(log)}",
        f"   Contributors:  {len(author_commits)}",
        f"   Files sampled: {len(sample_files)}",
        "",
        "By commits:",
    ]

    total_commits = sum(author_commits.values())
    for author, count in author_commits.most_common(top_n):
        pct = (count / total_commits) * 100
        bar = "█" * int(pct / 5)
        lines.append(f"   {author:20s} {count:4d} ({pct:5.1f}%) {bar}")

    lines.append("")
    lines.append("Activity by month:")
    for month in sorted(monthly_commits.keys())[-12:]:
        count = monthly_commits[month]
        bar = "█" * min(count, 20)
        lines.append(f"   {month} {count:3d} {bar}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# temper — measure how heated a file's history is
# ------------------------------------------------------------------

def temper(project_path: Path, file_path: Optional[str] = None, top_n: int = 10) -> str:
    """Measure how 'heated' a file's history is — revert wars, force pushes, rapid changes."""
    # Get all commits with subjects
    log = _git_json(["--no-merges"], project_path, timeout=30)

    # Detect revert patterns
    revert_keywords = ["revert", "undo", "roll back", "revert", "un-do", "reverse"]
    fixup_keywords = ["fixup", "amend", "fix", "patch", "hotfix"]
    conflict_keywords = ["merge", "conflict", "resolve"]

    file_heat: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "commits": 0, "reverts": 0, "fixups": 0, "conflicts": 0,
        "authors": 0, "first": 0, "last": 0
    })

    author_sets: Dict[str, Set[str]] = defaultdict(set)

    for entry in log:
        subject = entry["subject"].lower()
        ts = entry["timestamp"]

        # Find files touched by this commit
        try:
            files = _git(
                ["diff-tree", "--no-commit-id", "--name-only", "-r", entry["hash"]],
                project_path, timeout=5
            ).strip().splitlines()
        except RuntimeError:
            continue

        for f in files:
            if file_path and file_path not in f:
                continue
            h = file_heat[f]
            h["commits"] += 1
            h["last"] = max(h["last"], ts)
            if h["first"] == 0:
                h["first"] = ts
            else:
                h["first"] = min(h["first"], ts)
            author_sets[f].add(entry["author"])

            if any(kw in subject for kw in revert_keywords):
                h["reverts"] += 1
            if any(kw in subject for kw in fixup_keywords):
                h["fixups"] += 1
            if any(kw in subject for kw in conflict_keywords):
                h["conflicts"] += 1

    # Calculate heat score
    scored = []
    now = datetime.now(tz=timezone.utc).timestamp()
    for f, h in file_heat.items():
        if h["commits"] < 2:
            continue
        age_days = max(1, (now - h["first"]) / 86400)
        commit_rate = h["commits"] / age_days
        churn = h["reverts"] + h["fixups"] + h["conflicts"]
        author_count = len(author_sets[f])
        # Heat formula: high commit rate + churn + many authors = hot
        heat = (commit_rate * 10) + (churn * 5) + (author_count * 2)
        scored.append((f, heat, h, author_count))

    scored.sort(key=lambda x: -x[1])

    lines = [
        "🌡️  STRATA Temper Report",
        "   Heat = commit frequency + churn (reverts/fixups/conflicts) + author count",
        "",
    ]

    if file_path:
        lines.append(f"Filtered to: {file_path}")
        lines.append("")

    for f, heat, h, authors in scored[:top_n]:
        age_days = max(1, (now - h["first"]) / 86400)
        bar = "🔥" * min(int(heat / 5), 10)
        lines.append(f"{bar} {f}")
        lines.append(f"   Heat: {heat:.1f} | Commits: {h['commits']} | Authors: {authors}")
        lines.append(f"   Reverts: {h['reverts']} | Fixups: {h['fixups']} | Conflicts: {h['conflicts']}")
        lines.append(f"   Age: {age_days:.0f} days | Rate: {h['commits']/age_days:.2f}/day")
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI integration helpers
# ------------------------------------------------------------------

def archaeology_main(args) -> None:
    """Entry point for archaeology subcommands."""
    project_path = Path(args.path).resolve()
    if not (project_path / ".git").exists():
        print("❌ Not a git repository. Archaeology requires git history.")
        return

    if args.arch_command == "excavate":
        print(excavate(project_path, args.layer, args.file))
    elif args.arch_command == "fossil":
        print(fossil(project_path, args.file, args.commits))
    elif args.arch_command == "extinction":
        print(extinction(project_path))
    elif args.arch_command == "composition":
        print(composition(project_path, args.top))
    elif args.arch_command == "temper":
        print(temper(project_path, args.file, args.top))
    else:
        print(f"Unknown archaeology command: {args.arch_command}")
