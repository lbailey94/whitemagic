/**
 * SQLite OPFS Storage — Browser-side memory persistence
 *
 * Uses sql.js (SQLite compiled to WASM) with Origin Private File System (OPFS)
 * for persistent browser storage. Memories, embeddings, and associations
 * survive page reloads and work offline.
 */

// sql.js types
interface SqlJsStatic {
  Database: new (data?: Uint8Array) => SqlJsDatabase;
}

interface SqlJsDatabase {
  run(sql: string, params?: unknown[]): void;
  exec(sql: string, params?: unknown[]): Array<{ columns: string[]; values: unknown[][] }>;
  prepare(sql: string): Statement;
  close(): void;
  export(): Uint8Array;
}

interface Statement {
  run(params?: unknown[]): void;
  step(): boolean;
  get<T = unknown>(index?: number): T;
  getObject<T = Record<string, unknown>>(): T;
  finalize(): void;
}

// Memory record matching core schema
export interface MemoryRecord {
  id: string;
  content: string;
  garden: string;
  type: string;
  created_at: string;
  updated_at: string;
  access_count: number;
  last_accessed: string | null;
  embedding: number[] | null;
  holographic_coords: { x: number; y: number; z: number; w: number; t: number } | null;
  metadata: Record<string, unknown> | null;
}

// Association record
export interface AssociationRecord {
  id: string;
  source_id: string;
  target_id: string;
  weight: number;
  type: string;
  created_at: string;
}

// Query results
export interface QueryResult {
  memories: MemoryRecord[];
  total: number;
}

// Database stats
export interface DBStats {
  memoryCount: number;
  associationCount: number;
  unsyncedCount: number;
  dbSizeBytes: number;
}

// OPFS SQLite manager
export class OPFSSQLite {
  private db: SqlJsDatabase | null = null;
  private SQL: SqlJsStatic | null = null;
  private initPromise: Promise<void>;
  private isReady = false;
  private userId: string | null = null;
  private dbFileName: string;

  constructor(userId?: string) {
    this.userId = userId ?? null;
    this.dbFileName = userId ? `whitemagic_${userId}.db` : "whitemagic.db";
    this.initPromise = this.init();
  }

  /** Update the user ID and reinitialize */
  async switchUser(userId: string | null): Promise<void> {
    this.userId = userId;
    this.dbFileName = userId ? `whitemagic_${userId}.db` : "whitemagic.db";
    if (this.db) {
      this.db.close();
      this.db = null;
    }
    this.initPromise = this.init();
    return this.initPromise;
  }

  /** Wait for SQLite to be ready */
  async ready(): Promise<void> {
    return this.initPromise;
  }

  /** Initialize SQLite with OPFS persistence */
  private async init(): Promise<void> {
    try {
      // Load sql.js dynamically
      this.SQL = await this.loadSqlJs();

      // Try to load existing DB from OPFS
      let dbData: Uint8Array | undefined;
      try {
        const root = await navigator.storage?.getDirectory();
        if (root) {
          // @ts-ignore
          const fileHandle = await root.getFileHandle(this.dbFileName);
          // @ts-ignore
          const file = await fileHandle.getFile();
          dbData = new Uint8Array(await file.arrayBuffer());
        }
      } catch {
        // No existing DB, create new
      }

      // Initialize database
      this.db = dbData ? new this.SQL.Database(dbData) : new this.SQL.Database();

      // Create schema
      this.createSchema();

      // Save to OPFS
      await this.saveToOPFS();

      this.isReady = true;
      console.log(`[OPFSSQLite] Initialized with OPFS persistence (${this.dbFileName})`);
    } catch (error) {
      console.error("[OPFSSQLite] Init failed, falling back to in-memory:", error);
      // Fallback to in-memory
      if (this.SQL) {
        this.db = new this.SQL.Database();
        this.createSchema();
        this.isReady = true;
      }
    }
  }

