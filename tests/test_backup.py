"""
Tests for WhiteMagic Backup and Restore System
Phase 2A.5 - Day 4
"""

import json
import tempfile
from pathlib import Path
import pytest

from whitemagic.backup import BackupManager


class TestBackupManager:
    """Test BackupManager functionality."""
    
    def test_init(self, tmp_path):
        """Test BackupManager initialization."""
        backup_mgr = BackupManager(tmp_path)
        assert backup_mgr.base_dir == tmp_path
        assert backup_mgr.whitemagic_dir == tmp_path / "whitemagic"
        assert backup_mgr.backup_dir == tmp_path / "backups"
        assert backup_mgr.backup_dir.exists()
    
    def test_create_backup(self, tmp_path):
        """Test backup creation."""
        # Setup: create test memory files
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        test_file = short_term_dir / "test_memory.md"
        test_file.write_text("# Test Memory\nTest content")
        
        # Create backup
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.create_backup()
        
        assert result["success"]
        assert "backup_path" in result
        assert "manifest_path" in result
        assert Path(result["backup_path"]).exists()
        assert Path(result["manifest_path"]).exists()
        
        # Verify manifest
        manifest = result["manifest"]
        assert manifest["version"] == "2.1.1"
        assert manifest["stats"]["total_files"] == 1
        assert "timestamp" in manifest
    
    def test_list_backups(self, tmp_path):
        """Test listing backups."""
        backup_mgr = BackupManager(tmp_path)
        
        # Create whitemagic dir with a file
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        # Add a test file so backup isn't completely empty
        (short_term_dir / "test.md").write_text("Test content")
        
        # Create a backup (let it auto-name)
        result = backup_mgr.create_backup()
        assert result["success"]
        
        # List backups
        backups = backup_mgr.list_backups()
        
        # Should have at least 1 backup
        assert len(backups) >= 1, f"Expected at least 1 backup, got {len(backups)}. Backup dir: {backup_mgr.backup_dir}, files: {list(backup_mgr.backup_dir.glob('*'))}"
        
        for backup in backups:
            assert "path" in backup
            assert "name" in backup
            assert "size_mb" in backup
            assert "created" in backup
            assert "has_manifest" in backup
    
    def test_verify_backup(self, tmp_path):
        """Test backup verification."""
        # Setup
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        test_file = short_term_dir / "test.md"
        test_file.write_text("Test content")
        
        # Create backup
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.create_backup()
        backup_path = Path(result["backup_path"])
        
        # Verify
        verification = backup_mgr.verify_backup(backup_path)
        assert verification["valid"]
        assert verification["has_manifest"]
        assert verification["manifest_valid"]
        assert verification["file_count"] > 0
    
    def test_verify_missing_backup(self, tmp_path):
        """Test verification of non-existent backup."""
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.verify_backup(tmp_path / "nonexistent.tar.gz")
        
        assert not result["valid"]
        assert "error" in result
    
    def test_restore_backup_dry_run(self, tmp_path):
        """Test restore dry run."""
        # Setup
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        test_file = short_term_dir / "test.md"
        test_file.write_text("Test content")
        
        # Create backup
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.create_backup()
        backup_path = Path(result["backup_path"])
        
        # Dry run restore
        restore_result = backup_mgr.restore_backup(
            backup_path,
            dry_run=True
        )
        
        assert restore_result["success"]
        assert restore_result["dry_run"]
        assert "files_to_restore" in restore_result
        assert restore_result["total_files"] > 0
    
    def test_restore_backup_full(self, tmp_path):
        """Test full backup restore."""
        # Setup original data
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        test_file = short_term_dir / "test.md"
        original_content = "Original content"
        test_file.write_text(original_content)
        
        # Create backup
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.create_backup()
        backup_path = Path(result["backup_path"])
        
        # Modify file
        test_file.write_text("Modified content")
        
        # Create new target directory for restore
        restore_dir = tmp_path / "restore_test"
        restore_dir.mkdir()
        
        # Restore
        restore_result = backup_mgr.restore_backup(
            backup_path,
            target_dir=restore_dir,
            dry_run=False
        )
        
        assert restore_result["success"]
        assert restore_result["total_files"] > 0
        assert "pre_restore_backup" in restore_result
        
        # Verify restored content
        restored_file = restore_dir / "whitemagic" / "short_term" / "test.md"
        assert restored_file.exists()
        assert restored_file.read_text() == original_content
    
    def test_backup_with_no_compress(self, tmp_path):
        """Test uncompressed backup."""
        # Setup
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        test_file = short_term_dir / "test.md"
        test_file.write_text("Test content")
        
        # Create uncompressed backup
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.create_backup(compress=False)
        
        assert result["success"]
        backup_path = Path(result["backup_path"])
        assert backup_path.suffix == ".tar"
        assert backup_path.exists()
    
    def test_manifest_checksums(self, tmp_path):
        """Test that manifest includes file checksums."""
        # Setup
        whitemagic_dir = tmp_path / "whitemagic"
        short_term_dir = whitemagic_dir / "short_term"
        short_term_dir.mkdir(parents=True)
        
        test_file = short_term_dir / "test.md"
        test_file.write_text("Test content with checksum")
        
        # Create backup
        backup_mgr = BackupManager(tmp_path)
        result = backup_mgr.create_backup()
        
        manifest = result["manifest"]
        assert "files" in manifest
        
        # Check that files have checksums
        for file_path, file_info in manifest["files"].items():
            assert "sha256" in file_info
            assert "size" in file_info
            assert len(file_info["sha256"]) == 64  # SHA-256 hex length


class TestCLIIntegration:
    """Test CLI integration for backup commands."""
    
    def test_cli_backup_help(self):
        """Test that CLI backup help is available."""
        from cli import build_parser
        
        parser = build_parser()
        
        # Should not raise
        help_text = parser.format_help()
        assert "backup" in help_text
        assert "restore-backup" in help_text
        assert "list-backups" in help_text
        assert "verify-backup" in help_text
