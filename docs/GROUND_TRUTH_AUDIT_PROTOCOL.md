# Ground-truth validity audit protocol (frozen v1)

**Status: FROZEN 2026-09-16, before seeds 16–20 are scored.** Wrapper-side only; the substrate
never sees this rule. Purpose: mechanically flag questions where the **labeled** current value
has been superseded by a later statement in the same corpus, while the generator's answer key
retains the earlier value (the seed-2 `book_genre` case). Such questions remain visible and
scored; they are additionally reported as `ground_truth_ambiguous`.

---

## 1. Frozen rule

For each T1/T6 question `q` with label `L = q.answer`, topic key `T` and the scenario's ingest
turn order:

1. Let `A` = indexes of turns containing `L` (case-insensitive). If none → not applicable.
2. Flag `q` as **`ground_truth_ambiguous`** iff there exists a turn `u` with `index > max(A)` such
   that **all** of:
   - **(a)** `u` contains `T` as a **word-boundary token** (case-insensitive; `_` matches `_` or
     space; no raw-substring matches — `sport` must not match `transport`),
   - **(b)** `u` contains ≥ 1 assertion marker from the frozen list:
     `favorite · prefer · love · into · switched · changed my mind · go with · goes with ·
     all about · my choice · used to`,
   - **(c)** `u` does **not** contain `L` (case-insensitive).
3. Record: `question_id`, `label`, flagged turn index + text, matched marker.

**Topic key resolution (pinned, v1.1):** (1) the question-id suffix after the category prefix
(e.g., `T1_book_genre` → `book_genre`) — canonical in this corpus; else (2) `metadata.topic`
when present; else (3) the longest shared token (len ≥ 3, non-stopword) between the question and
the labeled answer turn; ties → lexicographic. If none → `audit_inapplicable: true`, not
flagged. *(v1.1 note, 2026-09-16, pre-run: v1's fallback could select a generic key such as
`favorite`, producing cross-topic false flags; the question-id suffix is the correct canonical
source. No scored run had used v1.)*

## 2. Reporting (pinned)

Both scorings are always reported together:

- **Raw** — the benchmark protocol unchanged (all questions).
- **Adjudicated** — the same computation with flagged questions excluded; the flag list is
  always published alongside. Flagged questions are **never deleted or modified**.

## 3. Assembly and freeze

The rule text above and the marker list are frozen before scoring seeds 16–20. Any change after
a scored run re-baselines that run. The audit is demonstration-validated on seeds 1–15 (already
scored; no new information is created — it is an audit of labels, not of substrate behavior).

---

# Revision v1.3 (2026-09-16) — task-update marker set + topic-match fix

**Status: FROZEN before any Testbed II (A) scoring. Applies to Testbed II corpora only.**
Supersedes v1.2 for those corpora; v1.2 remains the frozen rule for Phase 2 (MemoraStrict)
corpora. v1.3 exists because pre-pilot finding **F1** (the v1.2 topic regex only matches
literal underscores: under Python 3.12 `re.escape` leaves `_` unescaped, so the
`.replace("\\_", "[_ ]")` is dead code) and finding **F2** (the v1.2 marker list is
preference-phrased; task-update wording is not caught) make v1.2 inapplicable to the
work-log corpus family.

## 1. Frozen rule (v1.3)

For each T1/T6 question `q` with label `L = q.answer`, topic key `T` and the scenario's ingest
turn order:

1. Let `A` = indexes of turns containing `L` (case-insensitive). If none → not applicable.
2. Flag `q` as **`ground_truth_ambiguous`** iff there exists a turn `u` with `index > max(A)` such
   that **all** of:
   - **(a)** `u` contains `T` as a **word-boundary token** (case-insensitive; `_` matches `_` or
     space; no raw-substring matches — `sport` must not match `transport`),
   - **(b)** `u` contains ≥ 1 assertion marker from the frozen v1.3 list (task-update verbs):
     `moved to · shifted to · changed to · switched to · replaced by · now kept in · relocated to ·
     reassigned to · handed over to · transferred to · bumped to · cut to · raised to · retired`,
   - **(c)** `u` does **not** contain `L` (case-insensitive).
3. Record: `question_id`, `label`, flagged turn index + text, matched marker.

**Topic key resolution (pinned, unchanged from v1.1):** (1) the question-id suffix after the
category prefix (Testbed II qid convention: single token); else (2) `metadata.topic`; else (3)
the longest shared token (len ≥ 3, non-stopword) between question and labeled answer turn;
ties → lexicographic. If none → `audit_inapplicable: true`.

**F1 fix:** the topic regex is built as `re.compile(r"(?<![a-z0-9])" + re.escape(T).replace("_", "[_ ]") + r"(?![a-z0-9])", re.IGNORECASE)`. Note the replacement operates on the *unescaped* underscore directly (`re.escape` leaves `_` unescaped on Python 3.12); the v1.2 code replaced the literal two-character sequence `\_` which never occurs. Belt-and-braces: Testbed II qid topics are single tokens by generator contract, so `_` should not occur.

## 2. Reporting (unchanged from v1)

Raw + adjudicated always together; flags published, never deleted or modified.

## 3. Assembly and freeze

Frozen by commit before the first Testbed II (A) harness invocation. Positive controls: the 20
stale-label T1 questions (2 per seed, 301–310) must be flagged; negative controls: the 40
correct-label T1/T6 must not be flagged; T8/T2 are structurally inapplicable (not scanned).
v1.2 stays pinned for Phase 2 corpora — no re-baselining.
