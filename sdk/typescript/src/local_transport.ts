/**
 * WhiteMagic SDK — Local Transport (WASM-backed).
 *
 * Routes SDK calls to the in-browser WASM module instead of a remote
 * MCP server. This is the transport for the PWA substrate — zero
 * network calls for memory, governance, or karma operations.
 *
 * Usage:
 * ```typescript
 * import init, { MemoryStore, DharmaEngine, KarmaLedger, EdgeEngine, gnosis_snapshot } from './wasm/whitemagic_rs.js';
 * import { LocalTransport } from '@whitemagic/sdk';
 *
 * await init();  // load WASM module
 * const transport = new LocalTransport();
 * await transport.connect();
 *
 * const memId = await transport.callTool('memory.create', {
 *   title: 'Hello', content: 'World', tags: ['test']
 * });
 * ```
 */

import type { ToolResult, Memory } from "./types.js";

export interface WasmModule {
  MemoryStore: new () => WasmMemoryStore;
  DharmaEngine: new () => WasmDharmaEngine;
  KarmaLedger: new () => WasmKarmaLedger;
  EdgeEngine: new () => WasmEdgeEngine;
  gnosis_snapshot: (
    store: WasmMemoryStore,
    karma: WasmKarmaLedger,
    dharma: WasmDharmaEngine,
    engine: WasmEdgeEngine,
  ) => WasmGnosisSnapshot;
  wasm_ready: () => boolean;
  wasm_version: () => string;
  cosine_similarity: (a: string, b: string) => number;
  batch_similarity: (query: string, candidates: string, topK: number) => string;
  text_search: (query: string, texts: string) => string;
}

interface WasmMemoryStore {
  create(title: string, content: string, tagsJson: string): string;
  read(id: string): string;
  update(id: string, title: string, content: string): boolean;
  delete(id: string): boolean;
  search(query: string): string;
  search_by_tag(tag: string): string;
  list(): string;
  count(): number;
  export_json(): string;
  import_json(json: string): number;
}

interface WasmDharmaEngine {
  add_rule(rule: unknown): void;
  remove_rule(id: string): boolean;
  evaluate(text: string): WasmDharmaResult;
  rule_count(): number;
  list_rules(): string;
}

interface WasmDharmaResult {
  allowed: boolean;
  matched_rule: string;
  message: string;
  evaluated_rules: number;
}

interface WasmKarmaLedger {
  record(action: string, delta: number, description: string): string;
  balance(): number;
  count(): number;
  recent_json(n: number): string;
  export_json(): string;
}

interface WasmEdgeEngine {
  infer(query: string): unknown;
  get_stats(): string;
  local_rate(): number;
  reset_stats(): void;
  tokens_saved(): number;
}

interface WasmGnosisSnapshot {
  memory_count: number;
  karma_balance: number;
  karma_entries: number;
  dharma_rules: number;
  edge_queries: number;
  edge_local: number;
  edge_tokens_saved: number;
  to_json(): string;
}

/**
 * Local transport that routes tool calls to the in-browser WASM module.
 * No network calls — all operations run client-side.
 */
export class LocalTransport {
  private wasm: WasmModule | null = null;
  private store: WasmMemoryStore | null = null;
  private dharma: WasmDharmaEngine | null = null;
  private karma: WasmKarmaLedger | null = null;
  private engine: WasmEdgeEngine | null = null;
  private connected = false;

  /**
   * Connect to the WASM module. The module must be initialized
   * (via `init()`) before calling this.
   *
   * @param wasmModule - The initialized WASM module exports
   */
  async connect(wasmModule?: WasmModule): Promise<void> {
    if (wasmModule) {
      this.wasm = wasmModule;
    } else {
      // Try dynamic import of the default WASM module
      try {
        const mod = await import("./wasm/whitemagic_rs.js");
        if (typeof mod.init === "function") {
          await mod.init();
        }
        this.wasm = mod as unknown as WasmModule;
      } catch {
        throw new Error(
          "WASM module not found. Pass the module to connect() or ensure ./wasm/whitemagic_rs.js exists.",
        );
      }
    }

    if (!this.wasm) {
      throw new Error("Failed to load WASM module");
    }

    this.store = new this.wasm.MemoryStore();
    this.dharma = new this.wasm.DharmaEngine();
    this.karma = new this.wasm.KarmaLedger();
    this.engine = new this.wasm.EdgeEngine();
    this.connected = true;
  }

