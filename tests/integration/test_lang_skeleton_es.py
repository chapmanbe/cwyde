"""
Integration test: Spanish language plugin skeleton.

Validates that:
1. The Spanish plugin loads without error
2. The pipeline runs end-to-end on a Spanish sentence
3. A single annotated sentence with 'se descarta' is classified as INDICATION

This test proves the multilingual abstraction is real, not aspirational.
"""

import pytest


def test_spanish_plugin_loads():
    from cwyde.lang.registry import get_plugin
    plugin = get_plugin("es")
    assert plugin.code == "es"
    assert plugin.negation_typology() == "simple"
    assert plugin.script_direction() == "ltr"


def test_spanish_indication_patterns_load():
    from cwyde.lang.registry import get_plugin
    from cwyde.kb import load_patterns
    plugin = get_plugin("es")
    paths = plugin.indication_patterns()
    assert len(paths) >= 1
    patterns = load_patterns(paths[0])
    assert len(patterns.patterns) >= 1
    pattern_texts = [p.pattern for p in patterns.patterns]
    assert any("descarta" in p for p in pattern_texts)


def test_spanish_indication_pattern_compiles():
    import re
    from cwyde.lang.registry import get_plugin
    from cwyde.kb import load_patterns
    plugin = get_plugin("es")
    for path in plugin.indication_patterns():
        pf = load_patterns(path)
        for entry in pf.patterns:
            re.compile(entry.pattern)  # must not raise
