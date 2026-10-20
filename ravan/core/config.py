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

from ravan.core.config_migration import migrate_config_dict
from ravan.core.config_types import (
    DEFAULT_EXCLUDED_APPS,
    HotkeySpec,
    Snippet,
    Theme,
)

log = logging.getLogger(__name__)


@dataclass
class Config:
    convert_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("Pause", []))
    lang_indicator_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("L", ["Alt"]))
    autocorrect_enabled: bool = True
    prediction_enabled: bool = True
    learning_enabled: bool = True
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
    clean_clipboard_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("F12", ["Ctrl", "Shift"]))
    inline_calc_enabled: bool = True
    sound_feedback_enabled: bool = False
    undo_autocorrect_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("Z", ["Ctrl", "Shift"]))
    fix_punctuation_spacing: bool = True
    smart_punctuation_enabled: bool = True
    digit_mode: str = "auto"  # "auto" | "fa" | "en" | "keep"
    autocorrect_mode: str = "safe"  # "off" | "safe" | "normal"
    ignored_words: list[str] = field(default_factory=list)
    theme_mode: str = "auto"  # "auto" | "dark" | "light"
    has_seen_onboarding: bool = False
    quick_stats_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("S", ["Ctrl", "Alt"]))
    cloud_sync_enabled: bool = False
    gist_token: str = ""
    gist_id: str = ""
    last_sync_time: str = ""
    ui_language: str = "auto"  # "auto" | "en" | "fa"
    schema_version: int = 3
    sync_learning_profile: bool = False
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
    autofix_mode: str = "safe"  # "off" | "safe" | "aggressive"
    autofix_app_modes: dict[str, str] = field(default_factory=dict)
    autofix_blacklist: list[list[str]] = field(default_factory=list)
    global_undo_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("Pause", ["Ctrl", "Shift"]))
    auto_layout_switch: bool = False
    auto_layout_mode: str = "fix_only"  # "fix_only" | "switch_only" | "fix_and_switch"
    translit_enabled: bool = False
    translit_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("T", ["Ctrl", "Alt"]))
    suggestion_accept_arrow: str = "right"  # "right" | "left" | "none"
    continuation_suggestions_enabled: bool = True
    quick_accent_enabled: bool = False
    quick_accent_hold_ms: int = 300
    ai_assistant_enabled: bool = False
    ai_assistant_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("G", ["Ctrl", "Shift"]))
    ai_provider: str = "ollama"
    ai_endpoint_url: str = "http://localhost:11434"
    ai_api_key: str = ""
    ai_model: str = ""
    ai_replace_selection: bool = False
    voice_dictation_enabled: bool = False
    voice_dictation_hotkey: HotkeySpec = field(default_factory=lambda: HotkeySpec("V", ["Ctrl", "Alt"]))

    @property
    def auto_zwnj(self) -> bool:
        return self.auto_zwnj_enabled

    @auto_zwnj.setter
    def auto_zwnj(self, val: bool) -> None:
        self.auto_zwnj_enabled = bool(val)

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
        elif name:
            name_stem = name[:-4] if name.endswith(".exe") else name
            excl_stem = excl[:-4] if excl.endswith(".exe") else excl
            if name == excl or name.endswith(excl) or name_stem == excl_stem:
                return True
        elif c_name and c_name == excl:
            return True
    return False



