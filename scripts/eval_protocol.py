#!/usr/bin/env python3
"""Versioned scoring and evidence helpers for WhiteMagic evaluation runners.

Legacy metrics are preserved for historical comparison.  Strict metrics are
separate fields: they never overwrite or reinterpret a legacy score.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

LEGACY_PROTOCOL = "wm-retrieval-legacy-v1"
STRICT_PROTOCOL = "wm-evidence-strict-v1"
GROUPED_SOURCE_PROTOCOL = "wm-source-groups-v1"
MANIFEST_SCHEMA = "wm-evaluation-run-manifest-v1"


def normalized(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def result_id(result: dict[str, Any]) -> str:
    return str(result.get("id", result.get("memory_id", "")))


def supports_reference_text(content: str, answer: str) -> bool:
    """Conservative literal support: present, but not directly negated."""
    content_clean = normalized(content)
    answer_clean = normalized(answer)
    if len(answer_clean) < 3 or answer_clean not in content_clean:
        return False
    negated = re.compile(rf"\b(?:not|never|isn't|wasn't|no)\b[^.!?]{{0,40}}\b{re.escape(answer_clean)}\b")
    return negated.search(content_clean) is None


def legacy_longmemeval_score(
    results: list[dict[str, Any]], answer: str, answer_memory_ids: set[str]
) -> dict[str, Any]:
    """Historical ID-or-answer-substring retrieval proxy."""
    answer_clean = normalized(answer)
    ranks = []
    for rank, result in enumerate(results, 1):
        id_match = result_id(result) in answer_memory_ids
        text_match = len(answer_clean) >= 3 and answer_clean in normalized(
            result.get("content", result.get("content_preview", ""))
        )
        if id_match or text_match:
            ranks.append(rank)
    return {
        "recall_at_1": int(any(rank <= 1 for rank in ranks)),
        "recall_at_5": int(any(rank <= 5 for rank in ranks)),
        "recall_at_10": int(any(rank <= 10 for rank in ranks)),
        "mrr": 1.0 / ranks[0] if ranks else 0.0,
        "first_match_rank": ranks[0] if ranks else None,
    }


def strict_evidence_score(
    results: list[dict[str, Any]], required_memory_ids: set[str]
) -> dict[str, Any]:
    """Score source identity and coverage without pretending to judge answers."""
    ranked_ids = [result_id(result) for result in results]
    relevant_ranks = [
        rank for rank, memory_id in enumerate(ranked_ids, 1)
        if memory_id and memory_id in required_memory_ids
    ]
    found = set(ranked_ids) & required_memory_ids
    denominator = len(required_memory_ids)
    return {
        "protocol": STRICT_PROTOCOL,
        "relevant_source_hit_at_1": int(any(rank <= 1 for rank in relevant_ranks)),
        "relevant_source_hit_at_5": int(any(rank <= 5 for rank in relevant_ranks)),
        "relevant_source_mrr": 1.0 / relevant_ranks[0] if relevant_ranks else 0.0,
        "required_evidence_found": len(found),
        "required_evidence_total": denominator,
        "required_evidence_coverage_at_retrieval_limit": len(found) / denominator if denominator else None,
        "retrieval_limit": len(results),
        "supported_answer_correctness": None,
        "supported_answer_correctness_status": "not_applicable_no_answer_model",
    }


def _source_ref_key(ref: dict[str, Any], dataset_sha256: str) -> tuple[Any, ...]:
    """Return the stable identity fields used by grouped-source annotations."""
    span = ref.get("span", {})
    return (
        ref.get("dataset_sha256", dataset_sha256),
        ref.get("session_id"),
        ref.get("turn_index"),
        span.get("start"),
        span.get("end"),
        ref.get("text_sha256"),
    )


def grouped_source_score(
    results: list[dict[str, Any]],
    annotation: dict[str, Any],
    memory_source_refs: dict[str, dict[str, Any]],
    *,
    cutoffs: tuple[int, ...] = (1, 5, 10),
) -> dict[str, Any]:
    """Measure all-of evidence groups with one-of alternative source spans.

    The annotation identifies dataset sources; ``memory_source_refs`` connects
    run-specific memory IDs to those stable identities.  This is retrieval-only
    scoring and deliberately makes no claim about answer correctness.
    """
    if annotation.get("protocol") != GROUPED_SOURCE_PROTOCOL:
        return {
            "protocol": GROUPED_SOURCE_PROTOCOL,
            "supported": False,
            "unsupported_reason": "missing_or_unknown_grouped_source_protocol",
            "supported_answer_correctness": None,
            "supported_answer_correctness_status": "not_applicable_no_answer_model",
        }
    dataset_sha256 = str(annotation.get("dataset", {}).get("sha256", ""))
    groups = annotation.get("groups")
    if not dataset_sha256 or not isinstance(groups, list) or not groups:
        return {
            "protocol": GROUPED_SOURCE_PROTOCOL,
            "supported": False,
            "unsupported_reason": "invalid_grouped_source_annotation",
            "supported_answer_correctness": None,
            "supported_answer_correctness_status": "not_applicable_no_answer_model",
        }

    ranked_keys: list[tuple[Any, ...] | None] = []
    for result in results:
        ref = memory_source_refs.get(result_id(result))
        ranked_keys.append(_source_ref_key(ref, dataset_sha256) if ref else None)

    group_first_ranks: dict[str, int | None] = {}
    for group in groups:
        group_id = str(group.get("group_id", ""))
        alternatives = group.get("alternatives", [])
        if not group_id or not isinstance(alternatives, list) or not alternatives:
            return {
                "protocol": GROUPED_SOURCE_PROTOCOL,
                "supported": False,
                "unsupported_reason": "invalid_evidence_group",
                "supported_answer_correctness": None,
                "supported_answer_correctness_status": "not_applicable_no_answer_model",
            }
        alternative_keys = {
            _source_ref_key(alternative, dataset_sha256)
            for alternative in alternatives
        }
        group_first_ranks[group_id] = next(
            (rank for rank, key in enumerate(ranked_keys, 1) if key in alternative_keys),
            None,
        )

    cutoff_metrics: dict[str, dict[str, Any]] = {}
    total = len(group_first_ranks)
    for cutoff in sorted(set(cutoffs)):
        if cutoff < 1:
            raise ValueError("grouped-source cutoffs must be positive")
        found = sum(
            rank is not None and rank <= cutoff
            for rank in group_first_ranks.values()
        )
        cutoff_metrics[str(cutoff)] = {
            "required_groups_found": found,
            "required_groups_total": total,
            "required_group_coverage": found / total,
            "complete_evidence_bundle": found == total,
        }

    return {
        "protocol": GROUPED_SOURCE_PROTOCOL,
        "supported": True,
        "aggregation": "all_of_groups_with_one_of_alternatives",
        "group_first_ranks": group_first_ranks,
        "cutoffs": cutoff_metrics,
        "supported_answer_correctness": None,
        "supported_answer_correctness_status": "not_applicable_no_answer_model",
    }


def strict_abstention(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Missing/non-numeric scores invalidate, rather than pass, abstention."""
    if not results:
        return {"valid": True, "passed": True, "reason": "no_results"}
    scores = []
    for index, result in enumerate(results[:3]):
        score = result.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            return {
                "valid": False,
                "passed": False,
                "reason": "missing_non_numeric_or_non_finite_score",
                "result_index": index,
            }
        scores.append(float(score))
    return {
        "valid": True,
        "passed": max(scores) < 0.01,
        "reason": "scores_below_threshold" if max(scores) < 0.01 else "score_above_threshold",
    }


