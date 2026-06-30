#!/usr/bin/env python3
"""Version consistency checker for WhiteMagic release.

Ensures all version references across the codebase agree on the canonical version
from core/VERSION. Run this before release to catch version drift.
"""

import re
import sys
from pathlib import Path

# Get canonical version
ROOT = Path(__file__).parent.parent.parent
CANONICAL_FILE = ROOT / "core" / "VERSION"

if not CANONICAL_FILE.exists():
    print(f"ERROR: Canonical version file not found: {CANONICAL_FILE}")
    sys.exit(1)

CANONICAL = CANONICAL_FILE.read_text().strip()
print(f"Canonical version: {CANONICAL}")

# Files to check for version references
REFERENCES = [
    "README.md",
    "CHANGELOG.md",
    "core/README.md",
    "core/pyproject.toml",
    "SECURITY.md",
    "core/whitemagic-rust/Cargo.toml",
    "core/whitemagic-rust/Cargo.lock",
    "core/whitemagic-math/Cargo.toml",
    "core/whitemagic/bridges/julia/Project.toml",
    "core/whitemagic/bridges/julia/Manifest.toml",
    "core/mesh_aux/pixi.toml",
    "core/sdk_aux/vscode-extension/package.json",
    "polyglot/whitemagic-hs/whitemagic-haskell.cabal",
    "polyglot/whitemagic-jl/Project.toml",
    "polyglot/whitemagic-zig/pixi.toml",
    "core/.well-known/agent.json",
]

mismatches = []

for ref in REFERENCES:
    ref_path = ROOT / ref
    if not ref_path.exists():
        print(f"WARNING: Reference file not found: {ref}")
        continue

    content = ref_path.read_text()

    # File-specific checks
    if ref == "core/pyproject.toml":
        # Only check the version = line, not dependencies
        for line in content.split("\n"):
            if line.strip().startswith("version =") and "dependencies" not in line:
                version_match = re.search(r'"(\d+\.\d+\.\d+)"', line)
                if version_match:
                    version = version_match.group(1)
                    if version != CANONICAL:
                        mismatches.append((ref, version, line.strip()))
    elif ref in {"core/whitemagic-rust/Cargo.toml", "core/whitemagic-math/Cargo.toml"}:
        # Only check the package version line, not dependencies
        in_package = False
        for line in content.split("\n"):
            if line.strip().startswith("[package]"):
                in_package = True
            elif line.strip().startswith("[") and in_package:
                in_package = False
            elif in_package and line.strip().startswith("version ="):
                version_match = re.search(r'"(\d+\.\d+\.\d+)"', line)
                if version_match:
                    version = version_match.group(1)
                    if version != CANONICAL:
                        mismatches.append((ref, version, line.strip()))
    elif ref.endswith("Cargo.lock"):
        pattern = (
            r'\[\[package\]\]\nname = "(whitemagic-[^"]+)"\nversion = "(\d+\.\d+\.\d+)"'
        )
        for match in re.finditer(pattern, content):
            version = match.group(2)
            if version != CANONICAL:
                mismatches.append((ref, version, f"{match.group(1)} version field"))
    elif ref.endswith("package.json") or ref.endswith("package-lock.json"):
        matches = list(re.finditer(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', content))
        max_checks = 2 if ref.endswith("package-lock.json") else 1
        for match in matches[:max_checks]:
            version = match.group(1)
            if version != CANONICAL:
                mismatches.append((ref, version, "version field"))
    elif ref.endswith(".cabal"):
        version_match = re.search(r"^version:\s*(\d+\.\d+\.\d+)", content, re.MULTILINE)
        if version_match:
            version = version_match.group(1)
            if version != CANONICAL:
                mismatches.append((ref, version, "version field"))
    elif ref.endswith("pixi.toml") or ref.endswith("Project.toml"):
        version_match = re.search(
            r'^version\s*=\s*"(\d+\.\d+\.\d+)"', content, re.MULTILINE
        )
        if version_match:
            version = version_match.group(1)
            if version != CANONICAL:
                mismatches.append((ref, version, "version field"))
    elif ref.endswith("Manifest.toml"):
        pattern = (
            r'\[\[deps\.(WhiteMagic[^\]]+)\]\][\s\S]*?^version\s*=\s*"(\d+\.\d+\.\d+)"'
        )
        for match in re.finditer(pattern, content, re.MULTILINE):
            version = match.group(2)
            if version != CANONICAL:
                mismatches.append((ref, version, f"{match.group(1)} version field"))
    elif ref == "core/.well-known/agent.json":
        # Check JSON version field
        version_match = re.search(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', content)
        if version_match:
            version = version_match.group(1)
            if version != CANONICAL:
                mismatches.append((ref, version, "version field"))
    else:
        # For markdown files, check for vXX.X.X or XX.X.X patterns
        # but exclude changelog history sections and URLs
        lines = content.split("\n")
        in_changelog_history = False
        for i, line in enumerate(lines):
            # Detect changelog history sections
            if "## [" in line or "### [" in line:
                in_changelog_history = True
            elif line.startswith("##") and not line.startswith("###"):
                in_changelog_history = False

            if in_changelog_history:
                continue

            # Skip lines with URLs (http, https, www)
            if "http" in line or "www." in line:
                continue

            # Skip lines with dependency version patterns
            if ">=" in line or "<" in line or "~=" in line:
                continue

            # Skip historical / creation references
            if "Initial manifest creation" in line or "creation (v" in line:
                continue

            # Skip table rows referencing prior release baselines
            if "release baseline" in line.lower() and "current" not in line.lower():
                continue

            # Check for version patterns
            for match in re.finditer(r"v?(\d+\.\d+\.\d+)", line):
                version = match.group(1)
                if version != CANONICAL:
                    # Allow specific historical references
                    if "v21.0.0" in line and ("Initial" in line or "creation" in line):
                        continue
                    # Allow historical release baseline references (e.g., "v23.0.0 release baseline")
                    if "release baseline" in line:
                        continue
                    # Allow historical changelog entries (e.g., "## [23.1.0]")
                    if version == "23.1.0" and ("## [" in line or "v23.1.0" in line):
                        continue
                    mismatches.append((ref, version, line.strip()))

if mismatches:
    print("\nERROR: Version mismatches found:")
    for ref, version, line in mismatches:
        print(f"  {ref}: found '{version}' in line: {line[:80]}...")
    sys.exit(1)

print("\n✓ All references agree on canonical version")
sys.exit(0)
