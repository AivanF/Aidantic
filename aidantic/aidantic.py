__author__ = "AivanF"
__copyright__ = "AivanF"
__email__ = "projects@aivanf.com"
__license__ = "GPL3"
__version__ = "2022.04.12"
__status__ = "Dev"


from typing import (
    Generic, TypeVar, _GenericAlias, Any,
    Type, Optional, Union, Iterable, Tuple, Dict,
)
from typing_extensions import Literal

__all__ = [
    "ValidationError", "CreationError", "PathType",
    "BaseModel", "PlainWrapper", "OneOf",
    "ModelVisitorBase", "ModelValidator",
]

PathType = Tuple[str, ...]
JsonType = Union[dict, list, str, int, float, type(None)]


def join_path(path: PathType):
    return " -> ".join(map(str, path))


class ValidationError(BaseException):
    def __init__(self, msg, path: PathType):
        self.msg = msg
        self.path = path

    def __repr__(self):
        if self.path:
            return f"{join_path(self.path)}: {self.msg}"
        else:
            return self.msg

    def __str__(self):
        return self.__repr__()


class CreationError(ValidationError):
    pass


T = TypeVar("T")


class OneOf(Generic[T]):
    """
    Usage: OneOf[SomeClass]
    But SomeClass must have a field _discriminator: Union[str, Iterable[str]],
    which specifies fields used to determine specific subclass.
    """
    pass


PT = TypeVar("PT")


class PlainWrapper(Generic[PT]):
    """
    Wrapper for plain types like str, int.
    It's really useful for complex data validation,
    especially for sets of literal values known at run-time only.
    To validate values, you can overload __init__/validate methods,
    or use a custom ModelValidator visitor.
    """

    def __init__(self, value: PT, path: PathType = ()):
        self.value = value

    def validate(self):
        pass

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    def __hash__(self):
        return hash(self.value)

    def __bool__(self):
        return bool(self.value)

    def __getattr__(self, key):
        return getattr(self.value, key)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"{repr(self.value)}:{self.__class__.__name__}(PlainWrapper)"


# Parent model into key fields
TRACKED_MODEL_KEYS: Dict[Type["BaseModel"], Tuple[str, ...]] = {}
# Parent model into map of key values into child models
TRACKED_MODELS: Dict[Type["BaseModel"], Dict[Tuple, Type["BaseModel"]]] = {}


class BaseModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        # Inherit annotations
        ann = namespace.get("__annotations__", {})
        for parent in bases:
            pan = parent.__dict__.get("__annotations__", {})
            for key in pan:
                if key not in ann:
                    ann[key] = pan[key]
        namespace["__annotations__"] = ann

        cls: Type["BaseModel"]
        cls = super().__new__(mcs, name, bases, namespace)

        # Hanle OneOf logic
        if "_discriminator" in namespace:
            if isinstance(cls._discriminator, str):
                cls._discriminator = (cls._discriminator,)
            TRACKED_MODEL_KEYS[cls] = cls._discriminator
            TRACKED_MODELS[cls] = {}

        elif not name.endswith("Base"):
            # Register child model
            for parent in TRACKED_MODEL_KEYS:
                if issubclass(cls, parent):
                    # Annotation key fields must be Literals
                    keys = tuple(
                        cls.__annotations__[name].__args__[0]
                        for name in TRACKED_MODEL_KEYS[parent]
                    )
                    TRACKED_MODELS[parent][keys] = cls
        return cls


