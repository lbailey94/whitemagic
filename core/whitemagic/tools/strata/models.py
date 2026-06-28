from dataclasses import dataclass
from enum import Enum
from typing import Optional

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
