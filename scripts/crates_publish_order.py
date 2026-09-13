#!/usr/bin/env python3
"""Print workspace crates in dependency order for `cargo publish`.

The order is derived from `cargo metadata` instead of a hand-maintained list:
a crate must be published after every other workspace crate it depends on
(crates.io rejects a publish whose dependency version is not yet live).
Within a dependency layer, names are sorted for deterministic output.

Dev-dependencies are ignored (they are not resolved from the registry at
publish time); normal and build dependencies are both honored.

Usage:
    crates_publish_order.py [--manifest-path PATH] [--json]

Exit codes:
    0  order printed
    2  dependency cycle among workspace members, or no publishable members
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def workspace_order(manifest_path: str) -> list[str]:
    raw = subprocess.check_output(
        [
            "cargo",
            "metadata",
            "--no-deps",
            "--format-version",
            "1",
            "--manifest-path",
            manifest_path,
        ],
        text=True,
    )
    meta = json.loads(raw)

    members = {pkg["id"]: pkg for pkg in meta.get("packages", [])}
    workspace_ids = set(meta.get("workspace_members", []))
    publishable = {
        pkg["name"]: pkg
        for pkg_id, pkg in members.items()
        if pkg_id in workspace_ids and pkg.get("publish") != []
    }

    deps: dict[str, set[str]] = {name: set() for name in publishable}
    for name, pkg in publishable.items():
        for dep in pkg.get("dependencies", []):
            # Only registry-relevant workspace dependencies constrain order.
            if dep.get("kind") == "dev":
                continue
            if dep["name"] in publishable:
                deps[name].add(dep["name"])

    order: list[str] = []
    remaining = {name: set(ds) for name, ds in deps.items()}
    while remaining:
        layer = sorted(
            name for name, ds in remaining.items() if not (ds & remaining.keys())
        )
        if not layer:
            sys.stderr.write(
                "cycle detected among workspace crates: "
                + ", ".join(sorted(remaining))
                + "\n"
            )
            sys.exit(2)
        order.extend(layer)
        for name in layer:
            del remaining[name]

    if not order:
        sys.stderr.write("no publishable workspace members found\n")
        sys.exit(2)
    return order


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", default="Cargo.toml")
    parser.add_argument(
        "--json", action="store_true", help="emit a JSON array instead of a line"
    )
    args = parser.parse_args()

    order = workspace_order(args.manifest_path)
    if args.json:
        print(json.dumps(order))
    else:
        print(" ".join(order))


if __name__ == "__main__":
    main()
