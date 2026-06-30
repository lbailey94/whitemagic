"""
strata
Analyze codebases using AGENTS.md directives.
Detects structural stubs, archive drift, config inconsistencies, and dead code.
"""

import json
from pathlib import Path
from typing import Optional

# Import checkers package to trigger auto-registration
from whitemagic.tools.strata.config import load_config
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

# Re-export for backward compatibility
__all__ = ["Strata", "Finding", "FindingSeverity", "main"]


class Strata:
    """Analyze a codebase and report issues based on AGENTS.md directives."""

    def __init__(
        self,
        project_path: str,
        disabled_categories: list[str] | None = None,
        baseline_path: str | None = None,
        since_ref: str | None = None,
        diff_base: str | None = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.agents_md: str | None = None
        self.readme_md: str | None = None
        self.findings: list[Finding] = []
        self.config = load_config(self.project_path)
        self.severity_overrides: dict[str, FindingSeverity] = {}
        self._parse_config()
        extra_skip = set(self.config.get("skip", []))
        self.file_index = FileIndex(self.project_path, extra_skip=extra_skip or None)
        self.disabled_categories: set = set(disabled_categories or [])
        self.disabled_categories.update(self.config.get("disable", []))
        self.baseline: set = set()
        self.since_ref_files: set | None = None
        self.diff_base_lines: dict[str, set] | None = None
        if since_ref:
            self.since_ref_files = self._changed_files_since(since_ref)
        if diff_base:
            self.diff_base_lines = self._changed_lines_since(diff_base)
        if baseline_path:
            self._load_baseline(baseline_path)
        self._load_agents_md()
        self._load_readme_md()

    def _parse_config(self) -> None:
        """Parse severity overrides from config."""
        overrides = self.config.get("severity", {})
        for category, sev_str in overrides.items():
            try:
                self.severity_overrides[category] = FindingSeverity(sev_str.lower())
            except ValueError:
                continue

    def _load_agents_md(self) -> None:
        """Load AGENTS.md if present."""
        agents_path = self.project_path / "AGENTS.md"
        if agents_path.exists():
            self.agents_md = agents_path.read_text(encoding="utf-8")

    def _load_readme_md(self) -> None:
        """Load README.md if present."""
        readme_path = self.project_path / "README.md"
        if readme_path.exists():
            self.readme_md = readme_path.read_text(encoding="utf-8")

    def _load_baseline(self, path: str):
        """Load a baseline file to suppress known findings."""
        baseline_file = Path(path)
        if baseline_file.exists():
            data = json.loads(baseline_file.read_text(encoding="utf-8"))
            for entry in data:
                key = (
                    entry.get("category"),
                    entry.get("file"),
                    entry.get("line"),
                    entry.get("message"),
                )
                self.baseline.add(key)

    def _changed_files_since(self, ref: str) -> set | None:
        """Return set of file paths changed since the given git ref."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", ref, "--"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None
            files = set()
            for line in result.stdout.strip().splitlines():
                if line:
                    files.add(line)
            return files
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def _changed_lines_since(self, ref: str) -> dict[str, set] | None:
        """Return mapping of file paths to sets of changed line numbers since the given git ref."""
        import re as _re
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "-U0", ref, "--"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

        changed_lines: dict[str, set] = {}
        current_file: str | None = None
        for line in result.stdout.splitlines():
            if line.startswith("diff --git "):
                current_file = None
            elif line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("@@") and current_file is not None:
                match = _re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    start = int(match.group(1))
                    count = int(match.group(2)) if match.group(2) else 1
                    if count > 0:
                        changed_lines.setdefault(current_file, set()).update(
                            range(start, start + count)
                        )
        return changed_lines

    def _is_suppressed(self, finding: Finding, content: str) -> bool:
        """Check if a finding is suppressed by an inline comment on the same or previous line."""
        if finding.line is None:
            return False
        lines = content.splitlines()
        # Check previous, current, and next line
        for offset in (-1, 0, 1):
            check_line = finding.line + offset
            if check_line < 1 or check_line > len(lines):
                continue
            line_text = lines[check_line - 1]
            # Check for generic suppression
            if "# strata: ignore" in line_text:
                # Check for category-specific suppression
                if f"# strata: ignore[{finding.category}]" in line_text:
                    return True
                # Check that it's not a different category-specific suppression
                import re as _re

                if _re.search(r"# strata: ignore\[", line_text):
                    continue
                return True
        return False

    def analyze(
        self, parallel: bool = False, incremental: bool = False
    ) -> list[Finding]:
        """Run all analysis checks."""
        self.findings = []

        if not self.agents_md:
            self.findings.append(
                Finding(
                    severity=FindingSeverity.WARNING,
                    category="agents.md",
                    file=str(self.project_path),
                    line=None,
                    message="No AGENTS.md found. Consider creating one for agent context.",
                    suggestion="Create AGENTS.md with project context, conventions, and safety rules.",
                )
            )
            return self.findings

        self.file_index.incremental = incremental

        # Run all registered plugin checkers
        from whitemagic.tools.strata.checkers import get_checkers

        checkers = get_checkers()

        if parallel:
            from concurrent.futures import ThreadPoolExecutor

            def _run_checker(checker) -> list[Finding]:
                local_findings: list[Finding] = []
                checker(self.project_path, self.file_index, local_findings)
                return local_findings

            with ThreadPoolExecutor() as executor:
                results = executor.map(_run_checker, checkers)
            for local_findings in results:
                self.findings.extend(local_findings)
        else:
            for checker in checkers:
                checker(self.project_path, self.file_index, self.findings)

        # Apply config severity overrides
        self._apply_severity_overrides()

        # Apply post-check filters
        self._apply_filters()

        # Apply since-ref filter (only show findings in changed files)
        if self.since_ref_files is not None:
            self.findings = [
                f
                for f in self.findings
                if f.line is None or f.file is None or f.file in self.since_ref_files
            ]

        # Apply diff-base filter (only show findings on changed lines)
        if self.diff_base_lines is not None:
            self.findings = [
                f
                for f in self.findings
                if f.line is not None
                and f.file is not None
                and f.file in self.diff_base_lines
                and f.line in self.diff_base_lines[f.file]
            ]

        # Deduplicate findings across source and release/build copies
        self._deduplicate_source_copies()

        self.file_index.save_hash_cache()
        return self.findings

    def _apply_severity_overrides(self) -> None:
        """Adjust finding severities based on pyproject.toml config."""
        if not self.severity_overrides:
            return
        for finding in self.findings:
            override = self.severity_overrides.get(finding.category)
            if override is not None:
                finding.severity = override

    def _apply_filters(self) -> None:
        """Filter findings based on disabled categories, inline suppressions, and baseline."""
        filtered: list[Finding] = []
        file_cache: dict[str, str] = {}

        for finding in self.findings:
            # Skip disabled categories
            if finding.category in self.disabled_categories:
                continue

            # Skip baseline findings
            if self.baseline:
                key = (finding.category, finding.file, finding.line, finding.message)
                if key in self.baseline:
                    continue

            # Check inline suppression for file-based findings
            if finding.line is not None and finding.file:
                file_path = self.project_path / finding.file
                if file_path.exists():
                    content = file_cache.get(str(file_path))
                    if content is None:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        file_cache[str(file_path)] = content
                    if self._is_suppressed(finding, content):
                        continue

            filtered.append(finding)

        self.findings = filtered

    def _deduplicate_source_copies(self) -> None:
        """If the same finding appears in both src/ and release/build/dist, keep only src/."""
        source_dirs = {"src", "lib", "source", "sources", "pkg"}
        build_dirs = {"release", "build", "dist", "out", "target", "deploy"}

        # Group findings by normalized key (category, message, line, path_without_first_dir)
        groups: dict[tuple, list[Finding]] = {}
        for finding in self.findings:
            if finding.file is None or finding.line is None:
                continue
            parts = finding.file.split("/")
            if len(parts) < 2:
                continue
            normalized = (
                finding.category,
                finding.message,
                finding.line,
                "/".join(parts[1:]),
            )
            groups.setdefault(normalized, []).append(finding)

        to_remove: set = set()
        for normalized, items in groups.items():
            if len(items) < 2:
                continue
            source_finding = None
            build_findings = []
            for f in items:
                first_dir = f.file.split("/")[0]
                if first_dir in source_dirs:
                    source_finding = f
                elif first_dir in build_dirs:
                    build_findings.append(f)
            if source_finding and build_findings:
                for bf in build_findings:
                    to_remove.add(id(bf))

        self.findings = [f for f in self.findings if id(f) not in to_remove]

    def _report_sarif(self) -> str:
        """Generate a SARIF v2.1.0 report."""
        runs = [
            {
                "tool": {
                    "driver": {
                        "name": "STRATA",
                        "informationUri": "https://github.com/example/strata",
                        "rules": [],
                    }
                },
                "results": [],
            }
        ]
        rules = {}
        for f in self.findings:
            rule_id = f.category
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": rule_id,
                    "shortDescription": {"text": f.message},
                }
            result = {
                "ruleId": rule_id,
                "message": {"text": f.message},
                "level": f.severity.value,
                "locations": [],
            }
            if f.line is not None:
                result["locations"].append(
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.file},
                            "region": {"startLine": f.line},
                        }
                    }
                )
            runs[0]["results"].append(result)
        runs[0]["tool"]["driver"]["rules"] = list(rules.values())
        return json.dumps(
            {
                "version": "2.1.0",
                "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
                "runs": runs,
            },
            indent=2,
        )

    def _report_html(self) -> str:
        """Generate a self-contained HTML report."""
        severity_counts = {"error": 0, "warning": 0, "info": 0}
        for f in self.findings:
            severity_counts[f.severity.value] = (
                severity_counts.get(f.severity.value, 0) + 1
            )

        rows = []
        for f in self.findings:
            loc = f"{f.file}:{f.line}" if f.line is not None else f.file
            suggestion = f.suggestion or ""
            rows.append(
                f'<tr data-severity="{f.severity.value}">'
                f'<td><span class="badge {f.severity.value}">{f.severity.value.upper()}</span></td>'
                f"<td>{f.category}</td>"
                f"<td><code>{loc}</code></td>"
                f"<td>{f.message}</td>"
                f"<td>{suggestion}</td>"
                f"</tr>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>STRATA Report — {self.project_path.name}</title>
<style>
  :root {{ --bg: #0d1117; --fg: #c9d1d9; --muted: #8b949e; --border: #30363d;
          --error: #f85149; --warning: #d29922; --info: #58a6ff; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--fg); margin: 0; padding: 2rem; line-height: 1.5; }}
  h1 {{ margin: 0 0 0.5rem; }}
  .meta {{ color: var(--muted); margin-bottom: 1.5rem; }}
  .stats {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; }}
  .stat {{ background: var(--border); padding: 0.75rem 1rem; border-radius: 6px; min-width: 80px; text-align: center; }}
  .stat strong {{ display: block; font-size: 1.5rem; }}
  .filters {{ margin-bottom: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }}
  button {{ background: var(--border); color: var(--fg); border: 1px solid var(--border); padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; }}
  button.active {{ border-color: var(--info); }}
  input[type="search"] {{ background: var(--bg); color: var(--fg); border: 1px solid var(--border); padding: 0.4rem 0.6rem; border-radius: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
  th, td {{ text-align: left; padding: 0.6rem 0.5rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
  th {{ color: var(--muted); font-weight: 600; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #161b22; padding: 0.15rem 0.3rem; border-radius: 4px; font-size: 0.85rem; }}
  .badge {{ display: inline-block; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
  .badge.error {{ background: rgba(248,81,73,0.15); color: var(--error); }}
  .badge.warning {{ background: rgba(210,153,34,0.15); color: var(--warning); }}
  .badge.info {{ background: rgba(88,166,255,0.15); color: var(--info); }}
  tr:hover {{ background: rgba(48,54,61,0.4); }}
</style>
</head>
<body>
<h1>STRATA Report</h1>
<div class="meta">{self.project_path.name} &middot; {len(self.findings)} finding(s)</div>
<div class="stats">
  <div class="stat"><strong style="color:var(--error)">{severity_counts["error"]}</strong>Errors</div>
  <div class="stat"><strong style="color:var(--warning)">{severity_counts["warning"]}</strong>Warnings</div>
  <div class="stat"><strong style="color:var(--info)">{severity_counts["info"]}</strong>Info</div>
</div>
<div class="filters">
  <button class="active" onclick="filter('all')">All</button>
  <button onclick="filter('error')">Errors</button>
  <button onclick="filter('warning')">Warnings</button>
  <button onclick="filter('info')">Info</button>
  <input type="search" id="search" placeholder="Search findings..." oninput="search()">
</div>
<table>
<thead>
<tr><th>Severity</th><th>Category</th><th>Location</th><th>Message</th><th>Suggestion</th></tr>
</thead>
<tbody id="findings">
{"".join(rows)}
</tbody>
</table>
<script>
function filter(sev) {{
  document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('#findings tr').forEach(tr => {{
    tr.style.display = (sev === 'all' || tr.dataset.severity === sev) ? '' : 'none';
  }});
  search();
}}
function search() {{
  const q = document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('#findings tr').forEach(tr => {{
    if (tr.style.display === 'none') return;
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

    def report(
        self, format: str = "text", stratify: bool = False, context: bool = False
    ) -> str:
        """Generate a formatted report."""
        if stratify:
            from whitemagic.tools.strata.stratigraphy import StratigraphyReport

            return StratigraphyReport(self.project_path, self.findings).render()

        if format == "json":
            return json.dumps(
                [
                    {
                        "severity": f.severity.value,
                        "category": f.category,
                        "file": f.file,
                        "line": f.line,
                        "message": f.message,
                        "suggestion": f.suggestion,
                    }
                    for f in self.findings
                ],
                indent=2,
            )

        if format == "sarif":
            return self._report_sarif()

        if format == "html":
            return self._report_html()

        lines = [
            f"STRATA Report: {self.project_path.name}",
            "=" * 60,
            f"AGENTS.md: {'Found' if self.agents_md else 'NOT FOUND'}",
            f"Total findings: {len(self.findings)}",
            "",
        ]

        severity_counts = {}
        for f in self.findings:
            severity_counts[f.severity.value] = (
                severity_counts.get(f.severity.value, 0) + 1
            )

        for sev in ["error", "warning", "info"]:
            count = severity_counts.get(sev, 0)
            if count > 0:
                lines.append(f"  {sev.upper()}: {count}")

        lines.append("")

        enricher = None
        if context:
            from whitemagic.tools.strata.context import ContextEnricher

            enricher = ContextEnricher(self.project_path)

        for f in self.findings:
            icon = (
                "🔴"
                if f.severity == FindingSeverity.ERROR
                else "🟡"
                if f.severity == FindingSeverity.WARNING
                else "🔵"
            )
            loc = f":{f.line}" if f.line else ""
            ctx = ""
            if enricher and f.line is not None and f.file:
                scope = enricher.enrich(f.file, f.line)
                if scope:
                    ctx = f" in {scope}"
            lines.append(f"{icon} [{f.category}] {f.file}{loc}{ctx}")
            lines.append(f"   {f.message}")
            if f.suggestion:
                lines.append(f"   💡 {f.suggestion}")
            lines.append("")

        return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="STRATA — analyze codebases using AGENTS.md"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Run code analysis (default)"
    )
    analyze_parser.add_argument(
        "path", nargs="?", default=".", help="Project path to analyze"
    )
    analyze_parser.add_argument(
        "--format",
        choices=["text", "json", "sarif", "html"],
        default="text",
        help="Output format",
    )
    analyze_parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with non-zero code if errors found",
    )
    analyze_parser.add_argument(
        "--disable",
        action="append",
        default=[],
        help="Disable a check category (can be used multiple times)",
    )
    analyze_parser.add_argument(
        "--baseline",
        default=".strata-baseline.json",
        help="Path to baseline file for suppressing known findings",
    )
    analyze_parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate a baseline from current findings and exit",
    )
    analyze_parser.add_argument(
        "--stratify",
        action="store_true",
        help="Group findings by geological age layers via git blame",
    )
    analyze_parser.add_argument(
        "--since-ref",
        default=None,
        help="Only analyze files changed since the given git ref",
    )
    analyze_parser.add_argument(
        "--diff-base",
        default=None,
        help="Only report findings on lines changed since the given git ref",
    )
    analyze_parser.add_argument(
        "--survey",
        action="store_true",
        help="Fast surface survey using file metadata and git history",
    )
    analyze_parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for file changes and re-run analysis",
    )
    analyze_parser.add_argument(
        "--parallel", action="store_true", help="Run checkers in parallel using threads"
    )
    analyze_parser.add_argument(
        "--context",
        action="store_true",
        help="Show enclosing function/class context in text reports",
    )
    analyze_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Skip unchanged files based on content hash cache",
    )
    analyze_parser.add_argument(
        "--list-checks",
        action="store_true",
        help="List all registered checkers and their categories, then exit",
    )

    arch_parser = subparsers.add_parser(
        "archaeology",
        aliases=["arch"],
        help="Code Archaeology Kit — geological git history analysis",
    )
    arch_sub = arch_parser.add_subparsers(
        dest="arch_command", help="Archaeology subcommands"
    )

    excavate_p = arch_sub.add_parser(
        "excavate", help="Show code that existed in a time layer"
    )
    excavate_p.add_argument("path", nargs="?", default=".", help="Project path")
    excavate_p.add_argument(
        "--layer", required=True, help="Time layer: YYYY, YYYY-QN, or YYYY-MM"
    )
    excavate_p.add_argument(
        "--file", default=None, help="Filter to files containing this substring"
    )

    fossil_p = arch_sub.add_parser("fossil", help="Timeline of a file's evolution")
    fossil_p.add_argument("path", nargs="?", default=".", help="Project path")
    fossil_p.add_argument("--file", required=True, help="File path to trace")
    fossil_p.add_argument("--commits", type=int, default=20, help="Max commits to show")

    extinction_p = arch_sub.add_parser(
        "extinction", help="Find deleted code still referenced"
    )
    extinction_p.add_argument("path", nargs="?", default=".", help="Project path")

    comp_p = arch_sub.add_parser(
        "composition", help="Analyze codebase composition by contributor"
    )
    comp_p.add_argument("path", nargs="?", default=".", help="Project path")
    comp_p.add_argument(
        "--top", type=int, default=10, help="Number of top contributors"
    )

    temper_p = arch_sub.add_parser(
        "temper", help="Measure how 'heated' a file's history is"
    )
    temper_p.add_argument("path", nargs="?", default=".", help="Project path")
    temper_p.add_argument(
        "--file", default=None, help="Filter to files containing this substring"
    )
    temper_p.add_argument("--top", type=int, default=10, help="Number of top files")

    import sys

    subcommands = {"analyze", "archaeology", "arch"}
    if any(arg in subcommands for arg in sys.argv[1:] if not arg.startswith("-")):
        args = parser.parse_args()
    else:
        args = analyze_parser.parse_args()
        args.command = "analyze"

    if args.command == "analyze" and getattr(args, "list_checks", False):
        import inspect
        import re as _re

        from whitemagic.tools.strata.checkers import get_checkers

        print("Registered STRATA checkers:")
        print("-" * 60)
        for checker in get_checkers():
            name = checker.__name__
            doc = (
                (checker.__doc__ or "").strip().splitlines()[0]
                if checker.__doc__
                else ""
            )
            try:
                source = inspect.getsource(checker)
                categories = sorted(
                    set(_re.findall(r'category\s*=\s*"([^"]+)"', source))
                )
            except (OSError, TypeError):
                categories = []
            cat_str = f"  categories: {', '.join(categories)}" if categories else ""
            print(f"  {name:<40s} {doc}")
            if cat_str:
                print(f"  {'':40s} {cat_str}")
        return

    if args.command in ("archaeology", "arch"):
        from whitemagic.tools.strata.archaeology import archaeology_main

        archaeology_main(args)
        return

    if args.command == "analyze":
        if args.survey:
            from whitemagic.tools.strata.survey import SurveyReport

            print(SurveyReport(Path(args.path)).render())
            return

        def _run() -> None:
            baseline_path = args.baseline if Path(args.baseline).exists() else None
            arch = Strata(
                args.path,
                disabled_categories=args.disable,
                baseline_path=baseline_path,
                since_ref=args.since_ref,
                diff_base=args.diff_base,
            )
            arch.analyze(parallel=args.parallel, incremental=args.incremental)

            if args.generate_baseline:
                baseline_data = [
                    {
                        "category": f.category,
                        "file": f.file,
                        "line": f.line,
                        "message": f.message,
                    }
                    for f in arch.findings
                ]
                baseline_file = Path(args.baseline)
                baseline_file.write_text(
                    json.dumps(baseline_data, indent=2), encoding="utf-8"
                )
                print(
                    f"Baseline written to {baseline_file} ({len(baseline_data)} findings)"
                )
                return

            print(
                arch.report(
                    format=args.format, stratify=args.stratify, context=args.context
                )
            )

            if args.fail_on_error:
                errors = [
                    f for f in arch.findings if f.severity == FindingSeverity.ERROR
                ]
                if errors:
                    exit(1)

        if args.watch:
            from whitemagic.tools.strata.watch import FileWatcher

            watcher = FileWatcher(Path(args.path))
            watcher.run(_run)
        else:
            _run()


if __name__ == "__main__":
    main()
