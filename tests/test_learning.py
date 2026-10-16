"""Unit tests for user typing style learning engine and next-word prediction."""

from __future__ import annotations

from pathlib import Path

from ravan.core.learning import UserLearningEngine


def test_seeded_next_word_predictions(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)

    # Test seeded transitions
    next_words = engine.predict_next_words("سلام", limit=5)
    assert len(next_words) >= 3
    assert "عزیز" in next_words or "علیکم" in next_words

    ba_next = engine.predict_next_words("با", limit=5)
    assert "تشکر" in ba_next or "احترام" in ba_next


def test_learning_new_words_and_transitions(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)

    # Learn custom user domain phrases
    engine.learn_transition("گزارش", "فروش")
    engine.learn_transition("فروش", "ماهانه")

    assert "فروش" in engine.predict_next_words("گزارش")
    assert "ماهانه" in engine.predict_next_words("فروش")
    assert engine.get_word_boost("فروش") >= 1.0


def test_save_and_reload(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)

    engine.learn_transition("هوش", "مصنوعی")
    engine.save()

    assert model_file.is_file()

    # Create new instance loading the same file
    engine2 = UserLearningEngine(storage_path=model_file)
    predictions = engine2.predict_next_words("هوش")
    assert "مصنوعی" in predictions


def test_top_learned_completions(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)

    engine.learn_word("برنامه‌نویسی")
    engine.learn_word("برنامه‌نویسی")
    engine.learn_word("برنامه")

    completions = engine.top_learned_completions("برنامه")
    assert "برنامه‌نویسی" in completions
