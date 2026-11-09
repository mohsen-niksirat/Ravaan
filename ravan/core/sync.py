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


def _sanitize_error(err_str: str, token: str) -> str:
    """Ensure sensitive tokens never appear in error strings or logs."""
    tok = token.strip()
    if tok and len(tok) >= 6 and tok in err_str:
        return err_str.replace(tok, "[REDACTED_TOKEN]")
    return err_str


def snippet_to_dict(s: Any) -> dict[str, Any]:
    """Serialize a Snippet dataclass or dict preserving all Snippets 3.0 metadata.

    Omits optional Snippets 3.0 keys when they match their empty/False defaults
    (unless already present on an input dict) so minimal v1/v2 snippet payloads
    stay compact and backward-compatible.
    """
    if isinstance(s, dict):
        out: dict[str, Any] = {
            **s,
            "trigger": str(s.get("trigger", "")).strip(),
            "replacement": str(s.get("replacement", "")),
            "enabled": bool(s.get("enabled", True)),
        }
        if "is_regex" in s or s.get("is_regex"):
            out["is_regex"] = bool(s.get("is_regex", False))
        if "app_filter" in s or s.get("app_filter"):
            out["app_filter"] = str(s.get("app_filter", ""))
        if "is_image" in s or s.get("is_image"):
            out["is_image"] = bool(s.get("is_image", False))
        if "groups" in s or s.get("groups"):
            raw_groups = s.get("groups", [])
            out["groups"] = (
                [str(g) for g in raw_groups if str(g).strip()]
                if isinstance(raw_groups, list)
                else []
            )
        return out

    out = {
        "trigger": str(getattr(s, "trigger", "")).strip(),
        "replacement": str(getattr(s, "replacement", "")),
        "enabled": bool(getattr(s, "enabled", True)),
    }
    if getattr(s, "is_regex", False):
        out["is_regex"] = True
    app_filter = str(getattr(s, "app_filter", "") or "")
    if app_filter:
        out["app_filter"] = app_filter
    if getattr(s, "is_image", False):
        out["is_image"] = True
    groups = [str(g) for g in (getattr(s, "groups", None) or []) if str(g).strip()]
    if groups:
        out["groups"] = groups
    return out


def dict_to_snippet(s: dict[str, Any]) -> Any:
    """Deserialize a dict into a Snippet dataclass with full Snippets 3.0 metadata."""
    from ravan.core.config import Snippet

    norm = snippet_to_dict(s)
    return Snippet(
        trigger=norm["trigger"],
        replacement=norm["replacement"],
        enabled=norm["enabled"],
        is_regex=bool(norm.get("is_regex", False)),
        app_filter=str(norm.get("app_filter", "")),
        is_image=bool(norm.get("is_image", False)),
        groups=list(norm.get("groups", [])),
    )


