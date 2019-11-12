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
import collections
import math
from numbers import Number
from typing import List

from NanoVNASaver.SITools import Value, Format

PREFIXES = ("", "k", "M", "G", "T")
Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class RFTools:
    @staticmethod
    def normalize50(data: Datapoint):
        re = data.re
        im = data.im
        re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
        im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
        return re50, im50

    @staticmethod
    def gain(data: Datapoint) -> float:
        # re50, im50 = normalize50(data)
        # Calculate the gain / reflection coefficient
        # mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / \
        #       math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
        #
        #  Magnitude = |Gamma|:
        mag = math.sqrt(data.re**2 + data.im**2)
        if mag > 0:
            return 20 * math.log10(mag)
        return 0

    @staticmethod
    def qualityFactor(data: Datapoint):
        re50, im50 = RFTools.normalize50(data)
        if re50 != 0:
            Q = abs(im50 / re50)
        else:
            Q = -1
        return Q

    @staticmethod
    def calculateVSWR(data: Datapoint):
        # re50, im50 = normalize50(data)
        try:
            # mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / \
            # math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
            mag = math.sqrt(data.re**2 + data.im**2)
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
        re = data.re
        im = data.im
        return math.degrees(math.atan2(im, re))

    @staticmethod
    def phaseAngleRadians(data: Datapoint) -> float:
        re = data.re
        im = data.im
        return math.atan2(im, re)

    @staticmethod
    def groupDelay(data: List[Datapoint], index: int) -> float:
        if index <= 0:  # fix list boundaries
            index = 1
        elif index >= len(data) - 1:
            index = len(data -2)

        angle0 = RFTools.phaseAngleRadians(data[index-1])
        angle1 = RFTools.phaseAngleRadians(data[index+1])
        freq0 = data[index-1].freq
        freq1 = data[index+1].freq
        delta_angle = (angle1 - angle0)
        if abs(delta_angle) > math.tau:
            if delta_angle > 0:
                delta_angle = delta_angle % math.tau
            else:
                delta_angle = -1 * (delta_angle % math.tau)
        val = -delta_angle / math.tau / (freq1 - freq0)
        return val
