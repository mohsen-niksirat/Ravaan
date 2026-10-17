"""Unit tests for UserLearningEngine v2 (stupid backoff, decay, per-app weighting, export/import)."""

from pathlib import Path

from ravan.core.learning import UserLearningEngine


def test_stupid_backoff_and_interpolation():
    engine = UserLearningEngine(auto_load=False)
    engine.learn_trigram("خیلی", "ممنون", "عزیز")
    engine.learn_transition("ممنون", "شما")
    engine.learn_word("دوست")

    # Score with full trigram match
    s_tri = engine.compute_smoothed_score("عزیز", w2="ممنون", w1="خیلی")
    # Score with bigram fallback
    s_bi = engine.compute_smoothed_score("شما", w2="ممنون", w1="نامرتبط")
    # Score with unigram fallback
    s_uni = engine.compute_smoothed_score("دوست", w2="دیگر", w1="هیچ")

    assert s_tri > s_bi
    assert s_bi > s_uni
    assert s_uni > 0.0


def test_per_app_weighting():
    engine = UserLearningEngine(auto_load=False)
    # Learn 'asyncio' mostly in code editor
    for _ in range(5):
        engine.learn_word("asyncio", app_name="code.exe")
    # Learn 'سلام' in chat app
    for _ in range(5):
        engine.learn_word("سلام", app_name="telegram.exe")

    boost_code = engine.get_word_boost("asyncio", app_name="code.exe")
    boost_chat = engine.get_word_boost("asyncio", app_name="telegram.exe")
    assert boost_code > boost_chat

    cands_code = engine.predict_next_words("", limit=5, app_name="code.exe")
    cands_chat = engine.predict_next_words("", limit=5, app_name="telegram.exe")
    assert isinstance(cands_code, list)
    assert isinstance(cands_chat, list)


def test_exponential_decay():
    engine = UserLearningEngine(auto_load=False)
    engine.learn_word("testword")
    assert engine.word_counts["testword"] >= 1.0

    # Simulate 30 days elapsed
    t0 = engine.last_decay_time
    factor = engine.decay_frequencies(half_life_days=30.0, current_time=t0 + (30 * 86400))
    assert 0.49 <= factor <= 0.51
    assert 0.49 <= engine.word_counts["testword"] <= 0.51

    # Simulate another 90 days (should decay below threshold and be pruned)
    engine.decay_frequencies(half_life_days=30.0, current_time=t0 + (150 * 86400))
    assert "testword" not in engine.word_counts


def test_profile_export_and_import(tmp_path: Path):
    engine = UserLearningEngine(auto_load=False)
    engine.learn_trigram("word1", "word2", "word3", app_name="notepad.exe")

    export_file = tmp_path / "profile.json"
    engine.export_profile(export_file)
    assert export_file.is_file()

    new_engine = UserLearningEngine(auto_load=False)
    imported_count = new_engine.import_profile(export_file, merge=True)
    assert imported_count > 0
    assert "word3" in new_engine.word_counts
    assert new_engine.get_word_boost("word3", app_name="notepad.exe") > 1.0


def test_sentence_prediction():
    engine = UserLearningEngine(auto_load=False)
    # Check seeded phrases
    res1 = engine.predict_sentence_continuations("خوش", prefix="آم", limit=3)
    assert any("خوش آمدید" in s for s in res1)

    res2 = engine.predict_sentence_continuations("thank", prefix="yo", limit=3)
    assert any("thank you" in s.lower() for s in res2)
