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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import numpy.typing as npt

from .RFTools import Datapoint
from .Touchstone import Touchstone

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
    e00: complex = complex(0.0)  # Directivity
    e11: complex = complex(0.0)  # Port1 match
    delta_e: complex = complex(0.0)  # Tracking
    e10e01: complex = complex(0.0)  # Forward Reflection Tracking
    # 2 port
    e30: complex = complex(0.0)  # Forward isolation
    e22: complex = complex(0.0)  # Port2 match
    e10e32: complex = complex(0.0)  # Forward transmission

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
    short_touchstone: Touchstone = field(default_factory=Touchstone)
    short_is_ideal: bool = True
    short_l0: float = 5.7e-12
    short_l1: float = -8.96e-20
    short_l2: float = -1.1e-29
    short_l3: float = -4.12e-37
    short_length: float = -34.2  # ps

    open_state: str = ""
    open_touchstone: Touchstone = field(default_factory=Touchstone)
    open_is_ideal: bool = True
    open_c0: float = 2.1e-14
    open_c1: float = 5.67e-23
    open_c2: float = -2.39e-31
    open_c3: float = 2.0e-40
    open_length: float = 0.0

    load_state: str = ""
    load_touchstone: Touchstone = field(default_factory=Touchstone)
    load_is_ideal: bool = True
    load_r: float = 50.0
    load_l: float = 0.0
    load_c: float = 0.0
    load_length: float = 0.0

    through_is_ideal: bool = True
    through_length: float = 0.0


class CalDataSet(UserDict):
    def __init__(self) -> None:
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
            self._append_match(m, header, i, line)
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

    def freq_min(self) -> int:
        return self.frequencies()[0] if self.frequencies() else 0

    def freq_max(self) -> int:
        return self.frequencies()[-1] if self.frequencies() else 0

    def get(self, key: int, default: Optional[CalData] = None) -> CalData:  # type: ignore[override]
        if default:
            return self.data.get(key, default)
        return self.data[key]

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


ERROR_TERMS = ("e00", "e11", "delta_e", "e10e01", "e30", "e22", "e10e32")
RXP_CREATED = re.compile(r"^Created:\s*(?P<ts>\S+)")

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]


def _interp_complex(
    freq: FloatArray, xp: FloatArray, fp: ComplexArray
) -> ComplexArray:
    """Linear interpolation of complex values, holding the edge values
    outside of the calibrated range (same behaviour as the former
    scipy interp1d(kind="slinear", fill_value=(first, last)))."""
    return np.interp(freq, xp, fp.real) + 1j * np.interp(freq, xp, fp.imag)


def solve_one_port(  # noqa: PLR0913
    gm1: ComplexArray,
    gm2: ComplexArray,
    gm3: ComplexArray,
    g1: ComplexArray,
    g2: ComplexArray,
    g3: ComplexArray,
) -> tuple[ComplexArray, ComplexArray, ComplexArray]:
    """Solve the 3-term error model from measured (gm) and actual (g)
    reflection of short (1), open (2) and load (3).

    Returns (e00, e11, delta_e) with S11 = (m - e00) / (m * e11 - delta_e)
    """
    denominator = (
        g1 * (g2 - g3) * gm1
        + g2 * g3 * gm2
        - g2 * g3 * gm3
        - (g2 * gm2 - g3 * gm3) * g1
    )
    if np.any(denominator == 0):
        raise ZeroDivisionError("singular SOL measurement")
    e00 = (
        -(
            (g2 * gm3 - g3 * gm3) * g1 * gm2
            - (g2 * g3 * gm2 - g2 * g3 * gm3 - (g3 * gm2 - g2 * gm3) * g1) * gm1
        )
        / denominator
    )
    e11 = ((g2 - g3) * gm1 - g1 * (gm2 - gm3) + g3 * gm2 - g2 * gm3) / (
        denominator
    )
    delta_e = (
        -(
            (g1 * (gm2 - gm3) - g2 * gm2 + g3 * gm3) * gm1
            + (g2 * gm3 - g3 * gm3) * gm2
        )
        / denominator
    )
    return e00, e11, delta_e


