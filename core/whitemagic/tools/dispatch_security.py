"""dispatch_security.py — Security, sandbox, governance, and verification tools.

Domain slice imported by dispatch_table.py.
"""

from collections.abc import Callable
from typing import Any

from whitemagic.tools.dispatch_core import LazyHandler, LazyHandlerAbs

DISPATCH_SECURITY: dict[str, Callable[..., dict[str, Any]]] = {
    "sandbox.status": LazyHandler("sandbox", "handle_sandbox_status"),
    "sandbox.violations": LazyHandler("sandbox", "handle_sandbox_violations"),
    "sandbox.set_limits": LazyHandler("sandbox", "handle_sandbox_set_limits"),
    "shelter.create": LazyHandler("shelter", "handle_shelter_create"),
    "shelter.execute": LazyHandler("shelter", "handle_shelter_execute"),
    "shelter.inspect": LazyHandler("shelter", "handle_shelter_inspect"),
    "shelter.destroy": LazyHandler("shelter", "handle_shelter_destroy"),
    "shelter.status": LazyHandler("shelter", "handle_shelter_status"),
    "shelter.policy": LazyHandler("shelter", "handle_shelter_policy"),
    "governor_validate": LazyHandler("governor", "handle_governor_validate"),
    "governor_validate_path": LazyHandler("governor", "handle_governor_validate_path"),
    "governor_set_goal": LazyHandler("governor", "handle_governor_set_goal"),
    "governor_check_drift": LazyHandler("governor", "handle_governor_check_drift"),
    "governor_check_budget": LazyHandler("governor", "handle_governor_check_budget"),
    "governor_check_dharma": LazyHandler("governor", "handle_governor_check_dharma"),
    "governor_stats": LazyHandler("governor", "handle_governor_stats"),
    "evaluate_ethics": LazyHandler("dharma", "handle_evaluate_ethics"),
    "check_boundaries": LazyHandler("dharma", "handle_check_boundaries"),
    "verify_consent": LazyHandler("dharma", "handle_verify_consent"),
    "get_ethical_score": LazyHandler("dharma", "handle_get_ethical_score"),
    "get_dharma_guidance": LazyHandler("dharma", "handle_get_dharma_guidance"),
    "karma_report": LazyHandler("dharma", "handle_karma_report"),
    "karma_record": LazyHandler("dharma", "handle_karma_record"),
    "karmic_trace": LazyHandler("dharma", "handle_karmic_trace"),
    "karma.verify_chain": LazyHandler("dharma", "handle_karma_verify_chain"),
    "karma.anchor": LazyHandler("dharma", "handle_karma_anchor"),
    "karma.verify_anchor": LazyHandler("dharma", "handle_karma_verify_anchor"),
    "karma.anchor_status": LazyHandler("dharma", "handle_karma_anchor_status"),
    "dharma_rules": LazyHandler("dharma", "handle_dharma_rules"),
    "set_dharma_profile": LazyHandler("dharma", "handle_set_dharma_profile"),
    "dharma.escalate": LazyHandler("dharma", "handle_dharma_escalate"),
    "dharma.review_queue": LazyHandler("dharma", "handle_dharma_review_queue"),
    "dharma.resolve_review": LazyHandler("dharma", "handle_dharma_resolve_review"),
    "dharma.reload": LazyHandler("governance", "handle_dharma_reload"),
    "mcp_integrity.snapshot": LazyHandler(
        "violet_security", "handle_mcp_integrity_snapshot"
    ),
    "mcp_integrity.verify": LazyHandler(
        "violet_security", "handle_mcp_integrity_verify"
    ),
    "mcp_integrity.status": LazyHandler(
        "violet_security", "handle_mcp_integrity_status"
    ),
    "model.register": LazyHandler("violet_security", "handle_model_register"),
    "model.verify": LazyHandler("violet_security", "handle_model_verify"),
    "model.list": LazyHandler("violet_security", "handle_model_list"),
    "model.hash": LazyHandler("violet_security", "handle_model_hash"),
    "model.signing_status": LazyHandler(
        "violet_security", "handle_model_signing_status"
    ),
    "engagement.issue": LazyHandler("violet_security", "handle_engagement_issue"),
    "engagement.validate": LazyHandler("violet_security", "handle_engagement_validate"),
    "engagement.revoke": LazyHandler("violet_security", "handle_engagement_revoke"),
    "engagement.list": LazyHandler("violet_security", "handle_engagement_list"),
    "engagement.status": LazyHandler("violet_security", "handle_engagement_status"),
    "security.alerts": LazyHandler("violet_security", "handle_security_alerts"),
    "security.monitor_status": LazyHandler(
        "violet_security", "handle_security_monitor_status"
    ),
    "verification.request": LazyHandler("verification", "handle_verification_request"),
    "verification.attest": LazyHandler("verification", "handle_verification_attest"),
    "verification.status": LazyHandler("verification", "handle_verification_status"),
    "homeostasis": LazyHandler("governance", "handle_homeostasis"),
    "homeostasis.status": LazyHandler("governance", "handle_homeostasis_status"),
    "homeostasis.check": LazyHandler("governance", "handle_homeostasis_check"),
    "maturity.assess": LazyHandler("governance", "handle_maturity_assess"),
    "tool.graph": LazyHandler("governance", "handle_tool_graph"),
    "tool.graph_full": LazyHandler("governance", "handle_tool_graph_full"),
    "anomaly": LazyHandler("anomaly", "handle_anomaly"),
    "anomaly.check": LazyHandler("anomaly", "handle_anomaly_check"),
    "anomaly.history": LazyHandler("anomaly", "handle_anomaly_history"),
    "anomaly.status": LazyHandler("anomaly", "handle_anomaly_status"),
    "watcher_add": LazyHandler("watcher", "handle_watcher_add"),
    "watcher_remove": LazyHandler("watcher", "handle_watcher_remove"),
    "watcher_start": LazyHandler("watcher", "handle_watcher_start"),
    "watcher_stop": LazyHandler("watcher", "handle_watcher_stop"),
    "watcher_status": LazyHandler("watcher", "handle_watcher_status"),
    "watcher_recent_events": LazyHandler("watcher", "handle_watcher_recent_events"),
    "watcher_stats": LazyHandler("watcher", "handle_watcher_stats"),
    "watcher_list": LazyHandler("watcher", "handle_watcher_list"),
    "forge.status": LazyHandlerAbs(
        "whitemagic.tools.gana_forge", "handle_forge_status"
    ),
    "forge.reload": LazyHandlerAbs(
        "whitemagic.tools.gana_forge", "handle_forge_reload"
    ),
    "forge.validate": LazyHandlerAbs(
        "whitemagic.tools.gana_forge", "handle_forge_validate"
    ),
    # ── Security Bounty Tools (v24.1) ──
    "foundry.build": LazyHandler("security_tools", "handle_foundry_build"),
    "foundry.test": LazyHandler("security_tools", "handle_foundry_test"),
    "foundry.test_json": LazyHandler("security_tools", "handle_foundry_test_json"),
    "abi.parse": LazyHandler("security_tools", "handle_abi_parse"),
    "abi.summarize": LazyHandler("security_tools", "handle_abi_summarize"),
    "abi.decode_calldata": LazyHandler("security_tools", "handle_abi_decode_calldata"),
    "vuln.search": LazyHandler("security_tools", "handle_vuln_search"),
    "vuln.status": LazyHandler("security_tools", "handle_vuln_status"),
    "vuln.ingest_report": LazyHandler("security_tools", "handle_vuln_ingest_report"),
    "contest.add_finding": LazyHandler("security_tools", "handle_contest_add_finding"),
    "contest.format": LazyHandler("security_tools", "handle_contest_format"),
    "contest.status": LazyHandler("security_tools", "handle_contest_status"),
    "oss.scan_repo": LazyHandler("security_tools", "handle_oss_scan_repo"),
    "oss.scan_org": LazyHandler("security_tools", "handle_oss_scan_org"),
    "security.status": LazyHandler("security_tools", "handle_security_status"),
    # PoC Pipeline
    "poc.generate": LazyHandler("security_tools", "handle_poc_generate"),
    "poc.verify": LazyHandler("security_tools", "handle_poc_verify"),
    "contest.prepare": LazyHandler("security_tools", "handle_contest_prepare"),
    # HTTP Probe
    "http_probe.get": LazyHandler("security_tools", "handle_http_probe_get"),
    "http_probe.post": LazyHandler("security_tools", "handle_http_probe_post"),
    "http_probe.xss": LazyHandler("security_tools", "handle_http_probe_xss"),
    "http_probe.sqli": LazyHandler("security_tools", "handle_http_probe_sqli"),
    "http_probe.idor": LazyHandler("security_tools", "handle_http_probe_idor"),
    "http_probe.ssrf": LazyHandler("security_tools", "handle_http_probe_ssrf"),
    "api.state_machine": LazyHandler("security_tools", "handle_api_state_machine"),
    # Echidna
    "echidna.fuzz": LazyHandler("security_tools", "handle_echidna_fuzz"),
    "echidna.status": LazyHandler("security_tools", "handle_echidna_status"),
    # Fix Generator
    "fix.generate": LazyHandler("security_tools", "handle_fix_generate"),
    "fix.apply": LazyHandler("security_tools", "handle_fix_apply"),
    "pr.create": LazyHandler("security_tools", "handle_pr_create"),
    "bounty.track": LazyHandler("security_tools", "handle_bounty_track"),
    # Report Scraper
    "report.scrape": LazyHandler("security_tools", "handle_report_scrape"),
    "report.ingest": LazyHandler("security_tools", "handle_report_ingest"),
    # Phase 7: Advanced Tools
    "vuln_graph.status": LazyHandler("security_tools", "handle_vuln_graph_status"),
    "vuln_graph.chains": LazyHandler("security_tools", "handle_vuln_graph_chains"),
    "vuln_graph.cross_chain": LazyHandler("security_tools", "handle_vuln_graph_cross_chain"),
    "formal.verify": LazyHandler("security_tools", "handle_formal_verify"),
    "formal.status": LazyHandler("security_tools", "handle_formal_verify_status"),
    "swarm.analyze": LazyHandler("security_tools", "handle_swarm_analyze"),
    "swarm.status": LazyHandler("security_tools", "handle_swarm_status"),
    "predictive.score": LazyHandler("security_tools", "handle_predictive_score"),
    "predictive.batch": LazyHandler("security_tools", "handle_predictive_batch"),
    "audit.report": LazyHandler("security_tools", "handle_audit_report"),
    "monitor.status": LazyHandler("security_tools", "handle_monitor_status"),
    "monitor.alerts": LazyHandler("security_tools", "handle_monitor_alerts"),
    "monitor.contract": LazyHandler("security_tools", "handle_monitor_contract"),
    # Slither Integration
    "slither.scan": LazyHandler("security_tools", "handle_slither_scan"),
    "slither.status": LazyHandler("security_tools", "handle_slither_status"),
}
