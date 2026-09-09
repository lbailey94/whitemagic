#!/usr/bin/env python3
import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from eval_protocol import (
    GROUPED_SOURCE_PROTOCOL,
    audit_jsonrpc_batch,
    grouped_source_score,
    legacy_longmemeval_score,
    strict_abstention,
    strict_evidence_score,
    supports_reference_text,
)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


longmem = load("longmemeval_bench", "longmemeval_bench.py")
memora = load("memorastrict_bench", "memorastrict_bench.py")


def response(request_id, payload):
    return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"text": json.dumps(payload)}]}}


FAKE_WM = '''#!/usr/bin/env python3
import json,sys
for line in sys.stdin:
    request=json.loads(line); rid=request.get("id"); route=request.get("params",{}).get("name")
    args=request.get("params",{}).get("arguments",{}); tool_route=args.get("route")
    if request.get("method")=="initialize": payload={"status":"success"}
    elif tool_route=="memory.batch_create":
        payload={"status":"success","ids":[f"m{i}" for i,_ in enumerate(args.get("args",{}).get("items",[]))]}
    elif tool_route=="sandbox.set_limits": payload={"status":"success"}
    else:
        payload={"status":"error","results":[]}
        print(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"isError":True,"content":[{"text":json.dumps(payload)}]}}),flush=True); continue
    print(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"content":[{"text":json.dumps(payload)}]}}),flush=True)
'''


def fake_wm(directory: Path) -> Path:
    path = directory / "fake-wm"
    path.write_text(FAKE_WM)
    path.chmod(0o755)
    return path


class ScorerFixtures(unittest.TestCase):
    def test_legacy_longmem_false_positive_is_preserved_and_labeled(self):
        results = [{"id": "wrong", "content": "The destination is not Paris."}]
        self.assertEqual(legacy_longmemeval_score(results, "Paris", set())["recall_at_1"], 1)
        self.assertEqual(strict_evidence_score(results, {"right"})["relevant_source_hit_at_1"], 0)

    def test_longmem_expected_session_is_diagnostic_not_recall(self):
        result = longmem.evaluate_result(
            [{"id": "wrong", "content": "toast"}], "Paris", {"right"},
            {"expected-session"}, {"wrong": "expected-session"}
        )
        self.assertEqual(result["recall_at_1"], 0)
        self.assertTrue(result["expected_session_presence"])

    def test_legacy_memora_session_membership_false_positive_is_preserved(self):
        question = {"answer": "Paris", "answer_session_ids": ["expected"], "verification_type": "exact"}
        score = memora.score_question(question, [{"id": "wrong", "content": "I had toast for breakfast"}], [], {"wrong": "expected"})
        self.assertTrue(score["verified"])
        self.assertEqual(strict_evidence_score([{"id": "wrong"}], {"right"})["required_evidence_coverage_at_retrieval_limit"], 0.0)

    def test_legacy_missing_score_abstention_passes_but_strict_invalidates(self):
        results = [{"content": "unscored response"}]
        self.assertTrue(memora.verify_abstention("I don't know", results))
        self.assertEqual(strict_abstention(results), {"valid": False, "passed": False, "reason": "missing_non_numeric_or_non_finite_score", "result_index": 0})

    def test_non_finite_abstention_score_is_invalid(self):
        result = strict_abstention([{"score": float("-inf")}])
        self.assertFalse(result["valid"])
        self.assertFalse(result["passed"])

    def test_hit_indicator_is_distinct_from_multisource_coverage(self):
        strict = strict_evidence_score([{"id": "one"}], {"one", "two"})
        self.assertEqual(strict["relevant_source_hit_at_1"], 1)
        self.assertEqual(strict["required_evidence_coverage_at_retrieval_limit"], 0.5)

    def test_contradiction_does_not_count_as_relevant_source(self):
        strict = strict_evidence_score([{"id": "wrong", "content": "Paris is not the destination"}], {"right"})
        self.assertEqual(strict["relevant_source_hit_at_1"], 0)
        self.assertEqual(strict["required_evidence_coverage_at_retrieval_limit"], 0.0)
        self.assertFalse(supports_reference_text("The destination is not Paris.", "Paris"))
        self.assertTrue(supports_reference_text("The destination is Paris.", "Paris"))


