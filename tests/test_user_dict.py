from pathlib import Path

from ravan.core.config import Config
from ravan.core.dict import Dictionary
from ravan.core.predictor import DictPredictor
from ravan.core.user_dict import (
    add_user_word,
    load_user_words,
    remove_user_word,
    save_user_words,
)


def test_user_dict_save_load(tmp_path: Path):
    file_path = tmp_path / "user_words.txt"
    assert load_user_words(file_path) == []

    words = ["customterm", "نیک‌سیرت", "fastapi"]
    assert save_user_words(words, file_path) is True

    loaded = load_user_words(file_path)
    assert loaded == words


def test_add_and_remove_user_word(tmp_path: Path):
    file_path = tmp_path / "user_words.txt"
    assert add_user_word("antigravity", file_path) is True
    assert "antigravity" in load_user_words(file_path)

    # Adding duplicate should not duplicate
    assert add_user_word("antigravity", file_path) is True
    assert load_user_words(file_path).count("antigravity") == 1

    # Remove
    assert remove_user_word("antigravity", file_path) is True
    assert "antigravity" not in load_user_words(file_path)
    assert remove_user_word("antigravity", file_path) is False


def test_dictionary_add_word():
    d = Dictionary.english()
    d.add_word("supercalifragilistic", priority=True)
    assert any(e.word == "supercalifragilistic" for e in d.entries)
    comps = d.completions("supercali", 5)
    assert any(e.word == "supercalifragilistic" for e in comps)


def test_predictor_loads_custom_words(tmp_path: Path, monkeypatch):
    file_path = tmp_path / "user_words.txt"
    save_user_words(["mycustomjargon", "روان‌تایپ"], file_path)

    monkeypatch.setattr("ravan.core.user_dict.user_dict_path", lambda: file_path)

    cfg = Config()
    pred = DictPredictor.from_config(cfg)
    en_preds = [c.text for c in pred.predict("mycustom", "", 5)]
    assert "mycustomjargon" in en_preds

    fa_preds = [c.text for c in pred.predict("روان", "", 5)]
    assert "روان‌تایپ" in fa_preds
