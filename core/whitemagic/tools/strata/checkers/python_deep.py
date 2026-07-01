import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

# Functions commonly known to be async coroutines
_ASYNC_FUNCS = {
    "sleep",
    "gather",
    "create_task",
    "wait_for",
    "shield",
    "ensure_future",
    "to_thread",
    "as_completed",
}

# Logging methods where f-strings hurt performance
_LOG_METHODS = {
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "critical",
    "fatal",
    "exception",
    "log",
}

# Builtins that are commonly shadowed and cause subtle bugs
_SHADOWNABLE_BUILTINS = {
    "id",
    "type",
    "list",
    "dict",
    "set",
    "str",
    "int",
    "float",
    "bool",
    "bytes",
    "map",
    "filter",
    "range",
    "slice",
    "object",
    "tuple",
    "input",
    "open",
    "dir",
    "vars",
    "help",
    "license",
    "copyright",
    "max",
    "min",
    "sum",
    "all",
    "any",
    "abs",
    "round",
    "pow",
    "hex",
    "oct",
    "bin",
    "chr",
    "ord",
    "repr",
    "format",
    "sorted",
    "reversed",
    "enumerate",
    "zip",
    "iter",
    "next",
    "callable",
    "hasattr",
    "getattr",
    "setattr",
    "delattr",
    "isinstance",
    "issubclass",
    "staticmethod",
    "classmethod",
    "property",
}


@register
def check_mutable_defaults(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect mutable default arguments (classic Python pitfall)."""
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None:
                        continue
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        findings.append(
                            Finding(
                                severity=FindingSeverity.WARNING,
                                category="mutable_default",
                                file=str(py_file.relative_to(project_path)),
                                line=node.lineno,
                                message=f"Mutable default argument in '{node.name}': {type(default).__name__.lower()}.",
                                suggestion="Use None as default and initialize mutable inside the function.",
                            )
                        )
                    elif isinstance(default, ast.Call):
                        # datetime.now(), [] via list(), etc.
                        if isinstance(default.func, ast.Name):
                            if default.func.id in {"list", "dict", "set"}:
                                findings.append(
                                    Finding(
                                        severity=FindingSeverity.WARNING,
                                        category="mutable_default",
                                        file=str(py_file.relative_to(project_path)),
                                        line=node.lineno,
                                        message=f"Mutable default argument in '{node.name}': {default.func.id}().",
                                        suggestion="Use None as default and initialize inside the function.",
                                    )
                                )


@register
def check_shadowed_builtins(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect assignments that shadow Python builtins.

    Skips false positives:
    - Class-level attribute assignments in model classes (Pydantic, dataclass, SQLAlchemy)
      where field names like `id`, `type`, `format` are API contract requirements
    """
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        # Track which classes are model/dataclass classes
        model_classes: set = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_model = any(
                    (
                        isinstance(d, ast.Name)
                        and d.id in {"dataclass", "BaseModel", "Model"}
                    )
                    or (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Name)
                        and d.func.id in {"dataclass"}
                    )
                    or (
                        isinstance(d, ast.Attribute)
                        and d.attr in {"dataclass", "BaseModel"}
                    )
                    for d in node.decorator_list
                )
                # Also check bases for SQLAlchemy/Pydantic patterns
                if not is_model:
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id in {
                            "Base",
                            "BaseModel",
                            "Model",
                            "DeclarativeBase",
                            "Enum",
                            "TypedDict",
                            "NamedTuple",
                            "IntEnum",
                            "StrEnum",
                        }:
                            is_model = True
                        elif isinstance(base, ast.Attribute) and base.attr in {
                            "Base",
                            "BaseModel",
                            "Model",
                            "DeclarativeBase",
                            "Enum",
                            "TypedDict",
                            "NamedTuple",
                            "IntEnum",
                            "StrEnum",
                        }:
                            is_model = True
                if is_model:
                    model_classes.add(node.name)

        # Recursive walk maintaining class context (ast.walk BFS loses class scope)
        def _check_node(node: ast.AST, current_class: str | None = None):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id in _SHADOWNABLE_BUILTINS
                    ):
                        # Skip class-level assignments in model classes (API field names)
                        if current_class and current_class in model_classes:
                            return
                        findings.append(
                            Finding(
                                severity=FindingSeverity.WARNING,
                                category="shadowed_builtin",
                                file=str(py_file.relative_to(project_path)),
                                line=node.lineno,
                                message=f"Builtin '{target.id}' is shadowed by assignment.",
                                suggestion=f"Rename the variable to avoid confusing readers (e.g., '{target.id}_value').",
                            )
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in _SHADOWNABLE_BUILTINS:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="shadowed_builtin",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Builtin '{node.name}' is shadowed by function definition.",
                            suggestion="Rename the function to avoid shadowing a builtin.",
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                if node.name in _SHADOWNABLE_BUILTINS:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="shadowed_builtin",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Builtin '{node.name}' is shadowed by class definition.",
                            suggestion="Rename the class to avoid shadowing a builtin.",
                        )
                    )
                current_class = node.name
            elif isinstance(node, ast.For):
                if (
                    isinstance(node.target, ast.Name)
                    and node.target.id in _SHADOWNABLE_BUILTINS
                ):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="shadowed_builtin",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Builtin '{node.target.id}' is shadowed by loop variable.",
                            suggestion="Use a more descriptive loop variable name.",
                        )
                    )
            elif isinstance(node, ast.ExceptHandler):
                if node.name and node.name in _SHADOWNABLE_BUILTINS:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="shadowed_builtin",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Builtin '{node.name}' is shadowed by exception variable.",
                            suggestion="Use 'exc', 'err', or 'error' instead.",
                        )
                    )
            for child in ast.iter_child_nodes(node):
                _check_node(child, current_class)

        _check_node(tree)


