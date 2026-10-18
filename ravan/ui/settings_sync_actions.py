"""Sync actions (push/pull) for SettingsWindow."""

from __future__ import annotations

import logging
import threading
from tkinter import messagebox
from typing import Any

from ravan.core.i18n import t
from ravan.core.sync import merge_dictionaries, merge_snippets, pull_sync, push_sync

log = logging.getLogger(__name__)


def update_cfg_from_ui(win: Any) -> None:
    """Update window config from UI variables."""
    backend_val = (
        "webdav" if "webdav" in win._sync_backend_var.get().lower() else "gist"
    )
    win.cfg.sync_backend = backend_val
    if hasattr(win, "_gist_token_var"):
        win.cfg.gist_token = win._gist_token_var.get().strip()
    if hasattr(win, "_gist_id_var"):
        win.cfg.gist_id = win._gist_id_var.get().strip()
    if hasattr(win, "_webdav_url_var"):
        win.cfg.webdav_url = win._webdav_url_var.get().strip()
    if hasattr(win, "_webdav_username_var"):
        win.cfg.webdav_username = win._webdav_username_var.get().strip()
    if hasattr(win, "_webdav_password_var"):
        win.cfg.webdav_password = win._webdav_password_var.get().strip()
    if hasattr(win, "_cloud_sync_var"):
        win.cfg.cloud_sync_enabled = win._cloud_sync_var.get()
    if hasattr(win, "_sync_interval_var"):
        try:
            win.cfg.sync_interval_min = int(win._sync_interval_var.get())
        except (ValueError, TypeError):
            win.cfg.sync_interval_min = 0


def do_sync_push(win: Any) -> None:
    """Execute push sync for the configured backend."""
    update_cfg_from_ui(win)
    backend = win.cfg.sync_backend
    if backend == "gist" and (not win.cfg.gist_token or not win.cfg.gist_id):
        win._sync_status_var.set("❌ Please enter both Gist Token and Gist ID")
        return
    if backend == "webdav" and not win.cfg.webdav_url:
        win._sync_status_var.set("❌ Please enter WebDAV Server URL")
        return

    win._sync_status_var.set("⏳ Pushing to Cloud…")

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
        res = push_sync(win.cfg, user_words, snippets_data)

        def _ui() -> None:
            if not getattr(win, "_root", None):
                return
            if res.get("ok"):
                ts = res.get("timestamp", "")
                win.cfg.last_sync_time = ts
                win._last_sync_label_var.set(
                    t("settings.sync_last", "Last sync: {time}", time=ts)
                )
                win._sync_status_var.set("✅ Cloud push successful!")
            else:
                win._sync_status_var.set(
                    f"❌ Push failed: {res.get('error', 'Unknown')}"
                )

        if getattr(win, "_root", None):
            win._root.after(0, _ui)

    threading.Thread(target=_bg, name="ravan-sync-push", daemon=True).start()


def do_sync_pull(win: Any) -> None:
    """Execute pull sync with three-way merge for words and conflict prompt for snippets."""
    update_cfg_from_ui(win)
    backend = win.cfg.sync_backend
    if backend == "gist" and (not win.cfg.gist_token or not win.cfg.gist_id):
        win._sync_status_var.set("❌ Please enter both Gist Token and Gist ID")
        return
    if backend == "webdav" and not win.cfg.webdav_url:
        win._sync_status_var.set("❌ Please enter WebDAV Server URL")
        return

    win._sync_status_var.set("⏳ Pulling from Cloud…")

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
        res = pull_sync(
            win.cfg,
            current_words=current_words,
            current_snippets=current_snippets,
        )

        def _ui() -> None:
            if not getattr(win, "_root", None):
                return
            if not res.get("ok"):
                win._sync_status_var.set(
                    f"❌ Pull failed: {res.get('error', 'Unknown')}"
                )
                return

            from ravan.core.config import Snippet
            from ravan.core.sync import restore_backup
            from ravan.core.user_dict import save_user_words

            try:
                # 1. Merge words (union without duplicates)
                remote_words = res.get("user_words", [])
                merged_words = merge_dictionaries(current_words, remote_words)
                win._user_words_text.delete("1.0", "end")
                win._user_words_text.insert("1.0", "\n".join(merged_words))
                save_user_words(merged_words)

                # 2. Merge snippets with conflict check
                remote_snippets = res.get("snippets", [])
                _, conflicts = merge_snippets(
                    current_snippets, remote_snippets, resolution_strategy="keep_both"
                )

                strategy = "keep_both"
                if conflicts:
                    msg = (
                        f"Found {len(conflicts)} conflicting snippet(s) between local and remote.\n\n"
                        "Click 'Yes' to overwrite local with remote versions.\n"
                        "Click 'No' to keep both versions (remote triggers suffixed with _remote).\n"
                        "Click 'Cancel' to keep local versions."
                    )
                    choice = messagebox.askyesnocancel(
                        t("settings.sync_conflict_title", "Sync Conflict"),
                        msg,
                        parent=win._root,
                    )
                    if choice is True:
                        strategy = "remote"
                    elif choice is False:
                        strategy = "keep_both"
                    else:
                        strategy = "local"

                resolved_snippets, _ = merge_snippets(
                    current_snippets, remote_snippets, resolution_strategy=strategy
                )
                win._managed_snippets = [
                    Snippet(
                        trigger=str(s["trigger"]),
                        replacement=str(s["replacement"]),
                        enabled=bool(s.get("enabled", True)),
                    )
                    for s in resolved_snippets
                    if isinstance(s, dict) and s.get("trigger")
                ]
                win._update_snip_display()

                ts = res.get("timestamp", "")
                win.cfg.last_sync_time = ts
                win._last_sync_label_var.set(
                    t("settings.sync_last", "Last sync: {time}", time=ts)
                )
                win._sync_status_var.set(
                    f"✅ Pull successful! Merged {len(merged_words)} words & {len(win._managed_snippets)} snippets."
                )
            except Exception as exc:  # noqa: BLE001
                log.error("Failed applying pulled data: %s", exc)
                restore_backup()
                win._sync_status_var.set(
                    f"❌ Failed applying pulled data (backup restored): {exc}"
                )

        if getattr(win, "_root", None):
            win._root.after(0, _ui)

    threading.Thread(target=_bg, name="ravan-sync-pull", daemon=True).start()
