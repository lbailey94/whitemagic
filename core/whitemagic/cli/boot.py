# ruff: noqa: BLE001
import logging
import os

logger = logging.getLogger(__name__)

# Import Rich for beautiful CLI output
try:
    from rich.console import Console
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None  # type: ignore[assignment]


def bootstrap_env_from_argv(argv: list[str]) -> None:
    """Bootstrap environment variables from CLI flags *before* importing Whitemagic
    modules that compute state paths at import time.

    This keeps `--state-root`/`--base-dir` and `--silent-init` effective even when
    running as an installed console script (module import happens before Click
    parses options).
    """
    def _extract_value(flag: str) -> str | None:
        for i, arg in enumerate(argv):
            if arg == flag and i + 1 < len(argv):
                return argv[i + 1]
            if arg.startswith(flag + "="):
                return arg.split("=", 1)[1]
        return None

    state_root = _extract_value("--state-root") or _extract_value("--base-dir")
    if state_root:
        # CLI flag should win for this process.
        os.environ["WM_STATE_ROOT"] = state_root

    db_path = _extract_value("--db-path")
    if db_path:
        # CLI flag should win for this process.
        os.environ["WM_DB_PATH"] = db_path

    if "--silent-init" in argv or "--json" in argv:
        os.environ["WM_SILENT_INIT"] = "1"


