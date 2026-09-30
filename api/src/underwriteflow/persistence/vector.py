"""Minimal PostgreSQL vector type for pgvector columns."""

from typing import Any

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """Bind and read fixed-width pgvector values without a dependency."""

    cache_ok = True

    # Store the required vector width for SQL rendering and validation.
    def __init__(self, dimensions: int = 768) -> None:
        self.dimensions = dimensions

    # Render the native pgvector column declaration.
    def get_col_spec(self, **_: Any) -> str:
        return f"VECTOR({self.dimensions})"

    # Serialize a Python float list into pgvector text.
    def bind_processor(self, _dialect: Any):
        # Convert one validated vector to PostgreSQL text.
        def bind(value: list[float] | None) -> str | None:
            if value is None:
                return None
            if len(value) != self.dimensions:
                raise ValueError("vector has invalid dimensions")
            return "[" + ",".join(str(float(item)) for item in value) + "]"

        return bind

    # Deserialize pgvector text or driver-returned lists into floats.
    def result_processor(self, _dialect: Any, _coltype: Any):
        # Convert one database vector to a Python float list.
        def result(value: str | list[float] | None) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, list):
                return [float(item) for item in value]
            return [float(item) for item in value.strip("[]").split(",")]

        return result
