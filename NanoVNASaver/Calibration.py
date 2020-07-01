#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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
import cmath
import math
import os
import re
from collections import defaultdict, UserDict
from typing import List

from scipy.interpolate import interp1d

from NanoVNASaver.RFTools import Datapoint

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

def correct_delay(d: Datapoint, delay: float, reflect: bool = False):
    mult = 2 if reflect else 1
    corr_data = d.z * cmath.exp(
        complex(0, 1) * 2 * math.pi * d.freq * delay * -1 * mult)
    return Datapoint(d.freq, corr_data.real, corr_data.imag)


class CalData(UserDict):
    def __init__(self):
        data = {
            "short": None,
            "open": None,
            "load": None,
            "through": None,
            "isolation": None,
            # the frequence
            "freq": 0,
            # 1 Port
            "e00": 0.0,  # Directivity
            "e11": 0.0,  # Port match
            "delta_e": 0.0,  # Tracking
            # 2 port
            "e30": 0.0,  # Port match
            "e10e32": 0.0,  # Transmission
        }
        super().__init__(data)

    def __str__(self):
        d = self.data
        s = (f'{d["freq"]}'
             f' {d["short"].re} {d["short"].im}'
             f' {d["open"].re} {d["open"].im}'
             f' {d["load"].re} {d["load"].im}')
        if d["through"] is not None:
            s += (f' {d["through"].re} {d["through"].im}'
                  f' {d["isolation"].re} {d["isolation"].im}')
        return s

class CalDataSet:
    def __init__(self):
        self.data = defaultdict(CalData)

    def insert(self, name: str, dp: Datapoint):
        if not name in self.data[dp.freq]:
            raise KeyError(name)
        self.data[dp.freq]["freq"] = dp.freq
        self.data[dp.freq][name] = dp

    def frequencies(self) -> List[int]:
        return sorted(self.data.keys())

    def get(self, freq: int) -> CalData:
        return self.data[freq]

    def items(self):
        for item in self.data.items():
            yield item

    def values(self):
        for freq in self.frequencies():
            yield self.get(freq)

    def size_of(self, name: str) -> int:
        return len([v for v in self.data.values() if v[name] is not None])

    def complete1port(self) -> bool:
        for val in self.data.values():
            for name in ("short", "open", "load"):
                if val[name] is None:
                    return False
        return any(self.data)

    def complete2port(self) -> bool:
        for val in self.data.values():
            for name in ("short", "open", "load", "through", "isolation"):
                if val[name] is None:
                    return False
        return any(self.data)


