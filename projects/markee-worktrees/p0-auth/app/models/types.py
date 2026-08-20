"""Portable column types: PostgreSQL-native with SQLite fallbacks for tests.

Production runs on PostgreSQL (JSONB, native arrays); the test suite runs on
in-memory SQLite, which supports neither. ``with_variant`` keeps the PostgreSQL
DDL unchanged while degrading to JSON storage on SQLite.
"""
from __future__ import annotations

from sqlalchemy import JSON, Date, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

JSONBType = JSONB().with_variant(JSON(), "sqlite")
IntArray = ARRAY(Integer()).with_variant(JSON(), "sqlite")
StrArray = ARRAY(String()).with_variant(JSON(), "sqlite")
DateArray = ARRAY(Date()).with_variant(JSON(), "sqlite")
