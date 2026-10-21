"""Audit and verification suite for COMPARISON.md competitive parity matrix."""

from pathlib import Path


def test_comparison_doc_exists_and_bilingual():
    doc_path = Path("COMPARISON.md")
    assert doc_path.is_file(), "COMPARISON.md must exist in repository root"
    content = doc_path.read_text(encoding="utf-8")
    assert len(content) > 1000, "COMPARISON.md content is unexpectedly short"

    # Bilingual headers
    assert "مقایسه جامع روان" in content
    assert "Competitive Parity Matrix" in content
    assert "Feature Matrix" in content
    assert "Architecture & Implementation Mapping" in content


def test_every_checked_feature_maps_to_codebase():
    doc_path = Path("COMPARISON.md")
    content = doc_path.read_text(encoding="utf-8")

    # Map of claimed features to their real modules
    feature_mappings = [
        ("Auto-Fix", "ravan/core/autofix.py"),
        ("Auto-Switch", "ravan/platform/lang.py"),
        ("Undo & Blacklist", "ravan/core/learning.py"),
        ("Transliteration", "ravan/core/translit.py"),
        ("Continuous & Bigram", "ravan/core/predictor.py"),
        ("Suppression", "ravan/platform/focus.py"),
        ("Snippets 3.0", "ravan/core/snippet.py"),
        ("Packages", "ravan/core/package.py"),
        ("Quick Accent", "ravan/core/accent.py"),
        ("AI Assistant", "ravan/core/ai.py"),
        ("Voice Dictation", "ravan/core/voice.py"),
        ("Zero-log", "ravan/platform/hook.py"),
        ("DPAPI", "ravan/core/crypto.py"),
        ("Calculator", "ravan/core/calc.py"),
        ("Jalali", "ravan/core/jalali.py"),
        ("Clipboard History", "ravan/core/cliphistory.py"),
        ("Sync", "ravan/core/sync.py"),
    ]

    for label, file_rel_path in feature_mappings:
        module_file = Path(file_rel_path)
        assert module_file.is_file(), f"Claimed feature '{label}' maps to missing module {file_rel_path}"
        assert file_rel_path in content, f"Module path '{file_rel_path}' must be referenced in COMPARISON.md"


def test_honest_limitations_and_future_horizons():
    doc_path = Path("COMPARISON.md")
    content = doc_path.read_text(encoding="utf-8")

    # Must honestly report OS limitation (Windows-first vs Espanso cross-platform)
    assert "Windows" in content
    assert "Espanso" in content
    assert "Post-2.0" in content or "آینده" in content
