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

import logging
import math
import os
from typing import List

import numpy as np

from .RFTools import Datapoint

logger = logging.getLogger(__name__)


class Calibration:
    notes = []
    s11short: List[Datapoint] = []
    s11open: List[Datapoint] = []
    s11load: List[Datapoint] = []
    s21through: List[Datapoint] = []
    s21isolation: List[Datapoint] = []

    frequencies = []

    # 1-port
    e00 = []     # Directivity
    e11 = []     # Port match
    deltaE = []  # Tracking

    # 2-port
    e30 = []     # Port match
    e10e32 = []  # Transmission

    shortIdeal = np.complex(-1, 0)
    useIdealShort = True
    shortL0 = 5.7 * 10E-12
    shortL1 = -8960 * 10E-24
    shortL2 = -1100 * 10E-33
    shortL3 = -41200 * 10E-42
    shortLength = -34.2  # Picoseconds
    # These numbers look very large, considering what Keysight suggests their numbers are.

    useIdealOpen = True
    openIdeal = np.complex(1, 0)
    openC0 = 2.1 * 10E-14  # Subtract 50fF for the nanoVNA calibration if nanoVNA is calibrated?
    openC1 = 5.67 * 10E-23
    openC2 = -2.39 * 10E-31
    openC3 = 2.0 * 10E-40
    openLength = 0

    useIdealLoad = True
    loadR = 25
    loadL = 0
    loadC = 0
    loadLength = 0
    loadIdeal = np.complex(0, 0)

    useIdealThrough = True
    throughLength = 0

    isCalculated = False

    source = "Manual"

    def isValid2Port(self):
        valid = len(self.s21through) > 0 and len(self.s21isolation) > 0 and self.isValid1Port()
        valid &= len(self.s21through) == len(self.s21isolation) == len(self.s11short)
        return valid

    def isValid1Port(self):
        valid = len(self.s11short) > 0 and len(self.s11open) > 0 and len(self.s11load) > 0
        valid &= len(self.s11short) == len(self.s11open) == len(self.s11load)
        return valid

    def calculateCorrections(self) -> (bool, str):
        if not self.isValid1Port():
            logger.warning("Tried to calibrate from insufficient data.")
            if len(self.s11short) == 0 or len(self.s11open) == 0 or len(self.s11load) == 0:
                return (False,
                        "All of short, open and load calibration steps"
                        "must be completed for calibration to be applied.")
            return False, "All calibration data sets must be the same size."
        self.frequencies = [int] * len(self.s11short)
        self.e00 = [np.complex] * len(self.s11short)
        self.e11 = [np.complex] * len(self.s11short)
        self.deltaE = [np.complex] * len(self.s11short)
        self.e30 = [np.complex] * len(self.s11short)
        self.e10e32 = [np.complex] * len(self.s11short)
        logger.debug("Calculating calibration for %d points.", len(self.s11short))
        if self.useIdealShort:
            logger.debug("Using ideal values.")
        else:
            logger.debug("Using calibration set values.")
        if self.isValid2Port():
            logger.debug("Calculating 2-port calibration.")
        else:
            logger.debug("Calculating 1-port calibration.")
        for i in range(len(self.s11short)):
            self.frequencies[i] = self.s11short[i].freq
            f = self.s11short[i].freq
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

            gm1 = np.complex(self.s11short[i].re, self.s11short[i].im)
            gm2 = np.complex(self.s11open[i].re, self.s11open[i].im)
            gm3 = np.complex(self.s11load[i].re, self.s11load[i].im)

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
                    " Short == Load: %s"
                    " Short == Open: %s"
                    " Open == Load: %s",
                    i,
                    self.s11short[i] == self.s11load[i],
                    self.s11short[i] == self.s11open[i],
                    self.s11open[i] == self.s11load[i])
                return (self.isCalculated,
                        f"Two of short, open and load returned the same"
                        f" values at frequency {self.s11open[i].freq}Hz.")

            if self.isValid2Port():
                self.e30[i] = np.complex(
                    self.s21isolation[i].re, self.s21isolation[i].im)
                s21m = np.complex(self.s21through[i].re, self.s21through[i].im)
                if not self.useIdealThrough:
                    gammaThrough = np.exp(
                        np.complex(0, 1) * 2 * math.pi * self.throughLength * f * -1)
                    s21m = s21m / gammaThrough
                self.e10e32[i] = (s21m - self.e30[i]) * (1 - (self.e11[i]*self.e11[i]))

        self.isCalculated = True
        logger.debug("Calibration correctly calculated.")
        return self.isCalculated, "Calibration successful."

    def correct11(self, re, im, freq):
        s11m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i in range(len(self.s11short)):
            if abs(self.s11short[i].freq - freq) < distance:
                index = i
                distance = abs(self.s11short[i].freq - freq)
        # TODO: Interpolate with the adjacent data point to get better corrections?

        s11 = (s11m - self.e00[index]) / ((s11m * self.e11[index]) - self.deltaE[index])
        return s11.real, s11.imag

    def correct21(self, re, im, freq):
        s21m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i in range(len(self.s21through)):
            if abs(self.s21through[i].freq - freq) < distance:
                index = i
                distance = abs(self.s21through[i].freq - freq)
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

    def saveCalibration(self, filename):
        # Save the calibration data to file
        if filename == "" or not self.isValid1Port():
            return False
        try:
            file = open(filename, "w+")
            file.write("# Calibration data for NanoVNA-Saver\n")
            for note in self.notes:
                file.write(f"! {note}\n")
            file.write(
                "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                " ThroughR ThroughI IsolationR IsolationI\n")
            for i in range(len(self.s11short)):
                freq = str(self.s11short[i].freq)
                shortr = str(self.s11short[i].re)
                shorti = str(self.s11short[i].im)
                openr = str(self.s11open[i].re)
                openi = str(self.s11open[i].im)
                loadr = str(self.s11load[i].re)
                loadi = str(self.s11load[i].im)
                file.write(" ".join((freq, shortr, shorti, openr, openi, loadr, loadi)))
                if self.isValid2Port():
                    throughr = str(self.s21through[i].re)
                    throughi = str(self.s21through[i].im)
                    isolationr = str(self.s21isolation[i].re)
                    isolationi = str(self.s21isolation[i].im)
                    file.write(" ".join((throughr, throughi, isolationr, isolationi)))
                file.write("\n")
            file.close()
            return True
        except Exception as e:
            logger.exception("Error saving calibration data: %s", e)
            return False

    def loadCalibration(self, filename):
        # Load calibration data from file
        if filename == "":
            return

        self.source = os.path.basename(filename)

        self.s11short = []
        self.s11open = []
        self.s11load = []

        self.s21through = []
        self.s21isolation = []
        self.notes = []

        try:
            file = open(filename, "r")
            lines = file.readlines()
            parsed_header = False

            for line in lines:
                line = line.strip()
                if line.startswith("!"):
                    note = line[2:]
                    self.notes.append(note)
                    continue
                if line.startswith("#") and not parsed_header:
                    # Check that this is a valid header
                    if line == ("# Hz ShortR ShortI OpenR OpenI LoadR Load"
                                " ThroughR ThroughI IsolationR IsolationI"):
                        parsed_header = True
                    continue
                if not parsed_header:
                    logger.warning(
                        "Warning: Read line without having read header: %s", line)
                    continue
                try:
                    if line.count(" ") == 6:
                        freq, shortr, shorti, openr, openi, loadr, loadi = line.split(
                            " ")
                        self.s11short.append(
                            Datapoint(int(freq), float(shortr), float(shorti)))
                        self.s11open.append(
                            Datapoint(int(freq), float(openr), float(openi)))
                        self.s11load.append(
                            Datapoint(int(freq), float(loadr), float(loadi)))

                    else:
                        (freq, shortr, shorti, openr, openi, loadr, loadi,
                         throughr, throughi, isolationr, isolationi) = line.split(" ")
                        self.s11short.append(
                            Datapoint(int(freq), float(shortr), float(shorti)))
                        self.s11open.append(
                            Datapoint(int(freq), float(openr), float(openi)))
                        self.s11load.append(
                            Datapoint(int(freq), float(loadr), float(loadi)))
                        self.s21through.append(
                            Datapoint(int(freq), float(throughr), float(throughi)))
                        self.s21isolation.append(
                            Datapoint(int(freq), float(isolationr), float(isolationi)))

                except ValueError as e:
                    logger.exception(
                        "Error parsing calibration data \"%s\": %s", line, e)
            file.close()
        except Exception as e:
            logger.exception("Failed loading calibration data: %s", e)
