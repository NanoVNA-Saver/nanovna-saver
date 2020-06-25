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
import logging

from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.Formatting import (
    format_frequency_short, format_frequency_sweep,
)

logger = logging.getLogger(__name__)


class SweepSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()

        self.app = app
        self.setWindowTitle("Sweep settings")
        self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        title_box = QtWidgets.QGroupBox("Sweep name")
        title_layout = QtWidgets.QFormLayout(title_box)
        self.sweep_title_input = QtWidgets.QLineEdit()
        title_layout.addRow("Sweep name", self.sweep_title_input)
        title_button_layout = QtWidgets.QHBoxLayout()
        btn_set_sweep_title = QtWidgets.QPushButton("Set")
        btn_set_sweep_title.clicked.connect(
            lambda: self.app.setSweepTitle(self.sweep_title_input.text()))
        btn_reset_sweep_title = QtWidgets.QPushButton("Reset")
        btn_reset_sweep_title.clicked.connect(lambda: self.app.setSweepTitle(""))
        title_button_layout.addWidget(btn_set_sweep_title)
        title_button_layout.addWidget(btn_reset_sweep_title)
        title_layout.addRow(title_button_layout)
        layout.addWidget(title_box)

        settings_box = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout(settings_box)

        self.single_sweep_radiobutton = QtWidgets.QRadioButton("Single sweep")
        self.continuous_sweep_radiobutton = QtWidgets.QRadioButton("Continuous sweep")
        self.averaged_sweep_radiobutton = QtWidgets.QRadioButton("Averaged sweep")

        settings_layout.addWidget(self.single_sweep_radiobutton)
        self.single_sweep_radiobutton.setChecked(True)
        settings_layout.addWidget(self.continuous_sweep_radiobutton)
        settings_layout.addWidget(self.averaged_sweep_radiobutton)

        self.averages = QtWidgets.QLineEdit("3")
        self.truncates = QtWidgets.QLineEdit("0")

        settings_layout.addRow("Number of measurements to average", self.averages)
        settings_layout.addRow("Number to discard", self.truncates)
        settings_layout.addRow(
            QtWidgets.QLabel(
                "Averaging allows discarding outlying samples to get better averages."))
        settings_layout.addRow(
            QtWidgets.QLabel("Common values are 3/0, 5/2, 9/4 and 25/6."))
        
        self.s21att = QtWidgets.QLineEdit("0")

        settings_layout.addRow(QtWidgets.QLabel(""))
        settings_layout.addRow(QtWidgets.QLabel("Some times when you measure amplifiers you need to use an attenuator"))
        settings_layout.addRow(QtWidgets.QLabel("in line with  the S21 input (CH1) here you can specify it."))

        settings_layout.addRow("Attenuator in port CH1 (s21) in dB", self.s21att)
        settings_layout.addRow(QtWidgets.QLabel("Common values with un-un are 16.9 (49:1 2450) 9.54 (9:1 450)"))
        self.continuous_sweep_radiobutton.toggled.connect(
            lambda: self.app.worker.setContinuousSweep(
                self.continuous_sweep_radiobutton.isChecked()))
        self.averaged_sweep_radiobutton.toggled.connect(self.updateAveraging)
        self.averages.textEdited.connect(self.updateAveraging)
        self.truncates.textEdited.connect(self.updateAveraging)
        self.s21att.textEdited.connect(self.setS21Attenuator)
        layout.addWidget(settings_box)

        band_sweep_box = QtWidgets.QGroupBox("Sweep band")
        band_sweep_layout = QtWidgets.QFormLayout(band_sweep_box)

        self.band_list = QtWidgets.QComboBox()
        self.band_list.setModel(self.app.bands)
        self.band_list.currentIndexChanged.connect(self.updateCurrentBand)

        band_sweep_layout.addRow("Select band", self.band_list)

        self.band_pad_group = QtWidgets.QButtonGroup()
        self.band_pad_0 = QtWidgets.QRadioButton("None")
        self.band_pad_10 = QtWidgets.QRadioButton("10%")
        self.band_pad_25 = QtWidgets.QRadioButton("25%")
        self.band_pad_100 = QtWidgets.QRadioButton("100%")
        self.band_pad_0.setChecked(True)
        self.band_pad_group.addButton(self.band_pad_0)
        self.band_pad_group.addButton(self.band_pad_10)
        self.band_pad_group.addButton(self.band_pad_25)
        self.band_pad_group.addButton(self.band_pad_100)
        self.band_pad_group.buttonClicked.connect(self.updateCurrentBand)
        band_sweep_layout.addRow("Pad band limits", self.band_pad_0)
        band_sweep_layout.addRow("", self.band_pad_10)
        band_sweep_layout.addRow("", self.band_pad_25)
        band_sweep_layout.addRow("", self.band_pad_100)

        self.band_limit_label = QtWidgets.QLabel()

        band_sweep_layout.addRow(self.band_limit_label)

        btn_set_band_sweep = QtWidgets.QPushButton("Set band sweep")
        btn_set_band_sweep.clicked.connect(self.setBandSweep)
        band_sweep_layout.addRow(btn_set_band_sweep)

        self.updateCurrentBand()

        layout.addWidget(band_sweep_box)

    def updateCurrentBand(self):
        index_start = self.band_list.model().index(self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(index_stop, QtCore.Qt.ItemDataRole).value())

        if self.band_pad_10.isChecked():
            padding = 10
        elif self.band_pad_25.isChecked():
            padding = 25
        elif self.band_pad_100.isChecked():
            padding = 100
        else:
            padding = 0

        if padding > 0:
            span = stop - start
            start -= round(span * padding / 100)
            start = max(1, start)
            stop += round(span * padding / 100)

        self.band_limit_label.setText(
            f"Sweep span: {format_frequency_short(start)}"
            f" to {format_frequency_short(stop)}")

    def setS21Attenuator(self):
        
        try:
            s21att = float(self.s21att.text())
        except:
            s21att = 0

        if (s21att < 0):
            logger.warning("Values for attenuator are absolute and with no minus sign, resetting.")
            self.s21att.setText("0")
        else:
            logger.info("Setting an attenuator of %.2f dB inline with the CH1/S21 input", s21att)
            self.app.s21att = s21att



    def setBandSweep(self):
        index_start = self.band_list.model().index(self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(index_stop, QtCore.Qt.ItemDataRole).value())

        if self.band_pad_10.isChecked():
            padding = 10
        elif self.band_pad_25.isChecked():
            padding = 25
        elif self.band_pad_100.isChecked():
            padding = 100
        else:
            padding = 0

        if padding > 0:
            span = stop - start
            start -= round(span * padding / 100)
            start = max(1, start)
            stop += round(span * padding / 100)

        self.app.sweepStartInput.setText(format_frequency_sweep(start))
        self.app.sweepEndInput.setText(format_frequency_sweep(stop))
        self.app.sweepEndInput.textEdited.emit(self.app.sweepEndInput.text())

    def updateAveraging(self):
        self.app.worker.setAveraging(self.averaged_sweep_radiobutton.isChecked(),
                                     self.averages.text(),
                                     self.truncates.text())
