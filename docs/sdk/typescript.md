# TypeScript/JavaScript SDK

Official TypeScript SDK for WhiteMagic.

## Installation

```bash
npm install @whitemagic/client
# or
yarn add @whitemagic/client
# or
pnpm add @whitemagic/client
```

## Quick Start

```typescript
import { WhiteMagicClient } from '@whitemagic/client';

const client = new WhiteMagicClient({
  apiKey: process.env.WHITEMAGIC_API_KEY
});

// Create a memory
const memory = await client.memories.create({
  title: 'Meeting Notes',
  content: 'Discussed Q4 roadmap',
  type: 'short_term',
  tags: ['meeting', 'q4']
});

console.log('Created:', memory.id);
```

## Configuration

```typescript
const client = new WhiteMagicClient({
  apiKey: 'your-api-key',           // Required
  baseUrl: 'https://api.whitemagic.dev',  // Optional (default: production)
  timeout: 30000,                    // Optional (default: 30000ms)
  retries: 3,                        // Optional (default: 3)
});
```

## Memory Operations

### Create Memory

```typescript
const memory = await client.memories.create({
  title: 'Important Note',
  content: 'Remember to follow up',
  type: 'short_term',  // or 'long_term'
  tags: ['todo', 'urgent'],
  metadata: { priority: 'high' }
});
```

### List Memories

```typescript
const memories = await client.memories.list({
  type: 'short_term',
  tags: ['todo'],
  skip: 0,
  limit: 20
});

for (const memory of memories) {
  console.log(`${memory.title}: ${memory.content}`);
}
```

### Get Memory by ID

```typescript
const memory = await client.memories.get('memory-id-here');
console.log(memory.title);
```

### Update Memory

```typescript
const updated = await client.memories.update('memory-id-here', {
  content: 'Updated content',
  tags: ['updated', 'important']
});
```

### Delete Memory

```typescript
// Soft delete (archives the memory)
await client.memories.delete('memory-id-here');
```

### Restore Memory

```typescript
const restored = await client.memories.restore('memory-id-here');
```

### Search Memories

```typescript
const results = await client.memories.search({
  query: 'project planning',
  type: 'short_term',  // Optional
  tags: ['work'],      // Optional
  limit: 10
});
```

## User Operations

### Get Current User

```typescript
const user = await client.users.me();
console.log(user.email);
console.log(user.plan);
console.log(user.quota);
```

### Get Usage Stats

```typescript
const stats = await client.users.usage();
console.log(`API calls today: ${stats.api_calls_today}`);
console.log(`Memory count: ${stats.memory_count}`);
console.log(`Storage: ${stats.storage_bytes} bytes`);
```

## System Operations

### Health Check

```typescript
const health = await client.health();
console.log(`Status: ${health.status}`);
console.log(`Version: ${health.version}`);
```

## Error Handling

```typescript
import { WhiteMagicError } from '@whitemagic/client';

try {
  const memory = await client.memories.create({...});
} catch (error) {
  if (error instanceof WhiteMagicError) {
    console.error(`Error [${error.status}]: ${error.message}`);
    
    if (error.status === 401) {
      console.error('Invalid API key');
    } else if (error.status === 429) {
      console.error('Rate limit exceeded');
    } else if (error.status === 404) {
      console.error('Memory not found');
    }
  } else {
    console.error('Unexpected error:', error);
  }
}
```

## TypeScript Types

The SDK is fully typed. Import types as needed:

```typescript
import type {
  Memory,
  CreateMemoryRequest,
  UpdateMemoryRequest,
  ListMemoriesParams,
  SearchMemoriesParams,
  User,
  UsageStats,
  MemoryType,
} from '@whitemagic/client';

const createRequest: CreateMemoryRequest = {
  title: 'Test',
  content: 'Content',
  type: 'short_term',
  tags: []
};
```

## Examples

### Bulk Create Memories

```typescript
const notes = [
  { title: 'Note 1', content: 'Content 1', type: 'short_term' as const },
  { title: 'Note 2', content: 'Content 2', type: 'short_term' as const },
];

const created = await Promise.all(
  notes.map(note => client.memories.create(note))
);
```

### Search and Filter

```typescript
// Get all work-related short-term memories
const workMemories = await client.memories.list({
  type: 'short_term',
  tags: ['work']
});

// Search for specific content
const results = await client.memories.search({
  query: 'quarterly report',
  limit: 5
});
```

### Usage Monitoring

```typescript
setInterval(async () => {
  const stats = await client.users.usage();
  if (stats.api_calls_today > 900) {
    console.warn('Approaching daily API limit!');
  }
}, 60000); // Check every minute
```

## Best Practices

1. **Use Environment Variables** for API keys
2. **Handle Errors** appropriately
3. **Monitor Usage** to avoid hitting quotas
4. **Use TypeScript** for full type safety
5. **Batch Operations** when possible
6. **Cache Results** if appropriate

## Troubleshooting

### "Invalid API key"
- Verify your API key is correct
- Check that it hasn't been revoked
- Ensure you're using the `X-API-Key` header

### "Rate limit exceeded"
- Check your current plan limits
- Implement backoff logic
- Upgrade to higher tier if needed

### Timeout errors
- Increase timeout setting
- Check network connectivity
- Verify API status

## Source Code

- [GitHub Repository](https://github.com/lbailey94/whitemagic)
- [Package Source](https://github.com/lbailey94/whitemagic/tree/main/clients/typescript)

## Support

- [GitHub Issues](https://github.com/lbailey94/whitemagic/issues)
- [Documentation](https://github.com/lbailey94/whitemagic#readme)