class Calibration:
    CAL_NAMES = ("short", "open", "load", "through", "isolation",)
    IDEAL_SHORT = complex(-1, 0)
    IDEAL_OPEN = complex(1, 0)
    IDEAL_LOAD = complex(0, 0)

    def __init__(self):

        self.notes = []
        self.dataset = CalDataSet()
        self.interp = {}

        self.useIdealShort = True
        self.shortL0 = 5.7 * 10E-12
        self.shortL1 = -8960 * 10E-24
        self.shortL2 = -1100 * 10E-33
        self.shortL3 = -41200 * 10E-42
        self.shortLength = -34.2  # Picoseconfrequenciesds
        # These numbers look very large, considering what Keysight
        # suggests their numbers are.

        self.useIdealOpen = True
        # Subtract 50fF for the nanoVNA calibration if nanoVNA is
        # calibrated?
        self.openC0 = 2.1 * 10E-14
        self.openC1 = 5.67 * 10E-23
        self.openC2 = -2.39 * 10E-31
        self.openC3 = 2.0 * 10E-40
        self.openLength = 0

        self.useIdealLoad = True
        self.loadR = 25
        self.loadL = 0
        self.loadC = 0
        self.loadLength = 0

        self.useIdealThrough = True
        self.throughLength = 0

        self.isCalculated = False

        self.source = "Manual"

    def insert(self, name: str, data: List[Datapoint]):
        for dp in data:
            self.dataset.insert(name, dp)

    def size(self) -> int:
        return len(self.dataset.frequencies())

    def data_size(self, name) -> int:
        return self.dataset.size_of(name)

    def isValid1Port(self) -> bool:
        return self.dataset.complete1port()

    def isValid2Port(self) -> bool:
        return self.dataset.complete2port()

    def calc_corrections(self):
        if not self.isValid1Port():
            logger.warning(
                "Tried to calibrate from insufficient data.")
            raise ValueError(
                "All of short, open and load calibration steps"
                "must be completed for calibration to be applied.")
        logger.debug("Calculating calibration for %d points.", self.size())

        for freq, caldata in self.dataset.items():
            g1 = self.gamma_short(freq)
            g2 = self.gamma_open(freq)
            g3 = self.gamma_load(freq)

            gm1 = caldata["short"].z
            gm2 = caldata["open"].z
            gm3 = caldata["load"].z

            try:
                denominator = (g1 * (g2 - g3) * gm1 +
                               g2 * g3 * gm2 - g2 * g3 * gm3 -
                               (g2 * gm2 - g3 * gm3) * g1)
                caldata["e00"] = - ((g2 * gm3 - g3 * gm3) * g1 * gm2 -
                                    (g2 * g3 * gm2 - g2 * g3 * gm3 -
                                     (g3 * gm2 - g2 * gm3) * g1) * gm1
                                    ) / denominator
                caldata["e11"] = ((g2 - g3) * gm1 - g1 * (gm2 - gm3) +
                                  g3 * gm2 - g2 * gm3) / denominator
                caldata["delta_e"] = - ((g1 * (gm2 - gm3) - g2 * gm2 + g3 *
                                         gm3) * gm1 + (g2 * gm3 - g3 * gm3) *
                                        gm2) / denominator
            except ZeroDivisionError:
                self.isCalculated = False
                logger.error(
                    "Division error - did you use the same measurement"
                    " for two of short, open and load?")
                raise ValueError(
                    f"Two of short, open and load returned the same"
                    f" values at frequency {freq}Hz.")

            if self.isValid2Port():
                caldata["e30"] = caldata["isolation"].z

                gt = self.gamma_through(freq)
                caldata["e10e32"] = (caldata["through"].z / gt - caldata["e30"]
                                     ) * (1 - caldata["e11"]**2)

        self.gen_interpolation()
        self.isCalculated = True
        logger.debug("Calibration correctly calculated.")

    def gamma_short(self, freq: int) -> complex:
        g = Calibration.IDEAL_SHORT
        if not self.useIdealShort:
            logger.debug("Using short calibration set values.")
            Zsp = complex(0, 1) * 2 * math.pi * freq * (
                self.shortL0 + self.shortL1 * freq +
                self.shortL2 * freq**2 + self.shortL3 * freq**3)
            # Referencing https://arxiv.org/pdf/1606.02446.pdf (18) - (21)
            g = (Zsp / 50 - 1) / (Zsp / 50 + 1) * cmath.exp(
                complex(0, 1) * 2 * math.pi * 2 * freq *
                self.shortLength * -1)
        return g

    def gamma_open(self, freq: int) -> complex:
        g = Calibration.IDEAL_OPEN
        if not self.useIdealOpen:
            logger.debug("Using open calibration set values.")
            divisor = (2 * math.pi * freq * (
                self.openC0 + self.openC1 * freq +
                self.openC2 * freq**2 + self.openC3 * freq**3))
            if divisor != 0:
                Zop = complex(0, -1) / divisor
                g = ((Zop / 50 - 1) / (Zop / 50 + 1)) * cmath.exp(
                    complex(0, 1) * 2 * math.pi *
                    2 * freq * self.openLength * -1)
        return g

    def gamma_load(self, freq: int) -> complex:
        g = Calibration.IDEAL_LOAD
        if not self.useIdealLoad:
            logger.debug("Using load calibration set values.")
            Zl = self.loadR + (complex(0, 1) * 2 *
                               math.pi * freq * self.loadL)
            g = (Zl / 50 - 1) / (Zl / 50 + 1) * cmath.exp(
                complex(0, 1) * 2 * math.pi *
                2 * freq * self.loadLength * -1)
        return g

    def gamma_through(self, freq: int) -> complex:
        g = complex(1, 0)
        if not self.useIdealThrough:
            logger.debug("Using through calibration set values.")
            g = cmath.exp(complex(0, 1) * 2 * math.pi *
                          self.throughLength * freq * -1)
        return g

    def gen_interpolation(self):
        freq = []
        e00 = []
        e11 = []
        delta_e = []
        e30 = []
        e10e32 = []

        for caldata in self.dataset.values():
            freq.append(caldata["freq"])
            e00.append(caldata["e00"])
            e11.append(caldata["e11"])
            delta_e.append(caldata["delta_e"])
            e30.append(caldata["e30"])
            e10e32.append(caldata["e10e32"])

        self.interp["e00"] = interp1d(freq, e00, kind="slinear")
        self.interp["e11"] = interp1d(freq, e11, kind="slinear")
        self.interp["delta_e"] = interp1d(freq, delta_e, kind="slinear")
        self.interp["e30"] = interp1d(freq, e30, kind="slinear")
        self.interp["e10e32"] = interp1d(freq, e10e32, kind="slinear")

    def correct11(self, dp: Datapoint):
        i = self.interp
        try:
            s11 = (dp.z - i["e00"](dp.freq)) / (
                (dp.z * i["e11"](dp.freq)) - i["delta_e"](dp.freq))
            return Datapoint(dp.freq, s11.real, s11.imag)
        except ValueError:
            # TODO: implement warn message in gui
            logger.info("Data outside calibration")

        nearest = sorted(self.dataset.frequencies(),
                         key=lambda k: abs(dp.freq - k))[0]
        ds = self.dataset.get(nearest)
        s11 = (dp.z - ds["e00"]) / (
            (dp.z * ds["e11"]) - ds["delta_e"])
        return Datapoint(dp.freq, s11.real, s11.imag)

    def correct21(self, dp: Datapoint):
        i = self.interp
        try:
            s21 = (dp.z - i["e30"](dp.freq)) / i["e10e32"](dp.freq)
            return Datapoint(dp.freq, s21.real, s21.imag)
        except ValueError:
            # TODO: implement warn message in gui
            logger.info("Data outside calibration")

        nearest = sorted(self.dataset.frequencies(),
                         key=lambda k: abs(dp.freq - k))[0]
        ds = self.dataset.get(nearest)
        s21 = (dp.z - ds["e30"]) / ds["e10e32"]
        return Datapoint(dp.freq, s21.real, s21.imag)

    # TODO: implement tests
    def save(self, filename: str):
        # Save the calibration data to file
        if not self.isValid1Port():
            raise ValueError("Not a valid 1-Port calibration")
        with open(f"{filename}", "w") as calfile:
            calfile.write("# Calibration data for NanoVNA-Saver\n")
            for note in self.notes:
                calfile.write(f"! {note}\n")
            calfile.write(
                "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                " ThroughR ThroughI IsolationR IsolationI\n")
            for freq in self.dataset.frequencies():
                calfile.write(f"{self.dataset.get(freq)}\n")

    # TODO: implement tests
    # TODO: Exception should be catched by caller
    def load(self, filename):
        self.source = os.path.basename(filename)
        self.dataset = CalDataSet()
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

                for name in Calibration.CAL_NAMES[:nr_cals]:
                    self.dataset.insert(
                        name,
                        Datapoint(int(cal["freq"]),
                                  float(cal[f"{name}r"]),
                                  float(cal[f"{name}i"])))
