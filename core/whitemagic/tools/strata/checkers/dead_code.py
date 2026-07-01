import ast
import os
import time
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_dead_code(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Dead code detection with awareness of methods, dynamic dispatch, and public API."""
    all_functions: dict[str, tuple[Path, int]] = {}
    all_methods: dict[
        str, list[tuple[str, Path, int]]
    ] = {}  # class_name -> [(method_name, file, line)]
    all_calls: set = set()
    dynamic_names: set = set()  # names referenced in dicts/lists (dynamic dispatch)
    exports: set = set()  # names in __all__
    # Track all method locations to avoid double-counting them as standalone functions
    method_locations: set = set()  # (file, line, name)

    def _ordered_walk(node: ast.AST):
        """Depth-first walk that guarantees parent before children."""
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            for child in reversed(list(ast.iter_child_nodes(n))):
                stack.append(child)

    _DEAD_CODE_TIME_BUDGET = float(os.environ.get("STRATA_DEAD_CODE_BUDGET", "15"))
    _DEAD_CODE_MAX_FILE_SIZE = 100_000  # Skip files > 100KB
    _start_time = time.monotonic()

    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        # Time budget — stop if we've spent too long
        if time.monotonic() - _start_time > _DEAD_CODE_TIME_BUDGET:
            break
        # Skip very large files (slow AST parse + walk)
        try:
            if py_file.stat().st_size > _DEAD_CODE_MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        # Single ordered pass: parents before children
        for node in _ordered_walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    exports.add(elt.value)
                # Detect dynamic dispatch: dict values that are Name references
                if isinstance(node.value, ast.Dict):
                    for v in node.value.values:
                        if isinstance(v, ast.Name):
                            dynamic_names.add(v.id)
                        # Also detect Name references inside Call args (e.g., Tool(..., func=tool_name))
                        elif isinstance(v, ast.Call):
                            for arg in v.args:
                                if isinstance(arg, ast.Name):
                                    dynamic_names.add(arg.id)
                            for kw in v.keywords:
                                if isinstance(kw.value, ast.Name):
                                    dynamic_names.add(kw.value.id)
                # Also detect list/dict comprehensions and lists of Name references
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Name):
                            dynamic_names.add(elt.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.value, ast.Dict):
                    for v in node.value.values:
                        if isinstance(v, ast.Name):
                            dynamic_names.add(v.id)
                        elif isinstance(v, ast.Call):
                            for arg in v.args:
                                if isinstance(arg, ast.Name):
                                    dynamic_names.add(arg.id)
                            for kw in v.keywords:
                                if isinstance(kw.value, ast.Name):
                                    dynamic_names.add(kw.value.id)
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Name):
                            dynamic_names.add(elt.id)
            elif isinstance(node, ast.ClassDef):
                # Register methods on this class
                for child in ast.iter_child_nodes(node):
                    if isinstance(
                        child, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not child.name.startswith("_"):
                        # Skip methods with framework decorators (Pydantic validators, etc.)
                        has_framework_decorator = False
                        for decorator in child.decorator_list:
                            if isinstance(decorator, ast.Name):
                                if decorator.id in {
                                    "field_validator",
                                    "model_validator",
                                    "classmethod",
                                    "staticmethod",
                                    "property",
                                }:
                                    has_framework_decorator = True
                            elif isinstance(decorator, ast.Call):
                                if isinstance(decorator.func, ast.Name):
                                    if decorator.func.id in {
                                        "field_validator",
                                        "model_validator",
                                    }:
                                        has_framework_decorator = True
                        if has_framework_decorator:
                            continue
                        method_locations.add((py_file, child.lineno, child.name))
                        all_methods.setdefault(node.name, []).append(
                            (child.name, py_file, child.lineno)
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    # Skip methods (they were already recorded in method_locations)
                    if (py_file, node.lineno, node.name) in method_locations:
                        continue
                    # Track decorators: decorators are calls, and the decorated function
                    # is passed to them (dynamic dispatch)
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            all_calls.add(decorator.id)
                            dynamic_names.add(node.name)
                        elif isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name):
                                all_calls.add(decorator.func.id)
                                dynamic_names.add(node.name)
                            elif isinstance(decorator.func, ast.Attribute):
                                all_calls.add(decorator.func.attr)
                                dynamic_names.add(node.name)
                        elif isinstance(decorator, ast.Attribute):
                            all_calls.add(decorator.attr)
                            dynamic_names.add(node.name)
                    # Skip functions with common framework decorators (FastAPI, Flask, Click, etc.)
                    has_framework_decorator = False
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                dec_name = decorator.func.attr
                                if dec_name in {
                                    "get",
                                    "post",
                                    "put",
                                    "delete",
                                    "patch",
                                    "route",
                                    "endpoint",
                                    "exception_handler",
                                    "on_event",
                                    "before_request",
                                    "after_request",
                                }:
                                    has_framework_decorator = True
                            elif isinstance(decorator.func, ast.Name):
                                if decorator.func.id in {
                                    "route",
                                    "app",
                                    "bp",
                                    "contextmanager",
                                    "asynccontextmanager",
                                }:
                                    has_framework_decorator = True
                        elif isinstance(decorator, ast.Attribute):
                            if decorator.attr in {
                                "get",
                                "post",
                                "put",
                                "delete",
                                "patch",
                                "route",
                            }:
                                has_framework_decorator = True
                        elif isinstance(decorator, ast.Name):
                            if decorator.id in {
                                "contextmanager",
                                "asynccontextmanager",
                                "staticmethod",
                                "classmethod",
                                "property",
                                "field_validator",
                                "model_validator",
                            }:
                                has_framework_decorator = True
                    if has_framework_decorator:
                        continue
                    all_functions[node.name] = (py_file, node.lineno)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    all_calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    all_calls.add(node.func.attr)
                    # Detect GTK / GObject signal callbacks: obj.connect("clicked", callback)
                    if node.func.attr == "connect" and len(node.args) >= 2:
                        # First arg is signal name (string), second+ are callbacks
                        if isinstance(node.args[0], ast.Constant) and isinstance(
                            node.args[0].value, str
                        ):
                            for arg in node.args[1:]:
                                if isinstance(arg, ast.Name):
                                    dynamic_names.add(arg.id)
                                elif isinstance(arg, ast.Attribute):
                                    # self.on_mode_clicked -> on_mode_clicked
                                    if (
                                        isinstance(arg.value, ast.Name)
                                        and arg.value.id == "self"
                                    ):
                                        dynamic_names.add(arg.attr)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.asname:
                        all_calls.add(alias.asname)
                        all_calls.add(alias.name)

    # Directories where standalone functions are called via dispatch table (string-based lookup)
    _DISPATCH_DIRS = (
        "handlers/",
        "bridge/",
        "orchestration/",
        "fusions",
        "acceleration/",
        "middleware",
        "registry",
        "edge/",
    )

    for func_name, (file_path, line_num) in all_functions.items():
        if func_name in dynamic_names or func_name in exports:
            continue
        # Skip functions in dispatch table directories (called via string-based lookup)
        file_str = str(file_path)
        if any(d in file_str for d in _DISPATCH_DIRS):
            continue
        if func_name not in all_calls and func_name not in {
            "main",
            "run",
            "app",
            "index",
            "handler",
            "setup",
            "teardown",
            "create_app",
            "get_app",
            "init",
            "initialize",
            "configure",
            "register",
            "activate",
            "deactivate",
        }:
            # Skip common callback/hook/listener naming patterns (dynamically dispatched)
            if any(
                func_name.endswith(suffix)
                for suffix in (
                    "_hook",
                    "_callback",
                    "_listener",
                    "_handler",
                    "_observer",
                    "_filter",
                )
            ):
                continue
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="dead_code",
                    file=str(file_path.relative_to(project_path)),
                    line=line_num,
                    message=f"Function '{func_name}' may be unused (not called or exported).",
                    suggestion="If public API, add to __all__. If dynamically dispatched, it may be a false positive.",
                )
            )

    for class_name, methods in all_methods.items():
        for method_name, file_path, line_num in methods:
            # Skip if method is called anywhere or used dynamically (e.g., GTK signals)
            if method_name in all_calls or method_name in dynamic_names:
                continue
            # Skip common magic/public methods and methods frequently called
            # via dynamic dispatch in WhiteMagic (gardens, agents, parallel, war_room)
            _COMMON_DYNAMIC_METHODS = {
                # Standard public API
                "to_dict",
                "from_dict",
                "save",
                "load",
                "add",
                "delete",
                "get",
                "search",
                "list",
                "count",
                "store",
                "clear_cache",
                # Garden lifecycle (called via garden registry dispatch)
                "feel_",
                "on_",
                "experience_",
                "enter_",
                "begin_",
                "start_",
                "deepen_",
                "gather_",
                "encourage",
                "practice_",
                "consult_",
                "decompose_",
                "route_",
                "complete_",
                "register_",
                "cast_",
                "resolve_",
                "resume_",
                "checkpoint_",
                "take_",
                "create_",
                "configure_",
                "get_",
                "set_",
                "update_",
                "record_",
                "track_",
                "start_",
                "end_",
                "mark_",
                "army_",
                "save_",
                # Agent/swarm methods (called via war_room/swarm dispatch)
                "reconnaissance",
                "monitor_",
                "verify_",
                "status_report",
                "plan_",
                "merge_",
                "extract_",
                "scout_",
                "run_",
                "skip",
                "progress_",
                "recommend_",
                "get_pool",
                "run_io",
                "run_cpu",
                "run_api",
                "run_db",
                "read_",
                "execute_",
                "is_allowed",
                "assess_",
                "request_",
                "resolve_",
                "sanitize_",
                "describe",
                "should_route",
                "register_tool",
                "pack_",
                "observe_",
                "get_self_report",
                "clear_history",
                "suggest_",
                "get_sop",
                # Parallel/threading (called via thread pool dispatch)
                "add_task",
                "get_task",
                "get_results",
                "cancel_task",
                "add_stage",
                "read_batch",
                "run_fast",
                "time_callable",
                "get_all_rules",
                "get_metadata",
                "get_model_info",
                "add_candidate",
                "should_forget",
            }
            if method_name in _COMMON_DYNAMIC_METHODS or any(
                method_name.startswith(prefix)
                for prefix in (
                    "feel_",
                    "on_",
                    "get_",
                    "set_",
                    "start_",
                    "end_",
                    "mark_",
                    "record_",
                    "track_",
                    "update_",
                    "configure_",
                )
            ):
                continue
            # Skip methods on classes whose names match WhiteMagic dispatch patterns
            # These classes are registered in dispatch tables and called via string-based lookup
            _DISPATCH_CLASS_PATTERNS = (
                "Garden",
                "Agent",
                "Core",
                "Handler",
                "Provider",
                "Manager",
                "Engine",
                "Tracker",
                "Monitor",
                "Supervisor",
                "Executor",
                "Pipeline",
                "Scheduler",
                "Bandit",
                "Portal",
                "Lieutenant",
                "Campaign",
                "WarRoom",
                "Swarm",
                "Doctrine",
                "Holocron",
                "Librarian",
                "Editor",
                "Planner",
                "Sandbox",
                "Signer",
                "Ledger",
                "Validator",
                "Gate",
                "Crab",
                "Benchmark",
                "IChing",
                "Consolidation",
                "Decay",
                "ThreadingManager",
                "FileReader",
                "TestRunner",
                "Controller",
                "Optimizer",
                "ConversationReader",
                # WhiteMagic-specific dispatch classes
                "Bridge",
                "Miner",
                "Orchestrator",
                "Session",
                "Backend",
                "Studio",
                "Council",
                "Modes",
                "Intake",
                "State",
                "Enforcer",
                "Cache",
                "Spatial",
                "Dream",
                "System",
                "Creative",
                "Mansion",
                "Adaptive",
                "Holographic",
                "Hybrid",
                "Contract",
                "Browser",
                "Koka",
                "Zodiac",
                "Cognitive",
                "Recursive",
                "Fusion",
                "Embedding",
                # Dispatch table entry points (called via string-based lookup)
                "Handler",
                "Wrapper",
                "Router",
                "Dispatcher",
                "Startup",
                "Shutdown",
                "Lifecycle",
                "Bootstrap",
                "Loader",
                "Registry",
                "Factory",
                "Builder",
                "Adapter",
                "Proxy",
                "Facade",
                "Service",
            )
            if any(pattern in class_name for pattern in _DISPATCH_CLASS_PATTERNS):
                continue
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="dead_code",
                    file=str(file_path.relative_to(project_path)),
                    line=line_num,
                    message=f"Method '{class_name}.{method_name}' may be unused.",
                    suggestion="If public API, it may be called externally. Verify before removing.",
                )
            )