def audit_jsonrpc_batch(
    responses: list[dict[str, Any]], ingestion_ids: list[int], retrieval_id: int
) -> list[dict[str, Any]]:
    """Classify missing, malformed, error, and partial responses completely."""
    failures: list[dict[str, Any]] = []
    by_id: dict[Any, dict[str, Any]] = {}
    for index, response in enumerate(responses):
        if not isinstance(response, dict):
            failures.append({"stage": "malformed_response", "index": index, "detail": repr(response)})
            continue
        response_id = response.get("id")
        if response_id is None:
            failures.append({"stage": "malformed_response", "index": index, "detail": "missing id"})
            continue
        by_id[response_id] = response

    for response_id in ingestion_ids:
        response = by_id.get(response_id)
        if response is None:
            failures.append({"stage": "partial_ingestion", "request_id": response_id, "detail": "missing response"})
            continue
        if response.get("error") or response.get("result", {}).get("isError") is True:
            failures.append({"stage": "ingestion", "request_id": response_id, "detail": response.get("error", "MCP result isError=true")})
            continue
        payload = parse_jsonrpc_payload(response)
        if not payload.get("valid") or payload.get("payload", {}).get("status") != "success":
            failures.append({"stage": "ingestion", "request_id": response_id, "detail": payload})

    response = by_id.get(retrieval_id)
    if response is None:
        failures.append({"stage": "retrieval", "request_id": retrieval_id, "detail": "missing response"})
    elif response.get("error") or response.get("result", {}).get("isError") is True:
        failures.append({"stage": "retrieval", "request_id": retrieval_id, "detail": response.get("error", "MCP result isError=true")})
    else:
        payload = parse_jsonrpc_payload(response)
        if not payload.get("valid"):
            failures.append({"stage": "retrieval", "request_id": retrieval_id, "detail": payload})
        elif payload.get("payload", {}).get("status") not in (None, "success"):
            failures.append({"stage": "retrieval", "request_id": retrieval_id, "detail": payload})
        elif not isinstance(payload.get("payload", {}).get("results", payload.get("payload", {}).get("memories")), list):
            failures.append({"stage": "retrieval", "request_id": retrieval_id, "detail": "missing results list"})
    return failures


