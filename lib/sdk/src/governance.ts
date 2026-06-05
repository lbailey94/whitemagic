/** WhiteMagic SDK — Governance & Dharma operations */

import type { WhiteMagicClient } from "./client.js";
import type { DharmaEvaluation, KarmaEntry } from "./types.js";

export class GovernanceOps {
  constructor(private client: WhiteMagicClient) {}

  /** Evaluate an action against Dharma rules */
  async evaluateEthics(action: string, context?: string): Promise<DharmaEvaluation> {
    const result = await this.client.callTool("gana_straddling_legs", {
      tool: "evaluate_ethics",
      args: { action, context },
    });
    return result.details as unknown as DharmaEvaluation;
  }

  /** Check system boundaries */
  async checkBoundaries(): Promise<unknown> {
    const result = await this.client.callTool("gana_straddling_legs", {
      tool: "check_boundaries",
      args: {},
    });
    return result.details;
  }

  /** Get the Karma Ledger */
  async karmaReport(): Promise<KarmaEntry[]> {
    const result = await this.client.callTool("gana_hairy_head", {
      tool: "karma_report",
      args: {},
    });
    return (result.details as unknown as { entries: KarmaEntry[] }).entries;
  }

  /** Get Harmony Vector health snapshot */
  async harmonyVector(): Promise<unknown> {
    const result = await this.client.callTool("gana_mound", {
      tool: "view_hologram",
      args: {},
    });
    return result.details;
  }
}
