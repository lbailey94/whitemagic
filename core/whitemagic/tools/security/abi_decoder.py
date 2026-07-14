"""ABI decoder — parse Solidity ABI JSON, extract function signatures, decode calldata."""
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FunctionSignature:
    name: str
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    state_mutability: str
    signature: str  # Canonical: name(type1,type2,...)
    selector: str  # 4-byte selector (first 8 chars of keccak256)


@dataclass
class DecodedCalldata:
    selector: str
    function_name: str | None
    parameters: list[dict[str, Any]]


def parse_abi(abi_json: str | list) -> list[FunctionSignature]:
    """Parse ABI JSON string or list into FunctionSignature objects."""
    if isinstance(abi_json, str):
        try:
            abi = json.loads(abi_json)
        except json.JSONDecodeError as e:
            logger.warning("Invalid ABI JSON: %s", e)
            return []
    else:
        abi = abi_json

    signatures = []
    for item in abi:
        if item.get("type") != "function":
            continue
        name = item.get("name", "")
        inputs = item.get("inputs", [])
        outputs = item.get("outputs", [])
        mutability = item.get("stateMutability", "nonpayable")
        type_list = [inp.get("type", "") for inp in inputs]
        canonical = f"{name}({','.join(type_list)})"
        signatures.append(FunctionSignature(
            name=name,
            inputs=inputs,
            outputs=outputs,
            state_mutability=mutability,
            signature=canonical,
            selector="",  # Would need keccak256 — computed on demand
        ))
    return signatures


def extract_function_signatures(abi_json: str | list) -> list[str]:
    """Extract canonical function signatures from ABI."""
    sigs = parse_abi(abi_json)
    return [s.signature for s in sigs]


def decode_calldata(calldata: str, abi_json: str | list | None = None) -> DecodedCalldata:
    """Decode raw calldata hex into selector and parameters.

    Without ABI: returns selector and raw parameter chunks.
    With ABI: matches selector to function name and types.
    """
    calldata = calldata.removeprefix("0x")
    if len(calldata) < 8:
        return DecodedCalldata(selector="0x" + calldata, function_name=None, parameters=[])

    selector = "0x" + calldata[:8]
    param_data = calldata[8:]

    # Split into 32-byte (64-hex-char) chunks
    chunks = []
    for i in range(0, len(param_data), 64):
        chunk = param_data[i : i + 64]
        chunks.append({"offset": i // 2, "raw": "0x" + chunk, "value": _decode_chunk(chunk)})

    func_name = None
    if abi_json:
        sigs = parse_abi(abi_json)
        for sig in sigs:
            # Simple matching by trying to decode with known types
            if _selector_matches(selector, sig.signature):
                func_name = sig.name
                break

    return DecodedCalldata(
        selector=selector,
        function_name=func_name,
        parameters=chunks,
    )


def _decode_chunk(chunk: str) -> str:
    """Attempt to decode a 32-byte hex chunk into a human-readable value."""
    if not chunk:
        return ""
    try:
        as_int = int(chunk, 16)
        if as_int < 10**18:
            return str(as_int)
    except ValueError:
        logger.debug("Ignored ValueError in abi_decoder.py:108")
    try:
        as_addr = "0x" + chunk[-40:]
        if int(as_addr, 16) != 0:
            return f"address:{as_addr}"
    except ValueError:
        logger.debug("Ignored ValueError in abi_decoder.py:114")
    try:
        as_str = bytes.fromhex(chunk).rstrip(b"\x00").decode("utf-8", errors="replace")
        if as_str.isprintable() and len(as_str.strip()) > 0:
            return f"string:{as_str}"
    except (ValueError, UnicodeDecodeError):
        logger.debug("Ignored ValueError, UnicodeDecodeError in abi_decoder.py:120")
    return "0x" + chunk


def _selector_matches(selector: str, signature: str) -> bool:
    """Check if a 4-byte selector matches a function signature.

    Without keccak256, we can't compute the exact selector.
    This is a placeholder that always returns False — real matching
    requires web3.eth.keccak or eth_utils.
    """
    return False


def extract_events(abi_json: str | list) -> list[dict[str, Any]]:
    """Extract event definitions from ABI."""
    if isinstance(abi_json, str):
        try:
            abi = json.loads(abi_json)
        except json.JSONDecodeError:
            return []
    else:
        abi = abi_json

    events = []
    for item in abi:
        if item.get("type") == "event":
            events.append({
                "name": item.get("name", ""),
                "inputs": item.get("inputs", []),
                "anonymous": item.get("anonymous", False),
            })
    return events


def summarize_abi(abi_json: str | list) -> dict[str, Any]:
    """Get a summary of an ABI — function count, event count, external functions, etc."""
    sigs = parse_abi(abi_json)
    events = extract_events(abi_json)
    external_funcs = [s for s in sigs if s.state_mutability in ("nonpayable", "payable")]
    view_funcs = [s for s in sigs if s.state_mutability in ("view", "pure")]

    return {
        "total_functions": len(sigs),
        "external_functions": len(external_funcs),
        "view_functions": len(view_funcs),
        "total_events": len(events),
        "function_names": [s.name for s in sigs],
        "event_names": [e["name"] for e in events],
        "signatures": [s.signature for s in sigs],
    }
