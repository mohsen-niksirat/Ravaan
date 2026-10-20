"""System tray icon for Ravaan with quick toggles, pause timer, and status indicators."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


def _make_icon_image(dimmed: bool = False, paused: bool = False):
    from pathlib import Path

    from PIL import Image, ImageDraw, ImageFont

    icon_path = Path(__file__).resolve().parent.parent / "data" / "icon.ico"
    base_img: Image.Image | None = None
    if icon_path.is_file():
        try:
            raw = Image.open(icon_path)
            base_img = raw.resize((64, 64), Image.Resampling.LANCZOS).convert("RGBA")
        except Exception:
            base_img = None

    if base_img is None:
        base_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base_img)
        circle_color = (100, 110, 120, 180) if (dimmed or paused) else (70, 130, 180, 255)
        text_color = (200, 200, 200, 200) if (dimmed or paused) else (255, 255, 255, 255)
        draw.ellipse((4, 4, 60, 60), fill=circle_color)
        try:
            font = ImageFont.truetype("tahoma.ttf", 34)
        except OSError:
            font = ImageFont.load_default()
        draw.text((32, 30), "ر", fill=text_color, font=font, anchor="mm")

    if paused:
        overlay = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.ellipse((36, 36, 62, 62), fill=(240, 150, 0, 240))
        draw.rectangle((44, 43, 46, 55), fill=(255, 255, 255, 255))
        draw.rectangle((50, 43, 52, 55), fill=(255, 255, 255, 255))
        return Image.alpha_composite(base_img, overlay)

    if dimmed:
        r, g, b, a = base_img.split()
        a = a.point(lambda p: int(p * 0.45))
        base_img.putalpha(a)
        return base_img

    return base_img


class TrayIcon:
    """System tray manager with quick feature toggles and pause timer."""

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
        on_toggle_autocorrect: Callable[[bool], None] | None = None,
        is_autocorrect_enabled: Callable[[], bool] | None = None,
        on_toggle_auto_zwnj: Callable[[bool], None] | None = None,
        is_auto_zwnj_enabled: Callable[[], bool] | None = None,
        on_toggle_pause: Callable[[], None] | None = None,
        is_paused: Callable[[], bool] | None = None,
        on_toggle_translit: Callable[[], None] | None = None,
        is_translit_enabled: Callable[[], bool] | None = None,
        on_clean_clipboard: Callable[[], None] | None = None,
        on_quick_tips: Callable[[], None] | None = None,
    ) -> None:
        self._on_quit = on_quit
        self._on_show_lang = on_show_lang
        self._on_settings = on_settings
        self._on_quick_tips = on_quick_tips
        self._on_snippets = on_snippets
        self._on_diagnostics = on_diagnostics
        self._on_clean_clipboard = on_clean_clipboard
        self._on_toggle_prediction = on_toggle_prediction
        self._is_prediction_enabled = is_prediction_enabled
        self._on_update_found = on_update_found
        self._on_toggle_power_mode = on_toggle_power_mode
        self._is_power_mode_active = is_power_mode_active
        self._on_record_macro = on_record_macro
        self._on_toggle_autocorrect = on_toggle_autocorrect
        self._is_autocorrect_enabled = is_autocorrect_enabled
        self._on_toggle_auto_zwnj = on_toggle_auto_zwnj
        self._is_auto_zwnj_enabled = is_auto_zwnj_enabled
        self._on_toggle_pause = on_toggle_pause
        self._is_paused = is_paused
        self._on_toggle_translit = on_toggle_translit
        self._is_translit_enabled = is_translit_enabled
        self._icon: Any | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import pystray
            from pystray import MenuItem as Item
        except ImportError:
            log.warning("pystray not installed — tray icon disabled")
            return

        def visible_pred(_item: Any) -> bool:
            return self._is_prediction_enabled() if self._is_prediction_enabled else True

        def visible_autocorrect(_item: Any) -> bool:
            return self._is_autocorrect_enabled() if self._is_autocorrect_enabled else True

        def visible_auto_zwnj(_item: Any) -> bool:
            return self._is_auto_zwnj_enabled() if self._is_auto_zwnj_enabled else True

        def visible_power(_item: Any) -> bool:
            return self._is_power_mode_active() if self._is_power_mode_active else False

        def visible_translit(_item: Any) -> bool:
            return bool(self._is_translit_enabled and self._is_translit_enabled())

        def _toggle_translit(_icon: Any, _item: Any) -> None:
            if self._on_toggle_translit:
                self._on_toggle_translit()

        from ravan.core.i18n import t
        from ravan.ui.log_setup import open_logs_folder

        def pause_text(_item: Any) -> str:
            if self._is_paused and self._is_paused():
                return t("tray.resume", "▶ Resume Ravaan")
            return t("tray.pause_10m", "⏸ Pause for 10 min")

        quick_toggles_menu = pystray.Menu(
            Item(
                t("tray.word_prediction", "Word Prediction"),
                self._toggle_prediction,
                checked=visible_pred,
            ),
            Item(
                t("tray.translit", "Finglish Mode (Ctrl+Alt+T)"),
                _toggle_translit,
                checked=visible_translit,
            ),
            Item(
                t("tray.autocorrect", "Autocorrect"),
                self._toggle_autocorrect,
                checked=visible_autocorrect,
            ),
            Item(
                t("tray.auto_zwnj", "Auto-ZWNJ"),
                self._toggle_auto_zwnj,
                checked=visible_auto_zwnj,
            ),
            Item(
                t("tray.power_mode", "Power Mode (Focus Typing)"),
                self._toggle_power_mode,
                checked=visible_power,
            ),
        )

        menu = pystray.Menu(
            Item(pause_text, self._toggle_pause_action),
            Item(t("tray.quick_toggles", "Quick Toggles"), quick_toggles_menu),
            pystray.Menu.SEPARATOR,
            Item(t("tray.show_language", "Show language (Alt+L)"), self._show_lang),
            Item(t("tray.clean_clipboard", "Clean Clipboard Text (Ctrl+Shift+F12)"), self._clean_clipboard),
            Item(t("tray.record_macro", "Record Macro…"), self._record_macro),
            Item(t("tray.snippet_editor", "Snippets…"), self._snippets),
            Item(t("tray.quick_tips", "💡 Quick Tips & Shortcuts"), self._quick_tips),
            Item(t("tray.settings", "Settings…"), self._settings),
            Item(t("tray.diagnostics", "Diagnostics…"), self._diagnostics),
            Item(t("tray.open_logs", "Open logs folder"), lambda: open_logs_folder()),
            Item(t("tray.check_updates", "Check for updates…"), self._check_updates),
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

    def set_paused(self, paused: bool, remaining_min: int = 10) -> None:
        if self._icon is not None:
            try:
                self._icon.icon = _make_icon_image(paused=paused)
                self._icon.title = (
                    f"Ravaan (Paused ~{remaining_min}m)" if paused else "Ravan"
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

    def _quit(self, _icon: Any = None, _item: Any = None) -> None:
        self._on_quit()

    def _show_lang(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_show_lang:
            self._on_show_lang()

    def _toggle_power_mode(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_toggle_power_mode:
            self._on_toggle_power_mode()

    def _toggle_pause_action(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_toggle_pause:
            self._on_toggle_pause()

    def _clean_clipboard(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_clean_clipboard:
            self._on_clean_clipboard()

    def _record_macro(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_record_macro:
            self._on_record_macro()

    def _snippets(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_snippets:
            self._on_snippets()

    def _quick_tips(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_quick_tips:
            self._on_quick_tips()

    def _settings(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_settings:
            self._on_settings()

    def _diagnostics(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_diagnostics:
            self._on_diagnostics()

    def _toggle_prediction(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_toggle_prediction:
            current = (
                self._is_prediction_enabled() if self._is_prediction_enabled else True
            )
            self._on_toggle_prediction(not current)

    def _toggle_autocorrect(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_toggle_autocorrect:
            current = (
                self._is_autocorrect_enabled() if self._is_autocorrect_enabled else True
            )
            self._on_toggle_autocorrect(not current)

    def _toggle_auto_zwnj(self, _icon: Any = None, _item: Any = None) -> None:
        if self._on_toggle_auto_zwnj:
            current = (
                self._is_auto_zwnj_enabled() if self._is_auto_zwnj_enabled else True
            )
            self._on_toggle_auto_zwnj(not current)

    def _check_updates(self, _icon: Any = None, _item: Any = None) -> None:
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
