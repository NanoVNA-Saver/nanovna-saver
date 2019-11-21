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
    The formatSweepFrequency function is intended to be used to fill the sweep
    control text fields, where the displayed values should be short and easily
    readable if possible, but must maintain accuracy to single Hz precision.
    DESIRED BEHAVIOR:
    1) The output (string) shall represent the input (number) using the smallest
    appropriate SI unit (e.g. Hz, kHz, MHz, GHz), down to at most 1 Hz resolution,
    such that the integer part of the result is always between 1 and 999.
    2) The fractional part of the result shall be as short as possible, without loss
    of accuracy, inludding the possibility that no fractional part is returned.
    3) If no fractional part is returned, the decimal shall also not be displayed.
    4) Minimum supported return value shall be >= 1 Hz
    4) Maximum supported return value shall be < 10 GHz.
    '''

    def test_standardIntegerValues(self):
        # simple well-formed integers with no trailing zeros. Most importantly
        # there is no loss of accuracy in the result. Returned values are not
        # truncated if result would lose meaningful data.
        self.assertEqual(rft.formatSweepFrequency(1), '1Hz')
        self.assertEqual(rft.formatSweepFrequency(12), '12Hz')
        self.assertEqual(rft.formatSweepFrequency(123), '123Hz')
        self.assertEqual(rft.formatSweepFrequency(1234), '1.234kHz')
        self.assertEqual(rft.formatSweepFrequency(12345), '12.345kHz')
        self.assertEqual(rft.formatSweepFrequency(123456), '123.456kHz')
        self.assertEqual(rft.formatSweepFrequency(1234567), '1.234567MHz')
        self.assertEqual(rft.formatSweepFrequency(12345678), '12.345678MHz')
        self.assertEqual(rft.formatSweepFrequency(123456789), '123.456789MHz')
        self.assertEqual(rft.formatSweepFrequency(1023456789), '1.023456789GHz')

    def test_largeIntegerValues(self):
        self.assertEqual(rft.formatSweepFrequency(10023456789), '10.02345679GHz')
        self.assertEqual(rft.formatSweepFrequency(100023456789), '100.0234568GHz')
        self.assertEqual(rft.formatSweepFrequency(1000023456789), '1.000023457THz')

    def test_smallIntegerValues(self):
        self.assertEqual(rft.formatSweepFrequency(0.1), '100mHz')
        self.assertEqual(rft.formatSweepFrequency(0.0001), '100µHz')
        self.assertEqual(rft.formatSweepFrequency(0.0000001), '100nHz')

    def test_trailingZeroesNoFrac(self):
        # simple integers with trailing zeros and no fractional parts, results
        # in stripping all trailing zeros, and the decimal point.
        self.assertEqual(rft.formatSweepFrequency(1000), '1kHz')
        self.assertEqual(rft.formatSweepFrequency(10000), '10kHz')
        self.assertEqual(rft.formatSweepFrequency(100000), '100kHz')
        self.assertEqual(rft.formatSweepFrequency(1000000), '1MHz')

    def test_trailingZeroesWithFrac(self):
        # simple integers with trailing zeros that also have some fractional parts.
        # result retains all parts required for accuracy, but strips remaining
        # trailing zeros.
        self.assertEqual(rft.formatSweepFrequency(1200), '1.2kHz')
        self.assertEqual(rft.formatSweepFrequency(10200), '10.2kHz')
        self.assertEqual(rft.formatSweepFrequency(100020), '100.02kHz')
        self.assertEqual(rft.formatSweepFrequency(1000200), '1.0002MHz')


if __name__ == '__main__':
    unittest.main(verbosity=2)
