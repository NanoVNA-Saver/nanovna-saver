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

from NanoVNASaver.SITools import Value, Format


def clamp_int(value: int, imin: int, imax: int) -> int:
    assert imin <= imax
    if value < imin:
        return imin
    if value > imax:
        return imax
    return value


class Datapoint(NamedTuple):
    freq: int
    re: float
    im: float

    @property
    def z(self):
        """ return datapoint impedance as complex number """
        return complex(self.re, self.im)

    @property
    def phase(self):
        """ return datapoints phase value """
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
        elif mag > 1:
            return math.inf
        return (1 + mag) / (1 - mag)

    def to_impedance(self, ref_impedance: float = 50) -> complex:
        return ref_impedance * ((-self.z - 1) / (self.z - 1))

    def to_q_factor(self, ref_impedance: float = 50) -> float:
        imp = self.to_impedance(ref_impedance)
        if imp.real == 0.0:
            return -1
        return abs(imp.imag / imp.real)

    def to_capacitive_equivalent(self, ref_impedance: float = 50) -> float:
        if self.freq == 0:
            return math.inf
        imp = self.to_impedance(ref_impedance)
        if imp.imag == 0:
            return math.inf
        return -(1 / (self.freq * 2 * math.pi * imp.imag))

    def to_inductive_equivalent(self, ref_impedance: float = 50) -> float:
        if self.freq == 0:
            return math.inf
        imp = self.to_impedance(ref_impedance)
        if imp.imag == 0:
            return 0
        return imp.imag * 1 / (self.freq * 2 * math.pi)


class RFTools:
    @staticmethod
    def normalize50(data: Datapoint):
        result = data.to_impedance()
        return result.real, result.imag

    @staticmethod
    def gain(data: Datapoint) -> float:
        return data.gain

    @staticmethod
    def qualityFactor(data: Datapoint) -> float:
        return data.to_q_factor()

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
        return str(Value(freq, "Hz", Format(max_nr_digits=5)))

    @staticmethod
    def parseFrequency(freq: str) -> int:
        parser = Value(0, "Hz", Format(parse_sloppy_unit=True, parse_sloppy_kilo=True))
        try:
            return round(parser.parse(freq))
        except (ValueError, IndexError):
            return -1

    @staticmethod
    def groupDelay(data: List[Datapoint], index: int) -> float:
        idx0 = clamp_int(index - 1, 0, len(data) - 1)
        idx1 = clamp_int(index + 1, 0, len(data) - 1)
        delta_angle = (data[idx1].phase - data[idx0].phase)
        if abs(delta_angle) > math.tau:
            if delta_angle > 0:
                delta_angle = delta_angle % math.tau
            else:
                delta_angle = -1 * (delta_angle % math.tau)
        val = -delta_angle / math.tau / (data[idx1].freq - data[idx0].freq)
        return val
