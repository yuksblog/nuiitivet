"""The values a server function exchanges with its caller, and their JSON form.

A codec is built from a type annotation, never from the data. The receiving
side constructs only the types the function declares, so a message cannot
choose which class is instantiated.
"""

from __future__ import annotations

import base64
import dataclasses
import enum
import types
import typing
from datetime import date, datetime
from typing import Any, Callable, Union

Json = Any


class Codec:
    """Converts values of one declared type to JSON-ready data and back."""

    __slots__ = ("name", "encode", "decode")

    def __init__(self, name: str, encode: Callable[[Any], Json], decode: Callable[[Json], Any]) -> None:
        """Initialize Codec.

        Args:
            name: The type as error messages show it.
            encode: Turns a value into JSON-ready data; raises ``TypeError``
                for a value of another type.
            decode: Rebuilds the value from that data; raises ``TypeError``
                for data of another shape.
        """
        self.name = name
        self.encode = encode
        self.decode = decode

    def copy(self, value: Any) -> Any:
        """Return *value* as the other side of a connection would receive it."""
        return self.decode(self.encode(value))


def _mismatch(name: str, value: object) -> TypeError:
    return TypeError(f"expected {name}, got {type(value).__name__}")


def _exact(name: str, *accepted: type) -> Codec:
    def check(value: Any) -> Any:
        # bool is a subclass of int; a flag sent for a count is a mistake.
        if type(value) not in accepted:
            raise _mismatch(name, value)
        return value

    return Codec(name, check, check)


def _float() -> Codec:
    def check(value: Any) -> float:
        if type(value) not in (float, int):
            raise _mismatch("float", value)
        return float(value)

    return Codec("float", check, check)


def _text(name: str, kind: type, to_text: Callable[[Any], str], from_text: Callable[[str], Any]) -> Codec:
    def encode(value: Any) -> str:
        if type(value) is not kind:
            raise _mismatch(name, value)
        return to_text(value)

    def decode(data: Json) -> Any:
        if type(data) is not str:
            raise _mismatch(f"{name} as text", data)
        return from_text(data)

    return Codec(name, encode, decode)


def _enum(cls: type[enum.Enum]) -> Codec:
    def encode(value: Any) -> str:
        if type(value) is not cls:
            raise _mismatch(cls.__name__, value)
        return str(value.name)

    def decode(data: Json) -> Any:
        if type(data) is not str or data not in cls.__members__:
            raise TypeError(f"{data!r} is not a member of {cls.__name__}")
        return cls[data]

    return Codec(cls.__name__, encode, decode)


def _optional(inner: Codec) -> Codec:
    return Codec(
        f"{inner.name} | None",
        lambda value: None if value is None else inner.encode(value),
        lambda data: None if data is None else inner.decode(data),
    )


def _sequence(kind: type, item: Codec) -> Codec:
    name = f"{kind.__name__}[{item.name}]" if kind is list else f"tuple[{item.name}, ...]"

    def encode(value: Any) -> list[Json]:
        actual: type = type(value)
        if actual is not kind:
            raise _mismatch(name, value)
        return [item.encode(element) for element in value]

    def decode(data: Json) -> Any:
        if type(data) is not list:
            raise _mismatch(f"{name} as a list", data)
        elements = [item.decode(element) for element in data]
        return elements if kind is list else tuple(elements)

    return Codec(name, encode, decode)


def _fixed_tuple(items: list[Codec]) -> Codec:
    name = f"tuple[{', '.join(item.name for item in items)}]"

    def encode(value: Any) -> list[Json]:
        if type(value) is not tuple or len(value) != len(items):
            raise _mismatch(name, value)
        return [item.encode(element) for item, element in zip(items, value)]

    def decode(data: Json) -> tuple[Any, ...]:
        if type(data) is not list or len(data) != len(items):
            raise _mismatch(f"{name} as a list", data)
        return tuple(item.decode(element) for item, element in zip(items, data))

    return Codec(name, encode, decode)


