"""Tests for hierarchical workspace loader."""

import pytest
from pathlib import Path
from whitemagic.workspace_loader import (
    WorkspaceLoader,
    load_workspace_for_task,
    DirectoryInfo,
    WorkspaceContext
)


@pytest.fixture
def workspace_root(tmp_path):
    """Create a temporary workspace structure for testing."""
    # Create directory structure
    (tmp_path / "whitemagic").mkdir()
    (tmp_path / "whitemagic" / "core.py").touch()
    (tmp_path / "whitemagic" / "utils.py").touch()
    
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_core.py").touch()
    
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guides").mkdir()
    (tmp_path / "docs" / "archive").mkdir()
    (tmp_path / "docs" / "README.md").touch()
    
    (tmp_path / "backups").mkdir()
    (tmp_path / "backups" / "backup1.tar.gz").touch()
    
    (tmp_path / "README.md").touch()
    (tmp_path / "CHANGELOG.md").touch()
    
    return tmp_path


class TestWorkspaceLoader:
    """Test suite for WorkspaceLoader."""
    
    def test_initialization(self, workspace_root):
        """Test loader initialization."""
        loader = WorkspaceLoader(workspace_root)
        assert loader.workspace_root == workspace_root.resolve()
        assert isinstance(loader._dir_cache, dict)
    
    def test_detect_task_type_implementation(self, workspace_root):
        """Test task type detection for implementation tasks."""
        loader = WorkspaceLoader(workspace_root)
        
        assert loader._detect_task_type("Implement new feature") == "implementation"
        assert loader._detect_task_type("Create symbolic reasoning") == "implementation"
        assert loader._detect_task_type("Add metrics dashboard") == "implementation"
    
    def test_detect_task_type_debugging(self, workspace_root):
        """Test task type detection for debugging tasks."""
        loader = WorkspaceLoader(workspace_root)
        
        assert loader._detect_task_type("Fix import error") == "debugging"
        assert loader._detect_task_type("Debug memory leak") == "debugging"
        assert loader._detect_task_type("Resolve bug in core") == "debugging"
    
    def test_detect_task_type_documentation(self, workspace_root):
        """Test task type detection for documentation tasks."""
        loader = WorkspaceLoader(workspace_root)
        
        assert loader._detect_task_type("Update documentation") == "documentation"
        assert loader._detect_task_type("Write guide for API") == "documentation"
        assert loader._detect_task_type("Document new features") == "documentation"
    
    def test_detect_task_type_testing(self, workspace_root):
        """Test task type detection for testing tasks."""
        loader = WorkspaceLoader(workspace_root)
        
        assert loader._detect_task_type("Test new module") == "testing"
        assert loader._detect_task_type("Verify functionality") == "testing"
        assert loader._detect_task_type("Validate changes") == "testing"
    
    def test_extract_keywords(self, workspace_root):
        """Test keyword extraction."""
        loader = WorkspaceLoader(workspace_root)
        
        keywords = loader._extract_keywords("Implement symbolic reasoning module")
        assert "implement" in keywords
        assert "symbolic" in keywords
        assert "reasoning" in keywords
        assert "module" in keywords
        
        # Should filter stop words
        assert "the" not in keywords
        assert "a" not in keywords
    
    def test_load_for_task_tier_0(self, workspace_root):
        """Test tier 0 loading (minimal)."""
        loader = WorkspaceLoader(workspace_root)
        
        context = loader.load_for_task("Implement new feature", tier=0)
        
        assert context["task_type"] == "implementation"
        assert context["tier"] == 0
        assert "structure" in context
        assert context["lazy_load_available"] is True
        assert context["token_estimate"] < 5000  # Should be small
    
    def test_load_for_task_tier_1(self, workspace_root):
        """Test tier 1 loading (balanced)."""
        loader = WorkspaceLoader(workspace_root)
        
        context = loader.load_for_task("Implement new feature", tier=1)
        
        assert context["tier"] == 1
        assert context["token_estimate"] > 0
        # Tier 1 should have more than tier 0
        context_0 = loader.load_for_task("Implement new feature", tier=0)
        assert context["token_estimate"] >= context_0["token_estimate"]
    
    def test_load_for_task_tier_2(self, workspace_root):
        """Test tier 2 loading (full)."""
        loader = WorkspaceLoader(workspace_root)
        
        context = loader.load_for_task("Implement new feature", tier=2)
        
        assert context["tier"] == 2
        assert context["lazy_load_available"] is False
        # Should be most comprehensive
    
    def test_should_exclude_patterns(self, workspace_root):
        """Test exclusion of common patterns."""
        loader = WorkspaceLoader(workspace_root)
        
        # Should exclude
        assert loader._should_exclude(Path("node_modules/something"))
        assert loader._should_exclude(Path(".git/config"))
        assert loader._should_exclude(Path("__pycache__/file.pyc"))
        assert loader._should_exclude(Path("backups/backup.tar.gz"))
        
        # Should not exclude
        assert not loader._should_exclude(Path("whitemagic/core.py"))
        assert not loader._should_exclude(Path("tests/test_core.py"))
    
    def test_get_lazy_loadable_dirs(self, workspace_root):
        """Test getting list of lazy-loadable directories."""
        loader = WorkspaceLoader(workspace_root)
        
        dirs = loader.get_lazy_loadable_dirs()
        
        assert "whitemagic" in dirs
        assert "tests" in dirs
        assert "docs" in dirs
        # Should not include excluded patterns
        assert "backups" not in dirs  # In DEFAULT_EXCLUDES
    
    def test_load_directory_on_demand(self, workspace_root):
        """Test loading a specific directory on-demand."""
        loader = WorkspaceLoader(workspace_root)
        
        structure = loader.load_directory("whitemagic", max_depth=2)
        
        assert structure["name"] == "whitemagic"
        assert "items" in structure
        assert structure["token_estimate"] > 0
        
        # Should contain files
        file_names = [item["name"] for item in structure["items"] if item.get("type") == "file"]
        assert "core.py" in file_names
        assert "utils.py" in file_names
    
    def test_load_directory_nonexistent(self, workspace_root):
        """Test loading a non-existent directory raises error."""
        loader = WorkspaceLoader(workspace_root)
        
        with pytest.raises(ValueError, match="Directory not found"):
            loader.load_directory("nonexistent")
    
    def test_additional_paths(self, workspace_root):
        """Test including additional paths explicitly."""
        loader = WorkspaceLoader(workspace_root)
        
        # Create a special directory
        (workspace_root / "special").mkdir()
        (workspace_root / "special" / "file.txt").touch()
        
        context = loader.load_for_task(
            "Test task",
            tier=0,
            additional_paths=["special"]
        )
        
        # Special directory should be included
        dir_paths = [d["path"] for d in context["structure"]["directories"]]
        assert any("special" in path for path in dir_paths)
    
    def test_token_estimate_calculation(self, workspace_root):
        """Test that token estimates are reasonable."""
        loader = WorkspaceLoader(workspace_root)
        
        context_0 = loader.load_for_task("Test task", tier=0)
        context_1 = loader.load_for_task("Test task", tier=1)
        context_2 = loader.load_for_task("Test task", tier=2)
        
        # Each tier should have more tokens than the previous
        assert context_0["token_estimate"] <= context_1["token_estimate"]
        assert context_1["token_estimate"] <= context_2["token_estimate"]
        
        # All should be positive
        assert context_0["token_estimate"] > 0
        assert context_1["token_estimate"] > 0
        assert context_2["token_estimate"] > 0


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_load_workspace_for_task(self, workspace_root):
        """Test the convenience wrapper function."""
        context = load_workspace_for_task(
            str(workspace_root),
            "Implement new feature",
            tier=0
        )
        
        assert context["task_type"] == "implementation"
        assert context["tier"] == 0
        assert "structure" in context
        assert context["token_estimate"] > 0
    
    def test_load_with_additional_paths(self, workspace_root):
        """Test convenience function with additional paths."""
        (workspace_root / "custom").mkdir()
        
        context = load_workspace_for_task(
            str(workspace_root),
            "Test task",
            tier=0,
            additional_paths=["custom"]
        )
        
        assert context["tier"] == 0
        # Custom path should be included
        dir_paths = [d["path"] for d in context["structure"]["directories"]]
        assert any("custom" in path for path in dir_paths)


class TestDirectoryInfo:
    """Test DirectoryInfo dataclass."""
    
    def test_directory_info_creation(self):
        """Test creating DirectoryInfo instances."""
        info = DirectoryInfo(
            path=Path("/test"),
            name="test",
            file_count=5,
            subdirs=["sub1", "sub2"],
            relevance_score=0.8,
            description="Test directory"
        )
        
        assert info.path == Path("/test")
        assert info.name == "test"
        assert info.file_count == 5
        assert len(info.subdirs) == 2
        assert info.relevance_score == 0.8
        assert info.description == "Test directory"
    
    def test_directory_info_defaults(self):
        """Test DirectoryInfo with default values."""
        info = DirectoryInfo(
            path=Path("/test"),
            name="test",
            file_count=0,
            subdirs=[]
        )
        
        assert info.relevance_score == 0.0
        assert info.description is None
