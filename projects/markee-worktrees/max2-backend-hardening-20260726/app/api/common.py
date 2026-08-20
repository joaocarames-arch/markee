"""Shared Pydantic building blocks for API schemas."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _coerce_str(value: Any) -> Any:
    """Coerce non-null values to ``str`` (used for UUID → str fields)."""
    return str(value) if value is not None else None


# String identifier that accepts UUIDs (or any value) and serialises as a string.
StrId = Annotated[str, BeforeValidator(_coerce_str)]


class ORMModel(BaseModel):
    """Base schema that reads attributes from ORM objects."""

    model_config = ConfigDict(from_attributes=True)
