"""Shared event types used across Ravan threads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class CandidateKind(Enum):
    COMPLETION = auto()
    AUTOCORRECT = auto()
    NEXT_WORD = auto()


@dataclass(frozen=True)
class LanguageInfo:
    tag: str
    name: str
    hkl: int


@dataclass(frozen=True)
class FocusInfo:
    exe_name: str
    hwnd: int


@dataclass(frozen=True)
class Candidate:
    text: str
    score: float
    kind: CandidateKind


@dataclass(frozen=True)
class CharTyped:
    char: str


@dataclass(frozen=True)
class VKeyDown:
    vk: int


@dataclass(frozen=True)
class LanguageChanged:
    info: LanguageInfo


@dataclass(frozen=True)
class FocusChanged:
    info: FocusInfo


@dataclass(frozen=True)
class ConvertHotkeyPressed:
    pass


@dataclass(frozen=True)
class LangIndicatorHotkeyPressed:
    pass


@dataclass(frozen=True)
class CaretMoved:
    x: int
    y: int
    height: int


@dataclass(frozen=True)
class PredictResult:
    candidates: list[Candidate]


@dataclass(frozen=True)
class DismissPopup:
    pass


RavanEvent = (
    CharTyped
    | VKeyDown
    | LanguageChanged
    | FocusChanged
    | ConvertHotkeyPressed
    | LangIndicatorHotkeyPressed
    | CaretMoved
    | PredictResult
    | DismissPopup
)