def make_local_backup(
    user_words: list[str] | None = None,
    snippets: list[dict[str, Any]] | None = None,
) -> Path:
    """Create a local snapshot backup before performing push or pull sync."""
    backup_dir = config_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"sync_backup_{ts}.json"

    words_to_save: list[str] = []
    if user_words is not None:
        words_to_save = list(user_words)
    else:
        from ravan.core.user_dict import load_user_words

        words_to_save = load_user_words()

    snips_to_save: list[dict[str, Any]] = []
    if snippets is not None:
        snips_to_save = [
            snippet_to_dict(s)
            for s in snippets
            if (isinstance(s, dict) and s.get("trigger")) or getattr(s, "trigger", "")
        ]
    else:
        from ravan.core.config import load_config

        cfg = load_config()
        snips_to_save = [snippet_to_dict(s) for s in cfg.snippets]


    data = {
        "timestamp": datetime.now().isoformat(),
        "user_words": words_to_save,
        "snippets": snips_to_save,
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


def restore_backup(
    backup_file: Path | None = None,
) -> tuple[list[str], list[dict[str, Any]]] | None:
    """Restore user words and snippets from a backup file (or latest if None)."""
    backup_dir = config_dir() / "backups"
    if backup_file is None:
        all_backups = sorted(
            backup_dir.glob("sync_backup_*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if not all_backups:
            return None
        backup_file = all_backups[-1]

    if not backup_file.is_file():
        return None

    try:
        data = json.loads(backup_file.read_text(encoding="utf-8"))
        words = list(data.get("user_words", []))
        snips = list(data.get("snippets", []))
        from ravan.core.config import load_config, save_config
        from ravan.core.user_dict import save_user_words

        save_user_words(words)
        cfg = load_config()
        cfg.snippets = [
            dict_to_snippet(s)
            for s in snips
            if isinstance(s, dict) and str(s.get("trigger", "")).strip()
        ]

        save_config(cfg)
        return words, snips
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to restore backup from %s: %s", backup_file, exc)
        return None


def push_to_gist(
    token: str,
    gist_id: str,
    user_words: list[str],
    snippets: list[dict[str, Any]],
    timeout: float = 8.0,
    learning_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Push local user words, snippets, and optional learning profile to GitHub Gist."""
    tok = token.strip()
    gid = gist_id.strip()
    if not tok or not gid:
        return {"ok": False, "error": "Missing Gist Personal Access Token or Gist ID"}

    make_local_backup(user_words, snippets)

    payload_files = {
        "user_words.txt": {
            "content": "\n".join(user_words) + ("\n" if user_words else "")
        },
        "snippets.json": {
            "content": json.dumps(snippets, ensure_ascii=False, indent=2)
        },
    }
    if learning_profile is not None:
        payload_files["learning_profile.json"] = {
            "content": json.dumps(learning_profile, ensure_ascii=False, indent=2)
        }

    payload = {
        "description": "Ravaan Sync — User dictionary and snippets",
        "files": payload_files,
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
        return {"ok": False, "error": _sanitize_error(f"HTTP {err.code}: {err.reason}", tok)}
    except urllib.error.URLError as err:
        return {"ok": False, "error": _sanitize_error(f"Network error: {err.reason}", tok)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _sanitize_error(str(exc), tok)}


def pull_from_gist(
    token: str,
    gist_id: str,
    timeout: float = 8.0,
    current_words: list[str] | None = None,
    current_snippets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pull user words and snippets from GitHub Gist."""
    tok = token.strip()
    gid = gist_id.strip()
    if not tok or not gid:
        return {"ok": False, "error": "Missing Gist Personal Access Token or Gist ID"}

    # Automatically snapshot current state before pulling
    try:
        make_local_backup(user_words=current_words, snippets=current_snippets)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not create local pre-pull backup: %s", exc)

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
        return {"ok": False, "error": _sanitize_error(f"HTTP {err.code}: {err.reason}", tok)}
    except urllib.error.URLError as err:
        return {"ok": False, "error": _sanitize_error(f"Network error: {err.reason}", tok)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _sanitize_error(str(exc), tok)}

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
            snippet_to_dict(s)
            for s in raw_snippets
            if isinstance(s, dict) and str(s.get("trigger", "")).strip()
        ]
    except Exception:  # noqa: BLE001
        snippets = []

    learning_profile = None
    if "learning_profile.json" in files:
        try:
            learning_profile = json.loads(files["learning_profile.json"].get("content", "{}"))
        except Exception:  # noqa: BLE001
            pass

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "ok": True,
        "user_words": user_words,
        "snippets": snippets,
        "learning_profile": learning_profile,
        "error": None,
        "timestamp": now_iso,
    }


def merge_dictionaries(local_words: list[str], remote_words: list[str]) -> list[str]:
    """Union merge local and remote words preserving original casing without duplicates."""
    seen: set[str] = set()
    merged: list[str] = []
    for w in list(local_words) + list(remote_words):
        clean = w.strip()
        if not clean or clean.startswith("#"):
            continue
        key = clean.lower()
        if key not in seen:
            seen.add(key)
            merged.append(clean)
    return merged


def merge_snippets(
    local_snippets: list[dict[str, Any]],
    remote_snippets: list[dict[str, Any]],
    resolution_strategy: str = "keep_both",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge local and remote snippets. Detect conflicts where replacement differs."""
    merged: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []

    for s in local_snippets:
        trig = str(s.get("trigger", "")).strip()
        if trig:
            merged[trig] = dict(s)

    for s in remote_snippets:
        trig = str(s.get("trigger", "")).strip()
        if not trig:
            continue
        if trig not in merged:
            merged[trig] = dict(s)
        else:
            loc = merged[trig]
            if loc.get("replacement", "") != s.get("replacement", ""):
                conflicts.append({"trigger": trig, "local": loc, "remote": s})
                if resolution_strategy == "remote":
                    merged[trig] = dict(s)
                elif resolution_strategy == "keep_both":
                    remote_key = f"{trig}_remote"
                    merged[remote_key] = {**dict(s), "trigger": remote_key}

    return list(merged.values()), conflicts


def push_sync(
    cfg: Any,
    user_words: list[str],
    snippets: list[dict[str, Any]],
    timeout: float = 8.0,
    learning_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch push to configured sync backend (gist or webdav)."""
    if learning_profile is None and getattr(cfg, "sync_learning_profile", False):
        try:
            from ravan.core.learning import UserLearningEngine

            learning_profile = UserLearningEngine().export_profile()
        except Exception:  # noqa: BLE001
            learning_profile = None

    backend = getattr(cfg, "sync_backend", "gist").lower()
    if backend == "webdav":
        from ravan.core.webdav import WebDAVClient

        client = WebDAVClient(
            url=getattr(cfg, "webdav_url", ""),
            username=getattr(cfg, "webdav_username", ""),
            password=getattr(cfg, "webdav_password", ""),
        )
        return client.push(
            user_words, snippets, timeout=timeout, learning_profile=learning_profile
        )

    return push_to_gist(
        token=getattr(cfg, "gist_token", ""),
        gist_id=getattr(cfg, "gist_id", ""),
        user_words=user_words,
        snippets=snippets,
        timeout=timeout,
        learning_profile=learning_profile,
    )


def pull_sync(
    cfg: Any,
    timeout: float = 8.0,
    current_words: list[str] | None = None,
    current_snippets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Dispatch pull to configured sync backend (gist or webdav)."""
    backend = getattr(cfg, "sync_backend", "gist").lower()
    if backend == "webdav":
        from ravan.core.webdav import WebDAVClient

        client = WebDAVClient(
            url=getattr(cfg, "webdav_url", ""),
            username=getattr(cfg, "webdav_username", ""),
            password=getattr(cfg, "webdav_password", ""),
        )
        return client.pull(
            timeout=timeout,
            current_words=current_words,
            current_snippets=current_snippets,
        )

    return pull_from_gist(
        token=getattr(cfg, "gist_token", ""),
        gist_id=getattr(cfg, "gist_id", ""),
        timeout=timeout,
        current_words=current_words,
        current_snippets=current_snippets,
    )
