#!/usr/bin/env python3
"""Automated batch fixer for common 'except Exception' patterns.

Targets specific, safe-to-fix patterns:
- File I/O: OSError, FileNotFoundError, PermissionError
- JSON: json.JSONDecodeError
- SQLite: sqlite3.Error, sqlite3.OperationalError
- Network: ConnectionError, TimeoutError
- Import: ImportError, ModuleNotFoundError

Usage:
    python scripts/fix_exception_blocks.py --dry-run
    python scripts/fix_exception_blocks.py --apply
"""

import argparse
import ast
from pathlib import Path


class ExceptionBlockFixer(ast.NodeTransformer):
    """AST transformer to narrow except Exception blocks."""

    def __init__(self, filename: str):
        self.filename = filename
        self.changes = []
        self.imports = set()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler | None:
        if node.type is None:
            # bare except: - leave as-is (too risky)
            return node

        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            # Check context to determine appropriate exception
            context = self._get_exception_context(node)
            if context:
                new_type = context
                self.changes.append(f"Line {node.lineno}: Exception → {new_type}")
                
                # Add import if needed
                if "sqlite" in new_type.lower():
                    self.imports.add("sqlite3")
                elif "json" in new_type.lower():
                    self.imports.add("json")
                
                # Create new exception handler with specific type
                if isinstance(new_type, str):
                    # Parse the exception type
                    parts = new_type.split(", ")
                    if len(parts) == 1:
                        new_node = ast.Name(id=parts[0], ctx=ast.Load())
                    else:
                        # Tuple of exceptions
                        elts = [ast.Name(id=p.strip(), ctx=ast.Load()) for p in parts]
                        new_node = ast.Tuple(elts=elts, ctx=ast.Load())
                    
                    node = ast.ExceptHandler(
                        type=new_node,
                        name=node.name,
                        body=node.body
                    )

        return node

    def _get_exception_context(self, node: ast.ExceptHandler) -> str | None:
        """Determine appropriate exception type based on context."""
        # Look at the try block to infer what operation is being done
        try_block = self._get_parent_try(node)
        if not try_block:
            return None

        try_source = ast.get_source_segment(self._get_source(), try_block)
        if not try_source:
            return None

        try_source_lower = try_source.lower()

        # File operations
        if any(x in try_source_lower for x in ["open(", "read(", "write(", ".read()", ".write()"]):
            return "OSError, FileNotFoundError, PermissionError"
        
        # JSON operations
        if "json" in try_source_lower and any(x in try_source_lower for x in ["loads", "dumps", "load", "dump"]):
            return "json.JSONDecodeError, TypeError"
        
        # SQLite operations
        if "sqlite" in try_source_lower or any(x in try_source_lower for x in ["execute(", "cursor(", "commit(", "rollback("]):
            return "sqlite3.Error, sqlite3.OperationalError"
        
        # Network operations
        if any(x in try_source_lower for x in ["requests.", "urlopen", "http", "connect(", "socket"]):
            return "ConnectionError, TimeoutError, OSError"
        
        # Import operations
        if "import" in try_source_lower:
            return "ImportError, ModuleNotFoundError"
        
        return None

    def _get_parent_try(self, node: ast.ExceptHandler) -> ast.Try | None:
        """Get the parent Try node."""
        for parent in ast.walk(self._get_root()):
            if isinstance(parent, ast.Try) and node in parent.handlers:
                return parent
        return None

    def _get_source(self) -> str:
        """Get the source code."""
        with open(self.filename, 'r') as f:
            return f.read()

    def _get_root(self) -> ast.AST:
        """Get the root AST node."""
        with open(self.filename, 'r') as f:
            return ast.parse(f.read())


def analyze_file(filepath: Path) -> dict:
    """Analyze a file for fixable except Exception blocks."""
    try:
        with open(filepath, 'r') as f:
            source = f.read()
        
        tree = ast.parse(source)
        fixer = ExceptionBlockFixer(str(filepath))
        fixer.visit(tree)
        
        return {
            "file": str(filepath),
            "fixable": len(fixer.changes),
            "changes": fixer.changes,
            "imports_needed": list(fixer.imports)
        }
    except Exception as e:
        return {"file": str(filepath), "error": str(e), "fixable": 0}


def scan_directory(directory: Path) -> list[dict]:
    """Scan directory for fixable exception blocks."""
    results = []
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        result = analyze_file(py_file)
        if result.get("fixable", 0) > 0:
            results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description="Scan and fix except Exception blocks")
    parser.add_argument("--directory", type=str, default="whitemagic", help="Directory to scan")
    parser.add_argument("--dry-run", action="store_true", help="Only scan, don't apply fixes")
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    print(f"Scanning {directory} for fixable except Exception blocks...")
    results = scan_directory(directory)
    
    total_fixable = sum(r.get("fixable", 0) for r in results)
    print(f"\nFound {total_fixable} potentially fixable blocks in {len(results)} files\n")
    
    for result in results[:20]:  # Show first 20
        print(f"  {result['file']}: {result['fixable']} fixes")
        for change in result['changes'][:3]:
            print(f"    - {change}")
    
    if len(results) > 20:
        print(f"  ... and {len(results) - 20} more files")
    
    if not args.dry_run:
        print("\nTo apply fixes, this script needs to be extended with AST rewriting.")


if __name__ == "__main__":
    main()