def register_all_commands(main_group, get_memory, status_command_ref, json_dumps_ref) -> None:
    """Registers all commands and optional extensions to the main group."""
    import click

    from whitemagic.cli.lazy_groups import LazyGroup

    # Optional flags

    def _warn_load(name: str, e: Exception) -> None:
        if HAS_RICH and console:
            console.print(f"[yellow]Warning: Failed to load {name}: {e}[/yellow]")
        else:
            click.echo(f"Warning: Failed to load {name}: {e}", err=True)

    # Core system commands extracted previously
    from whitemagic.cli.commands.diagnostics_commands import (
        register_diagnostics_commands,
    )
    register_diagnostics_commands(main_group)

    from whitemagic.cli.commands.core_commands import (
        explore_command,
        init_command,
        list_tools,
        rules_command,
        setup,
        start_session_cli,
        systemmap_command,
        tools,
    )
    for cmd in [explore_command, init_command, rules_command, systemmap_command,
                start_session_cli, list_tools, setup, tools]:
        main_group.add_command(cmd)

    from whitemagic.cli.commands.data_commands import (
        backup_command,
        galaxy_command,
        restore_command,
    )
    for cmd in [galaxy_command, backup_command, restore_command]:
        main_group.add_command(cmd)

    # Extracted command groups
    from whitemagic.cli.commands.gana_commands import gana_group
    main_group.add_command(gana_group)

    from whitemagic.cli.commands.dharma_commands import dharma_group
    main_group.add_command(dharma_group)

    from whitemagic.cli.commands.wisdom_commands import wisdom_group
    main_group.add_command(wisdom_group)

    from whitemagic.cli.commands.maintenance_commands import maintenance_group
    main_group.add_command(maintenance_group)

    from whitemagic.cli.commands.vault_commands import vault_group
    main_group.add_command(vault_group)

    from whitemagic.cli.commands.memory_commands import (
        consolidate,
        context,
        journey,
        memory_list,
        recall,
        remember,
        search,
        stats,
    )
    for cmd in [remember, recall, search, context, consolidate, stats, memory_list, journey]:
        main_group.add_command(cmd)

    from whitemagic.cli.commands.scratchpad_commands import scratchpad
    main_group.add_command(scratchpad)

    from whitemagic.cli.commands.session_matrix_commands import (
        register_session_matrix_commands,
    )
    register_session_matrix_commands(main_group, get_memory, status_command_ref, json_dumps_ref)

    # 1. Extensions
    try:
        from whitemagic.cli.cli_commands_gardens import gardens
        from whitemagic.cli.cli_commands_intelligence import intelligence
        from whitemagic.cli.cli_commands_symbolic import iching, wuxing
        for cmd in [gardens, intelligence, iching, wuxing]:
            main_group.add_command(cmd)
    except (ImportError, ModuleNotFoundError) as e:
        _warn_load("extensions", e)

    # 2. Reasoning
    try:
        from whitemagic.cli.cli_reasoning import reasoning
        main_group.add_command(reasoning, name="reason")
    except (ImportError, ModuleNotFoundError) as e:
        _warn_load("reasoning CLI", e)

    # 3. Inference
    try:
        from whitemagic.cli.infer_commands import infer
        main_group.add_command(infer)
    except (ImportError, ModuleNotFoundError):
        pass

    if "infer" not in main_group.commands:
        @main_group.group(name="infer")
        def infer_fallback_group():
            """Local inference commands (fallback)"""
        try:
            from whitemagic.cli.commands.local_inference_commands import (
                infer_local_query,
                infer_local_status,
            )
            if os.getenv("WHITEMAGIC_ENABLE_LOCAL_MODELS", "").strip().lower() in {"1", "true", "yes", "on"}:
                infer_fallback_group.add_command(infer_local_query)
                infer_fallback_group.add_command(infer_local_status)
        except ImportError:
            pass  # Optional local inference commands not available
        except Exception as e:
            logger.debug("Unexpected error loading local inference commands: %s", e, exc_info=True)
    else:
        try:
            if os.getenv("WHITEMAGIC_ENABLE_LOCAL_MODELS", "").strip().lower() in {"1", "true", "yes", "on"}:
                from whitemagic.cli.commands.local_inference_commands import (
                    infer_local_query,
                    infer_local_status,
                )
                main_group.commands["infer"].add_command(infer_local_query)
                main_group.commands["infer"].add_command(infer_local_status)
        except ImportError:
            pass  # Optional local inference commands not available
        except Exception as e:
            logger.debug("Unexpected error loading local inference commands: %s", e, exc_info=True)

    from whitemagic.cli.registry import register_optional

    # 4. Hardware
    register_optional(main_group, "hardware", "whitemagic.cli.hardware_commands", "hardware")

    # 5. Sangha
    register_optional(main_group, "sangha", "whitemagic.cli.cli_sangha", "sangha_cli", cli_name="sangha")

    # 6. Archaeology
    try:
        from whitemagic.cli.cli_archaeology import archaeology, windsurf
        main_group.add_command(archaeology)
        main_group.add_command(windsurf)
    except (ImportError, ModuleNotFoundError):
        pass

    # 7. Watcher
    register_optional(main_group, "watcher", "whitemagic.cli.cli_watcher", "watch")

    # 8. Autonomous execution
    register_optional(main_group, "autonomous", "whitemagic.cli.cli_autonomous_execution", "autonomous")

    # 9. Local model
    @main_group.group(cls=LazyGroup, name="local")
    def local_group():
        """Local ML inference commands."""
        def loader():
            """
            Perform the loader operation.
            """
            from whitemagic.cli.cli_local import local_cli
            return local_cli
        return loader()

    # 10. Cache
    register_optional(main_group, "cache", "whitemagic.cli.cli_cache", "cache_cli", cli_name="cache")

    # 11. Zodiac
    register_optional(main_group, "zodiac", "whitemagic.cli.cli_zodiac", "zodiac_cli", cli_name="zodiac")

    # 12. Scratchpad (cli_scratchpad)
    register_optional(main_group, "scratch", "whitemagic.cli.cli_scratchpad", "scratch")

    # 13. Infrastructure (Optimization phase)
    try:
        from whitemagic.cli.cli_commands_optimization import optimization_cli
        from whitemagic.cli.cli_commands_phase import phase_cli
        from whitemagic.cli.cli_commands_supervisor import supervisor_cli
        from whitemagic.cli.cli_commands_thought import thought_cli
        main_group.add_command(optimization_cli)
        main_group.add_command(thought_cli)
        main_group.add_command(supervisor_cli)
        main_group.add_command(phase_cli)
    except ImportError:
        pass

    # 14. PRAT
    register_optional(main_group, "prat", "whitemagic.cli.cli_prat", "prat", cli_name="prat")

    # 15. Hologram
    register_optional(main_group, "holo", "whitemagic.cli.holo_commands", "holo_cli", cli_name="holo")

    # 16. Init
    register_optional(main_group, "init", "whitemagic.cli.init_command", "init_command")

    # 16b. Dream Cycle
    register_optional(main_group, "dream", "whitemagic.cli.commands.dream_commands", "dream_group", cli_name="dream")

    # 17. Rust bridge
    @main_group.group(cls=LazyGroup, name="rust")
    def rust_group():
        """Rust bridge commands (requires whitemagic-rust)."""
        def loader():
            """
            Perform the loader operation.
            """
            from whitemagic.cli.cli_rust import register_rust_commands
            return register_rust_commands(main_group)
        return loader()

    # 18. Plugins
    try:
        from whitemagic.plugins import load_plugins, register_commands
        load_plugins()
        register_commands(main_group)
    except (ImportError, ModuleNotFoundError) as e:
        if not os.getenv("WM_SILENT_INIT"):
            _warn_load("plugins", e)

    # 19. Self-improvement
    register_optional(main_group, "self-improve", "whitemagic.cli.commands.self_improve_commands", "self_improve", cli_name="self-improve", warn_on_fail=True)

    # 20. Interactive commands (repl, stream, pipeline)
    try:
        from whitemagic.cli.commands.interactive_commands import register_interactive_commands
        register_interactive_commands(main_group)
    except (ImportError, ModuleNotFoundError):
        pass

    # 21. Discoverability commands (manifest, capabilities, tools search/schema)
    try:
        from whitemagic.cli.commands.discoverability_commands import register_discoverability_commands
        register_discoverability_commands(main_group)
    except (ImportError, ModuleNotFoundError):
        pass

    # 22. Cognitive workflow commands (think, reflect, dream, evolve, ground)
    try:
        from whitemagic.cli.commands.cognitive_commands import register_cognitive_commands
        register_cognitive_commands(main_group)
    except (ImportError, ModuleNotFoundError):
        pass
