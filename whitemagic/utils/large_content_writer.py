#!/usr/bin/env python3
"""
Large Content Writer - Bypass Token Limits

Methods: Direct, Chunked, Python, Base64, Rust, Haskell
Special: Self-continuity via compressed serialization
"""

import base64
import gzip
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum

# Optional imports
try:
    from ..rust_bridge import write_file_fast
    RUST_AVAILABLE = True
except:
    RUST_AVAILABLE = False

try:
    from ..haskell_bridge import stream_write
    HASKELL_AVAILABLE = True
except:
    HASKELL_AVAILABLE = False


class WriteMethod(Enum):
    AUTO = "auto"
    DIRECT = "direct"
    CHUNKED = "chunked"
    PYTHON = "python"
    BASE64 = "base64"
    RUST = "rust"
    HASKELL = "haskell"


@dataclass
class WriteResult:
    success: bool
    filepath: str
    method_used: str
    bytes_written: int
    compressed: bool
    error: Optional[str] = None


class LargeContentWriter:
    """Intelligent writer selecting optimal method by size"""
    
    DIRECT_MAX = 8000
    CHUNKED_MAX = 50000
    PYTHON_MAX = 500000
    
    def write(self, filepath: Path, content: str, method: WriteMethod = WriteMethod.AUTO):
        """Write content using best method"""
        size = len(content)
        
        if method == WriteMethod.AUTO:
            method = self._select_method(size)
        
        try:
            if method == WriteMethod.BASE64:
                return self._write_base64(filepath, content)
            elif method == WriteMethod.RUST and RUST_AVAILABLE:
                return self._write_rust(filepath, content)
            else:
                return self._write_python(filepath, content)
        except Exception as e:
            return WriteResult(False, str(filepath), method.value, 0, False, str(e))
    
    def _select_method(self, size: int):
        if size < self.PYTHON_MAX:
            return WriteMethod.RUST if RUST_AVAILABLE else WriteMethod.PYTHON
        return WriteMethod.BASE64
    
    def _write_python(self, filepath: Path, content: str):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return WriteResult(True, str(filepath), "python", len(content), False)
    
    def _write_base64(self, filepath: Path, content: str):
        compressed = gzip.compress(content.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('ascii')
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(gzip.compress(content.encode('utf-8')))
        
        return WriteResult(True, str(filepath), "base64", len(compressed), True)
    
    def _write_rust(self, filepath: Path, content: str):
        bytes_written = write_file_fast(str(filepath), content)
        return WriteResult(True, str(filepath), "rust", bytes_written, False)


def write_large_content(filepath: str, content: str, method: str = "auto"):
    """Convenience function"""
    writer = LargeContentWriter()
    return writer.write(Path(filepath), content, WriteMethod(method))


# CLI interface
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m whitemagic.utils.large_content_writer <file> [method]")
        print("  Or: echo content | python -m whitemagic.utils.large_content_writer <file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "auto"
    
    # Read from stdin if no content arg
    content = sys.stdin.read()
    
    result = write_large_content(filepath, content, method)
    
    if result.success:
        print(f"✅ Written {result.bytes_written} bytes using {result.method_used}")
    else:
        print(f"❌ Error: {result.error}")
        sys.exit(1)
