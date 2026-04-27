/** WhiteMagic SDK — Agent coordination */

import type { WhiteMagicClient } from "./client.js";

export class AgentOps {
  constructor(private client: WhiteMagicClient) {}

  /** Register a new agent */
  async register(name: string, capabilities: string[]): Promise<unknown> {
    const result = await this.client.callTool("gana_girl", {
      tool: "agent.register",
      args: { name, capabilities },
    });
    return result.details;
  }

  /** List registered agents */
  async list(): Promise<unknown> {
    const result = await this.client.callTool("gana_girl", {
      tool: "agent.list",
      args: {},
    });
    return result.details;
  }

  /** Send a heartbeat for an agent */
  async heartbeat(agentId: string): Promise<unknown> {
    const result = await this.client.callTool("gana_girl", {
      tool: "agent.heartbeat",
      args: { agent_id: agentId },
    });
    return result.details;
  }
}
