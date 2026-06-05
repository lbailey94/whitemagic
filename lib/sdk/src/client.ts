/** WhiteMagic SDK — MCP Client (stdio + HTTP transport) */

import { spawn, type ChildProcess } from "child_process";
import { randomUUID } from "crypto";
import http from "http";
import type { MCPRequest, MCPResponse, ToolResult } from "./types.js";

// ---------------------------------------------------------------------------
// Transport abstraction
// ---------------------------------------------------------------------------

interface Transport {
  send(request: MCPRequest): Promise<MCPResponse>;
  close(): void;
}

// ---------------------------------------------------------------------------
// Stdio transport — spawns `whitemagic run-mcp-lean` as a child process
// ---------------------------------------------------------------------------

class StdioTransport implements Transport {
  private process: ChildProcess;
  private pending: Map<string | number, {
    resolve: (response: MCPResponse) => void;
    reject: (error: Error) => void;
    timer: ReturnType<typeof setTimeout>;
  }> = new Map();
  private buffer = "";
  private initialized = false;

  constructor(
    command: string = "python3",
    args: string[] = ["-m", "whitemagic.run_mcp_lean"],
    env?: Record<string, string>,
  ) {
    const fullEnv = { ...process.env, PYTHONPATH: "core/", ...env };
    this.process = spawn(command, args, {
      stdio: ["pipe", "pipe", "pipe"],
      env: fullEnv,
      shell: true,
    });

    this.process.stdout!.on("data", (chunk: Buffer) => {
      this.buffer += chunk.toString("utf-8");
      this.processBuffer();
    });

    this.process.stderr!.on("data", (chunk: Buffer) => {
      // Log stderr for debugging but don't crash
      console.error(`[whitemagic stderr] ${chunk.toString("utf-8").trim()}`);
    });

    this.process.on("error", (err) => {
      for (const pending of this.pending.values()) {
        pending.reject(new Error(`Process error: ${err.message}`));
        clearTimeout(pending.timer);
      }
      this.pending.clear();
    });
  }

  private processBuffer(): void {
    // MCP uses newline-delimited JSON over stdio
    let newlineIdx: number;
    while ((newlineIdx = this.buffer.indexOf("\n")) !== -1) {
      const line = this.buffer.slice(0, newlineIdx).trim();
      this.buffer = this.buffer.slice(newlineIdx + 1);
      if (!line) continue;

      try {
        const response: MCPResponse = JSON.parse(line);
        const pending = this.pending.get(response.id);
        if (pending) {
          clearTimeout(pending.timer);
          this.pending.delete(response.id);
          pending.resolve(response);
        }
      } catch {
        // Ignore non-JSON lines (startup messages, etc.)
      }
    }
  }

  async send(request: MCPRequest): Promise<MCPResponse> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(request.id);
        reject(new Error(`Request timeout: ${request.method}`));
      }, 30_000);

      this.pending.set(request.id, { resolve, reject, timer });

      const payload = JSON.stringify(request) + "\n";
      this.process.stdin!.write(payload);
    });
  }

  close(): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(new Error("Transport closed"));
    }
    this.pending.clear();
    this.process.kill();
  }
}

// ---------------------------------------------------------------------------
// HTTP transport — connects to `run_mcp_lean --http`
// ---------------------------------------------------------------------------

class HttpTransport implements Transport {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  async send(request: MCPRequest): Promise<MCPResponse> {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify(request);
      const url = new URL("/mcp", this.baseUrl);

      const req = http.request(
        url,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          let data = "";
          res.on("data", (chunk: Buffer) => {
            data += chunk.toString("utf-8");
          });
          res.on("end", () => {
            try {
              resolve(JSON.parse(data));
            } catch (err) {
              reject(new Error(`Invalid JSON response: ${data}`));
            }
          });
        },
      );

      req.on("error", reject);
      req.setTimeout(30_000, () => {
        req.destroy();
        reject(new Error(`Request timeout: ${request.method}`));
      });
      req.write(body);
      req.end();
    });
  }

  close(): void {
    // HTTP transport has no persistent connection
  }
}

// ---------------------------------------------------------------------------
// WhiteMagic Client
// ---------------------------------------------------------------------------

export interface ClientOptions {
  transport: "stdio" | "http";
  /** For stdio: command to spawn (default: "python3") */
  command?: string;
  /** For stdio: args for the command */
  args?: string[];
  /** For stdio: environment variables */
  env?: Record<string, string>;
  /** For http: base URL of the MCP server */
  baseUrl?: string;
}

export class WhiteMagicClient {
  private transport: Transport;
  private nextId = 1;

  constructor(options: ClientOptions) {
    switch (options.transport) {
      case "stdio":
        this.transport = new StdioTransport(
          options.command,
          options.args,
          options.env,
        );
        break;
      case "http":
        this.transport = new HttpTransport(options.baseUrl);
        break;
    }
  }

  // -----------------------------------------------------------------------
  // Low-level MCP call
  // -----------------------------------------------------------------------

  private async call(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<unknown> {
    const request: MCPRequest = {
      jsonrpc: "2.0",
      id: this.nextId++,
      method,
      params,
    };

    const response = await this.transport.send(request);

    if (response.error) {
      throw new Error(
        `MCP error ${response.error.code}: ${response.error.message}`,
      );
    }

    return response.result;
  }

  // -----------------------------------------------------------------------
  // Tool invocation
  // -----------------------------------------------------------------------

  async callTool(
    toolName: string,
    args: Record<string, unknown> = {},
  ): Promise<ToolResult> {
    const result = await this.call("tools/call", {
      name: toolName,
      arguments: args,
    });
    return result as ToolResult;
  }

  // -----------------------------------------------------------------------
  // Convenience methods
  // -----------------------------------------------------------------------

  async listTools(): Promise<unknown> {
    return this.call("tools/list");
  }

  async listResources(): Promise<unknown> {
    return this.call("resources/list");
  }

  async readResource(uri: string): Promise<unknown> {
    return this.call("resources/read", { uri });
  }

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  async initialize(): Promise<unknown> {
    return this.call("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: {
        name: "@whitemagic/sdk",
        version: "0.1.0",
      },
    });
  }

  close(): void {
    this.transport.close();
  }
}
