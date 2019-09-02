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
    s11data : List[Datapoint] = []
    s21data : List[Datapoint] = []

    filename = ""

    def __init__(self, filename):
        self.filename = filename

    def load(self):
        self.s11data = []
        self.s21data = []
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
                        continue
                    else:
                        # This is some other comment line
                        continue
                if not parsed_header:
                    print("Warning: Read line without having read header: " + l)
                    continue

                try:
                    if l.count(" ") > 2:
                        freq, re11, im11, re21, im21, _ = l.split(maxsplit=5)
                        freq = int(freq)
                        re11 = float(re11)
                        im11 = float(im11)
                        re21 = float(re21)
                        im21 = float(im21)
                        self.s11data.append(Datapoint(freq, re11, im11))
                        self.s21data.append(Datapoint(freq, re21, im21))
                    elif l.count(" ") == 2:
                        freq, re11, im11 = l.split()
                        freq = int(freq)
                        re11 = float(re11)
                        im11 = float(im11)
                        self.s11data.append(Datapoint(freq, re11, im11))
                    else:
                        print("Warning: Read a line with not enough values: " + l)
                        continue
                except ValueError as e:
                    print("Error parsing line " + l + " : " + str(e))

            file.close()
        except IOError as e:
            print("Failed to open " + self.filename)
        return

    def setFilename(self, filename):
        self.filename = filename