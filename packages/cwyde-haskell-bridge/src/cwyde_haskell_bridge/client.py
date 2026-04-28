"""
GamenBridge — subprocess client for gamen-validate.

Per-call mode (default): each request is a fresh subprocess.run() call.
Persistent mode: manages a long-running process (v0.2+ feature, stubbed here).

Pattern from:
  ~/Code/Julia/guideline-validation/extraction/src/guideline_extraction/detect_conflicts.py:208-226
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cwyde.formal.modal import ModalFormula

from cwyde_haskell_bridge.discovery import find_gamen_validate
from cwyde_haskell_bridge.schema import ConsistencyResult, PingResponse, ValidationResult


class GamenBridge:
    def __init__(
        self,
        binary: Path | None = None,
        mode: Literal["per_call", "persistent"] = "per_call",
        timeout_s: float = 5.0,
    ):
        if binary is not None:
            self._binary = binary
        else:
            self._binary = find_gamen_validate()

        if mode == "persistent":
            raise NotImplementedError("Persistent mode is v0.2+ scope")
        self._mode = mode
        self._timeout = timeout_s

    def _require_binary(self) -> Path:
        if self._binary is None:
            from cwyde.exceptions import GamenBinaryNotFound
            raise GamenBinaryNotFound(searched=["See find_gamen_validate()"])
        return self._binary

    def _call(self, request: dict) -> dict:
        binary = self._require_binary()
        payload = json.dumps(request) + "\n"
        try:
            result = subprocess.run(
                [str(binary)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            from cwyde.exceptions import GamenTimeout
            raise GamenTimeout(f"gamen-validate timed out after {self._timeout}s") from exc
        except OSError as exc:
            from cwyde.exceptions import GamenInvocationError
            raise GamenInvocationError(f"Failed to start gamen-validate: {exc}") from exc

        if result.returncode != 0:
            from cwyde.exceptions import GamenInvocationError
            raise GamenInvocationError(
                f"gamen-validate exited {result.returncode}: {result.stderr.strip()}"
            )

        try:
            response = json.loads(result.stdout.strip().splitlines()[0])
        except (json.JSONDecodeError, IndexError) as exc:
            from cwyde.exceptions import GamenInvocationError
            raise GamenInvocationError(f"Could not parse gamen-validate output: {result.stdout!r}") from exc

        if not response.get("ok", True):
            from cwyde.exceptions import GamenSemanticError
            raise GamenSemanticError(response.get("error", "unknown"), request)

        return response

    def ping(self) -> bool:
        try:
            resp = self._call({"action": "ping"})
            return resp.get("ok", False)
        except Exception:
            return False

    def validate_formula(self, formula: "ModalFormula") -> ValidationResult:
        resp = self._call({
            "action": "validate",
            "formula": formula.to_tree_json(),
        })
        return ValidationResult(**resp)

    def check_consistency(self, formulas: list["ModalFormula"]) -> ConsistencyResult:
        resp = self._call({
            "action": "check_consistency",
            "formulas": [f.to_tree_json() for f in formulas],
        })
        return ConsistencyResult(**resp)
