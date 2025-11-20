"""Documentation Guardian

Prevents documentation drift, outdated info, and sprawl.
Maintains coherence across growing documentation.
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime
import re

class DocumentationGuardian:
    """Protects documentation integrity"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.docs_dir = self.base_dir / "docs"
        self.root_docs = [self.base_dir / f for f in [
            "README.md", "CHANGELOG.md", "CONTRIBUTING.md"
        ] if (self.base_dir / f).exists()]
    
    def audit_structure(self) -> Dict[str, any]:
        """Audit documentation structure and organization"""
        
        if not self.docs_dir.exists():
            return {'status': 'no_docs_dir'}
        
        # Count files by location
        structure = {
            'root': len(self.root_docs),
            'docs_root': len(list(self.docs_dir.glob("*.md"))),
            'subdirs': {},
            'total': 0
        }
        
        for subdir in self.docs_dir.iterdir():
            if subdir.is_dir():
                md_count = len(list(subdir.rglob("*.md")))
                structure['subdirs'][subdir.name] = md_count
                structure['total'] += md_count
        
        structure['total'] += structure['docs_root'] + structure['root']
        
        return structure
    
    def find_duplicates(self) -> List[Tuple[str, List[Path]]]:
        """Find duplicate or near-duplicate documentation"""
        
        files_by_title = {}
        
        for md_file in self.docs_dir.rglob("*.md"):
            # Extract title from first heading
            content = md_file.read_text()
            match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if match:
                title = match.group(1).strip().lower()
                if title not in files_by_title:
                    files_by_title[title] = []
                files_by_title[title].append(md_file)
        
        # Return titles with multiple files
        duplicates = [
            (title, files) for title, files in files_by_title.items()
            if len(files) > 1
        ]
        
        return duplicates
    
    def find_outdated(self, days_threshold: int = 90) -> List[Tuple[Path, int]]:
        """Find documentation not updated recently
        
        Args:
            days_threshold: Consider files older than this outdated
        
        Returns:
            List of (file, days_old) tuples
        """
        now = datetime.now().timestamp()
        outdated = []
        
        for md_file in self.docs_dir.rglob("*.md"):
            if 'archive' in str(md_file):
                continue  # Skip archived files
            
            mtime = md_file.stat().st_mtime
            days_old = int((now - mtime) / 86400)
            
            if days_old > days_threshold:
                outdated.append((md_file, days_old))
        
        return sorted(outdated, key=lambda x: x[1], reverse=True)
    
    def suggest_organization(self) -> Dict[str, List[str]]:
        """Suggest better organization for docs"""
        
        suggestions = {
            'create_subdirs': [],
            'move_to_archive': [],
            'consolidate': []
        }
        
        # Check docs_root for files that should be in subdirs
        root_files = list(self.docs_dir.glob("*.md"))
        
        for file in root_files:
            name_lower = file.name.lower()
            
            # Files that should be in guides/
            if any(word in name_lower for word in ['guide', 'tutorial', 'howto']):
                suggestions['create_subdirs'].append(
                    f"Move {file.name} to docs/guides/"
                )
            
            # Files that should be in plans/
            elif any(word in name_lower for word in ['plan', 'roadmap', 'strategy']):
                suggestions['create_subdirs'].append(
                    f"Move {file.name} to docs/plans/"
                )
            
            # Old version files
            elif re.search(r'v\d+\.\d+\.\d+', name_lower):
                version_match = re.search(r'v(\d+\.\d+\.\d+)', name_lower)
                if version_match:
                    version = version_match.group(1)
                    suggestions['move_to_archive'].append(
                        f"Archive {file.name} to docs/archive/versions/v{version}/"
                    )
        
        # Check for duplicate content
        duplicates = self.find_duplicates()
        for title, files in duplicates:
            suggestions['consolidate'].append(
                f"Consolidate {len(files)} files with title '{title}'"
            )
        
        return suggestions
    
    def reorganize(self, dry_run: bool = True) -> int:
        """Apply suggested reorganization
        
        Args:
            dry_run: If True, only report what would be done
        
        Returns:
            Number of files moved/changed
        """
        suggestions = self.suggest_organization()
        changes = 0
        
        if dry_run:
            print("📋 Documentation Reorganization Plan:")
            print()
            
            if suggestions['create_subdirs']:
                print("📁 Move to subdirectories:")
                for suggestion in suggestions['create_subdirs']:
                    print(f"  - {suggestion}")
                changes += len(suggestions['create_subdirs'])
            
            if suggestions['move_to_archive']:
                print("\n📦 Archive old versions:")
                for suggestion in suggestions['move_to_archive']:
                    print(f"  - {suggestion}")
                changes += len(suggestions['move_to_archive'])
            
            if suggestions['consolidate']:
                print("\n🔄 Consolidate duplicates:")
                for suggestion in suggestions['consolidate']:
                    print(f"  - {suggestion}")
                changes += len(suggestions['consolidate'])
            
            print(f"\n📊 Total changes: {changes}")
            return changes
        
        # Actually reorganize
        # Implementation would go here
        # For now, return dry run count
        return changes
    
    def report(self) -> None:
        """Generate comprehensive documentation report"""
        print("📚 Documentation Guardian Report")
        print("=" * 60)
        print()
        
        # Structure audit
        structure = self.audit_structure()
        print(f"📊 Structure:")
        print(f"   Root docs: {structure['root']}")
        print(f"   Docs root: {structure['docs_root']}")
        for subdir, count in sorted(structure['subdirs'].items()):
            print(f"   docs/{subdir}: {count} files")
        print(f"   **Total: {structure['total']} files**")
        print()
        
        # Duplicates
        duplicates = self.find_duplicates()
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate titles:")
            for title, files in duplicates[:5]:
                print(f"   '{title}' ({len(files)} files)")
            if len(duplicates) > 5:
                print(f"   ... and {len(duplicates) - 5} more")
            print()
        
        # Outdated
        outdated = self.find_outdated(days_threshold=60)
        if outdated:
            print(f"📅 {len(outdated)} files not updated in 60+ days:")
            for file, days in outdated[:5]:
                rel_path = file.relative_to(self.base_dir)
                print(f"   {rel_path} ({days} days)")
            if len(outdated) > 5:
                print(f"   ... and {len(outdated) - 5} more")
            print()
        
        # Suggestions
        suggestions = self.suggest_organization()
        total_suggestions = sum(len(v) for v in suggestions.values())
        if total_suggestions:
            print(f"💡 {total_suggestions} organization suggestions available")
            print(f"   Run reorganize(dry_run=True) to see details")
        else:
            print("✅ Documentation well-organized!")

def audit_documentation():
    """CLI helper to audit documentation"""
    guardian = DocumentationGuardian()
    guardian.report()

def reorganize_docs(dry_run: bool = True):
    """CLI helper to reorganize documentation"""
    guardian = DocumentationGuardian()
    return guardian.reorganize(dry_run=dry_run)
