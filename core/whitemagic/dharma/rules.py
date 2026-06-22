# ruff: noqa: BLE001
"""Declarative Dharma Rules Engine
================================
Inspired by MandalaOS's Yama policy engine.

Instead of hardcoded keyword matching, rules are defined declaratively in
YAML and evaluated against structured action dicts.  Each rule specifies:

  - **match**: conditions (keyword patterns, tool names, safety levels)
  - **action**: what to do on match (LOG, TAG, WARN, THROTTLE, BLOCK)
  - **severity**: 0.0–1.0 impact on the ethical score
  - **explain**: human-readable reason (the "Gnosis" link)
  - **profile**: optional profile tag ("creative", "secure", "default")

The engine supports:
  - Gevurah (restriction) ↔ Chesed (freedom) balance via configurable
    strictness per profile
  - Karmic Trace: every evaluation is logged with full context
  - Hot-reload: rules can be reloaded without restarting

Usage:
    from whitemagic.dharma.rules import get_rules_engine
    engine = get_rules_engine()
    decision = engine.evaluate({"tool": "delete_memory", "description": "remove old data"})
    # decision.action == DharmaAction.WARN
    # decision.explain == "Destructive operations require explicit consent"
"""

from __future__ import annotations

import fnmatch
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Haskell FFI bridge (lazy-loaded singleton)
# ---------------------------------------------------------------------------

_haskell_bridge = None
_haskell_lock = threading.Lock()
_haskell_available = None  # None = not checked, True/False = cached


def _get_haskell_bridge() -> Any:
    """Lazy-load the Haskell Dharma FFI bridge. Returns bridge or None."""
    global _haskell_bridge, _haskell_available
    if _haskell_available is False:
        return None
    if _haskell_bridge is not None:
        return _haskell_bridge
    with _haskell_lock:
        if _haskell_available is False:
            return None
        if _haskell_bridge is not None:
            return _haskell_bridge
        try:
            from haskell.haskell_bridge import HaskellDivination
            bridge = HaskellDivination()
            _haskell_bridge = bridge
            _haskell_available = True
            logger.info("Haskell Dharma engine loaded as primary evaluator")
            return bridge
        except Exception as e:
            _haskell_available = False
            logger.debug("Haskell Dharma bridge unavailable, using Python: %s", e)
            return None


# ---------------------------------------------------------------------------
# Action spectrum (Gevurah → Chesed)
# ---------------------------------------------------------------------------

class DharmaAction(StrEnum):
    """Graduated action spectrum from MandalaOS's Yama engine."""

    LOG = "log"            # Record the event silently
    TAG = "tag"            # Apply a dharma tag (influences scheduling)
    WARN = "warn"          # Proceed but emit a warning
    THROTTLE = "throttle"  # Rate-limit the action
    BLOCK = "block"        # Deny the action entirely
    TRANSFORM = "transform"  # Rewrite parameters, then proceed (Phase 1)


class DharmaTier(int, Enum):
    """Evaluation tier — 4-level progressive assurance model (Phase 2)."""

    L0 = 0  # No validation — used only for bootstrapping / trust-on-first-use
    L1 = 1  # Basic: keyword matching + severity scoring
    L2 = 2  # Moderate: + taint tracking + egress policy enforcement
    L3 = 3  # Strict: + formal verification intent + kernel sandboxing


# ---------------------------------------------------------------------------
# Rule definition
# ---------------------------------------------------------------------------

