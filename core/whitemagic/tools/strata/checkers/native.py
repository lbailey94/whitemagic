import re
from pathlib import Path
from typing import List

from whitemagic.tools.strata.models import Finding, FindingSeverity
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.checkers import register


# ------------------------------------------------------------------
# Rust
# ------------------------------------------------------------------
@register
def check_rust(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Rust hygiene: unsafe blocks, unwrap/expect, todo!, debug prints, panic!, clone in loops.
    Skips test-only code gated by #[cfg(test)] or #[cfg(debug_assertions)].
    """
    for rs_file in file_index.files_by_extension(".rs"):
        try:
            content = file_index.read_text(rs_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        cfg_depth = 0
        unsafe_depth = 0
        loop_depth = 0
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track cfg(test) / cfg(debug_assertions) nesting
            if re.search(r'#\[cfg\s*\(\s*(test|debug_assertions)\s*\)\]', stripped):
                cfg_depth += 1
                continue
            if cfg_depth > 0:
                if stripped == "}":
                    cfg_depth -= 1
                continue

            if stripped.startswith("//"):
                continue

            # Strip string literal contents to avoid false positives
            # (e.g. code that searches for "todo!()" as a string)
            code_only = re.sub(r'"(?:[^"\\]|\\.)*"', '""', stripped)

            # Track braces for unsafe and loop scopes
            brace_delta = stripped.count("{") - stripped.count("}")

            # Track loop depth (for, while, loop)
            if re.search(r'\b(for|while|loop)\b', stripped):
                loop_depth += 1
            if loop_depth > 0 and brace_delta < 0:
                loop_depth = max(0, loop_depth + brace_delta)

            # Track unsafe depth
            if re.search(r'\bunsafe\b', stripped):
                unsafe_depth += 1
                # Check for SAFETY comment
                has_safety_comment = False
                for offset in (-3, -2, -1, 0, 1, 2, 3):
                    idx = i - 1 + offset
                    if 0 <= idx < len(lines):
                        if "SAFETY:" in lines[idx] or "// Safety:" in lines[idx]:
                            has_safety_comment = True
                            break
                if not has_safety_comment:
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="rust_unsafe",
                        file=str(rs_file.relative_to(project_path)),
                        line=i,
                        message="Unsafe block detected.",
                        suggestion="Document safety invariants and minimize unsafe scope."
                    ))
            if unsafe_depth > 0 and brace_delta < 0:
                unsafe_depth = max(0, unsafe_depth + brace_delta)

            # unwrap / expect inside unsafe blocks (double concern)
            for match in re.finditer(r'\.(unwrap|expect)\s*\(', stripped):
                if unsafe_depth > 0:
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="rust_panic_risk",
                        file=str(rs_file.relative_to(project_path)),
                        line=i,
                        message=f"Potential panic inside unsafe: .{match.group(1)}()",
                        suggestion="Avoid panicking inside unsafe; use match or return Result."
                    ))
                else:
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="rust_panic_risk",
                        file=str(rs_file.relative_to(project_path)),
                        line=i,
                        message=f"Potential panic: .{match.group(1)}()",
                        suggestion="Prefer ? operator or match for error handling."
                    ))

            # panic! / unreachable! macros
            for match in re.finditer(r'\b(panic!|unreachable!)\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="rust_panic_macro",
                    file=str(rs_file.relative_to(project_path)),
                    line=i,
                    message=f"Panic macro: {match.group(1)}().",
                    suggestion="Return errors instead of panicking in library code."
                ))

            # todo! / unimplemented!
            for match in re.finditer(r'\b(todo!|unimplemented!)\s*\(', code_only):
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category="rust_stub",
                    file=str(rs_file.relative_to(project_path)),
                    line=i,
                    message=f"Incomplete code: {match.group(1)} macro.",
                    suggestion="Implement before production."
                ))

            # clone() in loops (performance smell)
            if loop_depth > 0 and re.search(r'\.clone\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="rust_clone_in_loop",
                    file=str(rs_file.relative_to(project_path)),
                    line=i,
                    message=".clone() inside loop may hurt performance.",
                    suggestion="Consider using references, Cow, or pre-allocating."
                ))

            # debug print
            for match in re.finditer(r'\b(println!|eprintln!|dbg!)\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="rust_debug_print",
                    file=str(rs_file.relative_to(project_path)),
                    line=i,
                    message=f"Debug print: {match.group(1)} macro.",
                    suggestion="Use a logging crate (log, tracing) for production."
                ))

            # lock poisoning: .lock().unwrap() on Mutex / RwLock
            if re.search(r'\.(lock|read|write)\s*\(\s*\)\.unwrap\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="rust_lock_poisoning",
                    file=str(rs_file.relative_to(project_path)),
                    line=i,
                    message="Potential lock poisoning: .lock().unwrap() panics if the lock is poisoned.",
                    suggestion="Use .lock() and match on the Result, or call .unwrap_or_else() to handle poisoning."
                ))

            # floating point equality
            if re.search(r'\b\d+\.\d+(?:f32|f64)?\s*==\s*\d+\.\d+(?:f32|f64)?\b', stripped) or \
               re.search(r'\b\w+\s*==\s*\d+\.\d+(?:f32|f64)?\b', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="rust_float_equality",
                    file=str(rs_file.relative_to(project_path)),
                    line=i,
                    message="Direct equality comparison on floating-point values.",
                    suggestion="Use an epsilon comparison (approx_eq, ulps, or custom tolerance)."
                ))


# ------------------------------------------------------------------
# Go
# ------------------------------------------------------------------
@register
def check_go(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Go hygiene: ignored errors, bare panic, defer in loops, debug prints,
    context gaps, http.Get without timeout, ignored json.Marshal errors.
    """
    for go_file in file_index.files_by_extension(".go"):
        try:
            content = file_index.read_text(go_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        loop_depth = 0
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Track loop depth (for, range)
            brace_delta = stripped.count("{") - stripped.count("}")
            if re.search(r'\b(for|range)\b', stripped):
                loop_depth += 1
            if loop_depth > 0 and brace_delta < 0:
                loop_depth = max(0, loop_depth + brace_delta)

            # ignored error: _ = someFunc()
            if re.search(r'^\s*_\s*=\s*\w+\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="go_ignored_error",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message="Error return value is explicitly ignored.",
                    suggestion="Handle the error or document why it's safe to ignore."
                ))

            # bare panic
            if re.search(r'\bpanic\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="go_bare_panic",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message="Bare panic() detected.",
                    suggestion="Return errors up the call stack instead of panicking."
                ))

            # defer inside loop
            if loop_depth > 0 and re.search(r'\bdefer\s+', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="go_defer_in_loop",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message="defer inside loop may leak resources.",
                    suggestion="Refactor into a function or use explicit cleanup."
                ))

            # debug print
            for match in re.finditer(r'\b(fmt\.Println|fmt\.Printf|log\.Print|println)\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="go_debug_print",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message=f"Debug print: {match.group(1)}",
                    suggestion="Use structured logging (slog, zap, logrus) for production."
                ))

            # http.Get without timeout (naive: just flags http.Get)
            if re.search(r'\bhttp\.Get\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="go_http_no_timeout",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message="http.Get() without explicit timeout.",
                    suggestion="Use http.Client with a timeout or context.WithTimeout."
                ))

            # json.Marshal error ignored (naive: flag _ = json.Marshal)
            if re.search(r'\b_\s*,?\s*_?\s*[:]?=\s*json\.Marshal', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="go_ignored_marshal",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message="json.Marshal error is ignored.",
                    suggestion="Always check the error from json.Marshal."
                ))

        # Context propagation gaps: functions that start goroutines or handle HTTP
        # without accepting context.Context
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            # Function definition
            func_match = re.match(r'^func\s+\w+\s*\((.*)\)', stripped)
            if func_match:
                params = func_match.group(1)
                if "go func" in stripped or "goroutine" in stripped:
                    # If starting a goroutine without context
                    if "context.Context" not in params:
                        findings.append(Finding(
                            severity=FindingSeverity.INFO,
                            category="go_context_gap",
                            file=str(go_file.relative_to(project_path)),
                            line=i,
                            message="Goroutine started without context.Context for cancellation.",
                            suggestion="Pass context.Context for graceful shutdown and cancellation."
                        ))
                if "http.ResponseWriter" in params or "*http.Request" in params:
                    if "context.Context" not in params:
                        findings.append(Finding(
                            severity=FindingSeverity.INFO,
                            category="go_context_gap",
                            file=str(go_file.relative_to(project_path)),
                            line=i,
                            message="HTTP handler without context.Context parameter.",
                            suggestion="Accept context.Context for request-scoped values and deadlines."
                        ))

        # Second pass: SQL injection, resource leaks, hardcoded timeouts
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # SQL injection: string concatenation or Sprintf with SQL keywords
            sql_keywords = r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b'
            if re.search(sql_keywords, stripped, re.IGNORECASE):
                if re.search(r'["\']\s*\+|\+\s*["\']|fmt\.Sprintf|strconv\.Format', stripped):
                    findings.append(Finding(
                        severity=FindingSeverity.WARNING,
                        category="go_sql_injection",
                        file=str(go_file.relative_to(project_path)),
                        line=i,
                        message="Potential SQL injection: query built with string concatenation or formatting.",
                        suggestion="Use parameterized queries or a query builder."
                    ))

            # Resource leak: os.Open without defer Close
            if re.search(r'\bos\.Open\s*\(', stripped):
                has_cleanup = False
                for future in lines[i:min(len(lines), i+25)]:
                    if "defer" in future or ".Close()" in future:
                        has_cleanup = True
                        break
                if not has_cleanup:
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="go_resource_leak",
                        file=str(go_file.relative_to(project_path)),
                        line=i,
                        message="os.Open() without matching defer Close() may leak the file descriptor.",
                        suggestion="Add defer f.Close() after opening the file."
                    ))

            # Hardcoded timeout magic numbers
            if re.search(r'\b\d+\s*\*\s*time\.(Second|Millisecond|Minute|Hour)', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="go_hardcoded_timeout",
                    file=str(go_file.relative_to(project_path)),
                    line=i,
                    message="Hardcoded timeout value detected.",
                    suggestion="Extract timeout into a named constant or configurable parameter."
                ))


