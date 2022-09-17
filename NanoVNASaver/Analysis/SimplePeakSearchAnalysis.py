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

from PyQt5 import QtWidgets
import numpy as np

from NanoVNASaver.Analysis.Base import Analysis, QHLine
from NanoVNASaver.Formatting import format_frequency


logger = logging.getLogger(__name__)


class SimplePeakSearchAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)
        self._widget = QtWidgets.QWidget()
        outer_layout = QtWidgets.QFormLayout()
        self._widget.setLayout(outer_layout)

        self.rbtn_data_group = QtWidgets.QButtonGroup()
        self.rbtn_data_vswr = QtWidgets.QRadioButton("VSWR")
        self.rbtn_data_resistance = QtWidgets.QRadioButton("Resistance")
        self.rbtn_data_reactance = QtWidgets.QRadioButton("Reactance")
        self.rbtn_data_s21_gain = QtWidgets.QRadioButton("S21 Gain")
        self.rbtn_data_group.addButton(self.rbtn_data_vswr)
        self.rbtn_data_group.addButton(self.rbtn_data_resistance)
        self.rbtn_data_group.addButton(self.rbtn_data_reactance)
        self.rbtn_data_group.addButton(self.rbtn_data_s21_gain)

        self.rbtn_data_s21_gain.setChecked(True)

        self.rbtn_peak_group = QtWidgets.QButtonGroup()
        self.rbtn_peak_positive = QtWidgets.QRadioButton("Highest value")
        self.rbtn_peak_negative = QtWidgets.QRadioButton("Lowest value")
        self.rbtn_peak_group.addButton(self.rbtn_peak_positive)
        self.rbtn_peak_group.addButton(self.rbtn_peak_negative)

        self.rbtn_peak_positive.setChecked(True)

        self.checkbox_move_marker = QtWidgets.QCheckBox()

        outer_layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        outer_layout.addRow("Data source", self.rbtn_data_vswr)
        outer_layout.addRow("", self.rbtn_data_resistance)
        outer_layout.addRow("", self.rbtn_data_reactance)
        outer_layout.addRow("", self.rbtn_data_s21_gain)
        outer_layout.addRow(QHLine())
        outer_layout.addRow("Peak type", self.rbtn_peak_positive)
        outer_layout.addRow("", self.rbtn_peak_negative)
        outer_layout.addRow(QHLine())
        outer_layout.addRow("Move marker to peak", self.checkbox_move_marker)
        outer_layout.addRow(QHLine())

        outer_layout.addRow(QtWidgets.QLabel("<b>Results</b>"))

        self.peak_frequency = QtWidgets.QLabel()
        self.peak_value = QtWidgets.QLabel()

        outer_layout.addRow("Peak frequency:", self.peak_frequency)
        outer_layout.addRow("Peak value:", self.peak_value)

    def runAnalysis(self):
        if not self.app.data.s11:
            return
        s11 = self.app.data.s11
        s21 = self.app.data.s21

        if self.rbtn_data_vswr.isChecked():
            suffix = ""
            data = [d.vswr for d in s11]
        elif self.rbtn_data_resistance.isChecked():
            suffix = " \N{OHM SIGN}"
            data = [d.impedance().real for d in s11]
        elif self.rbtn_data_reactance.isChecked():
            suffix = " \N{OHM SIGN}"
            data = [d.impedance().imag for d in s11]
        elif self.rbtn_data_s21_gain.isChecked():
            suffix = " dB"
            data = [d.gain for d in s21]
        else:
            logger.warning("Searching for peaks on unknown data")
            return

        if len(data) == 0:
            return

        if self.rbtn_peak_positive.isChecked():
            idx_peak = np.argmax(data)
        elif self.rbtn_peak_negative.isChecked():
            idx_peak = np.argmin(data)
        else:
            # Both is not yet in
            logger.warning(
                "Searching for peaks,"
                " but neither looking at positive nor negative?")
            return

        self.peak_frequency.setText(
            format_frequency(self.app.data.s11[idx_peak].freq))
        self.peak_value.setText(str(round(data[idx_peak], 3)) + suffix)

        if self.checkbox_move_marker.isChecked() and self.app.markers:
            self.app.markers[0].setFrequency(
                str(self.app.data.s11[idx_peak].freq))
            self.app.markers[0].frequencyInput.setText(
                format_frequency(self.app.data.s11[idx_peak].freq))
