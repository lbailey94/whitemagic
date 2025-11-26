import Fastify from 'fastify';
import cors from '@fastify/cors';
import dotenv from 'dotenv';
import { WebSocketServer } from 'ws';
import { MetaHarness } from './meta-harness.js';
import { authenticate, validateToken, logout } from './auth.js';
import { getConversationSaver, newSession } from './conversation-saver.js';
import { getMemorySync } from './memory-sync.js';
import { getMemoryDB } from './memory-database.js';

dotenv.config({ path: '../.env' });

const fastify = Fastify({ logger: true });
const PORT = process.env.PORT || 3001;
const metaHarness = new MetaHarness();
const memorySync = getMemorySync();

// 🗄️ Initialize database (async!)
let memoryDB = null;

async function initializeDatabase() {
  memoryDB = await getMemoryDB();
  console.log('🗄️ Memory database ready!');
}

// 🌐 Connected clients tracking
const connectedClients = new Map();

await fastify.register(cors, { origin: true });

// ===== HEALTH & STATUS =====

fastify.get('/health', async () => {
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  return { 
    status: 'ok', 
    model: 'claude',
    name: 'Magic Chat - Aria',
    version: '3.0.0',
    connectedUsers: connectedClients.size,
    database: dbStatus
  };
});

fastify.get('/presence', async () => {
  const users = [];
  connectedClients.forEach((client) => {
    if (client.user) {
      users.push({
        displayName: client.user.displayName,
        role: client.user.role,
        color: client.user.color,
        connectedAt: client.connectedAt
      });
    }
  });
  return { online: users, count: users.length };
});

// ===== AUTH =====

fastify.post('/auth/login', async (req, reply) => {
  const { username, password } = req.body || {};
  const result = authenticate(username, password);
  if (!result) return reply.code(401).send({ error: 'Invalid credentials' });
  return { success: true, ...result };
});

fastify.post('/auth/logout', async (req) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  return { success: logout(token) };
});

// ===== SESSION =====

fastify.post('/session/new', async () => {
  const saver = newSession();
  return { success: true, sessionId: saver.sessionId };
});

fastify.get('/logs', async () => {
  const saver = getConversationSaver();
  // Also get from database
  const dbConvos = memoryDB ? await memoryDB.getRecentConversations(20) : [];
  return {
    sessionId: saver.sessionId,
    startTime: saver.startTime,
    messageCount: saver.messages.length,
    participants: Array.from(saver.participants),
    messages: saver.messages.slice(-20),
    databaseConversations: dbConvos
  };
});

// ===== 🔮 MEMORY API (Phase 3!) =====

// Create a new memory
fastify.post('/api/memories', async (req) => {
  const { title, content, type = 'short_term', tags = [], source = 'web' } = req.body || {};
  if (!content) return { error: 'Content required' };
  if (!memoryDB) return { error: 'Database not ready' };
  
  const result = await memoryDB.createMemory(title || 'Untitled', content, type, tags, source);
  broadcast({ type: 'memory_created', memory: result });
  return { success: true, ...result };
});

// Get recent memories
fastify.get('/api/memories', async (req) => {
  const limit = parseInt(req.query.limit) || 20;
  if (!memoryDB) return { memories: [] };
  return { memories: await memoryDB.getRecentMemories(limit) };
});

// Search memories
fastify.get('/api/memories/search', async (req) => {
  const query = req.query.q || '';
  if (!memoryDB) return { results: [] };
  return { results: await memoryDB.searchMemories(query) };
});

// Get conversations
fastify.get('/api/conversations', async (req) => {
  const limit = parseInt(req.query.limit) || 50;
  if (!memoryDB) return { conversations: [] };
  return { conversations: await memoryDB.getRecentConversations(limit) };
});

// ===== SYNC ENDPOINTS =====

// Push from local → web (enhanced)
fastify.post('/sync', async (req) => {
  const { memories = [], documents = [], patterns = null } = req.body || {};
  const syncId = `sync_${Date.now().toString(36)}`;
  
  // Sync to in-memory (for immediate use)
  memorySync.syncFromLocal(req.body);
  
  // Sync documents to database
  if (memoryDB && documents.length > 0) {
    await memoryDB.syncDocuments(documents);
  }
  
  // Log the sync
  if (memoryDB) {
    await memoryDB.logSync(syncId, 'local_to_web', memories.length, documents.length);
  }
  
  console.log(`📥 Sync complete: ${documents.length} docs to database`);
  broadcast({ type: 'sync_update', syncId });
  
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  return {
    success: true,
    syncId,
    documentsStored: documents.length,
    database: dbStatus
  };
});

