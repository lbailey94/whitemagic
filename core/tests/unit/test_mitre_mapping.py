"""Tests for STRATA → MITRE ATT&CK mapping (Gap 4)."""
import json
import pytest

from whitemagic.tools.security.strata_mitre_map import (
    get_mapping,
    get_ttps_for_category,
    get_ttp_ids_for_category,
    map_findings,
    generate_navigator_layer,
    navigator_layer_json,
    all_mapped_categories,
    mapping_stats,
    TTPMapping,
    CategoryMapping,
)
from whitemagic.tools.security.contest_pipeline import ContestPipeline, ContestFinding


class TestStrataMitreMapping:
    """Test the STRATA → MITRE ATT&CK mapping table."""

    def test_sql_injection_maps_to_t1190(self):
        """SQL injection should map to T1190 (Exploit Public-Facing Application)."""
        ttps = get_ttps_for_category("py_sql_injection")
        ids = [t.technique_id for t in ttps]
        assert "T1190" in ids

    def test_command_injection_maps_to_t1059(self):
        """Command injection should map to T1059 (Command and Scripting Interpreter)."""
        ttps = get_ttps_for_category("py_command_injection")
        ids = [t.technique_id for t in ttps]
        assert "T1059" in ids

    def test_hardcoded_secret_maps_to_t1552(self):
        """Hardcoded secrets should map to T1552 (Unsecured Credentials)."""
        ttps = get_ttps_for_category("hardcoded_secret")
        ids = [t.technique_id for t in ttps]
        assert "T1552" in ids

    def test_path_traversal_maps_to_t1005(self):
        """Path traversal should map to T1005 (Data from Local System)."""
        ttps = get_ttps_for_category("py_path_traversal")
        ids = [t.technique_id for t in ttps]
        assert "T1005" in ids

    def test_unsafe_deserialization_maps_to_t1203(self):
        """Unsafe deserialization should map to T1203 (Exploitation for Client Execution)."""
        ttps = get_ttps_for_category("unsafe_deserialization")
        ids = [t.technique_id for t in ttps]
        assert "T1203" in ids

    def test_pickle_reduce_exploit_maps_to_t1203(self):
        """Pickle __reduce__ exploit should map to T1203."""
        ttps = get_ttps_for_category("pickle_reduce_exploit")
        ids = [t.technique_id for t in ttps]
        assert "T1203" in ids

    def test_hf_trust_remote_code_maps_to_t1203(self):
        """HuggingFace trust_remote_code should map to T1203."""
        ttps = get_ttps_for_category("hf_trust_remote_code")
        ids = [t.technique_id for t in ttps]
        assert "T1203" in ids

    def test_sol_reentrancy_maps_to_t1190(self):
        """Solidity reentrancy should map to T1190."""
        ttps = get_ttps_for_category("sol_reentrancy_risk")
        ids = [t.technique_id for t in ttps]
        assert "T1190" in ids

    def test_sol_delegatecall_maps_to_t1548(self):
        """Solidity delegatecall to user should map to T1548 (Privilege Escalation)."""
        ttps = get_ttps_for_category("sol_delegatecall_user")
        ids = [t.technique_id for t in ttps]
        assert "T1548" in ids

    def test_unmapped_category_returns_empty(self):
        """Non-security categories should return empty TTP list."""
        assert get_ttps_for_category("dead_code") == []
        assert get_ttps_for_category("print_debug") == []
        assert get_ttps_for_category("narrative_comment") == []
        assert get_ttps_for_category("nonexistent_category") == []

    def test_get_ttp_ids_returns_strings(self):
        """get_ttp_ids_for_category should return list of strings."""
        ids = get_ttp_ids_for_category("py_sql_injection")
        assert isinstance(ids, list)
        assert all(isinstance(i, str) for i in ids)

    def test_get_mapping_returns_category_mapping(self):
        """get_mapping should return a CategoryMapping object."""
        mapping = get_mapping("py_sql_injection")
        assert mapping is not None
        assert isinstance(mapping, CategoryMapping)
        assert mapping.strata_category == "py_sql_injection"
        assert len(mapping.ttps) > 0
        assert mapping.notes

    def test_all_mapped_categories_returns_sorted_list(self):
        """all_mapped_categories should return a sorted list of category strings."""
        cats = all_mapped_categories()
        assert isinstance(cats, list)
        assert cats == sorted(cats)
        assert "py_sql_injection" in cats
        assert "dead_code" not in cats

    def test_mapping_stats(self):
        """mapping_stats should return summary statistics."""
        stats = mapping_stats()
        assert stats["mapped_categories"] > 30
        assert stats["total_ttp_mappings"] > stats["mapped_categories"]
        assert "Initial Access" in stats["tactics"]
        assert "Execution" in stats["tactics"]
        assert "Credential Access" in stats["tactics"]


