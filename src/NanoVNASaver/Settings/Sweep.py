#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
from enum import Enum
from math import exp, log
from threading import Lock
from typing import Iterator, NamedTuple

logger = logging.getLogger(__name__)


class SweepMode(Enum):
    SINGLE = 0
    CONTINOUS = 1
    AVERAGE = 2


class Properties(NamedTuple):
    name: str = ""
    mode: "SweepMode" = SweepMode.SINGLE
    averages: tuple[int, int] = (3, 0)
    logarithmic: bool = False


class Sweep:
    def __init__(
        self,
        start: int = 3600000,
        end: int = 30000000,
        points: int = 101,
        segments: int = 1,
        properties: "Properties" = None,
    ):
        self._start = start
        self._end = end
        self._points = points
        self._segments = segments
        self._properties = properties or Properties()
        self._lock = Lock()
        self.check()
        logger.debug("%s", self)

    def __repr__(self) -> str:
        return (
            "Sweep("
            + ", ".join(
                map(
                    str,
                    (
                        self.start,
                        self.end,
                        self.points,
                        self.segments,
                        self.properties,
                    ),
                )
            )
            + ")"
        )

    def __eq__(self, other) -> bool:
        return (
            self.start == other.start
            and self.end == other.end
            and self.points == other.points
            and self.segments == other.segments
            and self.properties == other.properties
        )

    def copy(self) -> "Sweep":
        with self._lock:
            return Sweep(
                self.start,
                self.end,
                self.points,
                self.segments,
                self._properties,
            )

    # Getters for attributes, either private or computed.

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    @property
    def points(self) -> int:
        return self._points

    @property
    def segments(self) -> int:
        return self._segments

    # Properties are immutable, this does not circumvent the accessors.
    @property
    def properties(self) -> "Properties":
        return self._properties

    @property
    def span(self) -> int:
        return self.end - self.start

    @property
    def stepsize(self) -> int:
        return round(self.span / (self.points * self.segments - 1))

    # Setters

    def set_points(self, points: int) -> None:
        with self._lock:
            self._points = points
            self.check()

    def update(self, start: int, end: int, segments: int, points: int) -> None:
        with self._lock:
            self._start = max(start, 1)
            self._end = max(end, start)
            self._segments = max(segments, 1)
            self._points = max(points, 1)
            self.check()

    def set_name(self, name: str) -> None:
        with self._lock:
            self._properties = self.properties._replace(name=name)

    def set_mode(self, mode: "SweepMode") -> None:
        with self._lock:
            self._properties = self.properties._replace(mode=mode)

    def set_averages(self, amount: int, truncates: int) -> None:
        with self._lock:
            self._properties = self.properties._replace(
                averages=(amount, truncates)
            )

    def set_logarithmic(self, logarithmic: bool) -> None:
        with self._lock:
            self._properties = self.properties._replace(logarithmic=logarithmic)

    def check(self):
        if (
            self.segments < 1
            or self.points < 1
            or self.start < 1
            or self.end < self.start
            or self.stepsize < 0
        ):
            raise ValueError(f"Illegal sweep settings: {self}")

    def _exp_factor(self, index: int) -> float:
        return exp(
            log((self.start + self.span) / self.start) / self.segments * index
        )

    def get_index_range(self, index: int) -> tuple[int, int]:
        if self.properties.logarithmic:
            start = round(self.start * self._exp_factor(index))
            end = round(self.start * self._exp_factor(index + 1))
        else:
            start = self.start + index * self.points * self.stepsize
            end = start + (self.points - 1) * self.stepsize
        logger.debug("get_index_range(%s) -> (%s, %s)", index, start, end)
        return start, end

    def get_frequencies(self) -> Iterator[int]:
        for i in range(self.segments):
            start, stop = self.get_index_range(i)
            step = (stop - start) / (self.points - 1)
            freq = start
            for _ in range(self.points):
                yield round(freq)
                freq += step
