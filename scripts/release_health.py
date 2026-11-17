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
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import base64
import hashlib
import tempfile

UA = "wm-release-health/1.0 (+https://github.com/lbailey94/whitemagic)"
DEFAULT_RELEASE_PUBKEY = "aade884b035d2f92333843faba153eb83b201d1d1db63e25d642d82f4b12770e"
# Select the expected matrix from the tag independently of its manifest.
GEN3_THREE_TARGETS = {
    "linux-x86_64": "wm-linux-x86_64",
    "linux-aarch64": "wm-linux-aarch64",
    "macos-aarch64": "wm-macos-aarch64",
}
GEN3_EARLY_WINDOWS_TARGETS = {
    **GEN3_THREE_TARGETS,
    "windows-x86_64": "wm-windows-x86_64.exe",
}
GEN3_FIVE_TARGETS = {
    **GEN3_EARLY_WINDOWS_TARGETS,
    "macos-x86_64": "wm-macos-x86_64",
}
V9_TARGETS = {
    **GEN3_FIVE_TARGETS,
    "linux-x86_64-musl": "wm-linux-x86_64-musl",
    "linux-aarch64-musl": "wm-linux-aarch64-musl",
}
NPM_PACKAGE = "whitemagic-mcp"
DOCKER_REPO = "lbailey94/whitemagic"
MCP_SERVER = "io.github.lbailey94/whitemagic-mcp"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_bytes(url: str, timeout: int = 20) -> tuple[int | None, bytes | str]:
    """Fetch raw bytes. Returns (status, bytes); (None, error-string) on transport failure."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:  # noqa: BLE001 - transport failures are data here
        return None, str(exc)


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


def verify_ed25519_signature(
    message: bytes, sig_hex: str, pubkey_hex: str | None = None
) -> tuple[bool, str | None]:
    """Verify detached hex-encoded Ed25519 signature over message."""
    pub_hex = (pubkey_hex or os.environ.get("WM_RELEASE_PUBKEY") or DEFAULT_RELEASE_PUBKEY).strip()
    try:
        pub_bytes = bytes.fromhex(pub_hex)
        sig_bytes = bytes.fromhex(sig_hex.strip())
    except ValueError as exc:
        return False, f"invalid hex in pubkey/signature: {exc}"
    if len(pub_bytes) != 32 or len(sig_bytes) != 64:
        return False, f"invalid Ed25519 key/sig length ({len(pub_bytes)}/{len(sig_bytes)})"
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig_bytes, message)
        return True, None
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        return False, f"signature verification failed: {exc}"

    # Fallback to openssl pkeyutl when cryptography is not installed
    der_pub = bytes.fromhex("302a300506032b6570032100") + pub_bytes
    try:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pub_file = td_path / "pub.der"
            sig_file = td_path / "sig.bin"
            msg_file = td_path / "msg.bin"
            pub_file.write_bytes(der_pub)
            sig_file.write_bytes(sig_bytes)
            msg_file.write_bytes(message)
            proc = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-keyform",
                    "DER",
                    "-inkey",
                    str(pub_file),
                    "-rawin",
                    "-in",
                    str(msg_file),
                    "-sigfile",
                    str(sig_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                return True, None
            return False, f"openssl verify failed: {(proc.stderr or proc.stdout).strip()}"
    except Exception as exc:  # noqa: BLE001
        return False, f"signature verification unavailable: {exc}"


def latest_version(repo: str) -> str:
    status, data = fetch_json(f"https://api.github.com/repos/{repo}/releases/latest")
    tag = data.get("tag_name", "") if isinstance(data, dict) else ""
    if status != 200 or not tag:
        raise SystemExit(f"could not resolve latest release for {repo}")
    return tag.lstrip("v")


def expected_manifest_targets(version: str, profile: str = "auto") -> dict[str, str]:
    if profile == "v9":
        return V9_TARGETS
    if profile == "v10":
        return GEN3_THREE_TARGETS

    major, minor, _patch = map(int, version.split("-", 1)[0].split("."))
    if major == 9 or version == "10.0.0-alpha.1":
        return V9_TARGETS
    if version in {"10.0.0-alpha", "10.2.0-alpha", "10.2.0-alpha.1"}:
        return GEN3_EARLY_WINDOWS_TARGETS
    if (major, minor) >= (11, 3):
        return GEN3_FIVE_TARGETS
    return GEN3_THREE_TARGETS


def required_release_assets(targets: dict[str, str]) -> list[str]:
    # POSIX releases include gzip assets. Windows ships only the raw .exe.
    return (
        [asset for target in targets.values() for asset in (target, f"{target}.sha256")]
        + [
            asset for target in targets.values() if not target.endswith(".exe")
            for asset in (f"{target}.gz", f"{target}.gz.sha256")
        ]
        + ["release-manifest.json", "release-manifest.json.sig"]
    )


def probe_github(
    repo: str, version: str, pubkey_hex: str | None = None, *, profile: str = "auto",
) -> dict:
    expected_targets = expected_manifest_targets(version, profile)
    required_assets = required_release_assets(expected_targets)
    url = f"https://api.github.com/repos/{repo}/releases/tags/v{version}"
    status, data = fetch_json(url)
    base = {"url": url, "required_assets": len(required_assets)}
    if status is None:
        return {**base, "status": "unreachable", "error": data}
    if status == 404:
        return {**base, "status": "missing", "missing_assets": required_assets}
    assets_by_name = {
        asset.get("name"): asset
        for asset in (data or {}).get("assets", [])
        if isinstance(asset, dict) and asset.get("name")
    }
    names = set(assets_by_name.keys())
    missing = [asset for asset in required_assets if asset not in names]
    manifest_error = None
    manifest_sha256 = None
    manifest_signature_valid = False
    artifact_integrity = "unverified"
    if not missing:
        base_dl = f"https://github.com/{repo}/releases/download/v{version}"
        m_url = f"{base_dl}/release-manifest.json"
        s_url = f"{base_dl}/release-manifest.json.sig"
        m_status, m_raw = fetch_bytes(m_url)
        s_status, s_raw = fetch_bytes(s_url)
        if m_status != 200 or not isinstance(m_raw, bytes) or not m_raw:
            manifest_error = f"release-manifest.json HTTP {m_status}"
        elif s_status != 200 or not isinstance(s_raw, bytes) or not s_raw:
            manifest_error = f"release-manifest.json.sig HTTP {s_status}"
        else:
            manifest_sha256 = hashlib.sha256(m_raw).hexdigest()
            sig_ok, sig_err = verify_ed25519_signature(
                m_raw, s_raw.decode("utf-8", errors="replace"), pubkey_hex=pubkey_hex
            )
            manifest_signature_valid = sig_ok
            try:
                m_data = json.loads(m_raw.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                m_data = None
                manifest_error = f"release-manifest.json invalid JSON: {exc}"
            if not manifest_error and not sig_ok:
                manifest_error = f"manifest signature invalid: {sig_err}"
            elif not manifest_error and (not isinstance(m_data, dict) or m_data.get("version") != version):
                manifest_error = f"manifest version {(m_data or {}).get('version')!r} != {version!r}"
            elif not manifest_error:
                m_targets = m_data.get("targets")
                if not isinstance(m_targets, dict):
                    manifest_error = "manifest missing targets object"
                elif m_targets.keys() != expected_targets.keys():
                    manifest_error = (
                        f"manifest target matrix {sorted(m_targets.keys())} != "
                        f"expected {sorted(expected_targets)}"
                    )
                else:
                    integrity_errors = []
                    for t_key, asset_name in sorted(expected_targets.items()):
                        t_decl = m_targets.get(t_key) or {}
                        expected_url = f"{base_dl}/{asset_name}"
                        t_url = str(t_decl.get("url") or "")
                        t_sha = str(t_decl.get("sha256") or "").strip().lower()
                        t_size = t_decl.get("size")
                        if t_url != expected_url:
                            integrity_errors.append(f"{t_key}: url {t_url!r} != {expected_url!r}")
                            continue
                        if not t_sha or len(t_sha) != 64:
                            integrity_errors.append(f"{t_key}: invalid sha256 {t_sha!r}")
                            continue
                        gh_asset = assets_by_name.get(asset_name) or {}
                        gh_size = gh_asset.get("size")
                        if not isinstance(gh_size, int) or gh_size < 0:
                            integrity_errors.append(f"{t_key}: GitHub asset size missing or invalid")
                        elif not isinstance(t_size, int) or t_size != gh_size:
                            integrity_errors.append(
                                f"{t_key}: manifest size {t_size} != GitHub asset size {gh_size}"
                            )
                        gh_digest = str(gh_asset.get("digest") or "").strip().lower()
                        if not gh_digest.startswith("sha256:"):
                            integrity_errors.append(f"{t_key}: GitHub asset digest missing or unsupported")
                        elif gh_digest != f"sha256:{t_sha}":
                            integrity_errors.append(
                                f"{t_key}: manifest sha256 {t_sha[:12]}… != GitHub asset {gh_digest[:19]}…"
                            )
                        sc_status, sc_raw = fetch_bytes(f"{base_dl}/{asset_name}.sha256")
                        if sc_status != 200 or not isinstance(sc_raw, bytes) or not sc_raw:
                            integrity_errors.append(f"{t_key}: sidecar HTTP {sc_status}")
                        else:
                            sc_sha = sc_raw.decode("utf-8", errors="replace").split()[0].strip().lower()
                            if sc_sha != t_sha:
                                integrity_errors.append(
                                    f"{t_key}: manifest sha256 {t_sha[:12]}… != sidecar {sc_sha[:12]}…"
                                )
                        sig_bundle = t_decl.get("signature")
                        if sig_bundle and sig_bundle in assets_by_name:
                            b_status, b_raw = fetch_bytes(f"{base_dl}/{sig_bundle}")
                            if b_status == 200 and isinstance(b_raw, bytes) and b_raw:
                                try:
                                    b_json = json.loads(b_raw.decode("utf-8"))
                                    if "messageSignature" in b_json:
                                        b_sha = base64.b64decode(
                                            b_json["messageSignature"]["messageDigest"]["digest"]
                                        ).hex().lower()
                                    else:
                                        rekord = json.loads(
                                            base64.b64decode(b_json["rekorBundle"]["Payload"]["body"])
                                        )
                                        b_sha = str(rekord["spec"]["data"]["hash"]["value"]).lower()
                                    if b_sha != t_sha:
                                        integrity_errors.append(
                                            f"{t_key}: manifest sha256 {t_sha[:12]}… != bundle {b_sha[:12]}…"
                                        )
                                except Exception as exc:  # noqa: BLE001
                                    integrity_errors.append(f"{t_key}: bundle parse error: {exc}")
                    if integrity_errors:
                        manifest_error = "; ".join(integrity_errors)
                        artifact_integrity = "failed"
                    else:
                        artifact_integrity = "verified"
    out = {
        **base,
        "status": (
            "live"
            if (not missing and not manifest_error and manifest_signature_valid and artifact_integrity == "verified")
            else "lagging"
        ),
        "published_at": (data or {}).get("published_at"),
        "found_assets": len(names),
        "missing_assets": missing,
        "manifest_sha256": manifest_sha256,
        "manifest_signature_valid": manifest_signature_valid,
        "artifact_integrity": artifact_integrity,
    }
    if manifest_error:
        out["manifest_error"] = manifest_error
    return out


def probe_crates(version: str) -> dict:
    script = Path(__file__).resolve().parent / "crates_publish_order.py"
    # Normal invocations belong to this checkout, independent of the caller's
    # cwd. CI also copies the checker/helpers to RUNNER_TEMP before checking
    # out an older release; those saved copies intentionally use the selected
    # tag checkout's manifest in cwd rather than the current source tree.
    manifest = script.parent.parent / "Cargo.toml"
    if not manifest.is_file():
        manifest = Path.cwd() / "Cargo.toml"
    try:
        order = json.loads(
            subprocess.check_output(
                [sys.executable, str(script), "--manifest-path", str(manifest), "--json"],
                text=True,
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


def probe_all(repo: str, version: str, *, profile: str = "auto") -> dict:
    registries = {
        "github-release": probe_github(repo, version, profile=profile),
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
        "scope": [
            "distribution availability",
            "artifact integrity",
            "install certification when attached",
        ],
        "unmeasured_excludes": [
            "CI status",
            "source-level test qualification",
            "performance qualification",
        ],
        "registries": registries,
    }


def summarize(record: dict) -> None:
    print(
        f"wm distribution health — {record['tag']} ({record['repo']}) "
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
    print(f"distribution status: {record['status'].upper()}")
    if record.get("unmeasured_excludes"):
        print("not measured here: " + ", ".join(record["unmeasured_excludes"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default=None)
    ap.add_argument("--repo", default="lbailey94/whitemagic")
    ap.add_argument(
        "--json", default=None, help="write the record to PATH ('-' = stdout)"
    )
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--profile", choices=("auto", "v9", "v10"), default="auto")
    args = ap.parse_args()

    version = args.version or latest_version(args.repo)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.]+)?", version):
        ap.error(f"expected a release version X.Y.Z[-suffix], got {version!r}")
    record = probe_all(args.repo, version, profile=args.profile)

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
