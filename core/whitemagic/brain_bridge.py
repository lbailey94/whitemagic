# ruff: noqa: BLE001
import base64
import json
import logging
import sys
import traceback
from typing import Any

# Set up logging to stderr so it doesn't interfere with stdout communication
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("brain_bridge")

def send_response(data: dict[str, Any]):
    """Send a base64-encoded JSON response to Elixir."""
    try:
        json_str = json.dumps(data)
        b64_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        sys.stdout.write(b64_str + "\n")
        sys.stdout.flush()
    except (OSError, FileNotFoundError, PermissionError) as e:
        logger.error("Error encoding response: %s", e, exc_info=True)

def handle_ping(args: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a ping event.

    Args:
        args: Parameter description.

    Returns:
        dict[str, Any]
    """
    return {"status": "ok", "pong": True}

def handle_consolidate(args: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a consolidate event.

    Args:
        args: Parameter description.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.memory.unified import consolidate
        count = consolidate()
        return {"status": "ok", "stats": {"consolidated": count}}
    except (ImportError, ModuleNotFoundError) as e:
        return {"status": "error", "message": str(e)}

def handle_consult_oracle(args: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a consult oracle event.

    Args:
        args: Parameter description.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.grimoire.auto_cast import CastContext, get_auto_caster
        question = args.get("question", "")
        context = args.get("context", {})

        caster = get_auto_caster()
        ctx = CastContext(
            task=question,
            emotional_state=context.get("emotional_state", "neutral"),
            wu_xing=context.get("wu_xing", "earth"),
            yin_yang=context.get("yin_yang", "yin")
        )
        results = caster.process_context(ctx)

        return {
            "status": "ok",
            "suggestions": [
                {"spell": r.spell.name, "confidence": round(r.confidence, 3)}
                for r in results if r.spell
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_execute_phase(args: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a execute phase event.

    Args:
        args: Parameter description.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
        phase = args.get("phase")
        dc = get_dream_cycle()

        # Map Elixir phase string to Python method
        phase_map = {
            "triage": dc._dream_triage,
            "consolidation": dc._dream_consolidation,
            "serendipity": dc._dream_serendipity,
            "governance": dc._dream_governance,
            "narrative": dc._dream_narrative,
            "kaizen": dc._dream_kaizen,
            "oracle": dc._dream_oracle,
            "decay": dc._dream_decay,
            "constellation": dc._dream_constellation,
            "prediction": dc._dream_prediction,
            "enrichment": dc._dream_enrichment,
            "harmonize": dc._dream_harmonize
        }

        if phase in phase_map:
            details = phase_map[phase]()
            return {"status": "ok", "details": details}
        else:
            return {"status": "error", "message": f"Unknown phase: {phase}"}
    except Exception as e:
        logger.error(f"Phase execution error: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

def main():
    """
    Perform the main operation.
    """
    logger.info("Brain Bridge active. Waiting for commands...")

    for line in sys.stdin:
        if not line.strip():
            continue

        try:
            request = json.loads(line)
            op = request.get("op")
            args = request.get("args", {})

            logger.info(f"Received op: {op}")

            if op == "ping":
                response = handle_ping(args)
            elif op == "consolidate":
                response = handle_consolidate(args)
            elif op == "consult_oracle":
                response = handle_consult_oracle(args)
            elif op == "execute_phase":
                response = handle_execute_phase(args)
            else:
                response = {"status": "error", "message": f"Unknown operation: {op}"}

            send_response(response)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {line}")
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            logger.error(f"Unexpected error: {traceback.format_exc()}")
            send_response({"status": "error", "message": "Internal bridge error"})

if __name__ == "__main__":
    main()
