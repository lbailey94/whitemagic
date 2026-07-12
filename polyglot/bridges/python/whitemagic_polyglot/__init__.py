"""WhiteMagic Polyglot Bridge — Python dispatcher for Julia, Elixir, Haskell, Rust backends."""

import json
import select
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    def _readline_timeout(self, proc: subprocess.Popen, timeout: float) -> str:
        """Read a line from proc.stdout without blocking indefinitely.

        Uses select to wait for data, then readline() to grab the full line.
        Falls back to char-by-char accumulation if readline blocks on partial data.
        """
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return ""
            ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 1.0))
            if not ready:
                continue
            # readline() will return at least one char if select says ready
            line = proc.stdout.readline()
            if not line:
                return ""
            return line

    def call(self, method: str, timeout: float = 10.0, **kwargs) -> Dict[str, Any]:
        proc = self._ensure_running()
        req = {"method": method, "params": kwargs}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        # Read lines until we get a valid JSON response (skip banners, errors, etc.)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._discard()
                raise TimeoutError(
                    f"Backend {self.command[0]} did not respond within {timeout}s"
                )
            line = self._readline_timeout(proc, remaining)
            if not line:
                self._discard()
                raise TimeoutError(
                    f"Backend {self.command[0]} did not respond within {timeout}s"
                )
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                # Non-JSON line (banner, debug output, etc.) — skip and keep reading
                continue

    def _discard(self):
        """Discard the current process so the next call spawns a fresh one."""
        if self.proc:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
            self.proc = None

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
            ["julia", "--project=.", "-L", str(src / "HolographicMemory.jl"), str(bridge)],
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


