"""WebDAV sync client for Nextcloud, ownCloud, and generic WebDAV servers."""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from ravan.core.sync import _sanitize_error, make_local_backup

log = logging.getLogger(__name__)


class WebDAVClient:
    """Client for pushing and pulling user data via WebDAV."""

    def __init__(self, url: str, username: str = "", password: str = "") -> None:
        self.url = url.strip().rstrip("/")
        self.username = username.strip()
        self.password = password.strip()

    def _get_auth_header(self) -> str:
        if not self.username and not self.password:
            return ""
        user_pass = f"{self.username}:{self.password}"
        encoded = base64.b64encode(user_pass.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    def push(
        self,
        user_words: list[str],
        snippets: list[dict[str, Any]],
        timeout: float = 8.0,
    ) -> dict[str, Any]:
        """Push user words and snippets to WebDAV server."""
        if not self.url:
            return {"ok": False, "error": "Missing WebDAV server URL"}

        make_local_backup(user_words, snippets)

        headers = {"User-Agent": "Ravaan-App"}
        auth = self._get_auth_header()
        if auth:
            headers["Authorization"] = auth

        words_content = ("\n".join(user_words) + ("\n" if user_words else "")).encode("utf-8")
        snip_content = json.dumps(snippets, ensure_ascii=False, indent=2).encode("utf-8")

        for filename, data in (
            ("user_words.txt", words_content),
            ("snippets.json", snip_content),
        ):
            target_url = f"{self.url}/{filename}"
            req = urllib.request.Request(
                target_url,
                data=data,
                headers={**headers, "Content-Type": "application/octet-stream"},
                method="PUT",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status not in (200, 201, 204):
                        return {"ok": False, "error": f"HTTP {resp.status} on {filename}"}
            except urllib.error.HTTPError as err:
                return {
                    "ok": False,
                    "error": _sanitize_error(f"HTTP {err.code}: {err.reason}", self.password),
                }
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": _sanitize_error(str(exc), self.password)}

        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {"ok": True, "error": None, "timestamp": now_iso}

    def pull(
        self,
        timeout: float = 8.0,
        current_words: list[str] | None = None,
        current_snippets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Pull user words and snippets from WebDAV server."""
        if not self.url:
            return {"ok": False, "error": "Missing WebDAV server URL"}

        try:
            make_local_backup(user_words=current_words, snippets=current_snippets)
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not create local pre-pull backup: %s", exc)

        headers = {"User-Agent": "Ravaan-App"}
        auth = self._get_auth_header()
        if auth:
            headers["Authorization"] = auth

        words: list[str] = []
        snippets: list[dict[str, Any]] = []

        # 1. Fetch user_words.txt
        words_url = f"{self.url}/user_words.txt"
        req = urllib.request.Request(words_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    text = resp.read().decode("utf-8")
                    words = [
                        ln.strip()
                        for ln in text.splitlines()
                        if ln.strip() and not ln.strip().startswith("#")
                    ]
        except urllib.error.HTTPError as err:
            if err.code != 404:
                return {
                    "ok": False,
                    "error": _sanitize_error(f"HTTP {err.code}: {err.reason}", self.password),
                }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": _sanitize_error(str(exc), self.password)}

        # 2. Fetch snippets.json
        snip_url = f"{self.url}/snippets.json"
        req = urllib.request.Request(snip_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw = json.loads(resp.read().decode("utf-8"))
                    snippets = [
                        {
                            "trigger": str(s.get("trigger", "")).strip(),
                            "replacement": str(s.get("replacement", "")),
                            "enabled": bool(s.get("enabled", True)),
                        }
                        for s in raw
                        if isinstance(s, dict) and s.get("trigger")
                    ]
        except urllib.error.HTTPError as err:
            if err.code != 404:
                return {
                    "ok": False,
                    "error": _sanitize_error(f"HTTP {err.code}: {err.reason}", self.password),
                }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": _sanitize_error(str(exc), self.password)}

        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "ok": True,
            "user_words": words,
            "snippets": snippets,
            "error": None,
            "timestamp": now_iso,
        }
