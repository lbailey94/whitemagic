from pathlib import Path
from typing import List, Callable

from whitemagic.tools.strata.models import Finding
from whitemagic.tools.strata.file_index import FileIndex


CheckerFunc = Callable[[Path, FileIndex, List[Finding]], None]


_checkers: List[CheckerFunc] = []


def register(func: CheckerFunc) -> CheckerFunc:
    _checkers.append(func)
    return func


def get_checkers() -> List[CheckerFunc]:
    return _checkers[:]


# Auto-import all checker modules so they self-register
import importlib
import pkgutil

for _, modname, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{modname}")
