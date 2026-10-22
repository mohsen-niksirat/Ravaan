"""Compute SHA256 checksums of distribution artifacts for release notes and package managers."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Compute hex SHA256 digest of a file in streaming chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(128 * 1024):
            h.update(chunk)
    return h.hexdigest()


def generate_checksums(dist_dir: Path | None = None) -> list[tuple[str, str, int]]:
    """Return list of (filename, sha256, size_bytes) for files in dist directory."""
    target_dir = dist_dir or (Path(__file__).resolve().parent.parent / "dist")
    if not target_dir.is_dir():
        return []

    results = []
    for p in sorted(target_dir.iterdir()):
        if p.is_file() and (p.suffix.lower() in (".exe", ".zip", ".msi", ".tar.gz", ".whl")):
            results.append((p.name, sha256_file(p), p.stat().st_size))
    return results


def format_markdown_table(checksums: list[tuple[str, str, int]]) -> str:
    """Format checksums into a markdown table for release notes."""
    lines = [
        "| File | Size | SHA256 Checksum |",
        "| :--- | :--- | :--- |",
    ]
    for name, sha, size in checksums:
        size_mb = size / (1024 * 1024)
        lines.append(f"| `{name}` | {size_mb:.2f} MB | `{sha}` |")
    return "\n".join(lines)


def format_sha256sums(checksums: list[tuple[str, str, int]]) -> str:
    """Format standard GNU coreutils compatible SHA256SUMS.txt (<hash>  <filename>)."""
    lines = [f"{sha}  {name}" for name, sha, _ in checksums]
    return "\n".join(lines) + ("\n" if lines else "")


def render_release_notes(version: str, table_md: str) -> str:
    """Render release notes using docs/RELEASE_NOTES_TEMPLATE.md."""
    repo_dir = Path(__file__).resolve().parent.parent
    tmpl_path = repo_dir / "docs" / "RELEASE_NOTES_TEMPLATE.md"
    if tmpl_path.is_file():
        content = tmpl_path.read_text(encoding="utf-8")
        content = content.replace("{{VERSION}}", version)
        content = content.replace("{{CHECKSUM_TABLE}}", table_md)
        return content

    return f"# Ravaan v{version}\n\n## Checksums\n\n{table_md}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate artifact checksums and release notes.")
    import ravan

    default_ver = getattr(ravan, "__version__", "2.0.0")
    parser.add_argument("--version", default=default_ver, help="Release version string")
    parser.add_argument("--write-notes", default=None, help="Path to write rendered release notes")
    parser.add_argument("--write-sums", default=None, help="Path to write standard SHA256SUMS.txt")
    parser.add_argument("--dist", default=None, help="Custom dist directory")
    args = parser.parse_args(argv)

    dist_path = Path(args.dist) if args.dist else None
    results = generate_checksums(dist_path)
    table_md = format_markdown_table(results) if results else "*(No artifacts found)*"

    if args.write_notes:
        notes_path = Path(args.write_notes)
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_release_notes(args.version, table_md)
        notes_path.write_text(rendered, encoding="utf-8")

    if args.write_sums:
        sums_path = Path(args.write_sums)
        sums_path.parent.mkdir(parents=True, exist_ok=True)
        sums_content = format_sha256sums(results)
        sums_path.write_text(sums_content, encoding="utf-8")

    print("\nSHA256 Checksums:\n")
    print(table_md)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
