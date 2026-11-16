"""Tests for Phase 4 Ravaan Hub registry, SHA-256 verification, install/update/uninstall & UI."""

from __future__ import annotations

import hashlib
import io
import json
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ravan.core.config import Config, Snippet
from ravan.core.hub import (
    BUILTIN_HUB_PACKS,
    HUB_CATEGORIES,
    HubManager,
    HubPack,
    is_newer_version,
)
from ravan.core.i18n import set_locale
from ravan.core.package import PackageIntegrityError, export_package
from ravan.ui.hub_browser import RavaanHubPanel
from ravan.ui.hub_preview_modal import open_hub_preview_modal
from ravan.ui.theme import create_managed_toplevel, destroy_managed_toplevel


def test_hub_categories_and_semver_comparison() -> None:
    cats = {cid for cid, _fa, _en in HUB_CATEGORIES}
    assert {"all", "official", "coding", "medical_legal", "proverbs"} <= cats
    builtin_cats = {p.category for p in BUILTIN_HUB_PACKS}
    assert builtin_cats == {"official", "coding", "medical_legal", "proverbs"}
    assert is_newer_version("1.2.0", "1.1.9") is True
    assert is_newer_version("2.0.0", "1.99.0") is True
    assert is_newer_version("1.2.0", "1.2.0") is False


def test_hub_fetch_index_caches_and_falls_back(tmp_path: Path) -> None:
    mgr = HubManager(base_dir=tmp_path)
    remote_payload = {
        "packs": [
            {
                "pack_id": "custom-remote-pack",
                "version": "1.0.0",
                "category": "coding",
                "title_en": "Remote Coding Pack",
                "title_fa": "بسته کدنویسی ریموت",
                "description_en": "Remote snippets",
                "description_fa": "قطعات کد ریموت",
                "author": "Tester",
                "download_url": "https://example.com/remote.ravaanpack",
                "sha256": "deadbeef",
                "snippet_count": 2,
                "preview_items": [[";rem", "remote snippet"]],
            }
        ]
    }
    raw = json.dumps(remote_payload).encode("utf-8")
    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(raw)):
        packs = mgr.fetch_index(force_refresh=True)
    assert len(packs) == 1
    assert packs[0].pack_id == "custom-remote-pack"
    assert mgr.cache_path.is_file()

    # Subsequent non-forced call reads cache without calling urlopen
    with patch.object(urllib.request, "urlopen", side_effect=AssertionError("must use cache")):
        cached_packs = mgr.fetch_index(force_refresh=False)
    assert len(cached_packs) == 1
    assert cached_packs[0].pack_id == "custom-remote-pack"

    # Forced refresh on network failure safely falls back to built-in packs
    with patch.object(urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
        fallback = mgr.fetch_index(force_refresh=True)
    assert len(fallback) == len(BUILTIN_HUB_PACKS)


def test_hub_remote_sha256_verification_and_tamper_rejection(tmp_path: Path) -> None:
    src_pack = tmp_path / "src.ravaanpack"
    export_package([Snippet(trigger=";hubok", replacement="verified value")], src_pack, name="Verified Pack")
    pack_bytes = src_pack.read_bytes()
    good_sha = hashlib.sha256(pack_bytes).hexdigest()

    mgr = HubManager(base_dir=tmp_path / "hub")
    bad_pack = HubPack(
        pack_id="tampered-pack", version="1.0.0", category="coding",
        title_en="Bad", title_fa="بد", description_en="", description_fa="",
        author="X", download_url="https://example.com/tampered.ravaanpack",
        sha256="0" * 64, snippet_count=1,
    )
    with (
        patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(pack_bytes)),
        pytest.raises(PackageIntegrityError),
    ):
        mgr.install_pack(bad_pack, [])
    assert not (mgr.packs_dir / "tampered-pack.ravaanpack.part").exists()
    assert mgr.is_installed("tampered-pack") is False

    # Reject insecure plain http://
    http_pack = HubPack(
        pack_id="insecure-pack", version="1.0.0", category="coding",
        title_en="HTTP", title_fa="HTTP", description_en="", description_fa="",
        author="X", download_url="http://example.com/bad.ravaanpack",
        sha256=good_sha, snippet_count=1,
    )
    with pytest.raises(ValueError, match="Unsafe Hub download scheme"):
        mgr.install_pack(http_pack, [])

    # Accept valid HTTPS pack with exact SHA-256
    good_pack = HubPack(
        pack_id="valid-remote", version="1.0.0", category="coding",
        title_en="Valid", title_fa="معتبر", description_en="", description_fa="",
        author="X", download_url="https://example.com/valid.ravaanpack",
        sha256=good_sha, snippet_count=1,
    )
    user_existing = [Snippet(trigger=";mine", replacement="keep me")]
    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(pack_bytes)):
        snips, _groups, manifest = mgr.install_pack(good_pack, user_existing)
    assert manifest["name"] == "Verified Pack"
    assert mgr.is_installed("valid-remote") is True
    assert {s.trigger for s in snips} == {";mine", ";hubok"}