def _mapping(item: Codec) -> Codec:
    name = f"dict[str, {item.name}]"

    def convert(value: Any, each: Callable[[Any], Any]) -> dict[str, Any]:
        if type(value) is not dict:
            raise _mismatch(name, value)
        for key in value:
            if type(key) is not str:
                raise _mismatch(f"a str key in {name}", key)
        return {key: each(element) for key, element in value.items()}

    return Codec(name, lambda value: convert(value, item.encode), lambda data: convert(data, item.decode))


def _dataclass(cls: type, memo: dict[Any, Codec]) -> Codec:
    fields: dict[str, Codec] = {}

    def encode(value: Any) -> dict[str, Json]:
        if type(value) is not cls:
            raise _mismatch(cls.__name__, value)
        return {
            name: _at(f"{cls.__name__}.{name}", codec.encode, getattr(value, name))
            for name, codec in fields.items()
        }

    def decode(data: Json) -> Any:
        if type(data) is not dict or data.keys() != fields.keys():
            raise _mismatch(f"{cls.__name__} as a dict of its fields", data)
        return cls(**{name: _at(f"{cls.__name__}.{name}", codec.decode, data[name]) for name, codec in fields.items()})

    codec = Codec(cls.__name__, encode, decode)
    # Registered before the fields are built: a field may refer back to cls.
    memo[cls] = codec
    hints = typing.get_type_hints(cls)
    for field in dataclasses.fields(cls):
        if not field.init:
            raise TypeError(f"{cls.__name__}.{field.name}: a field with init=False cannot be rebuilt on the other side")
        fields[field.name] = _at(f"{cls.__name__}.{field.name}", lambda hint: _build(hint, memo), hints[field.name])
    return codec


def _at(where: str, step: Callable[[Any], Any], value: Any) -> Any:
    """Run *step*, prefixing a ``TypeError`` with where in the value it happened."""
    try:
        return step(value)
    except TypeError as error:
        raise TypeError(f"{where}: {error}") from None


_SIMPLE: dict[Any, Callable[[], Codec]] = {
    type(None): lambda: _exact("None", type(None)),
    None: lambda: _exact("None", type(None)),
    bool: lambda: _exact("bool", bool),
    int: lambda: _exact("int", int),
    float: _float,
    str: lambda: _exact("str", str),
    bytes: lambda: _text(
        "bytes", bytes, lambda value: base64.b64encode(value).decode("ascii"), lambda text: base64.b64decode(text)
    ),
    datetime: lambda: _text("datetime", datetime, datetime.isoformat, datetime.fromisoformat),
    date: lambda: _text("date", date, date.isoformat, date.fromisoformat),
}

_SUPPORTED = (
    "None, bool, int, float, str, bytes, datetime, date, an Enum, a dataclass, "
    "list[T], tuple[T, ...], dict[str, T] and T | None"
)


def _build(hint: Any, memo: dict[Any, Codec]) -> Codec:
    if hint in memo:
        return memo[hint]
    if hint in _SIMPLE:
        return _SIMPLE[hint]()
    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        return _enum(hint)
    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        return _dataclass(hint, memo)

    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if origin in (Union, types.UnionType):
        rest = [arg for arg in args if arg is not type(None)]
        if len(rest) == 1 and len(args) == 2:
            return _optional(_build(rest[0], memo))
    elif origin is list and len(args) == 1:
        return _sequence(list, _build(args[0], memo))
    elif origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        return _sequence(tuple, _build(args[0], memo))
    elif origin is tuple and args and Ellipsis not in args:
        return _fixed_tuple([_build(arg, memo) for arg in args])
    elif origin is dict and len(args) == 2 and args[0] is str:
        return _mapping(_build(args[1], memo))
    raise TypeError(f"{_describe(hint)} cannot cross to a server function; the types that can are {_SUPPORTED}")


def _describe(hint: Any) -> str:
    return hint.__name__ if isinstance(hint, type) else str(hint)


def codec_for(hint: Any) -> Codec:
    """Return the codec of a type annotation.

    Args:
        hint: A resolved annotation, as ``typing.get_type_hints`` returns it.

    Raises:
        TypeError: If *hint* names a type that cannot cross.
    """
    return _build(hint, {})


__all__ = ["Codec", "Json", "codec_for"]
