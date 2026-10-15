"""Safe, zero-dependency inline mathematical evaluator.

Uses Python's AST parser to guarantee security (no eval/exec).
Supports arithmetic operators (+, -, *, /, //, %, ^, **),
parentheses, floats, integers, and Persian digits.
"""

from __future__ import annotations

import ast
import operator
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

_MATH_CHARS = set("0123456789۰۱۲۳۴۵۶۷۸۹+-*/^%() .٫,")


def safe_eval(expr: str) -> float | int | None:
    """Safely evaluate an arithmetic expression string using AST traversal."""
    cleaned = expr.replace("^", "**").replace("٫", ".").replace(",", "")
    try:
        node = ast.parse(cleaned, mode="eval")
    except Exception:
        return None

    def _visit(n: ast.AST) -> float | int | None:
        if isinstance(n, ast.Expression):
            return _visit(n.body)
        elif isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
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
            # Guard against massive exponentiation DoS
            if isinstance(n.op, ast.Pow):
                if abs(right) > 50 or abs(left) > 10000:
                    return None
            if isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
                return None
            try:
                return _SAFE_OPS[type(n.op)](left, right)
            except (ZeroDivisionError, OverflowError):
                return None
        return None

    try:
        res = _visit(node)
    except Exception:
        return None

    if res is None:
        return None
    if isinstance(res, float) and res.is_integer():
        return int(res)
    return res


def calculate(expr: str) -> str | None:
    """Evaluate an expression, preserving Persian digits if input contained them."""
    has_persian = any("\u06f0" <= c <= "\u06f9" for c in expr)
    normalized_expr = fa_to_en_digits(expr)
    val = safe_eval(normalized_expr)
    if val is None:
        return None

    if isinstance(val, float):
        # Round cleanly to 6 decimal places and strip trailing zeros
        formatted = f"{val:.6f}".rstrip("0").rstrip(".")
    else:
        formatted = str(val)

    if has_persian:
        return en_to_fa_digits(formatted)
    return formatted


def extract_math_expression(text: str) -> str | None:
    """Extract a trailing math expression from the text preceding an '=' trigger."""
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
    # Must contain at least one binary operator between numbers (not just a leading sign)
    has_binary_op = any(c in "+-*/^%" for c in expr.lstrip("+-"))
    if not (has_digit and has_binary_op):
        return None

    # Check balanced parentheses
    if expr.count("(") != expr.count(")"):
        return None

    # Ensure it evaluates successfully
    if safe_eval(fa_to_en_digits(expr)) is None:
        return None

    return expr
