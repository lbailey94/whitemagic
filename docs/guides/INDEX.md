# WhiteMagic Documentation Index

Welcome to WhiteMagic! This index will help you find the right documentation quickly.
Need a decision-tree style guide instead? See [DOCUMENTATION_MAP.md](archive/development/DOCUMENTATION_MAP.md) for a “which doc should I read?” flow.

---

## 🚀 **Quick Start** (Start Here!)

**New to WhiteMagic?** Start with these:

1. **[START_HERE.md](../START_HERE.md)** - **⭐ Best first read** - Quick orientation & path selection
2. **[README.md](../README.md)** - Project overview, features, installation
3. **[guides/QUICKSTART.md](guides/QUICKSTART.md)** - 5-minute hands-on tutorial
4. **[USER_GUIDE.md](USER_GUIDE.md)** - Complete beginner to advanced guide
5. **[README.md#-features](../README.md#-features)** - Snapshot of v2.6.5 parallel infrastructure + scratchpads

---

## 🎯 **Strategic Documentation**

**Understand the vision and architecture**:

1. **[VISION.md](VISION.md)** - **Philosophy, theory, and strategic direction**
   - Why "white magic"? The name's meaning
   - Core theory: Memory → Intelligence
   - Multi-timescale memory architecture
   - Market context & growth projections
   - 2026-2027 roadmap

2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - **Technical design and system overview**
   - Component structure
   - Data flow patterns
   - API design principles
   - Security model
   - Deployment architecture

3. **[VISION_TO_REALITY.md](VISION_TO_REALITY.md)** - **Gap analysis & priorities**
   - What's implemented vs what's planned
   - Strategic opportunities
   - Action plan (30/90/180 days)
   - Lessons from deployment

---

## 📚 **Core Documentation**

### User Guides

- **[Memory System](guides/MEMORY_SYSTEM_README.md)** - How the memory system works
- **[Advanced Usage](guides/ADVANCED_USAGE.md)** - Power user features
- **[System Overview](guides/SYSTEM_OVERVIEW.md)** - Architecture deep-dive

### MCP & Parallel Integration

- **[whitemagic-mcp/README.md](../whitemagic-mcp/README.md)** - MCP server setup for Cursor/Windsurf/Claude
- **[Tool Wrappers Guide](guides/TOOL_WRAPPERS_GUIDE.md)** - Framework integrations
- **[guides/CLI_METRICS.md](guides/CLI_METRICS.md)** - Track workflow health + prep for `whitemagic audit/docs-check`

---

## 🚢 **Production Deployment**

### Essential Reading

- **[DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)** - Complete deployment guide
  ⭐ **Most comprehensive** - Docker, PostgreSQL, Redis, Caddy
- **[DEPLOY_NOW.md](archive/v2.6.5-prep/DEPLOY_NOW.md)** - Quick deployment checklist (archived)
  ⏱️ **~45 minutes** from zero to production
- **[START_HERE.md](../START_HERE.md)** - Quick reference card

### Production Resources

- **[Optional Integrations](production/OPTIONAL_INTEGRATIONS.md)** - Sentry, Prometheus, log shipping
- **[Production Checklist](production/PRODUCTION_CHECKLIST.md)** - Pre-deployment verification
- **[Testing & Deployment Summary](production/TESTING_DEPLOYMENT_SUMMARY.md)** - Test coverage & strategies

---

## 🔧 **Development**

### Planning & Design

- **[ROADMAP.md](../ROADMAP.md)** - Project roadmap & milestones (current v2.6.5, upcoming 2.6.5/2.6.5)
- **[RELEASE_PLAN_v2.6.5_to_v2.1.9.md](RELEASE_PLAN_v2.6.5_to_v2.1.9.md)** - 3-week progressive release plan
- **[REST API Design](development/REST_API_DESIGN.md)** - API architecture
- **[Bugfix Report](development/BUGFIX_REPORT.md)** - Known issues & fixes

### Historical Context

- **[archive/phases/](archive/phases/)** - Completed phase documentation
- **[archive/reviews/](archive/reviews/)** - Historical review documents

---

## 💼 **For Business Users**

- **[PRIMER_FOR_NEW_USERS.md](../PRIMER_FOR_NEW_USERS.md)** - Non-technical overview
- **[PROJECT_ASSESSMENT.md](../PROJECT_ASSESSMENT.md)** - Honest project assessment
- **[EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md)** - Business value & ROI

---

## 📦 **Package & Distribution**

- **[CHANGELOG.md](../CHANGELOG.md)** - Version history
- **[RELEASE_NOTES_v0.1.0.md](../RELEASE_NOTES_v0.1.0.md)** - Initial release notes
- **[DEPENDENCIES_INSTALLED.md](../DEPENDENCIES_INSTALLED.md)** - Dependency manifest
- **[requirements-plugins.txt](../requirements-plugins.txt)** - Optional integrations

---

## 🗂️ **Archive**

Historical documents (for reference only):

- **[archive/](archive/)** - Day-by-day progress, old designs, deprecated docs
  - Phase completion summaries
  - Daily checkpoints
  - Old API designs
  - Migration guides

**Note**: Archive docs may be outdated. Refer to main documentation for current information.

---

## 🎯 **Common Tasks**

### I want to…

**Install WhiteMagic**
→ [README.md](../README.md#installation) → [INSTALL.md](../INSTALL.md)

**Deploy to production**
→ [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)

**Set up MCP in Cursor/Windsurf**
→ [whitemagic-mcp/README.md](../whitemagic-mcp/README.md)

**Understand the vision and philosophy**
→ [VISION.md](VISION.md) → [ARCHITECTURE.md](ARCHITECTURE.md)

**Understand the technical architecture**
→ [ARCHITECTURE.md](ARCHITECTURE.md) → [guides/SYSTEM_OVERVIEW.md](guides/SYSTEM_OVERVIEW.md)

**Add optional integrations (Sentry, etc.)**
→ [production/OPTIONAL_INTEGRATIONS.md](production/OPTIONAL_INTEGRATIONS.md)

**See what's changed**
→ [CHANGELOG.md](../CHANGELOG.md)

**See the roadmap**
→ [ROADMAP.md](../ROADMAP.md) → [RELEASE_PLAN_v2.6.5_to_v2.1.9.md](RELEASE_PLAN_v2.6.5_to_v2.1.9.md)

**Run audits / automate docs (v2.6.5)**
→ [guides/CLI_METRICS.md](guides/CLI_METRICS.md#44-cicd-integration) → README (audit + exec plan overview)

---

## 🆘 **Need Help?**

1. **Check the docs above** (most questions answered here)
2. **Read troubleshooting**: [whitemagic-mcp/README.md#troubleshooting](../whitemagic-mcp/README.md#troubleshooting)
3. **File an issue**: <https://github.com/lbailey94/whitemagic/issues>
4. **Discussions**: <https://github.com/lbailey94/whitemagic/discussions>

---

## 📊 **Documentation Stats**

- **Total docs**: 190+ markdown files
- **Active docs**: ~40 (core + guides + production + strategic)
- **Archived docs**: ~150 (historical reference, properly organized)
- **Cleanup**: v2.6.5 - Archived phases/, reviews/, daily logs, obsolete docs
- **Last updated**: November 16, 2025 (v2.6.5 parallel release)

---

**Tip**: Bookmark this page! It's your map to the entire WhiteMagic documentation ecosystem.
