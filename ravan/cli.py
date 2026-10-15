"""CLI diagnostics: language, caret, layout conversion."""

from __future__ import annotations

import argparse
import sys
import time


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser(prog="ravan-cli", description="Ravan diagnostics")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lang", help="Print current keyboard language")
    sub.add_parser("caret", help="Print caret / cursor position")
    p_convert = sub.add_parser("convert", help="Convert a word EN↔FA layout")
    p_convert.add_argument("word")
    p_predict = sub.add_parser("predict", help="Show prediction candidates")
    p_predict.add_argument("prefix")
    p_predict.add_argument("-n", type=int, default=5)
    p_hook = sub.add_parser("hook", help="Print raw keyboard hook events (Ctrl+C to stop)")
    p_hook.add_argument("-t", "--seconds", type=float, default=10.0)
    p_inject = sub.add_parser("inject", help="Inject text into the focused field (diagnostic)")
    p_inject.add_argument("text")

    args = parser.parse_args(argv)

    if sys.platform != "win32" and args.cmd in {"lang", "caret", "hook"}:
        print("This command requires Windows.", file=sys.stderr)
        return 1

    if args.cmd == "lang":
        from ravan.platform.lang import current_language, language_label

        info = current_language()
        if info is None:
            print("No foreground window / language")
            return 1
        print(f"{language_label(info)}  tag={info.tag}  name={info.name}  hkl={info.hkl:#x}")
        return 0

    if args.cmd == "caret":
        from ravan.platform.caret import get_caret_rect

        r = get_caret_rect()
        print(f"x={r.x} y={r.y} w={r.width} h={r.height}")
        return 0

    if args.cmd == "convert":
        from ravan.core.layout import LayoutMapper

        mapper = LayoutMapper()
        out = mapper.convert_word(args.word)
        print(out if out is not None else "(unconvertible)")
        return 0

    if args.cmd == "predict":
        from ravan.core.config import Config
        from ravan.core.predictor import DictPredictor

        pred = DictPredictor.from_config(Config())
        for c in pred.predict(args.prefix, "", args.n):
            print(f"{c.score:.4f}  {c.kind.name:12}  {c.text}")
        return 0

    if args.cmd == "hook":
        from ravan.platform.hook import KeyboardHook

        print(f"Listening for {args.seconds}s…")
        hook = KeyboardHook()
        hook.start()
        end = time.monotonic() + args.seconds
        try:
            while time.monotonic() < end:
                try:
                    ev = hook.events.get(timeout=0.2)
                except Exception:
                    continue
                if ev.is_key_down:
                    print(f"vk={ev.vk_code} scan={ev.scan_code} flags={ev.flags}")
        finally:
            hook.stop()
        return 0

    if args.cmd == "inject":
        from ravan.platform.inject import inject_text

        count = inject_text(args.text)
        print(f"Injected {len(args.text)} chars into the focused field")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
