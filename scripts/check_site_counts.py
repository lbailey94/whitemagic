#!/usr/bin/env python3
"""Compare the site's capability counts with the released binary's runtime manifest.

`wm manifest` against the released binary is the authority for the tool
surface; the site's `public/api/manifest.json` carries the derived counts.
Mapping verified across 9.1.7-9.1.9:

    authored_tools = callable_tools = counts.full_pre_profile - 1
        (full_pre_profile includes the `wm` meta-tool)
    curated_tools  = counts.profile_pre_meta
    mesh_opt_in_tools = full_pre_profile_routes named `sangha.mesh.*`

`mcp_entrypoints`, `gana_taxonomy`, `gana_active` and `crates` have no source
in the runtime manifest: they are carried and reported, never checked here
(`crates` is gated against the release manifest by the site's own --check).

Exit codes: 0 consistent, 1 drift (update the site counts before pushing),
2 usage or unreadable manifest.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DERIVED = ("authored_tools", "callable_tools", "curated_tools", "mesh_opt_in_tools")
CARRIED = ("mcp_entrypoints", "gana_taxonomy", "gana_active", "crates")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-manifest", required=True, help="wm manifest JSON")
    parser.add_argument("--site-manifest", required=True, help="public/api/manifest.json")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args()

    try:
        runtime = json.loads(Path(args.runtime_manifest).read_text(encoding="utf-8"))
        site = json.loads(Path(args.site_manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read manifest: {exc}", file=sys.stderr)
        return 2

    counts = runtime.get("counts") or {}
    full = counts.get("full_pre_profile")
    curated = counts.get("profile_pre_meta")
    if not isinstance(full, int) or not isinstance(curated, int):
        print(
            "runtime manifest lacks counts.full_pre_profile / counts.profile_pre_meta",
            file=sys.stderr,
        )
        return 2
    mesh = sum(
        1
        for route in runtime.get("full_pre_profile_routes") or []
        if str(route.get("name", "")).startswith("sangha.mesh.")
    )
    authored = full - 1
    derived = {
        "authored_tools": authored,
        "callable_tools": authored,
        "curated_tools": curated,
        "mesh_opt_in_tools": mesh,
    }
    site_counts = site.get("counts") or {}
    drift = {
        key: {"runtime": value, "site": site_counts.get(key)}
        for key, value in derived.items()
        if site_counts.get(key) != value
    }
    report = {
        "runtime": {
            "full_pre_profile": full,
            "profile_pre_meta": curated,
            "mesh_routes": mesh,
        },
        "derived": derived,
        "site": {key: site_counts.get(key) for key in DERIVED},
        "carried": {key: site_counts.get(key) for key in CARRIED},
        "drift": drift,
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for key in DERIVED:
            state = "ok" if key not in drift else "DRIFT"
            print(f"  {key:<20} runtime={derived[key]:<4} site={site_counts.get(key)}  {state}")
        carried = ", ".join(f"{key}={site_counts.get(key)}" for key in CARRIED)
        print(f"  carried (no runtime source): {carried}")
    if drift:
        print(
            "\nDRIFT: the tool surface moved — update public/api/manifest.json counts"
            " (and the prose that embeds them) before pushing the site sync:",
            file=sys.stderr,
        )
        for key, values in drift.items():
            print(f"  {key}: site {values['site']} -> runtime {values['runtime']}", file=sys.stderr)
        return 1
    print("site counts match the released binary's runtime manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
