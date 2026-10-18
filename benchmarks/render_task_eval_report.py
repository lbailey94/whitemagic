#!/usr/bin/env python3
"""Render the authored task measurements from their pinned machine record."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def render(record):
    families = record["summary_by_family"]
    cont = families["T_CONTINUITY_cross_session_decision_recovery"]
    conflict = families["T_CONFLICT_stale_and_conflicting_memory"]
    repair = families["T_REPAIR_surgical_bad_memory_repair"]
    discovery = families["T_DISCOVERY_authored_cue_guided_migration"]
    wm_c, wm_m, wm_r = (family["whitemagic_v10_4"] for family in (cont, conflict, repair))
    wm_d = discovery["whitemagic_cue_guided_migration"]
    pct = lambda value: f"{100 * value:.2f}%"
    calls = record["runtime_call_accounting"]
    scenarios = {family["family"]: family["scenarios"] for family in record["families"]}
    context_bytes = [case["whitemagic_v10_4"]["context_bytes"] for case in scenarios["T_CONTINUITY"]]
    source = record["source_provenance"]
    lines = [
        "# Authored memory-task regression measurements",
        "",
        f"Generated from `pinned-task-eval-results.json` at {record['generated_at']}. "
        f"The corpus contains {record['total_scenarios']} authored scenarios, eight per family. "
        "There is no connected model, unseen holdout, autonomous agent study, or general-performance qualification.",
        "",
        "| Task and scored outcome | WhiteMagic source candidate | Structured file comparison |",
        "|---|---:|---:|",
        f"| Continuity: decision recall, all eight cases | {pct(wm_c['mean_decision_recall_all_8'])} | {pct(cont['structured_metadata_files_equal_info']['mean_decision_recall_all_8'])} |",
        f"| Continuity: exact open-arc check | {pct(wm_c['mean_open_arc_precision'])} | {pct(cont['structured_metadata_files_equal_info']['mean_open_arc_precision'])} |",
        f"| Conflict: governed current truth, seven cases | {pct(wm_m['top1_current_truth_rate_governed_7'])} | {pct(conflict['structured_supersedes_files_equal_info']['top1_current_truth_rate_governed_7'])} |",
        f"| Repair: poison-free repaired identity in top three | {pct(wm_r['poison_free_and_repaired_in_top3_rate'])} | {pct(repair['record_addressed_files_equal_info']['poison_free_and_repaired_in_top3_rate'])} |",
        f"| Repair: repaired identity at rank one | {pct(wm_r['repaired_at_rank1_rate'])} | {pct(repair['record_addressed_files_equal_info']['repaired_at_rank1_rate'])} |",
        f"| Repair: legitimate neighbor state preserved | {pct(wm_r['legitimate_state_preserved_rate'])} | {pct(repair['record_addressed_files_equal_info']['legitimate_state_preserved_rate'])} |",
        f"| Cue-guided migration: obsolete-target recall | {pct(wm_d['mean_target_discovery_recall'])} | {pct(discovery['equal_information_files']['mean_target_discovery_recall'])} |",
        f"| Cue-guided migration: end-to-end workflow | {pct(wm_d['end_to_end_success_rate'])} | {pct(discovery['equal_information_files']['end_to_end_success_rate'])} |",
        "",
        f"Continuity scores only the exact compact `agent_context.text` string under the {cont['compact_context_byte_cap']:,}-byte UTF-8 cap. "
        f"Mean of per-context ceil(bytes/4) token estimates is {wm_c['mean_tokens_used']}; largest observed context is {max(context_bytes)} bytes. "
        "This estimate is not a model-tokenizer guarantee. Every consumed turn, checkpoint, queue, flag, crystal and briefing is inside the string; transport/debug metadata is excluded.",
        "",
        "The structured continuity files receive the same turn metadata, resolution links and typed/importance/content salience rules. "
        "They serialize turns only; WhiteMagic may include derived checkpoint, queue, flag and crystal fields. Wire overhead is not equal. "
        "The text heuristic can match quoted or otherwise invalid claims; it does not establish authority or truth.",
        "",
        f"Conflict current truth across all eight cases is {pct(wm_m['top1_current_truth_rate_all_8'])}. "
        "M8 deliberately writes an unlinked contradiction, retaining the boundary that ungoverned text is not a supersession operation. "
        f"Governed lineage verification is {pct(wm_m['lineage_verifiable_rate_governed_7'])}; the structured supersedes files do not provide a cryptographic revision DAG.",
        "",
        f"Discovery corpus sizes are {sorted(set(discovery['corpus_records_per_case']))} records per case, two obsolete and three legitimate; "
        f"there are {discovery['legitimate_neighbors_total']} legitimate neighbors overall. "
        "Both adapters receive the exact stale clues, search query and authoritative replacement. IDs do not reveal labels. "
        "The adapter uses bounded phrase/negation patterns; unfamiliar paraphrases can fail. "
        "WhiteMagic's workflow reads every obsolete ID to verify retirement to the expected head and separately verifies the converging DAG.",
        "",
        f"Runtime accounting: {calls['attempted']} requested calls, {calls['explicit_success']} explicit successful responses, "
        f"{calls['failed_or_unverified']} failed/unverified, {calls['ignored']} ignored. "
        "Protocol, response identity, lifecycle and byte-contract errors abort the run. Exit zero means measurement execution completed; inspect task scores and traces for task failures. "
        "Latency includes fresh process startup and unequal tool batches, so this run establishes no latency or operating-cost advantage.",
        "",
        "## Reproduction and identity",
        "",
        "```bash",
        "WM_BINARY=/absolute/path/to/reviewed/wm python3 benchmarks/pinned_task_eval.py",
        "python3 -m unittest discover -s benchmarks -p test_pinned_task_eval.py",
        "python3 benchmarks/render_task_eval_report.py",
        "```",
        "",
        f"- Source parent/commit: `{source['git_head']}`; tracked runtime diff SHA-256: `{source['tracked_diff_sha256']}`.",
        f"- Exact binary SHA-256: `{record['binary']['sha256']}`; reported version: `{source['binary_version_stdout']}`.",
        f"- Harness SHA-256: `{record['harness_sha256']}`.",
        f"- Raw call audit SHA-256: `{record['runtime_call_audit_sha256']}`; a gzip copy is retained as `runtime-call-audit.json.gz`.",
        "- Source file hashes are recorded in the JSON. A source candidate reporting the same version as a release is not necessarily the signed published binary.",
        "- Earlier v10.4.0 fixture results remain in `historical/pinned-task-eval-results-19169fa.json`; earlier code is preserved at Git commit `19169fa`.",
        "",
        "## Observed failure and boundary traces",
        "",
        "```json",
        json.dumps(record["documented_failure_traces"], indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    record = json.loads((HERE / "pinned-task-eval-results.json").read_text())
    (HERE / "TASK_EVAL_REPORT.md").write_text(render(record))
