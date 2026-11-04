# Native sandbox execution envelopes

`wm-sandbox --exec '<json>'` accepts an object with required nonempty string
`program` and optional string-array `args`, boolean `net`, string `workspace`,
boolean `rw`, and an empty `egress` array. `schema`, when supplied, must be
`"wm-sandbox-exec-v1"`. Omitting the schema remains supported for existing callers.
Omitted arguments default to `[]`; `net` and `rw` default to `false`.

Unknown or duplicate fields, wrong types (including `null`), empty workspace
paths, NUL characters in program/arguments/workspace, and `rw:true` without a
workspace fail with exit 64 before confinement setup or command execution.
Arguments are passed literally, without a shell or silent removal of invalid
members.

```sh
wm-sandbox --exec '{"schema":"wm-sandbox-exec-v1","program":"/usr/bin/printf","args":["[%s]\n","a b","$HOME"],"net":false}'
```

The workspace adds a read-only or read-write path to the existing builder grants;
it does not mount a new `/workspace` path, change the working directory, remove
default grants, or make a path read-only if a broader default grant is writable.
`net:true` selects the builder's existing network-permission mode. This runner
does not implement destination allowlists: nonempty `egress` is refused rather
than silently ignored. Empty `egress:[]` remains compatible with envelopes that
emit an explicit empty declaration.

Both the envelope and ordinary command forms refuse execution with exit 126 if
Landlock setup fails, including an unsupported kernel. Parser and builder tests
do not qualify all filesystem, network-protocol, IPC, cgroup, or hostile-tenant
containment properties. The CLI tests check literal argument delivery and the
absence of payload markers after malformed input or a forced setup failure.
