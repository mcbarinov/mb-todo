"""Application-level errors."""


class AppError(Exception):
    """Application-level error with a machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize with an error code and human-readable message.

        Args:
            code: Machine-readable error code (e.g. TODO_NOT_FOUND).
            message: Human-readable error description.

        """
        self.code = code
        self.message = message
        super().__init__(message)
