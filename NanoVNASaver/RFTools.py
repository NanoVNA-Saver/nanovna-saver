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
import math
import cmath
from numbers import Number
from typing import List, NamedTuple
from NanoVNASaver.SITools import Value, Format, clamp_value

FMT_FREQ = Format()
FMT_SHORT = Format(max_nr_digits=4)
FMT_SWEEP = Format(max_nr_digits=9, allow_strip=True)
FMT_PARSE = Format(parse_sloppy_unit=True, parse_sloppy_kilo=True,
                   parse_clamp_min=0)


def parallel_to_serial(z: complex) -> complex:
    """Convert parallel impedance to serial impedance equivalent"""
    z_sq_sum = z.real ** 2 + z.imag ** 2
    # TODO: Fix divide by zero
    return complex(z.real * z.imag ** 2 / z_sq_sum,
                   z.real ** 2 * z.imag / z_sq_sum)


def serial_to_parallel(z: complex) -> complex:
    """Convert serial impedance to parallel impedance equivalent"""
    z_sq_sum = z.real ** 2 + z.imag ** 2
    if z.real != 0 and z.imag != 0:
        return complex(z_sq_sum / z.real, z_sq_sum / z.imag)
    elif z.real != 0 and z_sq_sum > 0:
        return complex(z_sq_sum / z.real, math.inf)
    elif z.real != 0 and z_sq_sum < 0:
        return complex(z_sq_sum / z.real, -math.inf)
    elif z.imag != 0 and z_sq_sum > 0:
        return complex(math.inf, z_sq_sum / z.real)
    elif z.imag != 0 and z_sq_sum < 0:
        return complex(-math.inf, z_sq_sum / z.real)
    elif z_sq_sum == 0:
        return complex(0, 0)
    else:
        return complex(math.inf, math.inf)


def impedance_to_capacitance(z: complex, freq: float) -> float:
    """Calculate capacitive equivalent for reactance"""
    if freq == 0:
        return -math.inf
    if z.imag == 0:
        return math.inf
    return -(1 / (freq * 2 * math.pi * z.imag))


def impedance_to_inductance(z: complex, freq: float) -> float:
    """Calculate inductive equivalent for reactance"""
    if freq == 0:
        return 0
    return z.imag * 1 / (freq * 2 * math.pi)


def impedance_to_norm(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate normalized z from impedance"""
    return z / ref_impedance


def norm_to_impedance(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate impedance from normalized z"""
    return z * ref_impedance


def reflection_coefficient(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate reflection coefficient for z"""
    return (z - ref_impedance) / (z + ref_impedance)


def gamma_to_impedance(gamma: complex, ref_impedance: float = 50) -> complex:
    """Calculate impedance from gamma"""
    return ((-gamma - 1) / (gamma - 1)) * ref_impedance


def parseFrequency(freq: str) -> int:
    try:
        return int(Value(freq, "Hz", FMT_PARSE))
    except (ValueError, IndexError):
        return -1


class Datapoint(NamedTuple):
    freq: int
    re: float
    im: float

    @property
    def z(self) -> complex:
        """ return the datapoint impedance as complex number """
        return complex(self.re, self.im)

    @property
    def phase(self) -> float:
        """ return the datapoint's phase value """
        return cmath.phase(self.z)

    @property
    def gain(self) -> float:
        mag = abs(self.z)
        if mag > 0:
            return 20 * math.log10(mag)
        return 0

    @property
    def vswr(self) -> float:
        mag = abs(self.z)
        if mag == 1:
            return 1
        return (1 + mag) / (1 - mag)

    def impedance(self, ref_impedance: float = 50) -> complex:
        return gamma_to_impedance(self.z, ref_impedance)

    def qFactor(self, ref_impedance: float = 50) -> float:
        imp = self.impedance(ref_impedance)
        if imp.real == 0.0:
            return -1
        return abs(imp.imag / imp.real)

    def capacitiveEquivalent(self, ref_impedance: float = 50) -> float:
        return impedance_to_capacitance(self.impedance(ref_impedance), self.freq)

    def inductiveEquivalent(self, ref_impedance: float = 50) -> float:
        return impedance_to_inductance(self.impedance(ref_impedance), self.freq)


def groupDelay(data: List[Datapoint], index: int) -> float:
    idx0 = clamp_value(index - 1, 0, len(data) - 1)
    idx1 = clamp_value(index + 1, 0, len(data) - 1)
    delta_angle = data[idx1].phase - data[idx0].phase
    delta_freq = data[idx1].freq - data[idx0].freq
    if delta_freq == 0:
        return 0
    if abs(delta_angle) > math.tau:
        if delta_angle > 0:
            delta_angle = delta_angle % math.tau
        else:
            delta_angle = -1 * (delta_angle % math.tau)
    val = -delta_angle / math.tau / delta_freq
    return val


class RFTools:
    # TODO: Remove this class when unused
    @staticmethod
    def formatFrequency(freq: Number) -> str:
        return str(Value(freq, "Hz", FMT_FREQ))

    @staticmethod
    def formatShortFrequency(freq: Number) -> str:
        return str(Value(freq, "Hz", FMT_SHORT))

    @staticmethod
    def formatSweepFrequency(freq: Number) -> str:
        return str(Value(freq, "Hz", FMT_SWEEP))

    @staticmethod
    def parseFrequency(freq: str) -> int:
        return parseFrequency(freq)