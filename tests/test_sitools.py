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
import unittest
from decimal import Decimal  # noqa: F401
from math import inf, nan

# Import targets to be tested
from NanoVNASaver.SITools import (
    Format,
    Value,
    log_floor_125,
    round_ceil,
    round_floor,
)

F_DEFAULT = Format()

F_ASSERT_DIGITS_0 = Format(max_nr_digits=0)
F_ASSERT_DIGITS_2 = Format(max_nr_digits=31)
F_ASSERT_OFFSET_1 = Format(min_offset=-11)
F_ASSERT_OFFSET_2 = Format(max_offset=11)
F_ASSERT_OFFSET_3 = Format(min_offset=11)
F_ASSERT_CLAMP = Format(parse_clamp_min=10, parse_clamp_max=9)

F_DIGITS_1 = Format(
    max_nr_digits=1, min_offset=-2, max_offset=2, assume_infinity=False
)
F_DIGITS_3 = Format(
    max_nr_digits=3, min_offset=-2, max_offset=2, assume_infinity=False
)
F_DIGITS_4 = Format(max_nr_digits=4)
F_DIGITS_31 = Format(max_nr_digits=31)

F_WITH_SPACE = Format(space_str=" ")
F_WITH_UNDERSCORE = Format(space_str="_")


class TestSIToolsValue(unittest.TestCase):

    def test_format_assertions(self):
        self.assertRaises(AssertionError, Value, fmt=F_ASSERT_DIGITS_0)
        self.assertRaises(AssertionError, Value, fmt=F_ASSERT_DIGITS_2)
        self.assertRaises(AssertionError, Value, fmt=F_ASSERT_OFFSET_1)
        self.assertRaises(AssertionError, Value, fmt=F_ASSERT_OFFSET_2)
        self.assertRaises(AssertionError, Value, fmt=F_ASSERT_OFFSET_3)
        self.assertRaises(AssertionError, Value, fmt=F_ASSERT_CLAMP)

    def test_representation(self):
        a = Value(1)
        b = eval(repr(a))
        self.assertEqual(repr(a), repr(b))

    def test_default_format(self):
        self.assertEqual(str(Value(0)), "0.00000")
        self.assertEqual(str(Value(1)), "1.00000")
        self.assertEqual(str(Value(10)), "10.0000")
        self.assertEqual(str(Value(100)), "100.000")
        self.assertEqual(str(Value(-1)), "-1.00000")
        self.assertEqual(str(Value(-10)), "-10.0000")
        self.assertEqual(str(Value(-100)), "-100.000")

        self.assertEqual(str(Value(1e3)), "1.00000k")
        self.assertEqual(str(Value(1e4)), "10.0000k")
        self.assertEqual(str(Value(1e5)), "100.000k")
        self.assertEqual(str(Value(1e6)), "1.00000M")
        self.assertEqual(str(Value(1e7)), "10.0000M")
        self.assertEqual(str(Value(1e8)), "100.000M")
        self.assertEqual(str(Value(1e9)), "1.00000G")
        self.assertEqual(str(Value(1e12)), "1.00000T")
        self.assertEqual(str(Value(1e15)), "1.00000P")
        self.assertEqual(str(Value(1e18)), "1.00000E")
        self.assertEqual(str(Value(1e21)), "1.00000Z")
        self.assertEqual(str(Value(1e24)), "1.00000Y")
        self.assertEqual(str(Value(1e27)), "1.00000R")
        self.assertEqual(str(Value(1e30)), "1.00000Q")
        self.assertEqual(str(Value(1e34)), "\N{INFINITY}")
        self.assertEqual(str(Value(-1e34)), "-\N{INFINITY}")
        self.assertEqual(str(Value(nan)), "-")
        self.assertEqual(float(Value(1e27)), 1e27)
        self.assertEqual(str(Value(11, fmt=Format(printable_max=10))), "")
        self.assertEqual(
            str(Value(11, fmt=Format(allways_signed=True))), "+11.0000"
        )

        self.assertEqual(str(Value(0.1)), "100.000m")
        self.assertEqual(str(Value(0.01)), "10.0000m")
        self.assertEqual(str(Value(0.001)), "1.00000m")
        self.assertEqual(str(Value(1e-6)), "1.00000µ")
        self.assertEqual(str(Value(1e-9)), "1.00000n")
        self.assertEqual(str(Value(1e-12)), "1.00000p")
        self.assertEqual(str(Value(1e-15)), "1.00000f")
        self.assertEqual(str(Value(1e-18)), "1.00000a")
        self.assertEqual(str(Value(1e-21)), "1.00000z")
        self.assertEqual(str(Value(1e-24)), "1.00000y")
        self.assertEqual(str(Value(1e-27)), "1.00000r")
        self.assertEqual(str(Value(1e-30)), "1.00000q")
        self.assertEqual(str(Value(1e-33)), "0.00100q")
        self.assertEqual(str(Value(1e-35)), "0.00001q")
        self.assertEqual(str(Value(-1e-35)), "-0.00001q")
        self.assertEqual(str(Value(1e-36)), "0.00000")
        self.assertEqual(float(Value(1e-36)), 1e-36)

    def test_format_digits_1(self):
        v = Value(fmt=F_DIGITS_1)
        self.assertEqual(str(v.parse("1")), "1")
        self.assertEqual(str(v.parse("10")), "10")
        self.assertEqual(str(v.parse("100")), "100")
        self.assertEqual(str(v.parse("1e3")), "1k")
        self.assertEqual(str(v.parse("1e4")), "10k")
        self.assertEqual(str(v.parse("1e5")), "100k")
        self.assertEqual(str(v.parse("1e9")), "1000M")
        self.assertEqual(str(v.parse("1e-1")), "100m")
        self.assertEqual(str(v.parse("1e-2")), "10m")
        self.assertEqual(str(v.parse("1e-3")), "1m")
        self.assertEqual(str(v.parse("1e-9")), "0")

    def test_format_digits_3(self):
        v = Value(fmt=F_DIGITS_3)
        self.assertEqual(str(v.parse("1")), "1.00")
        self.assertEqual(str(v.parse("10")), "10.0")
        self.assertEqual(str(v.parse("100")), "100")
        self.assertEqual(str(v.parse("1e3")), "1.00k")
        self.assertEqual(str(v.parse("1e4")), "10.0k")
        self.assertEqual(str(v.parse("1e5")), "100k")
        self.assertEqual(str(v.parse("1e9")), "1000M")
        self.assertEqual(str(v.parse("1e-1")), "100m")
        self.assertEqual(str(v.parse("1e-2")), "10.0m")
        self.assertEqual(str(v.parse("1e-3")), "1.00m")
        self.assertEqual(str(v.parse("1e-9")), "0.00")

    def test_format_digits_4(self):
        v = Value(fmt=F_DIGITS_4)
        self.assertEqual(str(v.parse("1")), "1.000")
        self.assertEqual(str(v.parse("10")), "10.00")
        self.assertEqual(str(v.parse("100")), "100.0")
        self.assertEqual(str(v.parse("1e3")), "1.000k")
        self.assertEqual(str(v.parse("1e4")), "10.00k")
        self.assertEqual(str(v.parse("1e5")), "100.0k")
        self.assertEqual(str(v.parse("1e-1")), "100.0m")
        self.assertEqual(str(v.parse("1e-2")), "10.00m")
        self.assertEqual(str(v.parse("1e-3")), "1.000m")
        self.assertEqual(v.parse("\N{INFINITY}").value, inf)
        self.assertEqual(v.parse("-\N{INFINITY}").value, -inf)

    def test_format_attributes(self):
        v = Value("10.0", "Hz", fmt=F_DIGITS_4)
        self.assertEqual(v.value, 10.0)
        v.value = 11
        self.assertEqual(v.value, 11)
        v.parse(12)
        self.assertEqual(v.value, 12)
        v.parse("12 GHz")
        self.assertEqual(v.unit, "Hz")

    def test_rounding(self):
        self.assertEqual(round_floor(123.456), 123)
        self.assertEqual(round_floor(123.456, 1), 123.4)
        self.assertEqual(round_floor(123.456, -1), 120)
        self.assertEqual(round_ceil(123.456), 124)
        self.assertEqual(round_ceil(123.456, 1), 123.5)
        self.assertEqual(round_ceil(123.456, -1), 130)


# TODO: test F_DIGITS_31
#            F_WITH_SPACE
#            F_WITH_UNDERSCORE


class TestSIToolsFunctions(unittest.TestCase):

    def test_log_floor_125(self):
        self.assertEqual(log_floor_125(1), 1)
        self.assertEqual(log_floor_125(2), 2)
        self.assertEqual(log_floor_125(5), 5)
        self.assertEqual(log_floor_125(1000), 1000)
        self.assertEqual(log_floor_125(2000), 2000)
        self.assertEqual(log_floor_125(5000), 5000)
        self.assertEqual(log_floor_125(0.01), 0.01)
        self.assertEqual(log_floor_125(0.02), 0.02)
        self.assertEqual(log_floor_125(0.05), 0.05)
        self.assertEqual(log_floor_125(1.9), 1)
        self.assertEqual(log_floor_125(4.5), 2)
        self.assertEqual(log_floor_125(9.9), 5)
