"""Tests for Phase 7 advanced security capabilities."""
from pathlib import Path


class TestVulnerabilityGraph:
    def test_graph_init(self):
        from whitemagic.tools.security.vuln_graph import VulnerabilityGraph
        g = VulnerabilityGraph()
        assert g.status()["nodes"] == 0

    def test_add_nodes_and_edges(self):
        from whitemagic.tools.security.vuln_graph import (
            GraphEdge,
            GraphNode,
            VulnerabilityGraph,
        )
        g = VulnerabilityGraph()
        g.add_node(GraphNode("v1", "vulnerability", "Reentrancy"))
        g.add_node(GraphNode("e1", "exploit", "Drain funds"))
        g.add_edge(GraphEdge("v1", "e1", "enables", 0.9))
        assert g.status()["nodes"] == 2
        assert g.status()["edges"] == 1

    def test_find_exploit_chains(self):
        from whitemagic.tools.security.vuln_graph import (
            GraphEdge,
            GraphNode,
            VulnerabilityGraph,
        )
        g = VulnerabilityGraph()
        g.add_node(GraphNode("v1", "vulnerability", "V1"))
        g.add_node(GraphNode("v2", "vulnerability", "V2"))
        g.add_node(GraphNode("e1", "exploit", "E1"))
        g.add_edge(GraphEdge("v1", "v2", "leads_to"))
        g.add_edge(GraphEdge("v2", "e1", "enables"))
        chains = g.find_exploit_chains("v1", max_depth=5)
        assert len(chains) > 0
        assert chains[0][0] == "v1"

    def test_predict_severity(self):
        from whitemagic.tools.security.vuln_graph import (
            GraphEdge,
            GraphNode,
            VulnerabilityGraph,
        )
        g = VulnerabilityGraph()
        g.add_node(GraphNode("v1", "vulnerability", "V1"))
        g.add_edge(GraphEdge("v1", "e1", "enables", 0.9))
        assert g.predict_severity("v1") == "critical"

    def test_cross_chain_analysis(self):
        from whitemagic.tools.security.vuln_graph import get_vuln_graph
        g = get_vuln_graph()
        result = g.cross_chain_analysis([
            {"chain_id": "ethereum", "vulnerabilities": [{"category": "reentrancy", "name": "Reentrancy"}]},
            {"chain_id": "polygon", "vulnerabilities": [{"category": "reentrancy", "name": "Reentrancy"}]},
        ])
        assert result["chains_analyzed"] == 2
        assert result["cross_chain_links"] > 0


class TestFormalVerifier:
    def test_status(self):
        from whitemagic.tools.security.formal_verifier import FormalVerifier
        fv = FormalVerifier()
        status = fv.status()
        assert "available_solvers" in status
        assert "timeout" in status

    def test_generate_spec(self, tmp_path):
        from whitemagic.tools.security.formal_verifier import FormalVerifier
        fv = FormalVerifier()
        spec_path = fv.generate_spec("MyToken", ["balance invariant", "access control"], str(tmp_path))
        assert Path(spec_path).exists()
        content = Path(spec_path).read_text()
        assert "MyToken" in content
        assert "balance_invariant" in content


class TestSecuritySwarm:
    def test_swarm_init(self):
        from whitemagic.tools.security.multi_agent import SecuritySwarm
        s = SecuritySwarm()
        assert s.status()["registered_agents"] == 0

    def test_register_agent(self):
        from whitemagic.tools.security.multi_agent import AgentRole, SecuritySwarm
        s = SecuritySwarm()
        s.register_agent("test-1", AgentRole.SOLIDITY_AUDITOR)
        assert s.status()["registered_agents"] == 1

    def test_run_analysis_empty(self, tmp_path):
        from whitemagic.tools.security.multi_agent import SecuritySwarm
        s = SecuritySwarm()
        result = s.run_analysis(str(tmp_path))
        assert "total_findings" in result
        assert "agents_run" in result


class TestPredictiveScorer:
    def test_score_safe_contract(self):
        from whitemagic.tools.security.predictive_scoring import PredictiveScorer
        s = PredictiveScorer()
        result = s.score_contract("test.sol", "Safe", "pragma solidity ^0.8.20;\ncontract Safe {\n    uint256 public x;\n    function setX(uint256 _x) public {\n        x = _x;\n    }\n}\n")
        assert result.risk_score < 0.5
        assert result.confidence > 0.5

    def test_score_dangerous_contract(self):
        from whitemagic.tools.security.predictive_scoring import PredictiveScorer
        s = PredictiveScorer()
        content = (
            "pragma solidity ^0.7.0;\n"
            "contract Dangerous {\n"
            "    mapping(address => uint256) public balances;\n"
            "    function withdraw() public {\n"
            "        (bool ok,) = msg.sender.call{value: balances[msg.sender]}('');\n"
            "        balances[msg.sender] = 0;\n"
            "    }\n"
            "    function destroy() public {\n"
            "        selfdestruct(payable(msg.sender));\n"
            "    }\n"
            "}\n"
        )
        result = s.score_contract("test.sol", "Dangerous", content)
        assert result.risk_score > 0.3
        assert any(p["vulnerability"] == "unprotected_selfdestruct" for p in result.predicted_vulnerabilities)

    def test_batch_score(self):
        from whitemagic.tools.security.predictive_scoring import PredictiveScorer
        s = PredictiveScorer()
        results = s.batch_score([
            {"file": "a.sol", "name": "A", "content": "pragma solidity ^0.8.20;\ncontract A {}\n"},
            {"file": "b.sol", "name": "B", "content": "contract B { function f() public { selfdestruct(payable(msg.sender)); } }\n"},
        ])
        assert len(results) == 2
        assert results[0].risk_score >= results[1].risk_score  # sorted descending


