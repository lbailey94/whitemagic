"""Tests for multi-agent attack orchestration (Gap 3)."""
import pytest
from unittest.mock import patch, MagicMock

from whitemagic.tools.security.attack_cell import (
    AgentRole,
    AgentState,
    AttackCell,
    AttackCellResult,
    AGENT_CAPABILITIES,
    AGENT_TOOLS,
    AGENT_MITRE_TACTICS,
    attack_cell_status,
)


class TestAgentRole:
    """Test AgentRole enum."""

    def test_eight_roles_defined(self):
        """Should have exactly 8 agent roles."""
        assert len(list(AgentRole)) == 8

    def test_role_values(self):
        """Role values should match expected strings."""
        assert AgentRole.RECON.value == "recon"
        assert AgentRole.WEB.value == "web"
        assert AgentRole.EXPLOIT.value == "exploit"
        assert AgentRole.C2.value == "c2"
        assert AgentRole.CRYPTO.value == "crypto"
        assert AgentRole.SOCIAL_ENG.value == "social_eng"
        assert AgentRole.LATERAL.value == "lateral"
        assert AgentRole.REPORT.value == "report"


class TestAgentCapabilities:
    """Test agent capability mappings."""

    def test_all_roles_have_capabilities(self):
        """Every role should have capabilities defined."""
        for role in AgentRole:
            assert role in AGENT_CAPABILITIES
            assert len(AGENT_CAPABILITIES[role]) > 0

    def test_recon_has_network_read(self):
        assert "network_read" in AGENT_CAPABILITIES[AgentRole.RECON]

    def test_web_has_network_write(self):
        assert "network_write" in AGENT_CAPABILITIES[AgentRole.WEB]

    def test_report_has_no_network(self):
        """Report agent should not have network capabilities."""
        caps = AGENT_CAPABILITIES[AgentRole.REPORT]
        assert not any(c.startswith("network") for c in caps)


class TestAgentTools:
    """Test agent tool mappings."""

    def test_all_roles_have_tools(self):
        for role in AgentRole:
            assert role in AGENT_TOOLS

    def test_recon_has_nmap(self):
        assert "nmap_scan" in AGENT_TOOLS[AgentRole.RECON]

    def test_web_has_http_probe(self):
        assert "http_probe_get" in AGENT_TOOLS[AgentRole.WEB]

    def test_report_has_contest_tools(self):
        assert "contest.format" in AGENT_TOOLS[AgentRole.REPORT]


class TestAgentMitreTactics:
    """Test MITRE tactic mappings."""

    def test_recon_maps_to_reconnaissance(self):
        assert "TA0043" in AGENT_MITRE_TACTICS[AgentRole.RECON]

    def test_lateral_maps_to_lateral_movement(self):
        assert "TA0008" in AGENT_MITRE_TACTICS[AgentRole.LATERAL]

    def test_report_has_no_tactics(self):
        assert AGENT_MITRE_TACTICS[AgentRole.REPORT] == []


class TestAgentState:
    """Test AgentState dataclass."""

    def test_defaults(self):
        state = AgentState(role=AgentRole.RECON)
        assert state.status == "idle"
        assert state.findings == []
        assert state.shelter_id == ""
        assert state.error == ""

    def test_duration(self):
        state = AgentState(
            role=AgentRole.WEB,
            started_at=1000.0,
            completed_at=1005.5,
        )
        assert state.duration == 5.5

    def test_summary(self):
        state = AgentState(
            role=AgentRole.EXPLOIT,
            shelter_id="AC-123-exploit",
            status="success",
            findings=[{"severity": "high"}],
            started_at=1000.0,
            completed_at=1002.0,
        )
        s = state.summary()
        assert s["role"] == "exploit"
        assert s["status"] == "success"
        assert s["finding_count"] == 1
        assert s["duration_s"] == 2.0


