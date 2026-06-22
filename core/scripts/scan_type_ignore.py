#!/usr/bin/env python3
"""Scanner and fixer for type: ignore suppressions.

Targets:
- name-defined: Can often be fixed by adding imports
- Simple assignment: Can be fixed with type annotations
- Bare type: ignore: Can sometimes be removed after fixing underlying issue

Usage:
    python scripts/scan_type_ignore.py
"""

import re
from pathlib import Path
from collections import Counter


def scan_type_ignores(directory: Path) -> dict:
    """Scan for type: ignore patterns."""
    patterns = Counter()
    details = []
    
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        
        with open(py_file, 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            if "# type: ignore" in line:
                # Extract the error code if present
                match = re.search(r"# type: ignore\[(.*?)\]", line)
                if match:
                    code = match.group(1)
                    patterns[code] += 1
                    details.append({
                        "file": str(py_file),
                        "line": i,
                        "code": code,
                        "line_content": line.strip()
                    })
                else:
                    patterns["bare"] += 1
                    details.append({
                        "file": str(py_file),
                        "line": i,
                        "code": "bare",
                        "line_content": line.strip()
                    })
    
    return {"patterns": patterns, "details": details}


def main():
    directory = Path("whitemagic")
    result = scan_type_ignores(directory)
    
    print(f"Total type: ignore suppressions: {sum(result['patterns'].values())}")
    print(f"\nBreakdown by error code:")
    
    for code, count in result['patterns'].most_common():
        print(f"  {code}: {count}")
    
    print(f"\nAutomatable candidates (name-defined, simple assignment):")
    automatable = [d for d in result['details'] 
                   if d['code'] in ['name-defined', 'assignment'] 
                   or 'import-not-found' not in d['code'] and 'attr-defined' not in d['code']]
    
    print(f"  Found {len(automatable)} potential candidates for review")
    
    print(f"\nFirst 10 candidates:")
    for detail in automatable[:10]:
        print(f"  {detail['file']}:{detail['line']} [{detail['code']}]")
        print(f"    {detail['line_content'][:80]}")


if __name__ == "__main__":
    main()
