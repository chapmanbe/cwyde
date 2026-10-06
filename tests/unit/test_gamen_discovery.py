"""Binary discovery for gamen-validate (gamen-lean's binary; no gamen-hs cabal fallback)."""

import stat

import pytest

from cwyde.exceptions import GamenBinaryNotFound
from cwyde_haskell_bridge import discovery


def _exe(path):
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """No env vars, and an empty PATH, so only what a test sets up is found."""
    monkeypatch.delenv("CWYDE_GAMEN_BIN", raising=False)
    monkeypatch.delenv("GAMEN_VALIDATE_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    return tmp_path


def test_cwyde_variable_wins(clean_env, monkeypatch):
    cwyde_bin = _exe(clean_env / "cwyde-gv")
    other = _exe(clean_env / "other-gv")
    monkeypatch.setenv("CWYDE_GAMEN_BIN", str(cwyde_bin))
    monkeypatch.setenv("GAMEN_VALIDATE_BIN", str(other))
    assert discovery.find_gamen_validate() == cwyde_bin


def test_shared_variable_is_the_second_choice(clean_env, monkeypatch):
    shared = _exe(clean_env / "shared-gv")
    monkeypatch.setenv("CWYDE_GAMEN_BIN", str(clean_env / "missing"))
    monkeypatch.setenv("GAMEN_VALIDATE_BIN", str(shared))
    assert discovery.find_gamen_validate() == shared


def test_path_is_the_third_choice(clean_env, monkeypatch):
    bindir = clean_env / "bin"
    bindir.mkdir()
    exe = _exe(bindir / "gamen-validate")
    monkeypatch.setenv("PATH", str(bindir))
    assert discovery.find_gamen_validate() == exe


def test_nothing_found_is_none(clean_env):
    assert discovery.find_gamen_validate() is None


def test_a_gamen_hs_cabal_build_is_not_picked_up(clean_env, monkeypatch):
    home = clean_env / "home"
    leaf = (home / "Code/Haskell/gamen-hs/dist-newstyle/build/aarch64-osx/ghc-9.8.4/"
            "gamen-0.1.0.0/x/gamen-validate/build/gamen-validate")
    leaf.mkdir(parents=True)
    _exe(leaf / "gamen-validate")
    (home / ".cabal/bin").mkdir(parents=True)
    _exe(home / ".cabal/bin/gamen-validate")
    monkeypatch.setattr(discovery.Path, "home", classmethod(lambda cls: home))
    assert discovery.find_gamen_validate() is None


def test_require_raises_with_the_install_hint(clean_env):
    with pytest.raises(GamenBinaryNotFound) as err:
        discovery.require_gamen_validate()
    assert "tools/install.sh" in str(err.value)
    assert "cabal" not in str(err.value)
