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
        if self.url.lower().startswith("http://"):
            log.warning(
                "Security Warning: WebDAV server URL %s uses unencrypted HTTP. "
                "Credentials and dictionary data will be transmitted in plaintext! "
                "HTTPS is strongly recommended.",
                self.url,
            )

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
        learning_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Push user words, snippets, and optional learning profile to WebDAV server."""
        if not self.url:
            return {"ok": False, "error": "Missing WebDAV server URL"}

        make_local_backup(user_words, snippets)

        headers = {"User-Agent": "Ravaan-App"}
        auth = self._get_auth_header()
        if auth:
            headers["Authorization"] = auth

        words_content = ("\n".join(user_words) + ("\n" if user_words else "")).encode("utf-8")
        snip_content = json.dumps(snippets, ensure_ascii=False, indent=2).encode("utf-8")

        items_to_push: list[tuple[str, bytes]] = [
            ("user_words.txt", words_content),
            ("snippets.json", snip_content),
        ]
        if learning_profile is not None:
            learn_bytes = json.dumps(learning_profile, ensure_ascii=False, indent=2).encode("utf-8")
            items_to_push.append(("learning_profile.json", learn_bytes))

        for filename, data in items_to_push:
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
                            **s,
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

        # 3. Fetch optional learning_profile.json
        learning_profile: dict[str, Any] | None = None
        learn_url = f"{self.url}/learning_profile.json"
        req = urllib.request.Request(learn_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw_learn = json.loads(resp.read().decode("utf-8"))
                    if isinstance(raw_learn, dict):
                        learning_profile = raw_learn
        except urllib.error.HTTPError as err:
            if err.code != 404:
                return {
                    "ok": False,
                    "error": _sanitize_error(f"HTTP {err.code}: {err.reason}", self.password),
                }
        except Exception:  # noqa: BLE001
            learning_profile = None

        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "ok": True,
            "user_words": words,
            "snippets": snippets,
            "learning_profile": learning_profile,
            "error": None,
            "timestamp": now_iso,
        }
