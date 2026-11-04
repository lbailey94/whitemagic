# Routing policy and local comparison metrics

`sutra.route` uses Tripartite by default. `WM_PROMOTE_VALKYRIE_L05=1` or
`true` explicitly selects the experimental L0.5 hybrid when its projection is
available; `0`/`false` disables promotion. Missing means disabled and other
values refuse the request. A temporal-answer trial does not qualify a routing
model. Use a separately frozen routing set before promoting a deployment.

The top-level tier/confidence/rationale belong to the selected router.
Tripartite glyph/corner/skeleton are null at the top level when hybrid is
selected; its complete independent decision remains in `tripartite`. `shadow`
contains the hybrid's own result, including agreement and availability.

No routing request text is persisted by default. `WM_ROUTING_METRICS=1` or
`true` opts into content-free tier/agreement metrics. `0`/`false`/missing
disables it; other values refuse the request. The response reports disabled,
recorded or failed. Each file is bounded to 1 MiB, with one previous file;
rotation is process-serialized, not a multi-process append protocol. Files
are created mode 0600 on Unix. There is no time-based deletion guarantee.

Historical `routing_shadow.jsonl` files may contain request snippets from older
versions. This change does not read, alter, migrate or delete those files.
