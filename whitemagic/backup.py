"""
WhiteMagic Backup and Restore System
Phase 2A.5 - Day 4

Provides full system backup and restore capabilities for WhiteMagic memories,
including incremental backups, verification, and metadata preservation.
"""

import json
import shutil
import tarfile
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup and restore operations for WhiteMagic memory system."""
    
    def __init__(self, base_dir: Path):
        """
        Initialize the backup manager.
        
        Args:
            base_dir: Base directory containing whitemagic folder
        """
        self.base_dir = Path(base_dir)
        self.whitemagic_dir = self.base_dir / "whitemagic"
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(
        self,
        output_path: Optional[Path] = None,
        incremental: bool = False,
        last_backup: Optional[Path] = None,
        compress: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a backup of the WhiteMagic system.
        
        Args:
            output_path: Custom output path (default: backups/backup_TIMESTAMP.tar.gz)
            incremental: Create incremental backup (only changed files)
            last_backup: Path to last backup for incremental comparison
            compress: Whether to compress the backup (tar.gz vs tar)
        
        Returns:
            Dictionary with backup metadata and statistics
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine output path
        if output_path is None:
            ext = "tar.gz" if compress else "tar"
            output_path = self.backup_dir / f"backup_{timestamp}.{ext}"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating backup: {output_path}")
        
        # Collect files to backup
        files_to_backup = self._collect_backup_files(
            incremental=incremental,
            last_backup=last_backup
        )
        
        # Create tarball
        mode = "w:gz" if compress else "w"
        with tarfile.open(output_path, mode) as tar:
            for file_path in files_to_backup:
                arcname = file_path.relative_to(self.base_dir)
                tar.add(file_path, arcname=str(arcname))
        
        # Create manifest
        manifest = self._create_manifest(
            files_to_backup,
            output_path,
            incremental=incremental,
            timestamp=timestamp
        )
        
        # Save manifest alongside backup
        manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, default=str)
        
        logger.info(f"Backup created: {output_path}")
        logger.info(f"Files backed up: {manifest['stats']['total_files']}")
        logger.info(f"Total size: {manifest['stats']['total_size_mb']:.2f} MB")
        
        return {
            "success": True,
            "backup_path": str(output_path),
            "manifest_path": str(manifest_path),
            "manifest": manifest
        }
    
    def restore_backup(
        self,
        backup_path: Path,
        target_dir: Optional[Path] = None,
        verify: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Restore from a backup archive.
        
        Args:
            backup_path: Path to backup tar.gz file
            target_dir: Target directory (default: base_dir)
            verify: Verify backup integrity before restoring
            dry_run: Only show what would be restored
        
        Returns:
            Dictionary with restore results
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return {
                "success": False,
                "error": f"Backup file not found: {backup_path}"
            }
        
        # Verify backup if requested
        if verify:
            verification = self.verify_backup(backup_path)
            if not verification["valid"]:
                return {
                    "success": False,
                    "error": f"Backup verification failed: {verification.get('error')}"
                }
        
        target_dir = target_dir or self.base_dir
        target_dir = Path(target_dir)
        
        logger.info(f"Restoring backup: {backup_path}")
        logger.info(f"Target directory: {target_dir}")
        
        if dry_run:
            # List contents without extracting
            with tarfile.open(backup_path, "r:*") as tar:
                members = tar.getmembers()
                return {
                    "success": True,
                    "dry_run": True,
                    "files_to_restore": [m.name for m in members],
                    "total_files": len(members)
                }
        
        # Create backup of current state before restoring
        pre_restore_backup = self.backup_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        logger.info(f"Creating pre-restore backup: {pre_restore_backup}")
        self.create_backup(output_path=pre_restore_backup)
        
        # Extract backup
        restored_files = []
        with tarfile.open(backup_path, "r:*") as tar:
            members = tar.getmembers()
            for member in members:
                tar.extract(member, target_dir)
                restored_files.append(member.name)
        
        logger.info(f"Restored {len(restored_files)} files")
        
        return {
            "success": True,
            "restored_files": restored_files,
            "total_files": len(restored_files),
            "pre_restore_backup": str(pre_restore_backup),
            "target_dir": str(target_dir)
        }
    
    def verify_backup(self, backup_path: Path) -> Dict[str, Any]:
        """
        Verify backup integrity.
        
        Args:
            backup_path: Path to backup file
        
        Returns:
            Dictionary with verification results
        """
        backup_path = Path(backup_path)
        manifest_path = Path(str(backup_path) + ".manifest.json")
        
        if not backup_path.exists():
            return {
                "valid": False,
                "error": f"Backup file not found: {backup_path}"
            }
        
        # Check if manifest exists
        has_manifest = manifest_path.exists()
        
        # Verify tarball can be opened
        try:
            with tarfile.open(backup_path, "r:*") as tar:
                members = tar.getmembers()
                file_count = len(members)
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to open backup: {str(e)}"
            }
        
        # Load and verify manifest if it exists
        manifest_valid = True
        manifest = None
        if has_manifest:
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                
                # Verify file count matches
                if manifest["stats"]["total_files"] != file_count:
                    manifest_valid = False
            except Exception as e:
                manifest_valid = False
                logger.warning(f"Manifest verification failed: {e}")
        
        return {
            "valid": True,
            "backup_path": str(backup_path),
            "has_manifest": has_manifest,
            "manifest_valid": manifest_valid,
            "file_count": file_count,
            "manifest": manifest
        }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup metadata dictionaries
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("*.tar*")):
            if ".manifest.json" in backup_file.name:
                continue
            
            manifest_path = Path(str(backup_file) + ".manifest.json")
            manifest = None
            
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load manifest for {backup_file}: {e}")
            
            stat = backup_file.stat()
            backups.append({
                "path": str(backup_file),
                "name": backup_file.name,
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "has_manifest": manifest is not None,
                "manifest": manifest
            })
        
        return backups
    
    def _collect_backup_files(
        self,
        incremental: bool = False,
        last_backup: Optional[Path] = None
    ) -> List[Path]:
        """Collect files to include in backup."""
        files = []
        
        # Core directories to backup
        dirs_to_backup = [
            self.whitemagic_dir / "short_term",
            self.whitemagic_dir / "long_term",
            self.whitemagic_dir / "archived",
        ]
        
        # Include memory_index.json if it exists
        index_file = self.whitemagic_dir / "memory_index.json"
        if index_file.exists():
            files.append(index_file)
        
        # Collect all memory files
        for directory in dirs_to_backup:
            if directory.exists():
                for file_path in directory.rglob("*.md"):
                    if incremental and last_backup:
                        # TODO: Implement incremental logic
                        # For now, include all files
                        pass
                    files.append(file_path)
        
        return files
    
    def _create_manifest(
        self,
        files: List[Path],
        backup_path: Path,
        incremental: bool,
        timestamp: str
    ) -> Dict[str, Any]:
        """Create backup manifest with metadata."""
        total_size = sum(f.stat().st_size for f in files)
        
        # Calculate checksums for verification
        file_checksums = {}
        for file_path in files:
            rel_path = str(file_path.relative_to(self.base_dir))
            with open(file_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            file_checksums[rel_path] = {
                "sha256": checksum,
                "size": file_path.stat().st_size
            }
        
        return {
            "version": "2.1.1",
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "backup_path": str(backup_path),
            "incremental": incremental,
            "stats": {
                "total_files": len(files),
                "total_size": total_size,
                "total_size_mb": total_size / (1024 * 1024)
            },
            "files": file_checksums
        }
