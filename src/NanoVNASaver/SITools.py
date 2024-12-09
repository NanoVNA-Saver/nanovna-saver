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
from __future__ import annotations

import math
from decimal import Context, Decimal, InvalidOperation
from numbers import Number, Real
from typing import NamedTuple

PREFIXES = (
    "q",
    "r",
    "y",
    "z",
    "a",
    "f",
    "p",
    "n",
    "µ",
    "m",
    "",
    "k",
    "M",
    "G",
    "T",
    "P",
    "E",
    "Z",
    "Y",
    "R",
    "Q",
)


def clamp_value(value: Real, rmin: Real, rmax: Real) -> Real:
    assert rmin <= rmax
    return rmin if value < rmin else min(value, rmax)


def round_ceil(value: Real, digits: int = 0) -> Real:
    factor = 10**-digits
    return factor * math.ceil(value / factor)


def round_floor(value: Real, digits: int = 0) -> Real:
    factor = 10**-digits
    return factor * math.floor(value / factor)


def log_floor_125(x: float) -> float:
    log_base = 10 ** (math.floor(math.log10(x)))
    log_factor = x / log_base
    if log_factor >= 5:  # noqa: PLR2004
        return 5 * log_base
    return 2 * log_base if log_factor >= 2 else log_base  # noqa: PLR2004


class Format(NamedTuple):
    max_nr_digits: int = 6
    fix_decimals: bool = False
    space_str: str = ""
    assume_infinity: bool = True
    min_offset: int = -10
    max_offset: int = 10
    allow_strip: bool = False
    allways_signed: bool = False
    printable_min: float = -math.inf
    printable_max: float = math.inf
    unprintable_under: str = ""
    unprintable_over: str = ""
    parse_sloppy_unit: bool = False
    parse_sloppy_kilo: bool = False
    parse_clamp_min: float = -math.inf
    parse_clamp_max: float = math.inf


DEFAULT_FMT = Format()


class Value:
    CTX = Context(prec=60, Emin=-33, Emax=33)

    def __init__(
        self, value: Real = Decimal(0), unit: str = "", fmt=DEFAULT_FMT
    ) -> None:
        assert 1 <= fmt.max_nr_digits <= 30  # noqa: PLR2004
        assert -10 <= fmt.min_offset <= fmt.max_offset <= 10  # noqa: PLR2004
        assert fmt.parse_clamp_min < fmt.parse_clamp_max
        assert fmt.printable_min < fmt.printable_max
        self._unit = unit
        self.fmt = fmt
        if isinstance(value, str):
            self._value = Decimal(math.nan)
            if value.lower() != "nan":
                self.parse(value)
        else:
            self._value = Decimal(value, context=Value.CTX)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"{repr(self._value)}, '{self._unit}', {self.fmt})"
        )

    def __str__(self) -> str:
        fmt = self.fmt
        if math.isnan(self._value):
            return f"-{fmt.space_str}{self._unit}"
        if fmt.assume_infinity and abs(self._value) >= 10 ** (
            (fmt.max_offset + 1) * 3
        ):
            return (
                ("-" if self._value < 0 else "")
                + "\N{INFINITY}"
                + fmt.space_str
                + self._unit
            )
        if self._value < fmt.printable_min:
            return fmt.unprintable_under + self._unit
        if self._value > fmt.printable_max:
            return fmt.unprintable_over + self._unit

        offset = (
            clamp_value(
                int(math.log10(abs(self._value)) // 3),
                fmt.min_offset,
                fmt.max_offset,
            )
            if self._value
            else 0
        )

        real = float(self._value) / (10 ** (offset * 3))

        if fmt.max_nr_digits < 3:  # noqa: PLR2004
            formstr = ".0f"
        else:
            max_digits = fmt.max_nr_digits + (
                (
                    1
                    if not fmt.fix_decimals and abs(real) < 10  # noqa: PLR2004
                    else 0
                )
                + (
                    1
                    if not fmt.fix_decimals and abs(real) < 100  # noqa: PLR2004
                    else 0
                )
            )
            formstr = f".{max_digits - 3}f"

        if self.fmt.allways_signed:
            formstr = f"+{formstr}"
        result = format(real, formstr)

        if float(result) == 0.0:
            offset = 0

        if self.fmt.allow_strip and "." in result:
            result = result.rstrip("0").rstrip(".")

        return result + fmt.space_str + PREFIXES[offset + 10] + self._unit

    def __int__(self):
        return round(self._value)

    def __float__(self):
        return float(self._value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: Number):
        self._value = Decimal(value, context=Value.CTX)

    def parse(self, value: str) -> "Value":
        if isinstance(value, Number):
            self.value = value
            return self

        value = value.replace(" ", "")  # Ignore spaces

        if self._unit and (
            value.endswith(self._unit)
            or (
                self.fmt.parse_sloppy_unit
                and value.lower().endswith(self._unit.lower())
            )
        ):  # strip unit
            value = value[: -len(self._unit)]

        factor = 1
        # fix for e.g. KHz, mHz gHz as milli-Hertz mostly makes no
        # sense in NanoVNAs context
        if self.fmt.parse_sloppy_kilo and value[-1] in ("K", "m", "g"):
            value = value[:-1] + value[-1].swapcase()
        if value[-1] in PREFIXES:
            factor = 10 ** ((PREFIXES.index(value[-1]) - 10) * 3)
            value = value[:-1]

        if self.fmt.assume_infinity and value == "\N{INFINITY}":
            self._value = math.inf
        elif self.fmt.assume_infinity and value == "-\N{INFINITY}":
            self._value = -math.inf
        else:
            try:
                self._value = Decimal(value, context=Value.CTX) * Decimal(
                    factor, context=Value.CTX
                )
            except InvalidOperation as exc:
                raise ValueError() from exc
            self._value = clamp_value(
                self._value, self.fmt.parse_clamp_min, self.fmt.parse_clamp_max
            )
        return self

    @property
    def unit(self) -> str:
        return self._unit
