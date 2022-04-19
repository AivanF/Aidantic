__author__ = "AivanF"

from typing import List
from aidantic import PlainWrapper, BaseModel, ModelVisitorBase, ValidationError


class StatusCode(PlainWrapper["str"]):
    pass


class SomeModel(BaseModel):
    codes: List[StatusCode]


class Package(BaseModel):
    content: List[SomeModel]


class CrossValidator(ModelVisitorBase):
    _label = "Cross"
    _allowed = {"foo", "bar", "lol"}

    def __init__(self,):
        super().__init__()
        self.collected_codes = set()

    def visit(self, obj):
        super().visit(obj)
        unknown_codes = self.collected_codes - self._allowed
        if unknown_codes:
            raise ValidationError(f"Got {len(unknown_codes)} unknown codes", ())

    def visit_wrapper(self, obj, _type, path):
        if issubclass(_type, StatusCode):
            self.collected_codes.add(str(obj))


def test_visitor():
    obj = Package(content=[
        dict(codes=["foo", "bar"]),
        dict(codes=["lol", "bar"]),
    ])
    visitor = CrossValidator()
    visitor.visit(obj)
    assert len(visitor.collected_codes) == 3
