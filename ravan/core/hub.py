"""Ravaan Hub registry fetcher, SHA-256 package verifier, cache, and installer."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ravan.core.config import Snippet, config_dir
from ravan.core.config_types import SnippetGroup
from ravan.core.package import (
    PackageIntegrityError,
    export_package,
    extract_package_groups,
    import_package,
    inspect_package,
)

log = logging.getLogger(__name__)

DEFAULT_HUB_INDEX_URL = "https://raw.githubusercontent.com/mohsen-niksirat/Ravaan/main/hub/index.json"
DEFAULT_CACHE_TTL_SEC = 6 * 3600

HUB_CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("all", "همه بسته‌ها", "All Packs"),
    ("official", "نامه‌های اداری", "Official Letters"),
    ("coding", "پرامپت و کدنویسی", "Coding Prompts"),
    ("medical_legal", "پزشکی و حقوقی", "Medical & Legal"),
    ("proverbs", "ضرب‌المثل و ایموجی", "Proverbs & Symbols"),
)


@dataclass(frozen=True)
class HubPack:
    """Metadata descriptor for a community `.ravaanpack` bundle in Ravaan Hub."""

    pack_id: str
    version: str
    category: str
    title_en: str
    title_fa: str
    description_en: str
    description_fa: str
    author: str
    download_url: str
    sha256: str = ""
    snippet_count: int = 0
    verified: bool = True
    tags: tuple[str, ...] = ()
    preview_items: tuple[tuple[str, str], ...] = ()
    builtin_snippets: tuple[dict[str, Any], ...] = field(default=(), repr=False)


def parse_semver(version_str: str) -> tuple[int, ...]:
    """Parse semantic version string cleanly into numeric comparison tuple."""
    parts: list[int] = []
    for raw in str(version_str or "0").lstrip("vV").split("."):
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer_version(candidate: str, current: str) -> bool:
    """Return True if `candidate` represents a strictly higher semver than `current`."""
    return parse_semver(candidate) > parse_semver(current)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _builtin_packs() -> tuple[HubPack, ...]:
    official = (
        {"trigger": ";bism", "replacement": "به نام خداوند بخشنده و مهربان\n"},
        {"trigger": ";dear", "replacement": "با سلام و احترام،\nاحتراماً به استحضار می‌رساند "},
        {"trigger": ";regards", "replacement": "با تشکر و احترام فراوان\n{clipboard}"},
        {"trigger": ";attach", "replacement": "فایل پیوست جهت بررسی و اقدام مقتضی تقدیم حضور می‌گردد."},
        {"trigger": ";req", "replacement": "خواهشمند است دستور فرمایید اقدام لازم در اسرع وقت مبذول گردد."},
        {"trigger": ";date", "replacement": "تاریخ: {date_fa}"},
    )
    coding = (
        {"trigger": ";review", "replacement": "Review this diff for correctness, security flaws, edge cases, and clarity:"},
        {"trigger": ";commit", "replacement": "feat(core): summarize concise behavioral change"},
        {"trigger": ";fixbug", "replacement": "Root cause analysis:\n1. Reproduction steps\n2. Failing edge case\n3. Minimal verified fix"},
        {"trigger": ";pydoc", "replacement": '"""Brief single-line summary.\n\n    Args:\n        param: Description.\n    """'},
        {"trigger": ";persianui", "replacement": "با رعایت نیم‌فاصله استاندارد، راست‌به‌چپ بودن (RTL) و فونت Vazirmatn پیاده‌سازی شود."},
    )
    medical_legal = (
        {"trigger": ";rx", "replacement": "تشخیص بالینی اولیه و برنامه درمانی پیشنهادی بیمار به شرح زیر ثبت گردید:"},
        {"trigger": ";followup", "replacement": "توصیه به پیگیری مجدد ظرف ۱۴ روز و انجام آزمایش‌های تکمیلی طبق دستور پزشک معالج."},
        {"trigger": ";contract", "replacement": "این قرارداد در تاریخ {date_fa} بین طرفین با اهلیت کامل قانونی تنظیم و امضا گردید."},
        {"trigger": ";clause", "replacement": "تبصره: کلیه اختلافات ناشی از تفسیر یا اجرای این بند بدواً از طریق مذاکره مسالمت‌آمیز حل‌وفصل می‌گردد."},
        {"trigger": ";confidential", "replacement": "کلیه اطلاعات و مستندات مبادله‌شده محرمانه تلقی شده و افشای آن بدون رضایت کتبی ممنوع است."},
    )
    proverbs = (
        {"trigger": ";sabr", "replacement": "گر صبر کنی ز غوره حلوا سازی"},
        {"trigger": ";khosh", "replacement": "خوش آن که هر دو جهان را به یک نفس بفروشد"},
        {"trigger": ";check", "replacement": "✓"},
        {"trigger": ";arrow", "replacement": "←"},
        {"trigger": ";zwnj", "replacement": "\u200c"},
        {"trigger": ";thanks", "replacement": "سپاسگزارم از لطف و همراهی ارزشمند شما 🌸"},
    )
    specs = [
        ("official-letters-fa", "1.2.0", "official", "Official Persian Letters", "نامه‌های اداری فارسی", "Formal greetings, closings & official correspondence templates with ZWNJ.", "الگوهای رسمی نامه‌نگاری اداری، شروع و پایان نامه با رعایت دقیق نیم‌فاصله.", "Ravaan Team", official),
        ("dev-coding-prompts", "1.1.0", "coding", "Developer & AI Prompts", "پرامپت و ابزار برنامه‌نویسان", "Code review templates, conventional commits, docstrings & Persian RTL checklists.", "پرامپت‌های بازبینی کد، کامیت استاندارد، داک‌استرینگ و چک‌لیست RTL.", "Ravaan Community", coding),
        ("medical-legal-fa", "1.0.0", "medical_legal", "Medical & Legal Terms", "اصطلاحات پزشکی و حقوقی", "Standardized Persian clinical notes and formal contractual clauses.", "عبارات استاندارد گزارش بالینی، قراردادهای حقوقی و بندهای محرمانگی.", "Mohsen N.", medical_legal),
        ("proverbs-symbols-fa", "1.3.0", "proverbs", "Persian Proverbs & Symbols", "ضرب‌المثل و نشانگرهای تایپی", "Classic Persian proverbs plus quick Unicode arrows, checks, and ZWNJ triggers.", "ضرب‌المثل‌های فارسی به همراه میانبر فوری تیک، فلش و کاراکتر نیم‌فاصله.", "Ravaan Community", proverbs),
    ]
    packs: list[HubPack] = []
    for pid, ver, cat, t_en, t_fa, d_en, d_fa, auth, items in specs:
        preview = tuple((it["trigger"], it["replacement"].strip().splitlines()[0][:60]) for it in items[:4])
        packs.append(
            HubPack(
                pack_id=pid, version=ver, category=cat, title_en=t_en, title_fa=t_fa,
                description_en=d_en, description_fa=d_fa, author=auth,
                download_url=f"builtin://{pid}", sha256="", snippet_count=len(items),
                verified=True, tags=(cat, "fa"), preview_items=preview, builtin_snippets=items,
            )
        )
    return tuple(packs)


BUILTIN_HUB_PACKS: tuple[HubPack, ...] = _builtin_packs()
_BUILTIN_MAP: dict[str, HubPack] = {p.pack_id: p for p in BUILTIN_HUB_PACKS}


def _pack_from_dict(raw: dict[str, Any]) -> HubPack | None:
    pid = str(raw.get("pack_id") or raw.get("id") or "").strip()
    url = str(raw.get("download_url") or "").strip()
    if not pid or not url:
        return None
    base = _BUILTIN_MAP.get(pid)
    raw_prev = raw.get("preview_items", ())
    prev = tuple((str(it[0]), str(it[1])) for it in raw_prev if isinstance(it, (list, tuple)) and len(it) >= 2)
    return HubPack(
        pack_id=pid,
        version=str(raw.get("version", "1.0.0")),
        category=str(raw.get("category", "official")),
        title_en=str(raw.get("title_en") or raw.get("title") or pid),
        title_fa=str(raw.get("title_fa") or raw.get("title_en") or pid),
        description_en=str(raw.get("description_en") or raw.get("description") or ""),
        description_fa=str(raw.get("description_fa") or raw.get("description_en") or ""),
        author=str(raw.get("author", "Community")),
        download_url=url,
        sha256=str(raw.get("sha256", "")).strip().lower(),
        snippet_count=int(raw.get("snippet_count", len(prev))),
        verified=bool(raw.get("verified", True)),
        tags=tuple(str(t) for t in raw.get("tags", ())),
        preview_items=prev or (base.preview_items if base else ()),
        builtin_snippets=base.builtin_snippets if base else (),
    )


class HubManager:
    """Fetches, caches, SHA-256 verifies, installs, updates, and uninstalls Hub packs."""

    def __init__(self, base_dir: Path | str | None = None, index_url: str = DEFAULT_HUB_INDEX_URL) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else (config_dir() / "hub")
        self.index_url = index_url
        self.cache_path = self.base_dir / "hub_cache.json"
        self.state_path = self.base_dir / "hub_installed.json"
        self.packs_dir = self.base_dir / "packs"

    def _read_installed_map(self) -> dict[str, dict[str, Any]]:
        if not self.state_path.is_file():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001
            return {}

    def _write_installed_map(self, data: dict[str, dict[str, Any]]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def installed_info(self, pack_id: str) -> dict[str, Any] | None:
        return self._read_installed_map().get(pack_id)

    def is_installed(self, pack_id: str) -> bool:
        return pack_id in self._read_installed_map()

    def has_update(self, pack: HubPack) -> bool:
        info = self.installed_info(pack.pack_id)
        return bool(info and is_newer_version(pack.version, str(info.get("version", "0.0.0"))))

    def fetch_index(
        self,
        *,
        force_refresh: bool = False,
        cache_ttl_sec: int = DEFAULT_CACHE_TTL_SEC,
        timeout: float = 6.0,
    ) -> list[HubPack]:
        """Return Hub packs from cache or remote JSON index, falling back to curated packs."""
        if not force_refresh and self.cache_path.is_file():
            try:
                cached = json.loads(self.cache_path.read_text(encoding="utf-8"))
                fetched_at = float(cached.get("fetched_at", 0.0))
                if (time.time() - fetched_at) <= cache_ttl_sec:
                    parsed = [p for raw in cached.get("packs", []) if isinstance(raw, dict) and (p := _pack_from_dict(raw))]
                    if parsed:
                        return parsed
            except Exception:  # noqa: BLE001
                pass

        try:
            req = urllib.request.Request(self.index_url, headers={"User-Agent": "Ravaan-Hub/3.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_json = json.loads(resp.read().decode("utf-8"))
            raw_packs = raw_json.get("packs", raw_json) if isinstance(raw_json, dict) else raw_json
            if isinstance(raw_packs, list):
                parsed = [p for it in raw_packs if isinstance(it, dict) and (p := _pack_from_dict(it))]
                if parsed:
                    self.base_dir.mkdir(parents=True, exist_ok=True)
                    self.cache_path.write_text(
                        json.dumps({"fetched_at": time.time(), "packs": raw_packs}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    return parsed
        except (urllib.error.URLError, json.JSONDecodeError, OSError, ValueError) as exc:
            log.debug("Hub remote fetch fell back to offline index: %s", exc)

        return list(BUILTIN_HUB_PACKS)

    def _materialize_package(self, pack: HubPack, timeout: float = 20.0) -> Path:
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        dest = self.packs_dir / f"{pack.pack_id}.ravaanpack"

        if pack.download_url.startswith("builtin://"):
            snips = [Snippet(trigger=s["trigger"], replacement=s["replacement"], groups=[pack.category]) for s in pack.builtin_snippets]
            grp = [SnippetGroup(id=pack.category, name=pack.title_en)]
            export_package(
                snips, dest, name=pack.title_en, author=pack.author,
                description_en=pack.description_en, description_fa=pack.description_fa, groups=grp,
            )
            return dest

        if not pack.download_url.startswith("https://"):
            raise ValueError(f"Unsafe Hub download scheme rejected: {pack.download_url}")

        part = self.packs_dir / f"{pack.pack_id}.ravaanpack.part"
        part.unlink(missing_ok=True)
        try:
            req = urllib.request.Request(pack.download_url, headers={"User-Agent": "Ravaan-Hub/3.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp, part.open("wb") as out_fh:
                while chunk := resp.read(65536):
                    out_fh.write(chunk)
            if pack.sha256:
                actual = _sha256_file(part)
                if actual != pack.sha256.lower():
                    raise PackageIntegrityError(
                        f"Archive SHA-256 mismatch for '{pack.pack_id}' (expected {pack.sha256[:8]}, got {actual[:8]})"
                    )
            shutil.move(str(part), str(dest))
            return dest
        except Exception:
            part.unlink(missing_ok=True)
            raise

    def install_pack(
        self,
        pack: HubPack,
        existing_snippets: list[Snippet],
        existing_groups: list[SnippetGroup] | None = None,
        *,
        replace_existing: bool = True,
        timeout: float = 20.0,
    ) -> tuple[list[Snippet], list[SnippetGroup], dict[str, Any]]:
        """Download (or materialize), SHA-256 verify, and install a `.ravaanpack` bundle."""
        pkg_path = self._materialize_package(pack, timeout=timeout)
        manifest = inspect_package(pkg_path)
        pkg_snips = import_package(pkg_path, replace_existing=replace_existing, existing_snippets=existing_snippets)
        pkg_groups = extract_package_groups(manifest)

        merged_groups = list(existing_groups or [])
        seen_ids = {g.id for g in merged_groups}
        for grp in pkg_groups:
            if grp.id and grp.id not in seen_ids:
                merged_groups.append(grp)
                seen_ids.add(grp.id)

        installed_triggers = [str(s.get("trigger", "")).strip() for s in manifest.get("snippets", []) if s.get("trigger")]
        state = self._read_installed_map()
        state[pack.pack_id] = {
            "version": pack.version,
            "sha256": pack.sha256 or _sha256_file(pkg_path),
            "triggers": installed_triggers,
            "installed_at": time.time(),
        }
        self._write_installed_map(state)
        return pkg_snips, merged_groups, manifest

    def uninstall_pack(self, pack_id: str, existing_snippets: list[Snippet]) -> list[Snippet]:
        """Remove triggers belonging solely to `pack_id` and clear its install record."""
        state = self._read_installed_map()
        info = state.pop(pack_id, None)
        self._write_installed_map(state)
        pkg_file = self.packs_dir / f"{pack_id}.ravaanpack"
        pkg_file.unlink(missing_ok=True)
        if not info:
            return list(existing_snippets)
        # Keep triggers still claimed by other installed packs
        remaining_claimed = {trig for item in state.values() for trig in item.get("triggers", [])}
        to_remove = set(info.get("triggers", [])) - remaining_claimed
        return [s for s in existing_snippets if s.trigger not in to_remove]
