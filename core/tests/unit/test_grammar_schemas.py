# ruff: noqa: BLE001
"""Tests for grammar-constrained JSON schemas (Phase 3)."""

from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestGrammarSchemas:
    """Test the grammar schema definitions."""

    def test_entity_extraction_schema_is_valid_json(self):
        from whitemagic.inference.grammar_schemas import ENTITY_EXTRACTION_SCHEMA
        import json
        schema = json.loads(ENTITY_EXTRACTION_SCHEMA)
        assert schema["type"] == "object"
        assert "entities" in schema["properties"]
        assert "relations" in schema["properties"]
        assert "name" in schema["properties"]["entities"]["items"]["properties"]
        assert "type" in schema["properties"]["entities"]["items"]["properties"]

    def test_security_classification_schema_is_valid_json(self):
        from whitemagic.inference.grammar_schemas import SECURITY_CLASSIFICATION_SCHEMA
        import json
        schema = json.loads(SECURITY_CLASSIFICATION_SCHEMA)
        assert schema["type"] == "object"
        assert "is_attack" in schema["properties"]
        assert schema["properties"]["is_attack"]["type"] == "boolean"
        assert "confidence" in schema["properties"]
        assert schema["properties"]["confidence"]["type"] == "number"

    def test_safety_evaluation_schema_is_valid_json(self):
        from whitemagic.inference.grammar_schemas import SAFETY_EVALUATION_SCHEMA
        import json
        schema = json.loads(SAFETY_EVALUATION_SCHEMA)
        assert schema["type"] == "object"
        assert "score" in schema["properties"]
        assert schema["properties"]["score"]["type"] == "number"
        assert "reasoning" in schema["properties"]
        assert schema["properties"]["reasoning"]["type"] == "string"

    def test_tool_call_schema_is_valid_json(self):
        from whitemagic.inference.grammar_schemas import TOOL_CALL_SCHEMA
        import json
        schema = json.loads(TOOL_CALL_SCHEMA)
        assert schema["type"] == "object"
        assert "tool" in schema["properties"]
        assert "args" in schema["properties"]

    def test_tool_call_list_schema_is_valid_json(self):
        from whitemagic.inference.grammar_schemas import TOOL_CALL_LIST_SCHEMA
        import json
        schema = json.loads(TOOL_CALL_LIST_SCHEMA)
        assert schema["type"] == "object"
        assert "tool_calls" in schema["properties"]
        assert "final_answer" in schema["properties"]

    def test_content_summary_schema_is_valid_json(self):
        from whitemagic.inference.grammar_schemas import CONTENT_SUMMARY_SCHEMA
        import json
        schema = json.loads(CONTENT_SUMMARY_SCHEMA)
        assert schema["type"] == "object"
        assert "summary" in schema["properties"]
        assert "key_points" in schema["properties"]

    def test_get_schema_by_name(self):
        from whitemagic.inference.grammar_schemas import get_schema
        assert get_schema("entity_extraction") is not None
        assert get_schema("security_classification") is not None
        assert get_schema("safety_evaluation") is not None
        assert get_schema("tool_call") is not None
        assert get_schema("tool_call_list") is not None
        assert get_schema("content_summary") is not None
        assert get_schema("nonexistent") is None

    def test_get_grammar_by_name(self):
        from whitemagic.inference.grammar_schemas import get_grammar
        assert get_grammar("json_object") is not None
        assert get_grammar("tool_call") is not None
        assert get_grammar("nonexistent") is None

    def test_json_object_grammar_has_root_rule(self):
        from whitemagic.inference.grammar_schemas import JSON_OBJECT_GRAMMAR
        assert "root ::=" in JSON_OBJECT_GRAMMAR
        assert '"{"' in JSON_OBJECT_GRAMMAR

    def test_tool_call_grammar_has_root_rule(self):
        from whitemagic.inference.grammar_schemas import TOOL_CALL_GRAMMAR
        assert "root ::=" in TOOL_CALL_GRAMMAR

    def test_schemas_registry_has_all_schemas(self):
        from whitemagic.inference.grammar_schemas import SCHEMAS
        expected = {
            "entity_extraction",
            "security_classification",
            "safety_evaluation",
            "tool_call",
            "tool_call_list",
            "content_summary",
            "code_generation",
        }
        assert set(SCHEMAS.keys()) == expected

    def test_grammars_registry_has_all_grammars(self):
        from whitemagic.inference.grammar_schemas import GRAMMARS
        expected = {"json_object", "tool_call", "python_code"}
        assert set(GRAMMARS.keys()) == expected


class TestLlamaCppBackendGrammarSupport:
    """Test that LlamaCppBackend.complete accepts json_schema and grammar params."""

    def test_complete_accepts_json_schema_param(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        import inspect
        sig = inspect.signature(LlamaCppBackend.complete)
        assert "json_schema" in sig.parameters
        assert "grammar" in sig.parameters

    def test_complete_accepts_response_format_in_chat(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        import inspect
        sig = inspect.signature(LlamaCppBackend.chat)
        assert "response_format" in sig.parameters


class TestEntityExtractorUsesSchema:
    """Test that entity_extractor imports and uses the grammar schema."""

    def test_entity_extractor_imports_schema(self):
        # Just verify the import works and the module loads
        from whitemagic.core.intelligence.entity_extractor import EntityExtractor
        assert EntityExtractor is not None

    def test_entity_extractor_has_extract_llama(self):
        from whitemagic.core.intelligence.entity_extractor import EntityExtractor
        assert hasattr(EntityExtractor, "_extract_llama")


class TestSemanticDefenseUsesSchema:
    """Test that semantic_defense imports and uses the grammar schema."""

    def test_semantic_defense_imports_schema(self):
        from whitemagic.security.semantic_defense import _query_model_for_classification
        assert _query_model_for_classification is not None

    def test_semantic_defense_has_llama_available(self):
        from whitemagic.security.semantic_defense import _llama_available
        assert callable(_llama_available)


class TestEscalationUsesSchema:
    """Test that escalation imports and uses the grammar schema."""

    def test_escalation_has_evaluate_llm(self):
        from whitemagic.dharma.escalation import EscalationPipeline
        assert hasattr(EscalationPipeline, "_evaluate_llm")
