from ravan.core.journal import KeystrokeJournal


def test_last_word():
    j = KeystrokeJournal()
    for ch in "hello world":
        j.push(ch)
    assert j.last_word() == "world"


def test_backspace():
    j = KeystrokeJournal()
    for ch in "hi":
        j.push(ch)
    j.push("\b")
    assert j.text() == "h"


def test_last_word_trailing_spaces():
    j = KeystrokeJournal()
    for ch in "salam ":
        j.push(ch)
    assert j.last_word(allow_trailing_spaces=False) == ""
    assert j.last_word(allow_trailing_spaces=True) == "salam"
    word, trailing = j.last_word_info(allow_trailing_spaces=True)
    assert word == "salam"
    assert trailing == 1

    word_popped, trail_popped = j.pop_last_word_info(allow_trailing_spaces=True)
    assert word_popped == "salam"
    assert trail_popped == 1
    assert j.text() == ""


def test_last_word_multiple_trailing_spaces():
    j = KeystrokeJournal()
    for ch in "first second   ":
        j.push(ch)
    word, trailing = j.last_word_info(allow_trailing_spaces=True)
    assert word == "second"
    assert trailing == 3
    j.pop_last_word_info(allow_trailing_spaces=True)
    assert j.text() == "first "


def test_previous_word():
    j = KeystrokeJournal()
    assert j.previous_word() == ""

    for ch in "salam":
        j.push(ch)
    assert j.previous_word() == ""

    j.push(" ")
    assert j.previous_word() == "salam"

    for ch in "khoob":
        j.push(ch)
    assert j.previous_word() == "salam"

    j.push(" ")
    assert j.previous_word() == "khoob"
