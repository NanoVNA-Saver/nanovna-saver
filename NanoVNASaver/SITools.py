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
from typing import NamedTuple
from numbers import Number

PREFIXES = ("y", "z", "a", "f", "p", "n", "µ", "m",
            "", "k", "M", "G", "T", "P", "E", "Z", "Y")

# reduced set of prefixes for user entry (used by def parse)
PARSE_PREFIXES = ("", "k", "M", "G")

class Format(NamedTuple):
    max_nr_digits: int = 6
    fix_decimals: bool = False
    space_str: str = ""
    assume_infinity: bool = True
    min_offset: int = -8
    max_offset: int = 8
    allow_strip: bool = False
    parse_sloppy_unit: bool = False
    parse_sloppy_kilo: bool = False
    parse_allow_neg: bool = True


class Value:
    def __init__(self, value: Number = 0, unit: str = "", fmt=Format()):
        assert 3 <= fmt.max_nr_digits <= 27
        assert -8 <= fmt.min_offset <= fmt.max_offset <= 8
        self.value = value
        self._unit = unit
        self.fmt = fmt

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value}, '{self._unit}', {self.fmt})"

    def __str__(self) -> str:
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

        # handle corner-case of overflow during string format rounding.
        if result[:2] == '10' and str(real)[:1] == '9':
            # if overflow was 999 -> 1000, both digits and units will be wrong
            if float(result) > 999:
                real /= 1000.0
                offset += 1
                max_digits += 2
            # otherwise, only digits will be wrong
            else:
                max_digits -= 1
            formstr = "." + str(max_digits - 3) + "f"
            result = format(real, formstr)

        if float(result) == 0.0:
            offset = 0

        if self.fmt.allow_strip and "." in result:
            result = result.rstrip("0").rstrip(".")

        return result + fmt.space_str + PREFIXES[offset + 8] + self._unit

    def parse(self, value: str) -> float:
        value = value.replace(" ", "")  # Ignore spaces

        if not self.fmt.parse_allow_neg:
            if value.startswith('-'): return -1

        if self._unit and (
                value.endswith(self._unit) or
                (self.fmt.parse_sloppy_unit and
                 value.lower().endswith(self._unit.lower()))):  # strip unit
            value = value[:-len(self._unit)]

        factor = 1
        if self.fmt.parse_sloppy_kilo and value[-1] == "K":  # fix for e.g. KHz
            value = value[:-1] + "k"
        if value[-1] in PARSE_PREFIXES:
            factor = 10 ** ((PARSE_PREFIXES.index(value[-1])) * 3)
            value = value[:-1]

        if self.fmt.assume_infinity and value == "\N{INFINITY}":
            self.value = math.inf
        elif self.fmt.assume_infinity and value == "-\N{INFINITY}":
            self.value = -math.inf
        else:
            self.value = float(value) * factor
        return self.value

    @property
    def unit(self) -> str:
        return self._unit
