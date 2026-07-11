/** WhiteMagic SDK — Unified export */

export { WhiteMagicClient, type ClientOptions } from "./client.js";
export { MemoryOps } from "./memory.js";
export { GovernanceOps } from "./governance.js";
export { SystemOps } from "./system.js";
export { AgentOps } from "./agent.js";
export type {
  ToolResult,
  Memory,
  MemoryCreateRequest,
  MemorySearchRequest,
  MemorySearchResult,
  Galaxy,
  DharmaEvaluation,
  KarmaEntry,
  SystemStatus,
  MCPRequest,
  MCPResponse,
} from "./types.js";