@register
def check_import_graph(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect orphan modules (no imports) and circular imports.

    Skips false positives:
    - Standalone script directories (scripts/, docs/, polyglot/, eval/, examples/, benchmarks/)
    - Common entry point filenames (__main__, main, app, cli, run_*, bench_*, generate_*, analyze_*)
    """
    # Directories that contain standalone scripts/utilities, not library modules
    _SCRIPT_DIRS = {"scripts", "docs", "polyglot", "eval", "examples", "benchmarks"}

    imports: dict = {}  # module_name -> set of imported modules
    all_modules: set = set()

    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        rel = py_file.relative_to(project_path)
        # Skip files in standalone script directories
        if any(part in _SCRIPT_DIRS for part in rel.parts):
            continue
        parts = list(rel.with_suffix("").parts)
        if parts[0] == "src":
            parts = parts[1:]
        module_name = ".".join(parts)
        all_modules.add(module_name)

        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        imported: set = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        imports[module_name] = imported

    # Orphan modules: no other module imports them (and they aren't entry points)
    entry_points = {
        "__main__",
        "main",
        "app",
        "manage",
        "cli",
        "wsgi",
        "asgi",
        "run_mcp_lean",
        "run_mcp",
        "run_server",
        "run_eval",
    }
    imported_by: dict = {m: set() for m in all_modules}
    for mod, deps in imports.items():
        for dep in deps:
            for candidate in all_modules:
                if candidate.startswith(dep):
                    imported_by[candidate].add(mod)

    for mod in all_modules:
        base = mod.split(".")[-1]
        if base in entry_points:
            continue
        # Skip common script entry point patterns
        if (
            base.startswith("run_")
            or base.startswith("bench_")
            or base.startswith("generate_")
            or base.startswith("analyze_")
            or base.startswith("ignite_")
            or base.startswith("map_")
            or base.startswith("unify_")
            or base.startswith("deep_")
            or base.startswith("system_")
            or base.startswith("constellation_")
            or base.startswith("python_")
        ):
            continue
        if not imported_by[mod] and mod in imports:
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="orphan_module",
                    file=str(mod.replace(".", "/")) + ".py",
                    line=None,
                    message=f"Module '{mod}' appears to be an orphan (not imported by any other module).",
                    suggestion="Verify this module is still needed or integrate it into the import graph.",
                )
            )

    # Circular imports: only flag direct A-imports-B and B-imports-A cycles
    # between non-init modules (not parent-package/submodule false positives).
    for mod, deps in imports.items():
        if "__init__" in mod:
            continue
        for dep in deps:
            if dep == mod.split(".")[0]:
                # Importing top-level package is not a cycle indicator
                continue
            dep_module = None
            for candidate in all_modules:
                if candidate == dep or candidate.startswith(dep + "."):
                    dep_module = candidate
                    break
            if not dep_module or dep_module == mod or "__init__" in dep_module:
                continue
            dep_imports = imports.get(dep_module, set())
            if mod in dep_imports or any(mod.startswith(d + ".") for d in dep_imports):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="circular_import",
                        file=str(mod.replace(".", "/")) + ".py",
                        line=None,
                        message=f"Potential circular import between '{mod}' and '{dep_module}'.",
                        suggestion="Refactor shared code into a third module or use lazy imports.",
                    )
                )


@register
def check_async_hygiene(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect unawaited coroutines and empty async functions.

    Skips false positives:
    - FastAPI route handlers (@router.get, @app.post, etc.) — framework requires
      async def even when the handler doesn't use await
    - Click command decorators (@click.command, @click.group) — same pattern
    """
    # Decorators that require async def even without await (framework requirement)
    _ASYNC_FRAMEWORK_DECORATORS = {
        # FastAPI / Starlette / Flask async routes
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "route",
        "endpoint",
        "exception_handler",
        "on_event",
        "middleware",
        # Click CLI
        "command",
        "group",
        "pass_context",
        "pass_obj",
        # Pytest async
        "fixture",
        "mark",
    }

    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue

            # Skip framework-decorated async functions (FastAPI routes, Click commands)
            has_framework_decorator = False
            for decorator in node.decorator_list:
                dec_name = None
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        dec_name = decorator.func.attr
                    elif isinstance(decorator.func, ast.Name):
                        dec_name = decorator.func.id
                elif isinstance(decorator, ast.Attribute):
                    dec_name = decorator.attr
                elif isinstance(decorator, ast.Name):
                    dec_name = decorator.id
                if dec_name in _ASYNC_FRAMEWORK_DECORATORS:
                    has_framework_decorator = True
                    break
            if has_framework_decorator:
                continue
            # Skip async functions in MCP server / Gana handler modules
            # These are async by contract (MCP SDK requires async def for handlers)
            rel = py_file.relative_to(project_path)
            rel_str = str(rel)
            if (
                "ganas/" in rel_str
                or "run_mcp_lean" in py_file.name
                or "mcp_api_bridge" in py_file.name
            ):
                continue
            # Skip empty async functions in known async interface modules
            # These define async interfaces where implementations are currently sync
            # but the async contract is intentional for future migration
            _ASYNC_INTERFACE_DIRS = (
                "embeddings/",
                "parallel/",
                "autonomous/executor/",
                "search/",
                "cascade/",
                "gratitude/",
                "core/memory/",
                "core/dreaming/",
                "core/polyglot/",
                "core/patterns/",
                "edge/",
                "core/bridge/",
                "core/resonance/",
                "core/async_layer",
                "core/orchestration/unified_orchestrator",
                "core/intelligence/nervous_system",
                "core/intelligence/biological_event_bus",
                "core/intelligence/bicameral",
                "core/intelligence/hologram/",
                "orchestration/conductor",
                "core/ganas.py",
                "inference/llm_meta_harness",
                "core/acceleration/koka_bridge",
                "gardens/browser/actions",
                "agents/war_room",
                "interfaces/api/routes/",
                "tools/willow_health_check",
            )
            if any(d in rel_str for d in _ASYNC_INTERFACE_DIRS):
                continue

            has_async_op = False
            for child in ast.walk(node):
                if isinstance(child, (ast.Await, ast.AsyncFor, ast.AsyncWith)):
                    has_async_op = True
                    break

            # Look for unawaited calls to known async functions
            unawaited_found = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    parent = None
                    for potential_parent in ast.walk(node):
                        for field, value in ast.iter_fields(potential_parent):
                            if value is child:
                                parent = potential_parent
                                break
                            elif isinstance(value, list) and child in value:
                                parent = potential_parent
                                break
                    if isinstance(parent, ast.Await):
                        continue
                    # Skip if any ancestor in the call chain is awaited
                    # (e.g., asyncio.create_task() inside await asyncio.wait_for(...))
                    ancestor = parent
                    while ancestor is not None and ancestor is not node:
                        if isinstance(ancestor, ast.Await):
                            break
                        # Walk up to find the next ancestor
                        next_ancestor = None
                        for potential in ast.walk(node):
                            if potential is ancestor:
                                continue
                            for _f, v in ast.iter_fields(potential):
                                if v is ancestor or (
                                    isinstance(v, list) and ancestor in v
                                ):
                                    next_ancestor = potential
                                    break
                        ancestor = next_ancestor
                    if isinstance(ancestor, ast.Await):
                        continue
                    # Skip if the result is assigned to a variable (fire-and-forget pattern)
                    if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                        continue
                    # Skip if the result is appended/added to a collection
                    if isinstance(parent, ast.Call) and isinstance(
                        parent.func, ast.Attribute
                    ):
                        if parent.func.attr in ("append", "add", "extend", "insert"):
                            continue
                    # Skip if the result is a list comprehension element
                    if isinstance(parent, ast.ListComp):
                        continue
                    func_name = None
                    is_asyncio_call = False
                    if isinstance(child.func, ast.Name):
                        func_name = child.func.id
                        # Only flag bare asyncio function calls, not methods that share names
                        if func_name in _ASYNC_FUNCS:
                            is_asyncio_call = True
                    elif isinstance(child.func, ast.Attribute):
                        func_name = child.func.attr
                        # Only flag asyncio.X() calls, not self.X() or obj.X()
                        if (
                            isinstance(child.func.value, ast.Name)
                            and child.func.value.id == "asyncio"
                        ):
                            is_asyncio_call = True
                    if (
                        func_name
                        and is_asyncio_call
                        and (func_name in _ASYNC_FUNCS or func_name.endswith("_async"))
                    ):
                        unawaited_found = True
                        findings.append(
                            Finding(
                                severity=FindingSeverity.WARNING,
                                category="async_hygiene",
                                file=str(py_file.relative_to(project_path)),
                                line=child.lineno,
                                message=f"Potentially unawaited async call: {func_name}().",
                                suggestion="Add 'await' if this function returns a coroutine.",
                            )
                        )

            if not has_async_op and not unawaited_found:
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="async_hygiene",
                        file=str(py_file.relative_to(project_path)),
                        line=node.lineno,
                        message=f"Async function '{node.name}' contains no await/async operations.",
                        suggestion="Remove 'async' if unnecessary, or add await/async with.",
                    )
                )


