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


def test_empty_prefix():
    pred = _pred()
    assert pred.predict("", "", 5) == []


# convenience: CandidateKind.is_completion isn't real; remove above helper
