#!/usr/bin/env python3
"""
Python wrapper for Zig SIMD string processing
Provides SIMD-accelerated string operations for WhiteMagic
"""

import ctypes
import logging
from pathlib import Path

from whitemagic.core.acceleration.ffi_utils import LibraryLoader

logger = logging.getLogger(__name__)

# Unified library loader for Zig
_zig_loader = LibraryLoader(
    lib_name='libwhitemagic',
    base_path=Path(__file__).parent.parent.parent.parent / "whitemagic-zig",
    env_var='WM_ZIG_LIB',
    search_paths=['zig-out/lib/', ''],
)

ZIG_AVAILABLE = _zig_loader.available
zig_lib = _zig_loader.lib

# Define FFI signatures
if ZIG_AVAILABLE and zig_lib is not None:
    # wm_extract_keywords(text_ptr, text_len, out_ptr, out_capacity, max_keywords) -> keyword_count
    zig_lib.wm_extract_keywords.argtypes = [
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_size_t,
        ctypes.c_size_t,
    ]
    zig_lib.wm_extract_keywords.restype = ctypes.c_size_t

    # wm_simd_tokenize is not exported in current build, skip for now


class ZigStringProcessor:
    """Wrapper for Zig SIMD string processing operations"""

    def __init__(self):
        self.available = ZIG_AVAILABLE
        if not self.available:
            logger.warning("Zig SIMD string processor not available")

    def extract_keywords(self, text: str, max_keywords: int = 100) -> list[str]:
        """
        Extract keywords from text using SIMD-accelerated processing.

        Args:
            text: Input text
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of extracted keywords
        """
        if not self.available:
            raise RuntimeError("Zig SIMD library not available")

        text_bytes = text.encode('utf-8')
        text_len = len(text_bytes)
        out_capacity = 65536  # 64KB output buffer

        # Create buffers
        text_buffer = ctypes.create_string_buffer(text_bytes, text_len)
        out_buffer = ctypes.create_string_buffer(out_capacity)

        # Cast to u8 pointers for FFI
        text_ptr = ctypes.cast(text_buffer, ctypes.POINTER(ctypes.c_ubyte))
        out_ptr = ctypes.cast(out_buffer, ctypes.POINTER(ctypes.c_ubyte))

        # Call Zig function
        keyword_count = zig_lib.wm_extract_keywords(  # type: ignore[union-attr]
            text_ptr,
            text_len,
            out_ptr,
            out_capacity,
            max_keywords,
        )

        # Parse null-separated output
        keywords = []
        offset = 0
        for _ in range(keyword_count):
            end = out_buffer.raw.find(b'\x00', offset)
            if end == -1:
                break
            keyword = out_buffer.raw[offset:end].decode('utf-8')
            keywords.append(keyword)
            offset = end + 1

        return keywords

    def tokenize(self, text: str, max_tokens: int = 4096) -> list[tuple[str, int, int]]:
        """
        Tokenize text using SIMD-accelerated processing.

        Note: wm_simd_tokenize not currently exported, using Python fallback.

        Args:
            text: Input text
            max_tokens: Maximum number of tokens

        Returns:
            List of (token, start_offset, end_offset) tuples
        """
        if not self.available:
            raise RuntimeError("Zig SIMD library not available")

        # Python fallback since wm_simd_tokenize is not exported
        import re
        lowered = text.lower()
        tokens = []
        for match in re.finditer(r"\b\w+\b", lowered):
            token = match.group()
            if len(token) > 2:
                tokens.append((token, match.start(), match.end()))
                if len(tokens) >= max_tokens:
                    break
        return tokens


# Singleton instance
_zig_processor = None

def get_zig_processor() -> ZigStringProcessor:
    """Get the Zig string processor singleton"""
    global _zig_processor
    if _zig_processor is None:
        _zig_processor = ZigStringProcessor()
    return _zig_processor
