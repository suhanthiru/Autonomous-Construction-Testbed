"""Declared ideal overhead height sensor; masked cells never expose hidden heights."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SurfacePacket:
    origin_xy_m: tuple[float, float]
    cell_size_m: float
    width: int
    height: int
    heights_m: tuple[float, ...]
    visible: tuple[bool, ...]

    def __post_init__(self):
        if len(self.origin_xy_m) != 2 or not all(isfinite(v) for v in self.origin_xy_m):
            raise ValueError("surface origin must contain two finite world coordinates")
        if not isfinite(self.cell_size_m) or self.cell_size_m <= 0:
            raise ValueError("surface cell size must be finite and positive")
        if any(type(v) is not int or v < 1 for v in (self.width, self.height)):
            raise ValueError("surface dimensions must be positive integers")
        if len(self.heights_m) != self.width * self.height or len(self.visible) != len(
            self.heights_m
        ):
            raise ValueError("surface arrays do not match dimensions")
        for value, valid in zip(self.heights_m, self.visible, strict=True):
            if type(valid) is not bool or not isfinite(value):
                raise ValueError("surface samples must be finite with boolean visibility")
            if not valid and value != 0:
                raise ValueError("masked surface cells must contain zero")
