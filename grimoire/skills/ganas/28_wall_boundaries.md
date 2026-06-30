---
name: wm-marketplace
description: "Marketplace, voting, engagement tokens, and community governance"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_wall
    tools: [vote_create, vote_cast, vote_analyze, vote_list, vote_record_outcome, engagement_issue, engagement_list, engagement_revoke, engagement_status, engagement_validate, marketplace_publish, marketplace_discover, marketplace_negotiate, marketplace_complete]
    tags: [marketplace, voting, engagement, tokens, governance, boundaries, publish, discover]
---

# Boundaries & Marketplace

Create and vote on proposals, manage engagement tokens, and participate in the marketplace for agent-to-agent commerce.

## When to Use

- Creating a vote or proposal
- Casting votes on proposals
- Analyzing vote outcomes
- Issuing engagement tokens for contributions
- Publishing services to the marketplace
- Discovering and negotiating services
- Completing marketplace transactions

## How to Invoke

```python
# Create a vote
wm(route="gana_wall.vote_create", args={"question": "...", "options": [...]})

# Cast a vote
wm(route="gana_wall.vote_cast", args={"vote_id": "...", "choice": "..."})

# Analyze votes
wm(route="gana_wall.vote_analyze", args={"vote_id": "..."})

# Issue engagement tokens
wm(route="gana_wall.engagement_issue", args={"recipient": "...", "amount": 10})

# Publish to marketplace
wm(route="gana_wall.marketplace_publish", args={"service": "...", "terms": {...}})

# Discover services
wm(route="gana_wall.marketplace_discover", args={"query": "..."})

# Negotiate
wm(route="gana_wall.marketplace_negotiate", args={"listing_id": "...", "terms": {...}})
```
