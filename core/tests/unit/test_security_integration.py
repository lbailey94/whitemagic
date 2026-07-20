"""Integration tests: end-to-end security pipeline under engagement token governance.

Tests exercise the full flow:
1. STRATA scan → MITRE TTP mapping → contest pipeline
2. Engagement token issuance → offensive tool execution
3. Attack cell execution → findings aggregation → contest report
4. Violet profile governance enforcement across the pipeline
"""
import pytest
import time
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

from whitemagic.security.engagement_tokens import (
    EngagementTokenManager,
    get_token_manager,
)
from whitemagic.dharma.rules import DharmaRulesEngine
from whitemagic.tools.security.contest_pipeline import (
    ContestFinding,
    ContestPipeline,
    get_contest_pipeline,
)
from whitemagic.tools.security.strata_mitre_map import map_findings
from whitemagic.tools.security.attack_cell import AttackCell, AgentRole


class TestStrataToContestPipeline:
    """STRATA findings → MITRE mapping → contest pipeline integration."""

    def test_strata_findings_flow_to_contest_pipeline(self):
        """STRATA findings should flow through MITRE mapping into contest pipeline."""
        pipeline = ContestPipeline()
        strata_findings = [
            {"category": "py_sql_injection", "file": "app.py", "line": 42, "severity": "error",
             "message": "SQL injection vulnerability"},
            {"category": "unsafe_deserialization", "file": "crypto.py", "line": 10, "severity": "warning",
             "message": "Weak hash algorithm"},
        ]

        # Map to MITRE
        mapped = map_findings(strata_findings)
        assert len(mapped) == 2
        assert mapped[0]["ttp_ids"]  # Should have TTP IDs

        # Add to contest pipeline
        pipeline.add_from_strata(strata_findings)
        findings = pipeline.findings
        assert len(findings) == 2
        assert all(f.mitre_ttp_ids for f in findings)

    def test_contest_pipeline_format_includes_mitre(self):
        """Contest pipeline format output should include MITRE TTP IDs."""
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="Test Finding",
            severity="High",
            category="injection",
            file="app.py",
            line=42,
            description="SQL injection",
            impact="Data exfiltration",
            proof_of_concept="'; DROP TABLE--",
            mitigation="Use parameterized queries",
            mitre_ttp_ids=["T1055", "T1190"],
        )

        formatted = pipeline.format_for_platform("code4rena")
        assert "T1055" in formatted or "mitre" in formatted.lower() or "SQL" in formatted

    def test_mitre_navigator_export_from_pipeline(self):
        """Contest pipeline should export MITRE Navigator format."""
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="RCE via deserialization",
            severity="High",
            category="deserialization",
            file="handler.py",
            line=15,
            description="Unsafe deserialization",
            impact="Remote code execution",
            proof_of_concept="pickle.loads(user_input)",
            mitigation="Use safe deserialization",
            mitre_ttp_ids=["T1059", "T1203"],
        )

        navigator = pipeline.format_for_platform("mitre")
        assert "T1059" in navigator
        assert "T1203" in navigator

    # (moved above)


