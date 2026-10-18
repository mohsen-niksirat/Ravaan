"""System tray icon for Ravan."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


def _make_icon_image(dimmed: bool = False):
    from pathlib import Path

    from PIL import Image

    icon_path = Path(__file__).resolve().parent.parent / "data" / "icon.ico"
    if icon_path.is_file() and not dimmed:
        try:
            return Image.open(icon_path)
        except Exception:
            pass

    from PIL import ImageDraw, ImageFont

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    circle_color = (100, 110, 120, 180) if dimmed else (70, 130, 180, 255)
    text_color = (200, 200, 200, 200) if dimmed else (255, 255, 255, 255)
    draw.ellipse((4, 4, 60, 60), fill=circle_color)
    try:
        font = ImageFont.truetype("tahoma.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    draw.text((32, 30), "ر", fill=text_color, font=font, anchor="mm")
    return img


class TrayIcon:
    def __init__(
        self,
        on_quit: Callable[[], None],
        on_show_lang: Callable[[], None] | None = None,
        on_settings: Callable[[], None] | None = None,
        on_snippets: Callable[[], None] | None = None,
        on_diagnostics: Callable[[], None] | None = None,
        on_toggle_prediction: Callable[[bool], None] | None = None,
        is_prediction_enabled: Callable[[], bool] | None = None,
        on_update_found: Callable[[dict[str, Any]], None] | None = None,
        on_toggle_power_mode: Callable[[], None] | None = None,
        is_power_mode_active: Callable[[], bool] | None = None,
        on_record_macro: Callable[[], None] | None = None,
    ) -> None:
        self._on_quit = on_quit
        self._on_show_lang = on_show_lang
        self._on_settings = on_settings
        self._on_snippets = on_snippets
        self._on_diagnostics = on_diagnostics
        self._on_toggle_prediction = on_toggle_prediction
        self._is_prediction_enabled = is_prediction_enabled
        self._on_update_found = on_update_found
        self._on_toggle_power_mode = on_toggle_power_mode
        self._is_power_mode_active = is_power_mode_active
        self._on_record_macro = on_record_macro
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

        def visible_power(_item) -> bool:
            if self._is_power_mode_active is None:
                return False
            return self._is_power_mode_active()

        from ravan.core.i18n import t
        from ravan.ui.log_setup import open_logs_folder

        menu = pystray.Menu(
            Item(t("tray.show_language", "Show language (Alt+L)"), self._show_lang),
            Item(
                t("tray.power_mode", "Power Mode (Focus Typing)"),
                self._toggle_power_mode,
                checked=visible_power,
            ),
            Item(t("tray.record_macro", "Record Macro…"), self._record_macro),
            Item(t("tray.snippet_editor", "Snippets…"), self._snippets),
            Item(t("tray.settings", "Settings…"), self._settings),
            Item(t("tray.diagnostics", "Diagnostics…"), self._diagnostics),
            Item(t("tray.open_logs", "Open logs folder"), lambda: open_logs_folder()),
            Item(t("tray.check_updates", "Check for updates…"), self._check_updates),
            Item(
                t("tray.word_prediction", "Word prediction"),
                self._toggle_prediction,
                checked=visible_pred,
            ),
            pystray.Menu.SEPARATOR,
            Item(t("tray.quit", "Quit"), self._quit),
        )

        self._icon = pystray.Icon("Ravan", _make_icon_image(), "Ravan", menu)
        self._thread = threading.Thread(
            target=self._icon.run, name="ravan-tray", daemon=True
        )
        self._thread.start()

    def set_power_mode(self, active: bool) -> None:
        if self._icon is not None:
            try:
                self._icon.icon = _make_icon_image(dimmed=active)
                self._icon.title = (
                    "Ravan (Power Mode Active)" if active else "Ravan"
                )
            except Exception:
                pass

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

    def _toggle_power_mode(self, _icon=None, _item=None) -> None:
        if self._on_toggle_power_mode:
            self._on_toggle_power_mode()

    def _record_macro(self, _icon=None, _item=None) -> None:
        if self._on_record_macro:
            self._on_record_macro()

    def _snippets(self, _icon=None, _item=None) -> None:
        if self._on_snippets:
            self._on_snippets()

    def _settings(self, _icon=None, _item=None) -> None:
        if self._on_settings:
            self._on_settings()

    def _diagnostics(self, _icon=None, _item=None) -> None:
        if self._on_diagnostics:
            self._on_diagnostics()

    def _toggle_prediction(self, _icon=None, _item=None) -> None:
        if self._on_toggle_prediction:
            current = (
                self._is_prediction_enabled() if self._is_prediction_enabled else True
            )
            self._on_toggle_prediction(not current)

    def _check_updates(self, _icon=None, _item=None) -> None:
        def _bg():
            import webbrowser

            from ravan.core.i18n import t
            from ravan.core.updater import check_for_updates

            res = check_for_updates()
            if self._icon is not None:
                if res.get("error"):
                    self._icon.notify(
                        f"Could not check for updates: {res['error']}",
                        t("notifications.error_title", "Ravaan Error"),
                    )
                elif res["has_update"]:
                    summary = res.get("changelog_summary", "")
                    msg = t(
                        "notifications.update_available_body",
                        "Version {version} is available. Click to download.",
                        version=res["latest_version"],
                    )
                    balloon_text = f"{msg}\n{summary}" if summary else msg
                    self._icon.notify(
                        balloon_text,
                        t("notifications.update_available_title", "Ravaan Update Available"),
                    )
                    if self._on_update_found:
                        self._on_update_found(res)
                    else:
                        try:
                            webbrowser.open(res["release_url"])
                        except Exception:
                            pass
                else:
                    msg = t(
                        "notifications.no_update_body",
                        "You are using the latest version ({version}).",
                        version=res["current_version"],
                    )
                    self._icon.notify(
                        msg,
                        t("notifications.no_update_title", "Ravaan is up to date"),
                    )

        threading.Thread(target=_bg, name="ravan-update-check", daemon=True).start()

