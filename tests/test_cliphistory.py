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


def test_clipboard_history_pinning_and_persistence(tmp_path):
    storage = tmp_path / "clip.json"
    hist = ClipboardHistory(maxlen=50, storage_path=storage)
    hist.add("normal item 1")
    hist.add("important pin")
    hist.add("normal item 2")

    # Pin the item
    assert hist.is_pinned("important pin") is False
    assert hist.toggle_pin("important pin") is True
    assert hist.is_pinned("important pin") is True

    # Pinned items must appear at the top of items()
    items = hist.items()
    assert items[0] == "important pin"
    assert "normal item 2" in items

    # Verify persistence by creating a second instance from the same file
    hist2 = ClipboardHistory(maxlen=50, storage_path=storage)
    assert hist2.is_pinned("important pin") is True
    items2 = hist2.items()
    assert items2[0] == "important pin"

