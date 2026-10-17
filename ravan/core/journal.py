"""Keystroke journal — tracks recent typed characters for layout conversion."""

from __future__ import annotations

from collections import deque


class KeystrokeJournal:
    def __init__(self, maxlen: int = 256) -> None:
        self._chars: deque[str] = deque(maxlen=maxlen)

    def clear(self) -> None:
        self._chars.clear()

    def push(self, ch: str) -> None:
        if not ch:
            return
        if ch == "\b":
            if self._chars:
                self._chars.pop()
            return
        self._chars.append(ch)

    def text(self) -> str:
        return "".join(self._chars)

    def last_word(self, allow_trailing_spaces: bool = False) -> str:
        word, _ = self.last_word_info(allow_trailing_spaces=allow_trailing_spaces)
        return word

    def last_word_info(self, allow_trailing_spaces: bool = False) -> tuple[str, int]:
        """Return (word, trailing_spaces_count).

        When allow_trailing_spaces is True, trailing spaces are counted and
        the word immediately before them is returned.
        """
        text = self.text()
        if not text:
            return "", 0
        end = len(text)
        trailing_spaces = 0
        if allow_trailing_spaces:
            while end > 0 and text[end - 1] == " ":
                trailing_spaces += 1
                end -= 1
            if end == 0:
                return "", trailing_spaces
        elif end > 0 and text[end - 1].isspace():
            return "", 0

        i = end - 1
        while i >= 0 and not text[i].isspace():
            i -= 1
        return text[i + 1 : end], trailing_spaces

    def pop_last_word(self) -> str:
        word = self.last_word(allow_trailing_spaces=False)
        for _ in word:
            if self._chars:
                self._chars.pop()
        return word

    def pop_last_word_info(self, allow_trailing_spaces: bool = True) -> tuple[str, int]:
        word, trailing = self.last_word_info(allow_trailing_spaces=allow_trailing_spaces)
        total = len(word) + trailing
        for _ in range(total):
            if self._chars:
                self._chars.pop()
        return word, trailing

    def previous_word(self) -> str:
        """Return the completed word immediately before the current typing position."""
        text = self.text()
        words = text.split()
        if not words:
            return ""
        if text and not text[-1].isspace():
            return words[-2] if len(words) >= 2 else ""
        return words[-1]

    def previous_context(self, n: int = 2) -> str:
        """Return the last n completed words immediately before the current typing position."""
        text = self.text()
        words = text.split()
        if not words:
            return ""
        if text and not text[-1].isspace():
            completed = words[:-1]
        else:
            completed = words
        if not completed:
            return ""
        return " ".join(completed[-n:])

    def last_n_words_span(self, n: int = 1) -> tuple[str, int]:
        """Return (span_text, total_chars) for the last n words including intermediate/trailing spaces."""
        text = self.text()
        if not text or n <= 0:
            return "", 0

        end = len(text)
        curr = end
        while curr > 0 and text[curr - 1] == " ":
            curr -= 1

        words_found = 0
        while curr > 0 and words_found < n:
            while curr > 0 and not text[curr - 1].isspace():
                curr -= 1
            words_found += 1
            if words_found >= n:
                break
            while curr > 0 and text[curr - 1].isspace():
                curr -= 1

        start = max(0, curr)
        span_text = text[start:end]
        return span_text, len(span_text)

    def pop_last_n_chars(self, count: int) -> str:
        """Pop and return the last count characters from the journal."""
        popped = []
        for _ in range(min(count, len(self._chars))):
            popped.append(self._chars.pop())
        return "".join(reversed(popped))
