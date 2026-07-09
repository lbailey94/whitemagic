# Bounty Targeting Strategy — 2026

**Created**: 2026-07-08
**Status**: Active
**Purpose**: Prioritize live bounty targets for WhiteMagic's security tooling

---

## 1. Target Selection Framework

### Scoring Criteria
Each target is scored on:
- **Payout ceiling** (40%) — max possible reward per critical finding
- **Attack surface** (25%) — codebase complexity, scope size, contract types
- **Competition density** (15%) — fewer participants = higher per-researcher EV
- **Tooling fit** (10%) — how well WhiteMagic's checkers match the likely vuln classes
- **Time window** (10%) — remaining time for contests, or ongoing for bounties

### Tier System
- **Tier 1 (Primary)**: High payout + good tooling fit + active now
- **Tier 2 (Secondary)**: Medium payout or narrower scope
- **Tier 3 (Watchlist)**: Upcoming contests, monitor for launch

---

## 2. Active Targets — July 2026

### Tier 1: Primary Targets

#### Immunefi Ongoing Bounties

| Protocol | Max Bounty | Total Paid | Tooling Fit | Notes |
|----------|-----------|------------|-------------|-------|
| Ethena | $3M | $12.4K | High — DeFi, synthetic assets | Low total paid suggests unexplored surface |
| DeXe Protocol | $500K | $219.3K | High — governance, staking | Complex delegate system, reentrancy surface |
| SSV Network | $250K | $310.4K | Medium — validator infrastructure | Distributed validator tech, novel architecture |
| Lombard Finance | $250K | $40K | High — BTC bridge, liquid staking | Bridge contracts = high-value attack surface |
| Lido V3 | $2M | — | High — liquid staking | Bug bounty competition with $200K bonus pool |
| Aave V4 (Sherlock) | $2.5M | — | High — lending protocol | Largest Sherlock bounty, complex rate strategies |

#### Sherlock Active Contests

| Contest | Pool | Status | Tooling Fit |
|---------|------|--------|-------------|
| Convergence | $50K | Active | Medium — DeFi incentives |
| M^0 | $88K | Active | High — stablecoin infrastructure |

### Tier 2: Secondary Targets

#### Immunefi — Medium Payout, Good Fit

| Protocol | Max Bounty | Tooling Fit | Notes |
|----------|-----------|-------------|-------|
| The Graph | $1.5M | Medium — indexing, staking | Time-boxed (1 day response) |
| Alchemix | $300K | High — yield aggregator | Alchemix v2, complex self-repaying loans |
| Paradex | $500K | High — DEX, order matching | Order matching = manipulation surface |
| StackingDAO | $100K | High — liquid staking | Stacking contracts, STX chain |
| Zest Protocol V2 | $100K | High — Bitcoin lending | Recently launched, less audited |

#### Code4rena — Monitor for New Contests

