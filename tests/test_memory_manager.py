import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from whitemagic import MemoryManager


class MemoryManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base_path = Path(self._tmpdir.name)
        self.manager = MemoryManager(base_dir=self.base_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_create_memory_updates_metadata_and_files(self) -> None:
        path = self.manager.create_memory(
            title="Test Memory",
            content="Some useful insight.",
            memory_type="short_term",
            tags=["example"],
        )
        self.assertTrue(path.exists())

        metadata_path = self.base_path / "memory" / "metadata.json"
        raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        index = raw_metadata["memory_index"]
        self.assertEqual(len(index), 1)
        entry = index[0]
        self.assertEqual(entry["title"], "Test Memory")
        self.assertEqual(entry["tags"], ["example"])
        self.assertEqual(entry["type"], "short_term")

    def test_search_matches_titles_tags_and_content(self) -> None:
        self.manager.create_memory(
            title="Debugging Pattern",
            content="Always check the cache headers first.",
            memory_type="short_term",
            tags=["heuristic", "debugging"],
        )

        results = self.manager.search_memories(query="cache")
        self.assertEqual(len(results), 1)
        entry = results[0]["entry"]
        self.assertEqual(entry["title"], "Debugging Pattern")

        tag_results = self.manager.search_memories(tags=["debugging"])
        self.assertEqual(len(tag_results), 1)

    def test_context_summary_removes_frontmatter(self) -> None:
        self.manager.create_memory(
            title="Session Insight",
            content="## Key Finding\nCaching reduced latency by 30%.",
            memory_type="short_term",
            tags=["performance"],
        )
        self.manager.create_memory(
            title="Reusable Heuristic",
            content="Prefer async requests when waiting on IO bound tasks.",
            memory_type="long_term",
            tags=["performance", "heuristic"],
        )

        summary = self.manager.generate_context_summary(1)
        self.assertIn("Session Insight", summary)
        self.assertNotIn("title:", summary)  # frontmatter removed
        self.assertLess(len(summary), 1800)

    def test_consolidation_archives_and_promotes(self) -> None:
        path = self.manager.create_memory(
            title="Heuristic to Promote",
            content="Documented pattern worth keeping.",
            memory_type="short_term",
            tags=["heuristic"],
        )

        old_timestamp = datetime.now() - timedelta(days=10)
        os.utime(
            path,
            (old_timestamp.timestamp(), old_timestamp.timestamp()),
        )

        result = self.manager.consolidate_short_term(dry_run=False)

        self.assertGreaterEqual(result["archived"], 1)
        self.assertGreaterEqual(result["auto_promoted"], 1)
        archive_contents = list(self.manager.archive_dir.glob("*.md"))
        self.assertTrue(archive_contents)

        archived_entry = self.manager.list_all_memories(
            include_archived=True
        )["archived"][0]
        self.assertEqual(archived_entry["status"], "archived")

    def test_delete_memory_archives_by_default(self) -> None:
        path = self.manager.create_memory(
            title="Temporary Memory",
            content="This will be deleted.",
            memory_type="short_term",
            tags=["temp"],
        )
        filename = path.name

        result = self.manager.delete_memory(filename, permanent=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "archived")
        self.assertFalse(path.exists())
        
        # Check it's in archive
        archived = self.manager.list_all_memories(include_archived=True)["archived"]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["status"], "archived")

    def test_delete_memory_permanent(self) -> None:
        path = self.manager.create_memory(
            title="Disposable Memory",
            content="This will be permanently deleted.",
            memory_type="short_term",
            tags=["temp"],
        )
        filename = path.name

        result = self.manager.delete_memory(filename, permanent=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "permanently_deleted")
        self.assertFalse(path.exists())
        
        # Should not be in index or archive
        all_memories = self.manager.list_all_memories(include_archived=True)
        self.assertEqual(len(all_memories["short_term"]), 0)
        self.assertEqual(len(all_memories.get("archived", [])), 0)

    def test_update_memory_tags(self) -> None:
        path = self.manager.create_memory(
            title="Updateable Memory",
            content="Original content.",
            memory_type="short_term",
            tags=["original", "test"],
        )
        filename = path.name

        # Add tags
        result = self.manager.update_memory(
            filename, add_tags=["new", "additional"]
        )
        self.assertTrue(result["success"])
        
        entry = self.manager._index[filename]
        self.assertIn("new", entry["tags"])
        self.assertIn("additional", entry["tags"])
        self.assertIn("original", entry["tags"])
        
        # Remove tags
        result = self.manager.update_memory(
            filename, remove_tags=["original"]
        )
        self.assertTrue(result["success"])
        
        entry = self.manager._index[filename]
        self.assertNotIn("original", entry["tags"])
        self.assertIn("new", entry["tags"])

    def test_update_memory_content(self) -> None:
        path = self.manager.create_memory(
            title="Content Test",
            content="Original content.",
            memory_type="short_term",
            tags=["test"],
        )
        filename = path.name

        new_content = "Updated content with more details."
        result = self.manager.update_memory(filename, content=new_content)
        
        self.assertTrue(result["success"])
        
        # Read and verify
        entry = self.manager._index[filename]
        _, body = self.manager._read_memory_file(entry)
        self.assertIn("Updated content", body)
        self.assertNotIn("Original content", body)

    def test_list_all_tags(self) -> None:
        self.manager.create_memory(
            title="Memory 1", content="Content", 
            memory_type="short_term", tags=["tag1", "tag2"]
        )
        self.manager.create_memory(
            title="Memory 2", content="Content",
            memory_type="short_term", tags=["tag1", "tag3"]
        )
        self.manager.create_memory(
            title="Memory 3", content="Content",
            memory_type="long_term", tags=["tag2", "tag4"]
        )

        tags_info = self.manager.list_all_tags()

        self.assertEqual(tags_info["total_unique_tags"], 4)
        tag_names = [t["tag"] for t in tags_info["tags"]]
        self.assertIn("tag1", tag_names)
        self.assertIn("tag2", tag_names)
        self.assertIn("tag3", tag_names)
        self.assertIn("tag4", tag_names)
        
        # tag1 appears twice
        tag1_info = next(t for t in tags_info["tags"] if t["tag"] == "tag1")
        self.assertEqual(tag1_info["count"], 2)

    def test_tag_normalization(self) -> None:
        # Tags should be normalized to lowercase
        self.manager.create_memory(
            title="Case Test",
            content="Testing case normalization.",
            memory_type="short_term",
            tags=["Heuristic", "PATTERN", "MixedCase"],
        )

        tags_info = self.manager.list_all_tags()
        tag_names = [t["tag"] for t in tags_info["tags"]]
        
        # All should be lowercase due to normalization
        self.assertIn("heuristic", tag_names)
        self.assertIn("pattern", tag_names)
        self.assertIn("mixedcase", tag_names)

    def test_sort_by_accessed(self) -> None:
        # Create memories
        mem1 = self.manager.create_memory(
            title="Memory 1", content="Content 1",
            memory_type="short_term", tags=["test"]
        )
        mem2 = self.manager.create_memory(
            title="Memory 2", content="Content 2",
            memory_type="short_term", tags=["test"]
        )

        # Access mem1 to update its access time
        self.manager.read_recent_memories(memory_type="short_term", limit=1)
        
        # List by accessed time
        listing = self.manager.list_all_memories(sort_by="accessed")
        
        # First entry should be mem1 (most recently accessed)
        self.assertEqual(listing["short_term"][0]["filename"], mem1.name)
    
    def test_tag_removal_with_legacy_mixed_case(self) -> None:
        """Test that tag removal works with legacy mixed-case tags."""
        # Create memory with mixed-case tag (simulating legacy data)
        path = self.manager.create_memory(
            title="Legacy Memory",
            content="Has mixed case tag",
            memory_type="short_term",
            tags=["test"],
        )
        filename = path.name
        
        # Manually inject a mixed-case tag to simulate legacy data
        entry = self.manager._index[filename]
        entry["tags"] = ["Heuristic", "test"]  # Mixed case
        
        # Try to remove using lowercase
        result = self.manager.update_memory(
            filename, remove_tags=["heuristic"]
        )
        
        self.assertTrue(result["success"])
        
        # Verify the mixed-case tag was removed
        updated_entry = self.manager._index[filename]
        self.assertNotIn("Heuristic", updated_entry["tags"])
        self.assertNotIn("heuristic", updated_entry["tags"])
        self.assertIn("test", updated_entry["tags"])
    
    def test_tag_replacement_normalizes(self) -> None:
        """Test that replacing all tags applies normalization."""
        path = self.manager.create_memory(
            title="Test Memory",
            content="Content",
            memory_type="short_term",
            tags=["old"],
        )
        filename = path.name
        
        # Replace with mixed-case tags
        result = self.manager.update_memory(
            filename, tags=["NewTag", "ANOTHER", "mixed"]
        )
        
        self.assertTrue(result["success"])
        
        # All tags should be normalized to lowercase
        entry = self.manager._index[filename]
        self.assertEqual(sorted(entry["tags"]), ["another", "mixed", "newtag"])
    
    def test_tag_statistics_accuracy(self) -> None:
        """Test that tag statistics report correct values."""
        # Create multiple memories with tags
        self.manager.create_memory(
            "Memory 1", "Content", memory_type="short_term", tags=["tag1", "tag2"]
        )
        self.manager.create_memory(
            "Memory 2", "Content", memory_type="short_term", tags=["tag1"]
        )
        self.manager.create_memory(
            "Memory 3", "Content", memory_type="long_term", tags=["tag2", "tag3"]
        )
        
        stats = self.manager.list_all_tags()
        
        # Should have 3 unique tags
        self.assertEqual(stats["total_unique_tags"], 3)
        
        # Should have 5 total tag usages (tag1: 2, tag2: 2, tag3: 1)
        self.assertEqual(stats["total_tag_usages"], 5)
        
        # Should have 3 memories with tags
        self.assertEqual(stats["total_memories_with_tags"], 3)
    
    def test_restore_memory_from_archive(self) -> None:
        """Test restoring an archived memory."""
        # Create and delete (archive) a memory
        path = self.manager.create_memory(
            title="Archived Memory",
            content="Will be restored",
            memory_type="short_term",
            tags=["archived"],
        )
        filename = path.name
        
        # Archive it
        self.manager.delete_memory(filename, permanent=False)
        
        # Verify it's archived
        entry = self.manager._index[filename]
        self.assertEqual(entry["status"], "archived")
        
        # Restore to long_term
        result = self.manager.restore_memory(filename, memory_type="long_term")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["memory_type"], "long_term")
        
        # Verify it's active and in long_term
        entry = self.manager._index[filename]
        self.assertEqual(entry["status"], "active")
        self.assertEqual(entry["type"], "long_term")
        self.assertIn("long_term", entry["path"])
    
    def test_restore_non_archived_fails(self) -> None:
        """Test that restoring a non-archived memory fails."""
        path = self.manager.create_memory(
            "Active Memory", "Content", memory_type="short_term", tags=["test"]
        )
        filename = path.name
        
        result = self.manager.restore_memory(filename)
        
        self.assertFalse(result["success"])
        self.assertIn("not archived", result["error"])
    
    def test_normalize_legacy_tags_dry_run(self) -> None:
        """Test legacy tag normalization in dry-run mode."""
        # Create memories with mixed-case tags (simulate legacy data)
        path1 = self.manager.create_memory(
            "Memory 1", "Content", memory_type="short_term", tags=["test"]
        )
        path2 = self.manager.create_memory(
            "Memory 2", "Content", memory_type="short_term", tags=["test"]
        )
        
        # Manually inject mixed-case tags
        self.manager._index[path1.name]["tags"] = ["Heuristic", "Performance"]
        self.manager._index[path2.name]["tags"] = ["DEBUG", "Test"]
        
        # Run normalization in dry-run mode
        result = self.manager.normalize_legacy_tags(dry_run=True)
        
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["affected_memories"], 2)
        
        # Changes should be reported
        self.assertEqual(len(result["changes"]), 2)
        
        # But tags should NOT be changed in dry-run
        self.assertEqual(self.manager._index[path1.name]["tags"], ["Heuristic", "Performance"])
        self.assertEqual(self.manager._index[path2.name]["tags"], ["DEBUG", "Test"])
    
    def test_normalize_legacy_tags_applies_changes(self) -> None:
        """Test legacy tag normalization actually applies changes."""
        # Create memory with mixed-case tags
        path = self.manager.create_memory(
            "Legacy Memory", "Content", memory_type="short_term", tags=["test"]
        )
        filename = path.name
        
        # Manually inject mixed-case tags
        self.manager._index[filename]["tags"] = ["Heuristic", "PROVEN", "Debug"]
        
        # Run normalization with dry_run=False
        result = self.manager.normalize_legacy_tags(dry_run=False)
        
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["affected_memories"], 1)
        
        # Tags should be normalized
        normalized_tags = self.manager._index[filename]["tags"]
        self.assertEqual(sorted(normalized_tags), ["debug", "heuristic", "proven"])


if __name__ == "__main__":
    unittest.main()