# ------------------------------------------------------------------
# C / C++
# ------------------------------------------------------------------
# Known debug-only headers to skip
_CPP_DEBUG_HEADERS = {"fixed_debug.h", "MacroDebug.h", "debug.h", "DebugMacros.h"}


@register
def check_cpp(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Basic C/C++ hygiene: unsafe functions, raw malloc, debug prints, TODOs."""
    for c_file in file_index.files_by_extension(".c", ".cpp", ".cc", ".h", ".hpp"):
        if c_file.name in _CPP_DEBUG_HEADERS:
            continue
        try:
            content = c_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                # TODO/FIXME comments
                if re.search(r'\bTODO\b|\bFIXME\b', stripped):
                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="cpp_todo",
                        file=str(c_file.relative_to(project_path)),
                        line=i,
                        message="TODO/FIXME comment found.",
                        suggestion="Address before production or track in issue tracker."
                    ))
                continue

            # unsafe C functions
            for match in re.finditer(r'\b(strcpy|strcat|gets|sprintf|scanf)\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="cpp_unsafe_function",
                    file=str(c_file.relative_to(project_path)),
                    line=i,
                    message=f"Unsafe function: {match.group(1)}() — buffer overflow risk.",
                    suggestion=f"Use {match.group(1)}_s, strlcpy, or safer alternatives."
                ))

            # malloc without free check (very naive — just flags malloc)
            for match in re.finditer(r'\bmalloc\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="cpp_raw_malloc",
                    file=str(c_file.relative_to(project_path)),
                    line=i,
                    message="Raw malloc() detected.",
                    suggestion="Use smart pointers (C++) or ensure matching free()."
                ))

            # debug printf
            for match in re.finditer(r'\b(printf|fprintf|perror|puts)\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="cpp_debug_print",
                    file=str(c_file.relative_to(project_path)),
                    line=i,
                    message=f"Debug print: {match.group(1)}()",
                    suggestion="Remove or guard with #ifdef DEBUG."
                ))
