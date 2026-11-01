# Supersession identifiers

A recall hit can expose two different identifiers for a `Supersedes` relation. The edge points from the successor record (`src`) to the superseded record (`dst`). For a hit on `dst`:

- `superseded_by_record_id` is the successor record ID (`src`).
- `superseded_by_relation_id` is the ID of the `Supersedes` edge.
- Legacy recall `superseded_by` remains the relation ID for compatibility.

All three recall fields are present and `null` for an unsuperseded hit. Search aliases return the same fields. These are additive JSON fields; the public Rust `Hit` type also has new fields, so downstream struct literal construction must name them or use an applicable default update.

`memory.read` keeps its older `superseded_by` meaning: successor record ID from the revision journal. Its explicit pair describes one selected stored edge using the same direction and relation ordering as recall. In inconsistent or forked state, the legacy journal successor can differ from `superseded_by_record_id`; the explicit pair itself always comes from one stored edge. A missing stored edge gives null explicit fields. Neither surface resolves temporal authority or reconciles forks.