  /** Load sql.js from CDN */
  private async loadSqlJs(): Promise<SqlJsStatic> {
    return new Promise((resolve, reject) => {
      if (typeof window !== "undefined" && (window as any).SQL) {
        resolve((window as any).SQL as SqlJsStatic);
        return;
      }

      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/sql-wasm.js";
      script.onload = () => {
        resolve((window as any).SQL as SqlJsStatic);
      };
      script.onerror = () => reject(new Error("Failed to load sql.js"));
      document.head.appendChild(script);
    });
  }

  /** Save database to OPFS */
  private async saveToOPFS(): Promise<void> {
    if (!this.db) return;

    try {
      const data = this.db.export();
      const root = await navigator.storage?.getDirectory();
      if (root) {
        // @ts-ignore
        const fileHandle = await root.getFileHandle(this.dbFileName, { create: true });
        // @ts-ignore
        const writable = await fileHandle.createWritable();
        // @ts-ignore
        await writable.write(data.buffer);
        await writable.close();
      }
    } catch (error) {
      console.warn("[OPFSSQLite] Save to OPFS failed:", error);
    }
  }

  /** Create database schema */
  private createSchema(): void {
    if (!this.db) return;

    this.db.run(`
      CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        garden TEXT NOT NULL DEFAULT 'unknown',
        type TEXT NOT NULL DEFAULT 'memory',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        access_count INTEGER NOT NULL DEFAULT 0,
        last_accessed TEXT,
        embedding TEXT,
        holographic_x REAL,
        holographic_y REAL,
        holographic_z REAL,
        holographic_w REAL,
        holographic_t REAL,
        metadata TEXT
      )
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS associations (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL REFERENCES memories(id),
        target_id TEXT NOT NULL REFERENCES memories(id),
        weight REAL NOT NULL DEFAULT 1.0,
        type TEXT NOT NULL DEFAULT 'association',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      )
    `);

    this.db.run(`CREATE INDEX IF NOT EXISTS idx_memories_garden ON memories(garden)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_associations_source ON associations(source_id)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_associations_target ON associations(target_id)`);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation TEXT NOT NULL,
        memory_id TEXT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        synced INTEGER NOT NULL DEFAULT 0
      )
    `);
  }

  /** Insert a memory */
  async insertMemory(memory: Partial<MemoryRecord>): Promise<string> {
    await this.ready();
    if (!this.db) throw new Error("Database not initialized");

    const id = memory.id || crypto.randomUUID();
    const now = new Date().toISOString();

    const stmt = this.db.prepare(`
      INSERT INTO memories (id, content, garden, type, created_at, updated_at,
        embedding, holographic_x, holographic_y, holographic_z, holographic_w, holographic_t, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run([
      id,
      memory.content || "",
      memory.garden || "unknown",
      memory.type || "memory",
      memory.created_at || now,
      memory.updated_at || now,
      memory.embedding ? JSON.stringify(memory.embedding) : null,
      memory.holographic_coords?.x ?? null,
      memory.holographic_coords?.y ?? null,
      memory.holographic_coords?.z ?? null,
      memory.holographic_coords?.w ?? null,
      memory.holographic_coords?.t ?? null,
      memory.metadata ? JSON.stringify(memory.metadata) : null,
    ]);
    stmt.finalize();

    // Log for sync
    this.db.run("INSERT INTO sync_log (operation, memory_id) VALUES (?, ?)", ["insert", id]);

    await this.saveToOPFS();
    return id;
  }

