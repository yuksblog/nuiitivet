"""Result of value to vector conversion."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Tuple

T = TypeVar("T")


class VectorConverter(ABC, Generic[T]):
    """Interface for converting values to/from animation vectors."""

    @abstractmethod
    def to_vector(self, value: T) -> List[float]:
        """Convert a value to a list of floats."""
        ...

    @abstractmethod
    def from_vector(self, vector: List[float]) -> T:
        """Convert a list of floats back to a value."""
        ...


class FloatConverter(VectorConverter[float]):
    """Converter for single float values."""

    def to_vector(self, value: float) -> List[float]:
        return [value]

    def from_vector(self, vector: List[float]) -> float:
        return vector[0]


def _clamp_channel(value: float) -> int:
    try:
        return max(0, min(255, int(round(float(value)))))
    except Exception:
        return 0


class RgbaTupleConverter(VectorConverter[Tuple[int, int, int, int]]):
    """Converter for RGBA tuples."""

    def to_vector(self, value: Tuple[int, int, int, int]) -> List[float]:
        return [float(_clamp_channel(channel)) for channel in value]

    def from_vector(self, vector: List[float]) -> Tuple[int, int, int, int]:
        if len(vector) != 4:
            raise ValueError("RGBA vector must contain exactly 4 channels")
        return (
            _clamp_channel(vector[0]),
            _clamp_channel(vector[1]),
            _clamp_channel(vector[2]),
            _clamp_channel(vector[3]),
        )


__all__ = ["VectorConverter", "FloatConverter", "RgbaTupleConverter"]
