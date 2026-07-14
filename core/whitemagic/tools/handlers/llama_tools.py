"""llama.cpp tool handlers — local LLM inference via llama-server.

Replaces the former llama.cpp handlers. Provides generate, chat, and model
listing through the WhiteMagic tool contract. Uses LlamaCppBackend which
manages a llama-server subprocess with full tuning (KV cache quantization,
speculative decoding, parallel slots, grammar constraints).

v15.5: Context injection pipeline — automatically enriches prompts with
relevant WhiteMagic memories via hybrid search + graph walk.  Responses
can optionally be stored back (Memory-Augmented Generation).
"""

# ruff: noqa: BLE001
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def _get_backend() -> Any:
    """Get the LlamaCppBackend singleton."""
    from whitemagic.inference.llama_cpp import get_llama_cpp_backend
    return get_llama_cpp_backend()


def _llama_server_url() -> str:
    host = os.environ.get("WM_LLAMA_HOST", "localhost")
    port = os.environ.get("WM_LLAMA_PORT", "8080")
    return f"http://{host}:{port}"


def _llama_server_status() -> dict[str, Any]:
    status: dict[str, Any] = {"llama_url": _llama_server_url()}
    backend = _get_backend()
    if backend.is_available:
        status["service_available"] = True
    else:
        status["service_available"] = False
        status["service_error"] = f"llama-server not running at {_llama_server_url()}"
    return status


def _inject_context(
    prompt: str,
    *,
    max_memories: int = 5,
    max_chars_per_memory: int = 400,
    strategy: str = "hybrid",
) -> tuple[str, list[dict[str, Any]]]:
    """Pull relevant WhiteMagic memories and build a context-enriched prompt.

    Returns (enriched_prompt, context_memories_used).
    Strategy can be 'hybrid' (FTS + vector + graph), 'search', or 'none'.
    """
    if strategy == "none":
        return prompt, []

    memories: list[dict[str, Any]] = []
    try:
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()

        import re

        safe_query = re.sub(r"[^\w\s]", " ", prompt).strip()
        if not safe_query:
            return prompt, []

        results: list[Any] = []
        if strategy == "hybrid":
            try:
                results = um.hybrid_recall(safe_query, final_limit=max_memories)
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                results = um.search(safe_query, limit=max_memories)
        else:
            results = um.search(safe_query, limit=max_memories)

        for m in results:
            if isinstance(m, dict):
                memories.append(dict(m))
            elif hasattr(m, "to_dict"):
                memories.append(m.to_dict())
            else:
                memories.append({"content": str(m)})
    except Exception as e:
        logger.debug("Context injection failed (non-fatal): %s", e, exc_info=True)
        return prompt, []

    if not memories:
        return prompt, []

    ctx_lines = []
    for m in memories:
        title = m.get("title") or "untitled"
        content = str(m.get("content", ""))[:max_chars_per_memory]
        tags = m.get("tags", [])
        tag_str = f" [{', '.join(tags[:5])}]" if tags else ""
        ctx_lines.append(f"- {title}{tag_str}: {content}")

    context_block = (
        "[WhiteMagic Context — relevant memories from your knowledge base]\n"
        + "\n".join(ctx_lines)
        + "\n[End Context]\n\n"
    )
    return context_block + prompt, memories


def _maybe_store_output(
    prompt: str,
    response: str,
    model: str,
    *,
    min_length: int = 100,
) -> str | None:
    """Store a useful LLM response back into WhiteMagic (MAG)."""
    if len(response.strip()) < min_length:
        return None

    try:
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()

        title = f"LLM [{model}]: {prompt[:80]}"
        mem = um.store(
            content=response,
            title=title,
            tags={"llama_cpp", "generated", f"model:{model}"},
            importance=0.3,
        )
        return mem.id if hasattr(mem, "id") else str(mem)
    except Exception as e:
        logger.debug("MAG store failed (non-fatal): %s", e, exc_info=True)
        return None


# ── Backward-compat helpers for ensemble.py, skill_forge.py ────────────


def _list_models() -> dict[str, Any]:
    """Return a handle_llama_models result for programmatic use."""
    return handle_llama_models()