  /** Query memories with filters */
  async queryMemories(options: {
    garden?: string;
    type?: string;
    limit?: number;
    offset?: number;
    search?: string;
  } = {}): Promise<QueryResult> {
    await this.ready();
    if (!this.db) return { memories: [], total: 0 };

    let sql = "SELECT * FROM memories WHERE 1=1";
    const params: unknown[] = [];

    if (options.garden) {
      sql += " AND garden = ?";
      params.push(options.garden);
    }
    if (options.type) {
      sql += " AND type = ?";
      params.push(options.type);
    }
    if (options.search) {
      sql += " AND content LIKE ?";
      params.push(`%${options.search}%`);
    }

    sql += " ORDER BY created_at DESC";
    sql += ` LIMIT ${options.limit ?? 100}`;
    sql += ` OFFSET ${options.offset ?? 0}`;

    const results = this.db.exec(sql, params);
    const memories = this.parseMemories(results);

    // Get total count
    let countSql = "SELECT COUNT(*) FROM memories WHERE 1=1";
    if (options.garden) countSql += " AND garden = ?";
    if (options.type) countSql += " AND type = ?";
    if (options.search) countSql += " AND content LIKE ?";
    const countResults = this.db.exec(countSql, params);
    const total = (countResults[0]?.values[0]?.[0] as number) ?? 0;

    return { memories, total };
  }

  /** Parse query results into MemoryRecord array */
  private parseMemories(results: Array<{ columns: string[]; values: unknown[][] }>): MemoryRecord[] {
    if (!results.length) return [];

    const columns = results[0].columns;
    return results[0].values.map(row => {
      const obj: Record<string, unknown> = {};
      columns.forEach((col, i) => {
        obj[col] = row[i];
      });

      return {
        id: obj.id as string,
        content: obj.content as string,
        garden: obj.garden as string,
        type: obj.type as string,
        created_at: obj.created_at as string,
        updated_at: obj.updated_at as string,
        access_count: obj.access_count as number,
        last_accessed: (obj.last_accessed as string) ?? null,
        embedding: obj.embedding ? JSON.parse(obj.embedding as string) : null,
        holographic_coords: obj.holographic_x != null ? {
          x: obj.holographic_x as number,
          y: obj.holographic_y as number,
          z: obj.holographic_z as number,
          w: obj.holographic_w as number,
          t: obj.holographic_t as number,
        } : null,
        metadata: obj.metadata ? JSON.parse(obj.metadata as string) : null,
      };
    });
  }

  /** Get memory by ID */
  async getMemory(id: string): Promise<MemoryRecord | null> {
    await this.ready();
    if (!this.db) return null;

    const results = this.db.exec("SELECT * FROM memories WHERE id = ?", [id]);
    const memories = this.parseMemories(results);
    return memories[0] ?? null;
  }

  /** Update a memory */
  async updateMemory(id: string, updates: Partial<MemoryRecord>): Promise<void> {
    await this.ready();
    if (!this.db) return;

    const fields: string[] = [];
    const params: unknown[] = [];

    if (updates.content !== undefined) { fields.push("content = ?"); params.push(updates.content); }
    if (updates.garden !== undefined) { fields.push("garden = ?"); params.push(updates.garden); }
    if (updates.type !== undefined) { fields.push("type = ?"); params.push(updates.type); }
    if (updates.embedding !== undefined) { fields.push("embedding = ?"); params.push(JSON.stringify(updates.embedding)); }
    if (updates.holographic_coords) {
      const coords = updates.holographic_coords;
      fields.push("holographic_x = ?", "holographic_y = ?", "holographic_z = ?", "holographic_w = ?", "holographic_t = ?");
      params.push(coords.x, coords.y, coords.z, coords.w, coords.t);
    }
    if (updates.metadata !== undefined) { fields.push("metadata = ?"); params.push(JSON.stringify(updates.metadata)); }

    fields.push("updated_at = datetime('now')");
    params.push(id);

    this.db.run(`UPDATE memories SET ${fields.join(", ")} WHERE id = ?`, params);
    this.db.run("INSERT INTO sync_log (operation, memory_id) VALUES (?, ?)", ["update", id]);

    await this.saveToOPFS();
  }

  /** Delete a memory */
  async deleteMemory(id: string): Promise<void> {
    await this.ready();
    if (!this.db) return;

    this.db.run("DELETE FROM memories WHERE id = ?", [id]);
    this.db.run("DELETE FROM associations WHERE source_id = ? OR target_id = ?", [id, id]);
    this.db.run("INSERT INTO sync_log (operation, memory_id) VALUES (?, ?)", ["delete", id]);

    await this.saveToOPFS();
  }

