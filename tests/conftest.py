"""Pytest configuration and platform-specific test fixtures/guards."""

from __future__ import annotations

import sys

import pytest


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Automatically skip tests marked with 'windows' when executed on non-Windows platforms."""
    if item.get_closest_marker("windows") and sys.platform != "win32":
        pytest.skip("Test requires Windows platform (win32)")
