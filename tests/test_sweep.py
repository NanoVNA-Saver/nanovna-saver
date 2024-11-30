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
from NanoVNASaver.Settings.Sweep import Properties, Sweep, SweepMode


class TestCases(unittest.TestCase):

    def test_sweep(self):
        sweep = Sweep()
        self.assertEqual(sweep.start, 3600000)
        self.assertEqual(sweep.end, 30000000)
        self.assertEqual(sweep.points, 101)
        self.assertEqual(sweep.segments, 1)

        properties = sweep.properties
        self.assertEqual(properties.name, "")
        self.assertEqual(properties.mode, SweepMode.SINGLE)
        self.assertEqual(properties.averages, (3, 0))
        self.assertFalse(properties.logarithmic)

        self.assertTrue(Sweep(3600000) == sweep)
        self.assertFalse(Sweep(3600001) == sweep)
        self.assertRaises(ValueError, Sweep, -1)
        sweep = Sweep(segments=3)
        self.assertEqual(sweep.get_index_range(1), (12429117, 21170817))
        data = list(sweep.get_frequencies())
        self.assertEqual(data[0], 3600000)
        self.assertEqual(data[-1], 29999934)  # should be close to 30000000
        sweep = Sweep(segments=3, properties=Properties(logarithmic=True))
        self.assertEqual(sweep.get_index_range(1), (7298642, 14797272))
        data = list(sweep.get_frequencies())
        self.assertEqual(data[0], 3600000)
        self.assertEqual(data[-1], 30000000)

        sweep2 = sweep.copy()
        self.assertEqual(sweep, sweep2)

        sweep.set_points(14)
        self.assertEqual(sweep.points, 14)
        sweep.set_name("bla")
        self.assertEqual(sweep.properties.name, "bla")
