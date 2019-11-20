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
from .RFTools import Datapoint

logger = logging.getLogger(__name__)


class Touchstone:
    s11data: List[Datapoint] = []
    s21data: List[Datapoint] = []
    comments = []
    filename = ""

    def __init__(self, filename):
        self.filename = filename

    def load(self):
        self.s11data = []
        self.s21data = []

        realimaginary = False
        magnitudeangle = False
        dbangle = False

        factor = 1
        try:
            logger.info("Attempting to open file %s", self.filename)
            file = open(self.filename, "r")

            lines = file.readlines()
            parsed_header = False
            for line in lines:
                line = line.strip()
                if len(line) < 5:
                  continue
                if line.startswith("!"):
                    logger.info(line)
                    self.comments.append(line)
                    continue
                if line.startswith("#") and not parsed_header:
                    pattern = "^\s*#\s*(.?HZ)(?:\s+S)?(:?\s+(DB|MA|RI))(:?\s+R\s+([^\s]+))?\s*$"
                    #https://github.com/mihtjel/nanovna-saver/issues/99
                    match = re.match(pattern, line.upper())
                    try:
                        snp_format = match.group(3)
                        match = match.group(1)
                        parsed_header = True
                    except:
                        snp_format = "Unknown format header"
                        logger.debug("Comment line: %s", line)
                        continue
                    if snp_format == "RI":
                        logger.debug("Found header for RealImaginary and %s", match)
                        realimaginary = True
                    elif snp_format == "MA":
                          logger.debug("Found header for MagnitudeAngle and %s", match)
                          magnitudeangle = True
                    elif snp_format == "DB":
                          logger.debug("Found header for dBAngle and %s", match)
                          dbangle = True
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
                    elif magnitudeangle or dbangle:
                        values = line.split(maxsplit=5)
                        freq = values[0]
                        if dbangle:
                            #Transform db2mag
                            mag11 = 10**(float(values[1])/20)
                        else:
                            mag11 = float(values[1])
                        angle11 = float(values[2])
                        freq = int(float(freq) * factor)
                        re11 = float(mag11) * math.cos(math.radians(angle11))
                        im11 = float(mag11) * math.sin(math.radians(angle11))
                        self.s11data.append(Datapoint(freq, re11, im11))
                        if len(values) > 3:
                            if dbangle:
                                #Transform db2mag
                                mag21 = 10**(float(values[3])/20)
                            else:
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
