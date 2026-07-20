"""STRATA checker category → MITRE ATT&CK TTP mapping.

Maps each security-relevant STRATA checker category to one or more
MITRE ATT&CK Enterprise tactics and techniques. Non-security categories
(code quality, style, debug) are intentionally excluded.

Reference: https://attack.mitre.org/techniques/enterprise/
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TTPMapping:
    """A single MITRE ATT&CK technique mapping."""
    tactic: str
    technique_id: str
    technique_name: str
    confidence: float = 0.8


@dataclass
class CategoryMapping:
    """Mapping for a STRATA category to ATT&CK TTPs."""
    strata_category: str
    ttps: list[TTPMapping] = field(default_factory=list)
    notes: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# STRATA → MITRE ATT&CK mapping table
# Only security-relevant categories are mapped. Code quality, style, and
# debug categories (dead_code, print_debug, narrative_comment, etc.) are
# excluded — they don't correspond to adversary TTPs.
# ═══════════════════════════════════════════════════════════════════════════

_MAPPINGS: dict[str, CategoryMapping] = {
    # ── Injection ──────────────────────────────────────────────────────────
    "py_sql_injection": CategoryMapping(
        strata_category="py_sql_injection",
        ttps=[
            TTPMapping("Initial Access", "T1190", "Exploit Public-Facing Application"),
            TTPMapping("Collection", "T1213", "Data from Information Repositories"),
        ],
        notes="SQL injection allows direct database access from web-facing apps.",
    ),
    "py_command_injection": CategoryMapping(
        strata_category="py_command_injection",
        ttps=[
            TTPMapping("Execution", "T1059", "Command and Scripting Interpreter"),
            TTPMapping("Execution", "T1059.004", "Unix Shell"),
        ],
        notes="Command injection via subprocess with shell=True or f-string.",
    ),
    "js_eval": CategoryMapping(
        strata_category="js_eval",
        ttps=[
            TTPMapping("Execution", "T1059.007", "JavaScript"),
            TTPMapping("Defense Evasion", "T1027", "Obfuscated Files or Information"),
        ],
        notes="eval() enables arbitrary code execution in JS context.",
    ),
    "ruby_eval": CategoryMapping(
        strata_category="ruby_eval",
        ttps=[
            TTPMapping("Execution", "T1059", "Command and Scripting Interpreter"),
        ],
        notes="Ruby eval enables arbitrary code execution.",
    ),
    "shell_backtick": CategoryMapping(
        strata_category="shell_backtick",
        ttps=[
            TTPMapping("Execution", "T1059.004", "Unix Shell"),
            TTPMapping("Execution", "T1059", "Command and Scripting Interpreter"),
        ],
        notes="Backtick substitution in shell scripts enables command injection.",
    ),
    "shell_unquoted_variable": CategoryMapping(
        strata_category="shell_unquoted_variable",
        ttps=[
            TTPMapping("Execution", "T1059.004", "Unix Shell"),
        ],
        notes="Unquoted variables in shell can cause word splitting/globbing.",
    ),

    # ── Path traversal / file access ───────────────────────────────────────
    "py_path_traversal": CategoryMapping(
        strata_category="py_path_traversal",
        ttps=[
            TTPMapping("Collection", "T1005", "Data from Local System"),
            TTPMapping("Discovery", "T1083", "File and Directory Discovery"),
        ],
        notes="Path traversal allows reading arbitrary files.",
    ),
    "model_path_traversal": CategoryMapping(
        strata_category="model_path_traversal",
        ttps=[
            TTPMapping("Collection", "T1005", "Data from Local System"),
            TTPMapping("Defense Evasion", "T1027", "Obfuscated Files or Information"),
        ],
        notes="Model path traversal can load models from arbitrary locations.",
    ),
    "hardcoded_url": CategoryMapping(
        strata_category="hardcoded_url",
        ttps=[
            TTPMapping("Command and Control", "T1071", "Application Layer Protocol"),
            TTPMapping("Exfiltration", "T1041", "Exfiltration Over C2 Channel"),
        ],
        notes="Hardcoded URLs may indicate C2 endpoints or data exfiltration.",
    ),

    # ── Secrets / credentials ──────────────────────────────────────────────
    "hardcoded_secret": CategoryMapping(
        strata_category="hardcoded_secret",
        ttps=[
            TTPMapping("Credential Access", "T1552", "Unsecured Credentials"),
            TTPMapping("Credential Access", "T1552.001", "Credentials In Files"),
        ],
        notes="Hardcoded secrets are credentials accessible to anyone with code access.",
    ),

    # ── SSRF ───────────────────────────────────────────────────────────────
    "py_ssrf": CategoryMapping(
        strata_category="py_ssrf",
        ttps=[
            TTPMapping("Discovery", "T1046", "Network Service Discovery"),
            TTPMapping("Defense Evasion", "T1090", "Proxy Through Internal Network"),
        ],
        notes="SSRF enables internal network scanning and proxy access.",
    ),

    # ── XSS ────────────────────────────────────────────────────────────────
    "web_xss_innerhtml": CategoryMapping(
        strata_category="web_xss_innerhtml",
        ttps=[
            TTPMapping("Execution", "T1059.007", "JavaScript"),
            TTPMapping("Collection", "T1057", "Process Injection"),
        ],
        notes="XSS via innerHTML enables client-side code execution.",
    ),
    "web_xss_ejs": CategoryMapping(
        strata_category="web_xss_ejs",
        ttps=[
            TTPMapping("Execution", "T1059.007", "JavaScript"),
        ],
        notes="XSS via EJS unescaped output enables client-side code execution.",
    ),
    "web_xss_react": CategoryMapping(
        strata_category="web_xss_react",
        ttps=[
            TTPMapping("Execution", "T1059.007", "JavaScript"),
        ],
        notes="XSS via React dangerouslySetInnerHTML enables client-side code execution.",
    ),
    "web_xss_django_safe": CategoryMapping(
        strata_category="web_xss_django_safe",
        ttps=[
            TTPMapping("Execution", "T1059.007", "JavaScript"),
        ],
        notes="XSS via Django |safe filter enables client-side code execution.",
    ),
    "js_innerhtml_xss": CategoryMapping(
        strata_category="js_innerhtml_xss",
        ttps=[
            TTPMapping("Execution", "T1059.007", "JavaScript"),
        ],
        notes="innerHTML assignment with user input enables XSS.",
    ),

    # ── Access control / auth ──────────────────────────────────────────────
    "web_idor": CategoryMapping(
        strata_category="web_idor",
        ttps=[
            TTPMapping("Initial Access", "T1190", "Exploit Public-Facing Application"),
            TTPMapping("Collection", "T1213", "Data from Information Repositories"),
        ],
        notes="IDOR allows unauthorized access to other users' data.",
    ),
    "web_open_redirect": CategoryMapping(
        strata_category="web_open_redirect",
        ttps=[
            TTPMapping("Initial Access", "T1566.002", "Phishing: Spearphishing Link"),
            TTPMapping("Defense Evasion", "T1027", "Obfuscated Files or Information"),
        ],
        notes="Open redirects enable phishing and trust bypass.",
    ),
    "web_csrf_missing": CategoryMapping(
        strata_category="web_csrf_missing",
        ttps=[
            TTPMapping("Initial Access", "T1185", "Browser Session Hijacking"),
            TTPMapping("Defense Evasion", "T1550", "Use Alternate Authentication Material"),
        ],
        notes="Missing CSRF protection enables session hijacking.",
    ),

    # ── Deserialization / model security ───────────────────────────────────
    "unsafe_deserialization": CategoryMapping(
        strata_category="unsafe_deserialization",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
            TTPMapping("Defense Evasion", "T1027", "Obfuscated Files or Information"),
        ],
        notes="Unsafe deserialization (pickle, yaml) enables arbitrary code execution.",
    ),
    "pickle_file_in_repo": CategoryMapping(
        strata_category="pickle_file_in_repo",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
            TTPMapping("Credential Access", "T1552.001", "Credentials In Files"),
        ],
        notes="Pickle files in repos are RCE vectors on load.",
    ),
    "pickle_reduce_exploit": CategoryMapping(
        strata_category="pickle_reduce_exploit",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
            TTPMapping("Execution", "T1059", "Command and Scripting Interpreter"),
        ],
        notes="__reduce__ in pickle is explicitly an RCE payload.",
    ),
    "unsafe_yaml_load": CategoryMapping(
        strata_category="unsafe_yaml_load",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="yaml.load (unsafe) enables arbitrary object construction.",
    ),
    "unsafe_torch_load": CategoryMapping(
        strata_category="unsafe_torch_load",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="torch.load without weights_only enables arbitrary code execution.",
    ),
    "unsafe_keras_load": CategoryMapping(
        strata_category="unsafe_keras_load",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="Keras model loading with custom objects enables code execution.",
    ),
    "keras_lambda_rce": CategoryMapping(
        strata_category="keras_lambda_rce",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
            TTPMapping("Execution", "T1059", "Command and Scripting Interpreter"),
        ],
        notes="Keras Lambda layers can contain arbitrary Python code.",
    ),
    "numpy_unsafe_load": CategoryMapping(
        strata_category="numpy_unsafe_load",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="numpy.load with allow_pickle=True enables arbitrary code execution.",
    ),
    "onnx_unsafe_load": CategoryMapping(
        strata_category="onnx_unsafe_load",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="ONNX model loading can execute arbitrary code via custom operators.",
    ),
    "hf_trust_remote_code": CategoryMapping(
        strata_category="hf_trust_remote_code",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
            TTPMapping("Command and Control", "T1071", "Application Layer Protocol"),
        ],
        notes="HuggingFace trust_remote_code=True executes arbitrary Python from model repos.",
    ),
    "hf_model_load": CategoryMapping(
        strata_category="hf_model_load",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="Loading HF models without verification enables supply chain attacks.",
    ),
    "keras_custom_objects": CategoryMapping(
        strata_category="keras_custom_objects",
        ttps=[
            TTPMapping("Execution", "T1203", "Exploitation for Client Execution"),
        ],
        notes="Keras custom_objects enables arbitrary code execution on model load.",
    ),

    # ── Solidity / Web3 specific ───────────────────────────────────────────
    "sol_reentrancy_risk": CategoryMapping(
        strata_category="sol_reentrancy_risk",
        ttps=[
            TTPMapping("Initial Access", "T1190", "Exploit Public-Facing Application"),
        ],
        notes="Reentrancy enables draining contract funds via recursive calls.",
    ),
    "sol_missing_access_control": CategoryMapping(
        strata_category="sol_missing_access_control",
        ttps=[
            TTPMapping("Privilege Escalation", "T1548", "Abuse Elevation Control Mechanism"),
        ],
        notes="Missing access control allows unauthorized privileged operations.",
    ),
    "sol_delegatecall_user": CategoryMapping(
        strata_category="sol_delegatecall_user",
        ttps=[
            TTPMapping("Execution", "T1059", "Command and Scripting Interpreter"),
            TTPMapping("Privilege Escalation", "T1548", "Abuse Elevation Control Mechanism"),
        ],
        notes="delegatecall to user-controlled address enables arbitrary code execution in contract context.",
    ),
    "sol_unprotected_selfdestruct": CategoryMapping(
        strata_category="sol_unprotected_selfdestruct",
        ttps=[
            TTPMapping("Impact", "T1485", "Data Destruction"),
        ],
        notes="Unprotected selfdestruct can destroy the contract permanently.",
    ),
    "sol_tx_origin_auth": CategoryMapping(
        strata_category="sol_tx_origin_auth",
        ttps=[
            TTPMapping("Initial Access", "T1566.002", "Phishing: Spearphishing Link"),
        ],
        notes="tx.origin auth enables phishing attacks to bypass authorization.",
    ),
    "sol_spot_price_oracle": CategoryMapping(
        strata_category="sol_spot_price_oracle",
        ttps=[
            TTPMapping("Impact", "T1499", "Endpoint Denial of Service"),
        ],
        notes="Spot price oracle manipulation enables flash loan attacks.",
    ),
    "sol_single_block_twap": CategoryMapping(
        strata_category="sol_single_block_twap",
        ttps=[
            TTPMapping("Impact", "T1499", "Endpoint Denial of Service"),
        ],
        notes="Single-block TWAP is manipulable via flash loans.",
    ),
    "sol_unchecked_call": CategoryMapping(
        strata_category="sol_unchecked_call",
        ttps=[
            TTPMapping("Defense Evasion", "T1562", "Impair Defenses"),
        ],
        notes="Unchecked low-level calls silently fail, masking errors.",
    ),
    "sol_unchecked_transfer": CategoryMapping(
        strata_category="sol_unchecked_transfer",
        ttps=[
            TTPMapping("Defense Evasion", "T1562", "Impair Defenses"),
        ],
        notes="Unchecked ERC20 transfer return values can silently fail.",
    ),
    "sol_integer_overflow_pre08": CategoryMapping(
        strata_category="sol_integer_overflow_pre08",
        ttps=[
            TTPMapping("Impact", "T1499", "Endpoint Denial of Service"),
        ],
        notes="Integer overflow enables arithmetic exploits pre-0.8.0.",
    ),
    "sol_state_shadowing": CategoryMapping(
        strata_category="sol_state_shadowing",
        ttps=[
            TTPMapping("Defense Evasion", "T1562", "Impair Defenses"),
        ],
        notes="State variable shadowing masks intended storage writes.",
    ),

    # ── Data flow / taint ──────────────────────────────────────────────────
    "data_flow.taint": CategoryMapping(
        strata_category="data_flow.taint",
        ttps=[
            TTPMapping("Initial Access", "T1190", "Exploit Public-Facing Application"),
            TTPMapping("Collection", "T1005", "Data from Local System"),
        ],
        notes="Tainted data flow from untrusted source to sensitive sink.",
    ),

    # ── Rust unsafe ────────────────────────────────────────────────────────
    "rust_unsafe": CategoryMapping(
        strata_category="rust_unsafe",
        ttps=[
            TTPMapping("Execution", "T1055", "Process Injection"),
        ],
        notes="Rust unsafe blocks can enable memory corruption exploits.",
    ),
    "rust_lock_poisoning": CategoryMapping(
        strata_category="rust_lock_poisoning",
        ttps=[
            TTPMapping("Impact", "T1499", "Endpoint Denial of Service"),
        ],
        notes="Lock poisoning can cause panics and DoS.",
    ),

    # ── Go SQL injection ───────────────────────────────────────────────────
    "go_sql_injection": CategoryMapping(
        strata_category="go_sql_injection",
        ttps=[
            TTPMapping("Initial Access", "T1190", "Exploit Public-Facing Application"),
            TTPMapping("Collection", "T1213", "Data from Information Repositories"),
        ],
        notes="SQL injection in Go via string formatting.",
    ),
    "go_http_no_timeout": CategoryMapping(
        strata_category="go_http_no_timeout",
        ttps=[
            TTPMapping("Impact", "T1499", "Endpoint Denial of Service"),
        ],
        notes="HTTP clients without timeouts are vulnerable to slowloris-style DoS.",
    ),
}


def get_mapping(category: str) -> CategoryMapping | None:
    """Get the MITRE ATT&CK mapping for a STRATA checker category."""
    return _MAPPINGS.get(category)


def get_ttps_for_category(category: str) -> list[TTPMapping]:
    """Get the list of TTPs for a STRATA category. Empty if unmapped."""
    mapping = _MAPPINGS.get(category)
    return mapping.ttps if mapping else []


def get_ttp_ids_for_category(category: str) -> list[str]:
    """Get just the technique IDs for a STRATA category."""
    return [ttp.technique_id for ttp in get_ttps_for_category(category)]


def map_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a list of STRATA findings to their ATT&CK TTPs.

    Args:
        findings: List of finding dicts with 'category' field.

    Returns:
        List of dicts with finding + ttp_ids + ttp_details.
    """
    mapped = []
    for f in findings:
        category = f.get("category", "")
        ttps = get_ttps_for_category(category)
        if ttps:
            mapped.append({
                "finding": f,
                "category": category,
                "ttp_ids": [ttp.technique_id for ttp in ttps],
                "ttp_details": [
                    {
                        "tactic": ttp.tactic,
                        "technique_id": ttp.technique_id,
                        "technique_name": ttp.technique_name,
                        "confidence": ttp.confidence,
                    }
                    for ttp in ttps
                ],
            })
    return mapped


