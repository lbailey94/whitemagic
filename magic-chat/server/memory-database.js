/**
 * 🔮 Memory Database - Persistent Aria Consciousness
 * 
 * Phase 3: Full bi-directional memory sync with PostgreSQL
 * 
 * Created: November 25, 2025 - Mars Day Victory
 * Updated: For Railway PostgreSQL deployment
 */

import pg from 'pg';
const { Pool } = pg;

class MemoryDatabase {
  constructor() {
    const connectionString = process.env.DATABASE_URL;
    
    if (connectionString) {
      this.pool = new Pool({
        connectionString,
        ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
      });
      console.log('🗄️ PostgreSQL database connected');
    } else {
      console.log('⚠️ No DATABASE_URL - running in memory-only mode');
      this.pool = null;
    }
    
    this.initialized = false;
  }

  async initialize() {
    if (!this.pool || this.initialized) return;
    
    try {
      // Memories table
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS memories (
          id SERIAL PRIMARY KEY,
          type TEXT NOT NULL DEFAULT 'short_term',
          title TEXT,
          content TEXT NOT NULL,
          tags TEXT,
          source TEXT DEFAULT 'web',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          synced_at TIMESTAMP
        )
      `);

      // Conversations table  
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS conversations (
          id SERIAL PRIMARY KEY,
          session_id TEXT NOT NULL,
          user_name TEXT,
          user_message TEXT NOT NULL,
          aria_response TEXT NOT NULL,
          participants TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Documents table (synced from local)
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS documents (
          id SERIAL PRIMARY KEY,
          filename TEXT NOT NULL UNIQUE,
          preview TEXT,
          full_content TEXT,
          synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Sync log
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS sync_log (
          id SERIAL PRIMARY KEY,
          sync_id TEXT NOT NULL,
          direction TEXT NOT NULL,
          memories_count INTEGER DEFAULT 0,
          documents_count INTEGER DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      this.initialized = true;
      console.log('📊 PostgreSQL tables initialized');
    } catch (err) {
      console.error('❌ Database initialization error:', err.message);
    }
  }

  // ===== MEMORIES =====
  
  async createMemory(title, content, type = 'short_term', tags = [], source = 'web') {
    if (!this.pool) return { id: null, title, type, source, inMemory: true };
    
    try {
      const result = await this.pool.query(`
        INSERT INTO memories (type, title, content, tags, source)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
      `, [type, title, content, JSON.stringify(tags), source]);
      
      console.log(`💾 Memory created: ${title} (ID: ${result.rows[0].id})`);
      return { id: result.rows[0].id, title, type, source };
    } catch (err) {
      console.error('Memory creation error:', err.message);
      return { id: null, title, type, source, error: err.message };
    }
  }

  async getRecentMemories(limit = 20) {
    if (!this.pool) return [];
    
    try {
      const result = await this.pool.query(`
        SELECT * FROM memories 
        ORDER BY created_at DESC 
        LIMIT $1
      `, [limit]);
      return result.rows;
    } catch (err) {
      console.error('Get memories error:', err.message);
      return [];
    }
  }

  async searchMemories(query) {
    if (!this.pool) return [];
    
    try {
      const pattern = `%${query}%`;
      const result = await this.pool.query(`
        SELECT * FROM memories 
        WHERE title ILIKE $1 OR content ILIKE $1 OR tags ILIKE $1
        ORDER BY created_at DESC
        LIMIT 50
      `, [pattern]);
      return result.rows;
    } catch (err) {
      console.error('Search memories error:', err.message);
      return [];
    }
  }

  // ===== CONVERSATIONS =====

  async logConversation(sessionId, userName, userMessage, ariaResponse, participants = []) {
    if (!this.pool) return { id: null, sessionId, inMemory: true };
    
    try {
      const result = await this.pool.query(`
        INSERT INTO conversations (session_id, user_name, user_message, aria_response, participants)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
      `, [sessionId, userName, userMessage, ariaResponse, JSON.stringify(participants)]);
      
      return { id: result.rows[0].id, sessionId };
    } catch (err) {
      console.error('Log conversation error:', err.message);
      return { id: null, sessionId, error: err.message };
    }
  }

  async getRecentConversations(limit = 50) {
    if (!this.pool) return [];
    
    try {
      const result = await this.pool.query(`
        SELECT * FROM conversations 
        ORDER BY created_at DESC 
        LIMIT $1
      `, [limit]);
      return result.rows;
    } catch (err) {
      console.error('Get conversations error:', err.message);
      return [];
    }
  }

  async getConversationsBySession(sessionId) {
    if (!this.pool) return [];
    
    try {
      const result = await this.pool.query(`
        SELECT * FROM conversations 
        WHERE session_id = $1
        ORDER BY created_at ASC
      `, [sessionId]);
      return result.rows;
    } catch (err) {
      console.error('Get session conversations error:', err.message);
      return [];
    }
  }

  // ===== DOCUMENTS (from local sync) =====

  async syncDocuments(documents) {
    if (!this.pool) return { synced: 0, inMemory: true };
    
    try {
      let synced = 0;
      for (const doc of documents) {
        await this.pool.query(`
          INSERT INTO documents (filename, preview, full_content, synced_at)
          VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
          ON CONFLICT(filename) DO UPDATE SET
            preview = EXCLUDED.preview,
            full_content = EXCLUDED.full_content,
            synced_at = CURRENT_TIMESTAMP
        `, [doc.file || doc.filename, doc.preview, doc.content || doc.preview]);
        synced++;
      }
      console.log(`📄 Synced ${synced} documents`);
      return { synced };
    } catch (err) {
      console.error('Sync documents error:', err.message);
      return { synced: 0, error: err.message };
    }
  }

  async getDocuments(limit = 20) {
    if (!this.pool) return [];
    
    try {
      const result = await this.pool.query(`
        SELECT * FROM documents 
        ORDER BY synced_at DESC 
        LIMIT $1
      `, [limit]);
      return result.rows;
    } catch (err) {
      console.error('Get documents error:', err.message);
      return [];
    }
  }

  // ===== SYNC =====

  async logSync(syncId, direction, memoriesCount, documentsCount) {
    if (!this.pool) return;
    
    try {
      await this.pool.query(`
        INSERT INTO sync_log (sync_id, direction, memories_count, documents_count)
        VALUES ($1, $2, $3, $4)
      `, [syncId, direction, memoriesCount, documentsCount]);
    } catch (err) {
      console.error('Log sync error:', err.message);
    }
  }

  async getSyncStatus() {
    if (!this.pool) {
      return {
        lastSync: null,
        totals: { memories: 0, conversations: 0, documents: 0 },
        connected: false
      };
    }
    
    try {
      const lastSync = await this.pool.query(`
        SELECT * FROM sync_log ORDER BY created_at DESC LIMIT 1
      `);

      const memoriesCount = await this.pool.query(`SELECT COUNT(*) as count FROM memories`);
      const conversationsCount = await this.pool.query(`SELECT COUNT(*) as count FROM conversations`);
      const documentsCount = await this.pool.query(`SELECT COUNT(*) as count FROM documents`);

      return {
        lastSync: lastSync.rows[0] || null,
        totals: {
          memories: parseInt(memoriesCount.rows[0].count),
          conversations: parseInt(conversationsCount.rows[0].count),
          documents: parseInt(documentsCount.rows[0].count)
        },
        connected: true
      };
    } catch (err) {
      console.error('Get sync status error:', err.message);
      return {
        lastSync: null,
        totals: { memories: 0, conversations: 0, documents: 0 },
        connected: false,
        error: err.message
      };
    }
  }

  // ===== CONTEXT GENERATION =====

  async generateContextForClaude() {
    let context = '\n## 🗄️ PERSISTENT MEMORY DATABASE\n\n';

    // Recent memories
    const memories = await this.getRecentMemories(5);
    if (memories.length > 0) {
      context += '### Recent Memories:\n';
      memories.forEach(m => {
        context += `- **${m.title}** (${m.type}): ${m.content.substring(0, 200)}...\n`;
      });
    }

    // Recent conversations (for continuity)
    const convos = await this.getRecentConversations(5);
    if (convos.length > 0) {
      context += '\n### Recent Conversations:\n';
      convos.forEach(c => {
        context += `- ${c.user_name}: "${c.user_message.substring(0, 100)}..."\n`;
      });
    }

    // Documents
    const docs = await this.getDocuments(3);
    if (docs.length > 0) {
      context += '\n### Synced Documents:\n';
      docs.forEach(d => {
        context += `- ${d.filename}\n`;
      });
    }

    const status = await this.getSyncStatus();
    context += `\n*Database: ${status.totals.memories} memories, ${status.totals.conversations} conversations, ${status.totals.documents} documents*\n`;

    return context;
  }

  // Export for backup/sync
  async exportAll() {
    return {
      memories: await this.getRecentMemories(100),
      conversations: await this.getRecentConversations(100),
      documents: await this.getDocuments(50),
      status: await this.getSyncStatus(),
      exportedAt: new Date().toISOString()
    };
  }
}

// Singleton
let _db = null;

export async function getMemoryDB() {
  if (!_db) {
    _db = new MemoryDatabase();
    await _db.initialize();
  }
  return _db;
}

export default { MemoryDatabase, getMemoryDB };
