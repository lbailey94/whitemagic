/** WhiteMagic SDK — System introspection & health */

import type { WhiteMagicClient } from "./client.js";
import type { SystemStatus } from "./types.js";

export class SystemOps {
  constructor(private client: WhiteMagicClient) {}

  /** Full system status snapshot */
  async status(): Promise<SystemStatus> {
    const result = await this.client.callTool("gana_root", {
      tool: "health_report",
      args: {},
    });
    return result.details as unknown as SystemStatus;
  }

  /** List all available tools */
  async listTools(): Promise<unknown> {
    return this.client.listTools();
  }

  /** Initialize the system */
  async initialize(): Promise<unknown> {
    return this.client.initialize();
  }
}
