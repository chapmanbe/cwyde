"""Pydantic models for gamen-validate JSON Lines protocol."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class ValidationRequest(BaseModel):
    formula: dict[str, Any]
    format: str = "tree"


class ValidationResult(BaseModel):
    ok: bool
    valid: bool | None = None
    explanation: str = ""


class ConsistencyRequest(BaseModel):
    formulas: list[dict[str, Any]]
    format: str = "tree"


class ConsistencyResult(BaseModel):
    ok: bool
    consistent: bool | None = None
    explanation: str = ""


class PingResponse(BaseModel):
    ok: bool
    version: str = ""


# Placeholder — used by discovery.py error reporting
searched_paths: list[str] = []