def test_hub_builtin_install_update_and_uninstall_preserves_custom_snippets(tmp_path: Path) -> None:
    mgr = HubManager(base_dir=tmp_path / "hub")
    pack = BUILTIN_HUB_PACKS[0]
    existing = [Snippet(trigger=";custom", replacement="user own snippet")]

    snips, groups, _m = mgr.install_pack(pack, existing)
    assert mgr.is_installed(pack.pack_id) is True
    assert any(s.trigger == ";bism" for s in snips)
    assert any(s.trigger == ";custom" for s in snips)
    assert any(g.id == pack.category for g in groups)

    # Simulate newer remote version notification
    newer_pack = HubPack(
        **{**pack.__dict__, "version": "9.9.0"}  # type: ignore[arg-type]
    )
    assert mgr.has_update(newer_pack) is True

    after_uninstall = mgr.uninstall_pack(pack.pack_id, snips)
    assert mgr.is_installed(pack.pack_id) is False
    assert [s.trigger for s in after_uninstall] == [";custom"]


def test_hub_browser_ui_filtering_install_and_preview(tmp_path: Path) -> None:
    try:
        top, owned_root = create_managed_toplevel(None)
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display unavailable: {exc}")

    set_locale("en")
    mgr = HubManager(base_dir=tmp_path / "hub_ui")
    win_stub = SimpleNamespace(
        _root=top,
        cfg=Config(),
        _managed_snippets=[Snippet(trigger=";local", replacement="stay")],
        _update_snip_display=lambda: None,
    )
    panel = RavaanHubPanel(top, win_stub, manager=mgr)
    try:
        assert len(panel.filtered_packs()) == len(BUILTIN_HUB_PACKS)
        panel.select_category("coding")
        coding_filtered = panel.filtered_packs()
        assert coding_filtered and all(p.category == "coding" for p in coding_filtered)

        panel.select_category("all")
        panel._search_entry.set("medical")
        assert [p.category for p in panel.filtered_packs()] == ["medical_legal"]
        panel._search_entry.clear()

        modal = open_hub_preview_modal(
            top, BUILTIN_HUB_PACKS[1], installed=False, has_update=False,
            on_install=lambda _p: None, on_uninstall=lambda _p: None, theme_mode="dark",
        )
        modal.update_idletasks()
        modal.destroy()

        # Verify synchronous uninstall path after install_pack
        new_s, new_g, _m = mgr.install_pack(BUILTIN_HUB_PACKS[0], win_stub._managed_snippets)
        win_stub._managed_snippets = new_s
        win_stub.cfg.snippet_groups = new_g
        panel.uninstall_pack(BUILTIN_HUB_PACKS[0])
        assert [s.trigger for s in win_stub._managed_snippets] == [";local"]
    finally:
        destroy_managed_toplevel(top, owned_root)


def test_phase4_modules_respect_line_ceiling() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    for rel in (
        "ravan/core/hub.py",
        "ravan/ui/hub_browser.py",
        "ravan/ui/hub_preview_modal.py",
        "ravan/ui/settings_tabs_misc.py",
    ):
        lines = len((repo_root / rel).read_text(encoding="utf-8").splitlines())
        assert lines <= 400, f"{rel} has {lines} lines (exceeds 400-line ceiling)"
