"""P8.1-P8.3 — CI inventory, lane classification, and false-green gate tests.

Tests that:
- The CI inventory is complete and matches actual workflow files
- Lane assignments are valid and cover all jobs
- Duplicate groups are identified
- False-green gates (continue-on-error, || true) are classified and ratcheted
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(REPO_ROOT / "core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "core"))

import pytest

from benchmarks.ci_inventory import (
    INVENTORY,
    JobClass,
    Lane,
    get_jobs_by_lane,
    get_jobs_by_workflow,
    get_false_green_jobs,
    get_duplicate_groups,
    get_summary,
    LANE_DEFINITIONS,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


# ─── P8.1: Inventory completeness ─────────────────────────────────────


class TestInventoryCompleteness:
    """P8.1 — Every workflow file and job is inventoried."""

    def test_inventory_non_empty(self):
        assert len(INVENTORY) > 0

    def test_all_workflow_files_covered(self):
        """Every .yml workflow file has at least one job in the inventory."""
        yml_files = {f.name for f in WORKFLOWS_DIR.glob("*.yml")}
        inventoried = {j.workflow for j in INVENTORY}
        missing = yml_files - inventoried
        assert not missing, f"Workflows not in inventory: {missing}"

    def test_inventory_has_expected_workflows(self):
        workflows = {j.workflow for j in INVENTORY}
        expected = {
            "ci.yml", "core-ci.yml", "security-ci.yml",
            "release.yml", "publish.yml", "site-ci.yml",
            "slither.yml", "wasm-cicd.yml", "seed-binaries.yml",
        }
        assert expected <= workflows

    def test_summary_counts_are_consistent(self):
        s = get_summary()
        assert s["total_jobs"] == len(INVENTORY)
        assert s["lane_a"] + s["lane_b"] + s["lane_c"] + s["lane_d"] + \
            sum(1 for j in INVENTORY if j.lane == Lane.NONE) == s["total_jobs"]

    def test_no_unclassified_jobs(self):
        """Every job has a lane assignment (not NONE)."""
        unassigned = [j for j in INVENTORY if j.lane == Lane.NONE]
        assert not unassigned, f"Jobs without lane: {[j.job_id for j in unassigned]}"

    def test_blocking_jobs_are_in_lanes_a_or_b(self):
        """Blocking jobs should be in PR fast or PR integration lanes."""
        for j in INVENTORY:
            if j.classification == JobClass.BLOCKING:
                assert j.lane in (Lane.A_PR_FAST, Lane.B_PR_INTEGRATION, Lane.D_RELEASE), \
                    f"Blocking job {j.workflow}:{j.job_id} in lane {j.lane}"

    def test_release_jobs_are_in_lane_d(self):
        for j in INVENTORY:
            if j.classification == JobClass.RELEASE:
                assert j.lane == Lane.D_RELEASE, \
                    f"Release job {j.workflow}:{j.job_id} in lane {j.lane}"


# ─── P8.2: Lane definitions ───────────────────────────────────────────


class TestLaneDefinitions:
    """P8.2 — Four CI lanes are defined with clear purpose."""

    def test_all_four_lanes_defined(self):
        assert Lane.A_PR_FAST in LANE_DEFINITIONS
        assert Lane.B_PR_INTEGRATION in LANE_DEFINITIONS
        assert Lane.C_NIGHTLY in LANE_DEFINITIONS
        assert Lane.D_RELEASE in LANE_DEFINITIONS

    def test_lane_a_has_fast_jobs(self):
        """Lane A should have jobs targeting <10 min."""
        lane_a = get_jobs_by_lane(Lane.A_PR_FAST)
        assert len(lane_a) >= 5

    def test_lane_b_has_integration_jobs(self):
        lane_b = get_jobs_by_lane(Lane.B_PR_INTEGRATION)
        assert len(lane_b) >= 3

    def test_lane_c_has_nightly_jobs(self):
        lane_c = get_jobs_by_lane(Lane.C_NIGHTLY)
        assert len(lane_c) >= 2

    def test_lane_d_has_release_jobs(self):
        lane_d = get_jobs_by_lane(Lane.D_RELEASE)
        assert len(lane_d) >= 3

    def test_lanes_are_disjoint(self):
        """No job appears in more than one lane."""
        all_job_ids = [f"{j.workflow}:{j.job_id}" for j in INVENTORY]
        assert len(all_job_ids) == len(set(all_job_ids)), "Duplicate job IDs found"


# ─── P8.3: False-green gate detection ─────────────────────────────────


class TestFalseGreenGates:
    """P8.3 — False-green gates are identified and ratcheted."""

    def test_false_green_jobs_identified(self):
        """All jobs with continue-on-error or || true are in the inventory."""
        fg = get_false_green_jobs()
        assert len(fg) >= 10, "Expected at least 10 false-green jobs"

    def test_false_green_count_ratcheted(self):
        """False-green count should not increase."""
        fg = get_false_green_jobs()
        baseline = 14
        assert len(fg) <= baseline, \
            f"False-green jobs grew to {len(fg)} (baseline {baseline}): " + \
            ", ".join(f"{j.workflow}:{j.job_id}" for j in fg)

    def test_advisory_jobs_are_marked_advisory(self):
        """Jobs with continue-on-error should be classified as ADVISORY or RELEASE."""
        for j in get_false_green_jobs():
            if j.classification != JobClass.RELEASE:
                assert j.classification == JobClass.ADVISORY, \
                    f"{j.workflow}:{j.job_id} has continue-on-error but is {j.classification}"

    def test_blocking_jobs_have_no_false_green(self):
        """Blocking jobs must not have continue-on-error."""
        for j in INVENTORY:
            if j.classification == JobClass.BLOCKING:
                assert not j.has_continue_on_error, \
                    f"Blocking job {j.workflow}:{j.job_id} has continue-on-error"


# ─── P8.1: Duplicate detection ────────────────────────────────────────


class TestDuplicateDetection:
    """P8.1 — Duplicate jobs across workflows are identified."""

    def test_duplicate_groups_found(self):
        groups = get_duplicate_groups()
        assert len(groups) >= 1, "Expected at least one duplicate group"

    def test_known_duplicates_identified(self):
        """Known duplicate: ci.yml:stub-audit and core-ci.yml:stubs."""
        groups = get_duplicate_groups()
        all_pairs = " ".join(groups.keys())
        assert "stub" in all_pairs.lower(), \
            f"Stub audit duplicate not found in: {list(groups.keys())}"

    def test_duplicate_count_ratcheted(self):
        """Duplicate count should not grow."""
        groups = get_duplicate_groups()
        baseline = 2
        assert len(groups) <= baseline, \
            f"Duplicate groups grew to {len(groups)} (baseline {baseline})"
