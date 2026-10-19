"""
Statement.calculate_expression uchun xavfsiz hisoblagich (audit A8).

Ilgari formulalar eval() bilan bajarilardi; {"__builtins__": {}} sandbox emas —
().__class__.__base__.__subclasses__() orqali istalgan kod bajarilardi, ya'ni
admin'da formula yoza oladigan har kim serverda kod ishlata olardi.

Grammatika (faqat shular):
    son, Decimal('son'), column('ordering'), + - * / ( ), unar + -
Formula qatori:  <ifoda> = column('<target ordering>')
"""
import ast
import operator
from decimal import Decimal, InvalidOperation
from typing import Callable

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


class FormulaError(ValueError):
    pass


def _string_arg(call: ast.Call, func_name: str) -> str:
    if call.keywords or len(call.args) != 1:
        raise FormulaError(f"{func_name}() bitta matn argument oladi")
    arg = call.args[0]
    if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
        raise FormulaError(f"{func_name}() argumenti qo'shtirnoqdagi matn bo'lishi kerak")
    return arg.value


def _parse(expression: str) -> ast.Expression:
    try:
        return ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Formula sintaksisi noto'g'ri: {expression!r}") from e


def _eval_node(node: ast.AST, column: Callable[[str], Decimal]) -> Decimal:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, column)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return Decimal(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand, column)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left, column), _eval_node(node.right, column))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "column":
            return Decimal(column(_string_arg(node, "column")))
        if node.func.id == "Decimal":
            try:
                return Decimal(_string_arg(node, "Decimal"))
            except InvalidOperation as e:
                raise FormulaError("Decimal() argumenti son emas") from e
    raise FormulaError(f"Formulada ruxsat etilmagan element: {type(node).__name__}")


def evaluate_formula(expression: str, column: Callable[[str], Decimal]) -> Decimal:
    """Ifodani hisoblaydi. column(ordering) qiymatlarni beradi. Xato → FormulaError;
    nolga bo'lish Decimal xatosini (DivisionByZero/InvalidOperation) o'tkazadi."""
    return _eval_node(_parse(expression), column)


def validate_expression(expression: str) -> None:
    """Faqat sintaksis/whitelist tekshiruvi (qiymatlar 0 deb olinadi)."""
    evaluate_formula(expression, lambda _ordering: Decimal("1"))


def parse_formula_lines(text: str) -> list[tuple[str, str]]:
    """Matnni (ifoda, target_ordering) juftliklariga ajratadi va har birini tekshiradi."""
    lines = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.count("=") != 1:
            raise FormulaError(f"Har qatorda bitta '=' bo'lishi kerak: {line!r}")
        expression, target = (p.strip() for p in line.split("="))
        validate_expression(expression)
        target_tree = _parse(target)
        call = target_tree.body
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "column"):
            raise FormulaError(f"'=' dan keyin column('ordering') bo'lishi kerak: {line!r}")
        lines.append((expression, _string_arg(call, "column")))
    return lines


def source_orderings(expression: str) -> list[str]:
    """Ifodadagi column('...') argumentlari (tartib bilan)."""
    found = []
    for node in ast.walk(_parse(expression)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "column":
            found.append(_string_arg(node, "column"))
    return found
