__author__ = "AivanF"

from typing import Literal, List, Tuple, Union
import ast
import pytest
from aidantic import (
    BaseModel, ModelVisitorBase, OneOf, PlainWrapper,
    ValidationError, CreationError, PathType,
)

__all__ = ["AnyExpr", "parse_expr", "write_expr"]


class ExprBase(BaseModel):
    operator: str
    _discriminator = "operator"

    @classmethod
    def from_plain(cls, value: str, path: PathType) -> "AnyExpr":
        return parse_expr(value, path)


AnyExpr = OneOf[ExprBase]


class BinarySign(PlainWrapper["str"]):
    """
    It also could be written as a Union of Literals,
    but this would be too verbose.
    """
    _options = (
        "<", "<=", "==", "!=", ">=", ">",
        "+", "-", "*", "/", "and", "or",
    )

    def __init__(self, sign, path: PathType):
        if sign not in self._options:
            raise CreationError(f"Unknown sign '{sign}'", path)
        super().__init__(sign, path)


class BinaryExpr(ExprBase):
    operator: Literal["BIN"]
    sign: BinarySign
    left: AnyExpr
    right: AnyExpr

    def to_formula(self):
        return (
            f"({self.left.to_formula()} {self.sign} {self.right.to_formula()})"
        )


class ExprField(ExprBase):
    operator: Literal["FIELD"]
    name: str

    def to_formula(self):
        return self.name


class ExprLiteral(ExprBase):
    operator: Literal["LITERAL"]
    value: Union[float, int, str]

    def to_formula(self):
        return f"{repr(self.value)}"


class ExprFunction(ExprBase):
    operator: Literal["FUNCTION"]
    name: str
    arguments: List[AnyExpr]

    def to_formula(self):
        args = (o.to_formula() for o in self.arguments)
        return f"{self.name}({', '.join(args)})"


class FormulaFieldsValidator(ModelVisitorBase):
    def __init__(self, fields: List[str]):
        self.fields = fields
        super().__init__()

    def visit_model(self, obj, _type, path):
        if isinstance(obj, ExprField):
            if obj.name not in self.fields:
                raise ValidationError(f"Unknown column '{obj.name}'", path)
        super().visit_model(obj, _type, path)


class ExprVisitor(ast.NodeVisitor):
    """
    Typical visitor class for Python interpreter usage
    """

    def __init__(self, path):
        self.path = path

    def _parse(self, node, label):
        result = self.visit(node)
        if result is None:
            raise CreationError(
                f"Bad value {node.__class__.__name__} from {label}", self.path)
        return result

    def generic_visit(self, node):
        raise CreationError(
            f"No expr handler for {node.__class__.__name__}", self.path)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_BinOp(self, node):
        return BinaryExpr(
            sign=self._parse(node.op, "sign"),
            left=self._parse(node.left, "left"),
            right=self._parse(node.right, "right"))

    def visit_BoolOp(self, node):
        if len(node.values) != 2:
            raise CreationError("Bool of non-2 elements!", self.path)
        return BinaryExpr(
            sign=self._parse(node.op, "sign"),
            left=self._parse(node.values[0], "left"),
            right=self._parse(node.values[1], "right"))

    def visit_Add(self, node):
        return "+"

    def visit_Sub(self, node):
        return "-"

    def visit_Mult(self, node):
        return "*"

    def visit_Div(self, node):
        return "/"

    def visit_And(self, node):
        return "and"

    def visit_Or(self, node):
        return "or"

    def visit_Name(self, node):
        return ExprField(name=node.id)

    def visit_Call(self, node):
        name: ExprField = self._parse(node.func, "name")
        return ExprFunction(
            name=name.name,
            arguments=[
                self._parse(arg, i)
                for i, arg in enumerate(node.args)
            ])

    def visit_Constant(self, node):
        return ExprLiteral(value=node.n)

    def visit_Compare(self, node):
        if len(node.ops) != 1:
            raise CreationError(
                "Comparison of multiple elements!", self.path)
        sign = self.visit(node.ops[0])
        if sign is None:
            raise CreationError(
                f"Comparison bad sign {node.ops[0]}", self.path)
        return BinaryExpr(
            sign=sign,
            left=self._parse(node.left, "left"),
            right=self._parse(node.comparators[0], "right"),
        )

    def visit_Eq(self, node):
        return "=="

    def visit_NotEq(self, node):
        return "!="

    def visit_Lt(self, node):
        return "<"

    def visit_LtE(self, node):
        return "<="

    def visit_Gt(self, node):
        return ">"

    def visit_GtE(self, node):
        return ">="


def parse_expr(formula: str, path: PathType) -> AnyExpr:
    return ExprVisitor(path).visit(ast.parse(formula, mode="eval"))


def write_expr(expr: AnyExpr) -> str:
    return expr.to_formula()


formulas = [
    "3 <= (a/2 + 1) and smth(b) == 4",
    "log(pi, 2.7182)",
]


@pytest.mark.parametrize("formula", formulas)
def test_expr(formula):
    path = ()
    print(f"Original formula: {formula}")
    expr = parse_expr(formula, path)
    print(f"Parsed expression: {expr}")
    serialized = write_expr(expr)
    print(f"Serialized: {serialized}")

    new_expr = parse_expr(serialized, path)
    new_serialized = write_expr(new_expr)
    assert serialized == new_serialized


if __name__ == "__main__":
    test_expr(formulas[1])
