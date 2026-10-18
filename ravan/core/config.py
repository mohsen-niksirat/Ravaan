"""Application configuration — %APPDATA%\\Ravan\\config.json."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_EXCLUDED_APPS = [
    "explorer.exe",
    "1password.exe",
    "bitwarden.exe",
    "keepass.exe",
    "keepassxc.exe",
    "dashlane.exe",
    "lockapp.exe",
    "logonui.exe",
    "credentialuibroker.exe",
]


@dataclass
class HotkeySpec:
    key: str
    modifiers: list[str] = field(default_factory=list)


@dataclass
class Snippet:
    trigger: str
    replacement: str
    enabled: bool = True



@dataclass
class Theme:
    name: str = "dark"
    background_color: list[int] = field(default_factory=lambda: [30, 30, 30, 230])
    text_color: list[int] = field(default_factory=lambda: [240, 240, 240, 255])
    highlight_color: list[int] = field(default_factory=lambda: [70, 130, 180, 255])
    font_size: float = 14.0
    corner_radius: float = 6.0

    @classmethod
    def dark(cls) -> Theme:
        return cls(
            name="dark",
            background_color=[32, 33, 36, 235],
            text_color=[241, 243, 244, 255],
            highlight_color=[66, 133, 244, 255],
            font_size=14.0,
            corner_radius=8.0,
        )

    @classmethod
    def light(cls) -> Theme:
        return cls(
            name="light",
            background_color=[255, 255, 255, 240],
            text_color=[32, 33, 36, 255],
            highlight_color=[26, 115, 232, 255],
            font_size=14.0,
            corner_radius=8.0,
        )

    @classmethod
    def high_contrast(cls) -> Theme:
        return cls(
            name="high_contrast",
            background_color=[0, 0, 0, 255],
            text_color=[255, 255, 255, 255],
            highlight_color=[255, 255, 0, 255],
            font_size=15.0,
            corner_radius=4.0,
        )


@dataclass
class Config:
    convert_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("F12", []))
    lang_indicator_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("L", ["Alt"]))
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
    clipboard_history_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("V", ["Alt"]))
    normalize_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("F12", ["Ctrl"]))
    case_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("F12", ["Shift"]))
    inline_calc_enabled: bool = True
    sound_feedback_enabled: bool = False
    undo_autocorrect_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("Z", ["Ctrl", "Shift"]))
    fix_punctuation_spacing: bool = True
    autocorrect_mode: str = "safe"  # "off" | "safe" | "normal"
    ignored_words: list[str] = field(default_factory=list)
    theme_mode: str = "auto"  # "auto" | "dark" | "light"
    has_seen_onboarding: bool = False
    quick_stats_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("S", ["Alt"]))
    cloud_sync_enabled: bool = False
    gist_token: str = ""
    gist_id: str = ""
    last_sync_time: str = ""
    ui_language: str = "auto"  # "auto" | "en" | "fa"
    schema_version: int = 2
    sync_backend: str = "gist"  # "gist" | "webdav"
    webdav_url: str = ""
    webdav_username: str = ""
    webdav_password: str = ""
    sync_interval_min: int = 0  # 0 (off), 15, 60 min
    power_mode_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("P", ["Ctrl", "Alt"]))
    power_mode_duration_min: int = 0
    clip_history_ignore_passwords: bool = True
    clip_history_retention_days: int = 7
    popup_offset_x: int = 0
    popup_offset_y: int = 0


    def is_excluded(
        self,
        exe_name: str | None,
        class_name: str | None = None,
        window_class: str | None = None,
    ) -> bool:
        cls = class_name or window_class
        return is_app_excluded(exe_name, self.excluded_apps, class_name=cls)

    def is_word_ignored(self, word: str) -> bool:
        if not word:
            return False
        w_low = word.strip().lower()
        return any(w_low == ign.strip().lower() for ign in self.ignored_words)


def is_app_excluded(
    exe_name: str | None,
    excluded_apps: list[str],
    class_name: str | None = None,
    window_class: str | None = None,
) -> bool:
    """Return True if exe_name or class_name matches excluded_apps (case-insensitive)."""
    name = exe_name.strip().lower() if exe_name else ""
    c_name = (class_name or window_class or "").strip().lower()
    for item in excluded_apps:
        excl = item.strip().lower()
        if not excl:
            continue
        if excl.startswith("class:"):
            target_class = excl[6:].strip()
            if target_class and c_name == target_class:
                return True
        elif name and (name == excl or name.endswith(excl)):
            return True
        elif c_name and c_name == excl:
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


def migrate_config_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Perform schema version migration on config dictionary."""
    ver = int(data.get("schema_version", 1))
    if ver < 2:
        data["schema_version"] = 2
        data.setdefault("sync_backend", "gist")
        data.setdefault("webdav_url", "")
        data.setdefault("webdav_username", "")
        data.setdefault("webdav_password", "")
        data.setdefault("sync_interval_min", 0)
    return data


