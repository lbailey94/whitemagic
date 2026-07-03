# @whitemagic/sdk

TypeScript client SDK for WhiteMagic — local-first agent governance and metacognition substrate for AI agents.

## Installation

```bash
npm install @whitemagic/sdk
```

## Quick Start

```typescript
import { WhiteMagicClient, MemoryOps, SystemOps } from "@whitemagic/sdk";

// Stdio transport (spawns local Python backend)
const client = new WhiteMagicClient({
  transport: "stdio",
  command: "python3",
  args: ["-m", "whitemagic.run_mcp_lean"],
});

// Or HTTP transport (connect to running server)
const httpClient = new WhiteMagicClient({
  transport: "http",
  baseUrl: "http://localhost:8000",
});

// Initialize
await client.initialize();

// Memory operations
const memory = new MemoryOps(client);
const created = await memory.create({
  content: "Architectural decision: use HNSW for vector search",
  tags: ["architecture", "vector-search"],
  galaxy: "technical-debt",
});

const results = await memory.search({
  query: "vector search architecture",
  limit: 5,
  method: "hybrid",
});

// System health
const system = new SystemOps(client);
const status = await system.status();
console.log(`Memory count: ${status.memory_count}`);

client.close();
```

## API

### `WhiteMagicClient`

Low-level MCP client with stdio and HTTP transports.

- `callTool(name, args)` — invoke any registered tool
- `listTools()` — list all available tools
- `initialize()` — MCP handshake
- `close()` — clean up transport

### `MemoryOps`

High-level memory CRUD and search.

- `create(request)` — store a new memory
- `search(request)` — semantic/keyword/hybrid search
- `read(id)` — fetch memory by ID
- `update(id, updates)` — partial update
- `delete(id)` — remove memory

### `GovernanceOps`

Ethical governance and Dharma rules.

- `evaluateEthics(action, context?)` — evaluate against Dharma rules
- `checkBoundaries()` — system boundary check
- `karmaReport()` — Karma Ledger entries
- `harmonyVector()` — health snapshot

### `SystemOps`

System introspection.

- `status()` — full system snapshot
- `listTools()` — enumerate tools
- `initialize()` — handshake

### `AgentOps`

Multi-agent coordination.

- `register(name, capabilities)` — register an agent
- `list()` — list registered agents
- `heartbeat(agentId)` — send heartbeat

## Transport

**Stdio** (default): Spawns `python3 -m whitemagic.run_mcp_lean` as a child process. Best for local desktop apps and IDE plugins.

**HTTP**: Connects to a running WhiteMagic HTTP server. Best for web apps and remote access.

## License

MIT