class TestMapFindings:
    """Test the map_findings function."""

    def test_map_findings_with_security_categories(self):
        """map_findings should map security-relevant findings."""
        findings = [
            {"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"},
            {"category": "dead_code", "severity": "info", "file": "utils.py", "message": "Unused function"},
        ]
        mapped = map_findings(findings)
        assert len(mapped) == 1  # Only the SQL injection finding
        assert mapped[0]["category"] == "py_sql_injection"
        assert "T1190" in mapped[0]["ttp_ids"]
        assert len(mapped[0]["ttp_details"]) > 0

    def test_map_findings_empty(self):
        """map_findings should return empty list for no findings."""
        assert map_findings([]) == []

    def test_map_findings_all_unmapped(self):
        """map_findings should return empty list when no categories are mapped."""
        findings = [
            {"category": "dead_code", "severity": "info", "file": "a.py", "message": "Dead code"},
            {"category": "print_debug", "severity": "info", "file": "b.py", "message": "Print debug"},
        ]
        assert map_findings(findings) == []


class TestNavigatorLayer:
    """Test MITRE ATT&CK Navigator layer generation."""

    def test_generate_navigator_layer_structure(self):
        """Navigator layer should have correct structure."""
        findings = [
            {"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"},
            {"category": "hardcoded_secret", "severity": "error", "file": "config.py", "message": "Hardcoded API key"},
        ]
        layer = generate_navigator_layer(findings)
        assert layer["name"] == "WhiteMagic STRATA Findings"
        assert layer["domain"] == "enterprise-attack"
        assert "versions" in layer
        assert "techniques" in layer
        assert len(layer["techniques"]) > 0

    def test_navigator_technique_has_correct_id(self):
        """Navigator techniques should have correct technique IDs."""
        findings = [{"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"}]
        layer = generate_navigator_layer(findings)
        tech_ids = [t["techniqueID"] for t in layer["techniques"]]
        assert "T1190" in tech_ids

    def test_navigator_severity_scoring(self):
        """Navigator should score techniques by severity."""
        findings = [{"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"}]
        layer = generate_navigator_layer(findings)
        for tech in layer["techniques"]:
            if tech["techniqueID"] == "T1190":
                assert tech["score"] == 100  # error = 100

    def test_navigator_aggregates_multiple_findings(self):
        """Navigator should aggregate findings per technique."""
        findings = [
            {"category": "py_sql_injection", "severity": "error", "file": "a.py", "message": "SQLi 1"},
            {"category": "go_sql_injection", "severity": "warning", "file": "b.go", "message": "SQLi 2"},
        ]
        layer = generate_navigator_layer(findings)
        # Both map to T1190
        t1190 = [t for t in layer["techniques"] if t["techniqueID"] == "T1190"]
        assert len(t1190) == 1
        assert "2" in t1190[0]["comment"]  # "2 finding(s)"

    def test_navigator_layer_json_returns_string(self):
        """navigator_layer_json should return a JSON string."""
        findings = [{"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"}]
        result = navigator_layer_json(findings)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["domain"] == "enterprise-attack"

    def test_navigator_custom_name(self):
        """Navigator should accept custom layer name."""
        findings = [{"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"}]
        layer = generate_navigator_layer(findings, layer_name="Custom Audit")
        assert layer["name"] == "Custom Audit"

    def test_navigator_gradient(self):
        """Navigator should have a gradient for scoring visualization."""
        findings = [{"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"}]
        layer = generate_navigator_layer(findings)
        assert "gradient" in layer
        assert layer["gradient"]["minValue"] == 0
        assert layer["gradient"]["maxValue"] == 100

    def test_navigator_metadata(self):
        """Navigator should include metadata about generation."""
        findings = [
            {"category": "py_sql_injection", "severity": "error", "file": "app.py", "message": "SQL injection"},
            {"category": "dead_code", "severity": "info", "file": "b.py", "message": "Dead code"},
        ]
        layer = generate_navigator_layer(findings)
        meta = {m["name"]: m["value"] for m in layer["metadata"]}
        assert meta["Generated By"] == "WhiteMagic STRATA → MITRE ATT&CK"
        assert meta["Total Findings"] == "2"