def solve_two_port(  # noqa: PLR0913
    e00: ComplexArray,
    e11: ComplexArray,
    delta_e: ComplexArray,
    gm4: ComplexArray,
    gm5: ComplexArray,
    gm6: ComplexArray,
    gt: ComplexArray,
) -> tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
    """Solve forward transmission terms from through (gm4), reflection at
    port 1 while through connected (gm5) and isolation (gm6).

    Returns (e10e01, e30, e22, e10e32)"""
    gm7 = gm5 - e00
    e30 = gm6
    e10e01 = e00 * e11 - delta_e
    e22 = gm7 / (gm7 * e11 * gt**2 + e10e01 * gt**2)
    e10e32 = (gm4 - gm6) * (1 - e11 * e22 * gt**2) / gt
    return e10e01, e30, e22, e10e32


def correct_full_two_port(
    terms: dict[str, ComplexArray],
    s11m: ComplexArray,
    s21m: ComplexArray,
    s12m: ComplexArray,
    s22m: ComplexArray,
) -> tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
    """Full 2-port correction for a one-path (T/R) VNA using a forward
    and a reversed (DUT flipped) measurement.

    As the DUT is physically reversed, the reverse error terms equal the
    forward ones: reverse source match = e11, reverse load match = e22,
    reverse directivity = e00, ... This is the 12-term correction with
    those identities applied.
    """
    e00, e11, e10e01 = terms["e00"], terms["e11"], terms["e10e01"]
    e30, e22, e10e32 = terms["e30"], terms["e22"], terms["e10e32"]
    n11 = (s11m - e00) / e10e01
    n22 = (s22m - e00) / e10e01
    n21 = (s21m - e30) / e10e32
    n12 = (s12m - e30) / e10e32
    d = (1 + n11 * e11) * (1 + n22 * e11) - n21 * n12 * e22 * e22
    s11 = (n11 * (1 + n22 * e11) - e22 * n21 * n12) / d
    s22 = (n22 * (1 + n11 * e11) - e22 * n21 * n12) / d
    s21 = n21 * (1 + n22 * (e11 - e22)) / d
    s12 = n12 * (1 + n11 * (e11 - e22)) / d
    return s11, s21, s12, s22


