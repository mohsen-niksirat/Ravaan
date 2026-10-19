"""Export and import user data (config, words, snippets, learned model) via ZIP."""

from __future__ import annotations

import json
import logging
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ravan import __version__
from ravan.core.config import config_dir
from ravan.core.sync import merge_dictionaries, merge_snippets

log = logging.getLogger(__name__)

USER_DATA_FILES = (
    "config.json",
    "user_words.txt",
    "learned_corpus.json",
    "learning_v2.json",
    "clipboard_history.json",
    "stats.json",
    "snippets.json",
)


def export_user_data(dest_zip: Path | str | None = None) -> Path:
    """Export all Ravaan user profile data to a ZIP archive using the data manifest."""
    src_dir = config_dir()
    if dest_zip is None or not str(dest_zip).strip():
        ts_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_path = Path.cwd() / f"Ravan-Backup-{ts_str}.zip"
    else:
        target_path = Path(dest_zip).resolve()

    target_path.parent.mkdir(parents=True, exist_ok=True)

    files_to_pack: list[tuple[Path, str]] = []
    if src_dir.is_dir():
        for filename in USER_DATA_FILES:
            file_path = src_dir / filename
            if file_path.is_file():
                files_to_pack.append((file_path, filename))

    from ravan.core.data_manifest import get_data_manifest

    manifest_meta = get_data_manifest()
    manifest = {
        "app": "Ravaan",
        "version": __version__,
        "exported_at": datetime.now().isoformat(),
        "schema_version": 3,
        "files": [arcname for _, arcname in files_to_pack],
        "registry": manifest_meta.get("files", {}),
    }

    with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for file_path, arcname in files_to_pack:
            zf.write(file_path, arcname=arcname)

    log.info("Exported %d files to %s", len(files_to_pack), target_path)
    return target_path


