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
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="Check for newer versions on GitHub and exit",
    )
    args = parser.parse_args(argv)

    if args.version or args.check_updates:
        if args.version:
            from ravan import __version__

            print(__version__)

        if args.check_updates:
            from ravan.core.updater import check_for_updates

            res = check_for_updates()
            if res.get("error"):
                print(f"Error checking updates: {res['error']}", file=sys.stderr)
                return 1
            if res["has_update"]:
                print(f"Update available: v{res['latest_version']} (current: v{res['current_version']})")
                print(f"Download: {res['release_url']}")
            else:
                print(f"Ravaan is up to date (version {res['current_version']}).")
        return 0


    if sys.platform != "win32":
        print("Ravan currently supports Windows only.", file=sys.stderr)
        return 1

    from ravan.platform import winapi as wapi

    wapi.enable_dpi_awareness()

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
