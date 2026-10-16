"""Application configuration — %APPDATA%\\Ravan\\config.json."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_EXCLUDED_APPS = ["explorer.exe"]


@dataclass
class HotkeySpec:
    key: str
    modifiers: list[str] = field(default_factory=list)


@dataclass
class Snippet:
    trigger: str
    replacement: str


@dataclass
class Theme:
    background_color: list[int] = field(default_factory=lambda: [30, 30, 30, 230])
    text_color: list[int] = field(default_factory=lambda: [240, 240, 240, 255])
    highlight_color: list[int] = field(default_factory=lambda: [70, 130, 180, 255])
    font_size: float = 14.0
    corner_radius: float = 6.0


@dataclass
class Config:
    convert_hotkey: HotkeySpec = field(
        default_factory=lambda: HotkeySpec(key="F12", modifiers=[])
    )
    lang_indicator_hotkey: HotkeySpec = field(
        default_factory=lambda: HotkeySpec(key="L", modifiers=["Alt"])
    )
    autocorrect_enabled: bool = True
    prediction_enabled: bool = True
    quickpick_digits: bool = True
    prediction_debounce_ms: int = 50
    prediction_max_candidates: int = 5
    popup_timeout_ms: int = 4000
    min_prefix_len: int = 1
    next_word_prediction: bool = True
    excluded_apps: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_APPS))
    snippets: list[Snippet] = field(default_factory=list)
    launch_at_startup: bool = False
    theme: Theme = field(default_factory=Theme)
    english_dict_enabled: bool = True
    persian_dict_enabled: bool = True
    auto_zwnj_enabled: bool = True
    shift_space_zwnj: bool = True
    clipboard_history_enabled: bool = True
    clipboard_history_hotkey: HotkeySpec = field(
        default_factory=lambda: HotkeySpec(key="V", modifiers=["Alt"])
    )
    normalize_hotkey: HotkeySpec = field(
        default_factory=lambda: HotkeySpec(key="F12", modifiers=["Ctrl"])
    )
    case_hotkey: HotkeySpec = field(
        default_factory=lambda: HotkeySpec(key="F12", modifiers=["Shift"])
    )
    inline_calc_enabled: bool = True
    sound_feedback_enabled: bool = False
    undo_autocorrect_hotkey: HotkeySpec = field(
        default_factory=lambda: HotkeySpec(key="Z", modifiers=["Ctrl", "Shift"])
    )
    fix_punctuation_spacing: bool = True

    def is_excluded(self, exe_name: str | None) -> bool:
        return is_app_excluded(exe_name, self.excluded_apps)


def is_app_excluded(exe_name: str | None, excluded_apps: list[str]) -> bool:
    """Return True if exe_name matches any filename in excluded_apps (case-insensitive)."""
    if not exe_name:
        return False
    name = exe_name.strip().lower()
    for item in excluded_apps:
        excl = item.strip().lower()
        if not excl:
            continue
        if name == excl or name.endswith(excl):
            return True
    return False


def config_dir() -> Path:
    appdata = Path.home() / "AppData" / "Roaming"
    return appdata / "Ravan"


def config_path() -> Path:
    return config_dir() / "config.json"


def hotkey_to_text(spec: HotkeySpec) -> str:
    mods = [m.capitalize() for m in spec.modifiers]
    key = spec.key if len(spec.key) > 1 else spec.key.upper()
    return "+".join([*mods, key])


def text_to_hotkey(text: str) -> HotkeySpec | None:
    parts = [p.strip() for p in text.split("+") if p.strip()]
    if not parts:
        return None
    *mods, key = parts
    norm_mods: list[str] = []
    for m in mods:
        low = m.lower()
        if low in ("ctrl", "control"):
            norm_mods.append("Ctrl")
        elif low == "alt":
            norm_mods.append("Alt")
        elif low == "shift":
            norm_mods.append("Shift")
        elif low == "win":
            norm_mods.append("Win")
        else:
            return None
    return HotkeySpec(key=key, modifiers=norm_mods)


def _hotkey_from_dict(data: Any, default: HotkeySpec) -> HotkeySpec:
    if isinstance(data, dict):
        modifiers = data.get("modifiers", default.modifiers)
        if not isinstance(modifiers, list):
            modifiers = default.modifiers
        return HotkeySpec(
            key=str(data.get("key", default.key)).strip() or default.key,
            modifiers=[str(m) for m in modifiers],
        )
    return HotkeySpec(key=default.key, modifiers=list(default.modifiers))


def _theme_from_dict(data: Any) -> Theme:
    if not isinstance(data, dict):
        return Theme()
    return Theme(
        background_color=list(data.get("background_color", [30, 30, 30, 230])),
        text_color=list(data.get("text_color", [240, 240, 240, 255])),
        highlight_color=list(data.get("highlight_color", [70, 130, 180, 255])),
        font_size=max(6.0, min(float(data.get("font_size", 14.0)), 72.0)),
        corner_radius=max(0.0, min(float(data.get("corner_radius", 6.0)), 32.0)),
    )


def _bounded_int(data: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(int(data.get(key, default)), high))
    except (TypeError, ValueError):
        return default


def config_from_dict(data: dict[str, Any]) -> Config:
    snippets = [
        Snippet(trigger=str(s["trigger"]), replacement=str(s["replacement"]))
        for s in data.get("snippets", [])
        if isinstance(s, dict) and s.get("trigger") and "replacement" in s
    ]
    excluded = data.get("excluded_apps", DEFAULT_EXCLUDED_APPS)
    if not isinstance(excluded, list):
        excluded = DEFAULT_EXCLUDED_APPS
    return Config(
        convert_hotkey=_hotkey_from_dict(data.get("convert_hotkey"), HotkeySpec("F12")),
        lang_indicator_hotkey=_hotkey_from_dict(
            data.get("lang_indicator_hotkey"), HotkeySpec("L", ["Alt"])
        ),
        autocorrect_enabled=bool(data.get("autocorrect_enabled", True)),
        prediction_enabled=bool(data.get("prediction_enabled", True)),
        quickpick_digits=bool(data.get("quickpick_digits", True)),
        prediction_debounce_ms=_bounded_int(data, "prediction_debounce_ms", 50, 0, 5000),
        prediction_max_candidates=_bounded_int(data, "prediction_max_candidates", 5, 1, 20),
        popup_timeout_ms=_bounded_int(data, "popup_timeout_ms", 4000, 0, 120000),
        min_prefix_len=_bounded_int(data, "min_prefix_len", 1, 1, 64),
        next_word_prediction=bool(data.get("next_word_prediction", True)),
        excluded_apps=[str(x).strip().lower() for x in excluded if str(x).strip()],
        snippets=snippets,
        launch_at_startup=bool(data.get("launch_at_startup", False)),
        theme=_theme_from_dict(data.get("theme")),
        english_dict_enabled=bool(data.get("english_dict_enabled", True)),
        persian_dict_enabled=bool(data.get("persian_dict_enabled", True)),
        auto_zwnj_enabled=bool(data.get("auto_zwnj_enabled", True)),
        shift_space_zwnj=bool(data.get("shift_space_zwnj", True)),
        clipboard_history_enabled=bool(data.get("clipboard_history_enabled", True)),
        clipboard_history_hotkey=_hotkey_from_dict(
            data.get("clipboard_history_hotkey"), HotkeySpec("V", ["Alt"])
        ),
        normalize_hotkey=_hotkey_from_dict(
            data.get("normalize_hotkey"), HotkeySpec("F12", ["Ctrl"])
        ),
        case_hotkey=_hotkey_from_dict(
            data.get("case_hotkey"), HotkeySpec("F12", ["Shift"])
        ),
        inline_calc_enabled=bool(data.get("inline_calc_enabled", True)),
        sound_feedback_enabled=bool(data.get("sound_feedback_enabled", False)),
        undo_autocorrect_hotkey=_hotkey_from_dict(
            data.get("undo_autocorrect_hotkey"), HotkeySpec("Z", ["Ctrl", "Shift"])
        ),
        fix_punctuation_spacing=bool(data.get("fix_punctuation_spacing", True)),
    )


def config_to_dict(cfg: Config) -> dict[str, Any]:
    return asdict(cfg)


def load_config() -> Config:
    path = config_path()
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise TypeError("configuration root must be an object")
        return config_from_dict(data)
    except FileNotFoundError:
        cfg = Config()
        save_config(cfg)
        return cfg
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        log.warning("Failed to parse config at %s: %s; using defaults", path, exc)
        return Config()


def save_config(cfg: Config) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so an interruption cannot leave invalid JSON behind.
    fd, temporary = tempfile.mkstemp(prefix="config.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config_to_dict(cfg), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
