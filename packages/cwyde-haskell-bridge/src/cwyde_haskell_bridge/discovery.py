"""
Binary discovery for gamen-validate.

The binary is gamen-lean's `gamen-validate`; the gamen-hs cabal build is retired
as a runtime dependency. Install it from gamen-lean with `tools/install.sh`, which
prints the value to export.

Search order:
  1. CWYDE_GAMEN_BIN env var
  2. GAMEN_VALIDATE_BIN env var (compat with guideline-validation)
  3. shutil.which("gamen-validate")
  4. importlib.resources bundled binary (v1.0; returns None in v0.1)
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_gamen_validate() -> Path | None:
    """Return the path to a gamen-validate binary, or None if not found."""
    searched: list[str] = []

    # 1. CWYDE_GAMEN_BIN
    env = os.environ.get("CWYDE_GAMEN_BIN")
    if env:
        p = Path(env)
        if p.is_file() and os.access(p, os.X_OK):
            return p
        searched.append(f"CWYDE_GAMEN_BIN={env} (not executable)")

    # 2. GAMEN_VALIDATE_BIN (compat)
    env2 = os.environ.get("GAMEN_VALIDATE_BIN")
    if env2:
        p = Path(env2)
        if p.is_file() and os.access(p, os.X_OK):
            return p
        searched.append(f"GAMEN_VALIDATE_BIN={env2} (not executable)")

    # 3. PATH
    which = shutil.which("gamen-validate")
    if which:
        return Path(which)
    searched.append("PATH (not found)")

    # 4. Bundled binary (v1.0 — not yet implemented)
    # searched.append("bundled binary (v0.1: not available)")

    return None


def require_gamen_validate() -> Path:
    """Return the gamen-validate path or raise GamenBinaryNotFound."""
    path = find_gamen_validate()
    if path is None:
        from cwyde.exceptions import GamenBinaryNotFound
        raise GamenBinaryNotFound(searched=[
            "$CWYDE_GAMEN_BIN",
            "$GAMEN_VALIDATE_BIN",
            "gamen-validate on PATH",
            "install gamen-lean's gamen-validate with tools/install.sh "
            "(it prints the value to export)",
        ])
    return path
