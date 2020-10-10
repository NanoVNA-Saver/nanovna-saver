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
from functools import partial
from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.Formatting import (
    format_frequency_short, format_frequency_sweep,
)
from NanoVNASaver.Settings.Sweep import SweepMode

logger = logging.getLogger(__name__)


class SweepSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app
        self.padding = 0

        self.setWindowTitle("Sweep settings")
        self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.title_box())
        layout.addWidget(self.settings_box())
        layout.addWidget(self.sweep_box())
        self.update_band()

    def title_box(self):
        box = QtWidgets.QGroupBox("Sweep name")
        layout = QtWidgets.QFormLayout(box)

        input_title = QtWidgets.QLineEdit(self.app.sweep.properties.name)
        input_title.editingFinished.connect(
            lambda: self.update_title(input_title.text()))
        layout.addRow(input_title)
        return box

    def settings_box(self) -> 'QtWidgets.QWidget':
        box = QtWidgets.QGroupBox("Settings")
        layout = QtWidgets.QFormLayout(box)

        # Sweep Mode
        radio_button = QtWidgets.QRadioButton("Single sweep")
        radio_button.setChecked(
            self.app.sweep.properties.mode == SweepMode.SINGLE)
        radio_button.clicked.connect(
            lambda: self.update_mode(SweepMode.SINGLE))
        layout.addWidget(radio_button)

        radio_button = QtWidgets.QRadioButton("Continous sweep")
        radio_button.setChecked(
            self.app.sweep.properties.mode == SweepMode.CONTINOUS)
        radio_button.clicked.connect(
            lambda: self.update_mode(SweepMode.CONTINOUS))
        layout.addWidget(radio_button)

        radio_button = QtWidgets.QRadioButton("Averaged sweep")
        radio_button.setChecked(
            self.app.sweep.properties.mode == SweepMode.AVERAGE)
        radio_button.clicked.connect(
            lambda: self.update_mode(SweepMode.AVERAGE))
        layout.addWidget(radio_button)

        # Log sweep
        label = QtWidgets.QLabel(
            "Logarithmic sweeping changes the step width in each segment"
            " in logarithmical manner. Useful in conjunction with small"
            " amount of datapoints and many segments. Step display in"
            " SweepControl cannot reflect this currently.")
        label.setWordWrap(True)
        layout.addRow(label)
        checkbox = QtWidgets.QCheckBox("Logarithmic sweep")
        checkbox.setCheckState(self.app.sweep.properties.logarithmic)
        checkbox.toggled.connect(
            lambda: self.update_logarithmic(checkbox.isChecked()))
        layout.addWidget(checkbox)

        # Averaging
        label = QtWidgets.QLabel(
            "Averaging allows discarding outlying samples to get better"
            " averages. Common values are 3/0, 5/2, 9/4 and 25/6.")
        label.setWordWrap(True)
        layout.addRow(label)
        averages = QtWidgets.QLineEdit(
            str(self.app.sweep.properties.averages[0]))
        truncates = QtWidgets.QLineEdit(
            str(self.app.sweep.properties.averages[1]))
        averages.editingFinished.connect(
            lambda: self.update_averaging(averages, truncates))
        truncates.editingFinished.connect(
            lambda: self.update_averaging(averages, truncates))
        layout.addRow("Number of measurements to average", averages)
        layout.addRow("Number to discard", truncates)

        # TODO: is this more a device than a sweep property?
        label = QtWidgets.QLabel(
            "Some times when you measure amplifiers you need to use an"
            " attenuator in line with  the S21 input (CH1) here you can"
            " specify it.")
        label.setWordWrap(True)
        layout.addRow(label)

        input_att = QtWidgets.QLineEdit(str(self.app.s21att))
        input_att.editingFinished.connect(
            lambda: self.update_attenuator(input_att))
        layout.addRow("Attenuator in port CH1 (s21) in dB", input_att)
        return box

    def sweep_box(self) -> 'QtWidgets.QWidget':
        box = QtWidgets.QGroupBox("Sweep band")
        layout = QtWidgets.QFormLayout(box)

        self.band_list = QtWidgets.QComboBox()
        self.band_list.setModel(self.app.bands)
        # pylint: disable=unnecessary-lambda
        self.band_list.currentIndexChanged.connect(lambda: self.update_band())
        layout.addRow("Select band", self.band_list)

        for raw_label, btn_label, value in (("Pad band limits", "None", 0),
                                            ("", "10%", 10),
                                            ("", "25%", 25),
                                            ("", "100%", 100),):
            radio_button = QtWidgets.QRadioButton(btn_label)
            radio_button.setChecked(self.padding == value)
            radio_button.clicked.connect(partial(self.update_padding, value))
            layout.addRow(raw_label, radio_button)

        self.band_label = QtWidgets.QLabel()
        layout.addRow(self.band_label)

        btn_set_band_sweep = QtWidgets.QPushButton("Set band sweep")
        btn_set_band_sweep.clicked.connect(lambda: self.update_band(True))
        layout.addRow(btn_set_band_sweep)
        return box

    def update_band(self, apply: bool = False):
        logger.debug("update_band(%s)", apply)
        index_start = self.band_list.model().index(self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(index_stop, QtCore.Qt.ItemDataRole).value())

        if self.padding > 0:
            span = stop - start
            start -= round(span * self.padding / 100)
            start = max(1, start)
            stop += round(span * self.padding / 100)

        self.band_label.setText(
            f"Sweep span: {format_frequency_short(start)}"
            f" to {format_frequency_short(stop)}")

        if not apply:
            return

        self.app.sweep_control.input_start.setText(
            format_frequency_sweep(start))
        self.app.sweep_control.input_end.setText(
            format_frequency_sweep(stop))
        self.app.sweep_control.input_end.textEdited.emit(
            self.app.sweep_control.input_end.text())

    def update_attenuator(self, value: 'QtWidgets.QLineEdit'):
        try:
            att = float(value.text())
            assert att >= 0
        except (ValueError, AssertionError):
            logger.warning("Values for attenuator are absolute and with no"
                           " minus sign, resetting.")
            att = 0
        logger.debug("Attenuator %sdB inline with S21 input", att)
        value.setText(str(att))
        self.app.s21att = att

    def update_averaging(self,
                         averages: 'QtWidgets.QLineEdit',
                         truncs: 'QtWidgets.QLineEdit'):
        try:
            amount = int(averages.text())
            truncates = int(truncs.text())
            assert amount > 0
            assert truncates >= 0
            assert amount > truncates
        except (AssertionError, ValueError):
            logger.warning("Illegal averaging values, set default")
            amount = 3
            truncates = 0
        logger.debug("update_averaging(%s, %s)", amount, truncates)
        averages.setText(str(amount))
        truncs.setText(str(truncates))
        with self.app.sweep.lock:
            self.app.sweep.properties.averages = (amount, truncates)

    def update_logarithmic(self, logarithmic: bool):
        logger.debug("update_logarithmic(%s)", logarithmic)
        with self.app.sweep.lock:
            self.app.sweep.properties.logarithmic = logarithmic

    def update_mode(self, mode: 'SweepMode'):
        logger.debug("update_mode(%s)", mode)
        with self.app.sweep.lock:
            self.app.sweep.properties.mode = mode

    def update_padding(self, padding: int):
        logger.debug("update_padding(%s)", padding)
        self.padding = padding
        self.update_band()

    def update_title(self, title: str = ""):
        logger.debug("update_title(%s)", title)
        with self.app.sweep.lock:
            self.app.sweep.properties.name = title
        self.app.update_sweep_title()
