"""Tests for documentation integrity, community guidelines, and i18n parity."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestI18nParity:
    """Verifies complete 100% key parity and placeholder integrity between locales."""

    @pytest.fixture
    def locales(self) -> tuple[dict, dict]:
        en_file = REPO_ROOT / "ravan" / "data" / "locales" / "en.json"
        fa_file = REPO_ROOT / "ravan" / "data" / "locales" / "fa.json"
        assert en_file.is_file(), f"en.json not found at {en_file}"
        assert fa_file.is_file(), f"fa.json not found at {fa_file}"

        en_data = json.loads(en_file.read_text(encoding="utf-8"))
        fa_data = json.loads(fa_file.read_text(encoding="utf-8"))
        return en_data, fa_data

    @staticmethod
    def flatten_dict(d: dict, prefix: str = "") -> dict[str, str]:
        items: dict[str, str] = {}
        for k, v in d.items():
            pk = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(TestI18nParity.flatten_dict(v, pk))
            else:
                items[pk] = str(v)
        return items

    def test_complete_key_parity(self, locales: tuple[dict, dict]):
        en_data, fa_data = locales
        flat_en = self.flatten_dict(en_data)
        flat_fa = self.flatten_dict(fa_data)

        missing_in_fa = set(flat_en.keys()) - set(flat_fa.keys())
        missing_in_en = set(flat_fa.keys()) - set(flat_en.keys())

        assert not missing_in_fa, f"Keys in en.json missing in fa.json: {missing_in_fa}"
        assert not missing_in_en, f"Keys in fa.json missing in en.json: {missing_in_en}"
        assert len(flat_en) >= 250, f"Expected at least 250 localized strings, got {len(flat_en)}"

    def test_no_empty_translations(self, locales: tuple[dict, dict]):
        en_data, fa_data = locales
        flat_en = self.flatten_dict(en_data)
        flat_fa = self.flatten_dict(fa_data)

        for k, v in flat_en.items():
            assert v.strip(), f"Empty string in en.json for key '{k}'"
        for k, v in flat_fa.items():
            assert v.strip(), f"Empty string in fa.json for key '{k}'"

    def test_placeholder_parity(self, locales: tuple[dict, dict]):
        en_data, fa_data = locales
        flat_en = self.flatten_dict(en_data)
        flat_fa = self.flatten_dict(fa_data)

        placeholder_pattern = re.compile(r"\{([a-zA-Z0-9_]+)\}")
        for k, en_val in flat_en.items():
            fa_val = flat_fa[k]
            en_placeholders = set(placeholder_pattern.findall(en_val))
            fa_placeholders = set(placeholder_pattern.findall(fa_val))
            assert en_placeholders == fa_placeholders, (
                f"Placeholder mismatch in key '{k}': EN has {en_placeholders}, FA has {fa_placeholders}"
            )


class TestDocumentationFiles:
    """Verifies that all required documentation files exist and have quality content."""

    def test_readme_files_exist_and_bilingual(self):
        readme_en = REPO_ROOT / "README.md"
        readme_fa = REPO_ROOT / "README.fa.md"
        assert readme_en.is_file()
        assert readme_fa.is_file()

        en_text = readme_en.read_text(encoding="utf-8")
        assert "winget install MohsenNiksirat.Ravaan" in en_text
        assert "scoop install" in en_text
        assert "choco install" in en_text
        assert "README.fa.md" in en_text
        assert "Zero Telemetry" in en_text

        fa_text = readme_fa.read_text(encoding="utf-8")
        assert "دستیار تایپ روان" in fa_text
        assert "winget install" in fa_text
        assert "نیم‌فاصله" in fa_text
        assert "Zero Telemetry" in fa_text

    def test_demo_walkthrough_document(self):
        demo_file = REPO_ROOT / "docs" / "DEMO.md"
        assert demo_file.is_file()
        content = demo_file.read_text(encoding="utf-8")
        assert "Scenario 1: Wrong Keyboard Layout Auto-Fix" in content
        assert "Scenario 2: Persian Typography & ZWNJ Engine" in content
        assert "Scenario 3: Text Snippet Expansion" in content
        assert "Scenario 4: Finglish Phonetic Typing" in content
        assert "Scenario 5: Inline Math Calculator" in content
        assert "Scenario 6: Privacy Guard" in content

    def test_contributing_and_conduct(self):
        contrib = REPO_ROOT / "CONTRIBUTING.md"
        conduct = REPO_ROOT / "CODE_OF_CONDUCT.md"
        assert contrib.is_file()
        assert conduct.is_file()

        c_text = contrib.read_text(encoding="utf-8")
        assert "Zero Telemetry & Local-Only Privacy" in c_text
        assert "pytest" in c_text
        assert "ruff check" in c_text
        assert "راهنمای مشارکت (فارسی)" in c_text

        cond_text = conduct.read_text(encoding="utf-8")
        assert "Contributor Covenant" in cond_text
        assert "Our Pledge" in cond_text


class TestGitHubTemplates:
    """Verifies GitHub Issue and Pull Request templates."""

    def test_issue_templates_valid_yaml(self):
        issue_dir = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
        assert issue_dir.is_dir()

        bug = issue_dir / "bug_report.yml"
        feat = issue_dir / "feature_request.yml"
        dict_sug = issue_dir / "dictionary_suggestion.yml"
        cfg = issue_dir / "config.yml"

        for f in (bug, feat, dict_sug, cfg):
            assert f.is_file(), f"Missing template: {f.name}"
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"YAML in {f.name} did not load a dict"

    def test_pull_request_template(self):
        pr_tmpl = REPO_ROOT / ".github" / "pull_request_template.md"
        assert pr_tmpl.is_file()
        content = pr_tmpl.read_text(encoding="utf-8")
        assert "Zero Telemetry" in content
        assert "Zero Keystroke Logging" in content
        assert "Bilingual Parity" in content
        assert "Automated Tests" in content


class TestMarkdownInternalLinks:
    """Ensures relative links in key markdown docs point to existing files."""

    @pytest.mark.parametrize(
        "doc_relative_path",
        [
            "README.md",
            "README.fa.md",
            "CONTRIBUTING.md",
            "docs/DEMO.md",
            "docs/SECURITY_FAQ.md",
            "docs/SMARTSCREEN.md",
        ],
    )
    def test_markdown_links_resolve(self, doc_relative_path: str):
        doc_path = REPO_ROOT / doc_relative_path
        assert doc_path.is_file()
        content = doc_path.read_text(encoding="utf-8")

        # Match markdown links: [text](target)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        for match in link_pattern.finditer(content):
            target = match.group(2).split("#")[0].strip()
            # Skip external URLs, email links, and in-page anchors
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            target_path = (doc_path.parent / target).resolve()
            assert target_path.exists(), f"Broken relative link in {doc_relative_path}: '{target}' -> {target_path}"
