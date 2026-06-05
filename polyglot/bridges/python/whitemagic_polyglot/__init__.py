"""WhiteMagic Polyglot Bridge — Python dispatcher for Julia, Elixir, Haskell, Rust backends."""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

POLYGLOT_ROOT = Path(__file__).parent.parent.parent.parent


class PolyglotBackend:
    """Base class for polyglot backends communicating via JSON stdio."""

    def __init__(self, command: List[str], cwd: Optional[Path] = None):
        self.command = command
        self.cwd = cwd
        self.proc: Optional[subprocess.Popen] = None

    def _ensure_running(self) -> subprocess.Popen:
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        return self.proc

    def call(self, method: str, **kwargs) -> Dict[str, Any]:
        proc = self._ensure_running()
        req = {"method": method, "params": kwargs}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError(f"Backend {self.command[0]} returned empty response")
        return json.loads(line)

    def close(self):
        if self.proc:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
            self.proc = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class JuliaBackend(PolyglotBackend):
    """Julia HolographicMemory backend."""

    def __init__(self):
        bridge = POLYGLOT_ROOT / "bridges" / "julia" / "bridge.jl"
        src = POLYGLOT_ROOT / "whitemagic-jl" / "src"
        super().__init__(
            ["julia", "-L", str(src / "HolographicMemory.jl"), str(bridge)],
            cwd=POLYGLOT_ROOT / "whitemagic-jl",
        )


class ElixirBackend(PolyglotBackend):
    """Elixir HolographicMemory backend."""

    def __init__(self):
        bridge = POLYGLOT_ROOT / "bridges" / "elixir" / "bridge.exs"
        super().__init__(
            ["mix", "run", str(bridge)],
            cwd=POLYGLOT_ROOT / "elixir",
        )


class HaskellBackend(PolyglotBackend):
    """Haskell Holographic backend (compiled binary, fallback to runhaskell)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "bridges" / "haskell" / "bridge"
        if binary.exists():
            super().__init__([str(binary)])
        else:
            bridge = POLYGLOT_ROOT / "bridges" / "haskell" / "bridge.hs"
            super().__init__(
                ["runhaskell", str(bridge)],
                cwd=POLYGLOT_ROOT / "bridges" / "haskell",
            )


class RustBackend(PolyglotBackend):
    """Rust wm-core backend (compiled binary)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "whitemagic-rs" / "target" / "release" / "examples" / "bridge"
        super().__init__(
            [str(binary)],
            cwd=POLYGLOT_ROOT / "whitemagic-rs",
        )


def auto() -> PolyglotBackend:
    """Try backends in order: Julia -> Elixir -> Haskell -> Rust."""
    errors = []
    for cls in [JuliaBackend, ElixirBackend, HaskellBackend, RustBackend]:
        try:
            b = cls()
            b.call("ping")
            return b
        except Exception as e:
            errors.append(f"{cls.__name__}: {e}")
    raise RuntimeError(f"No polyglot backend available. Errors: {errors}")


if __name__ == "__main__":
    print("WhiteMagic Polyglot Bridge")
    print("Trying Julia backend...")
    try:
        with JuliaBackend() as b:
            print(b.call("ping"))
            print(b.call("encode", text="hello world"))
            print(b.call("nearest_neighbors", query="hello world", texts=["a", "b", "hello world"], k=2))
        print("Julia backend: OK")
    except Exception as e:
        print(f"Julia backend failed: {e}")
