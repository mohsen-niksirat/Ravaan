import pytest

from ravan.platform.clipboard import get_clipboard_text, set_clipboard_text

pytestmark = pytest.mark.windows


def test_clipboard_read_write_unicode():
    sample = "متن تستی کلیپ‌بورد روان 123"
    assert set_clipboard_text(sample) is True
    read_back = get_clipboard_text()
    assert read_back == sample
