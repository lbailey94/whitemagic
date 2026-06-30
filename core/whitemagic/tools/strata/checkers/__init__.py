from collections.abc import Callable
from pathlib import Path

from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding

CheckerFunc = Callable[[Path, FileIndex, list[Finding]], None]


_checkers: list[CheckerFunc] = []


def register(func: CheckerFunc) -> CheckerFunc:
    _checkers.append(func)
    return func


def get_checkers() -> list[CheckerFunc]:
    return _checkers[:]


# Auto-import all checker modules so they self-register
import importlib
import pkgutil

for _, modname, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{modname}")
