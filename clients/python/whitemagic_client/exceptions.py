"""WhiteMagic SDK exceptions."""


class WhiteMagicError(Exception):
    """Base exception for WhiteMagic SDK errors."""

    def __init__(
        self,
        message: str,
        status: int | None = None,
        code: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        if self.status:
            return f"WhiteMagicError[{self.status}]: {self.message}"
        return f"WhiteMagicError: {self.message}"
