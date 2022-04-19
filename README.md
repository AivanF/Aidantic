# Aidantic

Aidantic is a tiny library inspired by Pydantic,
made to be more suitable for:
- Data parsing.
- Subclasses lookup (like `OneOf` in JSON-Schema).
- Input data validation:
  - Exceptions store precise path.
  - Plain types values validation, see `PlainWrapper`.
  - Custom complex objects validation, see `ModelVisitorBase`.

The library isn't aimed to become a full replacement of Pydantic
(e.g, there is no planned support of JSON Schema, OpenAPI),
but in some cases it's worth using `:)`

ToDo List:
- 1: optional strict value type check
- 2: field name aliases
- 3: OneOf typing: pass inner class methods
- 4: probably some default types are missed and not supported 

License: GPL 3


# Usage

Install with pip: `pip install Aidantic`  
Or simply obtain a single source file from the repo.

## 1. Basics

```py
from typing import List
from aidantic import BaseModel

class Model(BaseModel):
    name: str
    data: List[int]

obj = Model(name="Foo", data=[61, 80, 33, 98])
assert obj.data[2] == 33
```
Simple yet boring, let's dive deeper!

## 2. OneOf
Sometimes an object may contain instance(s)
of plenty subclasses, and you, or your auxiliary lib,
have to decide which class to use during parsing process.
For this aim, Aidantic provides built-in support of
One-Of logic: all you need is to specify a key,
which should be used to subclass picking,
and declare its values for the subclasses.
No `Union` with boring enumeration is needed!
```py
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

data = dict(title="Bar42", content=[
    dict(key=314, value=15926535),
    dict(key=271, value="lol"),
])
package = PackageModel(**data)
package.validate()
assert package.content[1].value == "lol"
print(package)
```

Result:
```py
PackageModel(
  title='Bar42',
  content=[
    PieModel(key=314, value=15926535),
    EuropeModel(key=271, value='lol')
])
```

BTW, `_discriminator` may be a tuple of field names.

## 3. PlainWrapper
If you need to validate a set of values of plain types
(like str, int), you can utilise `PlainWrapper` class,
which can be used as a simple replacement of any plain type.
However, you should note that a wrapped value has
some limitations: typical `isinstance` usage won't work.
But comparison to plain values works well,
and you can easily access wrapper's `value` property.

There are a couple of use-cases:

### 3.1. Creation time validation
```py
from aidantic import PlainWrapper, BaseModel, CreationError, PathType

class StatusCode(PlainWrapper["str"]):
    _allowed = {"foo", "bar", "lol"}

    def __init__(self, code, path: PathType):
        if code not in self._allowed:
            raise CreationError(f"Unknown code '{code}'", path)
        super().__init__(code, path)

class SomeModel(BaseModel):
    code: StatusCode

obj = SomeModel(code="bar")
assert obj.code == "bar"
```

The same could be also written as a Union of Literals,
but this would be too verbose.

### 3.2. Validator class
If you have to perform more complex logic,
e.g load allowed values later, or compare values
from different objects, you can use a separate validator
that will traverse your data models:
```py
from typing import List
from aidantic import PlainWrapper, BaseModel, ModelVisitorBase, ValidationError

class StatusCode(PlainWrapper["str"]):
    pass

class SomeModel(BaseModel):
    codes: List[StatusCode]

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

obj = SomeModel(codes=["foo", "bar", "lol"])
CrossValidator().visit(obj)
```

## 4. Plain values parsing
Thanks to `from_plain` method,
it's pretty simple to write a parser that will translate
plain values like strings into objects:
```py
from aidantic import BaseModel
from expr import AnyExpr
class Message(BaseModel):
    title: str
    formula: AnyExpr

msg = Message(
    title="Please calculate the attached expression",
    formula="log(pi, 2.7182)",
)
print(msg)
```
```py
Message(
  title="Please calculate the attached expression",
  formula=ExprFunction(operator='FUNCTION', name='log', arguments=[
    ExprField(operator='FIELD', name='pi'), ExprLiteral(operator='LITERAL', value=2.7182)
  ])
)
```

See [`tests/test_expr.py`](https://github.com/AivanF/Aidantic/blob/main/tests/test_expr.py)
for implementation details!

# Historical intro

While I was developing CI and scenario scripts for
my GameDev pet-project [Destiny Garden](https://www.aivanf.com/destiny-garden-1),
I've met a need to parse and validate large scripts
written in custom YAML-based format.
I tried to use my beloved Pydantic for this problem,
but found it too focused on networking, ORM logic and too
rigid for game scenario scripting, so quickly I've
developed this library which is small yet powerful
for dealing with such specialised problems.
