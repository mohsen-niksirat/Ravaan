"""Tests for packaging, installer definitions, and release hash utilities."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.generate_hashes import (
    format_markdown_table,
    format_sha256sums,
    generate_checksums,
    render_release_notes,
    sha256_file,
)
from scripts.generate_hashes import (
    main as hashes_main,
)

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestInnoSetupScript:
    """Verifies installer/setup.iss configuration and safety rules."""

    @pytest.fixture
    def iss_content(self) -> str:
        iss_path = REPO_ROOT / "installer" / "setup.iss"
        assert iss_path.is_file(), f"setup.iss not found at {iss_path}"
        return iss_path.read_text(encoding="utf-8")

    def test_app_id_format(self, iss_content: str):
        match = re.search(r"AppId=\{\{([0-9A-Fa-f\-]{36})\}", iss_content)
        assert match is not None, "AppId with double leading brace and valid UUID not found in setup.iss"
        uuid = match.group(1)
        assert len(uuid) == 36

    def test_per_user_non_admin_scope(self, iss_content: str):
        assert "PrivilegesRequired=lowest" in iss_content

    def test_solid_compression_enabled(self, iss_content: str):
        assert "SolidCompression=yes" in iss_content
        assert "Compression=lzma2/ultra64" in iss_content

    def test_upgrade_in_place_safety(self, iss_content: str):
        assert "CloseApplications=force" in iss_content

    def test_uninstall_cleanup_prompt(self, iss_content: str):
        assert "CurUninstallStepChanged" in iss_content
        assert "{userappdata}\\Ravaan" in iss_content
        assert "DeleteDataPrompt" in iss_content
        assert "MB_DEFBUTTON2" in iss_content  # Safe default: 'No' is selected by default


class TestHashGenerator:
    """Verifies scripts/generate_hashes.py behavior."""

    def test_sha256_file(self, tmp_path: Path):
        test_file = tmp_path / "sample.txt"
        test_file.write_bytes(b"hello ravaan security")
        digest = sha256_file(test_file)
        assert len(digest) == 64
        # Standard sha256 of b"hello ravaan security"
        import hashlib
        expected = hashlib.sha256(b"hello ravaan security").hexdigest()
        assert digest == expected

    def test_format_sha256sums_gnu_format(self):
        checksums = [
            ("Ravaan-Setup-1.0.0.exe", "a" * 64, 1024),
            ("Ravaan-Portable-1.0.0.zip", "b" * 64, 2048),
        ]
        out = format_sha256sums(checksums)
        expected = f"{'a' * 64}  Ravaan-Setup-1.0.0.exe\n{'b' * 64}  Ravaan-Portable-1.0.0.zip\n"
        assert out == expected

    def test_format_markdown_table(self):
        checksums = [
            ("Ravaan-Setup-1.0.0.exe", "c" * 64, 10 * 1024 * 1024),
        ]
        table = format_markdown_table(checksums)
        assert "| `Ravaan-Setup-1.0.0.exe` | 10.00 MB | `cccc" in table

    def test_generate_checksums_and_render_notes(self, tmp_path: Path):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        dummy_exe = dist_dir / "Ravaan-Setup-1.0.0.exe"
        dummy_exe.write_bytes(b"sample bytes")

        res = generate_checksums(dist_dir)
        assert len(res) == 1
        name, sha, size = res[0]
        assert name == "Ravaan-Setup-1.0.0.exe"
        assert len(sha) == 64
        assert size == len(b"sample bytes")

        rendered = render_release_notes("1.0.0", "| table |")
        assert "1.0.0" in rendered
        assert "| table |" in rendered

    def test_cli_execution_with_output_files(self, tmp_path: Path):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        dummy_exe = dist_dir / "Ravaan-Setup-1.0.0.exe"
        dummy_exe.write_bytes(b"fake-exe-content")

        sums_file = tmp_path / "SHA256SUMS.txt"
        notes_file = tmp_path / "RELEASE_NOTES.md"

        ret = hashes_main([
            "--version", "1.0.0",
            "--dist", str(dist_dir),
            "--write-sums", str(sums_file),
            "--write-notes", str(notes_file),
        ])
        assert ret == 0
        assert sums_file.is_file()
        assert "Ravaan-Setup-1.0.0.exe" in sums_file.read_text(encoding="utf-8")
        assert notes_file.is_file()
        assert "Ravaan-Setup-1.0.0.exe" in notes_file.read_text(encoding="utf-8")


class TestWingetManifests:
    """Verifies Winget manifests follow schema v1.6.0."""

    @pytest.fixture
    def winget_dir(self) -> Path:
        p = REPO_ROOT / "packaging" / "winget" / "manifests" / "m" / "MohsenNiksirat" / "Ravaan" / "1.0.0"
        assert p.is_dir(), f"Winget directory not found at {p}"
        return p

    def test_version_manifest(self, winget_dir: Path):
        v_file = winget_dir / "MohsenNiksirat.Ravaan.yaml"
        data = yaml.safe_load(v_file.read_text(encoding="utf-8"))
        assert data["PackageIdentifier"] == "MohsenNiksirat.Ravaan"
        assert data["PackageVersion"] == "1.0.0"
        assert data["DefaultLocale"] == "en-US"
        assert data["ManifestType"] == "version"
        assert data["ManifestVersion"] == "1.6.0"

    def test_installer_manifest(self, winget_dir: Path):
        i_file = winget_dir / "MohsenNiksirat.Ravaan.installer.yaml"
        data = yaml.safe_load(i_file.read_text(encoding="utf-8"))
        assert data["PackageIdentifier"] == "MohsenNiksirat.Ravaan"
        assert data["InstallerType"] == "inno"
        assert data["Scope"] == "user"
        assert "/VERYSILENT" in data["InstallerSwitches"]["Silent"]
        assert data["ProductCode"] == "{C4E9C0A7-62F1-4F2B-933B-8C477614AA51}_is1"
        assert len(data["Installers"]) >= 1
        assert data["Installers"][0]["Architecture"] == "x64"

    def test_en_us_locale_manifest(self, winget_dir: Path):
        l_file = winget_dir / "MohsenNiksirat.Ravaan.locale.en-US.yaml"
        data = yaml.safe_load(l_file.read_text(encoding="utf-8"))
        assert data["PackageIdentifier"] == "MohsenNiksirat.Ravaan"
        assert data["PackageLocale"] == "en-US"
        assert data["PackageName"] == "Ravaan"
        assert "MIT" in data["License"]
        assert "persian" in [t.lower() for t in data["Tags"]]

    def test_fa_ir_locale_manifest(self, winget_dir: Path):
        l_file = winget_dir / "MohsenNiksirat.Ravaan.locale.fa-IR.yaml"
        data = yaml.safe_load(l_file.read_text(encoding="utf-8"))
        assert data["PackageIdentifier"] == "MohsenNiksirat.Ravaan"
        assert data["PackageLocale"] == "fa-IR"
        assert "روان" in data["PackageName"]
        assert "فارسی" in data["Tags"]


class TestScoopManifest:
    """Verifies Scoop package manifest."""

    def test_scoop_json(self):
        scoop_path = REPO_ROOT / "packaging" / "scoop" / "ravaan.json"
        assert scoop_path.is_file()
        data = json.loads(scoop_path.read_text(encoding="utf-8"))
        assert data["version"] == "2.6.0"
        assert data["bin"] == "Ravaan.exe"
        assert data["persist"] == "data"
        assert data["checkver"] == "github"
        assert "64bit" in data["architecture"]
        assert "Ravaan-Portable-2.6.0.zip" in data["architecture"]["64bit"]["url"]


class TestChocolateyPackage:
    """Verifies Chocolatey nuspec and install scripts."""

    @pytest.fixture
    def choco_dir(self) -> Path:
        p = REPO_ROOT / "packaging" / "chocolatey" / "ravaan"
        assert p.is_dir()
        return p

    def test_nuspec_xml(self, choco_dir: Path):
        nuspec_file = choco_dir / "ravaan.nuspec"
        tree = ET.parse(str(nuspec_file))
        root = tree.getroot()
        # Handle XML namespace if present
        ns = {"ns": "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"}
        metadata = root.find("ns:metadata", ns)
        if metadata is None:
            metadata = root.find("metadata")
        assert metadata is not None

        def get_val(tag: str) -> str:
            el = metadata.find(f"ns:{tag}", ns)
            if el is None:
                el = metadata.find(tag)
            assert el is not None, f"Tag {tag} not found in nuspec"
            return el.text or ""

        assert get_val("id") == "ravaan"
        assert get_val("version") == "2.6.0"
        assert "Mohsen Niksirat" in get_val("authors")
        assert "LICENSE" in get_val("licenseUrl")

    def test_chocolatey_install_script(self, choco_dir: Path):
        script_path = choco_dir / "tools" / "chocolateyinstall.ps1"
        assert script_path.is_file()
        content = script_path.read_text(encoding="utf-8")
        assert "Install-ChocolateyPackage" in content
        assert "/VERYSILENT" in content
        assert "/ALLUSERS=0" in content

    def test_chocolatey_uninstall_script(self, choco_dir: Path):
        script_path = choco_dir / "tools" / "chocolateyuninstall.ps1"
        assert script_path.is_file()
        content = script_path.read_text(encoding="utf-8")
        assert "Uninstall-ChocolateyPackage" in content
        assert "/VERYSILENT" in content


class TestSecurityAndTrustDocumentation:
    """Verifies security, privacy FAQ, and SmartScreen documentation."""

    def test_security_faq_bilingual(self):
        faq_path = REPO_ROOT / "docs" / "SECURITY_FAQ.md"
        assert faq_path.is_file()
        content = faq_path.read_text(encoding="utf-8")

        # English section
        assert "Zero Keystroke Logging" in content
        assert "Zero Telemetry" in content
        assert "SetWindowsHookExW" in content
        assert "SHA256SUMS.txt" in content

        # Persian section
        assert "حریم خصوصی" in content
        assert "Zero Keystroke Logging" in content
        assert "عدم ثبت کلیدها" in content
        assert "قلاب صفحه‌کلید" in content

    def test_smartscreen_guide_bilingual(self):
        ss_path = REPO_ROOT / "docs" / "SMARTSCREEN.md"
        assert ss_path.is_file()
        content = ss_path.read_text(encoding="utf-8")

        # English
        assert "More info" in content
        assert "Run anyway" in content
        assert "Get-FileHash" in content

        # Persian
        assert "اسمارت‌اسکرین" in content
        assert "اطلاعات بیشتر" in content
        assert "در هر صورت اجرا شود" in content

