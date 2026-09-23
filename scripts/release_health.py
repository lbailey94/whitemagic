#!/usr/bin/env python3
"""Probe every WhiteMagic distribution surface for one release version.

GitHub Releases are canonical; crates.io, npm, Docker Hub, and the official
MCP registry are mirrors that can lag (the observed "npm lagged" class). The
record this writes is the single machine-readable source of truth for "is
release X actually available everywhere":

    release-health.json  (also uploaded to the GitHub Release as an asset)

`release.yml` fans out on tag; `.github/workflows/release-health.yml` runs
this probe after the fan-out completes and on a daily schedule, retries any
laggards idempotently, re-probes, uploads the record, and goes red if any
surface is still behind (so the next day's run retries again).

Usage:
    release_health.py [--version 9.1.4] [--repo lbailey94/whitemagic]
                      [--json release-health.json] [--quiet]

    --version defaults to the latest GitHub Release (tag `v*`).
    --json - writes the record to stdout.

Exit codes:
    0  every surface is live
    1  one or more surfaces are lagging (the record is still written)
    2  usage / resolver problems
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "wm-release-health/1.0 (+https://github.com/lbailey94/whitemagic)"
TARGETS = [
    "wm-linux-x86_64-musl",
    "wm-linux-x86_64",
    "wm-linux-aarch64-musl",
    "wm-linux-aarch64",
    "wm-macos-x86_64",
    "wm-macos-aarch64",
    "wm-windows-x86_64.exe",
]
# Linux/macOS distributables are published gzip'd alongside the raw binary
# (2026-09-21, slow-link accessibility); Windows is raw only.
COMPRESSED_TARGETS = [t for t in TARGETS if t != "wm-windows-x86_64.exe"]
REQUIRED_RELEASE_ASSETS = (
    [
        asset
        for target in TARGETS
        for asset in (target, f"{target}.sha256")
    ]
    + [asset for target in COMPRESSED_TARGETS for asset in (f"{target}.gz", f"{target}.gz.sha256")]
    + ["release-manifest.json", "release-manifest.json.sig"]
)
NPM_PACKAGE = "whitemagic-mcp"
DOCKER_REPO = "lbailey94/whitemagic"
MCP_SERVER = "io.github.lbailey94/whitemagic-mcp"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str, timeout: int = 20) -> tuple[int | None, object]:
    """Fetch JSON. Returns (status, data); (None, error-string) on transport failure."""
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:  # noqa: BLE001 - transport failures are data here
        return None, str(exc)


def latest_version(repo: str) -> str:
    status, data = fetch_json(f"https://api.github.com/repos/{repo}/releases/latest")
    tag = data.get("tag_name", "") if isinstance(data, dict) else ""
    if status != 200 or not tag:
        raise SystemExit(f"could not resolve latest release for {repo}")
    return tag.lstrip("v")


def probe_github(repo: str, version: str) -> dict:
    url = f"https://api.github.com/repos/{repo}/releases/tags/v{version}"
    status, data = fetch_json(url)
    base = {"url": url, "required_assets": len(REQUIRED_RELEASE_ASSETS)}
    if status is None:
        return {**base, "status": "unreachable", "error": data}
    if status == 404:
        return {**base, "status": "missing", "missing_assets": REQUIRED_RELEASE_ASSETS}
    names = {asset.get("name") for asset in (data or {}).get("assets", [])}
    missing = [a for a in REQUIRED_RELEASE_ASSETS if a not in names]
    return {
        **base,
        "status": "live" if not missing else "lagging",
        "published_at": (data or {}).get("published_at"),
        "found_assets": len(names),
        "missing_assets": missing,
    }


def probe_crates(version: str) -> dict:
    script = Path(__file__).resolve().parent / "crates_publish_order.py"
    try:
        order = json.loads(
            subprocess.check_output(
                [sys.executable, str(script), "--json"], text=True
            )
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"status": "unreachable", "error": f"crate order unavailable: {exc}"}
    live, missing, unreachable = [], [], []
    for name in order:
        status, _ = fetch_json(f"https://crates.io/api/v1/crates/{name}/{version}")
        if status == 200:
            live.append(name)
        elif status == 404:
            missing.append(name)
        else:
            unreachable.append(name)
        time.sleep(0.25)  # crates.io crawl policy: be polite
    status = "live" if not missing and not unreachable else "lagging"
    return {
        "status": status,
        "url": f"https://crates.io/crates/{order[0]}/{version}",
        "live": live,
        "missing": missing,
        "unreachable": unreachable,
        "live_count": len(live),
        "total": len(order),
    }


def probe_npm(version: str) -> dict:
    url = f"https://registry.npmjs.org/{NPM_PACKAGE}/{version}"
    status, data = fetch_json(url)
    if status is None:
        return {"status": "unreachable", "url": url, "error": data}
    if status == 404:
        return {"status": "missing", "url": url}
    tarball = (data or {}).get("dist", {}).get("tarball")
    return {"status": "live", "url": url, "tarball": tarball}


def probe_docker(version: str) -> dict:
    url = f"https://hub.docker.com/v2/repositories/{DOCKER_REPO}/tags/{version}"
    status, data = fetch_json(url)
    if status is None:
        return {"status": "unreachable", "url": url, "error": data}
    if status == 404:
        return {"status": "missing", "url": url}
    data = data or {}
    images = data.get("images") or [{}]
    return {
        "status": "live",
        "url": url,
        "image": f"{DOCKER_REPO}:{version}",
        "last_pushed": images[0].get("last_pushed") or data.get("last_updated"),
        "digest": images[0].get("digest"),
    }


def probe_mcp_registry(version: str) -> dict:
    query = urllib.parse.quote(MCP_SERVER)
    url = (
        "https://registry.modelcontextprotocol.io/v0/servers"
        f"?search={query}&limit=100"
    )
    # The search endpoint is slow (24.8s observed 2026-09-23 for the full
    # name + limit=100); the 20s default marked it unreachable and failed the
    # v9.2.6 health gate three times while the entry was actually live.
    status, data = fetch_json(url, timeout=60)
    if status is None:
        return {"status": "unreachable", "url": url, "error": data}
    servers = (data or {}).get("servers", [])
    versions = sorted(
        entry.get("server", {}).get("version", "")
        for entry in servers
        if entry.get("server", {}).get("name") == MCP_SERVER
    )
    live = version in versions
    return {
        "status": "live" if live else "missing",
        "url": url,
        "server": MCP_SERVER,
        "versions_seen": versions,
        "total": (data or {}).get("metadata", {}).get("count"),
    }


def probe_all(repo: str, version: str) -> dict:
    registries = {
        "github-release": probe_github(repo, version),
        "crates.io": probe_crates(version),
        "npm": probe_npm(version),
        "docker": probe_docker(version),
        "mcp-registry": probe_mcp_registry(version),
    }
    status = (
        "healthy"
        if all(entry.get("status") == "live" for entry in registries.values())
        else "lagging"
    )
    return {
        "kind": "wm.release-health",
        "schema": 1,
        "version": version,
        "tag": f"v{version}",
        "repo": repo,
        "generated_at": utc_now(),
        "generator": "scripts/release_health.py",
        "status": status,
        "registries": registries,
    }


def summarize(record: dict) -> None:
    print(
        f"wm release health — {record['tag']} ({record['repo']}) "
        f"@ {record['generated_at']}"
    )
    for name, entry in record["registries"].items():
        detail = ""
        if name == "github-release":
            found = entry.get("found_assets")
            if found is not None:
                detail = f"{found} assets ({entry.get('required_assets')} required)"
            elif entry.get("status") == "missing":
                detail = "no release for tag"
            else:
                detail = entry.get("error", "")
        elif name == "crates.io":
            detail = (
                f"{entry.get('live_count')}/{entry.get('total')} crates"
                if entry.get("total")
                else entry.get("error", "")
            )
        elif name == "npm":
            detail = f"{NPM_PACKAGE}@{record['version']}"
        elif name == "docker":
            detail = entry.get("image", f"{DOCKER_REPO}:{record['version']}")
        elif name == "mcp-registry":
            detail = (
                f"{MCP_SERVER}@{record['version']}"
                if entry.get("status") == "live"
                else f"versions seen: {', '.join(entry.get('versions_seen', []))}"
            )
        print(f"  {name:<16} {entry.get('status', '?'):<11} {detail}")
    print(f"status: {record['status'].upper()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default=None)
    ap.add_argument("--repo", default="lbailey94/whitemagic")
    ap.add_argument(
        "--json", default=None, help="write the record to PATH ('-' = stdout)"
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    version = args.version or latest_version(args.repo)
    record = probe_all(args.repo, version)

    if args.json == "-":
        print(json.dumps(record, indent=2, sort_keys=True))
    elif args.json:
        Path(args.json).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if not args.quiet:
        summarize(record)
    return 0 if record["status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
