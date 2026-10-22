"""Release build automation script for Ravaan.

Builds standalone executable via PyInstaller, packages portable ZIP with
bilingual documentation, optionally compiles Inno Setup installer if ISCC is
available, and generates standard GNU SHA256SUMS.txt.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.generate_hashes import (
    format_markdown_table,
    format_sha256sums,
    generate_checksums,
    render_release_notes,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_iscc() -> Path | None:
    """Locate Inno Setup Compiler executable."""
    in_path = shutil.which("iscc")
    if in_path:
        return Path(in_path)

    standard_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
    ]
    for p in standard_paths:
        if p.is_file():
            return p
    return None


def build_pyinstaller() -> int:
    """Run PyInstaller using ravan.spec."""
    spec_file = REPO_ROOT / "ravan.spec"
    if not spec_file.is_file():
        print(f"Error: spec file not found at {spec_file}", file=sys.stderr)
        return 1

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def create_portable_zip(version: str, dist_dir: Path) -> Path:
    """Package standalone portable archive with documentation."""
    zip_path = dist_dir / f"Ravaan-Portable-{version}.zip"
    exe_path = dist_dir / "Ravaan.exe"

    if not exe_path.is_file():
        raise FileNotFoundError(f"Binary not found: {exe_path}. Build step must run first.")

    doc_files = [
        (REPO_ROOT / "README.md", "README.md"),
        (REPO_ROOT / "README.fa.md", "README.fa.md"),
        (REPO_ROOT / "LICENSE", "LICENSE"),
        (REPO_ROOT / "docs" / "SECURITY_FAQ.md", "docs/SECURITY_FAQ.md"),
        (REPO_ROOT / "docs" / "SMARTSCREEN.md", "docs/SMARTSCREEN.md"),
    ]

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, "Ravaan.exe")
        for src, arcname in doc_files:
            if src.is_file():
                zf.write(src, arcname)

    print(f"Created portable bundle: {zip_path} ({zip_path.stat().st_size / (1024*1024):.2f} MB)")
    return zip_path


def compile_inno_setup(version: str) -> int:
    """Compile Inno Setup installer if compiler is available."""
    iscc = find_iscc()
    if not iscc:
        print("Note: Inno Setup (ISCC) not found on system. Skipping installer compilation.")
        return 0

    iss_file = REPO_ROOT / "installer" / "setup.iss"
    cmd = [str(iscc), f"/DMyAppVersion={version}", str(iss_file)]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and package Ravaan release artifacts.")
    import ravan

    default_ver = getattr(ravan, "__version__", "2.0.0")
    parser.add_argument("--version", default=default_ver, help=f"Release version (default: {default_ver})")
    parser.add_argument("--skip-pyinstaller", action="store_true", help="Skip PyInstaller build step")
    parser.add_argument("--skip-installer", action="store_true", help="Skip Inno Setup compilation")
    parser.add_argument("--dist-dir", default=None, help="Custom dist directory")
    args = parser.parse_args(argv)

    dist_dir = Path(args.dist_dir) if args.dist_dir else (REPO_ROOT / "dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_pyinstaller:
        print("\n--- 1. Building Executable via PyInstaller ---")
        code = build_pyinstaller()
        if code != 0:
            print("PyInstaller build failed.", file=sys.stderr)
            return code

    if (dist_dir / "Ravaan.exe").is_file():
        print("\n--- 2. Creating Portable ZIP Bundle ---")
        create_portable_zip(args.version, dist_dir)

    if not args.skip_installer:
        print("\n--- 3. Compiling Inno Setup Installer ---")
        code = compile_inno_setup(args.version)
        if code != 0:
            print("Inno Setup compilation failed.", file=sys.stderr)
            return code

    print("\n--- 4. Computing Checksums & Release Notes ---")
    checksums = generate_checksums(dist_dir)
    table_md = format_markdown_table(checksums) if checksums else "*(No artifacts found)*"

    sums_path = dist_dir / "SHA256SUMS.txt"
    sums_path.write_text(format_sha256sums(checksums), encoding="utf-8")
    print(f"Wrote GNU checksums: {sums_path}")

    notes_path = dist_dir / "RELEASE_NOTES.md"
    rendered_notes = render_release_notes(args.version, table_md)
    notes_path.write_text(rendered_notes, encoding="utf-8")
    print(f"Wrote release notes: {notes_path}")

    print("\nArtifacts and Checksums:")
    print(table_md)
    print("\nRelease build process completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
