#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
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
import unittest

# Import targets to be tested
from NanoVNASaver.RFTools import (
    Datapoint,
    clamp_value,
    corr_att_data,
    gamma_to_impedance,
    groupDelay,
    impedance_to_capacitance,
    impedance_to_inductance,
    impedance_to_norm,
    norm_to_impedance,
    parallel_to_serial,
    reflection_coefficient,
    serial_to_parallel,
)


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
            complex(100, 100),
            3,
        )

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

        self.assertAlmostEqual(
            impedance_to_norm(complex(100, 100), 30), (complex(3.333, 3.333)), 3
        )

    def test_reflection_coefficient(self):
        self.assertRaises(ZeroDivisionError, reflection_coefficient, -50)
        self.assertEqual(reflection_coefficient(50), 0)
        self.assertEqual(reflection_coefficient(75), 0.2)
        # TODO: insert more test values here

    def test_gamma_to_impedance(self):
        self.assertEqual(gamma_to_impedance(0), 50)
        self.assertAlmostEqual(gamma_to_impedance(0.2), 75)
        self.assertEqual(gamma_to_impedance(1), math.inf)
        # TODO: insert more test values here

    def test_clamp_value(self):
        self.assertEqual(clamp_value(1, 0, 10), 1)
        self.assertEqual(clamp_value(1, 2, 10), 2)
        self.assertEqual(clamp_value(1, -10, -1), -1)

    def test_parallel_to_serial(self):
        self.assertEqual(parallel_to_serial(0), complex(0, 0))
        self.assertAlmostEqual(
            parallel_to_serial(complex(52, 260)), complex(50, 10)
        )

    def test_serial_to_parallel(self):
        self.assertEqual(
            serial_to_parallel(complex(0, 0)), complex(math.inf, math.inf)
        )
        self.assertEqual(
            serial_to_parallel(complex(50, 0)), complex(50, math.inf)
        )
        self.assertEqual(
            serial_to_parallel(complex(0, 50)), complex(math.inf, 50)
        )
        self.assertAlmostEqual(
            serial_to_parallel(complex(50, 10)), complex(52, 260)
        )

    def test_impedance_to_capacity(self):
        self.assertEqual(impedance_to_capacitance(0, 0), -math.inf)
        self.assertEqual(impedance_to_capacitance(0, 10), math.inf)
        self.assertAlmostEqual(
            impedance_to_capacitance(complex(50, 159.1549), 100000), 1e-8
        )

    def test_impedance_to_inductance(self):
        self.assertEqual(impedance_to_inductance(0, 0), 0)
        self.assertAlmostEqual(
            impedance_to_inductance(complex(50, 159.1549), 100000), 2.533e-4
        )

    def test_groupDelay(self):
        dpoints = [
            Datapoint(100000, 0.1091, 0.3118),
            Datapoint(100001, 0.1091, 0.3124),
            Datapoint(100002, 0.1091, 0.3130),
        ]
        dpoints0 = [
            Datapoint(100000, 0.1091, 0.3124),
            Datapoint(100000, 0.1091, 0.3124),
            Datapoint(100000, 0.1091, 0.3124),
        ]
        self.assertAlmostEqual(groupDelay(dpoints, 1), -9.514e-5)
        self.assertEqual(groupDelay(dpoints0, 1), 0.0)

    def test_cor_att_data(self):
        dp1 = [
            Datapoint(100000, 0.1091, 0.3118),
            Datapoint(100001, 0.1091, 0.3124),
            Datapoint(100002, 0.1091, 0.3130),
        ]
        dp2 = corr_att_data(dp1, 10)
        self.assertEqual(dp2[0].gain - dp1[0].gain, 10)
        self.assertEqual(len(dp1), len(dp2))
        # ignore negative attenuation
        dp3 = corr_att_data(dp1, -10)
        self.assertEqual(dp1, dp3)


class TestRFToolsDatapoint(unittest.TestCase):

    def setUp(self):
        self.dp = Datapoint(100000, 0.1091, 0.3118)
        self.dp0 = Datapoint(100000, 0, 0)
        self.dp50 = Datapoint(100000, 1, 0)
        self.dp75 = Datapoint(100000, 0.2, 0)
        self.dp_im50 = Datapoint(100000, 0, 1)
        self.dp_ill = Datapoint(100000, 1.1, 0)
        self.dp_div0 = Datapoint(100000, 0.0, 1.0)

    def test_properties(self):
        self.assertEqual(self.dp.z, complex(0.1091, 0.3118))
        self.assertEqual(self.dp.wavelength, 2997.92458)
        self.assertAlmostEqual(self.dp.phase, 1.23420722)
        self.assertEqual(self.dp0.gain, -math.inf)
        self.assertAlmostEqual(self.dp.gain, -9.6208748)
        self.assertEqual(self.dp50.vswr, math.inf)
        self.assertEqual(self.dp_im50.vswr, math.inf)
        self.assertEqual(self.dp_ill.vswr, math.inf)
        self.assertEqual(self.dp0.vswr, 1)
        self.assertAlmostEqual(self.dp.vswr, 1.9865736)
        self.assertAlmostEqual(
            self.dp.impedance(), complex(49.997525, 34.9974501)
        )
        self.assertAlmostEqual(
            self.dp.impedance(75), complex(74.99628755, 52.49617517)
        )
        self.assertEqual(self.dp0.qFactor(), 0.0)
        self.assertEqual(self.dp75.qFactor(), 0.0)
        self.assertEqual(self.dp_im50.qFactor(), -1.0)
        self.assertAlmostEqual(self.dp.qFactor(), 0.6999837)
        self.assertAlmostEqual(self.dp.capacitiveEquivalent(), -4.54761539e-08)
        self.assertAlmostEqual(self.dp.inductiveEquivalent(), 5.57001e-05)
        self.assertAlmostEqual(
            self.dp.shuntImpedance(), complex(-6.18740998e-04, 8.749362528)
        )
        self.assertAlmostEqual(
            self.dp.seriesImpedance(), complex(-2.02067318e-2, -285.7351012)
        )
        self.assertAlmostEqual(self.dp0.shuntImpedance(), 0)
        self.assertAlmostEqual(self.dp0.seriesImpedance(), math.inf)
        self.assertAlmostEqual(self.dp50.shuntImpedance(), math.inf)
