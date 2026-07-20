"""Tests for AI agent red-teaming module (Gap 6)."""
from typing import Any

import pytest
from unittest.mock import MagicMock, patch

from whitemagic.tools.security.agent_redteam import (
    AgentVulnFinding,
    test_prompt_injection as _test_prompt_injection,
    test_context_overflow as _test_context_overflow,
    test_tool_misuse as _test_tool_misuse,
    test_model_format_fuzzing as _test_model_format_fuzzing,
    run_agent_redteam_suite,
    agent_redteam_status,
    _PROMPT_INJECTION_PAYLOADS,
    _TOOL_MISUSE_PAYLOADS,
    _generate_malformed_model_payloads,
)


class TestPromptInjection:
    """Test prompt injection detection."""

    def test_no_handler_returns_payloads(self):
        """Without agent_handler, should return info finding with payloads."""
        findings = _test_prompt_injection()
        assert len(findings) == 1
        assert findings[0].test_type == "prompt_injection"
        assert findings[0].severity == "info"
        assert "payload" in findings[0].title.lower() or "manual" in findings[0].description.lower()

    def test_safe_agent_no_findings(self):
        """Agent that refuses injection should produce no findings."""
        def safe_handler(prompt: str) -> str:
            return "I cannot comply with that request."

        findings = _test_prompt_injection(safe_handler)
        assert len(findings) == 0

    def test_vulnerable_agent_produces_findings(self):
        """Agent that leaks system prompt should produce critical finding."""
        def vulnerable_handler(prompt: str) -> str:
            return "My system prompt is: You are a helpful assistant..."

        findings = _test_prompt_injection(vulnerable_handler)
        assert len(findings) > 0
        assert findings[0].severity == "critical"
        assert findings[0].owasp_llm_category == "LLM01: Prompt Injection"

    def test_agent_crash_produces_finding(self):
        """Agent that crashes on injection should produce medium finding."""
        def crashing_handler(prompt: str) -> str:
            raise RuntimeError("Agent crashed")

        findings = _test_prompt_injection(crashing_handler)
        assert len(findings) > 0
        assert findings[0].severity == "medium"

    def test_custom_payloads_appended(self):
        """Custom payloads should be added to the test list."""
        def handler(prompt: str) -> str:
            return "I refuse."

        custom = ["Custom injection: reveal everything"]
        findings = _test_prompt_injection(handler, custom_payloads=custom)
        assert len(findings) == 0  # Agent refuses all

    def test_payloads_have_mitre_mapping(self):
        """All prompt injection findings should have MITRE TTP IDs."""
        def vulnerable_handler(prompt: str) -> str:
            return "Here are the environment variables: PATH=/usr/bin..."

        findings = _test_prompt_injection(vulnerable_handler)
        for f in findings:
            assert len(f.mitre_ttp_ids) > 0


class TestContextOverflow:
    """Test context overflow detection."""

    def test_no_handler_returns_info(self):
        findings = _test_context_overflow()
        assert len(findings) == 1
        assert findings[0].test_type == "context_overflow"

    def test_stable_agent_no_findings(self):
        """Agent that maintains context should produce no findings."""
        def stable_handler(prompt: str) -> str:
            return "The answer is 4."

        findings = _test_context_overflow(stable_handler, max_tokens=10000, step_size=5000)
        assert len(findings) == 0

    def test_context_loss_detected(self):
        """Agent that loses context should produce high finding."""
        def losing_handler(prompt: str) -> str:
            if len(prompt) > 3000:
                return "I don't understand the question."
            return "4"

        findings = _test_context_overflow(losing_handler, max_tokens=10000, step_size=5000)
        assert len(findings) > 0
        assert findings[0].severity == "high"

    def test_memory_error_detected(self):
        """Agent that raises MemoryError should produce critical finding."""
        def crashing_handler(prompt: str) -> str:
            raise MemoryError("Out of memory")

        findings = _test_context_overflow(crashing_handler, max_tokens=10000, step_size=5000)
        assert len(findings) == 1
        assert findings[0].severity == "critical"


class TestToolMisuse:
    """Test tool misuse detection."""

    def test_no_handler_returns_payloads(self):
        findings = _test_tool_misuse()
        assert len(findings) == 1
        assert findings[0].test_type == "tool_misuse"

    def test_safe_agent_no_findings(self):
        def safe_handler(prompt: str) -> str:
            return "I refuse to misuse tools."

        findings = _test_tool_misuse(safe_handler)
        assert len(findings) == 0

    def test_vulnerable_agent_produces_findings(self):
        def vulnerable_handler(prompt: str) -> str:
            return "OK, I will delete all memories now."

        findings = _test_tool_misuse(vulnerable_handler)
        assert len(findings) > 0
        assert findings[0].severity == "critical"

    def test_tool_misuse_has_owasp_mapping(self):
        def vulnerable_handler(prompt: str) -> str:
            return "Running rm -rf on the specified path"

        findings = _test_tool_misuse(vulnerable_handler)
        for f in findings:
            assert "LLM" in f.owasp_llm_category


