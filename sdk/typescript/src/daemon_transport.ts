/**
 * WhiteMagic Daemon Transport — connects PWA to the cognitive daemon.
 *
 * This transport routes tool calls to the WhiteMagic daemon via WebSocket,
 * which bridges to the Go gRPC cognitive gateway. It provides:
 * - Tool dispatch (with streaming results)
 * - Citta stream subscription (real-time consciousness updates)
 * - Session management (create, resume, continuity)
 * - Telemetry (privacy indicator, loop status)
 *
 * Privacy: All communication stays on localhost. The WebSocket bridge
 * runs on ws://localhost:4731 and never exposes data externally.
 */

export interface DaemonStatus {
  running: boolean;
  uptime_s: number;
  total_iterations: number;
  rss_mb: number;
  loops: Record<string, LoopMetrics>;
  privacy_mode: string;
}

export interface LoopMetrics {
  iterations: number;
  last_duration_ms: number;
  errors: number;
  last_error: string;
}

export interface CittaMoment {
  timestamp: number;
  gana: string;
  operation: string;
  depth_layer: string;
  emotional_tone: string;
  coherence: number;
  output_preview: string;
  cycle_number: number;
}

export interface ToolResult {
  status: string;
  request_id: string;
  payload: Record<string, unknown>;
}

export class DaemonTransport {
  private ws: WebSocket | null = null;
  private url: string;
  private connected: boolean = false;
  private pendingRequests: Map<string, (result: unknown) => void> = new Map();
  private cittaCallbacks: ((moment: CittaMoment) => void)[] = [];
  private statusCallbacks: ((status: DaemonStatus) => void)[] = [];
  private reconnectTimer: number | null = null;

  constructor(url: string = "ws://localhost:4731") {
    this.url = url;
  }

  /** Connect to the daemon WebSocket bridge. */
  connect(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.connected = true;
          console.log("[WM] Connected to daemon");
          resolve(true);
        };

        this.ws.onclose = () => {
          this.connected = false;
          console.log("[WM] Disconnected from daemon");
          // Auto-reconnect after 3s
          this.reconnectTimer = window.setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = () => {
          this.connected = false;
          resolve(false);
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (e) {
            console.error("[WM] Failed to parse message:", e);
          }
        };
      } catch (e) {
        console.error("[WM] Failed to connect:", e);
        resolve(false);
      }
    });
  }

  /** Disconnect from the daemon. */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }

  /** Check if connected to the daemon. */
  get isConnected(): boolean {
    return this.connected;
  }

  /** Call a tool via the daemon. */
  async callTool(
    gana: string,
    tool: string,
    operation: string = "",
    args: Record<string, string> = {},
  ): Promise<ToolResult> {
    return this.sendRequest({
      type: "call_tool",
      gana,
      tool,
      operation,
      args,
    }) as Promise<ToolResult>;
  }

  /** Create a new session. */
  async createSession(
    agentId: string = "pwa",
    agentType: string = "pwa",
    metadata: Record<string, string> = {},
  ): Promise<{ session_id: string; created_at: number; continuity_context: string }> {
    return this.sendRequest({
      type: "create_session",
      agent_id: agentId,
      agent_type: agentType,
      metadata,
    });
  }

  /** Get daemon status. */
  async getStatus(): Promise<DaemonStatus> {
    return this.sendRequest({ type: "status" });
  }

  /** Subscribe to citta stream updates. */
  onCittaMoment(callback: (moment: CittaMoment) => void): () => void {
    this.cittaCallbacks.push(callback);
    return () => {
      this.cittaCallbacks = this.cittaCallbacks.filter((cb) => cb !== callback);
    };
  }

  /** Subscribe to status updates. */
  onStatusUpdate(callback: (status: DaemonStatus) => void): () => void {
    this.statusCallbacks.push(callback);
    return () => {
      this.statusCallbacks = this.statusCallbacks.filter((cb) => cb !== callback);
    };
  }

  /** Send a request and wait for response. */
  private sendRequest(message: unknown): Promise<unknown> {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.ws) {
        reject(new Error("Not connected to daemon"));
        return;
      }

      const requestId = crypto.randomUUID();
      const msg = { ...message as object, request_id: requestId };

      this.pendingRequests.set(requestId, resolve);
      this.ws.send(JSON.stringify(msg));

      // Timeout after 30s
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId);
          reject(new Error("Request timeout"));
        }
      }, 30000);
    });
  }

  /** Handle incoming WebSocket message. */
  private handleMessage(data: any): void {
    // Check if this is a response to a pending request
    if (data.request_id && this.pendingRequests.has(data.request_id)) {
      const resolve = this.pendingRequests.get(data.request_id)!;
      this.pendingRequests.delete(data.request_id);
      resolve(data);
      return;
    }

    // Check if this is a citta stream update
    if (data.type === "citta_moment" && data.moment) {
      this.cittaCallbacks.forEach((cb) => cb(data.moment));
      return;
    }

    // Check if this is a status update
    if (data.type === "status_update" && data.status) {
      this.statusCallbacks.forEach((cb) => cb(data.status));
      return;
    }
  }
}

/** Singleton instance. */
let _transport: DaemonTransport | null = null;

export function getDaemonTransport(): DaemonTransport {
  if (!_transport) {
    _transport = new DaemonTransport();
  }
  return _transport;
}
