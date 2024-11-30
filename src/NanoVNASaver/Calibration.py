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
import cmath
import logging
import math
import os
import re
from collections import UserDict, defaultdict
from dataclasses import dataclass

from scipy.interpolate import interp1d

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Touchstone import Touchstone

IDEAL_SHORT = complex(-1, 0)
IDEAL_OPEN = complex(1, 0)
IDEAL_LOAD = complex(0, 0)
IDEAL_THROUGH = complex(1, 0)

RXP_CAL_HEADER = re.compile(
    r"""
    ^ \# \s+ Hz \s+
    ShortR \s+ ShortI \s+ OpenR \s+ OpenI \s+
    LoadR \s+ LoadI
    (?P<through> \s+ ThroughR \s+ ThroughI)?
    (?P<thrurefl> \s+ ThrureflR \s+ ThrureflI)?
    (?P<isolation> \s+ IsolationR \s+ IsolationI)?
    \s* $
""",
    re.VERBOSE | re.IGNORECASE,
)

RXP_CAL_LINE = re.compile(
    r"""
    ^ \s*
    (?P<freq>\d+) \s+
    (?P<shortr>[-0-9Ee.]+) \s+ (?P<shorti>[-0-9Ee.]+) \s+
    (?P<openr>[-0-9Ee.]+) \s+ (?P<openi>[-0-9Ee.]+) \s+
    (?P<loadr>[-0-9Ee.]+) \s+ (?P<loadi>[-0-9Ee.]+)
    ( \s+ (?P<throughr>[-0-9Ee.]+) \s+ (?P<throughi>[-0-9Ee.]+))?
    ( \s+ (?P<thrureflr>[-0-9Ee.]+) \s+ (?P<thrurefli>[-0-9Ee.]+))?
    ( \s+ (?P<isolationr>[-0-9Ee.]+) \s+ (?P<isolationi>[-0-9Ee.]+))?
    \s* $
""",
    re.VERBOSE,
)

logger = logging.getLogger(__name__)


def correct_delay(d: Datapoint, delay: float, reflect: bool = False):
    mult = 2 if reflect else 1
    corr_data = d.z * cmath.exp(
        complex(0, 1) * 2 * math.pi * d.freq * delay * -1 * mult
    )
    return Datapoint(d.freq, corr_data.real, corr_data.imag)


@dataclass
class CalData:
    # pylint: disable=too-many-instance-attributes
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
            f"{self.freq}"
            f" {self.short.real} {self.short.imag}"
            f" {self.open.real} {self.open.imag}"
            f" {self.load.real} {self.load.imag}"
            + (
                f" {self.through.real} {self.through.imag}"
                f" {self.thrurefl.real} {self.thrurefl.imag}"
                f" {self.isolation.real} {self.isolation.imag}"
                if self.through
                else ""
            )
        )


@dataclass
class CalElement:
    # pylint: disable=too-many-instance-attributes
    short_state: str = ""
    short_touchstone: Touchstone = None
    short_is_ideal: bool = True
    short_l0: float = 5.7e-12
    short_l1: float = -8.96e-20
    short_l2: float = -1.1e-29
    short_l3: float = -4.12e-37
    short_length: float = -34.2  # ps

    open_state: str = ""
    open_touchstone: Touchstone = None
    open_is_ideal: bool = True
    open_c0: float = 2.1e-14
    open_c1: float = 5.67e-23
    open_c2: float = -2.39e-31
    open_c3: float = 2.0e-40
    open_length: float = 0.0

    load_state: str = ""
    load_touchstone: Touchstone = None
    load_is_ideal: bool = True
    load_r: float = 50.0
    load_l: float = 0.0
    load_c: float = 0.0
    load_length: float = 0.0

    through_is_ideal: bool = True
    through_length: float = 0.0