def parse_jsonrpc_payload(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["result"]["content"]
        text = content[0]["text"]
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise TypeError("inner payload is not an object")
        return {"valid": True, "payload": payload}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return {"valid": False, "error": f"{type(exc).__name__}: {exc}"}


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    *, runner: str, binary: str, dataset: str, output: str,
    command: list[str], configuration: dict[str, Any], failures: list[dict[str, Any]],
    annotations: list[str] | None = None,
) -> dict[str, Any]:
    """Build a reproducible manifest after output is durable on disk."""
    repo = Path(__file__).resolve().parent.parent
    def git(*args: str) -> str | None:
        completed = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
        return completed.stdout.strip() if completed.returncode == 0 else None
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "protocols": {"legacy": LEGACY_PROTOCOL, "strict": STRICT_PROTOCOL, "grouped_source": GROUPED_SOURCE_PROTOCOL},
        "command": command,
        "runner": {"path": str(Path(runner).resolve()), "sha256": sha256_file(runner)},
        "protocol_helper": {"path": str(Path(__file__).resolve()), "sha256": sha256_file(__file__)},
        "binary": {"path": str(Path(binary).resolve()), "sha256": sha256_file(binary)},
        "dataset": {"path": str(Path(dataset).resolve()), "sha256": sha256_file(dataset)},
        "output": {"path": str(Path(output).resolve()), "sha256": sha256_file(output)},
        "repository": {"path": str(repo), "branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"), "diff_sha256": hashlib.sha256((git("diff", "--binary") or "").encode()).hexdigest()},
        "configuration": configuration,
        "environment": {"python": sys.version, "platform": platform.platform(), "answer_generation_model": None},
        "valid_execution": not failures,
        "failures": failures,
    }
    if annotations is not None:
        manifest["annotations"] = [
            {"path": str(Path(path).resolve()), "sha256": sha256_file(path)}
            for path in annotations
        ]
    return manifest


def write_failure_receipt(
    *, receipt_path: str, runner: str, binary: str | None, dataset: str | None,
    command: list[str], stage: str, error: BaseException,
) -> None:
    """Write a machine-readable receipt even when no result file exists."""
    failure = {"stage": stage, "error_type": type(error).__name__, "detail": str(error)}
    def identity(path: str | None) -> dict[str, Any] | None:
        if path is None:
            return None
        resolved = Path(path).resolve()
        return {
            "path": str(resolved),
            "exists": resolved.is_file(),
            "sha256": sha256_file(resolved) if resolved.is_file() else None,
        }
    receipt = {
        "schema": MANIFEST_SCHEMA,
        "receipt_type": "pre_output_failure",
        "protocols": {"legacy": LEGACY_PROTOCOL, "strict": STRICT_PROTOCOL, "grouped_source": GROUPED_SOURCE_PROTOCOL},
        "command": command,
        "runner": identity(runner),
        "protocol_helper": identity(__file__),
        "binary": identity(binary),
        "dataset": identity(dataset),
        "output": None,
        "environment": {"python": sys.version, "platform": platform.platform(), "answer_generation_model": None},
        "valid_execution": False,
        "failures": [failure],
    }
    output = Path(receipt_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
