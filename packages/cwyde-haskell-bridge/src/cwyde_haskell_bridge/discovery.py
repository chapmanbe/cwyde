"""
Binary discovery for gamen-validate.

Generalizes the proven pattern from:
  ~/Code/Julia/guideline-validation/extraction/src/guideline_extraction/detect_conflicts.py:180-205

Search order:
  1. CWYDE_GAMEN_BIN env var
  2. GAMEN_VALIDATE_BIN env var (compat with guideline-validation)
  3. shutil.which("gamen-validate")
  4. cabal build output glob (~/.cabal or local dist-newstyle)
  5. importlib.resources bundled binary (v1.0; returns None in v0.1)
"""

from __future__ import annotations

import glob
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

    # 4. Cabal dist-newstyle in known project locations
    cabal_globs = [
        str(Path.home() / "Code" / "Haskell" / "gamen-hs" / "dist-newstyle" / "build" /
            "*" / "ghc-*" / "gamen-hs-*" / "x" / "gamen-validate" / "build" / "gamen-validate" / "gamen-validate"),
        str(Path.home() / ".cabal" / "bin" / "gamen-validate"),
    ]
    for pattern in cabal_globs:
        matches = glob.glob(pattern)
        if matches:
            p = Path(sorted(matches)[-1])  # latest build
            if p.is_file() and os.access(p, os.X_OK):
                return p
        searched.append(f"glob:{pattern} (no match)")

    # 5. Bundled binary (v1.0 — not yet implemented)
    # searched.append("bundled binary (v0.1: not available)")

    return None


def require_gamen_validate() -> Path:
    """Return the gamen-validate path or raise GamenBinaryNotFound."""
    from cwyde_haskell_bridge.schema import searched_paths
    path = find_gamen_validate()
    if path is None:
        from cwyde.exceptions import GamenBinaryNotFound
        raise GamenBinaryNotFound(searched=["See find_gamen_validate() for search order"])
    return path