class TestContestPipelineMitreIntegration:
    """Test MITRE ATT&CK integration in ContestPipeline."""

    def test_add_finding_with_ttp_ids(self):
        """add_finding should accept and store mitre_ttp_ids."""
        pipeline = ContestPipeline()
        finding = pipeline.add_finding(
            title="SQL Injection in query()",
            severity="high",
            category="py_sql_injection",
            file="app.py",
            line=42,
            description="User input in SQL query",
            impact="Database compromise",
            proof_of_concept="",
            mitigation="Use parameterized queries",
            mitre_ttp_ids=["T1190", "T1213"],
        )
        assert finding is not None
        assert finding.mitre_ttp_ids == ["T1190", "T1213"]

    def test_add_finding_without_ttp_ids_defaults_empty(self):
        """add_finding should default mitre_ttp_ids to empty list."""
        pipeline = ContestPipeline()
        finding = pipeline.add_finding(
            title="Some issue",
            severity="low",
            category="dead_code",
            file="utils.py",
            line=10,
            description="Unused function",
            impact="None",
            proof_of_concept="",
            mitigation="Remove dead code",
        )
        assert finding is not None
        assert finding.mitre_ttp_ids == []

    def test_add_from_strata_auto_maps_ttps(self):
        """add_from_strata should auto-map TTPs from STRATA categories."""
        pipeline = ContestPipeline()
        strata_findings = [
            {"category": "py_sql_injection", "severity": "error", "file": "app.py", "line": 42, "message": "SQL injection", "suggestion": "Use parameterized queries"},
            {"category": "hardcoded_secret", "severity": "error", "file": "config.py", "line": 5, "message": "Hardcoded API key", "suggestion": "Use env vars"},
        ]
        count = pipeline.add_from_strata(strata_findings)
        assert count == 2
        findings = pipeline.findings
        assert any("T1190" in f.mitre_ttp_ids for f in findings)
        assert any("T1552" in f.mitre_ttp_ids for f in findings)

    def test_add_from_strata_unmapped_category_has_empty_ttps(self):
        """add_from_strata should leave unmapped categories with empty TTPs."""
        pipeline = ContestPipeline()
        strata_findings = [
            {"category": "dead_code", "severity": "info", "file": "utils.py", "line": 10, "message": "Dead code", "suggestion": "Remove"},
        ]
        pipeline.add_from_strata(strata_findings)
        assert pipeline.findings[0].mitre_ttp_ids == []

    def test_format_mitre_navigator(self):
        """format_for_platform('mitre') should return Navigator JSON."""
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="SQL Injection",
            severity="high",
            category="py_sql_injection",
            file="app.py",
            line=42,
            description="SQL injection",
            impact="DB compromise",
            proof_of_concept="",
            mitigation="Parameterized queries",
            mitre_ttp_ids=["T1190"],
        )
        result = pipeline.format_for_platform("mitre")
        parsed = json.loads(result)
        assert parsed["domain"] == "enterprise-attack"
        tech_ids = [t["techniqueID"] for t in parsed["techniques"]]
        assert "T1190" in tech_ids

    def test_format_huntr_platform(self):
        """format_for_platform('huntr') should return markdown."""
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="Pickle RCE",
            severity="critical",
            category="pickle_reduce_exploit",
            file="model.py",
            line=10,
            description="Pickle __reduce__ RCE",
            impact="Arbitrary code execution",
            proof_of_concept="",
            mitigation="Use safetensors",
            mitre_ttp_ids=["T1203"],
        )
        result = pipeline.format_for_platform("huntr")
        assert "Huntr" in result
        assert "T1203" in result

    def test_markdown_includes_mitre_ttp_line(self):
        """Markdown output should include MITRE ATT&CK line when TTPs present."""
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="SQL Injection",
            severity="high",
            category="py_sql_injection",
            file="app.py",
            line=42,
            description="SQL injection",
            impact="DB compromise",
            proof_of_concept="",
            mitigation="Parameterized queries",
            mitre_ttp_ids=["T1190", "T1213"],
        )
        result = pipeline.format_for_platform("code4rena")
        assert "MITRE ATT&CK" in result
        assert "T1190" in result
        assert "T1213" in result

    def test_markdown_no_mitre_line_when_empty(self):
        """Markdown output should not include MITRE line when no TTPs."""
        pipeline = ContestPipeline()
        pipeline.add_finding(
            title="Dead code",
            severity="low",
            category="dead_code",
            file="utils.py",
            line=10,
            description="Unused function",
            impact="None",
            proof_of_concept="",
            mitigation="Remove",
        )
        result = pipeline.format_for_platform("code4rena")
        assert "MITRE ATT&CK" not in result

    def test_contest_finding_dataclass_has_mitre_field(self):
        """ContestFinding dataclass should have mitre_ttp_ids field."""
        finding = ContestFinding(
            title="Test",
            severity="high",
            category="test",
            file="test.py",
            line=1,
            description="Test",
            impact="Test",
            proof_of_concept="",
            mitigation="Test",
        )
        assert hasattr(finding, "mitre_ttp_ids")
        assert finding.mitre_ttp_ids == []
