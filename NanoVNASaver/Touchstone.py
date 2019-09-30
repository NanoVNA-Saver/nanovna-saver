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
import logging
import math
import re
from typing import List

Datapoint = collections.namedtuple('Datapoint', 'freq re im')

logger = logging.getLogger(__name__)


class Touchstone:
    s11data: List[Datapoint] = []
    s21data: List[Datapoint] = []

    filename = ""

    def __init__(self, filename):
        self.filename = filename

    def load(self):
        self.s11data = []
        self.s21data = []

        realimaginary = False
        magnitudeangle = False

        factor = 1
        try:
            logger.info("Attempting to open file %s", self.filename)
            file = open(self.filename, "r")

            lines = file.readlines()
            parsed_header = False
            for line in lines:
                line = line.strip()
                if line.startswith("!"):
                    logger.info(line)
                    continue
                if line.startswith("#") and not parsed_header:
                    pattern = "^# (.?HZ) (S )?RI( R 50)?$"
                    match = re.match(pattern, line.upper())
                    if match:
                        logger.debug("Found header for RealImaginary and %s", match.group(1))
                        match = match.group(1)
                        parsed_header = True
                        realimaginary = True
                        if match == "HZ":
                            factor = 1
                        elif match == "KHZ":
                            factor = 10**3
                        elif match == "MHZ":
                            factor = 10**6
                        elif match == "GHZ":
                            factor = 10**9
                        else:
                            factor = 10**9  # Default Touchstone frequency unit is GHz
                        continue

                    pattern = "^# (.?HZ) (S )?MA( R 50)?$"
                    match = re.match(pattern, line.upper())
                    if match:
                        logger.debug("Found header for MagnitudeAngle and %s", match.group(1))
                        match = match.group(1)
                        parsed_header = True
                        magnitudeangle = True
                        if match == "HZ":
                            factor = 1
                        elif match == "KHZ":
                            factor = 10**3
                        elif match == "MHZ":
                            factor = 10**6
                        elif match == "GHZ":
                            factor = 10**9
                        else:
                            factor = 10**9  # Default Touchstone frequency unit is GHz
                        continue

                    # else:
                    # This is some other comment line
                    logger.debug("Comment line: %s", line)
                    continue
                if not parsed_header:
                    logger.warning("Read line without having read header: %s", line)
                    continue

                try:
                    if realimaginary:
                        values = line.split(maxsplit=5)
                        freq = values[0]
                        re11 = values[1]
                        im11 = values[2]
                        freq = int(float(freq) * factor)
                        re11 = float(re11)
                        im11 = float(im11)
                        self.s11data.append(Datapoint(freq, re11, im11))
                        if len(values) > 3:
                            re21 = values[3]
                            im21 = values[4]
                            re21 = float(re21)
                            im21 = float(im21)
                            self.s21data.append(Datapoint(freq, re21, im21))
                    elif magnitudeangle:
                        values = line.split(maxsplit=5)
                        freq = values[0]
                        mag11 = float(values[1])
                        angle11 = float(values[2])
                        freq = int(float(freq) * factor)
                        re11 = float(mag11) * math.cos(math.radians(angle11))
                        im11 = float(mag11) * math.sin(math.radians(angle11))
                        self.s11data.append(Datapoint(freq, re11, im11))
                        if len(values) > 3:
                            mag21 = float(values[3])
                            angle21 = float(values[4])
                            re21 = float(mag21) * math.cos(math.radians(angle21))
                            im21 = float(mag21) * math.sin(math.radians(angle21))
                            self.s21data.append(Datapoint(freq, re21, im21))

                        continue
                except ValueError as e:
                    logger.exception("Failed to parse line: %s (%s)", line, e)

            file.close()
        except IOError as e:
            logger.exception("Failed to open %s: %s", self.filename, e)
        return

    def setFilename(self, filename):
        self.filename = filename
