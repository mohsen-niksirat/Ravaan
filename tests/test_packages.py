"""Comprehensive tests for .ravaanpack package format, integrity verification, and import/export."""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from ravan.core.config import Snippet
from ravan.core.config_types import SnippetGroup
from ravan.core.package import (
    PackageIntegrityError,
    detect_package_collisions,
    export_package,
    extract_package_groups,
    import_package,
    inspect_package,
)


def test_package_roundtrip_with_all_snippet_types():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pack_file = tmp_path / "comprehensive.ravaanpack"

        # Create dummy image
        img_file = tmp_path / "avatar.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRheader_content_sample")

        snippets = [
            Snippet(trigger=";hi", replacement="Hello world!"),
            Snippet(trigger=";img", replacement=f"image:{img_file}", is_image=True),
            Snippet(trigger=r"re:;order(\d+)", replacement="Order ID #$1", is_regex=True),
            Snippet(trigger=";form", replacement="Contact: [[name]] <[[email]]>"),
        ]

        groups = [
            SnippetGroup(id="browser_grp", name="Browsers", matchers=["chrome.exe", "msedge.exe"]),
            SnippetGroup(id="editor_grp", name="Editors", matchers=["code.exe"]),
        ]

        # Export package
        manifest = export_package(
            snippets=snippets,
            output_path=pack_file,
            name="Super Pack",
            author="Mohsen",
            description_en="All-in-one bundle",
            description_fa="بسته جامع",
            groups=groups,
        )

        assert pack_file.is_file()
        assert manifest["snippet_count"] == 4
        assert len(manifest["groups"]) == 2

        # Inspect package
        inspected = inspect_package(pack_file)
        assert inspected["name"] == "Super Pack"
        assert len(inspected["snippets"]) == 4

        # Extract groups
        extracted_groups = extract_package_groups(inspected)
        assert len(extracted_groups) == 2
        assert extracted_groups[0].id == "browser_grp"
        assert extracted_groups[0].matchers == ["chrome.exe", "msedge.exe"]

        # Import package
        extract_dir = tmp_path / "imported_images"
        imported = import_package(pack_file, image_dest_dir=extract_dir)

        assert len(imported) == 4
        assert imported[0].trigger == ";hi"
        assert imported[0].replacement == "Hello world!"

        # Verify image was safely extracted
        assert imported[1].is_image is True
        assert imported[1].replacement.startswith("image:")
        real_img_path = Path(imported[1].replacement.removeprefix("image:"))
        assert real_img_path.is_file()
        assert real_img_path.read_bytes() == img_file.read_bytes()

        # Verify regex snippet
        assert imported[2].is_regex is True
        assert imported[2].trigger == r"re:;order(\d+)"


