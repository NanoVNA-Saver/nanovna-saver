#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
from dataclasses import dataclass
from typing import List

from scipy.interpolate import interp1d

from NanoVNASaver.RFTools import Datapoint

RXP_CAL_LINE = re.compile(r"""^\s*
    (?P<freq>\d+) \s+
    (?P<shortr>[-0-9Ee.]+) \s+ (?P<shorti>[-0-9Ee.]+) \s+
    (?P<openr>[-0-9Ee.]+) \s+ (?P<openi>[-0-9Ee.]+) \s+
    (?P<loadr>[-0-9Ee.]+) \s+ (?P<loadi>[-0-9Ee.]+)(?: \s
    (?P<throughr>[-0-9Ee.]+) \s+ (?P<throughi>[-0-9Ee.]+) \s+
    (?P<thrureflr>[-0-9Ee.]+) \s+ (?P<thrurefli>[-0-9Ee.]+) \s+
    (?P<isolationr>[-0-9Ee.]+) \s+ (?P<isolationi>[-0-9Ee.]+)
    )?
""", re.VERBOSE)

logger = logging.getLogger(__name__)


def correct_delay(d: Datapoint, delay: float, reflect: bool = False):
    mult = 2 if reflect else 1
    corr_data = d.z * cmath.exp(
        complex(0, 1) * 2 * math.pi * d.freq * delay * -1 * mult)
    return Datapoint(d.freq, corr_data.real, corr_data.imag)


@dataclass
class CalData:
    short: complex = complex(0.0, 0.0)
    open: complex = complex(0.0, 0.0)
    load: complex = complex(0.0, 0.0)
    through: complex = complex(0.0, 0.0)
    thrurefl: complex = complex(0.0, 0.0)
    isolation: complex = complex(0.0, 0.0)
    freq: int = 0
    e00: float = 0.0  # Directivity
    e11: float = 0.0  # Port1 match
    delta_e: float = 0.0  # Tracking
    e10e01: float = 0.0  # Forward Reflection Tracking
    # 2 port
    e30: float = 0.0  # Forward isolation
    e22: float = 0.0  # Port2 match
    e10e32: float = 0.0  # Forward transmission

    def __str__(self):
        return (
            f'{self.freq}'
            f' {self.short.real} {self.short.imag}'
            f' {self.open.real} {self.open.imag}'
            f' {self.load.real} {self.load.imag}' + (
                f' {self.through.real} {self.through.imag}'
                f' {self.thrurefl.real} {self.thrurefl.imag}'
                f' {self.isolation.real} {self.isolation.imag}'
                if self.through else ''
            )
        )


class CalDataSet(UserDict):
    def __init__(self):
        self.data: defaultdict[int, CalData] = defaultdict(CalData)

    def insert(self, name: str, dp: Datapoint):
        if name not in {'short', 'open', 'load',
                        'through', 'thrurefl', 'isolation'}:
            raise KeyError(name)
        freq = dp.freq
        setattr(self.data[freq], name, (dp.z))
        self.data[freq].freq = freq

    def frequencies(self) -> List[int]:
        return sorted(self.data.keys())

    def get(self, freq: int) -> CalData:
        return self.data[freq]

    def items(self):
        yield from self.data.items()

    def values(self):
        for freq in self.frequencies():
            yield self.get(freq)

    def size_of(self, name: str) -> int:
        return len(
            [True for val in self.data.values() if getattr(val, name)]
        )

    def complete1port(self) -> bool:
        for val in self.data.values():
            if not all((val.short, val.open, val.load)):
                return False
        return any(self.data)

    def complete2port(self) -> bool:
        if not self.complete1port():
            return False
        for val in self.data.values():
            if not all((val.through, val.thrurefl, val.isolation)):
                return False
        return any(self.data)


