from __future__ import annotations

import ast
import math
import operator
import re

from .models import UnsafeExpressionError


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_SPOKEN = (
    (r"\bmultiplied by\b", "*"),
    (r"\bmultiply by\b", "*"),
    (r"\bdivided by\b", "/"),
    (r"\bdivide by\b", "/"),
    (r"\btimes\b", "*"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\bmodulo\b", "%"),
)


def extract_expression(command: str) -> str | None:
    text = command.lower().strip().rstrip("?.")
    text = re.sub(
        r"^(?:please\s+)?(?:calculate|compute|solve|what\s+is|how\s+much\s+is)\s+",
        "",
        text,
    )
    for pattern, symbol in _SPOKEN:
        text = re.sub(pattern, symbol, text)
    text = re.sub(r"\bequals\b", "", text).strip()
    if not re.search(r"\d", text) or re.search(r"[^0-9+\-*/%().\s]", text):
        return None
    return text


def safe_calculate(expression: str) -> int | float:
    if len(expression) > 160:
        raise UnsafeExpressionError("That calculation is too long.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise UnsafeExpressionError("I could not understand that calculation.") from error
    visited = 0

    def evaluate(node: ast.AST) -> float | int:
        nonlocal visited
        visited += 1
        if visited > 50:
            raise UnsafeExpressionError("That calculation is too complex.")
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            if not math.isfinite(float(node.value)) or abs(node.value) > 1e15:
                raise UnsafeExpressionError("That number is outside the supported range.")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = evaluate(node.left), evaluate(node.right)
            try:
                result = _BINARY[type(node.op)](left, right)
            except ZeroDivisionError as error:
                raise UnsafeExpressionError("Division by zero is not defined.") from error
            if not math.isfinite(float(result)) or abs(result) > 1e15:
                raise UnsafeExpressionError("That result is outside the supported range.")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](evaluate(node.operand))
        raise UnsafeExpressionError("That calculation contains an unsupported operation.")

    result = evaluate(tree)
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return round(result, 10) if isinstance(result, float) else result