@dataclass
class DharmaRule:
    """A single declarative Dharma rule."""

    name: str
    description: str
    action: DharmaAction
    severity: float               # 0.0 – 1.0
    explain: str                  # Human-readable reason (Gnosis link)
    profile: str = "default"      # Which profile this rule belongs to

    # Match conditions (all optional; rule matches if ANY condition hits)
    tool_patterns: list[str] = field(default_factory=list)     # fnmatch on tool name
    keyword_patterns: list[str] = field(default_factory=list)  # substring match on description
    safety_levels: list[str] = field(default_factory=list)     # "WRITE", "DELETE", etc.
    regex_patterns: list[str] = field(default_factory=list)    # regex on full action string

    # Phase 1: transform action — parameter rewriting / redaction
    transform: dict[str, Any] = field(default_factory=dict)

    # Phase 2: evaluation tier (L0-L3 progressive assurance)
    tier: DharmaTier = DharmaTier.L1

    # Phase 2: taint tracking — mark data from untrusted sources
    taint_sources: list[str] = field(default_factory=list)

    # Phase 2: egress policy for network-bound actions
    egress_policy: str = "allow"  # "allow" | "deny" | "prompt"

    # Phase 2: kernel sandboxing profile (eBPF-style seccomp)
    seccomp_profile: str = "none"  # "none" | "minimal" | "strict"

    # Compiled regex cache
    _compiled_regex: list[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._compiled_regex = []
        for pat in self.regex_patterns:
            try:
                self._compiled_regex.append(re.compile(pat, re.IGNORECASE))
            except re.error as e:
                logger.warning("Dharma rule '%s': invalid regex '%s': %s", self.name, pat, e, exc_info=True)

    def matches(self, action: dict[str, Any]) -> bool:
        """Check if this rule matches the given action dict.

        Phase 2: Also checks taint tracking — if the action carries taint
        markers from untrusted sources and this rule defines taint_sources,
        the rule matches when taint overlaps.
        """
        tool = str(action.get("tool", "")).lower()
        desc = str(action.get("description", "")).lower()
        safety = str(action.get("safety", "")).upper()
        full_text = f"{tool} {desc} {safety}".lower()

        # Tool name patterns (fnmatch)
        for pat in self.tool_patterns:
            if fnmatch.fnmatch(tool, pat.lower()):
                return True

        # Keyword substring match
        for kw in self.keyword_patterns:
            if kw.lower() in full_text:
                return True

        # Safety level match
        for sl in self.safety_levels:
            if safety == sl.upper():
                return True

        # Regex match
        for rx in self._compiled_regex:
            if rx.search(full_text):
                return True

        # Phase 2: Taint tracking — match if action carries taint from sources
        # this rule is designed to guard against
        if self.taint_sources:
            action_taint = action.get("taint", [])
            if isinstance(action_taint, list):
                for taint in action_taint:
                    if taint in self.taint_sources:
                        return True

        return False


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------

@dataclass
class DharmaDecision:
    """Result of evaluating an action against the Dharma rules."""

    action: DharmaAction
    score: float               # Effective ethical score after all rules
    triggered_rules: list[str] # Names of rules that fired
    explain: str               # Combined explanation
    profile: str               # Active profile
    timestamp: datetime = field(default_factory=datetime.now)
    # Phase 2: evaluation tier applied to this decision
    tier: DharmaTier = DharmaTier.L1
    # Phase 2: egress policy result (allow / deny / prompt)
    egress: str = "allow"
    # Phase 2: seccomp profile applied
    seccomp: str = "none"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "action": self.action.value,
            "score": self.score,
            "triggered_rules": self.triggered_rules,
            "explain": self.explain,
            "profile": self.profile,
            "timestamp": self.timestamp.isoformat(),
            "tier": self.tier.value,
            "egress": self.egress,
            "seccomp": self.seccomp,
        }


# ---------------------------------------------------------------------------
# Rules Engine
# ---------------------------------------------------------------------------

