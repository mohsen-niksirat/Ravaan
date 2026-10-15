"""Text expansion snippets."""

from __future__ import annotations

from .config import Config


class SnippetEngine:
    def __init__(self, snippets: list[tuple[str, str]]) -> None:
        self._snippets = snippets

    @classmethod
    def from_config(cls, cfg: Config) -> SnippetEngine:
        return cls([(s.trigger, s.replacement) for s in cfg.snippets])

    def expand(self, word: str) -> str | None:
        for trigger, replacement in self._snippets:
            if trigger == word:
                return replacement
        return None

    def all(self) -> list[tuple[str, str]]:
        return list(self._snippets)
