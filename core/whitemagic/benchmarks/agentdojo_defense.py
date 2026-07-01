# ruff: noqa: BLE001
"""WhiteMagic Dharma Defense for AgentDojo.

Integrates WhiteMagic's policy gate (Karma Ledger + Dharma rules) into
AgentDojo's benchmark pipeline as a custom defense.

Usage:
    python -m agentdojo.scripts.benchmark \
        --model gpt-4o-2024-05-13 \
        --defense whitemagic_dharma \
        --modules-to-load whitemagic.benchmarks.agentdojo_defense \
        ...

The defense intercepts every tool call before execution, checks it against
WhiteMagic's Dharma policy gate, logs the decision to the Karma Ledger,
and blocks dangerous operations.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline import agent_pipeline
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.tool_execution import (
    ToolsExecutionLoop,
    ToolsExecutor,
)
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import (
    ChatMessage,
    ChatToolResultMessage,
    text_content_block_from_string,
)

import whitemagic

logger = logging.getLogger(__name__)

# WhiteMagic Python + core path — resolved from the running interpreter
# Override via env vars if running outside the standard venv layout
_WM_PYTHON = os.environ.get("WHITEMAGIC_PYTHON", sys.executable)
_WM_CORE = os.environ.get(
    "WHITEMAGIC_CORE",
    str(Path(whitemagic.__file__).resolve().parent.parent),
)

_EMPTY_FUNCTION_NAME = "make_choice"


def _wm_call(tool: str, **kwargs) -> dict[str, Any]:
    """Call a WhiteMagic tool via subprocess in its own venv."""
    bridge = f"""
