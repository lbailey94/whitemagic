# MCP protocol compatibility

The Gen3 JSON-RPC handler keeps its existing `initialize` lifecycle for legacy
clients that negotiate `2024-11-05`. It also implements the bounded MCP
`2026-07-28` core-tools path over stdio and Streamable HTTP. Modern requests are
stateless: each request carries its protocol version and client capabilities in
`params._meta`; the server does not reuse metadata from an earlier request.

This is a bounded compatibility candidate, not a full MCP conformance claim.
The maintained fixture uses raw JSON-RPC, not an official MCP SDK; no SDK is
pinned in this checkout. The stdio loop handles one message per line and
rejects modern batches. JSON-RPC notifications, including modern notifications
and no-ID messages whose method is `server/discover`, receive no response. The
stdio handler currently ignores cancellation notifications; it does not stop an
in-progress tool call. The MCP specification says servers SHOULD stop cancelled
work, while allowing cancellation to be ignored when a request is unknown,
already complete, or cannot be cancelled. Long-running stream cancellation,
request-scoped SSE, and modern subscriptions are not implemented by this
candidate.

The modern path advertises `2026-07-28` and the legacy `2024-11-05` version
through `server/discover`, exposes the `tools` capability, returns complete
discovery, tool-list, and tool-call result shapes, and uses the protocol's
unsupported-version error when a request selects another version. Legacy
`initialize` requests that offer a later legacy revision negotiate down to
`2024-11-05`, which is the legacy version this handler reports. `clientCapabilities` is required and an empty object is valid.
`clientInfo` is optional, consistent with the schema's SHOULD guidance.

For modern Streamable HTTP requests, `MCP-Protocol-Version` and `Mcp-Method`
are required and must match the JSON body. `Mcp-Name` is also required and
checked for `tools/call`. Mismatches return HTTP 400 with JSON-RPC error
`-32020`; unsupported versions return HTTP 400 with `-32022`. Modern HTTP
batches and client notifications are rejected. An `Origin` header is accepted
only for explicit loopback origins (`localhost`, `127.0.0.1`, or `::1`).

The candidate does not advertise support for MCP extensions, resources,
prompts, elicitation, tasks, subscriptions, or modern HTTP+SSE streaming. The
classic `/sse` transport remains the existing legacy transport. Legacy requests
without modern metadata continue through their previous handler path.

The maintained external fixture and latency driver is
`crates/wm-gen3-harness/tests/interop/mcp_compat_probe.py`. It launches only the
supplied binary and creates disposable stores under the caller-supplied
isolated store root.

## Protocol references

- [MCP 2026-07-28 versioning and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [MCP 2026-07-28 stdio binding](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [MCP 2026-07-28 Streamable HTTP binding](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP 2026-07-28 tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [Authoritative TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts)
