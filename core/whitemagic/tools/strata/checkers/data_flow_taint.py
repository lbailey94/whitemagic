"""Data flow taint tracking checker — uses code graph data_flow edges for source→sink analysis.

Detects:
- User input (source) flowing to SQL queries (sink) without sanitization
- User input flowing to command execution
- User input flowing to HTML output (XSS)
- User input flowing to file operations (path traversal)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

logger = logging.getLogger(__name__)

# Source patterns — entry points for untrusted data
_SOURCE_PATTERNS = [
    (r"request\.(?:GET|POST|get|post|args|form|data|json|cookies|headers)\b", "HTTP request data"),
    (r"input\s*\(", "stdin input"),
    (r"sys\.argv\b", "command-line argument"),
    (r"os\.environ\b(?:\.get\(|\[)", "environment variable"),
    (r"open\s*\([^)]*['\"]r['\"]", "file read"),
    (r"socket\.(?:recv|recvfrom)\b", "socket input"),
]

# Sink patterns — dangerous operations
_SINK_PATTERNS = [
    (r"(?:cursor\.)?execute\s*\(", "SQL query", FindingSeverity.ERROR),
    (r"os\.(?:system|popen|execv?e?|spawn)\b", "command execution", FindingSeverity.ERROR),
    (r"subprocess\.(?:run|call|Popen|check_output)\b", "subprocess execution", FindingSeverity.ERROR),
    (r"eval\s*\(", "eval execution", FindingSeverity.ERROR),
    (r"exec\s*\(", "exec execution", FindingSeverity.ERROR),
    (r"(?:open|file)\s*\([^)]*['\"]w", "file write", FindingSeverity.WARNING),
    (r"(?:render_template|Response|HttpResponse|make_response)\s*\(", "HTML response", FindingSeverity.WARNING),
    (r"(?:innerHTML|dangerouslySetInnerHTML)\b", "DOM injection", FindingSeverity.WARNING),
]

# Sanitizer patterns — functions that neutralize taint
_SANITIZER_PATTERNS = [
    r"escape\s*\(",
    r"sanitize\s*\(",
    r"clean\s*\(",
    r"validate\s*\(",
    r"parameterized\s*\(",
    r"\.strip\s*\(",
    r"html\.escape\s*\(",
    r"bleach\.clean\s*\(",
    r"markupsafe\.escape\s*\(",
    r"shlex\.quote\s*\(",
]


@register
def check_data_flow_taint(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect taint flow from user input sources to dangerous sinks.

    Uses code graph data_flow edges when available for cross-file tracking.
    Falls back to intra-file pattern matching when graph is not built.
    """
    # Try code graph first for cross-file data flow
    graph_findings = _check_graph_data_flow()
    if graph_findings:
        findings.extend(graph_findings)
        return

    # Fallback: intra-file pattern matching
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        _check_intra_file_taint(rel, content, findings)


def _check_graph_data_flow() -> list[Finding]:
    """Use code graph data_flow edges for cross-file taint tracking."""
    findings: list[Finding] = []
    try:
        from whitemagic.core.intelligence.code_structure_graph import (
            get_code_structure_graph,
        )
        g = get_code_structure_graph()
        if g.stats()["node_count"] == 0:
            return findings

        # Find data_flow edges
        data_flow_edges = [
            e for e in g._edges.values() if e.edge_type == "data_flow"
        ]
        if not data_flow_edges:
            return findings

        # Build adjacency for data flow
        flow_adj: dict[str, list[str]] = {}
        for edge in data_flow_edges:
            flow_adj.setdefault(edge.source_id, []).append(edge.target_id)

        # Find source nodes (functions that receive user input)
        source_nodes: set[str] = set()
        for node_id, node in g._nodes.items():
            if node.node_type != "function":
                continue
            # Check if function name suggests it handles user input
            name_lower = node.name.lower()
            if any(pat in name_lower for pat in ("handle", "process", "receive", "parse", "view", "endpoint", "route")):
                source_nodes.add(node_id)

        # Find sink nodes (functions that perform dangerous operations)
        sink_nodes: set[str] = set()
        for node_id, node in g._nodes.items():
            if node.node_type != "function":
                continue
            name_lower = node.name.lower()
            if any(pat in name_lower for pat in ("execute", "query", "run", "eval", "render", "save", "write")):
                sink_nodes.add(node_id)

        # Trace paths from sources to sinks (BFS, max 4 hops)
        for source in source_nodes:
            visited = {source}
            queue = [(source, [source])]
            while queue:
                current, path = queue.pop(0)
                if len(path) > 4:
                    continue
                if current in sink_nodes and len(path) > 1:
                    node = g._nodes.get(current)
                    source_node = g._nodes.get(source)
                    if node and source_node:
                        path_names = [g._nodes.get(nid).name for nid in path if g._nodes.get(nid)]
                        findings.append(Finding(
                            severity=FindingSeverity.WARNING,
                            category="data_flow.taint",
                            file=node.file_path,
                            line=node.line_start,
                            message=f"Taint flow: {source_node.name} flows to {node.name}. Path: {' -> '.join(path_names[:4])}. Verify that input is properly sanitized.",
                            suggestion="Ensure all user input is sanitized before reaching this sink.",
                        ))
                    break
                for neighbor in flow_adj.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
    except Exception:
        logger.debug("Ignored Exception in data_flow_taint.py:149")
    return findings


def _check_intra_file_taint(
    file_path: str, content: str, findings: list[Finding]
):
    """Check for taint flow within a single file using pattern matching."""
    lines = content.splitlines()

    # Find source lines
    source_lines: list[tuple[int, str, str]] = []  # (line_num, match, var_hint)
    for i, line in enumerate(lines, 1):
        for pattern, label in _SOURCE_PATTERNS:
            if re.search(pattern, line):
                # Try to extract variable name being assigned
                var_match = re.search(r"(\w+)\s*=\s*" + pattern, line)
                var = var_match.group(1) if var_match else ""
                source_lines.append((i, label, var))
                break

    # Find sink lines
    sink_lines: list[tuple[int, str, FindingSeverity, str]] = []
    for i, line in enumerate(lines, 1):
        for pattern, label, severity in _SINK_PATTERNS:
            if re.search(pattern, line):
                sink_lines.append((i, label, severity, line.strip()))
                break

    # Check if any variable from source appears in sink
    for src_line, src_label, var in source_lines:
        if not var:
            continue
        for sink_line, sink_label, severity, sink_text in sink_lines:
            if var in sink_text:
                # Check for sanitizers between source and sink
                has_sanitizer = False
                for check_line in range(src_line, sink_line):
                    for san_pattern in _SANITIZER_PATTERNS:
                        if re.search(san_pattern, lines[check_line - 1]):
                            has_sanitizer = True
                            break
                    if has_sanitizer:
                        break

                if not has_sanitizer:
                    findings.append(Finding(
                        severity=severity,
                        category="data_flow.taint",
                        file=file_path,
                        line=sink_line,
                        message=f"Unsanitized {src_label} flows to {sink_label}: Variable '{var}' from {src_label} (line {src_line}) reaches {sink_label} (line {sink_line}) without sanitization.",
                        suggestion=f"Sanitize the input before passing it to {sink_label}.",
                    ))
