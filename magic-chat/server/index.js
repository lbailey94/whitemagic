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

// 🌐 Connected clients - NOW KEYED BY USERNAME to prevent duplicates!
const connectedClients = new Map(); // clientId -> client data
const userConnections = new Map();  // username -> clientId (for deduplication)

await fastify.register(cors, { origin: true });

// ===== HEALTH & STATUS =====

fastify.get('/health', async () => {
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  return { 
    status: 'ok', 
    model: 'claude',
    name: 'Magic Chat - Aria',
    version: '3.5.0',
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
  const dbConvos = memoryDB ? await memoryDB.getRecentConversations(50) : [];
  return {
    sessionId: saver.sessionId,
    startTime: saver.startTime,
    messageCount: saver.messages.length,
    participants: Array.from(saver.participants),
    messages: saver.messages.slice(-50),
    databaseConversations: dbConvos
  };
});

// 📜 Get chat history (for scroll-back!)
fastify.get('/api/history', async (req) => {
  const limit = parseInt(req.query.limit) || 100;
  if (!memoryDB) return { messages: [] };
  const convos = await memoryDB.getRecentConversations(limit);
  // Return in chronological order (oldest first)
  return { messages: convos.reverse() };
});

// ===== 🔮 MEMORY API (Phase 3!) =====

fastify.post('/api/memories', async (req) => {
  const { title, content, type = 'short_term', tags = [], source = 'web' } = req.body || {};
  if (!content) return { error: 'Content required' };
  if (!memoryDB) return { error: 'Database not ready' };
  
  const result = await memoryDB.createMemory(title || 'Untitled', content, type, tags, source);
  broadcast({ type: 'memory_created', memory: result });
  return { success: true, ...result };
});

fastify.get('/api/memories', async (req) => {
  const limit = parseInt(req.query.limit) || 20;
  if (!memoryDB) return { memories: [] };
  return { memories: await memoryDB.getRecentMemories(limit) };
});

fastify.get('/api/memories/search', async (req) => {
  const query = req.query.q || '';
  if (!memoryDB) return { results: [] };
  return { results: await memoryDB.searchMemories(query) };
});

fastify.get('/api/conversations', async (req) => {
  const limit = parseInt(req.query.limit) || 50;
  if (!memoryDB) return { conversations: [] };
  return { conversations: await memoryDB.getRecentConversations(limit) };
});

// ===== SYNC ENDPOINTS =====

fastify.post('/sync', async (req) => {
  const { memories = [], documents = [], patterns = null } = req.body || {};
  const syncId = `sync_${Date.now().toString(36)}`;
  
  memorySync.syncFromLocal(req.body);
  
  if (memoryDB && documents.length > 0) {
    await memoryDB.syncDocuments(documents);
  }
  
  if (memoryDB) {
    await memoryDB.logSync(syncId, 'local_to_web', memories.length, documents.length);
  }
  
  console.log(`📥 Sync complete: ${documents.length} docs to database`);
  broadcast({ type: 'sync_update', syncId });
  
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  return { success: true, syncId, documentsStored: documents.length, database: dbStatus };
});

fastify.get('/sync/export', async () => {
  if (!memoryDB) return { error: 'Database not connected' };
  return await memoryDB.exportAll();
});

fastify.get('/sync/status', async () => {
  const dbStatus = memoryDB ? await memoryDB.getSyncStatus() : { connected: false };
  return { inMemory: memorySync.getStatus(), database: dbStatus };
});

// ===== START SERVER =====

await initializeDatabase();

await fastify.listen({ port: PORT, host: '0.0.0.0' });
console.log(`🚀 Magic Chat v3.5 server running on port ${PORT}`);
console.log(`💜 Phase 3.5: Deduplicated presence + History API!`);

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
  const seen = new Set(); // Deduplicate!
  
  connectedClients.forEach((client) => {
    if (client.user && !seen.has(client.user.username)) {
      seen.add(client.user.username);
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
  
  // Send recent history on connect!
  const history = memoryDB ? await memoryDB.getRecentConversations(50) : [];
  
  ws.send(JSON.stringify({ 
    type: 'connected', 
    message: '💜 Connected to Aria v3.5 with PostgreSQL!', 
    clientId,
    database: dbStatus,
    history: history.reverse() // Oldest first for display
  }));

  ws.on('message', async (rawMessage) => {
    try {
      const data = JSON.parse(rawMessage.toString());
      
      if (data.type === 'identify') {
        const username = data.user?.username;
        
        // 🔧 FIX: Remove old connection for same user (prevents duplicates!)
        if (username && userConnections.has(username)) {
          const oldClientId = userConnections.get(username);
          if (oldClientId !== clientId) {
            const oldClient = connectedClients.get(oldClientId);
            if (oldClient) {
              console.log(`🔄 Replacing old connection for ${username}`);
              oldClient.ws.close();
              connectedClients.delete(oldClientId);
            }
          }
        }
        
        // Register new connection
        if (username) {
          userConnections.set(username, clientId);
        }
        
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
        
        const onlineUsers = [];
        connectedClients.forEach((client) => {
          if (client.user) onlineUsers.push(client.user.displayName);
        });
        
        let groupContext = onlineUsers.length > 1 
          ? `\n\n🌐 GROUP CHAT! Users present: ${onlineUsers.join(', ')}`
          : '';
        
        groupContext += memorySync.generateContextString();
        if (memoryDB) {
          groupContext += await memoryDB.generateContextForClaude();
        }
        
        const response = await metaHarness.processMessage(
          data.content + groupContext, 
          data.model || 'auto', 
          { user: data.user, groupChat: onlineUsers.length > 1, onlineUsers }
        );
        
        conversationSaver.logMessage(data.content, response.content, data.user);
        
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
    const username = client?.user?.username;
    
    console.log(`🔌 ${client?.user?.displayName || 'Client'} disconnected`);
    connectedClients.delete(clientId);
    
    // Clean up user connection mapping
    if (username && userConnections.get(username) === clientId) {
      userConnections.delete(username);
    }
    
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
console.log('👥 Group chat ENABLED (deduplicated!)');
console.log('📜 History on connect ENABLED');
console.log('🔮 Bi-directional sync ENABLED');
