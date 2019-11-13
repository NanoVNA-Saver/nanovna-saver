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


def gamma_to_impedance(gamma: complex, impedance: float) -> complex:
    return impedance * ((-gamma - 1) / (gamma - 1))


class Datapoint(NamedTuple):
    freq: int
    re: float
    im: float

    @property
    def z(self):
        """ return datapoint impedance as complex number """
        return complex(self.re, self.im)

class RFTools:
    @staticmethod
    def normalize50(data: Datapoint):
        result = gamma_to_impedance(data.z, 50)
        return result.real, result.imag

    @staticmethod
    def gain(data: Datapoint) -> float:
        mag = abs(data.z)
        if mag > 0:
            return 20 * math.log10(mag)
        return 0

    @staticmethod
    def qualityFactor(data: Datapoint):
        imp = gamma_to_impedance(data.z, 50)
        if imp.real != 0.0:
            return abs(imp.imag / imp.real)
        return -1

    @staticmethod
    def calculateVSWR(data: Datapoint):
        try:
            mag = abs(data.z)
            vswr = (1 + mag) / (1 - mag)
        except ZeroDivisionError:
            vswr = 1
        return vswr

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
    def phaseAngle(data: Datapoint) -> float:
        return math.degrees(cmath.phase(data.z))

    @staticmethod
    def phaseAngleRadians(data: Datapoint) -> float:
        return cmath.phase(data.z)

    @staticmethod
    def groupDelay(data: List[Datapoint], index: int) -> float:
        index0 = clamp_int(index - 1, 0, len(data) - 1)
        index1 = clamp_int(index + 1, 0, len(data) - 1)
        angle0 = cmath.phase(data[index0].z)
        angle1 = cmath.phase(data[index1].z)
        freq0 = data[index0].freq
        freq1 = data[index1].freq
        delta_angle = (angle1 - angle0)
        if abs(delta_angle) > math.tau:
            if delta_angle > 0:
                delta_angle = delta_angle % math.tau
            else:
                delta_angle = -1 * (delta_angle % math.tau)
        val = -delta_angle / math.tau / (freq1 - freq0)
        return val
