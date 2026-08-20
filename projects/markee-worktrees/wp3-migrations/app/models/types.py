"""Portable column types: PostgreSQL-native with SQLite fallbacks for tests.

Production runs on PostgreSQL (JSONB, native arrays); the test suite runs on
in-memory SQLite, which supports neither. ``with_variant`` keeps the PostgreSQL
DDL unchanged while degrading to JSON storage on SQLite.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

JSONBType = JSONB().with_variant(JSON(), "sqlite")
IntArray = ARRAY(Integer()).with_variant(JSON(), "sqlite")
StrArray = ARRAY(String()).with_variant(JSON(), "sqlite")


class _DateArray(TypeDecorator[list[date]]):
    """Store date lists as native arrays on PostgreSQL and JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Date()))
        return dialect.type_descriptor(JSON())

    def process_bind_param(
        self, value: list[date] | None, dialect: Dialect
    ) -> list[date] | list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise TypeError("DateArray expects a list of date values or None")
        if any(type(item) is not date for item in value):
            raise TypeError("DateArray elements must be datetime.date values")
        if dialect.name == "postgresql":
            return value
        return [item.isoformat() for item in value]

    def process_result_value(
        self, value: Any, dialect: Dialect
    ) -> list[date] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise TypeError("DateArray storage must contain a list or null")
        if dialect.name == "postgresql":
            if any(type(item) is not date for item in value):
                raise TypeError("DateArray elements must be datetime.date values")
            return value
        if any(not isinstance(item, str) for item in value):
            raise TypeError("DateArray JSON elements must be ISO-8601 strings")
        return [date.fromisoformat(item) for item in value]


DateArray = _DateArray()
