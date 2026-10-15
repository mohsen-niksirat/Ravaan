from ravan.core.dict import Dictionary, levenshtein


def test_levenshtein():
    assert levenshtein("the", "teh") == 2
    assert levenshtein("cat", "bat") == 1
    assert levenshtein("the", "the") == 0
    assert levenshtein("", "abc") == 3


def test_levenshtein_banded():
    assert levenshtein("hello", "hallo", max_dist=1) == 1
    assert levenshtein("abc", "xxxxxx", max_dist=1) == 2  # > max_dist short-circuit
    assert levenshtein("abc", "xxxxxx", max_dist=None) == 6


def test_completions_process():
    dict_ = Dictionary.english()
    results = dict_.completions("pro", 5)
    assert results
    assert all(e.word.startswith("pro") for e in results)


def test_fuzzy_the():
    dict_ = Dictionary.english()
    results = dict_.fuzzy_matches("teh", 2, 5)
    assert any(e.word == "the" for e, _ in results)


def test_persian_completions():
    dict_ = Dictionary.persian()
    results = dict_.completions("بر", 5)
    assert results


def test_rank_of_the():
    dict_ = Dictionary.english()
    assert dict_.rank_of("the") == 1


def test_no_duplicates():
    dict_ = Dictionary.persian()
    words = [e.word for e in dict_.entries]
    assert len(words) == len(set(words))
