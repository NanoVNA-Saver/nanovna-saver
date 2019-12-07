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
import unittest

# Import targets to be tested
from NanoVNASaver.RFTools import norm_to_impedance, impedance_to_norm, \
    reflection_coefficient, gamma_to_impedance, clamp_value, \
    impedance_to_capacity, impedance_to_inductance
import math


class TestRFTools(unittest.TestCase):

    def test_norm_to_impedance(self):
        self.assertEqual(norm_to_impedance(50, 0), 0)
        self.assertEqual(norm_to_impedance(1), 50)
        self.assertEqual(norm_to_impedance(-1), -50)
        self.assertEqual(norm_to_impedance(1.5), 75)
        self.assertEqual(norm_to_impedance(1, 75), 75)
        self.assertEqual(norm_to_impedance(complex(0, 1)), complex(0, 50))
        self.assertEqual(norm_to_impedance(complex(1, 1)), complex(50, 50))
        self.assertEqual(norm_to_impedance(complex(0, -1)), complex(0, -50))
        self.assertAlmostEqual(
            norm_to_impedance(complex(3.33333, 3.33333), 30),
            complex(100, 100), 3)

    def test_impedance_to_norm(self):
        self.assertRaises(ZeroDivisionError, impedance_to_norm, 0, 0)
        self.assertEqual(impedance_to_norm(0), 0)
        self.assertEqual(impedance_to_norm(50), 1)
        self.assertEqual(impedance_to_norm(-50), -1)
        self.assertEqual(impedance_to_norm(75), 1.5)
        self.assertEqual(impedance_to_norm(75, 75), 1)
        self.assertEqual(impedance_to_norm(complex(0, 50)), complex(0, 1))
        self.assertEqual(impedance_to_norm(complex(50, 50)), complex(1, 1))
        self.assertEqual(impedance_to_norm(complex(0, -50)), complex(0, -1))

        self.assertAlmostEqual(impedance_to_norm(
            complex(100, 100), 30), (complex(3.333, 3.333)), 3)

    def test_reflection_coefficient(self):
        self.assertRaises(ZeroDivisionError, reflection_coefficient, -50)
        self.assertEqual(reflection_coefficient(50), 0)
        self.assertEqual(reflection_coefficient(75), 0.2)
        # TODO: insert more test values here

    def test_gamma_to_impedance(self):
        self.assertEqual(gamma_to_impedance(0), 50)
        self.assertAlmostEqual(gamma_to_impedance(0.2), 75)
        # TODO: insert more test values here

    def test_clamp_value(self):
        self.assertEqual(clamp_value(1, 0, 10), 1)
        self.assertEqual(clamp_value(1, 2, 10), 2)
        self.assertEqual(clamp_value(1, -10, -1), -1)

    def test_impedance_to_capacity(self):
        self.assertEqual(impedance_to_capacity(0, 0), -math.inf)
