# ruff: noqa: BLE001
"""llama.cpp agent handler — autonomous agentic loop with tool calling.

Implements a real iterative tool-calling loop inspired by Sakana Fugu's
Conductor pattern (ICLR 2026). The local LLM generates responses, parses
tool-call requests, dispatches WhiteMagic tools via the unified API, and
feeds results back — iterating until task completion or max iterations.

Uses LlamaCppBackend (llama-server) for inference with full tuning support.
"""

import json
import logging
import re
import time
from typing import Any

from whitemagic.tools.handlers.tool_bandit import get_tool_bandit

logger = logging.getLogger(__name__)

_TOOL_CALL_PATTERN = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL,
)
_TOOL_CALL_INLINE = re.compile(
    r"\[TOOL_CALL\]\s*(\{.*?\})\s*(?:\[/TOOL_CALL\]|$)",
    re.DOTALL,
)
_COMPLETION_MARKERS = {"DONE", "TASK_COMPLETE", "COMPLETE", "FINISHED"}


def handle_llama_agent(**kwargs: Any) -> dict[str, Any]:
    """Run an autonomous agentic loop with a local LLM (llama.cpp).

    Args:
        model: Model name (ignored — uses loaded llama-server model)
        task: The task to accomplish
        max_iterations: Maximum loop iterations (default 10)
        system: Optional system prompt override
        context: Inject WhiteMagic memories (default True)
        store: Store agent outputs as memories (default True)
        available_tools: List of tool names the agent can call (default: auto-detect)
        temperature: Sampling temperature (default 0.7)

    Returns:
        Result with iteration log, final answer, and tool calls made.
    """
    model = kwargs.get("model", "llama-server")
    task = kwargs.get("task", "")
    if not task:
        return {
            "status": "error",
            "error_code": "invalid_params",
            "message": "task is required",
        }

    max_iterations = int(kwargs.get("max_iterations", 10))
    temperature = float(kwargs.get("temperature", 0.7))
    store_output = kwargs.get("store", True)

    from whitemagic.inference.llama_cpp import get_llama_cpp_backend

    backend = get_llama_cpp_backend()
    if not backend.is_available:
        return {
            "status": "error",
            "error": "llama-server not available",
            "error_code": "service_unavailable",
        }

    bandit = get_tool_bandit()
    task_type = bandit.classify_task_type(task)
    available_tools = kwargs.get("available_tools")
    if available_tools:
        bandit.register_tools(available_tools)
    recommended = bandit.recommend_tools(task=task, k=5, task_type=task_type)
    system_prompt = kwargs.get("system") or _build_system_prompt(
        available_tools, recommended, task_type
    )

    inject = kwargs.get("context", True)
    context_block = ""
    if inject:
        context_block = _inject_task_context(task)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt + context_block},
        {"role": "user", "content": task},
    ]

    iterations: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    total_tokens = 0
    final_answer = ""
    completed = False

    for iteration in range(1, max_iterations + 1):
        iter_start = time.time()
        logger.info("Agent iteration %d/%d", iteration, max_iterations)

        try:
            response = backend.chat(messages, temperature=temperature)
        except Exception as exc:
            logger.error("Agent iteration %d failed: %s", iteration, exc)
            iterations.append(
                {
                    "iteration": iteration,
                    "error": str(exc),
                    "duration_ms": (time.time() - iter_start) * 1000,
                }
            )
            break

        if response.startswith("Error:"):
            iterations.append(
                {
                    "iteration": iteration,
                    "error": response,
                    "duration_ms": (time.time() - iter_start) * 1000,
                }
            )
            break

        eval_count = len(response) // 4  # rough token estimate
        total_tokens += eval_count

        try:
            from whitemagic.core.consciousness.token_economy import get_token_tracker

            get_token_tracker().record_usage(
                eval_count, source="local", operation=f"llama_agent:{model}"
            )
        except (ImportError, AttributeError):
            pass

        calls = _parse_tool_calls(response)
        is_complete = _check_completion(response, calls)

        iter_info: dict[str, Any] = {
            "iteration": iteration,
            "response_preview": response[:200],
            "tool_calls": calls,
            "tokens": eval_count,
            "duration_ms": (time.time() - iter_start) * 1000,
        }
        iterations.append(iter_info)

        if calls:
            for call in calls:
                tool_name = call.get("tool", "")
                tool_args = call.get("args", {})

                logger.info("Tool call: %s(%s)", tool_name, list(tool_args.keys()))
                tool_result = _dispatch_tool(tool_name, tool_args)
                success = tool_result.get("status") == "success"
                bandit.record_outcome(tool_name, success=success, task_type=task_type)
                tool_calls.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "args": tool_args,
                        "result_status": tool_result.get("status", "unknown"),
                        "result_preview": str(tool_result.get("details", tool_result))[
                            :200
                        ],
                    }
                )

                messages.append({"role": "assistant", "content": response})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool '{tool_name}' returned:\n```json\n{json.dumps(tool_result, default=str, indent=2)[:2000]}\n```\nContinue with the task or say DONE if complete.",
                    }
                )

        if is_complete:
            final_answer = response
            completed = True
            logger.info("Agent completed at iteration %d", iteration)
            break

        if not calls:
            final_answer = response
            completed = True
            logger.info(
                "Agent finished (no more tool calls) at iteration %d", iteration
            )
            break

        if not calls:
            messages.append({"role": "assistant", "content": response})

    if not final_answer and iterations:
        final_answer = iterations[-1].get("response_preview", "")

    stored_id = None
    if store_output and final_answer:
        stored_id = _store_agent_output(task, final_answer, model, iterations)

    return {
        "status": "success",
        "model": model,
        "task": task,
        "completed": completed,
        "iterations": len(iterations),
        "max_iterations": max_iterations,
        "total_tokens": total_tokens,
        "tool_calls_made": len(tool_calls),
        "tool_calls": tool_calls,
        "iteration_log": iterations,
        "final_answer": final_answer,
        "stored_memory_id": stored_id,
    }


