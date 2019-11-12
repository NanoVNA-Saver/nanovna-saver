#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
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
import math
from numbers import Number

PREFIXES = ("y", "z", "a", "f", "p", "n", "µ", "m",
            "", "k", "M", "G", "T", "P", "E", "Z", "Y")


class Format(object):
    def __init__(self,
                 max_nr_digits: int = 6,
                 fix_decimals: bool = False,
                 space_str: str = "",
                 assume_infinity: bool = True,
                 min_offset: int = -8,
                 max_offset: int = 8):
        assert(min_offset >= -8 and max_offset <= 8 and min_offset < max_offset)
        self.max_nr_digits = max_nr_digits
        self.fix_decimals = fix_decimals
        self.space_str = space_str
        self.assume_infinity = assume_infinity
        self.min_offset = min_offset
        self.max_offset = max_offset

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"{self.max_nr_digits}, {self.fix_decimals}, "
                f"'{self.space_str}', {self.assume_infinity}, "
                f"{self.min_offset}, {self.max_offset})")


class Value(object):
    def __init__(self, value: Number = 0, unit: str = "", fmt=Format()):
        self.value = value
        self._unit = unit
        self.fmt = fmt

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value}, '{self._unit}', {self.fmt})"

    def __str__(self):
        fmt = self.fmt
        if fmt.assume_infinity and abs(self.value) >= 10 ** ((fmt.max_offset + 1) * 3):
            return ("-" if self.value < 0 else "") + "\N{INFINITY}" + fmt.space_str + self._unit

        if self.value == 0:
            offset = 0
        else:
            offset = int(math.log10(abs(self.value)) // 3)

        if offset < fmt.min_offset:
            offset = fmt.min_offset
        elif offset > fmt.max_offset:
            offset = fmt.max_offset

        real = self.value / (10 ** (offset * 3))

        if fmt.max_nr_digits < 4:
            formstr = ".0f"
        else:
            max_digits = fmt.max_nr_digits + (
                (1 if not fmt.fix_decimals and abs(real) < 10 else 0) +
                (1 if not fmt.fix_decimals and abs(real) < 100 else 0))
            formstr = "." + str(max_digits - 3) + "f"

        result = format(real, formstr)

        if float(result) == 0.0:
            offset = 0

        return result + fmt.space_str + PREFIXES[offset + 8] + self._unit

    def parse(self, value: str):
        value = value.replace(" ", "")  # Ignore spaces
        if self._unit and value.endswith(self._unit) or value.lower().endswith(self._unit.lower()):  # strip unit
            value = value[:-len(self._unit)]

        factor = 1
        if value[-1] in PREFIXES:
            factor = 10 ** ((PREFIXES.index(value[-1]) - 8) * 3)
            value = value[:-1]
        elif value[-1] == 'K':
            # Fix for the very common KHz
            factor = 10 ** ((PREFIXES.index(value[-1].lower()) - 8) * 3)
            value = value[:-1]
        self.value = float(value) * factor
        return self.value

    @property
    def unit(self):
        return self._unit
