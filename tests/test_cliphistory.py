from ravan.core.cliphistory import ClipboardHistory


def test_clipboard_history_add_and_dedupe():
    hist = ClipboardHistory(maxlen=5)
    assert hist.add("first item") is True
    assert hist.add("second item") is True
    # Immediate duplicate should be rejected
    assert hist.add("second item") is False
    assert len(hist) == 2
    assert hist.items() == ["second item", "first item"]

    # Re-adding first item should promote it to top
    assert hist.add("first item") is True
    assert hist.items() == ["first item", "second item"]


def test_clipboard_history_ignores_sentinels_and_empty():
    hist = ClipboardHistory(maxlen=5)
    assert hist.add("") is False
    assert hist.add("   ") is False
    assert hist.add("__ravan_sel_check_12345__") is False
    assert len(hist) == 0


def test_clipboard_history_capacity():
    hist = ClipboardHistory(maxlen=3)
    for i in range(5):
        hist.add(f"item-{i}")
    assert len(hist) == 3
    assert hist.items() == ["item-4", "item-3", "item-2"]
