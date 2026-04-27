/** WhiteMagic SDK — High-level memory operations */

import type { WhiteMagicClient } from "./client.js";
import type {
  Memory,
  MemoryCreateRequest,
  MemorySearchRequest,
  MemorySearchResult,
} from "./types.js";

export class MemoryOps {
  constructor(private client: WhiteMagicClient) {}

  /** Create a new memory */
  async create(request: MemoryCreateRequest): Promise<Memory> {
    const result = await this.client.callTool("gana_ghost", {
      tool: "gnosis",
      args: {
        action: "create",
        content: request.content,
        tags: request.tags ?? [],
        galaxy: request.galaxy,
      },
    });
    return result.details as unknown as Memory;
  }

  /** Search memories */
  async search(request: MemorySearchRequest): Promise<MemorySearchResult> {
    const result = await this.client.callTool("gana_ghost", {
      tool: "gnosis",
      args: {
        action: "search",
        query: request.query,
        limit: request.limit ?? 10,
        galaxy: request.galaxy,
        method: request.method ?? "hybrid",
      },
    });
    return result.details as unknown as MemorySearchResult;
  }

  /** Read a memory by ID */
  async read(id: string): Promise<Memory> {
    const result = await this.client.callTool("gana_ghost", {
      tool: "gnosis",
      args: {
        action: "read",
        memory_id: id,
      },
    });
    return result.details as unknown as Memory;
  }

  /** Update a memory */
  async update(
    id: string,
    updates: Partial<MemoryCreateRequest>,
  ): Promise<Memory> {
    const result = await this.client.callTool("gana_ghost", {
      tool: "gnosis",
      args: {
        action: "update",
        memory_id: id,
        ...updates,
      },
    });
    return result.details as unknown as Memory;
  }

  /** Delete a memory */
  async delete(id: string): Promise<boolean> {
    const result = await this.client.callTool("gana_ghost", {
      tool: "gnosis",
      args: {
        action: "delete",
        memory_id: id,
      },
    });
    return result.status === "success";
  }
}
