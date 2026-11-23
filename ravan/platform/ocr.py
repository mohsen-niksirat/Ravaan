"""Zero-dependency Windows Native WinRT OCR (`Windows.Media.Ocr`) with Persian ZWNJ cleanup."""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from ravan.core.normalizer import normalize_persian
from ravan.core.thesaurus import apply_homophone_fixes

log = logging.getLogger(__name__)

_PS_OCR_SCRIPT = r"""
param([string]$ImagePath, [string]$LangTag)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Foundation.IAsyncOperation`1, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = $null
if ($LangTag -and $LangTag -ne 'auto') {
    $lang = New-Object Windows.Globalization.Language($LangTag)
    if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($lang)) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    }
}
if (-not $engine) {
    foreach ($candidate in @('fa', 'fa-IR', 'en-US', 'en')) {
        $l = New-Object Windows.Globalization.Language($candidate)
        if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($l)) {
            $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($l)
            if ($engine) { break }
        }
    }
}
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if (-not $engine) {
    throw 'No supported Windows Media OCR language pack available.'
}

$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
Write-Output $result.Text
"""


def is_ocr_supported() -> bool:
    """Return True when Windows native WinRT OCR is available on this platform."""
    return sys.platform == "win32"


def postprocess_ocr_text(raw_text: str, normalize_fa: bool = True) -> str:
    """Clean and normalize OCR-extracted Persian/English text."""
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return ""
    if not normalize_fa:
        return cleaned
    norm = normalize_persian(
        cleaned,
        digits="keep",
        fix_zwnj=True,
        fix_spacing=True,
        fix_punctuation=True,
        fix_grammar=True,
    )
    return apply_homophone_fixes(norm)


def extract_text_from_image(
    image_path: str | Path,
    *,
    lang: str = "auto",
    normalize_fa: bool = True,
    timeout: float = 15.0,
) -> str:
    """Extract text from an image file using Windows Native OCR and apply Persian normalization."""
    path = Path(image_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"OCR image file not found: {path}")
    if not is_ocr_supported():
        return ""

    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _PS_OCR_SCRIPT,
            "-ImagePath",
            str(path),
            "-LangTag",
            lang,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags,
            check=False,
        )
        if res.returncode != 0:
            log.warning("Windows OCR exited with code %d: %s", res.returncode, res.stderr.strip())
            return ""
        return postprocess_ocr_text(res.stdout, normalize_fa=normalize_fa)
    except Exception as exc:  # noqa: BLE001
        log.warning("Windows native OCR failed: %s", exc)
        return ""


def capture_region_and_ocr(
    bbox: tuple[int, int, int, int] | None = None,
    *,
    lang: str = "auto",
    normalize_fa: bool = True,
) -> str:
    """Capture screen (or bounding box `(x1, y1, x2, y2)`) and extract normalized text via OCR."""
    if not is_ocr_supported():
        return ""
    try:
        from PIL import ImageGrab

        img = ImageGrab.grab(bbox=bbox)
    except Exception as exc:  # noqa: BLE001
        log.warning("Screen capture for OCR failed: %s", exc)
        return ""

    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", prefix="ravan_ocr_", delete=False)
    tmp_path = Path(tmp_file.name)
    tmp_file.close()
    try:
        img.save(tmp_path, format="PNG")
        return extract_text_from_image(tmp_path, lang=lang, normalize_fa=normalize_fa)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