class TestAuditReport:
    def test_generate_standard(self):
        from whitemagic.tools.security.audit_report import AuditReportGenerator
        gen = AuditReportGenerator()
        report = gen.generate(
            "TestProject",
            [{"severity": "high", "title": "Reentrancy", "file": "Vuln.sol", "line": 10, "category": "reentrancy", "description": "Reentrancy in withdraw", "impact": "Funds drained", "mitigation": "Use ReentrancyGuard"}],
        )
        assert "TestProject" in report.title
        assert "Reentrancy" in report.raw_markdown
        assert "High" in report.raw_markdown

    def test_generate_executive(self):
        from whitemagic.tools.security.audit_report import AuditReportGenerator
        gen = AuditReportGenerator()
        report = gen.generate("TestProject", [{"severity": "critical", "title": "Critical bug"}], format_type="executive")
        assert "Executive" in report.raw_markdown or "executive" in report.raw_markdown.lower()
        assert "critical" in report.executive_summary.lower()

    def test_generate_no_findings(self):
        from whitemagic.tools.security.audit_report import AuditReportGenerator
        gen = AuditReportGenerator()
        report = gen.generate("SafeProject", [])
        assert "no security issues" in report.executive_summary.lower()


class TestSecurityMonitor:
    def test_monitor_init(self):
        from whitemagic.tools.security.monitor import SecurityMonitor
        m = SecurityMonitor()
        assert m.status()["total_alerts"] == 0

    def test_add_alert(self):
        from whitemagic.tools.security.monitor import SecurityMonitor
        m = SecurityMonitor()
        alert = m.add_alert("high", "test", "Test alert")
        assert alert.severity == "high"
        assert m.status()["total_alerts"] == 1
        assert m.status()["high_alerts"] == 1

    def test_get_alerts_filtered(self):
        from whitemagic.tools.security.monitor import SecurityMonitor
        m = SecurityMonitor()
        m.add_alert("critical", "test", "Critical alert")
        m.add_alert("low", "test", "Low alert")
        critical = m.get_alerts(severity="critical")
        assert len(critical) == 1
        assert critical[0].severity == "critical"

    def test_register_callback(self):
        from whitemagic.tools.security.monitor import SecurityMonitor
        m = SecurityMonitor()
        received = []
        m.register_callback(lambda a: received.append(a))
        m.add_alert("high", "test", "Test")
        assert len(received) == 1

    def test_monitor_contract(self):
        from whitemagic.tools.security.monitor import SecurityMonitor
        m = SecurityMonitor()
        result = m.monitor_contract("0x1234", 1)
        assert result["address"] == "0x1234"
        assert result["monitoring"] is True


class TestPhase7MCPWiring:
    def test_phase7_tools_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        tools = [
            "vuln_graph.status", "vuln_graph.chains", "vuln_graph.cross_chain",
            "formal.verify", "formal.status",
            "swarm.analyze", "swarm.status",
            "predictive.score", "predictive.batch",
            "audit.report",
            "monitor.status", "monitor.alerts", "monitor.contract",
        ]
        for t in tools:
            assert t in DISPATCH_TABLE, f"{t} not in DISPATCH_TABLE"

    def test_phase7_tools_in_prat(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        tools = [
            "vuln_graph.status", "vuln_graph.chains", "vuln_graph.cross_chain",
            "formal.verify", "formal.status",
            "swarm.analyze", "swarm.status",
            "predictive.score", "predictive.batch",
            "audit.report",
            "monitor.status", "monitor.alerts", "monitor.contract",
        ]
        for t in tools:
            assert t in TOOL_TO_GANA, f"{t} not in TOOL_TO_GANA"

    def test_phase7_registry_defs(self):
        from whitemagic.tools.registry_defs import collect
        tools = collect()
        sec_names = {t.name for t in tools if t.category.value == "security"}
        assert "vuln_graph.status" in sec_names
        assert "formal.verify" in sec_names
        assert "swarm.analyze" in sec_names
        assert "predictive.score" in sec_names
        assert "audit.report" in sec_names
        assert "monitor.status" in sec_names