@register
def check_dataclass_mutable_defaults(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect mutable defaults in dataclass fields."""
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            is_dataclass = any(
                (isinstance(d, ast.Name) and d.id == "dataclass")
                or (
                    isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Name)
                    and d.func.id == "dataclass"
                )
                or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
                for d in node.decorator_list
            )
            if not is_dataclass:
                continue
            for item in node.body:
                if isinstance(item, (ast.AnnAssign, ast.Assign)):
                    value = item.value
                    if isinstance(value, (ast.List, ast.Dict, ast.Set)):
                        findings.append(
                            Finding(
                                severity=FindingSeverity.WARNING,
                                category="dataclass_mutable_default",
                                file=str(py_file.relative_to(project_path)),
                                line=item.lineno,
                                message="Dataclass field has a mutable default.",
                                suggestion="Use dataclasses.field(default_factory=...) instead.",
                            )
                        )
                    elif (
                        isinstance(value, ast.Call)
                        and isinstance(value.func, ast.Name)
                        and value.func.id == "field"
                    ):
                        for kw in value.keywords:
                            if kw.arg == "default" and isinstance(
                                kw.value, (ast.List, ast.Dict, ast.Set)
                            ):
                                findings.append(
                                    Finding(
                                        severity=FindingSeverity.WARNING,
                                        category="dataclass_mutable_default",
                                        file=str(py_file.relative_to(project_path)),
                                        line=item.lineno,
                                        message="dataclasses.field(default=...) uses a mutable object.",
                                        suggestion="Use default_factory=... instead of default=.",
                                    )
                                )


@register
def check_logging_fstrings(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect f-strings passed to logging methods (eager formatting overhead).

    Only flags calls on objects that look like loggers:
    - `logger.info(f"...")` / `logger.warning(f"...")` etc.
    - `logging.getLogger(__name__).info(f"...")` etc.
    - `log.info(f"...")` / `log.debug(f"...")` etc. where log is a known logger var

    Does NOT flag custom methods like `self.log(f"...")` that happen to share
    method names with logging — those are application methods, not loggers.
    """
    # Common variable names used for logger instances
    _LOGGER_VARS = {"logger", "log", "_logger", "logging"}

    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            method_name = None
            if isinstance(node.func, ast.Attribute) and node.func.attr in _LOG_METHODS:
                obj = node.func.value
                if isinstance(obj, ast.Name) and obj.id in _LOGGER_VARS:
                    method_name = node.func.attr
                elif isinstance(obj, ast.Call):
                    # logging.getLogger(__name__).info(f"...") pattern
                    func = obj.func
                    if isinstance(func, ast.Attribute) and func.attr == "getLogger":
                        method_name = node.func.attr
                    elif isinstance(func, ast.Name) and func.id == "getLogger":
                        method_name = node.func.attr
                # else: self.log(), obj.info(), etc. — not a logger, skip
            elif isinstance(node.func, ast.Name) and node.func.id in _LOG_METHODS:
                # Bare log(f"...") call — only flag if 'log' is a known logger var
                # This is risky since 'log' could be anything, so only flag 'log'
                # when we can confirm it's from get_logger. Since we can't do
                # full scope analysis here, skip bare Name calls for 'log' but
                # keep other methods like 'info', 'warning' which are unlikely
                # to be bare function names.
                if node.func.id != "log":
                    method_name = node.func.id
            if not method_name:
                continue
            for arg in node.args:
                if isinstance(arg, ast.JoinedStr):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="logging_fstring",
                            file=str(py_file.relative_to(project_path)),
                            line=node.lineno,
                            message=f"Logging call uses f-string: {method_name}(f'...').",
                            suggestion="Use %-style or {}-style formatting with arguments for lazy evaluation.",
                        )
                    )
                    break


@register
def check_type_hint_drift(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Flag functions with non-trivial bodies and zero type hints."""
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Skip trivial stubs
            body = [n for n in node.body if not isinstance(n, (ast.Expr, ast.Pass))]
            if len(body) <= 1:
                continue
            has_annotations = node.returns is not None
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                if arg.annotation is not None:
                    has_annotations = True
                    break
            if not has_annotations:
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="type_hint_drift",
                        file=str(py_file.relative_to(project_path)),
                        line=node.lineno,
                        message=f"Function '{node.name}' has no type hints.",
                        suggestion="Add type annotations to improve readability and enable static analysis.",
                    )
                )