class Calibration:
    CAL_NAMES = ("short", "open", "load", "through", "thrurefl", "isolation",)
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

    def _calc_port_1(self, freq: int, cal: CalData):
        g1 = self.gamma_short(freq)
        g2 = self.gamma_open(freq)
        g3 = self.gamma_load(freq)

        gm1 = cal.short
        gm2 = cal.open
        gm3 = cal.load

        denominator = (g1 * (g2 - g3) * gm1 +
                       g2 * g3 * gm2 - g2 * g3 * gm3 -
                       (g2 * gm2 - g3 * gm3) * g1)
        cal.e00 = - ((g2 * gm3 - g3 * gm3) * g1 * gm2 -
                     (g2 * g3 * gm2 - g2 * g3 * gm3 -
                         (g3 * gm2 - g2 * gm3) * g1) * gm1
                     ) / denominator
        cal.e11 = ((g2 - g3) * gm1 - g1 * (gm2 - gm3) +
                   g3 * gm2 - g2 * gm3) / denominator
        cal.delta_e = - ((g1 * (gm2 - gm3) - g2 * gm2 + g3 *
                          gm3) * gm1 + (g2 * gm3 - g3 * gm3) *
                         gm2) / denominator

    def _calc_port_2(self, freq: int, cal: CalData):
        gt = self.gamma_through(freq)

        gm4 = cal.through
        gm5 = cal.thrurefl
        gm6 = cal.isolation
        gm7 = gm5 - cal.e00

        cal.e30 = cal.isolation
        cal.e10e01 = cal.e00 * cal.e11 - cal.delta_e
        cal.e22 = gm7 / (
            gm7 * cal.e11 * gt ** 2 + cal.e10e01 * gt ** 2)
        cal.e10e32 = (gm4 - gm6) * (
            1 - cal.e11 * cal.e22 * gt ** 2) / gt

    def calc_corrections(self):
        if not self.isValid1Port():
            logger.warning(
                "Tried to calibrate from insufficient data.")
            raise ValueError(
                "All of short, open and load calibration steps"
                "must be completed for calibration to be applied.")
        logger.debug("Calculating calibration for %d points.", self.size())

        for freq, caldata in self.dataset.items():
            try:
                self._calc_port_1(freq, caldata)
                if self.isValid2Port():
                    self._calc_port_2(freq, caldata)
            except ZeroDivisionError as exc:
                self.isCalculated = False
                logger.error(
                    "Division error - did you use the same measurement"
                    " for two of short, open and load?")
                raise ValueError(
                    f"Two of short, open and load returned the same"
                    f" values at frequency {freq}Hz.") from exc

        self.gen_interpolation()
        self.isCalculated = True
        logger.debug("Calibration correctly calculated.")

    def gamma_short(self, freq: int) -> complex:
        g = Calibration.IDEAL_SHORT
        if not self.useIdealShort:
            logger.debug("Using short calibration set values.")
            Zsp = complex(0, 2 * math.pi * freq * (
                self.shortL0 + self.shortL1 * freq +
                self.shortL2 * freq ** 2 + self.shortL3 * freq ** 3))
            # Referencing https://arxiv.org/pdf/1606.02446.pdf (18) - (21)
            g = (Zsp / 50 - 1) / (Zsp / 50 + 1) * cmath.exp(
                complex(0, 2 * math.pi * 2 * freq * self.shortLength * -1))
        return g

    def gamma_open(self, freq: int) -> complex:
        g = Calibration.IDEAL_OPEN
        if not self.useIdealOpen:
            logger.debug("Using open calibration set values.")
            Zop = complex(0, 2 * math.pi * freq * (
                self.openC0 + self.openC1 * freq +
                self.openC2 * freq ** 2 + self.openC3 * freq ** 3))
            g = ((1 - 50 * Zop) / (1 + 50 * Zop)) * cmath.exp(
                complex(0, 2 * math.pi * 2 * freq * self.openLength * -1))
        return g

    def gamma_load(self, freq: int) -> complex:
        g = Calibration.IDEAL_LOAD
        if not self.useIdealLoad:
            logger.debug("Using load calibration set values.")
            Zl = complex(self.loadR, 0)
            if self.loadC > 0:
                Zl = self.loadR / \
                    complex(1, 2 * self.loadR * math.pi * freq * self.loadC)
            if self.loadL > 0:
                Zl = Zl + complex(0, 2 * math.pi * freq * self.loadL)
            g = (Zl / 50 - 1) / (Zl / 50 + 1) * cmath.exp(
                complex(0, 2 * math.pi * 2 * freq * self.loadLength * -1))
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
        e10e01 = []
        e30 = []
        e22 = []
        e10e32 = []

        for caldata in self.dataset.values():
            freq.append(caldata.freq)
            e00.append(caldata.e00)
            e11.append(caldata.e11)
            delta_e.append(caldata.delta_e)
            e10e01.append(caldata.e10e01)
            e30.append(caldata.e30)
            e22.append(caldata.e22)
            e10e32.append(caldata.e10e32)

        self.interp = {
            "e00": interp1d(freq, e00,
                            kind="slinear", bounds_error=False,
                            fill_value=(e00[0], e00[-1])),
            "e11": interp1d(freq, e11,
                            kind="slinear", bounds_error=False,
                            fill_value=(e11[0], e11[-1])),
            "delta_e": interp1d(freq, delta_e,
                                kind="slinear", bounds_error=False,
                                fill_value=(delta_e[0], delta_e[-1])),
            "e10e01": interp1d(freq, e10e01,
                               kind="slinear", bounds_error=False,
                               fill_value=(e10e01[0], e10e01[-1])),
            "e30": interp1d(freq, e30,
                            kind="slinear", bounds_error=False,
                            fill_value=(e30[0], e30[-1])),
            "e22": interp1d(freq, e22,
                            kind="slinear", bounds_error=False,
                            fill_value=(e22[0], e22[-1])),
            "e10e32": interp1d(freq, e10e32,
                               kind="slinear", bounds_error=False,
                               fill_value=(e10e32[0], e10e32[-1])),
        }

    def correct11(self, dp: Datapoint):
        i = self.interp
        s11 = (dp.z - i["e00"](dp.freq)) / (
            (dp.z * i["e11"](dp.freq)) - i["delta_e"](dp.freq))
        return Datapoint(dp.freq, s11.real, s11.imag)

    def correct21(self, dp: Datapoint, dp11: Datapoint):
        i = self.interp
        s21 = (dp.z - i["e30"](dp.freq)) / i["e10e32"](dp.freq)
        s21 = s21 * (i["e10e01"](dp.freq) / (i["e11"](dp.freq)
                                             * dp11.z - i["delta_e"](dp.freq)))
        return Datapoint(dp.freq, s21.real, s21.imag)

    # TODO: implement tests
    def save(self, filename: str):
        # Save the calibration data to file
        if not self.isValid1Port():
            raise ValueError("Not a valid 1-Port calibration")
        with open(filename, mode="w", encoding='utf-8') as calfile:
            calfile.write("# Calibration data for NanoVNA-Saver\n")
            for note in self.notes:
                calfile.write(f"! {note}\n")
            calfile.write(
                "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                " ThroughR ThroughI ThrureflR ThrureflI"
                " IsolationR IsolationI\n")
            for freq in self.dataset.frequencies():
                calfile.write(f"{self.dataset.get(freq)}\n")

    # TODO: implement tests
    # TODO: Exception should be catched by caller
    def load(self, filename):
        self.source = os.path.basename(filename)
        self.dataset = CalDataSet()
        self.notes = []

        parsed_header = False
        with open(filename, encoding='utf-8') as calfile:
            for i, line in enumerate(calfile):
                line = line.strip()
                if line.startswith("!"):
                    note = line[2:]
                    self.notes.append(note)
                    continue
                if line.startswith("#"):
                    if not parsed_header and line == (
                            "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                            " ThroughR ThroughI ThrureflR ThrureflI"
                            " IsolationR IsolationI"):
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

                nr_cals = 6 if cal["throughr"] else 3
                for name in Calibration.CAL_NAMES[:nr_cals]:
                    self.dataset.insert(
                        name,
                        Datapoint(int(cal["freq"]),
                                  float(cal[f"{name}r"]),
                                  float(cal[f"{name}i"])))
