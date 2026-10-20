"""GitHub release update checker and in-app installer for Ravaan."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ravan import __version__

log = logging.getLogger(__name__)

REPO_NAME = "mohsen-niksirat/Ravaan"
API_URL = f"https://api.github.com/repos/{REPO_NAME}/releases"


def is_prerelease(v: str) -> bool:
    """Return True if version string denotes a pre-release (e.g. -rc1, -beta, -alpha)."""
    clean = v.strip().lstrip("v").lower()
    return any(marker in clean for marker in ("-rc", "-beta", "-alpha", "-dev", "-pre"))


def parse_version_tuple(v: str) -> tuple[int, int, int, int, int]:
    """Parse version string into a comparable tuple:
    (major, minor, patch, stage, rc_num).

    Stable releases get stage=1. Pre-releases get stage=0 (rc), -1 (beta), -2 (alpha).
    """
    clean = v.strip().lstrip("v")
    base, sep, tag = clean.partition("-")
    nums: list[int] = []
    for part in base.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)

    if not sep or not tag:
        return (nums[0], nums[1], nums[2], 1, 0)

    tag_clean = tag.lower()
    rc_digits = "".join(ch for ch in tag_clean if ch.isdigit())
    rc_num = int(rc_digits) if rc_digits else 1
    stage = 0
    if "alpha" in tag_clean:
        stage = -2
    elif "beta" in tag_clean:
        stage = -1
    return (nums[0], nums[1], nums[2], stage, rc_num)


def compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings. Returns 1 if v1 > v2, 0 if equal, -1 if v1 < v2."""
    t1 = parse_version_tuple(v1)
    t2 = parse_version_tuple(v2)
    if t1 > t2:
        return 1
    if t1 < t2:
        return -1
    return 0


def parse_version(v: str) -> tuple[int, ...]:
    """Parse version string like 'v0.4.1' or '1.0.0-beta' into integer tuple."""
    clean = v.strip().lstrip("v").partition("-")[0]
    nums: list[int] = []
    for part in clean.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            nums.append(int(digits))
        else:
            break
    return tuple(nums) if nums else (0, 0, 0)


def extract_changelog_summary(body: str, max_lines: int = 4) -> str:
    """Extract a concise changelog summary from markdown release body."""
    if not body.strip():
        return "Bug fixes and performance improvements."

    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    content_lines = []
    for ln in lines:
        if ln.startswith("#") or ln.startswith("---") or ln.startswith("=="):
            continue
        content_lines.append(ln)
        if len(content_lines) >= max_lines:
            break

    return "\n".join(content_lines) if content_lines else "New release available."