class ElixirActorBackend(PolyglotBackend):
    """Elixir actor-based outcome processing backend."""

    def __init__(self):
        bridge = POLYGLOT_ROOT / "bridges" / "elixir" / "actor_bridge.exs"
        super().__init__(
            ["mix", "run", str(bridge), "--no-start"],
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


class RustCascadeBackend(PolyglotBackend):
    """Rust cascade accelerator backend (compiled binary)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "whitemagic-rs" / "target" / "release" / "examples" / "cascade_bridge"
        super().__init__(
            [str(binary)],
            cwd=POLYGLOT_ROOT / "whitemagic-rs",
        )


class HaskellCascadeBackend(PolyglotBackend):
    """Haskell cascade DAG verifier backend."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "bridges" / "haskell" / "cascade_bridge"
        if binary.exists():
            super().__init__([str(binary)])
        else:
            bridge = POLYGLOT_ROOT / "bridges" / "haskell" / "cascade_bridge.hs"
            super().__init__(
                ["runhaskell", str(bridge)],
                cwd=POLYGLOT_ROOT / "bridges" / "haskell",
            )


class HaskellTopologicalBackend(PolyglotBackend):
    """Haskell topological protection backend (Berry phase, Chern number, roundtrip verify)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "bridges" / "haskell" / "topological_bridge"
        if binary.exists():
            super().__init__([str(binary)])
        else:
            bridge = POLYGLOT_ROOT / "bridges" / "haskell" / "topological_bridge.hs"
            super().__init__(
                ["runhaskell", str(bridge)],
                cwd=POLYGLOT_ROOT / "bridges" / "haskell",
            )


class RustEvolutionBackend(PolyglotBackend):
    """Rust wm-evolution backend (compiled binary)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "whitemagic-rs" / "target" / "release" / "examples" / "evolution_bridge"
        super().__init__(
            [str(binary)],
            cwd=POLYGLOT_ROOT / "whitemagic-rs",
        )


class JuliaYieldBackend(PolyglotBackend):
    """Julia yield curve backend for numerics acceleration."""

    def __init__(self):
        bridge = POLYGLOT_ROOT / "bridges" / "julia" / "yield_bridge.jl"
        super().__init__(
            ["julia", str(bridge)],
            cwd=POLYGLOT_ROOT / "whitemagic-jl",
        )


class JuliaQuantumBackend(PolyglotBackend):
    """Julia quantum geometry backend for manifold operations and natural gradient."""

    def __init__(self):
        bridge = POLYGLOT_ROOT / "bridges" / "julia" / "quantum_bridge.jl"
        super().__init__(
            ["julia", str(bridge)],
            cwd=POLYGLOT_ROOT / "whitemagic-jl",
        )


class KokaBackend(PolyglotBackend):
    """Koka polyglot backend (compiled binary, fallback to koka run)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "bridges" / "koka" / "bridge"
        if binary.exists():
            super().__init__(
                [str(binary)],
                cwd=POLYGLOT_ROOT / "bridges" / "koka",
            )
        else:
            bridge = POLYGLOT_ROOT / "bridges" / "koka" / "bridge.kk"
            super().__init__(
                ["koka", "-e", str(bridge)],
                cwd=POLYGLOT_ROOT / "bridges" / "koka",
            )
        self._banner_read = False

    def call(self, method: str, timeout: float = 10.0, **kwargs) -> Dict[str, Any]:
        proc = self._ensure_running()
        if not self._banner_read:
            # Skip all lines until we see the "started" banner
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._discard()
                    raise TimeoutError(f"Koka backend did not start within {timeout}s")
                line = self._readline_timeout(proc, remaining)
                if not line:
                    self._discard()
                    raise TimeoutError(f"Koka backend did not start within {timeout}s")
                line = line.strip()
                if not line:
                    continue
                try:
                    banner = json.loads(line)
                    if banner.get("status") == "started":
                        break
                except json.JSONDecodeError:
                    continue  # Skip compile/load output
            self._banner_read = True
        req = {"method": method, "params": kwargs}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        # Read lines until we get a valid JSON response with status: ok or error
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._discard()
                raise TimeoutError(f"Koka backend did not respond within {timeout}s")
            line = self._readline_timeout(proc, remaining)
            if not line:
                self._discard()
                raise TimeoutError(f"Koka backend did not respond within {timeout}s")
            line = line.strip()
            if not line:
                continue
            try:
                resp = json.loads(line)
                if resp.get("status") in ("ok", "error"):
                    return resp
                continue
            except json.JSONDecodeError:
                continue


class KokaCascadeBackend(PolyglotBackend):
    """Koka garden resonance backend (compiled binary, fallback to koka run)."""

    def __init__(self):
        binary = POLYGLOT_ROOT / "bridges" / "koka" / "cascade_bridge"
        if binary.exists():
            super().__init__(
                [str(binary)],
                cwd=POLYGLOT_ROOT / "bridges" / "koka",
            )
        else:
            bridge = POLYGLOT_ROOT / "bridges" / "koka" / "cascade_bridge.kk"
            super().__init__(
                ["koka", "-e", str(bridge)],
                cwd=POLYGLOT_ROOT / "bridges" / "koka",
            )
        self._banner_read = False

    def call(self, method: str, timeout: float = 10.0, **kwargs) -> Dict[str, Any]:
        proc = self._ensure_running()
        if not self._banner_read:
            # Skip all lines until we see the "started" banner
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._discard()
                    raise TimeoutError(f"Koka cascade backend did not start within {timeout}s")
                line = self._readline_timeout(proc, remaining)
                if not line:
                    self._discard()
                    raise TimeoutError(f"Koka cascade backend did not start within {timeout}s")
                line = line.strip()
                if not line:
                    continue
                try:
                    banner = json.loads(line)
                    if banner.get("status") == "started":
                        break
                except json.JSONDecodeError:
                    continue  # Skip compile/load output
            self._banner_read = True
        req = {"method": method, "params": kwargs}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        # Read lines until we get a valid JSON response with status: ok or error
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._discard()
                raise TimeoutError(f"Koka cascade backend did not respond within {timeout}s")
            line = self._readline_timeout(proc, remaining)
            if not line:
                self._discard()
                raise TimeoutError(f"Koka cascade backend did not respond within {timeout}s")
            line = line.strip()
            if not line:
                continue
            try:
                resp = json.loads(line)
                # Skip banner-like responses, only return actual results
                if resp.get("status") in ("ok", "error"):
                    return resp
                # Skip "started" or other status lines
                continue
            except json.JSONDecodeError:
                continue


def auto() -> PolyglotBackend:
    """Try backends in order: Julia -> Elixir -> Haskell -> Rust -> Koka."""
    errors = []
    for cls in [JuliaBackend, ElixirBackend, HaskellBackend, RustBackend, KokaBackend]:
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
