from ravan.core.config import Config
from ravan.core.predictor import DictPredictor


def _pred() -> DictPredictor:
    return DictPredictor.from_config(Config())


def test_english_completion():
    pred = _pred()
    results = pred.predict("pro", "", 5)
    assert results
    assert all(c.text.startswith("pro") for c in results)


def test_prediction_completions_first():
    pred = _pred()
    results = pred.predict("hel", "", 5)
    assert results
    # First entry should be a COMPLETION (hello), not a fuzzy fix
    assert results[0].kind.name == "COMPLETION"
    assert results[0].text.lower().startswith("hel")


def test_correct_rejects_dictionary_word():
    pred = _pred()
    assert pred.correct("the") is None


def test_correct_rejects_prefix():
    # "hel" is a prefix of "hello" (len 5, within +2) → user is still typing → no autocorrect
    pred = _pred()
    assert pred.correct("hel") is None


def test_correct_typo_teh():
    # "teh" is a typo of "the"; its only completion is "tehran" (too long to be
    # what a 3-letter typo means) → autocorrect to "the"
    pred = _pred()
    cand = pred.correct("teh")
    assert cand is not None
    assert cand.text == "the"


def test_correct_short_word_rejected():
    pred = _pred()
    assert pred.correct("te") is None


def test_correct_unknown_long_word_returns_none():
    pred = _pred()
    assert pred.correct("xyzzyqwxyz") is None


def test_ranking_hierarchy_custom_over_frequency():
    from ravan.core.dict import DictEntry, Dictionary, Language

    # Custom word has rank=0, frequent word has rank=1
    custom_entry = DictEntry(word="project_secret", rank=0, frequency=10000000)
    freq_entry = DictEntry(word="project", rank=1, frequency=50000)
    en_dict = Dictionary([freq_entry, custom_entry], Language.ENGLISH)
    pred = DictPredictor(english=en_dict, persian=None)

    results = pred.predict("proj", "", 5)
    assert len(results) == 2
    # Custom word must rank #1 over standard frequent word
    assert results[0].text == "project_secret"
    assert results[1].text == "project"


def test_adaptive_learning_selection_boost():
    from ravan.core.dict import DictEntry, Dictionary, Language

    e1 = DictEntry(word="program", rank=1, frequency=10000)
    e2 = DictEntry(word="project", rank=2, frequency=5000)
    en_dict = Dictionary([e1, e2], Language.ENGLISH)
    pred = DictPredictor(english=en_dict, persian=None)

    # Initial state: program outranks project due to rank 1 vs 2
    initial = pred.predict("pro", "", 5)
    assert initial[0].text == "program"
    assert initial[1].text == "project"

    # User repeatedly chooses 'project'
    for _ in range(5):
        pred.record_selection("project")

    # Adaptive boost: 'project' now ranks #1 above 'program'
    boosted = pred.predict("pro", "", 5)
    assert boosted[0].text == "project"
    assert boosted[0].score > boosted[1].score


def test_next_word_prediction(tmp_path):
    from ravan.core.events import CandidateKind
    from ravan.core.learning import UserLearningEngine

    learning = UserLearningEngine(storage_path=tmp_path / "learning.json")
    pred = DictPredictor(english=None, persian=None, learning_engine=learning)

    # With seeded Persian bigrams, "سلام" should predict "عزیز", "علیکم", etc.
    results = pred.predict(prefix="", context="سلام", limit=5)
    assert len(results) > 0
    assert results[0].kind == CandidateKind.NEXT_WORD
    assert results[0].text in ("عزیز", "علیکم", "وقتتون")


def test_learned_completion_boost(tmp_path):
    from ravan.core.dict import DictEntry, Dictionary, Language
    from ravan.core.learning import UserLearningEngine

    learning = UserLearningEngine(storage_path=tmp_path / "learning.json")
    e1 = DictEntry(word="ساعت", rank=1, frequency=1000)
    fa_dict = Dictionary([e1], Language.PERSIAN)
    pred = DictPredictor(english=None, persian=fa_dict, learning_engine=learning)

    # Initially only 'ساعت'
    res = pred.predict("سا", "", 5)
    assert [c.text for c in res] == ["ساعت"]

    # User types and selects a new word "ساختمان"
    pred.record_selection("ساختمان", context="زیبایی")

    res2 = pred.predict("سا", "", 5)
    texts = [c.text for c in res2]
    assert "ساختمان" in texts
    # Newly learned word gets highest priority
    assert texts[0] == "ساختمان"


def test_autocorrect_modes():
    # Test "off" mode
    pred_off = DictPredictor.from_config(Config(autocorrect_mode="off"))
    assert pred_off.correct("teh") is None

    # Test "safe" mode
    pred_safe = DictPredictor.from_config(Config(autocorrect_mode="safe"))
    assert pred_safe.correct("teh") is not None
    assert pred_safe.correct("teh").text == "the"
    # "hel" is a prefix of "hello", so safe mode must reject it
    assert pred_safe.correct("hel") is None

    # Test "normal" mode
    pred_normal = DictPredictor.from_config(Config(autocorrect_mode="normal"))
    assert pred_normal.correct("teh") is not None
    assert pred_normal.correct("teh").text == "the"


def test_ignored_words_suppresses_autocorrect():
    cfg = Config(ignored_words=["teh", "mycustomword"])
    pred = DictPredictor.from_config(cfg)
    # Even though 'teh' is a known typo for 'the', it is ignored
    assert pred.correct("teh") is None
    assert pred.correct("TEH") is None


def test_session_suppression():
    pred = _pred()
    assert pred.correct("teh") is not None
    pred.suppress_session_word("teh")
    # Now it is suppressed for this session
    assert pred.correct("teh") is None


def test_prediction_latency_benchmark():
    import time

    pred = _pred()
    prefixes = ["th", "pro", "com", "سلام", "بر", "دان", "in", "te", "هم", "یک"]
    warmup = pred.predict("th", "", 5)
    warmup_fa = pred.predict("سلام", "", 5)
    assert warmup and warmup_fa

    # Measure 100 queries
    start = time.perf_counter()
    iterations = 100
    for i in range(iterations):
        p = prefixes[i % len(prefixes)]
        res = pred.predict(p, "", 5)
        assert len(res) > 0
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000.0
    # Must remain strictly < 15ms per keystroke (usually < 1ms)
    assert avg_ms < 15.0, f"Average latency too high: {avg_ms:.2f}ms"

