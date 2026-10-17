"""GitHub release update checker for Ravaan."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from ravan import __version__

log = logging.getLogger(__name__)

REPO_NAME = "mohsen-niksirat/Ravaan"
API_URL = f"https://api.github.com/repos/{REPO_NAME}/releases/latest"


def parse_version(v: str) -> tuple[int, ...]:
    """Parse version string like 'v0.4.1' or '1.0.0-beta' into integer tuple."""
    clean = v.strip().lstrip("v")
    nums: list[int] = []
    for part in clean.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            nums.append(int(digits))
        else:
            break
    return tuple(nums) if nums else (0, 0, 0)


def check_for_updates(
    current_ver: str = __version__,
    timeout: float = 4.0,
) -> dict[str, Any]:
    """Check GitHub releases API for latest published release.

    Returns dict with keys:
        'has_update': bool
        'current_version': str
        'latest_version': str
        'release_url': str
        'release_notes': str
        'error': str | None
    """
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
                "error": None,
            }
        log.warning("Could not reach update server: %s", err)
        return {
            "has_update": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "release_url": f"https://github.com/{REPO_NAME}/releases",
            "release_notes": "",
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
            "error": None,
        }

    html_url = str(data.get("html_url", f"https://github.com/{REPO_NAME}/releases"))
    body = str(data.get("body", "")).strip()

    latest_tuple = parse_version(tag)
    current_tuple = parse_version(current_ver)
    has_update = latest_tuple > current_tuple

    return {
        "has_update": has_update,
        "current_version": current_ver,
        "latest_version": tag.lstrip("v") if tag else current_ver,
        "release_url": html_url,
        "release_notes": body,
        "error": None,
    }
