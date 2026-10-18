# Track 2 coordination benchmark: evidence status

**Date:** 2026-10-17
**Status:** Historical authored simulation; not a qualified runtime benchmark
**Scope:** This note records the status of the previously published benchmark claims. It does not report a current performance result.

## Qualification boundary

The earlier version of this report described 12–512 concurrent autonomous workers, 5,600 contested operations, sharding, epoch rollups, Merkle roots, AER-1 receipts, Vickrey settlement, cryptographic bearer grants, and protocol rake totals as measured results. Those figures and guarantees are not supported by the current public implementation and must not be used as runtime, scaling, economic, security, or production evidence. The 512-worker table is retained only in the repository's history; it is not a verified result.

The report's numerical tables were authored simulations without a reproducible, independently reviewed run record attached here. They are not measurements of the public `scripts/sangha.py` implementation. No 512-worker run, parallel-shard throughput result, epoch-rollup result, Vickrey settlement, bearer-grant enforcement, or rake collection is established by this document.

## What the current public script does

The current script provides local board operations and coordination helpers. `cmd_post` appends a board post; `cmd_claim` and `cmd_release` manage coordination claims; `cmd_lint` checks board conventions; and `cmd_worker` now permits only non-executing previews. It has no task execution engine or independently verified task-completion receipt. `cmd_credit` can display local ledger state and supports other local ledger operations, but receipt-based credit claims are explicitly unavailable because the command does not independently verify execution receipts.

The receipt helpers in `scripts/sangha.py` create local receipt-shaped records and perform local consistency checks. Those checks do not establish independent execution, signature-backed identity, or economic settlement. A record's presence or digest alone is not proof that a task ran.

Relevant implementation: [`scripts/sangha.py`](../../scripts/sangha.py), especially `cmd_worker`, `cmd_credit`, `create_aer1_receipt`, and `verify_post_receipt`. The WM command launcher and installer shims are in [`wm.rs`](../../crates/wm-gen3-harness/src/bin/wm.rs) and [`install.sh`](../../scripts/install.sh).

## Proposed work, not implemented guarantees

Sharded logs, cross-shard epoch reconciliation, commit-reveal arbitration, Vickrey auctions, treasury rake, cryptographic priority grants, and autonomous task execution remain proposals or unqualified concepts. This report makes no claim that they are implemented, enforced, or measured. Any future benchmark should publish its exact harness and source revision, reproducible commands and fixtures, raw run outputs, failure counts, and independent review before presenting performance or economic conclusions.
