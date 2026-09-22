"""T1 harness helpers: sharding, session-level scoring, retrieval-row contract.

Hand-computed fixtures per the T1 spec acceptance gate (2026-09-22).
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import longmemeval_bench as bench  # noqa: E402


def make_dataset(n: int = 10) -> list[dict]:
    return [
        {"question_id": f"q{i}", "question_type": "single-session-user", "question": f"Q{i}"}
        for i in range(n)
    ]


class TestFilterDataset:
    def test_shards_are_disjoint_and_cover_the_set(self):
        dataset = make_dataset(10)
        shards = [bench.filter_dataset(dataset, shard=(i, 3)) for i in range(3)]
        ids = [row["question_id"] for shard in shards for row in shard]
        assert len(ids) == len(set(ids)) == 10, "shards must be disjoint and cover the set"
        assert sorted(ids) == [row["question_id"] for row in dataset]

    def test_ids_file_selects_in_dataset_order(self):
        dataset = make_dataset(5)
        tmp = Path("/tmp/opencode-t1-ids.txt")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text("q3\nq0\n", encoding="utf-8")
        selected = bench.filter_dataset(dataset, ids_file=str(tmp))
        assert [row["question_id"] for row in selected] == ["q0", "q3"]

    def test_ids_file_rejects_unknown_ids(self):
        tmp = Path("/tmp/opencode-t1-ids.txt")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text("q0\nmissing\n", encoding="utf-8")
        try:
            bench.filter_dataset(make_dataset(5), ids_file=str(tmp))
        except ValueError as exc:
            assert "not in the dataset" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("unknown ids must raise")

    def test_max_questions_applies_after_sharding(self):
        dataset = make_dataset(10)
        filtered = bench.filter_dataset(dataset, shard=(0, 2), max_questions=3)
        assert [row["question_id"] for row in filtered] == ["q0", "q2", "q4"]


class TestSessionMetrics:
    def test_recall_and_ndcg_single_gold(self):
        metrics = bench.session_metrics(["s1", "s2", "s3"], {"s2"})
        assert metrics["session_recall_at_1"] == 0
        assert metrics["session_recall_at_5"] == 1
        assert metrics["session_recall_at_10"] == 1
        # NDCG@5 = (1/log2(3)) / (1/log2(2)) with one relevant session.
        expected = (1 / math.log2(3)) / 1.0
        assert abs(metrics["session_ndcg_at_5"] - expected) < 1e-9

    def test_ndcg_two_gold_sessions(self):
        metrics = bench.session_metrics(["s3", "s1", "s4"], {"s1", "s4"})
        expected = (1 / math.log2(3) + 1 / math.log2(4)) / (
            1 / math.log2(2) + 1 / math.log2(3)
        )
        assert abs(metrics["session_ndcg_at_5"] - expected) < 1e-9
        assert metrics["session_recall_at_1"] == 0
        assert metrics["session_recall_at_5"] == 1

    def test_rank_one_gold_is_perfect(self):
        metrics = bench.session_metrics(["s1", "s2"], {"s1"})
        assert metrics["session_recall_at_1"] == 1
        assert abs(metrics["session_ndcg_at_5"] - 1.0) < 1e-9

    def test_no_gold_is_zero(self):
        metrics = bench.session_metrics(["s1"], set())
        assert metrics["session_recall_at_5"] == 0
        assert metrics["session_ndcg_at_5"] == 0


class TestSessionRankOrder:
    def test_first_occurrence_order_and_dedup(self):
        results = [
            {"id": "m1"},
            {"id": "m2"},
            {"id": "m1"},
            {"id": "m3"},
            {"id": "mX"},  # unmapped
        ]
        mapping = {"m1": "s1", "m2": "s2", "m3": "s1"}
        assert bench.session_rank_order(results, mapping) == ["s1", "s2"]


class TestRetrievalRowContract:
    def test_row_shape(self):
        item = {"question_id": "q1", "question": "Q", "question_type": "multi-session"}
        results = [
            {"id": "m1", "content": "alpha"},
            {"id": "m2", "content": "beta"},
        ]
        row = bench.build_retrieval_row(
            item,
            results,
            {"m1": "s1", "m2": "s2"},
            {"session_recall_at_5": 1},
            {"isolation": "per-question", "run_id": "t1-test"},
        )
        assert row["question_id"] == "q1"
        assert row["is_abstention"] is False
        assert [r["rank"] for r in row["retrieved"]] == [1, 2]
        assert row["retrieved"][0] == {
            "rank": 1,
            "memory_id": "m1",
            "session_id": "s1",
            "content": "alpha",
        }
        assert row["retrieval"]["session_recall_at_5"] == 1
        assert row["provenance"]["isolation"] == "per-question"

    def test_abstention_flag(self):
        item = {"question_id": "q9_abs", "question": "Q", "question_type": "multi-session"}
        row = bench.build_retrieval_row(item, [], {}, {}, {})
        assert row["is_abstention"] is True
        assert row["retrieved"] == []
