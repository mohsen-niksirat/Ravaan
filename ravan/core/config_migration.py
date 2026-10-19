"""Configuration schema migration helper."""

from __future__ import annotations

from typing import Any


def migrate_config_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Perform schema version migration on config dictionary."""
    try:
        ver = int(data.get("schema_version", 1))
    except (TypeError, ValueError):
        ver = 1
    if ver < 2:
        data.setdefault("sync_backend", "gist")
        data.setdefault("webdav_url", "")
        data.setdefault("webdav_username", "")
        data.setdefault("webdav_password", "")
        data.setdefault("sync_interval_min", 0)
    if ver < 3:
        data["schema_version"] = 3
        data.setdefault("sync_learning_profile", False)
        data.setdefault("theme_mode", "auto")
        data.setdefault("has_seen_onboarding", False)
        data.setdefault("popup_offset_x", 0)
        data.setdefault("popup_offset_y", 0)
    data.setdefault("autofix_mode", "safe")  # "off" | "safe" | "aggressive"
    data.setdefault("autofix_app_modes", {})
    data.setdefault("autofix_blacklist", [])
    data.setdefault("auto_layout_switch", False)
    data.setdefault("auto_layout_mode", "fix_only")  # "fix_only" | "switch_only" | "fix_and_switch"
    data.setdefault("translit_enabled", False)
    data.setdefault("quick_accent_enabled", False)
    data.setdefault("quick_accent_hold_ms", 300)
    data.setdefault("ai_assistant_enabled", False)
    data.setdefault("voice_dictation_enabled", False)
    data.setdefault("suggestion_accept_arrow", "right")
    data.setdefault("continuation_suggestions_enabled", True)
    return data
