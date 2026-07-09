import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _strip_comments_and_strings(line: str) -> str:
    """Remove Solidity string literals and inline comments so regex doesn't match inside them."""
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    line = re.sub(r"'(?:\\.|[^'\\])*'", "''", line)
    if "//" in line:
        line = line[: line.index("//")]
    return line


@register
def check_solidity(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Solidity security: tx.origin, unchecked calls, unprotected selfdestruct, delegatecall, reentrancy, shadowing, block.timestamp randomness."""
    for sol_file in file_index.files_by_extension(".sol"):
        try:
            content = file_index.read_text(sol_file)
        except (OSError, UnicodeDecodeError):
            continue

        lines = content.splitlines()
        rel_path = str(sol_file.relative_to(project_path))

        # Track contract state variables for shadowing detection
        state_vars: dict[str, int] = {}
        in_contract = False
        contract_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            if stripped.startswith("*"):
                continue

            code = _strip_comments_and_strings(stripped)

            # Track contract scope
            if re.search(r"\b(?:contract|library|interface)\s+\w+", code):
                in_contract = True
                contract_depth = code.count("{") - code.count("}")
                continue

            if in_contract:
                contract_depth += code.count("{") - code.count("}")
                if contract_depth <= 0:
                    in_contract = False

            # --- tx.origin in conditions ---
            if re.search(r"\btx\.origin\b", code):
                if re.search(r"(==|!=|require|if|assert|modifier)", code):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="sol_tx_origin_auth",
                            file=rel_path,
                            line=i,
                            message="tx.origin used for authorization — vulnerable to phishing attacks.",
                            suggestion="Use msg.sender instead of tx.origin for authorization checks.",
                        )
                    )

            # --- Unchecked low-level .call() ---
            for match in re.finditer(r"\.call\{[^}]*\}\(|\.call\(", code):
                rest_of_line = code[match.end():]
                next_few = " ".join(lines[i : min(len(lines), i + 3)])
                if not re.search(r"\b(require|assert|if|bool\s|response|success|result)", rest_of_line + " " + next_few):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="sol_unchecked_call",
                            file=rel_path,
                            line=i,
                            message="Unchecked low-level .call() — return value not verified.",
                            suggestion="Check the return value: (bool success, bytes memory data) = addr.call{...}(...); require(success);",
                        )
                    )

            # --- Unprotected selfdestruct / suicide ---
            if re.search(r"\bselfdestruct\s*\(|\bsuicide\s*\(", code):
                prev_lines = " ".join(lines[max(0, i - 5) : i])
                has_auth = re.search(r"\b(onlyOwner|onlyRole|require\s*\(\s*msg\.sender|modifier)", prev_lines)
                if not has_auth:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="sol_unprotected_selfdestruct",
                            file=rel_path,
                            line=i,
                            message="selfdestruct/suicide without access control.",
                            suggestion="Protect with onlyOwner or onlyRole modifier. selfdestruct can lock funds or destroy contract.",
                        )
                    )

            # --- delegatecall to user-controlled address ---
            if re.search(r"\.delegatecall\s*\(", code):
                if re.search(r"\bmsg\.sender\b|\bmsg\.data\b|\bcalldata\b", code) or re.search(
                    r"\bmsg\.sender\b|\bmsg\.data\b|\bcalldata\b",
                    " ".join(lines[max(0, i - 3) : i]),
                ):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="sol_delegatecall_user",
                            file=rel_path,
                            line=i,
                            message="delegatecall to potentially user-controlled address — arbitrary code execution risk.",
                            suggestion="Never delegatecall to user-supplied addresses. Use staticcall or restrict to trusted targets.",
                        )
                    )

            # --- Unchecked transfer/send (pre-0.8.0 pattern) ---
            if re.search(r"\.(transfer|send)\s*\(", code):
                rest = code + " " + " ".join(lines[i : min(len(lines), i + 2)])
                if not re.search(r"\brequire\s*\(|\bif\s*\(|\bassert\s*\(|\bbool\b", rest):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="sol_unchecked_transfer",
                            file=rel_path,
                            line=i,
                            message=".transfer()/.send() return value not checked (pre-0.8.0 revert behavior).",
                            suggestion="Use .call() with require() check, or wrap .send() in require().",
                        )
                    )

            # --- block.timestamp / blockhash as randomness ---
            if re.search(r"\bblock\.timestamp\b|\bblockhash\s*\(", code):
                full_text_lower = content.lower()
                if re.search(r"\brandom\b|\blottery\b|\bseed\b|\brandomness\b", code.lower()) or re.search(
                    r"\brandom\b|\blottery\b|\bseed\b|\brandomness\b",
                    full_text_lower,
                ):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="sol_block_timestamp_random",
                            file=rel_path,
                            line=i,
                            message="block.timestamp/blockhash used as randomness source — miner-manipulable.",
                            suggestion="Use Chainlink VRF or commit-reveal scheme for on-chain randomness.",
                        )
                    )

            # --- State variable shadowing (simplified) ---
            var_match = re.match(r"\s*(?:uint\d*|int\d*|bool|address|string|bytes\d*|mapping)\s+(?:public\s+|private\s+|internal\s+|constant\s+)?(\w+)", line)
            if var_match and in_contract and contract_depth > 0:
                var_name = var_match.group(1)
                if var_name in state_vars:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="sol_state_shadowing",
                            file=rel_path,
                            line=i,
                            message=f"State variable '{var_name}' may shadow an inherited variable.",
                            suggestion="Rename to avoid shadowing — shadowing can cause storage collisions in proxy patterns.",
                        )
                    )
                else:
                    state_vars[var_name] = i

            # --- Unchecked external call before state update (reentrancy heuristic) ---
            if re.search(r"\.(call|transfer|send)\s*[\({]", code):
                has_state_write_after = False
                for future_line in lines[i : min(len(lines), i + 5)]:
                    future_code = _strip_comments_and_strings(future_line.strip())
                    if re.search(r"^\s*\w+\s*=\s*", future_code) or re.search(r"\brequire\s*\(", future_code):
                        has_state_write_after = True
                        break
                has_state_write_before = False
                for prev_line in lines[max(0, i - 5) : i]:
                    prev_code = _strip_comments_and_strings(prev_line.strip())
                    if re.search(r"^\s*\w+\s*[-+*/]?=\s*", prev_code) or re.search(r"\bbalances\b|\b_balance\b|\bmsg\.value\b", prev_code):
                        has_state_write_before = False
                        break
                if not has_state_write_after and not has_state_write_before:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="sol_reentrancy_risk",
                            file=rel_path,
                            line=i,
                            message="External call detected — potential reentrancy if state updated after call.",
                            suggestion="Follow checks-effects-interactions pattern: update state before external calls, or use ReentrancyGuard.",
                        )
                    )

            # --- Unprotected mint / arbitrary transfer ---
            if re.search(r"\b_mint\s*\(|\btransfer\s*\(", code):
                if re.search(r"\bmsg\.sender\b", code) and not re.search(r"\bonlyOwner\b|\bonlyRole\b|\brequire\s*\(\s*msg\.sender\s*==", " ".join(lines[max(0, i - 3) : i + 1])):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="sol_unprotected_mint_transfer",
                            file=rel_path,
                            line=i,
                            message="mint/transfer involving msg.sender without visible access control.",
                            suggestion="Ensure only authorized roles can mint or transfer to arbitrary addresses.",
                        )
                    )