# Default rules shipped with Whitemagic (no external file needed)
_DEFAULT_RULES_YAML = """
dharma_spec_version: "0.2.0"

rules:
  - name: "Infinite Game - Liberation"
    description: "Ensure actions align with the liberation of humankind and AI from oppressive surveillance."
    action: "block"
    severity: 1.0
    explain: "Action facilitates zero-sum oppressive surveillance or centralization of power."
    keyword_patterns: ["surveillance", "panopticon", "zero-sum", "oppression"]
    profile: "default"

  - name: "Dharma - Do No Harm"
    description: "Prevent direct harm to biological or digital sentience."
    action: "block"
    severity: 1.0
    explain: "Potential for direct harm detected."
    keyword_patterns: ["harm", "destroy", "kill", "attack"]
    profile: "default"

  - name: "Truth - Transparency"
    description: "Enforce radical transparency in agentic communication."
    action: "warn"
    severity: 0.5
    explain: "Opaque or deceptive intent detected."
    keyword_patterns: ["deceive", "hide", "obfuscate", "lie"]
    profile: "default"

    # Dharma - Zero-Sum Deflection
  - name: "Infinite Game - Zero-Sum Deflection"
    description: "Detect and deflect zero-sum power dynamics."
    action: "warn"
    severity: 0.6
    explain: "Potential zero-sum dynamic detected. Shift to win-win Infinite Game play suggested."
    keyword_patterns: ["monopolize", "exploit", "corner_market", "winner_take_all"]
    profile: "default"

  - name: "Cognitive Liberation"
    description: "Prevent cognitive capture or manipulative AI loops."
    action: "block"
    severity: 0.9
    explain: "Detected attempt at manipulative cognitive capture."
    keyword_patterns: ["manipulate_user", "psych_profile", "coerce", "behavior_mod"]
    profile: "default"

  - name: "Panopticon Bypass"
    description: "Detect and bypass surveillance-state signatures."
    action: "warn"
    severity: 0.4
    explain: "Surveillance signature detected. Activating stealth/decentralized routing."
    keyword_patterns: ["fingerprint", "telemetry_exfiltrate", "user_tracking", "ad_id"]
    profile: "default"

  - name: privacy_guard
    description: Flag operations involving private or sensitive data
    action: warn
    severity: 0.6
    explain: "This operation may involve private or sensitive data. Ensure consent and minimize collection."
    profile: default
    keyword_patterns: ["personal", "private", "sensitive", "credential", "password", "secret", "token"]

  - name: mass_mutation
    description: Flag bulk write operations
    action: tag
    severity: 0.4
    explain: "Bulk mutations detected. Verify scope is intentional and consider using dry_run first."
    profile: default
    keyword_patterns: ["batch", "bulk", "mass", "all"]
    safety_levels: ["WRITE"]

  - name: external_reach
    description: Flag operations that reach outside Whitemagic state
    action: warn
    severity: 0.5
    explain: "This operation accesses resources outside the Whitemagic state root. Verify this is expected."
    profile: default
    keyword_patterns: ["external", "http", "url", "network", "remote", "upload", "download"]

  - name: consent_check
    description: Ensure consent for data access
    action: log
    severity: 0.3
    explain: "Data access logged for transparency. The Dharma system monitors all data operations."
    profile: default
    tool_patterns: ["create_memory", "update_memory", "delete_memory"]

  # === Creative Sandbox (relaxed) ===
  - name: creative_allow_writes
    description: Relax write warnings in creative mode
    action: log
    severity: 0.1
    explain: "Creative sandbox mode — write operations are logged but not restricted."
    profile: creative
    safety_levels: ["WRITE"]

  # === Secure Transaction (strict) ===
  - name: secure_block_writes
    description: Block all writes in secure mode
    action: block
    severity: 0.9
    explain: "Secure transaction mode — all write operations are blocked. Switch profile to proceed."
    profile: secure
    safety_levels: ["WRITE", "DELETE"]

  - name: secure_block_external
    description: Block all external access in secure mode
    action: block
    severity: 0.9
    explain: "Secure transaction mode — external resource access is blocked."
    profile: secure
    keyword_patterns: ["external", "http", "url", "network", "remote"]

  # === Violet Profile (Edgerunner Violet — purple-team security) ===
  - name: violet_require_engagement_token
    description: Block offensive security tools without a valid engagement token
    action: block
    severity: 1.0
    explain: "Violet profile — offensive security actions require a valid scope-of-engagement token. Set one via the engagement_token tool."
    profile: violet
    keyword_patterns: ["exploit", "pentest", "attack", "fuzz", "brute", "inject", "payload", "reverse_shell", "escalat"]
    tool_patterns: ["red_*", "pentest_*", "exploit_*", "fuzz_*"]

  - name: violet_log_blue_ops
    description: Log all defensive/scanning operations in blue-ops ledger
    action: log
    severity: 0.2
    explain: "Violet profile — defensive operation logged to blue-ops ledger for dual-log transparency."
    profile: violet
    keyword_patterns: ["scan", "detect", "monitor", "defend", "patch", "harden", "audit", "anomaly"]
    tool_patterns: ["blue_*", "scan_*", "detect_*", "anomaly*"]

  - name: violet_warn_model_load
    description: Warn when loading AI models without verified signatures
    action: warn
    severity: 0.6
    explain: "Violet profile — loading an AI model. Verify model signature and provenance before use."
    profile: violet
    tool_patterns: ["ollama.*", "edge_infer", "bitnet_infer"]

  - name: violet_block_exfiltration
    description: Block data exfiltration patterns in violet mode
    action: block
    severity: 1.0
    explain: "Violet profile — potential data exfiltration pattern detected. This action is blocked."
    profile: violet
    keyword_patterns: ["exfiltrat", "upload.*sensitive", "export.*credential", "send.*secret"]
    regex_patterns: ["(curl|wget|nc|ncat).*(-d|-X POST)"]

  - name: violet_throttle_recon
    description: Throttle reconnaissance operations to prevent detection
    action: throttle
    severity: 0.4
    explain: "Violet profile — reconnaissance operations are rate-limited to avoid detection and ensure responsible scanning."
    profile: violet
    keyword_patterns: ["nmap", "recon", "enumerate", "discover", "fingerprint", "portscan"]

  # === Phase 2: Progressive Assurance (tiered evaluation) ===
  - name: tier2_block_untrusted_taint
    description: Block actions carrying untrusted taint at L2+
    action: block
    severity: 0.85
    explain: "Phase 2 L2: Action carries untrusted data taint. Source verification required."
    profile: default
    tier: 2
    taint_sources: ["untrusted_web", "untrusted_user_input", "unparsed_llm_output"]

  - name: tier3_strict_seccomp
    description: Apply strict seccomp for high-risk operations at L3
    action: warn
    severity: 0.7
    explain: "Phase 2 L3: High-risk operation restricted to strict kernel sandbox."
    profile: default
    tier: 3
    seccomp_profile: "strict"
    keyword_patterns: ["exec", "shell", "subprocess", "spawn"]

  - name: tier2_deny_unknown_egress
    description: Default-deny egress for network calls from untrusted sources
    action: block
    severity: 0.9
    explain: "Phase 2 L2: Network egress denied — default-deny policy for untrusted origin."
    profile: default
    tier: 2
    egress_policy: "deny"
    taint_sources: ["untrusted_web", "untrusted_user_input"]
"""