class Calibration:
    def __init__(self):
        self.notes = []
        self.dataset = CalDataSet()
        self.cal_element = CalElement()
        self.interp: dict[str, ComplexArray] = {}
        self._interp_freq: FloatArray = np.array([], dtype=np.float64)
        self.isCalculated = False
        self.created: Optional[datetime] = None

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

    def _measured(self, name: str) -> ComplexArray:
        return np.array(
            [getattr(c, name) for c in self.dataset.values()],
            dtype=np.complex128,
        )

    def calc_corrections(self):
        if not self.isValid1Port():
            logger.warning("Tried to calibrate from insufficient data.")
            raise ValueError(
                "All of short, open and load calibration steps"
                "must be completed for calibration to be applied."
            )
        logger.debug("Calculating calibration for %d points.", self.size())

        freq = np.array(self.dataset.frequencies(), dtype=np.float64)
        error_msg = (
            "Two of short, open and load returned the same"
            " values at some frequency."
        )
        try:
            with np.errstate(divide="raise", invalid="raise"):
                e00, e11, delta_e = solve_one_port(
                    self._measured("short"),
                    self._measured("open"),
                    self._measured("load"),
                    self.gamma_short(freq),
                    self.gamma_open(freq),
                    self.gamma_load(freq),
                )
                if self.isValid2Port():
                    e10e01, e30, e22, e10e32 = solve_two_port(
                        e00,
                        e11,
                        delta_e,
                        self._measured("through"),
                        self._measured("thrurefl"),
                        self._measured("isolation"),
                        self.gamma_through(freq),
                    )
                else:
                    e10e01 = e00 * e11 - delta_e
                    e30 = np.zeros_like(e00)
                    e22 = np.zeros_like(e00)
                    e10e32 = np.zeros_like(e00)
        except (ZeroDivisionError, FloatingPointError) as exc:
            self.isCalculated = False
            logger.error(
                "Division error - did you use the same measurement"
                " for two of short, open and load?"
            )
            raise ValueError(error_msg) from exc
        terms = {
            "e00": e00,
            "e11": e11,
            "delta_e": delta_e,
            "e10e01": e10e01,
            "e30": e30,
            "e22": e22,
            "e10e32": e10e32,
        }
        if not all(np.all(np.isfinite(v)) for v in terms.values()):
            self.isCalculated = False
            raise ValueError(error_msg)

        # keep per frequency values in dataset for reference / export
        for i, caldata in enumerate(self.dataset.values()):
            for name, values in terms.items():
                setattr(caldata, name, complex(values[i]))

        self._interp_freq = freq
        self.interp = terms
        self.isCalculated = True
        if self.created is None:
            self.created = datetime.now()
        logger.debug("Calibration correctly calculated.")

    # Calibration standard models. All accept scalar or array frequencies.

    @staticmethod
    def _touchstone_gamma(touchstone, freq) -> ComplexArray:
        f_ts = np.array([d.freq for d in touchstone.s11], dtype=np.float64)
        z_ts = np.array([d.z for d in touchstone.s11], dtype=np.complex128)
        return _interp_complex(np.asarray(freq, dtype=np.float64), f_ts, z_ts)

    def gamma_short(self, freq):
        freq = np.asarray(freq, dtype=np.float64)
        if self.cal_element.short_state == "IDEAL":
            return np.full(freq.shape, IDEAL_SHORT, dtype=np.complex128)
        if self.cal_element.short_state == "FILE":
            return self._touchstone_gamma(
                self.cal_element.short_touchstone, freq
            )
        logger.debug("Using short calibration set values.")
        ce = self.cal_element
        Zsp = 1j * (
            2.0
            * math.pi
            * freq
            * (
                ce.short_l0
                + ce.short_l1 * freq
                + ce.short_l2 * freq**2
                + ce.short_l3 * freq**3
            )
        )
        # Referencing https://arxiv.org/pdf/1606.02446.pdf (18) - (21)
        return (
            (Zsp / 50.0 - 1.0)
            / (Zsp / 50.0 + 1.0)
            * np.exp(-4.0j * math.pi * freq * ce.short_length)
        )

    def gamma_open(self, freq):
        freq = np.asarray(freq, dtype=np.float64)
        if self.cal_element.open_state == "IDEAL":
            return np.full(freq.shape, IDEAL_OPEN, dtype=np.complex128)
        if self.cal_element.open_state == "FILE":
            return self._touchstone_gamma(
                self.cal_element.open_touchstone, freq
            )
        logger.debug("Using open calibration set values.")
        ce = self.cal_element
        Zop = 1j * (
            2.0
            * math.pi
            * freq
            * (
                ce.open_c0
                + ce.open_c1 * freq
                + ce.open_c2 * freq**2
                + ce.open_c3 * freq**3
            )
        )
        return ((1.0 - 50.0 * Zop) / (1.0 + 50.0 * Zop)) * np.exp(
            -4.0j * math.pi * freq * ce.open_length
        )

    def gamma_load(self, freq):
        freq = np.asarray(freq, dtype=np.float64)
        if self.cal_element.load_state == "IDEAL":
            return np.full(freq.shape, IDEAL_LOAD, dtype=np.complex128)
        if self.cal_element.load_state == "FILE":
            return self._touchstone_gamma(
                self.cal_element.load_touchstone, freq
            )
        logger.debug("Using load calibration set values.")
        ce = self.cal_element
        Zl = np.full(freq.shape, ce.load_r, dtype=np.complex128)
        if ce.load_c > 0.0:
            Zl = ce.load_r / (
                1.0 + 2.0j * ce.load_r * math.pi * freq * ce.load_c
            )
        if ce.load_l > 0.0:
            Zl = Zl + 2j * math.pi * freq * ce.load_l
        return (
            (Zl / 50.0 - 1.0)
            / (Zl / 50.0 + 1.0)
            * np.exp(-4j * math.pi * freq * ce.load_length)
        )

    def gamma_through(self, freq):
        freq = np.asarray(freq, dtype=np.float64)
        if self.cal_element.through_is_ideal:
            return np.full(freq.shape, IDEAL_THROUGH, dtype=np.complex128)
        logger.debug("Using through calibration set values.")
        return np.exp(-2.0j * math.pi * self.cal_element.through_length * freq)

    # Correction

    def terms_at(self, freq) -> dict[str, ComplexArray]:
        """Error terms interpolated to the given frequencies"""
        freq = np.asarray(freq, dtype=np.float64)
        return {
            name: _interp_complex(freq, self._interp_freq, values)
            for name, values in self.interp.items()
        }

    def correct11_array(self, freq, s11m) -> ComplexArray:
        t = self.terms_at(freq)
        s11m = np.asarray(s11m, dtype=np.complex128)
        return (s11m - t["e00"]) / (s11m * t["e11"] - t["delta_e"])

    def correct21_array(self, freq, s21m, s11m) -> ComplexArray:
        """Enhanced response correction of S21 (source match corrected)"""
        t = self.terms_at(freq)
        s11m = np.asarray(s11m, dtype=np.complex128)
        s21m = np.asarray(s21m, dtype=np.complex128)
        s21 = (s21m - t["e30"]) / t["e10e32"]
        return s21 * (t["e10e01"] / (t["e11"] * s11m - t["delta_e"]))

    def correct_two_port_array(
        self, freq, s11m, s21m, s12m, s22m
    ) -> tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
        if not self.isValid2Port():
            raise ValueError(
                "Full 2-port correction needs a 2-port calibration"
            )
        return correct_full_two_port(
            self.terms_at(freq),
            *(
                np.asarray(v, dtype=np.complex128)
                for v in (s11m, s21m, s12m, s22m)
            ),
        )

    def correct11(self, dp: Datapoint):
        s11 = complex(self.correct11_array([dp.freq], [dp.z])[0])
        return Datapoint(dp.freq, s11.real, s11.imag)

    def correct21(self, dp: Datapoint, dp11: Datapoint):
        s21 = complex(self.correct21_array([dp.freq], [dp.z], [dp11.z])[0])
        return Datapoint(dp.freq, s21.real, s21.imag)

    def freq_range(self) -> tuple[int, int]:
        return self.dataset.freq_min(), self.dataset.freq_max()

    def save(self, filename: str):
        notes = [n for n in self.notes if not RXP_CREATED.match(n)]
        if self.created:
            notes.append(
                f"Created: {self.created.isoformat(timespec='seconds')}"
            )
        self.dataset.notes = "\n".join(notes)
        if not self.isValid1Port():
            raise ValueError("Not a valid calibration")
        with open(filename, mode="w", encoding="utf-8") as calfile:
            calfile.write(str(self.dataset))

    def load(self, filename):
        self.source = os.path.basename(filename)
        with open(filename, encoding="utf-8") as calfile:
            self.dataset = CalDataSet().from_str(calfile.read())
            self.notes = self.dataset.notes.splitlines()
        self.created = None
        for note in self.notes:
            if m := RXP_CREATED.match(note):
                try:
                    self.created = datetime.fromisoformat(m.group("ts"))
                except ValueError:
                    logger.warning("Unparsable calibration date: %s", note)
        if self.created is None:
            try:
                self.created = datetime.fromtimestamp(
                    os.path.getmtime(filename)
                )
            except OSError:
                self.created = None