Code4rena runs 3-14 day contests with $50K-$500K pools. Check [code4rena.com/audits](https://code4rena.com/audits) weekly for new launches. Typical cadence: 2-4 contests per month.

### Tier 3: Watchlist

| Platform | Target | Trigger |
|----------|--------|---------|
| Sherlock | New contest announcements | Sherlock Discord / audits.sherlock.xyz |
| Code4rena | New audit launches | code4rena.com/audits page |
| CodeHawks | First Flights (beginner-friendly) | codehawks.cyfrin.io — good for testing pipeline |
| Cantina | Mega-comps ($200K-$2M) | cantina.xyz — experienced researcher focus |

---

## 3. WhiteMagic Tooling Alignment

### By Vulnerability Class

| Vuln Class | WhiteMagic Tools | Target Protocols |
|------------|-----------------|------------------|
| Reentrancy | STRATA checker, PoC template, memory checker | DeXe, Lombard, Aave V4 |
| Access control | STRATA checker, PoC template | SSV, Lido, StackingDAO |
| Integer overflow | STRATA checker, PoC template | Pre-0.8.0 contracts |
| Oracle manipulation | STRATA checker | Ethena, Aave V4 |
| Bridge vulnerabilities | Cross-chain graph, formal verifier | Lombard, Zest Protocol |
| Governance attacks | STRATA checker, vuln graph | DeXe, Lido |
| Liquid staking | STRATA + Slither + Echidna | Lido, StackingDAO, SSV |
| DEX manipulation | Predictive scoring, Echidna | Paradex, Convergence |

### Workflow per Target

1. **Recon** (30 min): Clone repo, run `foundry build`, run Slither triage
2. **Automated scan** (15 min): STRATA checkers + Slither integration + memory-augmented checker
3. **Predictive scoring** (10 min): Score each contract for risk, prioritize high-risk files
4. **Manual review** (2-4 hours): Focus on high-risk contracts, use PoC templates for verification
5. **Multi-agent swarm** (30 min): Deploy swarm for consensus findings
6. **Report generation** (15 min): Generate audit report, format for target platform
7. **Submission**: Use contest pipeline for C4/Sherlock/CodeHawks, or direct submission for Immunefi

---

## 4. Revenue Projections (Updated)

### Q3 2026 (Jul-Sep)

| Scenario | Source | Expected |
|----------|--------|----------|
| Conservative | 1 medium on Immunefi | $1K-$5K |
| Moderate | 1 high on Immunefi + 1 medium on C4 | $10K-$30K |
| Stretch | 1 critical on Immunefi | $50K-$250K |

### Q4 2026 (Oct-Dec)

| Scenario | Source | Expected |
|----------|--------|----------|
| Conservative | 2-3 mediums across platforms | $5K-$15K |
| Moderate | 1 high + 2-3 mediums | $20K-$60K |
| Stretch | 1 critical + 1 high | $100K-$500K |

### Year 1 Total (Jul 2026 - Jul 2027)

| Scenario | Range |
|----------|-------|
| Conservative | $3.5K-$17.5K |
| Moderate | $12.5K-$52K |
| Stretch | $37K-$170K+ |

---

## 5. Execution Schedule

### Week 1-2 (Jul 8-22): Pipeline Validation
- [ ] Select 1 Immunefi target (recommend Lombard Finance — good fit, $250K ceiling)
- [ ] Run full WhiteMagic pipeline end-to-end
- [ ] Submit at least 1 finding (even low/info for pipeline validation)
- [ ] Measure time spent per finding

### Week 3-4 (Jul 22-Aug 5): First Real Submission
- [ ] Enter next Code4rena or Sherlock contest
- [ ] Use multi-agent swarm for coverage
- [ ] Generate formal audit report
- [ ] Track time-to-submission and finding quality

### Week 5-8 (Aug 5-Sep 2): Scale Up
- [ ] Run 2-3 parallel targets (1 contest + 1 Immunefi ongoing)
- [ ] Use predictive scoring to prioritize
- [ ] Cross-reference with vuln knowledge graph
- [ ] First Echidna fuzzing campaign on high-risk target

### Week 9-12 (Sep 2-Sep 30): Optimize
- [ ] Analyze submission success rate
- [ ] Tune STRATA checkers based on missed findings
- [ ] Expand PoC template library based on real findings
- [ ] Ingest own findings into vuln knowledge base

---

## 6. Key Metrics to Track

| Metric | Target | Current |
|--------|--------|---------|
| Targets scanned | 10+ per month | 0 |
| Findings submitted | 5+ per month | 0 |
| Findings accepted | 30%+ acceptance rate | 0% |
| Time per finding | <4 hours avg | TBD |
| Critical findings | 1+ per quarter | 0 |
| Revenue | Track per-finding ROI | $0 |
| Pipeline uptime | 100% (all tools functional) | 100% |

---

## 7. Risk Management

- **Duplicate findings**: Contest pipelines deduplicate; for Immunefi, speed matters — submit early
- **Invalid findings**: Use PoC verification pipeline before submission; run Echidna for confirmation
- **Scope violations**: Always verify scope before submitting; check Immunefi/Sherlock scope docs
- **Reputation**: Start with smaller contests to build track record before targeting mega-comps
- **Tooling gaps**: If a finding class isn't covered by WhiteMagic, add a checker or PoC template

---

## 8. Platform Account Setup

| Platform | Status | Handle | Notes |
|----------|--------|--------|-------|
| Immunefi | TODO | — | Register at immunefi.com |
| Code4rena | TODO | — | Register at code4rena.com |
| Sherlock | TODO | — | Register at audits.sherlock.xyz, join Discord |
| CodeHawks | TODO | — | Register at codehawks.cyfrin.io |
| Cantina | TODO | — | Register at cantina.xyz |
| HackerOne | TODO | — | For traditional web vuln targets |
| Bugcrowd | TODO | — | For traditional web vuln targets |

---

*This document is updated as targets are pursued and findings are submitted.*
