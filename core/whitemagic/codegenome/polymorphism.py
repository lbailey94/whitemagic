"""Template Polymorphism Engine — stochastic variation layer.

Produces structurally different but semantically equivalent code from
the same template + variables. Inspired by G2's polymorphic routines.

Variation strategies:
  - Variable name mangling (synonym table)
  - Import shuffling (AST-safe reorder)
  - Control flow equivalence (if/else ↔ ternary, for ↔ while)
  - Comment variation (docstring style rotation)
  - Junk code insertion (no-op pass/type aliases for PoC obfuscation)
"""

from __future__ import annotations

import logging
import random
import re

logger = logging.getLogger(__name__)

# Synonym table for variable name mangling
_SYNONYMS: dict[str, list[str]] = {
    "get": ["fetch", "retrieve", "list", "obtain", "collect"],
    "create": ["make", "build", "construct", "generate", "init"],
    "update": ["modify", "patch", "adjust", "set", "change"],
    "delete": ["remove", "destroy", "purge", "drop", "clear"],
    "process": ["handle", "transform", "convert", "apply", "run"],
    "validate": ["check", "verify", "assert", "ensure", "guard"],
    "parse": ["read", "decode", "extract", "interpret", "analyze"],
    "save": ["store", "persist", "write", "commit", "record"],
    "load": ["fetch", "read", "import", "restore", "hydrate"],
    "send": ["dispatch", "emit", "forward", "transmit", "publish"],
    "init": ["setup", "bootstrap", "prepare", "configure", "initialize"],
    "main": ["run", "start", "execute", "launch", "entry"],
}

# Docstring styles for comment variation
_DOCSTRING_STYLES = ["google", "numpy", "sphinx", "rest"]

# Control flow equivalence transforms
def _ternary_to_if_else(code: str) -> str:
    """Convert simple ternary expressions to if/else statements."""
    pattern = r"(\w+)\s*=\s*(.+?)\s+if\s+(.+?)\s+else\s+(.+)"
    def replacer(match: re.Match[str]) -> str:
        var, true_val, condition, false_val = match.groups()
        return f"if {condition}:\n    {var} = {true_val}\nelse:\n    {var} = {false_val}"
    return re.sub(pattern, replacer, code, flags=re.MULTILINE)

def _if_else_to_ternary(code: str) -> str:
    """Convert simple if/else assignments to ternary expressions."""
    pattern = r"if\s+(.+?):\s*\n\s*(\w+)\s*=\s*(.+?)\s*\nelse:\s*\n\s*\2\s*=\s*(.+)"
    def replacer(match: re.Match[str]) -> str:
        condition, var, true_val, false_val = match.groups()
        return f"{var} = {true_val} if {condition} else {false_val}"
    return re.sub(pattern, replacer, code, flags=re.MULTILINE)

def _for_to_while(code: str) -> str:
    """Convert simple for loops over range to while loops."""
    pattern = r"for\s+(\w+)\s+in\s+range\((\d+)\):\s*\n\s*(.+)"
    def replacer(match: re.Match[str]) -> str:
        var, end, body = match.groups()
        return f"{var} = 0\nwhile {var} < {end}:\n    {body}\n    {var} += 1"
    return re.sub(pattern, replacer, code, flags=re.MULTILINE)

_TRANSFORMS = [_ternary_to_if_else, _if_else_to_ternary, _for_to_while]


