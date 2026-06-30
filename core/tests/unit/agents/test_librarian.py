"""Tests for the Multi-Agent Librarian System (recovered 2026-06-18)."""


class TestExtractedMemory:
    """Test the ExtractedMemory dataclass."""

    def test_default_construction(self):
        from whitemagic.agents.librarian import ExtractedMemory

        m = ExtractedMemory(content="hello", title="test")
        assert m.content == "hello"
        assert m.title == "test"
        assert m.tags == []
        assert m.confidence == 0.5
        assert m.source == "unknown"
        assert m.timestamp  # auto-populated


class TestLibrarianAgent:
    """Test the extraction agent."""

    def test_extract_from_text_with_remember(self):
        from whitemagic.agents.librarian import InMemoryStorage, LibrarianAgent

        agent = LibrarianAgent(storage=InMemoryStorage())
        text = (
            "Note: this is an important finding about memory. Remember: dragons exist."
        )
        extracted = agent.extract_from_text(text, source="test")

        assert len(extracted) >= 1
        # The "Note:" or "Remember:" pattern should match
        tags = [e.tags for e in extracted]
        assert any("extracted" in t for t in tags)

    def test_extract_from_text_short_content_filtered(self):
        from whitemagic.agents.librarian import InMemoryStorage, LibrarianAgent

        agent = LibrarianAgent(storage=InMemoryStorage())
        # Very short content should be filtered out
        text = "Note: hi."
        extracted = agent.extract_from_text(text)
        # All should be >15 chars
        for e in extracted:
            assert len(e.content) > 15

    def test_extract_questions(self):
        from whitemagic.agents.librarian import InMemoryStorage, LibrarianAgent

        agent = LibrarianAgent(storage=InMemoryStorage())
        text = "What is the meaning of life and how do we find it?"
        extracted = agent.extract_from_text(text)
        # Should extract a question
        question_extracted = [e for e in extracted if "question" in e.tags]
        assert len(question_extracted) >= 1

    def test_extract_from_conversation(self):
        from whitemagic.agents.librarian import InMemoryStorage, LibrarianAgent

        agent = LibrarianAgent(storage=InMemoryStorage())
        messages = [
            {
                "role": "user",
                "content": "Note: this is important context for the system",
            },
            {
                "role": "assistant",
                "content": "I have decided to implement the new design.",
            },
        ]
        extracted = agent.extract_from_conversation(messages)
        # Should extract from both messages
        sources = {e.source for e in extracted}
        assert "conversation_user" in sources or "conversation_assistant" in sources

    def test_store_extracted(self):
        from whitemagic.agents.librarian import (
            ExtractedMemory,
            InMemoryStorage,
            LibrarianAgent,
        )

        storage = InMemoryStorage()
        agent = LibrarianAgent(storage=storage)
        extracted = [
            ExtractedMemory(content="x" * 50, title="t1", tags=["a"], confidence=0.6),
            ExtractedMemory(content="y" * 50, title="t2", tags=["b"], confidence=0.7),
        ]
        stored = agent.store_extracted(extracted)
        assert len(stored) == 2
        assert len(storage.memories) == 2


class TestEditorAgent:
    """Test the editor / hygiene agent."""

    def test_calculate_similarity(self):
        from whitemagic.agents.librarian import EditorAgent

        e = EditorAgent()
        assert e._calculate_similarity("hello world", "hello world") == 1.0
        assert e._calculate_similarity("hello world", "goodbye world") < 1.0
        assert e._calculate_similarity("hello world", "xyz abc") == 0.0
        assert e._calculate_similarity("", "anything") == 0.0

    def test_find_duplicates(self):
        from whitemagic.agents.librarian import EditorAgent

        e = EditorAgent()
        memories = [
            {"content": "the quick brown fox jumps"},
            {"content": "the quick brown fox jumps over"},  # very similar
            {"content": "completely different content here"},  # not similar
            {"content": "another unrelated entry"},
        ]
        dups = e.find_duplicates(memories, threshold=0.7)
        # Should find at least one duplicate pair
        assert len(dups) >= 1
        # The very-similar pair should be detected
        indices = [(d[0], d[1]) for d in dups]
        assert (0, 1) in indices or (0, 1)[::-1] in indices

    def test_merge_duplicates(self):
        from whitemagic.agents.librarian import EditorAgent

        e = EditorAgent()
        memories = [
            {"content": "alpha beta gamma", "tags": ["a"], "importance": 0.5},
            {"content": "alpha beta delta", "tags": ["b"], "importance": 0.8},
            {"content": "completely different", "tags": ["c"], "importance": 0.3},
        ]
        # (0, 1) are duplicates
        merged = e.merge_duplicates(memories, [(0, 1, 0.8)])
        # Should be 2 memories (0+1 merged, 2 alone)
        assert len(merged) == 2
        # The higher-importance one (0.8) should be the survivor
        # It should have unioned tags
        survivor = merged[0]
        assert "a" in survivor["tags"]
        assert "b" in survivor["tags"]


class TestPlannerAgent:
    """Test the planner agent."""

    def test_extract_tasks(self):
        from whitemagic.agents.librarian import PlannerAgent

        p = PlannerAgent()
        memories = [
            {"id": "m1", "content": "Implement the new API. Then test it."},
            {"id": "m2", "content": "Just a thought, no action here."},
            {"id": "m3", "content": "Refactor the memory subsystem carefully."},
        ]
        tasks = p.extract_tasks_from_memories(memories)
        # Should extract "Implement..." and "Refactor..."
        verbs = {t["verb"] for t in tasks}
        assert "implement" in verbs
        assert "refactor" in verbs

    def test_plan_from_goal(self):
        from whitemagic.agents.librarian import PlannerAgent

        p = PlannerAgent()
        plan = p.plan_from_goal(
            "Implement the new feature",
            memories=[
                {"id": "m1", "content": "Implement the new feature with care."},
                {"id": "m2", "content": "unrelated content here"},
            ],
        )
        assert plan["goal"] == "Implement the new feature"
        assert plan["task_count"] >= 1
        assert plan["relevant_memories"] >= 1


class TestInMemoryStorage:
    """Test the default in-memory storage."""

    def test_basic_create(self):
        from whitemagic.agents.librarian import InMemoryStorage

        s = InMemoryStorage()
        r = s.create_memory(title="t", content="c", tags=["x"])
        assert r["success"] is True
        assert r["title"] == "t"
        assert len(s.memories) == 1

    def test_multiple_creates(self):
        from whitemagic.agents.librarian import InMemoryStorage

        s = InMemoryStorage()
        for i in range(5):
            s.create_memory(title=f"t{i}", content=f"c{i}")
        assert len(s.memories) == 5