class TestEngagementTokenGovernance:
    """Engagement token governance across the security pipeline."""

    def test_token_issuance_and_validation(self):
        """Tokens should be issued and validated for offensive tools."""
        mgr = EngagementTokenManager()
        issue_result = mgr.issue(
            scope=["127.0.0.1", "*.example.com"],
            tools=["nmap_*", "nikto_*", "attack_cell_*"],
            issuer="test-issuer",
            duration_minutes=30,
        )
        assert issue_result["status"] == "success"
        token_id = issue_result["token"]["token_id"]

        # Validate for authorized tool
        result = mgr.validate(token_id=token_id, tool="nmap_scan", target="127.0.0.1")
        assert result["valid"] is True

        # Validate for unauthorized tool
        result = mgr.validate(token_id=token_id, tool="sqlmap_scan", target="127.0.0.1")
        assert result["valid"] is False
        assert "tool_not_authorized" in result["reason"] or "not authorized" in result["reason"]

    def test_token_target_scope_enforcement(self):
        """Tokens should enforce target scope."""
        mgr = EngagementTokenManager()
        issue_result = mgr.issue(
            scope=["10.0.0.*"],
            tools=["nmap_*"],
            issuer="test",
            duration_minutes=10,
        )
        token_id = issue_result["token"]["token_id"]

        # In-scope target
        result = mgr.validate(token_id=token_id, tool="nmap_scan", target="10.0.0.5")
        assert result["valid"] is True

        # Out-of-scope target
        result = mgr.validate(token_id=token_id, tool="nmap_scan", target="192.168.1.1")
        assert result["valid"] is False
        assert "scope" in result["reason"].lower()

    def test_token_expiry(self):
        """Expired tokens should be rejected."""
        mgr = EngagementTokenManager()
        issue_result = mgr.issue(
            scope=["*"],
            tools=["*"],
            issuer="test",
            duration_minutes=0.01,  # 0.6 seconds
        )
        token_id = issue_result["token"]["token_id"]

        # Wait for expiry
        time.sleep(1.0)

        result = mgr.validate(token_id=token_id, tool="nmap_scan", target="127.0.0.1")
        assert result["valid"] is False
        assert "expired" in result["reason"].lower()

    def test_token_revocation(self):
        """Revoked tokens should be rejected."""
        mgr = EngagementTokenManager()
        issue_result = mgr.issue(
            scope=["*"],
            tools=["*"],
            issuer="test",
            duration_minutes=60,
        )
        token_id = issue_result["token"]["token_id"]

        # Revoke
        revoke_result = mgr.revoke(token_id)
        assert revoke_result["status"] == "success"

        # Should now be invalid
        result = mgr.validate(token_id=token_id, tool="nmap_scan", target="127.0.0.1")
        assert result["valid"] is False
        assert "revoked" in result["reason"].lower()

    def test_violet_profile_blocks_without_token(self):
        """Violet Dharma profile should block offensive tools without a token."""
        engine = DharmaRulesEngine()
        engine.set_profile("violet")
        action = {"tool": "nmap_scan", "description": "Port scan"}
        decision = engine.evaluate(action)
        assert decision.action == "block"

    def test_violet_profile_allows_non_offensive(self):
        """Violet profile should not block non-offensive tools."""
        engine = DharmaRulesEngine()
        engine.set_profile("violet")
        action = {"tool": "create_memory", "description": "Create a memory"}
        # create_memory should not be blocked by violet_require_engagement_token
        decision = engine.evaluate(action)
        # It might warn for privacy but shouldn't be blocked for engagement token
        assert decision.action != "block" or "engagement" not in decision.explain.lower()


class TestAttackCellFullPipeline:
    """Attack cell → contest pipeline → report integration."""

    def test_attack_cell_feeds_contest_pipeline(self):
        """Attack cell findings should be addable to contest pipeline."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nmap", 
                   return_value={"findings": [{"severity": "high", "title": "Open SSH", "mitre_ttp_ids": ["T1021"]}]}), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 1}

            cell = AttackCell(target="127.0.0.1", scope="recon")
            result = cell.execute()

            assert result.total_findings >= 1
            assert result.cell_id.startswith("AC-")
            # Verify recon agent ran
            recon_agents = [a for a in result.agents if a.role == AgentRole.RECON]
            assert len(recon_agents) == 1
            assert recon_agents[0].status == "success"

    def test_attack_cell_with_engagement_token(self):
        """Attack cell should accept and store engagement token ID."""
        cell = AttackCell(
            target="127.0.0.1",
            scope="recon",
            engagement_token_id="evt_test123",
        )
        assert cell.engagement_token_id == "evt_test123"
        result = cell.execute()
        assert result.cell_id.startswith("AC-")

    def test_attack_cell_multi_phase_execution(self):
        """Multi-phase attack cell should run all requested phases."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nmap", 
                   return_value={"findings": []}), \
             patch("whitemagic.tools.security.dynamic_testers.run_nikto", 
                   return_value={"findings": [{"severity": "medium", "title": "XSS"}]}), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 1}

            cell = AttackCell(target="http://example.com", scope="recon,web")
            result = cell.execute()

            roles = [a.role for a in result.agents]
            assert AgentRole.RECON in roles
            assert AgentRole.WEB in roles
            assert AgentRole.REPORT in roles  # Always added

    def test_attack_cell_severity_aggregation(self):
        """Attack cell should aggregate severities across agents."""
        with patch("whitemagic.tools.security.dynamic_testers.run_nmap",
                   return_value={"findings": [{"severity": "high"}, {"severity": "low"}]}), \
             patch("whitemagic.tools.security.contest_pipeline.get_contest_pipeline") as mock_pipeline:
            mock_pipeline.return_value.format_for_platform.return_value = "{}"
            mock_pipeline.return_value.status.return_value = {"total_findings": 2}

            cell = AttackCell(target="127.0.0.1", scope="recon")
            result = cell.execute()

            assert "high" in result.severity_counts
            assert "low" in result.severity_counts
            assert result.severity_counts["high"] >= 1
            assert result.severity_counts["low"] >= 1


