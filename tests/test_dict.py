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


def test_corpus_size():
    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    assert len(en_dict.entries) >= 500
    assert len(fa_dict.entries) >= 10000


def test_load_dictionary_entries_with_frequency(tmp_path):
    from ravan.core.dict import load_dictionary_entries

    f = tmp_path / "test_words.txt"
    f.write_text(
        "# Comment line\n"
        "apple\t50\n"
        "banana\t1000\n"
        "cherry\t300\n"
        "date\n",
        encoding="utf-8",
    )
    entries = load_dictionary_entries(str(f))
    assert len(entries) == 4
    # banana should be ranked #1 due to highest frequency (1000)
    assert entries[0].word == "banana"
    assert entries[0].rank == 1
    # cherry should be ranked #2 (300)
    assert entries[1].word == "cherry"
    assert entries[1].rank == 2
    # apple should be ranked #3 (50)
    assert entries[2].word == "apple"
    assert entries[2].rank == 3
    # date without frequency should follow
    assert entries[3].word == "date"
    assert entries[3].rank == 4