class ModelVisitorBase:
    """
    Visitor pattern is used to traverse nested models,
    to create and validate the data objects.
    """
    _visible = False
    _label = "?"

    def __init__(self):
        self.root = None

    def visit(self, obj):
        self.root = obj
        return self.visit_model(obj, obj.__class__, ())

    def visit_field(self, obj, _type, path) -> Any:
        if isinstance(_type, _GenericAlias):
            return self.visit_generic(obj, _type, path)
        elif issubclass(_type, BaseModel):
            return self.visit_model(obj, _type, path)
        elif issubclass(_type, PlainWrapper):
            return self.visit_wrapper(obj, _type, path)
        else:
            return self.visit_plain(obj, _type, path)

    def visit_generic(self, obj, _type, path) -> Any:
        self.show("Generic", path, _type)
        origin = _type.__origin__

        if origin == list:
            return self.visit_list(obj, _type, path)

        elif origin == Iterable:
            return self.visit_iterable(obj, _type, path)

        elif origin == Union:
            return self.visit_union(obj, _type, path)

        elif origin == Literal:
            return self.visit_literal(obj, _type, path)

        elif origin == OneOf:
            parent = _type.__args__[0]
            return self.visit_one_of(obj, parent, path)

        else:
            return self.visit_generic_other(obj, _type, path)

    def show(self, method, path, _type, value=None):
        if self._visible:
            if value is not None:
                print(f"{self._label} {path}: {method} {_type} {value}")
            else:
                print(f"{self._label} {path}: {method} {_type}")

    def visit_generic_other(self, obj, _type, path):
        pass

    def visit_list(self, obj, _type, path) -> Any:
        return self.visit_iterable(obj, _type, path)

    def visit_iterable(self, obj, _type, path) -> Any:
        self.show("Iterable", path, _type)
        if len(_type.__args__) == 0:
            return
        subtype = _type.__args__[0]
        if len(_type.__args__) > 0:
            subtype = _type.__args__[0]
            for i, value in enumerate(obj):
                next_path = path + (i,)
                self.visit_field(value, subtype, next_path)

    def visit_union(self, obj, _type, path) -> Any:
        # Special handle for Optional
        if len(_type.__args__) == 2 and \
                isinstance(None, _type.__args__[1]):
            if obj is not None:
                self.visit_field(obj, _type.__args__[0], path)
        else:
            self.visit_field(obj, obj.__class__, path)

    def visit_literal(self, obj, _type, path) -> Any:
        pass

    def visit_wrapper(self, obj, _type, path) -> Any:
        pass

    def visit_plain(self, obj, _type, path) -> Any:
        pass

    def visit_one_of(self, obj, parent, path) -> Any:
        return self.visit_model(obj, obj.__class__, path)

    def visit_model(self, obj, _type, path) -> Any:
        self.show("BaseModel", path, _type)
        for key, subtype in _type.__annotations__.items():
            value = getattr(obj, key, None)
            next_path = path + (key,)
            self.visit_field(value, subtype, next_path)


class ModelValidator(ModelVisitorBase):
    # _visible = True
    _label = "Vali"

    def visit_generic_other(self, obj, _type, path):
        raise ValidationError(
            f"type {_type} is not supported for validation", path
        )

    def visit_list(self, obj, _type, path):
        origin = _type.__origin__
        if not isinstance(obj, origin):
            raise ValidationError(f"is not {origin}", path)
        super().visit_list(obj, _type, path)

    def visit_union(self, obj, _type, path):
        self.show("Union", path, _type)
        appropriate = None
        first_ex = None
        for subtype in _type.__args__:
            try:
                self.visit_field(obj, subtype, path)
                appropriate = subtype
                break
            except ValidationError as ex:
                if first_ex is None:
                    first_ex = ex
                continue
        if appropriate is None:
            # Handle Optional specially
            if len(_type.__args__) == 2 and \
                    isinstance(None, _type.__args__[1]):
                raise first_ex
            raise ValidationError(f"{obj} is not {_type}", path)

    def visit_literal(self, obj, _type, path):
        self.show("Literal", path, _type)
        literal_value = _type.__args__[0]
        if obj != literal_value:
            raise ValidationError(
                f"expected literal {literal_value} but got {obj}", path
            )

    def visit_wrapper(self, obj, _type, path):
        self.show("Wrapper", path, _type, obj)
        if not isinstance(obj, _type):
            raise ValidationError(
                f"expected plain {_type} but got {obj}", path
            )
        obj.validate()

    def visit_plain(self, obj, _type, path):
        self.show("Plain", path, _type, obj)
        if not isinstance(obj, _type):
            raise ValidationError(
                f"expected plain {_type} but got {obj}", path
            )

    def visit_one_of(self, obj, parent, path):
        self.show("OneOf", path, parent)
        if obj.__class__ not in TRACKED_MODELS[parent].values():
            raise ValidationError(
                f"expected a child of {parent} but got {obj.__class__}",
                path
            )
        super().visit_one_of(obj, parent, path)

    def visit_model(self, obj, _type, path):
        if not isinstance(obj, _type):
            raise ValidationError(f"{obj} is not {_type}", path)
        super().visit_model(obj, _type, path)
        obj._validate(path, self)


