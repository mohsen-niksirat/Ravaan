"""Safe, zero-dependency inline mathematical evaluator (Math v2).

Uses Python's AST parser to guarantee security (no eval/exec).
Supports arithmetic operators (+, -, *, /, //, %, ^, **),
parentheses, floats, integers, Persian digits, percentage calculations (%),
rounding macros (=N), and currency-aware output (=t Toman, =r Rial).
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Any

from ravan.core.normalizer import en_to_fa_digits, fa_to_en_digits

_SAFE_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_MATH_CHARS = set("0123456789۰۱۲۳۴۵۶۷۸۹+-*/^%٪() .٫,")


def _preprocess_percentages(expr: str) -> str:
    """Transform percentage expressions into valid Python arithmetic.

    - Discount/Markup: '500 + 10%' -> '500 + (500 * (10 / 100))'
    - General Percentage: '100 * 20%' -> '100 * (20 / 100)'
    - Standalone: '50%' -> '(50 / 100)'
    """
    cleaned = expr.replace("٪", "%")
    # Discount or markup pattern: <number> [+-] <number>%
    cleaned = re.sub(
        r"(\d+(?:\.\d+)?)\s*([+-])\s*(\d+(?:\.\d+)?)\%",
        r"\1 \2 (\1 * (\3 / 100))",
        cleaned,
    )
    # Any remaining <number>%
    cleaned = re.sub(
        r"(\d+(?:\.\d+)?)\%",
        r"(\1 / 100)",
        cleaned,
    )
    return cleaned


def safe_eval(expr: str) -> float | int | None:
    """Safely evaluate an arithmetic expression string using AST traversal."""
    cleaned = expr.replace("٫", ".").replace(",", "")
    cleaned = _preprocess_percentages(cleaned)
    cleaned = cleaned.replace("^", "**")
    try:
        node = ast.parse(cleaned, mode="eval")
    except Exception:
        return None

    def _visit(n: ast.AST) -> float | int | None:
        if isinstance(n, ast.Expression):
            return _visit(n.body)
        elif isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)) and not isinstance(n.value, complex):
                return n.value
            return None
        elif isinstance(n, ast.UnaryOp) and type(n.op) in _SAFE_OPS:
            val = _visit(n.operand)
            return _SAFE_OPS[type(n.op)](val) if val is not None else None
        elif isinstance(n, ast.BinOp) and type(n.op) in _SAFE_OPS:
            left = _visit(n.left)
            right = _visit(n.right)
            if left is None or right is None:
                return None
            # Guard against massive exponentiation DoS and complex results from negative base
            if isinstance(n.op, ast.Pow):
                if abs(right) > 50 or abs(left) > 10000:
                    return None
                if left < 0 and not (isinstance(right, (int, float)) and float(right).is_integer()):
                    return None
            if isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
                return None
            try:
                out = _SAFE_OPS[type(n.op)](left, right)
                if isinstance(out, complex):
                    return None
                return out
            except (ZeroDivisionError, OverflowError, ValueError):
                return None
        return None

    try:
        res = _visit(node)
    except Exception:
        return None

    if res is None or not isinstance(res, (int, float)) or isinstance(res, complex):
        return None
    if isinstance(res, float) and res.is_integer():
        return int(res)
    return res



def parse_calc_query(text: str) -> tuple[str, int | None, str | None]:
    """Parse text ending with optional rounding macro (=N) or currency (=t/=r).

    Returns:
        (expr_part, decimals, currency)
    """
    cleaned = text.strip()
    if "=" in cleaned:
        expr_part, suffix = cleaned.rsplit("=", 1)
        suffix = suffix.strip()
        # Rounding macro e.g. =2 or =۰
        suffix_en = fa_to_en_digits(suffix)
        if suffix_en.isdigit() and len(suffix_en) <= 2:
            return expr_part.strip(), int(suffix_en), None
        # Currency macros
        if suffix.lower() in ("t", "ت"):
            return expr_part.strip(), None, "toman"
        if suffix.lower() in ("r", "ر"):
            return expr_part.strip(), None, "rial"
        if not suffix:
            return expr_part.strip(), None, None
    return cleaned, None, None


def calculate(
    expr: str,
    decimals: int | None = None,
    currency: str | None = None,
) -> str | None:
    """Evaluate expression, supporting rounding (=N) and currency (toman/rial)."""
    has_persian = any("\u06f0" <= c <= "\u06f9" for c in expr) or any(c in "تر٪" for c in expr)

    # Check if expr includes trailing macro (=2, =t, =r)
    expr_clean, parsed_dec, parsed_curr = parse_calc_query(expr)
    target_decimals = decimals if decimals is not None else parsed_dec
    target_currency = currency if currency is not None else parsed_curr

    normalized_expr = fa_to_en_digits(expr_clean)
    val = safe_eval(normalized_expr)
    if val is None:
        return None

    if target_decimals is not None:
        if target_decimals == 0:
            formatted = str(round(val))
        else:
            formatted = f"{val:.{target_decimals}f}"
    elif target_currency in ("toman", "t", "ت"):
        if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
            num_str = f"{int(val):,}"
        else:
            num_str = f"{val:,.2f}".rstrip("0").rstrip(".")
        formatted = f"{num_str} تومان"
    elif target_currency in ("rial", "r", "ر"):
        if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
            num_str = f"{int(val):,}"
        else:
            num_str = f"{val:,.2f}".rstrip("0").rstrip(".")
        formatted = f"{num_str} ریال"
    else:
        if isinstance(val, float):
            formatted = f"{val:.6f}".rstrip("0").rstrip(".")
        else:
            formatted = str(val)

    if has_persian:
        return en_to_fa_digits(formatted)
    return formatted


def extract_math_expression(text: str) -> str | None:
    """Extract a trailing math expression from text preceding an '=' trigger."""
    if not text:
        return None
    i = len(text)
    while i > 0 and text[i - 1] in _MATH_CHARS:
        i -= 1
    expr = text[i:].strip()
    if not expr:
        return None

    # Must contain at least one digit
    has_digit = any(c.isdigit() or ("\u06f0" <= c <= "\u06f9") for c in expr)
    # Must contain at least one binary operator between numbers (or % percentage)
    has_binary_op = any(c in "+-*/^%٪" for c in expr.lstrip("+-"))
    if not (has_digit and has_binary_op):
        return None

    # Check balanced parentheses
    if expr.count("(") != expr.count(")"):
        return None

    # Ensure it evaluates successfully
    if safe_eval(fa_to_en_digits(expr)) is None:
        return None

    return expr


def extract_math_query(text: str) -> tuple[str, int | None, str | None, int] | None:
    """Extract full math query with optional rounding/currency suffix.

    Returns:
        (expr_part, decimals, currency, matched_length)
    """
    if not text:
        return None

    # Match pattern: <math_chars>=<suffix>
    m = re.search(r"([0-9۰-۹\+\-\*\/\^\%٪\(\)\s\.\,٫]+)=([0-9۰-۹tTrRتر]?)$", text)
    if not m:
        return None

    expr_cand = m.group(1).strip()
    suffix = m.group(2).strip()

    valid_expr = extract_math_expression(expr_cand)
    if not valid_expr:
        # Check if expr_cand is a single number followed by currency or rounding e.g. 12000=t
        has_digit = any(c.isdigit() or ("\u06f0" <= c <= "\u06f9") for c in expr_cand)
        if has_digit and suffix and safe_eval(fa_to_en_digits(expr_cand)) is not None:
            valid_expr = expr_cand
        else:
            return None

    _, dec, curr = parse_calc_query(f"{valid_expr}={suffix}")
    matched_len = len(valid_expr) + 1 + len(suffix)
    return valid_expr, dec, curr, matched_len