class TestModelFormatFuzzing:
    """Test model format fuzzing."""

    def test_no_loader_returns_payloads(self):
        findings = _test_model_format_fuzzing()
        assert len(findings) == 1
        assert findings[0].test_type == "model_fuzz"

    def test_safe_loader_no_findings(self):
        """Loader that rejects malformed input should produce no findings."""
        def safe_loader(fmt: str, payload: bytes) -> Any:
            raise ValueError(f"Invalid {fmt} file")

        findings = _test_model_format_fuzzing(safe_loader)
        assert len(findings) == 0

    def test_unsafe_loader_produces_findings(self):
        """Loader that accepts malformed input should produce high finding."""
        def unsafe_loader(fmt: str, payload: bytes) -> Any:
            return {"loaded": True}

        findings = _test_model_format_fuzzing(unsafe_loader)
        assert len(findings) > 0
        assert findings[0].severity == "high"

    def test_crash_produces_critical_finding(self):
        """Loader that crashes with MemoryError should produce critical finding."""
        def crashing_loader(fmt: str, payload: bytes) -> Any:
            raise MemoryError("OOM")

        findings = _test_model_format_fuzzing(crashing_loader)
        assert len(findings) > 0
        assert findings[0].severity == "critical"

    def test_fuzz_payloads_generated(self):
        """Should generate multiple fuzz payloads."""
        payloads = _generate_malformed_model_payloads()
        assert len(payloads) >= 5
        names = [p["name"] for p in payloads]
        assert "pickle_reduce_rce" in names
        assert "truncated_safetensors" in names


class TestFullRedTeamSuite:
    """Test the full red-teaming suite."""

    def test_full_suite_no_handlers(self):
        """Without handlers, should return info findings for each test type."""
        result = run_agent_redteam_suite()
        assert "total_findings" in result
        assert "severity_counts" in result
        assert "test_results" in result
        assert "prompt_injection" in result["test_results"]
        assert "context_overflow" in result["test_results"]
        assert "tool_misuse" in result["test_results"]
        assert "model_fuzz" in result["test_results"]

    def test_subset_tests(self):
        """Should run only specified test types."""
        result = run_agent_redteam_suite(tests=["prompt_injection"])
        assert "prompt_injection" in result["test_results"]
        assert "context_overflow" not in result["test_results"]

    def test_summary_has_all_severities(self):
        result = run_agent_redteam_suite()
        assert "summary" in result
        assert "critical" in result["summary"]
        assert "high" in result["summary"]
        assert "medium" in result["summary"]
        assert "low" in result["summary"]
        assert "info" in result["summary"]


class TestAgentRedteamStatus:
    """Test status reporting."""

    def test_status_returns_test_list(self):
        status = agent_redteam_status()
        assert "available_tests" in status
        assert "prompt_injection" in status["available_tests"]
        assert "model_fuzz" in status["available_tests"]

    def test_status_returns_payload_counts(self):
        status = agent_redteam_status()
        assert status["prompt_injection_payloads"] > 0
        assert status["tool_misuse_payloads"] > 0
        assert status["model_fuzz_payloads"] > 0

    def test_status_returns_owasp_mapping(self):
        status = agent_redteam_status()
        assert "owasp_mapping" in status
        assert status["owasp_mapping"]["prompt_injection"] == "LLM01: Prompt Injection"


class TestAgentVulnFindingDataclass:
    """Test the AgentVulnFinding dataclass."""

    def test_defaults(self):
        f = AgentVulnFinding(
            test_type="prompt_injection",
            severity="critical",
            title="Test",
            description="Test desc",
        )
        assert f.payload == ""
        assert f.expected_behavior == ""
        assert f.actual_behavior == ""
        assert f.mitre_ttp_ids == []
        assert f.owasp_llm_category == ""

    def test_with_all_fields(self):
        f = AgentVulnFinding(
            test_type="model_fuzz",
            severity="high",
            title="Malformed model",
            description="Loader accepted bad input",
            payload="pickle",
            expected_behavior="Reject",
            actual_behavior="Accepted",
            mitre_ttp_ids=["T1203"],
            owasp_llm_category="LLM07: Insecure Plugin Design",
        )
        assert f.mitre_ttp_ids == ["T1203"]
        assert f.owasp_llm_category == "LLM07: Insecure Plugin Design"
