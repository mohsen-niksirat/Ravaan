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


def test_seeded_trigrams_and_english_transitions(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)

    # Persian seeded trigrams
    pred_fa_1 = engine.predict_next_words("خیلی ممنون", limit=3)
    assert "از" in pred_fa_1
    pred_fa_2 = engine.predict_next_words("به نام", limit=3)
    assert "خدا" in pred_fa_2

    # English seeded transitions & trigrams
    pred_en_1 = engine.predict_next_words("thank you", limit=3)
    assert "very" in pred_en_1
    pred_en_2 = engine.predict_next_words("looking forward", limit=3)
    assert "to" in pred_en_2
    pred_en_3 = engine.predict_next_words("how are", limit=3)
    assert "you" in pred_en_3

    # Fallback to bigram when trigram is not found
    pred_fallback = engine.predict_next_words("some unknown thank", limit=3)
    assert "you" in pred_fallback


def test_learn_trigrams(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)

    engine.learn_trigram("machine", "learning", "models")
    preds = engine.predict_next_words("machine learning", limit=3)
    assert "models" in preds

    # Persist and reload
    engine.save()
    engine2 = UserLearningEngine(storage_path=model_file)
    preds2 = engine2.predict_next_words("machine learning", limit=3)
    assert "models" in preds2


def test_learning_dpapi_encryption_at_rest(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)
    engine.learn_word("رمزگذاری")
    engine.save()

    raw_content = model_file.read_text(encoding="utf-8").strip()
    assert raw_content.startswith(("dpapi:", "mock-dpapi:"))
    assert not raw_content.startswith("{")

    # Transparent reload
    engine2 = UserLearningEngine(storage_path=model_file)
    assert "رمزگذاری" in engine2.word_counts


def test_learning_legacy_plaintext_load(tmp_path: Path):
    import json

    model_file = tmp_path / "learning.json"
    legacy_data = {
        "artifact": "ravaan_learning_profile",
        "version": 3,
        "word_counts": {"قدیمی": 5.0},
        "transitions": {},
        "trigrams": {},
        "app_word_counts": {},
    }
    model_file.write_text(json.dumps(legacy_data), encoding="utf-8")

    engine = UserLearningEngine(storage_path=model_file)
    assert "قدیمی" in engine.word_counts

    # Saving will now encrypt with DPAPI
    engine.save()
    re_saved = model_file.read_text(encoding="utf-8").strip()
    assert re_saved.startswith(("dpapi:", "mock-dpapi:"))


def test_learning_clear_learned_data(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file)
    engine.learn_word("کلمه_خصوصی")
    engine.learn_transition("کلمه_خصوصی", "مخفی")
    assert "کلمه_خصوصی" in engine.word_counts

    engine.clear_learned_data()
    assert "کلمه_خصوصی" not in engine.word_counts
    assert "کلمه_خصوصی" not in engine.transitions

    # Check persistence after clear
    engine2 = UserLearningEngine(storage_path=model_file)
    assert "کلمه_خصوصی" not in engine2.word_counts


def test_learning_disabled_toggle(tmp_path: Path):
    model_file = tmp_path / "learning.json"
    engine = UserLearningEngine(storage_path=model_file, learning_enabled=False)

    engine.learn_word("تست_غیرفعال")
    engine.learn_transition("کلمه_یک", "کلمه_دو")
    engine.learn_trigram("الف", "ب", "ج")

    assert "تست_غیرفعال" not in engine.word_counts
    assert "کلمه_یک" not in engine.transitions
    assert "الف ب" not in engine.trigrams