class CalDataSet(UserDict):
    def __init__(self):
        super().__init__()
        self.notes = ""
        self.data: defaultdict[int, CalData] = defaultdict(CalData)

    def __str__(self):
        return (
            (
                "# Calibration data for NanoVNA-Saver\n"
                + "\n".join([f"! {note}" for note in self.notes.splitlines()])
                + "\n"
                + "# Hz ShortR ShortI OpenR OpenI LoadR LoadI"
                + (
                    " ThroughR ThroughI ThrureflR"
                    " ThrureflI IsolationR IsolationI\n"
                    if self.complete2port()
                    else "\n"
                )
                + "\n".join(
                    [f"{self.data.get(freq)}" for freq in self.frequencies()]
                )
                + "\n"
            )
            if self.complete1port()
            else ""
        )

    def _append_match(
        self, m: re.Match, header: str, line_nr: int, line: str
    ) -> None:
        cal = m.groupdict()
        columns = {col[:-1] for col in cal.keys() if cal[col] and col != "freq"}
        if "through" in columns and header == "sol":
            logger.warning(
                "Through data with sol header. %i: %s", line_nr, line
            )
        # fix short data (without thrurefl)
        if "thrurefl" in columns and "isolation" not in columns:
            cal["isolationr"] = cal["thrureflr"]
            cal["isolationi"] = cal["thrurefli"]
            cal["thrureflr"], cal["thrurefli"] = None, None
        for name in columns:
            self.insert(
                name,
                Datapoint(
                    int(cal["freq"]),
                    float(cal[f"{name}r"]),
                    float(cal[f"{name}i"]),
                ),
            )

    def from_str(self, text: str) -> "CalDataSet":
        # reset data
        self.notes = ""
        self.data = defaultdict(CalData)
        header = ""
        # parse text
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()  # noqa: PLW2901

            if line.startswith("!"):
                self.notes += f"{line[2:]}\n"
                continue
            if m := RXP_CAL_HEADER.search(line):
                if header:
                    logger.warning(
                        "Duplicate header in cal data. %i: %s", i, line
                    )
                header = "through" if m.group("through") else "sol"
                continue
            if not line or line.startswith("#"):
                continue

            m = RXP_CAL_LINE.search(line)
            if not m:
                logger.warning("Illegal caldata. Line %i: %s", i, line)
                continue
            if not header:
                logger.warning(
                    "Caldata without having read header: %i: %s", i, line
                )
            self._append_match(m, header, line, i)
        return self

    def insert(self, name: str, dp: Datapoint):
        if name not in {
            "short",
            "open",
            "load",
            "through",
            "thrurefl",
            "isolation",
        }:
            raise KeyError(name)
        freq = dp.freq
        setattr(self.data[freq], name, (dp.z))
        self.data[freq].freq = freq

    def frequencies(self) -> list[int]:
        return sorted(self.data.keys())

    def get(self, key: int, default: CalData = None) -> CalData:
        return self.data.get(key, default)

    def items(self):
        yield from self.data.items()

    def values(self):
        for freq in self.frequencies():
            yield self.get(freq)

    def size_of(self, name: str) -> int:
        return len([True for val in self.data.values() if getattr(val, name)])

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
    def __init__(self):
        self.notes = []
        self.dataset = CalDataSet()
        self.cal_element = CalElement()
        self.interp = {}
        self.isCalculated = False

        self.source = "Manual"

    def insert(self, name: str, data: list[Datapoint]):
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

        denominator = (
            g1 * (g2 - g3) * gm1
            + g2 * g3 * gm2
            - g2 * g3 * gm3
            - (g2 * gm2 - g3 * gm3) * g1
        )
        cal.e00 = (
            -(
                (g2 * gm3 - g3 * gm3) * g1 * gm2
                - (g2 * g3 * gm2 - g2 * g3 * gm3 - (g3 * gm2 - g2 * gm3) * g1)
                * gm1
            )
            / denominator
        )
        cal.e11 = (
            (g2 - g3) * gm1 - g1 * (gm2 - gm3) + g3 * gm2 - g2 * gm3
        ) / denominator
        cal.delta_e = (
            -(
                (g1 * (gm2 - gm3) - g2 * gm2 + g3 * gm3) * gm1
                + (g2 * gm3 - g3 * gm3) * gm2
            )
            / denominator
        )

    def _calc_port_2(self, freq: int, cal: CalData):
        gt = self.gamma_through(freq)

        gm4 = cal.through
        gm5 = cal.thrurefl
        gm6 = cal.isolation
        gm7 = gm5 - cal.e00

        cal.e30 = cal.isolation
        cal.e10e01 = cal.e00 * cal.e11 - cal.delta_e
        cal.e22 = gm7 / (gm7 * cal.e11 * gt**2 + cal.e10e01 * gt**2)
        cal.e10e32 = (gm4 - gm6) * (1 - cal.e11 * cal.e22 * gt**2) / gt

    def calc_corrections(self):
        if not self.isValid1Port():
            logger.warning("Tried to calibrate from insufficient data.")
            raise ValueError(
                "All of short, open and load calibration steps"
                "must be completed for calibration to be applied."
            )
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
                    " for two of short, open and load?"
                )
                raise ValueError(
                    f"Two of short, open and load returned the same"
                    f" values at frequency {freq}Hz."
                ) from exc

        self.gen_interpolation()
        self.isCalculated = True
        logger.debug("Calibration correctly calculated.")

    def gamma_short(self, freq: int) -> complex:
        if self.cal_element.short_state == "IDEAL":
            return IDEAL_SHORT
        if self.cal_element.short_state == "FILE":
            self.cal_element.short_touchstone.gen_interpolation_s11()
            dp = self.cal_element.short_touchstone.s_freq("11", freq)
            return complex(dp.re, dp.im)
        logger.debug("Using short calibration set values.")
        cal_element = self.cal_element
        Zsp = complex(
            0.0,
            2.0
            * math.pi
            * freq
            * (
                cal_element.short_l0
                + cal_element.short_l1 * freq
                + cal_element.short_l2 * freq**2
                + cal_element.short_l3 * freq**3
            ),
        )
        # Referencing https://arxiv.org/pdf/1606.02446.pdf (18) - (21)
        return (
            (Zsp / 50.0 - 1.0)
            / (Zsp / 50.0 + 1.0)
            * cmath.exp(
                complex(0.0, -4.0 * math.pi * freq * cal_element.short_length)
            )
        )

    def gamma_open(self, freq: int) -> complex:
        if self.cal_element.open_state == "IDEAL":
            return IDEAL_OPEN
        if self.cal_element.open_state == "FILE":
            self.cal_element.open_touchstone.gen_interpolation_s11()
            dp = self.cal_element.open_touchstone.s_freq("11", freq)
            return complex(dp.re, dp.im)
        logger.debug("Using open calibration set values.")
        cal_element = self.cal_element
        Zop = complex(
            0.0,
            2.0
            * math.pi
            * freq
            * (
                cal_element.open_c0
                + cal_element.open_c1 * freq
                + cal_element.open_c2 * freq**2
                + cal_element.open_c3 * freq**3
            ),
        )
        return ((1.0 - 50.0 * Zop) / (1.0 + 50.0 * Zop)) * cmath.exp(
            complex(0.0, -4.0 * math.pi * freq * cal_element.open_length)
        )

    def gamma_load(self, freq: int) -> complex:
        if self.cal_element.load_state == "IDEAL":
            return IDEAL_LOAD
        if self.cal_element.load_state == "FILE":
            self.cal_element.load_touchstone.gen_interpolation_s11()
            dp = self.cal_element.load_touchstone.s_freq("11", freq)
            return complex(dp.re, dp.im)
        logger.debug("Using load calibration set values.")
        cal_element = self.cal_element
        Zl = complex(cal_element.load_r, 0.0)
        if cal_element.load_c > 0.0:
            Zl = cal_element.load_r / complex(
                1.0,
                2.0 * cal_element.load_r * math.pi * freq * cal_element.load_c,
            )
        if cal_element.load_l > 0.0:
            Zl = Zl + complex(0.0, 2 * math.pi * freq * cal_element.load_l)
        return (
            (Zl / 50.0 - 1.0)
            / (Zl / 50.0 + 1.0)
            * cmath.exp(
                complex(0.0, -4 * math.pi * freq * cal_element.load_length)
            )
        )

    def gamma_through(self, freq: int) -> complex:
        if self.cal_element.through_is_ideal:
            return IDEAL_THROUGH
        logger.debug("Using through calibration set values.")
        cal_element = self.cal_element
        return cmath.exp(
            complex(0.0, -2.0 * math.pi * cal_element.through_length * freq)
        )

    def gen_interpolation(self):
        (freq, e00, e11, delta_e, e10e01, e30, e22, e10e32) = zip(
            *[
                (
                    c.freq,
                    c.e00,
                    c.e11,
                    c.delta_e,
                    c.e10e01,
                    c.e30,
                    c.e22,
                    c.e10e32,
                )
                for c in self.dataset.values()
            ],
            strict=False,
        )

        self.interp = {
            "e00": interp1d(
                freq,
                e00,
                kind="slinear",
                bounds_error=False,
                fill_value=(e00[0], e00[-1]),
            ),
            "e11": interp1d(
                freq,
                e11,
                kind="slinear",
                bounds_error=False,
                fill_value=(e11[0], e11[-1]),
            ),
            "delta_e": interp1d(
                freq,
                delta_e,
                kind="slinear",
                bounds_error=False,
                fill_value=(delta_e[0], delta_e[-1]),
            ),
            "e10e01": interp1d(
                freq,
                e10e01,
                kind="slinear",
                bounds_error=False,
                fill_value=(e10e01[0], e10e01[-1]),
            ),
            "e30": interp1d(
                freq,
                e30,
                kind="slinear",
                bounds_error=False,
                fill_value=(e30[0], e30[-1]),
            ),
            "e22": interp1d(
                freq,
                e22,
                kind="slinear",
                bounds_error=False,
                fill_value=(e22[0], e22[-1]),
            ),
            "e10e32": interp1d(
                freq,
                e10e32,
                kind="slinear",
                bounds_error=False,
                fill_value=(e10e32[0], e10e32[-1]),
            ),
        }

    def correct11(self, dp: Datapoint):
        i = self.interp
        s11 = (dp.z - i["e00"](dp.freq)) / (
            (dp.z * i["e11"](dp.freq)) - i["delta_e"](dp.freq)
        )
        return Datapoint(dp.freq, s11.real, s11.imag)

    def correct21(self, dp: Datapoint, dp11: Datapoint):
        i = self.interp
        s21 = (dp.z - i["e30"](dp.freq)) / i["e10e32"](dp.freq)
        s21 = s21 * (
            i["e10e01"](dp.freq)
            / (i["e11"](dp.freq) * dp11.z - i["delta_e"](dp.freq))
        )
        return Datapoint(dp.freq, s21.real, s21.imag)

    def save(self, filename: str):
        self.dataset.notes = "\n".join(self.notes)
        if not self.isValid1Port():
            raise ValueError("Not a valid calibration")
        with open(filename, mode="w", encoding="utf-8") as calfile:
            calfile.write(str(self.dataset))

    def load(self, filename):
        self.source = os.path.basename(filename)
        with open(filename, encoding="utf-8") as calfile:
            self.dataset = CalDataSet().from_str(calfile.read())
            self.notes = self.dataset.notes.splitlines()
