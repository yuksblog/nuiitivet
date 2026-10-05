"""The types a server function exchanges, and what the other side receives."""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Optional

import pytest

from nuiitivet.remote.codec import codec_for


class Colour(enum.Enum):
    RED = 1
    GREEN = 2


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Shape:
    name: str
    colour: Colour
    points: list[Point]
    created: datetime
    note: str | None = None


@dataclass
class Tree:
    label: str
    children: list[Tree]


@dataclass
class Derived:
    width: int
    area: int = field(init=False, default=0)


def _over_the_wire(hint: Any, value: Any) -> Any:
    codec = codec_for(hint)
    return codec.decode(json.loads(json.dumps(codec.encode(value))))


@pytest.mark.parametrize(
    ("hint", "value"),
    [
        (type(None), None),
        (bool, True),
        (int, 7),
        (float, 1.5),
        (str, "text"),
        (bytes, b"\x00\xff"),
        (datetime, datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)),
        (date, date(2026, 1, 2)),
        (Colour, Colour.GREEN),
        (list[int], [1, 2]),
        (tuple[int, ...], (1, 2)),
        (tuple[int, str], (1, "a")),
        (dict[str, float], {"a": 1.0}),
        (Optional[int], None),
        (int | None, 3),
        (Point, Point(1.0, 2.0)),
        (
            Shape,
            Shape("s", Colour.RED, [Point(0.0, 1.0)], datetime(2026, 1, 2)),
        ),
        (Tree, Tree("root", [Tree("leaf", [])])),
    ],
)
def test_value_arrives_equal_and_of_the_same_type(hint: Any, value: Any) -> None:
    received = _over_the_wire(hint, value)

    assert received == value
    assert type(received) is type(value)


def test_a_received_value_is_a_copy() -> None:
    sent = [Point(1.0, 2.0)]

    received = codec_for(list[Point]).copy(sent)

    assert received == sent
    assert received is not sent
    assert received[0] is not sent[0]


def test_an_int_sent_as_float_arrives_as_float() -> None:
    received = _over_the_wire(float, 2)

    assert received == 2.0
    assert type(received) is float


@pytest.mark.parametrize(
    ("hint", "value"),
    [
        (int, True),
        (int, "1"),
        (str, 1),
        (list[int], (1, 2)),
        (list[int], [1, "2"]),
        (dict[str, int], {1: 1}),
        (tuple[int, str], (1,)),
        (Colour, 1),
        (Point, {"x": 1.0, "y": 2.0}),
        (int | None, "x"),
    ],
)
def test_a_value_of_another_type_is_rejected(hint: Any, value: Any) -> None:
    with pytest.raises(TypeError):
        codec_for(hint).encode(value)


def test_a_rejection_names_the_field() -> None:
    with pytest.raises(TypeError, match=r"Point\.y: expected float, got str"):
        codec_for(Point).encode(Point(1.0, "2"))  # type: ignore[arg-type]


def test_received_data_cannot_add_or_drop_a_field() -> None:
    codec = codec_for(Point)

    with pytest.raises(TypeError):
        codec.decode({"x": 1.0})
    with pytest.raises(TypeError):
        codec.decode({"x": 1.0, "y": 2.0, "z": 3.0})


def test_received_data_cannot_name_an_unknown_member() -> None:
    with pytest.raises(TypeError, match="not a member of Colour"):
        codec_for(Colour).decode("BLUE")


@pytest.mark.parametrize(
    "hint",
    [Any, object, set[int], dict[int, str], int | str, list, complex, Derived],
)
def test_a_type_that_cannot_cross_is_refused_when_declared(hint: Any) -> None:
    with pytest.raises(TypeError):
        codec_for(hint)
