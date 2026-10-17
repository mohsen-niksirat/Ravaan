"""GitHub Gist Cloud Sync for user words and snippets."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from ravan.core.config import config_dir

log = logging.getLogger(__name__)


def make_local_backup(
    user_words: list[str],
    snippets: list[dict[str, Any]],
) -> Path:
    """Create a local snapshot backup before performing push or pull sync."""
    backup_dir = config_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"sync_backup_{ts}.json"
    data = {
        "timestamp": datetime.now().isoformat(),
        "user_words": list(user_words),
        "snippets": list(snippets),
    }
    backup_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Prune older backups keeping newest 10
    all_backups = sorted(backup_dir.glob("sync_backup_*.json"), key=lambda p: p.stat().st_mtime)
    while len(all_backups) > 10:
        old = all_backups.pop(0)
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass
    return backup_file


def push_to_gist(
    token: str,
    gist_id: str,
    user_words: list[str],
    snippets: list[dict[str, Any]],
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Push local user words and snippets to GitHub Gist."""
    tok = token.strip()
    gid = gist_id.strip()
    if not tok or not gid:
        return {"ok": False, "error": "Missing Gist Personal Access Token or Gist ID"}

    make_local_backup(user_words, snippets)

    payload = {
        "description": "Ravaan Sync — User dictionary and snippets",
        "files": {
            "user_words.txt": {
                "content": "\n".join(user_words) + ("\n" if user_words else "")
            },
            "snippets.json": {
                "content": json.dumps(snippets, ensure_ascii=False, indent=2)
            },
        },
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gid}",
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "Ravaan-App",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status not in (200, 201):
                return {"ok": False, "error": f"HTTP {resp.status}"}
            now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return {"ok": True, "error": None, "timestamp": now_iso}
    except urllib.error.HTTPError as err:
        return {"ok": False, "error": f"HTTP {err.code}: {err.reason}"}
    except urllib.error.URLError as err:
        return {"ok": False, "error": f"Network error: {err.reason}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def pull_from_gist(
    token: str,
    gist_id: str,
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Pull user words and snippets from GitHub Gist."""
    tok = token.strip()
    gid = gist_id.strip()
    if not tok or not gid:
        return {"ok": False, "error": "Missing Gist Personal Access Token or Gist ID"}

    req = urllib.request.Request(
        f"https://api.github.com/gists/{gid}",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Ravaan-App",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return {"ok": False, "error": f"HTTP {resp.status}"}
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return {"ok": False, "error": f"HTTP {err.code}: {err.reason}"}
    except urllib.error.URLError as err:
        return {"ok": False, "error": f"Network error: {err.reason}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}

    files = data.get("files", {})
    words_file = files.get("user_words.txt", {})
    words_content = words_file.get("content", "")
    user_words = [
        ln.strip()
        for ln in words_content.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]

    snip_file = files.get("snippets.json", {})
    snip_content = snip_file.get("content", "[]")
    try:
        raw_snippets = json.loads(snip_content)
        snippets = [
            {
                "trigger": str(s.get("trigger", "")).strip(),
                "replacement": str(s.get("replacement", "")),
                "enabled": bool(s.get("enabled", True)),
            }
            for s in raw_snippets
            if isinstance(s, dict) and s.get("trigger")
        ]
    except Exception:  # noqa: BLE001
        snippets = []

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "ok": True,
        "user_words": user_words,
        "snippets": snippets,
        "error": None,
        "timestamp": now_iso,
    }
