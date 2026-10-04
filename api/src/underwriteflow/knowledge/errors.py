"""Stable errors for knowledge import and lifecycle operations."""


class KnowledgeError(ValueError):
    """Base error for safe knowledge service failures."""


class KnowledgeConflictError(KnowledgeError):
    """Raised when immutable knowledge identity conflicts."""


class KnowledgeValidationError(KnowledgeError):
    """Raised when a knowledge version cannot become active."""
