__author__ = "AivanF"

from aidantic import PathType, PlainWrapper, BaseModel, CreationError


class StatusCode(PlainWrapper["str"]):
    _allowed = {"foo", "bar", "lol"}

    def __init__(self, code, path: PathType):
        if code not in self._allowed:
            raise CreationError(f"Unknown code '{code}'", path)
        super().__init__(code, path)


class SomeModel(BaseModel):
    code: StatusCode


def test_wrapper():
    obj = SomeModel(code="bar")
    assert obj.code == "bar"
    assert obj.code.value == "bar"
    assert obj.serialize() == dict(code="bar")
