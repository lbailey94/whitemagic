from dataclasses import dataclass
from typing import Optional
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
    line: Optional[int]
    message: str
    suggestion: Optional[str] = None
