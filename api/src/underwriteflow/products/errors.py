"""Shared product-configuration exception types."""


class ProductConfigurationError(ValueError):
    """Raised when product configuration content is invalid or inconsistent."""


class ProductConflictError(ProductConfigurationError):
    """Raised when a concurrent activation change loses its race."""