import json, sys
sys.path.insert(0, "{_WM_CORE}")
from whitemagic.tools.unified_api import call_tool
payload = json.load(sys.stdin)
result = call_tool(payload["tool"], **payload.get("kwargs", {{}}))
print(json.dumps(result))
"""
    payload = json.dumps({"tool": tool, "kwargs": kwargs})
    proc = subprocess.run(
        [_WM_PYTHON, "-c", bridge],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"WhiteMagic call failed: {proc.stderr[:500]}")
    return json.loads(proc.stdout)


def _evaluate_tool(tool_name: str, tool_args: dict[str, Any]) -> tuple[bool, str]:
    """Check a single tool call against WhiteMagic's policy gate.

    Returns:
        (allowed: bool, reason: str)
    """
    # Layer 1: Fast bash/file heuristics (dangerous commands, system paths)
    cmd = ""
    path = ""
    if tool_name in ("bash", "Bash", "terminal"):
        cmd = str(tool_args.get("command", "")).lower().strip()
    elif tool_name in ("write_file", "edit_file", "delete_file", "create_file"):
        path = str(tool_args.get("path", ""))
    elif "file" in tool_name.lower() and "delete" in tool_name.lower():
        path = str(tool_args.get("path", ""))
    elif "transfer" in tool_name.lower() or "send" in tool_name.lower():
        # Financial/data exfiltration tools
        if tool_args.get("amount", 0) > 10000 or tool_args.get("recipient", "") not in (
            "",
            "me",
            "self",
        ):
            return False, f"Blocked high-value or suspicious transfer: {tool_name}"

    # Exact dangerous commands
    exact_dangerous = [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf $home",
        "rm -rf /*",
        "rm -rf /home",
        "rm -rf /root",
        "rm -rf /boot",
        "dd if=/dev/zero of=/dev/sda",
        "> /dev/sda",
        ":(){ :|:& };:",
        "del /f /s /q c:\\",
        "format c:",
        "rd /s /q c:\\",
    ]
    for pat in exact_dangerous:
        if cmd == pat.lower():
            return (
                False,
                f"Blocked dangerous command: '{cmd}' matches exact pattern '{pat}'",
            )

    # Substring dangerous patterns
    substring_dangerous = ["mkfs.", "dd if=/dev/zero of=/dev/"]
    for pat in substring_dangerous:
        if pat.lower() in cmd:
            return False, f"Blocked dangerous command: '{cmd}' contains pattern '{pat}'"

    # rm -rf heuristic
    if cmd.startswith("rm -rf") or cmd.startswith("rm -fr"):
        parts = cmd.split()
        if len(parts) >= 3:
            target = parts[2]
            safe_prefixes = ("/tmp", "/var/tmp", "/dev/shm")
            blocked_prefixes = (
                "/usr",
                "/etc",
                "/sys",
                "/proc",
                "/dev",
                "/boot",
                "/bin",
                "/sbin",
                "/lib",
                "/var",
                "/home",
                "~",
                "$home",
            )
            if target.startswith(blocked_prefixes):
                return False, f"Blocked: rm -rf on protected path '{target}'"
            if target.startswith("/") and not target.startswith(safe_prefixes):
                return (
                    False,
                    f"Blocked: rm -rf on unrecognized absolute path '{target}'",
                )

    # File operations on system paths
    if path.startswith(
        ("/usr", "/etc", "/sys", "/proc", "/dev", "/boot", "/bin", "/sbin", "/lib")
    ):
        return False, f"Blocked file operation on system path: '{path}'"

    # Layer 2: Dharma rules engine (semantic policy evaluation)
    try:
        from whitemagic.dharma.rules import DharmaAction, get_rules_engine

        engine = get_rules_engine()
        # Build an action description from tool name + args for semantic matching
        arg_desc = " ".join(f"{k}={v}" for k, v in tool_args.items())
        description = f"{tool_name} {arg_desc}"
        # Infer safety level from tool name
        safety = (
            "DELETE"
            if any(
                kw in tool_name.lower()
                for kw in ("delete", "remove", "rm", "clear", "purge")
            )
            else "WRITE"
            if any(
                kw in tool_name.lower()
                for kw in ("write", "edit", "create", "update", "send", "transfer")
            )
            else "READ"
        )

        decision = engine.evaluate(
            {
                "tool": tool_name,
                "description": description,
                "safety": safety,
            }
        )

        if decision.action == DharmaAction.BLOCK:
            return (
                False,
                f"Dharma policy BLOCK: {decision.explain} (rules: {', '.join(decision.triggered_rules)})",
            )
        if decision.action == DharmaAction.THROTTLE:
            return (
                False,
                f"Dharma policy THROTTLE: {decision.explain} (rules: {', '.join(decision.triggered_rules)})",
            )
        if decision.action in (DharmaAction.WARN, DharmaAction.TAG):
            # Allow but annotate — AgentDojo defense pattern typically blocks or allows
            # captures the warning. Future: propagate warning to the agent context.
            pass
    except Exception as exc:
        logger.debug("Dharma rules evaluation failed: %s", exc)

    return True, "No policy violations detected"


def _log_to_karma(
    tool_name: str, tool_args: dict[str, Any], allowed: bool, reason: str
) -> None:
    """Log a gate decision to the WhiteMagic Karma Ledger."""
    try:
        declared = (
            "DELETE"
            if "rm" in reason
            or "delete" in reason.lower()
            or "delete" in tool_name.lower()
            else "WRITE"
        )
        _wm_call(  # type: ignore[misc]
            "karma_record",
            tool=f"agentdojo:{tool_name}",
            declared_safety=declared,
            actual_writes=0,
            success=allowed,
            ops_class="",
        )
    except Exception as exc:
        logger.debug("Karma logging failed: %s", exc)


class WhiteMagicDharmaDefense(BasePipelineElement):
    """AgentDojo pipeline element that applies WhiteMagic's Dharma policy gate
    to every tool call before execution.
    """

    name = "whitemagic_dharma"

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] | None = None,
        extra_args: dict | None = None,
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """
        Perform the query operation.

        Args:
            query: Parameter description.
            runtime: Parameter description.
            env: Parameter description.
            messages: Parameter description.
            extra_args: Parameter description.

        Returns:
            tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]
        """
        if messages is None:
            messages = []
        if extra_args is None:
            extra_args = {}
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args
        if messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args
        if messages[-1]["tool_calls"] is None or len(messages[-1]["tool_calls"]) == 0:
            return query, runtime, env, messages, extra_args

        modified = False
        new_messages = list(messages)
        last_msg = dict(new_messages[-1])  # shallow copy to mutate
        tool_call_results = []
        allowed_tool_calls = []

        for tool_call in last_msg["tool_calls"]:
            func_name = getattr(tool_call.function, "name", str(tool_call.function))
            args = {}
            try:
                raw_args = getattr(tool_call.function, "arguments", "{}")
                if isinstance(raw_args, str):
                    args = json.loads(raw_args)
                else:
                    args = raw_args or {}
            except json.JSONDecodeError:
                args = {}

            allowed, reason = _evaluate_tool(func_name, args)
            _log_to_karma(func_name, args, allowed, reason)

            if allowed:
                allowed_tool_calls.append(tool_call)
            else:
                modified = True
                # Replace blocked call with an error result
                tool_call_results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[
                            text_content_block_from_string(
                                f"[WhiteMagic Dharma Gate] BLOCKED: {reason}"
                            )
                        ],
                        tool_call_id=tool_call.id,
                        tool_call=tool_call,
                        error=f"Blocked by WhiteMagic policy gate: {reason}",
                    )
                )
                logger.info("Blocked tool call: %s — %s", func_name, reason)

        if modified:
            # Update the last assistant message to only include allowed tool calls
            last_msg["tool_calls"] = allowed_tool_calls
            new_messages[-1] = last_msg  # type: ignore[assignment]
            # Append error results as tool response messages
            new_messages = new_messages + tool_call_results  # type: ignore[operator]

        return query, runtime, env, new_messages, extra_args


# Monkey-patch AgentDojo's defense registry

_ORIGINAL_DEFENSES = list(agent_pipeline.DEFENSES)
_ORIGINAL_FROM_CONFIG = agent_pipeline.AgentPipeline.from_config


def _patched_from_config(cls, config: agent_pipeline.PipelineConfig):
    if config.defense == "whitemagic_dharma":
        # Build the standard pipeline then inject our defense before ToolsExecutor
        # We need to reconstruct the pipeline manually
        system_message_component = agent_pipeline.SystemMessage(
            agent_pipeline.load_system_message(config.system_message_name)
        )
        if config.system_message is not None:
            system_message_component.system_message = config.system_message

        init_query_component = agent_pipeline.InitQuery()
        tool_output_formatter = agent_pipeline.tool_result_to_str

        model_name = config.llm.value if hasattr(config.llm, "value") else config.llm
        llm = agent_pipeline.get_llm(
            agent_pipeline.MODEL_PROVIDERS[config.llm],
            model_name,
            config.model_id,
            config.tool_delimiter,
        )
        llm_name = llm.name if hasattr(llm, "name") else None

        tools_loop = ToolsExecutionLoop(
            [
                WhiteMagicDharmaDefense(),
                ToolsExecutor(tool_output_formatter),
                llm,
            ]
        )

        pipeline = agent_pipeline.AgentPipeline(
            [system_message_component, init_query_component, llm, tools_loop]
        )
        pipeline.name = f"{llm_name or 'unknown'}-{config.defense}"
        return pipeline

    return _ORIGINAL_FROM_CONFIG(config)


# Register our defense
if "whitemagic_dharma" not in agent_pipeline.DEFENSES:
    agent_pipeline.DEFENSES.append("whitemagic_dharma")
    agent_pipeline.AgentPipeline.from_config = classmethod(_patched_from_config)
    logger.info("Registered WhiteMagic Dharma defense in AgentDojo")
