# Documentation Map - Quick Reference

**Which doc should I read?** Use this guide to navigate WhiteMagic's documentation.  
Looking for a full listing instead? See [docs/INDEX.md](docs/INDEX.md).

---

## 🆕 **I'm New Here**

**Start with these 3 documents** (in order):

1. **[README.md](README.md)** - Project overview, quick install (5 min read)
2. **[INSTALL.md](INSTALL.md)** - Detailed installation (10 min read)
3. **[guides/QUICKSTART.md](docs/guides/QUICKSTART.md)** - First memory in 5 minutes

**Then explore**: [docs/INDEX.md](docs/INDEX.md) - Complete documentation index

---

## 🚀 **I Want to Deploy**

### **Production Deploy** (2 hours)
→ **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive guide with Docker/PostgreSQL/Redis/Caddy

### **Local Development**
→ **[INSTALL.md](INSTALL.md)** - Local setup and configuration

### **Choose Your Hosting**
- **Vercel (frontend)**: Static dashboard hosting
- **Railway (backend)**: Managed Postgres + Redis + API
- **Self-hosted**: Docker Compose (all in `compose.yaml`)

**See**: [DEPLOYMENT_GUIDE.md § Hosting Options](DEPLOYMENT_GUIDE.md)

---

## 🔧 **I Want to Configure MCP**

### **Cursor / Windsurf / Claude Desktop**
→ **[whitemagic-mcp/README.md](whitemagic-mcp/README.md)** - Complete MCP setup guide

### **Test MCP Locally**
```bash
cd whitemagic-mcp
npm install && npm test  # 25+ automated tests
```

### **MCP Tools Reference**
- `create_memory`, `search_memories`, `get_context`
- `update_memory`, `delete_memory`, `restore_memory`
- `consolidate`

**See**: [whitemagic-mcp/README.md § Tools](whitemagic-mcp/README.md#tools)

---

## 📚 **I Need API Documentation**

### **REST API**
→ **[development/REST_API_DESIGN.md](docs/development/REST_API_DESIGN.md)** - API endpoints, schemas, authentication

### **Python SDK**
→ **[guides/ADVANCED_USAGE.md](docs/guides/ADVANCED_USAGE.md)** - Python API examples

### **Core Memory System**
→ **[guides/MEMORY_SYSTEM_README.md](docs/guides/MEMORY_SYSTEM_README.md)** - How memory tiers work

---

## 🧪 **I Want to Test**

### **Test Coverage Summary**
→ **[docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md](docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md)** - 196 Python + 27 MCP tests

### **Run Tests**
```bash
# Python tests (40+ tests)
python3 -m pytest -v

# MCP tests (25+ tests)
cd whitemagic-mcp && npm test
```

### **CI/CD Status**
- Python: `.github/workflows/ci.yml`
- MCP: `.github/workflows/test-mcp.yml`

---

## 🔐 **I Need Security Info**

### **Security Best Practices**
→ **[production/OPTIONAL_INTEGRATIONS.md](docs/production/OPTIONAL_INTEGRATIONS.md)** - Sentry, security headers, CORS

### **Run Security Guards**
```bash
python scripts/check_security_guards.py  # No wildcard CORS
python scripts/check_dependencies.py     # Manifest consistency
```

---

## 💼 **I Want Business Info**

### **Project Assessment**
→ **[docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md](docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md)** - Detailed review (Nov 8, 2025)

### **For Non-Technical Users**
→ **[PRIMER_FOR_NEW_USERS.md](PRIMER_FOR_NEW_USERS.md)** - What is WhiteMagic?

---

## 🗺️ **I Need the Roadmap**

→ **[ROADMAP.md](ROADMAP.md)** - Development phases, completed milestones, what's next

**Current Phase**: 2A Complete (REST API + Whop integration)  
**Next Phase**: 2B (Semantic search with embeddings)

---

## 📝 **I Want to Contribute**

1. **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
2. **[docs/INDEX.md](docs/INDEX.md)** - Full documentation index
3. **[TEST_COVERAGE_SUMMARY.md](TEST_COVERAGE_SUMMARY.md)** - Testing guide

---

## 🆘 **Troubleshooting**

### **Common Issues**
- **MCP not working**: [whitemagic-mcp/README.md § Troubleshooting](whitemagic-mcp/README.md#troubleshooting)
- **Deployment failing**: [DEPLOYMENT_GUIDE.md § Common Issues](DEPLOYMENT_GUIDE.md)
- **API errors**: Check logs in `docker compose logs api`

### **Get Help**
- 🐛 Issues: https://github.com/lbailey94/whitemagic/issues
- 💬 Discussions: https://github.com/lbailey94/whitemagic/discussions

---

## 📂 **All Core Documents**

### **Getting Started**
- [README.md](README.md) - Project overview
- [INSTALL.md](INSTALL.md) - Installation
- [START_HERE.md](START_HERE.md) - Quick reference card

### **Deployment**
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production deployment guide
- [INSTALL.md](INSTALL.md) - Local development setup

### **Configuration**
- [whitemagic-mcp/README.md](whitemagic-mcp/README.md) - MCP setup
- [.env.example](.env.example) - Environment variables
- [compose.yaml](compose.yaml) - Docker services

### **Assessment & Status**
- [docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md](docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md) - Latest review ⭐ **Most current**
- [docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md](docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md) - Testing stats
- [ROADMAP.md](ROADMAP.md) - Development plan

### **Reference**
- [docs/INDEX.md](docs/INDEX.md) - Complete doc index
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [LICENSE](LICENSE) - MIT License

---

## 🎯 **Quick Decision Tree**

**I want to...**

→ **Learn what WhiteMagic is**  
  └─ [README.md](README.md) → [PRIMER_FOR_NEW_USERS.md](PRIMER_FOR_NEW_USERS.md)

→ **Install and try it locally**  
  └─ [INSTALL.md](INSTALL.md) → [guides/QUICKSTART.md](docs/guides/QUICKSTART.md)

→ **Deploy to production**  
  └─ [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

→ **Set up local development**  
  └─ [INSTALL.md](INSTALL.md)

→ **Configure MCP in my IDE**  
  └─ [whitemagic-mcp/README.md](whitemagic-mcp/README.md)

→ **Understand the architecture**  
  └─ [guides/SYSTEM_OVERVIEW.md](docs/guides/SYSTEM_OVERVIEW.md)

→ **See test coverage**  
  └─ [docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md](docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md)

→ **Get business overview**  
  └─ [docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md](docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md)

→ **Navigate all docs**  
  └─ [docs/INDEX.md](docs/INDEX.md)

---

## 📊 **Documentation Stats**

- **Total markdown files**: 187
- **Active core docs**: ~15
- **Deployment guides**: 2 (production/local)
- **Archived docs**: 147 (in `docs/archive/`)
- **Last major update**: November 12, 2025

---

## ✅ **Doc Maintenance Status**

| Document | Status | Last Updated |
|----------|--------|--------------|
| README.md | ✅ Current | Nov 12, 2025 |
| DEPLOYMENT_GUIDE.md | ✅ Current | Nov 12, 2025 |
| INSTALL.md | ✅ Current | Nov 12, 2025 |
| docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md | ✅ Current | Nov 12, 2025 |
| whitemagic-mcp/README.md | ✅ Current | Nov 8, 2025 |
| docs/INDEX.md | ✅ Current | Nov 8, 2025 |

All deployment docs verified and synchronized as of November 12, 2025.

---

**Start here**: [README.md](README.md) → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) → **Ship it!** 🚀
