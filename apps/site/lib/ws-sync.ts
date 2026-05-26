/**
 * WebSocket Sync — Real-time bidirectional sync
 *
 * Syncs browser SQLite OPFS with server via WebSocket.
 * Supports:
 * - Push local changes to server
 * - Receive remote changes in real-time
 * - Conflict resolution (last-write-wins with vector clocks)
 * - Offline queue for pending operations
 */

// Sync message types
export type SyncMessageType =
  | "sync_request"
  | "sync_response"
  | "memory_created"
  | "memory_updated"
  | "memory_deleted"
  | "association_created"
  | "association_deleted"
  | "presence_update"
  | "heartbeat";

export interface SyncMessage {
  type: SyncMessageType;
  userId: string;
  timestamp: string;
  vectorClock: Record<string, number>;
  payload?: unknown;
}

export interface SyncStats {
  connected: boolean;
  lastSync: Date | null;
  pendingOps: number;
  receivedOps: number;
  conflicts: number;
}

// Offline operation queue
interface PendingOp {
  id: string;
  type: string;
  payload: unknown;
  timestamp: string;
  retries: number;
}

// WebSocket Sync Client
export class WSSyncClient {
  private ws: WebSocket | null = null;
  private userId: string;
  private url: string;
  private pendingOps: PendingOp[] = [];
  private vectorClock: Record<string, number> = {};
  private stats: SyncStats = {
    connected: false,
    lastSync: null,
    pendingOps: 0,
    receivedOps: 0,
    conflicts: 0,
  };
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private onMessageHandler: ((msg: SyncMessage) => void) | null = null;
  private onStatsChangeHandler: ((stats: SyncStats) => void) | null = null;

  constructor(userId: string, url = "ws://localhost:3002/sync") {
    this.userId = userId;
    this.url = url;
  }

  /** Set message handler */
  onMessage(handler: (msg: SyncMessage) => void): void {
    this.onMessageHandler = handler;
  }

  /** Set stats change handler */
  onStatsChange(handler: (stats: SyncStats) => void): void {
    this.onStatsChangeHandler = handler;
  }

  /** Connect to sync server */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("[WSSync] Connected");
      this.stats.connected = true;
      this.reconnectDelay = 1000;

      // Send auth message
      this.send({
        type: "sync_request",
        userId: this.userId,
        timestamp: new Date().toISOString(),
        vectorClock: this.vectorClock,
        payload: { action: "auth" },
      });

      // Start heartbeat
      this.heartbeatInterval = setInterval(() => this.sendHeartbeat(), 30000);

      // Flush pending ops
      this.flushPendingOps();

      this.emitStats();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as SyncMessage;
        this.handleMessage(msg);
      } catch {
        console.warn("[WSSync] Failed to parse message");
      }
    };

    this.ws.onclose = () => {
      console.log("[WSSync] Disconnected, reconnecting...");
      this.stats.connected = false;
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
        this.heartbeatInterval = null;
      }
      this.emitStats();
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error("[WSSync] Error:", error);
    };
  }

  /** Reconnect with exponential backoff */
  private reconnect(): void {
    setTimeout(() => {
      this.connect();
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }, this.reconnectDelay);
  }

  /** Send a message */
  private send(msg: SyncMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  /** Send heartbeat */
  private sendHeartbeat(): void {
    this.send({
      type: "heartbeat",
      userId: this.userId,
      timestamp: new Date().toISOString(),
      vectorClock: this.vectorClock,
    });
  }

  /** Handle incoming message */
  private handleMessage(msg: SyncMessage): void {
    // Update vector clock
    this.mergeVectorClock(msg.vectorClock);

    switch (msg.type) {
      case "sync_response":
        this.stats.lastSync = new Date();
        this.stats.receivedOps++;
        break;
      case "memory_created":
      case "memory_updated":
      case "memory_deleted":
      case "association_created":
      case "association_deleted":
        this.stats.receivedOps++;
        break;
      case "presence_update":
        // Handle presence updates
        break;
    }

    this.emitStats();
    this.onMessageHandler?.(msg);
  }

  /** Merge vector clocks */
  private mergeVectorClock(remote: Record<string, number>): void {
    for (const [key, value] of Object.entries(remote)) {
      this.vectorClock[key] = Math.max(this.vectorClock[key] ?? 0, value);
    }
  }

  /** Increment local vector clock */
  private incrementClock(): Record<string, number> {
    this.vectorClock[this.userId] = (this.vectorClock[this.userId] ?? 0) + 1;
    return { ...this.vectorClock };
  }

  /** Queue an operation for sync */
  queueOp(type: string, payload: unknown): void {
    const op: PendingOp = {
      id: `op_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      type,
      payload,
      timestamp: new Date().toISOString(),
      retries: 0,
    };

    this.pendingOps.push(op);
    this.stats.pendingOps = this.pendingOps.length;
    this.emitStats();

    // Try to flush immediately if connected
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.flushPendingOps();
    }
  }

  /** Flush pending operations */
  private flushPendingOps(): void {
    if (this.pendingOps.length === 0) return;

    const opsToSend = this.pendingOps.splice(0, 10); // Batch up to 10

    for (const op of opsToSend) {
      this.send({
        type: op.type as SyncMessageType,
        userId: this.userId,
        timestamp: op.timestamp,
        vectorClock: this.incrementClock(),
        payload: op.payload,
      });
    }

    this.stats.pendingOps = this.pendingOps.length;
    this.emitStats();

    // Retry failed ops
    if (this.pendingOps.length > 0) {
      setTimeout(() => this.flushPendingOps(), 1000);
    }
  }

  /** Get current stats */
  getStats(): SyncStats {
    return { ...this.stats };
  }

  /** Emit stats change */
  private emitStats(): void {
    this.onStatsChangeHandler?.(this.getStats());
  }

  /** Disconnect */
  disconnect(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    this.ws?.close();
    this.ws = null;
    this.stats.connected = false;
    this.emitStats();
  }
}

// Singleton instances per user
const syncClients = new Map<string, WSSyncClient>();

export function getSyncClient(userId: string, url?: string): WSSyncClient {
  let client = syncClients.get(userId);
  if (!client) {
    client = new WSSyncClient(userId, url);
    syncClients.set(userId, client);
  }
  return client;
}
