"""In-app update dialog with changelog summary and one-click download & install."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.core.updater import download_and_launch_installer

log = logging.getLogger(__name__)


class UpdateDialog:
    """Non-blocking dialog presenting release info and one-click installer."""

    def __init__(
        self,
        release_info: dict[str, Any],
        on_ready_to_exit: Callable[[], None] | None = None,
        parent: tk.Tk | tk.Toplevel | None = None,
    ) -> None:
        self.info = release_info
        self.on_ready_to_exit = on_ready_to_exit
        self.parent = parent
        self._root: tk.Toplevel | None = None

    def show(self) -> None:
        self._root = tk.Toplevel(self.parent)
        self._root.title(
            t(
                "updater.title",
                "Ravaan Update — v{version}",
                version=self.info["latest_version"],
            )
        )
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)

        rtl = is_rtl()
        align = "e" if rtl else "w"
        pack_side = "right" if rtl else "left"

        frm = ttk.Frame(self._root, padding=16)
        frm.pack(fill="both", expand=True)

        # Header
        ttk.Label(
            frm,
            text=t(
                "updater.header",
                "A new version of Ravaan is available!",
            ),
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=align, pady=(0, 4))

        version_str = f"v{self.info['current_version']}  ➔  v{self.info['latest_version']}"
        ttk.Label(
            frm,
            text=version_str,
            font=("Segoe UI", 10),
            foreground="#1a73e8",
        ).pack(anchor=align, pady=(0, 8))

        # Changelog summary
        ttk.Label(
            frm,
            text=t("updater.changelog_label", "What's New:"),
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=align, pady=(4, 2))

        txt = tk.Text(frm, width=48, height=6, wrap="word", relief="groove")
        txt.insert("1.0", self.info.get("changelog_summary", ""))
        txt.config(state="disabled")
        txt.pack(fill="x", pady=(0, 10))

        # Progress bar (initially hidden)
        progress_var = tk.DoubleVar(value=0.0)
        progress_bar = ttk.Progressbar(
            frm, variable=progress_var, maximum=1.0, mode="determinate"
        )
        status_var = tk.StringVar(value="")
        status_label = ttk.Label(frm, textvariable=status_var, foreground="#555555")

        # Buttons
        btn_bar = ttk.Frame(frm)
        btn_bar.pack(fill="x", pady=(4, 0))

        def _on_download() -> None:
            installer_url = self.info.get("installer_url")
            if not installer_url:
                webbrowser.open(self.info.get("release_url", ""))
                self._root.destroy()
                return

            download_btn.config(state="disabled")
            status_label.pack(fill="x", pady=(0, 4))
            progress_bar.pack(fill="x", pady=(0, 8))
            status_var.set(t("updater.downloading", "Downloading installer…"))

            def _progress(pct: float) -> None:
                def _ui() -> None:
                    progress_var.set(pct)
                    status_var.set(
                        t(
                            "updater.download_pct",
                            "Downloading installer… {pct}%",
                            pct=int(pct * 100),
                        )
                    )

                if self._root:
                    self._root.after(0, _ui)

            def _bg() -> None:
                success = download_and_launch_installer(
                    download_url=installer_url,
                    installer_name=self.info.get("installer_name"),
                    on_progress=_progress,
                    on_ready_to_exit=self.on_ready_to_exit,
                )
                if not success:

                    def _err_ui() -> None:
                        status_var.set(
                            t("updater.download_err", "Download failed. Opening browser…")
                        )
                        webbrowser.open(self.info.get("release_url", ""))

                    if self._root:
                        self._root.after(0, _err_ui)

            threading.Thread(target=_bg, name="ravan-installer-dl", daemon=True).start()

        download_btn = ttk.Button(
            btn_bar,
            text=t("updater.btn_install", "⬇ Download & Install"),
            command=_on_download,
        )
        download_btn.pack(side=pack_side, padx=(0, 6) if not rtl else (6, 0))

        ttk.Button(
            btn_bar,
            text=t("updater.btn_browser", "🌐 View on GitHub"),
            command=lambda: (
                webbrowser.open(self.info.get("release_url", "")),
                self._root.destroy(),
            ),
        ).pack(side=pack_side, padx=4)

        ttk.Button(
            btn_bar,
            text=t("updater.btn_later", "Later"),
            command=self._root.destroy,
        ).pack(side="left" if rtl else "right", padx=4)

        self._root.update_idletasks()
        w = self._root.winfo_reqwidth()
        h = self._root.winfo_reqheight()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = max(20, (sw - w) // 2)
        y = max(20, (sh - h) // 3)
        self._root.geometry(f"+{x}+{y}")
        self._root.deiconify()