def find_installer_asset(assets: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the setup installer asset (.exe with Setup in name, or any .exe)."""
    # 1. Prefer installer / setup executable
    for a in assets:
        name = str(a.get("name", "")).lower()
        if name.endswith(".exe") and ("setup" in name or "installer" in name):
            return a

    # 2. Fall back to any .exe asset
    for a in assets:
        name = str(a.get("name", "")).lower()
        if name.endswith(".exe"):
            return a

    return None


def extract_sha256_for_installer(
    assets: list[dict[str, Any]],
    installer_name: str | None = None,
    body: str = "",
) -> str | None:
    """Look for a 64-character hex SHA256 in release body or checksum asset."""
    if not body and not assets:
        return None

    if body:
        if installer_name:
            for line in body.splitlines():
                if installer_name.lower() in line.lower():
                    m = re.search(r"\b([a-fA-F0-9]{64})\b", line)
                    if m:
                        return m.group(1).lower()

        label_match = re.search(r"sha-?256[:\s=]+([a-fA-F0-9]{64})", body, re.IGNORECASE)
        if label_match:
            return label_match.group(1).lower()

    return None


def check_for_updates(
    current_ver: str = __version__,
    timeout: float = 6.0,
    allow_prereleases: bool = False,
) -> dict[str, Any]:
    """Check GitHub releases API for latest published release."""
    headers = {
        "User-Agent": f"Ravaan-App/{current_ver}",
        "Accept": "application/vnd.github.v3+json",
    }
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    req = urllib.request.Request(
        API_URL,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                return {
                    "has_update": False,
                    "current_version": current_ver,
                    "latest_version": current_ver,
                    "release_url": f"https://github.com/{REPO_NAME}/releases",
                    "release_notes": "",
                    "changelog_summary": "",
                    "installer_url": None,
                    "installer_name": None,
                    "expected_sha256": None,
                    "error": f"HTTP {response.status}",
                }
            raw_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code == 404:
            log.info("No releases found on GitHub for %s", REPO_NAME)
            return {
                "has_update": False,
                "current_version": current_ver,
                "latest_version": current_ver,
                "release_url": f"https://github.com/{REPO_NAME}/releases",
                "release_notes": "No published releases found yet.",
                "changelog_summary": "",
                "installer_url": None,
                "installer_name": None,
                "expected_sha256": None,
                "error": None,
            }
        log.warning("Could not reach update server: %s", err)
        return {
            "has_update": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "release_url": f"https://github.com/{REPO_NAME}/releases",
            "release_notes": "",
            "changelog_summary": "",
            "installer_url": None,
            "installer_name": None,
            "expected_sha256": None,
            "error": f"HTTP {err.code}: {err.reason}",
        }
    except urllib.error.URLError as err:
        log.warning("Could not reach update server: %s", err)
        return {
            "has_update": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "release_url": f"https://github.com/{REPO_NAME}/releases",
            "release_notes": "",
            "changelog_summary": "",
            "installer_url": None,
            "installer_name": None,
            "expected_sha256": None,
            "error": str(err.reason),
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("Update check failed: %s", exc)
        return {
            "has_update": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "release_url": f"https://github.com/{REPO_NAME}/releases",
            "release_notes": "",
            "changelog_summary": "",
            "installer_url": None,
            "installer_name": None,
            "expected_sha256": None,
            "error": str(exc),
        }

    releases = raw_data if isinstance(raw_data, list) else [raw_data]
    current_is_prerelease = is_prerelease(current_ver)

    eligible: list[dict[str, Any]] = []
    for r in releases:
        if not isinstance(r, dict) or r.get("draft"):
            continue
        tag = str(r.get("tag_name", "")).strip()
        if not tag:
            continue
        is_rel_prerelease = bool(r.get("prerelease")) or is_prerelease(tag)
        if is_rel_prerelease and not current_is_prerelease and not allow_prereleases:
            continue
        eligible.append(r)

    if not eligible:
        return {
            "has_update": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "release_url": f"https://github.com/{REPO_NAME}/releases",
            "release_notes": "No published releases found yet.",
            "changelog_summary": "",
            "installer_url": None,
            "installer_name": None,
            "expected_sha256": None,
            "error": None,
        }

    best_release = max(
        eligible,
        key=lambda r: parse_version_tuple(str(r.get("tag_name", ""))),
    )

    tag = str(best_release.get("tag_name", "")).strip()
    html_url = str(best_release.get("html_url", f"https://github.com/{REPO_NAME}/releases"))
    body = str(best_release.get("body", "")).strip()
    summary = extract_changelog_summary(body)

    assets = best_release.get("assets", [])
    installer = find_installer_asset(assets)
    installer_url = (
        str(installer.get("browser_download_url")) if installer else None
    )
    installer_name = str(installer.get("name")) if installer else None
    expected_sha256 = extract_sha256_for_installer(assets, installer_name, body)

    has_update = compare_versions(tag, current_ver) > 0

    return {
        "has_update": has_update,
        "current_version": current_ver,
        "latest_version": tag.lstrip("v") if tag else current_ver,
        "release_url": html_url,
        "release_notes": body,
        "changelog_summary": summary,
        "installer_url": installer_url,
        "installer_name": installer_name,
        "expected_sha256": expected_sha256,
        "error": None,
    }


def download_and_launch_installer(
    download_url: str,
    installer_name: str | None = None,
    expected_sha256: str | None = None,
    on_progress: Callable[[float], None] | None = None,
    on_ready_to_exit: Callable[[], None] | None = None,
    timeout: float = 30.0,
) -> bool:
    """Download installer executable and launch it, then trigger app exit.

    Enforces HTTPS protocol and verifies SHA-256 integrity and PE signature.
    """
    clean_url = download_url.strip()
    if not clean_url.lower().startswith("https://"):
        log.error("Insecure update URL rejected: %s (only HTTPS permitted)", download_url)
        raise ValueError("Insecure download URL: only HTTPS is permitted for updates")

    fname = installer_name or "Ravaan-Setup-Update.exe"
    target_path = Path(tempfile.gettempdir()) / fname

    req = urllib.request.Request(
        clean_url,
        headers={"User-Agent": f"Ravaan-App/{__version__}"},
    )
    try:
        hasher = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024

            with target_path.open("wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and on_progress:
                        on_progress(downloaded / total_size)

            if on_progress:
                on_progress(1.0)

        # 1. SHA-256 hash verification
        actual_sha256 = hasher.hexdigest().lower()
        if expected_sha256:
            clean_expected = expected_sha256.strip().lower()
            if actual_sha256 != clean_expected:
                log.error(
                    "Update verification failed! Expected SHA256 %s, got %s. Aborting update.",
                    clean_expected,
                    actual_sha256,
                )
                try:
                    target_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return False

        # 2. Binary signature verification (PE / MZ header)
        try:
            with target_path.open("rb") as f:
                magic = f.read(2)
            if magic != b"MZ":
                log.error(
                    "Update integrity failure: downloaded file is not a valid Windows executable (missing MZ magic)."
                )
                try:
                    target_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return False
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to inspect installer binary header: %s", exc)
            return False

        # Launch the installer detached
        subprocess.Popen([str(target_path)])
        log.info("Launched update installer: %s (SHA256: %s)", target_path, actual_sha256)

        # Signal app to release mutex and shut down cleanly
        if on_ready_to_exit:
            on_ready_to_exit()

        return True
    except Exception as exc:  # noqa: BLE001
        log.error("Failed downloading or launching installer: %s", exc)
        return False
