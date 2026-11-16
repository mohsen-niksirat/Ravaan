"""Cross-platform v3.0.0 architectural invariants & core parity tests (Linux/macOS/Windows CI)."""

from __future__ import annotations

import ast
import io
import json
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ravan import __version__
from ravan.core.ai import AI_PROVIDER_PRESETS, AIAssistantEngine, OllamaProvider
from ravan.core.config import Snippet
from ravan.core.hub import BUILTIN_HUB_PACKS, HubManager
from ravan.core.model_manager import VOICE_MODELS, ModelManager
from ravan.core.voice import VoiceEngine, pcm16_to_wav_bytes, postprocess_dictation

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_core_layer_never_imports_platform_or_ui() -> None:
    """Enforce the strict 3-layer dependency law: core/ never imports ui/ and v3 core never imports platform/."""
    core_dir = REPO_ROOT / "ravan" / "core"
    legacy_platform_exceptions = {"macro.py", "snippet_macros.py", "soak.py"}
    violations: list[str] = []
    for py_file in sorted(core_dir.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            mods = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else ([node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            )
            for mod in mods:
                if mod.startswith("ravan.ui"):
                    violations.append(f"{py_file.name}: imports ui ({mod})")
                elif mod.startswith("ravan.platform") and py_file.name not in legacy_platform_exceptions:
                    violations.append(f"{py_file.name}: imports platform ({mod})")
    assert not violations, f"3-Layer dependency violations: {violations}"


def test_v3_new_and_refactored_modules_respect_size_budget() -> None:
    """Verify modular line ceilings across Phases 1–4 deliverables."""
    budget = [
        ("ravan/core/ai.py", 400),
        ("ravan/core/hub.py", 400),
        ("ravan/core/model_manager.py", 400),
        ("ravan/core/voice.py", 400),
        ("ravan/platform/audio.py", 400),
        ("ravan/ui/ai_diff.py", 400),
        ("ravan/ui/ai_popup.py", 400),
        ("ravan/ui/hub_browser.py", 400),
        ("ravan/ui/hub_preview_modal.py", 400),
        ("ravan/ui/selection_toolbar.py", 400),
        ("ravan/ui/settings.py", 425),
        ("ravan/ui/settings_ai_voice.py", 400),
        ("ravan/ui/settings_voice_panel.py", 400),
        ("ravan/ui/waveform_pill.py", 400),
        ("ravan/ui/widgets/controls.py", 425),
        ("ravan/ui/widgets/icons.py", 425),
        ("ravan/ui/widgets/surface.py", 425),
    ]
    for rel, max_lines in budget:
        count = len((REPO_ROOT / rel).read_text(encoding="utf-8").splitlines())
        assert count <= max_lines, f"{rel} has {count} lines (budget {max_lines})"


def test_v3_cross_platform_core_pipeline_smoke(tmp_path: Path) -> None:
    """Verify Voice 2.0 core, AI 2.0 core, and Hub core work with zero Win32/Tk deps."""
    assert __version__ == "3.0.0"

    # Voice 2.0 core: RAM-only WAV encoding, catalog, Persian grammar postprocess
    wav = pcm16_to_wav_bytes(b"\x01\x00" * 1600, sample_rate=16000)
    assert wav[:4] == b"RIFF" and b"WAVE" in wav[:16]
    cleaned = postprocess_dictation("مي روم کتاب ها را بخوانم", digit_mode="fa")
    assert "می\u200cروم" in cleaned and "کتاب\u200cها" in cleaned

    mm = ModelManager(base_dir=tmp_path / "models")
    assert len(mm.list_models()) == len(VOICE_MODELS)
    ve = VoiceEngine(mode="offline", model_manager=mm)
    assert ve.start_recording() is True
    ve.record_chunk(b"\x01\x00" * 160)
    assert ve.stop_recording_and_transcribe(mock_result="مي روم") == "می\u200cروم"

    # AI 2.0 core: presets + NDJSON stream
    assert {"ollama", "openai", "gemini", "groq", "openrouter", "custom"} <= set(AI_PROVIDER_PRESETS)
    engine = AIAssistantEngine(OllamaProvider())
    ndjson = (json.dumps({"response": "تایید شد", "done": True}) + "\n").encode("utf-8")
    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(ndjson)):
        assert "".join(engine.process_stream("rewrite", "hello")) == "تایید شد"

    # Hub core: offline index + install + uninstall preserving custom user snippets
    hub = HubManager(base_dir=tmp_path / "hub")
    custom = [Snippet(trigger=";my", replacement="mine")]
    snips, _groups, _man = hub.install_pack(BUILTIN_HUB_PACKS[0], custom)
    assert any(s.trigger == ";bism" for s in snips)
    assert [s.trigger for s in hub.uninstall_pack(BUILTIN_HUB_PACKS[0].pack_id, snips)] == [";my"]