def config_from_dict(raw_data: dict[str, Any]) -> Config:
    data = migrate_config_dict(dict(raw_data))
    snippets = [
        Snippet(
            trigger=str(s["trigger"]),
            replacement=str(s["replacement"]),
            enabled=bool(s.get("enabled", True)),
        )
        for s in data.get("snippets", [])
        if isinstance(s, dict) and s.get("trigger") and "replacement" in s
    ]
    excluded = data.get("excluded_apps", DEFAULT_EXCLUDED_APPS)
    if not isinstance(excluded, list):
        excluded = DEFAULT_EXCLUDED_APPS

    from ravan.core.crypto import unprotect_secret

    gist_tok, g_mig = unprotect_secret(str(data.get("gist_token", "")))
    webdav_pwd, w_mig = unprotect_secret(str(data.get("webdav_password", "")))
    if g_mig or w_mig:
        log.info("Migrated plaintext sync credentials to DPAPI encryption.")

    return Config(
        convert_hotkey=_hotkey_from_dict(data.get("convert_hotkey"), HotkeySpec("F12")),
        lang_indicator_hotkey=_hotkey_from_dict(data.get("lang_indicator_hotkey"), HotkeySpec("L", ["Alt"])),
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
        clipboard_history_hotkey=_hotkey_from_dict(data.get("clipboard_history_hotkey"), HotkeySpec("V", ["Alt"])),
        normalize_hotkey=_hotkey_from_dict(data.get("normalize_hotkey"), HotkeySpec("F12", ["Ctrl"])),
        case_hotkey=_hotkey_from_dict(data.get("case_hotkey"), HotkeySpec("F12", ["Shift"])),
        inline_calc_enabled=bool(data.get("inline_calc_enabled", True)),
        sound_feedback_enabled=bool(data.get("sound_feedback_enabled", False)),
        undo_autocorrect_hotkey=_hotkey_from_dict(data.get("undo_autocorrect_hotkey"), HotkeySpec("Z", ["Ctrl", "Shift"])),
        fix_punctuation_spacing=bool(data.get("fix_punctuation_spacing", True)),
        autocorrect_mode=str(data.get("autocorrect_mode", "safe")).lower(),
        ignored_words=[str(w).strip() for w in data.get("ignored_words", []) if str(w).strip()],
        theme_mode=str(data.get("theme_mode", "auto")),
        has_seen_onboarding=bool(data.get("has_seen_onboarding", False)),
        quick_stats_hotkey=_hotkey_from_dict(data.get("quick_stats_hotkey"), HotkeySpec("S", ["Alt"])),
        cloud_sync_enabled=bool(data.get("cloud_sync_enabled", False)),
        gist_token=gist_tok,
        gist_id=str(data.get("gist_id", "")),
        last_sync_time=str(data.get("last_sync_time", "")),
        ui_language=str(data.get("ui_language", "auto")),
        schema_version=int(data.get("schema_version", 2)),
        sync_backend=str(data.get("sync_backend", "gist")),
        webdav_url=str(data.get("webdav_url", "")),
        webdav_username=str(data.get("webdav_username", "")),
        webdav_password=webdav_pwd,
        sync_interval_min=_bounded_int(data, "sync_interval_min", 0, 0, 1440),
        power_mode_hotkey=_hotkey_from_dict(data.get("power_mode_hotkey"), HotkeySpec("P", ["Ctrl", "Alt"])),
        power_mode_duration_min=_bounded_int(data, "power_mode_duration_min", 0, 0, 1440),
        clip_history_ignore_passwords=bool(data.get("clip_history_ignore_passwords", True)),
        clip_history_retention_days=_bounded_int(data, "clip_history_retention_days", 7, 1, 365),
        popup_offset_x=_bounded_int(data, "popup_offset_x", 0, -2000, 2000),
        popup_offset_y=_bounded_int(data, "popup_offset_y", 0, -2000, 2000),
    )


def config_to_dict(cfg: Config) -> dict[str, Any]:
    d = asdict(cfg)
    from ravan.core.crypto import protect_secret

    if d.get("gist_token"):
        d["gist_token"] = protect_secret(d["gist_token"])
    if d.get("webdav_password"):
        d["webdav_password"] = protect_secret(d["webdav_password"])
    return d


def load_config() -> Config:
    path = config_path()
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise TypeError("configuration root must be an object")
        cfg = config_from_dict(data)
    except FileNotFoundError:
        cfg = Config()
        save_config(cfg)
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        log.warning("Failed to parse config at %s: %s; moving corrupt file aside", path, exc)
        try:
            if path.is_file():
                backup = path.with_name(f"config.json.corrupt.{int(time.time())}")
                path.rename(backup)
                log.info("Moved corrupt config to %s", backup)
        except OSError:
            pass
        cfg = Config()
        save_config(cfg)

    try:
        from ravan.core.i18n import set_locale

        set_locale(cfg.ui_language)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to initialize locale: %s", exc)
    return cfg


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
