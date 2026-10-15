"""System tray icon for Ravan."""

from __future__ import annotations

import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)


def _make_icon_image():
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(70, 130, 180, 255))
    try:
        font = ImageFont.truetype("tahoma.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    draw.text((32, 30), "ر", fill=(255, 255, 255, 255), font=font, anchor="mm")
    return img


class TrayIcon:
    def __init__(
        self,
        on_quit: Callable[[], None],
        on_show_lang: Callable[[], None] | None = None,
        on_settings: Callable[[], None] | None = None,
        on_toggle_prediction: Callable[[bool], None] | None = None,
        is_prediction_enabled: Callable[[], bool] | None = None,
    ) -> None:
        self._on_quit = on_quit
        self._on_show_lang = on_show_lang
        self._on_settings = on_settings
        self._on_toggle_prediction = on_toggle_prediction
        self._is_prediction_enabled = is_prediction_enabled
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import pystray
            from pystray import MenuItem as Item
        except ImportError:
            log.warning("pystray not installed — tray icon disabled")
            return

        def visible_pred(_item) -> bool:
            if self._is_prediction_enabled is None:
                return True
            return self._is_prediction_enabled()

        menu = pystray.Menu(
            Item("Show language (Alt+L)", self._show_lang),
            Item("Settings…", self._settings),
            Item(
                "Word prediction",
                self._toggle_prediction,
                checked=visible_pred,
            ),
            pystray.Menu.SEPARATOR,
            Item("Quit", self._quit),
        )
        self._icon = pystray.Icon("Ravan", _make_icon_image(), "Ravan", menu)
        self._thread = threading.Thread(
            target=self._icon.run, name="ravan-tray", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:  # noqa: BLE001
                pass
            self._icon = None

    def notify(self, message: str, title: str = "Ravan") -> None:
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception:  # noqa: BLE001
                pass

    def _quit(self, _icon=None, _item=None) -> None:
        self._on_quit()

    def _show_lang(self, _icon=None, _item=None) -> None:
        if self._on_show_lang:
            self._on_show_lang()

    def _settings(self, _icon=None, _item=None) -> None:
        if self._on_settings:
            self._on_settings()

    def _toggle_prediction(self, _icon=None, _item=None) -> None:
        if self._on_toggle_prediction:
            current = (
                self._is_prediction_enabled() if self._is_prediction_enabled else True
            )
            self._on_toggle_prediction(not current)
