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
import cmath
import io
from operator import attrgetter
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

    def __init__(self,
                 unit: str = "GHZ",
                 parameter: str = "S",
                 t_format: str = "ma",
                 resistance: int = 50):
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
            raise TypeError("Not an option line: " + line)
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
                raise TypeError("Illegal option line: " + line)


class Touchstone:
    FIELD_ORDER = ("11", "21", "12", "22")

    def __init__(self, filename: str):
        self.filename = filename
        self.sdata = [[], [], [], []]  # at max 4 data pairs
        self.comments = []
        self.opts = Options()

    @property
    def s11data(self) -> list:
        return self.s("11")

    @property
    def s12data(self) -> list:
        return self.s("12")

    @property
    def s21data(self) -> list:
        return self.s("21")

    @property
    def s22data(self) -> list:
        return self.s("22")

    @property
    def r(self) -> int:
        return self.opts.resistance

    def s(self, name: str) -> list:
        return self.sdata[Touchstone.FIELD_ORDER.index(name)]

    def _parse_comments(self, fp) -> str:
        for line in fp:
            line = line.strip()
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
                next(data_list).append(Datapoint(freq, float(v), float(next(vals))))
            if self.opts.format == "ma":
                z = cmath.rect(float(v), math.radians(float(next(vals))))
                next(data_list).append(Datapoint(freq, z.real, z.imag))
            if self.opts.format == "db":
                z = cmath.rect(math.exp(float(v) / 20), math.radians(float(next(vals))))
                next(data_list).append(Datapoint(freq, z.real, z.imag))

    def load(self):
        logger.info("Attempting to open file %s", self.filename)
        try:
            with open(self.filename) as infile:
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
            for line in file:
                line = line.strip()
                # ignore empty lines (even if not specified)
                if line == "":
                    continue
                # accept comment lines after header
                if line.startswith("!"):
                    logger.warning("Comment after header: %s", line)
                    self.comments.append(line)
                    continue

                # ignore comments at data end
                data = line.split('!')[0]
                data = data.split()
                freq, data = round(float(data[0]) * self.opts.factor), data[1:]
                data_len = len(data)

                # consistency checks
                if freq <= prev_freq:
                    logger.warning("Frequency not ascending: %s", line)
                    need_reorder = True
                prev_freq = freq

                if prev_len == 0:
                    prev_len = data_len
                    if data_len % 2:
                        raise TypeError("Data values aren't pairs: " + line)
                elif data_len != prev_len:
                    raise TypeError("Inconsistent number of pairs: " + line)

                self._append_line_data(freq, data)
            if need_reorder:
                logger.warning("Reordering data")
                for datalist in self.sdata:
                    datalist.sort(key=attrgetter("freq"))
