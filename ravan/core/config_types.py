"""Config dataclasses and data structures."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_EXCLUDED_APPS = [
    "explorer.exe", "1password.exe", "bitwarden.exe", "keepass.exe", "keepassxc.exe",
    "dashlane.exe", "lockapp.exe", "logonui.exe", "credentialuibroker.exe",
]


@dataclass
class HotkeySpec:
    key: str
    modifiers: list[str] = field(default_factory=list)


@dataclass
class SnippetGroup:
    id: str = ""
    name: str = ""
    matchers: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class Snippet:
    trigger: str
    replacement: str
    enabled: bool = True
    # Snippets 3.0 fields
    is_regex: bool = False
    app_filter: str = ""
    is_image: bool = False
    groups: list[str] = field(default_factory=list)


@dataclass
class Theme:
    name: str = "dark"
    background_color: list[int] = field(default_factory=lambda: [30, 30, 30, 230])
    text_color: list[int] = field(default_factory=lambda: [240, 240, 240, 255])
    highlight_color: list[int] = field(default_factory=lambda: [70, 130, 180, 255])
    font_size: float = 14.0
    corner_radius: float = 6.0

    @classmethod
    def dark(cls) -> Theme:
        return cls(
            name="dark",
            background_color=[32, 33, 36, 235],
            text_color=[241, 243, 244, 255],
            highlight_color=[66, 133, 244, 255],
            font_size=14.0,
            corner_radius=8.0,
        )

    @classmethod
    def light(cls) -> Theme:
        return cls(
            name="light",
            background_color=[255, 255, 255, 240],
            text_color=[32, 33, 36, 255],
            highlight_color=[26, 115, 232, 255],
            font_size=14.0,
            corner_radius=8.0,
        )

    @classmethod
    def high_contrast(cls) -> Theme:
        return cls(
            name="high_contrast",
            background_color=[0, 0, 0, 255],
            text_color=[255, 255, 255, 255],
            highlight_color=[255, 255, 0, 255],
            font_size=15.0,
            corner_radius=4.0,
        )
