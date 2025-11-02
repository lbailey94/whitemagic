---
title: Example Short-Term Memory
created: 2025-10-23T16:50:00
tags: ["example", "template"]
---

## Context
This is an example short-term memory file. Short-term memories capture:
- Immediate context from current work
- Decisions made during a session
- Temporary insights that may need validation
- Work-in-progress discoveries

## Content
**Pattern Discovered**: When implementing authentication, starting with JWT tokens simplifies microservices architecture but requires careful secret management.

**Decision Made**: Chose JWT over session-based auth because:
1. Stateless nature fits microservices
2. Easier horizontal scaling
3. Better for mobile apps

**Open Questions**:
- How to handle token refresh elegantly?
- What's the optimal token expiration time?

## Next Steps
- Test implementation with production-like load
- If successful, promote pattern to long-term memory
- Document edge cases discovered
