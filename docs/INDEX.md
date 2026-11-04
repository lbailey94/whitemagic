# Documentation index

Map of `docs/` for the WhiteMagic Gen3 line. The product contract is in
[`../README.md`](../README.md); agent onboarding is in [`../skill.md`](../skill.md).

## Operate

| Document | What it covers |
|---|---|
| [`SELFTEST_AND_HOST_HEALTH.md`](SELFTEST_AND_HOST_HEALTH.md) | `wm selftest`: persistence invariants, host-health checks + thresholds, `--strict`/`--json` contracts, guard/CI use |
| [`INSTALL.md`](../INSTALL.md) | source build, store location, optional model layer, verification |
| [`STORE_AND_DATA_HYGIENE.md`](STORE_AND_DATA_HYGIENE.md) | store/data layout and disposable-store policy |
| [`STORE_LAYOUT.md`](STORE_LAYOUT.md) | Gen3 store byte-level map: LMDB DBIs, sidecars, sizes, backup coverage, 32 GiB map policy |
| [`DEPENDENCY_MANIFEST.md`](DEPENDENCY_MANIFEST.md) | declared dependencies and exceptions |
| [`DERIVED_CACHE_POLICY.md`](DERIVED_CACHE_POLICY.md) | derived embedding cache and per-record projection vectors |

## Develop & Architecture

| Document | What it covers |
|---|---|
| [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) | Gen3 developer guide: workspace layout, build/test/lint commands, dispatch/authority model |
| [`CHARTER.md`](CHARTER.md) | binding constitutional core (tiers, closures, budgets) |
| [`ANSWER_CONTRACT.md`](ANSWER_CONTRACT.md) | answer contract and evidence expectations |
| [`SUTRA_GUIDE.md`](SUTRA_GUIDE.md) | vectorized logoglyphic sutra & mudra reference |
| [`specs/`](specs/) | behavioral specifications (`W1_*`, `W2_*`) |
