#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
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


import sys
import unittest

# Import targets to be tested
from NanoVNASaver import RFTools
rft = RFTools.RFTools()

class TestCases(unittest.TestCase):

    '''
    INTENDED USE:
    The formatFrequency and formatShortFrequency function is intended to be used
    to fill return values in the UI that must be limited in length.
    DESIRED BEHAVIOR:
    1) The output (string) shall represent the input (number) using the smallest
    appropriate SI unit (e.g. Hz, kHz, MHz, GHz), down to at most 1 Hz resolution,
    such that the integer part of the result is always between 1 and 999.
    2) The total length of the result, including both integer and fractional digits
    shall be 6 digits total for formatFrequency, and 4 digits for formatShortFrequency.
    3) The least significant digit shall be rounded in the event that the result
    must be truncated to limit maximum size.
    '''

    def test_stdIntValuesNormal(self):
        # simple well-formed integers with no trailing zeros.
        # all results are 6 digits in length
        self.assertEqual(rft.formatFrequency(1), '1.00000Hz')
        self.assertEqual(rft.formatFrequency(12), '12.0000Hz')
        self.assertEqual(rft.formatFrequency(123), '123.000Hz')
        self.assertEqual(rft.formatFrequency(1234), '1.23400kHz')
        self.assertEqual(rft.formatFrequency(12345), '12.3450kHz')
        self.assertEqual(rft.formatFrequency(123456), '123.456kHz')
        self.assertEqual(rft.formatFrequency(1234567), '1.23457MHz')
        self.assertEqual(rft.formatFrequency(12345678), '12.3457MHz')
        self.assertEqual(rft.formatFrequency(123456789), '123.457MHz')

    def test_stdIntValuesShort(self):
        # simple well-formed integers with no trailing zeros.
        # all results are 4 digits in length
        self.assertEqual(rft.formatShortFrequency(1), '1.000Hz')
        self.assertEqual(rft.formatShortFrequency(12), '12.00Hz')
        self.assertEqual(rft.formatShortFrequency(123), '123.0Hz')
        self.assertEqual(rft.formatShortFrequency(1234), '1.234kHz')
        self.assertEqual(rft.formatShortFrequency(12345), '12.35kHz')
        self.assertEqual(rft.formatShortFrequency(123456), '123.5kHz')
        self.assertEqual(rft.formatShortFrequency(1234567), '1.235MHz')
        self.assertEqual(rft.formatShortFrequency(12345678), '12.35MHz')
        self.assertEqual(rft.formatShortFrequency(123456789), '123.5MHz')

    def test_simpleRounding(self):
        self.assertEqual(rft.formatFrequency(1.111111111), '1.11111Hz')
        self.assertEqual(rft.formatFrequency(4.444444444), '4.44444Hz')
        self.assertEqual(rft.formatFrequency(5.555555555), '5.55556Hz')
        self.assertEqual(rft.formatFrequency(6.666666666), '6.66667Hz')

    def test_overflowRounding(self):
        self.assertEqual(rft.formatFrequency(0.999999999), '1.00000Hz')
        self.assertEqual(rft.formatFrequency(9.999999999), '10.0000Hz')
        self.assertEqual(rft.formatFrequency(99.99999999), '100.000Hz')
        self.assertEqual(rft.formatFrequency(999.9999999), '1.00000kHz')
        self.assertEqual(rft.formatShortFrequency(999999), '1.000MHz')


if __name__ == '__main__':
    unittest.main(verbosity=2)