class ModelCreator(ModelVisitorBase):
    # _visible = True
    _label = "Crea"

    def visit_generic_other(self, obj, _type, path):
        raise CreationError(
            f"type {_type} is not supported for creation", path
        )

    def visit_iterable(self, obj, _type, path) -> object:
        if len(_type.__args__) > 0:
            subtype = _type.__args__[0]
            result = []
            for i, value in enumerate(obj):
                next_path = path + (i,)
                result.append(self.visit_field(value, subtype, next_path))
            return result
        else:
            return obj

    def visit_union(self, value, _type, path) -> object:
        result = None
        appropriate = None
        # Special handle for Optional
        if len(_type.__args__) == 2 and \
                type(None) == _type.__args__[1]:
            if value is None:
                return None
            else:
                subtype = _type.__args__[0]
                result = self.visit_field(value, subtype, path)
                VALIDATOR.visit_field(result, subtype, path)
                return result
        for subtype in _type.__args__:
            try:
                result = self.visit_field(value, subtype, path)
                VALIDATOR.visit_field(result, subtype, path)
                appropriate = subtype
                break
            except (TypeError, ValidationError):
                continue
        if appropriate is None:
            raise CreationError(f"{value} is not {_type}", path)
        return result

    def visit_literal(self, value, _type, path) -> object:
        literal_value = _type.__args__[0]
        if value != literal_value:
            raise CreationError(
                f"expected literal {literal_value}"
                f" but got {value}", path
            )
        return literal_value

    def visit_wrapper(self, value, _type, path) -> object:
        return _type(value, path=path)

    def visit_plain(self, value, _type, path) -> object:
        # TODO: consider strict value type checking
        return _type(value)

    def visit_one_of(self, value, parent, path) -> object:
        # Pass appropriate object
        if isinstance(value, parent):
            return value
        # Try create from keys
        key_names = TRACKED_MODEL_KEYS[parent]
        keys = None
        kwargs = value
        if isinstance(value, dict):
            keys = tuple(value.get(key) for key in key_names)
        elif len(key_names) == 1 and isinstance(value, (str, int)):
            # Consider single value as a key
            keys = (value,)
            kwargs = {key_names[0]: value}
        if keys is not None:
            _type = TRACKED_MODELS[parent].get(keys)
            if _type is not None:
                return _type(__start__path__=path, **kwargs)
        result = parent.from_plain(value, path)
        if result is not None:
            return result
        raise CreationError(
            f"OneOf of {parent.__name__} cannot resolve {value}", path)

    def visit_model(self, value, _type, path) -> object:
        if isinstance(value, _type):
            return value
        else:
            if not isinstance(value, dict):
                result = _type.from_plain(value, path)
                if result is None:
                    raise CreationError(
                        f"expected {dict}, got {value}", path
                    )
            else:
                result = _type(__start__path__=path, **value)
            return result


CREATOR = ModelCreator()
VALIDATOR = ModelValidator()


class BaseModel(metaclass=BaseModelMeta):
    def __init__(self, __start__path__: PathType  = (), **kwargs):
        for key, value in kwargs.items():
            _type = self.__annotations__.get(key)
            if _type is None:
                raise CreationError(
                    f"got unexpected {key}={value}"
                    f" for {self.__class__.__name__}",
                    __start__path__
                )
            value = CREATOR.visit_field(value, _type, __start__path__ + (key,))
            setattr(self, key, value)
        # Add missing literal values
        for key, _type in self.__annotations__.items():
            if isinstance(_type, _GenericAlias):
                origin = _type.__origin__
                if origin == Literal:
                    literal_value = _type.__args__[0]
                    if key in kwargs:
                        if literal_value != kwargs[key]:
                            raise CreationError(
                                f"got bad literal {key}={kwargs[key]}"
                                f" expected {literal_value}"
                                f" for {self.__class__.__name__}",
                                __start__path__
                            )
                    else:
                        setattr(self, key, literal_value)
            # Handle NoneType similar to a literal
            elif isinstance(None, _type):
                setattr(self, key, None)

    @classmethod
    def from_plain(cls, value, path) -> object:
        """
        This allows to parse some value, usually string, into an object.
        To be overridden.
        """
        return None

    @classmethod
    def get_children(cls) -> Dict[Tuple, Type["BaseModel"]]:
        return TRACKED_MODELS[cls]

    @classmethod
    def child_by_keys(cls, keys) -> Optional[Type["BaseModel"]]:
        return TRACKED_MODELS[cls].get(keys)

    def validate(self, validator=VALIDATOR):
        validator.visit(self)

    def _validate(self, path, validator: ModelValidator):
        """
        To be overridden.
        """
        pass

    @classmethod
    def _serialize_value(cls, value) -> JsonType:
        if isinstance(value, list) or isinstance(value, tuple):
            return cls._serialize_iterable(value)
        elif isinstance(value, dict):
            return {
                key: cls._serialize_value(val)
                for key, val in value.items()
            }
        elif isinstance(value, BaseModel):
            return value.serialize()
        elif isinstance(value, PlainWrapper):
            return value.value
        # TODO: raise error?
        return value

    @classmethod
    def _serialize_iterable(cls, obj) -> JsonType:
        result = []
        for value in obj:
            result.append(cls._serialize_value(value))
        return result

    def serialize(self) -> JsonType:
        result = {}
        for key, _type in self.__annotations__.items():
            value = getattr(self, key, None)
            result[key] = self._serialize_value(value)
        return result

    def __repr__(self):
        result = self.__class__.__name__ + "("
        result += ", ".join(
            f"{key}={repr(getattr(self, key, None))}"
            for key in self.__annotations__
        )
        return result + ")"
