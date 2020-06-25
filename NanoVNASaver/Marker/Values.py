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

from typing import List, NamedTuple
from NanoVNASaver.RFTools import Datapoint


class Label(NamedTuple):
    label_id: str
    name: str
    description: str
    default_active: bool


TYPES = (
    Label("actualfreq", "Frequency", "Actual frequency", True),
    Label("impedance", "Impedance", "Impedance", True),
    Label("admittance", "Admittance", "Admittance", False),
    Label("serr", "Series R", "Series R", False),
    Label("serlc", "Series X", "Series equivalent L/C", False),
    Label("serl", "Series L", "Series equivalent L", True),
    Label("serc", "Series C", "Series equivalent C", True),
    Label("parr", "Parallel R", "Parallel R", True),
    Label("parlc", "Parallel X", "Parallel equivalent L/C", True),
    Label("parl", "Parallel L", "Parallel equivalent L", False),
    Label("parc", "Parallel C", "Parallel equivalent C", False),
    Label("vswr", "VSWR", "VSWR", True),
    Label("returnloss", "Return loss", "Return loss", True),
    Label("s11mag", "|S11|", "S11 Magnitude", False),
    Label("s11q", "Quality factor", "S11 Quality factor", True),
    Label("s11z", "S11 |Z|", "S11 Z Magnitude", False),
    Label("s11phase", "S11 Phase", "S11 Phase", True),
    Label("s11polar", "S11 Polar", "S11 Polar", False),
    Label("s11groupdelay", "S11 Group Delay", "S11 Group Delay", False),
    Label("s21gain", "S21 Gain", "S21 Gain", True),
    Label("s21mag", "|S21|", "S21 Magnitude", False),
    Label("s21phase", "S21 Phase", "S21 Phase", True),
    Label("s21polar", "S21 Polar", "S21 Polar", False),
    Label("s21groupdelay", "S21 Group Delay", "S21 Group Delay", False),
)


def default_label_ids() -> str:
    return [l.label_id for l in TYPES if l.default_active]


class Value():
    """Contains the data area to calculate marker values from"""
    def __init__(self, freq: int = 0,
                 s11data: List[Datapoint] = None,
                 s21data: List[Datapoint] = None):
        self.freq = freq
        self.s11data = [] if s11data is None else s11data[:]
        self.s21data = [] if s21data is None else s21data[:]

    def store(self, index: int,
              s11data: List[Datapoint],
              s21data: List[Datapoint]):
        # handle boundaries
        if index == 0:
            index = 1
            s11data = [s11data[0], ] + s11data
            if s21data:
                s21data = [s21data[0], ] + s21data
        if index == len(s11data):
            s11data = s11data + [s11data[-1], ]
            if s21data:
                s21data = s21data + [s21data[-1], ]
        self.freq = s11data[1].freq
        self.s11data = s11data[index-1:index+2]
        if s21data:
            self.s21data = s21data[index-1:index+2]