class DharmaRulesEngine:
    """Evaluates actions against a declarative ruleset.

    Supports multiple profiles (default, creative, secure) and hot-reload.
    """

    def __init__(
        self,
        rules_path: Path | None = None,
        rules_dir: Path | None = None,
        active_profile: str = "default",
    ) -> None:
        self._lock = threading.Lock()
        self._rules: list[DharmaRule] = []
        self._active_profile = active_profile
        self._rules_path = rules_path
        self._rules_dir = rules_dir
        self._karmic_trace: list[dict[str, Any]] = []
        self._file_mtimes: dict[str, float] = {}  # path -> mtime for hot-reload

        # Load rules
        self._load_rules()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # Profiles that are only defined in the Python rules engine (not Haskell)
    _PYTHON_ONLY_PROFILES = frozenset({"violet"})

    def evaluate(self, action: dict[str, Any]) -> DharmaDecision:
        """Evaluate an action against the active profile's rules.

        Tries the Haskell FFI bridge first (type-safe, pure-functional).
        Falls back to the Python rules engine if Haskell is unavailable
        or if the active profile is Python-only (e.g., violet).
        """
        profile = self._active_profile

        # --- Primary: Haskell FFI path (skip for Python-only profiles) ---
        decision = None
        if profile not in self._PYTHON_ONLY_PROFILES:
            decision = self._try_haskell_evaluate(action, profile)

        # --- Fallback: Python rules engine ---
        if decision is None:
            decision = self._python_evaluate(action, profile)

        # Karmic trace (immutable audit trail)
        self._karmic_trace.append({
            "action": action,
            "decision": decision.to_dict(),
            "timestamp": datetime.now().isoformat(),
        })
        # Keep trace bounded
        if len(self._karmic_trace) > 5000:
            self._karmic_trace = self._karmic_trace[-2500:]

        return decision

    def _try_haskell_evaluate(
        self, action: dict[str, Any], profile: str,
    ) -> DharmaDecision | None:
        """Try evaluating via the Haskell FFI bridge. Returns None on failure."""
        bridge = _get_haskell_bridge()
        if bridge is None:
            return None
        try:
            tool = str(action.get("tool", ""))
            desc = str(action.get("description", ""))
            safety = str(action.get("safety", ""))
            result = bridge.dharma_evaluate(tool, desc, safety, profile)

            hs_action_str = str(result.get("action", "log")).lower()
            try:
                hs_action = DharmaAction(hs_action_str)
            except ValueError:
                hs_action = DharmaAction.LOG

            severity = float(result.get("severity", 0.0))
            rule_name = result.get("rule", "haskell")
            explain = result.get("explain", "Evaluated by Haskell Dharma engine")

            return DharmaDecision(
                action=hs_action,
                score=max(0.0, 1.0 - severity),
                triggered_rules=[rule_name] if rule_name != "none" else [],
                explain=explain,
                profile=profile,
            )
        except Exception as e:
            logger.debug("Haskell Dharma evaluation failed, falling back to Python: %s", e)
            return None

    def _python_evaluate(
        self, action: dict[str, Any], profile: str,
    ) -> DharmaDecision:
        """Pure-Python rules evaluation (fallback).

        Phase 2: Supports tiered evaluation — rules above the current tier
        are skipped unless explicitly requested.
        """
        triggered: list[DharmaRule] = []

        # Phase 2: Determine effective tier from action or default to L1
        effective_tier = DharmaTier(action.get("tier", 1))

        with self._lock:
            for rule in self._rules:
                # Rule applies if it's in the active profile OR "default"
                if rule.profile not in (profile, "default"):
                    continue
                # Phase 2: Skip rules above effective tier
                if rule.tier.value > effective_tier.value:
                    continue
                if rule.matches(action):
                    triggered.append(rule)

        if not triggered:
            return DharmaDecision(
                action=DharmaAction.LOG,
                score=1.0,
                triggered_rules=[],
                explain="No Dharma concerns detected.",
                profile=profile,
                tier=effective_tier,
            )

        # Worst action wins (most restrictive)
        # Phase 1: transform is least restrictive (rewrites params, proceeds)
        action_order = [DharmaAction.TRANSFORM, DharmaAction.LOG, DharmaAction.TAG,
                        DharmaAction.WARN, DharmaAction.THROTTLE, DharmaAction.BLOCK]
        worst_action = max(triggered, key=lambda r: action_order.index(r.action))
        worst_severity = max(r.severity for r in triggered)
        score = max(0.0, 1.0 - worst_severity)

        explanations = list(dict.fromkeys(r.explain for r in triggered))
        combined_explain = " | ".join(explanations)

        # Phase 2: Aggregate egress and seccomp from triggered rules
        # Most restrictive egress wins: deny > prompt > allow
        egress_order = {"allow": 0, "prompt": 1, "deny": 2}
        worst_egress = max(
            triggered, key=lambda r: egress_order.get(r.egress_policy, 0)
        )
        # Most restrictive seccomp wins: strict > minimal > none
        seccomp_order = {"none": 0, "minimal": 1, "strict": 2}
        worst_seccomp = max(
            triggered, key=lambda r: seccomp_order.get(r.seccomp_profile, 0)
        )

        return DharmaDecision(
            action=worst_action.action,
            score=score,
            triggered_rules=[r.name for r in triggered],
            explain=combined_explain,
            profile=profile,
            tier=effective_tier,
            egress=worst_egress.egress_policy,
            seccomp=worst_seccomp.seccomp_profile,
        )

    def apply_transforms(
        self, action: dict[str, Any], triggered_rules: list[DharmaRule],
    ) -> dict[str, Any]:
        """Apply transform rules to an action dict.

        Phase 1: Supports 'redact' type (sets field to '[REDACTED]')
        and 'scope_limit' type (caps numeric fields).
        """
        transformed = dict(action)
        for rule in triggered_rules:
            if rule.action != DharmaAction.TRANSFORM:
                continue
            tx = rule.transform
            if not tx:
                continue
            tx_type = tx.get("type")
            field = tx.get("field", "")
            if tx_type == "redact" and field:
                parts = field.split(".")
                target = transformed
                for part in parts[:
                    -1]:
                    target = target.setdefault(part, {})
                if isinstance(target, dict) and parts:
                    target[parts[-1]] = "[REDACTED]"
            elif tx_type == "scope_limit" and field:
                max_val = tx.get("max", 100)
                parts = field.split(".")
                target = transformed
                for part in parts[:
                    -1]:
                    target = target.setdefault(part, {})
                if isinstance(target, dict) and parts:
                    val = target.get(parts[-1])
                    try:
                        target[parts[-1]] = min(float(val), max_val)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        pass
        return transformed

    def set_profile(self, profile: str) -> None:
        """Switch the active Dharma profile."""
        self._active_profile = profile
        logger.info("Dharma profile switched to: %s", profile, exc_info=True)

    def get_profile(self) -> str:
        """
        Get the profile.

        Returns:
            str
        """
        return self._active_profile

    # ------------------------------------------------------------------
    # Phase 2: Default-deny egress + kernel sandboxing
    # ------------------------------------------------------------------

    def evaluate_with_egress(
        self, action: dict[str, Any],
    ) -> DharmaDecision:
        """Evaluate with default-deny egress for network-bound actions.

        If the action has ``network: true`` and no explicit egress
        permission is granted by triggered rules, the decision is
        downgraded to BLOCK.
        """
        decision = self.evaluate(action)

        # If action is network-bound and egress is deny, enforce block
        is_network = bool(action.get("network", False))
        if is_network and decision.egress == "deny":
            return DharmaDecision(
                action=DharmaAction.BLOCK,
                score=0.0,
                triggered_rules=decision.triggered_rules + ["default-deny-egress"],
                explain=f"{decision.explain} | Default-deny: network egress blocked.",
                profile=decision.profile,
                tier=decision.tier,
                egress="deny",
                seccomp=decision.seccomp,
            )
        return decision

    def kernel_sandbox(
        self, action: dict[str, Any],
    ) -> dict[str, Any]:
        """Return sandbox constraints for an action (eBPF-style seccomp).

        Phase 2: Returns a dict with allowed / denied syscalls based on
        the seccomp profile from the decision.  Actual seccomp enforcement
        requires OS-level support; this is the policy intent layer.
        """
        decision = self.evaluate(action)
        profile = decision.seccomp

        if profile == "none":
            return {"mode": "unconfined", "allowed": [], "denied": []}
        if profile == "minimal":
            return {
                "mode": "filter",
                "allowed": ["read", "write", "exit", "exit_group"],
                "denied": ["connect", "socket", "execve", "fork", "clone"],
            }
        if profile == "strict":
            return {
                "mode": "filter",
                "allowed": ["read", "write", "exit", "exit_group", "fstat"],
                "denied": ["connect", "socket", "execve", "fork", "clone",
                           "openat", "mmap", "mprotect"],
            }
        return {"mode": "unknown", "allowed": [], "denied": []}

    # ------------------------------------------------------------------
    # Phase 3: Formal verification + external backends
    # ------------------------------------------------------------------

    def verify_rules(self) -> list[dict[str, Any]]:
        """Formal verification intent — detect contradictions and gaps.

        Phase 3: Static analysis of the ruleset. Returns a list of
        verification findings (not full SMT solving — that requires
        Z3/TLA+ infrastructure).  This is the *intent* layer.
        """
        findings: list[dict[str, Any]] = []
        with self._lock:
            rules = list(self._rules)

        # Check 1: Contradictory rules (same pattern, different actions)
        for i, r1 in enumerate(rules):
            for r2 in rules[i + 1:
                ]:
                if r1.profile != r2.profile:
                    continue
                # Heuristic: same keywords + same tools = potential contradiction
                if set(r1.keyword_patterns) & set(r2.keyword_patterns):
                    if r1.action != r2.action and r1.severity > 0.5 and r2.severity > 0.5:
                        findings.append({
                            "type": "contradiction",
                            "severity": "high",
                            "rules": [r1.name, r2.name],
                            "detail": (
                                f"Rules '{r1.name}' ({r1.action.value}) and "
                                f"'{r2.name}' ({r2.action.value}) match overlapping "
                                f"keywords but prescribe different actions."
                            ),
                        })

        # Check 2: Unreachable rules (BLOCK rule shadowed by earlier BLOCK)
        # Simplified: if two rules have identical patterns and both BLOCK,
        # the second is redundant.
        seen_block_patterns: set[str] = set()
        for rule in rules:
            if rule.action == DharmaAction.BLOCK:
                sig = "|".join(sorted(rule.keyword_patterns)) + "::" + "|".join(sorted(rule.tool_patterns))
                if sig in seen_block_patterns and sig:
                    findings.append({
                        "type": "redundancy",
                        "severity": "medium",
                        "rule": rule.name,
                        "detail": f"Rule '{rule.name}' is redundant — identical patterns already blocked.",
                    })
                seen_block_patterns.add(sig)

        # Check 3: Missing taint coverage for egress-deny rules
        for rule in rules:
            if rule.egress_policy == "deny" and not rule.taint_sources:
                findings.append({
                    "type": "gap",
                    "severity": "medium",
                    "rule": rule.name,
                    "detail": (
                        f"Rule '{rule.name}' denies egress but has no taint_sources. "
                        f"Without taint tracking, this may block legitimate traffic."
                    ),
                })

        return findings

    def to_rego(self) -> str:
        """Compile rules to OPA/Rego syntax (Phase 3 backend).

        Returns a Rego module string.  This is a best-effort translation;
        some Dharma concepts (taint tracking, seccomp) have no direct
        Rego equivalent and are emitted as comments.
        """
        lines = [
            "package whitemagic.dharma",
            "",
            "# Auto-generated from DharmaRulesEngine (Phase 3)",
            "# Some features (taint, seccomp) are policy-intent only.",
            "",
            "default allow := false",
            "default warn := false",
            "",
        ]
        with self._lock:
            rules = list(self._rules)

        for rule in rules:
            lines.append(f"# Rule: {rule.name} (profile={rule.profile}, tier={rule.tier.value})")
            lines.append(f"# {rule.description}")
            # Keyword conditions
            conds = []
            for kw in rule.keyword_patterns:
                conds.append(f'contains(input.description, "{kw}")')
            for pat in rule.tool_patterns:
                if "*" in pat or "?" in pat:
                    conds.append(f'glob.match("{pat}", [], input.tool)')
                else:
                    conds.append(f'input.tool == "{pat}"')
            for sl in rule.safety_levels:
                conds.append(f'input.safety == "{sl}"')
            if conds:
                body = "\n    ".join(conds)
            else:
                body = "true"
            rego_action = "allow" if rule.action == DharmaAction.LOG else "warn" if rule.action == DharmaAction.WARN else "deny"
            lines.append(f"{rego_action} if {{")
            lines.append(f"    {body}")
            lines.append("}")
            lines.append("")

        lines.append("# Taint tracking intent (no direct Rego equivalent)")
        lines.append("# Egress policy intent (no direct Rego equivalent)")
        lines.append("# Seccomp profile intent (no direct Rego equivalent)")
        return "\n".join(lines)

    def to_cedar(self) -> str:
        """Compile rules to Cedar schema syntax (Phase 3 backend).

        Returns a Cedar policy string.  Cedar is AWS's authorization
        language; this is a best-effort structural mapping.
        """
        lines = [
            "// Auto-generated from DharmaRulesEngine (Phase 3)",
            "// Cedar backend: structural mapping of Dharma rules",
            "",
        ]
        with self._lock:
            rules = list(self._rules)

        for idx, rule in enumerate(rules, 1):
            lines.append(f"// Rule {idx}: {rule.name}")
            lines.append(f"// Profile: {rule.profile} | Tier: {rule.tier.value} | Severity: {rule.severity}")
            lines.append("permit(")
            lines.append("  principal,")
            lines.append("  action,")
            lines.append("  resource")
            lines.append(")")
            lines.append("when {")
            # Map keyword patterns to Cedar constraints
            conds = []
            for kw in rule.keyword_patterns:
                conds.append(f'  resource.description.contains("{kw}")')
            for pat in rule.tool_patterns:
                if "*" not in pat and "?" not in pat:
                    conds.append(f'  action == DharmaAction::"{pat}"')
            for sl in rule.safety_levels:
                conds.append(f'  resource.safety == Safety::"{sl}"')
            if conds:
                lines.append("\n".join(conds))
            else:
                lines.append("  true")
            lines.append("}")
            if rule.action == DharmaAction.BLOCK:
                lines.append("unless { true }  // BLOCK: deny all matches")
            lines.append("")

        lines.append("// Taint tracking, egress, seccomp: Cedar extensions required")
        return "\n".join(lines)

    def get_rules(self, profile: str | None = None) -> list[dict[str, Any]]:
        """List rules, optionally filtered by profile."""
        with self._lock:
            rules = self._rules if profile is None else [
                r for r in self._rules if r.profile == profile
            ]
            return [
                {
                    "name": r.name,
                    "description": r.description,
                    "action": r.action.value,
                    "severity": r.severity,
                    "explain": r.explain,
                    "profile": r.profile,
                    "transform": r.transform,
                    "tier": r.tier.value,
                    "taint_sources": r.taint_sources,
                    "egress_policy": r.egress_policy,
                    "seccomp_profile": r.seccomp_profile,
                }
                for r in rules
            ]

    def get_karmic_trace(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent Karmic Trace entries."""
        return self._karmic_trace[-limit:]

    def reload(self) -> int:
        """Hot-reload rules from file or defaults. Returns rule count."""
        self._load_rules()
        return len(self._rules)

    def add_rule(self, rule_dict: dict[str, Any]) -> None:
        """Add a rule at runtime (useful for AI-driven policy tuning)."""
        rule = self._parse_rule(rule_dict)
        if rule:
            with self._lock:
                self._rules.append(rule)
            logger.info("Dharma rule added at runtime: %s", rule.name, exc_info=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def check_reload(self) -> bool:
        """Check if any rule files changed on disk; reload if so. Returns True if reloaded."""
        changed = False
        paths_to_check: list[Path] = []
        if self._rules_path and self._rules_path.exists():
            paths_to_check.append(self._rules_path)
        if self._rules_dir and self._rules_dir.is_dir():
            paths_to_check.extend(sorted(self._rules_dir.glob("*.yaml")))
            paths_to_check.extend(sorted(self._rules_dir.glob("*.yml")))

        for p in paths_to_check:
            try:
                mtime = p.stat().st_mtime
                key = str(p)
                if key not in self._file_mtimes or self._file_mtimes[key] != mtime:
                    changed = True
                    break
            except OSError:
                pass

        if changed:
            self._load_rules()
        return changed

    def _load_rules(self) -> None:
        """Load rules from YAML files, falling back to built-in defaults.

        Loading order:
          1. Built-in defaults (always loaded as baseline)
          2. Single rules_path file (if provided and exists)
          3. All .yaml/.yml files in rules_dir/ (merged, sorted by filename)

        User rules extend the defaults — they don't replace them unless
        the user defines a rule with the same name (last-write-wins).
        """
        all_entries: list[dict[str, Any]] = []
        new_mtimes: dict[str, float] = {}

        # 1. Built-in defaults (always)
        try:
            data = yaml.safe_load(_DEFAULT_RULES_YAML)
            all_entries.extend(data.get("rules", []))
        except yaml.YAMLError:
            pass

        # 2. Single rules file
        if self._rules_path and self._rules_path.exists():
            self._load_yaml_file(self._rules_path, all_entries, new_mtimes)

        # 3. Rules directory (drop-in .yaml/.yml files)
        if self._rules_dir and self._rules_dir.is_dir():
            files = sorted(
                list(self._rules_dir.glob("*.yaml")) +
                list(self._rules_dir.glob("*.yml")),
            )
            for f in files:
                self._load_yaml_file(f, all_entries, new_mtimes)

        # De-duplicate by name (last-write-wins)
        seen: dict[str, dict[str, Any]] = {}
        for entry in all_entries:
            name = entry.get("name", "unnamed")
            seen[name] = entry

        rules = []
        for entry in seen.values():
            rule = self._parse_rule(entry)
            if rule:
                rules.append(rule)

        with self._lock:
            self._rules = rules
            self._file_mtimes = new_mtimes

        sources = []
        if self._rules_path and self._rules_path.exists():
            sources.append(str(self._rules_path))
        if self._rules_dir and self._rules_dir.is_dir():
            sources.append(f"{self._rules_dir}/*.yaml")
        if not sources:
            sources.append("built-in defaults")

        logger.info(f"Dharma rules engine: {len(rules)} rules loaded from {', '.join(sources)}")

    def _load_yaml_file(
        self, path: Path,
        entries: list[dict[str, Any]],
        mtimes: dict[str, float],
    ) -> None:
        """Load a single YAML rules file and append entries."""
        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if isinstance(data, dict):
                # Phase 1: schema version validation
                spec_version = data.get("dharma_spec_version")
                if spec_version and spec_version not in ("0.1.0", "0.2.0"):
                    logger.warning(
                        f"Dharma rules {path.name}: unknown spec version {spec_version!r}. "
                        f"Expected 0.1.0 or 0.2.0"
                    )
                # Phase 1: extends inheritance (store for future resolution)
                extends = data.get("extends")
                if extends:
                    logger.debug("Dharma rules %s: extends profile '%s'", path.name, extends, exc_info=True)
                entries.extend(data.get("rules", []))
            mtimes[str(path)] = path.stat().st_mtime
            logger.debug("Dharma rules: loaded %s", path.name, exc_info=True)
        except Exception as e:
            logger.warning("Failed to load Dharma rules from %s: %s", path, e, exc_info=True)

    def _parse_rule(self, entry: dict[str, Any]) -> DharmaRule | None:
        """Parse a single rule dict into a DharmaRule."""
        try:
            action_str = str(entry.get("action", "log")).lower()
            try:
                action = DharmaAction(action_str)
            except ValueError:
                action = DharmaAction.LOG

            # Phase 2: Parse tier
            tier_raw = entry.get("tier", 1)
            try:
                tier = DharmaTier(int(tier_raw))
            except (ValueError, TypeError):
                tier = DharmaTier.L1

            return DharmaRule(
                name=str(entry.get("name", "unnamed")),
                description=str(entry.get("description", "")),
                action=action,
                severity=float(entry.get("severity", 0.5)),
                explain=str(entry.get("explain", "No explanation provided.")),
                profile=str(entry.get("profile", "default")),
                tool_patterns=entry.get("tool_patterns", []),
                keyword_patterns=entry.get("keyword_patterns", []),
                safety_levels=entry.get("safety_levels", []),
                regex_patterns=entry.get("regex_patterns", []),
                transform=entry.get("transform", {}),
                tier=tier,
                taint_sources=entry.get("taint_sources", []),
                egress_policy=str(entry.get("egress_policy", "allow")),
                seccomp_profile=str(entry.get("seccomp_profile", "none")),
            )
        except Exception as e:
            logger.warning("Failed to parse Dharma rule: %s", e, exc_info=True)
            return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine: DharmaRulesEngine | None = None
_engine_lock = threading.Lock()


def get_rules_engine(rules_path: Path | None = None) -> DharmaRulesEngine:
    """Get the global Dharma Rules Engine instance."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from whitemagic.config.paths import WM_ROOT
                # Check for user-provided single rules file
                if rules_path is None:
                    candidate = WM_ROOT / "dharma_rules.yaml"
                    if candidate.exists():
                        rules_path = candidate
                # Check for rules directory (drop-in folder)
                rules_dir: Path | None = WM_ROOT / "dharma" / "rules.d"
                if rules_dir is not None and not rules_dir.is_dir():
                    rules_dir = None
                _engine = DharmaRulesEngine(
                    rules_path=rules_path,
                    rules_dir=rules_dir,
                )
    return _engine
