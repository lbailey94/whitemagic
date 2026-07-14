# Gana: gana_room

**25 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [anti_loop_check](../tools/anti_loop_check.md) | system | read | Dispatch-routable WhiteMagic tool 'anti_loop_check'. |
| [hermit.assess](../tools/hermit.assess.md) | security | write | Assess threat level from signals (boundary violations, coercion, abuse). May tri |
| [hermit.check_access](../tools/hermit.check_access.md) | security | read | Check if memory access is currently allowed given hermit crab state. |
| [hermit.mediate](../tools/hermit.mediate.md) | security | write | Request mediation to unlock from withdrawn state. Returns withdrawal records for |
| [hermit.resolve](../tools/hermit.resolve.md) | security | write | Resolve a mediation request — approve or deny unlock. |
| [hermit.status](../tools/hermit.status.md) | security | read | Get current hermit crab protection status — state, threat history, withdrawal re |
| [hermit.verify_ledger](../tools/hermit.verify_ledger.md) | security | read | Verify the integrity of the tamper-evident withdrawal ledger. |
| [hermit.withdraw](../tools/hermit.withdraw.md) | security | write | Manually trigger hermit crab withdrawal — encrypts and locks memories. |
| [immune_heal](../tools/immune_heal.md) | system | read | Dispatch-routable WhiteMagic tool 'immune_heal'. |
| [immune_scan](../tools/immune_scan.md) | system | read | Dispatch-routable WhiteMagic tool 'immune_scan'. |
| [mcp_integrity.snapshot](../tools/mcp_integrity.snapshot.md) | security | read | Take a snapshot of MCP tool definitions for tamper detection |
| [mcp_integrity.status](../tools/mcp_integrity.status.md) | security | read | Return MCP integrity subsystem status |
| [mcp_integrity.verify](../tools/mcp_integrity.verify.md) | security | read | Verify MCP tool definitions against a stored snapshot |
| [sandbox.set_limits](../tools/sandbox.set_limits.md) | governor | write | Set custom resource limits for a specific tool (timeout, memory, CPU) |
| [sandbox.status](../tools/sandbox.status.md) | introspection | read | Get sandbox status — per-tool execution stats, enabled state, resource module av |
| [sandbox.violations](../tools/sandbox.violations.md) | introspection | read | Get recent sandbox limit violations (timeout, memory, CPU) |
| [sangha_lock](../tools/sangha_lock.md) | system | write | Unified resource lock management for multi-agent coordination. Actions: acquire  |
| [sangha_lock_acquire](../tools/sangha_lock_acquire.md) | system | read | Dispatch-routable WhiteMagic tool 'sangha_lock_acquire'. |
| [sangha_lock_list](../tools/sangha_lock_list.md) | system | read | Dispatch-routable WhiteMagic tool 'sangha_lock_list'. |
| [sangha_lock_release](../tools/sangha_lock_release.md) | system | read | Dispatch-routable WhiteMagic tool 'sangha_lock_release'. |
| [security.alerts](../tools/security.alerts.md) | security | read | Return recent security alerts from the anomaly monitor |
| [security.monitor_status](../tools/security.monitor_status.md) | security | read | Return security monitor subsystem status |
| [tx_firewall.set_policy](../tools/tx_firewall.set_policy.md) | system | read | Dispatch-routable WhiteMagic tool 'tx_firewall.set_policy'. |
| [tx_firewall.status](../tools/tx_firewall.status.md) | system | read | Dispatch-routable WhiteMagic tool 'tx_firewall.status'. |
| [wasm_verify.status](../tools/wasm_verify.status.md) | system | read | Dispatch-routable WhiteMagic tool 'wasm_verify.status'. |
