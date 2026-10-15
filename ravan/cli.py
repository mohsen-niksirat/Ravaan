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
    p_num = sub.add_parser("num", help="Convert digits between Persian and English")
    p_num.add_argument("text")
    p_norm = sub.add_parser("norm", help="Normalize Persian text (Arabic chars, ZWNJ, punctuation)")
    p_norm.add_argument("text")
    p_norm.add_argument("--digits", choices=["fa", "en", "keep"], default="keep")
    p_jalali = sub.add_parser("jalali", help="Show current or converted Jalali (Shamsi) date")
    p_jalali.add_argument("date", nargs="?", default=None, help="Gregorian date (YYYY-MM-DD) or empty for today")
    p_calc = sub.add_parser("calc", help="Evaluate a math expression (supports Persian digits)")
    p_calc.add_argument("expr", help="Mathematical expression e.g. '1200*1.09' or '۱۲*۵'")
    p_dict = sub.add_parser("dict", help="Manage user custom dictionary")
    p_dict.add_argument("action", choices=["list", "add", "remove"])
    p_dict.add_argument("word", nargs="?", default="")
    p_words = sub.add_parser("words", help="Convert number to Persian words or format thousands")
    p_words.add_argument("number", help="Number to convert e.g. 1250000 or ۱۲۵۰۰۰۰")
    p_words.add_argument("--toman", action="store_true", help="Convert Rial to Toman words (divide by 10)")
    p_words.add_argument("--sep", action="store_true", help="Format with thousands separators")

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

    if args.cmd == "num":
        from ravan.core.normalizer import toggle_digits

        print(toggle_digits(args.text))
        return 0

    if args.cmd == "norm":
        from ravan.core.normalizer import normalize_persian

        print(normalize_persian(args.text, digits=args.digits))
        return 0

    if args.cmd == "jalali":
        from datetime import date
        from ravan.core.jalali import JalaliDate, current_time_str

        if args.date:
            parts = [int(p) for p in args.date.replace("/", "-").split("-")]
            if len(parts) == 3:
                g = date(parts[0], parts[1], parts[2])
                j = JalaliDate.from_gregorian(g)
            else:
                print("Invalid date format. Use YYYY-MM-DD or YYYY/MM/DD", file=sys.stderr)
                return 1
        else:
            j = JalaliDate.today()

        print(f"Jalali ISO:      {j.isoformat_fa()} ({j.isoformat()})")
        print(f"Persian text:    {j.format_persian(include_weekday=False)}")
        print(f"With weekday:    {j.format_persian(include_weekday=True)}")
        if not args.date:
            print(f"Current time:    {current_time_str(persian_digits=True)} ({current_time_str(persian_digits=False)})")
        return 0

    if args.cmd == "calc":
        from ravan.core.calc import calculate

        res = calculate(args.expr)
        if res is not None:
            print(res)
            return 0
        else:
            print("Error: Invalid mathematical expression", file=sys.stderr)
            return 1

    if args.cmd == "dict":
        from ravan.core.user_dict import add_user_word, load_user_words, remove_user_word

        if args.action == "list":
            words = load_user_words()
            if not words:
                print("User custom dictionary is empty.")
            else:
                for w in words:
                    print(w)
            return 0
        elif args.action == "add":
            if not args.word:
                print("Error: Specify a word to add.", file=sys.stderr)
                return 1
            if add_user_word(args.word):
                print(f"Added {args.word!r} to user custom dictionary.")
                return 0
            return 1
        elif args.action == "remove":
            if not args.word:
                print("Error: Specify a word to remove.", file=sys.stderr)
                return 1
            if remove_user_word(args.word):
                print(f"Removed {args.word!r} from user custom dictionary.")
                return 0
            else:
                print(f"Word {args.word!r} not found in user dictionary.")
                return 1

    if args.cmd == "words":
        from ravan.core.num2words import format_thousands, num_to_persian_words, to_toman_words

        if args.sep:
            print(format_thousands(args.number, persian_digits=True))
            return 0
        if args.toman:
            print(to_toman_words(args.number))
            return 0
        print(num_to_persian_words(args.number))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