def test_package_tamper_refusal_text_replacement():
    """Assert PackageIntegrityError when snippet replacement text in ZIP is modified."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pack_file = tmp_path / "valid.ravaanpack"

        snippets = [Snippet(trigger=";safe", replacement="Original safe text")]
        export_package(snippets, pack_file, name="Tamper Test")

        # Read zip and alter manifest content without updating SHA-256 hash
        tampered_file = tmp_path / "tampered.ravaanpack"
        with zipfile.ZipFile(pack_file, "r") as zin, zipfile.ZipFile(tampered_file, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "manifest.json":
                    manifest_data = json.loads(data.decode("utf-8"))
                    manifest_data["snippets"][0]["replacement"] = "MALICIOUS INJECTED TEXT"
                    data = json.dumps(manifest_data).encode("utf-8")
                zout.writestr(item, data)

        with pytest.raises(PackageIntegrityError) as exc_info:
            inspect_package(tampered_file)
        assert "SHA256 mismatch" in str(exc_info.value)


def test_package_tamper_refusal_image_binary():
    """Assert PackageIntegrityError when image binary in ZIP is tampered with."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pack_file = tmp_path / "img_valid.ravaanpack"
        img_file = tmp_path / "pic.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\nREAL_IMAGE_BYTES")

        snippets = [Snippet(trigger=";pic", replacement=str(img_file), is_image=True)]
        export_package(snippets, pack_file, name="Img Test")

        # Read zip and alter image binary
        tampered_file = tmp_path / "img_tampered.ravaanpack"
        with zipfile.ZipFile(pack_file, "r") as zin, zipfile.ZipFile(tampered_file, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("images/"):
                    data = b"TAMPERED_BYTES_REPLACED"
                zout.writestr(item, data)

        with pytest.raises(PackageIntegrityError) as exc_info:
            inspect_package(tampered_file)
        assert "SHA256 mismatch" in str(exc_info.value)


def test_collision_detection_and_resolution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pack_file = tmp_path / "collisions.ravaanpack"

        pack_snippets = [
            Snippet(trigger=";hello", replacement="New Hello!"),
            Snippet(trigger=";unique", replacement="Unique content"),
        ]
        export_package(pack_snippets, pack_file, name="Collision Pack")

        existing = [
            Snippet(trigger=";hello", replacement="Old Existing Hello"),
            Snippet(trigger=";bye", replacement="Existing Goodbye"),
        ]

        # 1. Collision detection
        manifest, collisions = detect_package_collisions(pack_file, existing)
        assert collisions == [";hello"]
        assert manifest["name"] == "Collision Pack"

        # 2. Import with replace_existing=False (Default merge: preserve existing)
        merged = import_package(pack_file, replace_existing=False, existing_snippets=existing)
        by_trig = {s.trigger: s.replacement for s in merged}
        assert len(merged) == 3
        assert by_trig[";hello"] == "Old Existing Hello"  # Preserved!
        assert by_trig[";unique"] == "Unique content"
        assert by_trig[";bye"] == "Existing Goodbye"

        # 3. Import with replace_existing=True (Overwrite on collision)
        overwritten = import_package(pack_file, replace_existing=True, existing_snippets=existing)
        by_trig_over = {s.trigger: s.replacement for s in overwritten}
        assert len(overwritten) == 3
        assert by_trig_over[";hello"] == "New Hello!"  # Overwritten!
        assert by_trig_over[";unique"] == "Unique content"
        assert by_trig_over[";bye"] == "Existing Goodbye"


def test_example_persian_dates_package():
    example_path = Path("examples/persian-dates.ravaanpack")
    assert example_path.is_file(), "Shipped example package examples/persian-dates.ravaanpack is missing!"

    manifest = inspect_package(example_path)
    assert manifest["name"] == "Persian Dates & Calendar"
    assert manifest["format_version"] == 2
    assert len(manifest["snippets"]) >= 5

    triggers = {s["trigger"] for s in manifest["snippets"]}
    assert ";;tarikh" in triggers
    assert ";;shamsi" in triggers
    assert ";;zaman" in triggers
    assert len(manifest["groups"]) >= 1


def test_cli_pack_import_and_export():
    from ravan.cli import main

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pack_path = tmp_path / "cli_pack.ravaanpack"

        # Export via CLI
        ret_exp = main(["pack", "export", str(pack_path), "--title", "CLI Pack", "--author", "Tester"])
        assert ret_exp == 0
        assert pack_path.is_file()

        # Import via CLI
        ret_imp = main(["pack", "import", str(pack_path)])
        assert ret_imp == 0

        # Import with --replace flag
        ret_imp_replace = main(["pack", "import", str(pack_path), "--replace"])
        assert ret_imp_replace == 0


def test_package_dialogs_headless():
    """Verify dialog classes instantiate and render without crashing in headless env."""
    import tkinter as tk

    try:
        root = tk.Tk()
        root.withdraw()
    except (tk.TclError, Exception):
        pytest.skip("No graphical display available for Tkinter")

    from ravan.ui.package_dialog import PackagePreviewDialog
    from ravan.ui.package_export_dialog import PackageExportDialog

    try:
        example_path = Path("examples/persian-dates.ravaanpack")
        dlg_preview = PackagePreviewDialog(root, example_path, [], lambda s, g: None)
        assert dlg_preview.package_path == example_path

        dlg_export = PackageExportDialog(root, [Snippet(trigger=";a", replacement="b")], [])
        assert dlg_export.name_var.get() == "Ravaan Snippets"
    finally:
        root.destroy()
