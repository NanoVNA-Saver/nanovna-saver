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
        #re50, im50 = normalize50(data)
        # Calculate the gain / reflection coefficient
        #mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
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
        #re50, im50 = normalize50(data)
        try:
            #mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
            mag = math.sqrt(data.re**2 + data.im**2)
            vswr = (1 + mag) / (1 - mag)
        except ZeroDivisionError as e:
            vswr = 1
        return vswr

    @staticmethod
    def capacitanceEquivalent(im50, freq) -> str:
        if im50 == 0 or freq == 0:
            return "- pF"
        capacitance = 10**12/(freq * 2 * math.pi * im50)
        if abs(capacitance) > 10000:
            return str(round(-capacitance/1000, 2)) + " nF"
        elif abs(capacitance) > 1000:
            return str(round(-capacitance/1000, 3)) + " nF"
        elif abs(capacitance) > 10:
            return str(round(-capacitance, 2)) + " pF"
        else:
            return str(round(-capacitance, 3)) + " pF"

    @staticmethod
    def inductanceEquivalent(im50, freq) -> str:
        if freq == 0:
            return "- nH"
        inductance = im50 * 1000000000 / (freq * 2 * math.pi)
        if abs(inductance) > 10000:
            return str(round(inductance / 1000, 2)) + " μH"
        elif abs(inductance) > 1000:
            return str(round(inductance/1000, 3)) + " μH"
        elif abs(inductance) > 10:
            return str(round(inductance, 2)) + " nH"
        else:
            return str(round(inductance, 3)) + " nH"

    @staticmethod
    def formatFrequency(freq):
        if freq < 1:
            return "- Hz"
        if math.log10(freq) < 3:
            return str(round(freq)) + " Hz"
        elif math.log10(freq) < 7:
            return "{:.3f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 8:
            return "{:.4f}".format(freq/1000000) + " MHz"
        else:
            return "{:.3f}".format(freq/1000000) + " MHz"

    @staticmethod
    def formatShortFrequency(freq):
        if freq < 1:
            return "- Hz"
        if math.log10(freq) < 3:
            return str(round(freq)) + " Hz"
        elif math.log10(freq) < 5:
            return "{:.3f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 6:
            return "{:.2f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 7:
            return "{:.1f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 8:
            return "{:.3f}".format(freq/1000000) + " MHz"
        elif math.log10(freq) < 9:
            return "{:.2f}".format(freq/1000000) + " MHz"
        else:
            return "{:.1f}".format(freq/1000000) + " MHz"

    @staticmethod
    def parseFrequency(freq: str):
        freq = freq.replace(" ", "")  # People put all sorts of weird whitespace in.
        if freq.isnumeric():
            return int(freq)

        multiplier = 1
        freq = freq.lower()

        if freq.endswith("k"):
            multiplier = 1000
            freq = freq[:-1]
        elif freq.endswith("m"):
            multiplier = 1000000
            freq = freq[:-1]

        if freq.isnumeric():
            return int(freq) * multiplier

        try:
            f = float(freq)
            return int(round(multiplier * f))
        except ValueError:
            # Okay, we couldn't parse this however much we tried.
            return -1

    @staticmethod
    def phaseAngle(data: Datapoint):
        re = data.re
        im = data.im
        return math.degrees(math.atan2(im, re))