  /** Insert an association */
  async insertAssociation(assoc: Partial<AssociationRecord>): Promise<string> {
    await this.ready();
    if (!this.db) throw new Error("Database not initialized");

    const id = assoc.id || crypto.randomUUID();

    this.db.run(`
      INSERT INTO associations (id, source_id, target_id, weight, type, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `, [id, assoc.source_id, assoc.target_id, assoc.weight ?? 1.0, assoc.type ?? "association", assoc.created_at || new Date().toISOString()]);

    await this.saveToOPFS();
    return id;
  }

  /** Get associations for a memory */
  async getAssociations(memoryId: string): Promise<AssociationRecord[]> {
    await this.ready();
    if (!this.db) return [];

    const results = this.db.exec(
      "SELECT * FROM associations WHERE source_id = ? OR target_id = ?",
      [memoryId, memoryId]
    );

    if (!results.length) return [];

    const columns = results[0].columns;
    return results[0].values.map(row => {
      const obj: Record<string, unknown> = {};
      columns.forEach((col, i) => { obj[col] = row[i]; });
      return obj as unknown as AssociationRecord;
    });
  }

  /** Get database stats */
  async getStats(): Promise<DBStats> {
    await this.ready();
    if (!this.db) return { memoryCount: 0, associationCount: 0, unsyncedCount: 0, dbSizeBytes: 0 };

    const memCount = (this.db.exec("SELECT COUNT(*) FROM memories")[0]?.values[0]?.[0] as number) ?? 0;
    const assocCount = (this.db.exec("SELECT COUNT(*) FROM associations")[0]?.values[0]?.[0] as number) ?? 0;
    const unsynced = (this.db.exec("SELECT COUNT(*) FROM sync_log WHERE synced = 0")[0]?.values[0]?.[0] as number) ?? 0;

    return {
      memoryCount: memCount,
      associationCount: assocCount,
      unsyncedCount: unsynced,
      dbSizeBytes: this.db.export().length,
    };
  }

  /** Get garden statistics */
  async getGardenStats(): Promise<Record<string, number>> {
    await this.ready();
    if (!this.db) return {};

    const results = this.db.exec("SELECT garden, COUNT(*) as count FROM memories GROUP BY garden");
    const stats: Record<string, number> = {};

    if (results.length) {
      results[0].values.forEach(row => {
        stats[row[0] as string] = row[1] as number;
      });
    }

    return stats;
  }

  /** Get unsynced operations for server reconciliation */
  async getUnsyncedOperations(): Promise<Array<{ id: number; operation: string; memory_id: string | null; timestamp: string }>> {
    await this.ready();
    if (!this.db) return [];

    const results = this.db.exec("SELECT id, operation, memory_id, timestamp FROM sync_log WHERE synced = 0 ORDER BY timestamp");
    if (!results.length) return [];

    return results[0].values.map(row => ({
      id: row[0] as number,
      operation: row[1] as string,
      memory_id: row[2] as string | null,
      timestamp: row[3] as string,
    }));
  }

  /** Mark operations as synced */
  async markSynced(ids: number[]): Promise<void> {
    await this.ready();
    if (!this.db || ids.length === 0) return;

    this.db.run(`UPDATE sync_log SET synced = 1 WHERE id IN (${ids.join(",")})`);
    await this.saveToOPFS();
  }

  /** Close database and persist */
  async close(): Promise<void> {
    await this.ready();
    if (this.db) {
      await this.saveToOPFS();
      this.db.close();
      this.db = null;
    }
  }
}

// Singleton instance
let opfsSQLite: OPFSSQLite | null = null;

export function getOPFSSQLite(userId?: string): OPFSSQLite {
  if (!opfsSQLite) {
    opfsSQLite = new OPFSSQLite(userId);
  } else if (userId !== undefined) {
    // Switch user if different
    opfsSQLite.switchUser(userId);
  }
  return opfsSQLite;
}
