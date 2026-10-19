"""Single data layer manifest registering all Ravaan files, schemas, and privacy policies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ravan import __version__
from ravan.core.config import config_dir

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataFileSpec:
    """Specification of a user data artifact managed by Ravaan."""

    name: str
    schema_version: int
    description: str
    privacy: str  # "credentials" | "sensitive" | "private" | "metrics"
    is_resettable: bool
    default_content: str = ""


DATA_REGISTRY: tuple[DataFileSpec, ...] = (
    DataFileSpec(
        name="config.json",
        schema_version=3,
        description="Core user settings, hotkeys, UI preferences, and DPAPI-encrypted sync credentials",
        privacy="credentials",
        is_resettable=True,
        default_content="{}",
    ),
    DataFileSpec(
        name="user_words.txt",
        schema_version=1,
        description="Custom vocabulary and user dictionary additions (UTF-8 plain text, one per line)",
        privacy="private",
        is_resettable=True,
        default_content="",
    ),
    DataFileSpec(
        name="learning_v2.json",
        schema_version=3,
        description="Learned n-gram transitions, vocabulary decay weights, and per-app language models",
        privacy="private",
        is_resettable=True,
        default_content='{"version": 3, "word_counts": {}, "transitions": {}, "trigrams": {}, "app_word_counts": {}}',
    ),
    DataFileSpec(
        name="clipboard_history.json",
        schema_version=1,
        description="Recent clipboard history ring buffer (password-filtered and entropy-screened)",
        privacy="sensitive",
        is_resettable=True,
        default_content="[]",
    ),
    DataFileSpec(
        name="stats.json",
        schema_version=1,
        description="Typing productivity metrics, session keystroke counters, and layout switch statistics",
        privacy="metrics",
        is_resettable=True,
        default_content="{}",
    ),
)


def get_data_manifest() -> dict[str, Any]:
    """Return live manifest metadata for all registered user data files on disk."""
    base_dir = config_dir()
    manifest_files: dict[str, Any] = {}

    for spec in DATA_REGISTRY:
        path = base_dir / spec.name
        exists = path.is_file()
        size_bytes = path.stat().st_size if exists else 0
        manifest_files[spec.name] = {
            "schema_version": spec.schema_version,
            "description": spec.description,
            "privacy": spec.privacy,
            "is_resettable": spec.is_resettable,
            "exists": exists,
            "size_bytes": size_bytes,
            "path": str(path),
        }

    return {
        "app": "Ravaan",
        "version": __version__,
        "schema_version": 3,
        "config_directory": str(base_dir),
        "files": manifest_files,
    }


def validate_backup_manifest(manifest: dict[str, Any]) -> tuple[bool, str]:
    """Validate an imported backup archive's manifest for compatibility."""
    if not isinstance(manifest, dict):
        return False, "Invalid manifest: root is not a JSON object"

    app = manifest.get("app", "")
    if app not in ("Ravan", "Ravaan"):
        return False, f"Unsupported application: {app!r}"

    schema_ver = manifest.get("schema_version", 1)
    if not isinstance(schema_ver, int) or schema_ver < 1 or schema_ver > 3:
        return False, f"Unsupported backup schema version: {schema_ver}"

    files = manifest.get("files", [])
    if not isinstance(files, list):
        return False, "Invalid manifest: 'files' must be a list"

    return True, "Valid manifest"


def reset_data_file(filename: str) -> bool:
    """Reset a registered data file to its initial default state, creating a safety backup first."""
    spec = next((s for s in DATA_REGISTRY if s.name == filename), None)
    if spec is None or not spec.is_resettable:
        log.warning("Cannot reset unregistered or non-resettable file: %s", filename)
        return False

    base_dir = config_dir()
    target_file = base_dir / filename
    if target_file.is_file():
        backup_dir = base_dir / "backups" / "resets"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = int(target_file.stat().st_mtime if target_file.exists() else 0)

        shutil_backup = backup_dir / f"{filename}.bak_{ts}"
        try:
            target_file.rename(shutil_backup)
        except OSError:
            pass

    target_file.write_text(spec.default_content, encoding="utf-8")
    log.info("Reset data file %s to default state", filename)
    return True


def get_storage_summary() -> dict[str, Any]:
    """Compute aggregate disk storage usage for all Ravaan configuration and cache files."""
    base_dir = config_dir()
    total_bytes = 0
    file_count = 0

    if base_dir.is_dir():
        for p in base_dir.rglob("*"):
            if p.is_file():
                total_bytes += p.stat().st_size
                file_count += 1

    return {
        "config_dir": str(base_dir),
        "total_files": file_count,
        "total_bytes": total_bytes,
        "total_kb": round(total_bytes / 1024, 2),
        "total_mb": round(total_bytes / (1024 * 1024), 2),
    }
