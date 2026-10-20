"""Dictionary binary compiler for Ravaan.

Compiles UTF-8 word-frequency lists (.txt) into compact, mmap-able binary index (.bin)
files for sub-millisecond cold start and zero-heap lookup.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ravan.core.dict import compile_dict_binary  # noqa: E402


def main() -> int:
    base_dir = repo_root / "ravan" / "data"
    fa_txt = base_dir / "words_fa.txt"
    fa_bin = base_dir / "words_fa.bin"
    en_txt = base_dir / "words_en.txt"
    en_bin = base_dir / "words_en.bin"

    print("Compiling Persian dictionary...")
    fa_count = compile_dict_binary(fa_txt, fa_bin)
    print(f"Persian dictionary compiled: {fa_count:,} words ({fa_bin.stat().st_size / (1024*1024):.2f} MB)")

    print("Compiling English dictionary...")
    en_count = compile_dict_binary(en_txt, en_bin)
    print(f"English dictionary compiled: {en_count:,} words ({en_bin.stat().st_size / (1024*1024):.2f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
