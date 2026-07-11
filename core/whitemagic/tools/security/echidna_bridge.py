"""Echidna integration — property-based fuzzing for Solidity contracts."""
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EchidnaResult:
    success: bool
    stdout: str
    stderr: str
    tests_passed: int
    tests_failed: int
    failures: list[dict[str, Any]]
    elapsed_s: float


class EchidnaBridge:
    """Subprocess bridge for Echidna property-based fuzzer."""

    def __init__(self, timeout: int = 300) -> None:
        self._echidna = shutil.which("echidna")
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return self._echidna is not None

    def fuzz(
        self,
        contract_file: str,
        contract_name: str,
        config_file: str | None = None,
        workdir: str | None = None,
    ) -> EchidnaResult:
        """Run Echidna on a Solidity contract."""
        if not self._echidna:
            return EchidnaResult(False, "", "echidna not found", 0, 0, [], 0.0)

        import time
        start = time.time()
        cmd = [self._echidna, contract_file, "--contract", contract_name]
        if config_file:
            cmd.extend(["--config", config_file])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=workdir or ".",
            )
            # Parse Echidna output
            passed, failed, failures = self._parse_output(result.stdout)
            return EchidnaResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                tests_passed=passed,
                tests_failed=failed,
                failures=failures,
                elapsed_s=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return EchidnaResult(False, "", "Timeout", 0, 0, [], self._timeout)
        except Exception as e:
            return EchidnaResult(False, "", str(e), 0, 0, [], 0.0)

    def _parse_output(self, output: str) -> tuple[int, int, list[dict[str, Any]]]:
        """Parse Echidna text output for pass/fail counts."""
        passed = 0
        failed = 0
        failures = []
        for line in output.splitlines():
            if "passed" in line.lower():
                passed += 1
            elif "failed" in line.lower() or "failed:" in line.lower():
                failed += 1
                failures.append({"line": line.strip()})
        return passed, failed, failures

    def generate_config(
        self,
        output_dir: str,
        test_mode: str = "property",
        seq_len: int = 10,
        contract_addr: str = "0x00a329c0648769a73afac7f9381e08fb43dbea72",
    ) -> str:
        """Generate an Echidna config YAML file."""
        config = f"""testMode: {test_mode}
seqLen: {seq_len}
contractAddr: "{contract_addr}"
"""
        config_path = Path(output_dir) / "echidna_config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config)
        return str(config_path)

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "echidna_path": self._echidna,
            "timeout": self._timeout,
        }
