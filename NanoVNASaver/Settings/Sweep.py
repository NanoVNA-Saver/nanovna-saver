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
from math import log
from threading import Lock
from typing import Iterator, Tuple

logger = logging.getLogger(__name__)


class SweepMode(Enum):
    SINGLE = 0
    CONTINOUS = 1
    AVERAGE = 2


class Properties():
    def __init__(self, name: str = "",
                 mode: 'SweepMode' = SweepMode.SINGLE,
                 averages: Tuple[int, int] = (3, 0),
                 logarithmic: bool = False):
        self.name = name
        self.mode = mode
        self.averages = averages
        self.logarithmic = logarithmic

    def __repr__(self):
        return (
            f"Properties('{self.name}', {self.mode}, {self.averages},"
            f" {self.logarithmic})")


class Sweep():
    def __init__(self, start: int = 3600000, end: int = 30000000,
                 points: int = 101, segments: int = 1,
                 properties: 'Properties' = Properties()):
        self.start = start
        self.end = end
        self.points = points
        self.segments = segments
        self.properties = properties
        self.lock = Lock()
        self.check()
        logger.debug("%s", self)

    def __repr__(self) -> str:
        return (
            f"Sweep({self.start}, {self.end}, {self.points}, {self.segments},"
            f" {self.properties})")

    def __eq__(self, other) -> bool:
        return(self.start == other.start and
               self.end == other.end and
               self.points == other.points and
               self.segments == other.segments and
               self.properties == other.properties)

    def copy(self) -> 'Sweep':
        return Sweep(self.start, self.end, self.points, self.segments,
                     self.properties)

    @property
    def span(self) -> int:
        return self.end - self.start

    @property
    def stepsize(self) -> int:
        return round(self.span / (self.points  * self.segments - 1))

    def check(self):
        if not(self.segments > 0 and
               self.points > 0 and
               self.start > 0 and
               self.end > 0 and
               self.stepsize >= 1):
            raise ValueError(f"Illegal sweep settings: {self}")

    def _exp_factor(self, index: int) -> float:
        return 1 - log(self.segments + 1 - index) / log(self.segments + 1)

    def get_index_range(self, index: int) -> Tuple[int, int]:
        if not self.properties.logarithmic:
            start = self.start + index * self.points * self.stepsize
            end = start + (self.points - 1) * self.stepsize
        else:
            start = round(self.start + self.span * self._exp_factor(index))
            end = round(self.start + self.span * self._exp_factor(index + 1))
        logger.debug("get_index_range(%s) -> (%s, %s)", index, start, end)
        return (start, end)

    def get_frequencies(self) -> Iterator[int]:
        for i in range(self.segments):
            start, stop = self.get_index_range(i)
            step = (stop - start) / self.points
            freq = start
            for _ in range(self.points):
                yield round(freq)
                freq += step