def import_user_data(src_zip: Path | str, merge: bool = False) -> dict[str, Any]:
    """Import and restore or merge Ravaan user data from a ZIP archive."""
    zip_path = Path(src_zip).resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(f"Backup file not found: {zip_path}")

    dest_dir = config_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create a safety backup of existing user data
    ts = int(time.time())
    backup_folder = dest_dir / "backups" / f"pre-import-{ts}"
    backup_folder.mkdir(parents=True, exist_ok=True)
    for filename in USER_DATA_FILES:
        curr = dest_dir / filename
        if curr.is_file():
            shutil.copy2(curr, backup_folder / filename)

    restored_files: list[str] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        archive_names = set(zf.namelist())

        if "manifest.json" in archive_names:
            try:
                manifest_dict = json.loads(zf.read("manifest.json").decode("utf-8"))
                from ravan.core.data_manifest import validate_backup_manifest

                valid, reason = validate_backup_manifest(manifest_dict)
                if not valid:
                    raise ValueError(f"Invalid backup archive: {reason}")
            except Exception as exc:
                if isinstance(exc, ValueError):
                    raise
                log.warning("Could not validate backup manifest: %s", exc)

        if not merge:
            # Clean replace mode with auto-migration of config
            for filename in USER_DATA_FILES:
                if filename in archive_names:
                    data = zf.read(filename)
                    if filename == "config.json":
                        try:
                            from ravan.core.config import migrate_config_dict

                            cfg_dict = json.loads(data.decode("utf-8"))
                            cfg_dict = migrate_config_dict(cfg_dict)
                            data = json.dumps(cfg_dict, ensure_ascii=False, indent=2).encode("utf-8")
                        except Exception:
                            pass
                    (dest_dir / filename).write_bytes(data)
                    restored_files.append(filename)
        else:
            # Intelligent merge mode
            # A. User words
            if "user_words.txt" in archive_names:
                imported_words = [
                    line.strip()
                    for line in zf.read("user_words.txt").decode("utf-8").splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                words_file = dest_dir / "user_words.txt"
                current_words = (
                    [
                        line.strip()
                        for line in words_file.read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    if words_file.is_file()
                    else []
                )
                merged_words = merge_dictionaries(current_words, imported_words)
                words_file.write_text("\n".join(merged_words) + "\n", encoding="utf-8")
                restored_files.append("user_words.txt (merged)")

            # B. Config & Snippets
            if "config.json" in archive_names:
                cfg_file = dest_dir / "config.json"
                try:
                    imported_cfg_dict = json.loads(
                        zf.read("config.json").decode("utf-8")
                    )
                    from ravan.core.config import migrate_config_dict

                    imported_cfg_dict = migrate_config_dict(imported_cfg_dict)
                    curr_cfg_dict = (
                        json.loads(cfg_file.read_text(encoding="utf-8"))
                        if cfg_file.is_file()
                        else {}
                    )
                    curr_cfg_dict = migrate_config_dict(curr_cfg_dict)
                    imp_snippets = imported_cfg_dict.get("snippets", [])
                    curr_snippets = curr_cfg_dict.get("snippets", [])
                    resolved_snips, _ = merge_snippets(
                        curr_snippets, imp_snippets, resolution_strategy="keep_both"
                    )
                    curr_cfg_dict["snippets"] = resolved_snips
                    cfg_file.write_text(
                        json.dumps(curr_cfg_dict, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    restored_files.append("config.json (snippets merged)")
                except Exception as exc:
                    log.warning("Failed merging config.json: %s", exc)

            # C. Learned model files
            for model_file in ("learned_corpus.json", "learning_v2.json"):
                if model_file in archive_names:
                    try:
                        imp_data = json.loads(zf.read(model_file).decode("utf-8"))
                        curr_path = dest_dir / model_file
                        curr_data = (
                            json.loads(curr_path.read_text(encoding="utf-8"))
                            if curr_path.is_file()
                            else {}
                        )
                        for k, v in imp_data.items():
                            if isinstance(v, (int, float)):
                                curr_data[k] = max(curr_data.get(k, 0), v)
                            elif isinstance(v, dict):
                                sub = curr_data.setdefault(k, {})
                                for sub_k, sub_v in v.items():
                                    sub[sub_k] = max(sub.get(sub_k, 0), sub_v)
                        curr_path.write_text(
                            json.dumps(curr_data, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        restored_files.append(f"{model_file} (merged)")
                    except Exception as exc:
                        log.warning("Failed merging %s: %s", model_file, exc)

            # D. Clipboard history
            if "clipboard_history.json" in archive_names:
                clip_file = dest_dir / "clipboard_history.json"
                try:
                    imp_data = json.loads(zf.read("clipboard_history.json").decode("utf-8"))

                    curr_data = (
                        json.loads(clip_file.read_text(encoding="utf-8"))
                        if clip_file.is_file()
                        else {}
                    )
                    imp_list = imp_data.get("items", []) if isinstance(imp_data, dict) else (imp_data if isinstance(imp_data, list) else [])
                    curr_list = curr_data.get("items", []) if isinstance(curr_data, dict) else (curr_data if isinstance(curr_data, list) else [])
                    merged_items = list(dict.fromkeys(curr_list + imp_list))[:50]
                    curr_pinned = curr_data.get("pinned", []) if isinstance(curr_data, dict) else []
                    imp_pinned = imp_data.get("pinned", []) if isinstance(imp_data, dict) else []
                    merged_pinned = list(dict.fromkeys(curr_pinned + imp_pinned))
                    merged_dict = {
                        "pinned": merged_pinned,
                        "items": merged_items,
                        "timestamps": curr_data.get("timestamps", {}) if isinstance(curr_data, dict) else {},
                    }
                    clip_file.write_text(json.dumps(merged_dict, ensure_ascii=False, indent=2), encoding="utf-8")
                    restored_files.append("clipboard_history.json (merged)")

                except Exception as exc:
                    log.warning("Failed merging clipboard_history.json: %s", exc)

    log.info("Imported backup from %s (merge=%s)", zip_path, merge)
    return {
        "ok": True,
        "restored_files": restored_files,
        "merge": merge,
        "backup_created": str(backup_folder),
    }
