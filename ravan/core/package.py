"""Snippet package (.ravaanpack) export and import manager."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from .config import Snippet

log = logging.getLogger(__name__)

PACKAGE_FORMAT_VERSION = 1


def export_package(
    snippets: list[Snippet],
    output_path: str | Path,
    title: str = "Ravaan Snippets",
    author: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Export a collection of snippets into a portable .ravaanpack bundle."""
    out = Path(output_path)
    bundle_snippets: list[dict[str, Any]] = []

    for s in snippets:
        item: dict[str, Any] = {
            "trigger": s.trigger,
            "replacement": s.replacement,
            "enabled": getattr(s, "enabled", True),
            "is_regex": getattr(s, "is_regex", False),
            "app_filter": getattr(s, "app_filter", ""),
            "is_image": getattr(s, "is_image", False),
        }
        # If it's an image snippet and path exists, embed as base64
        if getattr(s, "is_image", False) and s.replacement:
            img_path = Path(s.replacement)
            if img_path.is_file():
                try:
                    data = img_path.read_bytes()
                    item["image_data_b64"] = base64.b64encode(data).decode("ascii")
                    item["image_filename"] = img_path.name
                except Exception as exc:  # noqa: BLE001
                    log.warning("Failed to encode image %s: %s", img_path, exc)

        bundle_snippets.append(item)

    payload = {
        "format": "ravaanpack",
        "version": PACKAGE_FORMAT_VERSION,
        "title": title,
        "author": author,
        "description": description,
        "snippet_count": len(bundle_snippets),
        "snippets": bundle_snippets,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Exported %d snippets to %s", len(bundle_snippets), out)
    return payload


def import_package(
    input_path: str | Path,
    image_dest_dir: Path | None = None,
) -> list[Snippet]:
    """Import snippets from a .ravaanpack file, extracting embedded images if present."""
    inp = Path(input_path)
    if not inp.is_file():
        raise FileNotFoundError(f"Package file not found: {inp}")

    raw = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("format") != "ravaanpack":
        raise ValueError("Invalid .ravaanpack format")

    items = raw.get("snippets", [])
    if not isinstance(items, list):
        raise ValueError("Invalid package snippets list")

    imported: list[Snippet] = []
    if image_dest_dir is None:
        data_dir = Path(__file__).resolve().parent.parent / "data" / "snippet_images"
        image_dest_dir = data_dir

    for it in items:
        if not isinstance(it, dict) or "trigger" not in it or "replacement" not in it:
            continue
        trigger = str(it["trigger"]).strip()
        replacement = str(it["replacement"])
        enabled = bool(it.get("enabled", True))
        is_regex = bool(it.get("is_regex", False))
        app_filter = str(it.get("app_filter", ""))
        is_image = bool(it.get("is_image", False))

        # Restore embedded image if available
        if is_image and "image_data_b64" in it:
            b64_data = it["image_data_b64"]
            raw_fname = it.get("image_filename", f"img_{trigger.strip(':/')}.png")
            safe_fname = Path(raw_fname).name or f"img_{trigger.strip(':/')}.png"
            try:
                image_dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = (image_dest_dir / safe_fname).resolve()
                if not str(dest_file).startswith(str(image_dest_dir.resolve())):
                    raise ValueError(f"Unsafe image path: {raw_fname}")
                dest_file.write_bytes(base64.b64decode(b64_data))
                replacement = str(dest_file)
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to extract embedded snippet image: %s", exc)


        imported.append(
            Snippet(
                trigger=trigger,
                replacement=replacement,
                enabled=enabled,
                is_regex=is_regex,
                app_filter=app_filter,
                is_image=is_image,
            )
        )

    log.info("Imported %d snippets from %s", len(imported), inp)
    return imported
