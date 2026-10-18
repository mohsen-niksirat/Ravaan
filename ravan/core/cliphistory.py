"""Clipboard history ring buffer (سابقه کلیپ‌بورد) with security & privacy hardening."""

from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from pathlib import Path

log = logging.getLogger(__name__)

PASSWORD_MANAGER_APPS = {
    "1password.exe",
    "1password",
    "bitwarden.exe",
    "bitwarden",
    "keepass.exe",
    "keepass",
    "keepassxc.exe",
    "keepassxc",
    "dashlane.exe",
    "dashlane",
    "enpass.exe",
    "enpass",
    "lastpass.exe",
    "lastpass",
    "nordpass.exe",
    "nordpass",
    "roboform.exe",
    "roboform",
    "authy.exe",
    "authy",
}

SENSITIVE_PATTERNS = [
    re.compile(r"^(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}$"),  # GitHub tokens
    re.compile(r"^github_pat_[A-Za-z0-9_]{50,}$"),
    re.compile(r"^sk_live_[A-Za-z0-9]{20,}$"),  # Stripe Live keys
    re.compile(r"^xox[baprs]-[0-9a-zA-Z-]{20,}$"),  # Slack tokens
    re.compile(r"^AKIA[0-9A-Z]{16}$"),  # AWS Access Key
    re.compile(r"^AIza[0-9A-Za-z-_]{35}$"),  # Google API key
    re.compile(r"^-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),  # Private keys
]


def is_sensitive_pattern(text: str) -> bool:
    """Return True if text resembles a password, API key, token, or private key."""
    s = text.strip()
    if not s:
        return False
    for pat in SENSITIVE_PATTERNS:
        if pat.search(s):
            return True

    # Exclude common URLs, emails, and file paths
    if s.startswith(("http://", "https://", "ftp://", "file://", "ravan://")):
        return False
    if "@" in s and "." in s.partition("@")[2] and "/" not in s and " " not in s:
        return False
    if re.match(r"^[A-Za-z]:[\\/]", s) or s.startswith(("\\\\", "/")):
        return False

    # Password-manager pattern: single-line, no whitespace, length 10..128
    # with high character-class diversity (letters, digits, symbols)
    if "\n" not in s and " " not in s and "\t" not in s and 10 <= len(s) <= 128:
        has_lower = any(c.islower() for c in s)
        has_upper = any(c.isupper() for c in s)
        has_digit = any(c.isdigit() for c in s)
        symbols = [c for c in s if not c.isalnum() and c not in ("/", ".", "-", "_", ":")]
        has_symbol = len(symbols) > 0
        diversity = sum([has_lower, has_upper, has_digit, has_symbol])
        if diversity >= 3 and has_digit and (has_symbol or (has_lower and has_upper)):
            return True

    return False


class ClipboardHistory:
    def __init__(self, maxlen: int = 50, storage_path: Path | None = None) -> None:
        self.maxlen = maxlen
        self.storage_path = storage_path
        self._items: deque[str] = deque(maxlen=maxlen)
        self._pinned: list[str] = []
        self._timestamps: dict[str, float] = {}
        self._last_seen: str | None = None
        if self.storage_path is not None:
            self.load()

    def prune_expired(self, retention_days: int = 7) -> int:
        """Remove unpinned items older than retention_days. Returns count of pruned items."""
        if retention_days <= 0:
            return 0
        cutoff = time.time() - (retention_days * 86400)
        pruned = 0
        for item in list(self._items):
            if item in self._pinned:
                continue
            ts = self._timestamps.get(item, time.time())
            if ts < cutoff:
                try:
                    self._items.remove(item)
                    self._timestamps.pop(item, None)
                    pruned += 1
                except ValueError:
                    pass
        if pruned:
            self.save()
        return pruned

    def add(
        self,
        text: str | None,
        source_app: str | None = None,
        ignore_passwords: bool = True,
        excluded_apps: list[str] | None = None,
        retention_days: int = 7,
    ) -> bool:
        """Add text to history if valid, non-sensitive, and not a duplicate of top."""
        if not text:
            return False
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.startswith("__ravan_"):
            return False
        if stripped == self._last_seen:
            return False

        if ignore_passwords:
            # Check source app
            if source_app:
                app_clean = Path(source_app).name.lower()
                if app_clean in PASSWORD_MANAGER_APPS:
                    log.debug("Ignored clipboard item from password manager: %s", app_clean)
                    return False
                if excluded_apps and any(
                    app_clean == x.lower() or app_clean.endswith(x.lower())
                    for x in excluded_apps
                ):
                    log.debug("Ignored clipboard item from excluded app: %s", app_clean)
                    return False

            # Check sensitive password/token pattern
            if is_sensitive_pattern(stripped):
                log.debug("Ignored clipboard item matching sensitive / password pattern")
                return False

        # Auto-expire older items
        if retention_days > 0:
            self.prune_expired(retention_days)

        self._last_seen = stripped
        try:
            self._items.remove(stripped)
        except ValueError:
            pass

        self._items.appendleft(stripped)
        self._timestamps[stripped] = time.time()
        self.save()
        return True

    def toggle_pin(self, text: str) -> bool:
        clean = text.strip()
        if clean in self._pinned:
            self._pinned.remove(clean)
            self.save()
            return False
        else:
            self._pinned.append(clean)
            self.save()
            return True

    def is_pinned(self, text: str) -> bool:
        return text.strip() in self._pinned

    def items(self) -> list[str]:
        unpinned = [it for it in self._items if it not in self._pinned]
        return [*self._pinned, *unpinned]

    def clear(self) -> None:
        self._items.clear()
        self._pinned.clear()
        self._timestamps.clear()
        self._last_seen = None
        self.save()

    def __len__(self) -> int:
        return len(self.items())

    def save(self) -> None:
        if self.storage_path is None:
            return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "pinned": self._pinned,
                "items": list(self._items),
                "timestamps": self._timestamps,
            }
            tmp = self.storage_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(self.storage_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to save clipboard history: %s", exc)

    def load(self) -> None:
        if self.storage_path is None or not self.storage_path.is_file():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._pinned = [
                    str(x) for x in data.get("pinned", []) if str(x).strip()
                ]
                loaded_items = [
                    str(x) for x in data.get("items", []) if str(x).strip()
                ]
                raw_ts = data.get("timestamps", {})
                now = time.time()
                self._timestamps = {
                    str(k): float(v)
                    for k, v in raw_ts.items()
                    if isinstance(v, (int, float))
                }
                self._items.clear()
                for it in reversed(loaded_items[: self.maxlen]):
                    self._items.appendleft(it)
                    if it not in self._timestamps:
                        self._timestamps[it] = now
                if self._items:
                    self._last_seen = self._items[0]
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load clipboard history: %s", exc)
