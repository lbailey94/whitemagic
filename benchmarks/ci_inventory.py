"""P8.1 — CI workflow inventory and classification.

Maps every job across all workflow files, identifies duplicates, and
classifies each job into a CI lane (A: PR fast, B: PR integration,
C: Nightly, D: Release, or stale).

This module is importable by tests and provides a programmatic inventory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JobClass(str, Enum):
    """Classification of a CI job."""

    BLOCKING = "blocking"
    ADVISORY = "advisory"
    NIGHTLY = "nightly"
    RELEASE = "release"
    STALE = "stale"


class Lane(str, Enum):
    """CI lane assignment."""

    A_PR_FAST = "A"
    B_PR_INTEGRATION = "B"
    C_NIGHTLY = "C"
    D_RELEASE = "D"
    NONE = "none"


@dataclass
class JobEntry:
    """A single CI job across all workflows."""

    workflow: str
    job_name: str
    job_id: str
    classification: JobClass
    lane: Lane
    has_continue_on_error: bool = False
    has_pipe_mask: bool = False
    has_or_true: bool = False
    duplicates: list[str] = field(default_factory=list)
    notes: str = ""


# ─── Complete inventory ────────────────────────────────────────────────

INVENTORY: list[JobEntry] = [
    # ci.yml
    JobEntry("ci.yml", "Core (py3.12)", "core", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="Omega test gauntlet + eval harness"),
    JobEntry("ci.yml", "Lint & Typecheck", "lint", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="Ruff+BLE001 blocking; mypy steps are advisory (step-level continue-on-error)"),
    JobEntry("ci.yml", "Rust Quality", "rust-quality", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="Clippy + cargo test"),
    JobEntry("ci.yml", "Security Lint", "security", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="Bandit + pip-audit"),
    JobEntry("ci.yml", "Extras (mcp+cli)", "extras", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="Doctor check + MCP import + CLI JSON smoke"),
    JobEntry("ci.yml", "Optional API Extras", "optional-api", JobClass.ADVISORY, Lane.B_PR_INTEGRATION,
             has_continue_on_error=True, notes="FastAPI-gated tests, advisory"),
    JobEntry("ci.yml", "Optional Optimizer Extras", "optional-opt", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="CVXPY-gated tests"),
    JobEntry("ci.yml", "Build & Install Validation", "packaging", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="Wheel build + clean install + verify callable"),
    JobEntry("ci.yml", "Reproducible Build Verification", "reproducible-build", JobClass.ADVISORY, Lane.C_NIGHTLY,
             has_continue_on_error=True, notes="SHA-256 comparison, advisory"),
    JobEntry("ci.yml", "Live Network Tests (Opt-in)", "network-optin", JobClass.ADVISORY, Lane.C_NIGHTLY,
             notes="Only runs on workflow_dispatch"),
    JobEntry("ci.yml", "Version Consistency", "version-consistency", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="check_versions.py"),
    JobEntry("ci.yml", "Doc Drift Detection", "doc-drift", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="check_doc_drift.py"),
    JobEntry("ci.yml", "Site Facts Sync Check", "site-facts", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="sync_facts.py --check"),
    JobEntry("ci.yml", "Stub Audit", "stub-audit", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="check_stubs.py", duplicates=["core-ci.yml:stubs"]),
    JobEntry("ci.yml", "Coverage Report", "coverage", JobClass.ADVISORY, Lane.C_NIGHTLY,
             has_continue_on_error=True, notes="pytest --cov, advisory"),
    JobEntry("ci.yml", "STRATA Diff Review", "strata-review", JobClass.ADVISORY, Lane.A_PR_FAST,
             notes="PR-only, posts review comments"),

    # core-ci.yml
    JobEntry("core-ci.yml", "Ruff lint", "lint", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="ruff check whitemagic/ tests/", duplicates=["ci.yml:lint"]),
    JobEntry("core-ci.yml", "Stub audit", "stubs", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="check_stubs.py", duplicates=["ci.yml:stub-audit"]),
    JobEntry("core-ci.yml", "Duplicate code audit", "duplicates", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="check_duplicates.py"),
    JobEntry("core-ci.yml", "mypy type check", "typecheck", JobClass.ADVISORY, Lane.A_PR_FAST,
             has_continue_on_error=True, notes="Relaxed, warn-only"),
    JobEntry("core-ci.yml", "pytest", "test", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="xdist parallel, excludes verify/benchmarks/archive"),

    # security-ci.yml
    JobEntry("security-ci.yml", "STRATA Security Checkers", "strata-security", JobClass.ADVISORY, Lane.B_PR_INTEGRATION,
             has_continue_on_error=True, notes="All 3 STRATA steps are advisory"),
    JobEntry("security-ci.yml", "Secret Scanning", "secret-scanning", JobClass.ADVISORY, Lane.B_PR_INTEGRATION,
             has_or_true=True, notes="Scan is blocking, audit step is advisory (|| echo)"),
    JobEntry("security-ci.yml", "Dependency Vulnerability Check", "dependency-vulns", JobClass.ADVISORY, Lane.B_PR_INTEGRATION,
             has_or_true=True, has_continue_on_error=True, notes="pip-audit || true, npm audit continue-on-error"),
    JobEntry("security-ci.yml", "MCP Integrity Verification", "mcp-integrity", JobClass.ADVISORY, Lane.B_PR_INTEGRATION,
             has_continue_on_error=True, notes="Advisory, warns on drift"),
    JobEntry("security-ci.yml", "Audit Signer Key Verification", "audit-key-check", JobClass.ADVISORY, Lane.B_PR_INTEGRATION,
             has_continue_on_error=True, notes="Advisory, checks key availability"),
    JobEntry("security-ci.yml", "Security Test Suite", "security-tests", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="Security assessment + violet tests"),

    # release.yml
    JobEntry("release.yml", "CI Gate", "ci-gate", JobClass.BLOCKING, Lane.D_RELEASE,
             notes="Calls ci.yml workflow_call"),
    JobEntry("release.yml", "Build & Publish to PyPI", "build-and-publish", JobClass.RELEASE, Lane.D_RELEASE,
             notes="Build + sigstore + SBOM + PyPI + GitHub Release"),
    JobEntry("release.yml", "Build & Push Docker Image", "docker", JobClass.RELEASE, Lane.D_RELEASE,
             has_continue_on_error=True, notes="Docker Hub login is advisory"),

    # publish.yml
    JobEntry("publish.yml", "Publish to PyPI", "publish-pypi", JobClass.RELEASE, Lane.D_RELEASE,
             notes="whitemagic-mcp package to PyPI"),
    JobEntry("publish.yml", "Build wm-seed binaries", "publish-seed-binaries", JobClass.RELEASE, Lane.D_RELEASE,
             notes="Cross-platform seed binaries"),

    # site-ci.yml
    JobEntry("site-ci.yml", "TypeScript typecheck", "typecheck", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="tsc --noEmit"),
    JobEntry("site-ci.yml", "Next.js production build", "build", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="next build"),
    JobEntry("site-ci.yml", "ESLint", "lint", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="npm run lint"),
    JobEntry("site-ci.yml", "Catalog consistency check", "catalog-consistency", JobClass.BLOCKING, Lane.A_PR_FAST,
             notes="BRIDGE_MODULES ↔ impls ↔ dispatcher sync"),
    JobEntry("site-ci.yml", "Live route smoke test", "smoke", JobClass.NIGHTLY, Lane.C_NIGHTLY,
             notes="Only on main push, 32 routes"),

    # slither.yml
    JobEntry("slither.yml", "Slither static analysis", "slither", JobClass.ADVISORY, Lane.C_NIGHTLY,
             has_continue_on_error=True, notes="Solidity analysis, advisory"),

    # wasm-cicd.yml
    JobEntry("wasm-cicd.yml", "Build WASM", "build-wasm", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="wasm-pack build web + nodejs"),
    JobEntry("wasm-cicd.yml", "Publish to npm", "publish-npm", JobClass.RELEASE, Lane.D_RELEASE,
             notes="Only on tags"),
    JobEntry("wasm-cicd.yml", "Build Docker image", "build-docker", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="WASM Docker image"),
    JobEntry("wasm-cicd.yml", "Build Python package", "build-python", JobClass.BLOCKING, Lane.B_PR_INTEGRATION,
             notes="Python WASM SDK"),

    # seed-binaries.yml
    JobEntry("seed-binaries.yml", "Build wm-seed", "build", JobClass.RELEASE, Lane.D_RELEASE,
             notes="Cross-platform matrix, release-only"),
]


def get_jobs_by_lane(lane: Lane) -> list[JobEntry]:
    """Get all jobs assigned to a specific lane."""
    return [j for j in INVENTORY if j.lane == lane]


def get_jobs_by_workflow(workflow: str) -> list[JobEntry]:
    """Get all jobs in a specific workflow file."""
    return [j for j in INVENTORY if j.workflow == workflow]


def get_false_green_jobs() -> list[JobEntry]:
    """Get all jobs with continue-on-error, || true, or pipe masking."""
    return [j for j in INVENTORY if j.has_continue_on_error or j.has_or_true or j.has_pipe_mask]


def get_duplicate_groups() -> dict[str, list[str]]:
    """Get groups of duplicate jobs across workflows."""
    groups: dict[str, list[str]] = {}
    for j in INVENTORY:
        for dup in j.duplicates:
            key = tuple(sorted([f"{j.workflow}:{j.job_id}", dup]))
            label = " + ".join(key)
            if label not in groups:
                groups[label] = [f"{j.workflow}:{j.job_id}", dup]
    return groups


def get_summary() -> dict[str, int]:
    """Get summary counts."""
    return {
        "total_jobs": len(INVENTORY),
        "blocking": sum(1 for j in INVENTORY if j.classification == JobClass.BLOCKING),
        "advisory": sum(1 for j in INVENTORY if j.classification == JobClass.ADVISORY),
        "nightly": sum(1 for j in INVENTORY if j.classification == JobClass.NIGHTLY),
        "release": sum(1 for j in INVENTORY if j.classification == JobClass.RELEASE),
        "lane_a": len(get_jobs_by_lane(Lane.A_PR_FAST)),
        "lane_b": len(get_jobs_by_lane(Lane.B_PR_INTEGRATION)),
        "lane_c": len(get_jobs_by_lane(Lane.C_NIGHTLY)),
        "lane_d": len(get_jobs_by_lane(Lane.D_RELEASE)),
        "false_green": len(get_false_green_jobs()),
        "duplicates": len(get_duplicate_groups()),
    }


# ─── Lane definitions ──────────────────────────────────────────────────

LANE_DEFINITIONS = {
    Lane.A_PR_FAST: {
        "name": "Pull-request fast gate",
        "target": "<10 minutes",
        "jobs": [
            "ci.yml: core, lint, rust-quality, security, extras",
            "ci.yml: version-consistency, doc-drift, site-facts, stub-audit",
            "core-ci.yml: lint, stubs, duplicates, typecheck",
            "site-ci.yml: typecheck, lint, catalog-consistency",
        ],
        "install": "uv sync --frozen --no-dev",
        "checks": [
            "Contract validation (verify tests)",
            "Registry completeness/safety",
            "Version and fact drift",
            "Ruff no-new-debt gate",
            "Strict-boundary types",
            "Frontend typecheck/lint",
            "Leak detection (pytest --hygiene-strict)",
        ],
    },
    Lane.B_PR_INTEGRATION: {
        "name": "Pull-request integration",
        "target": "<25 minutes",
        "jobs": [
            "ci.yml: optional-opt, packaging",
            "core-ci.yml: test (xdist parallel)",
            "security-ci.yml: all 6 jobs",
            "site-ci.yml: build",
            "wasm-cicd.yml: build-wasm, build-docker, build-python",
        ],
        "install": "uv sync --frozen --all-extras --dev",
        "checks": [
            "SQLite/memory integration",
            "Dispatch/runtime integration",
            "Security/governance tests",
            "Frontend production build",
            "Package build and minimal-install smoke",
            "WASM build verification",
        ],
    },
    Lane.C_NIGHTLY: {
        "name": "Nightly",
        "target": "unlimited",
        "jobs": [
            "ci.yml: reproducible-build, coverage, network-optin",
            "site-ci.yml: smoke (32 routes)",
            "slither.yml: slither",
        ],
        "install": "uv sync --frozen (full dependency groups)",
        "checks": [
            "Full supported suite (random order, seeds 42+777)",
            "Supported native bridges",
            "Performance benchmarks (P6.3/P6.4/P6.5)",
            "Vulnerability scans",
            "Random-order/repeat tests",
            "Heavy optional integrations",
            "Coverage report",
            "Reproducible build verification",
        ],
    },
    Lane.D_RELEASE: {
        "name": "Release",
        "target": "unlimited",
        "jobs": [
            "release.yml: ci-gate, build-and-publish, docker",
            "publish.yml: publish-pypi, publish-seed-binaries",
            "wasm-cicd.yml: publish-npm",
            "seed-binaries.yml: build (matrix)",
        ],
        "install": "Locked clean install",
        "checks": [
            "Repeated full supported suite",
            "Wheel/sdist inspection",
            "Minimal and supported-full smoke",
            "Generated docs/facts",
            "Changelog/version/tag checks",
            "Artifact checksums/signing (sigstore)",
            "SBOM generation (CycloneDX)",
            "Docker image build + push",
        ],
    },
}
