"""Version Sync System

Prevents version drift by enforcing single source of truth (VERSION file)
and auto-updating all references throughout the project.
"""

from pathlib import Path
from typing import List, Dict, Tuple
import re

class VersionSyncSystem:
    """Automatic version synchronization across project"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.version_file = self.base_dir / "VERSION"
        self.current_version = self._read_version()
    
    def _read_version(self) -> str:
        """Read current version from VERSION file"""
        if not self.version_file.exists():
            return "unknown"
        return self.version_file.read_text().strip()
    
    def check_drift(self) -> Dict[str, List[Tuple[Path, str]]]:
        """Check for version drift across project
        
        Returns:
            Dict mapping incorrect versions to list of (file, line) tuples
        """
        drift = {}
        version_pattern = re.compile(r'v?(\d+\.\d+\.\d+)')
        
        # Check documentation
        for md_file in self.base_dir.glob("docs/**/*.md"):
            if 'archive' in str(md_file):
                continue  # Skip archived files
            
            content = md_file.read_text()
            for match in version_pattern.finditer(content):
                found_version = match.group(1)
                if found_version != self.current_version:
                    if found_version not in drift:
                        drift[found_version] = []
                    drift[found_version].append((md_file, match.group(0)))
        
        # Check Python files
        for py_file in self.base_dir.glob("whitemagic/**/*.py"):
            if '__pycache__' in str(py_file):
                continue
            
            content = py_file.read_text()
            if 'version' in content.lower():
                for match in version_pattern.finditer(content):
                    found_version = match.group(1)
                    if found_version != self.current_version:
                        if found_version not in drift:
                            drift[found_version] = []
                        drift[found_version].append((py_file, match.group(0)))
        
        return drift
    
    def fix_drift(self, dry_run: bool = True) -> int:
        """Fix version drift by updating to current version
        
        Args:
            dry_run: If True, only report what would be changed
        
        Returns:
            Number of files that would be/were updated
        """
        drift = self.check_drift()
        files_to_update = set()
        
        for old_version, occurrences in drift.items():
            for filepath, _ in occurrences:
                files_to_update.add(filepath)
        
        if dry_run:
            print(f"🔍 Would update {len(files_to_update)} files:")
            for filepath in sorted(files_to_update):
                print(f"  - {filepath.relative_to(self.base_dir)}")
            return len(files_to_update)
        
        # Actually update files
        updated = 0
        version_pattern = re.compile(r'v?(\d+\.\d+\.\d+)')
        
        for filepath in files_to_update:
            content = filepath.read_text()
            
            # Replace old versions with current (but be careful!)
            # Only replace in version strings, not in paths or other contexts
            updated_content = content
            for old_version in drift.keys():
                # Match "vX.Y.Z" or "X.Y.Z" in version contexts
                updated_content = re.sub(
                    rf'\bv?{re.escape(old_version)}\b',
                    self.current_version,
                    updated_content
                )
            
            if updated_content != content:
                filepath.write_text(updated_content)
                updated += 1
                print(f"  ✅ Updated {filepath.relative_to(self.base_dir)}")
        
        return updated
    
    def update_version(self, new_version: str, update_all: bool = True) -> None:
        """Update to new version and sync across project
        
        Args:
            new_version: New version string (e.g. "2.6.5")
            update_all: If True, update all references automatically
        """
        # Validate version format
        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            raise ValueError(f"Invalid version format: {new_version}")
        
        # Update VERSION file
        old_version = self.current_version
        self.version_file.write_text(new_version + '\n')
        self.current_version = new_version
        
        print(f"📝 Updated VERSION: {old_version} → {new_version}")
        
        if update_all:
            # Update all references
            self.fix_drift(dry_run=False)
            print(f"✅ Synced version across project")
    
    def report(self) -> None:
        """Generate version drift report"""
        print(f"📊 Version Drift Report")
        print(f"   Current version: {self.current_version}")
        print()
        
        drift = self.check_drift()
        
        if not drift:
            print("✅ No version drift detected!")
            return
        
        print(f"⚠️  Found {len(drift)} different versions in use:")
        print()
        
        for old_version, occurrences in sorted(drift.items()):
            print(f"  v{old_version} ({len(occurrences)} occurrences):")
            for filepath, match in occurrences[:5]:  # Show first 5
                rel_path = filepath.relative_to(self.base_dir)
                print(f"    - {rel_path}")
            if len(occurrences) > 5:
                print(f"    ... and {len(occurrences) - 5} more")
            print()
        
        print(f"💡 Run with fix_drift(dry_run=False) to update automatically")

def check_version_drift():
    """CLI helper to check version drift"""
    system = VersionSyncSystem()
    system.report()
    return system.check_drift()

def sync_versions(dry_run: bool = True):
    """CLI helper to sync versions"""
    system = VersionSyncSystem()
    return system.fix_drift(dry_run=dry_run)
