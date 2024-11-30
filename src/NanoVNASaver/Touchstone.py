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
import io
import logging
import math
from operator import attrgetter

from scipy.interpolate import interp1d

from NanoVNASaver.RFTools import Datapoint

logger = logging.getLogger(__name__)


class Options:
    # Fun fact: In Touchstone 1.1 spec all params are optional unordered.
    # Just the line has to start with "#"
    UNIT_TO_FACTOR = {
        "ghz": 10**9,
        "mhz": 10**6,
        "khz": 10**3,
        "hz": 10**0,
    }
    VALID_UNITS = UNIT_TO_FACTOR.keys()
    VALID_PARAMETERS = "syzgh"
    VALID_FORMATS = ("ma", "db", "ri")

    def __init__(
        self,
        unit: str = "GHZ",
        parameter: str = "S",
        t_format: str = "ma",
        resistance: int = 50,
    ):
        # set defaults
        assert unit.lower() in Options.VALID_UNITS
        assert parameter.lower() in Options.VALID_PARAMETERS
        assert t_format.lower() in Options.VALID_FORMATS
        assert resistance > 0
        self.unit = unit.lower()
        self.parameter = parameter.lower()
        self.format = t_format.lower()
        self.resistance = resistance

    @property
    def factor(self) -> int:
        return Options.UNIT_TO_FACTOR[self.unit]

    def __str__(self) -> str:
        return (
            f"# {self.unit} {self.parameter}"
            f" {self.format} r {self.resistance}"
        ).upper()

    def parse(self, line: str):
        if not line.startswith("#"):
            raise TypeError(f"Not an option line: {line}")
        punit = pparam = pformat = presist = False
        params = iter(line[1:].lower().split())
        for p in params:
            if p in Options.VALID_UNITS and not punit:
                self.unit = p
                punit = True
            elif p in Options.VALID_PARAMETERS and not pparam:
                self.parameter = p
                pparam = True
            elif p in Options.VALID_FORMATS and not pformat:
                self.format = p
                pformat = True
            elif p == "r" and not presist:
                rstr = next(params)
                try:
                    self.resistance = int(rstr)
                except ValueError:
                    logger.warning("Non integer resistance value: %s", rstr)
                    self.resistance = int(float(rstr))
            else:
                raise TypeError(f"Illegal option line: {line}")


