#!/usr/bin/env python3
"""Automated bare except Exception: sweep for WhiteMagic.

Conservatively replaces bare `except Exception:` with specific exceptions
or `except Exception as e: logger.debug(...)` based on context.
"""

import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def has_logger(content: str) -> bool:
    return "logger = logging.getLogger" in content or "getLogger(__name__)" in content


def has_logging_import(content: str) -> bool:
    return "import logging" in content


def add_logging_import(content: str) -> str:
    """Add `import logging` and `logger = ...` near the top of the file."""
    lines = content.split("\n")
    # Find the last import line (stdlib or third-party)
    last_import_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i
    if last_import_idx >= 0:
        insert_idx = last_import_idx + 1
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, "logger = logging.getLogger(__name__)")
        if not has_logging_import(content):
            lines.insert(insert_idx, "import logging")
    return "\n".join(lines)


def classify_and_fix(content: str, filepath: str) -> tuple[str, int]:
    """Classify bare except blocks and fix them. Returns (new_content, fixes)."""
    fixes = 0
    original = content

    # Strategy: use regex to find try/except blocks with bare except Exception:
    # This is a best-effort approach — we look at the try body to infer context.

    # Pattern to find try/except blocks with bare except
    # We capture the try body and the except body
    pattern = re.compile(
        r'^(?P<indent>[ \t]*)try:\s*\n'
        r'(?P<try_body>(?:\1[ \t]+.*\n)+)'
        r'\1except Exception:\s*\n'
        r'(?P<except_body>(?:\1[ \t]+.*\n)*)',
        re.MULTILINE,
    )

    def replacer(match):
        nonlocal fixes
        indent = match.group("indent")
        try_body = match.group("try_body")
        except_body = match.group("except_body")

        # Classify based on try body content
        try_text = try_body.lower()

        # 1. Optional module import → ImportError/AttributeError
        if re.search(r'from\s+\S+\s+import', try_text):
            new_except = f"{indent}except (ImportError, AttributeError):\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # 2. JSON operations → JSONDecodeError/TypeError
        if "json.loads" in try_text or "json.load" in try_text:
            new_except = f"{indent}except (json.JSONDecodeError, TypeError):\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # 3. File I/O → OSError/UnicodeDecodeError
        if any(k in try_text for k in ["read_text", "write_text", "open(", "readlines", "mkdir"]):
            new_except = f"{indent}except (OSError, UnicodeDecodeError) as e:\n{indent}    logger.debug(\"File operation failed: %s\", e)\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # 4. Subprocess / process → OSError
        if any(k in try_text for k in ["subprocess", "popen", "terminate", "kill()"]):
            new_except = f"{indent}except OSError as e:\n{indent}    logger.debug(\"Process operation failed: %s\", e)\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # 5. SQLite / DB → sqlite3.Error
        if any(k in try_text for k in ["cursor.execute", "conn.execute", "fetchone", "commit()"]):
            if "import sqlite3" in content or "sqlite3" in content:
                new_except = f"{indent}except sqlite3.Error as e:\n{indent}    logger.debug(\"DB operation failed: %s\", e)\n{except_body}"
            else:
                new_except = f"{indent}except Exception as e:\n{indent}    logger.debug(\"DB operation failed: %s\", e)\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # 6. HTTP / URL → urllib.error.URLError
        if any(k in try_text for k in ["urllib", "urlopen", "requests.get"]):
            new_except = f"{indent}except Exception as e:\n{indent}    logger.debug(\"Network request failed: %s\", e)\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # 7. Rust FFI / module attribute → ImportError/AttributeError
        if any(k in try_text for k in ["hasattr", "getattr", "compute_", "batch_"]):
            if "import" in try_text or "_rs" in try_text or "_rust" in try_text:
                new_except = f"{indent}except (ImportError, AttributeError):\n{except_body}"
                fixes += 1
                return match.group(0).replace(
                    f"{indent}except Exception:\n{except_body}",
                    new_except,
                )

        # 8. Queue / threading → OSError/ValueError
        if any(k in try_text for k in ["queue.", "threading", "put(", "get("]):
            new_except = f"{indent}except (OSError, ValueError) as e:\n{indent}    logger.debug(\"Queue/thread operation failed: %s\", e)\n{except_body}"
            fixes += 1
            return match.group(0).replace(
                f"{indent}except Exception:\n{except_body}",
                new_except,
            )

        # Default: generic Exception with debug logging
        # Try to extract a meaningful message from the try body
        msg = "Operation failed"
        if "emit(" in try_text:
            msg = "Event emit failed"
        elif "record_call" in try_text or "record(" in try_text:
            msg = "Recording operation failed"
        elif "search" in try_text:
            msg = "Search operation failed"
        elif "get(" in try_text and "backend" in try_text:
            msg = "Backend get failed"
        elif "write" in try_text or "writelines" in try_text:
            msg = "Write operation failed"
        elif "read" in try_text:
            msg = "Read operation failed"
        elif "load" in try_text:
            msg = "Load operation failed"
        elif "save" in try_text:
            msg = "Save operation failed"

        new_except = f"{indent}except Exception as e:\n{indent}    logger.debug(\"{msg}: %s\", e)\n{except_body}"
        fixes += 1
        return match.group(0).replace(
            f"{indent}except Exception:\n{except_body}",
            new_except,
        )

    new_content = pattern.sub(replacer, content)

    # If we made fixes and the file didn't have logging, add it
    if fixes > 0 and not has_logger(new_content):
        new_content = add_logging_import(new_content)

    return new_content, fixes


def main() -> int:
    root = Path("whitemagic")
    total_fixes = 0
    files_changed = 0

    for pyfile in root.rglob("*.py"):
        content = pyfile.read_text()
        if "except Exception:" not in content:
            continue
        if "except Exception as" in content or "except Exception, " in content:
            # Already has exception variable — skip
            pass

        new_content, fixes = classify_and_fix(content, str(pyfile))
        if fixes > 0:
            pyfile.write_text(new_content)
            total_fixes += fixes
            files_changed += 1
            print(f"  {pyfile}: {fixes} fixes")

    print(f"\nDone: {total_fixes} bare except blocks fixed across {files_changed} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
