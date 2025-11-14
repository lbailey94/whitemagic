# WhiteMagic v2.1.4 - Developer Experience Edition

**Release Date**: November 13, 2025  
**Focus**: Making WhiteMagic 10x easier to use

---

## 🎉 What's New

### Official SDKs (TypeScript + Python)
Finally! Pre-built client libraries so you don't have to write API integration code.

**TypeScript/JavaScript**:
```bash
npm install whitemagic-client
```

**Python**:
```bash
pip install whitemagic-client
```

**What this means**: 
- ✅ 3 lines of code instead of 20+
- ✅ Built-in retry logic and error handling
- ✅ Full type safety (TypeScript) and type hints (Python)
- ✅ Auto-complete in your IDE
- ✅ Professional, production-ready clients

**Links**:
- npm: https://www.npmjs.com/package/whitemagic-client
- PyPI: https://pypi.org/project/whitemagic-client/
- Docs: [TypeScript](docs/sdk/typescript.md) | [Python](docs/sdk/python.md)

---

### One-Command IDE Setup
Stop manually editing config files! Auto-setup wizard for MCP-compatible IDEs.

```bash
npx whitemagic-mcp-setup
```

**What this means**:
- ✅ Automatically detects Cursor, Windsurf, Claude Desktop, or VS Code
- ✅ Guided prompts for API key and settings
- ✅ Tests your connection before saving
- ✅ Backs up your existing config
- ✅ Ready in < 2 minutes

**Supported IDEs**:
- Cursor
- Windsurf  
- Claude Desktop (macOS, Windows, Linux)
- VS Code with Cline extension

**Docs**: [MCP CLI Setup Guide](docs/MCP_CLI_SETUP.md)

---

## 📈 Impact

### Before v2.1.4
```bash
# Read API docs (10 min)
# Write custom integration code (15 min)
# Find IDE config file location (5 min)
# Edit JSON by hand (5 min)
# Debug typos and errors (5 min)
# Total: ~40 minutes to get started
```

### After v2.1.4
```bash
npm install whitemagic-client      # 30 seconds
npx whitemagic-mcp-setup           # 2 minutes
# Total: ~3 minutes to get started
```

**13x faster onboarding!** 🚀

---

## 🛠️ Technical Details

### SDK Features
**TypeScript SDK**:
- ESM modules with full type definitions
- Fetch API with configurable timeout
- Exponential backoff retry logic
- Custom error class with context
- 12.5 kB package size

**Python SDK**:
- Pydantic V2 models for validation
- httpx client with async support ready
- Context manager (`with` statement) support
- Type hints for Python 3.9+
- ~12 kB package size

**Both SDKs**:
- Memory CRUD operations
- Search with filters
- User info and usage stats
- Health checks
- Comprehensive documentation

### CLI Features
**Auto-Detection**:
- Scans 4 IDE types automatically
- Platform-specific paths (macOS, Windows, Linux)
- Prioritizes existing configurations

**Safety**:
- Timestamped config backups
- Safe merging (preserves other MCP servers)
- Rollback capability
- Validation before writing

**Validation**:
- API key format checking
- Connection testing (health + auth)
- Clear error messages
- Version detection

---

## 📚 Documentation

### New Guides
- [TypeScript SDK Documentation](docs/sdk/typescript.md)
- [Python SDK Documentation](docs/sdk/python.md)
- [SDK Overview](docs/sdk/README.md)
- [MCP CLI Setup Guide](docs/MCP_CLI_SETUP.md)

### Updated
- [README.md](README.md) - New Quick Start section
- [Getting Started](docs/guides/QUICKSTART.md) - SDK examples

---

## 🐛 Bug Fixes

- Fixed TypeScript build (added DOM lib to tsconfig)
- Updated Windsurf config path (`mcp_server_config.json`)
- Improved error handling in setup wizard

---

## 🔄 Migration Guide

### For Existing Users

**No breaking changes!** Everything from v2.1.3 still works.

**New options available**:

1. **Switch to SDKs** (optional, recommended):
   ```bash
   # TypeScript
   npm install whitemagic-client
   
   # Python
   pip install whitemagic-client
   ```

2. **Use auto-setup for new IDEs** (optional):
   ```bash
   npx whitemagic-mcp-setup
   ```

Your existing integrations, API keys, and configurations continue to work unchanged.

---

## 📦 What's Included

### npm Packages
- `whitemagic-client@2.1.4` - TypeScript/JavaScript SDK
- `whitemagic-mcp@2.1.4` - MCP server with CLI setup tool

### PyPI Packages
- `whitemagic-client==2.1.4` - Python SDK
- `whitemagic==2.1.3` - Core library (unchanged)

---

## 🎯 Use Cases

### For Individual Developers
```typescript
// Quick prototype with memory
import { WhiteMagicClient } from 'whitemagic-client';

const client = new WhiteMagicClient({ apiKey: process.env.API_KEY });
await client.memories.create({
  title: 'User preferences',
  content: JSON.stringify(userData)
});
```

### For Teams
```bash
# Onboard new developer
npm install whitemagic-client
npx whitemagic-mcp-setup
# New dev is productive in < 5 minutes
```

### For AI Agent Builders
```python
# Give your agent memory
from whitemagic_client import WhiteMagicClient

with WhiteMagicClient(api_key='key') as client:
    # Agent stores learned patterns
    client.create_memory({
        'title': 'User preference',
        'content': 'Prefers concise responses',
        'tags': ['user_123', 'preferences']
    })
```

---

## 🚀 What's Next (v2.1.5)

Planned for next release:
- Usage dashboard (visualize your memory usage)
- Enhanced website (whitemagic.dev)
- Whop integration improvements
- Additional example projects

---

## 🙏 Thank You

Special thanks to:
- Early adopters who provided feedback
- MCP community for IDE standards
- Everyone testing and using WhiteMagic

---

## 📊 Stats

**Development Time**: 1 day intensive sprint  
**Code Added**: ~2,900 lines (SDKs + CLI + docs)  
**Tests**: All passing (223 tests)  
**Documentation**: 1,200+ lines added/updated

---

## 🔗 Links

- **Documentation**: https://github.com/lbailey94/whitemagic#readme
- **TypeScript SDK**: https://www.npmjs.com/package/whitemagic-client
- **Python SDK**: https://pypi.org/project/whitemagic-client/
- **Issues**: https://github.com/lbailey94/whitemagic/issues
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 💬 Feedback

We'd love to hear from you! 

- Found a bug? [Open an issue](https://github.com/lbailey94/whitemagic/issues)
- Have a feature request? [Start a discussion](https://github.com/lbailey94/whitemagic/discussions)
- Using WhiteMagic in production? Let us know!

---

**Full Changelog**: https://github.com/lbailey94/whitemagic/compare/v2.1.3...v2.1.4

---

*Making AI memory infrastructure accessible to everyone.* 🧙✨
