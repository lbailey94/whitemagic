# ruff: noqa: BLE001
"""Tests for the self-prompting autonomous work queue."""

from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestSelfPrompting:
    """Test the self-prompting work queue."""

    def test_queue_work(self):
        from whitemagic.core.consciousness.self_prompting import queue_work, get_queue_status, clear_completed
        clear_completed()
        item_id = queue_work("test task", priority=5)
        assert len(item_id) > 0
        status = get_queue_status()
        assert status["total"] >= 1

    def test_priority_ordering(self):
        from whitemagic.core.consciousness.self_prompting import (
            queue_work, _load_queue, clear_completed, Priority,
        )
        clear_completed()
        queue_work("low priority", priority=Priority.LOW)
        queue_work("critical", priority=Priority.CRITICAL)
        queue_work("normal", priority=Priority.NORMAL)
        items = _load_queue()
        pending = sorted([i for i in items if i.status == "pending"], key=lambda i: i.priority)
        assert pending[0].task == "critical"

    def test_process_queue(self):
        from whitemagic.core.consciousness.self_prompting import (
            queue_work, process_queue, clear_completed,
        )
        clear_completed()
        queue_work("process me", priority=1)
        results = process_queue(limit=10)
        assert results["processed"] >= 1

    def test_ask_human(self):
        from whitemagic.core.consciousness.self_prompting import (
            ask_human, get_pending_questions, answer_question, clear_completed,
        )
        qid = ask_human("What should I do?", context="testing")
        questions = get_pending_questions()
        assert len(questions) >= 1
        found = answer_question(qid, "Do the thing")
        assert found is True

    def test_clear_completed(self):
        from whitemagic.core.consciousness.self_prompting import (
            queue_work, process_queue, clear_completed,
        )
        clear_completed()
        queue_work("to be completed", priority=1)
        process_queue(limit=10)
        removed = clear_completed()
        assert removed >= 1

    def test_register_handler(self):
        from whitemagic.core.consciousness.self_prompting import (
            register_handler, queue_work, process_queue, clear_completed,
        )
        clear_completed()
        called = []
        def custom_handler(item):
            called.append(item.task)
            return "custom result"
        register_handler("test_handler", custom_handler)
        queue_work("custom task", handler="test_handler", priority=1)
        process_queue(limit=10)
        assert "custom task" in called

    def test_work_item_from_dict(self):
        from whitemagic.core.consciousness.self_prompting import WorkItem
        item = WorkItem.from_dict({"task": "test", "priority": 5, "status": "pending"})
        assert item.task == "test"
        assert item.priority == 5

    def test_max_attempts(self):
        from whitemagic.core.consciousness.self_prompting import (
            register_handler, queue_work, process_queue, clear_completed, _load_queue,
        )
        clear_completed()
        def failing_handler(item):
            raise RuntimeError("intentional failure")
        register_handler("fail_handler", failing_handler)
        queue_work("failing task", handler="fail_handler", priority=1)
        # Process multiple times to exhaust attempts
        for _ in range(4):
            process_queue(limit=10)
        items = _load_queue()
        failed = [i for i in items if i.task == "failing task" and i.status == "failed"]
        assert len(failed) == 1