class Touchstone:
    FIELD_ORDER = ("11", "21", "12", "22")

    def __init__(self, filename: str = ""):
        self.filename = filename
        self.sdata = [[], [], [], []]  # at max 4 data pairs
        self.comments = []
        self.opts = Options()
        self._interp = {}

    @property
    def s11(self) -> list[Datapoint]:
        return self.s("11")

    @s11.setter
    def s11(self, value: list[Datapoint]):
        self.sdata[0] = value

    @property
    def s12(self) -> list[Datapoint]:
        return self.s("12")

    @s12.setter
    def s12(self, value: list[Datapoint]):
        self.sdata[2] = value

    @property
    def s21(self) -> list[Datapoint]:
        return self.s("21")

    @s21.setter
    def s21(self, value: list[Datapoint]):
        self.sdata[1] = value

    @property
    def s22(self) -> list[Datapoint]:
        return self.s("22")

    @s22.setter
    def s22(self, value: list[Datapoint]):
        self.sdata[3] = value

    @property
    def r(self) -> int:
        return self.opts.resistance

    def s(self, name: str) -> list[Datapoint]:
        return self.sdata[Touchstone.FIELD_ORDER.index(name)]

    def s_freq(self, name: str, freq: int) -> Datapoint:
        return Datapoint(
            freq,
            float(self._interp[name]["real"](freq)),
            float(self._interp[name]["imag"](freq)),
        )

    def swap(self):
        self.sdata = [self.s22, self.s12, self.s21, self.s11]

    def min_freq(self) -> int:
        return self.s("11")[0].freq

    def max_freq(self) -> int:
        return self.s("11")[-1].freq

    def gen_interpolation(self):
        for i in Touchstone.FIELD_ORDER:
            freq = []
            real = []
            imag = []

            for dp in self.s(i):
                freq.append(dp.freq)
                real.append(dp.re)
                imag.append(dp.im)

            self._interp[i] = {
                "real": interp1d(
                    freq,
                    real,
                    kind="slinear",
                    bounds_error=False,
                    fill_value=(real[0], real[-1]),
                ),
                "imag": interp1d(
                    freq,
                    imag,
                    kind="slinear",
                    bounds_error=False,
                    fill_value=(imag[0], imag[-1]),
                ),
            }

    def gen_interpolation_s11(self):
        freq = []
        real = []
        imag = []
        for dp in self.s("11"):
            freq.append(dp.freq)
            real.append(dp.re)
            imag.append(dp.im)

        self._interp["11"] = {
            "real": interp1d(
                freq,
                real,
                kind="slinear",
                bounds_error=False,
                fill_value=(real[0], real[-1]),
            ),
            "imag": interp1d(
                freq,
                imag,
                kind="slinear",
                bounds_error=False,
                fill_value=(imag[0], imag[-1]),
            ),
        }

    def _parse_comments(self, fp) -> str:
        for ln in fp:
            line = ln.strip()
            if line.startswith("!"):
                logger.info(line)
                self.comments.append(line)
                continue
            return line

    def _append_line_data(self, freq: int, data: list):
        data_list = iter(self.sdata)
        vals = iter(data)
        for v in vals:
            if self.opts.format == "ri":
                next(data_list).append(
                    Datapoint(freq, float(v), float(next(vals)))
                )
            if self.opts.format == "ma":
                z = cmath.rect(float(v), math.radians(float(next(vals))))
                next(data_list).append(Datapoint(freq, z.real, z.imag))
            if self.opts.format == "db":
                z = cmath.rect(
                    10 ** (float(v) / 20), math.radians(float(next(vals)))
                )
                next(data_list).append(Datapoint(freq, z.real, z.imag))

    def load(self):
        logger.info("Attempting to open file %s", self.filename)
        try:
            with open(self.filename, encoding="utf-8") as infile:
                self.loads(infile.read())
        except IOError as e:
            logger.exception("Failed to open %s: %s", self.filename, e)

    def loads(self, s: str):
        """Parse touchstone 1.1 string input
        appends to existing sdata if Touchstone object exists
        """
        try:
            self._loads(s)
        except TypeError as e:
            logger.exception("Failed to parse %s: %s", self.filename, e)

    def _loads(self, s: str):
        need_reorder = False
        with io.StringIO(s) as file:
            opts_line = self._parse_comments(file)
            self.opts.parse(opts_line)

            prev_freq = 0.0
            prev_len = 0
            for ln in file:
                line = ln.strip()
                # ignore empty lines (even if not specified)
                if line == "":
                    continue
                # accept comment lines after header
                if line.startswith("!"):
                    logger.warning("Comment after header: %s", line)
                    self.comments.append(line)
                    continue

                # ignore comments at data end
                data = line.split("!")[0]
                data = data.split()
                freq, data = round(float(data[0]) * self.opts.factor), data[1:]
                data_len = len(data)
                if data_len % 2 != 0:
                    raise TypeError("Data values aren't pairs: " + line)

                # consistency checks
                if freq <= prev_freq:
                    logger.warning("Frequency not ascending: %s", line)
                    need_reorder = True
                prev_freq = freq

                if prev_len == 0:
                    prev_len = data_len
                elif data_len != prev_len:
                    raise TypeError(f"Inconsistent number of pairs: {line}")

                self._append_line_data(freq, data)
            if need_reorder:
                logger.warning("Reordering data")
                for datalist in self.sdata:
                    datalist.sort(key=attrgetter("freq"))

    def save(self, nr_params: int = 1):
        """Save touchstone data to file.

        Args:
            nr_params: Number of s-parameters. 2 for s1p, 4 for s2p
        """

        logger.info("Attempting to open file %s for writing", self.filename)
        with open(self.filename, "w", encoding="utf-8") as outfile:
            outfile.write(self.saves(nr_params))

    def saves(self, nr_params: int = 1) -> str:
        """Returns touchstone data as string.

        Args:
            nr_params: Number of s-parameters. 1 for s1p, 4 for s2p
        """
        assert nr_params in {1, 4}

        ts_str = "# HZ S RI R 50\n"
        for i, dp_s11 in enumerate(self.s11):
            ts_str += f"{dp_s11.freq} {dp_s11.re} {dp_s11.im}"
            for j in range(1, nr_params):
                dp = self.sdata[j][i]
                if dp.freq != dp_s11.freq:
                    raise LookupError("Frequencies of sdata not correlated")
                ts_str += f" {dp.re} {dp.im}"
            ts_str += "\n"
        return ts_str