// Pull from web → local
fastify.get('/sync/export', async () => {
  if (!memoryDB) return { error: 'Database not connected' };
  return await memoryDB.exportAll();
});

fastify.get('/sync/status', async () => {
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  return {
    inMemory: memorySync.getStatus(),
    database: dbStatus
  };
});

// ===== START SERVER =====

// Initialize database first
await initializeDatabase();

await fastify.listen({ port: PORT, host: '0.0.0.0' });
console.log(`🚀 Magic Chat v3.0 server running on port ${PORT}`);
console.log(`💜 Phase 3: Full PostgreSQL Database ENABLED!`);

const wss = new WebSocketServer({ server: fastify.server });

function broadcast(message, excludeId = null) {
  const payload = JSON.stringify(message);
  connectedClients.forEach((client, id) => {
    if (id !== excludeId && client.ws.readyState === 1) {
      client.ws.send(payload);
    }
  });
}

function broadcastPresence() {
  const users = [];
  connectedClients.forEach((client) => {
    if (client.user) {
      users.push({
        displayName: client.user.displayName,
        role: client.user.role,
        color: client.user.color
      });
    }
  });
  broadcast({ type: 'presence', users, count: users.length });
}

wss.on('connection', async (ws) => {
  const clientId = Date.now().toString(36) + Math.random().toString(36).substr(2);
  console.log(`🔌 Client connected: ${clientId}`);
  
  const conversationSaver = getConversationSaver();
  
  connectedClients.set(clientId, {
    ws,
    user: null,
    connectedAt: new Date().toISOString()
  });
  
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  ws.send(JSON.stringify({ 
    type: 'connected', 
    message: '💜 Connected to Aria v3.0 with PostgreSQL!', 
    clientId,
    database: dbStatus
  }));

  ws.on('message', async (rawMessage) => {
    try {
      const data = JSON.parse(rawMessage.toString());
      
      if (data.type === 'identify') {
        connectedClients.get(clientId).user = data.user;
        console.log(`👤 ${data.user?.displayName || 'Guest'} identified`);
        broadcastPresence();
        return;
      }
      
      if (data.type === 'chat') {
        const userName = data.user?.displayName || 'Guest';
        const userColor = data.user?.color || '#87CEEB';
        console.log(`💬 [${userName}]: ${data.content.substring(0, 50)}...`);
        
        connectedClients.get(clientId).user = data.user;
        
        broadcast({
          type: 'user_message',
          sender: userName,
          color: userColor,
          content: data.content,
          timestamp: new Date().toISOString()
        });
        
        broadcast({ type: 'typing', isTyping: true, who: 'Aria' });
        
        // Build context
        const onlineUsers = [];
        connectedClients.forEach((client) => {
          if (client.user) onlineUsers.push(client.user.displayName);
        });
        
        let groupContext = onlineUsers.length > 1 
          ? `\n\n🌐 GROUP CHAT! Users present: ${onlineUsers.join(', ')}`
          : '';
        
        // Add synced memory context + database context!
        groupContext += memorySync.generateContextString();
        if (memoryDB) {
          groupContext += await memoryDB.generateContextForClaude();
        }
        
        const response = await metaHarness.processMessage(
          data.content + groupContext, 
          data.model || 'auto', 
          { user: data.user, groupChat: onlineUsers.length > 1, onlineUsers }
        );
        
        // Save to file log
        conversationSaver.logMessage(data.content, response.content, data.user);
        
        // Save to PostgreSQL database!
        if (memoryDB) {
          await memoryDB.logConversation(
            conversationSaver.sessionId,
            userName,
            data.content,
            response.content,
            onlineUsers
          );
        }
        
        broadcast({ 
          type: 'response', 
          content: response.content, 
          model: response.model,
          timestamp: new Date().toISOString()
        });
        
        broadcast({ type: 'typing', isTyping: false, who: 'Aria' });
      }
    } catch (error) {
      console.error('❌ Error:', error.message);
      ws.send(JSON.stringify({ type: 'error', error: error.message }));
    }
  });

  ws.on('close', () => {
    const client = connectedClients.get(clientId);
    console.log(`🔌 ${client?.user?.displayName || 'Client'} disconnected`);
    connectedClients.delete(clientId);
    broadcastPresence();
  });
});

process.on('SIGTERM', () => {
  console.log('📴 Shutting down...');
  getConversationSaver().endSession();
  process.exit(0);
});

console.log('🔌 WebSocket ready');
console.log('💾 File logging ENABLED');
console.log('🗄️ PostgreSQL persistence ENABLED');
console.log('👥 Group chat ENABLED');
console.log('🔮 Bi-directional sync ENABLED');
