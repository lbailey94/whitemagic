# @whitemagic/client

Official TypeScript/JavaScript SDK for WhiteMagic - Memory infrastructure for AI agents.

## Installation

```bash
npm install @whitemagic/client
```

## Quick Start

```typescript
import { WhiteMagicClient } from '@whitemagic/client';

// Initialize client
const client = new WhiteMagicClient({
  apiKey: process.env.WHITEMAGIC_API_KEY,
  baseUrl: 'https://api.whitemagic.dev' // Optional, defaults to production
});

// Create a memory
const memory = await client.memories.create({
  title: 'My first memory',
  content: 'This is stored via the TypeScript SDK',
  type: 'short_term',
  tags: ['test', 'demo']
});

console.log('Memory created:', memory.id);

// Search memories
const results = await client.memories.search({
  query: 'test',
  limit: 10
});

// List all memories
const memories = await client.memories.list({
  type: 'short_term',
  skip: 0,
  limit: 20
});

// Update a memory
await client.memories.update(memory.id, {
  content: 'Updated content',
  tags: ['test', 'demo', 'updated']
});

// Delete a memory (soft delete - archives)
await client.memories.delete(memory.id);

// Restore a memory
await client.memories.restore(memory.id);
```

## Configuration

```typescript
const client = new WhiteMagicClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.whitemagic.dev', // Optional
  timeout: 30000, // Request timeout in ms (default: 30000)
  retries: 3, // Number of retries (default: 3)
});
```

## Features

- ✅ **Type-safe** - Full TypeScript support with generated types
- ✅ **Auto-retry** - Automatic retry with exponential backoff
- ✅ **Error handling** - Detailed error messages
- ✅ **Timeout control** - Configurable request timeouts
- ✅ **ESM & CommonJS** - Works in both module systems

## API Coverage

### Memories
- `memories.create()` - Create a new memory
- `memories.list()` - List memories with filtering
- `memories.get()` - Get a single memory by ID
- `memories.update()` - Update a memory
- `memories.delete()` - Delete (archive) a memory
- `memories.restore()` - Restore an archived memory
- `memories.search()` - Semantic search across memories

### Collections (v2.2.0+)
- `collections.create()` - Create a memory collection
- `collections.list()` - List collections
- `collections.get()` - Get collection by ID

### Users
- `users.me()` - Get current user info
- `users.usage()` - Get usage statistics

## Error Handling

```typescript
try {
  const memory = await client.memories.create({...});
} catch (error) {
  if (error.status === 401) {
    console.error('Invalid API key');
  } else if (error.status === 429) {
    console.error('Rate limit exceeded');
  } else {
    console.error('Error:', error.message);
  }
}
```

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Test
npm test
```

## License

MIT

## Links

- [WhiteMagic Documentation](https://github.com/lbailey94/whitemagic)
- [API Reference](https://api.whitemagic.dev/docs)
- [GitHub](https://github.com/lbailey94/whitemagic)
- [Issues](https://github.com/lbailey94/whitemagic/issues)
