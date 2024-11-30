#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020 Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
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
import csv
import logging
import os

from PyQt6 import QtWidgets

import NanoVNASaver.AnalyticTools as At
from NanoVNASaver.Analysis.Base import Analysis, QHLine
from NanoVNASaver.Formatting import format_frequency, format_resistance
from NanoVNASaver.RFTools import reflection_coefficient

logger = logging.getLogger(__name__)


def format_resistence_neg(x):
    return format_resistance(x, allow_negative=True)


def vswr_transformed(z, ratio=49) -> float:
    refl = reflection_coefficient(z / ratio)
    mag = abs(refl)
    return 1 if mag == 1 else (1 + mag) / (1 - mag)


class ResonanceAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)
        self.crossings: list[int] = []
        self.filename = ""
        self._widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QFormLayout()
        self._widget.setLayout(self.layout)
        self.input_description = QtWidgets.QLineEdit("")
        self.checkbox_move_marker = QtWidgets.QCheckBox()
        self.layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        self.layout.addRow("Description", self.input_description)
        self.layout.addRow(QHLine())

        self.layout.addRow(QHLine())

        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        self.layout.addRow(self.results_label)

    def _get_data(self, index):
        s11 = self.app.data.s11
        my_data = {
            "freq": s11[index].freq,
            "s11": s11[index].z,
            "lambda": s11[index].wavelength,
            "impedance": s11[index].impedance(),
            "vswr": s11[index].vswr,
        }
        my_data["vswr_49"] = vswr_transformed(my_data["impedance"], 49)
        my_data["vswr_4"] = vswr_transformed(my_data["impedance"], 4)
        my_data["r"] = my_data["impedance"].real
        my_data["x"] = my_data["impedance"].imag

        return my_data

    def runAnalysis(self):
        self.reset()
        self.filename = (
            os.path.join("/tmp/", f"{self.input_description.text()}.csv")
            if self.input_description.text()
            else ""
        )

        results_header = self.layout.indexOf(self.results_label)
        logger.debug(
            "Results start at %d, out of %d",
            results_header,
            self.layout.rowCount(),
        )

        for _ in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)

        self.crossings = sorted(
            set(At.zero_crossings([d.phase for d in self.app.data.s11]))
        )
        logger.debug("Found %d sections ", len(self.crossings))
        if not self.crossings:
            self.layout.addRow(QtWidgets.QLabel("No resonance found"))
            return

        self.do_resonance_analysis()

    def do_resonance_analysis(self):
        extended_data = []
        for crossing in self.crossings:
            extended_data.append(self._get_data(crossing))
            self.layout.addRow(
                "Resonance",
                QtWidgets.QLabel(
                    format_frequency(self.app.data.s11[crossing].freq)
                ),
            )
            self.layout.addWidget(QHLine())
        # Remove the final separator line
        self.layout.removeRow(self.layout.rowCount() - 1)
        if self.filename and extended_data:
            with open(
                self.filename, "w", encoding="utf-8", newline=""
            ) as csvfile:
                fieldnames = extended_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in extended_data:
                    writer.writerow(row)
