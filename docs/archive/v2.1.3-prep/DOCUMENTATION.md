# WhiteMagic Documentation Index

**Version**: 2.1.2  
**Last Updated**: November 3, 2025

---

## 📖 Quick Links

### For Users
- **[README.md](README.md)** - Project overview and quick start
- **[INSTALL.md](INSTALL.md)** - Installation guide (all platforms)
- **[ROADMAP.md](ROADMAP.md)** - Development roadmap and upcoming features
- **[RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md)** - v0.1.0 release details

### For Developers
- **[docs/development/PHASE_2A_PLAN.md](docs/development/PHASE_2A_PLAN.md)** - Current phase plan
- **[whitemagic-mcp/README.md](whitemagic-mcp/README.md)** - MCP server documentation
- **[tests/](tests/)** - Test suite and examples

---

## 📚 Full Documentation Structure

### Root Level (Essential Docs)

#### README.md
**Purpose**: Project overview, quick start, key features  
**Audience**: First-time visitors, developers evaluating the project  
**Content**:
- What is WhiteMagic?
- Key features
- Quick installation
- Basic usage examples
- Links to detailed docs

#### INSTALL.md
**Purpose**: Complete installation instructions  
**Audience**: Users setting up WhiteMagic  
**Content**:
- Prerequisites (Python, Node.js)
- Installation methods (git clone, pip)
- MCP server setup for IDEs
- Verification steps
- Troubleshooting

#### ROADMAP.md
**Purpose**: Project vision and development timeline  
**Audience**: Contributors, stakeholders, interested users  
**Content**:
- Completed phases (1A, 1B)
- Current phase (2A)
- Future phases (2B, 3)
- Feature requests
- Community input

#### RELEASE_NOTES_v0.1.0.md
**Purpose**: Release announcement and changelog  
**Audience**: Users upgrading or evaluating versions  
**Content**:
- What's new in v0.1.0
- Breaking changes
- Known issues
- Upgrade instructions

---

### docs/guides/ (User Guides)

#### QUICKSTART.md
**Purpose**: 5-minute tutorial to get started  
**Audience**: New users who want to try WhiteMagic immediately  
**Content**:
- Create your first memory
- Search and retrieve
- Use with MCP in IDE
- Next steps

#### ADVANCED_USAGE.md
**Purpose**: Deep dive into advanced features  
**Audience**: Power users, integration developers  
**Content**:
- Custom memory types
- Advanced search techniques
- Context generation strategies
- Memory consolidation workflows
- Automation examples

#### MEMORY_SYSTEM_README.md
**Purpose**: Technical overview of the memory system  
**Audience**: Developers, contributors  
**Content**:
- Tiered storage architecture
- Memory lifecycle
- Metadata management
- Tag normalization
- File format specifications

#### SYSTEM_OVERVIEW.md
**Purpose**: High-level architecture documentation  
**Audience**: Contributors, technical stakeholders  
**Content**:
- System components
- Data flow diagrams
- Technology stack
- Design decisions
- Extension points

#### TOOL_WRAPPERS_GUIDE.md
**Purpose**: Guide for wrapping WhiteMagic in other tools  
**Audience**: Integration developers  
**Content**:
- Python API reference
- MCP tool specifications
- REST API (Phase 2A)
- Example integrations
- Best practices

---

### docs/development/ (Development Plans)

#### PHASE_2A_PLAN.md
**Purpose**: Detailed plan for Whop integration & REST API  
**Audience**: Core contributors, project lead  
**Content**:
- Architecture design
- Database schema
- API specifications
- Implementation timeline
- Success criteria

#### REST_API_DESIGN.md
**Purpose**: REST API design document  
**Audience**: API developers, integrators  
**Content**:
- Endpoint specifications
- Authentication flow
- Request/response formats
- Error handling
- Rate limiting

#### BUGFIX_REPORT.md
**Purpose**: Historical record of bugs fixed in Phase 1B  
**Audience**: Contributors, QA  
**Content**:
- Critical bugs identified
- Root cause analysis
- Fixes implemented
- Verification results

---