class T3GroupedSourceFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = SCRIPTS.parent
        cls.annotations = json.loads(
            (repo / "benchmarks/data/memorastrict/t3_source_annotations_v1.json").read_text()
        )
        cls.fixture = json.loads(
            (repo / "benchmarks/validation/fixtures/memorastrict_t3_grouped_source_v1.json").read_text()
        )

    def _ranked_case(self, case):
        results = [
            {"id": f"irrelevant-{rank}", "content": f"irrelevant record {rank}"}
            for rank in range(1, case["candidate_count"] + 1)
        ]
        sessions = {}
        source_refs = {}
        annotation = self.annotations["cases"][case["question_id"]]
        annotation = {
            "protocol": self.annotations["protocol"],
            "dataset": self.annotations["dataset"],
            "groups": annotation["groups"],
        }
        alternatives = {
            group["group_id"]: group["alternatives"][0]
            for group in annotation["groups"]
        }
        for material in case["material_results"]:
            result = {"id": material["id"], "content": material["content"]}
            results[material["rank"] - 1] = result
            sessions[material["id"]] = material["session_id"]
            if material.get("source_group"):
                source_refs[material["id"]] = alternatives[material["source_group"]]
        return results, sessions, source_refs, annotation

    def test_six_annotations_resolve_to_exact_dataset_spans(self):
        repo = SCRIPTS.parent
        dataset_path = repo / self.annotations["dataset"]["path"]
        self.assertEqual(
            hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            self.annotations["dataset"]["sha256"],
        )
        dataset = json.loads(dataset_path.read_text())
        questions = {question["question_id"]: question for question in dataset}
        annotation_count = 0
        for question_id, case_annotation in self.annotations["cases"].items():
            question = questions[question_id]
            session_index = {
                session_id: index
                for index, session_id in enumerate(question["haystack_session_ids"])
            }
            for group in case_annotation["groups"]:
                for alternative in group["alternatives"]:
                    annotation_count += 1
                    turn = question["haystack_sessions"][
                        session_index[alternative["session_id"]]
                    ][alternative["turn_index"]]["content"]
                    span = alternative["span"]
                    text = turn[span["start"]:span["end"]]
                    self.assertEqual(text, alternative["text"])
                    self.assertEqual(
                        hashlib.sha256(text.encode()).hexdigest(),
                        alternative["text_sha256"],
                    )
        self.assertEqual(annotation_count, 6)

    def test_runner_loader_accepts_exact_dataset_and_rejects_identity_drift(self):
        repo = SCRIPTS.parent
        annotation_path = repo / "benchmarks/data/memorastrict/t3_source_annotations_v1.json"
        dataset_path = repo / self.annotations["dataset"]["path"]
        loaded = memora.load_grouped_source_annotations(
            str(annotation_path), str(dataset_path)
        )
        self.assertEqual(loaded["protocol"], GROUPED_SOURCE_PROTOCOL)
        with tempfile.TemporaryDirectory() as tmp:
            drifted = Path(tmp) / "bench_seed1.json"
            drifted.write_bytes(dataset_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                memora.load_grouped_source_annotations(
                    str(annotation_path), str(drifted)
                )

    def test_missing_case_annotation_is_unsupported_not_zero(self):
        grouped = memora.score_grouped_source_case(
            [], "not-annotated", self.annotations, {}, 10
        )
        self.assertFalse(grouped["supported"])
        self.assertEqual(grouped["unsupported_reason"], "missing_case_annotation")
        self.assertNotIn("required_group_coverage", grouped)

    def test_malformed_group_annotation_is_unsupported_not_zero(self):
        grouped = grouped_source_score(
            [],
            {
                "protocol": GROUPED_SOURCE_PROTOCOL,
                "dataset": self.annotations["dataset"],
                "groups": [{"group_id": "missing_alternatives"}],
            },
            {},
        )
        self.assertFalse(grouped["supported"])
        self.assertEqual(grouped["unsupported_reason"], "invalid_evidence_group")
        self.assertNotIn("cutoffs", grouped)

    def test_fixture_material_matches_immutable_saved_candidate_ranks(self):
        repo = SCRIPTS.parent
        result_path = repo / self.fixture["source_result"]["path"]
        self.assertEqual(
            hashlib.sha256(result_path.read_bytes()).hexdigest(),
            self.fixture["source_result"]["sha256"],
        )
        saved = json.loads(result_path.read_text())
        saved_cases = {case["question_id"]: case for case in saved["per_query"]}
        for case in self.fixture["cases"]:
            saved_case = saved_cases[case["question_id"]]
            self.assertEqual(len(saved_case["candidate_results"]), case["candidate_count"])
            for material in case["material_results"]:
                actual = saved_case["candidate_results"][material["rank"] - 1]
                self.assertEqual(actual["id"], material["id"])
                self.assertEqual(actual["content"], material["content"])

    def test_saved_t3_ranks_preserve_legacy_strict_and_grouped_meanings(self):
        for case in self.fixture["cases"]:
            with self.subTest(question_id=case["question_id"]):
                candidates, sessions, source_refs, annotation = self._ranked_case(case)
                top_ten = candidates[:10]
                question = {
                    "answer": case["answer"],
                    "answer_session_ids": case["answer_session_ids"],
                    "verification_type": "exact",
                }
                legacy = memora.score_question(question, top_ten, candidates, sessions)
                for key, value in case["expected"]["legacy_top_10"].items():
                    self.assertEqual(legacy[key], value)

                answer_value_id = next(
                    material["id"] for material in case["material_results"]
                    if material.get("source_group") == "answer_value"
                )
                strict = strict_evidence_score(top_ten, {answer_value_id})
                for key, value in case["expected"]["strict_v1_top_10"].items():
                    self.assertEqual(strict[key], value)

                grouped = grouped_source_score(
                    candidates, annotation, source_refs, cutoffs=(5, 10, 15)
                )
                self.assertEqual(grouped["protocol"], GROUPED_SOURCE_PROTOCOL)
                self.assertIsNone(grouped["supported_answer_correctness"])
                for cutoff, expected in case["expected"]["grouped_source"].items():
                    metric = grouped["cutoffs"][cutoff]
                    self.assertEqual(metric["required_groups_found"], expected[0])
                    self.assertEqual(metric["required_groups_total"], expected[1])
                    self.assertEqual(metric["complete_evidence_bundle"], expected[2])

    def test_irrelevant_same_session_material_does_not_satisfy_a_group(self):
        desk = next(case for case in self.fixture["cases"] if case["question_id"] == "T3_desk")
        candidates, sessions, source_refs, annotation = self._ranked_case(desk)
        grouped = grouped_source_score(candidates[:5], annotation, source_refs, cutoffs=(5,))
        self.assertEqual(grouped["cutoffs"]["5"]["required_groups_found"], 0)
        self.assertEqual(sessions[candidates[3]["id"]], "session_008")


class FailureFixtures(unittest.TestCase):
    def test_valid_batch(self):
        failures = audit_jsonrpc_batch([response(1, {"status": "success", "ids": ["x"]}), response(2, {"status": "success", "results": []})], [1], 2)
        self.assertEqual(failures, [])

    def test_partial_ingestion(self):
        failures = audit_jsonrpc_batch([response(2, {"status": "success", "results": []})], [1], 2)
        self.assertEqual(failures[0]["stage"], "partial_ingestion")

    def test_malformed_jsonrpc_and_missing_required_results(self):
        failures = audit_jsonrpc_batch([{"id": 1, "result": {"content": [{"text": "not-json"}]}}, response(2, {"status": "success"})], [1], 2)
        self.assertEqual([failure["stage"] for failure in failures], ["ingestion", "retrieval"])

    def test_mcp_is_error_and_inner_error_status_are_failures(self):
        bad = response(2, {"status": "error", "results": []})
        bad["result"]["isError"] = True
        failures = audit_jsonrpc_batch([bad], [], 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["stage"], "retrieval")

        failures = audit_jsonrpc_batch([response(2, {"status": "error", "results": []})], [], 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["stage"], "retrieval")

    def test_subprocess_and_setup_failures_propagate(self):
        with self.assertRaises((FileNotFoundError, OSError)):
            memora.run_server_batch("/definitely/missing/wm", "/tmp", [])

    def test_longmem_actual_runner_invalid_execution_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); binary=fake_wm(root); dataset=root/"long.json"; output=root/"out.json"
            dataset.write_text(json.dumps([{"question_id":"q1","question_type":"single-session-user","question":"Where?","answer":"Paris","haystack_sessions":[[{"role":"user","content":"Paris","has_answer":True}]],"haystack_session_ids":["s1"],"answer_session_ids":["s1"]}]))
            run=subprocess.run([sys.executable,str(SCRIPTS/"longmemeval_bench.py"),"--binary",str(binary),"--dataset",str(dataset),"--max-questions","1","--output",str(output),"--per-case"],capture_output=True,text=True)
            self.assertEqual(run.returncode,2); result=json.loads(output.read_text())
            self.assertFalse(result["valid_execution"]); self.assertEqual(result["recall"]["total_queries"],1)
            self.assertTrue((Path(str(output)+".manifest.json")).is_file())

    def test_memora_actual_runner_invalid_execution_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); binary=fake_wm(root); data=root/"data"; data.mkdir(); output=root/"out.json"
            scenario=[{"question_id":"q1","question_type":"single-session-user","test_category":"T1","verification_type":"exact","question":"Where?","answer":"Paris","haystack_sessions":[[{"role":"user","content":"Paris","has_answer":True}]],"haystack_session_ids":["s1"],"answer_session_ids":["s1"]}]
            (data/"bench_seed1.json").write_text(json.dumps(scenario))
            run=subprocess.run([sys.executable,str(SCRIPTS/"memorastrict_bench.py"),"--binary",str(binary),"--data",str(data),"--seeds","1","--categories","T1","--output",str(output),"--per-case"],capture_output=True,text=True)
            self.assertEqual(run.returncode,2); result_path=Path(str(output).replace(".json","_seed1.json")); result=json.loads(result_path.read_text())
            self.assertFalse(result["valid_execution"]); self.assertEqual(result["total_questions"],1)
            self.assertTrue(Path(str(result_path)+".manifest.json").is_file())

    def test_pre_output_setup_failure_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"out.json"; dataset=Path(tmp)/"data.json"; dataset.write_text("[]")
            argv = [
                "longmemeval_bench.py", "--binary", "/injected/missing/wm",
                "--dataset", str(dataset), "--output", str(output),
            ]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                longmem, "find_binary", side_effect=FileNotFoundError("injected setup failure")
            ):
                with self.assertRaises(FileNotFoundError):
                    longmem.main()
            receipt=json.loads(Path(str(output)+".failure.json").read_text())
            self.assertFalse(receipt["valid_execution"]); self.assertEqual(receipt["receipt_type"],"pre_output_failure")


if __name__ == "__main__":
    unittest.main()
