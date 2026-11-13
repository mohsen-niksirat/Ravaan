"""Per-app smart profiles for context-aware typing automation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VALID_PROFILE_PRESETS: tuple[str, ...] = ("default", "code", "chat", "formal", "custom")
VALID_PROFILE_LAYOUTS: tuple[str, ...] = ("none", "fa", "en")

PROFILE_BOOL_FIELDS: tuple[str, ...] = (
    "auto_zwnj",
    "orthography_guard",
    "smart_punctuation",
    "prediction_enabled",
    "autofix_enabled",
    "selection_toolbar",
)

# Preset defaults when explicitly assigned to an app profile.
# None means "inherit from global config".
PRESET_OVERRIDES: dict[str, dict[str, Any]] = {
    "default": {
        "auto_zwnj": None,
        "orthography_guard": None,
        "smart_punctuation": None,
        "prediction_enabled": None,
        "autofix_enabled": None,
        "selection_toolbar": None,
        "preferred_layout": "none",
    },
    "code": {
        "auto_zwnj": False,
        "orthography_guard": False,
        "smart_punctuation": False,
        "prediction_enabled": None,
        "autofix_enabled": False,
        "selection_toolbar": False,
        "preferred_layout": "none",
    },
    "chat": {
        "auto_zwnj": True,
        "orthography_guard": True,
        "smart_punctuation": False,
        "prediction_enabled": True,
        "autofix_enabled": True,
        "selection_toolbar": True,
        "preferred_layout": "none",
    },
    "formal": {
        "auto_zwnj": True,
        "orthography_guard": True,
        "smart_punctuation": True,
        "prediction_enabled": True,
        "autofix_enabled": None,
        "selection_toolbar": True,
        "preferred_layout": "fa",
    },
}

# Built-in automatic presets keyed by executable name (case-insensitive).
# At runtime without an explicit user rule, only safe restrictions ("code") alter globals;
# other recognized apps are surfaced as recommended presets in Settings UI.
BUILTIN_APP_PRESETS: dict[str, str] = {
    "code.exe": "code",
    "code - insiders.exe": "code",
    "cursor.exe": "code",
    "windsurf.exe": "code",
    "devenv.exe": "code",
    "pycharm64.exe": "code",
    "pycharm.exe": "code",
    "idea64.exe": "code",
    "webstorm64.exe": "code",
    "rider64.exe": "code",
    "sublime_text.exe": "code",
    "notepad++.exe": "code",
    "windowsterminal.exe": "code",
    "wt.exe": "code",
    "powershell.exe": "code",
    "pwsh.exe": "code",
    "cmd.exe": "code",
    "wezterm-gui.exe": "code",
    "alacritty.exe": "code",
    "mintty.exe": "code",
    "telegram.exe": "chat",
    "whatsapp.exe": "chat",
    "discord.exe": "chat",
    "slack.exe": "chat",
    "bale.exe": "chat",
    "eitaa.exe": "chat",
    "winword.exe": "formal",
    "obsidian.exe": "formal",
    "notion.exe": "formal",
    "thunderbird.exe": "formal",
}


@dataclass(frozen=True)
class ResolvedAppProfile:
    """Effective per-app behavioral flags resolved against global Config."""

    exe: str
    preset: str
    source: str  # "user" | "builtin" | "global"
    auto_zwnj: bool
    orthography_guard: bool
    smart_punctuation: bool
    prediction_enabled: bool
    autofix_enabled: bool
    selection_toolbar: bool
    preferred_layout: str


def normalize_exe_key(exe_name: str | None) -> str:
    """Normalize an executable name or path to lowercase basename."""
    if not exe_name or not isinstance(exe_name, str):
        return ""
    raw = exe_name.strip().replace("/", "\\").rsplit("\\", 1)[-1].lower()
    return raw


def detect_builtin_preset(exe_name: str | None) -> str:
    """Return built-in suggested preset for exe_name ('code', 'chat', 'formal', or 'default')."""
    key = normalize_exe_key(exe_name)
    if not key:
        return "default"
    if key in BUILTIN_APP_PRESETS:
        return BUILTIN_APP_PRESETS[key]
    stem = key[:-4] if key.endswith(".exe") else f"{key}.exe"
    return BUILTIN_APP_PRESETS.get(stem, "default")


def sanitize_profile_entry(raw: Any) -> dict[str, Any]:
    """Validate and normalize a single per-app profile dict."""
    if not isinstance(raw, dict):
        return {"preset": "default", "preferred_layout": "none"}
    preset = str(raw.get("preset", "custom")).strip().lower()
    if preset not in VALID_PROFILE_PRESETS:
        preset = "custom"
    layout = str(raw.get("preferred_layout", "none")).strip().lower()
    if layout not in VALID_PROFILE_LAYOUTS:
        layout = "none"

    entry: dict[str, Any] = {"preset": preset, "preferred_layout": layout}
    for field_name in PROFILE_BOOL_FIELDS:
        val = raw.get(field_name, None)
        entry[field_name] = bool(val) if isinstance(val, bool) else None
    return entry


def sanitize_app_profiles(raw: Any) -> dict[str, dict[str, Any]]:
    """Sanitize a mapping of executable -> profile settings."""
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, dict[str, Any]] = {}
    for key, val in raw.items():
        norm_key = normalize_exe_key(str(key))
        if not norm_key or not isinstance(val, dict):
            continue
        cleaned[norm_key] = sanitize_profile_entry(val)
    return cleaned


def _lookup_user_profile(profiles: dict[str, Any], exe_key: str) -> dict[str, Any] | None:
    if not exe_key or not isinstance(profiles, dict):
        return None
    if exe_key in profiles and isinstance(profiles[exe_key], dict):
        return profiles[exe_key]
    stem = exe_key[:-4] if exe_key.endswith(".exe") else f"{exe_key}.exe"
    for candidate_key, val in profiles.items():
        if not isinstance(val, dict):
            continue
        ck = normalize_exe_key(str(candidate_key))
        if ck == exe_key or ck == stem:
            return val
    return None


def resolve_effective_profile(cfg: Any, exe_name: str | None = None) -> ResolvedAppProfile:
    """Resolve effective feature flags for the current foreground executable."""
    g_zwnj = bool(getattr(cfg, "auto_zwnj_enabled", True))
    g_ortho = bool(getattr(cfg, "orthography_guard_enabled", True))
    g_smart_punct = bool(getattr(cfg, "smart_punctuation_enabled", True))
    g_pred = bool(getattr(cfg, "prediction_enabled", True))
    g_autofix = str(getattr(cfg, "autofix_mode", "safe")).lower() != "off"
    g_sel_tb = bool(getattr(cfg, "selection_toolbar_enabled", True))

    global_defaults = {
        "auto_zwnj": g_zwnj,
        "orthography_guard": g_ortho,
        "smart_punctuation": g_smart_punct,
        "prediction_enabled": g_pred,
        "autofix_enabled": g_autofix,
        "selection_toolbar": g_sel_tb,
    }

    exe_key = normalize_exe_key(exe_name)
    profiles_enabled = bool(getattr(cfg, "app_profiles_enabled", True))
    if not profiles_enabled or not exe_key:
        return ResolvedAppProfile(
            exe=exe_key,
            preset="default",
            source="global",
            preferred_layout="none",
            **global_defaults,
        )

    user_profiles = getattr(cfg, "app_profiles", None) or {}
    user_entry = _lookup_user_profile(user_profiles, exe_key)

    if user_entry is not None:
        clean = sanitize_profile_entry(user_entry)
        preset = clean["preset"]
        base_overrides = PRESET_OVERRIDES.get(preset, {})
        resolved: dict[str, bool] = {}
        for fname in PROFILE_BOOL_FIELDS:
            override = clean.get(fname)
            if override is None:
                override = base_overrides.get(fname)
            resolved[fname] = global_defaults[fname] if override is None else bool(override)
        pref_layout = clean.get("preferred_layout", "none")
        if pref_layout == "none":
            pref_layout = str(base_overrides.get("preferred_layout", "none"))
        return ResolvedAppProfile(
            exe=exe_key,
            preset=preset,
            source="user",
            preferred_layout=pref_layout,
            **resolved,
        )

    builtin_preset = detect_builtin_preset(exe_key)
    if builtin_preset == "code":
        code_ov = PRESET_OVERRIDES["code"]
        return ResolvedAppProfile(
            exe=exe_key,
            preset="code",
            source="builtin",
            auto_zwnj=bool(code_ov["auto_zwnj"]),
            orthography_guard=bool(code_ov["orthography_guard"]),
            smart_punctuation=bool(code_ov["smart_punctuation"]),
            prediction_enabled=g_pred,
            autofix_enabled=bool(code_ov["autofix_enabled"]),
            selection_toolbar=bool(code_ov["selection_toolbar"]),
            preferred_layout="none",
        )

    return ResolvedAppProfile(
        exe=exe_key,
        preset=builtin_preset if builtin_preset != "default" else "default",
        source="builtin" if builtin_preset != "default" else "global",
        preferred_layout="none",
        **global_defaults,
    )