  /**
   * Call a WhiteMagic tool by name. Routes to the appropriate
   * WASM subsystem.
   */
  async callTool(
    name: string,
    params: Record<string, unknown> = {},
  ): Promise<ToolResult> {
    if (!this.connected || !this.store) {
      throw new Error("LocalTransport not connected. Call connect() first.");
    }

    const [namespace, ...rest] = name.split(".");
    const method = rest.join(".");

    try {
      let details: Record<string, unknown> = {};

      switch (namespace) {
        case "memory":
          details = this._handleMemory(method, params);
          break;
        case "dharma":
          details = this._handleDharma(method, params);
          break;
        case "karma":
          details = this._handleKarma(method, params);
          break;
        case "gnosis":
          details = this._handleGnosis(method, params);
          break;
        case "edge":
          details = this._handleEdge(method, params);
          break;
        case "similarity":
          details = this._handleSimilarity(method, params);
          break;
        case "search":
          details = this._handleSearch(method, params);
          break;
        case "system":
          details = this._handleSystem(method, params);
          break;
        default:
          throw new Error(`Unknown tool namespace: ${namespace}`);
      }

      return {
        status: "success",
        tool: name,
        request_id: crypto.randomUUID(),
        message: "OK",
        details,
        retryable: false,
        timestamp: new Date().toISOString(),
      };
    } catch (err) {
      return {
        status: "error",
        tool: name,
        request_id: crypto.randomUUID(),
        message: err instanceof Error ? err.message : "Unknown error",
        details: {},
        error_code: "local_transport_error",
        retryable: false,
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * Disconnect and release WASM resources.
   */
  disconnect(): void {
    this.store = null;
    this.dharma = null;
    this.karma = null;
    this.engine = null;
    this.wasm = null;
    this.connected = false;
  }

  /**
   * Check if the transport is connected.
   */
  isConnected(): boolean {
    return this.connected;
  }

  // ── Private handlers ──────────────────────────────────────────

  private _handleMemory(
    method: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.store) throw new Error("MemoryStore not initialized");

    switch (method) {
      case "create": {
        const tags = Array.isArray(params.tags)
          ? JSON.stringify(params.tags)
          : "[]";
        const id = this.store.create(
          String(params.title ?? ""),
          String(params.content ?? ""),
          tags,
        );
        return { id, memory: JSON.parse(this.store.read(id)) };
      }
      case "read": {
        const json = this.store.read(String(params.id ?? ""));
        if (!json) return { found: false };
        return { found: true, memory: JSON.parse(json) };
      }
      case "update": {
        const ok = this.store.update(
          String(params.id ?? ""),
          String(params.title ?? ""),
          String(params.content ?? ""),
        );
        return { updated: ok };
      }
      case "delete": {
        const ok = this.store.delete(String(params.id ?? ""));
        return { deleted: ok };
      }
      case "search": {
        const results = this.store.search(String(params.query ?? ""));
        return { results: JSON.parse(results) };
      }
      case "search_by_tag": {
        const results = this.store.search_by_tag(String(params.tag ?? ""));
        return { results: JSON.parse(results) };
      }
      case "list": {
        const list = this.store.list();
        return { memories: JSON.parse(list) };
      }
      case "count": {
        return { count: this.store.count() };
      }
      case "export": {
        return { data: this.store.export_json() };
      }
      case "import": {
        const count = this.store.import_json(String(params.json ?? ""));
        return { imported: count };
      }
      default:
        throw new Error(`Unknown memory method: ${method}`);
    }
  }

  private _handleDharma(
    method: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.dharma) throw new Error("DharmaEngine not initialized");

    switch (method) {
      case "evaluate": {
        const result = this.dharma.evaluate(String(params.text ?? ""));
        return {
          allowed: result.allowed,
          matched_rule: result.matched_rule,
          message: result.message,
          evaluated_rules: result.evaluated_rules,
        };
      }
      case "list_rules": {
        return { rules: JSON.parse(this.dharma.list_rules()) };
      }
      case "rule_count": {
        return { count: this.dharma.rule_count() };
      }
      default:
        throw new Error(`Unknown dharma method: ${method}`);
    }
  }

  private _handleKarma(
    method: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.karma) throw new Error("KarmaLedger not initialized");

    switch (method) {
      case "record": {
        const id = this.karma.record(
          String(params.action ?? ""),
          Number(params.delta ?? 0),
          String(params.description ?? ""),
        );
        return { id, balance: this.karma.balance() };
      }
      case "balance": {
        return { balance: this.karma.balance() };
      }
      case "count": {
        return { count: this.karma.count() };
      }
      case "recent": {
        const n = Number(params.n ?? 10);
        return { entries: JSON.parse(this.karma.recent_json(n)) };
      }
      case "export": {
        return { data: this.karma.export_json() };
      }
      default:
        throw new Error(`Unknown karma method: ${method}`);
    }
  }

