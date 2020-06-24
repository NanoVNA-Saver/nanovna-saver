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
import logging
import math
import os
import re
from typing import List

import numpy as np

from .RFTools import Datapoint

RXP_CAL_LINE = re.compile(r"""^\s*
    (?P<freq>\d+) \s+
    (?P<shortr>[-0-9Ee.]+) \s+ (?P<shorti>[-0-9Ee.]+) \s+
    (?P<openr>[-0-9Ee.]+) \s+ (?P<openi>[-0-9Ee.]+) \s+
    (?P<loadr>[-0-9Ee.]+) \s+ (?P<loadi>[-0-9Ee.]+)(?: \s
    (?P<throughr>[-0-9Ee.]+) \s+ (?P<throughi>[-0-9Ee.]+) \s+
    (?P<isolationr>[-0-9Ee.]+) \s+ (?P<isolationi>[-0-9Ee.]+)
    )?
""", re.VERBOSE)

logger = logging.getLogger(__name__)


# TODO: make a real class of calibration
class Calibration:
    _CAL_NAMES = ("short", "open", "load", "through", "isolation",)

    def __init__(self):

        self.notes = []
        self.cals = {}
        self._reset_cals()
        self.frequencies = []
        # 1-port
        self.e00 = []     # Directivity
        self.e11 = []     # Port match
        self.deltaE = []  # Tracking

        # 2-port
        self.e30 = []     # Port match
        self.e10e32 = []  # Transmission

        self.shortIdeal = np.complex(-1, 0)
        self.useIdealShort = True
        self.shortL0 = 5.7 * 10E-12
        self.shortL1 = -8960 * 10E-24
        self.shortL2 = -1100 * 10E-33
        self.shortL3 = -41200 * 10E-42
        self.shortLength = -34.2  # Picoseconds
        # These numbers look very large, considering what Keysight suggests their numbers are.

        self.useIdealOpen = True
        self.openIdeal = np.complex(1, 0)
        self.openC0 = 2.1 * 10E-14  # Subtract 50fF for the nanoVNA calibration if nanoVNA is calibrated?
        self.openC1 = 5.67 * 10E-23
        self.openC2 = -2.39 * 10E-31
        self.openC3 = 2.0 * 10E-40
        self.openLength = 0

        self.useIdealLoad = True
        self.loadR = 25
        self.loadL = 0
        self.loadC = 0
        self.loadLength = 0
        self.loadIdeal = np.complex(0, 0)

        self.useIdealThrough = True
        self.throughLength = 0

        self.isCalculated = False

        self.source = "Manual"

    def _reset_cals(self):
        for name in Calibration._CAL_NAMES:
            self.cals[name] = []

    @property
    def s11short(self) -> List[Datapoint]:
        return self.cals["short"]
    @s11short.setter
    def s11short(self, values: List[Datapoint]):
        self.cals["short"] = values
    @property
    def s11open(self) -> List[Datapoint]:
        return self.cals["open"]
    @s11open.setter
    def s11open(self, values: List[Datapoint]):
        self.cals["open"] = values
    @property
    def s11load(self) -> List[Datapoint]:
        return self.cals["load"]
    @s11load.setter
    def s11load(self, values: List[Datapoint]):
        self.cals["load"] = values
    @property
    def s21through(self) -> List[Datapoint]:
        return self.cals["through"]
    @s21through.setter
    def s21through(self, values: List[Datapoint]):
        self.cals["through"] = values
    @property
    def s21isolation(self) -> List[Datapoint]:
        return self.cals["isolation"]
    @s21isolation.setter
    def s21isolation(self, values: List[Datapoint]):
        self.cals["isolation"] = values

    def isValid1Port(self):
        lengths = [len(self.cals[x])
                   for x in Calibration._CAL_NAMES[:3]]
        return min(lengths) > 0 and min(lengths) == max(lengths)

    def isValid2Port(self):
        lengths = [len(self.cals[x]) for x in Calibration._CAL_NAMES]
        return min(lengths) > 0 and min(lengths) == max(lengths)

    def calc_corrections(self):
        if not self.isValid1Port():
            logger.warning(
                "Tried to calibrate from insufficient data.")
            raise ValueError(
                "All of short, open and load calibration steps"
                "must be completed for calibration to be applied.")
        nr_points = len(self.cals["short"])
        logger.debug("Calculating calibration for %d points.", nr_points)
        self.frequencies = []
        self.e00 = [np.complex] * nr_points
        self.e11 = [np.complex] * nr_points
        self.deltaE = [np.complex] * nr_points
        self.e30 = [np.complex] * nr_points
        self.e10e32 = [np.complex] * nr_points
        if self.useIdealShort:
            logger.debug("Using ideal values.")
        else:
            logger.debug("Using calibration set values.")
        if self.isValid2Port():
            logger.debug("Calculating 2-port calibration.")
        else:
            logger.debug("Calculating 1-port calibration.")
        for i, cur_short in enumerate(self.cals["short"]):
            cur_open = self.cals["open"][i]
            cur_load = self.cals["load"][i]
            f = cur_short.freq
            self.frequencies.append(f)
            pi = math.pi

            if self.useIdealShort:
                g1 = self.shortIdeal
            else:
                Zsp = np.complex(0, 1) * 2 * pi * f * (self.shortL0 +
                                                       self.shortL1 * f +
                                                       self.shortL2 * f**2 +
                                                       self.shortL3 * f**3)
                gammaShort = ((Zsp/50) - 1) / ((Zsp/50) + 1)
                # (lower case) gamma = 2*pi*f
                # e^j*2*gamma*length
                # Referencing https://arxiv.org/pdf/1606.02446.pdf (18) - (21)
                g1 = gammaShort * np.exp(
                    np.complex(0, 1) * 2 * 2 * math.pi * f * self.shortLength * -1)

            if self.useIdealOpen:
                g2 = self.openIdeal
            else:
                divisor = (
                    2 * pi * f * (
                        self.openC0 + self.openC1 * f +
                        self.openC2 * f**2 + self.openC3 * f**3)
                    )
                if divisor != 0:
                    Zop = np.complex(0, -1) / divisor
                    gammaOpen = ((Zop/50) - 1) / ((Zop/50) + 1)
                    g2 = gammaOpen * np.exp(
                        np.complex(0, 1) * 2 * 2 * math.pi * f * self.openLength * -1)
                else:
                    g2 = self.openIdeal
            if self.useIdealLoad:
                g3 = self.loadIdeal
            else:
                Zl = self.loadR + (np.complex(0, 1) * 2 * math.pi * f * self.loadL)
                g3 = ((Zl/50)-1) / ((Zl/50)+1)
                g3 = g3 * np.exp(
                    np.complex(0, 1) * 2 * 2 * math.pi * f * self.loadLength * -1)

            gm1 = np.complex(cur_short.re, cur_short.im)
            gm2 = np.complex(cur_open.re, cur_open.im)
            gm3 = np.complex(cur_load.re, cur_load.im)

            try:
                denominator = (
                    g1 * (g2 - g3) * gm1 +
                    g2 * g3 * gm2 -
                    g2 * g3 * gm3 -
                    (g2 * gm2 - g3 * gm3) * g1)
                self.e00[i] = - (
                    (g2 * gm3 - g3 * gm3) * g1 * gm2 -
                    (g2 * g3 * gm2 - g2 * g3 * gm3 -
                     (g3 * gm2 - g2 * gm3) * g1) * gm1
                    ) / denominator
                self.e11[i] = (
                    (g2 - g3) * gm1 - g1 * (gm2 - gm3) +
                    g3 * gm2 - g2 * gm3
                    ) / denominator
                self.deltaE[i] = - (
                    (g1 * (gm2 - gm3) - g2 * gm2 + g3 * gm3) * gm1 +
                    (g2 * gm3 - g3 * gm3) * gm2
                    ) / denominator
            except ZeroDivisionError:
                self.isCalculated = False
                logger.error(
                    "Division error - did you use the same measurement"
                    " for two of short, open and load?")
                logger.debug(
                    "Division error at index %d"
                    " Short == Load: %s Short == Open: %s"
                    " Open == Load: %s", i,
                    cur_short == cur_load, cur_short == cur_open,
                    cur_open == cur_load)
                raise ValueError(
                    f"Two of short, open and load returned the same"
                    f" values at frequency {f}Hz.")

            if self.isValid2Port():
                cur_through = self.cals["through"][i]
                cur_isolation = self.cals["isolation"][i]

                self.e30[i] = np.complex(
                    cur_isolation.re, cur_isolation.im)
                s21m = np.complex(cur_through.re, cur_through.im)
                if not self.useIdealThrough:
                    gammaThrough = np.exp(
                        np.complex(0, 1) * 2 * math.pi *
                        self.throughLength * f * -1)
                    s21m = s21m / gammaThrough
                self.e10e32[i] = (s21m - self.e30[i]) * (
                    1 - (self.e11[i] * self.e11[i]))

        self.isCalculated = True
        logger.debug("Calibration correctly calculated.")

    def correct11(self, re, im, freq):
        s11m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i, cur_short in enumerate(self.cals["short"]):
            if abs(cur_short.freq - freq) < distance:
                index = i
                distance = abs(cur_short.freq - freq)
        # TODO: Interpolate with the adjacent data point 
        #       to get better corrections?

        s11 = (s11m - self.e00[index]) / (
            (s11m * self.e11[index]) - self.deltaE[index])
        return s11.real, s11.imag

    def correct21(self, re, im, freq):
        s21m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i, cur_through in enumerate(self.cals["through"]):
            if abs(cur_through.freq - freq) < distance:
                index = i
                distance = abs(cur_through.freq - freq)
        s21 = (s21m - self.e30[index]) / self.e10e32[index]
        return s21.real, s21.imag

    @staticmethod
    def correctDelay11(d: Datapoint, delay):
        input_val = np.complex(d.re, d.im)
        output = input_val * np.exp(np.complex(0, 1) * 2 * 2 * math.pi * d.freq * delay * -1)
        return Datapoint(d.freq, output.real, output.imag)

    @staticmethod
    def correctDelay21(d: Datapoint, delay):
        input_val = np.complex(d.re, d.im)
        output = input_val * np.exp(np.complex(0, 1) * 2 * math.pi * d.freq * delay * -1)
        return Datapoint(d.freq, output.real, output.imag)

    # TODO: implement tests
    def save(self, filename: str):
        # Save the calibration data to file
        if not self.isValid1Port():
            raise ValueError("Not a valid 1-Port calibration")
        with open(filename, "w+") as calfile:
            calfile.write("# Calibration data for NanoVNA-Saver\n")
            for note in self.notes:
                calfile.write(f"! {note}\n")
            calfile.write(
                "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                " ThroughR ThroughI IsolationR IsolationI\n")
            for i, cur_short in enumerate(self.cals["short"]):
                data = [
                    cur_short.freq,
                    cur_short.re, cur_short.im,
                    self.s11open[i].re, self.s11open[i].im,
                    self.s11load[i].re, self.s11load[i].im,
                ]
                if self.isValid2Port():
                    data.extend([
                        self.s21through[i].re, self.s21through[i].im,
                        self.s21isolation[i].re, self.s21isolation[i].im
                    ])
                calfile.write(" ".join([str(val) for val in data]))
                calfile.write("\n")

    # TODO: implement tests
    # TODO: Exception should be catched by caller
    def load(self, filename):
        self.source = os.path.basename(filename)
        self._reset_cals()
        self.notes = []

        parsed_header = False
        with open(filename) as calfile:
            for i, line in enumerate(calfile):
                line = line.strip()
                if line.startswith("!"):
                    note = line[2:]
                    self.notes.append(note)
                    continue
                if line.startswith("#"):
                    if not parsed_header:
                        # Check that this is a valid header
                        if line == (
                                "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                                " ThroughR ThroughI IsolationR IsolationI"):
                            parsed_header = True
                    continue
                if not parsed_header:
                    logger.warning(
                        "Warning: Read line without having read header: %s",
                        line)
                    continue

                m = RXP_CAL_LINE.search(line)
                if not m:
                    logger.warning("Illegal data in cal file. Line %i", i)
                cal = m.groupdict()

                if cal["throughr"]:
                    nr_cals = 5
                else:
                    nr_cals = 3
                
                for name in Calibration._CAL_NAMES[:nr_cals]:
                    self.cals[name].append(
                        Datapoint(int(cal["freq"]),
                                  float(cal[f"{name}r"]),
                                  float(cal[f"{name}i"])))
