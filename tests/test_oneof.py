__author__ = "AivanF"

from typing import List, Literal
from aidantic import BaseModel, OneOf


class RandomModel(BaseModel):
    _discriminator = "key"
    key: int


class EuropeModel(RandomModel):
    key: Literal[271]
    value: str


class PieModel(RandomModel):
    key: Literal[314]
    value: int


class PackageModel(BaseModel):
    title: str
    content: List[OneOf[RandomModel]]


def test_one_of():
    data = dict(title="Bar42", content=[
        dict(key=314, value=15926535),
        dict(key=271, value="lol"),
    ])
    package = PackageModel(**data)
    package.validate()
    assert package.content[0].value == 15926535
    assert package.content[1].value == "lol"
