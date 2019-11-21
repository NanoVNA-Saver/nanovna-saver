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
from numbers import Number, Real
from typing import List, NamedTuple

from NanoVNASaver.SITools import Value, Format


def clamp_value(value: Real, rmin: Real, rmax: Real) -> Real:
    assert rmin <= rmax
    if value < rmin:
        return rmin
    if value > rmax:
        return rmax
    return value


class Datapoint(NamedTuple):
    freq: int
    re: float
    im: float

    @property
    def z(self):
        """ return the datapoint impedance as complex number """
        return complex(self.re, self.im)

    @property
    def phase(self):
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
        if mag > 1:
            return math.inf
        return (1 + mag) / (1 - mag)

    def impedance(self, ref_impedance: float = 50) -> complex:
        return ref_impedance * ((-self.z - 1) / (self.z - 1))

    def qFactor(self, ref_impedance: float = 50) -> float:
        imp = self.impedance(ref_impedance)
        if imp.real == 0.0:
            return -1
        return abs(imp.imag / imp.real)

    def capacitiveEquivalent(self, ref_impedance: float = 50) -> float:
        if self.freq == 0:
            return math.inf
        imp = self.impedance(ref_impedance)
        if imp.imag == 0:
            return math.inf
        return -(1 / (self.freq * 2 * math.pi * imp.imag))

    def inductiveEquivalent(self, ref_impedance: float = 50) -> float:
        if self.freq == 0:
            return math.inf
        imp = self.impedance(ref_impedance)
        if imp.imag == 0:
            return 0
        return imp.imag * 1 / (self.freq * 2 * math.pi)


class RFTools:
    @staticmethod
    def capacitanceEquivalent(im50, freq) -> str:
        if im50 == 0 or freq == 0:
            return "- pF"
        capacitance = 1 / (freq * 2 * math.pi * im50)
        return str(Value(-capacitance, "F", Format(max_nr_digits=5, space_str=" ")))

    @staticmethod
    def inductanceEquivalent(im50, freq) -> str:
        if freq == 0:
            return "- nH"
        inductance = im50 * 1 / (freq * 2 * math.pi)
        return str(Value(inductance, "H", Format(max_nr_digits=5, space_str=" ")))

    @staticmethod
    def formatFrequency(freq: Number) -> str:
        return str(Value(freq, "Hz"))

    @staticmethod
    def formatShortFrequency(freq: Number) -> str:
        return str(Value(freq, "Hz", Format(max_nr_digits=4)))

    @staticmethod
    def formatSweepFrequency(freq: Number) -> str:
        return str(Value(freq, "Hz", Format(max_nr_digits=10, allow_strip=True)))

    @staticmethod
    def parseFrequency(freq: str) -> int:
        parser = Value(0, "Hz", Format(parse_sloppy_unit=True, parse_sloppy_kilo=True, parse_allow_neg=False))
        try:
            return round(parser.parse(freq))
        except (ValueError, IndexError):
            return -1

    @staticmethod
    def groupDelay(data: List[Datapoint], index: int) -> float:
        idx0 = clamp_value(index - 1, 0, len(data) - 1)
        idx1 = clamp_value(index + 1, 0, len(data) - 1)
        delta_angle = (data[idx1].phase - data[idx0].phase)
        if abs(delta_angle) > math.tau:
            if delta_angle > 0:
                delta_angle = delta_angle % math.tau
            else:
                delta_angle = -1 * (delta_angle % math.tau)
        val = -delta_angle / math.tau / (data[idx1].freq - data[idx0].freq)
        return val
