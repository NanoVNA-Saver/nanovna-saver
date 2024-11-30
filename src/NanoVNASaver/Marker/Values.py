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

from typing import NamedTuple

from NanoVNASaver.RFTools import Datapoint


class Label(NamedTuple):
    label_id: str
    name: str
    description: str
    default_active: bool


TYPES = (
    Label("actualfreq", "Frequency", "Actual frequency", True),
    Label("lambda", "Wavelength", "Wavelength", False),
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
    Label("s21magshunt", "S21 |Z| shunt", "S21 Z Magnitude shunt", False),
    Label("s21magseries", "S21 |Z| series", "S21 Z Magnitude series", False),
    Label("s21realimagshunt", "S21 R+jX shunt", "S21 Z Real+Imag shunt", False),
    Label(
        "s21realimagseries", "S21 R+jX series", "S21 Z Real+Imag series", False
    ),
)


def default_label_ids() -> str:
    return [label.label_id for label in TYPES if label.default_active]


class Value:
    """Contains the data area to calculate marker values from"""

    def __init__(
        self,
    ):
        self.freq: int = 0
        self.s11: list[Datapoint] = []
        self.s21: list[Datapoint] = []

    def store(self, index: int, s11: list[Datapoint], s21: list[Datapoint]):
        # handle boundaries
        if index == 0:
            index = 1
            s11 = [
                s11[0],
            ] + s11
            if s21:
                s21 = [
                    s21[0],
                ] + s21
        if index == len(s11):
            s11 += [
                s11[-1],
            ]
            if s21:
                s21 += [
                    s21[-1],
                ]

        self.freq = s11[1].freq
        self.s11 = s11[index - 1 : index + 2]
        if s21:
            self.s21 = s21[index - 1 : index + 2]
