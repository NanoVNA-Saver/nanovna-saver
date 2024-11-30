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
import logging
from typing import Callable

import numpy as np
from PyQt6 import QtWidgets

from NanoVNASaver.Analysis.Base import Analysis, QHLine
from NanoVNASaver.Formatting import (
    format_frequency,
    format_gain,
    format_resistance,
    format_vswr,
)

logger = logging.getLogger(__name__)


class SimplePeakSearchAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self.label["peak_freq"] = QtWidgets.QLabel()
        self.label["peak_db"] = QtWidgets.QLabel()

        self.button = {
            "vswr": QtWidgets.QRadioButton("VSWR"),
            "resistance": QtWidgets.QRadioButton("Resistance"),
            "reactance": QtWidgets.QRadioButton("Reactance"),
            "gain": QtWidgets.QRadioButton("S21 Gain"),
            "peak_h": QtWidgets.QRadioButton("Highest value"),
            "peak_l": QtWidgets.QRadioButton("Lowest value"),
            "move_marker": QtWidgets.QCheckBox(),
        }

        self.button["gain"].setChecked(True)
        self.button["peak_h"].setChecked(True)

        self.btn_group = {
            "data": QtWidgets.QButtonGroup(),
            "peak": QtWidgets.QButtonGroup(),
        }

        for btn in ("vswr", "resistance", "reactance", "gain"):
            self.btn_group["data"].addButton(self.button[btn])
        self.btn_group["peak"].addButton(self.button["peak_h"])
        self.btn_group["peak"].addButton(self.button["peak_l"])

        layout = self.layout
        layout.addRow(self.label["titel"])
        layout.addRow(QHLine())
        layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        layout.addRow("Data source", self.button["vswr"])
        layout.addRow("", self.button["resistance"])
        layout.addRow("", self.button["reactance"])
        layout.addRow("", self.button["gain"])
        layout.addRow(QHLine())
        layout.addRow("Peak type", self.button["peak_h"])
        layout.addRow("", self.button["peak_l"])
        layout.addRow(QHLine())
        layout.addRow("Move marker to peak", self.button["move_marker"])
        layout.addRow(QHLine())
        layout.addRow(self.label["result"])
        layout.addRow("Peak frequency:", self.label["peak_freq"])
        layout.addRow("Peak value:", self.label["peak_db"])

        self.set_titel("Simple peak search")

    def runAnalysis(self):
        if not self.app.data.s11:
            return

        s11 = self.app.data.s11
        data, fmt_fnc = self.data_and_format()

        if self.button["peak_l"].isChecked():
            idx_peak = np.argmin(data)
        else:
            self.button["peak_h"].setChecked(True)
            idx_peak = np.argmax(data)

        self.label["peak_freq"].setText(format_frequency(s11[idx_peak].freq))
        self.label["peak_db"].setText(fmt_fnc(data[idx_peak]))

        if self.button["move_marker"].isChecked() and self.app.markers:
            self.app.markers[0].setFrequency(f"{s11[idx_peak].freq}")

    def data_and_format(self) -> tuple[list[float], Callable]:
        s11 = self.app.data.s11
        s21 = self.app.data.s21

        if not s21:
            self.button["gain"].setEnabled(False)
            if self.button["gain"].isChecked():
                self.button["vswr"].setChecked(True)
        else:
            self.button["gain"].setEnabled(True)

        if self.button["gain"].isChecked():
            return ([d.gain for d in s21], format_gain)
        if self.button["resistance"].isChecked():
            return ([d.impedance().real for d in s11], format_resistance)
        if self.button["reactance"].isChecked():
            return ([d.impedance().imag for d in s11], format_resistance)
        # default
        return ([d.vswr for d in s11], format_vswr)
