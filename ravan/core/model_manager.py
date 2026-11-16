"""Offline ASR Whisper model manager with SHA-256 verification (%APPDATA%\\Ravaan\\models)."""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ravan.core.config import config_dir

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelSpec:
    """Descriptor for an offline downloadable Whisper ASR model."""

    model_id: str
    whisper_size: str
    name_en: str
    name_fa: str
    filename: str
    size_mb: int
    url: str
    sha256: str = ""
    recommended: bool = False


VOICE_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        model_id="whisper-tiny",
        whisper_size="tiny",
        name_en="Whisper Tiny (Fast CPU · ~75 MB)",
        name_fa="ویسپر Tiny (سریع برای CPU — حدود ۷۵ مگابایت)",
        filename="ggml-tiny.bin",
        size_mb=75,
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
        sha256="be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21",
        recommended=False,
    ),
    ModelSpec(
        model_id="whisper-base",
        whisper_size="base",
        name_en="Whisper Base (Balanced FA/EN · ~142 MB)",
        name_fa="ویسپر Base (متعادل فارسی/انگلیسی — حدود ۱۴۲ مگابایت)",
        filename="ggml-base.bin",
        size_mb=142,
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
        sha256="60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
        recommended=True,
    ),
    ModelSpec(
        model_id="whisper-small",
        whisper_size="small",
        name_en="Whisper Small (High Persian Accuracy · ~466 MB)",
        name_fa="ویسپر Small (دقت بالای فارسی — حدود ۴۶۶ مگابایت)",
        filename="ggml-small.bin",
        size_mb=466,
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
        sha256="1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b",
        recommended=False,
    ),
)

_MODELS_BY_ID: dict[str, ModelSpec] = {spec.model_id: spec for spec in VOICE_MODELS}


def verify_file_sha256(path: Path, expected_sha256: str) -> bool:
    """Verify SHA-256 checksum of a downloaded file using streaming 64KB reads."""
    clean_expected = (expected_sha256 or "").strip().lower()
    if not clean_expected:
        return path.is_file() and path.stat().st_size > 0
    if not path.is_file():
        return False
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().lower() == clean_expected


def default_models_dir() -> Path:
    """Return canonical %APPDATA%\\Ravaan\\models directory."""
    return config_dir() / "models"


class ModelManager:
    """Manage local offline ASR model weights with progress & SHA-256 verification."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else default_models_dir()

    def ensure_dir(self) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir

    @staticmethod
    def get_spec(model_id: str) -> ModelSpec:
        if model_id in _MODELS_BY_ID:
            return _MODELS_BY_ID[model_id]
        for spec in VOICE_MODELS:
            if spec.whisper_size == model_id:
                return spec
        raise KeyError(f"Unknown voice model id: {model_id!r}")

    def model_path(self, model_id: str) -> Path:
        spec = self.get_spec(model_id)
        return self.base_dir / spec.filename

    def is_installed(self, model_id: str, verify_hash: bool = False) -> bool:
        try:
            spec = self.get_spec(model_id)
        except KeyError:
            return False
        path = self.base_dir / spec.filename
        if not path.is_file() or path.stat().st_size == 0:
            return False
        if verify_hash and spec.sha256:
            return verify_file_sha256(path, spec.sha256)
        return True

    def get_installed_path(self, model_id: str) -> Path | None:
        if self.is_installed(model_id):
            return self.model_path(model_id)
        return None

    def list_models(self) -> list[dict[str, Any]]:
        """Return catalog items enriched with install state and disk size."""
        items: list[dict[str, Any]] = []
        for spec in VOICE_MODELS:
            target = self.base_dir / spec.filename
            installed = target.is_file() and target.stat().st_size > 0
            actual_bytes = int(target.stat().st_size) if installed else 0
            items.append({
                "model_id": spec.model_id,
                "whisper_size": spec.whisper_size,
                "name_en": spec.name_en,
                "name_fa": spec.name_fa,
                "filename": spec.filename,
                "size_mb": spec.size_mb,
                "sha256": spec.sha256,
                "recommended": spec.recommended,
                "installed": installed,
                "actual_bytes": actual_bytes,
                "path": str(target),
            })
        return items

    def download_model(
        self,
        model_id: str,
        on_progress: Callable[[int, int, str], None] | None = None,
        cancel_event: threading.Event | None = None,
        timeout: float = 30.0,
        verify_checksum: bool = True,
    ) -> Path:
        """Download a curated Whisper model atomically into models_dir with SHA-256 verification."""
        spec = self.get_spec(model_id)
        self.ensure_dir()
        target = self.base_dir / spec.filename
        part_path = self.base_dir / f"{spec.filename}.part"

        if part_path.exists():
            part_path.unlink(missing_ok=True)

        req = urllib.request.Request(
            spec.url,
            headers={"User-Agent": "Ravaan-Voice/3.0"},
            method="GET",
        )
        downloaded = 0
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                hdr_len = resp.headers.get("Content-Length")
                total = int(hdr_len) if hdr_len and str(hdr_len).isdigit() else spec.size_mb * 1024 * 1024
                if on_progress:
                    on_progress(0, total, "downloading")
                with part_path.open("wb") as out_fh:
                    while True:
                        if cancel_event is not None and cancel_event.is_set():
                            raise InterruptedError("Model download cancelled")
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        out_fh.write(chunk)
                        downloaded += len(chunk)
                        if on_progress:
                            on_progress(downloaded, max(total, downloaded), "downloading")

            if verify_checksum and spec.sha256:
                if on_progress:
                    on_progress(downloaded, downloaded, "verifying")
                if not verify_file_sha256(part_path, spec.sha256):
                    raise ValueError(f"SHA-256 verification failed for {spec.model_id}")

            shutil.move(str(part_path), str(target))
            if on_progress:
                on_progress(downloaded, downloaded, "ready")
            log.info("Downloaded voice model %s (%d bytes)", spec.model_id, downloaded)
            return target
        except Exception:
            part_path.unlink(missing_ok=True)
            raise

    def delete_model(self, model_id: str) -> bool:
        """Delete an installed model binary from disk."""
        try:
            target = self.model_path(model_id)
        except KeyError:
            return False
        if target.is_file():
            target.unlink(missing_ok=True)
            return True
        return False
