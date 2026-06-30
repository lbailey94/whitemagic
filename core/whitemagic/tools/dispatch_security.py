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
}
