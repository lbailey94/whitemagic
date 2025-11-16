# WhiteMagic SDKs

Official SDKs for WhiteMagic - Memory infrastructure for AI agents.

## Available SDKs

### TypeScript/JavaScript SDK
**Package**: `whitemagic-client`  
**Status**: ✅ Published (v2.2.1)  
**Install**: `npm install whitemagic-client`  
**npm**: https://www.npmjs.com/package/whitemagic-client

[TypeScript SDK Documentation](./typescript.md)

### Python SDK
**Package**: `whitemagic-client`  
**Status**: ✅ Published (v2.2.1)  
**Install**: `pip install whitemagic-client`  
**PyPI**: https://pypi.org/project/whitemagic-client/

[Python SDK Documentation](./python.md)

---

## Quick Start

### TypeScript

```typescript
import { WhiteMagicClient } from 'whitemagic-client';

const client = new WhiteMagicClient({
  apiKey: process.env.WHITEMAGIC_API_KEY
});

const memory = await client.memories.create({
  title: 'My memory',
  content: 'Stored via SDK',
  type: 'short_term'
});
```

### Python

```python
from whitemagic_client import WhiteMagicClient

client = WhiteMagicClient(api_key='your-key')
memory = client.create_memory({
    'title': 'My memory',
    'content': 'Stored via SDK',
    'type': 'short_term'
})
```

---

## Features

Both SDKs provide:

- ✅ **Type Safety** - Full type hints/definitions
- ✅ **Auto-Retry** - Exponential backoff for failed requests
- ✅ **Error Handling** - Detailed exception messages
- ✅ **Timeout Control** - Configurable request timeouts
- ✅ **Memory Operations** - Create, read, update, delete, search
- ✅ **User Operations** - Profile, usage stats, quotas
- ✅ **Health Checks** - System health monitoring

---

## API Coverage

| Feature | TypeScript | Python | Status |
|---------|-----------|--------|--------|
| Create Memory | ✅ | ✅ | Ready |
| List Memories | ✅ | ✅ | Ready |
| Get Memory | ✅ | ✅ | Ready |
| Update Memory | ✅ | ✅ | Ready |
| Delete Memory | ✅ | ✅ | Ready |
| Restore Memory | ✅ | ✅ | Ready |
| Search Memories | ✅ | ✅ | Ready |
| Get User Profile | ✅ | ✅ | Ready |
| Get Usage Stats | ✅ | ✅ | Ready |
| Health Check | ✅ | ✅ | Ready |
| Collections | 🚧 | 🚧 | v2.2.0 |
| Webhooks | 🚧 | 🚧 | v2.2.0 |

---

## Publishing Status

### TypeScript SDK
- [x] Code complete
- [x] Built successfully
- [x] **Published to npm** ✅ (Nov 12, 2025)
- [ ] CI/CD for auto-publish

### Python SDK
- [x] Code complete
- [x] Tested
- [x] **Published to PyPI** ✅ (Nov 12, 2025)
- [ ] CI/CD for auto-publish

---

## Next Steps

1. **Set up npm account** with 2FA
2. **Set up PyPI account** with 2FA
3. **Test SDKs** against live API
4. **Publish to package registries**
5. **Set up CI/CD** for automated publishing
6. **Write integration tests**
7. **Create video tutorials**

---

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development setup and guidelines.

## License

MIT - See [LICENSE](../../LICENSE) for details.