### docs/archive/ (Historical Documents)

**Purpose**: Historical development documents preserved for reference  
**Audience**: Contributors researching project history  

**Contents**:
- Phase 1A completion reports
- Analysis documents from planning
- Design iterations
- Progress summaries
- Legacy release notes

**Note**: These are kept for historical reference but are not actively maintained.

---

## 🗺️ Documentation Roadmap

### Upcoming Documentation (Phase 2A)

- [ ] **API_REFERENCE.md** - Complete REST API documentation
- [ ] **CONTRIBUTING.md** - Contribution guidelines
- [ ] **SECURITY.md** - Security policy and vulnerability reporting
- [ ] **CHANGELOG.md** - Ongoing changelog (separate from release notes)
- [ ] **FAQ.md** - Frequently asked questions
- [ ] **DEPLOYMENT.md** - Production deployment guide

### Future Documentation (Phase 2B+)

- [ ] **SEMANTIC_SEARCH_GUIDE.md** - Using semantic search features
- [ ] **TEAM_USAGE.md** - Guide for team/organization usage
- [ ] **INTEGRATIONS.md** - Third-party integrations catalog
- [ ] **PERFORMANCE.md** - Performance tuning guide
- [ ] **MIGRATION.md** - Migration guides between versions

---

## 📝 Documentation Standards

### Writing Style
- **Clear and Concise**: Get to the point quickly
- **Code Examples**: Show, don't just tell
- **Practical Focus**: Real-world use cases
- **Progressive Disclosure**: Basic → Advanced
- **Consistent Formatting**: Follow templates

### File Naming
- `UPPERCASE.md` for root-level docs
- `lowercase_with_underscores.md` for guides
- Descriptive names (not `doc1.md`)

### Markdown Format
- Use `###` for sections (reserve `#` and `##` for title/major sections)
- Code blocks with language hints: ```python
- Tables for comparisons
- Emojis sparingly (guides/overviews only)

### Maintenance
- Update "Last Updated" dates when making changes
- Add version numbers to technical specs
- Archive outdated docs instead of deleting
- Link related documents

---

## 🔍 Finding What You Need

### I want to...

**...get started quickly**  
→ [README.md](README.md) → [QUICKSTART.md](docs/guides/QUICKSTART.md)

**...install WhiteMagic**  
→ [INSTALL.md](INSTALL.md)

**...use advanced features**  
→ [ADVANCED_USAGE.md](docs/guides/ADVANCED_USAGE.md)

**...integrate WhiteMagic into my app**  
→ [TOOL_WRAPPERS_GUIDE.md](docs/guides/TOOL_WRAPPERS_GUIDE.md)

**...understand the architecture**  
→ [SYSTEM_OVERVIEW.md](docs/guides/SYSTEM_OVERVIEW.md)

**...set up MCP in my IDE**  
→ [whitemagic-mcp/README.md](whitemagic-mcp/README.md)

**...contribute to development**  
→ [PHASE_2A_PLAN.md](docs/development/PHASE_2A_PLAN.md) (coming: CONTRIBUTING.md)

**...see what's coming next**  
→ [ROADMAP.md](ROADMAP.md)

**...report a bug**  
→ [GitHub Issues](https://github.com/lbailey94/whitemagic/issues) (coming: SECURITY.md)

**...understand past decisions**  
→ [docs/archive/](docs/archive/)

---

## 🤝 Contributing to Documentation

Documentation improvements are always welcome!

### How to Help
1. Fix typos or unclear explanations
2. Add missing examples
3. Improve diagrams and visualizations
4. Translate to other languages (future)
5. Fill gaps in coverage

### Submission Process
1. Fork the repository
2. Make your changes
3. Test code examples work
4. Submit a pull request
5. Respond to review feedback

---

## 📧 Questions?

- **GitHub Discussions**: https://github.com/lbailey94/whitemagic/discussions
- **Issues**: https://github.com/lbailey94/whitemagic/issues
- **Email**: support@whitemagic.dev (coming soon)

---

**Last Updated**: November 3, 2025  
**Version**: 2.1.2
