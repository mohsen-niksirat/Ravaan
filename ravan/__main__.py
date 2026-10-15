"""python -m ravan"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ravan",
        description="Ravan (روان) — Windows typing assistant",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    args = parser.parse_args(argv)

    if args.version:
        from ravan import __version__

        print(__version__)
        return 0

    if sys.platform != "win32":
        print("Ravan currently supports Windows only.", file=sys.stderr)
        return 1

    from ravan.platform.singleinstance import SingleInstance

    guard = SingleInstance("Ravan")
    if not guard.acquired:
        print("Ravan is already running (tray icon).", file=sys.stderr)
        return 1

    from ravan.ui.app import RavanApp

    RavanApp().start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
