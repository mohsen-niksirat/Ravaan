"""Compute SHA256 checksums of distribution artifacts for release notes."""

from __future__ import annotations

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
        if p.is_file() and (p.suffix.lower() in (".exe", ".zip", ".tar.gz", ".whl")):
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


def main() -> int:
    results = generate_checksums()
    if not results:
        print("No distribution artifacts found in dist/")
        return 0

    print("\nSHA256 Checksums:\n")
    print(format_markdown_table(results))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
