"""Multi-agent security analysis swarm — coordinate multiple specialized agents."""
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    SOLIDITY_AUDITOR = "solidity_auditor"
    PYTHON_AUDITOR = "python_auditor"
    WEB_AUDITOR = "web_auditor"
    EXPLOIT_DEVELOPER = "exploit_developer"
    REPORT_WRITER = "report_writer"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentResult:
    agent_id: str
    role: AgentRole
    findings: list[dict[str, Any]]
    elapsed_s: float
    coverage: float = 0.0
    confidence: float = 0.0


@dataclass
class SwarmConfig:
    max_agents: int = 5
    timeout_per_agent: int = 60
    overlap_tolerance: float = 0.3
    min_confidence: float = 0.5


class SecuritySwarm:
    """Coordinate multiple specialized security analysis agents."""

    def __init__(self, config: SwarmConfig | None = None) -> None:
        self._config = config or SwarmConfig()
        self._agents: dict[str, AgentRole] = {}
        self._results: list[AgentResult] = []

    def register_agent(self, agent_id: str, role: AgentRole) -> None:
        if len(self._agents) >= self._config.max_agents:
            logger.warning("Max agents reached, cannot register %s", agent_id)
        self._agents[agent_id] = role

    def run_analysis(
        self,
        project_path: str,
        file_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run multi-agent analysis on a project."""
        start = time.time()
        from pathlib import Path
        project = Path(project_path)

        # Determine which agents to deploy based on file types
        if file_types is None:
            file_types = self._detect_file_types(project)
        agents_to_run = self._select_agents(file_types)
        all_findings: list[dict[str, Any]] = []

        for agent_id, role in agents_to_run.items():
            agent_start = time.time()
            findings = self._run_agent(agent_id, role, project, file_types)
            elapsed = time.time() - agent_start
            result = AgentResult(
                agent_id=agent_id,
                role=role,
                findings=findings,
                elapsed_s=elapsed,
                coverage=len(findings) / max(1, len(list(project.rglob("*")))),
                confidence=0.7,
            )
            self._results.append(result)
            all_findings.extend(findings)

        # Deduplicate and merge
        merged = self._merge_findings(all_findings)
        consensus = self._find_consensus(all_findings)

        return {
            "total_findings": len(merged),
            "agents_run": len(agents_to_run),
            "agent_results": [
                {
                    "agent_id": r.agent_id,
                    "role": r.role.value,
                    "findings": len(r.findings),
                    "elapsed_s": r.elapsed_s,
                    "coverage": r.coverage,
                }
                for r in self._results
            ],
            "consensus_findings": consensus,
            "merged_findings": merged[:20],
            "total_elapsed_s": time.time() - start,
        }

    def _detect_file_types(self, project: Path) -> list[str]:
        extensions = set()
        for f in project.rglob("*"):
            if f.is_file() and f.suffix:
                extensions.add(f.suffix)
        return list(extensions)

    def _select_agents(self, file_types: list[str]) -> dict[str, AgentRole]:
        agents: dict[str, AgentRole] = {}
        if any(ft in file_types for ft in [".sol"]):
            agents["solidity-1"] = AgentRole.SOLIDITY_AUDITOR
        if any(ft in file_types for ft in [".py"]):
            agents["python-1"] = AgentRole.PYTHON_AUDITOR
        if any(ft in file_types for ft in [".js", ".ts", ".jsx", ".tsx", ".html"]):
            agents["web-1"] = AgentRole.WEB_AUDITOR
        agents["exploit-1"] = AgentRole.EXPLOIT_DEVELOPER
        agents["report-1"] = AgentRole.REPORT_WRITER
        return agents

    def _run_agent(
        self,
        agent_id: str,
        role: AgentRole,
        project: Path,
        file_types: list[str],
    ) -> list[dict[str, Any]]:
        """Run a single agent's analysis."""
        from whitemagic.tools.strata.checkers import get_checkers

        findings: list[dict[str, Any]] = []
        checkers = get_checkers()

        if role == AgentRole.SOLIDITY_AUDITOR:
            from whitemagic.tools.strata.checkers.solidity import FileIndex
            fi = FileIndex(project)
            for checker in checkers:
                if "solidity" in checker.__name__ or "security" in checker.__name__:
                    try:
                        checker_findings: list[Any] = []
                        checker(project, fi, checker_findings)
                        for f in checker_findings:
                            findings.append({
                                "category": f.category,
                                "file": f.file,
                                "line": f.line,
                                "message": f.message,
                                "severity": f.severity.value,
                                "agent": agent_id,
                            })
                    except Exception as e:
                        logger.debug("Checker %s failed: %s", checker.__name__, e)

        elif role == AgentRole.PYTHON_AUDITOR:
            for checker in checkers:
                if "python" in checker.__name__:
                    try:
                        from whitemagic.tools.strata.checkers.solidity import FileIndex
                        fi = FileIndex(project)
                        checker_findings: list[Any] = []
                        checker(project, fi, checker_findings)
                        for f in checker_findings:
                            findings.append({
                                "category": f.category,
                                "file": f.file,
                                "line": f.line,
                                "message": f.message,
                                "severity": f.severity.value,
                                "agent": agent_id,
                            })
                    except Exception:
                        pass

        elif role == AgentRole.WEB_AUDITOR:
            for checker in checkers:
                if "web" in checker.__name__:
                    try:
                        from whitemagic.tools.strata.checkers.solidity import FileIndex
                        fi = FileIndex(project)
                        checker_findings: list[Any] = []
                        checker(project, fi, checker_findings)
                        for f in checker_findings:
                            findings.append({
                                "category": f.category,
                                "file": f.file,
                                "line": f.line,
                                "message": f.message,
                                "severity": f.severity.value,
                                "agent": agent_id,
                            })
                    except Exception:
                        pass

        return findings

    def _merge_findings(self, all_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge and deduplicate findings from multiple agents."""
        seen: dict[str, dict[str, Any]] = {}
        for f in all_findings:
            key = f"{f.get('file', '')}:{f.get('line', 0)}:{f.get('category', '')}"
            if key in seen:
                seen[key]["agents"] = seen[key].get("agents", []) + [f.get("agent", "")]
                seen[key]["confidence"] = min(1.0, seen[key].get("confidence", 0.5) + 0.2)
            else:
                f["agents"] = [f.get("agent", "")]
                f["confidence"] = 0.5
                seen[key] = f
        return list(seen.values())

    def _find_consensus(self, all_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find findings reported by multiple agents (high confidence)."""
        merged = self._merge_findings(all_findings)
        return [f for f in merged if len(f.get("agents", [])) >= 2]

    def status(self) -> dict[str, Any]:
        return {
            "registered_agents": len(self._agents),
            "max_agents": self._config.max_agents,
            "results_count": len(self._results),
        }


_swarm: SecuritySwarm | None = None


def get_security_swarm() -> SecuritySwarm:
    global _swarm
    if _swarm is None:
        _swarm = SecuritySwarm()
    return _swarm
