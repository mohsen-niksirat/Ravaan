"""Per-app snippet groups, app matching, and image snippet validation (Snippets 3.0)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ravan.core.config_types import Snippet, SnippetGroup

log = logging.getLogger(__name__)

__all__ = [
    "SnippetGroup",
    "group_matches_app",
    "groups_from_dict",
    "groups_to_dict",
    "resolve_image_snippet",
    "snippet_matches_app",
    "validate_image_path",
]


def group_matches_app(
    group: SnippetGroup,
    app_name: str | None,
    window_class: str | None = None,
) -> bool:
    """Check if the active application or window class matches an enabled snippet group."""
    if not getattr(group, "enabled", True):
        return False
    if not group.matchers:
        return False

    from ravan.core.config import is_app_excluded

    return is_app_excluded(app_name, group.matchers, class_name=window_class)


def snippet_matches_app(
    snippet: Snippet,
    app_name: str | None,
    window_class: str | None = None,
    groups: list[SnippetGroup] | dict[str, SnippetGroup] | None = None,
) -> bool:
    """Determine whether a snippet is permitted to trigger in the active app context."""
    app_low = app_name.lower().strip() if app_name else ""

    # 1. Legacy app_filter check (comma-separated list of exe basenames)
    filt = getattr(snippet, "app_filter", "")
    if filt and app_low:
        allowed = [a.strip().lower() for a in filt.split(",") if a.strip()]
        base = os.path.basename(app_low)
        base_no_ext = os.path.splitext(base)[0]
        if allowed and not any(a in (app_low, base, base_no_ext) for a in allowed):
            return False

    # 2. Per-app Snippet Groups check
    assigned_groups = getattr(snippet, "groups", None) or []
    if not assigned_groups:
        # Snippets not assigned to any group fire globally
        return True

    if not groups:
        # Assigned to groups, but no groups defined in engine -> do not fire
        return False

    # Build lookup map keyed by both group id and group name (case-insensitive)
    groups_map: dict[str, SnippetGroup] = {}
    if isinstance(groups, dict):
        for k, v in groups.items():
            groups_map[k.lower()] = v
            if v.name:
                groups_map[v.name.lower()] = v
            if v.id:
                groups_map[v.id.lower()] = v
    else:
        for g in groups:
            if g.id:
                groups_map[g.id.lower()] = g
            if g.name:
                groups_map[g.name.lower()] = g

    # Fires if active app matches AT LEAST ONE enabled group assigned to this snippet
    for grp_ref in assigned_groups:
        ref_low = grp_ref.strip().lower()
        grp = groups_map.get(ref_low)
        if grp is not None and group_matches_app(grp, app_name, window_class):
            return True

    return False


def resolve_image_snippet(
    replacement: str, is_image: bool = False
) -> tuple[bool, str]:
    """Detect if a snippet replacement represents an image and extract its file path."""
    stripped = replacement.strip()
    if stripped.startswith("image:"):
        return True, stripped[6:].strip()
    if is_image:
        return True, stripped
    return False, ""


def validate_image_path(path_str: str) -> tuple[bool, str]:
    """Validate that path exists and is a valid image format at save time."""
    if not path_str or not path_str.strip():
        return False, "Image path cannot be empty"
    p = Path(path_str.strip())
    if not p.is_file():
        return False, f"Image file does not exist: {p}"
    try:
        from PIL import Image

        with Image.open(p) as img:
            img.verify()
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"Invalid image format: {exc}"


def groups_to_dict(groups: list[SnippetGroup]) -> list[dict[str, Any]]:
    return [
        {
            "id": g.id,
            "name": g.name,
            "matchers": list(g.matchers),
            "enabled": bool(getattr(g, "enabled", True)),
        }
        for g in groups
    ]


def groups_from_dict(data: list[Any]) -> list[SnippetGroup]:
    if not isinstance(data, list):
        return []
    result: list[SnippetGroup] = []
    for item in data:
        if isinstance(item, dict) and ("id" in item or "name" in item):
            name = str(item.get("name", "")).strip()
            gid = str(item.get("id", "")).strip() or name.lower().replace(" ", "_")
            matchers = [str(m).strip() for m in item.get("matchers", []) if str(m).strip()]
            enabled = bool(item.get("enabled", True))
            result.append(SnippetGroup(id=gid, name=name or gid, matchers=matchers, enabled=enabled))
    return result
