from dataclasses import dataclass
from enum import Enum

__all__ = ["FindingSeverity", "Finding"]


class FindingSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Finding:
    severity: FindingSeverity
    category: str
    file: str
    line: int | None
    message: str
    suggestion: str | None = None
