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
from NanoVNASaver import Formatting as fmt


class TestCases(unittest.TestCase):

    def test_format_frequency(self):
        self.assertEqual(fmt.format_frequency(1), '1.00000Hz')
        self.assertEqual(fmt.format_frequency(12), '12.0000Hz')
        self.assertEqual(fmt.format_frequency(123), '123.000Hz')
        self.assertEqual(fmt.format_frequency(1234), '1.23400kHz')
        self.assertEqual(fmt.format_frequency(1234567), '1.23457MHz')
        self.assertEqual(fmt.format_frequency(1234567890), '1.23457GHz')
        self.assertEqual(fmt.format_frequency(0), '0.00000Hz')
        self.assertEqual(fmt.format_frequency(-1), '-1.00000Hz')

        self.assertEqual(fmt.format_frequency_space(1), '1.00000 Hz')
        self.assertEqual(fmt.format_frequency_space(12), '12.0000 Hz')
        self.assertEqual(fmt.format_frequency_space(123), '123.000 Hz')
        self.assertEqual(fmt.format_frequency_space(1234), '1.23400 kHz')
        self.assertEqual(fmt.format_frequency_space(1234567), '1.23457 MHz')
        self.assertEqual(fmt.format_frequency_space(1234567890), '1.23457 GHz')
        self.assertEqual(fmt.format_frequency_space(0), '0.00000 Hz')
        self.assertEqual(fmt.format_frequency_space(-1), '-1.00000 Hz')

        self.assertEqual(fmt.format_frequency_short(1), '1.000Hz')
        self.assertEqual(fmt.format_frequency_short(12), '12.00Hz')
        self.assertEqual(fmt.format_frequency_short(123), '123.0Hz')
        self.assertEqual(fmt.format_frequency_short(1234), '1.234kHz')
        self.assertEqual(fmt.format_frequency_short(1234567), '1.235MHz')
        self.assertEqual(fmt.format_frequency_short(1234567890), '1.235GHz')
        self.assertEqual(fmt.format_frequency_short(0), '0.000Hz')
        self.assertEqual(fmt.format_frequency_short(-1), '-1.000Hz')

        self.assertEqual(fmt.format_frequency_chart(1), '1.000')
        self.assertEqual(fmt.format_frequency_chart(12), '12.00')
        self.assertEqual(fmt.format_frequency_chart(123), '123.0')
        self.assertEqual(fmt.format_frequency_chart(1234), '1.234k')
        self.assertEqual(fmt.format_frequency_chart(1234567), '1.235M')
        self.assertEqual(fmt.format_frequency_chart(1234567890), '1.235G')
        self.assertEqual(fmt.format_frequency_chart(0), '0.000')
        self.assertEqual(fmt.format_frequency_chart(-1), '-1.000')

    def test_format_frequency_inputs(self):
        self.assertEqual(fmt.format_frequency_inputs(1), '1Hz')
        self.assertEqual(fmt.format_frequency_inputs(12), '12Hz')
        self.assertEqual(fmt.format_frequency_inputs(123), '123Hz')
        self.assertEqual(fmt.format_frequency_inputs(1234), '1.234kHz')
        self.assertEqual(fmt.format_frequency_inputs(1234567), '1.234567MHz')
        self.assertEqual(fmt.format_frequency_inputs(1234567890), '1.23456789GHz')
        self.assertEqual(fmt.format_frequency_inputs(0), '0Hz')
        self.assertEqual(fmt.format_frequency_inputs(-1), '- Hz')

    def test_format_gain(self):
        self.assertEqual(fmt.format_gain(1), '1.000 dB')
        self.assertEqual(fmt.format_gain(12), '12.000 dB')
        self.assertEqual(fmt.format_gain(1.23456), '1.235 dB')
        self.assertEqual(fmt.format_gain(-1), '-1.000 dB')
        self.assertEqual(fmt.format_gain(-1, invert=True), '1.000 dB')

    def test_format_q_factor(self):
        self.assertEqual(fmt.format_q_factor(1), '1')
        self.assertEqual(fmt.format_q_factor(12), '12')
        self.assertEqual(fmt.format_q_factor(123), '123')
        self.assertEqual(fmt.format_q_factor(1234), '1234')
        self.assertEqual(fmt.format_q_factor(12345), '\N{INFINITY}')
        self.assertEqual(fmt.format_q_factor(-1), '\N{INFINITY}')
        self.assertEqual(fmt.format_q_factor(1.2345), '1.234')

    def test_format_vswr(self):
        self.assertEqual(fmt.format_vswr(1), '1.000')
        self.assertEqual(fmt.format_vswr(1.234), '1.234')
        self.assertEqual(fmt.format_vswr(12345.12345), '12345.123')

    def test_format_magnitude(self):
        self.assertEqual(fmt.format_magnitude(1), '1.000')
        self.assertEqual(fmt.format_magnitude(1.234), '1.234')
        self.assertEqual(fmt.format_magnitude(12345.12345), '12345.123')

    def test_format_resistance(self):
        self.assertEqual(fmt.format_resistance(1), '1 \N{OHM SIGN}')
        self.assertEqual(fmt.format_resistance(12), '12 \N{OHM SIGN}')
        self.assertEqual(fmt.format_resistance(123), '123 \N{OHM SIGN}')
        self.assertEqual(fmt.format_resistance(1234), '1.234 k\N{OHM SIGN}')
        self.assertEqual(fmt.format_resistance(12345), '12.345 k\N{OHM SIGN}')
        self.assertEqual(fmt.format_resistance(123456), '123.46 k\N{OHM SIGN}')
        self.assertEqual(fmt.format_resistance(-1), '- \N{OHM SIGN}')

    def test_format_capacitance(self):
        self.assertEqual(fmt.format_capacitance(1), '1 F')
        self.assertEqual(fmt.format_capacitance(1e-3), '1 mF')
        self.assertEqual(fmt.format_capacitance(1e-6), '1 µF')
        self.assertEqual(fmt.format_capacitance(1e-9), '1 nF')
        self.assertEqual(fmt.format_capacitance(1e-12), '1 pF')
        self.assertEqual(fmt.format_capacitance(-1), '-1 F')
        self.assertEqual(fmt.format_capacitance(-1, False), '- pF')

    def test_format_inductance(self):
        self.assertEqual(fmt.format_inductance(1), '1 H')
        self.assertEqual(fmt.format_inductance(1e-3), '1 mH')
        self.assertEqual(fmt.format_inductance(1e-6), '1 µH')
        self.assertEqual(fmt.format_inductance(1e-9), '1 nH')
        self.assertEqual(fmt.format_inductance(1e-12), '1 pH')
        self.assertEqual(fmt.format_inductance(-1), '-1 H')
        self.assertEqual(fmt.format_inductance(-1, False), '- nH')

    def test_format_group_delay(self):
        self.assertEqual(fmt.format_group_delay(1), '1.0000 s')
        self.assertEqual(fmt.format_group_delay(1e-9), '1.0000 ns')
        self.assertEqual(fmt.format_group_delay(1.23456e-9), '1.2346 ns')

    def test_format_phase(self):
        self.assertEqual(fmt.format_phase(0), '0.00°')
        self.assertEqual(fmt.format_phase(1), '57.30°')
        self.assertEqual(fmt.format_phase(-1), '-57.30°')
        self.assertEqual(fmt.format_phase(3.1416), '180.00°')
        self.assertEqual(fmt.format_phase(6.2831), '360.00°')
        self.assertEqual(fmt.format_phase(9.4247), '540.00°')
        self.assertEqual(fmt.format_phase(-3.1416), '-180.00°')

    def test_format_complex_imp(self):
        self.assertEqual(fmt.format_complex_imp(complex(1, 0)), '1+j0 \N{OHM SIGN}')
        self.assertEqual(fmt.format_complex_imp(complex(1234, 1234)), '1.23k+j1.23k \N{OHM SIGN}')
        self.assertEqual(fmt.format_complex_imp(complex(1234, -1234)), '1.23k-j1.23k \N{OHM SIGN}')
        self.assertEqual(fmt.format_complex_imp(complex(1.234, 1234)), '1.23+j1.23k \N{OHM SIGN}')
        self.assertEqual(fmt.format_complex_imp(complex(-1, 1.23e-3)), '- +j1.23m \N{OHM SIGN}')
        self.assertEqual(fmt.format_complex_imp(complex(-1, 1.23e-3), True), '-1+j1.23m \N{OHM SIGN}')

    def test_format_wavelength(self):
        self.assertEqual(fmt.format_wavelength(12.3456), '12.35 m')