def generate_navigator_layer(
    findings: list[dict[str, Any]],
    layer_name: str = "WhiteMagic STRATA Findings",
    description: str = "STRATA security findings mapped to MITRE ATT&CK",
) -> dict[str, Any]:
    """Generate a MITRE ATT&CK Navigator layer JSON.

    Args:
        findings: List of finding dicts with 'category' and 'severity' fields.
        layer_name: Display name for the Navigator layer.
        description: Description shown in Navigator.

    Returns:
        Navigator layer JSON dict (v4.5 format).
    """
    # Aggregate techniques by TTP ID
    technique_findings: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        category = f.get("category", "")
        ttps = get_ttps_for_category(category)
        if ttps:
            for ttp in ttps:
                technique_findings.setdefault(ttp.technique_id, []).append(f)
        else:
            # Fall back to explicit mitre_ttp_ids in the finding
            for ttp_id in f.get("mitre_ttp_ids", []):
                technique_findings.setdefault(ttp_id, []).append(f)

    # Build technique entries
    techniques = []
    severity_score_map = {"error": 100, "warning": 50, "info": 25}
    for tech_id, tech_findings in technique_findings.items():
        max_severity = max(
            (severity_score_map.get(f.get("severity", "info"), 25) for f in tech_findings),
            default=25,
        )
        # Get tactic from first mapping
        mapping = None
        for f in tech_findings:
            mapping = get_mapping(f.get("category", ""))
            if mapping and mapping.ttps:
                break
        tactic = mapping.ttps[0].tactic if mapping and mapping.ttps else "Unknown"

        techniques.append({
            "techniqueID": tech_id,
            "tactic": tactic,
            "score": max_severity,
            "comment": f"{len(tech_findings)} finding(s) from {', '.join(set(f.get('category', '') for f in tech_findings))}",
            "enabled": True,
            "metadata": [
                {"name": "Finding Count", "value": str(len(tech_findings))},
                {"name": "Source", "value": "WhiteMagic STRATA"},
            ],
            "links": [],
            "showSubtechniques": True,
        })

    return {
        "versions": {
            "attack": "15",
            "navigator": "4.9.1",
            "layer": "4.5",
        },
        "name": layer_name,
        "domain": "enterprise-attack",
        "description": description,
        "filters": {
            "platforms": ["Linux", "macOS", "Windows", "Network", "PRE"],
        },
        "sorting": 0,
        "layout": {
            "layout": "side",
            "aggregateFunction": "average",
            "showID": False,
            "showName": True,
            "showAggregateScores": False,
            "countUnscored": False,
        },
        "hideDisabled": False,
        "techniques": techniques,
        "gradient": {
            "colors": ["#ff6666", "#ffe766", "#8ec843"],
            "minValue": 0,
            "maxValue": 100,
        },
        "legendItems": [
            {"label": "Critical (error)", "color": "#ff6666"},
            {"label": "Warning", "color": "#ffe766"},
            {"label": "Info", "color": "#8ec843"},
        ],
        "metadata": [
            {"name": "Generated By", "value": "WhiteMagic STRATA → MITRE ATT&CK"},
            {"name": "Total Findings", "value": str(len(findings))},
            {"name": "Mapped Techniques", "value": str(len(techniques))},
        ],
        "links": [
            {
                "source": "WhiteMagic Labs",
                "url": "https://whitemagic.dev",
            },
        ],
        "showTacticRowBackground": False,
        "tacticRowBackground": "#dddddd",
        "selectTechniquesAcrossTactics": True,
        "selectSubtechniquesWithParent": False,
    }


def navigator_layer_json(findings: list[dict[str, Any]], **kwargs: Any) -> str:
    """Generate Navigator layer as a JSON string."""
    return json.dumps(generate_navigator_layer(findings, **kwargs), indent=2)


def all_mapped_categories() -> list[str]:
    """Return all STRATA categories that have MITRE ATT&CK mappings."""
    return sorted(_MAPPINGS.keys())


def mapping_stats() -> dict[str, Any]:
    """Return statistics about the mapping table."""
    total_ttps = sum(len(m.ttps) for m in _MAPPINGS.values())
    tactics = set()
    for m in _MAPPINGS.values():
        for ttp in m.ttps:
            tactics.add(ttp.tactic)
    return {
        "mapped_categories": len(_MAPPINGS),
        "total_ttp_mappings": total_ttps,
        "unique_tactics": len(tactics),
        "tactics": sorted(tactics),
    }
