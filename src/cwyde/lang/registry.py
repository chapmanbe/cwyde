"""Language plugin registry."""

from __future__ import annotations

from cwyde.exceptions import UnknownLanguage

_registry: dict[str, object] = {}


def register(plugin) -> None:
    _registry[plugin.code] = plugin


def get_plugin(code: str):
    if code not in _registry:
        _load_builtin(code)
    if code not in _registry:
        raise UnknownLanguage(f"No language plugin registered for {code!r}. Available: {list(_registry)}")
    return _registry[code]


def _load_builtin(code: str) -> None:
    if code == "en":
        from cwyde.lang.en.adapter import EnglishPlugin
        register(EnglishPlugin())
    elif code == "es":
        from cwyde.lang.es.adapter import SpanishPlugin
        register(SpanishPlugin())