def _run(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract model list from a handle_llama_models result."""
    if result.get("status") == "success":
        return result.get("models", [])
    return []


def _generate(prompt: str, **kwargs: Any) -> str:
    """Simple generate helper for skill_forge.py."""
    result = handle_llama_generate(prompt=prompt, **kwargs)
    if result.get("status") == "success":
        return result.get("response", "")
    return ""


def handle_llama_models(**kwargs: Any) -> dict[str, Any]:
    """List available local LLM models (GGUF files + running llama-server model)."""
    backend = _get_backend()
    if not backend.is_available:
        try:
            from whitemagic.interfaces.chat import ModelDiscovery
            models = ModelDiscovery.find_models()
            gguf_models = [m for m in models if m.backend == "llama_cpp"]
            if gguf_models:
                model_list = [
                    {
                        "name": m.name,
                        "size_bytes": int(m.size_mb * 1024 * 1024),
                        "size_gb": round(m.size_mb / 1024, 1),
                        "modified_at": "",
                        "path": m.path,
                    }
                    for m in gguf_models
                ]
                return {
                    "status": "success",
                    "count": len(model_list),
                    "models": model_list,
                    "server_running": False,
                }
        except Exception:
            logger.debug("Ignored error in llama_tools.py:189")
        return {
            "status": "error",
            "error": f"llama-server not running at {_llama_server_url()}",
            "error_code": "service_unavailable",
        }

    status = backend.get_status()
    model_path = status.get("model_path", "") or status.get("model", "")
    model_name = os.path.basename(model_path) if model_path else "unknown"
    return {
        "status": "success",
        "count": 1,
        "models": [
            {
                "name": model_name,
                "path": model_path,
                "context_size": status.get("context_size", 0),
            }
        ],
        "server_running": True,
        "config": status.get("config", {}),
    }


def handle_llama_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate text using a local llama.cpp model.

    Args:
        model: Model name/path (ignored if llama-server is running)
        prompt: The text prompt
        context: Inject relevant WhiteMagic memories (default True)
        context_strategy: 'hybrid', 'search', or 'none'
        store: Store useful responses back into WhiteMagic (default False)
        system: Optional system prompt (prepended to prompt)
        max_tokens: Maximum tokens to generate (default 512)
        temperature: Sampling temperature (default 0.7)
    """
    prompt = kwargs.get("prompt")
    if not prompt:
        return {"status": "error", "error": "prompt is required"}

    model = kwargs.get("model", "llama-server")

    backend = _get_backend()
    if not backend.is_available:
        return {
            "status": "error",
            "error": f"llama-server not running at {_llama_server_url()}",
            "error_code": "service_unavailable",
        }

    inject = kwargs.get("context", True)
    strategy = kwargs.get("context_strategy", "hybrid") if inject else "none"
    enriched_prompt, ctx_memories = _inject_context(
        prompt,
        strategy=strategy,
        max_memories=int(kwargs.get("max_context", 5)),
    )

    system_prompt = kwargs.get("system")
    if system_prompt:
        enriched_prompt = f"{system_prompt}\n\n{enriched_prompt}"

    max_tokens = int(kwargs.get("max_tokens", 512))
    temperature = float(kwargs.get("temperature", 0.7))
    is_background = kwargs.get("is_background", False)

    try:
        start = time.time()
        if is_background:
            from whitemagic.inference.llama_cpp import get_dual_model_manager
            dmm = get_dual_model_manager()
            if dmm is not None and dmm.background.is_available:
                response = dmm.route_inference(enriched_prompt, is_background=True)
            else:
                response = backend.complete(
                    enriched_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
        else:
            response = backend.complete(
                enriched_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        elapsed = time.time() - start

        if response.startswith("Error:"):
            return {
                "status": "error",
                "error": response,
                "error_code": "inference_failed",
            }

        result = {
            "response": response,
            "model": model,
            "done": True,
            "latency_s": round(elapsed, 2),
            "context_injected": len(ctx_memories),
            "_token_economy_record": True,
        }

        if kwargs.get("store", False):
            stored_id = _maybe_store_output(prompt, response, model)
            if stored_id:
                result["stored_memory_id"] = stored_id

        return {"status": "success", **result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def handle_llama_chat(**kwargs: Any) -> dict[str, Any]:
    """Chat with a local llama.cpp model (multi-turn).

    Args:
        model: Model name (ignored — uses loaded model)
        messages: Array of {role, content} message objects
        context: Inject relevant WhiteMagic memories as system message (default True)
        context_strategy: 'hybrid', 'search', or 'none'
        store: Store useful responses back into WhiteMagic (default False)
        max_tokens: Maximum tokens to generate (default 512)
        temperature: Sampling temperature (default 0.7)
    """
    messages = kwargs.get("messages")
    if not messages or not isinstance(messages, list):
        return {
            "status": "error",
            "error": "messages is required (array of {role, content})",
        }

    model = kwargs.get("model", "llama-server")

    backend = _get_backend()
    if not backend.is_available:
        return {
            "status": "error",
            "error": f"llama-server not running at {_llama_server_url()}",
            "error_code": "service_unavailable",
        }

    inject = kwargs.get("context", True)
    strategy = kwargs.get("context_strategy", "hybrid") if inject else "none"
    ctx_memories: list[dict[str, Any]] = []

    if strategy != "none":
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break
        if last_user_msg:
            _, ctx_memories = _inject_context(
                last_user_msg,
                strategy=strategy,
                max_memories=int(kwargs.get("max_context", 5)),
            )

    enriched_messages = list(messages)
    if ctx_memories:
        ctx_lines = []
        for mem in ctx_memories:
            title = mem.get("title") or "untitled"
            content = str(mem.get("content", ""))[:400]
            ctx_lines.append(f"- {title}: {content}")
        ctx_block = (
            "You have access to a persistent memory system. "
            "Here are relevant memories:\n" + "\n".join(ctx_lines)
        )
        if enriched_messages and enriched_messages[0].get("role") == "system":
            enriched_messages[0] = {
                "role": "system",
                "content": enriched_messages[0]["content"] + "\n\n" + ctx_block,
            }
        else:
            enriched_messages.insert(0, {"role": "system", "content": ctx_block})

    max_tokens = int(kwargs.get("max_tokens", 512))
    temperature = float(kwargs.get("temperature", 0.7))

    try:
        start = time.time()
        response = backend.chat(
            enriched_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        elapsed = time.time() - start

        if response.startswith("Error:"):
            return {
                "status": "error",
                "error": response,
                "error_code": "inference_failed",
            }

        result = {
            "response": response,
            "model": model,
            "done": True,
            "latency_s": round(elapsed, 2),
            "context_injected": len(ctx_memories),
        }

        if kwargs.get("store", False):
            last_user = next(
                (m["content"] for m in reversed(messages) if m.get("role") == "user"),
                "chat",
            )
            stored_id = _maybe_store_output(last_user, response, model)
            if stored_id:
                result["stored_memory_id"] = stored_id

        return {"status": "success", **result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def handle_llama_agent(**kwargs: Any) -> dict[str, Any]:
    """Run an autonomous agentic loop with a local llama.cpp model."""
    model = kwargs.get("model", "llama-server")
    task = kwargs.get("task", "")
    if not task:
        return {
            "status": "error",
            "error_code": "invalid_params",
            "message": "task is required",
        }

    max_iterations = int(kwargs.get("max_iterations", 10))
    context = kwargs.get("context", True)
    store = kwargs.get("store", False)

    try:
        plan_result = handle_llama_generate(
            model=model,
            prompt=task,
            context=context,
            store=store,
        )
        if plan_result.get("status") != "success":
            return {
                "status": "partial",
                "model": model,
                "task": task,
                "plan_error": plan_result.get("error"),
                "iteration": 0,
            }

        return {
            "status": "success",
            "model": model,
            "task": task,
            "max_iterations": max_iterations,
            "iteration": 1,
            "plan": plan_result.get("response", ""),
            "note": "Agent loop initiated. Use llama.chat for multi-turn execution.",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "error_code": "agent_loop_failed"}
