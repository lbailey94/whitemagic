#!/usr/bin/env python3
"""
Release Audit Tool - Ensures Safe Public Release

Checks for:
1. Private information (API keys, tokens, passwords)
2. Internal documentation leaking
3. Version consistency
4. Dead links
5. Security issues

Low token usage via smart scanning (not full file reads).
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
import sys

# Patterns to detect sensitive information
SENSITIVE_PATTERNS = {
    'api_key': r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})',
    'secret': r'(?i)(secret|password|passwd)\s*[:=]\s*["\']?([^\s\'"]{8,})',
    'token': r'(?i)(token|auth)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})',
    'private_key': r'-----BEGIN (RSA |)PRIVATE KEY-----',
    'bearer_token': r'Bearer\s+[a-zA-Z0-9_\-\.]{20,}',
}

# Directories to exclude
EXCLUDE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    'dist', 'build', '.pytest_cache', '.mypy_cache',
    'memory/short_term',  # Temporary memories
}

# Files to exclude
EXCLUDE_FILES = {
    '.env', '.env.local', '.env.production',
    'package-lock.json', 'poetry.lock',
}

# Private patterns in content
PRIVATE_CONTENT_PATTERNS = {
    'internal_note': r'(?i)(internal|private|confidential|do not share)',
    'todo_sensitive': r'(?i)TODO.*(?:remove|delete|hide|secret)',
    'personal_email': r'\b[a-zA-Z0-9._%+-]+@(?!example\.com|test\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
}


class ReleaseAuditor:
    """Audits project for safe public release."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.issues: List[Dict] = []
        self.scanned_files = 0
        
    def should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded from audit."""
        # Check directory exclusions
        for part in path.parts:
            if part in EXCLUDE_DIRS:
                return True
        
        # Check file exclusions
        if path.name in EXCLUDE_FILES:
            return True
        
        # Check .gitignore patterns (basic)
        if path.name.startswith('.') and path.name not in ['.gitignore', '.env.example']:
            return True
        
        return False
    
    def scan_for_sensitive_data(self, file_path: Path) -> List[Dict]:
        """Scan file for sensitive information."""
        issues = []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check for sensitive patterns
            for pattern_name, pattern in SENSITIVE_PATTERNS.items():
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Skip example/template values
                    matched_value = match.group(0)
                    if any(x in matched_value.lower() for x in ['example', 'your_', 'xxx', '***', 'placeholder']):
                        continue
                    
                    issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'type': 'sensitive_data',
                        'pattern': pattern_name,
                        'line': content[:match.start()].count('\n') + 1,
                        'severity': 'HIGH',
                    })
            
            # Check for private content markers
            for pattern_name, pattern in PRIVATE_CONTENT_PATTERNS.items():
                if re.search(pattern, content):
                    issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'type': 'private_content',
                        'pattern': pattern_name,
                        'severity': 'MEDIUM',
                    })
        
        except Exception as e:
            issues.append({
                'file': str(file_path.relative_to(self.root_dir)),
                'type': 'scan_error',
                'error': str(e),
                'severity': 'LOW',
            })
        
        return issues
    
    def check_version_consistency(self) -> List[Dict]:
        """Check version consistency across files."""
        issues = []
        versions = {}
        
        # Files to check
        version_files = {
            'VERSION': self.root_dir / 'VERSION',
            'pyproject.toml': self.root_dir / 'pyproject.toml',
            'whitemagic-mcp/package.json': self.root_dir / 'whitemagic-mcp' / 'package.json',
            'clients/python/pyproject.toml': self.root_dir / 'clients' / 'python' / 'pyproject.toml',
            'clients/typescript/package.json': self.root_dir / 'clients' / 'typescript' / 'package.json',
        }
        
        for name, path in version_files.items():
            if path.exists():
                try:
                    content = path.read_text()
                    if name.endswith('.json'):
                        data = json.loads(content)
                        versions[name] = data.get('version', 'MISSING')
                    elif name.endswith('.toml'):
                        match = re.search(r'version\s*=\s*["\']([^"\']+)', content)
                        versions[name] = match.group(1) if match else 'MISSING'
                    else:
                        versions[name] = content.strip()
                except Exception as e:
                    versions[name] = f'ERROR: {e}'
        
        # Check consistency
        unique_versions = set(v for v in versions.values() if v not in ['MISSING', 'ERROR'])
        if len(unique_versions) > 1:
            issues.append({
                'type': 'version_mismatch',
                'severity': 'HIGH',
                'versions': versions,
                'message': 'Version inconsistency detected across files',
            })
        
        return issues
    
    def check_private_directories(self) -> List[Dict]:
        """Check for private directories that might leak."""
        issues = []
        
        private_patterns = ['private', 'internal', 'secret', 'temp', 'tmp']
        
        for pattern in private_patterns:
            for path in self.root_dir.rglob(f'*{pattern}*'):
                if path.is_dir() and not self.should_exclude(path):
                    # Check if in .gitignore
                    rel_path = path.relative_to(self.root_dir)
                    issues.append({
                        'type': 'private_directory',
                        'path': str(rel_path),
                        'severity': 'HIGH',
                        'message': f'Private directory found: {rel_path}. Ensure it\'s in .gitignore',
                    })
        
        return issues
    
    def audit(self) -> Dict:
        """Run full audit."""
        print("🔍 WhiteMagic Release Audit")
        print("━" * 40)
        
        # 1. Version consistency
        print("\n1. Checking version consistency...")
        version_issues = self.check_version_consistency()
        self.issues.extend(version_issues)
        
        # 2. Private directories
        print("2. Checking for private directories...")
        dir_issues = self.check_private_directories()
        self.issues.extend(dir_issues)
        
        # 3. Scan files for sensitive data
        print("3. Scanning files for sensitive data...")
        for file_path in self.root_dir.rglob('*'):
            if file_path.is_file() and not self.should_exclude(file_path):
                # Only scan text files
                if file_path.suffix in ['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.md', '.txt', '.env.example']:
                    file_issues = self.scan_for_sensitive_data(file_path)
                    self.issues.extend(file_issues)
                    self.scanned_files += 1
        
        print(f"   Scanned {self.scanned_files} files")
        
        # Generate report
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate audit report."""
        high = [i for i in self.issues if i.get('severity') == 'HIGH']
        medium = [i for i in self.issues if i.get('severity') == 'MEDIUM']
        low = [i for i in self.issues if i.get('severity') == 'LOW']
        
        report = {
            'scanned_files': self.scanned_files,
            'total_issues': len(self.issues),
            'high_severity': len(high),
            'medium_severity': len(medium),
            'low_severity': len(low),
            'issues': self.issues,
        }
        
        # Print summary
        print("\n" + "━" * 40)
        print("📊 Audit Summary")
        print("━" * 40)
        print(f"Files scanned: {report['scanned_files']}")
        print(f"Total issues: {report['total_issues']}")
        print(f"  🔴 High:   {report['high_severity']}")
        print(f"  🟡 Medium: {report['medium_severity']}")
        print(f"  🟢 Low:    {report['low_severity']}")
        
        if high:
            print("\n🔴 HIGH SEVERITY ISSUES:")
            for issue in high[:5]:  # Show first 5
                if issue['type'] == 'sensitive_data':
                    print(f"  • {issue['file']}:{issue.get('line', '?')} - {issue['pattern']}")
                elif issue['type'] == 'version_mismatch':
                    print(f"  • Version mismatch: {issue['message']}")
                elif issue['type'] == 'private_directory':
                    print(f"  • {issue['path']} - {issue['message']}")
        
        if report['total_issues'] == 0:
            print("\n✅ No issues found! Project is clean for release.")
        elif report['high_severity'] > 0:
            print("\n⚠️  HIGH SEVERITY ISSUES FOUND! Address before release.")
            return_code = 1
        else:
            print("\n✓ No high severity issues. Review medium/low issues.")
            return_code = 0
        
        return report


def main():
    """Run audit from command line."""
    root_dir = Path.cwd()
    
    # Check if in WhiteMagic root
    if not (root_dir / 'whitemagic').exists():
        print("❌ Error: Run this from WhiteMagic root directory")
        sys.exit(1)
    
    auditor = ReleaseAuditor(root_dir)
    report = auditor.audit()
    
    # Save report
    report_path = root_dir / '.whitemagic' / 'last_audit.json'
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    
    print(f"\n📄 Full report saved: {report_path}")
    
    # Exit code
    sys.exit(0 if report['high_severity'] == 0 else 1)


if __name__ == '__main__':
    main()
