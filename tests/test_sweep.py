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

# Import targets to be tested
from NanoVNASaver.Settings.Sweep import Sweep, Properties


class TestCases(unittest.TestCase):

    def test_sweep(self):
        sweep = Sweep()
        self.assertEqual(str(sweep),
                         "Sweep(3600000, 30000000, 101, 1, Properties('',"
                         " SweepMode.SINGLE, (3, 0), False))")
        self.assertTrue(Sweep(3600000) == sweep)
        self.assertFalse(Sweep(3600001) == sweep)
        self.assertRaises(ValueError, Sweep, -1)
        sweep = Sweep(segments=3)
        self.assertEqual(sweep.get_index_range(1), (12429117, 21170817))
        data = list(sweep.get_frequencies())
        self.assertEqual(data[0], 3600000)
        self.assertEqual(data[-1], 29913383)
        sweep = Sweep(segments=3, properties=Properties(logarithmic=True))
        self.assertEqual(sweep.get_index_range(1), (9078495, 16800000))
        data = list(sweep.get_frequencies())
        self.assertEqual(data[0], 3600000)
        self.assertEqual(data[-1], 29869307)

        sweep2 = sweep.copy()
        self.assertEqual(sweep, sweep2)