class TestAttackCell:
    """Test AttackCell execution."""

    def test_execute_recon_only(self):
        """Recon-only scope should run recon + report agents."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nmap", return_value={"findings": []}), \
             patch("whitemagic.tools.security.dynamic_testers.run_nuclei", return_value={"findings": []}), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 0}

            cell = AttackCell(target="127.0.0.1", scope="recon")
            result = cell.execute()

            assert result.cell_id.startswith("AC-")
            assert len(result.agents) == 2  # recon + report
            assert result.agents[0].role == AgentRole.RECON
            assert result.agents[1].role == AgentRole.REPORT

    def test_execute_web_agent(self):
        """Web agent should run against HTTP targets."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nikto", return_value={"findings": [{"severity": "high", "title": "XSS"}]}), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 1}

            cell = AttackCell(target="http://example.com", scope="web")
            result = cell.execute()

            assert len(result.agents) >= 2  # web + report
            web_agent = [a for a in result.agents if a.role == AgentRole.WEB][0]
            assert web_agent.status == "success"
            assert len(web_agent.findings) == 1

    def test_execute_skips_non_http_for_web(self):
        """Web agent should produce no findings for non-HTTP targets."""
        cell = AttackCell(target="127.0.0.1", scope="web")
        result = cell.execute()
        web_agent = [a for a in result.agents if a.role == AgentRole.WEB][0]
        assert web_agent.status == "completed"
        assert len(web_agent.findings) == 0

    def test_execute_c2_simulation(self):
        """C2 agent should produce a simulation finding."""
        cell = AttackCell(target="http://example.com", scope="c2")
        result = cell.execute()
        c2_agent = [a for a in result.agents if a.role == AgentRole.C2][0]
        assert c2_agent.status == "success"
        assert len(c2_agent.findings) == 1
        assert "T1071" in c2_agent.findings[0]["mitre_ttp_ids"]

    def test_execute_crypto_agent_contract(self):
        """Crypto agent should detect contract addresses."""
        cell = AttackCell(target="0x1234567890abcdef1234567890abcdef12345678", scope="crypto")
        result = cell.execute()
        crypto_agent = [a for a in result.agents if a.role == AgentRole.CRYPTO][0]
        assert len(crypto_agent.findings) == 1
        assert "T1552" in crypto_agent.findings[0]["mitre_ttp_ids"]

    def test_execute_social_eng_agent(self):
        """Social eng agent should return prompt injection payloads."""
        cell = AttackCell(target="ai_agent", scope="social")
        result = cell.execute()
        social_agent = [a for a in result.agents if a.role == AgentRole.SOCIAL_ENG][0]
        assert social_agent.status == "success"
        assert len(social_agent.findings) > 0

    def test_execute_report_always_added(self):
        """Report agent should always be added when other phases run."""
        cell = AttackCell(target="127.0.0.1", scope="recon")
        result = cell.execute()
        roles = [a.role for a in result.agents]
        assert AgentRole.REPORT in roles

    def test_execute_aggregates_findings(self):
        """Result should aggregate all agent findings."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nmap", return_value={"findings": [{"severity": "high"}, {"severity": "medium"}]}), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 2}

            cell = AttackCell(target="127.0.0.1", scope="recon")
            result = cell.execute()

            # Recon findings + report finding
            assert result.total_findings >= 2
            assert "high" in result.severity_counts

    def test_execute_handles_agent_failure(self):
        """Cell should continue even if an agent fails."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nmap", side_effect=Exception("Network error")), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 0}

            cell = AttackCell(target="127.0.0.1", scope="recon")
            result = cell.execute()

            recon_agent = [a for a in result.agents if a.role == AgentRole.RECON][0]
            assert recon_agent.status == "failed"
            assert "Network error" in recon_agent.error

    def test_cell_id_is_unique(self):
        """Each cell should have a unique ID."""
        cell1 = AttackCell(target="127.0.0.1")
        cell2 = AttackCell(target="127.0.0.1")
        assert cell1._cell_id != cell2._cell_id


class TestAttackCellStatus:
    """Test status reporting."""

    def test_status_returns_all_roles(self):
        status = attack_cell_status()
        assert len(status["agent_roles"]) == 8
        assert "recon" in status["agent_roles"]

    def test_status_returns_capabilities(self):
        status = attack_cell_status()
        assert "recon" in status["capabilities"]
        assert "network_read" in status["capabilities"]["recon"]

    def test_status_returns_tools(self):
        status = attack_cell_status()
        assert "recon" in status["tools"]
        assert "nmap_scan" in status["tools"]["recon"]

    def test_status_returns_mitre_tactics(self):
        status = attack_cell_status()
        assert "recon" in status["mitre_tactics"]
        assert "TA0043" in status["mitre_tactics"]["recon"]

    def test_status_returns_shelter_template(self):
        status = attack_cell_status()
        assert status["shelter_template"] == "violet"


class TestAttackCellResult:
    """Test AttackCellResult dataclass."""

    def test_summary(self):
        result = AttackCellResult(
            cell_id="AC-123",
            target="http://example.com",
            scope="recon,web",
            total_findings=5,
            severity_counts={"high": 2, "medium": 3},
            started_at=1000.0,
            completed_at=1010.0,
        )
        s = result.summary()
        assert s["cell_id"] == "AC-123"
        assert s["total_findings"] == 5
        assert s["severity_counts"]["high"] == 2
        assert s["duration_s"] == 10.0
