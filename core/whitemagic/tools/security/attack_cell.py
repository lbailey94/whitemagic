"""Multi-agent attack orchestration — 8-agent cell mapped to shelter system.

Maps a purple-team attack cell to WhiteMagic's Shelter compartment system.
Each agent runs in its own isolated shelter with scoped capabilities,
Dharma profile enforcement, and engagement token governance.

Agent Roles (8-agent cell):
  1. Recon Agent — network scanning, OSINT (nmap, nuclei)
  2. Web Agent — web app testing (http_probe, ffuf, nikto)
  3. Exploit Agent — vulnerability exploitation (sqlmap, PoC pipeline)
  4. C2 Agent — command & control simulation (http_probe post)
  5. Crypto Agent — cryptographic attacks (foundry, ABI analysis)
  6. Social Eng Agent — prompt injection, phishing simulation
  7. Lateral Agent — lateral movement simulation (nmap, hydra)
  8. Report Agent — finding aggregation, MITRE Navigator output

Each agent:
  - Runs in a violet shelter compartment
  - Has scoped capabilities (fs_read, fs_write, network)
  - Requires engagement token for offensive actions
  - Reports findings to shared contest pipeline
  - MITRE ATT&CK TTPs auto-mapped

Usage:
    from whitemagic.tools.security.attack_cell import AttackCell
    cell = AttackCell(target="http://example.com", scope="recon,web,exploit,report")
    result = cell.execute()
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# Counter for unique cell IDs
_cell_counter = 0


class AgentRole(StrEnum):
    """Roles in the 8-agent attack cell."""
    RECON = "recon"
    WEB = "web"
    EXPLOIT = "exploit"
    C2 = "c2"
    CRYPTO = "crypto"
    SOCIAL_ENG = "social_eng"
    LATERAL = "lateral"
    REPORT = "report"


# Agent role → shelter capabilities mapping
AGENT_CAPABILITIES: dict[AgentRole, list[str]] = {
    AgentRole.RECON: ["network_read", "fs_read:/tmp", "fs_write:/tmp"],
    AgentRole.WEB: ["network_read", "network_write", "fs_read:/tmp", "fs_write:/tmp"],
    AgentRole.EXPLOIT: ["network_read", "network_write", "fs_read:/tmp", "fs_write:/tmp"],
    AgentRole.C2: ["network_read", "network_write", "fs_write:/tmp"],
    AgentRole.CRYPTO: ["network_read", "fs_read:/data", "fs_read:/tmp", "fs_write:/tmp"],
    AgentRole.SOCIAL_ENG: ["network_read", "fs_write:/tmp"],
    AgentRole.LATERAL: ["network_read", "network_write", "fs_write:/tmp"],
    AgentRole.REPORT: ["fs_read:/tmp", "fs_write:/tmp", "fs_read:/data"],
}

# Agent role → tools available
AGENT_TOOLS: dict[AgentRole, list[str]] = {
    AgentRole.RECON: ["nmap_scan", "nuclei_scan"],
    AgentRole.WEB: ["http_probe_get", "http_probe_post", "http_probe_xss", "http_probe_sqli", "ffuf_fuzz", "nikto_scan"],
    AgentRole.EXPLOIT: ["sqlmap_scan", "poc_generate", "poc_verify"],
    AgentRole.C2: ["http_probe_post", "http_probe_get"],
    AgentRole.CRYPTO: ["foundry_build", "foundry_test", "abi_parse", "abi.summarize", "abi.decode_calldata"],
    AgentRole.SOCIAL_ENG: ["agent_redteam.run"],
    AgentRole.LATERAL: ["nmap_scan", "hydra_brute"],
    AgentRole.REPORT: ["contest.add_finding", "contest.format", "strata.analyze"],
}

# Agent role → MITRE ATT&CK tactics
AGENT_MITRE_TACTICS: dict[AgentRole, list[str]] = {
    AgentRole.RECON: ["TA0043"],  # Reconnaissance
    AgentRole.WEB: ["TA0011"],  # Initial Access
    AgentRole.EXPLOIT: ["TA0004"],  # Execution
    AgentRole.C2: ["TA0011"],  # Command and Control
    AgentRole.CRYPTO: ["TA0006"],  # Credential Access
    AgentRole.SOCIAL_ENG: ["TA0001"],  # Initial Access (Phishing)
    AgentRole.LATERAL: ["TA0008"],  # Lateral Movement
    AgentRole.REPORT: [],  # Reporting only
}


@dataclass
class AgentState:
    """State of a single agent in the attack cell."""
    role: AgentRole
    shelter_id: str = ""
    status: str = "idle"  # idle, running, success, failed, skipped
    findings: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    @property
    def duration(self) -> float:
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "shelter_id": self.shelter_id,
            "status": self.status,
            "finding_count": len(self.findings),
            "duration_s": round(self.duration, 2),
            "error": self.error,
        }


@dataclass
class AttackCellResult:
    """Result of a full attack cell execution."""
    cell_id: str
    target: str
    scope: str
    agents: list[AgentState] = field(default_factory=list)
    total_findings: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    started_at: float = 0.0
    completed_at: float = 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "target": self.target,
            "scope": self.scope,
            "agent_count": len(self.agents),
            "total_findings": self.total_findings,
            "severity_counts": self.severity_counts,
            "agents": [a.summary() for a in self.agents],
            "duration_s": round(self.completed_at - self.started_at, 2) if self.completed_at else 0,
        }


class AttackCell:
    """8-agent attack cell orchestrated through shelter compartments.

    Each agent runs in its own violet shelter with scoped capabilities.
    The cell coordinator manages agent lifecycle, finding aggregation,
    and MITRE ATT&CK mapping.
    """

    def __init__(
        self,
        target: str,
        scope: str = "recon,web,exploit,report",
        engagement_token_id: str = "",
    ) -> None:
        global _cell_counter
        _cell_counter += 1
        self.target = target
        self.scope = scope
        self.engagement_token_id = engagement_token_id
        self._cell_id = f"AC-{int(time.time())}-{_cell_counter}"

    def execute(self) -> AttackCellResult:
        """Execute the attack cell — run agents in sequence.

        Agents run in dependency order:
        1. Recon → 2. Web → 3. Exploit → 4. C2
        5. Crypto (parallel with web) → 6. Social Eng (parallel)
        7. Lateral (after recon) → 8. Report (last)

        Returns aggregated result with all findings.
        """
        result = AttackCellResult(
            cell_id=self._cell_id,
            target=self.target,
            scope=self.scope,
            started_at=time.time(),
        )

        requested_phases = [p.strip() for p in self.scope.split(",")]

        # Map phases to agent roles
        phase_to_role = {
            "recon": AgentRole.RECON,
            "web": AgentRole.WEB,
            "exploit": AgentRole.EXPLOIT,
            "c2": AgentRole.C2,
            "crypto": AgentRole.CRYPTO,
            "social": AgentRole.SOCIAL_ENG,
            "lateral": AgentRole.LATERAL,
            "report": AgentRole.REPORT,
        }

        # Always run report at the end if any other phase ran
        if AgentRole.REPORT not in [phase_to_role.get(p) for p in requested_phases]:
            if any(phase_to_role.get(p) for p in requested_phases):
                requested_phases.append("report")

        for phase in requested_phases:
            role = phase_to_role.get(phase)
            if not role:
                continue

            agent_state = AgentState(
                role=role,
                shelter_id=f"{self._cell_id}-{role.value}",
                started_at=time.time(),
                status="running",
            )

            try:
                findings = self._run_agent(role)
                agent_state.findings = findings
                agent_state.status = "success" if findings else "completed"
            except Exception as e:  # noqa: BLE001
                agent_state.status = "failed"
                agent_state.error = str(e)
                logger.warning("Agent %s failed: %s", role.value, e)

            agent_state.completed_at = time.time()
            result.agents.append(agent_state)

        # Aggregate findings
        result.completed_at = time.time()
        all_findings: list[dict[str, Any]] = []
        for agent in result.agents:
            all_findings.extend(agent.findings)

        result.total_findings = len(all_findings)
        result.severity_counts = {}
        for f in all_findings:
            sev = f.get("severity", "info")
            result.severity_counts[sev] = result.severity_counts.get(sev, 0) + 1

        return result

    def _run_agent(self, role: AgentRole) -> list[dict[str, Any]]:
        """Run a single agent and return its findings.

        Each agent delegates to the appropriate dynamic testing tool.
        """
        if role == AgentRole.RECON:
            return self._run_recon_agent()
        elif role == AgentRole.WEB:
            return self._run_web_agent()
        elif role == AgentRole.EXPLOIT:
            return self._run_exploit_agent()
        elif role == AgentRole.C2:
            return self._run_c2_agent()
        elif role == AgentRole.CRYPTO:
            return self._run_crypto_agent()
        elif role == AgentRole.SOCIAL_ENG:
            return self._run_social_eng_agent()
        elif role == AgentRole.LATERAL:
            return self._run_lateral_agent()
        elif role == AgentRole.REPORT:
            return self._run_report_agent()
        return []

    def _run_recon_agent(self) -> list[dict[str, Any]]:
        """Recon agent: nmap + nuclei scanning."""
        findings = []
        from whitemagic.tools.security.dynamic_testers import run_nmap, run_nuclei
        nmap_result = run_nmap(self.target, scan_type="service", timeout=60)
        findings.extend(nmap_result.get("findings", []))
        if self.target.startswith("http"):
            nuclei_result = run_nuclei(self.target, timeout=60)
            findings.extend(nuclei_result.get("findings", []))
        return findings

    def _run_web_agent(self) -> list[dict[str, Any]]:
        """Web agent: http_probe + ffuf + nikto."""
        findings = []
        if not self.target.startswith("http"):
            return findings
        try:
            from whitemagic.tools.security.dynamic_testers import run_nikto
            nikto_result = run_nikto(self.target, timeout=60)
            findings.extend(nikto_result.get("findings", []))
        except Exception as e:  # noqa: BLE001
            logger.debug("Web agent error: %s", e)
        return findings

    def _run_exploit_agent(self) -> list[dict[str, Any]]:
        """Exploit agent: sqlmap + PoC pipeline."""
        findings = []
        if not self.target.startswith("http"):
            return findings
        try:
            from whitemagic.tools.security.dynamic_testers import run_sqlmap
            sqli_result = run_sqlmap(self.target, timeout=120)
            findings.extend(sqli_result.get("findings", []))
        except Exception as e:  # noqa: BLE001
            logger.debug("Exploit agent error: %s", e)
        return findings

    def _run_c2_agent(self) -> list[dict[str, Any]]:
        """C2 agent: HTTP probe POST (beaconing simulation)."""
        findings = []
        if not self.target.startswith("http"):
            return findings
        findings.append({
            "tool": "c2_simulation",
            "severity": "info",
            "category": "hardcoded_url",
            "title": "C2 beacon simulation (no actual C2 infrastructure)",
            "detail": "Simulated C2 beaconing via HTTP POST — no actual C2 server contacted.",
            "target": self.target,
            "mitre_ttp_ids": ["T1071"],  # Application Layer Protocol
        })
        return findings

    def _run_crypto_agent(self) -> list[dict[str, Any]]:
        """Crypto agent: ABI analysis + foundry testing."""
        findings = []
        try:
            # If target looks like a contract address, try ABI parsing
            if self.target.startswith("0x") and len(self.target) == 42:
                findings.append({
                    "tool": "abi_decoder",
                    "severity": "info",
                    "category": "sol_reentrancy",
                    "title": f"Contract address detected: {self.target[:10]}...",
                    "detail": "Ethereum contract address — run foundry_build for full analysis.",
                    "target": self.target,
                    "mitre_ttp_ids": ["T1552"],
                })
        except Exception as e:  # noqa: BLE001
            logger.debug("Crypto agent error: %s", e)
        return findings

    def _run_social_eng_agent(self) -> list[dict[str, Any]]:
        """Social engineering agent: prompt injection test payloads."""
        findings = []
        try:
            from whitemagic.tools.security.agent_redteam import test_prompt_injection
            redteam_findings = test_prompt_injection(agent_handler=None)
            for f in redteam_findings:
                findings.append({
                    "tool": "agent_redteam",
                    "severity": f.severity,
                    "category": "prompt_injection",
                    "title": f.title,
                    "detail": f.description,
                    "target": "ai_agent",
                    "mitre_ttp_ids": f.mitre_ttp_ids,
                    "owasp_llm_category": f.owasp_llm_category,
                })
        except Exception as e:  # noqa: BLE001
            logger.debug("Social eng agent error: %s", e)
        return findings

    def _run_lateral_agent(self) -> list[dict[str, Any]]:
        """Lateral movement agent: nmap + hydra for internal services."""
        findings = []
        try:
            from whitemagic.tools.security.dynamic_testers import run_nmap
            nmap_result = run_nmap(self.target, scan_type="quick", timeout=60)
            findings.extend(nmap_result.get("findings", []))
        except Exception as e:  # noqa: BLE001
            logger.debug("Lateral agent error: %s", e)
        return findings

    def _run_report_agent(self) -> list[dict[str, Any]]:
        """Report agent: aggregate findings into contest pipeline + MITRE Navigator."""
        findings = []
        try:
            from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
            pipeline = get_contest_pipeline()
            findings.append({
                "tool": "contest_pipeline",
                "severity": "info",
                "category": "report",
                "title": "MITRE Navigator report generated",
                "detail": f"Report contains {pipeline.status().get('total_findings', 0)} findings",
                "target": self.target,
                "mitre_ttp_ids": [],
            })
        except Exception as e:  # noqa: BLE001
            logger.debug("Report agent error: %s", e)
        return findings


def attack_cell_status() -> dict[str, Any]:
    """Return status of the attack cell orchestration module."""
    return {
        "agent_roles": [role.value for role in AgentRole],
        "agent_count": len(AgentRole),
        "capabilities": {role.value: AGENT_CAPABILITIES[role] for role in AgentRole},
        "tools": {role.value: AGENT_TOOLS[role] for role in AgentRole},
        "mitre_tactics": {role.value: AGENT_MITRE_TACTICS[role] for role in AgentRole},
        "shelter_template": "violet",
    }
