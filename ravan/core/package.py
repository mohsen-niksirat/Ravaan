"""Snippet package (.ravaanpack) export, import, and integrity verification manager."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import zipfile
from pathlib import Path
from typing import Any

from .config import Snippet
from .config_types import SnippetGroup

log = logging.getLogger(__name__)

PACKAGE_FORMAT_VERSION = 2


class PackageIntegrityError(ValueError):
    """Raised when a .ravaanpack package manifest SHA-256 hash does not match contents."""


def _calc_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_package(
    snippets: list[Snippet],
    output_path: str | Path,
    name: str = "Ravaan Snippets",
    author: str = "",
    description_en: str = "",
    description_fa: str = "",
    groups: list[SnippetGroup] | None = None,
    word_list: list[str] | None = None,
    title: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Export a collection of snippets into a verified, portable .ravaanpack ZIP bundle."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pkg_name = title or name
    desc_en = description_en or description
    desc_fa = description_fa or description

    bundle_snippets: list[dict[str, Any]] = []
    images_to_pack: list[tuple[str, Path, bytes]] = []

    for s in snippets:
        is_img = getattr(s, "is_image", False) or s.replacement.startswith("image:")
        raw_repl = s.replacement[6:].strip() if s.replacement.startswith("image:") else s.replacement.strip()

        if is_img and raw_repl:
            img_file = Path(raw_repl)
            if img_file.is_file():
                img_bytes = img_file.read_bytes()
                img_hash = _calc_sha256(img_bytes)
                safe_name = f"images/{img_hash[:10]}_{img_file.name}"
                images_to_pack.append((safe_name, img_file, img_bytes))
                item_repl = safe_name
                item_hash = img_hash
            else:
                item_repl = raw_repl
                item_hash = _calc_sha256(item_repl.encode("utf-8"))
        else:
            item_repl = s.replacement
            item_hash = _calc_sha256(s.replacement.encode("utf-8"))

        bundle_snippets.append({
            "trigger": s.trigger,
            "replacement": item_repl,
            "enabled": bool(getattr(s, "enabled", True)),
            "is_regex": bool(getattr(s, "is_regex", False)),
            "app_filter": str(getattr(s, "app_filter", "")),
            "is_image": bool(is_img),
            "groups": list(getattr(s, "groups", [])),
            "sha256": item_hash,
        })

    groups_data = [
        {
            "id": g.id,
            "name": g.name,
            "matchers": list(g.matchers),
            "enabled": bool(getattr(g, "enabled", True)),
        }
        for g in (groups or [])
    ]

    manifest = {
        "format": "ravaanpack",
        "format_version": PACKAGE_FORMAT_VERSION,
        "version": PACKAGE_FORMAT_VERSION,
        "name": pkg_name,
        "title": pkg_name,
        "author": author,
        "description": desc_en,
        "description_en": desc_en,
        "description_fa": desc_fa,
        "snippet_count": len(bundle_snippets),
        "snippets": bundle_snippets,
        "groups": groups_data,
        "word_list": list(word_list or []),
    }

    # Create ZIP archive
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write images
        for arc_name, _, img_data in images_to_pack:
            zf.writestr(arc_name, img_data)
        # Write manifest.json
        manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
        zf.writestr("manifest.json", manifest_json.encode("utf-8"))

    log.info("Exported %d snippets to %s (.ravaanpack v2)", len(bundle_snippets), out)
    return manifest


def inspect_package(input_path: str | Path) -> dict[str, Any]:
    """Inspect and cryptographically verify a .ravaanpack package manifest and contents."""
    inp = Path(input_path)
    if not inp.is_file():
        raise FileNotFoundError(f"Package file not found: {inp}")

    # Check if file is a valid ZIP archive
    if zipfile.is_zipfile(inp):
        with zipfile.ZipFile(inp, "r") as zf:
            if "manifest.json" not in zf.namelist():
                raise PackageIntegrityError("Corrupt package: missing manifest.json")
            manifest_raw = zf.read("manifest.json").decode("utf-8")
            manifest = json.loads(manifest_raw)

            if not isinstance(manifest, dict) or manifest.get("format") != "ravaanpack":
                raise PackageIntegrityError("Invalid .ravaanpack format identifier")

            # Verify SHA-256 hashes of every snippet
            for s_info in manifest.get("snippets", []):
                trig = s_info.get("trigger", "")
                repl = s_info.get("replacement", "")
                is_img = bool(s_info.get("is_image", False))
                expected_hash = s_info.get("sha256", "")

                if not expected_hash:
                    raise PackageIntegrityError(f"Missing SHA256 digest for snippet '{trig}'")

                if is_img and repl in zf.namelist():
                    actual_data = zf.read(repl)
                    actual_hash = _calc_sha256(actual_data)
                else:
                    actual_hash = _calc_sha256(repl.encode("utf-8"))

                if actual_hash != expected_hash:
                    raise PackageIntegrityError(
                        f"Package integrity failure: SHA256 mismatch for snippet '{trig}' "
                        f"(expected {expected_hash[:8]}, got {actual_hash[:8]})"
                    )

            return manifest

    # Fallback support for legacy v1 single-file JSON packages
    try:
        raw = json.loads(inp.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("format") == "ravaanpack":
            return raw
    except Exception:  # noqa: BLE001
        pass

    raise PackageIntegrityError("Invalid package: neither a valid .ravaanpack ZIP nor legacy format")


def extract_package_groups(manifest: dict[str, Any]) -> list[SnippetGroup]:
    """Extract snippet groups from verified package manifest."""
    groups_data = manifest.get("groups", [])
    result: list[SnippetGroup] = []
    for g in groups_data:
        result.append(
            SnippetGroup(
                id=str(g.get("id", "")),
                name=str(g.get("name", "")),
                matchers=list(g.get("matchers", [])),
                enabled=bool(g.get("enabled", True)),
            )
        )
    return result


def detect_package_collisions(
    package_path: str | Path,
    existing_snippets: list[Snippet],
) -> tuple[dict[str, Any], list[str]]:
    """Inspect package and return (manifest, list of colliding triggers)."""
    manifest = inspect_package(package_path)
    existing_triggers = {s.trigger for s in existing_snippets}
    package_triggers = [str(s.get("trigger", "")) for s in manifest.get("snippets", [])]
    collisions = [t for t in package_triggers if t in existing_triggers]
    return manifest, collisions


def import_package(
    input_path: str | Path,
    image_dest_dir: Path | None = None,
    replace_existing: bool = False,
    existing_snippets: list[Snippet] | None = None,
) -> list[Snippet]:
    """Import and extract verified snippets from a .ravaanpack package."""
    inp = Path(input_path)
    manifest = inspect_package(inp)  # Strict SHA256 verification
    items = manifest.get("snippets", [])

    if image_dest_dir is None:
        from ravan.core.config import config_dir

        image_dest_dir = config_dir() / "snippet_images"

    existing_map = {s.trigger: s for s in existing_snippets} if existing_snippets else {}
    imported: list[Snippet] = []

    # If ZIP package
    if zipfile.is_zipfile(inp):
        with zipfile.ZipFile(inp, "r") as zf:
            for it in items:
                trig = str(it["trigger"]).strip()
                repl = str(it["replacement"])
                is_img = bool(it.get("is_image", False))
                grps = list(it.get("groups", []))

                if is_img and repl in zf.namelist():
                    safe_name = Path(repl).name
                    image_dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = (image_dest_dir / safe_name).resolve()
                    # Path traversal guard
                    if not str(dest_file).startswith(str(image_dest_dir.resolve())):
                        raise ValueError(f"Unsafe path traversal attempt in package: {repl}")
                    dest_file.write_bytes(zf.read(repl))
                    final_repl = f"image:{dest_file}"
                else:
                    final_repl = repl

                snip = Snippet(
                    trigger=trig,
                    replacement=final_repl,
                    enabled=bool(it.get("enabled", True)),
                    is_regex=bool(it.get("is_regex", False)),
                    app_filter=str(it.get("app_filter", "")),
                    is_image=is_img,
                    groups=grps,
                )
                imported.append(snip)
    else:
        # Legacy v1 single-file JSON unpacker
        for it in items:
            trig = str(it["trigger"]).strip()
            repl = str(it["replacement"])
            is_img = bool(it.get("is_image", False))
            if is_img and "image_data_b64" in it:
                b64_data = it["image_data_b64"]
                raw_fname = it.get("image_filename", f"img_{trig.strip(':/')}.png")
                safe_fname = Path(raw_fname).name or f"img_{trig.strip(':/')}.png"
                image_dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = (image_dest_dir / safe_fname).resolve()
                if not str(dest_file).startswith(str(image_dest_dir.resolve())):
                    raise ValueError(f"Unsafe path traversal attempt in package: {raw_fname}")
                dest_file.write_bytes(base64.b64decode(b64_data))
                repl = f"image:{dest_file}"

            imported.append(
                Snippet(
                    trigger=trig,
                    replacement=repl,
                    enabled=bool(it.get("enabled", True)),
                    is_regex=bool(it.get("is_regex", False)),
                    app_filter=str(it.get("app_filter", "")),
                    is_image=is_img,
                    groups=list(it.get("groups", [])),
                )
            )

    if existing_snippets is not None:
        result: list[Snippet] = list(existing_snippets)
        for s in imported:
            if s.trigger in existing_map:
                if replace_existing:
                    result = [x for x in result if x.trigger != s.trigger]
                    result.append(s)
            else:
                result.append(s)
        return result

    return imported


def cli_pack_handler(args: Any) -> int:
    """Handle 'ravan pack export' and 'ravan pack import' commands."""
    from ravan.core.config import load_config, save_config

    cfg = load_config()
    if args.action == "export":
        export_package(
            cfg.snippets,
            args.path,
            title=getattr(args, "title", "Ravaan Snippets"),
            author=getattr(args, "author", ""),
            groups=getattr(cfg, "snippet_groups", []),
        )
        print(f"Exported {len(cfg.snippets)} snippets to {args.path}")
        return 0

    if args.action == "import":
        try:
            manifest, collisions = detect_package_collisions(args.path, cfg.snippets)
        except PackageIntegrityError as err:
            print(f"Package integrity error: {err}")
            return 1
        except Exception as err:  # noqa: BLE001
            print(f"Failed to inspect package: {err}")
            return 1

        replace = getattr(args, "replace", False)
        if collisions:
            col_list = ", ".join(collisions[:5]) + ("..." if len(collisions) > 5 else "")
            print(f"Collisions detected ({len(collisions)}): {col_list}")
            if not replace:
                print("Skipping collided triggers (pass --replace to overwrite).")

        cfg.snippets = import_package(
            args.path,
            replace_existing=replace,
            existing_snippets=cfg.snippets,
        )

        # Merge groups
        pkg_groups = extract_package_groups(manifest)
        existing_group_ids = {g.id for g in cfg.snippet_groups}
        added_groups = 0
        for g in pkg_groups:
            if g.id not in existing_group_ids:
                cfg.snippet_groups.append(g)
                existing_group_ids.add(g.id)
                added_groups += 1

        save_config(cfg)
        print(
            f"Successfully imported from {args.path}: "
            f"{manifest.get('name', 'Package')} "
            f"({len(manifest.get('snippets', []))} snippets, {added_groups} groups, total {len(cfg.snippets)})"
        )
        return 0

    return 1
