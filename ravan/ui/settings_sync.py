"""Background sync actions for SettingsWindow (Push/Pull to GitHub Gist)."""

from __future__ import annotations

import logging
import threading
from typing import Any

from ravan.core.sync import pull_from_gist, push_to_gist

log = logging.getLogger(__name__)


def do_sync_push(win: Any) -> None:
    token = win._gist_token_var.get().strip()
    gist_id = win._gist_id_var.get().strip()
    if not token or not gist_id:
        win._sync_status_var.set("❌ Please enter both Gist Token and Gist ID")
        return

    win._sync_status_var.set("⏳ Pushing to Gist…")

    user_words = [
        ln.strip()
        for ln in win._user_words_text.get("1.0", "end").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    snippets_data = [
        {"trigger": s.trigger, "replacement": s.replacement, "enabled": s.enabled}
        for s in win._managed_snippets
    ]

    def _bg() -> None:
        res = push_to_gist(token, gist_id, user_words, snippets_data)

        def _ui() -> None:
            if not win._root:
                return
            if res["ok"]:
                ts = res.get("timestamp", "")
                win.cfg.last_sync_time = ts
                win.cfg.gist_token = token
                win.cfg.gist_id = gist_id
                win._last_sync_label_var.set(f"Last sync: {ts}")
                win._sync_status_var.set("✅ Push to Gist successful!")
            else:
                win._sync_status_var.set(f"❌ Push failed: {res.get('error', 'Unknown')}")

        if win._root:
            win._root.after(0, _ui)

    threading.Thread(target=_bg, name="ravan-sync-push", daemon=True).start()


def do_sync_pull(win: Any) -> None:
    token = win._gist_token_var.get().strip()
    gist_id = win._gist_id_var.get().strip()
    if not token or not gist_id:
        win._sync_status_var.set("❌ Please enter both Gist Token and Gist ID")
        return

    win._sync_status_var.set("⏳ Pulling from Gist…")

    current_words = [
        ln.strip()
        for ln in win._user_words_text.get("1.0", "end").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    current_snippets = [
        {"trigger": s.trigger, "replacement": s.replacement, "enabled": s.enabled}
        for s in win._managed_snippets
    ]

    def _bg() -> None:
        res = pull_from_gist(
            token,
            gist_id,
            current_words=current_words,
            current_snippets=current_snippets,
        )

        def _ui() -> None:
            if not win._root:
                return
            if res["ok"]:
                from ravan.core.config import Snippet
                from ravan.core.sync import restore_backup
                from ravan.core.user_dict import save_user_words

                try:
                    words = res.get("user_words", [])
                    win._user_words_text.delete("1.0", "end")
                    win._user_words_text.insert("1.0", "\n".join(words))
                    save_user_words(words)

                    raw_snippets = res.get("snippets", [])
                    win._managed_snippets = [
                        Snippet(
                            trigger=s["trigger"],
                            replacement=s["replacement"],
                            enabled=s.get("enabled", True),
                        )
                        for s in raw_snippets
                    ]
                    win._update_snip_display()

                    ts = res.get("timestamp", "")
                    win.cfg.last_sync_time = ts
                    win.cfg.gist_token = token
                    win.cfg.gist_id = gist_id
                    win._last_sync_label_var.set(f"Last sync: {ts}")
                    win._sync_status_var.set("✅ Pull from Gist successful! Words and snippets updated.")
                except Exception as exc:  # noqa: BLE001
                    log.error("Failed applying pulled data; restoring backup: %s", exc)
                    restore_backup()
                    win._sync_status_var.set(f"❌ Failed to apply pulled data (restored backup): {exc}")
            else:
                win._sync_status_var.set(f"❌ Pull failed: {res.get('error', 'Unknown')}")

        if win._root:
            win._root.after(0, _ui)

    threading.Thread(target=_bg, name="ravan-sync-pull", daemon=True).start()
