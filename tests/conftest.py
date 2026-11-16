"""Pytest configuration and platform-specific test fixtures/guards."""

from __future__ import annotations

import gc
import sys
from collections.abc import Iterator

import pytest


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Automatically skip tests marked with 'windows' when executed on non-Windows platforms."""
    if item.get_closest_marker("windows") and sys.platform != "win32":
        pytest.skip("Test requires Windows platform (win32)")


@pytest.fixture(autouse=True, scope="module")
def _cleanup_tk_objects_after_module() -> Iterator[None]:
    """Collect lingering Tkinter/PhotoImage cycles on the main thread between modules.

    Prevents worker threads in later multi-threaded tests from triggering CPython's
    cyclic GC on orphaned Tk objects (which causes ``Tcl_AsyncDelete`` crashes).
    """
    yield
    if "tkinter" in sys.modules:
        if "ravan.ui.widgets.icons" in sys.modules:
            import tkinter as tk

            if getattr(tk, "_default_root", None) is None:
                from ravan.ui.widgets.icons import clear_icon_cache

                clear_icon_cache()
        gc.collect()
