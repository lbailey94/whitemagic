#!/usr/bin/env python3
"""Generation-aware, fail-closed helpers for the post-release tail."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


VERSION_RE = re.compile(r"^(\d+)\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
CONTRACT_KIND = "whitemagic-route-schema-manifest"
GEN2_CONTRACT = Path("docs/contract/route-schema-manifest.json")
GEN3_CONTRACT = Path("docs/gen3/route-schema-manifest.json")


def family_for_version(version: str) -> str:
    normalized = version.removeprefix("v")
    match = VERSION_RE.fullmatch(normalized)
    if not match:
        raise ValueError("version must be full semver: X.Y.Z[-suffix]")
    major = int(match.group(1))
    if major == 9:
        return "gen2"
    if major == 10:
        return "gen3"
    raise ValueError(f"no registered release family for version {normalized}")


def contract_path(root: Path, family: str) -> Path:
    return root / (GEN2_CONTRACT if family == "gen2" else GEN3_CONTRACT)


def validate_contract(data: Any, version: str, family: str) -> None:
    if not isinstance(data, dict):
        raise ValueError("contract JSON root must be an object")
    if data.get("kind") != CONTRACT_KIND:
        raise ValueError("contract kind is missing or unexpected")
    if data.get("format_version") != 1:
        raise ValueError("contract format_version must be 1")
    if data.get("version") != version:
        raise ValueError(f"contract version {data.get('version')!r} != release {version!r}")
    expected_source = {
        "gen2": "running binary registry (one exact revision)",
        "gen3": "running binary registry (Gen3 hybrid contract bridge)",
    }[family]
    if data.get("source") != expected_source:
        raise ValueError(f"contract source does not identify the {family} runtime")
    if data.get("generated_by") != "wm contract --json":
        raise ValueError("contract generator identity is unexpected")
    tools = data.get("tools")
    counts = data.get("counts")
    if not isinstance(tools, list) or not isinstance(counts, dict):
        raise ValueError("contract tools/counts are missing")
    routes = [row.get("route") for row in tools if isinstance(row, dict)]
    if len(routes) != len(tools) or any(not isinstance(route, str) or not route for route in routes):
        raise ValueError("contract tools must each have a named route")
    if len(set(routes)) != len(routes):
        raise ValueError("contract contains duplicate route names")
    if counts.get("routes") != len(tools):
        raise ValueError("contract route count does not match tools array")
    declared = counts.get("declared")
    undeclared = counts.get("undeclared")
    if not isinstance(declared, int) or not isinstance(undeclared, int):
        raise ValueError("contract declared/undeclared counts are missing")
    if declared < 0 or undeclared < 0 or declared + undeclared != len(tools):
        raise ValueError("contract declared/undeclared counts do not sum to routes")


def _write_atomic(destination: Path, contents: bytes) -> None:
    # Keep generation-specific outputs physically separate; distinct path
    # strings are insufficient if an output parent is a symlink.
    for ancestor in destination.parents:
        if ancestor.is_symlink():
            raise ValueError(f"contract output parent must not be a symlink: {ancestor}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    old_mode = stat.S_IMODE(destination.stat().st_mode) if destination.exists() else 0o644
    fd, tmp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents if contents.endswith(b"\n") else contents + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, old_mode)
        os.replace(tmp, destination)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def export_contract(version: str, binary: Path, root: Path, *, dry_run: bool = False) -> Path:
    family = family_for_version(version)
    destination = contract_path(root, family)
    if dry_run:
        if family == "gen2":
            print(f"[dry-run] {binary} contract --out {destination}")
        else:
            print(f"[dry-run] {binary} contract --json -> {destination}")
        print(f"[dry-run] validate {family} manifest version/source before write")
        return destination

    with tempfile.TemporaryDirectory(prefix="wm-release-contract-") as temp_dir:
        generated = Path(temp_dir) / "route-schema-manifest.json"
        if family == "gen2":
            command = [str(binary), "contract", "--out", str(generated)]
            proc = subprocess.run(command, text=True, capture_output=True, check=False, timeout=120)
            if proc.returncode != 0:
                raise RuntimeError(f"Gen2 contract export failed: {proc.stderr or proc.stdout}")
            if not generated.is_file():
                raise RuntimeError("Gen2 `wm contract --out` did not create its output")
            contents = generated.read_bytes()
        else:
            command = [str(binary), "contract", "--json"]
            proc = subprocess.run(command, text=True, capture_output=True, check=False, timeout=120)
            if proc.returncode != 0:
                raise RuntimeError(f"Gen3 contract export failed: {proc.stderr or proc.stdout}")
            contents = proc.stdout.encode("utf-8")

    try:
        data = json.loads(contents)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"released binary emitted invalid contract JSON: {exc}") from exc
    validate_contract(data, version, family)
    _write_atomic(destination, contents)
    print(f"{family} contract manifest written: {destination}")
    return destination


def select_workflow_run(runs: Any, version: str, source_sha: str, kind: str) -> str | None:
    family_for_version(version)
    if not isinstance(runs, list):
        raise ValueError("workflow run list must be a JSON array")
    # Only a tag push creates the canonical GitHub Release. A manually
    # dispatched workflow may share a SHA but does not prove that publication.
    expected_events = {"push"} if kind == "release" else {"workflow_run"}
    candidates = [
        row for row in runs
        if isinstance(row, dict)
        and row.get("event") in expected_events
        and str(row.get("headSha", "")).lower() == source_sha.lower()
        and (kind != "release" or row.get("headBranch") == f"v{version}")
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda row: row.get("createdAt", ""), reverse=True)
    run_id = candidates[0].get("databaseId")
    return str(run_id) if run_id is not None else None


def verify_health_record(record: Any, version: str, manifest_sha256: str) -> None:
    family_for_version(version)
    if not isinstance(record, dict):
        raise ValueError("release-health record must be a JSON object")
    if record.get("kind") != "wm.release-health" or record.get("schema") != 1:
        raise ValueError("release-health kind/schema is missing or unsupported")
    if record.get("version") != version:
        raise ValueError(f"health version {record.get('version')!r} != {version!r}")
    if record.get("tag") != f"v{version}":
        raise ValueError(f"health tag {record.get('tag')!r} != v{version}")
    if record.get("status") != "healthy":
        raise ValueError("release-health record is not healthy")
    registries = record.get("registries")
    if not isinstance(registries, dict):
        raise ValueError("release-health registries object is missing")
    for name in ("github-release", "crates.io", "npm", "docker", "mcp-registry"):
        entry = registries.get(name)
        if not isinstance(entry, dict) or entry.get("status") != "live":
            raise ValueError(f"release-health registry {name} is not live")
    github_release = registries.get("github-release")
    if not isinstance(github_release, dict):
        raise ValueError("release-health exact GitHub release result is missing")
    if github_release.get("status") != "live":
        raise ValueError("release-health record does not report the exact GitHub release live")
    if github_release.get("manifest_sha256") != manifest_sha256:
        raise ValueError("health record is bound to a different release manifest")
    if github_release.get("manifest_signature_valid") is not True:
        raise ValueError("health record does not verify the release manifest signature")
    if github_release.get("artifact_integrity") != "verified":
        raise ValueError("health record does not verify release artifact integrity")
    certifications = record.get("install_certification")
    if not isinstance(certifications, dict):
        raise ValueError("release-health install certifications are missing")
    for name in ("npm", "docker"):
        certification = certifications.get(name)
        if not isinstance(certification, dict):
            raise ValueError(f"{name} install certification is missing")
        if certification.get("status") != "pass":
            raise ValueError(f"{name} install certification did not pass")
        if certification.get("bound_manifest_sha256") != manifest_sha256:
            raise ValueError(f"{name} certification is bound to a different manifest")
        if certification.get("artifact_integrity") != "verified":
            raise ValueError(f"{name} certified artifact integrity is not verified")
        if certification.get("runtime_selftest") != "pass":
            raise ValueError(f"{name} runtime self-test did not pass")
        selftest = certification.get("selftest")
        if not isinstance(selftest, dict) or not (
            bool(selftest.get("passed")) or selftest.get("status") == "ok"
        ):
            raise ValueError(f"{name} certification does not contain a passing runtime self-test")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    family = sub.add_parser("family")
    family.add_argument("version")
    contract = sub.add_parser("contract")
    contract.add_argument("--version", required=True)
    contract.add_argument("--binary", type=Path)
    contract.add_argument("--repo-root", type=Path, default=Path.cwd())
    contract.add_argument("--dry-run", action="store_true")
    for name in ("select-release", "select-health"):
        selection = sub.add_parser(name)
        selection.add_argument("--version", required=True)
        selection.add_argument("--source-sha", required=True)
    health = sub.add_parser("verify-health")
    health.add_argument("--version", required=True)
    health.add_argument("--manifest-sha256", required=True)
    health.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "family":
            print(family_for_version(args.version))
        elif args.command == "contract":
            if not args.dry_run and args.binary is None:
                parser.error("--binary is required unless --dry-run is set")
            export_contract(args.version, args.binary or Path("wm"), args.repo_root, dry_run=args.dry_run)
        elif args.command in ("select-release", "select-health"):
            runs = json.load(sys.stdin)
            kind = "release" if args.command == "select-release" else "health"
            selected = select_workflow_run(runs, args.version, args.source_sha, kind)
            if selected is None:
                raise ValueError(f"no matching {kind} run is bound to v{args.version} source {args.source_sha}")
            print(selected)
        else:
            record = json.loads(args.record.read_text(encoding="utf-8"))
            verify_health_record(record, args.version, args.manifest_sha256)
            print(f"release health verified for v{args.version} manifest {args.manifest_sha256}")
    except (OSError, json.JSONDecodeError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"release-tail error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
