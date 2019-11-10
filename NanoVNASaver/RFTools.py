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
    def gain(data: Datapoint):
        # re50, im50 = normalize50(data)
        # Calculate the gain / reflection coefficient
        # mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / \
        #       math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
        #
        #  Magnitude = |Gamma|:
        mag = math.sqrt(data.re**2 + data.im**2)
        if mag > 0:
            return 20 * math.log10(mag)
        else:
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
        capacitance = 10**12/(freq * 2 * math.pi * im50)
        return str(Value(-capacitance, "F", Format(max_nr_digits=5)))
        
    @staticmethod
    def inductanceEquivalent(im50, freq) -> str:
        if freq == 0:
            return "- nH"
        inductance = im50 * 1000000000 / (freq * 2 * math.pi)
        return str(Value(inductance, "H", Format(max_nr_digits=5)))

    @staticmethod
    def formatFrequency(freq):
        return str(Value(freq, "Hz", Format(max_nr_digits=6)))

    @staticmethod
    def formatShortFrequency(freq):
        return str(Value(freq, "Hz", Format(max_nr_digits=4)))

    @staticmethod
    def formatSweepFrequency(freq: int,
                             mindigits: int = 2,
                             appendHz: bool = True,
                             insertSpace: bool = False,
                             countDot: bool = True,
                             assumeInfinity: bool = True) -> str:
        """ Format frequency with SI prefixes

            mindigits count refers to the number of decimal place digits
            that will be shown, padded with zeroes if needed.
        """
        freqstr = str(freq)
        freqlen = len(freqstr)

        # sanity checks
        if freqlen > 15:
            if assumeInfinity:
                return "\N{INFINITY}"
            raise ValueError("Frequency too big. More than 15 digits!")

        if freq < 1:
            return " - " + (" " if insertSpace else "") + ("Hz" if appendHz else "")

        si_index = (freqlen - 1) // 3
        dot_pos = freqlen % 3 or 3
        intfstr = freqstr[:dot_pos]
        decfstr = freqstr[dot_pos:]
        nzdecfstr = decfstr.rstrip('0')
        if si_index != 0:
            while len(nzdecfstr) < mindigits:
                nzdecfstr += '0'
        freqstr = intfstr + ("." if len(nzdecfstr) > 0 else "") + nzdecfstr
        return freqstr + (" " if insertSpace else "") + PREFIXES[si_index] + ("Hz" if appendHz else "")

    @staticmethod
    def parseFrequency(freq: str) -> int:
        parser = Value(0, "Hz")
        try:
            return round(parser.parse(freq))
        except (ValueError, IndexError):
            return -1

    @staticmethod
    def phaseAngle(data: Datapoint):
        re = data.re
        im = data.im
        return math.degrees(math.atan2(im, re))
