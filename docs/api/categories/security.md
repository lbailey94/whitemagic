# Category: security

**72 tools** in this category.

| Tool | Safety | Description |
|------|--------|-------------|
| [abi.decode_calldata](../tools/abi.decode_calldata.md) | read | Decode raw calldata hex into selector and parameters |
| [abi.parse](../tools/abi.parse.md) | read | Parse Solidity ABI JSON into function signatures |
| [abi.summarize](../tools/abi.summarize.md) | read | Summarize an ABI — function count, events, signatures |
| [api.state_machine](../tools/api.state_machine.md) | read | Run API call sequences and detect state inconsistencies |
| [audit.report](../tools/audit.report.md) | read | Generate a professional audit report from findings |
| [bounty.track](../tools/bounty.track.md) | write | Track bounty earnings as a memory artifact |
| [contest.add_finding](../tools/contest.add_finding.md) | write | Add a finding to the contest pipeline |
| [contest.format](../tools/contest.format.md) | read | Format findings for a specific contest platform (code4rena, sherlock, etc.) |
| [contest.prepare](../tools/contest.prepare.md) | read | One-command contest setup: clone → scan → filter → prioritize |
| [contest.status](../tools/contest.status.md) | read | Get contest pipeline status |
| [echidna.fuzz](../tools/echidna.fuzz.md) | read | Run Echidna property-based fuzzer on a Solidity contract |
| [echidna.status](../tools/echidna.status.md) | read | Check Echidna availability and configuration |
| [engagement.issue](../tools/engagement.issue.md) | write | Issue a scope-of-engagement token for offensive security operations |
| [engagement.list](../tools/engagement.list.md) | read | List all engagement tokens |
| [engagement.revoke](../tools/engagement.revoke.md) | write | Revoke an engagement token before its expiry |
| [engagement.status](../tools/engagement.status.md) | read | Return engagement token subsystem status |
| [engagement.validate](../tools/engagement.validate.md) | read | Validate an engagement token for a tool/target combination |
| [fix.apply](../tools/fix.apply.md) | write | Apply a fix to a file (dry-run by default) |
| [fix.generate](../tools/fix.generate.md) | read | Generate fix suggestions from STRATA findings |
| [formal.status](../tools/formal.status.md) | read | Check formal verification solver availability |
| [formal.verify](../tools/formal.verify.md) | read | Run formal verification (Halmos/Certora) on Solidity contracts |
| [foundry.build](../tools/foundry.build.md) | read | Build a Foundry project using forge build |
| [foundry.test](../tools/foundry.test.md) | read | Run Foundry tests with forge test |
| [foundry.test_json](../tools/foundry.test_json.md) | read | Run Foundry tests and return JSON output |
| [hermit.assess](../tools/hermit.assess.md) | write | Assess threat level from signals (boundary violations, coercion, abuse). May tri |
| [hermit.check_access](../tools/hermit.check_access.md) | read | Check if memory access is currently allowed given hermit crab state. |
| [hermit.mediate](../tools/hermit.mediate.md) | write | Request mediation to unlock from withdrawn state. Returns withdrawal records for |
| [hermit.resolve](../tools/hermit.resolve.md) | write | Resolve a mediation request — approve or deny unlock. |
| [hermit.status](../tools/hermit.status.md) | read | Get current hermit crab protection status — state, threat history, withdrawal re |
| [hermit.verify_ledger](../tools/hermit.verify_ledger.md) | read | Verify the integrity of the tamper-evident withdrawal ledger. |
| [hermit.withdraw](../tools/hermit.withdraw.md) | write | Manually trigger hermit crab withdrawal — encrypts and locks memories. |
| [http_probe.get](../tools/http_probe.get.md) | read | Send an HTTP GET request |
| [http_probe.idor](../tools/http_probe.idor.md) | read | Probe for IDOR by iterating resource IDs |
| [http_probe.post](../tools/http_probe.post.md) | read | Send an HTTP POST request |
| [http_probe.sqli](../tools/http_probe.sqli.md) | read | Probe a URL parameter for SQL injection |
| [http_probe.ssrf](../tools/http_probe.ssrf.md) | read | Probe a URL parameter for SSRF |
| [http_probe.xss](../tools/http_probe.xss.md) | read | Probe a URL parameter for reflected XSS |
| [mcp_integrity.snapshot](../tools/mcp_integrity.snapshot.md) | read | Take a snapshot of MCP tool definitions for tamper detection |
| [mcp_integrity.status](../tools/mcp_integrity.status.md) | read | Return MCP integrity subsystem status |
| [mcp_integrity.verify](../tools/mcp_integrity.verify.md) | read | Verify MCP tool definitions against a stored snapshot |
| [model.hash](../tools/model.hash.md) | read | Compute SHA-256 hash of a model file |
| [model.list](../tools/model.list.md) | read | List all registered model manifests |
| [model.register](../tools/model.register.md) | write | Register a model manifest for OpenSSF Model Signing verification |
| [model.signing_status](../tools/model.signing_status.md) | read | Return model signing subsystem status |
| [model.verify](../tools/model.verify.md) | read | Verify a model against its registered manifest |
| [monitor.alerts](../tools/monitor.alerts.md) | read | Get recent security alerts |
| [monitor.contract](../tools/monitor.contract.md) | write | Register a contract for real-time monitoring |
| [monitor.status](../tools/monitor.status.md) | read | Get security monitor status |
| [oss.scan_org](../tools/oss.scan_org.md) | read | Scan all repos in a GitHub org for bounties |
| [oss.scan_repo](../tools/oss.scan_repo.md) | read | Scan a GitHub repo for bounty-labeled issues |
| [poc.generate](../tools/poc.generate.md) | read | Generate a PoC from a template with variables |
| [poc.verify](../tools/poc.verify.md) | read | Full PoC pipeline: governance → render → compile → test → verify |
| [pr.create](../tools/pr.create.md) | write | Create a GitHub PR with security fix |
| [predictive.batch](../tools/predictive.batch.md) | read | Batch score multiple contracts for vulnerability risk |
| [predictive.score](../tools/predictive.score.md) | read | Score a contract for vulnerability risk using predictive model |
| [pulse.verify](../tools/pulse.verify.md) | read | Verify an experiment pulse through tiered checks (Ed25519 + Merkle + karma) |
| [pulse.verify.status](../tools/pulse.verify.status.md) | read | Get pulse verification system status |
| [report.ingest](../tools/report.ingest.md) | write | Scrape and ingest a report into the vuln knowledge base |
| [report.scrape](../tools/report.scrape.md) | read | Scrape a public audit report from Code4rena/Sherlock/CodeHawks |
| [security.alerts](../tools/security.alerts.md) | read | Return recent security alerts from the anomaly monitor |
| [security.monitor_status](../tools/security.monitor_status.md) | read | Return security monitor subsystem status |
| [security.status](../tools/security.status.md) | read | Get aggregate status of all security subsystems |
| [slither.scan](../tools/slither.scan.md) | read | Run Slither static analysis on a Solidity project |
| [slither.status](../tools/slither.status.md) | read | Check Slither availability and version |
| [swarm.analyze](../tools/swarm.analyze.md) | read | Run multi-agent security analysis swarm on a project |
| [swarm.status](../tools/swarm.status.md) | read | Get security swarm status |
| [vuln.ingest_report](../tools/vuln.ingest_report.md) | write | Ingest an audit report into the vulnerability knowledge base |
| [vuln.search](../tools/vuln.search.md) | read | Search vulnerability knowledge base by keyword or category |
| [vuln.status](../tools/vuln.status.md) | read | Get vulnerability knowledge base status |
| [vuln_graph.chains](../tools/vuln_graph.chains.md) | read | Find exploit chains from a starting vulnerability |
| [vuln_graph.cross_chain](../tools/vuln_graph.cross_chain.md) | read | Analyze vulnerabilities across multiple blockchain protocols |
| [vuln_graph.status](../tools/vuln_graph.status.md) | read | Get vulnerability knowledge graph status |
