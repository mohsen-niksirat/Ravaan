"""Release readiness and final verification tests for Ravaan v1.0.0."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
import yaml

import ravan
from scripts.build_release import (
    create_portable_zip,
    find_iscc,
)
from scripts.build_release import (
    main as release_main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestVersionConsistency:
    """Verifies that all version metadata across the repository are in 100% agreement."""

    def test_all_versions_equal_2_1_0(self):
        expected_version = "2.1.0"

        # 1. ravan module
        assert ravan.__version__ == expected_version, (
            f"ravan.__version__ is {ravan.__version__}, expected {expected_version}"
        )

        # 2. pyproject.toml
        pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
        assert match is not None, "Version not found in pyproject.toml"
        assert match.group(1) == expected_version

        # 3. installer/setup.iss
        iss_text = (REPO_ROOT / "installer" / "setup.iss").read_text(encoding="utf-8")
        assert f'#define MyAppVersion "{expected_version}"' in iss_text

        # 4. Winget version manifest
        winget_ver_file = (
            REPO_ROOT / "packaging" / "winget" / "manifests" / "m" / "MohsenNiksirat" / "Ravaan" / expected_version / "MohsenNiksirat.Ravaan.yaml"
        )
        assert winget_ver_file.is_file()
        winget_data = yaml.safe_load(winget_ver_file.read_text(encoding="utf-8"))
        assert winget_data["PackageVersion"] == expected_version

        # 5. Scoop manifest
        scoop_file = REPO_ROOT / "packaging" / "scoop" / "ravaan.json"
        assert scoop_file.is_file()
        scoop_data = json.loads(scoop_file.read_text(encoding="utf-8"))
        assert scoop_data["version"] == expected_version

        # 6. Chocolatey nuspec
        choco_file = REPO_ROOT / "packaging" / "chocolatey" / "ravaan" / "ravaan.nuspec"
        assert choco_file.is_file()
        tree = ET.parse(str(choco_file))
        root = tree.getroot()
        ns = {"ns": "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"}
        metadata = root.find("ns:metadata", ns)
        if metadata is None:
            metadata = root.find("metadata")
        assert metadata is not None
        ver_el = metadata.find("ns:version", ns)
        if ver_el is None:
            ver_el = metadata.find("version")
        assert ver_el is not None
        assert ver_el.text == expected_version


class TestPyInstallerSpec:
    """Verifies ravan.spec configuration for clean standalone builds."""

    @pytest.fixture
    def spec_content(self) -> str:
        spec_path = REPO_ROOT / "ravan.spec"
        assert spec_path.is_file()
        return spec_path.read_text(encoding="utf-8")

    def test_spec_entrypoint_and_datas(self, spec_content: str):
        assert 'ravan/__main__.py' in spec_content
        assert 'ravan" / "data"' in spec_content
        assert 'name="Ravaan"' in spec_content
        assert 'console=False' in spec_content
        assert 'icon.ico' in spec_content


class TestDataFilesIntegrity:
    """Ensures all essential binary and lexicon data files exist and are valid."""

    def test_persian_lexicon_assets(self):
        data_dir = REPO_ROOT / "ravan" / "data"
        words_txt = data_dir / "words_fa.txt"
        words_bin = data_dir / "words_fa.bin"
        assert words_txt.is_file() and words_txt.stat().st_size > 1_000_000
        assert words_bin.is_file() and words_bin.stat().st_size > 1_000_000

    def test_english_lexicon_assets(self):
        data_dir = REPO_ROOT / "ravan" / "data"
        words_txt = data_dir / "words_en.txt"
        words_bin = data_dir / "words_en.bin"
        assert words_txt.is_file() and words_txt.stat().st_size > 100_000
        assert words_bin.is_file() and words_bin.stat().st_size > 100_000

    def test_json_data_assets(self):
        data_dir = REPO_ROOT / "ravan" / "data"
        finglish_file = data_dir / "finglish_dict.json"
        zwnj_file = data_dir / "zwnj_rules.json"
        icon_file = data_dir / "icon.ico"

        assert finglish_file.is_file()
        f_data = json.loads(finglish_file.read_text(encoding="utf-8"))
        assert len(f_data) >= 5000

        assert zwnj_file.is_file()
        z_data = json.loads(zwnj_file.read_text(encoding="utf-8"))
        assert isinstance(z_data, dict)

        assert icon_file.is_file() and icon_file.stat().st_size > 1000


class TestReleaseBuildPipeline:
    """Verifies packaging script functions."""

    def test_create_portable_zip(self, tmp_path: Path):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        dummy_exe = dist_dir / "Ravaan.exe"
        dummy_exe.write_bytes(b"dummy-executable-binary")

        zip_out = create_portable_zip("1.0.0", dist_dir)
        assert zip_out.is_file()

        with zipfile.ZipFile(zip_out, "r") as zf:
            namelist = zf.namelist()
            assert "Ravaan.exe" in namelist
            assert "README.md" in namelist
            assert "README.fa.md" in namelist
            assert "LICENSE" in namelist
            assert "docs/SECURITY_FAQ.md" in namelist
            assert "docs/SMARTSCREEN.md" in namelist

    def test_find_iscc(self):
        # find_iscc should either return a Path to ISCC or None without crashing
        res = find_iscc()
        assert res is None or isinstance(res, Path)

    def test_build_release_cli_skip_compilers(self, tmp_path: Path):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        dummy_exe = dist_dir / "Ravaan.exe"
        dummy_exe.write_bytes(b"dummy-exe-content")

        ret = release_main([
            "--version", "1.0.0",
            "--skip-pyinstaller",
            "--skip-installer",
            "--dist-dir", str(dist_dir),
        ])
        assert ret == 0
        assert (dist_dir / "Ravaan-Portable-1.0.0.zip").is_file()
        assert (dist_dir / "SHA256SUMS.txt").is_file()
        assert (dist_dir / "RELEASE_NOTES.md").is_file()
