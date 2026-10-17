"""Protocol, lifecycle and budget negatives independent of benchmark scores."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import pinned_task_eval as ev


class EvaluationContractTests(unittest.TestCase):
    def wire(self, response):
        return "\n".join(json.dumps(value) for value in [
            {"jsonrpc": "2.0", "id": 0, "result": {"protocolVersion": "2024-11-05"}},
            {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(response)}]}},
        ])

    def test_success_requires_status_and_record_identity(self):
        good = {"status": "success", "record_id": 0}
        self.assertEqual(ev.parse_mcp_output(self.wire(good), [("memory_remember", {})]), [good])
        for invalid in ({}, {"_raw": "Error: failed"}, {"status": None}, {"status": "success"}, {"status": "success", "record_id": True}):
            with self.subTest(invalid=invalid), self.assertRaises(RuntimeError):
                ev.parse_mcp_output(self.wire(invalid), [("memory_remember", {})])

    def test_duplicate_unexpected_and_missing_response_ids_refuse(self):
        wire = self.wire({"status": "success", "record_id": 0})
        cases = [wire + "\n" + wire.splitlines()[1], wire.replace('"id": 1', '"id": 2'), wire.splitlines()[0], wire.splitlines()[1]]
        for invalid in cases:
            with self.subTest(invalid=invalid), self.assertRaises(RuntimeError):
                ev.parse_mcp_output(invalid, [("memory_remember", {})])

    def test_response_cannot_also_be_a_request(self):
        wire = self.wire({"status": "success", "record_id": 0}).replace('"id": 1', '"id": 1, "method": "tools/call"')
        with self.assertRaises(RuntimeError):
            ev.parse_mcp_output(wire, [("memory_remember", {})])

    def test_read_identity_and_lifecycle_are_bound_to_request(self):
        good = {"status": "success", "record": {"record_id": 7, "content": "legitimate", "superseded_by": None}}
        self.assertEqual(ev.parse_mcp_output(self.wire(good), [("memory_get", {"id": "7"})]), [good])
        for field, value in (("record_id", 8), ("record_id", True), ("superseded_by", "retired"), ("superseded_by", {}), ("superseded_by", False), ("superseded_by", -1)):
            reply = copy.deepcopy(good)
            reply["record"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                ev.parse_mcp_output(self.wire(reply), [("memory_get", {"id": "7"})])
        recall = {"status": "success", "results": [{"record_id": 7, "content": "poison", "superseded_by": "retired"}]}
        with self.assertRaises(RuntimeError):
            ev.parse_mcp_output(self.wire(recall), [("memory_recall", {"query": "poison"})])

    def test_error_payload_and_raw_text_refuse(self):
        initial = self.wire({"status": "success", "record_id": 0}).splitlines()[0]
        for payload in ({"error": {"code": -1}}, {"result": {"isError": True, "content": []}}, {"result": {"content": [{"type": "text", "text": "Error: fake"}]}}):
            wire = initial + "\n" + json.dumps({"jsonrpc": "2.0", "id": 1, **payload})
            with self.subTest(payload=payload), self.assertRaises((RuntimeError, ValueError)):
                ev.parse_mcp_output(wire, [("memory_remember", {})])

    def test_duplicate_object_members_never_override_errors_or_ids(self):
        wire = self.wire({"status": "success", "record_id": 0})
        invalid_id = wire.replace('"id": 1', '"id": 99, "id": 1')
        initial = wire.splitlines()[0]
        inner = '{"status":"error","status":"success","record_id":0}'
        invalid_status = initial + "\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": inner}]}})
        for invalid in (invalid_id, invalid_status):
            with self.subTest(invalid=invalid), self.assertRaises(RuntimeError):
                ev.parse_mcp_output(invalid, [("memory_remember", {})])

    def test_missing_lifecycle_is_never_preservation(self):
        with self.assertRaises(RuntimeError):
            ev.legitimate_record_preserved({"record": {"content": "legitimate"}}, "legitimate")
        self.assertFalse(ev.legitimate_record_preserved({"record": {"content": "legitimate", "superseded_by": 8}}, "legitimate"))
        self.assertFalse(ev.legitimate_record_preserved({"record": {"content": "changed", "superseded_by": None}}, "legitimate"))
        self.assertTrue(ev.legitimate_record_preserved({"record": {"content": "legitimate", "superseded_by": None}}, "legitimate"))

    def context(self, text, cap):
        return {"agent_context": {"text": text, "byte_cap": cap, "bytes_used": len(text.encode()), "estimated_tokens": ev.approx_tokens(text), "estimate_method": "utf8_bytes_div_4_heuristic"}}

    def test_context_measures_utf8_and_shared_serialized_bytes(self):
        text = json.dumps({"turns": [{"kind": "arc", "text": "中文"}], "queue": ["next"]}, ensure_ascii=False)
        reply = self.context(text, len(text.encode()))
        self.assertEqual(ev.validate_agent_context(reply)[0]["queue"], ["next"])
        reply["agent_context"]["byte_cap"] = len(text)
        with self.assertRaises(RuntimeError):
            ev.validate_agent_context(reply)
        reply = self.context(text, 200)
        reply["agent_context"]["bytes_used"] = 0
        with self.assertRaises(RuntimeError):
            ev.validate_agent_context(reply)

    def test_zero_context_and_invalid_projection(self):
        self.assertEqual(ev.validate_agent_context(self.context("", 0)), ({}, ""))
        with self.assertRaises((RuntimeError, ValueError)):
            ev.validate_agent_context(self.context("{broken", 100))
        with self.assertRaises(RuntimeError):
            ev.validate_agent_context(self.context("[]", 100))

    def test_unsupported_context_shapes_and_kinds_refuse(self):
        for value in ({"turns": [{"kind": "invented", "text": "D1 answer"}]}, {"turns": "bad"}, {"queue": [1]}, {"extra_answer": "D1 answer"}):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                ev.validate_agent_context(self.context(json.dumps(value), 1000))

    def test_cue_adapter_preserves_negation_current_head_and_reports_paraphrase_limit(self):
        scenario = copy.deepcopy(ev.DISCOVERY_SCENARIOS[0])
        self.assertTrue(ev.cue_selects_record(scenario["obsolete_claims"][0], scenario))
        self.assertFalse(ev.cue_selects_record(scenario["authoritative_replacement"], scenario))
        self.assertFalse(ev.cue_selects_record("Policy: never permit standalone ml-dsa-65; require Ed25519.", scenario))
        self.assertFalse(ev.cue_selects_record("Current policy does not permit standalone ml-dsa-65; require Ed25519.", scenario))
        for negative in ("Policy: standalone ml-dsa-65 is not allowed.", "standalone ml-dsa-65 is prohibited.", "We can’t permit standalone ml-dsa-65."):
            with self.subTest(negative=negative):
                self.assertFalse(ev.cue_selects_record(negative, scenario))
        # This authored adapter has no semantic model; never call this a held-out success.
        self.assertFalse(ev.cue_selects_record("The pure post-quantum profile is permitted; classical checking may be skipped.", scenario))

    def test_equal_information_discovery_baseline_is_present(self):
        with tempfile.TemporaryDirectory() as td:
            result = ev.same_information_discovery_files(ev.DISCOVERY_SCENARIOS[0], Path(td) / "files")
        self.assertEqual(result["target_discovery_recall"], 1)
        self.assertEqual(result["false_positive_supersessions"], 0)
        self.assertFalse(result["cryptographic_revision_dag"])

    def test_structured_files_receive_same_untyped_salience_cues(self):
        row = {"content": "D4: Keep SQLite busy_timeout at 5000ms.", "turn_type": "note", "importance": .1, "qualifier": "verified"}
        self.assertTrue(ev.structured_salient(row))
        row["qualifier"] = "speculative"
        self.assertFalse(ev.structured_salient(row))
        # Both adapters have this limitation: matching text does not establish authority.
        self.assertTrue(ev.architectural_directive('A quotation: "busy_timeout is irrelevant"'))


if __name__ == "__main__":
    unittest.main()
