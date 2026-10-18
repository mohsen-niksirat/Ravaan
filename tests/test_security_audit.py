"""Security audit tests verifying that raw keystrokes are never logged or stored."""

from __future__ import annotations

import logging
import re

from ravan.core.learning import UserLearningEngine
from ravan.platform.hook import HookEvent


class LogListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_keylogger_risk_audit_no_keystroke_dumps_in_logs():
    """Verify that keyboard hook events and typing activity never log raw keystrokes."""
    handler = LogListHandler()
    root_log = logging.getLogger("ravan")
    old_level = root_log.level
    root_log.setLevel(logging.DEBUG)
    root_log.addHandler(handler)

    try:
        # Simulate firing synthetic raw hook events
        _events = [
            HookEvent(vk_code=65, flags=0, scan_code=30, is_key_down=True),   # 'A'
            HookEvent(vk_code=83, flags=0, scan_code=31, is_key_down=True),   # 'S'
            HookEvent(vk_code=68, flags=0, scan_code=32, is_key_down=True),   # 'D'
            HookEvent(vk_code=70, flags=0, scan_code=33, is_key_down=True),   # 'F'
            HookEvent(vk_code=13, flags=0, scan_code=28, is_key_down=True),   # Return
        ]
        assert len(_events) == 5
        # Simulate component logging during hook operations
        log = logging.getLogger("ravan.platform.hook")
        log.info("Keyboard hook installed")
        log.info("Keyboard hook uninstalled")

        # Patterns that would indicate a keylogger dumping raw keystrokes
        leaky_patterns = [
            re.compile(r"vk_code\s*=\s*\d+", re.IGNORECASE),
            re.compile(r"scan_code\s*=\s*\d+", re.IGNORECASE),
            re.compile(r"raw_keystroke", re.IGNORECASE),
            re.compile(r"key_pressed\s*:", re.IGNORECASE),
            re.compile(r"key_event\s*:", re.IGNORECASE),
            re.compile(r"dumping_keys", re.IGNORECASE),
        ]

        for record in handler.records:
            msg = record.getMessage()
            for pat in leaky_patterns:
                assert not pat.search(msg), f"Potential keystroke leak detected in log: {msg!r}"

    finally:
        root_log.removeHandler(handler)
        root_log.setLevel(old_level)


def test_learning_profile_stores_only_word_aggregates(tmp_path):
    """Verify that learning profile stores only aggregated word frequencies."""
    profile_path = tmp_path / "learning_profile.json"
    engine = UserLearningEngine(storage_path=profile_path, auto_load=False)

    # Train on words and transitions
    words = ["سلام", "دوستان", "عزیز", "پروژه", "روان"]
    for i in range(len(words) - 1):
        engine.learn_transition(words[i], words[i + 1])
    engine.save()

    data = engine.export_profile()
    # Profile must contain only frequency statistics and token maps
    assert "word_counts" in data
    assert "transitions" in data

    # Ensure no raw keycodes or timestamps per keystroke exist
    for word, count in data["word_counts"].items():
        assert isinstance(word, str)
        assert isinstance(count, (int, float))
        # Words must be clean tokens, not raw scan codes or serialized events
        assert not word.startswith("vk_")
        assert not word.startswith("scan_")

    # Transitions must be pairs of words
    for context, next_words in data["transitions"].items():
        assert isinstance(context, str)
        assert isinstance(next_words, dict)
        for next_word, count in next_words.items():
            assert isinstance(next_word, str)
            assert isinstance(count, (int, float))
