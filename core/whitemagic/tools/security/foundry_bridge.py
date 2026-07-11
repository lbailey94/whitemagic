"""Foundry subprocess bridge — forge build, forge test, cast call, anvil fork."""
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FoundryResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    data: Any = None


class FoundryBridge:
    """Subprocess bridge for Foundry toolkit (forge/cast/anvil)."""

    def __init__(self, project_dir: str | None = None) -> None:
        self._project_dir = project_dir or os.getcwd()
        self._forge = shutil.which("forge")
        self._cast = shutil.which("cast")
        self._anvil = shutil.which("anvil")

    @property
    def available(self) -> bool:
        return self._forge is not None

    def _run(self, cmd: list[str], timeout: int = 120) -> FoundryResult:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._project_dir,
            )
            return FoundryResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return FoundryResult(False, "", "Timeout", -1)
        except Exception as e:
            return FoundryResult(False, "", str(e), -1)

    def build(self, silent: bool = True) -> FoundryResult:
        if not self._forge:
            return FoundryResult(False, "", "forge not found", -1)
        cmd = [self._forge, "build"]
        if silent:
            cmd.append("--silent")
        return self._run(cmd)

    def test(self, match: str | None = None, gas_report: bool = False) -> FoundryResult:
        if not self._forge:
            return FoundryResult(False, "", "forge not found", -1)
        cmd = [self._forge, "test", "-vvv"]
        if match:
            cmd.extend(["--match-test", match])
        if gas_report:
            cmd.append("--gas-report")
        return self._run(cmd, timeout=300)

    def test_json(self, match: str | None = None) -> FoundryResult:
        if not self._forge:
            return FoundryResult(False, "", "forge not found", -1)
        cmd = [self._forge, "test", "--json"]
        if match:
            cmd.extend(["--match-test", match])
        result = self._run(cmd, timeout=300)
        if result.success and result.stdout:
            try:
                result.data = [json.loads(line) for line in result.stdout.strip().splitlines() if line.strip()]
            except (json.JSONDecodeError, ValueError):
                pass
        return result

    def fork(self, rpc_url: str, block_number: int | None = None) -> FoundryResult:
        if not self._anvil:
            return FoundryResult(False, "", "anvil not found", -1)
        cmd = [self._anvil, "--fork-url", rpc_url]
        if block_number:
            cmd.extend(["--fork-block-number", str(block_number)])
        return self._run(cmd, timeout=10)

    def cast_call(self, to: str, sig: str, args: str = "", rpc_url: str = "http://localhost:8545") -> FoundryResult:
        if not self._cast:
            return FoundryResult(False, "", "cast not found", -1)
        cmd = [self._cast, "call", to, sig]
        if args:
            cmd.append(args)
        cmd.extend(["--rpc-url", rpc_url])
        return self._run(cmd)

    def cast_send(self, to: str, sig: str, args: str = "", private_key: str = "", rpc_url: str = "http://localhost:8545") -> FoundryResult:
        if not self._cast:
            return FoundryResult(False, "", "cast not found", -1)
        cmd = [self._cast, "send", to, sig]
        if args:
            cmd.append(args)
        if private_key:
            cmd.extend(["--private-key", private_key])
        cmd.extend(["--rpc-url", rpc_url])
        return self._run(cmd, timeout=60)

    def init_project(self, name: str) -> FoundryResult:
        if not self._forge:
            return FoundryResult(False, "", "forge not found", -1)
        cmd = [self._forge, "init", name, "--no-commit"]
        return self._run(cmd)

    def install(self, lib: str) -> FoundryResult:
        if not self._forge:
            return FoundryResult(False, "", "forge not found", -1)
        cmd = [self._forge, "install", lib, "--no-commit"]
        return self._run(cmd)

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "forge": self._forge,
            "cast": self._cast,
            "anvil": self._anvil,
            "project_dir": self._project_dir,
        }


_bridge: FoundryBridge | None = None


def get_foundry_bridge(project_dir: str | None = None) -> FoundryBridge:
    global _bridge
    if _bridge is None or project_dir:
        _bridge = FoundryBridge(project_dir)
    return _bridge
