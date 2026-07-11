"""Advanced Solidity security checkers — vulnerability pattern detection."""
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _strip(line: str) -> str:
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    line = re.sub(r"'(?:\\.|[^'\\])*'", "''", line)
    if "//" in line:
        line = line[: line.index("//")]
    return line


@register
def check_solidity_access_control(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect missing access control on privileged functions."""
    privileged_keywords = (
        r"\b(mint|burn|pause|unpause|upgrade|setAdmin|setOwner|setFee|setRate|"
        r"setTreasury|setController|setGovernor|setManager|setOperator|setMinter|"
        r"setPauser|setRouter|setOracle|setToken|withdraw|sweep|rescue|recover|"
        r"settle|execute|propose|cancel|approve|authorize|grantRole|revokeRole)\b"
    )
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        rel = str(sol_file.relative_to(project_path))
        for i, line in enumerate(lines, 1):
            code = _strip(line.strip())
            if not code or code.startswith(("//", "/*", "*")):
                continue
            func_match = re.match(r"\s*function\s+(\w+)", line)
            if not func_match:
                continue
            func_name = func_match.group(1)
            if not re.search(privileged_keywords, func_name, re.IGNORECASE):
                continue
            context = " ".join(lines[max(0, i - 1) : min(len(lines), i + 5)])
            has_auth = re.search(
                r"\b(onlyOwner|onlyRole|onlyAdmin|onlyGovernor|onlyMinter|onlyPauser|"
                r"onlyAuthorized|require\s*\(\s*msg\.sender\s*==|"
                r"require\s*\(\s*hasRole|_checkRole|accessControl|Ownable)",
                context,
            )
            is_external = re.search(r"\bexternal\b", context)
            if is_external and not has_auth:
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="sol_missing_access_control",
                        file=rel,
                        line=i,
                        message=f"Privileged function '{func_name}' lacks access control modifier.",
                        suggestion="Add onlyOwner, onlyRole, or require(msg.sender == owner) check.",
                    )
                )


@register
def check_solidity_oracle_manipulation(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect spot price reliance and single-block TWAP patterns."""
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        rel = str(sol_file.relative_to(project_path))
        content.lower()
        for i, line in enumerate(lines, 1):
            code = _strip(line.strip())
            if not code:
                continue
            if re.search(r"\bgetReserves\b|\bslot0\b|\bprice0Cumulative\b|\bprice1Cumulative\b", code):
                context = " ".join(lines[max(0, i - 3) : min(len(lines), i + 3)])
                if not re.search(r"\btimeWeighted|twap|TWAP|cumulative.*last|observation.*length|oldest", context, re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="sol_spot_price_oracle",
                            file=rel,
                            line=i,
                            message="Direct reserve/slot0 access — vulnerable to flash loan oracle manipulation.",
                            suggestion="Use a TWAP oracle (Uniswap V3 OracleLibrary) or Chainlink price feeds.",
                        )
                    )
            if re.search(r"\bblock\.timestamp\b.*\bblock\.timestamp\b", " ".join(lines[max(0, i - 2) : i + 1])):
                if re.search(r"price|oracle|rate|value|amount", code, re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="sol_single_block_twap",
                            file=rel,
                            line=i,
                            message="Single-block timestamp difference for TWAP — manipulable within one block.",
                            suggestion="Use multi-block TWAP with at least 2 observation periods.",
                        )
                    )


