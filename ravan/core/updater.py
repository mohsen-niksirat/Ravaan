"""GitHub release update checker and in-app installer for Ravaan."""

from __future__ import annotations

import json
import logging
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
API_URL = f"https://api.github.com/repos/{REPO_NAME}/releases/latest"


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


def check_for_updates(
    current_ver: str = __version__,
    timeout: float = 6.0,
) -> dict[str, Any]:
    """Check GitHub releases API for latest published release."""
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": f"Ravaan-App/{current_ver}",
            "Accept": "application/vnd.github.v3+json",
        },
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
                    "error": f"HTTP {response.status}",
                }
            data = json.loads(response.read().decode("utf-8"))
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
            "error": str(exc),
        }

    tag = str(data.get("tag_name", "")).strip()
    if not tag:
        return {
            "has_update": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "release_url": f"https://github.com/{REPO_NAME}/releases",
            "release_notes": "No published releases found yet.",
            "changelog_summary": "",
            "installer_url": None,
            "installer_name": None,
            "error": None,
        }

    html_url = str(data.get("html_url", f"https://github.com/{REPO_NAME}/releases"))
    body = str(data.get("body", "")).strip()
    summary = extract_changelog_summary(body)

    assets = data.get("assets", [])
    installer = find_installer_asset(assets)
    installer_url = (
        str(installer.get("browser_download_url")) if installer else None
    )
    installer_name = str(installer.get("name")) if installer else None

    latest_tuple = parse_version(tag)
    current_tuple = parse_version(current_ver)
    has_update = latest_tuple > current_tuple

    return {
        "has_update": has_update,
        "current_version": current_ver,
        "latest_version": tag.lstrip("v") if tag else current_ver,
        "release_url": html_url,
        "release_notes": body,
        "changelog_summary": summary,
        "installer_url": installer_url,
        "installer_name": installer_name,
        "error": None,
    }


def download_and_launch_installer(
    download_url: str,
    installer_name: str | None = None,
    on_progress: Callable[[float], None] | None = None,
    on_ready_to_exit: Callable[[], None] | None = None,
    timeout: float = 30.0,
) -> bool:
    """Download installer executable and launch it, then trigger app exit."""
    fname = installer_name or "Ravaan-Setup-Update.exe"
    target_path = Path(tempfile.gettempdir()) / fname

    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"Ravaan-App/{__version__}"},
    )
    try:
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
                    downloaded += len(chunk)
                    if total_size > 0 and on_progress:
                        on_progress(downloaded / total_size)

        # Launch the installer detached
        subprocess.Popen([str(target_path)])
        log.info("Launched update installer: %s", target_path)

        # Signal app to release mutex and shut down cleanly
        if on_ready_to_exit:
            on_ready_to_exit()

        return True
    except Exception as exc:  # noqa: BLE001
        log.error("Failed downloading or launching installer: %s", exc)
        return False
