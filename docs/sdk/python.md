# Python SDK

Official Python SDK for WhiteMagic.

## Installation

```bash
pip install whitemagic-client
```

## Quick Start

```python
import os
from whitemagic_client import WhiteMagicClient

client = WhiteMagicClient(api_key=os.getenv('WHITEMAGIC_API_KEY'))

# Create a memory
memory = client.create_memory({
    'title': 'Meeting Notes',
    'content': 'Discussed Q4 roadmap',
    'type': 'short_term',
    'tags': ['meeting', 'q4']
})

print(f'Created: {memory.id}')
```

## Configuration

```python
from whitemagic_client import WhiteMagicClient

client = WhiteMagicClient(
    api_key='your-api-key',
    base_url='https://api.whitemagic.dev',  # Optional (default: production)
    timeout=30.0,                            # Optional (default: 30.0)
    retries=3,                               # Optional (default: 3)
)
```

## Context Manager

```python
with WhiteMagicClient(api_key='your-key') as client:
    memory = client.create_memory({
        'title': 'Test',
        'content': 'Content',
        'type': 'short_term'
    })
    # Client automatically closed
```

## Memory Operations

### Create Memory

```python
from whitemagic_client import CreateMemoryRequest

memory = client.create_memory(
    CreateMemoryRequest(
        title='Important Note',
        content='Remember to follow up',
        type='short_term',
        tags=['todo', 'urgent'],
        metadata={'priority': 'high'}
    )
)

# Or use dict
memory = client.create_memory({
    'title': 'Important Note',
    'content': 'Remember to follow up',
    'type': 'short_term',
    'tags': ['todo', 'urgent']
})
```

### List Memories

```python
memories = client.list_memories({
    'type': 'short_term',
    'tags': ['todo'],
    'skip': 0,
    'limit': 20
})

for memory in memories:
    print(f'{memory.title}: {memory.content}')
```

### Get Memory by ID

```python
memory = client.get_memory('memory-id-here')
print(memory.title)
```

### Update Memory

```python
updated = client.update_memory('memory-id-here', {
    'content': 'Updated content',
    'tags': ['updated', 'important']
})
```

### Delete Memory

```python
# Soft delete (archives the memory)
client.delete_memory('memory-id-here')
```

### Restore Memory

```python
restored = client.restore_memory('memory-id-here')
```

### Search Memories

```python
results = client.search_memories({
    'query': 'project planning',
    'type': 'short_term',  # Optional
    'tags': ['work'],      # Optional
    'limit': 10
})
```

## User Operations

### Get Current User

```python
user = client.get_current_user()
print(user.email)
print(user.plan)
print(user.quota)
```

### Get Usage Stats

```python
stats = client.get_usage_stats()
print(f'API calls today: {stats.api_calls_today}')
print(f'Memory count: {stats.memory_count}')
print(f'Storage: {stats.storage_bytes} bytes')
```

## System Operations

### Health Check

```python
health = client.health_check()
print(f'Status: {health.status}')
print(f'Version: {health.version}')
```

## Error Handling

```python
from whitemagic_client import WhiteMagicError

try:
    memory = client.create_memory({...})
except WhiteMagicError as e:
    print(f'Error [{e.status}]: {e.message}')

    if e.status == 401:
        print('Invalid API key')
    elif e.status == 429:
        print('Rate limit exceeded')
    elif e.status == 404:
        print('Memory not found')
```

## Type Hints

The SDK uses Pydantic for full type safety:

```python
from whitemagic_client import (
    Memory,
    CreateMemoryRequest,
    UpdateMemoryRequest,
    ListMemoriesParams,
    SearchMemoriesParams,
    User,
    UsageStats,
    MemoryType,
)

def create_work_memory(title: str, content: str) -> Memory:
    request = CreateMemoryRequest(
        title=title,
        content=content,
        type='short_term',
        tags=['work']
    )
    return client.create_memory(request)
```

## Examples

### Bulk Create Memories

```python
notes = [
    {'title': 'Note 1', 'content': 'Content 1', 'type': 'short_term'},
    {'title': 'Note 2', 'content': 'Content 2', 'type': 'short_term'},
]

created = [client.create_memory(note) for note in notes]
```

### Search and Filter

```python
# Get all work-related short-term memories
work_memories = client.list_memories({
    'type': 'short_term',
    'tags': ['work']
})

# Search for specific content
results = client.search_memories({
    'query': 'quarterly report',
    'limit': 5
})
```

### Usage Monitoring

```python
import time

while True:
    stats = client.get_usage_stats()
    if stats.api_calls_today > 900:
        print('Warning: Approaching daily API limit!')
    time.sleep(60)  # Check every minute
```

### Async Context Manager (Future)

```python
# Coming in v2.2.7
from whitemagic_client import AsyncWhiteMagicClient

async with AsyncWhiteMagicClient(api_key='your-key') as client:
    memory = await client.create_memory({...})
```

## Best Practices

1. **Use Environment Variables** for API keys
2. **Handle Exceptions** appropriately
3. **Monitor Usage** to avoid hitting quotas
4. **Use Type Hints** for better IDE support
5. **Use Context Managers** for automatic cleanup
6. **Batch Operations** when possible

## Troubleshooting

### "Invalid API key"

- Verify your API key is correct
- Check that it hasn't been revoked
- Ensure you're using the correct environment

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
- [Package Source](https://github.com/lbailey94/whitemagic/tree/main/clients/python)

## Support

- [GitHub Issues](https://github.com/lbailey94/whitemagic/issues)
- [Documentation](https://github.com/lbailey94/whitemagic#readme)