@register
def check_solidity_unchecked_external(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect external calls without return value checks (broader than .call())."""
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        rel = str(sol_file.relative_to(project_path))
        for i, line in enumerate(lines, 1):
            code = _strip(line.strip())
            if not code:
                continue
            if re.search(r"\.(transferFrom|approve|send)\s*\(", code):
                rest = code + " " + " ".join(lines[i : min(len(lines), i + 3)])
                if not re.search(r"\brequire\s*\(|\bif\s*\(|\bassert\s*\(|\bbool\b.*=|return\s+bool", rest):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="sol_unchecked_erc20",
                            file=rel,
                            line=i,
                            message="ERC20 operation return value not checked — silent failure risk.",
                            suggestion="Check return value: require(token.transferFrom(..., ...)); or use SafeERC20.",
                        )
                    )


@register
def check_solidity_arbitrary_transfer(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect transfers to user-controlled addresses without validation."""
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        rel = str(sol_file.relative_to(project_path))
        for i, line in enumerate(lines, 1):
            code = _strip(line.strip())
            if not code:
                continue
            transfer_patterns = [
                (r"(?:payable\s*\(\s*)?(msg\.sender|msg\.data|tx\.origin)\s*\)?\s*\.transfer\s*\(", "transfer"),
                (r"(?:payable\s*\(\s*)?(msg\.sender|msg\.data|tx\.origin)\s*\)?\s*\.send\s*\(", "send"),
                (r"(msg\.sender|msg\.data|tx\.origin)\s*\.call\{[^}]*value:", "call with value"),
            ]
            for pattern, op in transfer_patterns:
                match = re.search(pattern, code)
                if match:
                        context = " ".join(lines[max(0, i - 5) : i])
                        has_validation = re.search(
                            r"\brequire\s*\(|\bif\s*\(.*return\b|\bonlyOwner\b|\bonlyRole\b",
                            context,
                        )
                        if not has_validation:
                            findings.append(
                                Finding(
                                    severity=FindingSeverity.WARNING,
                                    category="sol_arbitrary_transfer",
                                    file=rel,
                                    line=i,
                                    message=f"Ether {op} to user-controlled address without validation.",
                                    suggestion="Validate the destination address or restrict to known addresses.",
                                )
                            )


@register
def check_solidity_reentrancy_patterns(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect CEI (Checks-Effects-Interactions) violations — state write after external call."""
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        rel = str(sol_file.relative_to(project_path))
        in_func = False
        brace_depth = 0
        for i, line in enumerate(lines, 1):
            code = _strip(line.strip())
            if not code:
                continue
            if re.match(r"\s*function\s+\w+", line) and "{" in line:
                in_func = True
                brace_depth = code.count("{") - code.count("}")
                continue
            if in_func:
                brace_depth += code.count("{") - code.count("}")
                if brace_depth <= 0:
                    in_func = False
                    continue
                if re.search(r"\.(call|transfer|send)\s*[\({]", code):
                    for future_idx in range(i, min(len(lines), i + 8)):
                        future_code = _strip(lines[future_idx].strip())
                        if not future_code:
                            continue
                        if re.match(r"^\s*[\w\[\].]+\s*(?:[-+*/]?=)\s*", future_code) and not re.search(
                            r"\brequire\b|\bassert\b|\bif\b", future_code
                        ):
                            if not re.search(r"\bReentrancyGuard\b|\bnonReentrant\b", content):
                                findings.append(
                                    Finding(
                                        severity=FindingSeverity.WARNING,
                                        category="sol_cei_violation",
                                        file=rel,
                                        line=i,
                                        message="State update after external call — CEI violation, potential reentrancy.",
                                        suggestion="Move state updates before external calls, or use ReentrancyGuard.nonReentrant.",
                                    )
                                )
                            break


@register
def check_solidity_integer_overflow(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect integer overflow/underflow risks — pre-0.8.0 pragma, unchecked blocks, SafeMath absence."""
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        rel = str(sol_file.relative_to(project_path))
        full_lower = content.lower()

        # Check pragma version
        pragma_match = re.search(r"pragma\s+solidity\s+\^?([\d.]+)", content)
        if pragma_match:
            version = pragma_match.group(1)
            parts = version.split(".")
            if len(parts) < 3:
                parts += ["0"] * (3 - len(parts))
            major, minor, patch = (int(x) for x in parts[:3])
            if major == 0 and minor < 8:
                has_safemath = "safemath" in full_lower or "using SafeMath" in content
                if not has_safemath:
                    for i, line in enumerate(lines, 1):
                        code = _strip(line.strip())
                        if not code:
                            continue
                        if re.search(r"[\w\[\]]+\s*[+\-*/]?=\s*[\w\[\].]+", code) and re.search(
                            r"\b(balances|amount|value|supply|totalSupply|_totalSupply|balanceOf)\b", code
                        ):
                            if not re.search(r"\brequire\b|\bassert\b|\bif\b", code):
                                findings.append(
                                    Finding(
                                        severity=FindingSeverity.WARNING,
                                        category="sol_integer_overflow_pre08",
                                        file=rel,
                                        line=i,
                                        message=f"Arithmetic on financial values without SafeMath (Solidity {version} <0.8.0).",
                                        suggestion="Upgrade to Solidity >=0.8.0 (auto overflow checks) or use SafeMath.",
                                    )
                                )
                                break

        # Check unchecked blocks in >=0.8.0
        for i, line in enumerate(lines, 1):
            code = _strip(line.strip())
            if not code:
                continue
            if re.search(r"\bunchecked\s*\{", code):
                context = " ".join(lines[max(0, i) : min(len(lines), i + 5)])
                if re.search(r"\b(balances|amount|value|supply|totalSupply|balanceOf|_totalSupply)\b", context):
                    has_bound_check = re.search(r"\brequire\b|\bif\b.*\breturn\b|\bassert\b", context)
                    if not has_bound_check:
                        findings.append(
                            Finding(
                                severity=FindingSeverity.INFO,
                                category="sol_unchecked_block",
                                file=rel,
                                line=i,
                                message="unchecked block on financial values — verify no overflow/underflow possible.",
                                suggestion="Ensure inputs are bounded before unchecked arithmetic, or add require() checks.",
                            )
                        )

        # Detect subtraction without prior balance check (underflow risk in <0.8.0)
        if pragma_match and major == 0 and minor < 8:
            for i, line in enumerate(lines, 1):
                code = _strip(line.strip())
                if not code:
                    continue
                if re.search(r"[\w\[\]]+\s*-=\s*[\w\[\].]+", code) or re.search(
                    r"[\w\[\]]+\s*=\s*[\w\[\]]+\s*-\s*[\w\[\].]+", code
                ):
                    prev_context = " ".join(lines[max(0, i - 3) : i])
                    if not re.search(r"\brequire\s*\(.*>=|\.balanceOf|balances\[.*\]\s*>=", prev_context):
                        if re.search(r"\b(balances|amount|value|supply)\b", code):
                            findings.append(
                                Finding(
                                    severity=FindingSeverity.WARNING,
                                    category="sol_subtraction_underflow",
                                    file=rel,
                                    line=i,
                                    message="Subtraction without prior balance check — underflow risk in pre-0.8.0.",
                                    suggestion="Add require(balances[x] >= amount) before subtraction, or upgrade to >=0.8.0.",
                                )
                            )