def migrate_legacy_appdata(base_appdata: Path | None = None) -> bool:
    """Migrate legacy %APPDATA%/Ravan directory to canonical %APPDATA%/Ravaan."""
    if base_appdata is None:
        env_appdata = os.environ.get("APPDATA")
        base_appdata = Path(env_appdata) if env_appdata else Path.home() / "AppData" / "Roaming"

    legacy_dir = base_appdata / "Ravan"
    canonical_dir = base_appdata / "Ravaan"

    if not legacy_dir.is_dir() or legacy_dir == canonical_dir:
        return False

    canonical_dir.mkdir(parents=True, exist_ok=True)
    migrated_any = False

    for item in legacy_dir.iterdir():
        if item.name.startswith("MIGRATED_TO_RAVAAN"):
            continue
        dest = canonical_dir / item.name
        if not dest.exists():
            try:
                import shutil

                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
                migrated_any = True
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed migrating legacy file %s to %s: %s", item, dest, exc)

    if migrated_any:
        log.info("Migrated legacy user data from %s to %s", legacy_dir, canonical_dir)
        try:
            note = legacy_dir / "MIGRATED_TO_RAVAAN.txt"
            note.write_text(
                "Ravaan user settings and data migrated to %APPDATA%\\Ravaan.\n"
                "This folder is kept as a legacy backup.\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    return migrated_any


def config_dir() -> Path:
    env_appdata = os.environ.get("APPDATA")
    appdata = Path(env_appdata) if env_appdata else Path.home() / "AppData" / "Roaming"
    canonical = appdata / "Ravaan"
    legacy = appdata / "Ravan"
    if legacy.is_dir() and not canonical.exists():
        migrate_legacy_appdata(appdata)
    return canonical


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
    try:
        font_size = max(6.0, min(float(data.get("font_size", 14.0)), 72.0))
    except (TypeError, ValueError):
        font_size = 14.0
    try:
        corner_radius = max(0.0, min(float(data.get("corner_radius", 6.0)), 32.0))
    except (TypeError, ValueError):
        corner_radius = 6.0
    return Theme(
        background_color=list(data.get("background_color", [30, 30, 30, 230])),
        text_color=list(data.get("text_color", [240, 240, 240, 255])),
        highlight_color=list(data.get("highlight_color", [70, 130, 180, 255])),
        font_size=font_size,
        corner_radius=corner_radius,
    )


def _bounded_int(data: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(int(data.get(key, default)), high))
    except (TypeError, ValueError):
        return default


def config_from_dict(raw_data: dict[str, Any]) -> Config:
    data = migrate_config_dict(dict(raw_data))
    snippets = [
        Snippet(
            trigger=str(s["trigger"]),
            replacement=str(s["replacement"]),
            enabled=bool(s.get("enabled", True)),
            is_regex=bool(s.get("is_regex", False)),
            app_filter=str(s.get("app_filter", "")),
            is_image=bool(s.get("is_image", False)),
        )
        for s in data.get("snippets", [])
        if isinstance(s, dict) and s.get("trigger") and "replacement" in s
    ]
    excluded = data.get("excluded_apps", DEFAULT_EXCLUDED_APPS)
    if not isinstance(excluded, list):
        excluded = DEFAULT_EXCLUDED_APPS

    from ravan.core.crypto import (
        CRED_TARGET_AI,
        CRED_TARGET_GIST,
        CRED_TARGET_WEBDAV,
        WINCRED_PREFIX,
        get_credential,
        save_credential,
        unprotect_secret,
    )

    # Gist token resolution
    raw_gist = str(data.get("gist_token", "")).strip()
    if raw_gist.startswith(WINCRED_PREFIX):
        target = raw_gist[len(WINCRED_PREFIX) :].strip() or CRED_TARGET_GIST
        gist_tok = get_credential(target)
        g_mig = False
    elif raw_gist:
        gist_tok, g_mig = unprotect_secret(raw_gist)
        if gist_tok:
            save_credential(CRED_TARGET_GIST, gist_tok)
            g_mig = True
    else:
        gist_tok = get_credential(CRED_TARGET_GIST)
        g_mig = False

    # WebDAV password resolution
    raw_webdav = str(data.get("webdav_password", "")).strip()
    if raw_webdav.startswith(WINCRED_PREFIX):
        target = raw_webdav[len(WINCRED_PREFIX) :].strip() or CRED_TARGET_WEBDAV
        webdav_pwd = get_credential(target)
        w_mig = False
    elif raw_webdav:
        webdav_pwd, w_mig = unprotect_secret(raw_webdav)
        if webdav_pwd:
            save_credential(CRED_TARGET_WEBDAV, webdav_pwd)
            w_mig = True
    else:
        webdav_pwd = get_credential(CRED_TARGET_WEBDAV)
        w_mig = False

    # AI API key resolution
    raw_ai = str(data.get("ai_api_key", "")).strip()
    if raw_ai.startswith(WINCRED_PREFIX):
        target = raw_ai[len(WINCRED_PREFIX) :].strip() or CRED_TARGET_AI
        ai_key = get_credential(target)
        a_mig = False
    elif raw_ai:
        ai_key, a_mig = unprotect_secret(raw_ai)
        if ai_key:
            save_credential(CRED_TARGET_AI, ai_key)
            a_mig = True
    else:
        ai_key = get_credential(CRED_TARGET_AI)
        a_mig = False

    if g_mig or w_mig or a_mig:
        log.info("Migrated credentials to Windows Credential Manager.")

    return Config(
        convert_hotkey=_hotkey_from_dict(data.get("convert_hotkey"), HotkeySpec("Pause")),
        lang_indicator_hotkey=_hotkey_from_dict(data.get("lang_indicator_hotkey"), HotkeySpec("L", ["Alt"])),
        autocorrect_enabled=bool(data.get("autocorrect_enabled", True)),
        prediction_enabled=bool(data.get("prediction_enabled", True)),
        learning_enabled=bool(data.get("learning_enabled", True)),
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
        clean_clipboard_hotkey=_hotkey_from_dict(data.get("clean_clipboard_hotkey"), HotkeySpec("F12", ["Ctrl", "Shift"])),
        inline_calc_enabled=bool(data.get("inline_calc_enabled", True)),
        sound_feedback_enabled=bool(data.get("sound_feedback_enabled", False)),
        undo_autocorrect_hotkey=_hotkey_from_dict(data.get("undo_autocorrect_hotkey"), HotkeySpec("Z", ["Ctrl", "Shift"])),
        fix_punctuation_spacing=bool(data.get("fix_punctuation_spacing", True)),
        smart_punctuation_enabled=bool(data.get("smart_punctuation_enabled", True)),
        digit_mode=str(data.get("digit_mode", "auto")),
        autocorrect_mode=str(data.get("autocorrect_mode", "safe")).lower(),
        ignored_words=[str(w).strip() for w in data.get("ignored_words", []) if str(w).strip()],
        theme_mode=str(data.get("theme_mode", "auto")),
        has_seen_onboarding=bool(data.get("has_seen_onboarding", False)),
        quick_stats_hotkey=_hotkey_from_dict(data.get("quick_stats_hotkey"), HotkeySpec("S", ["Ctrl", "Alt"])),
        cloud_sync_enabled=bool(data.get("cloud_sync_enabled", False)),
        gist_token=gist_tok,
        gist_id=str(data.get("gist_id", "")),
        last_sync_time=str(data.get("last_sync_time", "")),
        ui_language=str(data.get("ui_language", "auto")),
        schema_version=_bounded_int(data, "schema_version", 3, 1, 100),
        sync_learning_profile=bool(data.get("sync_learning_profile", False)),
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
        autofix_mode=str(data.get("autofix_mode", "safe")).lower(),
        autofix_app_modes=dict(data.get("autofix_app_modes", {})),
        autofix_blacklist=list(data.get("autofix_blacklist", [])),
        global_undo_hotkey=_hotkey_from_dict(data.get("global_undo_hotkey"), HotkeySpec("Pause", ["Ctrl", "Shift"])),
        auto_layout_switch=bool(data.get("auto_layout_switch", False)),
        auto_layout_mode=str(data.get("auto_layout_mode", "fix_only")),
        translit_enabled=bool(data.get("translit_enabled", False)),
        translit_hotkey=_hotkey_from_dict(data.get("translit_hotkey"), HotkeySpec("T", ["Ctrl", "Alt"])),
        suggestion_accept_arrow=str(data.get("suggestion_accept_arrow", "right")),
        continuation_suggestions_enabled=bool(data.get("continuation_suggestions_enabled", True)),
        quick_accent_enabled=bool(data.get("quick_accent_enabled", False)),
        quick_accent_hold_ms=_bounded_int(data, "quick_accent_hold_ms", 300, 100, 2000),
        ai_assistant_enabled=bool(data.get("ai_assistant_enabled", False)),
        ai_assistant_hotkey=_hotkey_from_dict(data.get("ai_assistant_hotkey"), HotkeySpec("G", ["Ctrl", "Shift"])),
        ai_provider=str(data.get("ai_provider", "ollama")),
        ai_endpoint_url=str(data.get("ai_endpoint_url", "http://localhost:11434")),
        ai_api_key=ai_key,
        ai_model=str(data.get("ai_model", "")),
        ai_replace_selection=bool(data.get("ai_replace_selection", False)),
        voice_dictation_enabled=bool(data.get("voice_dictation_enabled", False)),
        voice_dictation_hotkey=_hotkey_from_dict(data.get("voice_dictation_hotkey"), HotkeySpec("V", ["Ctrl", "Alt"])),
    )


def config_to_dict(cfg: Config) -> dict[str, Any]:
    d = asdict(cfg)
    from ravan.core.crypto import (
        CRED_TARGET_AI,
        CRED_TARGET_GIST,
        CRED_TARGET_WEBDAV,
        WINCRED_PREFIX,
        delete_credential,
        save_credential,
    )

    if cfg.gist_token:
        save_credential(CRED_TARGET_GIST, cfg.gist_token)
        d["gist_token"] = f"{WINCRED_PREFIX}{CRED_TARGET_GIST}"
    else:
        d["gist_token"] = ""
        delete_credential(CRED_TARGET_GIST)

    if cfg.webdav_password:
        save_credential(CRED_TARGET_WEBDAV, cfg.webdav_password)
        d["webdav_password"] = f"{WINCRED_PREFIX}{CRED_TARGET_WEBDAV}"
    else:
        d["webdav_password"] = ""
        delete_credential(CRED_TARGET_WEBDAV)

    if cfg.ai_api_key:
        save_credential(CRED_TARGET_AI, cfg.ai_api_key)
        d["ai_api_key"] = f"{WINCRED_PREFIX}{CRED_TARGET_AI}"
    else:
        d["ai_api_key"] = ""
        delete_credential(CRED_TARGET_AI)

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
    replaced = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config_to_dict(cfg), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        replaced = True
    finally:
        if not replaced:
            try:
                os.unlink(temporary)
            except OSError:
                pass

