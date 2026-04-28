"""
Shared pytest fixtures and configuration.

--require-gamen flag: turns the gamen integration test skip into a hard failure.
Use this in CI environments where gamen-validate should be available.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--require-gamen",
        action="store_true",
        default=False,
        help="Fail (rather than skip) gamen-validate tests when binary is not available",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_gamen: test requires gamen-validate binary",
    )


@pytest.fixture(scope="session")
def gamen_available():
    from cwyde_haskell_bridge.discovery import find_gamen_validate
    return find_gamen_validate() is not None


@pytest.fixture(autouse=True)
def _handle_gamen_skip(request, gamen_available):
    marker = request.node.get_closest_marker("requires_gamen")
    if marker is None:
        return
    if not gamen_available:
        if request.config.getoption("--require-gamen"):
            pytest.fail("gamen-validate binary not found and --require-gamen is set")
        else:
            pytest.skip("gamen-validate binary not available")