  private _handleGnosis(
    method: string,
    _params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.wasm || !this.store || !this.karma || !this.dharma || !this.engine) {
      throw new Error("WASM subsystems not initialized");
    }

    switch (method) {
      case "snapshot": {
        const snapshot = this.wasm.gnosis_snapshot(
          this.store,
          this.karma,
          this.dharma,
          this.engine,
        );
        return JSON.parse(snapshot.to_json());
      }
      default:
        throw new Error(`Unknown gnosis method: ${method}`);
    }
  }

  private _handleEdge(
    method: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.engine) throw new Error("EdgeEngine not initialized");

    switch (method) {
      case "infer": {
        const result = this.engine.infer(String(params.query ?? "")) as {
          answer: string;
          confidence: number;
          method: string;
          needs_cloud: boolean;
          tokens_saved: number;
        };
        return {
          answer: result.answer,
          confidence: result.confidence,
          method: result.method,
          needs_cloud: result.needs_cloud,
          tokens_saved: result.tokens_saved,
        };
      }
      case "stats": {
        return JSON.parse(this.engine.get_stats());
      }
      case "local_rate": {
        return { rate: this.engine.local_rate() };
      }
      case "tokens_saved": {
        return { total: this.engine.tokens_saved() };
      }
      case "reset_stats": {
        this.engine.reset_stats();
        return { reset: true };
      }
      default:
        throw new Error(`Unknown edge method: ${method}`);
    }
  }

  private _handleSimilarity(
    method: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.wasm) throw new Error("WASM module not initialized");

    switch (method) {
      case "cosine": {
        const score = this.wasm.cosine_similarity(
          JSON.stringify(params.a ?? []),
          JSON.stringify(params.b ?? []),
        );
        return { score };
      }
      case "batch": {
        const results = this.wasm.batch_similarity(
          JSON.stringify(params.query ?? []),
          JSON.stringify(params.candidates ?? []),
          Number(params.top_k ?? 10),
        );
        return { results: JSON.parse(results) };
      }
      default:
        throw new Error(`Unknown similarity method: ${method}`);
    }
  }

  private _handleSearch(
    method: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.wasm) throw new Error("WASM module not initialized");

    switch (method) {
      case "text": {
        const results = this.wasm.text_search(
          String(params.query ?? ""),
          JSON.stringify(params.texts ?? []),
        );
        return { matches: JSON.parse(results) };
      }
      default:
        throw new Error(`Unknown search method: ${method}`);
    }
  }

  private _handleSystem(
    method: string,
    _params: Record<string, unknown>,
  ): Record<string, unknown> {
    if (!this.wasm) throw new Error("WASM module not initialized");

    switch (method) {
      case "ready": {
        return { ready: this.wasm.wasm_ready() };
      }
      case "version": {
        return { version: this.wasm.wasm_version() };
      }
      default:
        throw new Error(`Unknown system method: ${method}`);
    }
  }
}
