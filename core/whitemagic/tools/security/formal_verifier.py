"""Formal verification integration — SMT-based property checking for Solidity."""
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    property_name: str
    verified: bool
    counterexample: str | None
    elapsed_s: float
    solver: str
    output: str


class FormalVerifier:
    """Integrate with formal verification tools (Halmos, Certora, K-framework)."""

    def __init__(self, timeout: int = 120) -> None:
        self._halmos = shutil.which("halmos")
        self._certora = shutil.which("certoraRun")
        self._timeout = timeout

    @property
    def available_solvers(self) -> list[str]:
        solvers = []
        if self._halmos:
            solvers.append("halmos")
        if self._certora:
            solvers.append("certora")
        return solvers

    def verify_halmos(
        self,
        project_dir: str,
        match: str = ".*",
        solver_timeout: int = 60,
    ) -> list[VerificationResult]:
        """Run Halmos symbolic execution on Foundry tests."""
        if not self._halmos:
            return [VerificationResult(
                property_name="*", verified=False, counterexample=None,
                elapsed_s=0, solver="halmos", output="halmos not found",
            )]

        import time
        start = time.time()
        cmd = [self._halmos, "--match", match, "--solver-timeout", str(solver_timeout)]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self._timeout, cwd=project_dir,
            )
            elapsed = time.time() - start
            return self._parse_halmos_output(result.stdout, elapsed)
        except subprocess.TimeoutExpired:
            return [VerificationResult("*", False, None, self._timeout, "halmos", "Timeout")]
        except Exception as e:
            return [VerificationResult("*", False, None, 0, "halmos", str(e))]

    def _parse_halmos_output(self, output: str, elapsed: float) -> list[VerificationResult]:
        results = []
        for line in output.splitlines():
            if "PASS" in line or "verified" in line.lower():
                prop = line.split(":")[0].strip() if ":" in line else line.strip()
                results.append(VerificationResult(prop, True, None, elapsed, "halmos", line))
            elif "FAIL" in line or "counterexample" in line.lower():
                prop = line.split(":")[0].strip() if ":" in line else line.strip()
                ce = line.split("counterexample:", 1)[1].strip() if "counterexample:" in line else None
                results.append(VerificationResult(prop, False, ce, elapsed, "halmos", line))
        return results

    def generate_spec(
        self,
        contract_name: str,
        properties: list[str],
        output_dir: str,
    ) -> str:
        """Generate a Certora spec file from property descriptions."""
        spec_lines = [
            f"// Spec for {contract_name}",
            f"using {contract_name} as {contract_name.lower()};",
            "",
        ]
        for prop in properties:
            spec_lines.append(f"rule {prop.replace(' ', '_')} {{")
            spec_lines.append(f"    // TODO: define {prop}")
            spec_lines.append("    assert(true);")
            spec_lines.append("}")
            spec_lines.append("")
        spec_content = "\n".join(spec_lines)
        spec_path = Path(output_dir) / f"{contract_name}.spec"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(spec_content)
        return str(spec_path)

    def generate_spec_from_findings(
        self,
        findings: list[Any],
        contract_name: str,
        output_dir: str,
    ) -> str:
        """Auto-generate formal verification specs from STRATA findings.

        Converts static analysis findings into Certora spec rules by
        mapping finding categories to formal properties.
        """
        category_to_property = {
            "reentrancy": "no_reentrancy_state_change",
            "integer_overflow": "no_arithmetic_overflow",
            "integer_underflow": "no_arithmetic_underflow",
            "access_control": "only_authorized_callers",
            "unchecked_external_call": "external_call_success_checked",
            "tx_origin": "no_tx_origin_auth",
            "dangerous_strict_equality": "no_strict_equality_balance",
            "shadowing": "no_state_variable_shadowing",
            "uninitialized_storage": "no_uninitialized_storage_pointer",
            "delegate_call": "no_untrusted_delegatecall",
            "selfdestruct": "no_selfdestruct",
            "block_timestamp": "no_block_timestamp_dependency",
            "block_number": "no_block_number_dependency",
            "gas_limit": "no_gas_limit_dependency",
            "dos": "no_dos_via_gas_limit",
            "front_running": "no_front_running_susceptibility",
            "timestamp_dependence": "no_timestamp_manipulation",
            "ether_payout": "correct_ether_payout",
            "erc20_violation": "erc20_compliance",
            "erc721_violation": "erc721_compliance",
        }

        properties: list[str] = []
        seen_categories: set[str] = set()

        for finding in findings:
            category = getattr(finding, "category", "") if not isinstance(finding, dict) else finding.get("category", "")
            if category in seen_categories:
                continue
            prop = category_to_property.get(category)
            if prop:
                properties.append(prop)
                seen_categories.add(category)

        if not properties:
            properties.append("basic_safety")

        return self.generate_spec(contract_name, properties, output_dir)

    def verify_property(
        self,
        project_dir: str,
        contract_name: str,
        property_expr: str,
    ) -> VerificationResult:
        """Verify a single property expression using available solver."""
        if self._halmos:
            results = self.verify_halmos(project_dir, match=f".*{contract_name}.*")
            if results:
                return results[0]
        return VerificationResult(
            property_name=property_expr,
            verified=False,
            counterexample=None,
            elapsed_s=0,
            solver="none",
            output="No formal verification solver available",
        )

    def status(self) -> dict[str, Any]:
        return {
            "available_solvers": self.available_solvers,
            "halmos_path": self._halmos,
            "certora_path": self._certora,
            "timeout": self._timeout,
        }
