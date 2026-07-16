# Compatibility shim: whitemagic_rs -> whitemagic_rust
# The Rust maturin build installs as whitemagic_rust, but legacy code
# imports whitemagic_rs. This bridge resolves the naming mismatch.

try:
    from whitemagic_rust import *  # type: ignore
except ImportError:
    pass

# Stub for functions not present in the Rust build
try:
    extract_patterns_from_content  # type: ignore[used-before-def]
except NameError:

    def extract_patterns_from_content(
        samples: list[str], threshold: float = 0.1
    ) -> tuple:
        """Stub pattern extraction — returns empty result matching Rust signature."""
        return (0, 0, [], [], [], [], 0.0)
