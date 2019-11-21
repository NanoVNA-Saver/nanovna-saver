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
    The parseFrequency function is intended to interpret a frequency text string,
    which may include SI units (e.g. Hz, kHz, MHz...) or exponential notation
    (e.g. 10e3, 45e6...) and returns a positive integer number as a result, or an
    error code (e.g. -1)
    DESIRED BEHAVIOR:
    1) The output (integer) value shall represent the input (string) representation,
    based on the use of the SI units Hz, kHz, MHz or GHz, or exponential notation, or
    a numeric value.
    2) If the input string is malformed (i.e. not made up of logical legal values) then
    the output returned shall be the error code -1.
    '''

    def test_basicSIUnits(self):
        # simple well-formed integers with correct SI units
        self.assertEqual(rft.parseFrequency('123Hz'), 123)
        self.assertEqual(rft.parseFrequency('123456Hz'), 123456)
        self.assertEqual(rft.parseFrequency('123kHz'), 123000)
        self.assertEqual(rft.parseFrequency('123456kHz'), 123456000)
        self.assertEqual(rft.parseFrequency('123MHz'), 123000000)
        self.assertEqual(rft.parseFrequency('123456MHz'), 123456000000)
        self.assertEqual(rft.parseFrequency('123GHz'), 123000000000)
        self.assertEqual(rft.parseFrequency('123456GHz'), 123456000000000)

    def test_regularIntegers(self):
        self.assertEqual(rft.parseFrequency('123'), 123)
        self.assertEqual(rft.parseFrequency('123456'), 123456)
        self.assertEqual(rft.parseFrequency('123456789'), 123456789)

    def test_commonMistakeKHz_vs_kHz(self):
        # some poorly formatted values that still work as expected
        self.assertEqual(rft.parseFrequency('123kHz'), 123000)
        self.assertEqual(rft.parseFrequency('123KHz'), 123000)

    def test_illegalInputValues(self):
        # poorly formatted inputs that are identified as illegal
        self.assertEqual(rft.parseFrequency('Junk'), -1)
        self.assertEqual(rft.parseFrequency('Garbage'), -1)
        self.assertEqual(rft.parseFrequency('123.Junk'), -1)

    def test_rejectNegativeFreqValues(self):
        # negative frequencies are not useful for this application, return -1
        self.assertEqual(rft.parseFrequency('-123'), -1)
        self.assertEqual(rft.parseFrequency('-123KHz'), -1)

    def test_missingDigitsAfterPeriod(self):
        # some poorly formatted values that still work as expected
        self.assertEqual(rft.parseFrequency('123.'), 123)
        self.assertEqual(rft.parseFrequency('123.Hz'), 123)
        self.assertEqual(rft.parseFrequency('123.kHz'), 123000)
        self.assertEqual(rft.parseFrequency('123.MHz'), 123000000)
        self.assertEqual(rft.parseFrequency('123.GHz'), 123000000000)

    def test_illegalSIUnits(self):
        # The legal set of SI prefixes was redused for parseFrequency to reduce
        # the potential that typos will result in unexpected output. This tests
        # the illegal SI Units to verify a -1 error code result.
        self.assertEqual(rft.parseFrequency('123EHz'), -1)
        self.assertEqual(rft.parseFrequency('123PHz'), -1)
        self.assertEqual(rft.parseFrequency('123THz'), -1)
        self.assertEqual(rft.parseFrequency('123YHz'), -1)
        self.assertEqual(rft.parseFrequency('123ZHz'), -1)
        self.assertEqual(rft.parseFrequency('123aHz'), -1)
        self.assertEqual(rft.parseFrequency('123fHz'), -1)
        self.assertEqual(rft.parseFrequency('123mHz'), -1)
        self.assertEqual(rft.parseFrequency('123nHz'), -1)
        self.assertEqual(rft.parseFrequency('123pHz'), -1)
        self.assertEqual(rft.parseFrequency('123yHz'), -1)
        self.assertEqual(rft.parseFrequency('123zHz'), -1)

    def test_partialHzText(self):
        # Accidentally missing the H in Hz, previously resulted in detection
        # of the 'z' SI unit (zepto = 10^-21), which then rounded to 0.
        # After reduction of legal SI values in SITools, this now returns
        # a -1 failure code instead.
        self.assertEqual(rft.parseFrequency('123z'), -1)
        self.assertEqual(rft.parseFrequency('123.z'), -1)
        self.assertEqual(rft.parseFrequency('1.23z'), -1)

    def test_basicExponentialNotation(self):
        # check basic exponential notation
        self.assertEqual(rft.parseFrequency('123e3'), 123000)
        self.assertEqual(rft.parseFrequency('123e6'), 123000000)
        self.assertEqual(rft.parseFrequency('123e9'), 123000000000)
        self.assertEqual(rft.parseFrequency('123e4'), 1230000)
        self.assertEqual(rft.parseFrequency('123e12'), 123000000000000)
        self.assertEqual(rft.parseFrequency('123e18'), 123000000000000000000)

    def test_negativeExponentialNotation(self):
        # negative exponential values resulting in N < 0, return 0
        self.assertEqual(rft.parseFrequency('123e-3'), 0)
        self.assertEqual(rft.parseFrequency('1234e-4'), 0)
        self.assertEqual(rft.parseFrequency('12345e-5'), 0)
        self.assertEqual(rft.parseFrequency('12345678e-8'), 0)
        # negative exponential values resulting in N > 0, return N
        self.assertEqual(rft.parseFrequency('100000e-5'), 1)
        self.assertEqual(rft.parseFrequency('100000e-4'), 10)
        self.assertEqual(rft.parseFrequency('100000e-3'), 100)
        self.assertEqual(rft.parseFrequency('100000e-2'), 1000)
        self.assertEqual(rft.parseFrequency('100000e-1'), 10000)

    def test_multiplePeriods(self):
        # multiple periods are properly detected as bad
        self.assertEqual(rft.parseFrequency('123..Hz'), -1)
        self.assertEqual(rft.parseFrequency('123...Hz'), -1)
        self.assertEqual(rft.parseFrequency('123....Hz'), -1)
        self.assertEqual(rft.parseFrequency('1.23.Hz'), -1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