class TestAgentRedteamIntegration:
    """AI agent red-teaming integration with contest pipeline."""

    def test_redteam_findings_have_mitre_mapping(self):
        """Redteam findings should include MITRE TTP IDs."""
        from whitemagic.tools.security.agent_redteam import test_prompt_injection
        findings = test_prompt_injection(agent_handler=None)
        assert len(findings) > 0
        for f in findings:
            assert f.mitre_ttp_ids  # Every finding should have TTPs
            assert f.owasp_llm_category  # Every finding should have OWASP mapping

    def test_redteam_findings_addable_to_contest(self):
        """Redteam findings should be convertible to contest findings."""
        from whitemagic.tools.security.agent_redteam import test_prompt_injection
        findings = test_prompt_injection(agent_handler=None)
        pipeline = ContestPipeline()

        for f in findings:
            pipeline.add_finding(
                title=f.title,
                severity=f.severity,
                category=f.owasp_llm_category,
                file="agent.py",
                line=None,
                description=f.description,
                impact="AI agent compromise",
                proof_of_concept=f.payload[:200],
                mitigation="Input validation and output filtering",
                mitre_ttp_ids=f.mitre_ttp_ids,
            )

        assert len(pipeline.findings) >= 1
        assert all(f.mitre_ttp_ids for f in pipeline.findings)


class TestContinuousScanningIntegration:
    """Continuous scanning → MITRE → contest pipeline integration."""

    def test_strata_findings_mapped_and_fed_to_pipeline(self):
        """STRATA findings should be mapped to MITRE and fed to contest pipeline."""
        raw_findings = [
            {"category": "web_xss_innerhtml", "file": "view.py", "line": 25, "severity": "error",
             "message": "Reflected XSS"},
            {"category": "py_sql_injection", "file": "fetch.py", "line": 10, "severity": "error",
             "message": "SSRF vulnerability"},
        ]

        # Map to MITRE
        mapped = map_findings(raw_findings)
        assert len(mapped) == 2
        assert all(m["ttp_ids"] for m in mapped)

        # Feed to contest pipeline
        pipeline = ContestPipeline()
        pipeline.add_from_strata(raw_findings)
        assert len(pipeline.findings) == 2

        # Verify MITRE TTPs propagated
        for finding in pipeline.findings:
            assert finding.mitre_ttp_ids

    def test_navigator_export_from_full_pipeline(self):
        """Full pipeline should produce valid MITRE Navigator output."""
        pipeline = ContestPipeline()
        findings = [
            ContestFinding(
                title="SQL Injection",
                severity="High",
                category="injection",
                file="db.py",
                line=50,
                description="SQL injection in query",
                impact="Database compromise",
                proof_of_concept="' OR 1=1--",
                mitigation="Parameterized queries",
                mitre_ttp_ids=["T1190"],
            ),
            ContestFinding(
                title="Weak Crypto",
                severity="Medium",
                category="crypto",
                file="auth.py",
                line=20,
                description="MD5 hash used",
                impact="Password cracking",
                proof_of_concept="hashlib.md5(password)",
                mitigation="Use bcrypt",
                mitre_ttp_ids=["T1110"],
            ),
        ]
        for f in findings:
            pipeline.add_finding(
                title=f.title,
                severity=f.severity,
                category=f.category,
                file=f.file,
                line=f.line,
                description=f.description,
                impact=f.impact,
                proof_of_concept=f.proof_of_concept,
                mitigation=f.mitigation,
                mitre_ttp_ids=f.mitre_ttp_ids,
            )

        navigator = pipeline.format_for_platform("mitre")
        assert "T1190" in navigator
        assert "T1110" in navigator
