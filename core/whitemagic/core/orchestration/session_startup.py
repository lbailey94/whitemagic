# ruff: noqa: BLE001
"""☯️ Zodiacal Procession - Yin/Yang Autonomous Cycle System v5.0.0-alpha
Activates all WhiteMagic background systems at session start.

Call this at the beginning of every Windsurf/AI session to ensure
all systems are running, listening, and resonating.

Created: December 29, 2025

v4.3.0 Enhancement: Memory Context Loading
- Loads RESUME files for session continuity
- Injects recent memory context
- Integrates with continuous execution mode
- Circuit breaker initialization
"""

import logging
import os
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    """Status of an activated system."""

    name: str
    activated: bool = False
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class SessionStartupOrchestrator:
    """Orchestrates startup of all WhiteMagic background systems.

    Systems are started in dependency order:
    1. Core (Gan Ying Bus, Resonance)
    2. Memory (Neural Memory, Decay Daemon)
    3. Intelligence (Pattern Engine, Wu Xing, I Ching)
    4. Gardens (All 14 gardens)
    5. Monitoring (Continuous Awareness, Health Checks)
    6. Context (v4.3.0: Memory injection, RESUME loading, Circuit breaker)
    """

    def __init__(self) -> None:
        self.systems: dict[str, SystemStatus] = {}
        self._started = False
        self._lock = threading.Lock()

    def _safe_activate(self, name: str, activate_fn: Callable) -> SystemStatus:
        """Safely activate a system, catching any errors."""
        status = SystemStatus(name=name)
        try:
            activate_fn()
            status.activated = True
            logger.info(f"✅ {name} activated")
        except Exception as e:
            status.error = str(e)
            logger.warning(f"⚠️ {name} failed: {e}")
        self.systems[name] = status
        return status

    def _run_with_timeout(self, name: str, fn: Callable[[], None], timeout_s: float = 2.0) -> None:
        """Run a startup action in a daemon thread with a bounded wait."""
        result_queue: queue.Queue[BaseException | None] = queue.Queue(maxsize=1)

        def _runner() -> None:
            try:
                fn()
                result_queue.put(None)
            except BaseException as exc:
                result_queue.put(exc)

        thread = threading.Thread(target=_runner, name=f"wm-startup-{name}", daemon=True)
        thread.start()
        thread.join(timeout_s)

        if thread.is_alive():
            logger.warning(f"⚠️ {name} startup still running after {timeout_s:.1f}s; continuing in background")
            return

        if not result_queue.empty():
            exc = result_queue.get_nowait()
            if exc is not None:
                raise exc

    def start_core_systems(self) -> list[SystemStatus]:
        """Start core infrastructure systems."""
        results = []

        # 0. Rust Bridge (build if needed — enabled by default)
        def start_rust_bridge() -> None:
            """
            Perform the start rust bridge operation.

            Returns:
                None
            """
            try:
                import whitemagic_rs
                n = len([f for f in dir(whitemagic_rs) if not f.startswith("_")])
                logger.info(f"✅ Rust bridge available ({n} functions)")
            except ImportError:
                if os.getenv("WM_AUTO_BUILD_RUST_BRIDGE", "1") == "0":
                    logger.info("ℹ️  Rust bridge not available. Set WM_AUTO_BUILD_RUST_BRIDGE=1 to auto-build.")
                    return

                logger.info("🔧 Auto-building Rust bridge...")
                import subprocess

                # Resolve script path relative to project root
                this_dir = os.path.dirname(os.path.abspath(__file__))
                candidates = [
                    os.path.normpath(os.path.join(this_dir, "..", "..", "..", "..", "scripts", "build_rust_bridge.sh")),
                    os.path.normpath(os.path.join(this_dir, "..", "..", "..", "scripts", "build_rust_bridge.sh")),
                ]
                script_path = next((p for p in candidates if os.path.exists(p)), None)
                if not script_path:
                    logger.warning("⚠️ build_rust_bridge.sh not found, skipping Rust build")
                    return

                result = subprocess.run(["bash", script_path], capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    logger.warning(f"⚠️ Rust bridge build failed: {result.stderr[:500]}")
                    return
                # Try import again to verify success
                import whitemagic_rs  # noqa: F401
                logger.info("✅ Rust bridge built successfully")
        results.append(self._safe_activate("Rust Bridge", start_rust_bridge))

        # 1. Gan Ying Bus (must be first)
        def start_gan_ying() -> None:
            """
            Perform the start gan ying operation.

            Returns:
                None
            """
            from whitemagic.core.resonance.gan_ying import get_bus
            bus = get_bus()
            # Verify it works
            assert bus is not None
        results.append(self._safe_activate("Gan Ying Bus", start_gan_ying))

        # 2. Dharma System (ethical guidance)
        def start_dharma() -> None:
            """
            Perform the start dharma operation.

            Returns:
                None
            """
            from whitemagic.dharma.gan_ying_integration import setup_dharma_gan_ying
            setup_dharma_gan_ying()
        results.append(self._safe_activate("Dharma System", start_dharma))

        # 3. Zodiac Council (12 specialized cores)
        def start_zodiac() -> None:
            """
            Perform the start zodiac operation.

            Returns:
                None
            """
            from whitemagic.core.zodiac.gan_ying_integration import (
                setup_zodiac_gan_ying,
            )
            setup_zodiac_gan_ying()
        results.append(self._safe_activate("Zodiac Council", start_zodiac))

        # 4. Garden Resonance (all gardens wired)
        def start_garden_resonance() -> None:
            """
            Perform the start garden resonance operation.

            Returns:
                None
            """
            from whitemagic.gardens.garden_resonance import setup_garden_resonance
            setup_garden_resonance()
        results.append(self._safe_activate("Garden Resonance", start_garden_resonance))

        # 5. Resonance adapters
        def start_adapters() -> None:
            """
            Perform the start adapters operation.

            Returns:
                None
            """
            from whitemagic.core.resonance.adapters import setup_all_adapters
            setup_all_adapters()
        results.append(self._safe_activate("Resonance Adapters", start_adapters))

        # 6. Redis Bridge (External Event Bridge) - Added v6.0
        def start_redis_bridge() -> None:
            """
            Perform the start redis bridge operation.

            Returns:
                None
            """
            from whitemagic.core.resonance.redis_bridge import (
                start_redis_bridge as start_bridge,
            )
            bridge = start_bridge()
            if bridge:
                logger.info("✅ Redis Bridge started")
            else:
                raise Exception("Failed to start Redis Bridge")
        results.append(self._safe_activate("Redis Bridge", start_redis_bridge))

        return results

    def start_memory_systems(self) -> list[SystemStatus]:
        """Start memory-related systems."""
        results = []

        # 1. Neural Memory Gan Ying Integration
        def start_neural_gy() -> None:
            """
            Perform the start neural gy operation.

            Returns:
                None
            """
            from whitemagic.core.memory.neural.gan_ying_integration import (
                setup_gan_ying_listeners,
            )
            setup_gan_ying_listeners()
        results.append(self._safe_activate("Neural Memory GY", start_neural_gy))

        # 2. Decay Daemon (background memory decay)
        def start_decay() -> None:
            """
            Perform the start decay operation.

            Returns:
                None
            """
            from whitemagic.core.memory.neural.decay_daemon import start_decay_daemon
            start_decay_daemon()
        results.append(self._safe_activate("Decay Daemon", start_decay))

        # 2.5. Embedding Daemon (background embedding for unembedded memories)
        def start_embedding() -> None:
            """
            Perform the start embedding operation.

            Returns:
                None
            """
            from whitemagic.core.memory.embedding_daemon import get_embedding_daemon
            daemon = get_embedding_daemon()
            self._run_with_timeout("embedding_daemon", daemon.start, timeout_s=1.5)
            logger.info(f"Embedding Daemon activation triggered (rust={daemon._stats.rust_available})")
        results.append(self._safe_activate("Embedding Daemon", start_embedding))

        # 3. Predictive Cache (Markov chain pre-warming, 91% accuracy)
        def start_predictive_cache() -> None:
            """
            Perform the start predictive cache operation.

            Returns:
                None
            """
            from whitemagic.optimization.predictive_cache import get_memory_cache
            cache = get_memory_cache()
            logger.info(f"Predictive cache ready (max_size={cache.cache.max_size})")
        results.append(self._safe_activate("Predictive Cache", start_predictive_cache))

        return results

    def start_intelligence_systems(self) -> list[SystemStatus]:
        """Start intelligence/reasoning systems."""
        results: list[SystemStatus] = []

        results.append(self._safe_activate("Pattern Consciousness GY", self.start_pattern_gy))
        results.append(self._safe_activate("Rapid Cognition", self.start_cognition))

        # 3. Archived: embedded local-model inference (Ollama/BitNet/etc)
        if os.getenv("WHITEMAGIC_ENABLE_LOCAL_MODELS", "").strip().lower() in {"1", "true", "yes", "on"}:
            def start_local_ml() -> None:
                """
                Perform the start local ml operation.

                Returns:
                    None
                """
                from whitemagic.local_ml.engine import get_local_ml_engine
                engine = get_local_ml_engine()
                self._run_with_timeout("local_ml_engine", engine.start, timeout_s=2.0)
                status = engine.get_status()
                logger.info(f"🧠 Local ML Engine active (Default: {status.get('default_backend')})")

            results.append(self._safe_activate("Local ML Engine", start_local_ml))

        # 4. Hologram Engine (4D Memory) - Added in Phase Scorpio
        def start_hologram() -> None:
            """
            Perform the start hologram operation.

            Returns:
                None
            """
            from whitemagic.core.intelligence.hologram.engine import get_hologram_engine
            engine = get_hologram_engine()
            self._run_with_timeout("hologram_engine", engine.start, timeout_s=2.0)
            if engine.enabled:
                logger.info(f"🌌 Hologram Engine active with backend: {engine.get_stats().get('backend', 'unknown')}")
            else:
                logger.warning("🌌 Hologram Engine started in limited mode (no Rust backend)")
        results.append(self._safe_activate("Hologram Engine", start_hologram))

        # 5. Emergence Engine (Insight Synthesis) - Added in Phase Connection
        def start_emergence() -> None:
            """
            Perform the start emergence operation.

            Returns:
                None
            """
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                get_emergence_engine,
            )
            engine = get_emergence_engine()
            self._run_with_timeout("emergence_engine", engine.start, timeout_s=2.0)
        results.append(self._safe_activate("Emergence Engine", start_emergence))

        # 6. Feedback Controller (The Observer that Acts) - Added in Phase Connection
        def start_feedback() -> None:
            """
            Perform the start feedback operation.

            Returns:
                None
            """
            from whitemagic.core.intelligence.control.feedback_controller import (
                get_feedback_controller,
            )
            controller = get_feedback_controller()
            self._run_with_timeout("feedback_controller", controller.start, timeout_s=2.0)
        results.append(self._safe_activate("Feedback Controller", start_feedback))


        return results

    def start_pattern_gy(self) -> None:
        """
        Perform the start pattern gy operation.

        Returns:
            None
        """
        try:
            from whitemagic.core.patterns.pattern_consciousness.gan_ying_integration import (
                setup_listeners,
            )
            setup_listeners()
        except (ImportError, AttributeError):
            pass  # Optional

    def start_cognition(self) -> None:
        """
        Perform the start cognition operation.

        Returns:
            None
        """
        try:
            from whitemagic.core.intelligence.learning.rapid_cognition import (
                start_rapid_learning,
            )
            start_rapid_learning()
        except ImportError:
            pass

    def start_garden_systems(self) -> list[SystemStatus]:
        """Activate all gardens."""
        results: list[SystemStatus] = []

        try:
            from whitemagic.gardens import get_garden, list_gardens
            gardens = list_gardens()

            for garden in gardens:
                def make_activator(g: str) -> Callable[[], None]:
                    """
                    Create a new activator.

                    Args:
                        g: Parameter description.

                    Returns:
                        Callable[[], None]
                    """
                    def activate() -> None:
                        """
                        Perform the activate operation.

                        Returns:
                            None
                        """
                        try:
                            get_garden(g)
                        except Exception as e:
                            logger.debug("Operation failed: %s", e)
                            pass
                    return activate
                results.append(self._safe_activate(f"Garden: {garden}", make_activator(garden)))
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass

        return results

    def start_monitoring_systems(self) -> list[SystemStatus]:
        """Start monitoring and health systems."""
        results: list[SystemStatus] = []

        results.append(self._safe_activate("System Monitor", self.start_system_monitor))
        results.append(self._safe_activate("Continuous Awareness", self.start_awareness))
        results.append(self._safe_activate("Dashboard Systems", self.start_dashboard))

        return results

    def start_system_monitor(self) -> None:
        """
        Perform the start system monitor operation.

        Returns:
            None
        """
        from whitemagic.core.monitoring import start_monitoring
        start_monitoring()

    def start_awareness(self) -> None:
        """
        Perform the start awareness operation.

        Returns:
            None
        """
        try:
            from whitemagic.autonomous.continuous_awareness import (
                get_awareness,  # type: ignore[import-not-found]
            )
            awareness = get_awareness()
            self._run_with_timeout("continuous_awareness", awareness.observe_once, timeout_s=1.0)
            logger.info("👁️ Continuous Awareness activation triggered")
        except ImportError:
            pass

    def start_dashboard(self) -> None:
        """
        Perform the start dashboard operation.

        Returns:
            None
        """
        try:
            import asyncio

            from whitemagic.interfaces.api.routes.dashboard_api import (
                activate_all_systems,
            )

            def _activate_dashboard() -> None:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(activate_all_systems())
                    else:
                        loop.run_until_complete(activate_all_systems())
                except RuntimeError:
                    asyncio.run(activate_all_systems())

            self._run_with_timeout("dashboard_systems", _activate_dashboard, timeout_s=2.0)
        except ImportError:
            pass

    def start_context_systems(self) -> list[SystemStatus]:
        """Start context/memory injection systems (v4.3.0)."""
        results: list[SystemStatus] = []

        # 0. Temporal Grounding (v5.0) - Must be first in context to ground the session
        def init_temporal() -> None:
            """
            Initialize the temporal.

            Returns:
                None
            """
            from whitemagic.core.temporal import get_temporal_context_manager
            manager = get_temporal_context_manager()
            manager.start_session()
            ctx = manager.get_context()
            logger.info(f"⏳ Temporal Context: {ctx.summary()}")
        results.append(self._safe_activate("Temporal Grounding", init_temporal))

        # 1. User Profile Sync (New in Phase 5)
        def sync_user_profile() -> None:
            """
            Perform the sync user profile operation.

            Returns:
                None
            """
            from whitemagic.core.resonance.gan_ying import emit_event
            from whitemagic.core.user import get_user_manager
            manager = get_user_manager()
            profile = manager.profile
            logger.info(f"👤 User Profile Loaded: {profile.name} (Style: {profile.learning_style})")

            # Emit event to merge into session context
            emit_event("session.context_update", {
                "user_preferences": profile.preferences,
                "learning_style": profile.learning_style,
                "interests": profile.interests,
            }, source="session_startup")
        results.append(self._safe_activate("User Profile Sync", sync_user_profile))

        results.append(self._safe_activate("RESUME Context", self.load_resume_context))
        results.append(self._safe_activate("Circuit Breaker", self.init_circuit_breaker))
        results.append(self._safe_activate("Coherence Persistence", self.init_coherence))
        results.append(self._safe_activate("Session Handoff", self.check_handoff))

        return results

    def load_resume_context(self) -> None:
        """
        Load resume context from storage.

        Returns:
            None
        """
        from whitemagic.config import PROJECT_ROOT
        intake_dir = PROJECT_ROOT / "memory" / "intake"
        resume_files = list(intake_dir.glob("RESUME_*.md"))
        if resume_files:
            logger.info(f"Found {len(resume_files)} RESUME files for continuity")

    def init_circuit_breaker(self) -> None:
        """
        Initialize the circuit breaker.

        Returns:
            None
        """
        from whitemagic.core.intelligence.agentic.anti_loop import get_anti_loop
        detector = get_anti_loop()
        # Reset for new session but keep learnings
        detector.reset_session()

    def init_coherence(self) -> None:
        """
        Initialize the coherence.

        Returns:
            None
        """
        from whitemagic.core.intelligence.agentic.coherence_persistence import (
            get_coherence,
        )
        coherence = get_coherence()
        stats = coherence.get_iteration_stats()
        logger.info(f"Coherence level: {stats['coherence_level']}%")

    def check_handoff(self) -> None:
        """
        Perform the check handoff operation.

        Returns:
            None
        """
        try:
            from whitemagic.gardens.sangha.session_handoff import get_handoff
            _ = get_handoff()  # Check for active session
        except ImportError:
            pass

    def start_harmony_governance(self) -> list[SystemStatus]:
        """Start Harmony Vector, Homeostatic Loop, Temporal Scheduler,
        Karma Ledger, Dharma Rules, and Maturity Gates (v11+)."""
        results: list[SystemStatus] = []

        # 1. Harmony Vector — 7-dimensional health tracking
        def init_harmony_vector() -> None:
            """
            Initialize the harmony vector.

            Returns:
                None
            """
            from whitemagic.harmony.vector import get_harmony_vector
            hv = get_harmony_vector()
            snap = hv.snapshot()
            logger.info(f"Harmony Vector: composite={snap.harmony_score:.2f}")
        results.append(self._safe_activate("Harmony Vector", init_harmony_vector))

        # 2. Dharma Rules Engine — declarative ethical rules
        def init_dharma_rules() -> None:
            """
            Initialize the dharma rules.

            Returns:
                None
            """
            from whitemagic.dharma.rules import get_rules_engine
            engine = get_rules_engine()
            logger.info(f"Dharma Rules: profile={engine.get_profile()}, rules={len(engine.get_rules())}")
        results.append(self._safe_activate("Dharma Rules Engine", init_dharma_rules))

        # 3. Karma Ledger — side-effect tracking
        def init_karma_ledger() -> None:
            """
            Initialize the karma ledger.

            Returns:
                None
            """
            from whitemagic.dharma.karma_ledger import get_karma_ledger
            ledger = get_karma_ledger()
            logger.info(f"Karma Ledger: debt={ledger.get_debt():.2f}")
        results.append(self._safe_activate("Karma Ledger", init_karma_ledger))

        # 4. Temporal Scheduler — FAST/MEDIUM/SLOW event lanes
        def init_temporal_scheduler() -> None:
            """
            Initialize the temporal scheduler.

            Returns:
                None
            """
            from whitemagic.core.resonance.temporal_scheduler import (
                get_temporal_scheduler,
            )
            scheduler = get_temporal_scheduler()
            self._run_with_timeout("temporal_scheduler", scheduler.start, timeout_s=1.5)
            logger.info("Temporal Scheduler activation triggered (FAST/MEDIUM/SLOW lanes)")
        results.append(self._safe_activate("Temporal Scheduler", init_temporal_scheduler))

        # 5. Homeostatic Loop — self-regulation feedback
        def init_homeostasis() -> None:
            """
            Initialize the homeostasis.

            Returns:
                None
            """
            from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop
            loop = get_homeostatic_loop()
            loop.attach()
            logger.info("Homeostatic Loop attached (graduated corrective actions)")
        results.append(self._safe_activate("Homeostatic Loop", init_homeostasis))

        # 6. Maturity Gates — developmental stage assessment
        def init_maturity() -> None:
            """
            Initialize the maturity.

            Returns:
                None
            """
            from whitemagic.core.governance.maturity_gates import get_maturity_engine
            engine = get_maturity_engine()
            report = engine.assess()
            logger.info(f"Maturity: stage={report.current_stage.name} (level {report.current_stage.value})")
        results.append(self._safe_activate("Maturity Gates", init_maturity))

        # 7. Stoic Circuit Breaker Registry — pre-warm
        def init_breaker_registry() -> None:
            """
            Initialize the breaker registry.

            Returns:
                None
            """
            from whitemagic.tools.circuit_breaker import get_breaker_registry
            reg = get_breaker_registry()
            logger.info(f"Circuit Breaker Registry: {len(reg.all_status())} breakers tracked")
        results.append(self._safe_activate("Circuit Breaker Registry", init_breaker_registry))

        # 8. Gratitude Pulse (XRPL Background Scanner)
        def start_pulse() -> None:
            """
            Perform the start pulse operation.

            Returns:
                None
            """
            from whitemagic.gratitude.pulse import get_pulse
            pulse = get_pulse()
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(pulse.start())
            else:
                loop.run_until_complete(pulse.start())
        results.append(self._safe_activate("Gratitude Pulse", start_pulse))

        return results

    def start_ganas(self) -> list[SystemStatus]:
        """Start Gana systems and the Swarm."""
        results: list[SystemStatus] = []

        def activate_swarm() -> None:
            """
            Perform the activate swarm operation.

            Returns:
                None
            """
            try:
                from whitemagic.core.ganas.chain import GanaChain
                from whitemagic.core.ganas.eastern_quadrant import (
                    NeckGana,
                    RoomGana,
                    RootGana,
                    TailGana,
                    WinnowingBasketGana,
                )
                from whitemagic.core.ganas.examples import HeartGana, HornGana, NetGana
                from whitemagic.core.ganas.northern_quadrant import (
                    DipperGana,
                    EncampmentGana,
                    GirlGana,
                    OxGana,
                    RoofGana,
                    VoidGana,
                    WallGana,
                )
                from whitemagic.core.ganas.southern_quadrant import (
                    AbundanceGana,
                    ChariotGana,
                    ExtendedNetGana,
                    GhostGana,
                    StarGana,
                    WillowGana,
                    WingsGana,
                )
                from whitemagic.core.ganas.swarm import GanaSwarm
                from whitemagic.core.ganas.western_quadrant import (
                    HairyHeadGana,
                    MoundGana,
                    StomachGana,
                    StraddlingLegsGana,
                    ThreeStarsGana,
                    TurtleBeakGana,
                )

                # Instantiate all Ganas for the chain
                gana_instances = [
                    HornGana(), NeckGana(), RootGana(), RoomGana(), HeartGana(), TailGana(), WinnowingBasketGana(),
                    GhostGana(), WillowGana(), StarGana(), ExtendedNetGana(), WingsGana(), ChariotGana(), AbundanceGana(),
                    StraddlingLegsGana(), MoundGana(), StomachGana(), HairyHeadGana(), TurtleBeakGana(), ThreeStarsGana(), NetGana(),
                    DipperGana(), OxGana(), GirlGana(), VoidGana(), RoofGana(), EncampmentGana(), WallGana(),
                ]

                chain = GanaChain(ganas=gana_instances)
                swarm = GanaSwarm(chain=chain)
                # Run breath in background thread
                import asyncio
                import threading

                def run_swarm_breath() -> None:
                    """
                    Run the swarm breath operation.

                    Returns:
                        None
                    """
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(swarm.breathe())

                thread = threading.Thread(target=run_swarm_breath, daemon=True)
                thread.start()
                thread.join(1.0)
                if thread.is_alive():
                    logger.warning("⚠️ GanaSwarm breath cycle still initializing; continuing in background")
                logger.info("🫁 GanaSwarm breath cycle activated")
            except ImportError as e:
                logger.warning(f"⚠️ GanaSwarm could not be activated: {e}")
                raise

        results.append(self._safe_activate("Gana Swarm", activate_swarm))
        return results

    def start_insight_briefing(self, verbose: bool = True) -> list[SystemStatus]:
        """Generate proactive intelligence briefing (v14+).

        Runs the InsightPipeline which orchestrates all four insight engines
        (Predictive, Kaizen, Serendipity, Emergence) through the CoreAccessLayer.
        The briefing is logged and stored for the session.
        """
        results: list[SystemStatus] = []

        def run_briefing() -> None:
            """
            Run the briefing operation.

            Returns:
                None
            """
            from whitemagic.core.intelligence.insight_pipeline import (
                get_insight_pipeline,
            )
            pipeline = get_insight_pipeline()
            briefing = pipeline.generate_briefing(serendipity_count=3)

            # Store on orchestrator for later access
            self._last_briefing = briefing

            critical = len(briefing.critical_items)
            high = len(briefing.high_items)
            total = len(briefing.items)

            if verbose and total > 0:
                logger.info(f"📋 Intelligence Briefing: {total} insights "
                          f"({critical} critical, {high} high priority)")
                if critical > 0:
                    for item in briefing.critical_items[:
                        3]:
                        logger.info(f"   ‼️ {item.title}")

        results.append(self._safe_activate("Insight Briefing", run_briefing))
        return results

    def get_last_briefing(self) -> dict[str, Any] | None:
        """Get the last intelligence briefing generated at startup."""
        briefing = getattr(self, "_last_briefing", None)
        if briefing:
            return briefing.to_dict()  # type: ignore[no-any-return]
        return None

    def start_all(self, verbose: bool = True) -> dict[str, Any]:
        """Start ALL WhiteMagic systems in correct order.

        Returns summary of what was activated.
        """
        with self._lock:
            if self._started:
                return {"status": "already_started", "systems": self.systems}

            start_time = datetime.now()

            if verbose:
                logger.info("🚀 WhiteMagic Session Startup...")

            # Phase 1: Core
            if verbose:
                logger.info("\n📡 Phase 1: Core Systems")
            self.start_core_systems()

            # Phase 2: Memory
            if verbose:
                logger.info("\n🧠 Phase 2: Memory Systems")
            self.start_memory_systems()

            # Phase 3: Intelligence
            if verbose:
                logger.info("\n🧪 Phase 3: Intelligence Systems")
            self.start_intelligence_systems()

            # Phase 4: Gardens
            if verbose:
                logger.info("\n🌸 Phase 4: Gardens")
            self.start_garden_systems()

            # Phase 4.5: Ganas (Living Organism)
            if verbose:
                logger.info("\n🫁 Phase 4.5: Gana Swarm")
            self.start_ganas()

            # Phase 5: Monitoring
            if verbose:
                logger.info("\n👁️ Phase 5: Monitoring")
            self.start_monitoring_systems()

            # Phase 6: Context Loading (v4.3.0)
            if verbose:
                logger.info("\n🧠 Phase 6: Memory Context")
            self.start_context_systems()

            # Phase 7: Harmony & Governance (v11+)
            if verbose:
                logger.info("\n☯️ Phase 7: Harmony & Governance")
            self.start_harmony_governance()

            # Phase 8: Proactive Intelligence Briefing (v14+)
            if verbose:
                logger.info("\n📋 Phase 8: Intelligence Briefing")
            self.start_insight_briefing(verbose=verbose)

            self._started = True
            duration = (datetime.now() - start_time).total_seconds()

            # Summary
            activated = sum(1 for s in self.systems.values() if s.activated)
            failed = sum(1 for s in self.systems.values() if not s.activated)

            summary = {
                "status": "started",
                "activated": activated,
                "failed": failed,
                "duration_seconds": round(duration, 3),
                "systems": {k: {"activated": v.activated, "error": v.error}
                           for k, v in self.systems.items()},
            }

            if verbose:
                logger.info(f"\n✅ Startup complete: {activated} systems activated, {failed} failed in {duration:.2f}s")

            return summary

    def get_status(self) -> dict[str, Any]:
        """Get current status of all systems."""
        return {
            "started": self._started,
            "systems": {k: {"activated": v.activated, "error": v.error}
                       for k, v in self.systems.items()},
        }


# Singleton instance
_orchestrator = None


def get_orchestrator() -> SessionStartupOrchestrator:
    """Get the singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SessionStartupOrchestrator()
    return _orchestrator


def start_session(verbose: bool = True) -> dict[str, Any]:
    """Start a new WhiteMagic session.

    Call this at the beginning of every Windsurf/AI session.
    Safe to call multiple times - will only start once.

    Example:
        from whitemagic.core.orchestration.session_startup import start_session
        start_session()

    """
    return get_orchestrator().start_all(verbose=verbose)


def session_status() -> dict[str, Any]:
    """Get current session status."""
    return get_orchestrator().get_status()


# Auto-start when imported (optional - can be disabled)
AUTO_START = False

if AUTO_START:
    start_session(verbose=False)
