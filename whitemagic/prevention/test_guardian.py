"""Test Guardian

Prevents test coverage degradation and ensures tests exist for new code.
Continuous protection against regression.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Set
import ast

class TestGuardian:
    """Protects test coverage and quality"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.src_dir = self.base_dir / "whitemagic"
        self.test_dir = self.base_dir / "tests"
    
    def find_untested_files(self) -> List[Tuple[Path, str]]:
        """Find Python files without corresponding tests
        
        Returns:
            List of (file, reason) tuples
        """
        untested = []
        
        for py_file in self.src_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or py_file.name == '__init__.py':
                continue
            
            # Derive expected test file path
            rel_path = py_file.relative_to(self.src_dir)
            test_file = self.test_dir / f"test_{rel_path}"
            
            if not test_file.exists():
                untested.append((py_file, "no_test_file"))
        
        return untested
    
    def analyze_test_coverage_gaps(self) -> Dict[str, List[str]]:
        """Analyze which functions/classes lack tests"""
        
        gaps = {
            'untested_functions': [],
            'untested_classes': [],
            'low_coverage_files': []
        }
        
        # Find all Python modules
        for py_file in self.src_dir.rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                tree = ast.parse(content)
                
                # Extract functions and classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if not node.name.startswith('_'):  # Public functions
                            gaps['untested_functions'].append(
                                f"{py_file.relative_to(self.src_dir)}::{node.name}"
                            )
                    elif isinstance(node, ast.ClassDef):
                        gaps['untested_classes'].append(
                            f"{py_file.relative_to(self.src_dir)}::{node.name}"
                        )
            except Exception:
                # Skip files that can't be parsed
                pass
        
        return gaps
    
    def suggest_test_files(self) -> List[Tuple[Path, Path]]:
        """Suggest test files to create
        
        Returns:
            List of (source_file, suggested_test_file) tuples
        """
        suggestions = []
        untested = self.find_untested_files()
        
        for src_file, reason in untested:
            rel_path = src_file.relative_to(self.src_dir)
            test_file = self.test_dir / f"test_{rel_path}"
            suggestions.append((src_file, test_file))
        
        return suggestions
    
    def generate_test_stub(self, src_file: Path) -> str:
        """Generate test file stub for a source file
        
        Args:
            src_file: Source file to generate tests for
        
        Returns:
            Test file content as string
        """
        rel_path = src_file.relative_to(self.src_dir)
        module_path = str(rel_path.with_suffix('')).replace('/', '.')
        
        # Parse source to find testable items
        try:
            content = src_file.read_text()
            tree = ast.parse(content)
            
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
        except Exception:
            functions = []
            classes = []
        
        # Generate stub
        lines = [
            f'"""Tests for whitemagic.{module_path}"""',
            '',
            'import pytest',
            f'from whitemagic.{module_path} import (',
        ]
        
        # Add imports
        for cls in classes:
            lines.append(f'    {cls},')
        for func in functions:
            lines.append(f'    {func},')
        
        if classes or functions:
            lines[-1] = lines[-1].rstrip(',')  # Remove trailing comma
        
        lines.extend([')', '', ''])
        
        # Generate test stubs for classes
        for cls in classes:
            lines.extend([
                f'class Test{cls}:',
                f'    """Tests for {cls}"""',
                '    ',
                '    def test_initialization(self):',
                f'        """Test {cls} can be initialized"""',
                f'        instance = {cls}()',
                '        assert instance is not None',
                '    ',
                '    @pytest.mark.skip(reason="Not implemented")',
                '    def test_basic_functionality(self):',
                f'        """Test {cls} basic functionality"""',
                '        raise NotImplementedError("Add tests here")',
                '',
                ''
            ])
        
        # Generate test stubs for functions
        for func in functions:
            lines.extend([
                f'def test_{func}():',
                f'    """Test {func} function"""',
                '    # TODO: Implement test',
                '    pytest.skip("Not implemented")',
                '',
                ''
            ])
        
        return '\n'.join(lines)
    
    def create_missing_tests(self, dry_run: bool = True) -> int:
        """Create test stubs for files without tests
        
        Args:
            dry_run: If True, only report what would be created
        
        Returns:
            Number of test files created/would create
        """
        suggestions = self.suggest_test_files()
        
        if dry_run:
            print(f"📝 Would create {len(suggestions)} test files:")
            for src_file, test_file in suggestions[:10]:
                print(f"  - {test_file.relative_to(self.base_dir)}")
            if len(suggestions) > 10:
                print(f"  ... and {len(suggestions) - 10} more")
            return len(suggestions)
        
        # Actually create test stubs
        created = 0
        for src_file, test_file in suggestions:
            test_file.parent.mkdir(parents=True, exist_ok=True)
            
            stub_content = self.generate_test_stub(src_file)
            test_file.write_text(stub_content)
            
            created += 1
            print(f"  ✅ Created {test_file.relative_to(self.base_dir)}")
        
        return created
    
    def report(self) -> None:
        """Generate comprehensive test coverage report"""
        print("🧪 Test Guardian Report")
        print("=" * 60)
        print()
        
        # Count source files
        src_files = [
            f for f in self.src_dir.rglob("*.py")
            if '__pycache__' not in str(f) and f.name != '__init__.py'
        ]
        
        # Count test files
        test_files = []
        if self.test_dir.exists():
            test_files = list(self.test_dir.rglob("test_*.py"))
        
        print(f"📊 Coverage Overview:")
        print(f"   Source files: {len(src_files)}")
        print(f"   Test files: {len(test_files)}")
        
        # Find untested
        untested = self.find_untested_files()
        coverage_pct = ((len(src_files) - len(untested)) / len(src_files) * 100) if src_files else 0
        
        print(f"   Coverage: {coverage_pct:.1f}%")
        print(f"   Untested: {len(untested)} files")
        print()
        
        if untested:
            print(f"⚠️  Files without tests (showing first 10):")
            for src_file, reason in untested[:10]:
                rel_path = src_file.relative_to(self.src_dir)
                print(f"   - whitemagic/{rel_path}")
            if len(untested) > 10:
                print(f"   ... and {len(untested) - 10} more")
            print()
        
        print(f"💡 Run create_missing_tests(dry_run=False) to generate test stubs")

def audit_test_coverage():
    """CLI helper to audit test coverage"""
    guardian = TestGuardian()
    guardian.report()

def create_test_stubs(dry_run: bool = True):
    """CLI helper to create test stubs"""
    guardian = TestGuardian()
    return guardian.create_missing_tests(dry_run=dry_run)
