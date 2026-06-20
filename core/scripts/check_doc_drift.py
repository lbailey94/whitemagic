#!/usr/bin/env python3
"""Doc drift detector — ensures documentation stays in sync with reality.

Checks:
1. Garden count = 28 (matches grimoire/gana system)
2. Gana tool count = 28 in registry
3. Dispatch table tool count >= 400
4. Registry callable tool count >= 350
5. No stale references to archived directories
6. Version consistency (delegates to check_versions.py)
7. POLYGLOT_STATUS language list matches buildable reality

Run this in CI to catch doc/code drift early.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CORE = ROOT / "core"
ERRORS: list[str] = []
WARNINGS: list[str] = []


def error(msg: str) -> None:
    ERRORS.append(msg)
    print(f"  ❌ {msg}")


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"  ⚠️  {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


# ---------------------------------------------------------------------------
# 1. Garden count
# ---------------------------------------------------------------------------
def check_gardens() -> None:
    print("\n[1/7] Garden count...")
    try:
        from whitemagic.gardens import list_gardens

        gardens = list_gardens()
        count = len(gardens)
        if count != 28:
            error(f"Garden count = {count}, expected 28")
        else:
            ok(f"Garden count = {count}")
    except Exception as e:
        error(f"Could not list gardens: {e}")


# ---------------------------------------------------------------------------
# 2. Gana tool count
# ---------------------------------------------------------------------------
def check_gana_tools() -> None:
    print("\n[2/7] Gana tool count...")
    try:
        from whitemagic.tools.registry import TOOL_REGISTRY, ToolCategory

        gana = [t for t in TOOL_REGISTRY if t.category == ToolCategory.GANA]
        count = len(gana)
        if count != 28:
            error(f"Gana tools = {count}, expected 28")
        else:
            ok(f"Gana tools = {count}")
    except Exception as e:
        error(f"Could not count Gana tools: {e}")


# ---------------------------------------------------------------------------
# 3. Dispatch table count
# ---------------------------------------------------------------------------
def check_dispatch_table() -> None:
    print("\n[3/7] Dispatch table count...")
    try:
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        count = len(DISPATCH_TABLE)
        if count < 400:
            error(f"Dispatch tools = {count}, expected >= 400")
        else:
            ok(f"Dispatch tools = {count}")
    except Exception as e:
        error(f"Could not count dispatch table: {e}")


# ---------------------------------------------------------------------------
# 4. Registry callable tool count
# ---------------------------------------------------------------------------
def check_registry_tools() -> None:
    print("\n[4/7] Registry callable tool count...")
    try:
        from whitemagic.tools.tool_surface import get_surface_counts

        counts = get_surface_counts()
        callable_tools = counts.get("callable_tools", 0)
        if callable_tools < 350:
            error(f"Callable tools = {callable_tools}, expected >= 350")
        else:
            ok(f"Callable tools = {callable_tools}")
    except Exception as e:
        error(f"Could not count registry tools: {e}")


# ---------------------------------------------------------------------------
# 5. No stale references to archived directories
# ---------------------------------------------------------------------------
def check_no_stale_refs() -> None:
    print("\n[5/7] Stale directory references...")
    stale_patterns = [
        (r"\barchive/\b", "archive/"),
        (r"\blegacy/\b", "legacy/"),
        (r"\bwhitemagic-site/\b", "whitemagic-site/"),
    ]
    checked = [
        ROOT / "README.md",
        ROOT / "core" / "README.md",
        ROOT / "core" / "docs" / "POLYGLOT_STATUS.md",
        ROOT / "core" / "docs" / "STRATEGIC_ROADMAP.md",
    ]
    found_any = False
    for doc in checked:
        if not doc.exists():
            continue
        text = doc.read_text()
        for pattern, name in stale_patterns:
            for match in re.finditer(pattern, text):
                line_num = text[: match.start()].count("\n") + 1
                warn(f"{doc.relative_to(ROOT)}:{line_num} references removed '{name}'")
                found_any = True
    if not found_any:
        ok("No stale directory references in key docs")


# ---------------------------------------------------------------------------
# 6. Version consistency
# ---------------------------------------------------------------------------
def check_versions() -> None:
    print("\n[6/7] Version consistency...")
    script = CORE / "scripts" / "check_versions.py"
    if not script.exists():
        warn("check_versions.py not found — skipping")
        return
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        error("Version mismatch detected (see check_versions.py output)")
        for line in result.stdout.splitlines()[-10:]:
            print(f"    {line}")
    else:
        ok("All version references consistent")


# ---------------------------------------------------------------------------
# 7. Tool-count drift across canonical docs
# ---------------------------------------------------------------------------
def check_tool_count_drift() -> None:
    """Scan canonical docs for ANY claimed tool counts and flag drift.

    Catches phrasings like:
      - "453 callable tools"
      - "425 dispatch tools" / "425 dispatch entries"
      - "311 individual tools" (legacy classic-mode wording)
      - "all 425 dispatch tools"  (mid-sentence)
    Reports every occurrence whose number disagrees with the live registry.
    """
    print("\n[7/8] Tool-count drift across canonical docs...")
    docs = [
        ROOT / "AI_PRIMARY.md",
        ROOT / "AGENTS.md",
        ROOT / "SYSTEM_MAP.md",
        ROOT / "docs" / "public" / "SYSTEM_MAP.md",
        ROOT / "README.md",
    ]
    try:
        from whitemagic.tools.tool_surface import get_surface_counts

        counts = get_surface_counts()
        actual_callable = counts.get("callable_tools", 0)
        actual_dispatch = counts.get("dispatch_tools", 0)
    except Exception as e:
        warn(f"Could not load surface counts: {e}")
        return

    callable_pat = re.compile(r"(\d+)\s+callable\s+tools", re.IGNORECASE)
    # "dispatch tools" or "dispatch entries" or "individual tools" all describe
    # the same underlying number (live dispatch table size in non-PRAT mode).
    dispatch_pat = re.compile(
        r"(\d+)\s+(?:dispatch\s+tools|dispatch\s+entries|individual\s+tools)",
        re.IGNORECASE,
    )

    drift_count = 0
    checked_count = 0
    for doc in docs:
        if not doc.exists():
            continue
        text = doc.read_text()
        rel = doc.relative_to(ROOT)
        for match in callable_pat.finditer(text):
            checked_count += 1
            claimed = int(match.group(1))
            if claimed != actual_callable:
                line_num = text[: match.start()].count("\n") + 1
                error(f"{rel}:{line_num} claims {claimed} callable tools, actual = {actual_callable}")
                drift_count += 1
        for match in dispatch_pat.finditer(text):
            checked_count += 1
            claimed = int(match.group(1))
            if claimed != actual_dispatch:
                line_num = text[: match.start()].count("\n") + 1
                error(f"{rel}:{line_num} claims {claimed} dispatch tools, actual = {actual_dispatch}")
                drift_count += 1

    if drift_count == 0:
        ok(f"All {checked_count} tool-count references match reality ({actual_callable} callable / {actual_dispatch} dispatch)")


# ---------------------------------------------------------------------------
# 8. Test-count drift across canonical docs
# ---------------------------------------------------------------------------
def check_test_count_consistency() -> None:
    """Scan canonical docs for claimed test-pass counts and flag drift.

    The drift bug we hit on 2026-04-27: ``AGENTS.md`` claimed 2,154
    passing tests, ``SYSTEM_MAP.md`` claimed 2,063, the actual baseline
    was 2,179. None of the previous checks caught it because they only
    looked at tool counts.

    Strategy here: find every ``N passing tests`` / ``N tests passing``
    reference and require it to be clearly labeled as either the frozen
    v22.2.0 release baseline or the current local audit baseline. The
    check does NOT shell out to pytest (too slow); it enforces the
    canonical Option C wording policy.
    """
    print("\n[8/9] Test-count consistency across canonical docs...")
    docs = [
        ROOT / "AI_PRIMARY.md",
        ROOT / "AGENTS.md",
        ROOT / "SYSTEM_MAP.md",
        ROOT / "docs" / "public" / "SYSTEM_MAP.md",
        ROOT / "README.md",
    ]

    # Match e.g. "2,216 passing tests", "2243 tests passing", "2,063 tests passing"
    # but NOT "2,243 passed" because that phrase appears in copy-pasted pytest
    # summary blocks where short-term staleness is acceptable.
    pat = re.compile(
        r"(\d[\d,]*)\s+(?:passing\s+tests|tests\s+passing|tests passing)",
        re.IGNORECASE,
    )

    release_baseline = 2216
    current_audit_baseline = 1470
    release_markers = ("release baseline", "v22.2.0 release", "v22.2 release", "v22.2.1 release", "v22.2.2 release", "v22.2.3 release", "v22.3.0 release", "v22.4.0 release")
    current_markers = ("current local audit", "current audit baseline", "live audit baseline", "v22.2.1 release", "v22.2.2 release", "v22.2.3 release", "v22.3.0 release", "v22.4.0 release")
    seen: dict[str, list[tuple[str, int, str]]] = {}
    for doc in docs:
        if not doc.exists():
            continue
        text = doc.read_text()
        rel = str(doc.relative_to(ROOT))
        lines = text.splitlines()
        for match in pat.finditer(text):
            count = int(match.group(1).replace(",", ""))
            line_num = text[: match.start()].count("\n") + 1
            line_text = lines[line_num - 1].lower()
            seen.setdefault(rel, []).append((f"line {line_num}", count, line_text))

    all_counts: list[int] = []
    for entries in seen.values():
        for _, count, _ in entries:
            all_counts.append(count)

    if not all_counts:
        ok("No test-count references found in canonical docs (skipped)")
        return

    drift_count = 0
    for doc_rel, entries in sorted(seen.items()):
        for where, count, line_text in entries:
            is_release = count == release_baseline and any(marker in line_text for marker in release_markers)
            is_current = count == current_audit_baseline and any(marker in line_text for marker in current_markers)
            if not (is_release or is_current):
                error(
                    f"{doc_rel}:{where} claims {count:,} tests without an accepted Option C baseline label"
                )
                drift_count += 1

    if drift_count == 0:
        ok(
            f"All {len(all_counts)} test-count references use Option C "
            f"({release_baseline:,} release / {current_audit_baseline:,} current audit)"
        )
        return


# ---------------------------------------------------------------------------
# 9. POLYGLOT_STATUS buildable languages
# ---------------------------------------------------------------------------
def check_polyglot_status() -> None:
    print("\n[9/9] POLYGLOT_STATUS build claims...")
    status_file = CORE / "docs" / "POLYGLOT_STATUS.md"
    if not status_file.exists():
        warn("POLYGLOT_STATUS.md not found")
        return

    text = status_file.read_text()

    # Check for claim that Go builds clean in whitemagic-go
    if "whitemagic-go && go build" in text and "polyglot/whitemagic-go" in text:
        # This is OK if we already updated the doc
        if "archived" in text.lower():
            ok("POLYGLOT_STATUS notes archived whitemagic-go")
        else:
            warn("POLYGLOT_STATUS may still reference archived polyglot/whitemagic-go/")

    # Check that mesh_aux is documented
    if "mesh_aux" not in text:
        warn("POLYGLOT_STATUS does not mention core/mesh_aux/")
    else:
        ok("POLYGLOT_STATUS references core/mesh_aux")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("WhiteMagic Doc Drift Detector")
    print("=" * 60)

    # Ensure we can import whitemagic
    os.environ.setdefault("WM_SILENT_INIT", "1")
    sys.path.insert(0, str(CORE))

    check_gardens()
    check_gana_tools()
    check_dispatch_table()
    check_registry_tools()
    check_no_stale_refs()
    check_versions()
    check_tool_count_drift()
    check_test_count_consistency()
    check_polyglot_status()

    print("\n" + "=" * 60)
    if ERRORS:
        print(f"RESULT: {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)")
        return 1
    elif WARNINGS:
        print(f"RESULT: 0 errors, {len(WARNINGS)} warning(s)")
        return 0
    else:
        print("RESULT: All checks passed — documentation is in sync.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