class PolymorphismEngine:
    """Apply stochastic variations to generated code.

    The same template + variables will produce structurally different
    but semantically equivalent output across runs.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def polymorph(
        self,
        code: str,
        *,
        mangle_names: bool = True,
        shuffle_imports: bool = True,
        transform_control_flow: bool = True,
        vary_comments: bool = True,
        insert_junk: bool = False,
        intensity: float = 0.3,
    ) -> str:
        """Apply polymorphic transformations to code.

        Args:
            code: Source code to polymorph
            mangle_names: Rename variables using synonym table
            shuffle_imports: Reorder import statements (AST-safe)
            transform_control_flow: Apply equivalent control flow transforms
            vary_comments: Rotate docstring/comment styles
            insert_junk: Insert no-op statements (for PoC obfuscation)
            intensity: Probability [0,1] of applying each transform

        Returns:
            Polymorphed code string
        """
        result = code

        if mangle_names and self._rng.random() < intensity:
            result = self._mangle_variable_names(result)

        if shuffle_imports and self._rng.random() < intensity:
            result = self._shuffle_imports(result)

        if transform_control_flow and self._rng.random() < intensity:
            result = self._transform_control_flow(result)

        if vary_comments and self._rng.random() < intensity:
            result = self._vary_comments(result)

        if insert_junk and self._rng.random() < intensity:
            result = self._insert_junk_code(result)

        return result

    def _mangle_variable_names(self, code: str) -> str:
        """Rename function/variable names using synonym table."""
        result = code
        # Find function definitions: def get_items( -> def fetch_items(
        def_pattern = re.compile(r"\bdef\s+(get|create|update|delete|process|validate|parse|save|load|send|init|main)_(\w+)")
        for match in def_pattern.finditer(result):
            prefix = match.group(1)
            suffix = match.group(2)
            synonyms = _SYNONYMS.get(prefix, [prefix])
            new_prefix = self._rng.choice(synonyms)
            old_name = f"{prefix}_{suffix}"
            new_name = f"{new_prefix}_{suffix}"
            # Replace all occurrences of the old name
            result = re.sub(rf"\b{re.escape(old_name)}\b", new_name, result)
        return result

    def _shuffle_imports(self, code: str) -> str:
        """Reorder import statements (preserving __future__ and conditional imports)."""
        lines = code.split("\n")
        import_lines: list[tuple[int, str]] = []
        other_lines: list[tuple[int, str]] = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("from __future__"):
                other_lines.append((i, line))  # Keep __future__ in place
            elif stripped.startswith("import ") or stripped.startswith("from "):
                import_lines.append((i, line))
            else:
                other_lines.append((i, line))

        if len(import_lines) < 2:
            return code

        # Shuffle import lines
        shuffled = list(import_lines)
        self._rng.shuffle(shuffled)

        # Reconstruct: find the position of first import, place all imports there
        first_import_pos = min(idx for idx, _ in import_lines)
        result_lines: list[str] = [""] * len(lines)

        # Place non-import lines
        for idx, line in other_lines:
            result_lines[idx] = line

        # Place shuffled imports starting at first import position
        for i, (_, line) in enumerate(shuffled):
            result_lines[first_import_pos + i] = line

        return "\n".join(result_lines)

    def _transform_control_flow(self, code: str) -> str:
        """Apply a random control flow equivalence transform."""
        transform = self._rng.choice(_TRANSFORMS)
        return transform(code)

    def _vary_comments(self, code: str) -> str:
        """Rotate docstring style markers in comments."""
        style = self._rng.choice(_DOCSTRING_STYLES)
        # Replace TODO comments with style-specific annotations
        if style == "google":
            code = re.sub(r"# TODO:", "# TODO(google-style):", code)
        elif style == "numpy":
            code = re.sub(r"# TODO:", "# NOTE:", code)
        elif style == "sphinx":
            code = re.sub(r"# TODO:", ".. todo::", code)
        elif style == "rest":
            code = re.sub(r"# TODO:", "# FIXME:", code)
        return code

    def _insert_junk_code(self, code: str) -> str:
        """Insert no-op statements for obfuscation (PoC use case)."""
        lines = code.split("\n")
        junk_options = [
            "pass  # type: ignore",
            "_ = None",
            "_: type = type",
            "T = type('T', (), {})",
        ]
        # Insert 1-3 junk lines at random positions (not at start/end)
        num_junk = self._rng.randint(1, min(3, len(lines) // 4))
        for _ in range(num_junk):
            pos = self._rng.randint(2, len(lines) - 2)
            junk = self._rng.choice(junk_options)
            lines.insert(pos, junk)
        return "\n".join(lines)

    def get_variation_count(self, code: str) -> int:
        """Estimate the number of possible variations for a given code string."""
        count = 1
        # Count mangleable function names
        def_pattern = re.compile(r"\bdef\s+(get|create|update|delete|process|validate|parse|save|load|send|init|main)_(\w+)")
        matches = def_pattern.findall(code)
        for prefix, _ in matches:
            count *= len(_SYNONYMS.get(prefix, [prefix]))
        # Control flow transforms
        count *= len(_TRANSFORMS) + 1
        # Docstring styles
        count *= len(_DOCSTRING_STYLES)
        return count
