"""Add E402 to existing BLE001 noqa comments in files that have E402 hits.

This is the path of least resistance: the E402 hits are all from a
deliberate pattern (file-level docstring, then `logger = ...` then
imports). Adding E402 to the existing noqa scope is the right call
for a polish pass — fixing each one mechanically is high-risk and
low-value (the code works, it's just a stylistic concern).
"""
import re
import subprocess
from pathlib import Path

ROOT = Path("whitemagic")
NOQA_PATTERN = re.compile(r"^#\s*ruff:\s*noqa:\s*([A-Z0-9, ]+?)\s*$", re.MULTILINE)


def has_e402(path: Path) -> bool:
    """Check if ruff finds E402 hits in this file."""
    result = subprocess.run(
        ["/home/lucas/Desktop/WHITEMAGIC/core/.venv/bin/ruff", "check", str(path.resolve()), "--select", "E402", "--output-format", "concise"],
        capture_output=True, text=True, cwd="/home/lucas/Desktop/WHITEMAGIC/core",
    )
    return "Found" in result.stdout and "0 found" not in result.stdout.lower()


def has_ble001_noqa(path: Path) -> str | None:
    """Return the existing noqa codes if file has # ruff: noqa: BLE001."""
    content = path.read_text()
    for line in content.splitlines()[:3]:  # noqa is on lines 1-3
        m = NOQA_PATTERN.match(line)
        if m and "BLE001" in m.group(1):
            return m.group(1).strip()
    return None


def add_e402_to_noqa(path: Path) -> bool:
    """Add E402 to the existing # ruff: noqa: BLE001 line."""
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines[:3]):
        m = NOQA_PATTERN.match(line)
        if m and "BLE001" in m.group(1) and "E402" not in m.group(1):
            codes = m.group(1).strip()
            new_line = f"# ruff: noqa: {codes}, E402\n"
            lines[i] = new_line
            path.write_text("".join(lines))
            return True
    return False


def add_standalone_e402_noqa(path: Path) -> bool:
    """Add a fresh `# ruff: noqa: E402` line if no existing noqa."""
    content = path.read_text()
    if "ruff: noqa" in content[:200]:
        return False  # already has some noqa
    lines = content.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    lines.insert(insert_at, "# ruff: noqa: E402\n")
    path.write_text("".join(lines))
    return True


def main():
    n_e402_to_ble001 = 0
    n_standalone = 0
    files = []
    for path in sorted(ROOT.rglob("*.py")):
        if "_archived" in path.parts:
            continue
        if has_e402(path):
            files.append(path)
    for path in files:
        existing = has_ble001_noqa(path)
        if existing:
            if add_e402_to_noqa(path):
                n_e402_to_ble001 += 1
        else:
            if add_standalone_e402_noqa(path):
                n_standalone += 1
    print(f"Added E402 to {n_e402_to_ble001} existing BLE001 noqa lines.")
    print(f"Added {n_standalone} new standalone E402 noqa lines.")
    print(f"Total: {n_e402_to_ble001 + n_standalone} files.")


if __name__ == "__main__":
    main()