def _build_system_prompt(
    available_tools: list[str] | None = None,
    recommended: list[dict[str, Any]] | None = None,
    task_type: str = "general",
) -> str:
    """Build system prompt with tool-calling instructions and bandit recommendations."""
    tools_section = ""
    if available_tools:
        tools_list = "\n".join(f"  - {t}" for t in available_tools)
        tools_section = f"\n\nAvailable tools:\n{tools_list}"
    else:
        tools_section = "\n\nYou have access to WhiteMagic's tool system. Available tools include memory search, knowledge graph queries, and analysis tools."

    rec_section = ""
    if recommended:
        rec_lines = []
        for rec in recommended:
            rec_lines.append(
                f"  - {rec['tool']} (success rate: {rec['expected_value']:.1%}, {rec['total_calls']} past calls)"
            )
        rec_section = (
            f"\n\nRecommended tools for this task type ({task_type}):\n"
            + "\n".join(rec_lines)
        )

    return (
        "You are an autonomous AI agent powered by WhiteMagic."
        + tools_section
        + rec_section
        + """

To call a tool, include a JSON block in your response:
```json
{"tool": "tool_name", "args": {"param": "value"}}
```

You can make multiple tool calls in sequence. After each tool call, you will receive the result and can decide what to do next.

When the task is complete, respond with DONE followed by your final answer.

Be concise and efficient. Use tools when they help, but don't over-use them."""
    )


def _inject_task_context(task: str) -> str:
    """Inject relevant WhiteMagic memories as context for the task."""
    try:
        from whitemagic.tools.handlers.llama_tools import _inject_context

        _, memories = _inject_context(task, strategy="hybrid", max_memories=5)
        if memories:
            lines = []
            for mem in memories:
                title = mem.get("title") or "untitled"
                content = str(mem.get("content", ""))[:300]
                lines.append(f"- {title}: {content}")
            return "\n\nRelevant memories:\n" + "\n".join(lines)
    except Exception as exc:
        logger.debug("Context injection failed: %s", exc)
    return ""


def _parse_tool_calls(response: str) -> list[dict[str, Any]]:
    """Parse tool-call requests from model response."""
    calls: list[dict[str, Any]] = []

    for match in _TOOL_CALL_PATTERN.finditer(response):
        try:
            data = json.loads(match.group(1))
            if "tool" in data:
                calls.append(
                    {
                        "tool": data["tool"],
                        "args": data.get("args", data.get("parameters", {})),
                    }
                )
        except json.JSONDecodeError:
            continue

    for match in _TOOL_CALL_INLINE.finditer(response):
        try:
            data = json.loads(match.group(1))
            if "tool" in data:
                calls.append(
                    {
                        "tool": data["tool"],
                        "args": data.get("args", data.get("parameters", {})),
                    }
                )
        except json.JSONDecodeError:
            continue

    return calls


def _check_completion(response: str, tool_calls: list[dict[str, Any]]) -> bool:
    """Check if the agent has completed the task."""
    response_upper = response.strip().upper()
    for marker in _COMPLETION_MARKERS:
        if response_upper.startswith(marker):
            return True

    if not tool_calls and len(response) > 50:
        return True

    return False


def _dispatch_tool(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a WhiteMagic tool call via the unified API."""
    try:
        from whitemagic.tools.unified_api import UnifiedAPI

        api = UnifiedAPI()
        result = api.call(tool_name, **tool_args)
        if isinstance(result, dict):
            return result
        return {"status": "success", "result": str(result)}
    except Exception as exc:
        logger.error("Tool dispatch failed for %s: %s", tool_name, exc)
        return {
            "status": "error",
            "error": str(exc),
            "tool": tool_name,
        }


def _store_agent_output(
    task: str,
    output: str,
    model: str,
    iterations: list[dict[str, Any]],
) -> str | None:
    """Store agent output as a WhiteMagic memory."""
    try:
        from whitemagic.core.memory.unified import UnifiedMemory

        mem = UnifiedMemory()
        content = f"Task: {task}\n\nResult: {output[:2000]}"
        memory_id = mem.remember(
            content=content,
            title=f"Agent: {task[:60]}",
            tags=["agent", "llama_cpp", model, "autonomous"],
            source="llama_agent",
            metadata={
                "model": model,
                "iterations": len(iterations),
                "tool_calls": sum(len(i.get("tool_calls", [])) for i in iterations),
            },
        )
        return str(memory_id) if memory_id else None
    except Exception as exc:
        logger.debug("Failed to store agent output: %s", exc)
        return None
