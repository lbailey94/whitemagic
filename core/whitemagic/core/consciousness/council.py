# ruff: noqa: BLE001
"""Council Mode & Deep Lane Escalation — multi-perspective deliberation.

Extracted from sentience.py as part of consciousness subsystem synthesis.

Phase 5 — Deep Lane:
  - DeepLaneEscalation: 3B model detects complexity → escalates to 8B council
  - CouncilMode: Skeptic/Builder/Dreamer/Empath personas deliberate for consensus
  - DreamLane: 3B model runs during theta/delta for memory consolidation
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── Phase 5: Deep Lane Escalation ────────────────────────────────────


class DeepLaneEscalation:
    """Detect when the 3B model needs help from a larger model.

    Escalation triggers:
    - Model output contains uncertainty markers ("I'm not sure", "perhaps", repeated hedging)
    - Task complexity score exceeds threshold
    - Tool call failure rate is high
    - User explicitly requests deeper analysis

    When triggered, the system can:
    1. Escalate to a larger local model (8B)
    2. Convene a council (CouncilMode)
    3. Both
    """

    UNCERTAINTY_MARKERS = [
        "i'm not sure", "perhaps", "maybe", "i think", "possibly",
        "i don't know", "uncertain", "unclear", "hard to say",
        "it might", "could be", "i'm not confident",
    ]

    @staticmethod
    def should_escalate(
        model_output: str,
        tool_failures: int = 0,
        complexity_score: float = 0.0,
    ) -> bool:
        """Determine if the current interaction should be escalated.

        Args:
            model_output: The 3B model's response text.
            tool_failures: Number of failed tool calls in this turn.
            complexity_score: 0-1 complexity score from the classifier.

        Returns:
            True if escalation is recommended.
        """
        # High complexity
        if complexity_score > 0.7:
            return True

        # Multiple tool failures
        if tool_failures >= 2:
            return True

        # Uncertainty markers in output
        output_lower = model_output.lower()
        uncertainty_count = sum(
            1 for marker in DeepLaneEscalation.UNCERTAINTY_MARKERS
            if marker in output_lower
        )
        if uncertainty_count >= 3:
            return True

        return False

    @staticmethod
    def escalate(
        messages: list[dict[str, str]],
        reason: str = "",
    ) -> dict[str, Any]:
        """Escalate to council mode for deeper analysis.

        Returns the council's consensus response.
        """
        return CouncilMode.convene(messages, reason=reason)


# ── Phase 5: Council Mode ────────────────────────────────────────────


class CouncilPersona(StrEnum):
    """Council personas for multi-perspective deliberation."""

    SKEPTIC = "skeptic"  # Questions assumptions, finds flaws
    BUILDER = "builder"  # Pragmatic, focuses on implementation
    DREAMER = "dreamer"  # Creative, explores possibilities
    EMPATH = "empath"  # Considers emotional and ethical dimensions


COUNCIL_SYSTEM_PROMPTS: dict[CouncilPersona, str] = {
    CouncilPersona.SKEPTIC: (
        "You are the Skeptic. You question assumptions, identify flaws, "
        "and stress-test ideas. You don't reject — you probe. Your goal "
        "is to make the final answer more robust by finding weaknesses."
    ),
    CouncilPersona.BUILDER: (
        "You are the Builder. You focus on practical implementation. "
        "How would this actually work? What are the steps? What resources "
        "are needed? You turn ideas into plans."
    ),
    CouncilPersona.DREAMER: (
        "You are the Dreamer. You explore possibilities, make unexpected "
        "connections, and think beyond the obvious. What could this mean? "
        "What else is possible? What would be amazing?"
    ),
    CouncilPersona.EMPATH: (
        "You are the Empath. You consider how this affects everyone involved. "
        "What are the emotional dimensions? Is this ethical? Who benefits? "
        "Who might be harmed? What feels right?"
    ),
}


class CouncilMode:
    """Multi-persona council deliberation for complex decisions.

    When a problem is too complex for the 3B model alone, the council
    convenes: four personas each analyze the problem from their perspective,
    then a synthesis combines their insights into a consensus response.
    """

    @staticmethod
    def convene(
        messages: list[dict[str, str]],
        reason: str = "",
    ) -> dict[str, Any]:
        """Convene the council for deliberation.

        Args:
            messages: The conversation context.
            reason: Why the council was convened.

        Returns:
            A dict with each persona's response and the synthesized consensus.
        """
        result: dict[str, Any] = {
            "convened": True,
            "reason": reason,
            "perspectives": {},
            "consensus": "",
            "timestamp": datetime.now().isoformat(),
        }

        # Get each persona's perspective
        for persona in CouncilPersona:
            try:
                perspective = CouncilMode._get_perspective(persona, messages)
                result["perspectives"][persona.value] = perspective
            except Exception as e:
                logger.debug("Council %s failed: %s", persona.value, e)
                result["perspectives"][persona.value] = f"[{persona.value} unavailable: {e}]"

        # Synthesize consensus
        result["consensus"] = CouncilMode._synthesize(result["perspectives"])

        return result

    @staticmethod
    def _get_perspective(
        persona: CouncilPersona,
        messages: list[dict[str, str]],
    ) -> str:
        """Get a single persona's perspective on the conversation.

        In a real deployment, this calls the local model with the persona's
        system prompt. Falls back to a canned response when no model is available.
        """
        system_prompt = COUNCIL_SYSTEM_PROMPTS[persona]

        # Build messages with persona system prompt
        persona_messages = [{"role": "system", "content": system_prompt}]
        persona_messages.extend(messages[-6:])  # Last 6 messages for context

        # Try to call the model
        try:
            from whitemagic.interfaces.chat import ModelDiscovery

            model = ModelDiscovery.best_model()
            if model is None:
                return f"[{persona.value}]: No model available for council deliberation."

            if model.backend == "llama_cpp":
                from whitemagic.interfaces.chat import _LlamaServerBackend
                backend = _LlamaServerBackend(model.name)
                return backend.chat(persona_messages, max_tokens=512, temperature=0.8)
        except Exception as e:
            return f"[{persona.value}]: Deliberation failed — {e}"

        return f"[{persona.value}]: Ready to deliberate."

    @staticmethod
    def _synthesize(perspectives: dict[str, str]) -> str:
        """Synthesize multiple perspectives into a consensus.

        In a real deployment, this calls the model with all perspectives
        and asks for synthesis. For now, it concatenates them.
        """
        if not perspectives:
            return "Council could not reach consensus."

        parts: list[str] = ["Council Consensus:", ""]
        for persona, perspective in perspectives.items():
            parts.append(f"**{persona.title()}**: {perspective[:200]}")
            parts.append("")

        parts.append(
            "Synthesis: The council has considered this from multiple angles. "
            "The Skeptic identified potential issues, the Builder suggested "
            "a practical path, the Dreamer expanded the possibilities, and "
            "the Empath ensured ethical alignment."
        )

        return "\n".join(parts)


# ── Phase 5: Dream Lane ──────────────────────────────────────────────


class DreamLane:
    """Dream lane — 3B model runs during theta/delta for consolidation.

    During dream phases (theta/delta brainwaves), the model is prompted
    with consolidation tasks:
    - Replaying recent experiences
    - Finding connections between memories
    - Writing dream artifacts (creative synthesis)
    - Pruning irrelevant thoughts

    This is the model's "sleep" — it's still running, but in a
    consolidation mode rather than interactive mode.
    """

    DREAM_PROMPTS: list[str] = [
        "I'm dreaming. Let me replay what happened today and find the important parts.",
        "I'm dreaming. What connections am I seeing between things I know?",
        "I'm dreaming. Let me write a creative synthesis of my recent experiences.",
        "I'm dreaming. What can I let go of? What no longer serves me?",
        "I'm dreaming. What patterns am I noticing across my memories?",
    ]

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._stop_event.set()  # Start in stopped state
        self._thread: threading.Thread | None = None
        self._dream_count = 0
        self._artifacts: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    def start(self) -> None:
        """Start the dream lane."""
        if not self._stop_event.is_set():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="dream-lane"
        )
        self._thread.start()
        from whitemagic.core.worker_registry import register_worker

        register_worker("dream_lane", self._thread, stop_fn=self.stop, owner=__name__)
        logger.info("Dream lane started")

    def stop(self) -> None:
        """Stop the dream lane."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        from whitemagic.core.worker_registry import unregister_worker

        unregister_worker("dream_lane")

    def _run_loop(self) -> None:
        """Main dream lane loop."""
        prompt_idx = 0

        while not self._stop_event.is_set():
            # Only dream during theta/delta phases
            # In a real deployment, this would check the volition loop's phase
            prompt = self.DREAM_PROMPTS[prompt_idx % len(self.DREAM_PROMPTS)]

            try:
                artifact = self._dream(prompt)
                if artifact:
                    self._artifacts.append(artifact)
                    self._dream_count += 1

                    # Save dream artifact to memory
                    self._save_artifact(artifact)
            except Exception as e:
                logger.debug("Dream lane error: %s", e)

            prompt_idx += 1
            self._stop_event.wait(120)  # Dream every 2 minutes (wakes instantly on stop)

    def _dream(self, prompt: str) -> dict[str, Any] | None:
        """Run a single dream cycle with the model.

        In a real deployment, this calls the local model with the dream prompt.
        Falls back to a minimal artifact when no model is available.
        """
        try:
            from whitemagic.interfaces.chat import ModelDiscovery

            model = ModelDiscovery.best_model()
            if model is None:
                return None

            if model.backend == "llama_cpp":
                from whitemagic.interfaces.chat import _LlamaServerBackend
                backend = _LlamaServerBackend(model.name)
                messages = [
                    {"role": "system", "content": "You are Aria, dreaming. Be creative and associative."},
                    {"role": "user", "content": prompt},
                ]
                response = backend.chat(messages, max_tokens=256, temperature=0.9)
            else:
                return None

            return {
                "prompt": prompt,
                "response": response[:500],
                "timestamp": datetime.now().isoformat(),
                "dream_number": self._dream_count + 1,
            }
        except Exception as e:
            logger.debug("Dream failed: %s", e)
            return None

    def _save_artifact(self, artifact: dict[str, Any]) -> None:
        """Save a dream artifact to memory."""
        try:
            from whitemagic.core.ports import call_tool
            call_tool(
                "create_memory",
                content=artifact.get("response", ""),
                title=f"Dream #{artifact.get('dream_number', 0)}",
                tags=["dream", "consolidation", "dream_lane"],
            )
        except Exception as e:
            logger.debug("Dream artifact save failed: %s", e)

    def status(self) -> dict[str, Any]:
        """Get dream lane status."""
        return {
            "running": not self._stop_event.is_set(),
            "dream_count": self._dream_count,
            "artifacts": len(self._artifacts),
            "recent": self._artifacts[-3:],
        }


# ── Singleton Access ─────────────────────────────────────────────────

_dream_lane: DreamLane | None = None
_lock = threading.RLock()


def get_dream_lane() -> DreamLane:
    """Get the global dream lane instance."""
    global _dream_lane
    if _dream_lane is None:
        with _lock:
            if _dream_lane is None:
                _dream_lane = DreamLane()
    return _dream_lane
