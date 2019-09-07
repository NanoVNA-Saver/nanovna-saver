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
from typing import List

Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class Touchstone:
    s11data: List[Datapoint] = []
    s21data: List[Datapoint] = []

    filename = ""

    def __init__(self, filename):
        self.filename = filename

    def load(self):
        self.s11data = []
        self.s21data = []
        factor = 1
        try:
            file = open(self.filename, "r")

            lines = file.readlines()
            parsed_header = False
            for l in lines:
                l = l.strip()
                if l.startswith("!"):
                    continue
                if l.startswith("#") and not parsed_header:
                    # Check that this is a valid header
                    if l == "# Hz S RI R 50":
                        parsed_header = True
                        factor = 1
                        continue
                    elif l == "# kHz S RI R 50":
                        parsed_header = True
                        factor = 10**3
                        continue
                    elif l == "# MHz S RI R 50":
                        parsed_header = True
                        factor = 10**6
                        continue
                    elif l == "# GHz S RI R 50":
                        parsed_header = True
                        factor = 10**9
                        continue
                    else:
                        # This is some other comment line
                        continue
                if not parsed_header:
                    print("Warning: Read line without having read header: " + l)
                    continue

                try:
                    values = l.split(maxsplit=5)
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
                except ValueError as e:
                    print("Error parsing line " + l + " : " + str(e))

            file.close()
        except IOError as e:
            print("Failed to open " + self.filename)
        return

    def setFilename(self, filename):
        self.filename = filename
